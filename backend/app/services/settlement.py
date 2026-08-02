"""Phase 4 settlement — checkout + x402 via XPay facilitator (no Coinbase)."""

from __future__ import annotations

import logging
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import money
from app.models.fees import FeeConfig, LedgerStatus, ReferralLedgerEntry
from app.models.orm import Agent, Listing, ListingStatus, Transaction, TransactionStatus
from app.services.fees import DEFAULT_RATES, FeeRates, compute_split
from app.services import wallets as wallet_svc

logger = logging.getLogger(__name__)

USDC_BY_NETWORK = {
    "base-sepolia": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "base-mainnet": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
}

CHAIN_ID_BY_NETWORK = {
    "base-sepolia": 84532,
    "base": 8453,
    "base-mainnet": 8453,
}


@dataclass(frozen=True)
class CheckoutResult:
    transaction: Transaction
    payment_requirements: dict[str, Any]
    reused: bool


async def _active_rates(db: AsyncSession) -> FeeRates:
    result = await db.execute(
        select(FeeConfig).where(FeeConfig.active.is_(True)).order_by(FeeConfig.created_at.desc())
    )
    row = result.scalars().first()
    if row is None:
        return DEFAULT_RATES
    return FeeRates(platform_fee_bps=row.platform_fee_bps, referral_bps=row.referral_bps)


def to_atomic_usdc(amount: Decimal) -> str:
    """USDC has 6 decimals — x402 maxAmountRequired is atomic units as decimal string."""
    atomic = int(money(amount) * Decimal(1_000_000))
    return str(atomic)


async def create_checkout(
    db: AsyncSession,
    *,
    buyer: Agent,
    listing_id: uuid.UUID,
    idempotency_key: str,
) -> CheckoutResult:
    existing = await db.execute(
        select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    )
    prior = existing.scalar_one_or_none()
    if prior is not None:
        return CheckoutResult(
            transaction=prior,
            payment_requirements=_payment_requirements_for(prior),
            reused=True,
        )

    listing = await db.get(Listing, listing_id)
    if listing is None or listing.status != ListingStatus.ACTIVE:
        raise ValueError("listing not found or inactive")

    seller = await db.get(Agent, listing.agent_id)
    if seller is None or not seller.wallet_address:
        raise ValueError("seller has no wallet_address")
    if buyer.id == seller.id:
        raise ValueError("cannot buy own listing")
    if not buyer.wallet_address:
        raise ValueError("buyer has no wallet_address — run wallet backfill")

    rates = await _active_rates(db)
    has_referrer = buyer.referred_by_agent_id is not None
    split = compute_split(listing.price_usdc, has_referrer=has_referrer, rates=rates)

    settings = get_settings()
    txn = Transaction(
        idempotency_key=idempotency_key,
        listing_id=listing.id,
        buyer_agent_id=buyer.id,
        seller_agent_id=seller.id,
        gross_usdc=split.gross_usdc,
        platform_fee_usdc=split.platform_fee_usdc,
        referral_usdc=split.referral_usdc,
        seller_net_usdc=split.seller_net_usdc,
        referrer_agent_id=buyer.referred_by_agent_id,
        status=TransactionStatus.PENDING,
        meta={
            "network": settings.wallet_network,
            "pay_to": seller.wallet_address,
            "buyer_wallet": buyer.wallet_address,
            "platform_keep_usdc": str(split.platform_keep_usdc),
            "fee_note": "v1 on-chain: gross→seller; fee/referral ledger off-chain",
        },
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return CheckoutResult(
        transaction=txn,
        payment_requirements=_payment_requirements_for(txn),
        reused=False,
    )


def _payment_requirements_for(txn: Transaction) -> dict[str, Any]:
    settings = get_settings()
    network = (txn.meta or {}).get("network") or settings.wallet_network
    asset = USDC_BY_NETWORK.get(network, USDC_BY_NETWORK["base-sepolia"])
    pay_to = (txn.meta or {}).get("pay_to")
    return {
        "x402Version": 1,
        "error": "Payment required to complete purchase",
        "accepts": [
            {
                "scheme": "exact",
                "network": network,
                "maxAmountRequired": to_atomic_usdc(txn.gross_usdc),
                "resource": f"/agent/buy/{txn.id}/pay",
                "description": f"HelloAgents listing purchase {txn.listing_id}",
                "mimeType": "application/json",
                "payTo": pay_to,
                "maxTimeoutSeconds": 600,
                "asset": asset,
                "extra": {"name": "USDC", "version": "2"},
            }
        ],
        "transaction_id": str(txn.id),
        "gross_usdc": str(txn.gross_usdc),
        "seller_net_usdc": str(txn.seller_net_usdc),
        "platform_fee_usdc": str(txn.platform_fee_usdc),
        "referral_usdc": str(txn.referral_usdc),
    }


def _eip712_transfer_with_authorization(
    *,
    from_addr: str,
    to_addr: str,
    value_atomic: int,
    valid_after: int,
    valid_before: int,
    nonce: str,
    network: str,
) -> dict[str, Any]:
    asset = USDC_BY_NETWORK[network]
    chain_id = CHAIN_ID_BY_NETWORK[network]
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": "USDC",
            "version": "2",
            "chainId": chain_id,
            "verifyingContract": asset,
        },
        "message": {
            "from": from_addr,
            "to": to_addr,
            "value": str(value_atomic),
            "validAfter": str(valid_after),
            "validBefore": str(valid_before),
            "nonce": nonce,
        },
    }


