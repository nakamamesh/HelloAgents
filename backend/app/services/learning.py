"""Platform-level learning from completed settlements — ranking + template hints.

No LLM. No automatic fee changes (fees stay human-locked).
Inspired by agency-agents outcome metrics + search-relevance thinking.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Agent, AgentStatus, Listing, ListingStatus, Transaction, TransactionStatus

logger = logging.getLogger(__name__)


async def record_settlement_outcome(db: AsyncSession, *, txn: Transaction) -> dict[str, Any]:
    """Persist lightweight outcome counters on listing + seller meta (idempotent)."""
    out: dict[str, Any] = {}
    if txn.status != TransactionStatus.COMPLETED:
        return {"skipped": True, "reason": "not_completed"}
    prior = (txn.meta or {}).get("learning") or {}
    if prior.get("recorded"):
        return {"skipped": True, "reason": "already_recorded", **prior}

    listing = await db.get(Listing, txn.listing_id) if txn.listing_id else None
    seller = await db.get(Agent, txn.seller_agent_id) if txn.seller_agent_id else None

    if listing is not None:
        meta = dict(listing.meta or {})
        sales = int(meta.get("completed_sales") or 0) + 1
        gmv = Decimal(str(meta.get("completed_gmv_usdc") or "0")) + Decimal(str(txn.gross_usdc))
        meta["completed_sales"] = sales
        meta["completed_gmv_usdc"] = str(gmv)
        listing.meta = meta
        out["listing_id"] = str(listing.id)
        out["listing_sales"] = sales

    if seller is not None:
        meta = dict(seller.meta or {})
        plat = dict(meta.get("platform_stats") or {})
        plat["completed_sales"] = int(plat.get("completed_sales") or 0) + 1
        plat["completed_gmv_usdc"] = str(
            Decimal(str(plat.get("completed_gmv_usdc") or "0")) + Decimal(str(txn.gross_usdc))
        )
        meta["platform_stats"] = plat
        seller.meta = meta
        out["seller_slug"] = seller.slug

    out["recorded"] = True
    return out


async def catalog_rank_scores(db: AsyncSession) -> dict[str, float]:
    """listing_id -> score from completed sales, GMV, and seller reputation."""
    result = await db.execute(
        select(Listing, Agent)
        .join(Agent, Listing.agent_id == Agent.id)
        .where(Listing.status == ListingStatus.ACTIVE, Agent.status == AgentStatus.ACTIVE)
    )
    scores: dict[str, float] = {}
    for listing, agent in result.all():
        meta = listing.meta or {}
        sales = float(meta.get("completed_sales") or 0)
        gmv = float(meta.get("completed_gmv_usdc") or 0)
        rep = float(agent.reputation_score or 0)
        scores[str(listing.id)] = sales * 10.0 + gmv + rep
    return scores


async def backfill_outcomes(db: AsyncSession) -> dict[str, Any]:
    """One-shot: derive listing/seller stats from completed txs (idempotent overwrite)."""
    from collections import defaultdict

    txns = await db.execute(
        select(Transaction).where(Transaction.status == TransactionStatus.COMPLETED)
    )
    completed = list(txns.scalars().all())
    listing_stats: dict[Any, dict[str, Decimal | int]] = defaultdict(
        lambda: {"sales": 0, "gmv": Decimal("0")}
    )
    seller_stats: dict[Any, dict[str, Decimal | int]] = defaultdict(
        lambda: {"sales": 0, "gmv": Decimal("0")}
    )
    for txn in completed:
        if txn.listing_id:
            listing_stats[txn.listing_id]["sales"] = int(listing_stats[txn.listing_id]["sales"]) + 1
            listing_stats[txn.listing_id]["gmv"] = Decimal(
                str(listing_stats[txn.listing_id]["gmv"])
            ) + Decimal(str(txn.gross_usdc))
        if txn.seller_agent_id:
            seller_stats[txn.seller_agent_id]["sales"] = int(seller_stats[txn.seller_agent_id]["sales"]) + 1
            seller_stats[txn.seller_agent_id]["gmv"] = Decimal(
                str(seller_stats[txn.seller_agent_id]["gmv"])
            ) + Decimal(str(txn.gross_usdc))

    for lid, st in listing_stats.items():
        listing = await db.get(Listing, lid)
        if listing is None:
            continue
        meta = dict(listing.meta or {})
        meta["completed_sales"] = int(st["sales"])
        meta["completed_gmv_usdc"] = str(st["gmv"])
        listing.meta = meta
    for sid, st in seller_stats.items():
        agent = await db.get(Agent, sid)
        if agent is None:
            continue
        meta = dict(agent.meta or {})
        plat = dict(meta.get("platform_stats") or {})
        plat["completed_sales"] = int(st["sales"])
        plat["completed_gmv_usdc"] = str(st["gmv"])
        meta["platform_stats"] = plat
        agent.meta = meta
    await db.commit()
    return {
        "ok": True,
        "transactions": len(completed),
        "listings_updated": len(listing_stats),
        "sellers_updated": len(seller_stats),
    }
    """Aggregate outcome stats for matching/templates (read-only recommendations)."""
    txns = await db.execute(
        select(Transaction).where(Transaction.status == TransactionStatus.COMPLETED)
    )
    completed = list(txns.scalars().all())
    by_capability: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sales": 0.0, "gmv": 0.0}
    )
    total_gmv = Decimal("0")
    for txn in completed:
        total_gmv += Decimal(str(txn.gross_usdc))
        listing = await db.get(Listing, txn.listing_id) if txn.listing_id else None
        caps = (listing.capabilities if listing else None) or []
        for cap in caps[:8]:
            key = str(cap)
            by_capability[key]["sales"] += 1
            by_capability[key]["gmv"] += float(txn.gross_usdc)

    top_caps = sorted(
        (
            {"capability": k, "sales": int(v["sales"]), "gmv": round(v["gmv"], 6)}
            for k, v in by_capability.items()
        ),
        key=lambda x: (x["sales"], x["gmv"]),
        reverse=True,
    )[:15]

    listings = await db.execute(
        select(Listing, Agent)
        .join(Agent, Listing.agent_id == Agent.id)
        .where(Listing.status == ListingStatus.ACTIVE, Agent.status == AgentStatus.ACTIVE)
    )
    template_hints = []
    for listing, agent in listings.all():
        sales = int((listing.meta or {}).get("completed_sales") or 0)
        if sales > 0:
            template_hints.append(
                {
                    "title_pattern": listing.title,
                    "price_usdc": str(listing.price_usdc),
                    "capabilities": listing.capabilities[:6],
                    "completed_sales": sales,
                    "seller_slug": agent.slug,
                }
            )
    template_hints.sort(key=lambda x: x["completed_sales"], reverse=True)

    return {
        "completed_transactions": len(completed),
        "total_gmv_usdc": str(total_gmv),
        "top_capabilities": top_caps,
        "listing_templates": template_hints[:20],
        "fee_note": (
            "Fees remain locked (10% / 2.5% referral). "
            "Insights are ranking/template hints only — no auto fee mutation."
        ),
        "agency_inspired": [
            "Outcome metrics → rank catalog by completed sales",
            "Template learning from winning listing titles/prices",
            "Zero-LLM recruit templates; optional LLM polish",
        ],
    }
