import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.position_monitor import MonitoredPosition, PositionMonitor
from app.services.node_executor import ExecutionContext


def _make_position(
    position_id: str = "pos-1",
    status: str = "active",
    side: str = "buy",
    entry_price: float = 0.6,
    size: float = 100.0,
    **overrides,
) -> MonitoredPosition:
    return MonitoredPosition(
        position_id=position_id,
        strategy_id=overrides.get("strategy_id", "strat-1"),
        user_id=overrides.get("user_id", "user-1"),
        platform=overrides.get("platform", "polymarket"),
        market_id=overrides.get("market_id", "mkt-1"),
        market_title=overrides.get("market_title", "Test Market"),
        side=side,
        entry_price=entry_price,
        size=size,
        entry_time=datetime.now(timezone.utc),
        status=status,
        risk_nodes=overrides.get("risk_nodes", []),
        risk_edges=overrides.get("risk_edges", []),
        trail_states=overrides.get("trail_states", {}),
        circuit_breaker_state=overrides.get("circuit_breaker_state", {}),
        current_market_data=overrides.get("current_market_data", {}),
        portfolio_state=overrides.get("portfolio_state", {}),
        withdrawal_strategy_id=overrides.get("withdrawal_strategy_id"),
    )


@pytest.fixture
def monitor():
    engine = MagicMock()
    paper = MagicMock()
    return PositionMonitor(
        execution_engine=engine,
        paper_trading_service=paper,
        interval_seconds=1.0,
    )


class TestRegisterPosition:
    def test_adds_to_monitored_positions(self, monitor):
        pos = _make_position(position_id="pos-a")
        monitor.register_position(pos)
        assert "pos-a" in monitor._monitored_positions
        assert monitor._monitored_positions["pos-a"] is pos

    def test_overwrites_existing_position_with_same_id(self, monitor):
        pos1 = _make_position(position_id="pos-x", entry_price=0.5)
        pos2 = _make_position(position_id="pos-x", entry_price=0.7)
        monitor.register_position(pos1)
        monitor.register_position(pos2)
        assert monitor._monitored_positions["pos-x"].entry_price == 0.7

    def test_multiple_positions_coexist(self, monitor):
        monitor.register_position(_make_position(position_id="p1"))
        monitor.register_position(_make_position(position_id="p2"))
        monitor.register_position(_make_position(position_id="p3"))
        assert len(monitor._monitored_positions) == 3


class TestUnregisterPosition:
    def test_removes_existing_position(self, monitor):
        monitor.register_position(_make_position(position_id="pos-r"))
        result = monitor.unregister_position("pos-r")
        assert result is True
        assert "pos-r" not in monitor._monitored_positions

    def test_returns_false_for_nonexistent_position(self, monitor):
        result = monitor.unregister_position("no-such-id")
        assert result is False

    def test_only_removes_specified_position(self, monitor):
        monitor.register_position(_make_position(position_id="keep"))
        monitor.register_position(_make_position(position_id="remove"))
        monitor.unregister_position("remove")
        assert "keep" in monitor._monitored_positions
        assert "remove" not in monitor._monitored_positions


class TestGetPosition:
    def test_returns_correct_position(self, monitor):
        pos = _make_position(position_id="pos-g")
        monitor.register_position(pos)
        result = monitor.get_position("pos-g")
        assert result is pos

    def test_returns_none_for_missing(self, monitor):
        assert monitor.get_position("nonexistent") is None


class TestGetActivePositions:
    def test_returns_only_active_positions(self, monitor):
        monitor.register_position(_make_position(position_id="a1", status="active"))
        monitor.register_position(_make_position(position_id="a2", status="active"))
        monitor.register_position(_make_position(position_id="c1", status="closed"))
        active = monitor.get_active_positions()
        assert len(active) == 2
        assert all(p.status == "active" for p in active)

    def test_returns_empty_when_no_active(self, monitor):
        monitor.register_position(_make_position(position_id="c1", status="closed"))
        monitor.register_position(_make_position(position_id="c2", status="closed"))
        assert monitor.get_active_positions() == []

    def test_returns_empty_when_no_positions(self, monitor):
        assert monitor.get_active_positions() == []


