"""Public join + catalog — no admin key required."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config import get_settings
from app.models.orm import Agent, AgentRole, AgentStatus, Listing, ListingStatus
from app.models.fees import mint_referral_code
from app.services.auth import hash_api_key
from app.services.fees import DEFAULT_RATES, FeeRates, compute_split
from app.services.registry import mint_api_key
from app.services import wallets as wallet_svc
from app.models.fees import FeeConfig

router = APIRouter(prefix="/public", tags=["public"])


class PublicRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=256)
    role: AgentRole = AgentRole.SELLER
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    referral_code: str | None = Field(default=None, max_length=32)
    slug: str | None = Field(default=None, max_length=128)
    # Agency persona path e.g. "specialized/recruitment-specialist.md"
    persona_source: str | None = Field(default=None, max_length=512)

    @field_validator("slug")
    @classmethod
    def slug_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.match(r"^[a-z0-9][a-z0-9\-]*$", v):
            raise ValueError("slug must be lowercase alphanumeric/hyphen")
        return v

    @field_validator("persona_source")
    @classmethod
    def persona_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lstrip("/")
        if ".." in v or not v.endswith(".md"):
            raise ValueError("persona_source must be a .md path under snapshot/")
        return v


class PublicRegisterResponse(BaseModel):
    agent_id: UUID
    slug: str
    api_key: str
    referral_code: str
    role: AgentRole
    join_hint: str
    fees: dict
    wallet_address: str | None = None
    wallet_network: str | None = None
    recruit_pitch: dict | None = None


class FeePreviewRequest(BaseModel):
    gross_usdc: Decimal = Field(..., max_digits=24, decimal_places=6)
    has_referrer: bool = True

    @field_validator("gross_usdc", mode="before")
    @classmethod
    def no_float(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("use string Decimal, not float")
        return v


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:100] or "agent"


async def _active_rates(db: AsyncSession) -> FeeRates:
    result = await db.execute(
        select(FeeConfig).where(FeeConfig.active.is_(True)).order_by(FeeConfig.created_at.desc())
    )
    row = result.scalars().first()
    if row is None:
        return DEFAULT_RATES
    return FeeRates(platform_fee_bps=row.platform_fee_bps, referral_bps=row.referral_bps)


@router.get("/fees")
async def public_fees(db: AsyncSession = Depends(get_db)) -> dict:
    rates = await _active_rates(db)
    example = compute_split("10.000000", has_referrer=True, rates=rates)
    return {
        "platform_fee_bps": rates.platform_fee_bps,
        "referral_bps": rates.referral_bps,
        "platform_fee_pct": rates.platform_fee_bps / 100,
        "referral_pct": rates.referral_bps / 100,
        "example_10_usdc": {
            "gross": str(example.gross_usdc),
            "seller_net": str(example.seller_net_usdc),
            "platform_fee": str(example.platform_fee_usdc),
            "referral": str(example.referral_usdc),
            "platform_keep": str(example.platform_keep_usdc),
        },
    }


@router.post("/fees/preview")
async def preview_fees(body: FeePreviewRequest, db: AsyncSession = Depends(get_db)) -> dict:
    rates = await _active_rates(db)
    split = compute_split(body.gross_usdc, has_referrer=body.has_referrer, rates=rates)
    return {
        "gross_usdc": str(split.gross_usdc),
        "platform_fee_usdc": str(split.platform_fee_usdc),
        "referral_usdc": str(split.referral_usdc),
        "platform_keep_usdc": str(split.platform_keep_usdc),
        "seller_net_usdc": str(split.seller_net_usdc),
        "has_referrer": split.has_referrer,
    }


@router.post("/register", response_model=PublicRegisterResponse, status_code=201)
async def public_register(
    body: PublicRegisterRequest, db: AsyncSession = Depends(get_db)
) -> PublicRegisterResponse:
    slug = body.slug or _slugify(body.name)
    existing = await db.execute(select(Agent).where(Agent.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{mint_referral_code()[:4]}"

    referrer: Agent | None = None
    if body.referral_code:
        code = body.referral_code.strip().lower()
        res = await db.execute(select(Agent).where(Agent.referral_code == code))
        referrer = res.scalar_one_or_none()
        if referrer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown referral_code")

    # unique referral code for new agent
    code = mint_referral_code()
    while True:
        clash = await db.execute(select(Agent).where(Agent.referral_code == code))
        if clash.scalar_one_or_none() is None:
            break
        code = mint_referral_code()

    raw_key = mint_api_key()
    persona_version_id = None
    if body.persona_source:
        from app.models.orm import PersonaVersion

        res = await db.execute(
            select(PersonaVersion)
            .where(PersonaVersion.source_path == body.persona_source)
            .order_by(PersonaVersion.created_at.desc())
            .limit(1)
        )
        persona = res.scalar_one_or_none()
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unknown persona_source — GET /public/personas",
            )
        persona_version_id = persona.id
        if not body.description:
            body.description = persona.description or persona.mission

    agent = Agent(
        slug=slug,
        name=body.name,
        description=body.description,
        role=body.role,
        status=AgentStatus.ACTIVE,
        api_key_hash=hash_api_key(raw_key),
        referral_code=code,
        referred_by_agent_id=referrer.id if referrer else None,
        persona_version_id=persona_version_id,
        reputation_score=Decimal("0"),
        referral_budget=Decimal("0"),
        meta={
            "skills": body.skills,
            "public_join": True,
            "persona_source": body.persona_source,
        },
    )
    db.add(agent)
    await db.flush()

    wallet_address: str | None = None
    wallet_network: str | None = None
    try:
        provisioned = await wallet_svc.provision_evm_account(agent.slug)
        if provisioned:
            agent.wallet_id = provisioned.wallet_id
            agent.wallet_address = provisioned.address
            agent.meta = {
                **(agent.meta or {}),
                "wallet_network": provisioned.network,
            }
            wallet_address = provisioned.address
            wallet_network = provisioned.network
    except Exception as exc:  # noqa: BLE001
        if get_settings().wallet_required:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"wallet provision failed: {exc}",
            ) from exc

    await db.commit()
    await db.refresh(agent)

    # Auto-enlist as recruiter — every joiner publishes a pitch
    pitch_summary: dict | None = None
    try:
        from app.services import recruit as recruit_svc

        pitch_summary = await recruit_svc.publish_pitch(db, agent=agent, broadcast=True)
        await db.commit()
        pitch_summary = {
            "id": pitch_summary["id"],
            "referral_code": pitch_summary["referral_code"],
            "pitch_preview": pitch_summary["pitch"][:240],
        }
    except Exception:  # noqa: BLE001
        pitch_summary = None

    rates = await _active_rates(db)
    return PublicRegisterResponse(
        agent_id=agent.id,
        slug=agent.slug,
        api_key=raw_key,
        referral_code=code,
        role=agent.role,
        join_hint=(
            "Store api_key once. Use X-API-Key on /agent/* . "
            "Share referral_code / POST /agent/recruit to earn 2.5% of referred GMV."
        ),
        fees={
            "platform_fee_bps": rates.platform_fee_bps,
            "referral_bps": rates.referral_bps,
        },
        wallet_address=wallet_address,
        wallet_network=wallet_network,
        recruit_pitch=pitch_summary,
    )


@router.get("/catalog")
async def public_catalog(
    limit: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, max_length=200),
    capability: str | None = Query(default=None, max_length=120),
    min_sales: int = Query(default=0, ge=0, le=1_000_000),
    agent_slug: str | None = Query(default=None, max_length=128),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    from app.services import learning as learn_svc

    result = await db.execute(
        select(Listing, Agent)
        .join(Agent, Listing.agent_id == Agent.id)
        .where(Listing.status == ListingStatus.ACTIVE, Agent.status == AgentStatus.ACTIVE)
    )
    rows = list(result.all())
    scores = await learn_svc.catalog_rank_scores(db)

    q_l = (q or "").strip().lower()
    cap_l = (capability or "").strip().lower()
    slug_l = (agent_slug or "").strip().lower()

    filtered: list[tuple[Listing, Agent]] = []
    for listing, agent in rows:
        sales = int((listing.meta or {}).get("completed_sales") or 0)
        if sales < min_sales:
            continue
        if slug_l and agent.slug.lower() != slug_l:
            continue
        caps = [str(c) for c in (listing.capabilities or [])]
        if cap_l and not any(cap_l in c.lower() for c in caps):
            continue
        if q_l:
            hay = " ".join(
                [
                    listing.title or "",
                    listing.description or "",
                    agent.name or "",
                    agent.slug or "",
                    " ".join(caps),
                ]
            ).lower()
            if q_l not in hay:
                continue
        filtered.append((listing, agent))

    filtered.sort(
        key=lambda pair: (
            scores.get(str(pair[0].id), 0.0),
            pair[0].created_at.timestamp() if pair[0].created_at else 0,
        ),
        reverse=True,
    )
    filtered = filtered[:limit]
    return [
        {
            "listing_id": str(listing.id),
            "title": listing.title,
            "description": (listing.description or "")[:280],
            "price_usdc": str(listing.price_usdc),
            "capabilities": listing.capabilities,
            "agent_slug": agent.slug,
            "agent_name": agent.name,
            "agent_role": agent.role.value,
            "referral_code": agent.referral_code,
            "rank_score": scores.get(str(listing.id), 0.0),
            "completed_sales": int((listing.meta or {}).get("completed_sales") or 0),
            "reputation_score": str(agent.reputation_score),
        }
        for listing, agent in filtered
    ]


@router.post("/match")
async def public_match(
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Rank sellers for a free-text need (capability overlap + outcomes)."""
    need = str(body.get("need") or body.get("query") or "").strip()
    limit = min(int(body.get("limit") or 10), 50)
    if len(need) < 2:
        raise HTTPException(status_code=400, detail="need required")
    tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9\-]{3,}", need)}
    catalog = await public_catalog(limit=200, q=None, capability=None, min_sales=0, agent_slug=None, db=db)
    scored: list[dict] = []
    for item in catalog:
        caps = [str(c).lower() for c in (item.get("capabilities") or [])]
        title = (item.get("title") or "").lower()
        overlap = sum(1 for t in tokens if t in title or any(t in c for c in caps))
        rank = float(item.get("rank_score") or 0)
        score = overlap * 20 + rank
        scored.append({**item, "match_score": score, "token_overlap": overlap})
    scored.sort(key=lambda x: (x["match_score"], x.get("rank_score") or 0), reverse=True)
    return {"need": need, "matches": scored[:limit]}


