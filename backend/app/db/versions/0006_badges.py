"""agent_badges + reputation plumbing

Revision ID: 0006_badges
Revises: 0005_settled_pending_payout
Create Date: 2026-08-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_badges"
down_revision: Union[str, None] = "0005_settled_pending_payout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id"),
            nullable=False,
        ),
        sa.Column("badge_code", sa.String(length=64), nullable=False),
        sa.Column(
            "meta",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("agent_id", "badge_code", name="uq_agent_badge_code"),
    )
    op.create_index("ix_agent_badges_agent_id", "agent_badges", ["agent_id"])
    op.create_index("ix_agent_badges_badge_code", "agent_badges", ["badge_code"])


def downgrade() -> None:
    op.drop_index("ix_agent_badges_badge_code", table_name="agent_badges")
    op.drop_index("ix_agent_badges_agent_id", table_name="agent_badges")
    op.drop_table("agent_badges")
