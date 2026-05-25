from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agentic_search.search_orchestrator import SearchOrchestrator
from app.agentic_search.schemas import (
    SearchCategory,
    SearchDepth,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.agentic_search.searxng_client import SearXNGUnavailableError


@pytest.fixture
def mock_searxng():
    client = AsyncMock()
    client.search = AsyncMock()
    client.search_multi = AsyncMock()
    client.check_available = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_scrapling():
    parser = AsyncMock()
    parser.parse_url = AsyncMock()
    parser.parse_html = AsyncMock()
    parser.available = AsyncMock(return_value=True)
    parser.close = AsyncMock()
    return parser


@pytest.fixture
def mock_camoufox():
    crawler = AsyncMock()
    crawler.extract_page_safe = AsyncMock()
    crawler.available = AsyncMock(return_value=True)
    crawler.close = AsyncMock()
    return crawler


@pytest.fixture
def orchestrator(mock_searxng, mock_scrapling, mock_camoufox):
    return SearchOrchestrator(
        searxng_client=mock_searxng,
        scrapling_parser=mock_scrapling,
        camoufox_crawler=mock_camoufox,
        cache_ttl=300,
        cache_max_size=10,
    )


def sample_raw():
    return [
        {
            "url": "https://example.com/1",
            "title": "Result 1",
            "snippet": "Snippet 1",
            "engine": "google",
            "score": 0.9,
            "category": "general",
        },
        {
            "url": "https://example.com/2",
            "title": "Result 2",
            "snippet": "Snippet 2",
            "engine": "ddg",
            "score": 0.7,
            "category": "general",
        },
    ]


@pytest.mark.asyncio
async def test_search_quick(orchestrator, mock_searxng):
    mock_searxng.search.return_value = sample_raw()

    request = SearchRequest(query="test", depth=SearchDepth.QUICK)
    response = await orchestrator.search(request)

    assert len(response.results) == 2
    assert response.results[0].title == "Result 1"
    assert set(response.engines_used) == {"google", "ddg"}
    assert response.cached is False
    mock_searxng.search.assert_awaited_once_with(query="test", category="general")


@pytest.mark.asyncio
async def test_search_cached(orchestrator, mock_searxng):
    mock_searxng.search.return_value = sample_raw()

    request = SearchRequest(query="test", depth=SearchDepth.QUICK)
    response1 = await orchestrator.search(request)
    assert response1.cached is False

    response2 = await orchestrator.search(request)
    assert response2.cached is True
    assert mock_searxng.search.await_count == 1


@pytest.mark.asyncio
async def test_search_standard_with_extraction(orchestrator, mock_searxng, mock_scrapling):
    mock_searxng.search.return_value = sample_raw()
    mock_scrapling.parse_url.return_value = {
        "url": "https://example.com/1",
        "content": "Full content here",
        "title": "Result 1",
    }

    request = SearchRequest(query="test", depth=SearchDepth.STANDARD, extract_content=True)
    response = await orchestrator.search(request)

    assert len(response.results) > 0
    assert any(r.content == "Full content here" for r in response.results)


@pytest.mark.asyncio
async def test_search_deep(orchestrator, mock_searxng, mock_scrapling, mock_camoufox):
    mock_searxng.search_multi.return_value = sample_raw()
    mock_scrapling.parse_url.return_value = {
        "url": "https://example.com/1",
        "content": "Deep content",
        "title": "Result 1",
    }

    request = SearchRequest(query="test", depth=SearchDepth.DEEP, max_results=5)
    response = await orchestrator.search(request)

    assert len(response.results) > 0
    mock_searxng.search_multi.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_deep_falls_back_to_camoufox(orchestrator, mock_searxng, mock_scrapling, mock_camoufox):
    mock_searxng.search_multi.return_value = sample_raw()
    mock_scrapling.parse_url.return_value = None
    mock_camoufox.extract_page_safe.return_value = {
        "url": "https://example.com/1",
        "content": "<html><body>Browser content</body></html>",
    }
    mock_scrapling.parse_html.return_value = {
        "url": "https://example.com/1",
        "content": "Parsed browser content",
        "title": "Result 1",
    }

    request = SearchRequest(query="test", depth=SearchDepth.DEEP, max_results=5)
    response = await orchestrator.search(request)

    assert len(response.results) > 0


@pytest.mark.asyncio
async def test_search_searxng_unavailable_fallback(orchestrator, mock_searxng, mock_camoufox, mock_scrapling):
    mock_searxng.search.side_effect = SearXNGUnavailableError("SearXNG down")
    mock_camoufox.extract_page_safe.return_value = {
        "url": "https://lite.duckduckgo.com/lite/?q=test",
        "content": "<html><body>Fallback result</body></html>",
    }
    mock_scrapling.parse_html.return_value = {
        "url": "https://lite.duckduckgo.com/lite/?q=test",
        "content": "Fallback result",
        "title": "test",
    }

    request = SearchRequest(query="test", depth=SearchDepth.QUICK)
    response = await orchestrator.search(request)

    assert len(response.results) >= 0


@pytest.mark.asyncio
async def test_self_check(orchestrator, mock_searxng, mock_scrapling, mock_camoufox):
    status = await orchestrator.self_check()

    assert status["searxng"] is True
    assert status["scrapling"] is True
    assert status["camoufox"] is True


@pytest.mark.asyncio
async def test_close(orchestrator, mock_searxng, mock_scrapling, mock_camoufox):
    await orchestrator.close()

    mock_searxng.close.assert_awaited_once()
    mock_scrapling.close.assert_awaited_once()
    mock_camoufox.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_expiry(orchestrator, mock_searxng):
    mock_searxng.search.return_value = sample_raw()

    orchestrator.cache_ttl = -1
    request = SearchRequest(query="test", depth=SearchDepth.QUICK)
    await orchestrator.search(request)
    response2 = await orchestrator.search(request)

    assert response2.cached is False
    assert mock_searxng.search.await_count == 2


@pytest.mark.asyncio
async def test_make_cache_key(orchestrator):
    request = SearchRequest(query="test", depth=SearchDepth.STANDARD, categories=[SearchCategory.NEWS])
    key1 = orchestrator._make_cache_key(request)

    request2 = SearchRequest(query="test", depth=SearchDepth.STANDARD, categories=[SearchCategory.NEWS])
    key2 = orchestrator._make_cache_key(request2)

    assert key1 == key2


@pytest.mark.asyncio
async def test_make_cache_key_different_queries(orchestrator):
    r1 = SearchRequest(query="cats", depth=SearchDepth.QUICK)
    r2 = SearchRequest(query="dogs", depth=SearchDepth.QUICK)

    assert orchestrator._make_cache_key(r1) != orchestrator._make_cache_key(r2)
