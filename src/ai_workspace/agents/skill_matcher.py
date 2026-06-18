"""
Skill Matcher — injects pi-compatible skill workflows into agent prompts.

Unlike tools (executed at runtime), skills are prompt-level context injected
BEFORE the agent loop starts. This mirrors pi's architecture:

- Tools: called by the agent during execution (read_file, shell_exec, etc.)
- Skills: injected as system prompt augmentation (commit workflow, debug method, etc.)

The matcher checks the user's task against skill descriptions and injects
the matching skill's workflow into the system prompt.
"""

from __future__ import annotations

import logging
from typing import Optional

from ai_workspace.skills.loader import Skill, SkillLoader

logger = logging.getLogger("aiw.skill_matcher")


def match_and_inject_skill(
    task: str,
    system_prompt: str = "",
    *,
    loader: SkillLoader | None = None,
    threshold: float = 0.15,
) -> str:
    """Match a skill to the user's task and inject its workflow into the prompt.

    Uses keyword overlap between task and skill descriptions to find
    the best match. If found, prepends the skill workflow to the prompt.

    Args:
        task: The user's task description.
        system_prompt: Existing system prompt (augmented with skill if matched).
        loader: SkillLoader instance (created if None).
        threshold: Minimum keyword overlap ratio (0-1) to trigger injection.

    Returns:
        Augmented system prompt (or original if no match).
    """
    if loader is None:
        loader = SkillLoader()

    skill = _find_best_skill(task, loader)
    if skill is None:
        return system_prompt

    # Check if the match is strong enough
    score = _keyword_overlap(task, skill.description)
    if score < threshold:
        return system_prompt

    logger.info("Injected skill '%s' (score=%.2f) into prompt", skill.name, score)

    # Build the skill context
    skill_context = _build_skill_context(skill, task, score)

    # Inject into system prompt
    if system_prompt:
        return f"{system_prompt}\n\n{skill_context}"
    return skill_context


def _find_best_skill(task: str, loader: SkillLoader) -> Optional[Skill]:
    """Find the skill with the highest keyword overlap with the task."""
    best: Optional[Skill] = None
    best_score = 0.0

    for skill in loader._skills.values():
        score = _keyword_overlap(task, skill.description)
        # Also check skill name keywords in task
        name_score = _keyword_overlap(task, skill.name.replace("-", " "))

        # Weight: 60% description match, 40% name match
        combined = score * 0.6 + name_score * 0.4

        if combined > best_score:
            best_score = combined
            best = skill

    return best


def _keyword_overlap(text: str, target: str) -> float:
    """Calculate keyword overlap ratio between two strings."""
    text_words = set(text.lower().split())
    target_words = set(target.lower().split())

    # Filter short words
    text_words = {w for w in text_words if len(w) > 2}
    target_words = {w for w in target_words if len(w) > 2}

    if not text_words or not target_words:
        return 0.0

    overlap = len(text_words & target_words)
    total = len(text_words | target_words)

    return overlap / max(1, total)


def _build_skill_context(skill: Skill, task: str, score: float) -> str:
    """Build a prompt context block for a matched skill."""
    parts: list[str] = []

    parts.append(f"[SKILL: {skill.name} — {skill.description}]")
    parts.append("")

    if skill.workflow_steps:
        parts.append("## Workflow (follow these steps)")
        for i, step in enumerate(skill.workflow_steps, 1):
            parts.append(f"{i}. {step}")
        parts.append("")

    if skill.rules:
        parts.append("## Rules (must follow)")
        for rule in skill.rules:
            parts.append(f"- {rule}")
        parts.append("")

    parts.append(f"## Your Task")
    parts.append(task)
    parts.append("")
    parts.append("Apply the workflow above to complete this task. Use available tools as needed.")
    parts.append(f"[/SKILL: {skill.name}]")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Explicit skill injection for known commands
# ---------------------------------------------------------------------------

_SKILL_TRIGGERS: dict[str, list[str]] = {
    "commit": ["commit", "commitar", "save changes", "git commit", "stage"],
    "create-pr": ["create pr", "create a pr", "pull request", "abrir pr", "criar pr"],
    "debug": ["debug", "bug", "fix", "broken", "not working", "corrigir", "arrumar", "consertar", "debugging"],
    "desloppify": ["clean up", "polish", "remove cruft", "desloppify", "limpar codigo"],
    "pre-review": ["review", "code review", "pre-review", "check my code", "revisar", "revisao"],
    "feature-dev": ["implement", "build", "feature", "start", "criar feature", "desenvolver"],
    "deploy-checklist": ["deploy", "release", "production", "staging", "post-deploy"],
    "daily": ["daily", "standup", "end of day", "what was done", "hoje"],
    "learn": ["remember", "learn", "persist", "correction", "convention"],
    "onboard": ["onboard", "analyze repo", "new project", "understand codebase", "analisar projeto"],
    "docs-keeper": ["audit docs", "check docs", "documentation health", "docs health"],
    "deep-research": ["research", "deep research", "pesquisar", "investigate", "estudar"],
    "nixfiles": ["nixos", "nix", "flake", "nixfiles", "home manager", "configuration.nix"],
}


def explicit_skill_for_task(task: str) -> Optional[str]:
    """Check if task explicitly matches a skill trigger. Returns skill name or None.

    This is faster and more reliable than keyword overlap for well-known commands.
    Falls back to overlap-based matching for ambiguous tasks.
    """
    task_lower = task.lower()

    for skill_name, triggers in _SKILL_TRIGGERS.items():
        for trigger in triggers:
            if trigger in task_lower:
                return skill_name

    return None


def inject_skill_for_task(
    task: str,
    system_prompt: str = "",
    *,
    loader: SkillLoader | None = None,
) -> str:
    """Smart skill injection: check explicit triggers first, then overlap.

    Args:
        task: User's task.
        system_prompt: Existing system prompt.
        loader: SkillLoader (created if None).

    Returns:
        Augmented system prompt.
    """
    if loader is None:
        loader = SkillLoader()

    # 1. Check explicit triggers (fast path)
    skill_name = explicit_skill_for_task(task)
    if skill_name:
        skill = loader.get(skill_name)
        if skill:
            logger.info("Skill trigger matched: '%s' -> %s", task[:60], skill_name)
            context = _build_skill_context(skill, task, 1.0)
            if system_prompt:
                return f"{system_prompt}\n\n{context}"
            return context

    # 2. Fall back to keyword overlap
    return match_and_inject_skill(task, system_prompt, loader=loader)
