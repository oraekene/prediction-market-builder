import pytest
from unittest.mock import AsyncMock
from httpx import Response

from app.services.kalshi_connector import KalshiConnector
from app.services.exchange_base import ExchangeOrder


@pytest.fixture
def connector():
    return KalshiConnector()


@pytest.mark.asyncio
async def test_get_order_book(connector):
    async def mock_request(*args, **kwargs):
        return {"market": {"bid": 0.5, "ask": 0.6, "bid_size": 1000, "ask_size": 800, "last_price": 0.55}}
    connector._request = mock_request

    book = await connector.get_order_book("TEST-123")
    assert book.platform == "kalshi"
    assert book.mid_price == 0.55
    assert book.spread > 0


@pytest.mark.asyncio
async def test_place_order_success(connector):
    async def mock_request(*args, **kwargs):
        return {"order": {"order_id": "ord-1", "status": "FILLED", "filled_count": 100, "fill_price": 55}}
    connector._request = mock_request

    order = ExchangeOrder(platform="kalshi", market_id="TEST-123", side="buy", order_type="market", price=0.55, amount=100)
    fill = await connector.place_order(order, {"private_key": "key"})
    assert fill.platform_order_id == "ord-1"
    assert fill.filled_amount == 100


@pytest.mark.asyncio
async def test_place_order_failure(connector):
    async def mock_request(*args, **kwargs):
        raise __import__("httpx").HTTPStatusError("error", request=None, response=Response(400, text="bad"))
    connector._request = mock_request

    order = ExchangeOrder(platform="kalshi", market_id="TEST-123", side="buy", order_type="market", price=0.55, amount=100)
    fill = await connector.place_order(order, {"private_key": "key"})
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
        return {"balance": 10000}
    connector._request = mock_request
    balances = await connector.get_balance({"private_key": "key"})
    assert balances[0].free == 10000
