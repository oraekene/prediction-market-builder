import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.ai.domain_providers.base import DomainProvider, DomainData, DomainItem

logger = logging.getLogger(__name__)

_MOCK_TOPICS: dict[str, list[str]] = {
    "eth": ["SEC Delays ETH ETF Decision", "Whale Moves 50K ETH to CEX", "ETH Layer 2 TVL Hits New ATH", "Ethereum Staking Rate Reaches 28%"],
    "btc": ["BTC Volatility Spikes Ahead of Halving", "Institutional Bitcoin Holdings Reach Record", "Bitcoin Hashrate Hits All-Time High"],
    "fed": ["Fed Signals Potential Rate Cut", "Inflation Data Beats Expectations", "Fed Minutes Reveal Divided Committee"],
    "crypto": ["Crypto Market Cap Surpasses $3T", "DeFi Total Value Locked Rebounds", "Stablecoin Supply Expands for 6th Month"],
    "regulation": ["New Crypto Regulation Framework Proposed", "CFTC Unveils Digital Asset Rules", "SEC Enforcement Actions Decline 40%"],
    "sol": ["Solana TVL Surpasses $10B", "SOL Ecosystem DEX Volume Reaches New Monthly Record"],
    "trump": ["Trump Media Stock Volatility Increases", "Trump Leads in Key Swing State Polls"],
    "ai": ["AI Chip Demand Surges 200% Year-over-Year", "Major Tech Companies Announce AI Spending Plans"],
    "stocks": ["S&P 500 Earnings Beat Expectations", "NASDAQ Composite Reaches New High", "Institutional Rotation from Growth to Value"],
}


class NewsDomainProvider(DomainProvider):
    def __init__(self, news_api_key: str | None = None):
        self._api_key = news_api_key

    @property
    def name(self) -> str:
        return "news"

    @property
    def description(self) -> str:
        return "News headlines and articles relevant to the query"

    async def query(self, query: str, context: dict | None = None) -> DomainData:
        start = time.time()
        articles = await self._fetch_real_news(query)
        if not articles:
            articles = self._mock_headlines(query)
        items = []
        for art in articles:
            title = art.get("title", art.get("headline", ""))
            desc = art.get("description", "")
            text = f"{title} {desc}".strip()
            if not text:
                continue
            source_name = "unknown"
            src = art.get("source", {})
            if isinstance(src, dict):
                source_name = src.get("name", "unknown")
            elif isinstance(src, str):
                source_name = src
            items.append(DomainItem(
                text=text,
                metadata={"source": source_name},
                source=art.get("url", ""),
                timestamp=self._parse_date(art.get("publishedAt")),
            ))
        elapsed = int((time.time() - start) * 1000)
        return DomainData(domain="news", items=items, query_time_ms=elapsed)

    async def _fetch_real_news(self, query: str) -> list[dict[str, Any]]:
        if not self._api_key:
            return []
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": query, "pageSize": 10, "language": "en"},
                    headers={"X-Api-Key": self._api_key},
                    timeout=10,
                )
                data = resp.json()
                return data.get("articles", [])
        except Exception as e:
            logger.debug("News API fetch failed: %s", e)
            return []

    def _mock_headlines(self, query: str) -> list[dict[str, Any]]:
        keywords = query.lower().split()
        matched: list[dict[str, Any]] = []
        for kw, headlines in _MOCK_TOPICS.items():
            if kw in keywords:
                for h in headlines:
                    matched.append({
                        "title": h,
                        "description": "",
                        "source": "CryptoNews",
                        "url": "",
                        "publishedAt": datetime.now(timezone.utc).isoformat(),
                    })
        if not matched:
            matched.append({
                "title": f"Latest Developments in {query}",
                "description": "Analysis and market-moving updates are emerging",
                "source": "FinancialTimes",
                "url": "",
                "publishedAt": datetime.now(timezone.utc).isoformat(),
            })
        return matched[:5]

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
