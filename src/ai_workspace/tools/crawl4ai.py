"""
Crawl4AI Tool — LLM-friendly web scraping with markdown output.

Uses crawl4ai-flake (Nix-packaged) for zero-cost, local web scraping.
Returns clean markdown optimized for LLM consumption.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ai_workspace.tools.base import Tool

logger = logging.getLogger("aiw.tools.crawl4ai")


class Crawl4AIInput(BaseModel):
    """Input schema for Crawl4AITool."""
    url: str = Field(..., description="URL to scrape")
    timeout: int = Field(30, description="Max wait time in seconds")


class Crawl4AITool(Tool):
    """Async web scraper producing LLM-optimized markdown.

    Features:
    - JavaScript rendering via Playwright
    - Clean markdown output (headings, tables, code blocks)
    - URL-based caching (no re-scrape)
    - Automatic domain extraction for source tracking
    """

    name: str = "crawl4ai_scrape"
    description: str = (
        "Scrape a URL and return clean markdown content. "
        "Handles JavaScript rendering. Best for getting readable content "
        "from any web page. Use this first before other web tools."
    )
    args_schema: type[BaseModel] = Crawl4AIInput

    def _run(self, url: str, timeout: int = 30) -> str:
        """Synchronous wrapper for async scrape."""
        try:
            result = asyncio.run(self._scrape_async(url, timeout))
            if result["status"] == "success":
                return result["content"] or f"Scraped {url} but got empty content."
            return f"Failed to scrape {url}: {result['error']}"
        except ImportError:
            return "crawl4ai not installed. Install via crawl4ai-flake."
        except Exception as e:
            return f"Scrape error for {url}: {e}"

    async def _scrape_async(self, url: str, timeout: int = 30) -> dict[str, Any]:
        """Internal async scrape method."""
        domain = urlparse(url).netloc.lower().replace("www.", "")

        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=url,
                    timeout=timeout,
                    cache_mode="by_url",
                )

            content = result.markdown if result.markdown else ""
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
