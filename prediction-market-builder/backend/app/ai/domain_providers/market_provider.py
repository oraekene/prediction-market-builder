import logging
import time
from datetime import datetime, timezone

from app.ai.domain_providers.base import DomainProvider, DomainData, DomainItem

logger = logging.getLogger(__name__)


class MarketDomainProvider(DomainProvider):
    def __init__(self, market_aggregator=None):
        self._market_aggregator = market_aggregator

    @property
    def name(self) -> str:
        return "markets"

    @property
    def description(self) -> str:
        return "Prediction market odds, volume, liquidity, and participant data"

    async def query(self, query: str, context: dict | None = None) -> DomainData:
        start = time.time()
        try:
            if self._market_aggregator:
                markets = await self._market_aggregator.fetch_all()
            else:
                from app.services.market_aggregator import MarketAggregator
                ma = MarketAggregator()
                markets = await ma.fetch_all()
            items = []
            for m in markets:
                title = m.get("title", "")
                if query.lower() not in title.lower() and not self._query_matches_any(query, m):
                    continue
                text = (
                    f"{title} odds={m.get('current_odds', 0):.2f} "
                    f"volume={m.get('volume', 0):.0f} "
                    f"liquidity={m.get('liquidity', 0):.0f}"
                )
                items.append(DomainItem(
                    text=text,
                    metadata={
                        "odds": m.get("current_odds", 0),
                        "volume": m.get("volume", 0),
                        "liquidity": m.get("liquidity", 0),
                        "participants": m.get("participants", 0),
                        "category": m.get("category", ""),
                        "platform": m.get("platform", ""),
                    },
                    source=m.get("platform_market_id", ""),
                    timestamp=datetime.now(timezone.utc),
                ))
                if len(items) >= 10:
                    break
            elapsed = int((time.time() - start) * 1000)
            return DomainData(domain="markets", items=items, query_time_ms=elapsed)
        except Exception as e:
            logger.warning("Market provider query failed: %s", e)
            elapsed = int((time.time() - start) * 1000)
            return DomainData(domain="markets", error=str(e), query_time_ms=elapsed)

    def _query_matches_any(self, query: str, market: dict) -> bool:
        q = query.lower()
        for val in [market.get("title", ""), market.get("category", ""), market.get("description", "")]:
            if q in val.lower():
                return True
        return False
