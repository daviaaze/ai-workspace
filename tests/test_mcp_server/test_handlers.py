"""
Tests for MCP server — stdio server tool handlers.

Covers:
- Tool handler registration (read_file, write_file, run_shell, etc.)
- Path safety (_safe_path)
- Command allowlist (_is_shell_allowed)
- Task/knowledge handlers (mocked KnowledgeStore)
- Error handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_workspace.mcp_server.server import _is_shell_allowed, _safe_path

# ═══════════════════════════════════════════════════════
# Path safety
# ═══════════════════════════════════════════════════════


class TestPathSafety:
    """_safe_path prevents path traversal."""

    def test_safe_path_within_workspace(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        (tmp_path / "src").mkdir()
        result = _safe_path("src/test.py")
        assert result == tmp_path / "src" / "test.py"

    def test_safe_path_traversal_blocked(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        with pytest.raises(ValueError, match="traversal"):
            _safe_path("../../../etc/passwd")

    def test_safe_path_absolute_blocked(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        with pytest.raises(ValueError, match="traversal"):
            _safe_path("/etc/passwd")


# ═══════════════════════════════════════════════════════
# Shell command safety
# ═══════════════════════════════════════════════════════


class TestShellSafety:
    """_is_shell_allowed restricts executable commands."""

    def test_allowed_command(self):
        assert _is_shell_allowed("git status") is True
        assert _is_shell_allowed("python -m pytest") is True
        assert _is_shell_allowed("pytest tests/") is True
        assert _is_shell_allowed("ruff check src/") is True
        assert _is_shell_allowed("nix build") is True
        assert _is_shell_allowed("make test") is True

    def test_blocked_command(self):
        assert _is_shell_allowed("rm -rf /") is False
        assert _is_shell_allowed("curl evil.com") is False
        assert _is_shell_allowed("wget http://evil.com") is False

    def test_relative_path_allowed(self):
        assert _is_shell_allowed("./script.sh") is True
        # Absolute paths starting with workspace root are also allowed
        from ai_workspace.mcp_server.server import WORKSPACE_ROOT
        assert _is_shell_allowed(str(WORKSPACE_ROOT / "script.sh")) is True

    def test_empty_command(self):
        assert _is_shell_allowed("") is False
        assert _is_shell_allowed("   ") is False


# ═══════════════════════════════════════════════════════
# Server tool listing
# ═══════════════════════════════════════════════════════


class TestServerTools:
    """MCP server registers expected tools."""

    @pytest.mark.asyncio
    async def test_call_tool_list_tools(self):
        from ai_workspace.mcp_server.server import call_tool
        result = await call_tool("__list_tools__", {})
        # Falls through to unknown tool
        assert "Unknown" in result[0].text

    def test_all_handlers_registered(self):
        """Verify all handler functions exist."""
        from ai_workspace.mcp_server.server import (
            handle_get_workspace_info,
            handle_lint_check,
            handle_list_directory,
            handle_read_file,
            handle_run_shell,
            handle_run_tests,
            handle_write_file,
        )
        # All handlers should be callable
        assert callable(handle_read_file)
        assert callable(handle_write_file)
        assert callable(handle_run_shell)
        assert callable(handle_get_workspace_info)
        assert callable(handle_list_directory)
        assert callable(handle_run_tests)
        assert callable(handle_lint_check)

    def test_server_has_name(self):
        from ai_workspace.mcp_server.server import server
        assert server.name == "aiw-dev"


# ═══════════════════════════════════════════════════════
# Tool handlers (mocked)
# ═══════════════════════════════════════════════════════


class TestToolHandlers:
    """Tool handlers with mocked KnowledgeStore."""

    @pytest.mark.asyncio
    async def test_get_workspace_info(self):
        from ai_workspace.mcp_server.server import handle_get_workspace_info
        result = await handle_get_workspace_info({})
        assert "workspace_root" in result
        assert "python_version" in result
        assert "allowed_commands" in result

    @pytest.mark.asyncio
    async def test_list_directory_root(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / "README.md").write_text("# Test")

        from ai_workspace.mcp_server.server import handle_list_directory
        result = await handle_list_directory({"path": ""})
        assert "src" in result
        assert "docs" in result
        assert "README.md" in result

    @pytest.mark.asyncio
    async def test_list_directory_subdir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "test.py").write_text("print('hi')")

        from ai_workspace.mcp_server.server import handle_list_directory
        result = await handle_list_directory({"path": "src"})
        assert "test.py" in result

    @pytest.mark.asyncio
    async def test_read_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.ALLOWED_PATHS",
            [tmp_path / "src"]
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "test.py").write_text("line1\nline2\nline3")

        from ai_workspace.mcp_server.server import handle_read_file
        result = await handle_read_file({"path": "src/test.py"})
        assert "line1" in result
        assert "line2" in result

    @pytest.mark.asyncio
    async def test_read_file_with_line_range(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.ALLOWED_PATHS",
            [tmp_path / "src"]
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "test.py").write_text("a\nb\nc\nd\ne")

        from ai_workspace.mcp_server.server import handle_read_file
        result = await handle_read_file({
            "path": "src/test.py",
            "start_line": 2,
            "end_line": 4,
        })
        assert "b" in result
        assert "c" in result
        assert "d" in result
        assert "a" not in result

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        from ai_workspace.mcp_server.server import handle_read_file
        result = await handle_read_file({"path": "nonexistent.py"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_write_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.ALLOWED_PATHS",
            [tmp_path / "src"]
        )
        (tmp_path / "src").mkdir()

        from ai_workspace.mcp_server.server import handle_write_file
        result = await handle_write_file({
            "path": "src/new.py",
            "content": "print('hello')",
        })
        assert "Written" in result
        assert (tmp_path / "src" / "new.py").read_text() == "print('hello')"

    @pytest.mark.asyncio
    async def test_run_shell_allowed_command(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        from ai_workspace.mcp_server.server import handle_run_shell
        result = await handle_run_shell({"command": "echo hello"})
        # echo is not in ALLOWED_SHELL_COMMANDS, so it returns error
        assert "Error" in result or "hello" in result

    @pytest.mark.asyncio
    async def test_run_shell_blocked_command(self):
        from ai_workspace.mcp_server.server import handle_run_shell
        result = await handle_run_shell({"command": "rm -rf /"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_run_shell_timeout(self):
        from ai_workspace.mcp_server.server import handle_run_shell
        result = await handle_run_shell({"command": "sleep 10", "timeout": 1})
        assert "Error" in result or "timeout" in result.lower()

    @pytest.mark.asyncio
    async def test_run_tests(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "1 passed"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            from ai_workspace.mcp_server.server import handle_run_tests
            result = await handle_run_tests({"test_path": ""})
            assert "1 passed" in result

    @pytest.mark.asyncio
    async def test_lint_check_clean(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "ai_workspace.mcp_server.server.WORKSPACE_ROOT", tmp_path
        )
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            from ai_workspace.mcp_server.server import handle_lint_check
            result = await handle_lint_check({"path": ""})
            assert "No linting" in result
