import pytest
from unittest.mock import AsyncMock
from httpx import Response

from app.services.drift_connector import DriftConnector
from app.services.exchange_base import ExchangeOrder


@pytest.fixture
def connector():
    return DriftConnector()


@pytest.mark.asyncio
async def test_get_order_book(connector):
    async def mock_request(*args, **kwargs):
        return {
            "bids": [{"price": "0.50", "size": "500"}],
            "asks": [{"price": "0.52", "size": "400"}],
        }
    connector._request = mock_request

    book = await connector.get_order_book("SOL-PERP")
    assert book.platform == "drift"
    assert len(book.bids) == 1
    assert book.bids[0].price == 0.50


@pytest.mark.asyncio
async def test_place_order_success(connector):
    async def mock_request(*args, **kwargs):
        return {"order_id": "drift-1", "status": "FILLED", "filled_size": "10", "avg_fill_price": "150.0", "slippage": "0.001"}
    connector._request = mock_request

    order = ExchangeOrder(platform="drift", market_id="SOL-PERP", side="buy", order_type="market", price=150.0, amount=10)
    fill = await connector.place_order(order, {"api_key": "key"})
    assert fill.platform_order_id == "drift-1"
    assert fill.filled_amount == 10


@pytest.mark.asyncio
async def test_place_order_failure(connector):
    async def mock_request(*args, **kwargs):
        raise __import__("httpx").HTTPStatusError("error", request=None, response=Response(500, text="server error"))
    connector._request = mock_request

    order = ExchangeOrder(platform="drift", market_id="SOL-PERP", side="buy", order_type="market", price=150.0, amount=10)
    fill = await connector.place_order(order, {"api_key": "key"})
    assert fill.status == "failed"


@pytest.mark.asyncio
async def test_available(connector):
    async def mock_request(*args, **kwargs):
        return {"markets": []}
    connector._request = mock_request
    assert await connector.available() is True


@pytest.mark.asyncio
async def test_get_balance(connector):
    async def mock_request(*args, **kwargs):
        return {"accounts": [{"symbol": "USDC", "free": "5000", "locked": "100", "total": "5100"}]}
    connector._request = mock_request
    balances = await connector.get_balance({"api_key": "key"})
    assert balances[0].free == 5000
