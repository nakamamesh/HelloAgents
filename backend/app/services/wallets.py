"""Turnkey agent wallets — provision, balances, spend policies (Phase 3–4)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_NAME_RE = re.compile(r"[^a-z0-9\-]+")

_CAIP2 = {
    "base-sepolia": "eip155:84532",
    "base": "eip155:8453",
    "base-mainnet": "eip155:8453",
}

USDC_BY_NETWORK = {
    "base-sepolia": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "base-mainnet": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
}

POLICY_EIP3009 = "ha-allow-eip3009-usdc-capped"
POLICY_SIGN_TX_USDC = "ha-allow-sign-tx-usdc-contract"


@dataclass(frozen=True)
class WalletProvision:
    wallet_id: str  # Turnkey wallet id
    address: str
    network: str


def wallet_configured() -> bool:
    s = get_settings()
    return bool(
        s.turnkey_organization_id
        and s.turnkey_api_public_key
        and s.turnkey_api_private_key
    )


def account_name_for_slug(slug: str) -> str:
    cleaned = _NAME_RE.sub("-", slug.lower()).strip("-")[:80]
    return f"ha-{cleaned}"


def _client():
    from turnkey_api_key_stamper import ApiKeyStamper, ApiKeyStamperConfig
    from turnkey_http import TurnkeyClient

    settings = get_settings()
    stamper = ApiKeyStamper(
        ApiKeyStamperConfig(
            api_public_key=settings.turnkey_api_public_key,
            api_private_key=settings.turnkey_api_private_key,
        )
    )
    return TurnkeyClient(
        base_url=settings.turnkey_api_base_url,
        stamper=stamper,
        organization_id=settings.turnkey_organization_id,
    )


def turnkey_client():
    """Public accessor for Turnkey HTTP client."""
    if not wallet_configured():
        raise RuntimeError("Turnkey not configured")
    return _client()


def _eth_account_params():
    from turnkey_sdk_types.generated.types import (
        v1AddressFormat,
        v1Curve,
        v1PathFormat,
        v1WalletAccountParams,
    )

    return v1WalletAccountParams(
        curve=v1Curve.CURVE_SECP256K1,
        pathFormat=v1PathFormat.PATH_FORMAT_BIP32,
        path="m/44'/60'/0'/0/0",
        addressFormat=v1AddressFormat.ADDRESS_FORMAT_ETHEREUM,
    )


async def provision_evm_account(slug: str) -> WalletProvision | None:
    """Idempotent Turnkey EVM wallet for an agent. None if Turnkey not configured."""
    if not wallet_configured():
        logger.info("Turnkey not configured — skip wallet for %s", slug)
        return None

    settings = get_settings()
    name = account_name_for_slug(slug)
    from turnkey_sdk_types.generated.types import (
        CreateWalletBody,
        GetWalletAccountsBody,
        GetWalletsBody,
    )

    client = _client()
    org = settings.turnkey_organization_id

    existing = client.get_wallets(GetWalletsBody(organizationId=org))
    for w in existing.wallets or []:
        if getattr(w, "walletName", None) == name:
            accounts = client.get_wallet_accounts(
                GetWalletAccountsBody(organizationId=org, walletId=w.walletId)
            )
            address = None
            for acc in accounts.accounts or []:
                address = getattr(acc, "address", None)
                if address:
                    break
            if address:
                return WalletProvision(
                    wallet_id=w.walletId,
                    address=address,
                    network=settings.wallet_network,
                )

    created = client.create_wallet(
        CreateWalletBody(
            organizationId=org,
            walletName=name,
            accounts=[_eth_account_params()],
        )
    )
    addresses = list(created.addresses or [])
    if not addresses:
        raise RuntimeError(f"Turnkey created wallet {created.walletId} with no address")
    return WalletProvision(
        wallet_id=created.walletId,
        address=addresses[0],
        network=settings.wallet_network,
    )


async def ensure_treasury_wallet() -> WalletProvision | None:
    return await provision_evm_account("platform-treasury")


async def list_balances(address: str) -> dict[str, Any]:
    """Read balances for an address via Turnkey (network from settings)."""
    if not wallet_configured():
        return {"configured": False, "balances": []}

    settings = get_settings()
    caip2 = _CAIP2.get(settings.wallet_network, settings.wallet_network)
    from turnkey_sdk_types.generated.types import GetWalletAddressBalancesBody

    client = _client()
    result = client.get_wallet_address_balances(
        GetWalletAddressBalancesBody(
            organizationId=settings.turnkey_organization_id,
            address=address,
            caip2=caip2,
        )
    )

    balances: list[dict[str, str]] = []
    for item in result.balances or []:
        balances.append(
            {
                "symbol": str(
                    getattr(item, "symbol", None) or getattr(item, "asset", None) or "?"
                ),
                "amount": str(
                    getattr(item, "balance", None)
                    or getattr(item, "amount", None)
                    or "0"
                ),
                "contract": str(
                    getattr(item, "address", None)
                    or getattr(item, "contractAddress", None)
                    or ""
                ),
            }
        )

    return {
        "configured": True,
        "network": settings.wallet_network,
        "address": address,
        "balances": balances,
    }


def _spend_limit_atomic() -> int:
    settings = get_settings()
    usdc = Decimal(str(settings.wallet_spend_limit_usdc))
    return int(usdc * Decimal(1_000_000))


def _policy_specs(*, treasury_address: str, usdc: str, limit_atomic: int) -> list[dict[str, str]]:
    """Org ALLOW policies: EIP-3009 to treasury under cap; SIGN_TX only to USDC contract."""
    return [
        {
            "policyName": POLICY_EIP3009,
            "condition": (
                "activity.type == 'ACTIVITY_TYPE_SIGN_RAW_PAYLOAD_V2' && "
                "eth.eip_712.primary_type == 'TransferWithAuthorization' && "
                "eth.eip_712.domain.name == 'USDC' && "
                f"eth.eip_712.domain.verifying_contract == '{usdc}' && "
                f"eth.eip_712.message.to == '{treasury_address}' && "
                f"eth.eip_712.message.value <= {limit_atomic}"
            ),
            "notes": (
                f"HelloAgents: EIP-3009 USDC only to treasury, max {limit_atomic} atomic"
            ),
        },
        {
            "policyName": POLICY_SIGN_TX_USDC,
            "condition": (
                "(activity.type == 'ACTIVITY_TYPE_SIGN_TRANSACTION_V2' || "
                "activity.type == 'ACTIVITY_TYPE_SIGN_TRANSACTION') && "
                f"eth.tx.to == '{usdc}'"
            ),
            "notes": "HelloAgents: EVM txs only to USDC contract (self-settle + ERC20 transfer)",
        },
    ]


async def ensure_spend_policies(*, treasury_address: str | None = None) -> dict[str, Any]:
    """Idempotent Turnkey org policies for spend limit + USDC/treasury allowlist."""
    if not wallet_configured():
        return {"ok": False, "error": "Turnkey not configured"}

    from turnkey_sdk_types.generated.types import (
        CreatePolicyBody,
        GetPoliciesBody,
        UpdatePolicyBody,
        v1Effect,
    )

    settings = get_settings()
    if not treasury_address:
        treasury = await ensure_treasury_wallet()
        if treasury is None:
            return {"ok": False, "error": "treasury wallet unavailable"}
        treasury_address = treasury.address

    network = settings.wallet_network
    usdc = USDC_BY_NETWORK.get(network, USDC_BY_NETWORK["base-sepolia"])
    limit_atomic = _spend_limit_atomic()
    specs = _policy_specs(
        treasury_address=treasury_address, usdc=usdc, limit_atomic=limit_atomic
    )

    client = _client()
    org = settings.turnkey_organization_id
    existing = client.get_policies(GetPoliciesBody(organizationId=org))
    by_name: dict[str, Any] = {}
    for p in existing.policies or []:
        name = getattr(p, "policyName", None) or getattr(p, "name", None)
        if name:
            by_name[str(name)] = p

    created: list[str] = []
    updated: list[str] = []
    for spec in specs:
        name = spec["policyName"]
        prior = by_name.get(name)
        if prior is None:
            client.create_policy(
                CreatePolicyBody(
                    organizationId=org,
                    policyName=name,
                    effect=v1Effect.EFFECT_ALLOW,
                    condition=spec["condition"],
                    notes=spec["notes"],
                )
            )
            created.append(name)
            continue
        policy_id = getattr(prior, "policyId", None) or getattr(prior, "id", None)
        prior_cond = getattr(prior, "condition", None) or ""
        if policy_id and prior_cond != spec["condition"]:
            client.update_policy(
                UpdatePolicyBody(
                    organizationId=org,
                    policyId=str(policy_id),
                    policyName=name,
                    policyEffect=v1Effect.EFFECT_ALLOW,
                    policyCondition=spec["condition"],
                    policyNotes=spec["notes"],
                )
            )
            updated.append(name)

    return {
        "ok": True,
        "network": network,
        "usdc": usdc,
        "treasury": treasury_address,
        "spend_limit_usdc": str(settings.wallet_spend_limit_usdc),
        "spend_limit_atomic": limit_atomic,
        "created": created,
        "updated": updated,
        "unchanged": [
            s["policyName"]
            for s in specs
            if s["policyName"] not in created and s["policyName"] not in updated
        ],
        "note": (
            "ALLOW policies only — confirm org has no unrestricted SIGN_* allows "
            "that bypass these guards"
        ),
    }
