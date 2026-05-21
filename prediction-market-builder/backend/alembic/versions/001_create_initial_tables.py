"""Create initial tables

Revision ID: 001
Revises:
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("polymarket_key", sa.String(), nullable=True),
        sa.Column("kalshi_key", sa.String(), nullable=True),
        sa.Column("drift_key", sa.String(), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "markets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("platform", sa.Enum("polymarket", "kalshi", "drift", name="marketplatform"), nullable=True),
        sa.Column("platform_market_id", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("current_odds", sa.Float(), nullable=True),
        sa.Column("bid", sa.Float(), nullable=True),
        sa.Column("ask", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("liquidity", sa.Float(), nullable=True),
        sa.Column("participants", sa.Float(), nullable=True),
        sa.Column("close_time", sa.DateTime(), nullable=True),
        sa.Column("resolution_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Enum("open", "closed", "resolved", name="marketstatus"), nullable=True),
        sa.Column("outcomes", sa.JSON(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "platform_market_id", name="uq_platform_market"),
    )
    op.create_table(
        "strategies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("draft", "active", "paused", "archived", name="strategystatus"), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("nodes", sa.JSON(), nullable=True),
        sa.Column("edges", sa.JSON(), nullable=True),
        sa.Column("risk_profile", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategies_user_id", "strategies", ["user_id"])
    op.create_table(
        "trades",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("strategy_id", sa.String(), nullable=True),
        sa.Column("market_id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("pending", "executed", "failed", "cancelled", name="tradestatus"), nullable=True),
        sa.Column("platform_trade_id", sa.String(), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_user_id", "trades", ["user_id"])


def downgrade() -> None:
    op.drop_table("trades")
    op.drop_table("strategies")
    op.drop_table("markets")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS marketplatform")
    op.execute("DROP TYPE IF EXISTS marketstatus")
    op.execute("DROP TYPE IF EXISTS strategystatus")
    op.execute("DROP TYPE IF EXISTS tradestatus")
