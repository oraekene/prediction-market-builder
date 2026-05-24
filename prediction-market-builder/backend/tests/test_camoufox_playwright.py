from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agentic_search.camoufox_playwright import CamoufoxCrawler


@pytest.fixture
def crawler():
    return CamoufoxCrawler(headless=True, max_concurrent_pages=1)


@pytest.mark.asyncio
async def test_available_no_camoufox(crawler):
    with patch.dict("sys.modules", {"camoufox": None, "playwright": None}):
        available = await crawler.available()
        assert available is False


@pytest.mark.asyncio
async def test_block_resources_blocks_images():
    crawler = CamoufoxCrawler()
    route = MagicMock()
    route.request.resource_type = "image"
    await crawler._block_resources(route)
    route.abort.assert_awaited_once()


@pytest.mark.asyncio
async def test_block_resources_allows_document():
    crawler = CamoufoxCrawler()
    route = MagicMock()
    route.request.resource_type = "document"
    await crawler._block_resources(route)
    route.continue_.assert_awaited_once()


@pytest.mark.asyncio
async def test_flatten_a11y_tree_empty(crawler):
    result = crawler._flatten_a11y_tree(None)
    assert result == []

    result = crawler._flatten_a11y_tree({})
    assert result == [{"role": "", "name": "", "value": "", "description": "", "depth": 0}]


@pytest.mark.asyncio
async def test_flatten_a11y_tree_with_children(crawler):
    node = {
        "role": "RootWebArea",
        "name": "Test Page",
        "children": [
            {"role": "heading", "name": "Title", "children": []},
            {"role": "button", "name": "Submit"},
        ],
    }
    result = crawler._flatten_a11y_tree(node)
    assert len(result) == 3
    assert result[0]["role"] == "RootWebArea"
    assert result[1]["role"] == "heading"
    assert result[2]["role"] == "button"
    assert result[1]["depth"] == 1
    assert result[2]["depth"] == 1


@pytest.mark.asyncio
async def test_close_no_browser(crawler):
    await crawler.close()
    assert crawler._browser is None


@pytest.mark.asyncio
async def test_close_with_browser(crawler):
    mock_browser = AsyncMock()
    crawler._browser = mock_browser
    await crawler.close()
    mock_browser.close.assert_awaited_once()
    assert crawler._browser is None


@pytest.mark.asyncio
async def test_extract_page_safe_timeout(crawler):
    async def slow_extract(url):
        await asyncio.sleep(100)
        return {}

    crawler.extract_page = slow_extract
    result = await crawler.extract_page_safe("https://example.com")
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_extract_page_safe_exception(crawler):
    async def failing_extract(url):
        raise ValueError("boom")

    crawler.extract_page = failing_extract
    result = await crawler.extract_page_safe("https://example.com")
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_ensure_browser_import_error(crawler):
    with patch.dict("sys.modules", {"camoufox": None}):
        with pytest.raises(ImportError):
            await crawler.ensure_browser()


@pytest.mark.asyncio
async def test_ensure_browser_launch_error(crawler):
    with patch("camoufox.PlaywrightCamoufox") as mock_camoufox:
        mock_camoufox.launch.side_effect = Exception("launch failed")
        with pytest.raises(Exception, match="launch failed"):
            await crawler.ensure_browser()
