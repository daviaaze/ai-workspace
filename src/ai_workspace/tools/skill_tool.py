"""
Skill Tool — invokes pi-compatible skills from within the agent loop.

Let the agent call skills by name during coding sessions:
- "run_skill('debug', task='tests failing')" → injects debug workflow
- "run_skill('commit')" → conventional commit workflow
- "run_skill('pre-review')" → pre-PR review workflow
"""

from __future__ import annotations

import logging
from typing import Any

from crewai.tools import BaseTool

from ai_workspace.skills.loader import SkillLoader, Skill

logger = logging.getLogger("aiw.skill_tool")


# Global loader (lazy)
_loader: SkillLoader | None = None


def _get_loader() -> SkillLoader:
    global _loader
    if _loader is None:
        _loader = SkillLoader()
    return _loader


class RunSkillTool(BaseTool):
    """Execute a pi-compatible skill workflow.

    The agent calls this to follow a structured workflow for complex tasks
    like debugging, creating PRs, deploying, or feature development.
    """

    name: str = "run_skill"
    description: str = (
        "Execute a structured workflow skill. Use this for complex multi-step tasks. "
        "Available skills: commit, create-pr, daily, debug, deploy-checklist, "
        "desloppify, feature-dev, learn, onboard, pre-review.\n"
        "Args:\n"
        "  skill: skill name (e.g., 'debug', 'commit', 'pre-review')\n"
        "  task: optional task description for context\n"
        "  extra: optional extra context (file paths, error messages, etc.)"
    )

    def _run(self, skill: str, task: str = "", extra: str = "") -> str:
        """Load and format a skill workflow for the agent.

        Args:
            skill: Name of the skill to run.
            task: User's task description (context for the skill).
            extra: Additional context (file paths, error messages, etc.).
        """
        loader = _get_loader()
        skill_obj = loader.get(skill)

        if skill_obj is None:
            available = [s["name"] for s in loader.list_skills()]
            return (
                f"Skill '{skill}' not found.\n"
                f"Available skills: {', '.join(available)}\n"
                f"Tip: Use 'aiw skills list' to see all available skills."
            )

        # Build a rich prompt from the skill workflow
        parts: list[str] = []

        # Skill header
        parts.append(f"## Skill: {skill_obj.name}")
        parts.append(f"Description: {skill_obj.description}")
        parts.append(f"Source: {skill_obj.source} ({skill_obj.path})")
        parts.append("")

        # Workflow steps
        if skill_obj.workflow_steps:
            parts.append("### Workflow")
            for i, step in enumerate(skill_obj.workflow_steps, 1):
                parts.append(f"{i}. {step}")
            parts.append("")

        # Rules
        if skill_obj.rules:
            parts.append("### Rules")
            for rule in skill_obj.rules:
                parts.append(f"- {rule}")
            parts.append("")

        # User's task
        if task:
            parts.append(f"### Your Task")
            parts.append(f"{task}")
            if extra:
                parts.append(f"\nAdditional context: {extra}")
            parts.append("")

        # Instructions
        parts.append("### Instructions")
        parts.append(
            "Follow the workflow above to complete the task. "
            "Use the available tools (read_file, write_file, edit_file, shell_exec, git) "
            "to execute each step. After completing all steps, provide a summary."
        )

        result = "\n".join(parts)

        # Also store the raw skill content for the agent to reference
        if skill_obj.raw_content and len(skill_obj.raw_content) < 3000:
            result += f"\n\n### Full Skill Reference\n{skill_obj.raw_content}"

        return result


class ListSkillsTool(BaseTool):
    """List all available pi-compatible skills."""

    name: str = "list_skills"
    description: str = (
        "List all available structured workflow skills. "
        "Use this to discover what skills are available before running one."
    )

    def _run(self, source: str = "") -> str:
        """List available skills, optionally filtered by source.

        Args:
            source: Filter by source: 'pi', 'user', 'project', or '' for all.
        """
        loader = _get_loader()
        skills = loader.list_skills()

        if source:
            skills = [s for s in skills if s.get("source") == source]

        if not skills:
            return "No skills found. Place SKILL.md files in ~/.pi/agent/skills/<name>/"

        lines = ["Available skills:"]
        by_source: dict[str, list[str]] = {}
        for s in sorted(skills, key=lambda s: s["name"]):
            src = s.get("source", "unknown")
            by_source.setdefault(src, []).append(f"  {s['name']}: {s['description']}")

        for src in ["project", "user", "pi"]:
            if src in by_source:
                lines.append(f"\n[{src} skills]")
                lines.extend(by_source[src])

        return "\n".join(lines)


def get_skill_tools() -> list[BaseTool]:
    """Return skill tools for agent registration."""
    return [RunSkillTool(), ListSkillsTool()]
