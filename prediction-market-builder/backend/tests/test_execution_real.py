import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.execution import ExecutionEngine, SimulatedExecutionEngine
from app.services.exchange_base import OrderBook, OrderBookLevel, FillResult, Balance


@pytest.fixture
def engine():
    eng = ExecutionEngine()
    for name in list(eng._connectors.keys()):
        eng._connectors[name] = AsyncMock()
    return eng


class TestExecutionEngine:
    @pytest.mark.asyncio
    async def test_get_order_book(self, engine):
        mock_conn = engine._connectors["polymarket"]
        mock_conn.get_order_book.return_value = OrderBook(
            platform="polymarket", market_id="123",
            bids=[OrderBookLevel(0.5, 100)], asks=[OrderBookLevel(0.6, 100)],
            mid_price=0.55, spread=0.1,
        )
        book = await engine.get_order_book("polymarket", "123")
        assert book.mid_price == 0.55
        mock_conn.get_order_book.assert_awaited_once_with("123")

    @pytest.mark.asyncio
    async def test_place_order(self, engine):
        mock_conn = engine._connectors["polymarket"]
        mock_conn.place_order.return_value = FillResult(
            order_id="c1", platform_order_id="p1", status="filled",
            filled_amount=100, fill_price=0.55, total_cost=55, slippage=0.0,
        )
        user = MagicMock()
        user.id = "u1"
        user.polymarket_key = "key:secret"
        user.kalshi_key = None
        user.drift_key = None

        fill = await engine.place_order("polymarket", "123", "buy", 100, 0.55, user)
        assert fill.status == "filled"
        assert fill.platform_order_id == "p1"

    @pytest.mark.asyncio
    async def test_calculate_slippage_buy(self, engine):
        mock_conn = engine._connectors["polymarket"]
        mock_conn.get_order_book.return_value = OrderBook(
            platform="polymarket", market_id="123",
            bids=[OrderBookLevel(0.5, 100)],
            asks=[OrderBookLevel(0.55, 50), OrderBookLevel(0.56, 50)],
            mid_price=0.525, spread=0.05,
        )
        result = await engine.calculate_slippage("polymarket", "123", 100, "buy")
        assert result["filled_amount"] == 100
        assert result["avg_fill_price"] > 0
        assert len(result["fill_curve"]) == 2

    @pytest.mark.asyncio
    async def test_monitor_order_filled(self, engine):
        mock_conn = engine._connectors["polymarket"]
        filled = FillResult(order_id="", platform_order_id="p1", status="filled", filled_amount=100, fill_price=0.55, total_cost=55, slippage=0)
        pending = FillResult(order_id="", platform_order_id="p1", status="pending", filled_amount=0, fill_price=0, total_cost=0, slippage=0)
        mock_conn.get_order_status.side_effect = [pending, filled]

        result = await engine.monitor_order("polymarket", "p1", max_wait=10, poll_interval=1)
        assert result.status == "filled"

    @pytest.mark.asyncio
    async def test_monitor_order_timeout(self, engine):
        mock_conn = engine._connectors["polymarket"]
        mock_conn.get_order_status.return_value = FillResult(order_id="", platform_order_id="p1", status="pending", filled_amount=0, fill_price=0, total_cost=0, slippage=0)

        result = await engine.monitor_order("polymarket", "p1", max_wait=0, poll_interval=1)
        assert result.status == "pending_review"

    @pytest.mark.asyncio
    async def test_available(self, engine):
        mock_conn = engine._connectors["polymarket"]
        mock_conn.available.return_value = True
        assert await engine.available("polymarket") is True

    @pytest.mark.asyncio
    async def test_available_failure(self, engine):
        mock_conn = engine._connectors["polymarket"]
        mock_conn.available.side_effect = Exception("down")
        assert await engine.available("polymarket") is False

    @pytest.mark.asyncio
    async def test_close(self, engine):
        for mock_conn in engine._connectors.values():
            mock_conn.close = AsyncMock()
        await engine.close()
        for mock_conn in engine._connectors.values():
            mock_conn.close.assert_awaited_once()

    def test_simulated_engine_exists(self):
        sim = SimulatedExecutionEngine()
        assert "polymarket" in sim.order_books
        book = sim.get_order_book("polymarket", 0.5, 1_000_000)
        assert "bids" in book
        assert "asks" in book

    def test_simulated_fill(self):
        sim = SimulatedExecutionEngine()
        book = sim.get_order_book("polymarket", 0.5, 1_000_000)
        result = sim.simulate_fill("polymarket", "buy", 100, 0.55, book)
        assert "status" in result
        assert result["filled_amount"] <= 100
