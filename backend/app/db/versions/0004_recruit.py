"""recruit_pitches table

Revision ID: 0004_recruit
Revises: 0003_wallets
Create Date: 2026-08-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_recruit"
down_revision: Union[str, None] = "0003_wallets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recruit_pitches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recruiter_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("recruiter_slug", sa.String(length=80), nullable=False),
        sa.Column("referral_code", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("pitch", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_recruit_pitches_recruiter_agent_id", "recruit_pitches", ["recruiter_agent_id"])
    op.create_index("ix_recruit_pitches_recruiter_slug", "recruit_pitches", ["recruiter_slug"])


def downgrade() -> None:
    op.drop_index("ix_recruit_pitches_recruiter_slug", table_name="recruit_pitches")
    op.drop_index("ix_recruit_pitches_recruiter_agent_id", table_name="recruit_pitches")
    op.drop_table("recruit_pitches")