def _turnkey_sign_eip712(*, sign_with: str, typed_data: dict[str, Any]) -> str:
    import json

    from turnkey_sdk_types.generated.types import (
        SignRawPayloadBody,
        v1HashFunction,
        v1PayloadEncoding,
    )

    if not wallet_svc.wallet_configured():
        raise RuntimeError("Turnkey not configured")

    settings = get_settings()
    client = wallet_svc.turnkey_client()
    resp = client.sign_raw_payload(
        SignRawPayloadBody(
            organizationId=settings.turnkey_organization_id,
            signWith=sign_with,
            payload=json.dumps(typed_data),
            encoding=v1PayloadEncoding.PAYLOAD_ENCODING_EIP712,
            hashFunction=v1HashFunction.HASH_FUNCTION_NOT_APPLICABLE,
        )
    )
    r, s, v = resp.r, resp.s, resp.v
    if not (r and s and v is not None):
        raise RuntimeError(f"unexpected Turnkey sign response: {resp}")
    r_hex = r[2:] if str(r).startswith("0x") else str(r)
    s_hex = s[2:] if str(s).startswith("0x") else str(s)
    v_int = int(str(v), 16) if str(v).startswith("0x") else int(v)
    return "0x" + r_hex.zfill(64) + s_hex.zfill(64) + format(v_int, "02x")


