from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.agentic_search.search_router import router, init_search_orchestrator, register_search_tools, _orchestrator as mod_orchestrator
from app.agentic_search.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchDepth,
    SearchCategory,
)
from app.ai.tool_registry import ToolRegistry


def _make_search_response() -> SearchResponse:
    return SearchResponse(
        results=[
            SearchResultItem(
                url="https://example.com/1",
                title="Result One",
                snippet="A search result snippet",
                engine="google",
                score=0.95,
                category="general",
            ),
            SearchResultItem(
                url="https://example.com/2",
                title="Result Two",
                snippet="Another snippet",
                engine="ddg",
                score=0.80,
                category="general",
            ),
        ],
        total_found=2,
        engines_used=["google", "ddg"],
        took_ms=150,
        cached=False,
    )


@pytest.fixture
def mock_orchestrator():
    orch = MagicMock()
    orch.search = AsyncMock(return_value=_make_search_response())
    orch.self_check = AsyncMock(return_value={"searxng": True, "scrapling": True, "camoufox": False})
    orch.camoufox = MagicMock()
    orch.camoufox.extract_page_safe = AsyncMock(return_value={
        "url": "https://example.com",
        "title": "Test Page",
        "content": "<html><body>Hello</body></html>",
        "status_code": 200,
        "took_ms": 100,
    })
    return orch


@pytest.fixture
def test_app(mock_orchestrator):
    app = FastAPI()
    init_search_orchestrator(mock_orchestrator)
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


class TestSearchEndpoint:
    def test_search_quick(self, client):
        resp = client.post("/api/v1/search", json={
            "query": "federal reserve rates",
            "depth": "quick",
            "max_results": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["title"] == "Result One"
        assert data["engines_used"] == ["google", "ddg"]
        assert data["cached"] is False

    def test_search_standard(self, client):
        resp = client.post("/api/v1/search", json={
            "query": "inflation data",
            "depth": "standard",
            "max_results": 10,
            "categories": ["news"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 2

    def test_search_deep(self, client):
        resp = client.post("/api/v1/search", json={
            "query": "bitcoin price prediction",
            "depth": "deep",
            "max_results": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) <= 5

    def test_search_invalid_depth_returns_422(self, client):
        resp = client.post("/api/v1/search", json={
            "query": "test",
            "depth": "ultra",
        })
        assert resp.status_code == 422

    def test_search_status(self, client):
        resp = client.get("/api/v1/search/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data
        assert data["checks"]["searxng"] is True


class TestSearchNotInitialized:
    @pytest.fixture(autouse=True)
    def reset_orchestrator(self):
        import app.agentic_search.search_router as sr
        old = sr._orchestrator
        sr._orchestrator = None
        yield
        sr._orchestrator = old

    @pytest.fixture
    def app_no_init(self):
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client_no_init(self, app_no_init):
        return TestClient(app_no_init)

    def test_search_returns_empty(self, client_no_init):
        resp = client_no_init.post("/api/v1/search", json={"query": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["total_found"] == 0

    def test_status_returns_error(self, client_no_init):
        resp = client_no_init.get("/api/v1/search/status")
        assert resp.status_code == 200
        assert resp.json()["error"] == "Search not initialized"


class TestToolRegistration:
    def test_register_search_tools(self):
        tr = ToolRegistry()
        mock_orch = MagicMock()
        register_search_tools(tr, mock_orch)

        tools = tr.list_tools(toolset_filter="search")
        names = {t["name"] for t in tools}
        assert "search_web" in names
        assert "search_news" in names
        assert "search_crawl" in names

    def test_search_web_schema(self):
        tr = ToolRegistry()
        register_search_tools(tr, MagicMock())

        defs = tr.get_definitions({"search_web"})
        assert len(defs) == 1
        params = defs[0]["function"]["parameters"]
        assert "query" in params["required"]
        assert params["properties"]["depth"]["enum"] == ["quick", "standard", "deep"]

    @pytest.mark.asyncio
    async def test_search_web_dispatch(self):
        tr = ToolRegistry()
        mock_orch = MagicMock()
        mock_orch.search = AsyncMock(return_value=_make_search_response())
        register_search_tools(tr, mock_orch)

        result = await tr.execute("search_web", {"query": "test", "depth": "quick"})
        assert "results" in result
        assert result["total_found"] == 2

    @pytest.mark.asyncio
    async def test_search_news_dispatch(self):
        tr = ToolRegistry()
        mock_orch = MagicMock()
        mock_orch.search = AsyncMock(return_value=_make_search_response())
        register_search_tools(tr, mock_orch)

        result = await tr.execute("search_news", {"query": "latest news"})
        assert "results" in result

    @pytest.mark.asyncio
    async def test_search_crawl_dispatch(self):
        tr = ToolRegistry()
        mock_orch = MagicMock()
        mock_orch.camoufox = MagicMock()
        mock_orch.camoufox.extract_page_safe = AsyncMock(return_value={
            "url": "https://example.com",
            "content": "test", "title": "", "status_code": 200, "took_ms": 50,
        })
        register_search_tools(tr, mock_orch)

        result = await tr.execute("search_crawl", {"url": "https://example.com"})
        assert result["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_search_crawl_missing_url(self):
        tr = ToolRegistry()
        register_search_tools(tr, MagicMock())

        result = await tr.execute("search_crawl", {})
        assert "error" in result
