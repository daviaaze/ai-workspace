"""Git operations for CrewAI agents — status, diff, log, commit, branch, PR."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


DEFAULT_REPO = os.environ.get("AIW_GIT_REPO", os.getcwd())


def _run_git(args: list[str], repo: str = DEFAULT_REPO, timeout: int = 30) -> str:
    """Run a git command in the given repo and return its combined output."""
    repo_path = Path(repo).resolve()
    if not (repo_path / ".git").exists() and not repo_path.name == ".git":
        return f" Not a git repo: {repo_path}"
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f" Timeout running: git {' '.join(args)}"
    except FileNotFoundError:
        return " git not installed"
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        return f" git {' '.join(args)} failed (exit {result.returncode}): {err}"
    out = (result.stdout or "").strip()
    return out or "(no output)"





class GitStatusInput(BaseModel):
    repo: str = Field(default=DEFAULT_REPO, description="Path to the git repo (default: cwd)")


class GitStatusTool(BaseTool):
    name: str = "git_status"
    description: str = "Show the working tree status of a git repository."
    args_schema: Type[BaseModel] = GitStatusInput

    def _run(self, repo: str = DEFAULT_REPO) -> str:
        return _run_git(["status", "--short", "--branch"], repo=repo)





class GitDiffInput(BaseModel):
    repo: str = Field(default=DEFAULT_REPO, description="Path to the git repo (default: cwd)")
    staged: bool = Field(default=False, description="Show staged changes instead of unstaged")
    file: str | None = Field(default=None, description="Limit diff to a specific file")


class GitDiffTool(BaseTool):
    name: str = "git_diff"
    description: str = (
        "Show diffs in the repo. By default shows unstaged changes. "
        "Set staged=true to see what is staged for commit. "
        "Optionally restrict to a single file path."
    )
    args_schema: Type[BaseModel] = GitDiffInput

    def _run(self, repo: str = DEFAULT_REPO, staged: bool = False, file: str | None = None) -> str:
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file:
            args.extend(["--", file])
        result = _run_git(args, repo=repo)
        if result == "(no output)":
            return "(no diff)"
        if len(result) > 50_000:
            return f"{result[:50_000]}\n... [truncated; full diff is {len(result)} bytes]"
        return result





class GitLogInput(BaseModel):
    repo: str = Field(default=DEFAULT_REPO, description="Path to the git repo (default: cwd)")
    limit: int = Field(default=10, description="Max commits to show")
    oneline: bool = Field(default=True, description="Use oneline format")


class GitLogTool(BaseTool):
    name: str = "git_log"
    description: str = "Show recent git commits. By default uses oneline format."
    args_schema: Type[BaseModel] = GitLogInput

    def _run(self, repo: str = DEFAULT_REPO, limit: int = 10, oneline: bool = True) -> str:
        args = ["log", f"-n{limit}"]
        if oneline:
            args.append("--oneline")
        else:
            args.append("--pretty=format:%h %ad %s [%an] -- %d")
            args.append("--date=short")
        return _run_git(args, repo=repo)





class GitCommitInput(BaseModel):
    message: str = Field(description="Commit message")
    repo: str = Field(default=DEFAULT_REPO, description="Path to the git repo (default: cwd)")
    add_all: bool = Field(default=True, description="git add -A before commit")
    files: list[str] | None = Field(default=None, description="Specific files to add (overrides add_all)")


class GitCommitTool(BaseTool):
    name: str = "git_commit"
    description: str = (
        "Stage and commit changes. By default stages all modified files (git add -A). "
        "Optionally restrict to a specific list of files. "
        "The commit message is taken verbatim — include a subject line and optional body."
    )
    args_schema: Type[BaseModel] = GitCommitInput

    def _run(
        self,
        message: str,
        repo: str = DEFAULT_REPO,
        add_all: bool = True,
        files: list[str] | None = None,
    ) -> str:
        if add_all and not files:
            add_out = _run_git(["add", "-A"], repo=repo)
            if add_out.startswith(""):
                return add_out
        elif files:
            add_out = _run_git(["add", "--", *files], repo=repo)
            if add_out.startswith(""):
                return add_out
        return _run_git(["commit", "-m", message], repo=repo)





class GitBranchInput(BaseModel):
    repo: str = Field(default=DEFAULT_REPO, description="Path to the git repo (default: cwd)")
    create: str | None = Field(default=None, description="Create a new branch with this name")
    checkout: str | None = Field(default=None, description="Switch to this branch")


class GitBranchTool(BaseTool):
    name: str = "git_branch"
    description: str = (
        "List branches, or create/checkout a branch. "
        "Pass create='name' to make a new branch, or checkout='name' to switch."
    )
    args_schema: Type[BaseModel] = GitBranchInput

    def _run(
        self,
        repo: str = DEFAULT_REPO,
        create: str | None = None,
        checkout: str | None = None,
    ) -> str:
        if create:
            return _run_git(["checkout", "-b", create], repo=repo)
        if checkout:
            return _run_git(["checkout", checkout], repo=repo)
        return _run_git(["branch", "-a"], repo=repo)





class GhPRCreateInput(BaseModel):
    title: str = Field(description="PR title")
    body: str = Field(default="", description="PR description (markdown)")
    base: str = Field(default="main", description="Base branch (the one you want to merge into)")
    head: str | None = Field(default=None, description="Head branch (defaults to current branch)")
    draft: bool = Field(default=False, description="Open as draft PR")
    repo: str = Field(default=DEFAULT_REPO, description="Path to the git repo (default: cwd)")


class GhPRCreateTool(BaseTool):
    name: str = "gh_create_pr"
    description: str = (
        "Open a GitHub pull request using the gh CLI. "
        "Requires that gh is installed and authenticated. "
        "By default the PR is opened against 'main' from the current branch."
    )
    args_schema: Type[BaseModel] = GhPRCreateInput

    def _run(
        self,
        title: str,
        body: str = "",
        base: str = "main",
        head: str | None = None,
        draft: bool = False,
        repo: str = DEFAULT_REPO,
    ) -> str:
        repo_path = Path(repo).resolve()
        args = ["gh", "pr", "create", "--title", title, "--base", base]
        if head:
            args.extend(["--head", head])
        if draft:
            args.append("--draft")
        if body:
            args.extend(["--body", body])
        try:
            result = subprocess.run(
                args,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except FileNotFoundError:
            return " gh CLI not installed"
        except subprocess.TimeoutExpired:
            return " gh pr create timed out"
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            return f" gh pr create failed: {err}"
        return result.stdout.strip() or " PR created"


def get_git_tools() -> list[BaseTool]:
    """Return all git tools for agent wiring."""
    return [
        GitStatusTool(),
        GitDiffTool(),
        GitLogTool(),
        GitCommitTool(),
        GitBranchTool(),
        GhPRCreateTool(),
    ]


__all__ = [
    "GitStatusTool",
    "GitDiffTool",
    "GitLogTool",
    "GitCommitTool",
    "GitBranchTool",
    "GhPRCreateTool",
    "get_git_tools",
]
