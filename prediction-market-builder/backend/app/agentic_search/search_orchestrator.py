from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from typing import Any

from app.agentic_search.schemas import (
    SearchCategory,
    SearchDepth,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.agentic_search.searxng_client import SearXNGClient, SearXNGUnavailableError
from app.agentic_search.scrapling_parser import ScraplingParser
from app.agentic_search.camoufox_playwright import CamoufoxCrawler

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    def __init__(
        self,
        searxng_client: SearXNGClient | None = None,
        scrapling_parser: ScraplingParser | None = None,
        camoufox_crawler: CamoufoxCrawler | None = None,
        cache_ttl: int = 300,
        cache_max_size: int = 500,
        rate_limit_per_min: int = 30,
    ):
        self.searxng = searxng_client or SearXNGClient()
        self.scrapling = scrapling_parser or ScraplingParser()
        self.camoufox = camoufox_crawler or CamoufoxCrawler()
        self.cache_ttl = cache_ttl
        self.cache_max_size = cache_max_size
        self.rate_limit_per_min = rate_limit_per_min
        self._cache: OrderedDict[str, tuple[float, SearchResponse]] = OrderedDict()
        self._rate_limit_timestamps: list[float] = []

    async def search(self, request: SearchRequest) -> SearchResponse:
        cache_key = self._make_cache_key(request)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        await self._check_rate_limit()
        start = time.monotonic()

        try:
            if request.depth == SearchDepth.QUICK:
                results, engines = await self._search_quick(request)
            elif request.depth == SearchDepth.STANDARD:
                results, engines = await self._search_standard(request)
            elif request.depth == SearchDepth.DEEP:
                results, engines = await self._search_deep(request)
            else:
                results, engines = [], []
        except SearXNGUnavailableError:
            logger.warning("SearXNG unavailable, attempting fallback search")
            results, engines = await self._fallback_search(request)

        took_ms = int((time.monotonic() - start) * 1000)
        response = SearchResponse(
            results=results[: request.max_results],
            total_found=len(results),
            engines_used=engines,
            took_ms=took_ms,
            cached=False,
        )
        self._store_in_cache(cache_key, response)
        return response

    async def self_check(self) -> dict[str, bool]:
        results = await asyncio.gather(
            self.searxng.check_available(),
            self.scrapling.available(),
            self.camoufox.available(),
            return_exceptions=True,
        )
        return {
            "searxng": bool(results[0]) if not isinstance(results[0], Exception) else False,
            "scrapling": bool(results[1]) if not isinstance(results[1], Exception) else False,
            "camoufox": bool(results[2]) if not isinstance(results[2], Exception) else False,
        }

    async def close(self):
        await self.searxng.close()
        await self.scrapling.close()
        await self.camoufox.close()

    async def _search_quick(self, request: SearchRequest) -> tuple[list[SearchResultItem], list[str]]:
        results = await self.searxng.search(
            query=request.query,
            category=request.categories[0].value if request.categories else "general",
        )
        engines = list({r["engine"] for r in results})
        items = [self._raw_to_item(r) for r in results]
        return items, engines

    async def _search_standard(self, request: SearchRequest) -> tuple[list[SearchResultItem], list[str]]:
        raw_results = await self.searxng.search(
            query=request.query,
            category=request.categories[0].value if request.categories else "general",
        )
        engines = list({r["engine"] for r in raw_results})
        top = raw_results[: max(5, request.max_results * 2)]

        async def enrich(item: dict) -> SearchResultItem:
            result_item = self._raw_to_item(item)
            if request.extract_content:
                parsed = await self.scrapling.parse_url(item["url"])
                if parsed:
                    result_item.content = parsed.get("content")
                    result_item.extracted_at = time.time()
            return result_item

        items = await asyncio.gather(*[enrich(r) for r in top], return_exceptions=True)
        result_items: list[SearchResultItem] = []
        for item in items:
            if isinstance(item, Exception):
                logger.warning("Enrichment failed: %s", item)
                continue
            result_items.append(item)
        result_items.sort(key=lambda x: x.score, reverse=True)
        return result_items, engines

    async def _search_deep(self, request: SearchRequest) -> tuple[list[SearchResultItem], list[str]]:
        follow_ups = self._generate_follow_ups(request.query)
        all_queries = [request.query] + follow_ups

        raw_results = await self.searxng.search_multi(
            queries=all_queries,
            category=request.categories[0].value if request.categories else "general",
        )
        seen_engines: set[str] = set()
        for r in raw_results:
            seen_engines.add(r.get("engine", ""))
        engines = list(seen_engines)
        top = raw_results[: max(10, request.max_results * 3)]

        async def deep_enrich(item: dict) -> SearchResultItem:
            result_item = self._raw_to_item(item)
            parsed = await self.scrapling.parse_url(item["url"])
            if parsed and parsed.get("content"):
                result_item.content = parsed["content"]
                result_item.extracted_at = time.time()
            elif parsed is None:
                browser_result = await self.camoufox.extract_page_safe(item["url"])
                if browser_result.get("content"):
                    parsed_content = await self.scrapling.parse_html(
                        browser_result["content"], item["url"]
                    )
                    if parsed_content:
                        result_item.content = parsed_content.get("content")
                        result_item.extracted_at = time.time()
            return result_item

        items = await asyncio.gather(*[deep_enrich(r) for r in top], return_exceptions=True)
        result_items: list[SearchResultItem] = []
        for item in items:
            if isinstance(item, Exception):
                logger.warning("Deep enrichment failed: %s", item)
                continue
            result_items.append(item)
        result_items.sort(key=lambda x: x.score, reverse=True)
        return result_items, engines

    async def _fallback_search(self, request: SearchRequest) -> tuple[list[SearchResultItem], list[str]]:
        logger.info("Using Camoufox fallback for query: %s", request.query)
        try:
            search_url = f"https://lite.duckduckgo.com/lite/?q={request.query.replace(' ', '+')}"
            browser_result = await self.camoufox.extract_page_safe(search_url)
            if browser_result.get("content"):
                scraped = await self.scrapling.parse_html(browser_result["content"], search_url)
                if scraped:
                    item = SearchResultItem(
                        url=search_url,
                        title=scraped.get("title", request.query),
                        snippet=scraped.get("snippet", ""),
                        engine="camoufox_fallback",
                        score=0.5,
                        category=request.categories[0].value if request.categories else "general",
                    )
                    return [item], ["camoufox_fallback"]
        except Exception as e:
            logger.warning("Fallback search failed: %s", e)
        return [], []

    def _generate_follow_ups(self, query: str) -> list[str]:
        return [
            f"{query} 2026",
            f"{query} news analysis",
        ]

    def _raw_to_item(self, raw: dict[str, Any]) -> SearchResultItem:
        return SearchResultItem(
            url=raw.get("url", ""),
            title=raw.get("title", ""),
            snippet=raw.get("snippet", ""),
            engine=raw.get("engine", ""),
            score=raw.get("score", 0.0),
            category=raw.get("category", "general"),
        )

    def _make_cache_key(self, request: SearchRequest) -> str:
        raw = f"{request.query}|{request.depth.value}|{request.categories}|{request.max_results}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> SearchResponse | None:
        if key in self._cache:
            timestamp, response = self._cache[key]
            if time.monotonic() - timestamp < self.cache_ttl:
                cached = response.model_copy(deep=True)
                cached.cached = True
                return cached
            del self._cache[key]
        return None

    def _store_in_cache(self, key: str, response: SearchResponse):
        while len(self._cache) >= self.cache_max_size:
            self._cache.popitem(last=False)
        self._cache[key] = (time.monotonic(), response)

    async def _check_rate_limit(self):
        now = time.monotonic()
        window = 60.0
        self._rate_limit_timestamps = [t for t in self._rate_limit_timestamps if now - t < window]
        if len(self._rate_limit_timestamps) >= self.rate_limit_per_min:
            sleep_time = self._rate_limit_timestamps[0] + window - now
            if sleep_time > 0:
                logger.warning("Rate limit reached, sleeping %.1fs", sleep_time)
                await asyncio.sleep(sleep_time)
        self._rate_limit_timestamps.append(time.monotonic())
