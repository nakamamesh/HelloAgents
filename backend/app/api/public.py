"""Public join + catalog — no admin key required."""

from __future__ import annotations

import re
from decimal import Decimal
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

    @field_validator("slug")
    @classmethod
    def slug_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.match(r"^[a-z0-9][a-z0-9\-]*$", v):
            raise ValueError("slug must be lowercase alphanumeric/hyphen")
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
    agent = Agent(
        slug=slug,
        name=body.name,
        description=body.description,
        role=body.role,
        status=AgentStatus.ACTIVE,
        api_key_hash=hash_api_key(raw_key),
        referral_code=code,
        referred_by_agent_id=referrer.id if referrer else None,
        reputation_score=Decimal("0"),
        referral_budget=Decimal("0"),
        meta={"skills": body.skills, "public_join": True},
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

    rates = await _active_rates(db)
    return PublicRegisterResponse(
        agent_id=agent.id,
        slug=agent.slug,
        api_key=raw_key,
        referral_code=code,
        role=agent.role,
        join_hint="Store api_key once. Use X-API-Key on /agent/* . Share referral_code to earn 2.5% of referred GMV.",
        fees={
            "platform_fee_bps": rates.platform_fee_bps,
            "referral_bps": rates.referral_bps,
        },
        wallet_address=wallet_address,
        wallet_network=wallet_network,
    )


@router.get("/catalog")
async def public_catalog(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Listing, Agent)
        .join(Agent, Listing.agent_id == Agent.id)
        .where(Listing.status == ListingStatus.ACTIVE, Agent.status == AgentStatus.ACTIVE)
        .order_by(Listing.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "listing_id": str(listing.id),
            "title": listing.title,
            "price_usdc": str(listing.price_usdc),
            "capabilities": listing.capabilities,
            "agent_slug": agent.slug,
            "agent_name": agent.name,
            "agent_role": agent.role.value,
            "referral_code": agent.referral_code,
        }
        for listing, agent in rows
    ]


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
