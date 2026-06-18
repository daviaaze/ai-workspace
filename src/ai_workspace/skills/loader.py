"""
Skill Loader — discovers and executes pi-compatible skills as crewAI workflows.

Skill locations (searched in order):
1. pi-setup/skills/           (project skills)
2. ~/.agents/skills/          (user skills)
3. ~/.pi/agent/skills/        (pi skills)

Each skill is a directory with SKILL.md containing:
- YAML frontmatter: name, description
- Markdown body: workflow steps, rules, tips

Usage:
    loader = SkillLoader()
    skills = loader.discover()
    loader.run("debug", task="tests failing in test_store.py")
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.skills")


@dataclass
class Skill:
    """A loaded skill from SKILL.md."""
    name: str
    description: str
    path: Path
    source: str                    # "project", "user", "pi"
    workflow_steps: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    raw_content: str = ""


class SkillLoader:
    """Discover and load pi-compatible skills from standard locations."""

    def __init__(self, project_root: str | Path | None = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._skills: dict[str, Skill] = {}
        self._discovered = False

    #  Discovery 

    def discover(self) -> dict[str, Skill]:
        """Scan all skill locations and return loaded skills."""
        if self._discovered:
            return self._skills

        locations = [
            (self.project_root / "pi-setup" / "skills", "project"),
            (Path.home() / ".agents" / "skills", "user"),
            (Path.home() / ".pi" / "agent" / "skills", "pi"),
        ]

        for base, source in locations:
            if not base.is_dir():
                continue
            for skill_dir in base.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    # Check for root .md files (single-file skills)
                    # In ~/.pi/agent/skills/, root .md files are individual skills
                    if source == "pi" and base == skill_dir.parent:
                        continue
                    continue
                try:
                    skill = self._load(skill_md, source)
                    if skill and skill.name not in self._skills:
                        self._skills[skill.name] = skill
                except Exception as e:
                    logger.warning("Failed to load skill %s: %s", skill_md, e)

        self._discovered = True
        return self._skills

    def _load(self, path: Path, source: str) -> Skill | None:
        """Parse a SKILL.md file into a Skill object."""
        content = path.read_text(encoding="utf-8")

        # Parse YAML frontmatter (--- ... ---)
        frontmatter: dict[str, str] = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # Simple YAML parsing (name: value, description: value)
                for line in parts[1].strip().split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, _, val = line.partition(":")
                        frontmatter[key.strip()] = val.strip()
                body = parts[2]

        name = frontmatter.get("name", path.parent.name)
        description = frontmatter.get("description", "")

        if not description:
            return None  # Skills must have descriptions per spec

        # Extract workflow steps
        # Format 1: "1. **Name** — description" (debug, commit, create-pr)
        # Format 2: "## Phase" headers + bullet points (feature-dev, onboard)
        workflow_steps: list[str] = []
        rules: list[str] = []

        for line in body.split("\n"):
            stripped = line.strip()

            # Format 1: numbered step
            match = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s*[—\-]\s*(.+)", stripped)
            if match:
                workflow_steps.append(f"{match.group(1)}: {match.group(2)}")
                continue

            # Format 2: bullet under a ## heading
            if stripped.startswith("- "):
                workflow_steps.append(stripped[2:])
                continue

        # If no steps found, use raw body (truncated)
        if not workflow_steps:
            workflow_steps = [body.strip()[:5000]]

        return Skill(
            name=name,
            description=description,
            path=path,
            source=source,
            workflow_steps=workflow_steps,
            rules=rules,
            raw_content=body.strip(),
        )

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        self.discover()
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, str]]:
        """Return all discovered skills with basic info."""
        self.discover()
        return [
            {
                "name": s.name,
                "description": s.description,
                "source": s.source,
                "steps": len(s.workflow_steps),
            }
            for s in sorted(self._skills.values(), key=lambda s: s.name)
        ]

    #  Execution 

    def build_task_description(
        self,
        skill_name: str,
        task: str,
        extra_context: str = "",
    ) -> str:
        """Build a crewAI task description from a skill's workflow.

        The skill's workflow steps are injected as instructions the agent
        must follow. The user's task provides the specific context.

        Args:
            skill_name: Name of the skill (e.g., "debug", "feature-dev")
            task: The user's task description (e.g., "tests failing in test_store.py")
            extra_context: Additional context to inject

        Returns:
            A formatted task description string for crewAI.

        Raises:
            ValueError: If skill not found.
        """
        skill = self.get(skill_name)
        if not skill:
            available = ", ".join(self._skills.keys()) if self._skills else "none"
            raise ValueError(
                f"Skill '{skill_name}' not found. Available: {available}"
            )

        parts = [
            f"## Task: {task}",
            "",
            "### Instructions (follow this workflow):",
            "",
        ]

        if skill.workflow_steps:
            for i, step in enumerate(skill.workflow_steps, 1):
                parts.append(f"{i}. {step}")
        else:
            # No structured steps found — use raw content
            parts.append(skill.raw_content[:8000])

        if skill.rules:
            parts.append("")
            parts.append("### Rules:")
            for rule in skill.rules:
                parts.append(f"- {rule}")

        if extra_context:
            parts.append("")
            parts.append(f"### Additional Context:")
            parts.append(extra_context)

        return "\n".join(parts)

    def run(
        self,
        skill_name: str,
        task: str,
        *,
        provider: str = "ollama",
        model: str = "qwen3:14b",
        extra_context: str = "",
        stream_sink: Any = None,  # CLIStreamSink, TUIStreamSink, etc.
    ) -> str:
        """Execute a skill as a crewAI agent task.

        Args:
            skill_name: Skill to run
            task: User's task description
            provider: LLM provider
            model: Model name
            extra_context: Additional context
            stream_sink: Optional output stream for progress

        Returns:
            Agent response string.
        """
        from ai_workspace.agents.swarm import create_agent
        from crewai import Task, Crew

        task_desc = self.build_task_description(skill_name, task, extra_context)

        agent = create_agent(
            model=f"{provider}/{model}",
            extra_tools=None,  # Uses default tool set
        )

        crew_task = Task(
            description=task_desc,
            expected_output="The completed task result.",
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[crew_task],
            verbose=True,
        )

        if stream_sink and hasattr(stream_sink, "on_start"):
            stream_sink.on_start(f"Skill: {skill_name} — {task}")

        try:
            result = crew.kickoff()
            output = str(result)

            if stream_sink and hasattr(stream_sink, "on_complete"):
                stream_sink.on_complete(output[:500])

            return output
        except Exception as e:
            if stream_sink and hasattr(stream_sink, "on_error"):
                stream_sink.on_error(str(e))
            raise



_loader: SkillLoader | None = None


def get_loader(project_root: str | Path | None = None) -> SkillLoader:
    """Get or create the global SkillLoader instance."""
    global _loader
    if _loader is None:
        _loader = SkillLoader(project_root=project_root)
    return _loader
