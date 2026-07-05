"""Capability — unified task descriptor for agent loop."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_workspace.agents.patterns import LoopPattern


@dataclass
class Capability:
    """A named capability that the agent loop can execute.

    Each capability declares:
    - What tools it needs (tool names to mount)
    - What model configuration it prefers
    - What context sources to inject
    - What LoopPattern to use

    Built-in capabilities are registered as module-level constants.
    """

    name: str
    description: str = ""
    pattern: LoopPattern = LoopPattern.REACT
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    default_model: str = ""
    context_sources: list[str] = field(default_factory=list)
    max_turns: int = 20
    temperature: float | None = None


# ── Built-in capabilities ───────────────────────────────────

CAPABILITY_CHAT = Capability(
    name="chat",
    description="General conversation, Q&A, and brainstorming",
    pattern=LoopPattern.DIRECT,
    required_tools=[],
    optional_tools=["web_search", "rag"],
    context_sources=["memory", "skills"],
    max_turns=10,
)

CAPABILITY_RESEARCH = Capability(
    name="research",
    description="Deep research with web search and knowledge retrieval",
    pattern=LoopPattern.REACT,
    required_tools=["web_search", "web_fetch"],
    optional_tools=["paper_search", "browser_agent"],
    context_sources=["kb", "memory"],
    max_turns=30,
)

CAPABILITY_CODE = Capability(
    name="code",
    description="Coding, debugging, and code analysis with full tool access",
    pattern=LoopPattern.REACT,
    required_tools=["filesystem", "git", "shell", "diff_edit"],
    optional_tools=["code_graph", "code_search", "web_search"],
    context_sources=["project_context", "rules"],
    max_turns=50,
)

CAPABILITY_SOLVE = Capability(
    name="solve",
    description="Step-by-step problem solving with reasoning",
    pattern=LoopPattern.REACT,
    required_tools=[],
    optional_tools=["rag", "web_search"],
    context_sources=["memory"],
    max_turns=20,
    temperature=0.3,
)

CAPABILITY_WRITE = Capability(
    name="write",
    description="Long-form writing, drafting, and editing",
    pattern=LoopPattern.DIRECT,
    required_tools=[],
    optional_tools=["rag", "web_search"],
    context_sources=["memory", "kb"],
    max_turns=15,
)

# Registry
BUILTIN_CAPABILITIES: dict[str, Capability] = {
    c.name: c for c in [
        CAPABILITY_CHAT,
        CAPABILITY_RESEARCH,
        CAPABILITY_CODE,
        CAPABILITY_SOLVE,
        CAPABILITY_WRITE,
    ]
}


def get_capability(name: str) -> Capability:
    """Look up a built-in capability by name.

    Falls back to CHAT if not found.
    """
    return BUILTIN_CAPABILITIES.get(name, CAPABILITY_CHAT)


def suggest_capability(task: str) -> Capability:
    """Heuristically suggest a capability based on task description.

    Simple keyword matching. For production, use the SmartRouter.
    """
    task_lower = task.lower()

    if any(kw in task_lower for kw in [
        "code", "implement", "function", "debug", "fix", "refactor",
        "write a ", "create ", "add ", "modify ",
    ]):
        return CAPABILITY_CODE
    if any(kw in task_lower for kw in [
        "research", "search", "find", "investigate", "explore",
        "what is", "how does", "analyze",
    ]):
        return CAPABILITY_RESEARCH
    if any(kw in task_lower for kw in [
        "solve", "calculate", "compute", "proof", "equation",
        "reason", "explain why",
    ]):
        return CAPABILITY_SOLVE
    if any(kw in task_lower for kw in [
        "write", "essay", "draft", "document", "report",
        "article", "blog",
    ]):
        return CAPABILITY_WRITE

    return CAPABILITY_CHAT
