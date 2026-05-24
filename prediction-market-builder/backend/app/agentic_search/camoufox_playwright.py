from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_RESOURCE_BLOCKLIST = ["image", "media", "font", "stylesheet"]


class CamoufoxCrawler:
    def __init__(
        self,
        headless: bool = True,
        viewport: dict | None = None,
        timeout: int = 30000,
        max_scrolls: int = 0,
        max_concurrent_pages: int = 2,
    ):
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 720}
        self.timeout = timeout
        self.max_scrolls = max_scrolls
        self.max_concurrent_pages = max_concurrent_pages
        self._browser: Any = None
        self._playwright: Any = None
        self._semaphore: asyncio.Semaphore | None = None

    async def ensure_browser(self):
        if self._browser is not None:
            return
        try:
            from camoufox import PlaywrightCamoufox
            self._playwright = PlaywrightCamoufox
            self._browser = await PlaywrightCamoufox.launch(
                headless=self.headless,
                humanize_mouse=True,
                screen={"width": self.viewport["width"], "height": self.viewport["height"]},
            )
            self._semaphore = asyncio.Semaphore(self.max_concurrent_pages)
            logger.info("Camoufox browser launched successfully")
        except ImportError as e:
            logger.error("Camoufox/Playwright not installed: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to launch Camoufox browser: %s", e)
            raise

    async def extract_page(self, url: str) -> dict[str, Any]:
        await self.ensure_browser()
        async with self._semaphore:
            page = None
            context = None
            start = time.monotonic()
            try:
                context = await self._browser.new_context(
                    viewport=self.viewport,
                    user_agent=None,
                    locale="en-US",
                    timezone_id="America/New_York",
                )
                await context.route("**/*", self._block_resources)
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)
                await self._scroll_page(page)
                page_title = await page.title()
                page_url = page.url
                a11y_tree = None
                try:
                    a11y_snapshot = await page.accessibility.snapshot()
                    a11y_tree = self._flatten_a11y_tree(a11y_snapshot) if a11y_snapshot else None
                except Exception as e:
                    logger.debug("Accessibility tree extraction failed: %s", e)
                content = None
                try:
                    content = await page.content()
                except Exception as e:
                    logger.debug("Page content extraction failed: %s", e)
                status_code = None
                try:
                    status_code = await page.evaluate("window.performance.getEntriesByType('resource')[0]?.responseStatus")
                except Exception:
                    pass
                screenshot_b64 = None
                took_ms = int((time.monotonic() - start) * 1000)
                return {
                    "url": page_url,
                    "title": page_title,
                    "content": content,
                    "accessibility_tree": a11y_tree,
                    "status_code": status_code or 200,
                    "took_ms": took_ms,
                }
            except Exception as e:
                took_ms = int((time.monotonic() - start) * 1000)
                return {
                    "url": url,
                    "title": "",
                    "content": None,
                    "accessibility_tree": None,
                    "status_code": 0,
                    "took_ms": took_ms,
                    "error": str(e),
                }
            finally:
                if page is not None:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass

    async def extract_page_safe(self, url: str) -> dict[str, Any]:
        try:
            result = await asyncio.wait_for(
                self.extract_page(url),
                timeout=self.timeout / 1000 + 5,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("extract_page timed out for URL: %s", url)
            return {
                "url": url,
                "title": "",
                "content": None,
                "accessibility_tree": None,
                "status_code": 0,
                "took_ms": self.timeout,
                "error": "Timeout",
            }
        except Exception as e:
            logger.warning("extract_page_safe failed for URL %s: %s", url, e)
            return {
                "url": url,
                "title": "",
                "content": None,
                "accessibility_tree": None,
                "status_code": 0,
                "took_ms": 0,
                "error": str(e),
            }

    async def close(self):
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
            self._browser = None
            self._playwright = None
            logger.info("Camoufox browser closed")

    async def available(self) -> bool:
        try:
            import importlib
            importlib.import_module("camoufox")
            importlib.import_module("playwright")
            return True
        except ImportError:
            return False

    async def _block_resources(self, route: Any):
        resource_type = route.request.resource_type
        if resource_type in _RESOURCE_BLOCKLIST:
            await route.abort()
        else:
            await route.continue_()

    async def _scroll_page(self, page: Any):
        for _ in range(self.max_scrolls):
            try:
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            except Exception:
                break

    def _flatten_a11y_tree(self, node: Any, depth: int = 0) -> list[dict]:
        if not node or not isinstance(node, dict):
            return []
        result = [{
            "role": node.get("role", ""),
            "name": node.get("name", ""),
            "value": node.get("value", ""),
            "description": node.get("description", ""),
            "depth": depth,
        }]
        for child in node.get("children", []):
            result.extend(self._flatten_a11y_tree(child, depth + 1))
        return result
