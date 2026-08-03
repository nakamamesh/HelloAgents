from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base, Money


def _pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda members: [m.value for m in members],
    )


class AgentRole(str, enum.Enum):
    SELLER = "seller"
    PUBLISHER = "publisher"
    BUYER = "buyer"


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DRAFT = "draft"


class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    SETTLED_PENDING_PAYOUT = "settled_pending_payout"


class PersonaVersion(Base):
    __tablename__ = "persona_versions"
    __table_args__ = (
        UniqueConstraint("source_path", "upstream_commit", name="uq_persona_source_commit"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    emoji: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vibe: Mapped[str | None] = mapped_column(String(256), nullable=True)
    division: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    identity: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow: Mapped[str | None] = mapped_column(Text, nullable=True)
    deliverables: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    sellable_capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    catalog_products: Mapped[list] = mapped_column(JSONB, default=list)
    agent_card: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_path: Mapped[str] = mapped_column(String(512))
    upstream_commit: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UpstreamSyncAudit(Base):
    __tablename__ = "upstream_sync_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upstream_commit: Mapped[str] = mapped_column(String(64), index=True)
    personas_changed: Mapped[list] = mapped_column(JSONB, default=list)
    local_override_conflicts: Mapped[list] = mapped_column(JSONB, default=list)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[AgentRole] = mapped_column(_pg_enum(AgentRole, "agent_role"), index=True)
    status: Mapped[AgentStatus] = mapped_column(
        _pg_enum(AgentStatus, "agent_status"), default=AgentStatus.DRAFT
    )
    persona_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_versions.id"), nullable=True
    )
    api_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reputation_score: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    referral_budget: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    referral_code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    referred_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    # wallet_id = Turnkey wallet id; wallet_address = 0x…
    wallet_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listings: Mapped[list[Listing]] = relationship(back_populates="agent")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_usdc: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[ListingStatus] = mapped_column(
        _pg_enum(ListingStatus, "listing_status"), default=ListingStatus.ACTIVE
    )
    capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped[Agent] = relationship(back_populates="listings")


class Transaction(Base):
    """Single source of truth for fee + referral splits at settlement."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True
    )
    buyer_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    seller_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    gross_usdc: Mapped[Decimal] = mapped_column(Money)
    platform_fee_usdc: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    referral_usdc: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    seller_net_usdc: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    referrer_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    status: Mapped[TransactionStatus] = mapped_column(
        _pg_enum(TransactionStatus, "transaction_status"),
        default=TransactionStatus.PENDING,
    )
    checkout_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentBadge(Base):
    """Simple digital badges awarded from settlements / eval gate."""

    __tablename__ = "agent_badges"
    __table_args__ = (
        UniqueConstraint("agent_id", "badge_code", name="uq_agent_badge_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), index=True
    )
    badge_code: Mapped[str] = mapped_column(String(64), index=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
