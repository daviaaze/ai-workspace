"""
Code Review Graph Tool — wraps code-review-graph for crewAI agents.

Provides:
- build_or_update_graph: Build AST-level code graph
- get_impact_radius: Blast radius of a change
- query_graph: Callers/callees/dependents of a symbol
- semantic_search_nodes: Natural language search over code
- get_architecture_overview: High-level architecture
- detect_changes: Risk analysis of pending changes
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool

logger = logging.getLogger("aiw.tools.code_graph")


class CodeReviewGraphTool(BaseTool):
    """Graph-based code analysis for intelligent coding.

    Builds a structural graph of the codebase (AST-level), then
    provides impact analysis, dependency tracing, semantic search,
    and architecture overview.

    Usage by agents:
        - Before editing: check impact_radius of changed files
        - Understanding code: semantic_search for concepts
        - Code review: detect_changes for risk assessment
        - Onboarding: get_architecture_overview
    """

    name: str = "code_graph"
    description: str = (
        "Graph-based code analysis tool. Use before editing or reviewing code. "
        "Commands: build(repo_root), impact(repo_root, files=['src/x.py']), "
        "query(repo_root, pattern='callers_of', target='function_name'), "
        "search(repo_root, query='concept'), "
        "overview(repo_root), changes(repo_root). "
        "All commands require repo_root pointing to a git repository."
    )

    def _resolve_repo(self, repo_root: str | None = None) -> Path:
        """Resolve repo root from argument or CWD."""
        if repo_root:
            path = Path(repo_root).expanduser().resolve()
        else:
            path = Path.cwd()
        if not (path / ".git").exists():
            # Try parent directories
            for parent in [path] + list(path.parents):
                if (parent / ".git").exists():
                    return parent
            raise ValueError(f"No git repository found at {path}")
        return path

    def _run_sync(self, coro):
        """Run an async function synchronously."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        # Already in async context — use thread pool
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()

    def _run(
        self,
        command: str,
        repo_root: str | None = None,
        **kwargs,
    ) -> str:
        """Execute a code-review-graph command.

        Args:
            command: One of build, impact, query, search, overview, changes
            repo_root: Path to git repository (default: CWD)
            **kwargs: Command-specific arguments
        """
        try:
            repo = self._resolve_repo(repo_root)
        except ValueError as e:
            return f"Error: {e}"

        try:
            if command == "build":
                return self._cmd_build(repo, **kwargs)
            elif command == "impact":
                return self._cmd_impact(repo, **kwargs)
            elif command == "query":
                return self._cmd_query(repo, **kwargs)
            elif command == "search":
                return self._cmd_search(repo, **kwargs)
            elif command == "overview":
                return self._cmd_overview(repo, **kwargs)
            elif command == "changes":
                return self._cmd_changes(repo, **kwargs)
            else:
                return (
                    f"Unknown command: {command}. "
                    "Available: build, impact, query, search, overview, changes"
                )
        except Exception as e:
            logger.error("code_graph.%s failed: %s", command, e)
            return f"Error in code_graph.{command}: {e}"

    def _cmd_build(self, repo: Path, full_rebuild: bool = False, **kw) -> str:
        """Build or update the code graph."""
        from code_review_graph.main import build_or_update_graph_tool

        result = self._run_sync(
            build_or_update_graph_tool(
                repo_root=str(repo),
                full_rebuild=full_rebuild,
            )
        )
        return str(result)

    def _cmd_impact(self, repo: Path, files: list[str] | None = None, **kw) -> str:
        """Get impact radius of changed files."""
        from code_review_graph.main import get_impact_radius_tool

        if files is None:
            # Default: check git diff for changed files
            import subprocess
            try:
                out = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    capture_output=True, text=True, cwd=str(repo),
                )
                files = [f for f in out.stdout.strip().split("\n") if f]
            except Exception:
                files = []

        if not files:
            return "No files specified. Pass files=['src/file.py'] or run in a repo with uncommitted changes."

        result = get_impact_radius_tool(
            repo_root=str(repo),
            paths=files,
        )
        return str(result)

    def _cmd_query(
        self,
        repo: Path,
        pattern: str = "callers_of",
        target: str = "",
        **kw,
    ) -> str:
        """Query the graph for relationships."""
        from code_review_graph.main import query_graph_tool

        result = query_graph_tool(
            repo_root=str(repo),
            pattern=pattern,
            target=target,
        )
        return str(result)

    def _cmd_search(self, repo: Path, query: str = "", **kw) -> str:
        """Semantic search over code symbols."""
        from code_review_graph.main import semantic_search_nodes_tool

        result = semantic_search_nodes_tool(
            repo_root=str(repo),
            query=query,
        )
        return str(result)

    def _cmd_overview(self, repo: Path, **kw) -> str:
        """Get high-level architecture overview."""
        from code_review_graph.main import get_architecture_overview_tool

        result = get_architecture_overview_tool(
            repo_root=str(repo),
        )
        return str(result)

    def _cmd_changes(self, repo: Path, **kw) -> str:
        """Detect and analyze changes for risk assessment."""
        from code_review_graph.main import detect_changes_tool

        result = self._run_sync(
            detect_changes_tool(repo_root=str(repo))
        )
        return str(result)
