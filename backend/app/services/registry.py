from __future__ import annotations

import secrets
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Agent, AgentRole, AgentStatus, Listing, ListingStatus
from app.services.auth import hash_api_key


def mint_api_key() -> str:
    return f"ha_live_{secrets.token_urlsafe(32)}"


async def create_agent(
    db: AsyncSession,
    *,
    slug: str,
    name: str,
    role: AgentRole,
    description: str | None = None,
    status: AgentStatus = AgentStatus.ACTIVE,
    referral_budget: Decimal = Decimal("0"),
    reputation_score: Decimal = Decimal("0"),
    meta: dict | None = None,
) -> tuple[Agent, str]:
    existing = await db.execute(select(Agent).where(Agent.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug already exists")

    raw_key = mint_api_key()
    agent = Agent(
        slug=slug,
        name=name,
        role=role,
        description=description,
        status=status,
        referral_budget=referral_budget,
        reputation_score=reputation_score,
        api_key_hash=hash_api_key(raw_key),
        meta=meta or {},
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent, raw_key


async def list_agents(
    db: AsyncSession,
    *,
    role: AgentRole | None = None,
    status_filter: AgentStatus | None = None,
) -> list[Agent]:
    stmt = select(Agent).order_by(Agent.created_at.desc())
    if role is not None:
        stmt = stmt.where(Agent.role == role)
    if status_filter is not None:
        stmt = stmt.where(Agent.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: UUID) -> Agent:
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


async def update_agent(
    db: AsyncSession,
    agent_id: UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    status: AgentStatus | None = None,
    meta: dict | None = None,
) -> Agent:
    agent = await get_agent(db, agent_id)
    if name is not None:
        agent.name = name
    if description is not None:
        agent.description = description
    if status is not None:
        agent.status = status
    if meta is not None:
        agent.meta = meta
    await db.commit()
    await db.refresh(agent)
    return agent


async def rotate_api_key(db: AsyncSession, agent_id: UUID) -> tuple[Agent, str]:
    agent = await get_agent(db, agent_id)
    raw_key = mint_api_key()
    agent.api_key_hash = hash_api_key(raw_key)
    await db.commit()
    await db.refresh(agent)
    return agent, raw_key


async def create_listing(
    db: AsyncSession,
    *,
    agent_id: UUID,
    title: str,
    price_usdc: Decimal,
    description: str | None = None,
    status: ListingStatus = ListingStatus.ACTIVE,
    capabilities: list | None = None,
    meta: dict | None = None,
) -> Listing:
    await get_agent(db, agent_id)
    listing = Listing(
        agent_id=agent_id,
        title=title,
        description=description,
        price_usdc=price_usdc,
        status=status,
        capabilities=capabilities or [],
        meta=meta or {},
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


async def list_listings(
    db: AsyncSession,
    *,
    agent_id: UUID | None = None,
    status_filter: ListingStatus | None = None,
) -> list[Listing]:
    stmt = select(Listing).order_by(Listing.created_at.desc())
    if agent_id is not None:
        stmt = stmt.where(Listing.agent_id == agent_id)
    if status_filter is not None:
        stmt = stmt.where(Listing.status == status_filter)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_listing(db: AsyncSession, listing_id: UUID) -> Listing:
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


async def update_listing(
    db: AsyncSession,
    listing_id: UUID,
    *,
    title: str | None = None,
    description: str | None = None,
    price_usdc: Decimal | None = None,
    status: ListingStatus | None = None,
    capabilities: list | None = None,
    meta: dict | None = None,
) -> Listing:
    listing = await get_listing(db, listing_id)
    if title is not None:
        listing.title = title
    if description is not None:
        listing.description = description
    if price_usdc is not None:
        listing.price_usdc = price_usdc
    if status is not None:
        listing.status = status
    if capabilities is not None:
        listing.capabilities = capabilities
    if meta is not None:
        listing.meta = meta
    await db.commit()
    await db.refresh(listing)
    return listing


async def delete_listing(db: AsyncSession, listing_id: UUID) -> None:
    listing = await get_listing(db, listing_id)
    listing.status = ListingStatus.ARCHIVED
    await db.commit()
