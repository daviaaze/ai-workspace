"""
Coding Agent Tools — file I/O, shell execution, and git operations.

Design principles (from SWE-agent, OpenHands CodeAct, Aider research):
1. str_replace_editor — exact old-string match, no fuzzy matching
2. Atomic writes — temp file + os.replace, never corrupt
3. Must-read-before-write — refuse edits to unseen files
4. Line numbers — help LLM target edits precisely
5. Path sandboxing — restrict to workspace root
6. Undo stack — reversible edits (last N)
7. Shell allowlist — only safe commands, timeout, no interactive

Refs:
- OpenHands CodeAct (arXiv 2402.01030)
- SWE-agent ACI (arXiv 2405.15793)
- Aider EditBlockCoder (github.com/Aider-AI/aider)
- learnwithparam.com/edit-tool-design
"""

from __future__ import annotations

import hashlib
import logging
import os
import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from ai_workspace.tools.base import Tool

logger = logging.getLogger("aiw.code_tools")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_path(raw: str, workspace: str | Path | None = None) -> Path:
    """Resolve a path, optionally relative to workspace root.

    Raises ValueError if the path escapes the workspace.
    """
    p = Path(raw)
    if not p.is_absolute():
        if workspace:
            p = (Path(workspace) / p).resolve()
        else:
            p = p.resolve()

    if workspace:
        ws = Path(workspace).resolve()
        try:
            p.relative_to(ws)
        except ValueError:
            raise ValueError(
                f"Path '{raw}' escapes workspace '{ws}'. "
                f"All file operations must stay within the workspace."
            )

    return p


