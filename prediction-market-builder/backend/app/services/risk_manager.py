from typing import Any
from dataclasses import dataclass, field
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_node_handlers import register_risk_handlers

_RISK_REGISTRY: NodeRegistry | None = None
CONDITION_EVALUATORS = {}
ACTION_EXECUTORS = {}


def _get_risk_registry() -> NodeRegistry:
    global _RISK_REGISTRY
    if _RISK_REGISTRY is None:
        _RISK_REGISTRY = NodeRegistry()
        register_risk_handlers(_RISK_REGISTRY)
    return _RISK_REGISTRY


def register_condition(name: str):
    def decorator(fn):
        CONDITION_EVALUATORS[name] = fn
        return fn
    return decorator


def register_action(name: str):
    def decorator(fn):
        ACTION_EXECUTORS[name] = fn
        return fn
    return decorator


@register_condition("max_drawdown")
def _cond_drawdown(params: dict, signal: dict, portfolio: dict, _size: float) -> bool:
    peak = portfolio.get("peak_capital", portfolio.get("current_capital", 10000))
    current = portfolio.get("current_capital", 10000)
    if peak <= 0:
        return False
    drawdown = (peak - current) / peak
    return drawdown >= params.get("threshold", 0.15)


@register_condition("min_confidence")
def _cond_confidence(params: dict, signal: dict, _portfolio: dict, _size: float) -> bool:
    return signal.get("confidence", 0) < params.get("min_confidence", 0.5)


@register_condition("max_position_size")
def _cond_position_size(params: dict, _signal: dict, _portfolio: dict, suggested_size: float) -> bool:
    return suggested_size > params.get("max_size", 0.2)


@register_condition("always")
def _cond_always(_params: dict, _signal: dict, _portfolio: dict, _size: float) -> bool:
    return True


@register_action("reject")
def _act_reject(result: dict, _params: dict, _signal: dict, _portfolio: dict) -> None:
    result["approved"] = False
    result["suggested_size"] = 0.0
    result["violations"].append("rule_rejected")


@register_action("approve")
def _act_approve(result: dict, _params: dict, _signal: dict, _portfolio: dict) -> None:
    result["approved"] = True
    if "rule_rejected" in result["violations"]:
        result["violations"].remove("rule_rejected")
    result["violations"].append("rule_approved")


@register_action("scale_position")
def _act_scale(result: dict, params: dict, signal: dict, _portfolio: dict) -> None:
    factor = params.get("factor", 1.0)
    current = result.get("suggested_size", 0.0)
    if current == 0.0:
        current = _kelly_size(signal, 0.25)
    result["suggested_size"] = round(current * factor, 4)


@register_action("fixed_fraction")
def _act_fixed(result: dict, params: dict, _signal: dict, _portfolio: dict) -> None:
    result["suggested_size"] = params.get("fraction", 0.01)


def evaluate_rules(rules: list, signal: dict, portfolio: dict) -> dict[str, Any]:
    result = {"approved": True, "suggested_size": 0.0, "violations": [], "matched_rule": None}
    for rule in rules:
        condition = rule.get("condition", {})
        action = rule.get("action", {})
        cond_type = condition.get("type", "always")
        action_type = action.get("type", "approve")
        if cond_type not in CONDITION_EVALUATORS:
            continue
        cond_result = CONDITION_EVALUATORS[cond_type](
            condition.get("params", {}), signal, portfolio, result["suggested_size"]
        )
        if cond_result:
            if action_type in ACTION_EXECUTORS:
                ACTION_EXECUTORS[action_type](result, action.get("params", {}), signal, portfolio)
            result["matched_rule"] = cond_type
            break
    return result


@dataclass
class RiskProfile:
    max_position_size: float = 0.2
    max_drawdown: float = 0.15
    stop_loss: float = 0.1
    kelly_fraction: float = 0.25
    max_correlation: float = 0.7
    min_confidence: float = 0.6
    rules: list = field(default_factory=list)


