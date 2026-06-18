"""Safe shell command execution with an allowlist for CrewAI agents."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import ClassVar, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def _default_workspace() -> str:
    return os.environ.get("AIW_FS_ROOT", os.getcwd())





READ_ONLY = {
    "ls", "cat", "head", "tail", "wc", "file", "stat", "which", "type",
    "echo", "pwd", "date", "env", "printenv", "true", "false", "test",
    "grep", "find", "rg", "ag", "fd", "tree", "du", "df",
}

DEV = {
    "pytest", "ruff", "mypy", "black", "isort", "flake8", "pylint",
    "python", "python3", "pip", "poetry", "uv", "tox", "nox",
    "node", "npm", "npx", "pnpm", "yarn", "tsc", "eslint", "prettier",
    "cargo", "rustc", "go", "gofmt", "goimports",
    "make", "cmake", "ninja",
}

VERSION_CONTROL = {"git", "gh", "svn", "hg"}

SAFE = READ_ONLY | DEV | VERSION_CONTROL

NEVER_ALLOWED = {
    "rm", "mv", "cp", "dd", "shred", "mkfs", "fdisk",
    "chmod", "chown", "chgrp", "useradd", "userdel", "usermod",
    "systemctl", "service", "init", "reboot", "shutdown", "poweroff",
    "iptables", "ufw", "firewall-cmd", "nft",
    "curl", "wget", "nc", "netcat", "ssh", "scp", "rsync", "ftp", "sftp",
    "sudo", "su", "doas", "pkexec",
    "kill", "pkill", "killall",
    "mount", "umount", "swapon", "swapoff",
    "crontab", "at", "batch",
}





class SafeShellInput(BaseModel):
    command: str = Field(description=f"Shell command to run. First token must be in the allowlist ({', '.join(sorted(SAFE))})")
    timeout: int = Field(default=30, description="Timeout in seconds")
    extra_allowed: list[str] | None = Field(default=None, description="Extra commands to allow for this invocation")


class SafeShellTool(BaseTool):
    """Execute shell commands in a sandboxed allowlist mode.

    The first token of the command must be in the allowlist. The
    tool refuses to run any command whose first token is in
    NEVER_ALLOWED, regardless of context.
    """

    name: str = "shell_exec"
    description: str = (
        "Run a shell command and return its combined output. "
        "Only commands in the safety allowlist are permitted (ls, cat, grep, git, python, pytest, ruff, etc.). "
        "Destructive commands (rm, sudo, shutdown, etc.) are blocked. "
        "Use this to run tests, format code, list files, check git status, etc."
    )
    args_schema: Type[BaseModel] = SafeShellInput

    def _run(
        self,
        command: str,
        timeout: int = 30,
        extra_allowed: list[str] | None = None,
    ) -> str:
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            return f" Parse error: {e}"
        if not tokens:
            return " Empty command"

        head = tokens[0]
        if head in NEVER_ALLOWED:
            return f" Command '{head}' is never allowed"

        allowed = SAFE | set(extra_allowed or [])
        if head not in allowed:
            return (
                f" Command '{head}' is not in the allowlist. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )

        try:
            result = subprocess.run(
                tokens,
                cwd=_default_workspace(),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except FileNotFoundError:
            return f" Command not found: {head}"
        except subprocess.TimeoutExpired:
            return f" Timeout after {timeout}s"
        except Exception as e:
            return f" Execution error: {e}"

        parts = []
        if result.stdout:
            parts.append(result.stdout.rstrip())
        if result.stderr:
            parts.append(f"[stderr]\n{result.stderr.rstrip()}")
        parts.append(f"[exit {result.returncode}]")
        out = "\n".join(parts)
        if len(out) > 30_000:
            return f"{out[:30_000]}\n... [truncated]"
        return out


def get_shell_tool() -> BaseTool:
    """Return the shell tool for agent wiring."""
    return SafeShellTool()


__all__ = [
    "SafeShellTool",
    "get_shell_tool",
    "SAFE",
    "NEVER_ALLOWED",
]
