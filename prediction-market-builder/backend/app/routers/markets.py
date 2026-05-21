from fastapi import APIRouter, Query
from app.services.market_aggregator import MarketAggregator

router = APIRouter(prefix="/api/markets", tags=["markets"])
aggregator = MarketAggregator()


@router.get("")
async def list_markets(
    platform: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None),
    min_volume: float | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    platforms = [platform] if platform else None
    markets = await aggregator.fetch_all(platforms)
    if category:
        markets = [m for m in markets if m.get("category", "").lower() == category.lower()]
    if search:
        markets = [m for m in markets if search.lower() in m.get("title", "").lower()]
    if min_volume:
        markets = [m for m in markets if (m.get("volume") or 0) >= min_volume]
    return {"markets": markets[offset: offset + limit], "total": len(markets)}


@router.get("/{market_id}")
async def get_market(market_id: str):
    for connector in aggregator.connectors.values():
        market = await connector.fetch_market(market_id)
        if market:
            return market
    return {"error": "Market not found"}
