import pytest
from app.services.risk_manager import RiskManager, RiskProfile


def test_risk_approves_good_signal():
    mgr = RiskManager(RiskProfile(min_confidence=0.5))
    result = mgr.evaluate_trade(
        market={"current_odds": 0.55},
        signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 10000, "peak_capital": 10000},
    )
    assert result["approved"] is True
    assert result["suggested_size"] > 0


def test_risk_rejects_low_confidence():
    mgr = RiskManager(RiskProfile(min_confidence=0.6))
    result = mgr.evaluate_trade(
        market={"current_odds": 0.55},
        signal={"probability": 0.7, "confidence": 0.3, "market_odds": 0.55},
        portfolio={"current_capital": 10000, "peak_capital": 10000},
    )
    assert result["approved"] is False
    assert "low_confidence" in result["violations"]


def test_risk_rejects_max_drawdown():
    mgr = RiskManager(RiskProfile(max_drawdown=0.1))
    result = mgr.evaluate_trade(
        market={"current_odds": 0.55},
        signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 8000, "peak_capital": 10000},
    )
    assert result["approved"] is False
    assert "max_drawdown_reached" in result["violations"]


def test_evaluate_rules_none_returns_default_approved():
    result = RiskManager(RiskProfile(rules=[], min_confidence=0.3)).evaluate_trade(
        market={}, signal={"probability": 0.6, "confidence": 0.8, "market_odds": 0.55}, portfolio={}
    )
    assert result["approved"] is True


def test_max_drawdown_condition_triggers():
    rules = [
        {"condition": {"type": "max_drawdown", "params": {"threshold": 0.1}}, "action": {"type": "reject"}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 8000, "peak_capital": 10000}
    )
    assert result["approved"] is False
    assert "rule_rejected" in result["violations"]


def test_max_drawdown_condition_does_not_trigger():
    rules = [
        {"condition": {"type": "max_drawdown", "params": {"threshold": 0.3}}, "action": {"type": "reject"}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        portfolio={"current_capital": 9000, "peak_capital": 10000}
    )
    assert result["approved"] is True


def test_min_confidence_condition_triggers():
    rules = [
        {"condition": {"type": "min_confidence", "params": {"min_confidence": 0.7}}, "action": {"type": "reject"}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"confidence": 0.3, "probability": 0.6, "market_odds": 0.5}, portfolio={}
    )
    assert result["approved"] is False


def test_max_position_size_condition_triggers():
    rules = [
        {"condition": {"type": "max_position_size", "params": {"max_size": 0.1}}, "action": {"type": "reject"}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.6, "confidence": 0.8, "market_odds": 0.5}, portfolio={}
    )
    assert result["approved"] is True


def test_always_condition_triggers_reject():
    rules = [
        {"condition": {"type": "always", "params": {}}, "action": {"type": "reject"}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.9, "confidence": 0.9, "market_odds": 0.5}, portfolio={}
    )
    assert result["approved"] is False


def test_approve_action_overrides_reject():
    rules = [
        {"condition": {"type": "always", "params": {}}, "action": {"type": "approve"}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.6, "market_odds": 0.5},
        portfolio={"current_capital": 8000, "peak_capital": 10000}
    )
    assert result["approved"] is True
    assert "rule_approved" in result["violations"]


def test_scale_position_action():
    rules = [
        {"condition": {"type": "always", "params": {}}, "action": {"type": "scale_position", "params": {"factor": 0.5}}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.8, "market_odds": 0.55}, portfolio={}
    )
    assert result["suggested_size"] > 0


def test_fixed_fraction_action():
    rules = [
        {"condition": {"type": "always", "params": {}}, "action": {"type": "fixed_fraction", "params": {"fraction": 0.05}}}
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.7, "market_odds": 0.5}, portfolio={}
    )
    assert result["suggested_size"] == 0.05


def test_first_matching_rule_wins():
    rules = [
        {"condition": {"type": "always", "params": {}}, "action": {"type": "reject"}},
        {"condition": {"type": "always", "params": {}}, "action": {"type": "approve"}},
    ]
    result = RiskManager(RiskProfile(rules=rules)).evaluate_trade(
        market={}, signal={"probability": 0.6, "market_odds": 0.5}, portfolio={}
    )
    assert result["approved"] is False
    assert result["matched_rule"] == "always"


def test_monitor_positions_stop_loss_triggers():
    mgr = RiskManager(RiskProfile(stop_loss=0.1))
    portfolio = {
        "current_capital": 10000,
        "peak_capital": 10000,
        "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55}],
    }
    market = {"current_odds": 0.45}
    result = mgr.monitor_positions(portfolio, market)
    assert result["alert_count"] > 0
    assert any(a["type"] == "stop_loss" for a in result["alerts"])


def test_monitor_positions_take_profit_triggers():
    mgr = RiskManager(RiskProfile(stop_loss=0.1))
    portfolio = {
        "current_capital": 10000,
        "peak_capital": 10000,
        "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55}],
    }
    market = {"current_odds": 0.68}
    result = mgr.monitor_positions(portfolio, market)
    assert result["alert_count"] > 0
    assert any(a["type"] == "take_profit" for a in result["alerts"])


def test_monitor_positions_no_alerts():
    mgr = RiskManager(RiskProfile(stop_loss=0.1))
    portfolio = {
        "current_capital": 10000,
        "peak_capital": 10000,
        "positions": [{"market_id": "mkt-1", "side": "buy", "price": 0.55}],
    }
    market = {"current_odds": 0.55}
    result = mgr.monitor_positions(portfolio, market)
    assert result["alert_count"] == 0


def test_monitor_positions_empty_positions():
    mgr = RiskManager(RiskProfile(stop_loss=0.1))
    portfolio = {"current_capital": 10000, "peak_capital": 10000, "positions": []}
    market = {"current_odds": 0.45}
    result = mgr.monitor_positions(portfolio, market)
    assert result["alert_count"] == 0


def test_no_rule_match_uses_fallback_profile():
    mgr = RiskManager(RiskProfile(min_confidence=0.6))
    result = mgr.evaluate_trade(
        market={"current_odds": 0.55},
        signal={"probability": 0.7, "confidence": 0.3, "market_odds": 0.55},
        portfolio={"current_capital": 10000, "peak_capital": 10000},
    )
    assert result["approved"] is False
    assert "low_confidence" in result["violations"]