class TestBuildContext:
    def test_creates_execution_context_with_defaults(self, monitor):
        pos = _make_position(
            position_id="ctx-1",
            side="buy",
            entry_price=0.65,
            size=50.0,
        )
        ctx = monitor._build_context(pos)

        assert isinstance(ctx, ExecutionContext)
        assert ctx.signal["position_id"] == "ctx-1"
        assert ctx.signal["side"] == "buy"
        assert ctx.signal["entry_price"] == 0.65
        assert ctx.signal["size"] == 50.0
        assert ctx.signal["market_odds"] == 0.65
        assert ctx.portfolio["current_capital"] == 10000
        assert ctx.portfolio["peak_capital"] == 10000
        assert ctx.market["current_odds"] == 0.65

    def test_build_context_uses_position_market_data(self, monitor):
        pos = _make_position(
            current_market_data={"current_odds": 0.8, "probability": 0.75},
        )
        ctx = monitor._build_context(pos)
        assert ctx.market["current_odds"] == 0.8
        assert ctx.signal["probability"] == 0.75
        assert ctx.signal["market_odds"] == 0.8

    def test_build_context_preserves_portfolio_state(self, monitor):
        pos = _make_position(
            portfolio_state={"current_capital": 5000, "daily_pnl": -100},
        )
        ctx = monitor._build_context(pos)
        assert ctx.portfolio["current_capital"] == 5000
        assert ctx.portfolio["daily_pnl"] == -100
        assert ctx.daily_pnl == -100

    def test_build_context_copies_trail_states(self, monitor):
        trail = {"ts-1": {"high_water_mark": 0.9}}
        pos = _make_position(trail_states=trail)
        ctx = monitor._build_context(pos)
        assert ctx.trail_states["ts-1"]["high_water_mark"] == 0.9

    def test_build_context_copies_circuit_breaker_state(self, monitor):
        cb = {"triggered": True}
        pos = _make_position(circuit_breaker_state=cb)
        ctx = monitor._build_context(pos)
        assert ctx.circuit_breaker_state == cb


class TestStartStopLifecycle:
    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self, monitor):
        assert monitor._running is False
        await monitor.start()
        assert monitor._running is True
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_sets_running_flag_false(self, monitor):
        await monitor.start()
        assert monitor._running is True
        await monitor.stop()
        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, monitor):
        await monitor.start()
        task1 = monitor._task
        await monitor.start()  # second call should be no-op
        assert monitor._task is task1
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self, monitor):
        await monitor.stop()  # should not raise
        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_stop_clears_task(self, monitor):
        await monitor.start()
        assert monitor._task is not None
        await monitor.stop()
        assert monitor._task is None


class TestMonitoredPositionsDict:
    def test_dict_populated_on_register(self, monitor):
        assert len(monitor._monitored_positions) == 0
        monitor.register_position(_make_position(position_id="d1"))
        assert len(monitor._monitored_positions) == 1
        monitor.register_position(_make_position(position_id="d2"))
        assert len(monitor._monitored_positions) == 2

    def test_dict_cleared_on_unregister(self, monitor):
        monitor.register_position(_make_position(position_id="d1"))
        monitor.register_position(_make_position(position_id="d2"))
        monitor.unregister_position("d1")
        assert len(monitor._monitored_positions) == 1
        assert "d2" in monitor._monitored_positions

    def test_dict_values_are_monitored_position_instances(self, monitor):
        pos = _make_position(position_id="inst-1")
        monitor.register_position(pos)
        stored = monitor._monitored_positions["inst-1"]
        assert isinstance(stored, MonitoredPosition)
        assert stored.position_id == "inst-1"


class TestComputePnl:
    def test_buy_side_pnl(self, monitor):
        pos = _make_position(side="buy", entry_price=0.6, size=100)
        pnl = monitor._compute_pnl(pos, exit_price=0.7)
        assert pnl == pytest.approx(10.0)

    def test_buy_side_loss(self, monitor):
        pos = _make_position(side="buy", entry_price=0.6, size=100)
        pnl = monitor._compute_pnl(pos, exit_price=0.5)
        assert pnl == pytest.approx(-10.0)

    def test_sell_side_pnl(self, monitor):
        pos = _make_position(side="sell", entry_price=0.6, size=100)
        pnl = monitor._compute_pnl(pos, exit_price=0.5)
        assert pnl == pytest.approx(10.0)

    def test_sell_side_loss(self, monitor):
        pos = _make_position(side="sell", entry_price=0.6, size=100)
        pnl = monitor._compute_pnl(pos, exit_price=0.7)
        assert pnl == pytest.approx(-10.0)


class TestUpdatePositionMarketData:
    def test_updates_existing_position(self, monitor):
        pos = _make_position(position_id="u1")
        monitor.register_position(pos)
        result = monitor.update_position_market_data("u1", {"current_odds": 0.9})
        assert result is True
        assert pos.current_market_data["current_odds"] == 0.9

    def test_returns_false_for_missing_position(self, monitor):
        result = monitor.update_position_market_data("nope", {"current_odds": 0.9})
        assert result is False


class TestUpdatePositionPortfolioState:
    def test_updates_existing_position(self, monitor):
        pos = _make_position(position_id="u1")
        monitor.register_position(pos)
        result = monitor.update_position_portfolio_state("u1", {"current_capital": 8000})
        assert result is True
        assert pos.portfolio_state["current_capital"] == 8000

    def test_returns_false_for_missing_position(self, monitor):
        result = monitor.update_position_portfolio_state("nope", {"current_capital": 8000})
        assert result is False
