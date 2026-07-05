"""Agent Swarm — multi-agent patterns (now agent_loop-native).

After B3 migration (2026-07-03): all ``Crew(...).kickoff()`` calls replaced
by chained ``chat_sync`` calls.  SwarmConfig no longer creates crewai.LLM
objects — it resolves provider + model strings that ``chat_sync`` / ``agent_loop``
consume directly.

The old ``Agent`` / ``Crew`` / ``Task`` API is simulated via thin wrappers
so that existing callers (orchestrator, worker, cli, skills/loader) continue
to work.

.. note::
    Functions still return ``str`` (formerly ``Crew.kickoff()`` returned
    crewai's str-ifiable result, so downstream callers already called
    ``str(result)`` or used the result as a string — no breaking change).
"""

from __future__ import annotations

import asyncio
from typing import Any

from ai_workspace.providers import chat_sync

# ── Helpers ──────────────────────────────────────────────────


def _chat(
    provider: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
) -> str:
    """Single-turn chat wrapper (replaces Agent+Task+Crew for 1 agent)."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return chat_sync(
        messages,
        provider=provider,
        model=model,
        temperature=temperature,
    )


def _chain(provider: str, model_a: str, model_b: str, system_a: str, user_prompt: str, system_b: str) -> str:
    """Two-step chain (simulates hierarchical Crew with 2 agents).

    1. Agent A processes the user prompt → intermediate result.
    2. Agent B receives A's output as context and produces the final answer.
    """
    step_a = _chat(provider, model_a, system_a, user_prompt)
    step_b_input = f"Previous agent output:\n{step_a}\n\n{user_prompt}"
    return _chat(provider, model_b, system_b, step_b_input)


# ── SwarmConfig (backward-compatible API) ─────────────────────


class SwarmConfig:
    """Model resolution config — replaces crewai.LLM with provider+model strings.

    The ``deep_llm`` / ``coder_llm`` / ``fast_llm`` properties return dicts
    that can be unpacked into :func:`chat_sync` kwargs.

    Backward compat: existing callers that pass these to ``load_agent()``
    must be updated (load_agent now accepts dicts too).
    """

    def __init__(
        self,
        coder_model: str = "",
        default_model: str = "ollama/qwen3:14b",
        deep_model: str = "",
        provider: str | None = None,
    ):
        def _parse(model_str: str, fallback_provider: str = "ollama"):
            """Parse provider-prefixed model strings like 'deepseek/deepseek-chat'."""
            parts = model_str.split("/", 1)
            if len(parts) == 2 and parts[0] in {"deepseek", "gemini", "openrouter", "nvidia", "ollama"}:
                return parts[0], parts[1]
            # If provider is already set explicitly, use it
            if provider:
                return provider, parts[-1]
            return fallback_provider, parts[-1]

        fast_prov, fast_model = _parse(default_model)
        code_model = coder_model or default_model
        code_prov, code_model_resolved = _parse(code_model)
        deep_model_str = deep_model or code_model
        deep_prov, deep_model_resolved = _parse(deep_model_str)

        self.provider = fast_prov
        self.fast_llm = {"provider": fast_prov, "model": fast_model}
        self.coder_llm = {"provider": code_prov, "model": code_model_resolved}
        self.deep_llm = {"provider": deep_prov, "model": deep_model_resolved}


# ── Agent creation (returns dict — backward compat via dict API) ──


def _agent_system_prompt(name: str) -> str:
    """Look up the system prompt for a named agent role (matching agents.yaml).

    Kept in sync with the YAML definitions for each role so that
    :func:`chat_sync` receives the same system prompt that was
    previously injected via ``load_agent(…)``.
    """
    prompts = {
        "researcher": (
            "You are a world-class web researcher. Your goal is to find "
            "accurate, up-to-date information on any topic. Use search tools "
            "to fetch web pages and extract relevant data. Always cite sources. "
            "Be thorough, objective, and precise."
        ),
        "coder": (
            "You are a senior software engineer. Write clean, well-documented "
            "code. Read existing files before editing. Use tools to explore "
            "the codebase. Follow project conventions."
        ),
        "analyst": (
            "You are a strategic analyst. Review code and architecture "
            "for correctness, security, and performance. Provide actionable "
            "feedback and suggest improvements."
        ),
        "writer": (
            "You are a technical writer. Synthesise research into clear, "
            "well-structured reports. Use markdown formatting. Be concise "
            "but thorough."
        ),
        "planner": (
            "You are a senior technical architect. Break down complex tasks "
            "into actionable steps. Create structured execution plans."
        ),
        "general": (
            "You are a helpful AI assistant. Answer questions clearly and "
            "concisely. Use tools when needed."
        ),
    }
    return prompts.get(name, prompts["general"])


def create_researcher(cfg: SwarmConfig) -> dict[str, Any]:
    """Return a researcher agent dict (backward compat)."""
    return {**_agent_dict("researcher", cfg.deep_llm)}


def create_coder(cfg: SwarmConfig) -> dict[str, Any]:
    """Return a coder agent dict (backward compat)."""
    return {**_agent_dict("coder", cfg.coder_llm)}


def create_analyst(cfg: SwarmConfig) -> dict[str, Any]:
    """Return an analyst agent dict (backward compat)."""
    return {**_agent_dict("analyst", cfg.fast_llm)}


def create_writer(cfg: SwarmConfig) -> dict[str, Any]:
    """Return a writer agent dict (backward compat)."""
    return {**_agent_dict("writer", cfg.fast_llm)}


def create_planner(cfg: SwarmConfig) -> dict[str, Any]:
    """Return a planner agent dict (backward compat)."""
    return {**_agent_dict("planner", cfg.deep_llm)}


def _agent_dict(name: str, llm: dict[str, str]) -> dict[str, Any]:
    """Build a lightweight agent descriptor dict.

    Callers that previously received a ``crewai.Agent`` and accessed
    ``.role`` / ``.goal`` / ``.backstory`` can now use the dict keys.
    """
    return {
        "name": name,
        "system": _agent_system_prompt(name),
        "provider": llm["provider"],
        "model": llm["model"],
    }


# ── Crew functions (now return strings directly) ──────────────


def research_crew(
    query: str,
    cfg: SwarmConfig | None = None,
) -> str:
    """Research crew: researcher → writer (2-step chain)."""
    if cfg is None:
        cfg = SwarmConfig()

    return _chain(
        provider=cfg.provider,
        model_a=cfg.deep_llm["model"],
        model_b=cfg.fast_llm["model"],
        system_a=_agent_system_prompt("researcher"),
        user_prompt=f"Research the following topic thoroughly:\n\n{query}",
        system_b=_agent_system_prompt("writer"),
    )


def code_review_crew(
    files: str,
    cfg: SwarmConfig | None = None,
) -> str:
    """Code review crew: coder → analyst (2-step chain)."""
    if cfg is None:
        cfg = SwarmConfig()

    return _chain(
        provider=cfg.provider,
        model_a=cfg.coder_llm["model"],
        model_b=cfg.fast_llm["model"],
        system_a=_agent_system_prompt("coder"),
        user_prompt=(
            f"Review the following code and write a comprehensive review:\n\n{files}"
        ),
        system_b=_agent_system_prompt("analyst"),
    )


def daily_planning_crew(
    context: str,
    cfg: SwarmConfig | None = None,
) -> str:
    """Daily planning crew: planner → writer (2-step chain)."""
    if cfg is None:
        cfg = SwarmConfig()

    return _chain(
        provider=cfg.provider,
        model_a=cfg.deep_llm["model"],
        model_b=cfg.fast_llm["model"],
        system_a=_agent_system_prompt("planner"),
        user_prompt=f"Plan the following work and tasks:\n\n{context}",
        system_b=_agent_system_prompt("writer"),
    )


def coding_crew(
    task_description: str,
    cfg: SwarmConfig | None = None,
    working_dir: str = ".",
) -> str:
    """Coding crew: coder (single agent with tools context)."""
    if cfg is None:
        cfg = SwarmConfig()

    system = (
        f"{_agent_system_prompt('coder')}\n\n"
        f"Working directory: {working_dir}\n"
        f"Use tools to read, edit, and create files as needed."
    )
    return _chat(
        provider=cfg.provider,
        model=cfg.coder_llm["model"],
        system=system,
        user=f"Working directory: {working_dir}\n\nTask: {task_description}",
    )


# ── Agent creation (general-purpose, backward compat) ─────────


def create_agent(
    cfg: SwarmConfig | None = None,
    model: str = "qwen3:14b",
) -> dict[str, Any]:
    """Create a general-purpose agent dict.

    Returns a lightweight dict that can be passed to :func:`_run_single_agent`
    or used directly with :func:`chat_sync`.
    """
    if cfg is None:
        cfg = SwarmConfig(coder_model=model, default_model=model)
    return {
        "name": "general",
        "system": _agent_system_prompt("general"),
        "provider": cfg.provider,
        "model": cfg.coder_llm["model"],
        "tools": get_all_tools(),
    }


def create_coder_with_tools(cfg: SwarmConfig) -> dict[str, Any]:
    """Coder agent dict with full filesystem/git/shell tool access."""
    return {
        "name": "coder_full",
        "system": _agent_system_prompt("coder"),
        "provider": cfg.provider,
        "model": cfg.coder_llm["model"],
        "tools": get_coder_tools(),
    }


def create_researcher_with_tools(cfg: SwarmConfig) -> dict[str, Any]:
    """Researcher agent dict with full web + browser tool access."""
    return {
        "name": "researcher",
        "system": _agent_system_prompt("researcher"),
        "provider": cfg.provider,
        "model": cfg.deep_llm["model"],
        "tools": get_researcher_tools(),
    }


# ── Tool bundles (unchanged) ──────────────────────────────────


def get_all_tools() -> list[Any]:
    """All available workspace tools."""
    from ai_workspace.tools import (
        DiffEditTool,
        GitBranchTool,
        GitCommitTool,
        GitDiffTool,
        GitLogTool,
        GitStatusTool,
        HeadlessBrowserTool,
        ListDirTool,
        MercadoLivreSearchTool,
        OLXSearchTool,
        PaginatedScraperTool,
        ReadFileTool,
        SafeShellTool,
        SearchCodeTool,
        WebFetchTool,
        WriteFileTool,
    )

    tools: list[Any] = [
        ReadFileTool(),
        WriteFileTool(),
        ListDirTool(),
        SearchCodeTool(),
        SafeShellTool(),
        GitStatusTool(),
        GitDiffTool(),
        GitLogTool(),
        GitCommitTool(),
        GitBranchTool(),
        DiffEditTool(),
        WebFetchTool(),
        HeadlessBrowserTool(),
        PaginatedScraperTool(),
        MercadoLivreSearchTool(),
        OLXSearchTool(),
    ]

    return tools


def get_coder_tools() -> list[Any]:
    """Tool bundle for the Coder agent (filesystem + git + shell)."""
    from ai_workspace.tools import (
        DiffEditTool,
        EditFileTool,
        GitBranchTool,
        GitCommitTool,
        GitDiffTool,
        GitLogTool,
        GitStatusTool,
        ListDirTool,
        ReadFileTool,
        SafeShellTool,
        SearchCodeTool,
        WriteFileTool,
    )

    return [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        ListDirTool(),
        SearchCodeTool(),
        SafeShellTool(),
        GitStatusTool(),
        GitDiffTool(),
        GitLogTool(),
        GitCommitTool(),
        GitBranchTool(),
        DiffEditTool(),
    ]


def get_researcher_tools() -> list[Any]:
    """Tool bundle for the Researcher agent (web + browser)."""
    from ai_workspace.tools import (
        HeadlessBrowserTool,
        MercadoLivreSearchTool,
        OLXSearchTool,
        PaginatedScraperTool,
        WebFetchTool,
        get_browser_agent_tool,
    )

    tools: list[Any] = [
        WebFetchTool(),
        HeadlessBrowserTool(),
        PaginatedScraperTool(),
        MercadoLivreSearchTool(),
        OLXSearchTool(),
    ]

    if get_browser_agent_tool is not None:
        tools.append(get_browser_agent_tool())

    return tools


# ═══════════════════════════════════════════════════════════
# BatchSwarm — Parallel agent workers
# ═══════════════════════════════════════════════════════════


class BatchSwarm:
    """Run N tasks in parallel across M agent workers.

    Uses ``chat_sync`` per-task (sync, thread-safe).

    Usage::

        swarm = BatchSwarm(model="qwen3:14b")
        tasks = [
            "Research topic A",
            "Research topic B",
            "Research topic C",
        ]
        results = swarm.run(tasks, max_workers=3)
        for task, result in results:
            print(f"{task}: {result.summary[:100]}...")
    """

    def __init__(
        self,
        model: str = "qwen3:14b",
        provider: str = "ollama",
        max_workers: int = 4,
    ):
        self.model = model
        self.provider = provider
        self.max_workers = max_workers

    def run(
        self,
        tasks: list[str],
        max_workers: int | None = None,
        progress_callback: callable | None = None,
    ) -> list[tuple[str, str, bool]]:
        """Execute tasks in parallel, respecting max_workers.

        Returns:
            List of (task, result, success) tuples.
        """
        import concurrent.futures

        workers = min(max_workers or self.max_workers, len(tasks))
        if progress_callback:
            progress_callback(0, len(tasks), "starting")

        results: list[tuple[str, str, bool]] = []

        def _run_one(task: str) -> tuple[str, str, bool]:
            try:
                result = _chat(
                    provider=self.provider,
                    model=self.model,
                    system=_agent_system_prompt("general"),
                    user=task,
                )
                return task, result, True
            except Exception as e:
                return task, str(e), False

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run_one, t) for t in tasks]
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                results.append(future.result())
                if progress_callback:
                    progress_callback(i + 1, len(tasks))

        return results

    async def run_async(
        self,
        tasks: list[str],
        max_workers: int | None = None,
        progress_callback: callable | None = None,
    ) -> list[tuple[str, str, bool]]:
        """Async implementation of batch processing."""
        workers = min(max_workers or self.max_workers, len(tasks))
        semaphore = asyncio.Semaphore(workers)
        results: list[tuple[str, str, bool]] = []

        async def _worker(task: str) -> tuple[str, str, bool]:
            async with semaphore:
                return await asyncio.to_thread(self.run, [task])[0]

        if progress_callback:
            progress_callback(0, len(tasks), "starting")

        tasks_async = [_worker(t) for t in tasks]
        for coro in asyncio.as_completed(tasks_async):
            result = await coro
            results.append(result)

        return results
