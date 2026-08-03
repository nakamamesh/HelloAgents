"""Settlement — checkout + x402 via XPay facilitator (no Coinbase)."""

from __future__ import annotations

import asyncio
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

    treasury = await wallet_svc.ensure_treasury_wallet()
    if treasury is None or not treasury.address:
        raise ValueError("platform treasury wallet unavailable — configure Turnkey")

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
            "pay_to": treasury.address,
            "treasury_wallet": treasury.address,
            "seller_wallet": seller.wallet_address,
            "buyer_wallet": buyer.wallet_address,
            "platform_keep_usdc": str(split.platform_keep_usdc),
            "fee_note": "v2 on-chain: gross→treasury; treasury pays seller_net + referral",
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
    # USDC EIP-3009 expects 27/28; Turnkey often returns 0/1
    if v_int in (0, 1):
        v_int += 27
    return "0x" + r_hex.zfill(64) + s_hex.zfill(64) + format(v_int, "02x")


def _rpc_url(network: str) -> str:
    if network in ("base-sepolia",):
        return "https://base-sepolia-rpc.publicnode.com"
    if network in ("base", "base-mainnet"):
        return "https://mainnet.base.org"
    return "https://base-sepolia-rpc.publicnode.com"


def _transfer_with_authorization_calldata(
    *,
    from_addr: str,
    to_addr: str,
    value_atomic: int,
    valid_after: int,
    valid_before: int,
    nonce: str,
    signature: str,
) -> str:
    from eth_abi import encode
    from eth_hash.auto import keccak

    raw = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
    if len(raw) != 65:
        raise ValueError(f"bad signature length {len(raw)}")
    r, s, v = raw[:32], raw[32:64], raw[64]
    sel = keccak(
        b"transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)"
    )[:4]
    args = encode(
        ["address", "address", "uint256", "uint256", "uint256", "bytes32", "uint8", "bytes32", "bytes32"],
        [
            from_addr,
            to_addr,
            value_atomic,
            valid_after,
            valid_before,
            bytes.fromhex(nonce[2:] if nonce.startswith("0x") else nonce),
            v,
            r,
            s,
        ],
    )
    return "0x" + sel.hex() + args.hex()


def _extract_signed_tx(signed: Any) -> str:
    signed_hex = getattr(signed, "signedTransaction", None)
    if not signed_hex and hasattr(signed, "model_dump"):
        signed_hex = (signed.model_dump() or {}).get("signedTransaction")
    if not signed_hex:
        dump = signed.model_dump() if hasattr(signed, "model_dump") else {}
        activity = dump.get("activity") or {}
        result = activity.get("result") or {}
        inner = result.get("signTransactionResult") or result
        signed_hex = inner.get("signedTransaction")
    if not signed_hex:
        raise RuntimeError(f"Turnkey sign_transaction missing signed tx: {signed}")
    if not str(signed_hex).startswith("0x"):
        signed_hex = "0x" + str(signed_hex)
    return str(signed_hex)


