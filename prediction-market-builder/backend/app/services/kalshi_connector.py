import json
import logging
import time
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.services.exchange_base import (
    ExchangeConnector,
    ExchangeOrder,
    OrderBook,
    OrderBookLevel,
    FillResult,
    Balance,
)
from app.services.execution_config import KALSHI_SETTINGS

logger = logging.getLogger(__name__)


def _sign_rsa(method: str, path: str, body: dict | None, private_key_pem: str) -> dict:
    timestamp = str(int(time.time()))
    msg = f"{timestamp}{method}{path}"
    if body:
        msg += json.dumps(body, sort_keys=True)
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    assert isinstance(private_key, rsa.RSAPrivateKey)
    signature = private_key.sign(msg.encode(), padding.PKCS1v15(), hashes.SHA256())
    return {
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "KALSHI-ACCESS-SIGNATURE": signature.hex(),
    }


class KalshiConnector(ExchangeConnector):
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._settings = KALSHI_SETTINGS

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_base_url,
                timeout=self._settings.timeout_seconds,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def _request(self, method: str, path: str, private_key: str = "", **kwargs) -> dict:
        client = self._get_client()
        headers = kwargs.pop("headers", {})
        if private_key:
            headers.update(_sign_rsa(method, path, kwargs.get("json"), private_key))
        for attempt in range(self._settings.max_retries):
            try:
                resp = await client.request(method, path, headers=headers, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 502, 503, 504) and attempt < self._settings.max_retries - 1:
                    wait = self._settings.retry_delay_seconds * (2 ** attempt)
                    await asyncio.sleep(wait)
                    continue
                raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self._settings.max_retries - 1:
                    wait = self._settings.retry_delay_seconds * (2 ** attempt)
                    await asyncio.sleep(wait)
                    continue
                raise

    async def get_order_book(self, market_id: str) -> OrderBook:
        data = await self._request("GET", f"/market/{market_id}")
        market = data.get("market", {})
        bid = float(market.get("bid", 0))
        ask = float(market.get("ask", 0))
        mid = (bid + ask) / 2 if bid and ask else 0.0
        spread = (ask - bid) / mid if mid > 0 else 0.0
        return OrderBook(
            platform="kalshi",
            market_id=market_id,
            bids=[OrderBookLevel(price=bid, size=float(market.get("bid_size", 0)))],
            asks=[OrderBookLevel(price=ask, size=float(market.get("ask_size", 0)))],
            mid_price=mid,
            spread=spread,
            last_price=float(market.get("last_price", 0)),
        )

    async def place_order(self, order: ExchangeOrder, credentials: dict) -> FillResult:
        private_key = credentials.get("private_key", "")
        body = {
            "ticker": order.market_id,
            "side": order.side.upper(),
            "type": order.order_type.upper(),
            "price": int(order.price * 100),
            "count": int(order.amount),
            "client_order_id": order.client_order_id or "",
        }
        try:
            data = await self._request("POST", "/portfolio/order", private_key=private_key, json=body)
            order_data = data.get("order", {})
            platform_id = order_data.get("order_id", "")
            status = order_data.get("status", "pending").lower()
            filled = float(order_data.get("filled_count", 0))
            fill_price = float(order_data.get("fill_price", 0)) / 100
            cost = filled * fill_price
            slippage = abs(fill_price - order.price) / order.price if order.price > 0 else 0
            return FillResult(
                order_id=order.client_order_id or "",
                platform_order_id=platform_id,
                status=status,
                filled_amount=filled,
                fill_price=fill_price,
                total_cost=cost,
                slippage=slippage,
            )
        except httpx.HTTPStatusError as e:
            return FillResult(
                order_id=order.client_order_id or "",
                platform_order_id=None,
                status="failed",
                filled_amount=0,
                fill_price=0,
                total_cost=0,
                slippage=0,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            return FillResult(
                order_id=order.client_order_id or "",
                platform_order_id=None,
                status="failed",
                filled_amount=0,
                fill_price=0,
                total_cost=0,
                slippage=0,
                error=str(e),
            )

    async def cancel_order(self, platform_order_id: str) -> bool:
        try:
            await self._request("DELETE", f"/portfolio/order/{platform_order_id}")
            return True
        except Exception:
            return False

    async def get_order_status(self, platform_order_id: str) -> FillResult:
        data = await self._request("GET", f"/portfolio/order/{platform_order_id}")
        order_data = data.get("order", {})
        status = order_data.get("status", "pending").lower()
        filled = float(order_data.get("filled_count", 0))
        fill_price = float(order_data.get("fill_price", 0)) / 100
        return FillResult(
            order_id="",
            platform_order_id=platform_order_id,
            status=status,
            filled_amount=filled,
            fill_price=fill_price,
            total_cost=filled * fill_price,
            slippage=0,
        )

    async def get_balance(self, credentials: dict) -> list[Balance]:
        private_key = credentials.get("private_key", "")
        data = await self._request("GET", "/portfolio/balance", private_key=private_key)
        return [Balance(asset="USDC", free=float(data.get("balance", 0)), locked=0, total=float(data.get("balance", 0)))]

    async def available(self) -> bool:
        try:
            await self._request("GET", "/markets?limit=1")
            return True
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


import asyncio
