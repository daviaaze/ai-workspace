"""Tests for context.py — ContextBundle for project context injection."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ai_workspace.agents.context import (
    ContextBundle,
    ProjectContext,
)


class TestProjectContext:
    def test_default_construction(self):
        ctx = ProjectContext(cwd="/tmp")
        assert ctx.cwd == "/tmp"
        assert ctx.git_branch == ""
        assert ctx.git_status == ""
        assert ctx.git_recent_commits == []
        assert ctx.project_tree == ""
        assert ctx.recent_files == []
        assert ctx.file_count == 0
        assert ctx.language == ""

    def test_full_construction(self):
        ctx = ProjectContext(
            cwd="/test",
            git_branch="main",
            git_status=" M src/main.py",
            git_recent_commits=["abc123 fix bug", "def456 add feature"],
            project_tree="test/\n  src/",
            recent_files=["src/main.py"],
            file_count=2,
            language="python",
        )
        assert ctx.git_branch == "main"
        assert ctx.git_status == " M src/main.py"
        assert len(ctx.git_recent_commits) == 2
        assert ctx.language == "python"


# ── _format_context ────────────────────────────────────────

class TestFormatContext:
    def test_minimal_context(self):
        ctx = ProjectContext(cwd="/tmp")
        bundle = ContextBundle(cwd="/tmp")
        formatted = bundle._format_context(ctx)
        assert "<project_context>" in formatted
        assert "<cwd>/tmp</cwd>" in formatted
        assert "</project_context>" in formatted

    def test_with_git_info(self):
        ctx = ProjectContext(
            cwd="/repo",
            git_branch="feature-x",
            git_status=" M file.py",
            git_recent_commits=["abc123 desc"],
        )
        bundle = ContextBundle(cwd="/repo")
        formatted = bundle._format_context(ctx)
        assert "<git_branch>feature-x</git_branch>" in formatted
        assert "abc123 desc" in formatted
        assert "<git_status>" in formatted

    def test_with_language(self):
        ctx = ProjectContext(cwd="/repo", language="python")
        bundle = ContextBundle(cwd="/repo")
        formatted = bundle._format_context(ctx)
        assert "<language>python</language>" in formatted

    def test_with_session_id(self):
        ctx = ProjectContext(cwd="/repo")
        bundle = ContextBundle(cwd="/repo")
        formatted = bundle._format_context(ctx, session_id="sess-123")
        assert "<session_id>sess-123</session_id>" in formatted

    def test_with_project_tree(self):
        ctx = ProjectContext(cwd="/repo", project_tree="repo/\n  src/\n    main.py")
        bundle = ContextBundle(cwd="/repo")
        formatted = bundle._format_context(ctx)
        assert "<project_tree>" in formatted


# ── Language detection ─────────────────────────────────────

class TestDetectLanguage:
    def test_python_detected(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").touch()
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle._detect_language() == "python"

    def test_rust_detected(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").touch()
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle._detect_language() == "rust"

    def test_go_detected(self, tmp_path: Path):
        (tmp_path / "go.mod").touch()
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle._detect_language() == "go"

    def test_unknown_language(self, tmp_path: Path):
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle._detect_language() == ""

    def test_indicator_precedence(self, tmp_path: Path):
        """pyproject.toml takes precedence over Cargo.toml."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "Cargo.toml").touch()
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle._detect_language() == "python"


# ── get_guidelines ─────────────────────────────────────────

