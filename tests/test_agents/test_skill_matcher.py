"""Tests for skill_matcher.py — keyword overlap + explicit trigger matching."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ai_workspace.agents.skill_matcher import (
    _build_skill_context,
    _keyword_overlap,
    explicit_skill_for_task,
    match_and_inject_skill,
)
from ai_workspace.skills.loader import Skill

# ── Fixtures ────────────────────────────────────────────────

SAMPLE_SKILL = Skill(
    name="commit",
    description="Create a safe git commit with conventional commit message",
    workflow_steps=["1. Stage changes", "2. Write message", "3. Commit"],
    rules=["Never force push", "Use conventional commits"],
    path=Path("/fake/skills/commit"),
    source="project",
)


def _mock_loader(skills: list[Skill] | None = None) -> MagicMock:
    """Create a mock SkillLoader with given skills."""
    if skills is None:
        skills = [SAMPLE_SKILL]
    loader = MagicMock()
    loader._skills = {s.name: s for s in skills}
    loader.get = lambda name: loader._skills.get(name)
    return loader


# ── _keyword_overlap ───────────────────────────────────────

class TestKeywordOverlap:
    def test_exact_match(self):
        score = _keyword_overlap("commit changes", "commit changes safely")
        assert score > 0, "Should have overlap"

    def test_no_overlap_returns_zero(self):
        score = _keyword_overlap("python", "rust go java")
        assert score == 0.0

    def test_short_words_filtered(self):
        """Words with <= 2 chars are ignored."""
        score = _keyword_overlap("a an the ok no", "ok yes no maybe")
        # "ok" is 2 chars, "no" is 2 chars — both filtered
        # "the" is 3 chars but only in first
        # "yes" (3) and "maybe" (4) only in second
        # After filtering both: first has "the", second has "yes", "maybe"
        # No overlap → 0.0
        assert score == 0.0

    def test_partial_overlap(self):
        score = _keyword_overlap("debug test fix", "debug code test")
        # Common: "debug", "test" → 2 overlap
        # Union: "debug", "test", "fix", "code" → 4
        # Score: 2/4 = 0.5
        assert score == 0.5

    def test_empty_target(self):
        assert _keyword_overlap("hello world", "") == 0.0

    def test_empty_text(self):
        assert _keyword_overlap("", "hello world") == 0.0


# ── match_and_inject_skill ──────────────────────────────────

class TestMatchAndInjectSkill:
    def test_injects_when_match_above_threshold(self):
        loader = _mock_loader()
        result = match_and_inject_skill(
            "commit my changes", "", loader=loader, threshold=0.1,
        )
        assert "[SKILL: commit" in result
        assert "Workflow (follow these steps)" in result

    def test_returns_original_when_below_threshold(self):
        loader = _mock_loader()
        result = match_and_inject_skill(
            "python programming", "", loader=loader, threshold=0.9,
        )
        assert result == ""

    def test_appends_to_existing_prompt(self):
        loader = _mock_loader()
        result = match_and_inject_skill(
            "commit code now", "Existing prompt text", loader=loader, threshold=0.1,
        )
        assert result.startswith("Existing prompt text")
        assert "[SKILL: commit" in result

    def test_no_skills_returns_original(self):
        loader = _mock_loader([])
        result = match_and_inject_skill("commit code", "prompt", loader=loader)
        assert result == "prompt"


# ── explicit_skill_for_task ─────────────────────────────────

class TestExplicitSkillForTask:
    def test_direct_trigger(self):
        assert explicit_skill_for_task("commit this code") == "commit"

    def test_partial_word(self):
        """'commitar' contains 'commit' as substring."""
        assert explicit_skill_for_task("commitar agora") == "commit"

    def test_no_match_returns_none(self):
        assert explicit_skill_for_task("hello world") is None

    def test_multiple_triggers_match_first(self):
        """Returns the first matching skill name in iteration order."""
        assert explicit_skill_for_task("debug bug fix") == "debug"

    def test_case_insensitive(self):
        assert explicit_skill_for_task("CREATE PR now") == "create-pr"


# ── _build_skill_context ───────────────────────────────────

class TestBuildSkillContext:
    def test_includes_workflow_steps(self):
        context = _build_skill_context(SAMPLE_SKILL, "commit my code", 0.8)
        assert "1. Stage changes" in context
        assert "2. Write message" in context
        assert "3. Commit" in context

    def test_includes_rules(self):
        context = _build_skill_context(SAMPLE_SKILL, "commit my code", 0.8)
        assert "Never force push" in context
        assert "Use conventional commits" in context

    def test_includes_task_text(self):
        context = _build_skill_context(SAMPLE_SKILL, "commit my code", 0.8)
        assert "## Your Task" in context
        assert "commit my code" in context

    def test_includes_score_tag(self):
        context = _build_skill_context(SAMPLE_SKILL, "task", 0.85)
        assert "[SKILL: commit" in context
        assert "[/SKILL: commit]" in context

    def test_empty_workflow_handling(self):
        skill = Skill(
            name="empty",
            description="empty skill",
            path=Path("/fake/skills/empty"),
            source="project",
        )
        context = _build_skill_context(skill, "task", 0.5)
        assert "## Your Task" in context
        assert "Workflow" not in context
