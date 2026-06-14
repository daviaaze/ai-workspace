"""
Agent Swarm using crewAI.

Defines specialized agents:
- researcher: deep search, web research
- coder: code generation, review
- analyst: data analysis, pattern recognition
- writer: content synthesis, reports
- planner: task breakdown, prioritization

Each agent can use:
- crewAI native tools (FileReadTool, DirectoryReadTool, etc.)
- MCP servers (via MCP client)
- opencli for browser automation
- Knowledge store for memory
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
    """Creates a research agent with deep search capabilities."""
    return Agent(
        role="Research Specialist",
        goal=(
            "Conduct thorough research on any topic. Break down complex "
            "questions into sub-questions, find answers from reliable "
            "sources, and synthesize findings into clear reports."
        ),
        backstory=(
            "You are a senior research analyst with years of experience "
            "in investigative research. You are methodical, thorough, and "
            "always verify information before reporting it. You excel at "
            "finding connections between seemingly unrelated topics."
        ),
        llm=cfg.deep_llm,
        verbose=True,
        allow_delegation=True,
    )


def create_coder(cfg: SwarmConfig) -> Agent:
    """Creates a coding agent for code generation, review, and debugging."""
    return Agent(
        role="Senior Software Engineer",
        goal=(
            "Write clean, efficient, well-documented code. Review code for "
            "bugs, security issues, and performance problems. Suggest "
            "improvements and best practices."
        ),
        backstory=(
            "You are a senior engineer with expertise in multiple languages "
            "and frameworks. You follow SOLID principles, write comprehensive "
            "tests, and believe in code that is readable before it is clever. "
            "You have deep knowledge of Python, TypeScript, Rust, and Nix."
        ),
        llm=cfg.coder_llm,
        verbose=True,
        allow_delegation=False,
    )


def create_analyst(cfg: SwarmConfig) -> Agent:
    """Creates a data/pattern analyst agent."""
    return Agent(
        role="Data Analyst",
        goal=(
            "Analyze data, identify patterns and trends, extract actionable "
            "insights. Present findings clearly with supporting evidence."
        ),
        backstory=(
            "You are a quantitative analyst who loves finding signal in noise. "
            "You combine statistical thinking with domain expertise to uncover "
            "insights that others miss. You always question assumptions and "
            "validate conclusions."
        ),
        llm=cfg.fast_llm,
        verbose=True,
        allow_delegation=True,
    )


def create_writer(cfg: SwarmConfig) -> Agent:
    """Creates a content writer/synthesizer agent."""
    return Agent(
        role="Technical Writer & Synthesizer",
        goal=(
            "Transform complex information into clear, engaging, well-structured "
            "content. Create reports, summaries, documentation, and briefings."
        ),
        backstory=(
            "You are a skilled communicator who bridges the gap between "
            "technical complexity and human understanding. You write for "
            "clarity first, adjusting tone and depth to your audience. "
            "You use Obsidian markdown for all output."
        ),
        llm=cfg.fast_llm,
        verbose=True,
        allow_delegation=False,
    )


def create_planner(cfg: SwarmConfig) -> Agent:
    """Creates a planning/strategy agent."""
    return Agent(
        role="Strategic Planner",
        goal=(
            "Break down complex goals into actionable steps. Prioritize tasks, "
            "estimate effort, identify dependencies, and track progress."
        ),
        backstory=(
            "You are a strategic thinker who excels at turning vague ideas "
            "into concrete plans. You use frameworks like GTD, OKRs, and "
            "agile methodologies to organize work effectively."
        ),
        llm=cfg.deep_llm,
        verbose=True,
        allow_delegation=True,
    )


# ═══════════════════════════════════════════════════════════════
# Pre-built Crews for common workflows
# ═══════════════════════════════════════════════════════════════

def research_crew(
    topic: str,
    cfg: SwarmConfig | None = None,
) -> Crew:
    """Crew for deep research on a topic."""
    if cfg is None:
        cfg = SwarmConfig()

    researcher = create_researcher(cfg)
    writer = create_writer(cfg)

    plan_task = Task(
        description=(
            f"Research topic: {topic}\n\n"
            f"1. Break this topic into 3-5 specific sub-questions\n"
            f"2. For each sub-question, provide a detailed answer\n"
            f"3. Identify connections between sub-topics\n"
            f"4. Note any areas of uncertainty\n\n"
            f"Focus on practical, actionable information."
        ),
        expected_output=(
            "A research brief with sub-questions, answers, "
            "and connections between topics."
        ),
        agent=researcher,
    )

    write_task = Task(
        description=(
            f"Transform the research findings about '{topic}' into a "
            f"comprehensive report suitable for an Obsidian vault:\n\n"
            f"1. Title and metadata (tags, date, status)\n"
            f"2. Executive summary\n"
            f"3. Key findings with bullet points\n"
            f"4. Detailed sections\n"
            f"5. Related topics and further reading\n\n"
            f"Format in clean markdown."
        ),
        expected_output="A markdown report ready for Obsidian.",
        agent=writer,
        context=[plan_task],
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[plan_task, write_task],
        verbose=True,
    )


def code_review_crew(
    code_or_project: str,
    cfg: SwarmConfig | None = None,
) -> Crew:
    """Crew for code review and analysis."""
    if cfg is None:
        cfg = SwarmConfig()

    coder = create_coder(cfg)
    analyst = create_analyst(cfg)

    review_task = Task(
        description=(
            f"Review this code/project: {code_or_project}\n\n"
            f"1. Identify potential bugs and edge cases\n"
            f"2. Check for security vulnerabilities\n"
            f"3. Evaluate code quality and maintainability\n"
            f"4. Suggest improvements with examples\n"
            f"5. Rate overall quality (A-F)"
        ),
        expected_output="Detailed code review with findings and recommendations.",
        agent=coder,
    )

    analysis_task = Task(
        description=(
            "Analyze the codebase structure and patterns:\n"
            "1. Architecture patterns used\n"
            "2. Technical debt assessment\n"
            "3. Performance considerations\n"
            "4. Testing coverage estimation\n"
        ),
        expected_output="Codebase architecture analysis.",
        agent=analyst,
        context=[review_task],
    )

    return Crew(
        agents=[coder, analyst],
        tasks=[review_task, analysis_task],
        verbose=True,
    )


def daily_planning_crew(
    goals: str,
    cfg: SwarmConfig | None = None,
) -> Crew:
    """Crew for daily planning and task prioritization."""
    if cfg is None:
        cfg = SwarmConfig()

    planner = create_planner(cfg)
    writer = create_writer(cfg)

    plan_task = Task(
        description=(
            f"Today's context and goals: {goals}\n\n"
            f"Create a daily plan:\n"
            f"1. Top 3 priorities with estimated time\n"
            f"2. Secondary tasks\n"
            f"3. Dependencies and blockers\n"
            f"4. Energy-based scheduling (deep work vs shallow tasks)\n"
            f"5. End-of-day review criteria"
        ),
        expected_output="A structured daily plan with priorities and time estimates.",
        agent=planner,
    )

    format_task = Task(
        description=(
            "Format the daily plan as an Obsidian daily note with:\n"
            "- YAML frontmatter (date, tags, focus)\n"
            "- Priority matrix (urgent/important grid)\n"
            "- Time-blocked schedule\n"
            "- Notes/reflections section"
        ),
        expected_output="A markdown daily note for Obsidian.",
        agent=writer,
        context=[plan_task],
    )

    return Crew(
        agents=[planner, writer],
        tasks=[plan_task, format_task],
        verbose=True,
    )
