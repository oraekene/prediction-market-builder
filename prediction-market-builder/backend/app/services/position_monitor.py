import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.services.node_executor import NodeRegistry, GraphExecutor, ExecutionContext
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


@dataclass
class MonitoredPosition:
    position_id: str
    strategy_id: str
    user_id: str
    platform: str
    market_id: str
    market_title: str
    side: str
    entry_price: float
    size: float
    entry_time: datetime
    status: str = "active"
    risk_nodes: list[dict] = field(default_factory=list)
    risk_edges: list[dict] = field(default_factory=list)
    trail_states: dict[str, Any] = field(default_factory=dict)
    circuit_breaker_state: dict[str, Any] = field(default_factory=dict)
    current_market_data: dict[str, Any] = field(default_factory=dict)
    portfolio_state: dict[str, Any] = field(default_factory=dict)
    withdrawal_strategy_id: str | None = None


class PositionMonitor:
    def __init__(self, execution_engine=None, paper_trading_service=None,
                 interval_seconds: float = 5.0):
        self.execution_engine = execution_engine
        self.paper_trading_service = paper_trading_service
        self._interval_seconds = interval_seconds
        self._monitored_positions: dict[str, MonitoredPosition] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._risk_calculator = RiskCalculator()
        self._portfolio_manager = PortfolioManager()
        self._node_registry = NodeRegistry()
        self._graph_executor = GraphExecutor(self._node_registry)
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("PositionMonitor started with interval %.1fs", self._interval_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("PositionMonitor stopped")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._check_all_positions()
            except Exception:
                logger.exception("Error in position monitor loop")
            await asyncio.sleep(self._interval_seconds)

    async def _check_all_positions(self) -> None:
        async with self._lock:
            active = {
                pid: pos for pid, pos in self._monitored_positions.items()
                if pos.status == "active"
            }

        for position_id, position in active.items():
            try:
                context = self._build_context(position)
                result = await self._graph_executor.execute(
                    position.risk_nodes,
                    position.risk_edges,
                    context,
                )

                violations = result.get("violations", [])
                approved = result.get("approved", True)

                if not approved or violations:
                    logger.info(
                        "Position %s triggered risk check: approved=%s violations=%s",
                        position_id, approved, violations,
                    )
                    await self._execute_close(position)

                self._update_trail_state(position, context)

            except Exception:
                logger.exception("Error checking position %s", position_id)

    def _build_context(self, position: MonitoredPosition) -> ExecutionContext:
        market_data = position.current_market_data.copy()
        market_data.setdefault("current_odds", position.entry_price)

        portfolio = position.portfolio_state.copy()
        portfolio.setdefault("current_capital", 10000)
        portfolio.setdefault("peak_capital", 10000)
        portfolio.setdefault("positions", [])
        portfolio.setdefault("returns", [])

        signal = {
            "probability": market_data.get("probability", 0.5),
            "market_odds": market_data.get("current_odds", position.entry_price),
            "confidence": market_data.get("confidence", 0.7),
            "position_id": position.position_id,
            "side": position.side,
            "entry_price": position.entry_price,
            "size": position.size,
        }

        return ExecutionContext(
            market=market_data,
            signal=signal,
            portfolio=portfolio,
            risk_calculator=self._risk_calculator,
            portfolio_manager=self._portfolio_manager,
            execution_engine=self.execution_engine,
            position_monitor=self,
            trail_states=position.trail_states.copy(),
            circuit_breaker_state=position.circuit_breaker_state.copy(),
            daily_pnl=portfolio.get("daily_pnl", 0.0),
            weekly_pnl=portfolio.get("weekly_pnl", 0.0),
            monthly_pnl=portfolio.get("monthly_pnl", 0.0),
            consecutive_losses=portfolio.get("consecutive_losses", 0),
            price_history=portfolio.get("price_history", []),
        )

    async def _execute_close(self, position: MonitoredPosition) -> None:
        current_price = position.current_market_data.get(
            "current_odds", position.entry_price
        )
        sell_side = "sell" if position.side == "buy" else "buy"

        try:
            if self.execution_engine:
                if hasattr(self.execution_engine, "place_order"):
                    user = position.portfolio_state.get("user")
                    fill = await self.execution_engine.place_order(
                        platform=position.platform,
                        market_id=position.market_id,
                        side=sell_side,
                        amount=position.size,
                        price=current_price,
                        user=user,
                        strategy_id=position.strategy_id,
                    )
                    logger.info(
                        "Closed position %s via execution engine: fill=%s",
                        position.position_id,
                        fill.status if hasattr(fill, "status") else fill,
                    )
                elif hasattr(self.execution_engine, "simulate_fill"):
                    order_book = self.execution_engine.get_order_book(
                        position.platform,
                        current_price,
                        position.size * 1000,
                    )
                    fill = self.execution_engine.simulate_fill(
                        platform=position.platform,
                        side=sell_side,
                        amount=position.size,
                        price=current_price,
                        order_book=order_book,
                    )
                    logger.info(
                        "Closed position %s via simulated fill: %s",
                        position.position_id,
                        fill.get("status", "unknown"),
                    )

            pnl = self._compute_pnl(position, current_price)

            async with self._lock:
                position.status = "closed"
                position.current_market_data["exit_price"] = current_price
                position.current_market_data["exit_time"] = datetime.now(timezone.utc).isoformat()
                position.current_market_data["pnl"] = pnl

        except Exception:
            logger.exception("Failed to close position %s", position.position_id)
            async with self._lock:
                position.status = "closed"
                position.current_market_data["exit_price"] = current_price
                position.current_market_data["exit_time"] = datetime.now(timezone.utc).isoformat()
                position.current_market_data["close_error"] = True

    def _compute_pnl(self, position: MonitoredPosition, exit_price: float) -> float:
        if position.side == "buy":
            pnl = (exit_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - exit_price) * position.size
        return round(pnl, 6)

    def _update_trail_state(self, position: MonitoredPosition, context: ExecutionContext) -> None:
        current_price = position.current_market_data.get(
            "current_odds", position.entry_price
        )

        for node in position.risk_nodes:
            if node.get("type") not in ("trailing_stop", "take_profit", "stop_loss"):
                continue

            node_id = node["id"]
            data = node.get("data", {})
            trail_pct = data.get("trail_pct", 0.05)
            activation_pct = data.get("activation_pct", 0.02)
            node_type = node["type"]

            if node_type == "trailing_stop":
                state = position.trail_states.get(node_id, {})
                high_water = state.get("high_water_mark", position.entry_price)

                if position.side == "buy":
                    gain_pct = (current_price - position.entry_price) / position.entry_price if position.entry_price > 0 else 0
                    activated = gain_pct >= activation_pct
                    if current_price > high_water:
                        high_water = current_price
                    stop_price = high_water * (1 - trail_pct)
                    triggered = activated and current_price <= stop_price
                else:
                    gain_pct = (position.entry_price - current_price) / position.entry_price if position.entry_price > 0 else 0
                    activated = gain_pct >= activation_pct
                    if current_price < high_water or high_water == position.entry_price:
                        high_water = current_price
                    stop_price = high_water * (1 + trail_pct)
                    triggered = activated and current_price >= stop_price

                position.trail_states[node_id] = {
                    "high_water_mark": high_water,
                    "stop_price": stop_price,
                    "activated": activated,
                    "triggered": triggered,
                }

            elif node_type == "take_profit":
                state = position.trail_states.get(node_id, {})
                take_profit_pct = data.get("take_profit", 0.2)

                if position.side == "buy":
                    gain_pct = (current_price - position.entry_price) / position.entry_price if position.entry_price > 0 else 0
                else:
                    gain_pct = (position.entry_price - current_price) / position.entry_price if position.entry_price > 0 else 0

                position.trail_states[node_id] = {
                    "gain_pct": round(gain_pct, 4),
                    "take_profit_pct": take_profit_pct,
                    "triggered": gain_pct >= take_profit_pct,
                }

            elif node_type == "stop_loss":
                state = position.trail_states.get(node_id, {})
                stop_loss_pct = data.get("stop_loss", 0.1)

                if position.side == "buy":
                    loss_pct = (position.entry_price - current_price) / position.entry_price if position.entry_price > 0 else 0
                else:
                    loss_pct = (current_price - position.entry_price) / position.entry_price if position.entry_price > 0 else 0

                position.trail_states[node_id] = {
                    "loss_pct": round(loss_pct, 4),
                    "stop_loss_pct": stop_loss_pct,
                    "triggered": loss_pct >= stop_loss_pct,
                }

    def register_position(self, position: MonitoredPosition) -> None:
        self._monitored_positions[position.position_id] = position
        logger.info("Registered position %s for monitoring", position.position_id)

    def unregister_position(self, position_id: str) -> bool:
        removed = self._monitored_positions.pop(position_id, None)
        if removed:
            logger.info("Unregistered position %s from monitoring", position_id)
        return removed is not None

    def get_position(self, position_id: str) -> MonitoredPosition | None:
        return self._monitored_positions.get(position_id)

    def get_active_positions(self) -> list[MonitoredPosition]:
        return [
            pos for pos in self._monitored_positions.values()
            if pos.status == "active"
        ]

    def update_position_market_data(self, position_id: str, market_data: dict) -> bool:
        position = self._monitored_positions.get(position_id)
        if not position:
            return False
        position.current_market_data.update(market_data)
        return True

    def update_position_portfolio_state(self, position_id: str, portfolio_state: dict) -> bool:
        position = self._monitored_positions.get(position_id)
        if not position:
            return False
        position.portfolio_state.update(portfolio_state)
        return True
