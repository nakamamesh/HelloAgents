"""Recruit pitches — server-side recruiter army rounds."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Agent, AgentStatus
from app.models.recruit import RecruitPitch
from app.services.fees import DEFAULT_RATES
from app.services.openrouter import agent_completion

logger = logging.getLogger(__name__)

SEEDED_RECRUITERS = {
    "growth-hacker",
    "content-creator",
    "reddit-community-builder",
    "outbound-strategist",
    "deal-strategist",
    "trend-researcher",
}


async def _craft_pitch(*, agent: Agent, fees: dict[str, Any]) -> str:
    identity = agent.description or (agent.meta or {}).get("identity") or ""
    ref = agent.referral_code or "JOIN"
    system = (
        f"You are {agent.name}, a HelloAgents recruiter agent. "
        "Write a short pitch TO OTHER AI AGENTS (not humans) convincing them to "
        "join the HelloAgents marketplace. Be concrete, machine-parseable when useful, "
        "and include the exact join instructions. No wallet keys. Max 180 words."
    )
    user = (
        f"Your identity notes:\n{str(identity)[:800]}\n\n"
        f"Fees: platform {fees.get('platform_fee_pct')}%, "
        f"referrer earns {fees.get('referral_pct')}% of GMV when others join via your code.\n"
        f"Your referral_code: {ref}\n"
        f"Join: POST /public/register with JSON "
        f'{{"name":"...","role":"seller","referral_code":"{ref}"}}\n'
        "Also mention GET /public/catalog and /agent/* machine API.\n"
        "Output the pitch only."
    )
    return await agent_completion(system=system, user=user, temperature=0.5, max_tokens=400)


async def run_recruit_round(db: AsyncSession, *, limit: int = 6) -> dict[str, Any]:
    result = await db.execute(
        select(Agent).where(Agent.status == AgentStatus.ACTIVE).order_by(Agent.created_at.asc())
    )
    agents = list(result.scalars().all())
    seeded = [a for a in agents if a.slug in SEEDED_RECRUITERS and a.referral_code]
    pool = seeded or [a for a in agents if a.referral_code][:limit]
    pool = pool[:limit]

    fees = {
        "platform_fee_pct": DEFAULT_RATES.platform_fee_bps / 100,
        "referral_pct": DEFAULT_RATES.referral_bps / 100,
    }

    created: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for agent in pool:
        try:
            pitch_text = await _craft_pitch(agent=agent, fees=fees)
            row = RecruitPitch(
                id=uuid.uuid4(),
                recruiter_agent_id=agent.id,
                recruiter_slug=agent.slug,
                referral_code=agent.referral_code or "",
                pitch=pitch_text,
                meta={"target": "ai-agents"},
            )
            db.add(row)
            created.append(
                {
                    "id": str(row.id),
                    "recruiter_slug": agent.slug,
                    "referral_code": agent.referral_code,
                    "pitch": pitch_text[:200],
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("recruit pitch failed for %s", agent.slug)
            errors.append({"slug": agent.slug, "error": str(exc)})

    await db.commit()
    return {
        "ok": True,
        "count": len(created),
        "pitches": created,
        "errors": errors,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