class RiskManager:
    def __init__(self, profile: RiskProfile | None = None):
        self.profile = profile or RiskProfile()
        self.executor = GraphExecutor(_get_risk_registry())
        self.risk_calc = RiskCalculator()
        self.portfolio_mgr = PortfolioManager()

    def evaluate_trade(self, market: dict[str, Any], signal: dict[str, Any],
                       portfolio: dict[str, Any]) -> dict[str, Any]:
        if self.profile.rules:
            nodes = self._rules_to_graph(self.profile.rules)
            if nodes:
                ctx = ExecutionContext(
                    signal=signal,
                    portfolio=portfolio,
                    market=market,
                )
                result = self.executor.execute(nodes, [], ctx)
                if isinstance(result, dict) and result.get("triggered"):
                    return {
                        "approved": False,
                        "suggested_size": result.get("suggested_size", 0.0),
                        "violations": [result.get("reason", "rule_rejected")],
                        "matched_rule": result.get("node_type"),
                    }
            result = evaluate_rules(self.profile.rules, signal, portfolio)
            if result["matched_rule"] is not None:
                return result
        return self._fallback_evaluate(signal, portfolio)

    CONDITIONS_TO_NODES = {
        "max_drawdown": "drawdown_monitor",
        "min_confidence": "var_check",
        "max_position_size": "position_sizer",
        "always": None,
    }

    ACTIONS_TO_NODES = {
        "reject": "alert",
        "approve": "alert",
        "scale_position": "position_sizer",
        "fixed_fraction": "position_sizer",
    }

    def _rules_to_graph(self, rules: list[dict]) -> list[dict]:
        nodes = []
        for i, rule in enumerate(rules):
            condition = rule.get("condition", {})
            action = rule.get("action", {})
            cond_type = condition.get("type", "always")
            action_type = action.get("type", "approve")
            cond_params = condition.get("params", {})
            action_params = action.get("params", {})

            node_type = self.CONDITIONS_TO_NODES.get(cond_type)
            if node_type is None and cond_type == "always":
                pass
            elif node_type:
                params = dict(cond_params)
                if cond_type == "max_position_size":
                    params["mode"] = "fixed"
                    params["max_size"] = cond_params.get("max_size", 0.2)
                elif cond_type == "max_drawdown":
                    params["threshold"] = cond_params.get("threshold", 0.15)
                nodes.append({
                    "id": f"rule_{i}_cond",
                    "type": node_type,
                    "params": params,
                })

            act_node = self.ACTIONS_TO_NODES.get(action_type)
            if act_node:
                params = dict(action_params)
                if action_type == "reject":
                    params["message"] = f"rule {cond_type} rejected"
                elif action_type == "approve":
                    params["message"] = f"rule {cond_type} approved"
                elif action_type == "scale_position":
                    params["mode"] = "kelly"
                    params["factor"] = action_params.get("factor", 1.0)
                elif action_type == "fixed_fraction":
                    params["mode"] = "fixed"
                    params["fraction"] = action_params.get("fraction", 0.01)
                nodes.append({
                    "id": f"rule_{i}_action",
                    "type": act_node,
                    "params": params,
                })
        return nodes

    def _fallback_evaluate(self, signal: dict, portfolio: dict) -> dict:
        max_size = self._calculate_kelly_criterion(signal)
        constrained_size = min(max_size, self.profile.max_position_size)
        current_drawdown = self._calculate_drawdown(portfolio)
        confidence = signal.get("confidence", 0.5)
        violations = []
        if constrained_size <= 0:
            violations.append("no_edge")
        if current_drawdown >= self.profile.max_drawdown:
            violations.append("max_drawdown_reached")
        if confidence < self.profile.min_confidence:
            violations.append("low_confidence")
        approved = len(violations) == 0
        return {
            "approved": approved,
            "suggested_size": round(constrained_size, 4),
            "kelly_fraction": self.profile.kelly_fraction,
            "violations": violations,
            "max_drawdown": current_drawdown,
            "confidence": confidence,
        }

    def _calculate_kelly_criterion(self, signal: dict[str, Any]) -> float:
        probability = signal.get("probability", 0.5)
        odds = signal.get("market_odds", 0.5)
        b = (1 - odds) / odds if odds > 0 else 0
        p = probability
        q = 1 - p
        if b <= 0:
            return 0
        kelly = (p * b - q) / b
        return max(0, kelly * self.profile.kelly_fraction)

    def monitor_positions(self, portfolio: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
        positions = portfolio.get("positions", [])
        alerts = []
        for pos in positions:
            position_market = dict(market)
            position_market["side"] = pos.get("side", "buy")
            position_market["entry_price"] = pos.get("price", market.get("current_odds", 0.5))
            position_market["current_odds"] = market.get("current_odds", 0.5)
            ctx = ExecutionContext(
                signal={},
                portfolio=portfolio,
                market=position_market,
            )
            sl_node = {"id": "stop_loss_check", "type": "stop_loss", "data": {"stop_loss": self.profile.stop_loss}}
            tp_node = {"id": "take_profit_check", "type": "take_profit", "data": {"take_profit": 0.2}}
            sl_result = self.executor.execute([sl_node], [], ctx)
            tp_result = self.executor.execute([tp_node], [], ctx)
            if sl_result and sl_result.get("triggered"):
                alerts.append({
                    "type": "stop_loss",
                    "market_id": pos.get("market_id"),
                    "side": pos.get("side"),
                    "loss_pct": sl_result["positions"][0]["loss_pct"] if sl_result.get("positions") else 0,
                })
            if tp_result and tp_result.get("triggered"):
                alerts.append({
                    "type": "take_profit",
                    "market_id": pos.get("market_id"),
                    "side": pos.get("side"),
                    "gain_pct": tp_result["positions"][0]["gain_pct"] if tp_result.get("positions") else 0,
                })
        return {"alerts": alerts, "alert_count": len(alerts)}

    def _calculate_drawdown(self, portfolio: dict[str, Any]) -> float:
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
