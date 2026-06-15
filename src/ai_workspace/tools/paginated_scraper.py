"""
Paginated scraper tool — navigates multi-page SPAs by clicking "next page".

Specialized for Receita Federal and similar government portals
that use paginated tables with "Próximo" / "Next" buttons.
"""

import os
import re
import time
from typing import Any, Type

from pydantic import BaseModel, Field

from crewai.tools import BaseTool


class PaginatedScraperInput(BaseModel):
    """Input for paginated scraper."""
    url: str = Field(description="URL of the first page")
    next_button_text: str = Field(
        default="Próximo",
        description="Text on the 'next page' button (e.g., 'Próximo', 'Next', '>')"
    )
    max_pages: int = Field(default=20, description="Maximum pages to scrape")
    wait_per_page: int = Field(default=3, description="Seconds to wait per page for JS rendering")
    max_length: int = Field(default=15000, description="Max characters to return")


class PaginatedScraperTool(BaseTool):
    """Scrapes multi-page SPAs by clicking 'next page' buttons.

    Use this for portals with paginated lists (e.g., Receita Federal
    editais that show 20 lots per page across many pages).
    """

    name: str = "paginated_scraper"
    description: str = (
        "Opens a URL and clicks the 'next page' button repeatedly "
        "to scrape multi-page tables. Returns concatenated text from all pages. "
        "Use this when you need data from ALL pages of a paginated list, "
        "like Receita Federal lots that span 13+ pages."
    )
    args_schema: Type[BaseModel] = PaginatedScraperInput

    def _run(
        self,
        url: str,
        next_button_text: str = "Próximo",
        max_pages: int = 20,
        wait_per_page: int = 3,
        max_length: int = 15000,
    ) -> str:
        """Scrape all pages."""
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
            import concurrent.futures
            import asyncio
        except ImportError:
            return "ERROR: Playwright not installed."

        try:
            # Check for asyncio event loop
            try:
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        self._scrape_sync, url, next_button_text,
                        max_pages, wait_per_page, max_length
                    )
                    return future.result(timeout=120)
            except RuntimeError:
                return self._scrape_sync(
                    url, next_button_text, max_pages, wait_per_page, max_length
                )

        except Exception as e:
            return f"SCRAPER ERROR: {type(e).__name__}: {e}"

    def _scrape_sync(
        self, url: str, next_button_text: str,
        max_pages: int, wait_per_page: int, max_length: int
    ) -> str:
        """Synchronous scraping."""
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

        all_text = []
        current_page = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-dev-shm-usage", "--disable-gpu"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="pt-BR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(wait_per_page * 1000)

                while current_page < max_pages:
                    current_page += 1

                    # Extract current page text
                    text = page.evaluate("""() => {
                        const body = document.body;
                        if (!body) return '';
                        return body.innerText || body.textContent || '';
                    }""")

                    # Also extract tables
                    tables = page.evaluate("""() => {
                        const tables = document.querySelectorAll('table');
                        return Array.from(tables).map(t => {
                            const rows = t.querySelectorAll('tr');
                            return Array.from(rows).map(r => {
                                const cells = r.querySelectorAll('td, th');
                                return Array.from(cells).map(c => c.innerText.trim());
                            });
                        });
                    }""")

                    all_text.append(f"\n=== PAGE {current_page} ===")

                    # Add table data more concisely
                    if tables:
                        for ti, table in enumerate(tables):
                            if not table:
                                continue
                            all_text.append(f"\nTable {ti + 1}:")
                            for row in table[:50]:
                                all_text.append(" | ".join(row))
                    else:
                        # Just add extracted text
                        text = re.sub(r"\n{4,}", "\n\n", text or "")
                        all_text.append(text[:3000])

                    # Check if there's a "next" button
                    next_btn = None
                    try:
                        # Try multiple selectors
                        for selector in [
                            f"button:has-text('{next_button_text}')",
                            f"a:has-text('{next_button_text}')",
                            f"span:has-text('{next_button_text}')",
                            "button[aria-label='Next']",
                            "button[aria-label='Próximo']",
                            "a[aria-label='Próxima página']",
                            "li.next:not(.disabled) a",
                            ".pagination .next a",
                            "button.mat-paginator-navigation-next:not([disabled])",
                        ]:
                            try:
                                btn = page.locator(selector).first
                                if btn.is_visible():
                                    next_btn = btn
                                    break
                            except Exception:
                                continue

                    except Exception:
                        pass

                    if next_btn is None or current_page >= max_pages:
                        break

                    # Click next page
                    try:
                        next_btn.click()
                        page.wait_for_timeout(wait_per_page * 1000)
                    except Exception:
                        # Try URL-based pagination
                        current_url = page.url
                        if "page=" in current_url or "pagina=" in current_url:
                            import re as regex
                            new_url = regex.sub(
                                r'(page[=_])(\d+)',
                                rf'\g<1>{current_page}',
                                current_url
                            )
                            page.goto(new_url, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(wait_per_page * 1000)
                        else:
                            break

                result = "\n".join(all_text)
                return f"Scraped {current_page} pages.\n\n{result[:max_length]}"

            finally:
                browser.close()
