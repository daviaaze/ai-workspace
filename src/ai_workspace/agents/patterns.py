"""Loop execution patterns — strategy enum and suggestion logic."""

from __future__ import annotations

from enum import Enum


class LoopPattern(Enum):
    """Which execution strategy to use."""

    DIRECT = "direct"
    """Single LLM call, no tools. For chat, translation, classification."""

    REACT = "react"
    """Thought → Action → Observation → repeat. For coding, debugging."""

    PLAN_EXECUTE = "plan_execute"
    """Plan once, execute steps. For structured, predictable tasks. (Phase 2+)"""

    REWOO = "rewoo"
    """Plan tools → execute all in parallel → synthesize. (Phase 2+)"""

    DAG = "dag"
    """Compile task into DAG, execute with parallel + local repair. (Phase 5+)"""


# ── Heuristic suggestion ─────────────────────────────────────


def suggest_pattern(
    task: str,
    tools: list[dict] | None = None,
) -> LoopPattern:
    """Suggest the best loop pattern for a given task."""
    task_lower = task.lower()

    # No tools → Direct (nothing else we can do)
    if not tools:
        return LoopPattern.DIRECT

    # Coding / debugging keywords → ReAct
    code_kw = ["fix", "debug", "implement", "refactor", "add", "change",
                "corrigir", "corrige", "conserta", "arrumar", "build",
                "criar", "generate", "scaffold", "migrate"]
    if any(kw in task_lower for kw in code_kw):
        return LoopPattern.REACT

    # Research / comparison with multiple sources → ReWOO (plan→parallel→synthesize)
    rewoo_kw = ["research and", "search and", "compare and",
                "plan and execute", "plan and run", "parallel",
                "multiple sources", "search across", "compare prices"]
    if any(kw in task_lower for kw in rewoo_kw) and len(task.split()) > 8:
        return LoopPattern.REWOO

    # Complex multi-step tasks → DAG (parallel sub-tasks with dependencies)
    dag_kw = ["and", "then", "deploy", "setup", "configure", "install",
              "e", "depois", "configurar", "instalar", "both"]
    if any(kw in task_lower.split() for kw in dag_kw) and len(task.split()) > 10:
        return LoopPattern.DAG

    # Trivial single-greeting → Direct even with tools
    trivial = ["hi", "hello", "oi", "ola", "hey", "thanks", "obrigado"]
    if task_lower.strip().rstrip("!.?") in trivial:
        return LoopPattern.DIRECT

    # Default: ReAct (safe for unknown tasks with tools)
    return LoopPattern.REACT
