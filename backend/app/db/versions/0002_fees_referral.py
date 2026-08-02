"""add fee_configs, referral ledger, referral codes

Revision ID: 0002_fees_referral
Revises: 0001_core
Create Date: 2026-08-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_fees_referral"
down_revision: Union[str, None] = "0001_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("referral_code", sa.String(32), nullable=True))
    op.add_column(
        "agents",
        sa.Column("referred_by_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
    )
    op.create_index("ix_agents_referral_code", "agents", ["referral_code"], unique=True)

    op.add_column(
        "transactions",
        sa.Column("referrer_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
    )

    op.create_table(
        "fee_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform_fee_bps", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("referral_bps", sa.Integer(), nullable=False, server_default="250"),
        sa.Column("min_fee_usdc", sa.Numeric(24, 6), nullable=False, server_default="0.010000"),
        sa.Column("referral_cap_usdc", sa.Numeric(24, 6), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "referral_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("referrer_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("referred_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("amount_usdc", sa.Numeric(24, 6), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_referral_ledger_idempotency"),
    )
    op.create_index("ix_referral_ledger_entries_referrer_agent_id", "referral_ledger_entries", ["referrer_agent_id"])

    # seed default fee config
    op.execute(
        sa.text(
            """
            INSERT INTO fee_configs (id, platform_fee_bps, referral_bps, min_fee_usdc, active, notes)
            VALUES (
              gen_random_uuid(),
              1000,
              250,
              0.010000,
              true,
              'Launch: 10% platform fee, 2.5% referral from fee pot'
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_table("referral_ledger_entries")
    op.drop_table("fee_configs")
    op.drop_column("transactions", "referrer_agent_id")
    op.drop_index("ix_agents_referral_code", table_name="agents")
    op.drop_column("agents", "referred_by_agent_id")
    op.drop_column("agents", "referral_code")
