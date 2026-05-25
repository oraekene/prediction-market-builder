from typing import Any
from dataclasses import dataclass, field
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_node_handlers import register_risk_handlers

_RISK_REGISTRY: NodeRegistry | None = None


def _get_risk_registry() -> NodeRegistry:
    global _RISK_REGISTRY
    if _RISK_REGISTRY is None:
        _RISK_REGISTRY = NodeRegistry()
        register_risk_handlers(_RISK_REGISTRY)
    return _RISK_REGISTRY


_CONDITION_NODE_MAP = {
    "max_drawdown": "drawdown_monitor",
    "min_confidence": "min_confidence",
    "max_position_size": "position_size_check",
    "always": "always",
}

_ACTION_NODE_MAP = {
    "reject": "reject_action",
    "approve": "approve_action",
    "scale_position": "position_sizer",
    "fixed_fraction": "position_sizer",
}


def _condition_to_node(cond_type: str, cond_params: dict) -> dict | None:
    node_type = _CONDITION_NODE_MAP.get(cond_type)
    if node_type is None:
        return None
    data = {}
    if cond_type == "max_drawdown":
        data["max_drawdown"] = cond_params.get("threshold", 0.15)
    elif cond_type == "min_confidence":
        data["min_confidence"] = cond_params.get("min_confidence", 0.5)
    elif cond_type == "max_position_size":
        data["max_size"] = cond_params.get("max_size", 0.2)
    else:
        data = dict(cond_params)
    return {"id": f"cond_{cond_type}", "type": node_type, "data": data}


def _action_to_node(action_type: str, action_params: dict, cond_type: str) -> dict:
    node_type = _ACTION_NODE_MAP.get(action_type, "approve_action")
    data = {}
    if action_type == "reject":
        data["message"] = f"rule {cond_type} rejected"
        data["severity"] = "error"
    elif action_type == "approve":
        data["message"] = f"rule {cond_type} approved"
        data["severity"] = "info"
    elif action_type == "scale_position":
        data["method"] = "kelly"
        data["factor"] = action_params.get("factor", 1.0)
    elif action_type == "fixed_fraction":
        data["method"] = "fixed"
        data["fraction"] = action_params.get("fraction", 0.01)
    else:
        data = dict(action_params)
    return {"id": f"act_{action_type}", "type": node_type, "data": data}


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

    async def evaluate_trade(self, market: dict[str, Any], signal: dict[str, Any],
                              portfolio: dict[str, Any]) -> dict[str, Any]:
        if self.profile.rules:
            ctx = ExecutionContext(
                signal=signal,
                portfolio=portfolio,
                market=market,
                risk_calculator=self.risk_calc,
                portfolio_manager=self.portfolio_mgr,
            )
            for rule in self.profile.rules:
                condition = rule.get("condition", {})
                action = rule.get("action", {})
                cond_type = condition.get("type", "always")
                cond_params = condition.get("params", {})
                action_type = action.get("type", "approve")
                action_params = action.get("params", {})

                cond_node = _condition_to_node(cond_type, cond_params)
                if cond_node is None:
                    continue

                cond_result = await self.executor.execute([cond_node], [], ctx)
                if cond_result.get("triggered"):
                    act_node = _action_to_node(action_type, action_params, cond_type)
                    act_result = await self.executor.execute([act_node], [], ctx)
                    return {
                        "approved": act_result.get("approved", False),
                        "suggested_size": act_result.get("suggested_size", 0.0),
                        "violations": act_result.get("violations", ["rule_rejected"]),
                        "matched_rule": cond_type,
                    }
        return self._fallback_evaluate(signal, portfolio)

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

    async def monitor_positions(self, portfolio: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
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
            sl_result = await self.executor.execute([sl_node], [], ctx)
            tp_result = await self.executor.execute([tp_node], [], ctx)
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
