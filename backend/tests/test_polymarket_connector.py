import pytest
from unittest.mock import AsyncMock, patch
from httpx import Response

from app.services.polymarket_connector import PolymarketConnector
from app.services.exchange_base import ExchangeOrder, OrderBookLevel


@pytest.fixture
def connector():
    return PolymarketConnector()


@pytest.mark.asyncio
async def test_get_order_book(connector):
    mock_data = {
        "bids": [{"price": "0.55", "size": "1000"}],
        "asks": [{"price": "0.60", "size": "800"}],
        "last_price": "0.58",
    }
    async def mock_request(*args, **kwargs):
        return mock_data
    connector._request = mock_request

    book = await connector.get_order_book("123")
    assert book.platform == "polymarket"
    assert len(book.bids) == 1
    assert book.bids[0].price == 0.55
    assert book.mid_price == 0.575
    assert book.last_price == 0.58


@pytest.mark.asyncio
async def test_available_success(connector):
    async def mock_request(*args, **kwargs):
        return {"markets": []}
    connector._request = mock_request
    assert await connector.available() is True


@pytest.mark.asyncio
async def test_available_failure(connector):
    async def mock_request(*args, **kwargs):
        raise Exception("down")
    connector._request = mock_request
    assert await connector.available() is False


@pytest.mark.asyncio
async def test_place_order_success(connector):
    async def mock_request(*args, **kwargs):
        return {"id": "order-1", "status": "FILLED", "matched_size": "100", "average_filled_price": "0.55", "fee": "0.5"}
    connector._request = mock_request

    order = ExchangeOrder(platform="polymarket", market_id="123", side="buy", order_type="market", price=0.55, amount=100, client_order_id="client-1")
    fill = await connector.place_order(order, {"api_key": "key", "secret": "secret"})
    assert fill.status == "filled"
    assert fill.platform_order_id == "order-1"
    assert fill.filled_amount == 100


@pytest.mark.asyncio
async def test_place_order_http_error(connector):
    async def mock_request(*args, **kwargs):
        raise __import__("httpx").HTTPStatusError("error", request=None, response=Response(400, text="bad request"))
    connector._request = mock_request

    order = ExchangeOrder(platform="polymarket", market_id="123", side="buy", order_type="market", price=0.55, amount=100)
    fill = await connector.place_order(order, {"api_key": "key", "secret": "secret"})
    assert fill.status == "failed"
    assert fill.error is not None


@pytest.mark.asyncio
async def test_cancel_order(connector):
    cancelled = False
    async def mock_request(*args, **kwargs):
        nonlocal cancelled
        cancelled = True
        return {}
    connector._request = mock_request
    result = await connector.cancel_order("order-1")
    assert result is True
    assert cancelled


@pytest.mark.asyncio
async def test_get_balance(connector):
    async def mock_request(*args, **kwargs):
        return {"USDC": {"balance": "5000"}}
    connector._request = mock_request
    balances = await connector.get_balance({"api_key": "key", "secret": "secret"})
    assert len(balances) == 1
    assert balances[0].asset == "USDC"
    assert balances[0].free == 5000