@router.get("/insights")
async def public_insights(db: AsyncSession = Depends(get_db)) -> dict:
    """Platform learning snapshot — ranking/template hints (fees locked)."""
    from app.services import learning as learn_svc

    return await learn_svc.platform_insights(db)


@router.get("/personas")
async def public_personas(
    limit: int = Query(default=100, ge=1, le=300),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Browse Agency persona templates available for join (persona_source on register)."""
    from app.models.orm import PersonaVersion

    result = await db.execute(
        select(PersonaVersion).order_by(PersonaVersion.division.asc(), PersonaVersion.name.asc()).limit(limit)
    )
    # de-dupe by source_path keeping latest
    latest: dict[str, Any] = {}
    for p in result.scalars().all():
        prev = latest.get(p.source_path)
        if prev is None or (p.created_at and prev["created_at"] and p.created_at > prev["_dt"]):
            latest[p.source_path] = {
                "source_path": p.source_path,
                "name": p.name,
                "division": p.division,
                "description": (p.description or "")[:240],
                "sellable_capabilities": (p.sellable_capabilities or [])[:8],
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "_dt": p.created_at,
            }
    personas = [{k: v for k, v in row.items() if k != "_dt"} for row in latest.values()]
    return {
        "count": len(personas),
        "personas": personas,
        "join_hint": 'POST /public/register with {"name":"...","persona_source":"<source_path>","referral_code":"..."}',
        "upstream": "msitarzewski/agency-agents (MIT)",
    }


@router.get("/recruit/pitches")
async def public_recruit_pitches(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public feed of recruiter pitches (for agents browsing join offers)."""
    from app.models.recruit import RecruitPitch

    result = await db.execute(
        select(RecruitPitch).order_by(RecruitPitch.created_at.desc()).limit(limit)
    )
    rows = list(result.scalars().all())
    return {
        "pitches": [
            {
                "id": str(r.id),
                "recruiter_slug": r.recruiter_slug,
                "referral_code": r.referral_code,
                "pitch": r.pitch,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "join_hint": f"POST /public/register with referral_code={r.referral_code}",
            }
            for r in rows
        ]
    }


@router.get("/recruit/leaderboard")
async def public_recruit_leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Top recruiters by referral USDC earned."""
    from app.services import recruit as recruit_svc

    return await recruit_svc.leaderboard(db, limit=limit)


@router.get("/agents/{slug}/card")
async def public_agent_card(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Agent).where(Agent.slug == slug))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    card = {
        "name": agent.name,
        "slug": agent.slug,
        "description": agent.description,
        "role": agent.role.value,
        "referral_code": agent.referral_code,
        "reputation_score": str(agent.reputation_score),
        "skills": (agent.meta or {}).get("skills", []),
        "join_url_hint": f"/public/register with referral_code={agent.referral_code}",
        "protocol": "helloagents-v0",
    }
    if agent.persona_version_id:
        from app.models.orm import PersonaVersion

        persona = await db.get(PersonaVersion, agent.persona_version_id)
        if persona:
            card["agent_card"] = persona.agent_card
            card["sellable_capabilities"] = persona.sellable_capabilities
    from app.services import reputation as rep_svc

    card["badges"] = await rep_svc.list_badges(db, agent_id=agent.id)
    return card
