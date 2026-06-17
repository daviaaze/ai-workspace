"""Project Rules loader — reads .rules and injects into agent context."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.rules")


def find_rules_file(workspace_root: Path | None = None) -> Path | None:
    """Find .rules file in workspace or ancestors."""
    root = workspace_root or Path.cwd()
    for parent in [root] + list(root.parents):
        rules_file = parent / ".rules"
        if rules_file.exists():
            return rules_file
        # Stop at git root or filesystem root
        if (parent / ".git").exists() or parent.parent == parent:
            break
    return None


def load_rules(workspace_root: Path | None = None) -> dict[str, Any]:
    """Load .rules as a dict. Returns empty dict if not found."""
    import yaml

    rules_file = find_rules_file(workspace_root)
    if rules_file is None:
        return {}

    try:
        with open(rules_file) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load .rules: %s", e)
        return {}


def rules_to_prompt(workspace_root: Path | None = None) -> str:
    """Convert .rules to text suitable for injection into agent system prompt.

    Returns empty string if no .rules found.
    """
    rules = load_rules(workspace_root)
    if not rules:
        return ""

    lines = ["\n## Project Rules (.rules)\n"]

    # Architecture rules
    arch = rules.get("architecture", {})
    if must_list := arch.get("rules", []):
        lines.append("### You MUST:")
        for r in must_list:
            lines.append(f"- {r}")

    # Never rules
    if never_list := arch.get("never", []):
        lines.append("\n### You MUST NOT:")
        for n in never_list:
            lines.append(f"- {n}")

    # Patterns
    if patterns := arch.get("patterns", {}):
        lines.append("\n### Use these patterns:")
        for name, tmpl in patterns.items():
            lines.append(f"- `{name}`: `{tmpl}`")

    # Testing
    testing = rules.get("testing", {})
    if testing:
        lines.append("\n### Testing:")
        lines.append(f"- Framework: {testing.get('framework', 'pytest')}")
        lines.append(f"- Coverage target: {testing.get('coverage_target', 80)}%")

    # Git
    git = rules.get("git", {})
    if git:
        lines.append("\n### Git:")
        lines.append(f"- Commit style: {git.get('commit_style', 'conventional')}")
        if branch := git.get("branch_naming"):
            lines.append(f"- Branch naming: {branch}")

    return "\n".join(lines)
