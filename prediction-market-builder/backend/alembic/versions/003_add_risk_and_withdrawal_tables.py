"""Add monitored_positions, safe_wallets, withdrawal_strategies, withdrawal_records tables

Revision ID: 003
Revises: 002
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'monitored_positions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=True),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('market_id', sa.String(), nullable=False),
        sa.Column('market_title', sa.String(), nullable=True),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('size', sa.Float(), nullable=False),
        sa.Column('high_water_mark', sa.Float(), nullable=True),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), server_default='active'),
        sa.Column('risk_config', sa.JSON(), server_default='{}'),
        sa.Column('trail_states', sa.JSON(), server_default='{}'),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('withdrawal_strategy_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_monitored_positions_user_id', 'monitored_positions', ['user_id'])
    op.create_index('ix_monitored_positions_strategy_id', 'monitored_positions', ['strategy_id'])

    op.create_table(
        'safe_wallets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('currency', sa.String(), server_default='USDC'),
        sa.Column('balance', sa.Float(), server_default='0'),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('is_disconnected', sa.Boolean(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_safe_wallets_user_id', 'safe_wallets', ['user_id'])

    op.create_table(
        'withdrawal_strategies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('steps', sa.JSON(), server_default='[]'),
        sa.Column('current_step_index', sa.Integer(), server_default='0'),
        sa.Column('step_states', sa.JSON(), server_default='{}'),
        sa.Column('safe_wallet_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_withdrawal_strategies_user_id', 'withdrawal_strategies', ['user_id'])

    op.create_table(
        'withdrawal_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('safe_wallet_id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('source', sa.String(), server_default='profits'),
        sa.Column('trigger_type', sa.String(), server_default='manual'),
        sa.Column('trigger_step_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_withdrawal_records_user_id', 'withdrawal_records', ['user_id'])


def downgrade() -> None:
    op.drop_table('withdrawal_records')
    op.drop_table('withdrawal_strategies')
    op.drop_table('safe_wallets')
    op.drop_table('monitored_positions')
