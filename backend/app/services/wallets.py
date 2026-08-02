"""Turnkey agent wallets — provision + balance (Phase 3). No settlement."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_NAME_RE = re.compile(r"[^a-z0-9\-]+")

_CAIP2 = {
    "base-sepolia": "eip155:84532",
    "base": "eip155:8453",
    "base-mainnet": "eip155:8453",
}


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
