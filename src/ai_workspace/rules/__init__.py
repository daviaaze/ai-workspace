"""
Rules System — behavioral guardrails injected into agent contexts.

Rules are markdown files loaded from a rules directory. Each rule has a name
(from filename) and content. The RulesLoader reads and caches them, then
provides methods to inject rules as system prompts or context fragments.

Mirrors the pi coding agent rules system:
- rules/global.md  — Core behavioral imperatives (Tone, Think First, Git, Escalation)
- rules/code.md    — Code quality standards (Architecture, Validation, Error Handling)
- rules/infra.md   — Infrastructure rules (in pi: NixOS, DB, deployment)

Usage:
    from ai_workspace.rules import RulesLoader

    loader = RulesLoader()
    loader.load()

    # Get all rules as a combined system prompt
    system_prompt = loader.as_system_prompt()

    # Get specific rule
    global_rule = loader.get("global")

    # Filter by tags
    code_rules = loader.by_tag("code")

    # Inject into agent context
    loader.inject_into_context(ctx, tags=["global", "code"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


@dataclass
class Rule:
    """A single behavioral rule."""
    name: str
    content: str
    tags: set[str] = field(default_factory=set)
    always_apply: bool = False

    @property
    def as_system_fragment(self) -> str:
        """Render the rule as a system prompt fragment."""
        header = f"## Rule: {self.name.replace('_', ' ').title()}"
        return f"{header}\n\n{self.content}\n"


class RulesLoader:
    """Load, cache, and inject behavioral rules into agent contexts.

    Rules are markdown files in a configurable directory. File naming convention:
    - `NN-name.md` (e.g., `00-global.md`, `01-code.md`)
    - Leading number defines order
    - Name after dash becomes the rule name

    Frontmatter metadata (YAML-style):
    ```markdown
    ---
    tags: [global, code]
    always_apply: true
    ---
    ```
    """

    DEFAULT_RULES_DIR: ClassVar[Path] = Path(__file__).parent / "rules"

    def __init__(self, rules_dir: Path | None = None):
        self.rules_dir = Path(rules_dir) if rules_dir else self.DEFAULT_RULES_DIR
        self._rules: list[Rule] = []
        self._by_name: dict[str, Rule] = {}
        self._loaded = False

    def load(self) -> list[Rule]:
        """Load all rule files from the rules directory. Idempotent if already loaded."""
        if self._loaded:
            return self._rules

        self._rules = []
        self._by_name = {}

        if not self.rules_dir.exists():
            return self._rules

        for rule_file in sorted(self.rules_dir.glob("*.md")):
            rule = self._parse_rule_file(rule_file)
            if rule:
                self._rules.append(rule)
                self._by_name[rule.name] = rule

        self._loaded = True
        return self._rules

    def _parse_rule_file(self, path: Path) -> Rule | None:
        """Parse a single rule markdown file."""
        content = path.read_text()

        # Extract frontmatter if present
        tags: set[str] = set()
        always_apply = False

        lines = content.split("\n")
        if lines and lines[0].strip() == "---":
            # Find end of frontmatter
            end_idx = 1
            while end_idx < len(lines) and lines[end_idx].strip() != "---":
                line = lines[end_idx].strip()
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip()
                    if key.strip() == "tags":
                        tags = {t.strip() for t in val.strip("[]").split(",") if t.strip()}
                    elif key.strip() == "always_apply":
                        always_apply = val.lower() == "true"
                end_idx += 1
            # Content is everything after the frontmatter
            body = "\n".join(lines[end_idx + 1:]).strip()
        else:
            body = content.strip()
            # Auto-tag based on filename
            name = path.stem.split("-", 1)[-1] if "-" in path.stem else path.stem
            if name in ("global",):
                tags = {"global"}
            elif name in ("code",):
                tags = {"code"}
            elif name in ("infra",):
                tags = {"infra"}

        # Extract name from filename (after leading number)
        stem = path.stem
        if "-" in stem:
            name = stem.split("-", 1)[1]
        else:
            name = stem

        return Rule(
            name=name,
            content=body,
            tags=tags,
            always_apply=always_apply,
        )

    def get(self, name: str) -> Rule | None:
        """Get a rule by name."""
        if not self._loaded:
            self.load()
        return self._by_name.get(name)

    def by_tag(self, *tags: str) -> list[Rule]:
        """Get rules matching any of the given tags."""
        if not self._loaded:
            self.load()
        return [r for r in self._rules if r.tags.intersection(tags)]

    @property
    def all(self) -> list[Rule]:
        """All loaded rules in order."""
        if not self._loaded:
            self.load()
        return list(self._rules)

    @property
    def always_apply_rules(self) -> list[Rule]:
        """Rules marked as alwaysApply: true."""
        if not self._loaded:
            self.load()
        return [r for r in self._rules if r.always_apply]

    def as_system_prompt(self, tags: list[str] | None = None) -> str:
        """Render rules as a combined system prompt string.

        Args:
            tags: If provided, only include rules matching these tags.
                  If None, include all rules.
        """
        if not self._loaded:
            self.load()

        if tags:
            rules = self.by_tag(*tags)
        else:
            rules = self._rules

        if not rules:
            return ""

        parts = ["# Behavioral Rules\n"]
        for rule in rules:
            parts.append(rule.as_system_fragment)

        return "\n".join(parts)

    def inject_into_context(self, ctx, tags: list[str] | None = None) -> None:
        """Inject rules into a workflow or agent context.

        Sets ctx.rules or attaches rules to the context object.

        Args:
            ctx: Workflow Context or any object with a 'rules' attribute
            tags: If provided, only inject rules matching these tags
        """
        if not self._loaded:
            self.load()

        if tags:
            rules = self.by_tag(*tags)
        else:
            rules = self._rules

        if hasattr(ctx, 'rules'):
            if ctx.rules is None:
                ctx.rules = list(rules)
            else:
                ctx.rules.extend(rules)
        else:
            ctx.rules = list(rules)

    def __repr__(self) -> str:
        loaded = len(self._rules) if self._loaded else 0
        return f"RulesLoader(dir={self.rules_dir}, loaded={loaded})"


# Module-level singleton instance
_rules_loader: RulesLoader | None = None


def get_rules_loader() -> RulesLoader:
    """Get the module-level rules loader singleton."""
    global _rules_loader
    if _rules_loader is None:
        _rules_loader = RulesLoader()
        _rules_loader.load()
    return _rules_loader
