"""Baseline schema for the entire application.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-13

This replaces the previous broken chain (001-003) which referenced tables
that were never created and used SQLite-only server_defaults. There is no
production database to preserve; fresh installs run this baseline directly.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

_TRUE = sa.text("true")
_FALSE = sa.text("false")
_ZERO = sa.text("0")
_ONE = sa.text("1")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=_TRUE),
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
        sa.Column("version", sa.Integer(), nullable=True, server_default=_ONE),
        sa.Column("version_history", sa.JSON(), nullable=True),
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

    op.create_table(
        "strategy_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "paper_wallets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("initial_balance", sa.Float(), nullable=True),
        sa.Column("current_balance", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=_TRUE),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_wallets_user_id", "paper_wallets", ["user_id"])

    op.create_table(
        "paper_orders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("wallet_id", sa.String(), nullable=False),
        sa.Column("strategy_id", sa.String(), nullable=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("market_id", sa.String(), nullable=False),
        sa.Column("market_title", sa.String(), nullable=True),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("order_type", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("filled_amount", sa.Float(), nullable=True),
        sa.Column("fill_price", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("pending", "partial", "filled", "cancelled", name="orderstatus"), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("slippage", sa.Float(), nullable=True),
        sa.Column("platform_order_id", sa.String(), nullable=True),
        sa.Column("resolved_outcome", sa.String(), nullable=True),
        sa.Column("calibration_error", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_orders_wallet_id", "paper_orders", ["wallet_id"])

    op.create_table(
        "research_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("strategy_id", sa.String(), nullable=True),
        sa.Column("status", sa.Enum("running", "paused", "completed", "failed", name="sessionstatus"), nullable=True),
        sa.Column("mode", sa.Enum("manual", "cron", "continuous", name="sessionmode"), nullable=True),
        sa.Column("trigger_type", sa.String(), nullable=True),
        sa.Column(
            "composite_preset",
            sa.Enum(
                "sharpe_max", "win_rate_max", "risk_adjusted",
                "win_rate", "calmar", "profit_factor",
                name="compositepreset",
            ),
            nullable=True,
        ),
        sa.Column("current_iteration", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("total_kept", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("total_reverted", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("avg_sharpe", sa.Float(), nullable=True),
        sa.Column("avg_win_rate", sa.Float(), nullable=True),
        sa.Column("best_sharpe", sa.Float(), nullable=True),
        sa.Column("best_win_rate", sa.Float(), nullable=True),
        sa.Column("rlm_alpha_vector_id", sa.String(), nullable=True),
        sa.Column("toto2_regime", sa.String(), nullable=True),
        sa.Column("toto2_volatility", sa.Float(), nullable=True),
        sa.Column("tabpfn_top_features", sa.JSON(), nullable=True),
        sa.Column("hypothesis_count", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("pareto_front", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_sessions_user_id", "research_sessions", ["user_id"])
    op.create_index("ix_research_sessions_strategy_id", "research_sessions", ["strategy_id"])

    op.create_table(
        "experiment_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("hypothesis_prompt", sa.Text(), nullable=True),
        sa.Column("regime_at_time", sa.String(), nullable=True),
        sa.Column("volatility_at_time", sa.Float(), nullable=True),
        sa.Column("feature_importance_at_time", sa.JSON(), nullable=True),
        sa.Column("rlm_alpha_vector_snapshot", sa.JSON(), nullable=True),
        sa.Column("backtest_config", sa.JSON(), nullable=True),
        sa.Column("backtest_trades", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("backtest_win_rate", sa.Float(), nullable=True),
        sa.Column("backtest_sharpe", sa.Float(), nullable=True),
        sa.Column("backtest_max_drawdown", sa.Float(), nullable=True),
        sa.Column("backtest_total_pnl", sa.Float(), nullable=True),
        sa.Column("tabpfn_probability", sa.Float(), nullable=True),
        sa.Column("tabpfn_confidence", sa.Float(), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("shap_explanation", sa.JSON(), nullable=True),
        sa.Column("verdict", sa.String(), nullable=True),
        sa.Column("git_commit_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_results_session_id", "experiment_results", ["session_id"])

    op.create_table(
        "research_session_configs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("max_concurrent", sa.Integer(), nullable=True),
        sa.Column("composite_preset", sa.String(), nullable=True),
        sa.Column("cron_enabled", sa.Boolean(), nullable=True, server_default=_FALSE),
        sa.Column("cron_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("continuous_enabled", sa.Boolean(), nullable=True, server_default=_FALSE),
        sa.Column("rlm_sources", sa.JSON(), nullable=True),
        sa.Column("rlm_cron_enabled", sa.Boolean(), nullable=True, server_default=_FALSE),
        sa.Column("rlm_cron_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("max_hypotheses_per_session", sa.Integer(), nullable=True),
        sa.Column("enable_genetic_optimization", sa.Boolean(), nullable=True, server_default=_FALSE),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_research_session_configs_user_id", "research_session_configs", ["user_id"])

    op.create_table(
        "rlm_alpha_vectors",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("source_hash", sa.String(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("alpha_vector", sa.JSON(), nullable=True),
        sa.Column("linguistic_signals", sa.JSON(), nullable=True),
        sa.Column("sub_agent_traces", sa.JSON(), nullable=True),
        sa.Column("dspy_trajectory", sa.Text(), nullable=True),
        sa.Column("traces", sa.JSON(), nullable=True),
        sa.Column("used_in_sessions", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rlm_alpha_vectors_user_id", "rlm_alpha_vectors", ["user_id"])
    op.create_index("ix_rlm_alpha_vectors_source_hash", "rlm_alpha_vectors", ["source_hash"])

    op.create_table(
        "hermes_traces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tool_calls_attempted", sa.JSON(), nullable=True),
        sa.Column("tool_results", sa.JSON(), nullable=True),
        sa.Column("classification_chain", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hermes_traces_session_id", "hermes_traces", ["session_id"])

    op.create_table(
        "meta_strategies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("strategy_ids", sa.JSON(), nullable=True),
        sa.Column("scoring_config", sa.JSON(), nullable=True),
        sa.Column("promotion_config", sa.JSON(), nullable=True),
        sa.Column("confluence_config", sa.JSON(), nullable=True),
        sa.Column("consumer", sa.String(), nullable=True),
        sa.Column("current_winner_id", sa.String(), nullable=True),
        sa.Column("last_promotion_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meta_strategies_user_id", "meta_strategies", ["user_id"])

    op.create_table(
        "risk_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_templates_user_id", "risk_templates", ["user_id"])

    op.create_table(
        "monitored_positions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("strategy_id", sa.String(), nullable=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("market_id", sa.String(), nullable=False),
        sa.Column("market_title", sa.String(), nullable=True),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("size", sa.Float(), nullable=False),
        sa.Column("high_water_mark", sa.Float(), nullable=True),
        sa.Column("entry_time", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("risk_config", sa.JSON(), nullable=True),
        sa.Column("trail_states", sa.JSON(), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("exit_time", sa.DateTime(), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("withdrawal_strategy_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monitored_positions_user_id", "monitored_positions", ["user_id"])
    op.create_index("ix_monitored_positions_strategy_id", "monitored_positions", ["strategy_id"])

    op.create_table(
        "safe_wallets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("balance", sa.Float(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("is_disconnected", sa.Boolean(), nullable=True, server_default=_TRUE),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safe_wallets_user_id", "safe_wallets", ["user_id"])

    op.create_table(
        "withdrawal_strategies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=_TRUE),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("current_step_index", sa.Integer(), nullable=True, server_default=_ZERO),
        sa.Column("step_states", sa.JSON(), nullable=True),
        sa.Column("safe_wallet_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_withdrawal_strategies_user_id", "withdrawal_strategies", ["user_id"])

    op.create_table(
        "withdrawal_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("safe_wallet_id", sa.String(), nullable=False),
        sa.Column("strategy_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("trigger_type", sa.String(), nullable=True),
        sa.Column("trigger_step_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_withdrawal_records_user_id", "withdrawal_records", ["user_id"])


def downgrade() -> None:
    op.drop_table("withdrawal_records")
    op.drop_table("withdrawal_strategies")
    op.drop_table("safe_wallets")
    op.drop_table("monitored_positions")
    op.drop_table("risk_templates")
    op.drop_table("meta_strategies")
    op.drop_table("hermes_traces")
    op.drop_table("rlm_alpha_vectors")
    op.drop_table("research_session_configs")
    op.drop_table("experiment_results")
    op.drop_table("research_sessions")
    op.drop_table("paper_orders")
    op.drop_table("paper_wallets")
    op.drop_table("strategy_templates")
    op.drop_table("trades")
    op.drop_table("strategies")
    op.drop_table("markets")
    op.drop_table("users")
