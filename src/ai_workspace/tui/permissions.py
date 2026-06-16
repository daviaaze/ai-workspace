"""
Permission Gate — intercepts tool calls and requires human approval.

Architecture:
  AgentWorker (thread)          TUI (main thread)
  ┌─────────────────┐           ┌─────────────────┐
  │ tool about to    │           │                 │
  │ execute          │──perm_q──▶│ PermissionModal │
  │                  │           │ shows diff      │
  │ wait for verdict │◀─resp_q──│ user: a/A/d     │
  │ execute or skip  │           │                 │
  └─────────────────┘           └─────────────────┘
"""

from __future__ import annotations

import difflib
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


class PermissionVerdict(Enum):
    ALLOW = auto()
    ALLOW_ALWAYS = auto()
    DENY = auto()


@dataclass
class PermissionRequest:
    """A request for human approval before a tool executes."""
    request_id: str
    agent_name: str
    tool_name: str
    task: str
    description: str  # What will be done
    preview: str       # Diff, command, or content preview
    input_args: dict[str, Any] = field(default_factory=dict)
    
    # Thread synchronization
    _event: threading.Event = field(default_factory=threading.Event)
    _verdict: PermissionVerdict | None = None
    
    def wait(self, timeout: float = 120.0) -> PermissionVerdict:
        """Wait for human verdict. Returns DENY on timeout."""
        if self._event.wait(timeout):
            return self._verdict or PermissionVerdict.DENY
        return PermissionVerdict.DENY
    
    def resolve(self, verdict: PermissionVerdict) -> None:
        """Called by TUI when human decides."""
        self._verdict = verdict
        self._event.set()


class PermissionGate:
    """Manages permission requests for an agent worker.
    
    Dangerous tools (edit_file, write_file, shell_exec) are intercepted.
    The gate either auto-approves (safe commands) or requests human approval
    via the permission_queue.
    """
    
    # Tools that always require permission
    DANGEROUS_TOOLS = {"write_file", "edit_file"}
    
    # Shell commands that require permission
    DANGEROUS_SHELL_PATTERNS = [
        "rm ", "rmdir", "mv ", "cp -r", "chmod", "chown",
        "git push", "git commit", "git reset", "git rebase",
        "pip install", "npm install -g", "sudo",
        "> /dev/", "dd ", "mkfs", "format",
    ]
    
    # Safe shell commands (auto-approve)
    SAFE_SHELL_PATTERNS = [
        "ls", "cat", "head", "tail", "wc", "find", "grep",
        "echo", "pwd", "which", "whoami", "date",
        "git status", "git diff", "git log", "git branch",
        "python -m pytest", "python -c",
        "cargo check", "cargo test", "go build", "go test",
        "nix build", "nix flake check",
    ]
    
    def __init__(self, agent_name: str = "agent"):
        self.agent_name = agent_name
        self._always_allowed: set[str] = set()  # Tools always allowed
    
    def check_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        task: str = "",
    ) -> PermissionRequest | None:
        """Check if a tool call needs permission.
        
        Returns:
            PermissionRequest if approval needed, None if auto-approved.
        """
        # Already always-allowed
        if tool_name in self._always_allowed:
            return None
        
        # Not a dangerous tool
        if tool_name not in self.DANGEROUS_TOOLS and tool_name != "shell_exec":
            return None
        
        # Shell: check command patterns
        if tool_name == "shell_exec":
            command = tool_args.get("command", "")
            if self._is_safe_shell(command):
                return None
            description = f"Execute: {command[:100]}"
            preview = command[:500]
        elif tool_name == "write_file":
            path = tool_args.get("path", "?")
            content = tool_args.get("content", "")
            description = f"Write file: {path}"
            preview = self._format_write_preview(path, content)
        elif tool_name == "edit_file":
            path = tool_args.get("path", "?")
            old_text = tool_args.get("old_text", "")
            new_text = tool_args.get("new_text", "")
            description = f"Edit file: {path}"
            preview = self._format_edit_preview(path, old_text, new_text)
            if not preview:  # Empty diff → auto-approve
                return None
        else:
            return None
        
        import uuid
        return PermissionRequest(
            request_id=str(uuid.uuid4())[:12],
            agent_name=self.agent_name,
            tool_name=tool_name,
            task=task,
            description=description,
            preview=preview,
            input_args=tool_args,
        )
    
    def check_and_wait(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        task: str = "",
        timeout: float = 120.0,
    ) -> PermissionVerdict:
        """Check if permission needed, wait for verdict if so.
        
        Returns ALLOW if auto-approved or human approved.
        Returns DENY if human denied or timed out.
        """
        request = self.check_tool(tool_name, tool_args, task)
        if request is None:
            return PermissionVerdict.ALLOW
        
        # Wait for human verdict
        verdict = request.wait(timeout)
        
        if verdict == PermissionVerdict.ALLOW_ALWAYS:
            self._always_allowed.add(tool_name)
        
        return verdict
    
    def _is_safe_shell(self, command: str) -> bool:
        """Check if a shell command is safe to auto-approve."""
        cmd_lower = command.strip().lower()
        for safe in self.SAFE_SHELL_PATTERNS:
            if cmd_lower.startswith(safe):
                return True
        return False
    
    def _format_write_preview(self, path: str, content: str) -> str:
        """Format a write preview showing the file diff."""
        abspath = Path(path)
        if abspath.exists():
            try:
                old_content = abspath.read_text()[:10_000]
                diff = difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=str(abspath),
                    tofile=str(abspath),
                    lineterm="",
                )
                return "\n".join(list(diff)[:100])
            except Exception:
                pass
        return content[:2000]
    
    def _format_edit_preview(self, path: str, old_text: str, new_text: str) -> str:
        """Format an edit preview showing the diff."""
        if not old_text and not new_text:
            return ""
        
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=path, tofile=path,
            lineterm="",
        )
        return "\n".join(list(diff)[:100])
