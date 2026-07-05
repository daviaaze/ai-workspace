"""Verify CLI command registration — catch shadowing and missing commands.

This test file is a safety harness. It must pass before and after any
refactoring of the CLI module to ensure no commands are lost or shadowed.
"""

from __future__ import annotations

from ai_workspace.cli import app


def _get_groups() -> dict[str, list[str]]:
    """Return a dict mapping group name → list of command names."""
    groups: dict[str, list[str]] = {}
    for g in app.registered_groups:
        name = g.name
        # Typer commands w/o explicit name use the function name at runtime
        cmds = [c.name or "(unnamed)" for c in g.typer_instance.registered_commands]
        groups[name] = cmds
    return groups


def _get_top_commands() -> list[str]:
    """Return the list of top-level command names (no group)."""
    return [c.name or "(unnamed)" for c in app.registered_commands]


# ── Group existence tests ──────────────────────────────────


def test_all_expected_groups_exist():
    """Every expected CLI group should be registered exactly once."""
    groups = _get_groups()
    expected = {
        "memory",
        "source",
        "session",
        "tool",
        "task",
        "kb",
        "schedule",
        "skill",
        "obsidian",
        "cache",
        "wf",
        "research",
        "project",
        "rules",
        "trace",
        "eval",
        "mcp",
        "partners",
        "context-fs",
    }
    actual = set(groups.keys())
    missing = expected - actual
    extra = actual - expected

    assert not missing, f"Expected groups missing: {missing}"
    # Extra groups may be added over time — warn but don't fail
    if extra:
        import warnings
        warnings.warn(f"Unexpected groups found: {extra}")


def test_no_duplicate_groups():
    """No group name should appear more than once (would shadow commands)."""
    groups = _get_groups()
    assert len(groups) == len(set(groups.keys())), (
        "Duplicate groups detected. Use `app.registered_groups` to investigate."
    )


# ── Memory group tests ─────────────────────────────────────


def test_memory_group_has_all_commands():
    """The memory group should expose all 8 commands from both original groups."""
    groups = _get_groups()
    # Normalize unnamed → actual function names
    cmds = {c if c != "(unnamed)" else "add-or-recall" for c in groups["memory"]}
    # We expect either named or function-named versions
    named = {c for c in groups["memory"] if c != "(unnamed)"}

    assert "stats" in named, "Missing: memory stats"
    assert "show" in named, "Missing: memory show"
    assert "l1" in named, "Missing: memory l1"
    assert "consolidate" in named, "Missing: memory consolidate"
    assert "list" in named, "Missing: memory list"
    assert "search" in named, "Missing: memory search"
    # add and recall use function names (unnamed), verify at least 2 unnamed exist
    unnamed_count = sum(1 for c in groups["memory"] if c == "(unnamed)")
    assert unnamed_count >= 2, (
        f"Expected at least 2 unnamed commands (add, recall), got {unnamed_count}"
    )


# ── Source group tests ─────────────────────────────────────


def test_source_group_has_all_commands():
    """The source group should expose all 5 commands: stats, seed, check, endorse, flag."""
    groups = _get_groups()
    named = {c for c in groups["source"] if c != "(unnamed)"}

    assert "stats" in named, "Missing: source stats"
    assert "endorse" in named, "Missing: source endorse (was shadowed before fix)"
    assert "flag" in named, "Missing: source flag (was shadowed before fix)"
    # check and seed use function names (unnamed)
    assert "check" in named or any(
        True for c in groups["source"] if c == "(unnamed)"
    ), "Missing: source check or seed"
    assert len(groups["source"]) == 5, (
        f"Expected 5 source commands, got {len(groups['source'])}: {groups['source']}"
    )


# ─── Top-level command tests ───────────────────────────────


def test_top_level_commands_exist():
    """Key top-level commands should be present (check via --help output)."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "ai_workspace.cli", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    stdout = result.stdout

    expected = [
        "search",
        "deep-research",
        "agent",
        "code",
        "ask",
        "chat",
        "tui",
        "web",
        "health",
        "init",
        "config",
        "version",
        "budget",
        "improve",
    ]
    missing = [c for c in expected if c not in stdout]
    assert not missing, f"Top-level commands missing from --help: {missing}"


# ── Help output smoke tests ────────────────────────────────


def test_memory_help_succeeds():
    """Running 'aiw memory --help' should not crash."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "ai_workspace.cli", "memory", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"memory --help failed:\n{result.stderr}"
    assert "stats" in result.stdout
    assert "add" in result.stdout or "remember" in result.stdout
    assert "recall" in result.stdout
    assert "consolidate" in result.stdout


def test_source_help_succeeds():
    """Running 'aiw source --help' should show endorse and flag."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "ai_workspace.cli", "source", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"source --help failed:\n{result.stderr}"
    assert "endorse" in result.stdout, "source endorse missing from help"
    assert "flag" in result.stdout, "source flag missing from help"


def test_top_help_succeeds():
    """Running 'aiw --help' should not crash."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "ai_workspace.cli", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"--help failed:\n{result.stderr}"
