"""
Web fetch tool for CrewAI agents.

Fetches a URL and returns extracted text content from raw HTML.
For SPA pages, tries API endpoint patterns automatically.
"""

import json
import re
from typing import Any, Type

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from crewai.tools import BaseTool


class WebFetchInput(BaseModel):
    """Input schema for WebFetchTool."""
    url: str = Field(description="URL to fetch and extract text from")
    extract_text: bool = Field(default=True, description="Extract visible text from HTML")
    max_length: int = Field(default=5000, description="Maximum characters to return")


class WebFetchTool(BaseTool):
    """Fetches a URL and returns its text content.

    Handles static HTML, JSON APIs, and SPA pages by auto-detecting
    and trying alternative API endpoint patterns.
    """

    name: str = "web_fetch"
    description: str = (
        "Fetches a URL and returns its visible text content. "
        "Use this to read web pages, API responses, or any HTTP resource. "
        "For SPA/Angular pages, it automatically tries API endpoints."
    )
    args_schema: Type[BaseModel] = WebFetchInput

    def _run(self, url: str, extract_text: bool = True, max_length: int = 5000) -> str:
        """Execute the web fetch."""
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(
                    url,
                    headers={
                        "Accept": "text/html,application/json,application/xhtml+xml,*/*",
                        "User-Agent": "Mozilla/5.0 AIWorkspace/1.0 DeepResearch",
                        "Accept-Language": "pt-BR,en;q=0.9",
                    },
                )
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            # If it's JSON, return formatted
            if "application/json" in content_type:
                data = response.json()
                return json.dumps(data, indent=2, ensure_ascii=False)[:max_length]

            # Parse HTML
            html = response.text
            if not extract_text:
                return html[:max_length]

            soup = BeautifulSoup(html, "lxml")

            # Remove script, style, nav, footer, header
            for tag in soup(["script", "style", "nav", "footer", "header", "svg"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)

            # Detect SPA pages
            is_spa = bool(
                soup.find("sle-app") or
                soup.find("app-root") or
                soup.find("div", id="root") or
                soup.find("script", src=lambda s: s and ("main-" in s or "polyfills" in s))
            )

            if not is_spa:
                return text[:max_length]

            # SPA detected — try API endpoints
            api_result = self._try_api_endpoints(url, response, max_length)
            if api_result:
                return api_result[:max_length]

            # All API attempts failed — return honest error message
            return (
                "SPA PAGE — DATA NOT ACCESSIBLE\n\n"
                f"URL: {url}\n"
                "This is a JavaScript single-page application. "
                "The page content cannot be read without a browser.\n"
                "Tried API endpoints but all returned errors.\n\n"
                "DO NOT INVENT the data. Report honestly that it is inaccessible."
            )

        except httpx.HTTPStatusError as e:
            return f"HTTP {e.response.status_code} fetching {url}: {e.response.text[:300]}"
        except httpx.TimeoutException:
            return f"TIMEOUT fetching {url} (30s limit). Page too slow or unreachable."
        except Exception as e:
            return f"Error fetching {url}: {type(e).__name__}: {e}"

    def _try_api_endpoints(self, url: str, response: httpx.Response, max_length: int) -> str:
        """Try API endpoint alternatives for SPA pages."""
        api_urls = []
        if "/portal/" in url:
            api_urls.append(url.replace("/portal/", "/api/"))

        for api_url in api_urls:
            try:
                resp = httpx.get(
                    api_url,
                    headers={
                        "Accept": "application/json,*/*",
                        "User-Agent": "Mozilla/5.0 AIWorkspace/1.0",
                    },
                    timeout=15.0,
                )

                if resp.status_code == 200:
                    if "application/json" in resp.headers.get("content-type", ""):
                        data = resp.json()
                        return json.dumps(data, indent=2, ensure_ascii=False)
                    if resp.text.strip().startswith("{"):
                        return resp.text

                # Record the error for the final message
                return f"API ENDPOINT ERROR: {api_url} returned HTTP {resp.status_code}. Response: {resp.text[:300]}"

            except Exception:
                continue

        return ""
