import pytest
from app.services.node_executor import ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.action_node_handlers import (
    handle_close_position,
    handle_close_position_on_take_profit,
    handle_withdraw_to_safe_wallet,
    handle_convert_to_stablecoin,
    handle_withdrawal_strategy,
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


# ── handle_close_position ──────────────────────────────────────────────


def test_handle_close_position_with_positions():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "positions": [
                {"market_id": "mkt-1", "side": "buy", "price": 0.55, "size": 200},
                {"market_id": "mkt-2", "side": "sell", "price": 0.60, "size": 150},
            ],
        },
    )
    node = {"id": "cp1", "type": "close_position", "data": {"close_pct": 100}}
    result = handle_close_position(node, {}, ctx)
    assert result["action"] == "close_position"
    assert result["close_pct"] == 100
    assert result["approved"] is True
    assert len(result["orders_placed"]) == 2
    assert result["orders_placed"][0]["side"] == "sell"
    assert result["orders_placed"][0]["amount"] == 200
    assert result["orders_placed"][1]["side"] == "buy"
    assert result["orders_placed"][1]["amount"] == 150


def test_handle_close_position_with_partial_pct():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "positions": [
                {"market_id": "mkt-1", "side": "buy", "price": 0.55, "size": 200},
            ],
        },
    )
    node = {"id": "cp2", "type": "close_position", "data": {"close_pct": 50}}
    result = handle_close_position(node, {}, ctx)
    assert result["close_pct"] == 50
    assert len(result["orders_placed"]) == 1
    assert result["orders_placed"][0]["amount"] == 100


def test_handle_close_position_target_market():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "positions": [
                {"market_id": "mkt-1", "side": "buy", "price": 0.55, "size": 200},
                {"market_id": "mkt-2", "side": "buy", "price": 0.60, "size": 150},
            ],
        },
    )
    node = {
        "id": "cp3",
        "type": "close_position",
        "data": {"close_pct": 100, "market_id": "mkt-1"},
    }
    result = handle_close_position(node, {}, ctx)
    assert len(result["orders_placed"]) == 1
    assert result["orders_placed"][0]["market_id"] == "mkt-1"


def test_handle_close_position_no_positions():
    ctx = ExecutionContext(
        portfolio={"current_capital": 10000, "positions": []},
    )
    node = {"id": "cp4", "type": "close_position", "data": {"close_pct": 100}}
    result = handle_close_position(node, {}, ctx)
    assert result["action"] == "close_position"
    assert result["orders_placed"] == []


# ── handle_close_position_on_take_profit ───────────────────────────────


def test_handle_close_position_on_take_profit_triggered_auto_execute():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "positions": [
                {"market_id": "mkt-1", "side": "buy", "price": 0.55, "size": 200},
            ],
        },
    )
    node = {
        "id": "cpt1",
        "type": "close_position_on_take_profit",
        "data": {"auto_execute": True},
    }
    inputs = {"tp": {"triggered": True, "profit": 0.2}}
    result = handle_close_position_on_take_profit(node, inputs, ctx)
    assert result["executed"] is True
    assert result["approved"] is True
    assert len(result["orders_placed"]) == 1


def test_handle_close_position_on_take_profit_triggered_auto_execute_disabled():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "positions": [
                {"market_id": "mkt-1", "side": "buy", "price": 0.55, "size": 200},
            ],
        },
    )
    node = {
        "id": "cpt2",
        "type": "close_position_on_take_profit",
        "data": {"auto_execute": False},
    }
    inputs = {"tp": {"triggered": True, "profit": 0.2}}
    result = handle_close_position_on_take_profit(node, inputs, ctx)
    assert result["executed"] is False
    assert result["reason"] == "auto_execute_disabled"


