import pytest
from app.services.risk_engine import evaluate_risk_template, evaluate_rule, CONDITION_EVALUATORS, ACTION_EXECUTORS


def test_max_drawdown_condition_triggers():
    condition = {"type": "max_drawdown", "params": {"threshold": 0.1}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 8000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is True


def test_max_drawdown_condition_does_not_trigger():
    condition = {"type": "max_drawdown", "params": {"threshold": 0.1}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 9500, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is False


def test_min_confidence_condition_triggers():
    condition = {"type": "min_confidence", "params": {"min_confidence": 0.5}}
    signal = {"probability": 0.7, "confidence": 0.3, "market_odds": 0.55}
    portfolio = {"current_capital": 10000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is True


def test_min_confidence_does_not_trigger():
    condition = {"type": "min_confidence", "params": {"min_confidence": 0.5}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 10000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio) is False


def test_max_position_size_triggers():
    condition = {"type": "max_position_size", "params": {"max_size": 0.1}}
    signal = {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55}
    portfolio = {"current_capital": 10000, "peak_capital": 10000}
    assert evaluate_rule(condition, signal, portfolio, suggested_size=0.15) is True


def test_always_condition():
    condition = {"type": "always", "params": {}}
    signal = {}
    portfolio = {}
    assert evaluate_rule(condition, signal, portfolio) is True


def test_reject_action():
    result = {"approved": True, "suggested_size": 0.1, "violations": []}
    params = {}
    ACTION_EXECUTORS["reject"](result, params, signal={}, portfolio={})
    assert result["approved"] is False
    assert "rule_rejected" in result["violations"]


def test_approve_action():
    result = {"approved": False, "suggested_size": 0.0, "violations": ["rule_rejected"]}
    params = {}
    ACTION_EXECUTORS["approve"](result, params, signal={}, portfolio={})
    assert result["approved"] is True
    assert "rule_approved" in result["violations"]
    assert "rule_rejected" not in result["violations"]


def test_scale_position_action():
    result = {"approved": True, "suggested_size": 0.2, "violations": []}
    params = {"factor": 0.5}
    ACTION_EXECUTORS["scale_position"](result, params, signal={"probability": 0.5, "market_odds": 0.5}, portfolio={})
    assert result["suggested_size"] == 0.1


def test_fixed_fraction_action():
    result = {"approved": True, "suggested_size": 0.0, "violations": []}
    params = {"fraction": 0.02}
    ACTION_EXECUTORS["fixed_fraction"](result, params, signal={}, portfolio={"current_capital": 10000})
    assert result["suggested_size"] == 0.02


def test_evaluate_risk_template_full_pipeline():
    from dataclasses import dataclass

    @dataclass
    class FakeTemplate:
        rules = [
            {"condition": {"type": "max_drawdown", "params": {"threshold": 0.15}}, "action": {"type": "reject", "params": {}}},
            {"condition": {"type": "always", "params": {}}, "action": {"type": "approve", "params": {}}},
        ]

    result = evaluate_risk_template(
        FakeTemplate(),
        signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 8000, "peak_capital": 10000},
    )
    assert result["approved"] is False
    assert "max_drawdown" in result["matched_rule"]


def test_evaluate_risk_template_falls_back_to_default():
    from dataclasses import dataclass

    @dataclass
    class FakeTemplate:
        rules = []

    result = evaluate_risk_template(
        FakeTemplate(),
        signal={"probability": 0.5, "confidence": 0.3, "market_odds": 0.5},
        portfolio={"current_capital": 10000, "peak_capital": 10000},
    )
    assert result["approved"] is False
