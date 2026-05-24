from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


class ScraplingParser:
    def __init__(
        self,
        max_content_length: int = 100_000,
        fallback_to_lxml: bool = True,
        request_timeout: int = 15,
    ):
        self.max_content_length = max_content_length
        self.fallback_to_lxml = fallback_to_lxml
        self.request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None
        self._available: bool | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.request_timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                },
            )
        return self._client

    async def parse_url(self, url: str) -> dict[str, Any] | None:
        try:
            client = await self._get_client()
            resp = await client.get(url)
            if resp.status_code == 404:
                logger.info("URL returned 404: %s", url)
                return None
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                logger.debug("Skipping non-HTML content: %s", content_type)
                return None
            return await self.parse_html(resp.text, url)
        except httpx.TimeoutException:
            logger.warning("Timeout fetching URL: %s", url)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("HTTP error %s for URL: %s", e.response.status_code, url)
            return None
        except httpx.RequestError as e:
            logger.warning("Request error for URL %s: %s", url, e)
            return None

    async def parse_html(self, html: str, url: str) -> dict[str, Any]:
        scrapling = None
        if self._available is None or self._available:
            try:
                import importlib
                scrapling = importlib.import_module("scrapling")
            except ImportError:
                self._available = False
                scrapling = None

        if scrapling and hasattr(scrapling, "AdaptiveParser"):
            self._available = True
            try:
                parser = scrapling.AdaptiveParser()
                result = parser.parse(html)
                content = self._extract_scrapling(result)
            except Exception as e:
                logger.warning("Scrapling parse failed, falling back: %s", e)
                content = self._fallback_extract(html)
        elif self.fallback_to_lxml:
            content = self._fallback_extract(html)
        else:
            content = self._basic_extract(html)

        title = self._extract_title(html, url)
        author = self._extract_meta(html, "author")
        date = (
            self._extract_meta(html, "article:published_time")
            or self._extract_meta(html, "date")
        )
        language = self._extract_language(html)

        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]

        snippet = content[:200].strip()

        return {
            "url": url,
            "title": title,
            "content": content,
            "snippet": snippet,
            "author": author,
            "date": date,
            "language": language,
            "word_count": len(content.split()),
        }

    async def extract_article(self, url: str) -> dict[str, Any] | None:
        result = await self.parse_url(url)
        if result is None:
            return None
        wc = result.get("word_count", 0)
        read_time_min = max(1, round(wc / 200))
        return {
            "headline": result.get("title", ""),
            "author": result.get("author"),
            "date": result.get("date"),
            "body_text": result.get("content", ""),
            "word_count": wc,
            "estimated_read_time": read_time_min,
        }

    async def available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import importlib
            importlib.import_module("scrapling")
            self._available = True
        except ImportError:
            self._available = False
        return self._available

    def _extract_scrapling(self, result: Any) -> str:
        try:
            text_methods = ["get_text", "text", "extract_text", "__str__"]
            for method in text_methods:
                if hasattr(result, method):
                    text = getattr(result, method)()
                    if isinstance(text, str) and text.strip():
                        return " ".join(text.split())
            return str(result)
        except Exception:
            return ""

    def _fallback_extract(self, html: str) -> str:
        try:
            from lxml import html as lxml_html
            from lxml.html import cleanup
            tree = lxml_html.fromstring(html)
            cleanup.cleanup_html(tree)
            for tag in tree.xpath("//script | //style | //nav | //footer | //header | //noscript | //aside"):
                tag.getparent().remove(tag)
            body = tree.find(".//body") or tree.find(".//article") or tree
            text = body.text_content() if hasattr(body, "text_content") else lxml_html.tostring(body, encoding="unicode")
            return " ".join(text.split())
        except Exception:
            return self._basic_extract(html)

    def _basic_extract(self, html: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_title(self, html: str, url: str) -> str:
        import re
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
            if title:
                return title
        m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html)
        if m:
            return m.group(1)
        parsed = urlparse(url)
        return parsed.netloc

    def _extract_meta(self, html: str, name: str) -> str | None:
        import re
        patterns = [
            rf'<meta[^>]+name=["\']{name}["\'][^>]+content=["\']([^"\']+)',
            rf'<meta[^>]+property=["\']{name}["\'][^>]+content=["\']([^"\']+)',
            rf'<meta[^>]+content=["\']([^"\']+)[^>]+name=["\']{name}["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _extract_language(self, html: str) -> str:
        import re
        m = re.search(r'<html[^>]*\blang=["\']([a-z]+)', html, re.IGNORECASE)
        if m:
            return m.group(1)
        return "en"

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
