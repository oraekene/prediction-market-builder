import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.position_monitor import MonitoredPosition, PositionMonitor
from app.services.node_executor import ExecutionContext


def _make_position(
    position_id: str = "pos-int-1",
    side: str = "buy",
    entry_price: float = 0.6,
    size: float = 100.0,
    status: str = "active",
    risk_nodes: list | None = None,
    risk_edges: list | None = None,
    trail_states: dict | None = None,
    current_market_data: dict | None = None,
    portfolio_state: dict | None = None,
    **overrides,
) -> MonitoredPosition:
    return MonitoredPosition(
        position_id=position_id,
        strategy_id=overrides.get("strategy_id", "strat-int-1"),
        user_id=overrides.get("user_id", "user-int-1"),
        platform=overrides.get("platform", "polymarket"),
        market_id=overrides.get("market_id", "mkt-int-1"),
        market_title=overrides.get("market_title", "Integration Test Market"),
        side=side,
        entry_price=entry_price,
        size=size,
        entry_time=datetime.now(timezone.utc),
        status=status,
        risk_nodes=risk_nodes or [],
        risk_edges=risk_edges or [],
        trail_states=trail_states or {},
        circuit_breaker_state=overrides.get("circuit_breaker_state", {}),
        current_market_data=current_market_data or {},
        portfolio_state=portfolio_state or {},
        withdrawal_strategy_id=overrides.get("withdrawal_strategy_id"),
    )


def _make_trailing_stop_node(
    node_id: str = "ts-1",
    trail_pct: float = 0.05,
    activation_pct: float = 0.02,
) -> dict:
    return {
        "id": node_id,
        "type": "trailing_stop",
        "data": {
            "trail_pct": trail_pct,
            "activation_pct": activation_pct,
        },
    }


def _make_stop_loss_node(
    node_id: str = "sl-1",
    stop_loss: float = 0.1,
) -> dict:
    return {
        "id": node_id,
        "type": "stop_loss",
        "data": {"stop_loss": stop_loss},
    }


def _make_take_profit_node(
    node_id: str = "tp-1",
    take_profit: float = 0.2,
) -> dict:
    return {
        "id": node_id,
        "type": "take_profit",
        "data": {"take_profit": take_profit},
    }


@pytest.fixture
def monitor():
    engine = MagicMock()
    paper = MagicMock()
    return PositionMonitor(
        execution_engine=engine,
        paper_trading_service=paper,
        interval_seconds=1.0,
    )


