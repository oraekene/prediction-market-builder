import asyncio
import logging
import httpx
from datetime import datetime, timezone
from typing import Any
from app.models.market import MarketPlatform, MarketStatus

logger = logging.getLogger(__name__)


class PolymarketMarketData:
    BASE_URL = "https://clob.polymarket.com"

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/markets",
                params={"limit": limit, "offset": offset},
                timeout=10,
            )
            resp.raise_for_status()
            return [self._normalize(m) for m in resp.json().get("data", [])]

    async def fetch_market(self, market_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/markets/{market_id}", timeout=10)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._normalize(resp.json())

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": MarketPlatform.POLYMARKET,
            "platform_market_id": raw.get("id", ""),
            "title": raw.get("question", raw.get("title", "")),
            "description": raw.get("description", ""),
            "category": raw.get("category", ""),
            "current_odds": float(raw.get("outcomePrices", [0.5])[0]) if raw.get("outcomePrices") else 0.5,
            "bid": float(raw.get("bid", 0)),
            "ask": float(raw.get("ask", 0)),
            "volume": float(raw.get("volume", 0)),
            "liquidity": float(raw.get("liquidity", 0)),
            "participants": int(raw.get("participants", 0)),
            "close_time": raw.get("closeTime"),
            "status": MarketStatus.OPEN if raw.get("closed") is False else MarketStatus.CLOSED,
            "outcomes": raw.get("outcomes", ["Yes", "No"]),
            "raw_data": raw,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


class KalshiMarketData:
    BASE_URL = "https://trading-api.kalshi.com/trade-api/v2"

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/markets",
                params={"limit": limit, "offset": offset},
                timeout=10,
            )
            resp.raise_for_status()
            return [self._normalize(m) for m in resp.json().get("markets", [])]

    async def fetch_market(self, market_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/markets/{market_id}", timeout=10)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._normalize(resp.json())

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": MarketPlatform.KALSHI,
            "platform_market_id": raw.get("ticker", raw.get("id", "")),
            "title": raw.get("title", raw.get("question", "")),
            "description": raw.get("description", ""),
            "category": raw.get("category", ""),
            "current_odds": float(raw.get("yes_bid", raw.get("yes_ask", 0.5))),
            "bid": float(raw.get("yes_bid")),
            "ask": float(raw.get("yes_ask")),
            "volume": float(raw.get("volume", 0)),
            "liquidity": float(raw.get("liquidity", 0)),
            "participants": int(raw.get("participants", 0)),
            "close_time": raw.get("close_time"),
            "status": MarketStatus.OPEN if raw.get("status") == "open" else MarketStatus.CLOSED,
            "outcomes": ["Yes", "No"],
            "raw_data": raw,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


class DriftMarketData:
    BASE_URL = "https://api.drift.trade"

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/v2/markets",
                params={"limit": limit, "offset": offset},
                timeout=10,
            )
            resp.raise_for_status()
            return [self._normalize(m) for m in resp.json()]

    async def fetch_market(self, market_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/v2/markets/{market_id}", timeout=10)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return self._normalize(resp.json())

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": MarketPlatform.DRIFT,
            "platform_market_id": raw.get("marketId", raw.get("id", "")),
            "title": raw.get("question", raw.get("title", "")),
            "description": raw.get("description", ""),
            "category": raw.get("category", ""),
            "current_odds": float(raw.get("price", raw.get("current_odds", 0.5))),
            "bid": float(raw.get("bid", 0)),
            "ask": float(raw.get("ask", 0)),
            "volume": float(raw.get("volume", 0)),
            "liquidity": float(raw.get("liquidity", 0)),
            "participants": int(raw.get("participants", 0)),
            "close_time": raw.get("closeTime", raw.get("expiry")),
            "status": MarketStatus.OPEN if raw.get("status", "open") == "open" else MarketStatus.CLOSED,
            "outcomes": raw.get("outcomes", ["Yes", "No"]),
            "raw_data": raw,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


class MarketAggregator:
    """Fetches real market listings from supported platforms.

    On platform failure, that platform contributes nothing and the error
    is logged — never replaced with fabricated mock data.
    """

    def __init__(self):
        self.connectors = {
            "polymarket": PolymarketMarketData(),
            "kalshi": KalshiMarketData(),
            "drift": DriftMarketData(),
        }

    async def fetch_all(self, platforms: list[str] | None = None) -> list[dict[str, Any]]:
        targets = platforms or list(self.connectors.keys())
        connectors = {p: self.connectors[p] for p in targets if p in self.connectors}
        results = await asyncio.gather(
            *(c.fetch_markets() for c in connectors.values()),
            return_exceptions=True,
        )
        combined: list[dict[str, Any]] = []
        for platform, result in zip(connectors.keys(), results):
            if isinstance(result, Exception):
                logger.warning("Failed to fetch markets from %s: %s", platform, result)
            else:
                combined.extend(result)
        return combined

    async def fetch_market(self, platform: str, market_id: str) -> dict[str, Any] | None:
        connector = self.connectors.get(platform)
        if not connector:
            return None
        try:
            return await connector.fetch_market(market_id)
        except Exception as exc:
            logger.warning("Failed to fetch market %s from %s: %s", market_id, platform, exc)
            return None
