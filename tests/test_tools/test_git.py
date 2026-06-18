"""
Tests for git tools.

Uses a real temp git repo (git init + commits) to exercise the tools
end-to-end. The `gh` tool is mocked to avoid network/auth dependencies.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Set up a real git repo in tmp_path for the tools to operate on."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@test.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@test.com"
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"

    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, env=env, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, env=env, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, env=env, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# Test repo")
    subprocess.run(["git", "add", "."], cwd=tmp_path, env=env, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, env=env, check=True, capture_output=True)
    monkeypatch.setenv("AIW_GIT_REPO", str(tmp_path))
    return tmp_path


# ─── GitStatusTool ──────────────────────────────────


def test_git_status_clean_repo(git_repo):
    from ai_workspace.tools import GitStatusTool
    tool = GitStatusTool()
    out = tool._run(repo=str(git_repo))
    assert "main" in out  # branch name shown


def test_git_status_dirty_repo(git_repo):
    from ai_workspace.tools import GitStatusTool
    (git_repo / "new.txt").write_text("untracked")
    tool = GitStatusTool()
    out = tool._run(repo=str(git_repo))
    assert "new.txt" in out


def test_git_status_not_a_repo(tmp_path):
    from ai_workspace.tools import GitStatusTool
    tool = GitStatusTool()
    out = tool._run(repo=str(tmp_path))
    assert "Not a git repo" in out


# ─── GitDiffTool ────────────────────────────────────


def test_git_diff_works(git_repo):
    from ai_workspace.tools import GitDiffTool
    (git_repo / "README.md").write_text("# Modified")
    tool = GitDiffTool()
    out = tool._run(repo=str(git_repo))
    assert "Modified" in out or "modified" in out or "README.md" in out


def test_git_diff_no_changes(git_repo):
    from ai_workspace.tools import GitDiffTool
    tool = GitDiffTool()
    out = tool._run(repo=str(git_repo))
    assert out == "(no diff)"


def test_git_diff_specific_file(git_repo):
    from ai_workspace.tools import GitDiffTool
    (git_repo / "README.md").write_text("# Modified")
    (git_repo / "other.py").write_text("print('hi')")
    tool = GitDiffTool()
    out = tool._run(repo=str(git_repo), file="README.md")
    assert "README.md" in out or "Modified" in out or "modified" in out


# ─── GitLogTool ─────────────────────────────────────


def test_git_log_shows_commits(git_repo):
    from ai_workspace.tools import GitLogTool
    tool = GitLogTool()
    out = tool._run(repo=str(git_repo), limit=5)
    assert "Initial commit" in out


def test_git_log_limit(git_repo):
    from ai_workspace.tools import GitLogTool
    env = os.environ.copy()
    for i in range(3):
        (git_repo / f"f{i}.txt").write_text(f"file {i}")
        subprocess.run(["git", "add", "."], cwd=git_repo, env=env, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Commit {i}"], cwd=git_repo, env=env, check=True, capture_output=True)
    tool = GitLogTool()
    out = tool._run(repo=str(git_repo), limit=2)
    # With limit=2, we should see the last two commits (Commit 2 and Commit 1)
    assert "Commit 2" in out
    assert "Initial commit" not in out


# ─── GitCommitTool ──────────────────────────────────


def test_git_commit_adds_and_commits(git_repo):
    from ai_workspace.tools import GitCommitTool
    (git_repo / "new.py").write_text("print('hi')")
    tool = GitCommitTool()
    out = tool._run(repo=str(git_repo), message="Add new.py")
    # Either output mentions the commit OR the file shows up in log
    assert "Add new.py" in out or out == "" or out == "(no output)"  # git commit produces no stdout on success


def test_git_commit_specific_files(git_repo):
    from ai_workspace.tools import GitCommitTool
    (git_repo / "a.py").write_text("a")
    (git_repo / "b.py").write_text("b")
    tool = GitCommitTool()
    out = tool._run(repo=str(git_repo), message="Add a", add_all=False, files=["a.py"])
    env = os.environ.copy()
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=git_repo,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "b.py" in result.stdout  # b.py should still be untracked


# ─── GitBranchTool ──────────────────────────────────


def test_git_branch_list(git_repo):
    from ai_workspace.tools import GitBranchTool
    tool = GitBranchTool()
    out = tool._run(repo=str(git_repo))
    assert "main" in out


def test_git_branch_create(git_repo):
    from ai_workspace.tools import GitBranchTool
    env = os.environ.copy()
    tool = GitBranchTool()
    out = tool._run(repo=str(git_repo), create="feature/test")
    # git checkout -b produces "Switched to a new branch 'feature/test'" in stderr, not stdout
    # _run_git captures both but prioritize stdout; on success stdout may be empty
    assert "feature/test" in out or "Switched" in out or out == "(no output)"
    # Verify branch exists
    result = subprocess.run(
        ["git", "branch", "--list", "feature/test"],
        cwd=git_repo,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "feature/test" in result.stdout


# ─── GhPRCreateTool (mocked) ────────────────────────


def test_gh_pr_create_invokes_gh(monkeypatch):
    from ai_workspace.tools import GhPRCreateTool

    fake_result = subprocess.CompletedProcess(
        args=["gh", "pr", "create"], returncode=0,
        stdout="https://github.com/owner/repo/pull/42\n", stderr="",
    )
    with patch("ai_workspace.tools.git.subprocess.run", return_value=fake_result):
        tool = GhPRCreateTool()
        out = tool._run(title="My PR", body="Description")
    assert "pull/42" in out


def test_gh_pr_create_handles_missing_gh(monkeypatch):
    from ai_workspace.tools import GhPRCreateTool

    with patch("ai_workspace.tools.git.subprocess.run", side_effect=FileNotFoundError):
        tool = GhPRCreateTool()
        out = tool._run(title="My PR")
    assert "gh CLI not installed" in out


# ─── Convenience ────────────────────────────────────


def test_get_git_tools_returns_six():
    from ai_workspace.tools import get_git_tools
    tools = get_git_tools()
    assert len(tools) == 6
    names = {t.name for t in tools}
    assert names == {"git_status", "git_diff", "git_log", "git_commit", "git_branch", "gh_create_pr"}
