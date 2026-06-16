"""
Browser agent tool — wraps the `browser-use` library to give agents
a fully autonomous browser (click, type, navigate, extract, fill forms).

This is the high-level tool from the v2 spec. For a thin MCP-style
"give me 70+ raw Playwright tools" experience, use
`HeadlessBrowserTool` from `headless_browser.py` instead.

Install the dependency with:
    pip install browser-use
    playwright install chromium
"""

from __future__ import annotations

import os
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class BrowserUseAgentInput(BaseModel):
    task: str = Field(
        description=(
            "Natural-language task for the browser agent. "
            "Example: 'Find the top 5 trending AI papers on Hacker News and return their titles and links.' "
            "Example: 'Log in to example.com with credentials user@test.com / secret123 and download the report.'"
        )
    )
    max_steps: int = Field(default=20, description="Max steps the agent can take before giving up")
    headless: bool = Field(default=True, description="Run browser without a visible window")


class BrowserUseAgentTool(BaseTool):
    name: str = "browser_agent"
    description: str = (
        "Run an autonomous browser agent powered by the browser-use library. "
        "Use this when a website is a SPA (React/Angular/Vue), requires interaction "
        "(clicking, filling forms, logging in), or any task that is impractical with raw fetch. "
        "The agent will use the configured LLM to reason about page state and take actions. "
        "Returns the agent's final summary as a string."
    )
    args_schema: Type[BaseModel] = BrowserUseAgentInput

    def _run(self, task: str, max_steps: int = 20, headless: bool = True) -> str:
        try:
            from browser_use import Agent  # type: ignore
        except ImportError:
            return (
                "❌ browser-use is not installed. "
                "Install with: pip install browser-use && playwright install chromium"
            )

        # Pick an LLM based on available providers
        llm = _pick_llm()
        if llm is None:
            return (
                "❌ No LLM configured for the browser agent. "
                "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_HOST, or use ChatBrowserUse()."
            )

        try:
            import asyncio

            async def _run() -> str:
                agent = Agent(
                    task=task,
                    llm=llm,
                    headless=headless,
                    max_actions_per_step=4,
                )
                history = await agent.run(max_steps=max_steps)
                # history may be list of steps or an object with .final_result()
                if hasattr(history, "final_result"):
                    return history.final_result() or "(agent finished with no result)"
                if isinstance(history, list) and history:
                    last = history[-1]
                    return getattr(last, "result", None) or str(last)
                return str(history)

            return asyncio.run(_run())
        except Exception as e:
            return f"❌ Browser agent failed: {e}"


def _pick_llm() -> Any:
    """Pick the best available LLM for the browser agent.

    Priority:
    1. ChatBrowserUse (browser-use's own optimized model)
    2. Anthropic (claude-3-7-sonnet — best for browser reasoning)
    3. OpenAI (gpt-4o — second best)
    4. Ollama local (qwen3:14b or similar)
    """
    try:
        from browser_use import ChatBrowserUse  # type: ignore

        return ChatBrowserUse()
    except Exception:
        pass

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from browser_use import ChatAnthropic  # type: ignore

            return ChatAnthropic(model="claude-3-7-sonnet-20250219")
        except Exception:
            pass

    if os.getenv("OPENAI_API_KEY"):
        try:
            from browser_use import ChatOpenAI  # type: ignore

            return ChatOpenAI(model="gpt-4o")
        except Exception:
            pass

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    if ollama_host:
        try:
            from browser_use import ChatOllama  # type: ignore

            return ChatOllama(model="qwen3:14b", host=ollama_host)
        except Exception:
            pass

    return None


def get_browser_agent_tool() -> BaseTool:
    """Return the browser agent tool for agent wiring."""
    return BrowserUseAgentTool()


__all__ = ["BrowserUseAgentTool", "get_browser_agent_tool"]
