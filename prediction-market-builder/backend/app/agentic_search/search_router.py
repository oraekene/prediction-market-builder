from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from app.agentic_search.search_orchestrator import SearchOrchestrator
from app.agentic_search.schemas import SearchRequest, SearchResponse, SearchDepth, SearchCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["agentic-search"])

_orchestrator: SearchOrchestrator | None = None


def init_search_orchestrator(orchestrator: SearchOrchestrator) -> None:
    global _orchestrator
    _orchestrator = orchestrator


@router.post("", response_model=SearchResponse)
async def search(body: SearchRequest) -> SearchResponse:
    if not _orchestrator:
        return SearchResponse(
            results=[], total_found=0, engines_used=[], took_ms=0, cached=False
        )
    return await _orchestrator.search(body)


@router.get("/status")
async def search_status() -> dict[str, Any]:
    if not _orchestrator:
        return {"error": "Search not initialized"}
    status = await _orchestrator.self_check()
    return {"status": "ok" if any(status.values()) else "unavailable", "checks": status}


def register_search_tools(tr: Any, orchestrator: SearchOrchestrator) -> None:
    tr.register(
        name="search_web",
        toolset="search",
        schema={
            "description": "Search the web for information on a given query. Supports quick, standard, and deep depth levels. Standard extracts content from top results; deep generates follow-up queries and uses browser rendering for JS-heavy pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"},
                    "depth": {
                        "type": "string",
                        "enum": ["quick", "standard", "deep"],
                        "description": "quick=just search results, standard=+content extraction, deep=+follow-up queries+browser rendering",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return (1-50)",
                        "default": 10,
                    },
                    "category": {
                        "type": "string",
                        "enum": ["general", "news", "science", "social"],
                        "description": "Search category filter",
                        "default": "general",
                    },
                },
                "required": ["query"],
            },
        },
        handler=lambda **kw: _handle_search_tool(orchestrator, kw),
    )
    tr.register(
        name="search_news",
        toolset="search",
        schema={
            "description": "Quick search for recent news articles on a topic. Uses the news category and returns results fast.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "News search query"},
                    "max_results": {"type": "integer", "description": "Max results (1-20)", "default": 5},
                },
                "required": ["query"],
            },
        },
        handler=lambda **kw: _handle_news_tool(orchestrator, kw),
    )
    tr.register(
        name="search_crawl",
        toolset="search",
        schema={
            "description": "Deep crawl a specific URL to extract full page content, including JavaScript-rendered content. Useful for pages that don't load in standard search snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to crawl and extract content from"},
                },
                "required": ["url"],
            },
        },
        handler=lambda **kw: _handle_crawl_tool(orchestrator, kw),
    )


def _handle_search_tool(orchestrator: SearchOrchestrator, kw: dict[str, Any]) -> dict[str, Any]:
    import asyncio
    depth_map = {"quick": SearchDepth.QUICK, "standard": SearchDepth.STANDARD, "deep": SearchDepth.DEEP}
    depth = depth_map.get(kw.get("depth", "standard"), SearchDepth.STANDARD)
    cat_str = kw.get("category", "general")
    try:
        cat = SearchCategory(cat_str)
    except ValueError:
        cat = SearchCategory.GENERAL
    req = SearchRequest(
        query=kw.get("query", ""),
        max_results=min(int(kw.get("max_results", 10)), 50),
        depth=depth,
        categories=[cat],
        extract_content=depth in (SearchDepth.STANDARD, SearchDepth.DEEP),
    )
    resp = asyncio.get_event_loop().run_until_complete(orchestrator.search(req))
    return resp.model_dump()


def _handle_news_tool(orchestrator: SearchOrchestrator, kw: dict[str, Any]) -> dict[str, Any]:
    import asyncio
    req = SearchRequest(
        query=kw.get("query", ""),
        max_results=min(int(kw.get("max_results", 5)), 20),
        depth=SearchDepth.QUICK,
        categories=[SearchCategory.NEWS],
    )
    resp = asyncio.get_event_loop().run_until_complete(orchestrator.search(req))
    return resp.model_dump()


def _handle_crawl_tool(orchestrator: SearchOrchestrator, kw: dict[str, Any]) -> dict[str, Any]:
    import asyncio
    url = kw.get("url", "")
    if not url:
        return {"error": "url is required"}
    result = asyncio.get_event_loop().run_until_complete(
        orchestrator.camoufox.extract_page_safe(url)
    )
    return result