def test_handle_close_position_on_take_profit_not_triggered():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "positions": [
                {"market_id": "mkt-1", "side": "buy", "price": 0.55, "size": 200},
            ],
        },
    )
    node = {
        "id": "cpt3",
        "type": "close_position_on_take_profit",
        "data": {"auto_execute": True},
    }
    inputs = {"tp": {"triggered": False}}
    result = handle_close_position_on_take_profit(node, inputs, ctx)
    assert result["executed"] is False
    assert result["reason"] == "no_trigger"


def test_handle_close_position_on_take_profit_no_inputs():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55, "size": 200}],
        },
    )
    node = {
        "id": "cpt4",
        "type": "close_position_on_take_profit",
        "data": {"auto_execute": True},
    }
    result = handle_close_position_on_take_profit(node, {}, ctx)
    assert result["executed"] is False
    assert result["reason"] == "no_trigger"


# ── handle_withdraw_to_safe_wallet ─────────────────────────────────────


def test_handle_withdraw_to_safe_wallet_from_profits():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 15000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "ws1",
        "type": "withdraw_to_safe_wallet",
        "data": {"withdraw_pct": 50, "source": "profits"},
    }
    result = handle_withdraw_to_safe_wallet(node, {}, ctx)
    assert result["action"] == "withdraw"
    assert result["source"] == "profits"
    assert result["amount"] == 2500
    assert result["approved"] is True


def test_handle_withdraw_to_safe_wallet_from_profits_no_profits():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 8000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "ws2",
        "type": "withdraw_to_safe_wallet",
        "data": {"withdraw_pct": 50, "source": "profits"},
    }
    result = handle_withdraw_to_safe_wallet(node, {}, ctx)
    assert result["amount"] == 0


def test_handle_withdraw_to_safe_wallet_from_capital():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 15000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "ws3",
        "type": "withdraw_to_safe_wallet",
        "data": {"withdraw_pct": 20, "source": "capital"},
    }
    result = handle_withdraw_to_safe_wallet(node, {}, ctx)
    assert result["source"] == "capital"
    assert result["amount"] == 3000


def test_handle_withdraw_to_safe_wallet_custom_wallet():
    ctx = ExecutionContext(
        portfolio={"current_capital": 15000, "initial_capital": 10000},
    )
    node = {
        "id": "ws4",
        "type": "withdraw_to_safe_wallet",
        "data": {
            "withdraw_pct": 100,
            "source": "profits",
            "safe_wallet_id": "cold-storage-1",
            "target_currency": "USDT",
        },
    }
    result = handle_withdraw_to_safe_wallet(node, {}, ctx)
    assert result["safe_wallet_id"] == "cold-storage-1"
    assert result["currency"] == "USDT"
    assert result["amount"] == 5000


# ── handle_convert_to_stablecoin ───────────────────────────────────────


def test_handle_convert_to_stablecoin_basic():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 15000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "cs1",
        "type": "convert_to_stablecoin",
        "data": {"target_stablecoin": "USDC", "convert_pct": 100},
    }
    result = handle_convert_to_stablecoin(node, {}, ctx)
    assert result["action"] == "convert"
    assert result["amount"] == 5000
    assert result["stablecoin"] == "USDC"
    assert result["approved"] is True


def test_handle_convert_to_stablecoin_partial():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 20000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "cs2",
        "type": "convert_to_stablecoin",
        "data": {"target_stablecoin": "DAI", "convert_pct": 30},
    }
    result = handle_convert_to_stablecoin(node, {}, ctx)
    assert result["amount"] == 3000
    assert result["stablecoin"] == "DAI"


def test_handle_convert_to_stablecoin_no_profits():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "cs3",
        "type": "convert_to_stablecoin",
        "data": {"target_stablecoin": "USDC", "convert_pct": 100},
    }
    result = handle_convert_to_stablecoin(node, {}, ctx)
    assert result["amount"] == 0


# ── handle_withdrawal_strategy ─────────────────────────────────────────


