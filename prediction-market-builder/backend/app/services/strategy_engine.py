from typing import Any
from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_node_handlers import register_risk_handlers
from app.services.performance_node_handlers import PERFORMANCE_HANDLERS
from app.services.shap_node_handlers import register_shap_handlers
from app.services.palette_node_handlers import register_palette_handlers
from app.services.advanced_risk_node_handlers import register_advanced_risk_handlers
from app.services.action_node_handlers import register_action_handlers


_default_registry: NodeRegistry | None = None


def _get_registry() -> NodeRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = NodeRegistry()
        _default_registry.register("threshold_condition", _handle_threshold)
        register_risk_handlers(_default_registry)
        register_shap_handlers(_default_registry)
        register_palette_handlers(_default_registry)
        register_advanced_risk_handlers(_default_registry)
        register_action_handlers(_default_registry)
        for node_type, handler in PERFORMANCE_HANDLERS.items():
            _default_registry.register(node_type, handler)
    return _default_registry


def _handle_threshold(node: dict, inputs: dict, ctx: ExecutionContext) -> dict:
    data = node.get("data", {})
    field = data.get("field", "current_odds")
    operator = data.get("operator", "lt")
    threshold = data.get("threshold", 0.5)
    threshold_high = data.get("threshold_high", 1.0)
    value = ctx.market.get(field, 0.5)
    if operator == "lt":
        triggered = value < threshold
    elif operator == "gt":
        triggered = value > threshold
    elif operator == "between":
        triggered = threshold <= value <= threshold_high
    elif operator == "outside":
        triggered = value < threshold or value > threshold_high
    else:
        triggered = False
    return {"triggered": triggered, "value": value, "threshold": threshold}


class StrategyEngine:
    def __init__(self, registry: NodeRegistry | None = None):
        self.registry = registry or _get_registry()
        self.executor = GraphExecutor(self.registry)
        self.strategies: dict[str, Any] = {}

    def register_strategy(self, strategy_id: str, config: dict[str, Any]):
        self.strategies[strategy_id] = config

    async def evaluate_strategy(self, strategy_id: str, market: dict[str, Any]) -> dict[str, Any]:
        config = self.strategies.get(strategy_id)
        if not config:
            return {"error": "Strategy not found"}
        nodes = config.get("nodes", [])
        edges = config.get("edges", [])
        ctx = ExecutionContext(
            market=market,
            risk_calculator=RiskCalculator(),
            portfolio_manager=PortfolioManager(),
        )
        return await self.executor.execute(nodes, edges, ctx)

    async def evaluate(self, nodes: list, edges: list, ctx: ExecutionContext | None = None) -> dict[str, Any]:
        if ctx is None:
            ctx = ExecutionContext(
                risk_calculator=RiskCalculator(),
                portfolio_manager=PortfolioManager(),
            )
        return await self.executor.execute(nodes, edges, ctx)
