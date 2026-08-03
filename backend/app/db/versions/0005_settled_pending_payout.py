"""Add settled_pending_payout transaction status

Revision ID: 0005_settled_pending_payout
Revises: 0004_recruit
Create Date: 2026-08-03

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0005_settled_pending_payout"
down_revision: Union[str, None] = "0004_recruit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE transaction_status ADD VALUE IF NOT EXISTS 'settled_pending_payout'"
    )


def downgrade() -> None:
    # Postgres cannot remove enum values safely; leave in place.
    pass