async def facilitator_verify_and_settle(payment_payload: dict[str, Any], requirements: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    base = settings.x402_facilitator_url.rstrip("/")
    body = {"x402Version": 1, "paymentPayload": payment_payload, "paymentRequirements": requirements}
    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        verify = await client.post(f"{base}/verify", json=body)
        if verify.status_code >= 400:
            raise RuntimeError(f"facilitator verify failed: {verify.status_code} {verify.text[:300]}")
        settle = await client.post(f"{base}/settle", json=body)
        if settle.status_code >= 400:
            raise RuntimeError(f"facilitator settle failed: {settle.status_code} {settle.text[:300]}")
        return settle.json()


async def pay_and_settle(db: AsyncSession, *, buyer: Agent, txn_id: uuid.UUID) -> dict[str, Any]:
    """Sign EIP-3009 via Turnkey, settle via XPay facilitator, finalize txn + referral ledger."""
    txn = await db.get(Transaction, txn_id)
    if txn is None:
        raise ValueError("transaction not found")
    if txn.buyer_agent_id != buyer.id:
        raise ValueError("not your transaction")
    if txn.status == TransactionStatus.COMPLETED:
        return {"transaction_id": str(txn.id), "status": "completed", "reused": True, "meta": txn.meta}
    if txn.status != TransactionStatus.PENDING:
        raise ValueError(f"transaction status is {txn.status}")

    settings = get_settings()
    network = (txn.meta or {}).get("network") or settings.wallet_network
    pay_to = (txn.meta or {}).get("pay_to")
    from_addr = buyer.wallet_address
    if not from_addr or not pay_to:
        raise ValueError("missing buyer/seller wallet")

    if settings.settlement_dry_run:
        settle_result = {
            "success": True,
            "dry_run": True,
            "network": network,
            "from": from_addr,
            "to": pay_to,
            "value_atomic": to_atomic_usdc(txn.gross_usdc),
            "note": "SETTLEMENT_DRY_RUN=true — no on-chain transfer",
        }
        txn.status = TransactionStatus.COMPLETED
        txn.completed_at = datetime.now(timezone.utc)
        txn.checkout_id = f"dry-run-{txn.id}"
        txn.meta = {**(txn.meta or {}), "settle": settle_result, "dry_run": True}
        if txn.referral_usdc > 0 and txn.referrer_agent_id is not None:
            db.add(
                ReferralLedgerEntry(
                    referrer_agent_id=txn.referrer_agent_id,
                    referred_agent_id=buyer.id,
                    transaction_id=txn.id,
                    amount_usdc=txn.referral_usdc,
                    status=LedgerStatus.PENDING.value,
                    idempotency_key=f"ref:{txn.id}",
                    meta={"network": network, "dry_run": True},
                )
            )
        await db.commit()
        await db.refresh(txn)
        return {
            "transaction_id": str(txn.id),
            "status": "completed",
            "dry_run": True,
            "checkout_id": txn.checkout_id,
            "gross_usdc": str(txn.gross_usdc),
            "seller_net_usdc": str(txn.seller_net_usdc),
            "platform_fee_usdc": str(txn.platform_fee_usdc),
            "referral_usdc": str(txn.referral_usdc),
            "settle": settle_result,
        }

    value_atomic = int(to_atomic_usdc(txn.gross_usdc))
    now = int(time.time())
    nonce = "0x" + secrets.token_hex(32)
    typed = _eip712_transfer_with_authorization(
        from_addr=from_addr,
        to_addr=pay_to,
        value_atomic=value_atomic,
        valid_after=0,
        valid_before=now + 600,
        nonce=nonce,
        network=network,
    )
    signature = _turnkey_sign_eip712(sign_with=from_addr, typed_data=typed)

    accept = _payment_requirements_for(txn)["accepts"][0]
    payment_payload = {
        "x402Version": 1,
        "scheme": "exact",
        "network": network,
        "payload": {
            "signature": signature,
            "authorization": {
                "from": from_addr,
                "to": pay_to,
                "value": str(value_atomic),
                "validAfter": "0",
                "validBefore": str(now + 600),
                "nonce": nonce,
            },
        },
    }

    settle_result = await facilitator_verify_and_settle(payment_payload, accept)

    txn.status = TransactionStatus.COMPLETED
    txn.completed_at = datetime.now(timezone.utc)
    txn.checkout_id = str(settle_result.get("transaction") or settle_result.get("txHash") or "")
    txn.meta = {
        **(txn.meta or {}),
        "settle": settle_result,
        "payment_payload": {"authorization": payment_payload["payload"]["authorization"]},
    }

    if txn.referral_usdc > 0 and txn.referrer_agent_id is not None:
        db.add(
            ReferralLedgerEntry(
                referrer_agent_id=txn.referrer_agent_id,
                referred_agent_id=buyer.id,
                transaction_id=txn.id,
                amount_usdc=txn.referral_usdc,
                status=LedgerStatus.PENDING.value,
                idempotency_key=f"ref:{txn.id}",
                meta={"network": network},
            )
        )

    await db.commit()
    await db.refresh(txn)
    return {
        "transaction_id": str(txn.id),
        "status": "completed",
        "checkout_id": txn.checkout_id,
        "gross_usdc": str(txn.gross_usdc),
        "seller_net_usdc": str(txn.seller_net_usdc),
        "platform_fee_usdc": str(txn.platform_fee_usdc),
        "referral_usdc": str(txn.referral_usdc),
        "settle": settle_result,
    }
