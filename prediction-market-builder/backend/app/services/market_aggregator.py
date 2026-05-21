import httpx
import random
from datetime import datetime, timedelta, timezone
from typing import Any
from app.models.market import MarketPlatform, MarketStatus


class PolymarketConnector:
    BASE_URL = "https://clob.polymarket.com"

    MOCK_MARKETS = [
        {"id": "pm-001", "question": "Will BTC exceed $100k by Dec 2026?", "category": "Crypto", "outcomePrices": [0.72], "volume": 2500000, "liquidity": 800000, "participants": 1200, "closeTime": (datetime.now(timezone.utc) + timedelta(days=180)).isoformat(), "closed": False},
        {"id": "pm-002", "question": "Will the Fed cut rates in Q3 2026?", "category": "Economy", "outcomePrices": [0.45], "volume": 1800000, "liquidity": 600000, "participants": 890, "closeTime": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(), "closed": False},
        {"id": "pm-003", "question": "Will ETH complete the Pectra upgrade by Sept 2026?", "category": "Crypto", "outcomePrices": [0.88], "volume": 950000, "liquidity": 300000, "participants": 540, "closeTime": (datetime.now(timezone.utc) + timedelta(days=120)).isoformat(), "closed": False},
        {"id": "pm-004", "question": "Will US inflation stay above 3% through 2026?", "category": "Economy", "outcomePrices": [0.61], "volume": 3100000, "liquidity": 1100000, "participants": 2100, "closeTime": (datetime.now(timezone.utc) + timedelta(days=200)).isoformat(), "closed": False},
        {"id": "pm-005", "question": "Will a US spot SOL ETF be approved by Dec 2026?", "category": "Crypto", "outcomePrices": [0.34], "volume": 4200000, "liquidity": 1500000, "participants": 3400, "closeTime": (datetime.now(timezone.utc) + timedelta(days=210)).isoformat(), "closed": False},
    ]

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/markets",
                    params={"limit": limit, "offset": offset},
                    timeout=5,
                )
                resp.raise_for_status()
                return [self._normalize(m) for m in resp.json().get("data", [])]
        except Exception:
            return [self._normalize(m) for m in self.MOCK_MARKETS]

    async def fetch_market(self, market_id: str) -> dict[str, Any] | None:
        for m in self.MOCK_MARKETS:
            if m["id"] == market_id:
                return self._normalize(m)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/markets/{market_id}", timeout=5)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return self._normalize(resp.json())
        except Exception:
            return None

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


class KalshiConnector:
    BASE_URL = "https://trading-api.kalshi.com/trade-api/v2"
    MOCK_MARKETS = [
        {"ticker": "KX-001", "title": "Will GDP growth exceed 2.5% in 2026?", "category": "Economy", "yes_bid": 0.58, "yes_ask": 0.62, "volume": 5200000, "liquidity": 2100000, "participants": 4100, "close_time": (datetime.now(timezone.utc) + timedelta(days=220)).isoformat(), "status": "open"},
        {"ticker": "KX-002", "title": "Will unemployment drop below 4% in 2026?", "category": "Economy", "yes_bid": 0.41, "yes_ask": 0.45, "volume": 3800000, "liquidity": 1400000, "participants": 2900, "close_time": (datetime.now(timezone.utc) + timedelta(days=190)).isoformat(), "status": "open"},
        {"ticker": "KX-003", "title": "Will the S&P 500 reach 7000 by Dec 2026?", "category": "Stocks", "yes_bid": 0.29, "yes_ask": 0.33, "volume": 4500000, "liquidity": 1800000, "participants": 3600, "close_time": (datetime.now(timezone.utc) + timedelta(days=200)).isoformat(), "status": "open"},
    ]

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/markets",
                    params={"limit": limit, "offset": offset},
                    timeout=5,
                )
                resp.raise_for_status()
                return [self._normalize(m) for m in resp.json().get("markets", [])]
        except Exception:
            return [self._normalize(m) for m in self.MOCK_MARKETS]

    async def fetch_market(self, market_id: str) -> dict[str, Any] | None:
        for m in self.MOCK_MARKETS:
            if m["ticker"] == market_id:
                return self._normalize(m)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/markets/{market_id}", timeout=5)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return self._normalize(resp.json())
        except Exception:
            return None

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


class DriftConnector:
    BASE_URL = "https://api.drift.trade"
    MOCK_MARKETS = [
        {"marketId": "drift-001", "question": "Will SOL price exceed $500 by Dec 2026?", "category": "Crypto", "price": 0.47, "volume": 1800000, "liquidity": 600000, "participants": 750, "closeTime": (datetime.now(timezone.utc) + timedelta(days=210)).isoformat(), "status": "open"},
        {"marketId": "drift-002", "question": "Will JUP reach $5 market cap by end of 2026?", "category": "Crypto", "price": 0.23, "volume": 890000, "liquidity": 300000, "participants": 420, "closeTime": (datetime.now(timezone.utc) + timedelta(days=190)).isoformat(), "status": "open"},
        {"marketId": "drift-003", "question": "Will PYTH staking launch before Sept 2026?", "category": "Crypto", "price": 0.81, "volume": 320000, "liquidity": 100000, "participants": 180, "closeTime": (datetime.now(timezone.utc) + timedelta(days=100)).isoformat(), "status": "open"},
    ]

    async def fetch_markets(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.BASE_URL}/v2/markets",
                    params={"limit": limit, "offset": offset},
                    timeout=5,
                )
                resp.raise_for_status()
                return [self._normalize(m) for m in resp.json()]
        except Exception:
            return [self._normalize(m) for m in self.MOCK_MARKETS]

    async def fetch_market(self, market_id: str) -> dict[str, Any] | None:
        for m in self.MOCK_MARKETS:
            if m["marketId"] == market_id:
                return self._normalize(m)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.BASE_URL}/v2/markets/{market_id}", timeout=5)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return self._normalize(resp.json())
        except Exception:
            return None

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
    def __init__(self):
        self.connectors = {
            "polymarket": PolymarketConnector(),
            "kalshi": KalshiConnector(),
            "drift": DriftConnector(),
        }

    async def fetch_all(self, platforms: list[str] | None = None) -> list[dict[str, Any]]:
        targets = platforms or list(self.connectors.keys())
        results = []
        for platform in targets:
            connector = self.connectors.get(platform)
            if connector:
                try:
                    markets = await connector.fetch_markets()
                    results.extend(markets)
                except Exception as e:
                    print(f"Failed to fetch from {platform}: {e}")
        return results
