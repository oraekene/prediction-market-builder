import pytest
from datetime import datetime, timezone, timedelta
from app.services.withdrawal_engine import WithdrawalEngine


@pytest.fixture
def engine():
    return WithdrawalEngine()


# ── profit_threshold condition ─────────────────────────────────────────


def test_profit_threshold_triggers(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 5000},
            "action": {"type": "withdraw_pct", "pct": 50},
        }
    ]
    portfolio = {"unrealised_profit": 6000, "current_value": 20000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["type"] == "withdraw"
    assert actions[0]["amount"] == 10000
    assert step_states["step-1"]["status"] == "executed"


def test_profit_threshold_does_not_trigger(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 5000},
            "action": {"type": "withdraw_pct", "pct": 50},
        }
    ]
    portfolio = {"unrealised_profit": 3000, "current_value": 20000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0
    assert "step-1" not in step_states


# ── profit_pct condition ───────────────────────────────────────────────


def test_profit_pct_triggers(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_pct", "target_pct": 10},
            "action": {"type": "withdraw_pct", "pct": 25},
        }
    ]
    portfolio = {"profit_pct": 15, "current_value": 20000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["amount"] == 5000


def test_profit_pct_does_not_trigger(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_pct", "target_pct": 20},
            "action": {"type": "withdraw_pct", "pct": 25},
        }
    ]
    portfolio = {"profit_pct": 15, "current_value": 20000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


# ── trailing_stop_fall condition ───────────────────────────────────────


def test_trailing_stop_fall_triggers(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "trailing_stop_fall", "fall_pct": 5},
            "action": {"type": "withdraw_pct", "pct": 100},
        }
    ]
    portfolio = {"peak_value": 20000, "current_value": 18500}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["amount"] == 18500


def test_trailing_stop_fall_does_not_trigger(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "trailing_stop_fall", "fall_pct": 10},
            "action": {"type": "withdraw_pct", "pct": 100},
        }
    ]
    portfolio = {"peak_value": 20000, "current_value": 19000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


def test_trailing_stop_fall_zero_peak(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "trailing_stop_fall", "fall_pct": 5},
            "action": {"type": "withdraw_pct", "pct": 100},
        }
    ]
    portfolio = {"peak_value": 0, "current_value": 0}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


# ── profit_rise condition ──────────────────────────────────────────────


def test_profit_rise_triggers(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_rise", "rise_pct": 10},
            "action": {"type": "withdraw_pct", "pct": 50},
        }
    ]
    portfolio = {
        "baseline_profit": 1000,
        "unrealised_profit": 1500,
        "current_value": 20000,
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["amount"] == 10000


def test_profit_rise_does_not_trigger(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_rise", "rise_pct": 20},
            "action": {"type": "withdraw_pct", "pct": 50},
        }
    ]
    portfolio = {
        "baseline_profit": 1000,
        "unrealised_profit": 1100,
        "current_value": 20000,
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


def test_profit_rise_zero_baseline(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_rise", "rise_pct": 500},
            "action": {"type": "withdraw_pct", "pct": 100},
        }
    ]
    portfolio = {
        "baseline_profit": 0,
        "unrealised_profit": 600,
        "current_value": 20000,
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1


# ── drawdown_from_peak condition ───────────────────────────────────────


def test_drawdown_from_peak_triggers(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "drawdown_from_peak", "max_drawdown_pct": 10},
            "action": {"type": "withdraw_fixed", "amount": 2000},
        }
    ]
    portfolio = {"all_time_peak": 20000, "current_value": 17500}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["amount"] == 2000


def test_drawdown_from_peak_does_not_trigger(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "drawdown_from_peak", "max_drawdown_pct": 15},
            "action": {"type": "withdraw_fixed", "amount": 2000},
        }
    ]
    portfolio = {"all_time_peak": 20000, "current_value": 18000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


def test_drawdown_from_peak_zero_peak(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "drawdown_from_peak", "max_drawdown_pct": 10},
            "action": {"type": "withdraw_fixed", "amount": 1000},
        }
    ]
    portfolio = {"all_time_peak": 0, "current_value": 0}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


# ── combined (AND) condition ───────────────────────────────────────────


