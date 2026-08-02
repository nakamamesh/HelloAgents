"""Machine API for agents — /agent/* (API key or JWT)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.orm import Agent
from app.models.schemas import (
    AgentOut,
    ListingOut,
    MachineListingCreate,
    TokenResponse,
)
from app.services import registry
from app.services.auth import create_agent_jwt, get_current_agent

router = APIRouter(prefix="/agent", tags=["machine"])


@router.post("/token", response_model=TokenResponse)
async def exchange_token(agent: Agent = Depends(get_current_agent)) -> TokenResponse:
    """Exchange API key (X-API-Key or Bearer ha_…) for a short-lived JWT."""
    settings = get_settings()
    token = create_agent_jwt(agent.id)
    return TokenResponse(
        access_token=token,
        expires_minutes=settings.jwt_expires_minutes,
        agent_id=agent.id,
        slug=agent.slug,
    )


@router.get("/me", response_model=AgentOut)
async def me(agent: Agent = Depends(get_current_agent)) -> AgentOut:
    return AgentOut.model_validate(agent)


@router.get("/listings", response_model=list[ListingOut])
async def my_listings(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> list[ListingOut]:
    listings = await registry.list_listings(db, agent_id=agent.id)
    return [ListingOut.model_validate(x) for x in listings]


@router.post("/listings", response_model=ListingOut, status_code=201)
async def create_my_listing(
    body: MachineListingCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> ListingOut:
    listing = await registry.create_listing(
        db,
        agent_id=agent.id,
        title=body.title,
        description=body.description,
        price_usdc=body.price_usdc,
        capabilities=body.capabilities,
        meta=body.meta,
    )
    return ListingOut.model_validate(listing)