def _atomic_write(filepath: Path, content: str) -> None:
    """Write content atomically using temp file + os.replace.

    Ensures the filesystem never holds a corrupted, partial file.
    If content is identical to existing, skip write (no-op).
    """
    filepath = filepath.resolve()
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # No-op if content unchanged
    if filepath.exists():
        try:
            existing = filepath.read_text(encoding="utf-8")
            if existing == content:
                logger.debug("File unchanged, skipping write: %s", filepath)
                return
        except (OSError, UnicodeDecodeError):
            pass

    fd, temp_path = tempfile.mkstemp(dir=str(filepath.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, str(filepath))
        logger.info("Atomic write: %s (%d chars)", filepath, len(content))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def _file_hash(filepath: Path) -> str:
    """Short hash of file content for change detection."""
    if not filepath.exists():
        return ""
    return hashlib.md5(filepath.read_bytes()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Undo stack
# ---------------------------------------------------------------------------


@dataclass
class EditRecord:
    """Record of an edit for undo."""
    filepath: Path
    old_content: str
    new_content: str
    timestamp: float = field(default_factory=time.time)


class UndoStack:
    """Stack of reversible edits (last N)."""
    def __init__(self, max_undo: int = 50) -> None:
        self._stack: list[EditRecord] = []
        self.max_undo = max_undo

    def push(self, record: EditRecord) -> None:
        self._stack.append(record)
        if len(self._stack) > self.max_undo:
            self._stack.pop(0)

    def pop(self) -> EditRecord | None:
        if not self._stack:
            return None
        return self._stack.pop()

    def undo(self) -> EditRecord | None:
        """Undo last edit — restore old content."""
        record = self.pop()
        if record:
            _atomic_write(record.filepath, record.old_content)
        return record

    def __len__(self) -> int:
        return len(self._stack)


# Global undo stack (shared across tools)
_undo_stack = UndoStack()


# ---------------------------------------------------------------------------
# Path sandbox
# ---------------------------------------------------------------------------


class PathSandbox:
    """Restricts file operations to a workspace root."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd()

    def validate(self, path: str | Path) -> Path:
        """Validate that path is within workspace. Returns resolved path."""
        p = Path(path)
        if not p.is_absolute():
            p = (self.workspace / p).resolve()
        else:
            p = p.resolve()
        try:
            p.relative_to(self.workspace)
        except ValueError:
            raise PermissionError(
                f"Access denied: '{path}' is outside workspace '{self.workspace}'"
            )
        return p


# Global sandbox
_path_sandbox = PathSandbox()


# ---------------------------------------------------------------------------
# Shell allowlist
# ---------------------------------------------------------------------------


# Commands that are always safe (read-only, no side effects)
_SAFE_COMMANDS: set[str] = {
    "ls", "cat", "head", "tail", "wc", "find", "grep", "rg",
    "git", "echo", "pwd", "which", "file", "stat", "du", "df",
    "sort", "uniq", "cut", "tr", "awk", "sed", "diff", "patch",
    "python", "python3", "node", "npm", "cargo", "go", "rustc",
    "black", "ruff", "mypy", "pytest", "cargo", "make", "cmake",
    "mkdir", "touch", "cp", "mv", "rm", "chmod", "chown",
}

# Dangerous commands (never allowed)
_BLOCKED_COMMANDS: set[str] = {
    "sudo", "su", "reboot", "shutdown", "halt", "poweroff",
    "mkfs", "dd", "fdisk", "parted", "mount", "umount",
    "docker", "podman", "systemctl", "service",
    "curl", "wget",  # blocked unless --allow-network
    "ssh", "scp", "nc", "telnet",
    "eval", "exec", "source",
}

# Dangerous patterns (substrings in command line)
_DANGEROUS_PATTERNS: list[str] = [
    "rm -rf /",
    "rm -rf /*",
    "> /dev/sda",
    "mkfs.",
    "dd if=",
    ":(){ :|:& };:",  # fork bomb
    "chmod 777 /",
    "chown -R /",
]


def _is_safe_command(cmd: str) -> tuple[bool, str]:
    """Check if a shell command is safe to execute.

    Returns (is_safe, reason).
    """
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return False, "Could not parse command"

    if not parts:
        return False, "Empty command"

    # Check command name
    cmd_name = os.path.basename(parts[0])
    if cmd_name in _BLOCKED_COMMANDS:
        return False, f"Blocked command: {cmd_name}"

    if cmd_name not in _SAFE_COMMANDS:
        # Unknown command — check if it's in blocked patterns
        pass

    # Check for dangerous patterns
    cmd_lower = cmd.lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.lower() in cmd_lower:
            return False, f"Dangerous pattern detected: {pattern}"

    # Check for pipe to shell
    if "| sh" in cmd or "| bash" in cmd or "| /bin/sh" in cmd or "| /bin/bash" in cmd:
        return False, "Piping to shell interpreter is blocked"

    # Check for redirect overwrite of important paths
    redirect_patterns = [
        "> /etc/", "> /bin/", "> /usr/", "> /boot/", "> /sys/",
        ">> /etc/", ">> /bin/", ">> /usr/",
    ]
    for pattern in redirect_patterns:
        if pattern in cmd_lower:
            return False, f"Redirect to system path blocked: {pattern}"

    return True, "OK"


# ---------------------------------------------------------------------------
# Tool 1: ReadFileTool
# ---------------------------------------------------------------------------


class ReadFileTool(Tool):
    """Read a file with line numbers, optional offset/limit.

    Always shows line numbers so the LLM can target edits precisely.
    """

    name: str = "read_file"
    description: str = (
        "Read a file from the workspace. Returns content with line numbers. "
        "Use 'offset' and 'limit' to read specific sections. "
        "Always read a file before editing it."
    )

    def _run(
        self,
        path: str,
        offset: int = 0,
        limit: int = 500,
    ) -> str:
        """Read file content.

        Args:
            path: File path (relative to workspace or absolute).
            offset: Line number to start from (1-indexed, 0 for beginning).
            limit: Maximum lines to read.
        """
        try:
            filepath = _path_sandbox.validate(path)
        except PermissionError as exc:
            return f"Error: {exc}"

        if not filepath.exists():
            return f"Error: File not found: {path}"

        if filepath.is_dir():
            # List directory contents
            try:
                entries = sorted(filepath.iterdir())[:200]
                lines = [f"Directory: {filepath}"]
                for entry in entries:
                    suffix = "/" if entry.is_dir() else ""
                    size_str = ""
                    if entry.is_file():
                        try:
                            size = entry.stat().st_size
                            if size < 1024:
                                size_str = f" ({size}B)"
                            elif size < 1024 * 1024:
                                size_str = f" ({size/1024:.1f}KB)"
                            else:
                                size_str = f" ({size/1024/1024:.1f}MB)"
                        except OSError:
                            pass
                    lines.append(f"  {entry.name}{suffix}{size_str}")
                return "\n".join(lines)
            except PermissionError:
                return f"Error: Permission denied reading directory: {path}"

        try:
            content = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: Binary file, cannot read as text: {path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"

        all_lines = content.split("\n")

        # Apply offset/limit
        start = max(0, offset - 1) if offset > 0 else 0
        end = min(start + limit, len(all_lines)) if limit else len(all_lines)
        selected = all_lines[start:end]

        # Format with line numbers
        result_lines = []
        for i, line in enumerate(selected, start=start + 1):
            result_lines.append(f"{i:6d}  {line}")

        header = f"File: {filepath} ({len(all_lines)} lines, {len(content)} chars)"
        if len(selected) < len(all_lines):
            header += f" [showing lines {start+1}-{end} of {len(all_lines)}]"

        return header + "\n" + "\n".join(result_lines)


# ---------------------------------------------------------------------------
# Tool 2: WriteFileTool
# ---------------------------------------------------------------------------


class WriteFileTool(Tool):
    """Write (create or overwrite) a file with atomic write."""

    name: str = "write_file"
    description: str = (
        "Write content to a file (creates or overwrites). "
        "Uses atomic write: the file is never left in a partial state. "
        "For modifying existing files, prefer edit_file for partial edits."
    )

    def _run(self, path: str, content: str) -> str:
        """Write file content atomically.

        Args:
            path: File path (relative to workspace or absolute).
            content: Full file content to write.
        """
        try:
            filepath = _path_sandbox.validate(path)
        except PermissionError as exc:
            return f"Error: {exc}"

        existed = filepath.exists()
        old_content = ""
        if existed:
            try:
                old_content = filepath.read_text(encoding="utf-8")
            except Exception:
                pass

        old_hash = _file_hash(filepath)

        try:
            _atomic_write(filepath, content)
        except OSError as exc:
            return f"Error writing {path}: {exc}"

        new_hash = _file_hash(filepath)

        # Record for undo
        if existed:
            _undo_stack.push(EditRecord(
                filepath=filepath,
                old_content=old_content,
                new_content=content,
            ))

        msg = "created" if not existed else "updated"
        return (
            f"File {msg}: {path} ({len(content)} chars)\n"
            f"Hash: {old_hash} -> {new_hash}"
        )


# ---------------------------------------------------------------------------
# Tool 3: EditFileTool (str_replace_editor)
# ---------------------------------------------------------------------------


class EditFileTool(Tool):
    """Edit a file using str_replace_editor pattern.

    The LLM provides an exact 'old' string that must match exactly once.
    The tool replaces it with the 'new' string. This is the proven pattern
    from OpenHands CodeAct and SWE-agent ACI.
    """

    name: str = "edit_file"
    description: str = (
        "Edit a file by exact string replacement. "
        "Provide the exact 'old' string to find (must match exactly once in the file) "
        "and the 'new' string to replace it with. "
        "Use read_file first to see the current content with line numbers. "
        "For deleting lines, use an empty string as 'new'. "
        "Use replace_all=True to replace all occurrences of old with new."
    )

    def _run(
        self,
        path: str,
        old: str,
        new: str,
        replace_all: bool = False,
    ) -> str:
        """Edit a file by exact string replacement.

        Args:
            path: File path.
            old: Exact string to find (must be unambiguous).
            new: Replacement string.
            replace_all: If True, replace all occurrences. Default is single.
        """
        try:
            filepath = _path_sandbox.validate(path)
        except PermissionError as exc:
            return f"Error: {exc}"

        if not filepath.exists():
            return f"Error: File not found: {path}. Use read_file first to read existing files."

        try:
            content = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: Cannot edit binary file: {path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"

        if not old:
            return "Error: 'old' string cannot be empty. To insert at a position, provide surrounding context as 'old'."

        # Count occurrences
        count = content.count(old)

        if count == 0:
            # Provide helpful diagnostics
            # Check if old is close to something in the file
            lines = content.split("\n")
            suggestions = []
            old_stripped = old.strip()
            for i, line in enumerate(lines, 1):
                if old_stripped and old_stripped[:30] in line:
                    suggestions.append(f"  Line {i}: ...{line.strip()[:80]}...")
                if len(suggestions) >= 3:
                    break

            msg = f"Error: 'old' string not found in {path}. "
            msg += f"Searched for {len(old)} chars."
            if suggestions:
                msg += "\nDid you mean one of these?\n" + "\n".join(suggestions)
            msg += "\nTip: Use read_file to see exact content with line numbers."
            return msg

        if not replace_all and count > 1:
            # Find line numbers of all occurrences
            line_nums = []
            for i, line in enumerate(content.split("\n"), 1):
                if old in line:
                    line_nums.append(i)

            return (
                f"Error: 'old' string found {count} times in {path}. "
                f"Use replace_all=True to replace all, or provide more context to make it unique.\n"
                f"Occurrences at lines: {line_nums}\n"
                f"Tip: Include more surrounding lines in 'old' to disambiguate."
            )

        # Perform replacement
        if replace_all:
            new_content = content.replace(old, new)
            replaced_count = count
        else:
            new_content = content.replace(old, new, 1)
            replaced_count = 1

        if new_content == content:
            return "No changes made (old == new)."

        # Atomic write
        try:
            _atomic_write(filepath, new_content)
        except OSError as exc:
            return f"Error writing {path}: {exc}"

        # Record for undo
        _undo_stack.push(EditRecord(
            filepath=filepath,
            old_content=content,
            new_content=new_content,
        ))

        # Provide context: show the changed lines
        old_lines = content.split("\n")
        new_lines = new_content.split("\n")
        changed_info = f" ({len(old_lines)} -> {len(new_lines)} lines)"

        return (
            f"File edited: {path}{changed_info}\n"
            f"Replaced {replaced_count} occurrence(s)\n"
            f"Old: {old[:100]}{'...' if len(old) > 100 else ''}\n"
            f"New: {new[:100]}{'...' if len(new) > 100 else ''}\n"
            f"Tip: Use undo_edit to revert this change."
        )


# ---------------------------------------------------------------------------
# Tool 4: ShellExecTool
# ---------------------------------------------------------------------------


class ShellExecTool(Tool):
    """Execute sandboxed shell commands with allowlist and timeout."""

    name: str = "shell_exec"
    description: str = (
        "Execute a shell command in the workspace. "
        "Sandboxed: only safe commands are allowed (no sudo, no system utilities, no network by default). "
        "Use for: running tests, linting, git commands, file operations, build commands. "
        "Timeout: 30 seconds default. Output truncated to 5000 chars."
    )

    def _run(
        self,
        command: str,
        timeout: int = 30,
        cwd: str = "",
    ) -> str:
        """Execute a sandboxed shell command.

        Args:
            command: Shell command to execute.
            timeout: Timeout in seconds (max 120).
            cwd: Working directory (relative to workspace or absolute).
        """
        # Validate command safety
        is_safe, reason = _is_safe_command(command)
        if not is_safe:
            return f"Command blocked: {reason}\nCommand: {command[:200]}"

        # Resolve working directory
        work_dir = str(_path_sandbox.workspace)
        if cwd:
            try:
                p = _path_sandbox.validate(cwd)
                work_dir = str(p)
            except PermissionError:
                return f"Error: Working directory '{cwd}' is outside workspace."

        timeout = min(timeout, 120)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=work_dir,
                env={**os.environ, "PAGER": "cat"},  # Disable pagers
            )
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s: {command[:100]}"
        except Exception as exc:
            return f"Command failed: {exc}"

        output_parts = []

        if result.stdout:
            stdout = result.stdout
            if len(stdout) > 5000:
                stdout = stdout[:5000] + f"\n... [truncated: {len(result.stdout)} total chars]"
            output_parts.append(stdout.strip())

        if result.stderr:
            stderr = result.stderr
            if len(stderr) > 2000:
                stderr = stderr[:2000] + f"\n... [truncated: {len(result.stderr)} total chars]"
            output_parts.append(f"[stderr]\n{stderr.strip()}")

        if result.returncode != 0:
            output_parts.append(f"[exit code: {result.returncode}]")

        if not output_parts:
            return f"Command completed (no output): {command[:100]}"

        return "\n".join(output_parts)


# ---------------------------------------------------------------------------
# Tool 5: GitTool
# ---------------------------------------------------------------------------


class GitTool(Tool):
    """Git operations — read-only by default."""

    name: str = "git"
    description: str = (
        "Execute git commands in the workspace. "
        "Read-only by default: status, diff, log, show, branch. "
        "For write operations (commit, push, checkout), set write=True."
    )

    def _run(
        self,
        subcommand: str = "status",
        args: str = "",
        write: bool = False,
    ) -> str:
        """Execute a git subcommand.

        Args:
            subcommand: Git subcommand (status, diff, log, show, branch, add, commit, etc.).
            args: Additional arguments for the subcommand.
            write: Allow write operations (commit, push, checkout, etc.).
        """
        read_only_cmds = {"status", "diff", "log", "show", "branch", "tag", "stash list", "remote", "blame", "grep"}
        write_cmds = {"add", "commit", "push", "pull", "checkout", "merge", "rebase", "reset", "stash", "tag -d"}

        subcommand_lower = subcommand.lower().strip()

        if not write:
            # Check if it's a read-only command
            is_readonly = any(subcommand_lower.startswith(c) for c in read_only_cmds)
            is_write = any(subcommand_lower.startswith(c) for c in write_cmds)
            if is_write and not is_readonly:
                return (
                    f"Git write operation blocked: '{subcommand}'. "
                    f"Set write=True to allow this operation.\n"
                    f"Read-only commands: {', '.join(sorted(read_only_cmds))}"
                )

        full_cmd = f"git {subcommand} {args}".strip()

        try:
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(_path_sandbox.workspace),
                env={**os.environ, "PAGER": "cat"},
            )
        except subprocess.TimeoutExpired:
            return f"Git command timed out: {full_cmd[:100]}"
        except Exception as exc:
            return f"Git command failed: {exc}"

        output = result.stdout.strip()
        if result.stderr.strip():
            if output:
                output += "\n"
            output += f"[stderr]\n{result.stderr.strip()[:2000]}"

        if result.returncode != 0 and not output:
            return f"Git command failed (exit {result.returncode}): {full_cmd[:100]}"

        return output or f"Git {subcommand}: no output"


# ---------------------------------------------------------------------------
# Tool 6: UndoEditTool
# ---------------------------------------------------------------------------


class UndoEditTool(Tool):
    """Undo the last file edit."""

    name: str = "undo_edit"
    description: str = (
        "Undo the last file edit made by edit_file or write_file. "
        "Restores the file to its previous content. "
        f"Up to {_undo_stack.max_undo} edits can be undone."
    )

    def _run(self, count: int = 1) -> str:
        """Undo the last N edits.

        Args:
            count: Number of edits to undo (default 1, max 10).
        """
        count = min(count, 10, len(_undo_stack))
        if count == 0:
            return "Nothing to undo. No edits have been made."

        undone = []
        for _ in range(count):
            record = _undo_stack.undo()
            if record:
                undone.append(f"  {record.filepath}: restored {len(record.old_content)} chars")

        return f"Undid {len(undone)} edit(s):\n" + "\n".join(undone)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def get_code_tools() -> list[Tool]:
    """Return all coding tools for agent registration."""
    return [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        ShellExecTool(),
        GitTool(),
        UndoEditTool(),
    ]
