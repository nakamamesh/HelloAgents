from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base, Money


class LedgerStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    VOID = "void"


class FeeConfig(Base):
    """Singleton-ish active fee schedule (latest active row wins)."""

    __tablename__ = "fee_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_fee_bps: Mapped[int] = mapped_column(Integer, default=1000)  # 10%
    referral_bps: Mapped[int] = mapped_column(Integer, default=250)  # 2.5% of gross
    min_fee_usdc: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.010000"))
    referral_cap_usdc: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReferralLedgerEntry(Base):
    __tablename__ = "referral_ledger_entries"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_referral_ledger_idempotency"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), index=True
    )
    referred_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )
    amount_usdc: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[str] = mapped_column(String(32), default=LedgerStatus.PENDING.value)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def mint_referral_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10].lower()
