"""Automatic project context injection for agent system prompts."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectContext:
    """Structured project context for agent injection."""
    cwd: str
    git_branch: str = ""
    git_status: str = ""
    git_recent_commits: list[str] = field(default_factory=list)
    project_tree: str = ""
    recent_files: list[str] = field(default_factory=list)
    open_files: list[str] = field(default_factory=list)
    file_count: int = 0
    language: str = ""  # python, rust, go, etc.


class ContextBundle:
    """Collects and formats project context for agent injection.
    
    The context is injected as XML tags in the agent's system prompt,
    following pi's <project_context> pattern.
    """
    
    # Directories to exclude from project tree
    EXCLUDE_DIRS = {
        ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
        "node_modules", ".venv", "venv", "env", ".env",
        "dist", "build", ".aiw", "target", ".direnv",
        ".ruff_cache", ".tox", "egg-info",
    }
    
    # Files that indicate project type
    LANGUAGE_INDICATORS = {
        "pyproject.toml": "python",
        "setup.py": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "package.json": "javascript/typescript",
        "CMakeLists.txt": "c/c++",
        "flake.nix": "nix",
        "Makefile": "make",
    }
    
    def __init__(self, cwd: str | None = None, max_tree_depth: int = 3):
        self.cwd = Path(cwd).resolve() if cwd else Path.cwd()
        self.max_tree_depth = max_tree_depth
    
    async def build(
        self,
        session_id: str | None = None,
        include_git: bool = True,
        include_tree: bool = True,
        tree_max_files: int = 200,
    ) -> str:
        """Build the complete project context string.
        
        Returns a formatted string ready for injection into the agent prompt.
        """
        context = ProjectContext(cwd=str(self.cwd))
        
        # Git info
        if include_git and self._is_git_repo():
            context.git_branch = self._get_git_branch()
            context.git_status = self._get_git_status()
            context.git_recent_commits = self._get_recent_commits(5)
        
        # Project tree
        if include_tree:
            context.project_tree = self._get_project_tree(tree_max_files)
        
        # Language detection
        context.language = self._detect_language()
        
        # Recent files
        context.recent_files = self._get_recent_files(10)
        
        return self._format_context(context, session_id)
    
    def _is_git_repo(self) -> bool:
        return (self.cwd / ".git").exists()
    
    def _get_git_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.cwd, timeout=3,
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    def _get_git_status(self) -> str:
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=self.cwd, timeout=3,
            )
            return result.stdout.strip()[:2000]
        except Exception:
            return ""
    
    def _get_recent_commits(self, count: int = 5) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--oneline", "--no-decorate"],
                capture_output=True, text=True, cwd=self.cwd, timeout=3,
            )
            return [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        except Exception:
            return []
    
    def _get_project_tree(self, max_files: int = 200) -> str:
        """Generate a text tree of the project directory.
        
        Excludes common build/dependency directories.
        """
        lines = []
        file_count = 0
        
        try:
            for root, dirs, files in os.walk(self.cwd):
                # Filter excluded dirs
                dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS and not d.startswith(".")]
                
                rel = Path(root).relative_to(self.cwd)
                depth = len(rel.parts) if str(rel) != "." else 0
                
                if depth > self.max_tree_depth:
                    dirs.clear()
                    continue
                
                prefix = "  " * depth
                
                if depth == 0:
                    lines.append(f"{self.cwd.name}/")
                else:
                    lines.append(f"{prefix}{rel.name}/")
                
                # Add files (limited)
                for f in sorted(files)[:20]:
                    if not f.startswith(".") and file_count < max_files:
                        if depth <= self.max_tree_depth:
                            lines.append(f"{prefix}  {f}")
                            file_count += 1
                
                if file_count >= max_files:
                    lines.append(f"{prefix}  ... ({max_files}+ files)")
                    break
        
        except Exception:
            return "[project tree unavailable]"
        
        return "\n".join(lines[:max_files + 50])
    
    def _detect_language(self) -> str:
        """Detect the primary programming language of the project."""
        for indicator, lang in self.LANGUAGE_INDICATORS.items():
            if (self.cwd / indicator).exists():
                return lang
        return ""
    
    def _get_recent_files(self, count: int = 10) -> list[str]:
        """Get recently modified files using git."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~5", "HEAD"],
                capture_output=True, text=True, cwd=self.cwd, timeout=3,
            )
            files = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
            return files[:count]
        except Exception:
            return []
    
    def _format_context(self, ctx: ProjectContext, session_id: str | None = None) -> str:
        """Format the context as XML tags for injection into the agent prompt.
        
        Follows pi's <project_context> pattern.
        """
        parts = []
        parts.append("<project_context>")
        parts.append(f"  <cwd>{ctx.cwd}</cwd>")
        
        if ctx.language:
            parts.append(f"  <language>{ctx.language}</language>")
        
        if ctx.git_branch:
            parts.append(f"  <git_branch>{ctx.git_branch}</git_branch>")
        
        if ctx.git_recent_commits:
            parts.append("  <recent_commits>")
            for commit in ctx.git_recent_commits[:3]:
                parts.append(f"    {commit}")
            parts.append("  </recent_commits>")
        
        if ctx.git_status:
            # Truncate for prompt
            status = ctx.git_status[:500]
            parts.append(f"  <git_status>\n{status}\n  </git_status>")
        
        if ctx.project_tree:
            tree = ctx.project_tree[:2000]
            parts.append(f"  <project_tree>\n{tree}\n  </project_tree>")
        
        if ctx.recent_files:
            parts.append("  <recent_files>")
            for f in ctx.recent_files[:5]:
                parts.append(f"    {f}")
            parts.append("  </recent_files>")
        
        if session_id:
            parts.append(f"  <session_id>{session_id}</session_id>")
        
        parts.append("</project_context>")
        
        return "\n".join(parts)
    
    def get_guidelines(self) -> list[str]:
        """Get project-specific guidelines for the agent.
        
        These are injected as instructions in the system prompt.
        """
        guidelines = []
        
        # Nix project guidelines
        if (self.cwd / "flake.nix").exists():
            guidelines.append("This is a Nix project. Use 'nix build .#default' to build.")
        
        # Python project guidelines
        if (self.cwd / "pyproject.toml").exists():
            guidelines.append("Use 'python -m pytest' to run tests.")
            guidelines.append("Format with black/isort before committing.")
        
        # Rust project guidelines
        if (self.cwd / "Cargo.toml").exists():
            guidelines.append("Use 'cargo build', 'cargo test', 'cargo clippy'.")
        
        return guidelines
