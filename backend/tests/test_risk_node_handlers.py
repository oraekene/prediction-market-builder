import pytest
import numpy as np
from app.services.node_executor import ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_node_handlers import (
    handle_var_check, handle_drawdown_monitor, handle_correlation_check,
    handle_concentration_check, handle_position_sizer, handle_hedge_action,
    handle_rebalance_action, handle_alert_action, handle_stop_loss, handle_take_profit,
)


@pytest.fixture
def ctx():
    return ExecutionContext(
        market={"current_odds": 0.55},
        signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 10000, "peak_capital": 11000, "returns": {}},
        risk_calculator=RiskCalculator(),
        portfolio_manager=PortfolioManager(10000),
    )


def test_handle_var_check_triggers(ctx):
    node = {"id": "v1", "type": "var_check", "data": {"confidence": 0.95, "limit": 0.02}}
    np.random.seed(42)
    ctx.portfolio["returns"] = list(np.random.normal(0.001, 0.02, 100))
    result = handle_var_check(node, {}, ctx)
    assert "triggered" in result
    assert "var" in result
    assert "es" in result


def test_handle_drawdown_monitor_triggers(ctx):
    node = {"id": "d1", "type": "drawdown_monitor", "data": {"max_drawdown": 0.1}}
    result = handle_drawdown_monitor(node, {}, ctx)
    assert "triggered" in result
    assert "drawdown" in result


def test_handle_correlation_check(ctx):
    node = {"id": "c1", "type": "correlation_check", "data": {"max_correlation": 0.7}}
    result = handle_correlation_check(node, {}, ctx)
    assert "triggered" in result
    assert "correlation" in result


def test_handle_concentration_check(ctx):
    node = {"id": "cc1", "type": "concentration_check", "data": {"max_concentration": 0.5}}
    result = handle_concentration_check(node, {}, ctx)
    assert "triggered" in result


def test_handle_position_sizer_kelly(ctx):
    node = {"id": "ps1", "type": "position_sizer", "data": {"method": "kelly"}}
    result = handle_position_sizer(node, {}, ctx)
    assert "suggested_size" in result
    assert result["suggested_size"] > 0


def test_handle_position_sizer_fixed(ctx):
    node = {"id": "ps2", "type": "position_sizer", "data": {"method": "fixed", "fraction": 0.03}}
    result = handle_position_sizer(node, {}, ctx)
    assert result["suggested_size"] == 0.03


def test_handle_hedge_action(ctx):
    node = {"id": "h1", "type": "hedge_action", "data": {"hedge_ratio": 0.5}}
    result = handle_hedge_action(node, {}, ctx)
    assert "hedges" in result


def test_handle_rebalance_action(ctx):
    node = {"id": "r1", "type": "rebalance_action", "data": {}}
    result = handle_rebalance_action(node, {}, ctx)
    assert "trades" in result


def test_handle_alert_action(ctx):
    node = {"id": "a1", "type": "alert_action", "data": {"message": "test alert"}}
    result = handle_alert_action(node, {}, ctx)
    assert result["message"] == "test alert"
    assert result["severity"] == "warning"


def test_handle_stop_loss_triggers():
    ctx = ExecutionContext(
        market={"current_odds": 0.45},
        signal={},
        portfolio={
            "current_capital": 10000,
            "peak_capital": 10000,
            "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55}],
        },
    )
    node = {"id": "sl1", "type": "stop_loss", "data": {"stop_loss": 0.1}}
    result = handle_stop_loss(node, {}, ctx)
    assert result["triggered"] is True
    assert len(result["positions"]) == 1
    assert result["positions"][0]["market_id"] == "mkt-1"


def test_handle_stop_loss_does_not_trigger():
    ctx = ExecutionContext(
        market={"current_odds": 0.52},
        signal={},
        portfolio={
            "current_capital": 10000,
            "peak_capital": 10000,
            "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55}],
        },
    )
    node = {"id": "sl2", "type": "stop_loss", "data": {"stop_loss": 0.1}}
    result = handle_stop_loss(node, {}, ctx)
    assert result["triggered"] is False


def test_handle_take_profit_triggers():
    ctx = ExecutionContext(
        market={"current_odds": 0.68},
        signal={},
        portfolio={
            "current_capital": 10000,
            "peak_capital": 10000,
            "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55}],
        },
    )
    node = {"id": "tp1", "type": "take_profit", "data": {"take_profit": 0.2}}
    result = handle_take_profit(node, {}, ctx)
    assert result["triggered"] is True
    assert len(result["positions"]) == 1


def test_handle_take_profit_does_not_trigger():
    ctx = ExecutionContext(
        market={"current_odds": 0.58},
        signal={},
        portfolio={
            "current_capital": 10000,
            "peak_capital": 10000,
            "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55}],
        },
    )
    node = {"id": "tp2", "type": "take_profit", "data": {"take_profit": 0.2}}
    result = handle_take_profit(node, {}, ctx)
    assert result["triggered"] is False


def test_handle_stop_loss_short_position():
    ctx = ExecutionContext(
        market={"current_odds": 0.62},
        signal={},
        portfolio={
            "current_capital": 10000,
            "peak_capital": 10000,
            "positions": [{"market_id": "mkt-1", "side": "sell", "price": 0.55}],
        },
    )
    node = {"id": "sl3", "type": "stop_loss", "data": {"stop_loss": 0.1}}
    result = handle_stop_loss(node, {}, ctx)
    assert result["triggered"] is True


def test_handle_take_profit_short_position():
    ctx = ExecutionContext(
        market={"current_odds": 0.45},
        signal={},
        portfolio={
            "current_capital": 10000,
            "peak_capital": 10000,
            "positions": [{"market_id": "mkt-1", "side": "sell", "price": 0.55}],
        },
    )
    node = {"id": "tp3", "type": "take_profit", "data": {"take_profit": 0.15}}
    result = handle_take_profit(node, {}, ctx)
    assert result["triggered"] is True


def test_handle_stop_loss_no_positions():
    ctx = ExecutionContext(
        market={"current_odds": 0.45},
        signal={},
        portfolio={"current_capital": 10000, "peak_capital": 10000, "positions": []},
    )
    node = {"id": "sl4", "type": "stop_loss", "data": {"stop_loss": 0.1}}
    result = handle_stop_loss(node, {}, ctx)
    assert result["triggered"] is False
