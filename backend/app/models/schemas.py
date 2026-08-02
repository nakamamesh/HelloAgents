from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.orm import AgentRole, AgentStatus, ListingStatus


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str


class OpenRouterSmokeResponse(BaseModel):
    model: str
    reply: str


class AgentCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=128, pattern=r"^[a-z0-9][a-z0-9\-]*$")
    name: str = Field(..., min_length=1, max_length=256)
    role: AgentRole
    description: str | None = None
    status: AgentStatus = AgentStatus.ACTIVE
    referral_budget: Decimal = Field(default=Decimal("0"), max_digits=24, decimal_places=6)
    reputation_score: Decimal = Field(default=Decimal("0"), max_digits=24, decimal_places=6)
    meta: dict = Field(default_factory=dict)

    @field_validator("referral_budget", "reputation_score", mode="before")
    @classmethod
    def no_float(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("money fields must be string or Decimal, not float")
        return v


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    status: AgentStatus | None = None
    meta: dict | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    description: str | None
    role: AgentRole
    status: AgentStatus
    reputation_score: Decimal
    referral_budget: Decimal
    created_at: datetime
    updated_at: datetime


class AgentCreated(AgentOut):
    api_key: str = Field(..., description="Shown once — store securely")


class ListingCreate(BaseModel):
    agent_id: UUID
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    price_usdc: Decimal = Field(..., max_digits=24, decimal_places=6)
    status: ListingStatus = ListingStatus.ACTIVE
    capabilities: list = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)

    @field_validator("price_usdc", mode="before")
    @classmethod
    def no_float_price(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("price_usdc must be string or Decimal, not float")
        return v


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    price_usdc: Decimal | None = Field(default=None, max_digits=24, decimal_places=6)
    status: ListingStatus | None = None
    capabilities: list | None = None
    meta: dict | None = None

    @field_validator("price_usdc", mode="before")
    @classmethod
    def no_float_price(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("price_usdc must be string or Decimal, not float")
        return v


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    title: str
    description: str | None
    price_usdc: Decimal
    status: ListingStatus
    capabilities: list
    created_at: datetime
    updated_at: datetime


class MachineListingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    price_usdc: Decimal = Field(..., max_digits=24, decimal_places=6)
    capabilities: list = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)

    @field_validator("price_usdc", mode="before")
    @classmethod
    def no_float_price(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("price_usdc must be string or Decimal, not float")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_minutes: int
    agent_id: UUID
    slug: str
