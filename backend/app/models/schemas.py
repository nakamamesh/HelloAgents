from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str


class OpenRouterSmokeResponse(BaseModel):
    model: str
    reply: str


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    role: str
    status: str
    reputation_score: Decimal
    referral_budget: Decimal
    created_at: datetime


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    title: str
    description: str | None
    price_usdc: Decimal = Field(..., description="USDC amount as Decimal / numeric(24,6)")
    status: str
    created_at: datetime
