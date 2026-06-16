"""
Crawl4AI Tool — LLM-friendly web scraping with markdown output.

Uses crawl4ai-flake (Nix-packaged) for zero-cost, local web scraping.
Returns clean markdown optimized for LLM consumption.

Usage:
    from ai_workspace.tools.crawl4ai import Crawl4AITool
    tool = Crawl4AITool()
    result = await tool.scrape("https://example.com")
    print(result["content"])  # clean markdown
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("aiw.tools.crawl4ai")


class Crawl4AITool:
    """Async web scraper producing LLM-optimized markdown.

    Features:
    - JavaScript rendering via Playwright
    - Clean markdown output (headings, tables, code blocks)
    - URL-based caching (no re-scrape)
    - Automatic domain extraction for source tracking
    """

    def __init__(self):
        self._crawler = None

    async def _get_crawler(self):
        """Lazy-init the crawler (Playwright is heavy)."""
        if self._crawler is None:
            try:
                from crawl4ai import AsyncWebCrawler
                self._crawler = AsyncWebCrawler()
                logger.info("Crawl4AI initialized")
            except ImportError:
                raise ImportError(
                    "crawl4ai not installed. Add crawl4ai-flake to your Nix inputs: "
                    "https://github.com/daviaaze/crawl4ai-flake"
                )
        return self._crawler

    async def scrape(
        self,
        url: str,
        *,
        timeout: int = 30,
        max_content_length: int = 50_000,
    ) -> dict[str, Any]:
        """Scrape a URL and return clean markdown + metadata.

        Args:
            url: Target URL to scrape
            timeout: Max wait time in seconds
            max_content_length: Truncate content to this many chars

        Returns:
            dict with keys: url, content (markdown), title, domain,
            status, error (if failed)
        """
        domain = urlparse(url).netloc.lower().replace("www.", "")

        try:
            crawler = await self._get_crawler()
            async with crawler:
                result = await crawler.arun(
                    url=url,
                    timeout=timeout,
                    cache_mode="by_url",  # Don't re-scrape same URL
                )

            content = result.markdown[:max_content_length] if result.markdown else ""

            return {
                "url": url,
                "content": content,
                "title": result.metadata.get("title", "") if hasattr(result, "metadata") else "",
                "domain": domain,
                "status": "success",
                "error": None,
            }

        except Exception as e:
            logger.warning("Crawl4AI scrape failed for %s: %s", url, e)
            return {
                "url": url,
                "content": "",
                "title": "",
                "domain": domain,
                "status": "error",
                "error": str(e),
            }

    async def scrape_multiple(
        self,
        urls: list[str],
        *,
        timeout: int = 30,
        max_concurrent: int = 3,
    ) -> list[dict[str, Any]]:
        """Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            timeout: Per-URL timeout
            max_concurrent: Max parallel scrapes

        Returns:
            List of result dicts (same format as scrape())
        """
        import asyncio

        sem = asyncio.Semaphore(max_concurrent)

        async def _scrape_one(url: str) -> dict[str, Any]:
            async with sem:
                return await self.scrape(url, timeout=timeout)

        return await asyncio.gather(*[_scrape_one(u) for u in urls])
