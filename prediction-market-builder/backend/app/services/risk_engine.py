from typing import Any


DEFAULT_PROFILE = {
    "max_position_size": 0.2,
    "max_drawdown": 0.15,
    "stop_loss": 0.1,
    "kelly_fraction": 0.25,
    "max_correlation": 0.7,
    "min_confidence": 0.6,
}


def evaluate_risk_template(template, signal: dict[str, Any], portfolio: dict[str, Any]) -> dict[str, Any]:
    result = {"approved": True, "suggested_size": 0.0, "violations": [], "matched_rule": None}

    for rule in template.rules:
        condition = rule.get("condition", {})
        action = rule.get("action", {})
        cond_type = condition.get("type", "always")
        action_type = action.get("type", "approve")

        if cond_type not in CONDITION_EVALUATORS:
            continue

        cond_result = CONDITION_EVALUATORS[cond_type](condition.get("params", {}), signal, portfolio, result["suggested_size"])
        if cond_result:
            if action_type in ACTION_EXECUTORS:
                ACTION_EXECUTORS[action_type](result, action.get("params", {}), signal, portfolio)
            result["matched_rule"] = cond_type
            break

    if result["matched_rule"] is None:
        fallback_evaluate(result, signal, portfolio)

    return result


def fallback_evaluate(result: dict, signal: dict, portfolio: dict) -> None:
    current_drawdown = _calc_drawdown(portfolio)
    confidence = signal.get("confidence", 0.5)
    if current_drawdown >= DEFAULT_PROFILE["max_drawdown"]:
        result["approved"] = False
        result["violations"].append("max_drawdown_reached")
    if confidence < DEFAULT_PROFILE["min_confidence"]:
        result["approved"] = False
        result["violations"].append("low_confidence")
    if result["approved"]:
        suggested = _kelly_size(signal, DEFAULT_PROFILE["kelly_fraction"])
        result["suggested_size"] = round(min(suggested, DEFAULT_PROFILE["max_position_size"]), 4)
    result["matched_rule"] = "default_profile"


def _calc_drawdown(portfolio: dict) -> float:
    peak = portfolio.get("peak_capital", portfolio.get("current_capital", 10000))
    current = portfolio.get("current_capital", 10000)
    if peak <= 0:
        return 0
    return (peak - current) / peak


def _kelly_size(signal: dict, kelly_fraction: float) -> float:
    probability = signal.get("probability", 0.5)
    odds = signal.get("market_odds", 0.5)
    if odds <= 0:
        return 0
    b = (1 - odds) / odds
    p = probability
    q = 1 - p
    if b <= 0:
        return 0
    kelly = (p * b - q) / b
    return max(0, kelly * kelly_fraction)


def evaluate_rule(condition: dict, signal: dict, portfolio: dict, suggested_size: float = 0.0) -> bool:
    cond_type = condition.get("type", "always")
    params = condition.get("params", {})
    if cond_type in CONDITION_EVALUATORS:
        return CONDITION_EVALUATORS[cond_type](params, signal, portfolio, suggested_size)
    return False


def _cond_max_drawdown(params: dict, signal: dict, portfolio: dict, size: float) -> bool:
    return _calc_drawdown(portfolio) >= params.get("threshold", 0.15)


def _cond_min_confidence(params: dict, signal: dict, portfolio: dict, size: float) -> bool:
    return signal.get("confidence", 0) < params.get("min_confidence", 0.5)


def _cond_max_position_size(params: dict, signal: dict, portfolio: dict, suggested_size: float) -> bool:
    return suggested_size > params.get("max_size", 0.2)


def _cond_always(params: dict, signal: dict, portfolio: dict, size: float) -> bool:
    return True


CONDITION_EVALUATORS = {
    "max_drawdown": _cond_max_drawdown,
    "min_confidence": _cond_min_confidence,
    "max_position_size": _cond_max_position_size,
    "always": _cond_always,
}


def _act_reject(result: dict, params: dict, signal: dict, portfolio: dict) -> None:
    result["approved"] = False
    result["suggested_size"] = 0.0
    result["violations"].append("rule_rejected")


def _act_approve(result: dict, params: dict, signal: dict, portfolio: dict) -> None:
    result["approved"] = True
    if "rule_rejected" in result["violations"]:
        result["violations"].remove("rule_rejected")
    result["violations"].append("rule_approved")


def _act_scale_position(result: dict, params: dict, signal: dict, portfolio: dict) -> None:
    factor = params.get("factor", 1.0)
    current = result.get("suggested_size", 0.0)
    if current == 0.0:
        current = _kelly_size(signal, DEFAULT_PROFILE["kelly_fraction"])
    result["suggested_size"] = round(current * factor, 4)


def _act_fixed_fraction(result: dict, params: dict, signal: dict, portfolio: dict) -> None:
    result["suggested_size"] = params.get("fraction", 0.01)


ACTION_EXECUTORS = {
    "reject": _act_reject,
    "approve": _act_approve,
    "scale_position": _act_scale_position,
    "fixed_fraction": _act_fixed_fraction,
}