async def _broadcast_turnkey_call(
    *,
    from_addr: str,
    to_contract: str,
    data: str,
    network: str,
) -> dict[str, Any]:
    """Sign EIP-1559 contract call with Turnkey and broadcast via public RPC."""
    import rlp
    from turnkey_sdk_types.generated.types import SignTransactionBody, v1TransactionType

    chain_id = CHAIN_ID_BY_NETWORK[network]
    rpc = _rpc_url(network)

    async with httpx.AsyncClient(timeout=45.0, trust_env=False) as client:

        async def eth(method: str, params: list[Any]) -> Any:
            resp = await client.post(
                rpc, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            )
            resp.raise_for_status()
            body = resp.json()
            if body.get("error"):
                raise RuntimeError(f"rpc {method}: {body['error']}")
            return body["result"]

        tx_nonce = int(await eth("eth_getTransactionCount", [from_addr, "pending"]), 16)
        latest = await eth("eth_getBlockByNumber", ["latest", False])
        base_fee = int(latest["baseFeePerGas"], 16)
        max_priority = 1_000_000
        max_fee = base_fee * 2 + max_priority
        gas_est = int(
            await eth("eth_estimateGas", [{"from": from_addr, "to": to_contract, "data": data}]), 16
        )
        gas_limit = int(gas_est * 12 // 10)
        fields = [
            chain_id,
            tx_nonce,
            max_priority,
            max_fee,
            gas_limit,
            bytes.fromhex(to_contract[2:]),
            0,
            bytes.fromhex(data[2:]),
            [],
        ]
        unsigned_hex = "02" + rlp.encode(fields).hex()
        settings = get_settings()
        signed = wallet_svc.turnkey_client().sign_transaction(
            SignTransactionBody(
                organizationId=settings.turnkey_organization_id,
                signWith=from_addr,
                unsignedTransaction=unsigned_hex,
                type=v1TransactionType.TRANSACTION_TYPE_ETHEREUM,
            )
        )
        signed_hex = _extract_signed_tx(signed)
        tx_hash = await eth("eth_sendRawTransaction", [signed_hex])
        receipt = None
        for _ in range(20):
            await asyncio.sleep(1.5)
            receipt = await eth("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                break
        ok = bool(receipt and int(receipt.get("status", "0x0"), 16) == 1)
        return {
            "success": ok,
            "transaction": tx_hash,
            "network": network,
            "from": from_addr,
            "to": to_contract,
            "receipt_status": (receipt or {}).get("status"),
            "errorReason": None if ok else "tx_receipt_failed",
        }


def _usdc_transfer_calldata(*, to_addr: str, value_atomic: int) -> str:
    from eth_abi import encode
    from eth_hash.auto import keccak

    sel = keccak(b"transfer(address,uint256)")[:4]
    args = encode(["address", "uint256"], [to_addr, value_atomic])
    return "0x" + sel.hex() + args.hex()


async def _usdc_transfer_via_turnkey(
    *, from_addr: str, to_addr: str, value_atomic: int, network: str
) -> dict[str, Any]:
    asset = USDC_BY_NETWORK[network]
    data = _usdc_transfer_calldata(to_addr=to_addr, value_atomic=value_atomic)
    result = await _broadcast_turnkey_call(
        from_addr=from_addr, to_contract=asset, data=data, network=network
    )
    return {**result, "value_atomic": str(value_atomic), "recipient": to_addr}


async def _rpc_usdc_balance_atomic(address: str, network: str) -> int:
    asset = USDC_BY_NETWORK[network]
    addr = address.lower()
    data = "0x70a08231" + addr[2:].zfill(64)
    rpc = _rpc_url(network)
    async with httpx.AsyncClient(timeout=20.0, trust_env=False) as client:
        resp = await client.post(
            rpc,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": asset, "data": data}, "latest"],
            },
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(f"rpc balanceOf: {body['error']}")
        return int(body["result"], 16)


async def _wait_treasury_funded(
    *, treasury: str, need_atomic: int, network: str, attempts: int = 12
) -> int:
    """XPay can return success before the Transfer is queryable — poll briefly."""
    bal = 0
    for i in range(attempts):
        bal = await _rpc_usdc_balance_atomic(treasury, network)
        if bal >= need_atomic:
            return bal
        await asyncio.sleep(1.0 + i * 0.25)
    return bal


async def _self_settle_via_turnkey(
    *,
    from_addr: str,
    to_addr: str,
    value_atomic: int,
    valid_after: int,
    valid_before: int,
    nonce: str,
    signature: str,
    network: str,
) -> dict[str, Any]:
    """Submit EIP-3009 ourselves when XPay /settle fails (buyer pays gas via Turnkey)."""
    asset = USDC_BY_NETWORK[network]
    data = _transfer_with_authorization_calldata(
        from_addr=from_addr,
        to_addr=to_addr,
        value_atomic=value_atomic,
        valid_after=valid_after,
        valid_before=valid_before,
        nonce=nonce,
        signature=signature,
    )
    result = await _broadcast_turnkey_call(
        from_addr=from_addr, to_contract=asset, data=data, network=network
    )
    return {
        "success": result["success"],
        "self_settle": True,
        "transaction": result["transaction"],
        "network": network,
        "payer": from_addr,
        "errorReason": result.get("errorReason"),
        "receipt_status": result.get("receipt_status"),
    }


async def _disperse_splits(
    db: AsyncSession,
    *,
    txn: Transaction,
    buyer: Agent,
    network: str,
    dry_run: bool = False,
    prior_payouts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """After gross lands in treasury: pay seller_net + referral; platform_keep stays."""
    meta = txn.meta or {}
    treasury = meta.get("treasury_wallet") or meta.get("pay_to")
    seller_wallet = meta.get("seller_wallet")
    if not treasury or not seller_wallet:
        seller = await db.get(Agent, txn.seller_agent_id)
        seller_wallet = seller_wallet or (seller.wallet_address if seller else None)
    if not treasury or not seller_wallet:
        return {"success": False, "errorReason": "missing treasury/seller wallet"}

    prior = prior_payouts or meta.get("payouts") or {}
    payouts: dict[str, Any] = {
        "treasury": treasury,
        "seller_wallet": seller_wallet,
        "seller_net_usdc": str(txn.seller_net_usdc),
        "referral_usdc": str(txn.referral_usdc),
        "platform_keep_usdc": meta.get("platform_keep_usdc"),
    }

    if dry_run:
        payouts["dry_run"] = True
        payouts["success"] = True
        return payouts

    seller_atomic = int(to_atomic_usdc(txn.seller_net_usdc))
    ref_atomic = (
        int(to_atomic_usdc(txn.referral_usdc))
        if txn.referral_usdc > 0 and txn.referrer_agent_id is not None
        else 0
    )
    need = 0
    prior_seller = prior.get("seller") or {}
    if not prior_seller.get("success"):
        need += seller_atomic
    prior_ref = prior.get("referral") or {}
    if ref_atomic and not prior_ref.get("success"):
        need += ref_atomic
    if need > 0:
        bal = await _wait_treasury_funded(
            treasury=treasury, need_atomic=need, network=network
        )
        payouts["treasury_balance_atomic"] = str(bal)
        if bal < need:
            payouts["success"] = False
            payouts["errorReason"] = (
                f"treasury_underfunded need={need} have={bal}"
            )
            if prior_seller.get("success"):
                payouts["seller"] = prior_seller
            if prior_ref.get("success"):
                payouts["referral"] = prior_ref
            return payouts

    if prior_seller.get("success"):
        payouts["seller"] = {**prior_seller, "reused": True}
    else:
        seller_tx = await _usdc_transfer_via_turnkey(
            from_addr=treasury,
            to_addr=seller_wallet,
            value_atomic=seller_atomic,
            network=network,
        )
        payouts["seller"] = seller_tx
        if not seller_tx.get("success"):
            payouts["success"] = False
            payouts["errorReason"] = "seller_payout_failed"
            return payouts

    if txn.referral_usdc > 0 and txn.referrer_agent_id is not None:
        if prior_ref.get("success"):
            payouts["referral"] = {**prior_ref, "reused": True}
        else:
            referrer = await db.get(Agent, txn.referrer_agent_id)
            ref_wallet = referrer.wallet_address if referrer else None
            if not ref_wallet:
                payouts["referral"] = {
                    "success": False,
                    "errorReason": "referrer_has_no_wallet",
                }
                payouts["success"] = False
                return payouts
            ref_tx = await _usdc_transfer_via_turnkey(
                from_addr=treasury,
                to_addr=ref_wallet,
                value_atomic=ref_atomic,
                network=network,
            )
            payouts["referral"] = {**ref_tx, "referrer_wallet": ref_wallet}
            if ref_tx.get("success"):
                existing = await db.execute(
                    select(ReferralLedgerEntry).where(
                        ReferralLedgerEntry.idempotency_key == f"ref:{txn.id}"
                    )
                )
                entry = existing.scalar_one_or_none()
                if entry is not None:
                    entry.status = LedgerStatus.PAID.value
                    entry.meta = {
                        **(entry.meta or {}),
                        "payout_tx": ref_tx.get("transaction"),
                    }
            else:
                payouts["success"] = False
                payouts["errorReason"] = "referral_payout_failed"
                return payouts

    payouts["success"] = True
    return payouts


async def retry_payouts(db: AsyncSession, *, txn_id: uuid.UUID) -> dict[str, Any]:
    """Re-run treasury → seller/referrer after settle succeeded but disperse failed."""
    txn = await db.get(Transaction, txn_id)
    if txn is None:
        raise ValueError("transaction not found")
    allowed = {
        TransactionStatus.COMPLETED,
        TransactionStatus.SETTLED_PENDING_PAYOUT,
    }
    if txn.status not in allowed:
        raise ValueError(
            f"transaction status is {txn.status}, need completed or settled_pending_payout"
        )
    meta = txn.meta or {}
    settle = meta.get("settle") or {}
    if not settle.get("success"):
        raise ValueError("settle did not succeed; cannot retry payouts")
    prior = meta.get("payouts") or {}
    if prior.get("success") and txn.status == TransactionStatus.COMPLETED:
        return {
            "transaction_id": str(txn.id),
            "status": "completed",
            "reused": True,
            "payouts": prior,
        }
    buyer = await db.get(Agent, txn.buyer_agent_id)
    if buyer is None:
        raise ValueError("buyer missing")
    network = meta.get("network") or get_settings().wallet_network
    payouts = await _disperse_splits(
        db, txn=txn, buyer=buyer, network=network, prior_payouts=prior
    )
    if payouts.get("success"):
        txn.status = TransactionStatus.COMPLETED
        txn.completed_at = txn.completed_at or datetime.now(timezone.utc)
        status_out = "completed"
        try:
            from app.services import reputation as rep_svc

            rep = await rep_svc.apply_settlement_reputation(db, txn=txn)
            meta = {**meta, "reputation": rep}
        except Exception:  # noqa: BLE001
            logger.exception("reputation apply failed on retry")
        try:
            from app.services import learning as learn_svc

            learned = await learn_svc.record_settlement_outcome(db, txn=txn)
            meta = {**meta, "learning": learned}
        except Exception:  # noqa: BLE001
            logger.exception("platform learning record failed on retry")
    else:
        txn.status = TransactionStatus.SETTLED_PENDING_PAYOUT
        status_out = "settled_pending_payout"
    txn.meta = {
        **meta,
        "payouts": payouts,
        "payouts_retried_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.commit()
    await db.refresh(txn)
    return {
        "transaction_id": str(txn.id),
        "status": status_out,
        "reused": False,
        "payouts": payouts,
        "gross_usdc": str(txn.gross_usdc),
        "seller_net_usdc": str(txn.seller_net_usdc),
        "referral_usdc": str(txn.referral_usdc),
    }


async def facilitator_verify_and_settle(payment_payload: dict[str, Any], requirements: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    base = settings.x402_facilitator_url.rstrip("/")
    body = {"x402Version": 1, "paymentPayload": payment_payload, "paymentRequirements": requirements}
    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        verify = await client.post(f"{base}/verify", json=body)
        if verify.status_code >= 400:
            raise RuntimeError(f"facilitator verify failed: {verify.status_code} {verify.text[:300]}")
        verify_body = verify.json()
        if verify_body.get("isValid") is False:
            raise RuntimeError(f"facilitator verify invalid: {verify_body}")
        settle = await client.post(f"{base}/settle", json=body)
        if settle.status_code >= 400:
            raise RuntimeError(f"facilitator settle failed: {settle.status_code} {settle.text[:300]}")
        return settle.json()


async def _confirm_settle_on_chain(
    settle_result: dict[str, Any],
    *,
    from_addr: str,
    to_addr: str,
    value_atomic: int,
    network: str,
) -> dict[str, Any]:
    """Require mined receipt + USDC Transfer buyer→treasury before trusting XPay success."""
    if not settle_result.get("success"):
        return settle_result
    tx_hash = settle_result.get("transaction") or settle_result.get("txHash")
    if not tx_hash:
        return {
            **settle_result,
            "success": False,
            "errorReason": "facilitator_success_missing_tx",
            "confirmed": False,
        }

    rpc = _rpc_url(network)
    usdc = USDC_BY_NETWORK[network].lower()
    fr = from_addr.lower()
    to = to_addr.lower()
    transfer_topic = (
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    )

    async with httpx.AsyncClient(timeout=45.0, trust_env=False) as client:
        receipt = None
        for i in range(18):
            resp = await client.post(
                rpc,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_getTransactionReceipt",
                    "params": [tx_hash],
                },
            )
            resp.raise_for_status()
            body = resp.json()
            if body.get("error"):
                return {
                    **settle_result,
                    "success": False,
                    "errorReason": f"rpc receipt: {body['error']}",
                    "confirmed": False,
                }
            receipt = body.get("result")
            if receipt:
                break
            await asyncio.sleep(1.0 + i * 0.15)

    if not receipt:
        return {
            **settle_result,
            "success": False,
            "errorReason": "settle_tx_not_found",
            "transaction": tx_hash,
            "confirmed": False,
        }
    if int(receipt.get("status") or "0x0", 16) != 1:
        return {
            **settle_result,
            "success": False,
            "errorReason": "settle_tx_reverted",
            "transaction": tx_hash,
            "confirmed": False,
        }

    found = False
    for log in receipt.get("logs") or []:
        if (log.get("address") or "").lower() != usdc:
            continue
        topics = log.get("topics") or []
        if len(topics) < 3 or (topics[0] or "").lower() != transfer_topic:
            continue
        log_from = "0x" + topics[1][-40:].lower()
        log_to = "0x" + topics[2][-40:].lower()
        amount = int(log.get("data") or "0x0", 16)
        if log_from == fr and log_to == to and amount == value_atomic:
            found = True
            break

    if not found:
        return {
            **settle_result,
            "success": False,
            "errorReason": "settle_missing_usdc_transfer",
            "transaction": tx_hash,
            "confirmed": False,
        }

    return {
        **settle_result,
        "success": True,
        "transaction": tx_hash,
        "confirmed": True,
        "network": network,
        "payer": from_addr,
    }


async def pay_and_settle(db: AsyncSession, *, buyer: Agent, txn_id: uuid.UUID) -> dict[str, Any]:
    """Sign EIP-3009 via Turnkey, settle via XPay (or self-settle), then disperse fee splits."""
    txn = await db.get(Transaction, txn_id)
    if txn is None:
        raise ValueError("transaction not found")
    if txn.buyer_agent_id != buyer.id:
        raise ValueError("not your transaction")
    if txn.status == TransactionStatus.COMPLETED:
        return {"transaction_id": str(txn.id), "status": "completed", "reused": True, "meta": txn.meta}
    if txn.status == TransactionStatus.SETTLED_PENDING_PAYOUT:
        return await retry_payouts(db, txn_id=txn_id)
    if txn.status != TransactionStatus.PENDING:
        raise ValueError(f"transaction status is {txn.status}")

    settings = get_settings()
    network = (txn.meta or {}).get("network") or settings.wallet_network
    pay_to = (txn.meta or {}).get("pay_to")
    from_addr = buyer.wallet_address
    if not from_addr or not pay_to:
        raise ValueError("missing buyer/pay_to wallet")

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
        payouts = await _disperse_splits(
            db, txn=txn, buyer=buyer, network=network, dry_run=True
        )
        txn.status = TransactionStatus.COMPLETED
        txn.completed_at = datetime.now(timezone.utc)
        txn.checkout_id = f"dry-run-{txn.id}"
        txn.meta = {
            **(txn.meta or {}),
            "settle": settle_result,
            "payouts": payouts,
            "dry_run": True,
        }
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
            "payouts": payouts,
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
    if settle_result.get("success"):
        settle_result = await _confirm_settle_on_chain(
            settle_result,
            from_addr=from_addr,
            to_addr=pay_to,
            value_atomic=value_atomic,
            network=network,
        )
    if not settle_result.get("success"):
        logger.warning(
            "XPay settle failed/unconfirmed (%s) — attempting Turnkey self-settle",
            settle_result.get("errorReason"),
        )
        try:
            settle_result = await _self_settle_via_turnkey(
                from_addr=from_addr,
                to_addr=pay_to,
                value_atomic=value_atomic,
                valid_after=0,
                valid_before=now + 600,
                nonce=nonce,
                signature=signature,
                network=network,
            )
        except Exception as exc:  # noqa: BLE001 — surface as settle failure
            logger.exception("self-settle failed")
            settle_result = {
                "success": False,
                "errorReason": f"self_settle_error: {exc}",
                "facilitator": settle_result,
                "network": network,
                "payer": from_addr,
            }

    payouts: dict[str, Any] | None = None
    txn.meta = {
        **(txn.meta or {}),
        "settle": settle_result,
        "payment_payload": {"authorization": payment_payload["payload"]["authorization"]},
    }

    if settle_result.get("success"):
        txn.checkout_id = str(settle_result.get("transaction") or settle_result.get("txHash") or "")
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
        try:
            payouts = await _disperse_splits(db, txn=txn, buyer=buyer, network=network)
        except Exception as exc:  # noqa: BLE001
            logger.exception("payout disperse failed")
            payouts = {"success": False, "errorReason": str(exc)}
        txn.meta = {**(txn.meta or {}), "payouts": payouts}
        if payouts and payouts.get("success"):
            txn.status = TransactionStatus.COMPLETED
            txn.completed_at = datetime.now(timezone.utc)
            status_out = "completed"
            try:
                from app.services import reputation as rep_svc

                rep = await rep_svc.apply_settlement_reputation(db, txn=txn)
                txn.meta = {**(txn.meta or {}), "reputation": rep}
            except Exception:  # noqa: BLE001
                logger.exception("reputation apply failed")
            try:
                from app.services import learning as learn_svc

                learned = await learn_svc.record_settlement_outcome(db, txn=txn)
                txn.meta = {**(txn.meta or {}), "learning": learned}
            except Exception:  # noqa: BLE001
                logger.exception("platform learning record failed")
        else:
            txn.status = TransactionStatus.SETTLED_PENDING_PAYOUT
            status_out = "settled_pending_payout"
    else:
        txn.status = TransactionStatus.FAILED
        status_out = "failed"

    await db.commit()
    await db.refresh(txn)
    return {
        "transaction_id": str(txn.id),
        "status": status_out,
        "checkout_id": txn.checkout_id,
        "gross_usdc": str(txn.gross_usdc),
        "seller_net_usdc": str(txn.seller_net_usdc),
        "platform_fee_usdc": str(txn.platform_fee_usdc),
        "referral_usdc": str(txn.referral_usdc),
        "settle": settle_result,
        "payouts": payouts,
    }