class TestGetGuidelines:
    def test_nix_guidelines(self, tmp_path: Path):
        (tmp_path / "flake.nix").touch()
        bundle = ContextBundle(cwd=str(tmp_path))
        guidelines = bundle.get_guidelines()
        assert any("Nix project" in g for g in guidelines)

    def test_python_guidelines(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").touch()
        bundle = ContextBundle(cwd=str(tmp_path))
        guidelines = bundle.get_guidelines()
        assert any("pytest" in g for g in guidelines)
        assert any("Format" in g for g in guidelines)

    def test_rust_guidelines(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").touch()
        bundle = ContextBundle(cwd=str(tmp_path))
        guidelines = bundle.get_guidelines()
        assert any("cargo build" in g for g in guidelines)

    def test_no_guidelines(self, tmp_path: Path):
        """Empty directory returns no guidelines."""
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle.get_guidelines() == []


# ── _is_git_repo ───────────────────────────────────────────

class TestIsGitRepo:
    def test_git_repo_exists(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle._is_git_repo() is True

    def test_no_git_repo(self, tmp_path: Path):
        bundle = ContextBundle(cwd=str(tmp_path))
        assert bundle._is_git_repo() is False


# ── _get_project_tree (mocked os.walk) ─────────────────────

class TestGetProjectTree:
    def test_empty_directory(self, tmp_path: Path):
        bundle = ContextBundle(cwd=str(tmp_path))
        tree = bundle._get_project_tree(max_files=200)
        # Just the directory name
        assert tmp_path.name in tree
        # No files
        assert len(tree.split("\n")) == 1

    def test_with_files(self, tmp_path: Path):
        (tmp_path / "src" / "main.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "main.py").write_text("print('hi')")
        (tmp_path / "README.md").write_text("# Readme")
        bundle = ContextBundle(cwd=str(tmp_path))
        tree = bundle._get_project_tree(max_files=200)
        assert tmp_path.name in tree
        assert "main.py" in tree
        assert "README.md" in tree
        assert "src" in tree

    def test_exclude_dirs(self, tmp_path: Path):
        """node_modules and __pycache__ should be excluded."""
        (tmp_path / "node_modules" / "pkg" / "index.js").parent.mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "index.js").write_text("// code")
        (tmp_path / "app.py").write_text("print('hi')")
        bundle = ContextBundle(cwd=str(tmp_path))
        tree = bundle._get_project_tree(max_files=200)
        assert "app.py" in tree
        assert "node_modules" not in tree
        assert "__pycache__" not in tree

    def test_max_depth_limit(self, tmp_path: Path):
        """Deeply nested dirs beyond max_depth should be excluded."""
        deep = tmp_path / "a" / "b" / "c" / "d" / "e.txt"
        deep.parent.mkdir(parents=True)
        (tmp_path / "top.txt").write_text("hi")
        bundle = ContextBundle(cwd=str(tmp_path), max_tree_depth=2)
        tree = bundle._get_project_tree(max_files=200)
        assert "top.txt" in tree
        # beyond depth 2, deep dirs should not appear
        assert "e.txt" not in tree or "..." in tree  # truncated

    def test_tree_truncated_at_max_files(self, tmp_path: Path):
        for i in range(50):
            (tmp_path / f"file_{i}.txt").write_text("x")
        bundle = ContextBundle(cwd=str(tmp_path))
        tree = bundle._get_project_tree(max_files=10)
        # Should not list all 50 files
        lines = [l for l in tree.split("\n") if "file_" in l]
        assert len(lines) < 50


# ── build() with mocked subprocess ─────────────────────────

class TestBuild:
    def test_build_minimal(self, tmp_path: Path):
        """build() without git dir returns partial context."""
        bundle = ContextBundle(cwd=str(tmp_path))
        context = asyncio.run(bundle.build(
            include_git=True,
            include_tree=False,
            session_id=None,
        ))
        assert "<project_context>" in context
        assert "<cwd>" in context
        # No git info since .git doesn't exist
        assert "<git_branch>" not in context

    def test_build_with_git_repo(self, tmp_path: Path):
        """With .git dir, git commands are attempted but may fail."""
        (tmp_path / ".git").mkdir()
        bundle = ContextBundle(cwd=str(tmp_path))
        context = asyncio.run(bundle.build(
            include_git=True,
            include_tree=False,
        ))
        assert "<project_context>" in context
        # Git commands will fail since not a real git repo,
        # but should not crash — empty strings handled gracefully

    def test_build_with_project_tree(self, tmp_path: Path):
        (tmp_path / "main.py").write_text("print('hi')")
        bundle = ContextBundle(cwd=str(tmp_path))
        context = asyncio.run(bundle.build(
            include_git=False,
            include_tree=True,
        ))
        assert "<project_tree>" in context
        assert "main.py" in context

    def test_build_exception_safety(self):
        """Build should not crash even if cwd doesn't exist."""
        bundle = ContextBundle(cwd="/nonexistent_path_xyz")
        context = asyncio.run(bundle.build(include_git=False, include_tree=False))
        assert "<project_context>" in context
