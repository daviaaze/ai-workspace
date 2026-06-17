"""
Agent Swarm using crewAI -- YAML-driven configuration.

Agent definitions live in ../config/agents.yaml.
Task templates live in ../config/tasks.yaml.

Python factories here wire LLMs and tools from SwarmConfig
into the YAML-defined agents and tasks.
"""

from __future__ import annotations

from typing import Any

from crewai import Agent, Crew, Task
from crewai.llm import LLM


class SwarmConfig:
    """Configuration for the agent swarm."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "ollama/qwen3:14b",
        coder_model: str = "ollama/qwen3-coder:30b",
        deep_model: str = "ollama/deepseek-r1:14b",
    ):
        # crewAI 1.14+ keeps the full model name when provider is explicit,
        # so strip the ollama/ prefix before passing to LLM().
        fast_model = default_model.split("/")[-1] if "/" in default_model else default_model
        code_model = coder_model.split("/")[-1] if "/" in coder_model else coder_model
        reasoning_model = deep_model.split("/")[-1] if "/" in deep_model else deep_model

        # Fast, general-purpose model
        self.fast_llm = LLM(
            model=fast_model,
            base_url=f"{base_url}/v1",
            api_key="ollama",
            provider="ollama",
        )

        # Large coding model
        self.coder_llm = LLM(
            model=code_model,
            base_url=f"{base_url}/v1",
            api_key="ollama",
            provider="ollama",
        )

        # Deep reasoning model
        self.deep_llm = LLM(
            model=reasoning_model,
            base_url=f"{base_url}/v1",
            api_key="ollama",
            provider="ollama",
        )


# ═══════════════════════════════════════════════════════════════
# Agent Definitions
# ═══════════════════════════════════════════════════════════════

def create_researcher(cfg: SwarmConfig) -> Agent:
    """Creates a research agent from agents.yaml."""
    from ai_workspace.config.loader import load_agent
    return load_agent("researcher", llm=cfg.deep_llm)


def create_coder(cfg: SwarmConfig) -> Agent:
    """Creates a coding agent from agents.yaml."""
    from ai_workspace.config.loader import load_agent
    return load_agent("coder", llm=cfg.coder_llm)


def create_analyst(cfg: SwarmConfig) -> Agent:
    """Creates an analyst agent from agents.yaml."""
    from ai_workspace.config.loader import load_agent
    return load_agent("analyst", llm=cfg.fast_llm)


def create_writer(cfg: SwarmConfig) -> Agent:
    """Creates a writer agent from agents.yaml."""
    from ai_workspace.config.loader import load_agent
    return load_agent("writer", llm=cfg.fast_llm)


def create_planner(cfg: SwarmConfig) -> Agent:
    """Creates a planner agent from agents.yaml."""
    from ai_workspace.config.loader import load_agent
    return load_agent("planner", llm=cfg.deep_llm)


# ═══════════════════════════════════════════════════════════════
# Pre-built Crews for common workflows
# ═══════════════════════════════════════════════════════════════

def research_crew(
    topic: str,
    cfg: SwarmConfig | None = None,
) -> Crew:
    """Crew for deep research on a topic (YAML-driven)."""
    from ai_workspace.config.loader import load_task
    
    if cfg is None:
        cfg = SwarmConfig()

    researcher = create_researcher(cfg)
    writer = create_writer(cfg)

    plan_task = load_task("research_plan", topic=topic, agent=researcher)
    write_task = load_task("research_write", topic=topic, agent=writer, context=[plan_task])

    return Crew(
        agents=[researcher, writer],
        tasks=[plan_task, write_task],
        verbose=True,
        planning=True,
    )


def code_review_crew(
    code_or_project: str,
    cfg: SwarmConfig | None = None,
) -> Crew:
    """Crew for code review and analysis (YAML-driven)."""
    from ai_workspace.config.loader import load_task
    
    if cfg is None:
        cfg = SwarmConfig()

    coder = create_coder(cfg)
    analyst = create_analyst(cfg)

    review_task = load_task("code_review", code=code_or_project, agent=coder)
    analysis_task = load_task("code_analysis", agent=analyst, context=[review_task])

    return Crew(
        agents=[coder, analyst],
        tasks=[review_task, analysis_task],
        verbose=True,
        planning=True,
    )


def daily_planning_crew(
    goals: str,
    cfg: SwarmConfig | None = None,
) -> Crew:
    """Crew for daily planning (YAML-driven)."""
    from ai_workspace.config.loader import load_task
    
    if cfg is None:
        cfg = SwarmConfig()

    planner = create_planner(cfg)
    writer = create_writer(cfg)

    plan_task = load_task("daily_plan", goals=goals, agent=planner)
    format_task = load_task("daily_format", agent=writer, context=[plan_task])

    return Crew(
        agents=[planner, writer],
        tasks=[plan_task, format_task],
        verbose=True,
    )


# ═══════════════════════════════════════════════════════════════
# v2 Tool Bundles -- wire filesystem/git/shell into agents
# ═══════════════════════════════════════════════════════════════


def get_all_tools() -> list[Any]:
    """Return ALL tools -- filesystem, git, shell, web, coding.

    This is the unified tool set for the general-purpose agent.
    """
    from ai_workspace.tools import (
        get_filesystem_tools,
        get_git_tools,
        get_shell_tool,
        WebFetchTool,
        HeadlessBrowserTool,
        PaginatedScraperTool,
        Crawl4AITool,
        MercadoLivreSearchTool,
        OLXSearchTool,
    )

    tools: list[Any] = []
    tools.extend(get_filesystem_tools())
    tools.extend(get_git_tools())
    tools.append(get_shell_tool())
    try:
        tools.append(Crawl4AITool())
    except Exception:
        pass
    tools.extend([
        WebFetchTool(),
        HeadlessBrowserTool(),
        PaginatedScraperTool(),
        MercadoLivreSearchTool(),
        OLXSearchTool(),
    ])
    return tools


def get_coder_tools() -> list[Any]:
    """Return the tool bundle for the Coder agent (filesystem + git + shell + code graph)."""
    from ai_workspace.tools import (
        get_filesystem_tools,
        get_git_tools,
        get_shell_tool,
    )
    tools: list[Any] = []
    tools.extend(get_filesystem_tools())
    tools.extend(get_git_tools())
    tools.append(get_shell_tool())

    # Code graph tool (optional — requires code-review-graph package)
    try:
        from ai_workspace.tools.code_graph import CodeReviewGraphTool
        tools.append(CodeReviewGraphTool())
    except ImportError:
        pass

    return tools


def create_agent(cfg: SwarmConfig | None = None, model: str = "qwen3:14b") -> Agent:
    """Create a general-purpose agent with ALL tools (YAML-driven)."""
    from ai_workspace.config.loader import load_agent
    
    if cfg is None:
        cfg = SwarmConfig(coder_model=f"ollama/{model}", default_model=f"ollama/{model}")

    return load_agent("general", llm=cfg.coder_llm, tools=get_all_tools())


def get_researcher_tools() -> list[Any]:
    """Return the tool bundle for the Researcher agent.

    Includes web fetch, headless browser, paginated scraper, marketplace
    search, and (if installed) the browser-use autonomous agent.
    """
    from ai_workspace.tools import (
        WebFetchTool,
        HeadlessBrowserTool,
        PaginatedScraperTool,
        MercadoLivreSearchTool,
        OLXSearchTool,
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


def create_coder_with_tools(cfg: SwarmConfig) -> Agent:
    """Coder agent with full filesystem/git/shell tool access."""
    from ai_workspace.config.loader import load_agent
    return load_agent("coder_full", llm=cfg.coder_llm, tools=get_coder_tools())


def coding_crew(
    task_description: str,
    cfg: SwarmConfig | None = None,
    working_dir: str = ".",
) -> Crew:
    """Crew for autonomous coding tasks (YAML-driven)."""
    from ai_workspace.config.loader import load_task
    
    if cfg is None:
        cfg = SwarmConfig()

    coder = create_coder_with_tools(cfg)
    code_task = load_task("coding_task", task_description=task_description, working_dir=working_dir, agent=coder)

    return Crew(
        agents=[coder],
        tasks=[code_task],
        verbose=True,
    )


def create_researcher_with_tools(cfg: SwarmConfig) -> Agent:
    """Researcher agent with full web + browser tool access."""
    from ai_workspace.config.loader import load_agent
    return load_agent("researcher", llm=cfg.deep_llm, tools=get_researcher_tools())
