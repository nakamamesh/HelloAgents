"""Fulfillment + review columns on transactions

Revision ID: 0007_fulfillment
Revises: 0006_badges
Create Date: 2026-08-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_fulfillment"
down_revision: Union[str, None] = "0006_badges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "fulfillment_status",
            sa.String(length=32),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("artifact_uri", sa.Text(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("artifact_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("delivery_deadline_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("review_score", sa.Numeric(precision=5, scale=4), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("review_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_transactions_fulfillment_status",
        "transactions",
        ["fulfillment_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_fulfillment_status", table_name="transactions")
    op.drop_column("transactions", "reviewed_at")
    op.drop_column("transactions", "review_notes")
    op.drop_column("transactions", "review_score")
    op.drop_column("transactions", "delivery_deadline_at")
    op.drop_column("transactions", "delivered_at")
    op.drop_column("transactions", "artifact_hash")
    op.drop_column("transactions", "artifact_uri")
    op.drop_column("transactions", "fulfillment_status")
