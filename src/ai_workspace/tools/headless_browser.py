"""
Headless browser tool using Playwright.

Renders JavaScript SPA pages, waits for content to load,
and returns the visible text. Use this for pages that
web_fetch can't handle (Angular, React, Vue apps).
"""

import re

from pydantic import BaseModel, Field

from ai_workspace.tools.base import Tool


class HeadlessBrowserInput(BaseModel):
    """Input schema for HeadlessBrowserTool."""
    url: str = Field(description="URL to open in the browser")
    max_length: int = Field(default=8000, description="Maximum characters to return")
    wait_selector: str = Field(
        default="",
        description="CSS selector to wait for before extracting text (e.g., 'table', '.item-list')"
    )
    wait_time: int = Field(
        default=3,
        description="Extra seconds to wait after page loads (for JS rendering)"
    )


class HeadlessBrowserTool(Tool):
    """Renders a web page using a real browser (Chromium via Playwright).

    Unlike web_fetch which only gets raw HTML, this tool runs JavaScript
    and waits for dynamic content to load. Use this for:
    - Angular/React/Vue SPA pages (Receita Federal, gov.br portals)
    - Pages that show 'Carregando...' with web_fetch
    - Any page that requires JavaScript to display content
    """

    name: str = "headless_browser"
    description: str = (
        "Opens a URL in a real Chromium browser, runs JavaScript, "
        "waits for content to load, and returns the visible text. "
        "Use this for SPA/Angular pages that web_fetch can't read. "
        "This is the only tool that can access JavaScript-heavy sites "
        "like the Receita Federal portal (www25.receita.fazenda.gov.br)."
    )
    args_schema: type[BaseModel] = HeadlessBrowserInput

    def _run(
        self,
        url: str,
        max_length: int = 8000,
        wait_selector: str = "",
        wait_time: int = 3,
    ) -> str:
        """Render a page and return visible text."""
        try:
            import asyncio

            from playwright.async_api import async_playwright
            from playwright.sync_api import TimeoutError as PwTimeout
            from playwright.sync_api import sync_playwright

            # Check if we're inside an asyncio event loop
            try:
                asyncio.get_running_loop()
                # We're in async context — run Playwright sync in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        self._render_sync, url, max_length, wait_selector, wait_time
                    )
                    return future.result(timeout=60)
            except RuntimeError:
                # No running event loop — use sync API directly
                return self._render_sync(url, max_length, wait_selector, wait_time)

        except ImportError:
            return (
                "ERROR: Playwright not installed. "
                "Install with: pip install playwright"
            )
        except Exception as e:
            return f"BROWSER ERROR: {type(e).__name__}: {e}"

    def _render_sync(self, url: str, max_length: int, wait_selector: str, wait_time: int) -> str:
        """Render a page synchronously using Playwright sync API."""
        from playwright.sync_api import TimeoutError as PwTimeout
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
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
                except Exception as e:
                    browser.close()
                    return f"ERROR loading {url}: {e}"

                # Wait for dynamic content
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=15000)
                    except PwTimeout:
                        pass

                page.wait_for_timeout(wait_time * 1000)

                # Extract visible text
                text = page.evaluate("""() => {
                    const body = document.body;
                    if (!body) return '';
                    return body.innerText || body.textContent || '';
                }""")

                # Also extract tables
                table_data = ""
                try:
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
                    if tables and any(tables):
                        table_data = "\n\n=== TABLE DATA ===\n"
                        for ti, table in enumerate(tables):
                            if not table:
                                continue
                            table_data += f"\nTable {ti + 1}:\n"
                            for row in table[:30]:
                                table_data += " | ".join(row) + "\n"
                except Exception:
                    pass

                browser.close()

                text = re.sub(r"\n{4,}", "\n\n", text or "")
                text = re.sub(r"[ \t]{3,}", "  ", text or "")

                result = text.strip() or "(empty page)"
                if table_data:
                    result += table_data

                return result[:max_length]

        except Exception as e:
            return f"BROWSER ERROR: {type(e).__name__}: {e}"
