"""Add platform_order_id to paper_orders

Revision ID: 002
Revises: 001
Create Date: 2026-05-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("paper_orders", sa.Column("platform_order_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("paper_orders", "platform_order_id")
