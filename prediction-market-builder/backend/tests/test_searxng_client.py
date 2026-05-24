from __future__ import annotations

import pytest
from httpx import AsyncClient, Request, Response
from unittest.mock import AsyncMock

from app.agentic_search.searxng_client import (
    SearXNGClient,
    SearXNGUnavailableError,
    SearXNGTimeoutError,
    SearXNGParseError,
)


@pytest.fixture
def client():
    return SearXNGClient(base_url="http://test:8888", max_retries=1)


@pytest.fixture
def sample_response():
    return {
        "query": "test query",
        "number_of_results": 100,
        "results": [
            {
                "url": "https://example.com/1",
                "title": "Result One",
                "content": "Snippet for result one",
                "engine": "google",
                "score": 0.95,
                "positions": [1, 2],
                "category": "general",
                "publishedDate": None,
            },
            {
                "url": "https://example.com/2",
                "title": "Result Two",
                "content": "Snippet for result two",
                "engine": "duckduckgo",
                "score": 0.85,
                "positions": [3],
                "category": "general",
                "publishedDate": "2026-05-24",
            },
        ],
    }


@pytest.mark.asyncio
async def test_search_success(client, sample_response, monkeypatch):
    async def mock_get(url, **kwargs):
        return Response(200, json=sample_response)

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    results = await client.search("test query")
    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/1"
    assert results[0]["score"] == 0.95
    assert results[1]["engine"] == "duckduckgo"
    assert results[0]["source_query"] == "test query"


@pytest.mark.asyncio
async def test_search_empty_results(client, monkeypatch):
    async def mock_get(url, **kwargs):
        return Response(200, json={"query": "x", "number_of_results": 0, "results": []})

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    results = await client.search("empty query")
    assert results == []


@pytest.mark.asyncio
async def test_search_connection_error(client, monkeypatch):
    async def mock_get(url, **kwargs):
        raise SearXNGUnavailableError("Connection refused")

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    with pytest.raises(SearXNGUnavailableError):
        await client.search("fail")


@pytest.mark.asyncio
async def test_search_timeout(client, monkeypatch):
    async def mock_get(url, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    with pytest.raises(SearXNGUnavailableError):
        await client.search("timeout")


@pytest.mark.asyncio
async def test_search_invalid_json(client, monkeypatch):
    async def mock_get(url, **kwargs):
        return Response(200, text="not-json")

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    with pytest.raises(SearXNGParseError):
        await client.search("bad json")


@pytest.mark.asyncio
async def test_search_http_error(client, monkeypatch):
    async def mock_get(url, **kwargs):
        return Response(500)

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    with pytest.raises(SearXNGUnavailableError):
        await client.search("server error")


@pytest.mark.asyncio
async def test_search_multi_deduplicates(client, sample_response, monkeypatch):
    call_count = 0

    async def mock_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(200, json=sample_response)
        return Response(200, json={
            "query": "q2",
            "number_of_results": 1,
            "results": [{
                "url": "https://example.com/1",
                "title": "Result One (duplicate)",
                "content": "Same URL",
                "engine": "google",
                "score": 0.9,
                "positions": [1],
                "category": "general",
            }],
        })

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    results = await client.search_multi(["q1", "q2"])
    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/1"
    assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_search_multi_partial_failure(client, sample_response, monkeypatch):
    async def mock_get(url, **kwargs):
        q = kwargs["params"]["q"]
        if q == "fail":
            raise SearXNGUnavailableError("fail")
        return Response(200, json=sample_response)

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    results = await client.search_multi(["good", "fail"])
    assert len(results) == 2


@pytest.mark.asyncio
async def test_count_results(client, monkeypatch):
    async def mock_get(url, **kwargs):
        return Response(200, json={"query": "test", "number_of_results": 42, "results": []})

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    count = await client.count_results("test")
    assert count == 42


@pytest.mark.asyncio
async def test_check_available_success(client, monkeypatch):
    async def mock_get(url, **kwargs):
        return Response(200, json={"results": []})

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    available = await client.check_available()
    assert available is True


@pytest.mark.asyncio
async def test_check_available_failure(client, monkeypatch):
    async def mock_get(url, **kwargs):
        raise Exception("down")

    monkeypatch.setattr(client, "_get_client", AsyncMock(return_value=AsyncMock(get=mock_get)))
    available = await client.check_available()
    assert available is False


@pytest.mark.asyncio
async def test_close(client):
    mock_client = AsyncMock()
    client._client = mock_client
    await client.close()
    mock_client.aclose.assert_awaited_once()
    assert client._client is None
