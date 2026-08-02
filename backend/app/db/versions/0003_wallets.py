"""add wallet_address for CDP agent wallets

Revision ID: 0003_wallets
Revises: 0002_fees_referral
Create Date: 2026-08-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_wallets"
down_revision: Union[str, None] = "0002_fees_referral"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("wallet_address", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_agents_wallet_address", "agents", ["wallet_address"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agents_wallet_address", table_name="agents")
    op.drop_column("agents", "wallet_address")
