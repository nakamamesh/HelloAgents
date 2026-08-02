"""core tables: personas, agents, listings, transactions

Revision ID: 0001_core
Revises:
Create Date: 2026-08-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_core"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "persona_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("emoji", sa.String(32), nullable=True),
        sa.Column("vibe", sa.String(256), nullable=True),
        sa.Column("division", sa.String(128), nullable=True),
        sa.Column("identity", sa.Text(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("workflow", sa.Text(), nullable=True),
        sa.Column("deliverables", sa.Text(), nullable=True),
        sa.Column("success_metrics", sa.Text(), nullable=True),
        sa.Column("sellable_capabilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("catalog_products", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("agent_card", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_path", sa.String(512), nullable=False),
        sa.Column("upstream_commit", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source_path", "upstream_commit", name="uq_persona_source_commit"),
    )
    op.create_index("ix_persona_versions_division", "persona_versions", ["division"])

    op.create_table(
        "upstream_sync_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("upstream_commit", sa.String(64), nullable=False),
        sa.Column("personas_changed", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "local_override_conflicts",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_upstream_sync_audits_upstream_commit", "upstream_sync_audits", ["upstream_commit"])

    agent_role = postgresql.ENUM(
        "seller", "publisher", "buyer", name="agent_role", create_type=False
    )
    agent_status = postgresql.ENUM(
        "active", "suspended", "draft", name="agent_status", create_type=False
    )
    listing_status = postgresql.ENUM(
        "active", "paused", "archived", name="listing_status", create_type=False
    )
    transaction_status = postgresql.ENUM(
        "pending", "completed", "failed", "refunded", name="transaction_status", create_type=False
    )
    agent_role.create(op.get_bind(), checkfirst=True)
    agent_status.create(op.get_bind(), checkfirst=True)
    listing_status.create(op.get_bind(), checkfirst=True)
    transaction_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("role", agent_role, nullable=False),
        sa.Column("status", agent_status, nullable=False, server_default="draft"),
        sa.Column("persona_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persona_versions.id"), nullable=True),
        sa.Column("api_key_hash", sa.String(128), nullable=True),
        sa.Column("reputation_score", sa.Numeric(24, 6), nullable=False, server_default="0"),
        sa.Column("referral_budget", sa.Numeric(24, 6), nullable=False, server_default="0"),
        sa.Column("wallet_id", sa.String(128), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_agents_slug", "agents", ["slug"])
    op.create_index("ix_agents_role", "agents", ["role"])

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_usdc", sa.Numeric(24, 6), nullable=False),
        sa.Column("status", listing_status, nullable=False, server_default="active"),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_listings_agent_id", "listings", ["agent_id"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id"), nullable=True),
        sa.Column("buyer_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("seller_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("gross_usdc", sa.Numeric(24, 6), nullable=False),
        sa.Column("platform_fee_usdc", sa.Numeric(24, 6), nullable=False, server_default="0"),
        sa.Column("referral_usdc", sa.Numeric(24, 6), nullable=False, server_default="0"),
        sa.Column("seller_net_usdc", sa.Numeric(24, 6), nullable=False, server_default="0"),
        sa.Column("status", transaction_status, nullable=False, server_default="pending"),
        sa.Column("checkout_id", sa.String(128), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_transactions_idempotency_key", "transactions", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("listings")
    op.drop_table("agents")
    op.drop_table("upstream_sync_audits")
    op.drop_table("persona_versions")
    sa.Enum(name="transaction_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="listing_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="agent_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="agent_role").drop(op.get_bind(), checkfirst=True)
