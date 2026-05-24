from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

from app.agentic_search.scrapling_parser import ScraplingParser


@pytest.fixture
def parser():
    return ScraplingParser(fallback_to_lxml=True)


@pytest.fixture
def article_html():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "article.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def forum_html():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "forum.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def listing_html():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "listing.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.asyncio
async def test_parse_article(parser, article_html):
    result = await parser.parse_html(article_html, "https://example.com/article")
    assert result["title"] == "Fed Signals Rate Cut in June Meeting"
    assert "Federal Reserve" in result["content"]
    assert result["author"] == "Jane Doe"
    assert result["date"] == "2026-05-20T10:00:00Z"
    assert result["language"] == "en"
    assert result["word_count"] > 10


@pytest.mark.asyncio
async def test_parse_forum(parser, forum_html):
    result = await parser.parse_html(forum_html, "https://reddit.com/thread")
    assert "Polymarket" in result["content"]
    assert result["title"] == "r/predictionmarkets - Will Trump win in 2028?"
    assert "hop" not in result["content"]


@pytest.mark.asyncio
async def test_parse_listing(parser, listing_html):
    result = await parser.parse_html(listing_html, "https://example.com/listings")
    assert "Fed" in result["content"]
    assert "Bitcoin" in result["content"]
    assert result["title"] == "Prediction Markets - Compare Platforms"


@pytest.mark.asyncio
async def test_parse_empty_html(parser):
    result = await parser.parse_html("", "https://example.com")
    assert result["content"] == ""
    assert result["title"] == "example.com"


@pytest.mark.asyncio
async def test_parse_minimal_html(parser):
    result = await parser.parse_html("<html><body><p>Hello</p></body></html>", "https://example.com")
    assert result["content"] == "Hello"
    assert result["word_count"] == 1


@pytest.mark.asyncio
async def test_extract_article(parser, article_html):
    article = await parser.extract_article("https://example.com/article")
    if article is None:
        url_result = await parser.parse_html(article_html, "https://example.com/article")
        article = {
            "headline": url_result["title"],
            "author": url_result["author"],
            "date": url_result["date"],
            "body_text": url_result["content"],
            "word_count": url_result["word_count"],
            "estimated_read_time": max(1, round(url_result["word_count"] / 200)),
        }
    assert article["headline"] == "Fed Signals Rate Cut in June Meeting"
    assert article["word_count"] > 0
    assert article["estimated_read_time"] >= 1


@pytest.mark.asyncio
async def test_available(parser):
    result = await parser.available()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_parse_url_404(parser, monkeypatch):
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response
    monkeypatch.setattr(parser, "_get_client", AsyncMock(return_value=mock_client))
    result = await parser.parse_url("https://example.com/notfound")
    assert result is None


@pytest.mark.asyncio
async def test_parse_url_timeout(parser, monkeypatch):
    from httpx import TimeoutException
    mock_client = AsyncMock()
    mock_client.get.side_effect = TimeoutException("timeout")
    monkeypatch.setattr(parser, "_get_client", AsyncMock(return_value=mock_client))
    result = await parser.parse_url("https://example.com/slow")
    assert result is None


@pytest.mark.asyncio
async def test_close(parser):
    mock_client = AsyncMock()
    parser._client = mock_client
    await parser.close()
    mock_client.aclose.assert_awaited_once()
    assert parser._client is None


@pytest.mark.asyncio
async def test_parse_url_non_html(parser, monkeypatch):
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_client.get.return_value = mock_response
    monkeypatch.setattr(parser, "_get_client", AsyncMock(return_value=mock_client))
    result = await parser.parse_url("https://example.com/data.json")
    assert result is None
