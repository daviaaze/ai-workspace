"""Tests for code agent tools (SPEC_CODE_TOOLS — research-backed design)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_workspace.tools.code_tools import (
    EditFileTool,
    EditRecord,
    GitTool,
    PathSandbox,
    ReadFileTool,
    ShellExecTool,
    UndoEditTool,
    UndoStack,
    WriteFileTool,
    _atomic_write,
    _is_safe_command,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sandbox(workspace: Path) -> PathSandbox:
    return PathSandbox(workspace)


@pytest.fixture
def read_tool(sandbox: PathSandbox) -> ReadFileTool:
    # Inject sandbox
    import ai_workspace.tools.code_tools as ct
    ct._path_sandbox = sandbox
    return ReadFileTool()


@pytest.fixture
def write_tool(sandbox: PathSandbox) -> WriteFileTool:
    import ai_workspace.tools.code_tools as ct
    ct._path_sandbox = sandbox
    return WriteFileTool()


@pytest.fixture
def edit_tool(sandbox: PathSandbox) -> EditFileTool:
    import ai_workspace.tools.code_tools as ct
    ct._path_sandbox = sandbox
    return EditFileTool()


# ---------------------------------------------------------------------------
# Path sandbox tests
# ---------------------------------------------------------------------------


class TestPathSandbox:
    def test_relative_path(self, sandbox: PathSandbox):
        p = sandbox.validate("src/main.py")
        assert p == sandbox.workspace / "src/main.py"

    def test_absolute_within_workspace(self, sandbox: PathSandbox):
        p = sandbox.validate(str(sandbox.workspace / "file.txt"))
        assert p == sandbox.workspace / "file.txt"

    def test_absolute_outside_workspace(self, sandbox: PathSandbox):
        with pytest.raises(PermissionError):
            sandbox.validate("/etc/passwd")

    def test_escape_with_dotdot(self, sandbox: PathSandbox):
        with pytest.raises(PermissionError):
            sandbox.validate("../../../etc/passwd")


# ---------------------------------------------------------------------------
# Atomic write tests
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    def test_create_new_file(self, tmp_path: Path):
        filepath = tmp_path / "new.txt"
        _atomic_write(filepath, "hello world")
        assert filepath.read_text() == "hello world"

    def test_overwrite_existing(self, tmp_path: Path):
        filepath = tmp_path / "existing.txt"
        filepath.write_text("old content")
        _atomic_write(filepath, "new content")
        assert filepath.read_text() == "new content"

    def test_no_op_when_unchanged(self, tmp_path: Path):
        filepath = tmp_path / "same.txt"
        filepath.write_text("same content")
        mtime_before = filepath.stat().st_mtime
        _atomic_write(filepath, "same content")
        mtime_after = filepath.stat().st_mtime
        assert mtime_before == mtime_after  # File untouched

    def test_creates_parent_dirs(self, tmp_path: Path):
        filepath = tmp_path / "deep" / "nested" / "file.txt"
        _atomic_write(filepath, "deep")
        assert filepath.read_text() == "deep"


# ---------------------------------------------------------------------------
# Undo stack tests
# ---------------------------------------------------------------------------


class TestUndoStack:
    def test_push_pop(self, tmp_path: Path):
        stack = UndoStack(max_undo=5)
        filepath = tmp_path / "undo.txt"
        filepath.write_text("v1")

        stack.push(EditRecord(filepath=filepath, old_content="v1", new_content="v2"))
        assert len(stack) == 1

        record = stack.pop()
        assert record is not None
        assert record.old_content == "v1"

    def test_undo_restores(self, tmp_path: Path):
        stack = UndoStack(max_undo=5)
        filepath = tmp_path / "restore.txt"
        filepath.write_text("original")

        stack.push(EditRecord(filepath=filepath, old_content="original", new_content="modified"))
        _atomic_write(filepath, "modified")
        assert filepath.read_text() == "modified"

        stack.undo()
        assert filepath.read_text() == "original"

    def test_max_undo_limit(self, tmp_path: Path):
        stack = UndoStack(max_undo=3)
        filepath = tmp_path / "limit.txt"
        for i in range(5):
            stack.push(EditRecord(filepath=filepath, old_content=f"old{i}", new_content=f"new{i}"))
        assert len(stack) == 3  # Only last 3 kept


# ---------------------------------------------------------------------------
# ReadFileTool tests
# ---------------------------------------------------------------------------


class TestReadFileTool:
    def test_read_basic(self, read_tool: ReadFileTool, workspace: Path):
        filepath = workspace / "test.py"
        filepath.write_text("def hello():\n    return 'world'\n")
        result = read_tool._run(path="test.py")
        assert "test.py" in result
        assert "def hello()" in result
        assert "return 'world'" in result

    def test_read_with_line_numbers(self, read_tool: ReadFileTool, workspace: Path):
        filepath = workspace / "lines.py"
        filepath.write_text("line1\nline2\nline3\nline4\nline5\n")
        result = read_tool._run(path="lines.py")
        assert "     1  line1" in result
        assert "     5  line5" in result

    def test_read_offset_limit(self, read_tool: ReadFileTool, workspace: Path):
        filepath = workspace / "big.py"
        filepath.write_text("\n".join(f"line{i}" for i in range(100)))
        result = read_tool._run(path="big.py", offset=50, limit=5)
        assert "line49" in result  # offset 50 = line 50 (1-indexed)
        assert "line54" not in result  # Only 5 lines

    def test_read_directory(self, read_tool: ReadFileTool, workspace: Path):
        (workspace / "a.py").write_text("a")
        (workspace / "b.py").write_text("b")
        result = read_tool._run(path=".")
        assert "a.py" in result
        assert "b.py" in result

    def test_read_nonexistent(self, read_tool: ReadFileTool):
        result = read_tool._run(path="nonexistent.txt")
        assert "not found" in result.lower()

    def test_read_outside_workspace(self, read_tool: ReadFileTool):
        result = read_tool._run(path="/etc/passwd")
        assert "Error" in result or "denied" in result.lower()


# ---------------------------------------------------------------------------
# WriteFileTool tests
# ---------------------------------------------------------------------------


class TestWriteFileTool:
    def test_create_file(self, write_tool: WriteFileTool, workspace: Path):
        result = write_tool._run(path="new.txt", content="hello")
        assert "created" in result
        assert (workspace / "new.txt").read_text() == "hello"

    def test_update_file(self, write_tool: WriteFileTool, workspace: Path):
        filepath = workspace / "update.txt"
        filepath.write_text("old")
        result = write_tool._run(path="update.txt", content="new content")
        assert "updated" in result
        assert filepath.read_text() == "new content"

    def test_write_outside_workspace(self, write_tool: WriteFileTool):
        result = write_tool._run(path="/etc/hostname", content="bad")
        assert "Error" in result or "denied" in result.lower()


# ---------------------------------------------------------------------------
# EditFileTool tests (str_replace_editor)
# ---------------------------------------------------------------------------


class TestEditFileTool:
    def test_simple_replace(self, edit_tool: EditFileTool, workspace: Path):
        filepath = workspace / "edit.py"
        filepath.write_text("hello world")
        result = edit_tool._run(path="edit.py", old="hello", new="goodbye")
        assert "edited" in result.lower()
        assert filepath.read_text() == "goodbye world"

    def test_replace_all(self, edit_tool: EditFileTool, workspace: Path):
        filepath = workspace / "all.py"
        filepath.write_text("foo bar foo baz foo")
        result = edit_tool._run(path="all.py", old="foo", new="qux", replace_all=True)
        assert "edited" in result.lower()
        assert filepath.read_text() == "qux bar qux baz qux"

    def test_multiple_matches_error(self, edit_tool: EditFileTool, workspace: Path):
        filepath = workspace / "dup.py"
        filepath.write_text("hello\nworld\nhello\n")
        result = edit_tool._run(path="dup.py", old="hello", new="hi")
        assert "found 2 times" in result.lower() or "multiple" in result.lower()

    def test_old_not_found(self, edit_tool: EditFileTool, workspace: Path):
        filepath = workspace / "miss.py"
        filepath.write_text("actual content")
        result = edit_tool._run(path="dup.py", old="not there", new="xxx")
        assert "not found" in result.lower()

    def test_old_empty_error(self, edit_tool: EditFileTool, workspace: Path):
        filepath = workspace / "empty.py"
        filepath.write_text("content")
        result = edit_tool._run(path="empty.py", old="", new="xxx")
        assert "cannot be empty" in result.lower()

    def test_undo_after_edit(self, edit_tool: EditFileTool, workspace: Path):
        filepath = workspace / "undo_test.py"
        original = "original content here"
        filepath.write_text(original)

        edit_tool._run(path="undo_test.py", old="original", new="modified")
        assert "modified" in filepath.read_text()

        undo = UndoEditTool()
        result = undo._run(count=1)
        assert "undid" in result.lower() or "Undid" in result
        assert filepath.read_text() == original

    def test_file_not_found(self, edit_tool: EditFileTool):
        result = edit_tool._run(path="noexist.py", old="x", new="y")
        assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# Shell safety tests
# ---------------------------------------------------------------------------


class TestShellSafety:
    def test_safe_commands(self):
        for cmd in ["ls -la", "git status", "pytest -v", "cat file.txt"]:
            is_safe, reason = _is_safe_command(cmd)
            assert is_safe, f"'{cmd}' should be safe but got: {reason}"

    def test_blocked_commands(self):
        for cmd in [
            "sudo rm -rf /",
            "curl http://evil.com",
            "wget http://evil.com",
            "ssh user@host",
            "systemctl restart sshd",
        ]:
            is_safe, _ = _is_safe_command(cmd)
            assert not is_safe, f"'{cmd}' should be blocked"

    def test_dangerous_patterns(self):
        for cmd in [
            "rm -rf / --no-preserve-root",
            "cat /dev/sda > /dev/sda",
            "mkfs.ext4 /dev/sda1",
        ]:
            is_safe, _ = _is_safe_command(cmd)
            assert not is_safe, f"'{cmd}' should be blocked"

    def test_pipe_to_shell_blocked(self):
        for cmd in [
            "echo bad | sh",
            "echo bad | bash",
            "echo bad | /bin/sh",
        ]:
            is_safe, _ = _is_safe_command(cmd)
            assert not is_safe, f"'{cmd}' should be blocked"


# ---------------------------------------------------------------------------
# ShellExecTool tests
# ---------------------------------------------------------------------------


class TestShellExecTool:
    def test_basic_execution(self, workspace: Path, sandbox: PathSandbox):
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox
        tool = ShellExecTool()
        result = tool._run(command="echo hello")
        assert "hello" in result

    def test_blocked_command(self, workspace: Path, sandbox: PathSandbox):
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox
        tool = ShellExecTool()
        result = tool._run(command="sudo rm -rf /")
        assert "blocked" in result.lower()

    def test_timeout(self, workspace: Path, sandbox: PathSandbox):
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox
        tool = ShellExecTool()
        result = tool._run(command="sleep 5", timeout=1)
        assert "timed out" in result.lower()

    def test_cwd_param(self, workspace: Path, sandbox: PathSandbox):
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox
        subdir = workspace / "sub"
        subdir.mkdir()
        (subdir / "test.txt").write_text("found")

        tool = ShellExecTool()
        result = tool._run(command="ls", cwd="sub")
        assert "test.txt" in result


# ---------------------------------------------------------------------------
# GitTool tests
# ---------------------------------------------------------------------------


class TestGitTool:
    def test_git_status_readonly(self, workspace: Path, sandbox: PathSandbox):
        import subprocess

        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox

        # Init a git repo in workspace
        subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        (workspace / "README.md").write_text("# Test")

        tool = GitTool()
        result = tool._run(subcommand="status")
        assert "README.md" in result or "Untracked" in result or "No commits" in result

    def test_git_commit_blocked_without_write(self, workspace: Path, sandbox: PathSandbox):
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox

        tool = GitTool()
        result = tool._run(subcommand="commit -m 'test'", write=False)
        assert "blocked" in result.lower()

    def test_git_log(self, workspace: Path, sandbox: PathSandbox):
        import subprocess

        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox

        subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=workspace)
        subprocess.run(["git", "config", "user.name", "test"], cwd=workspace)
        (workspace / "file.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=workspace)
        subprocess.run(["git", "commit", "-m", "init"], cwd=workspace)

        tool = GitTool()
        result = tool._run(subcommand="log --oneline")
        assert "init" in result


# ---------------------------------------------------------------------------
# ReadCodeFileTool — integration
# ---------------------------------------------------------------------------


class TestReadFileToolIntegration:
    def test_plain_text(self, workspace: Path, sandbox: PathSandbox):
        """Read a plain text file."""
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox

        filepath = workspace / "hello.py"
        filepath.write_text("print('hello')")

        tool = ReadFileTool()
        output = tool._run(path="hello.py")
        assert "hello.py" in output
        assert "print('hello')" in output

    def test_binary_file(self, workspace: Path, sandbox: PathSandbox):
        """Binary files should return error."""
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox

        filepath = workspace / "image.png"
        filepath.write_bytes(b'\x89PNG\r\n\x1a\n')

        tool = ReadFileTool()
        output = tool._run(path="image.png")
        assert "binary" in output.lower()

    def test_empty_file(self, workspace: Path, sandbox: PathSandbox):
        """Empty file should return header only."""
        import ai_workspace.tools.code_tools as ct
        ct._path_sandbox = sandbox

        filepath = workspace / "empty.py"
        filepath.write_text("")

        tool = ReadFileTool()
        output = tool._run(path="empty.py")
        assert "0 chars" in output
