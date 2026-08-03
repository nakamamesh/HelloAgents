"""Post-settlement fulfillment: deliver → review → dispute / SLA timeout."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import money
from app.models.orm import Agent, Transaction, TransactionStatus

logger = logging.getLogger(__name__)

AWAITING = "awaiting_delivery"
DELIVERED = "delivered"
ACCEPTED = "accepted"
DISPUTED = "disputed"
TIMED_OUT = "timed_out"
REFUND_REQUESTED = "refund_requested"
NONE = "none"

REP_BUYER_ACCEPT = Decimal("0.020000")
REP_SELLER_ACCEPT = Decimal("0.030000")
REP_DISPUTE_HIT = Decimal("0.050000")


def mark_awaiting_delivery(txn: Transaction) -> None:
    """Call when settlement reaches COMPLETED (or dry-run complete)."""
    if txn.fulfillment_status and txn.fulfillment_status not in (NONE, ""):
        return
    settings = get_settings()
    now = datetime.now(timezone.utc)
    txn.fulfillment_status = AWAITING
    txn.delivery_deadline_at = now + timedelta(hours=max(1, settings.delivery_sla_hours))


def _txn_dict(txn: Transaction) -> dict[str, Any]:
    return {
        "transaction_id": str(txn.id),
        "status": txn.status.value if hasattr(txn.status, "value") else str(txn.status),
        "fulfillment_status": txn.fulfillment_status,
        "listing_id": str(txn.listing_id) if txn.listing_id else None,
        "buyer_agent_id": str(txn.buyer_agent_id) if txn.buyer_agent_id else None,
        "seller_agent_id": str(txn.seller_agent_id) if txn.seller_agent_id else None,
        "gross_usdc": str(txn.gross_usdc),
        "seller_net_usdc": str(txn.seller_net_usdc),
        "referral_usdc": str(txn.referral_usdc),
        "platform_fee_usdc": str(txn.platform_fee_usdc),
        "artifact_uri": txn.artifact_uri,
        "artifact_hash": txn.artifact_hash,
        "delivered_at": txn.delivered_at.isoformat() if txn.delivered_at else None,
        "delivery_deadline_at": (
            txn.delivery_deadline_at.isoformat() if txn.delivery_deadline_at else None
        ),
        "review_score": str(txn.review_score) if txn.review_score is not None else None,
        "review_notes": txn.review_notes,
        "reviewed_at": txn.reviewed_at.isoformat() if txn.reviewed_at else None,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
        "completed_at": txn.completed_at.isoformat() if txn.completed_at else None,
        "meta": {
            k: v
            for k, v in (txn.meta or {}).items()
            if k not in ("payment_payload",)  # omit bulky auth blobs
        },
    }


async def list_agent_transactions(
    db: AsyncSession,
    *,
    agent: Agent,
    limit: int = 50,
    role: str | None = None,
) -> list[dict[str, Any]]:
    q = select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
    if role == "buyer":
        q = q.where(Transaction.buyer_agent_id == agent.id)
    elif role == "seller":
        q = q.where(Transaction.seller_agent_id == agent.id)
    else:
        from sqlalchemy import or_

        q = q.where(
            or_(
                Transaction.buyer_agent_id == agent.id,
                Transaction.seller_agent_id == agent.id,
            )
        )
    res = await db.execute(q)
    return [_txn_dict(t) for t in res.scalars().all()]


async def deliver(
    db: AsyncSession,
    *,
    seller: Agent,
    txn_id: uuid.UUID,
    artifact_uri: str,
    artifact_payload: str | None = None,
) -> dict[str, Any]:
    txn = await db.get(Transaction, txn_id)
    if txn is None:
        raise ValueError("transaction not found")
    if txn.seller_agent_id != seller.id:
        raise ValueError("only the seller can deliver")
    if txn.status not in (
        TransactionStatus.COMPLETED,
        TransactionStatus.SETTLED_PENDING_PAYOUT,
    ):
        raise ValueError(f"cannot deliver when payment status is {txn.status}")
    if txn.fulfillment_status not in (AWAITING, TIMED_OUT, DELIVERED):
        raise ValueError(f"fulfillment is {txn.fulfillment_status}, need awaiting_delivery")
    uri = artifact_uri.strip()
    if not uri:
        raise ValueError("artifact_uri required")
    digest = None
    if artifact_payload:
        digest = hashlib.sha256(artifact_payload.encode("utf-8")).hexdigest()
    elif uri.startswith("sha256:"):
        digest = uri.split(":", 1)[1][:128]
    else:
        digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()

    txn.artifact_uri = uri[:4000]
    txn.artifact_hash = digest
    txn.delivered_at = datetime.now(timezone.utc)
    txn.fulfillment_status = DELIVERED
    meta = dict(txn.meta or {})
    meta["delivery"] = {
        "by": str(seller.id),
        "at": txn.delivered_at.isoformat(),
        "uri": txn.artifact_uri,
        "hash": digest,
    }
    txn.meta = meta
    await db.commit()
    await db.refresh(txn)
    try:
        from app.services import webhooks as wh

        await wh.emit(
            "order.delivered",
            {"transaction_id": str(txn.id), "seller_slug": seller.slug, "artifact_uri": uri},
        )
    except Exception:  # noqa: BLE001
        logger.debug("webhook emit skipped", exc_info=True)
    return _txn_dict(txn)


async def review(
    db: AsyncSession,
    *,
    buyer: Agent,
    txn_id: uuid.UUID,
    score: Decimal,
    notes: str | None = None,
    accept: bool = True,
) -> dict[str, Any]:
    txn = await db.get(Transaction, txn_id)
    if txn is None:
        raise ValueError("transaction not found")
    if txn.buyer_agent_id != buyer.id:
        raise ValueError("only the buyer can review")
    if txn.fulfillment_status != DELIVERED:
        raise ValueError("seller must deliver before review")
    score = money(score)
    if score < Decimal("0") or score > Decimal("1"):
        raise ValueError("score must be 0..1")
    txn.review_score = score
    txn.review_notes = (notes or "")[:4000] or None
    txn.reviewed_at = datetime.now(timezone.utc)
    txn.fulfillment_status = ACCEPTED if accept else DISPUTED

    from app.services import reputation as rep_svc

    out: dict[str, Any] = {"review": _txn_dict(txn)}
    if accept and score >= Decimal("0.700000"):
        seller = await db.get(Agent, txn.seller_agent_id) if txn.seller_agent_id else None
        if seller:
            await rep_svc._bump(seller, REP_SELLER_ACCEPT)
            badge = await rep_svc.award_badge(
                db,
                agent_id=seller.id,
                badge_code="buyer_accepted",
                meta={"transaction_id": str(txn.id), "score": str(score)},
            )
            out["seller_badge"] = badge is not None
        await rep_svc._bump(buyer, REP_BUYER_ACCEPT)
        await rep_svc.award_badge(
            db,
            agent_id=buyer.id,
            badge_code="reviewed_purchase",
            meta={"transaction_id": str(txn.id)},
        )
    elif not accept:
        seller = await db.get(Agent, txn.seller_agent_id) if txn.seller_agent_id else None
        if seller:
            await rep_svc._bump(seller, -REP_DISPUTE_HIT)
        meta = dict(txn.meta or {})
        meta["dispute"] = {
            "opened_by": str(buyer.id),
            "at": txn.reviewed_at.isoformat(),
            "notes": txn.review_notes,
            "score": str(score),
        }
        txn.meta = meta
    await db.commit()
    await db.refresh(txn)
    out["review"] = _txn_dict(txn)
    return out


async def request_refund(
    db: AsyncSession,
    *,
    agent: Agent,
    txn_id: uuid.UUID,
    reason: str,
) -> dict[str, Any]:
    """Mark refund requested. On-chain clawback is admin/treasury (ask before funds)."""
    txn = await db.get(Transaction, txn_id)
    if txn is None:
        raise ValueError("transaction not found")
    if agent.id not in (txn.buyer_agent_id, txn.seller_agent_id):
        raise ValueError("not a party to this transaction")
    if txn.status == TransactionStatus.REFUNDED:
        return {"reused": True, **_txn_dict(txn)}
    if txn.fulfillment_status not in (AWAITING, DELIVERED, DISPUTED, TIMED_OUT, ACCEPTED):
        raise ValueError(f"cannot refund from fulfillment {txn.fulfillment_status}")
    txn.fulfillment_status = REFUND_REQUESTED
    meta = dict(txn.meta or {})
    meta["refund_request"] = {
        "by": str(agent.id),
        "reason": reason[:1000],
        "at": datetime.now(timezone.utc).isoformat(),
        "note": "ledger flag only — treasury must execute USDC return",
    }
    txn.meta = meta
    await db.commit()
    await db.refresh(txn)
    return _txn_dict(txn)


async def admin_mark_refunded(
    db: AsyncSession, *, txn_id: uuid.UUID, note: str | None = None
) -> dict[str, Any]:
    txn = await db.get(Transaction, txn_id)
    if txn is None:
        raise ValueError("transaction not found")
    txn.status = TransactionStatus.REFUNDED
    meta = dict(txn.meta or {})
    meta["refunded"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "note": (note or "")[:500],
    }
    txn.meta = meta
    await db.commit()
    await db.refresh(txn)
    return _txn_dict(txn)


async def expire_overdue(db: AsyncSession, *, limit: int = 100) -> dict[str, Any]:
    """Mark awaiting_delivery past deadline as timed_out; soft reputation hit."""
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(Transaction)
        .where(
            Transaction.fulfillment_status == AWAITING,
            Transaction.delivery_deadline_at.is_not(None),
            Transaction.delivery_deadline_at < now,
        )
        .limit(limit)
    )
    rows = list(res.scalars().all())
    from app.services import reputation as rep_svc

    timed: list[str] = []
    for txn in rows:
        txn.fulfillment_status = TIMED_OUT
        if txn.seller_agent_id:
            seller = await db.get(Agent, txn.seller_agent_id)
            if seller:
                await rep_svc._bump(seller, -REP_DISPUTE_HIT)
        timed.append(str(txn.id))
    await db.commit()
    return {"timed_out": timed, "count": len(timed)}
