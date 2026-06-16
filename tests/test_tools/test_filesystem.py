"""
Tests for filesystem tools: ReadFileTool, WriteFileTool, EditFileTool,
ListDirTool, SearchCodeTool.

Uses a real temp directory for workspace root.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Set AIW_FS_ROOT to a temp directory for tool sandboxing."""
    monkeypatch.setenv("AIW_FS_ROOT", str(tmp_path))
    return tmp_path


# ─── ReadFileTool ───────────────────────────────────


def test_read_file_returns_contents(workspace):
    from ai_workspace.tools import ReadFileTool
    f = workspace / "hello.txt"
    f.write_text("hello world")
    tool = ReadFileTool()
    out = tool._run(path="hello.txt")
    assert "hello world" in out


def test_read_file_missing_returns_error(workspace):
    from ai_workspace.tools import ReadFileTool
    tool = ReadFileTool()
    out = tool._run(path="nope.txt")
    assert "not found" in out


def test_read_file_truncates_large_files(workspace):
    from ai_workspace.tools import ReadFileTool
    big = workspace / "big.txt"
    big.write_text("x" * 1000)
    tool = ReadFileTool()
    out = tool._run(path="big.txt", max_bytes=100)
    assert "[truncated" in out


def test_read_file_blocks_escape(workspace):
    from ai_workspace.tools import ReadFileTool
    tool = ReadFileTool()
    out = tool._run(path="../../etc/passwd")
    assert "escapes workspace" in out or "⛔" in out


# ─── WriteFileTool ──────────────────────────────────


def test_write_file_creates_file(workspace):
    from ai_workspace.tools import WriteFileTool
    tool = WriteFileTool()
    out = tool._run(path="new/file.txt", content="hello")
    assert "Wrote" in out
    assert (workspace / "new" / "file.txt").read_text() == "hello"


def test_write_file_refuses_overwrite(workspace):
    from ai_workspace.tools import WriteFileTool
    (workspace / "x.txt").write_text("original")
    tool = WriteFileTool()
    out = tool._run(path="x.txt", content="replacement")
    assert "exists" in out
    assert (workspace / "x.txt").read_text() == "original"


def test_write_file_overwrites_when_allowed(workspace):
    from ai_workspace.tools import WriteFileTool
    (workspace / "x.txt").write_text("original")
    tool = WriteFileTool()
    out = tool._run(path="x.txt", content="replacement", overwrite=True)
    assert (workspace / "x.txt").read_text() == "replacement"


# ─── EditFileTool ───────────────────────────────────


def test_edit_file_replaces_unique_string(workspace):
    from ai_workspace.tools import EditFileTool
    (workspace / "code.py").write_text("def foo():\n    return 1\n")
    tool = EditFileTool()
    out = tool._run(
        path="code.py",
        old_text="    return 1",
        new_text="    return 42",
    )
    assert "Edited" in out
    assert (workspace / "code.py").read_text() == "def foo():\n    return 42\n"


def test_edit_file_refuses_ambiguous_match(workspace):
    from ai_workspace.tools import EditFileTool
    (workspace / "x.py").write_text("x = 1\nx = 2\nx = 3\n")
    tool = EditFileTool()
    out = tool._run(path="x.py", old_text="x = ", new_text="y = ")
    assert "appears 3 times" in out


def test_edit_file_replace_all(workspace):
    from ai_workspace.tools import EditFileTool
    (workspace / "x.py").write_text("x = 1\nx = 2\nx = 3\n")
    tool = EditFileTool()
    out = tool._run(path="x.py", old_text="x = ", new_text="y = ", replace_all=True)
    assert "3 replacements" in out
    assert (workspace / "x.py").read_text() == "y = 1\ny = 2\ny = 3\n"


def test_edit_file_missing_old_text(workspace):
    from ai_workspace.tools import EditFileTool
    (workspace / "x.py").write_text("foo")
    tool = EditFileTool()
    out = tool._run(path="x.py", old_text="bar", new_text="baz")
    assert "not found" in out


# ─── ListDirTool ────────────────────────────────────


def test_list_dir_returns_files(workspace):
    from ai_workspace.tools import ListDirTool
    (workspace / "a.txt").write_text("a")
    (workspace / "b").mkdir()
    tool = ListDirTool()
    out = tool._run(path=".")
    assert "a.txt" in out
    assert "b" in out


def test_list_dir_excludes_pycache(workspace):
    from ai_workspace.tools import ListDirTool
    (workspace / "__pycache__").mkdir()
    (workspace / "real.py").write_text("")
    tool = ListDirTool()
    out = tool._run(path=".")
    assert "real.py" in out
    assert "__pycache__" not in out


def test_list_dir_recurses(workspace):
    from ai_workspace.tools import ListDirTool
    (workspace / "sub").mkdir()
    (workspace / "sub" / "deep.txt").write_text("deep")
    tool = ListDirTool()
    out = tool._run(path=".", max_depth=3)
    assert "deep.txt" in out


# ─── SearchCodeTool ─────────────────────────────────


def test_search_code_finds_pattern(workspace):
    from ai_workspace.tools import SearchCodeTool
    (workspace / "a.py").write_text("def foo():\n    return 1\n")
    (workspace / "b.py").write_text("def bar():\n    return 'no match here'\n")
    tool = SearchCodeTool()
    out = tool._run(pattern="def foo", path=".")
    assert "a.py" in out
    assert "b.py" not in out


def test_search_code_no_matches(workspace):
    from ai_workspace.tools import SearchCodeTool
    (workspace / "a.py").write_text("hello")
    tool = SearchCodeTool()
    out = tool._run(pattern="zzznottherezzz", path=".")
    assert "no matches" in out


def test_search_code_invalid_regex(workspace):
    from ai_workspace.tools import SearchCodeTool
    tool = SearchCodeTool()
    out = tool._run(pattern="[unclosed", path=".")
    assert "Invalid regex" in out


def test_search_code_respects_max_results(workspace):
    from ai_workspace.tools import SearchCodeTool
    for i in range(20):
        (workspace / f"f{i}.py").write_text(f"needle = {i}\n")
    tool = SearchCodeTool()
    out = tool._run(pattern="needle", path=".", max_results=5)
    assert "truncated" in out


# ─── Convenience function ──────────────────────────


def test_get_filesystem_tools_returns_all_five():
    from ai_workspace.tools import get_filesystem_tools
    tools = get_filesystem_tools()
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == {"read_file", "write_file", "edit_file", "list_dir", "search_code"}
