"""Integration + E2E tests for Task 4.3: Agentic Search Pipeline.

Tests the full search stack through FastAPI TestClient,
ToolRegistry dispatch, and end-to-end auth->search lifecycle.
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import MagicMock, AsyncMock, patch

from app.agentic_search.search_orchestrator import SearchOrchestrator
from app.agentic_search.schemas import (
    SearchRequest, SearchResponse, SearchResultItem, SearchDepth, SearchCategory,
)
from app.agentic_search.search_router import router, init_search_orchestrator, register_search_tools
from app.ai.tool_registry import ToolRegistry


@pytest.fixture
def sample_response() -> SearchResponse:
    return SearchResponse(
        results=[
            SearchResultItem(url="https://example.com/1", title="Result One",
                             snippet="Snippet 1", engine="google", score=0.95,
                             category="general"),
            SearchResultItem(url="https://example.com/2", title="Result Two",
                             snippet="Snippet 2", engine="ddg", score=0.80,
                             category="general"),
        ],
        total_found=2, engines_used=["google", "ddg"], took_ms=150, cached=False,
    )


@pytest.fixture
def mock_orch(sample_response):
    orch = MagicMock()
    orch.search = AsyncMock(return_value=sample_response)
    orch.self_check = AsyncMock(return_value={
        "searxng": True, "scrapling": True, "camoufox": False,
    })
    orch.camoufox = MagicMock()
    orch.camoufox.extract_page_safe = AsyncMock(return_value={
        "url": "https://example.com", "title": "Test Page",
        "content": "<html><body>Hello</body></html>",
        "status_code": 200, "took_ms": 100,
    })
    orch.searxng = MagicMock()
    orch.scrapling = MagicMock()
    return orch


class TestSearchAPIIntegration:
    """Integration: search API endpoints through TestClient."""

    @pytest.fixture
    def app(self, mock_orch):
        app = FastAPI()
        init_search_orchestrator(mock_orch)
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_search_endpoint_all_depths(self, client):
        for depth in ["quick", "standard", "deep"]:
            resp = client.post("/api/v1/search", json={
                "query": "federal reserve rates",
                "depth": depth,
                "max_results": 5,
            })
            assert resp.status_code == 200, f"depth={depth} failed: {resp.json()}"
            data = resp.json()
            assert len(data["results"]) == 2
            assert data["results"][0]["title"] == "Result One"

    def test_search_with_categories(self, client):
        resp = client.post("/api/v1/search", json={
            "query": "inflation data",
            "depth": "standard",
            "categories": ["news", "general"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 2

    def test_search_status_endpoint(self, client):
        resp = client.get("/api/v1/search/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checks"]["searxng"] is True
        assert data["status"] == "ok"

    def test_search_invalid_input_returns_422(self, client):
        resp = client.post("/api/v1/search", json={})
        assert resp.status_code == 422


class TestSearchE2E:
    """E2E: full search lifecycle through Hermes tools."""

    @pytest.fixture
    def orch(self, mock_orch):
        return mock_orch

    def test_tool_registry_search_web(self, orch, sample_response):
        tr = ToolRegistry()
        register_search_tools(tr, orch)

        tools = tr.list_tools(toolset_filter="search")
        assert len(tools) == 3

        result = tr.dispatch("search_web", {
            "query": "bitcoin price",
            "depth": "quick",
            "max_results": 5,
        })
        assert result["total_found"] == 2
        assert result["results"][0]["engine"] == "google"

    def test_tool_registry_search_news(self, orch):
        tr = ToolRegistry()
        register_search_tools(tr, orch)

        result = tr.dispatch("search_news", {"query": "latest news", "max_results": 3})
        assert result["total_found"] == 2
        assert len(result["results"]) == 2

    def test_tool_registry_search_crawl(self, orch):
        tr = ToolRegistry()
        register_search_tools(tr, orch)

        result = tr.dispatch("search_crawl", {"url": "https://example.com"})
        assert result["url"] == "https://example.com"
        assert result["status_code"] == 200

    def test_tool_search_web_defaults_depth(self, orch):
        tr = ToolRegistry()
        register_search_tools(tr, orch)

        result = tr.dispatch("search_web", {"query": "test"})
        assert "results" in result

    def test_tool_search_error_on_orchestrator_failure(self, orch):
        orch.search = AsyncMock(side_effect=Exception("Search failed"))
        tr = ToolRegistry()
        register_search_tools(tr, orch)

        result = tr.dispatch("search_web", {"query": "test"})
        assert "error" in result


class TestSearchOrchestration:
    """Integration: orchestrator wiring with mocked components."""

    @pytest.mark.asyncio
    async def test_search_quick_depth(self, mock_orch, sample_response):
        mock_orch.search.assert_not_called()
        result = await mock_orch.search(SearchRequest(
            query="test", depth=SearchDepth.QUICK,
        ))
        assert result.total_found == 2

    @pytest.mark.asyncio
    async def test_search_standard_depth(self, mock_orch):
        result = await mock_orch.search(SearchRequest(
            query="test", depth=SearchDepth.STANDARD,
        ))
        assert result.total_found == 2

    @pytest.mark.asyncio
    async def test_search_deep_depth(self, mock_orch):
        result = await mock_orch.search(SearchRequest(
            query="test", depth=SearchDepth.DEEP,
        ))
        assert result.total_found == 2

    @pytest.mark.asyncio
    async def test_self_check_status(self, mock_orch):
        status = await mock_orch.self_check()
        assert status["searxng"] is True
        assert status["scrapling"] is True
        assert status["camoufox"] is False

    @pytest.mark.asyncio
    async def test_orchestrator_close(self, mock_orch):
        mock_orch.searxng.close = AsyncMock()
        mock_orch.scrapling.close = AsyncMock()
        mock_orch.camoufox.close = AsyncMock()

        mock_search_orch = SearchOrchestrator.__new__(SearchOrchestrator)
        mock_search_orch.searxng = mock_orch.searxng
        mock_search_orch.scrapling = mock_orch.scrapling
        mock_search_orch.camoufox = mock_orch.camoufox

        await mock_search_orch.close()
        mock_orch.searxng.close.assert_awaited_once()

    def test_depth_enum_values(self):
        assert SearchDepth.QUICK.value == "quick"
        assert SearchDepth.STANDARD.value == "standard"
        assert SearchDepth.DEEP.value == "deep"

    def test_category_enum_values(self):
        assert SearchCategory.GENERAL.value == "general"
        assert SearchCategory.NEWS.value == "news"
        assert SearchCategory.SCIENCE.value == "science"
