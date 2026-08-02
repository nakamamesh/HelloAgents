"""Coinbase CDP agentic wallets — provision + balance (Phase 3). No settlement."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_NAME_RE = re.compile(r"[^a-z0-9\-]+")


@dataclass(frozen=True)
class WalletProvision:
    wallet_id: str  # CDP account name
    address: str
    network: str


def cdp_configured() -> bool:
    s = get_settings()
    return bool(s.cdp_api_key_id and s.cdp_api_key_secret and s.cdp_wallet_secret)


def account_name_for_slug(slug: str) -> str:
    cleaned = _NAME_RE.sub("-", slug.lower()).strip("-")[:100]
    return f"ha-{cleaned}"


async def provision_evm_account(slug: str) -> WalletProvision | None:
    """Idempotent CDP EVM account for an agent. None if CDP not configured."""
    if not cdp_configured():
        logger.info("CDP not configured — skip wallet for %s", slug)
        return None

    settings = get_settings()
    name = account_name_for_slug(slug)
    from cdp import CdpClient
    from cdp.update_account_types import UpdateAccountOptions

    async with CdpClient(
        api_key_id=settings.cdp_api_key_id,
        api_key_secret=settings.cdp_api_key_secret,
        wallet_secret=settings.cdp_wallet_secret,
    ) as cdp:
        account = await cdp.evm.get_or_create_account(name=name)
        if settings.cdp_account_policy_id:
            try:
                account = await cdp.evm.update_account(
                    address=account.address,
                    update=UpdateAccountOptions(
                        account_policy=settings.cdp_account_policy_id
                    ),
                )
            except Exception:  # noqa: BLE001
                logger.warning("Could not attach CDP policy to %s", name, exc_info=True)

    return WalletProvision(
        wallet_id=name,
        address=account.address,
        network=settings.cdp_network,
    )


async def ensure_treasury_wallet() -> WalletProvision | None:
    """Platform fee treasury account (separate from agent wallets)."""
    return await provision_evm_account("platform-treasury")


async def list_balances(address: str) -> dict[str, Any]:
    """Read token balances for an address on configured network."""
    if not cdp_configured():
        return {"configured": False, "balances": []}

    settings = get_settings()
    from cdp import CdpClient

    async with CdpClient(
        api_key_id=settings.cdp_api_key_id,
        api_key_secret=settings.cdp_api_key_secret,
        wallet_secret=settings.cdp_wallet_secret,
    ) as cdp:
        result = await cdp.evm.list_token_balances(
            address=address,
            network=settings.cdp_network,
        )

    balances: list[dict[str, str]] = []
    for item in result.balances:
        token = item.token
        amount = item.amount
        balances.append(
            {
                "symbol": str(getattr(token, "symbol", None) or "?"),
                "amount": str(getattr(amount, "amount", amount)),
                "decimals": str(getattr(amount, "decimals", "")),
                "contract": str(getattr(token, "contract_address", None) or ""),
            }
        )

    return {
        "configured": True,
        "network": settings.cdp_network,
        "address": address,
        "balances": balances,
    }
