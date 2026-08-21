import asyncio
import inspect
from typing import Any, Callable, Awaitable


NodeHandler = Callable[..., Any] | Callable[..., Awaitable[Any]]


class ExecutionContext:
    def __init__(self, market: dict | None = None, signal: dict | None = None,
                 portfolio: dict | None = None, risk_calculator=None,
                 portfolio_manager=None, tabpfn=None,
                 performance_snapshot: dict | None = None,
                 explainability_service=None, hermes=None, rlm=None,
                 market_regime=None, market_aggregator=None,
                 chromadb_manager=None,
                 trail_states: dict | None = None,
                 circuit_breaker_state: dict | None = None,
                 withdrawal_state: dict | None = None,
                 daily_pnl: float = 0.0,
                 weekly_pnl: float = 0.0,
                 monthly_pnl: float = 0.0,
                 consecutive_losses: int = 0,
                 price_history: list | None = None,
                 factor_exposures: dict | None = None,
                 greeks: dict | None = None,
                 vpin: float = 0.0,
                 ofi: float = 0.0,
                 position_monitor=None,
                 execution_engine=None):
        self.market = market or {}
        self.signal = signal or {}
        self.portfolio = portfolio or {}
        self.risk_calculator = risk_calculator
        self.portfolio_manager = portfolio_manager
        self.tabpfn = tabpfn
        self.performance_snapshot = performance_snapshot or {}
        self.explainability_service = explainability_service
        self.hermes = hermes
        self.rlm = rlm
        self.market_regime = market_regime
        self.market_aggregator = market_aggregator
        self.chromadb_manager = chromadb_manager
        self.trail_states = trail_states or {}
        self.circuit_breaker_state = circuit_breaker_state or {}
        self.withdrawal_state = withdrawal_state or {}
        self.daily_pnl = daily_pnl
        self.weekly_pnl = weekly_pnl
        self.monthly_pnl = monthly_pnl
        self.consecutive_losses = consecutive_losses
        self.price_history = price_history or []
        self.factor_exposures = factor_exposures or {}
        self.greeks = greeks or {}
        self.vpin = vpin
        self.ofi = ofi
        self.position_monitor = position_monitor
        self.execution_engine = execution_engine


class NodeRegistry:
    def __init__(self):
        self._handlers: dict[str, NodeHandler] = {}

    def register(self, node_type: str, handler: NodeHandler):
        self._handlers[node_type] = handler

    def get(self, node_type: str) -> NodeHandler | None:
        return self._handlers.get(node_type)


class GraphExecutor:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry

    async def execute(self, nodes: list, edges: list, context: ExecutionContext) -> dict[str, Any]:
        if not nodes:
            return {"approved": True, "suggested_size": 0.0, "violations": []}

        adjacency = {n["id"]: [] for n in nodes}
        in_degree = {n["id"]: 0 for n in nodes}
        node_map = {n["id"]: n for n in nodes}

        for edge in edges:
            s, t = edge["source"], edge["target"]
            if s in adjacency and t in adjacency:
                adjacency[s].append(t)
                in_degree[t] += 1

        queue = [nid for nid, d in in_degree.items() if d == 0]
        outputs = {}
        processed = 0

        while queue:
            nid = queue.pop(0)
            processed += 1
            node = node_map[nid]
            node_inputs = {}
            for edge in edges:
                if edge["target"] == nid and edge["source"] in outputs:
                    node_inputs[edge["source"]] = outputs[edge["source"]]

            handler = self.registry.get(node["type"])
            if handler:
                try:
                    if inspect.iscoroutinefunction(handler):
                        outputs[nid] = await handler(node, node_inputs, context)
                    else:
                        outputs[nid] = handler(node, node_inputs, context)
                except Exception as e:
                    outputs[nid] = {"error": str(e)}
            else:
                outputs[nid] = {}

            for neighbor in adjacency.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if processed < len(nodes):
            unprocessed = [n["id"] for n in nodes if n["id"] not in outputs]
            for uid in unprocessed:
                outputs[uid] = {"error": f"Cycle detected: node {uid} could not be evaluated"}

        action_outputs = {
            k: v for k, v in outputs.items()
            if isinstance(v, dict) and ("approved" in v or "action" in v)
        }
        if action_outputs:
            return list(action_outputs.values())[-1]

        if outputs:
            return list(outputs.values())[-1]
        return {"approved": True, "suggested_size": 0.0, "violations": []}
