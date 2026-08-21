from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SearXNGUnavailableError(Exception):
    ...


class SearXNGTimeoutError(SearXNGUnavailableError):
    ...


class SearXNGParseError(SearXNGUnavailableError):
    ...


class SearXNGClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8888",
        timeout: int = 15,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None
        self._available: bool | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                limits=limits,
            )
        return self._client

    async def search(
        self,
        query: str,
        category: str = "general",
        pageno: int = 1,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                client = await self._get_client()
                resp = await client.get(
                    "/search",
                    params={
                        "q": query,
                        "format": "json",
                        "category": category,
                        "pageno": pageno,
                        "language": language,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self._available = True
                return self._normalize_results(data, query, category)
            except httpx.TimeoutException as e:
                last_error = SearXNGTimeoutError(f"SearXNG timeout on attempt {attempt + 1}: {e}")
                logger.warning("SearXNG timeout (attempt %d/%d): %s", attempt + 1, self.max_retries, e)
            except httpx.HTTPStatusError as e:
                last_error = SearXNGUnavailableError(f"SearXNG HTTP {e.response.status_code}: {e}")
                logger.error("SearXNG HTTP error: %s", e)
                break
            except httpx.RequestError as e:
                last_error = SearXNGUnavailableError(f"SearXNG connection error: {e}")
                logger.warning("SearXNG request error (attempt %d/%d): %s", attempt + 1, self.max_retries, e)
            except (ValueError, KeyError) as e:
                last_error = SearXNGParseError(f"SearXNG parse error: {e}")
                logger.error("SearXNG parse error: %s", e)
                break
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        self._available = False
        raise last_error or SearXNGUnavailableError("Unknown SearXNG error")

    async def search_multi(
        self,
        queries: list[str],
        category: str = "general",
    ) -> list[dict[str, Any]]:
        coros = [self.search(q, category=category) for q in queries]
        results = await asyncio.gather(*coros, return_exceptions=True)
        merged: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for result in results:
            if isinstance(result, Exception):
                logger.warning("search_multi sub-query failed: %s", result)
                continue
            for item in result:
                url = item.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    merged.append(item)
        merged.sort(key=lambda x: x.get("score", 0), reverse=True)
        return merged

    async def count_results(self, query: str, category: str = "general") -> int:
        client = await self._get_client()
        resp = await client.get(
            "/search",
            params={"q": query, "format": "json", "category": category, "pageno": 1},
        )
        resp.raise_for_status()
        data = resp.json()
        return int(data.get("number_of_results", 0))

    async def check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            client = await self._get_client()
            resp = await client.get("/search", params={"q": "test", "format": "json", "pageno": 1}, timeout=5)
            self._available = resp.is_success
        except Exception:
            self._available = False
        return self._available

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _normalize_results(
        self,
        data: dict[str, Any],
        query: str,
        category: str,
    ) -> list[dict[str, Any]]:
        results = data.get("results", [])
        normalized = []
        for r in results:
            normalized.append({
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "engine": r.get("engine", ""),
                "score": float(r.get("score", 0)),
                "category": r.get("category", category),
                "positions": r.get("positions", []),
                "published_date": r.get("publishedDate", None),
                "source_query": query,
            })
        normalized.sort(key=lambda x: x["score"], reverse=True)
        return normalized
