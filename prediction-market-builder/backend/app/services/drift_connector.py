import asyncio
import logging
from typing import Any

import httpx

from app.services.exchange_base import (
    ExchangeConnector,
    ExchangeOrder,
    OrderBook,
    OrderBookLevel,
    FillResult,
    Balance,
)
from app.services.execution_config import DRIFT_SETTINGS

logger = logging.getLogger(__name__)


class DriftConnector(ExchangeConnector):
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._settings = DRIFT_SETTINGS

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_base_url,
                timeout=self._settings.timeout_seconds,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def _request(self, method: str, path: str, api_key: str = "", **kwargs) -> dict:
        client = self._get_client()
        headers = kwargs.pop("headers", {})
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
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
        data = await self._request("GET", f"/v1/markets/{market_id}/orderbook")
        bids = [OrderBookLevel(price=float(b["price"]), size=float(b["size"])) for b in data.get("bids", [])]
        asks = [OrderBookLevel(price=float(a["price"]), size=float(a["size"])) for a in data.get("asks", [])]
        best_bid = bids[0].price if bids else 0.0
        best_ask = asks[0].price if asks else 0.0
        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
        spread = (best_ask - best_bid) / mid if mid > 0 else 0.0
        return OrderBook(
            platform="drift",
            market_id=market_id,
            bids=bids,
            asks=asks,
            mid_price=mid,
            spread=spread,
        )

    async def place_order(self, order: ExchangeOrder, credentials: dict) -> FillResult:
        api_key = credentials.get("api_key", "")
        body = {
            "market_id": order.market_id,
            "side": order.side,
            "order_type": order.order_type,
            "price": str(order.price),
            "size": str(order.amount),
        }
        try:
            data = await self._request("POST", "/v1/orders", api_key=api_key, json=body)
            return FillResult(
                order_id=order.client_order_id or "",
                platform_order_id=data.get("order_id", ""),
                status=data.get("status", "pending").lower(),
                filled_amount=float(data.get("filled_size", 0)),
                fill_price=float(data.get("avg_fill_price", order.price)),
                total_cost=float(data.get("filled_size", 0)) * float(data.get("avg_fill_price", order.price)),
                slippage=float(data.get("slippage", 0)),
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
            await self._request("DELETE", f"/v1/orders/{platform_order_id}")
            return True
        except Exception:
            return False

    async def get_order_status(self, platform_order_id: str) -> FillResult:
        data = await self._request("GET", f"/v1/orders/{platform_order_id}")
        return FillResult(
            order_id="",
            platform_order_id=platform_order_id,
            status=data.get("status", "pending").lower(),
            filled_amount=float(data.get("filled_size", 0)),
            fill_price=float(data.get("avg_fill_price", 0)),
            total_cost=float(data.get("filled_size", 0)) * float(data.get("avg_fill_price", 0)),
            slippage=0,
        )

    async def get_balance(self, credentials: dict) -> list[Balance]:
        api_key = credentials.get("api_key", "")
        data = await self._request("GET", "/v1/accounts", api_key=api_key)
        return [Balance(asset=a.get("symbol", "USDC"), free=float(a.get("free", 0)), locked=float(a.get("locked", 0)), total=float(a.get("total", 0))) for a in data.get("accounts", [])]

    async def available(self) -> bool:
        try:
            await self._request("GET", "/v1/markets?limit=1")
            return True
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