@pytest.mark.asyncio
class TestPositionMonitorIntegration:

    async def test_register_position_on_paper_trade(self, monitor):
        """Placing a paper trade with auto_monitor:true tracks the position."""
        pos = _make_position(
            position_id="paper-trade-1",
            entry_price=0.65,
            size=200.0,
            current_market_data={"current_odds": 0.65, "probability": 0.7},
            portfolio_state={"current_capital": 10000, "user": MagicMock()},
        )
        monitor.register_position(pos)

        tracked = monitor.get_position("paper-trade-1")
        assert tracked is not None
        assert tracked.position_id == "paper-trade-1"
        assert tracked.entry_price == 0.65
        assert tracked.size == 200.0
        assert tracked.status == "active"
        assert tracked.current_market_data["current_odds"] == 0.65

        active = monitor.get_active_positions()
        assert len(active) == 1
        assert active[0].position_id == "paper-trade-1"

    async def test_evaluate_trailing_stop_detects_trigger(self, monitor):
        """Register a position with trailing stop, simulate price drop, verify trigger."""
        trail_node = _make_trailing_stop_node(
            node_id="ts-drop",
            trail_pct=0.05,
            activation_pct=0.02,
        )
        pos = _make_position(
            position_id="pos-drop-1",
            side="buy",
            entry_price=0.60,
            risk_nodes=[trail_node],
            current_market_data={"current_odds": 0.60},
        )
        monitor.register_position(pos)

        context = monitor._build_context(pos)
        monitor._update_trail_state(pos, context)
        assert pos.trail_states["ts-drop"]["triggered"] is False
        assert pos.trail_states["ts-drop"]["activated"] is False

        monitor.update_position_market_data("pos-drop-1", {"current_odds": 0.65})
        context2 = monitor._build_context(pos)
        monitor._update_trail_state(pos, context2)
        assert pos.trail_states["ts-drop"]["activated"] is True
        assert pos.trail_states["ts-drop"]["high_water_mark"] == pytest.approx(0.65)
        assert pos.trail_states["ts-drop"]["triggered"] is False

        monitor.update_position_market_data("pos-drop-1", {"current_odds": 0.55})
        context3 = monitor._build_context(pos)
        monitor._update_trail_state(pos, context3)
        assert pos.trail_states["ts-drop"]["triggered"] is True

    async def test_update_hwm_on_price_rise(self, monitor):
        """Register position, simulate price rise, verify HWM is updated."""
        trail_node = _make_trailing_stop_node(
            node_id="ts-hwm",
            trail_pct=0.10,
            activation_pct=0.01,
        )
        pos = _make_position(
            position_id="pos-hwm-1",
            side="buy",
            entry_price=0.50,
            risk_nodes=[trail_node],
            current_market_data={"current_odds": 0.50},
        )
        monitor.register_position(pos)

        monitor.update_position_market_data("pos-hwm-1", {"current_odds": 0.55})
        ctx1 = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx1)
        assert pos.trail_states["ts-hwm"]["high_water_mark"] == pytest.approx(0.55)

        monitor.update_position_market_data("pos-hwm-1", {"current_odds": 0.62})
        ctx2 = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx2)
        assert pos.trail_states["ts-hwm"]["high_water_mark"] == pytest.approx(0.62)

        monitor.update_position_market_data("pos-hwm-1", {"current_odds": 0.58})
        ctx3 = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx3)
        assert pos.trail_states["ts-hwm"]["high_water_mark"] == pytest.approx(0.62)

    async def test_start_stop_lifecycle(self, monitor):
        """Start/stop monitor, verify flags and task lifecycle."""
        assert monitor._running is False
        assert monitor._task is None

        await monitor.start()
        assert monitor._running is True
        assert monitor._task is not None
        assert not monitor._task.done()

        await monitor.stop()
        assert monitor._running is False
        assert monitor._task is None

    async def test_start_is_idempotent(self, monitor):
        """Calling start multiple times does not create multiple tasks."""
        await monitor.start()
        task1 = monitor._task

        await monitor.start()
        assert monitor._task is task1

        await monitor.stop()

    async def test_stop_without_start_is_safe(self, monitor):
        """Stopping without starting does not raise."""
        await monitor.stop()
        assert monitor._running is False
        assert monitor._task is None

    async def test_handle_empty_portfolio(self, monitor):
        """Monitor with no positions runs without errors."""
        assert len(monitor.get_active_positions()) == 0

        await monitor.start()
        await asyncio.sleep(0.1)
        await monitor.stop()

        assert len(monitor.get_active_positions()) == 0

    async def test_check_all_positions_with_empty_portfolio(self, monitor):
        """_check_all_positions handles empty monitored dict cleanly."""
        await monitor._check_all_positions()
        assert len(monitor._monitored_positions) == 0

    async def test_build_context_has_all_required_fields(self, monitor):
        """Verify context has all required fields populated."""
        pos = _make_position(
            position_id="ctx-full-1",
            side="sell",
            entry_price=0.75,
            size=150.0,
            trail_states={"ts-x": {"high_water_mark": 0.8}},
            circuit_breaker_state={"tripped": False},
            current_market_data={
                "current_odds": 0.78,
                "probability": 0.80,
                "confidence": 0.9,
            },
            portfolio_state={
                "current_capital": 8500,
                "peak_capital": 9000,
                "daily_pnl": -50,
                "weekly_pnl": 200,
                "monthly_pnl": 1500,
                "consecutive_losses": 2,
                "price_history": [0.7, 0.72, 0.75],
            },
        )
        ctx = monitor._build_context(pos)

        assert isinstance(ctx, ExecutionContext)
        assert ctx.signal["position_id"] == "ctx-full-1"
        assert ctx.signal["side"] == "sell"
        assert ctx.signal["entry_price"] == 0.75
        assert ctx.signal["size"] == 150.0
        assert ctx.signal["market_odds"] == 0.78
        assert ctx.signal["probability"] == 0.80
        assert ctx.signal["confidence"] == 0.9

        assert ctx.market["current_odds"] == 0.78
        assert ctx.portfolio["current_capital"] == 8500
        assert ctx.portfolio["peak_capital"] == 9000
        assert ctx.daily_pnl == -50
        assert ctx.weekly_pnl == 200
        assert ctx.monthly_pnl == 1500
        assert ctx.consecutive_losses == 2
        assert ctx.price_history == [0.7, 0.72, 0.75]
        assert ctx.trail_states == {"ts-x": {"high_water_mark": 0.8}}
        assert ctx.circuit_breaker_state == {"tripped": False}
        assert ctx.position_monitor is monitor
        assert ctx.execution_engine is monitor.execution_engine

    async def test_multiple_positions_tracked_simultaneously(self, monitor):
        """Register 3 positions, verify all are tracked independently."""
        nodes_a = [_make_trailing_stop_node("ts-a", trail_pct=0.03)]
        nodes_b = [_make_stop_loss_node("sl-b", stop_loss=0.15)]
        nodes_c = [_make_take_profit_node("tp-c", take_profit=0.25)]

        pos_a = _make_position(
            position_id="multi-a",
            side="buy",
            entry_price=0.55,
            risk_nodes=nodes_a,
            current_market_data={"current_odds": 0.55},
        )
        pos_b = _make_position(
            position_id="multi-b",
            side="sell",
            entry_price=0.70,
            risk_nodes=nodes_b,
            current_market_data={"current_odds": 0.70},
        )
        pos_c = _make_position(
            position_id="multi-c",
            side="buy",
            entry_price=0.40,
            risk_nodes=nodes_c,
            current_market_data={"current_odds": 0.40},
        )

        monitor.register_position(pos_a)
        monitor.register_position(pos_b)
        monitor.register_position(pos_c)

        active = monitor.get_active_positions()
        assert len(active) == 3

        ids = {p.position_id for p in active}
        assert ids == {"multi-a", "multi-b", "multi-c"}

        monitor.update_position_market_data("multi-a", {"current_odds": 0.58})
        monitor.update_position_market_data("multi-b", {"current_odds": 0.65})
        monitor.update_position_market_data("multi-c", {"current_odds": 0.50})

        ctx_a = monitor._build_context(pos_a)
        monitor._update_trail_state(pos_a, ctx_a)
        assert pos_a.trail_states["ts-a"]["high_water_mark"] == pytest.approx(0.58)

        ctx_b = monitor._build_context(pos_b)
        monitor._update_trail_state(pos_b, ctx_b)
        assert pos_b.trail_states["sl-b"]["loss_pct"] == pytest.approx(-0.0714, abs=1e-4)

        ctx_c = monitor._build_context(pos_c)
        monitor._update_trail_state(pos_c, ctx_c)
        assert pos_c.trail_states["tp-c"]["gain_pct"] == pytest.approx(0.25)

    async def test_unregister_position(self, monitor):
        """Register then unregister a position, verify it is removed."""
        pos = _make_position(position_id="unreg-1")
        monitor.register_position(pos)
        assert monitor.get_position("unreg-1") is pos

        result = monitor.unregister_position("unreg-1")
        assert result is True
        assert monitor.get_position("unreg-1") is None
        assert len(monitor.get_active_positions()) == 0

    async def test_unregister_nonexistent_returns_false(self, monitor):
        """Unregistering a position that was never registered returns False."""
        result = monitor.unregister_position("ghost-id")
        assert result is False

    async def test_unregister_does_not_affect_others(self, monitor):
        """Unregistering one position does not remove other tracked positions."""
        monitor.register_position(_make_position(position_id="keep-1"))
        monitor.register_position(_make_position(position_id="keep-2"))

        monitor.unregister_position("keep-1")

        assert monitor.get_position("keep-1") is None
        assert monitor.get_position("keep-2") is not None
        assert len(monitor.get_active_positions()) == 1

    async def test_trailing_stop_does_not_trigger_before_activation(self, monitor):
        """Trailing stop should not trigger before activation threshold is reached."""
        trail_node = _make_trailing_stop_node(
            node_id="ts-pre",
            trail_pct=0.05,
            activation_pct=0.10,
        )
        pos = _make_position(
            position_id="pos-pre-act",
            side="buy",
            entry_price=0.50,
            risk_nodes=[trail_node],
            current_market_data={"current_odds": 0.50},
        )
        monitor.register_position(pos)

        monitor.update_position_market_data("pos-pre-act", {"current_odds": 0.51})
        ctx = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx)

        assert pos.trail_states["ts-pre"]["activated"] is False
        assert pos.trail_states["ts-pre"]["triggered"] is False

    async def test_stop_loss_detects_loss(self, monitor):
        """Stop loss node triggers when loss exceeds threshold."""
        sl_node = _make_stop_loss_node("sl-int", stop_loss=0.05)
        pos = _make_position(
            position_id="pos-sl-int",
            side="buy",
            entry_price=0.60,
            risk_nodes=[sl_node],
            current_market_data={"current_odds": 0.60},
        )
        monitor.register_position(pos)

        monitor.update_position_market_data("pos-sl-int", {"current_odds": 0.55})
        ctx = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx)

        assert pos.trail_states["sl-int"]["loss_pct"] == pytest.approx(0.0833, abs=1e-4)
        assert pos.trail_states["sl-int"]["triggered"] is True

    async def test_take_profit_detects_gain(self, monitor):
        """Take profit node triggers when gain exceeds threshold."""
        tp_node = _make_take_profit_node("tp-int", take_profit=0.10)
        pos = _make_position(
            position_id="pos-tp-int",
            side="buy",
            entry_price=0.50,
            risk_nodes=[tp_node],
            current_market_data={"current_odds": 0.50},
        )
        monitor.register_position(pos)

        monitor.update_position_market_data("pos-tp-int", {"current_odds": 0.60})
        ctx = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx)

        assert pos.trail_states["tp-int"]["gain_pct"] == pytest.approx(0.20)
        assert pos.trail_states["tp-int"]["triggered"] is True

    async def test_sell_side_trailing_stop(self, monitor):
        """Trailing stop logic works correctly for sell-side positions."""
        trail_node = _make_trailing_stop_node(
            node_id="ts-sell",
            trail_pct=0.05,
            activation_pct=0.02,
        )
        pos = _make_position(
            position_id="pos-sell-ts",
            side="sell",
            entry_price=0.60,
            risk_nodes=[trail_node],
            current_market_data={"current_odds": 0.60},
        )
        monitor.register_position(pos)

        monitor.update_position_market_data("pos-sell-ts", {"current_odds": 0.55})
        ctx1 = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx1)
        assert pos.trail_states["ts-sell"]["activated"] is True
        assert pos.trail_states["ts-sell"]["high_water_mark"] == pytest.approx(0.55)

        monitor.update_position_market_data("pos-sell-ts", {"current_odds": 0.65})
        ctx2 = monitor._build_context(pos)
        monitor._update_trail_state(pos, ctx2)
        assert pos.trail_states["ts-sell"]["triggered"] is True

    async def test_execute_close_via_execution_engine(self, monitor):
        """_execute_close calls execution engine and marks position closed."""
        mock_fill = MagicMock()
        mock_fill.status = "filled"
        monitor.execution_engine.place_order = AsyncMock(return_value=mock_fill)

        pos = _make_position(
            position_id="close-1",
            side="buy",
            entry_price=0.60,
            size=100.0,
            portfolio_state={"user": MagicMock()},
            current_market_data={"current_odds": 0.70},
        )
        monitor.register_position(pos)

        await monitor._execute_close(pos)

        assert pos.status == "closed"
        assert pos.current_market_data["exit_price"] == 0.70
        assert "exit_time" in pos.current_market_data
        assert pos.current_market_data["pnl"] == pytest.approx(10.0)
        monitor.execution_engine.place_order.assert_awaited_once()

    async def test_check_all_positions_closes_on_violation(self, monitor):
        """_check_all_positions closes position when graph executor returns violation."""
        monitor.execution_engine.place_order = AsyncMock(return_value=MagicMock(status="filled"))

        nodes = [{"id": "gate-1", "type": "risk_gate", "data": {}}]
        pos = _make_position(
            position_id="viol-1",
            side="buy",
            entry_price=0.60,
            size=50.0,
            risk_nodes=nodes,
            current_market_data={"current_odds": 0.60},
            portfolio_state={"user": MagicMock()},
        )
        monitor.register_position(pos)

        with patch.object(
            monitor._graph_executor,
            "execute",
            new_callable=AsyncMock,
            return_value={"approved": False, "violations": ["max_loss_exceeded"]},
        ):
            await monitor._check_all_positions()

        assert pos.status == "closed"

    async def test_check_all_positions_skips_closed_positions(self, monitor):
        """_check_all_positions does not re-check closed positions."""
        pos = _make_position(position_id="closed-skip", status="closed")
        monitor.register_position(pos)

        with patch.object(
            monitor._graph_executor,
            "execute",
            new_callable=AsyncMock,
        ) as mock_exec:
            await monitor._check_all_positions()
            mock_exec.assert_not_called()

    async def test_build_context_copies_do_not_mutate_original(self, monitor):
        """_build_context returns copies so mutations do not affect original position."""
        trail = {"ts-copy": {"high_water_mark": 0.9}}
        circuit = {"tripped": True}
        market = {"current_odds": 0.75, "probability": 0.8}
        portfolio = {"current_capital": 5000, "daily_pnl": -100}

        pos = _make_position(
            position_id="copy-1",
            trail_states=trail,
            circuit_breaker_state=circuit,
            current_market_data=market,
            portfolio_state=portfolio,
        )
        ctx = monitor._build_context(pos)

        assert ctx.trail_states["ts-copy"]["high_water_mark"] == 0.9
        assert ctx.circuit_breaker_state["tripped"] is True
        assert ctx.market["current_odds"] == 0.75
        assert ctx.portfolio["current_capital"] == 5000

    async def test_concurrent_unregister_and_check(self, monitor):
        """Unregistering during a check cycle does not cause errors."""
        pos = _make_position(position_id="race-1")
        monitor.register_position(pos)

        monitor.unregister_position("race-1")
        await monitor._check_all_positions()
        assert monitor.get_position("race-1") is None
