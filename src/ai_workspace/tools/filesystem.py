"""
Filesystem tools for CrewAI agents.

Provides safe, sandboxed read/write operations:
- ReadFileTool: read file contents
- WriteFileTool: create or overwrite a file
- EditFileTool: targeted string replacement (preserves formatting)
- ListDirTool: directory listing
- SearchCodeTool: grep-like content search

Safety: write operations are restricted to a configurable
workspace root (default: current working directory).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, ClassVar, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def _default_workspace() -> str:
    return os.environ.get("AIW_FS_ROOT", os.getcwd())


def _resolve_safe(path: str, workspace: str | None = None) -> Path:
    """Resolve a path and ensure it stays within the workspace.

    `workspace` defaults to the current AIW_FS_ROOT env var, looked up
    on every call so test monkeypatching works.
    """
    if workspace is None:
        workspace = _default_workspace()
    base = Path(workspace).resolve()
    target = (base / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise PermissionError(
            f"Path '{path}' escapes workspace root '{base}'"
        )
    return target


# ─── Read ─────────────────────────────────────────────


class ReadFileInput(BaseModel):
    path: str = Field(description="Path relative to workspace root, or absolute (must be inside workspace)")
    max_bytes: int = Field(default=200_000, description="Max file size to read (returns truncation notice if exceeded)")


class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = (
        "Read the contents of a file. Returns the full text. "
        "Use for inspecting source code, configs, or any text file. "
        "Path is relative to the workspace root unless absolute (must still be inside workspace)."
    )
    args_schema: Type[BaseModel] = ReadFileInput

    def _run(self, path: str, max_bytes: int = 200_000) -> str:
        try:
            p = _resolve_safe(path)
        except PermissionError as e:
            return f"⛔ {e}"
        if not p.exists():
            return f"❌ File not found: {path}"
        if not p.is_file():
            return f"❌ Not a file: {path}"
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"❌ Read error: {e}"
        if len(content) > max_bytes:
            return (
                f"{content[:max_bytes]}\n\n"
                f"... [truncated; file is {len(content)} bytes, max_bytes={max_bytes}]"
            )
        return content


# ─── Write ────────────────────────────────────────────


class WriteFileInput(BaseModel):
    path: str = Field(description="Path to write to (relative to workspace or absolute inside workspace)")
    content: str = Field(description="Content to write")
    overwrite: bool = Field(default=False, description="If False, refuses to overwrite existing files")


class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = (
        "Create a new file with the given content. "
        "By default refuses to overwrite existing files — set overwrite=true to replace. "
        "Use this for scaffolding new files. For targeted edits to existing files, prefer edit_file."
    )
    args_schema: Type[BaseModel] = WriteFileInput

    def _run(self, path: str, content: str, overwrite: bool = False) -> str:
        try:
            p = _resolve_safe(path)
        except PermissionError as e:
            return f"⛔ {e}"
        if p.exists() and not overwrite:
            return f"❌ File exists: {path}. Pass overwrite=true to replace."
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        except Exception as e:
            return f"❌ Write error: {e}"
        return f"✓ Wrote {len(content)} bytes to {path}"


# ─── Edit (targeted replacement) ─────────────────────


class EditFileInput(BaseModel):
    path: str = Field(description="Path to file to edit")
    old_text: str = Field(description="Exact text to replace (must be unique in the file)")
    new_text: str = Field(description="Replacement text")
    replace_all: bool = Field(default=False, description="Replace all occurrences (default: only if old_text appears once)")


class EditFileTool(BaseTool):
    name: str = "edit_file"
    description: str = (
        "Edit a file by replacing a unique chunk of text with new text. "
        "Safer than write_file because it preserves surrounding content and formatting. "
        "By default requires the old_text to appear exactly once in the file."
    )
    args_schema: Type[BaseModel] = EditFileInput

    def _run(self, path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
        try:
            p = _resolve_safe(path)
        except PermissionError as e:
            return f"⛔ {e}"
        if not p.exists():
            return f"❌ File not found: {path}"
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            return f"❌ Read error: {e}"

        occurrences = content.count(old_text)
        if occurrences == 0:
            return f"❌ old_text not found in {path}"
        if occurrences > 1 and not replace_all:
            return f"❌ old_text appears {occurrences} times in {path}. Use replace_all=true or provide a longer old_text."

        if replace_all:
            new_content = content.replace(old_text, new_text)
        else:
            new_content = content.replace(old_text, new_text, 1)

        try:
            p.write_text(new_content, encoding="utf-8")
        except Exception as e:
            return f"❌ Write error: {e}"
        return f"✓ Edited {path} ({occurrences} replacement{'s' if replace_all else ''})"


# ─── List directory ──────────────────────────────────


class ListDirInput(BaseModel):
    path: str = Field(default=".", description="Directory to list (relative to workspace)")
    max_depth: int = Field(default=2, description="Max depth to recurse")
    show_hidden: bool = Field(default=False, description="Include hidden files (starting with .)")


class ListDirTool(BaseTool):
    name: str = "list_dir"
    description: str = (
        "List files and directories under a path. "
        "Recurses up to max_depth levels. Excludes common noisy dirs by default (.git, __pycache__, node_modules, .venv)."
    )
    args_schema: Type[BaseModel] = ListDirInput

    EXCLUDE: ClassVar[set[str]] = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache", "target", "dist", "build"}

    def _run(self, path: str = ".", max_depth: int = 2, show_hidden: bool = False) -> str:
        try:
            root = _resolve_safe(path)
        except PermissionError as e:
            return f"⛔ {e}"
        if not root.exists():
            return f"❌ Not found: {path}"
        if not root.is_dir():
            return f"❌ Not a directory: {path}"

        lines: list[str] = []

        def walk(d: Path, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                entries = sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                lines.append(f"{'  ' * depth}⛔ [permission denied]")
                return
            for entry in entries:
                if not show_hidden and entry.name.startswith("."):
                    continue
                if entry.name in self.EXCLUDE:
                    continue
                kind = "📁" if entry.is_dir() else "📄"
                lines.append(f"{'  ' * depth}{kind} {entry.name}")
                if entry.is_dir():
                    walk(entry, depth + 1)

        walk(root, 0)
        return "\n".join(lines) if lines else "(empty directory)"


# ─── Search code ──────────────────────────────────────


class SearchCodeInput(BaseModel):
    pattern: str = Field(description="Regex pattern to search for")
    path: str = Field(default=".", description="Directory to search in (relative to workspace)")
    file_glob: str = Field(default="*", description="Glob to filter files (e.g. '*.py')")
    max_results: int = Field(default=50, description="Max matches to return")
    context_lines: int = Field(default=2, description="Lines of context to show around each match")


class SearchCodeTool(BaseTool):
    name: str = "search_code"
    description: str = (
        "Search for a regex pattern in files. "
        "Returns file path, line number, and surrounding context for each match. "
        "Use this instead of grep when an agent needs to find code patterns."
    )
    args_schema: Type[BaseModel] = SearchCodeInput

    def _run(
        self,
        pattern: str,
        path: str = ".",
        file_glob: str = "*",
        max_results: int = 50,
        context_lines: int = 2,
    ) -> str:
        try:
            root = _resolve_safe(path)
        except PermissionError as e:
            return f"⛔ {e}"
        if not root.exists():
            return f"❌ Not found: {path}"
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"❌ Invalid regex: {e}"

        matches: list[str] = []
        files = root.rglob(file_glob) if root.is_dir() else [root]
        for f in files:
            if not f.is_file():
                continue
            if any(part in f.parts for part in ListDirTool.EXCLUDE):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    rel = f.relative_to(root)
                    matches.append(f"{rel}:{i}: {line.rstrip()}")
                    if len(matches) >= max_results:
                        break
            if len(matches) >= max_results:
                matches.append(f"... (truncated at {max_results} matches)")
                break
        return "\n".join(matches) if matches else f"(no matches for /{pattern}/)"


# ─── Convenience: get all tools as a list ────────────


def get_filesystem_tools() -> list[BaseTool]:
    """Return all filesystem tools for agent wiring."""
    return [ReadFileTool(), WriteFileTool(), EditFileTool(), ListDirTool(), SearchCodeTool()]


__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "ListDirTool",
    "SearchCodeTool",
    "get_filesystem_tools",
]
