"""
ScrapingChain — hierarchical web scraping with automatic fallback.

Priority order (cheapest → most expensive):
1. WebFetchTool     (static HTML, $0, fast)
2. Crawl4AITool     (JS rendering, markdown, $0, medium)
3. HeadlessBrowser  (real browser for SPAs, $0, slow)
4. BrowserUseAgent  (autonomous navigation, $0, very slow)
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from ai_workspace.tools.base import Tool

logger = logging.getLogger("aiw.tools.scraping_chain")


class ScrapingChainInput(BaseModel):
    url: str = Field(description="URL to scrape")
    max_steps: int = Field(
        default=3,
        description="Max fallback steps (1-4). 1 = only primary tool, 4 = try all.",
    )
    timeout: int = Field(default=30, description="Timeout per tool in seconds")


class ScrapingChainTool(Tool):
    """Intelligently scrape any URL using the cheapest tool that works.

    Automatically falls back through the tool hierarchy:
    WebFetch → Crawl4AI → HeadlessBrowser → BrowserUse
    """

    name: str = "scrape"
    description: str = (
        "Scrape a URL using the best available tool. Automatically falls back "
        "if a tool fails (e.g., static HTML fetcher can't handle JavaScript). "
        "Returns clean markdown or structured text. Use this as the primary "
        "web scraping tool — it picks the right tool for you."
    )

    def _run(
        self,
        url: str,
        max_steps: int = 3,
        timeout: int = 30,
    ) -> str:
        import time

        tools = self._get_tools()
        results: list[str] = []

        for i, tool in enumerate(tools[:max_steps]):
            tool_name = tool.__class__.__name__
            logger.info("ScrapingChain: trying %s for %s (step %d/%d)",
                        tool_name, url, i + 1, max_steps)

            try:
                start = time.monotonic()
                result = tool._run(url=url, timeout=min(timeout, 30))
                elapsed = time.monotonic() - start

                # Check if the tool actually returned useful content
                if result and not result.startswith("") and not result.startswith("Error"):
                    logger.info("ScrapingChain: %s succeeded (%.1fs, %d chars)",
                              tool_name, elapsed, len(result))
                    return f"[via {tool_name}]\n\n{result}"

                results.append(f"{tool_name}: {result[:200]}")
            except Exception as e:
                results.append(f"{tool_name}: {e}")

        return (
            f"All {max_steps} scraping tools failed for {url}:\n" +
            "\n".join(f"  - {r}" for r in results)
        )

    def _get_tools(self) -> list[Tool]:
        """Return available scraping tools in priority order."""
        tools: list[Tool] = []

        # 1. WebFetch — static HTML, fastest
        try:
            from ai_workspace.tools import WebFetchTool
            tools.append(WebFetchTool())
        except ImportError:
            pass

        # 2. Crawl4AI — JS rendering, markdown output
        try:
            from ai_workspace.tools import Crawl4AITool
            tools.append(Crawl4AITool())
        except ImportError:
            pass

        # 3. HeadlessBrowser — real browser for SPAs
        try:
            from ai_workspace.tools import HeadlessBrowserTool
            tools.append(HeadlessBrowserTool())
        except ImportError:
            pass

        # 4. BrowserUseAgent — autonomous navigation
        try:
            from ai_workspace.tools import BrowserUseAgentTool
            tools.append(BrowserUseAgentTool())
        except ImportError:
            pass

        return tools
