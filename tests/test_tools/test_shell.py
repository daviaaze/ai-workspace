"""
Tests for the safe shell tool.

Verifies the allowlist works, dangerous commands are blocked,
and real commands produce expected output.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("AIW_FS_ROOT", str(tmp_path))
    (tmp_path / "hello.txt").write_text("hello world")
    return tmp_path


# ─── Allowed commands ───────────────────────────────


def test_ls_works(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="ls")
    assert "hello.txt" in out


def test_cat_works(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="cat hello.txt")
    assert "hello world" in out


def test_pwd_works(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="pwd")
    assert str(workspace) in out


def test_echo_works(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="echo hi")
    assert "hi" in out


def test_grep_works(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="grep hello hello.txt")
    assert "hello" in out


def test_extra_allowed_adds_command(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    # 'date' is in SAFE but let's test extra_allowed with something normally not there
    out = tool._run(command="printf %s hi", extra_allowed=["printf"])
    assert "hi" in out


# ─── Blocked commands ──────────────────────────────


def test_blocks_rm(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="rm hello.txt")
    assert "never allowed" in out or "not in the allowlist" in out
    assert (workspace / "hello.txt").exists()  # file still there


def test_blocks_sudo(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="sudo rm -rf /")
    assert "never allowed" in out


def test_blocks_kill(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="kill -9 1")
    assert "never allowed" in out


def test_blocks_curl(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="curl https://example.com")
    assert "never allowed" in out


def test_blocks_unknown_command(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="this_command_does_not_exist_xyz")
    assert "not in the allowlist" in out


# ─── Output capture ────────────────────────────────


def test_captures_stderr(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="ls nonexistent_file_xyz 2>&1; cat nonexistent_file_xyz 2>&1 || true")
    # ls/cat may or may not print to stderr depending on shell, but exit code should be reported
    assert "[exit" in out or "No such file" in out or "exit" in out


def test_timeout_protection(workspace, monkeypatch):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    # sleep 5 with 1s timeout
    out = tool._run(command="sleep 5", timeout=1, extra_allowed=["sleep"])
    assert "Timeout" in out


def test_truncates_long_output(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    # Generate >30k bytes of output
    out = tool._run(command="python3 -c \"print('x' * 50000)\"")
    assert "truncated" in out


# ─── Edge cases ────────────────────────────────────


def test_empty_command(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="")
    assert "Empty command" in out


def test_malformed_quotes(workspace):
    from ai_workspace.tools import SafeShellTool
    tool = SafeShellTool()
    out = tool._run(command="echo 'unclosed")
    assert "Parse error" in out


def test_get_shell_tool():
    from ai_workspace.tools import get_shell_tool
    tool = get_shell_tool()
    assert tool.name == "shell_exec"