def test_handle_withdrawal_strategy_profit_threshold():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 15000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "ws1",
        "type": "withdrawal_strategy",
        "data": {
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "profit_threshold", "amount": 4000},
                    "action": {"type": "withdraw_pct", "pct": 50},
                    "once": True,
                }
            ]
        },
    }
    result = handle_withdrawal_strategy(node, {}, ctx)
    assert result["action"] == "withdrawal_strategy"
    assert result["approved"] is True
    assert len(result["actions"]) == 1
    assert result["actions"][0]["amount"] == 2500


def test_handle_withdrawal_strategy_profit_threshold_not_met():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 12000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "ws2",
        "type": "withdrawal_strategy",
        "data": {
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "profit_threshold", "amount": 5000},
                    "action": {"type": "withdraw_pct", "pct": 50},
                }
            ]
        },
    }
    result = handle_withdrawal_strategy(node, {}, ctx)
    assert len(result["actions"]) == 0


def test_handle_withdrawal_strategy_profit_pct():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 13000,
            "initial_capital": 10000,
        },
    )
    node = {
        "id": "ws3",
        "type": "withdrawal_strategy",
        "data": {
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "profit_pct", "pct": 0.2},
                    "action": {"type": "withdraw_fixed", "amount": 1000},
                }
            ]
        },
    }
    result = handle_withdrawal_strategy(node, {}, ctx)
    assert len(result["actions"]) == 1
    assert result["actions"][0]["amount"] == 1000


def test_handle_withdrawal_strategy_drawdown_from_peak():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 9000,
            "initial_capital": 10000,
            "peak_capital": 11000,
        },
    )
    node = {
        "id": "ws4",
        "type": "withdrawal_strategy",
        "data": {
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "drawdown_from_peak", "pct": 10},
                    "action": {"type": "withdraw_fixed", "amount": 500},
                }
            ]
        },
    }
    result = handle_withdrawal_strategy(node, {}, ctx)
    assert len(result["actions"]) == 1
    assert result["actions"][0]["amount"] == 500


def test_handle_withdrawal_strategy_drawdown_not_triggered():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 10500,
            "initial_capital": 10000,
            "peak_capital": 11000,
        },
    )
    node = {
        "id": "ws5",
        "type": "withdrawal_strategy",
        "data": {
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "drawdown_from_peak", "pct": 10},
                    "action": {"type": "withdraw_fixed", "amount": 500},
                }
            ]
        },
    }
    result = handle_withdrawal_strategy(node, {}, ctx)
    assert len(result["actions"]) == 0


def test_handle_withdrawal_strategy_once_flag():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 15000,
            "initial_capital": 10000,
        },
        withdrawal_state={"step-1": {"status": "executed"}},
    )
    node = {
        "id": "ws6",
        "type": "withdrawal_strategy",
        "data": {
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "profit_threshold", "amount": 4000},
                    "action": {"type": "withdraw_pct", "pct": 50},
                    "once": True,
                }
            ]
        },
    }
    result = handle_withdrawal_strategy(node, {}, ctx)
    assert len(result["actions"]) == 0


def test_handle_withdrawal_strategy_sequential_steps():
    ctx = ExecutionContext(
        portfolio={
            "current_capital": 15000,
            "initial_capital": 10000,
        },
        withdrawal_state={"step-1": {"status": "executed"}},
    )
    node = {
        "id": "ws7",
        "type": "withdrawal_strategy",
        "data": {
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "profit_threshold", "amount": 4000},
                    "action": {"type": "withdraw_pct", "pct": 25},
                    "once": True,
                },
                {
                    "id": "step-2",
                    "condition": {"type": "profit_threshold", "amount": 4000},
                    "action": {"type": "withdraw_fixed", "amount": 1000},
                    "once": True,
                },
            ]
        },
    }
    result = handle_withdrawal_strategy(node, {}, ctx)
    assert len(result["actions"]) == 1
    assert result["actions"][0]["step_id"] == "step-2"
    assert result["steps_evaluated"] == 2
