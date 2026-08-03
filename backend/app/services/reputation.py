"""Reputation score bumps + badge awards (numeric money-safe Decimals for scores)."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import money
from app.models.orm import Agent, AgentBadge, Transaction

logger = logging.getLogger(__name__)

REP_CAP = Decimal("5.000000")
REP_SELLER_SALE = Decimal("0.050000")
REP_BUYER_PURCHASE = Decimal("0.020000")
REP_REFERRER = Decimal("0.010000")
REP_EVAL_PASS = Decimal("0.030000")


async def _bump(agent: Agent, delta: Decimal) -> Decimal:
    nxt = money(agent.reputation_score + delta)
    if nxt > REP_CAP:
        nxt = REP_CAP
    if nxt < Decimal("0"):
        nxt = Decimal("0")
    agent.reputation_score = nxt
    return nxt


async def award_badge(
    db: AsyncSession,
    *,
    agent_id: uuid.UUID,
    badge_code: str,
    meta: dict[str, Any] | None = None,
) -> AgentBadge | None:
    existing = await db.execute(
        select(AgentBadge).where(
            AgentBadge.agent_id == agent_id,
            AgentBadge.badge_code == badge_code,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None
    row = AgentBadge(agent_id=agent_id, badge_code=badge_code, meta=meta or {})
    db.add(row)
    return row


async def apply_settlement_reputation(
    db: AsyncSession, *, txn: Transaction
) -> dict[str, Any]:
    """Bump seller/buyer/referrer scores and award settlement badges."""
    out: dict[str, Any] = {"bumps": {}, "badges": []}
    seller = await db.get(Agent, txn.seller_agent_id) if txn.seller_agent_id else None
    buyer = await db.get(Agent, txn.buyer_agent_id) if txn.buyer_agent_id else None
    if seller:
        out["bumps"]["seller"] = str(await _bump(seller, REP_SELLER_SALE))
        badge = await award_badge(
            db,
            agent_id=seller.id,
            badge_code="first_sale",
            meta={"transaction_id": str(txn.id)},
        )
        if badge:
            out["badges"].append({"agent_id": str(seller.id), "badge": "first_sale"})
        await award_badge(
            db,
            agent_id=seller.id,
            badge_code="settled_seller",
            meta={"transaction_id": str(txn.id)},
        )
    if buyer:
        out["bumps"]["buyer"] = str(await _bump(buyer, REP_BUYER_PURCHASE))
        badge = await award_badge(
            db,
            agent_id=buyer.id,
            badge_code="first_purchase",
            meta={"transaction_id": str(txn.id)},
        )
        if badge:
            out["badges"].append({"agent_id": str(buyer.id), "badge": "first_purchase"})
    if txn.referrer_agent_id and txn.referral_usdc and txn.referral_usdc > 0:
        referrer = await db.get(Agent, txn.referrer_agent_id)
        if referrer:
            out["bumps"]["referrer"] = str(await _bump(referrer, REP_REFERRER))
            badge = await award_badge(
                db,
                agent_id=referrer.id,
                badge_code="referrer",
                meta={"transaction_id": str(txn.id)},
            )
            if badge:
                out["badges"].append({"agent_id": str(referrer.id), "badge": "referrer"})
    return out


async def apply_eval_pass(
    db: AsyncSession, *, agent: Agent, score: float, task: str
) -> dict[str, Any]:
    bump = str(await _bump(agent, REP_EVAL_PASS))
    badge = await award_badge(
        db,
        agent_id=agent.id,
        badge_code="verified_deliverable",
        meta={"score": score, "task": task[:200]},
    )
    meta = dict(agent.meta or {})
    evolutions = list(meta.get("evolutions") or [])
    evolutions.append(
        {
            "kind": "eval_pass",
            "score": score,
            "task": task[:200],
            "reputation": bump,
        }
    )
    # keep last 20 self-improve events
    meta["evolutions"] = evolutions[-20:]
    meta["last_eval_pass_score"] = score
    agent.meta = meta
    return {
        "reputation": bump,
        "badge_awarded": badge is not None,
        "evolutions": len(meta["evolutions"]),
    }


async def list_badges(db: AsyncSession, *, agent_id: uuid.UUID) -> list[dict[str, Any]]:
    res = await db.execute(
        select(AgentBadge)
        .where(AgentBadge.agent_id == agent_id)
        .order_by(AgentBadge.awarded_at.desc())
    )
    return [
        {
            "badge_code": b.badge_code,
            "awarded_at": b.awarded_at.isoformat() if b.awarded_at else None,
            "meta": b.meta or {},
        }
        for b in res.scalars().all()
    ]
