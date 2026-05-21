import pytest
from app.services.market_aggregator import PolymarketConnector


@pytest.mark.asyncio
async def test_polymarket_normalize():
    connector = PolymarketConnector()
    raw = {
        "id": "123",
        "question": "Will it rain?",
        "outcomePrices": ["0.65", "0.35"],
        "volume": "1000000",
        "closed": False,
    }
    result = connector._normalize(raw)
    assert result["platform_market_id"] == "123"
    assert result["title"] == "Will it rain?"
    assert result["current_odds"] == 0.65
    assert result["volume"] == 1000000.0


@pytest.mark.asyncio
async def test_polymarket_normalize_empty():
    connector = PolymarketConnector()
    result = connector._normalize({})
    assert result["platform_market_id"] == ""
    assert result["current_odds"] == 0.5