def test_combined_and_triggers(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {
                "type": "combined",
                "logic": "and",
                "conditions": [
                    {"type": "profit_threshold", "threshold": 5000},
                    {"type": "profit_pct", "target_pct": 10},
                ],
            },
            "action": {"type": "withdraw_pct", "pct": 25},
        }
    ]
    portfolio = {
        "unrealised_profit": 6000,
        "profit_pct": 15,
        "current_value": 20000,
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1


def test_combined_and_does_not_trigger_one_fails(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {
                "type": "combined",
                "logic": "and",
                "conditions": [
                    {"type": "profit_threshold", "threshold": 5000},
                    {"type": "profit_pct", "target_pct": 20},
                ],
            },
            "action": {"type": "withdraw_pct", "pct": 25},
        }
    ]
    portfolio = {
        "unrealised_profit": 6000,
        "profit_pct": 15,
        "current_value": 20000,
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


def test_combined_and_empty_conditions(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {
                "type": "combined",
                "logic": "and",
                "conditions": [],
            },
            "action": {"type": "withdraw_pct", "pct": 25},
        }
    ]
    portfolio = {"unrealised_profit": 10000, "current_value": 20000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


# ── combined (OR) condition ────────────────────────────────────────────


def test_combined_or_triggers(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {
                "type": "combined",
                "logic": "or",
                "conditions": [
                    {"type": "profit_threshold", "threshold": 5000},
                    {"type": "profit_pct", "target_pct": 50},
                ],
            },
            "action": {"type": "withdraw_pct", "pct": 25},
        }
    ]
    portfolio = {
        "unrealised_profit": 6000,
        "profit_pct": 15,
        "current_value": 20000,
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1


def test_combined_or_does_not_trigger(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {
                "type": "combined",
                "logic": "or",
                "conditions": [
                    {"type": "profit_threshold", "threshold": 5000},
                    {"type": "profit_pct", "target_pct": 50},
                ],
            },
            "action": {"type": "withdraw_pct", "pct": 25},
        }
    ]
    portfolio = {
        "unrealised_profit": 3000,
        "profit_pct": 15,
        "current_value": 20000,
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


# ── withdraw_pct action ────────────────────────────────────────────────


def test_withdraw_pct_action(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_pct", "pct": 30},
        }
    ]
    portfolio = {"unrealised_profit": 1000, "current_value": 25000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["type"] == "withdraw"
    assert actions[0]["pct"] == 30
    assert actions[0]["amount"] == 7500


def test_withdraw_pct_specific_asset(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_pct", "pct": 50, "asset": "ETH"},
        }
    ]
    portfolio = {
        "unrealised_profit": 1000,
        "current_value": 25000,
        "holdings": {"ETH": {"value": 10000}, "BTC": {"value": 5000}},
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["asset"] == "ETH"
    assert actions[0]["amount"] == 5000


# ── withdraw_fixed action ──────────────────────────────────────────────


def test_withdraw_fixed_action(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_fixed", "amount": 3000},
        }
    ]
    portfolio = {"unrealised_profit": 1000, "current_value": 25000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["type"] == "withdraw"
    assert actions[0]["amount"] == 3000
    assert actions[0]["pct"] is None


def test_withdraw_fixed_insufficient_funds(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_fixed", "amount": 50000},
        }
    ]
    portfolio = {"unrealised_profit": 1000, "current_value": 25000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0
    assert step_states["step-1"]["status"] == "executed"


def test_withdraw_fixed_specific_asset(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_fixed", "amount": 2000, "asset": "BTC"},
        }
    ]
    portfolio = {
        "unrealised_profit": 1000,
        "current_value": 25000,
        "holdings": {"BTC": {"value": 8000}},
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["asset"] == "BTC"
    assert actions[0]["amount"] == 2000


def test_withdraw_fixed_insufficient_asset(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_fixed", "amount": 10000, "asset": "ETH"},
        }
    ]
    portfolio = {
        "unrealised_profit": 1000,
        "current_value": 25000,
        "holdings": {"ETH": {"value": 5000}},
    }
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


# ── once flag ──────────────────────────────────────────────────────────


def test_once_flag_prevents_re_execution(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_pct", "pct": 10},
            "once": True,
        }
    ]
    portfolio = {"unrealised_profit": 5000, "current_value": 20000}
    step_states = {}
    actions1 = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions1) == 1
    assert step_states["step-1"]["status"] == "done"
    actions2 = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions2) == 0


def test_once_not_set_allows_re_execution(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_pct", "pct": 10},
            "once": False,
        }
    ]
    portfolio = {"unrealised_profit": 5000, "current_value": 20000}
    step_states = {}
    actions1 = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions1) == 1
    assert step_states["step-1"]["status"] == "executed"
    actions2 = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions2) == 1


# ── cooldown ───────────────────────────────────────────────────────────


def test_cooldown_prevents_immediate_re_execution(engine):
    now = datetime.now(timezone.utc)
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_pct", "pct": 10},
            "cooldown_seconds": 3600,
        }
    ]
    portfolio = {"unrealised_profit": 5000, "current_value": 20000}
    step_states = {
        "step-1": {
            "status": "executed",
            "last_executed_at": now.isoformat(),
        }
    }
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0


def test_cooldown_allows_after_elapsed(engine):
    past = datetime.now(timezone.utc) - timedelta(seconds=7200)
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_pct", "pct": 10},
            "cooldown_seconds": 3600,
        }
    ]
    portfolio = {"unrealised_profit": 5000, "current_value": 20000}
    step_states = {
        "step-1": {
            "status": "executed",
            "last_executed_at": past.isoformat(),
        }
    }
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1


# ── sequential constraint ──────────────────────────────────────────────


def test_sequential_requires_previous_executed(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 99999},
            "action": {"type": "withdraw_pct", "pct": 10},
            "once": True,
        },
        {
            "id": "step-2",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_fixed", "amount": 500},
            "sequential": True,
            "once": True,
        },
    ]
    portfolio = {"unrealised_profit": 5000, "current_value": 20000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0
    assert "step-1" not in step_states
    assert "step-2" not in step_states


def test_sequential_allows_after_previous_done(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_pct", "pct": 10},
            "once": True,
        },
        {
            "id": "step-2",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_fixed", "amount": 500},
            "sequential": True,
            "once": True,
        },
    ]
    portfolio = {"unrealised_profit": 5000, "current_value": 20000}
    step_states = {"step-1": {"status": "done"}}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 1
    assert actions[0]["step_id"] == "step-2"


def test_sequential_blocks_if_previous_not_done(engine):
    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 99999},
            "action": {"type": "withdraw_pct", "pct": 10},
        },
        {
            "id": "step-2",
            "condition": {"type": "profit_threshold", "threshold": 0},
            "action": {"type": "withdraw_fixed", "amount": 500},
            "sequential": True,
        },
    ]
    portfolio = {"unrealised_profit": 5000, "current_value": 20000}
    step_states = {}
    actions = engine.evaluate_withdrawal_strategy(steps, step_states, portfolio)
    assert len(actions) == 0
