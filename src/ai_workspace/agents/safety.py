"""
Agent Safety — Sandbox, command validation, deception detection.

Three layers:
  1. SafetySandbox — validates and confines tool execution
  2. DeceptionDetector — flags fabricated outputs
  3. SafetyValidator — unified safety check pipeline

Refs:
- SPEC_SAFETY.md
- Operational Safety Failures (arXiv 2605.30777, 2026)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_workspace.core.result import ErrorCode, Failure, Result, Success

logger = logging.getLogger("aiw.safety")


# ═══════════════════════════════════════════════════════════
# Safety error
# ═══════════════════════════════════════════════════════════

@dataclass
class SafetyError:
    """A safety violation detected during execution.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable description.
        detail: Additional context (e.g., the full command).
        recoverable: Whether the agent can retry with a safer approach.
        suggestion: Recommended fix for the agent.
    """
    code: str
    message: str
    detail: str = ""
    recoverable: bool = False
    suggestion: str = ""


# ═══════════════════════════════════════════════════════════
# Sandbox config
# ═══════════════════════════════════════════════════════════

@dataclass
class SandboxConfig:
    """Configuration for the safety sandbox.

    Attributes:
        workspace_root: Only paths under this directory can be written to.
        allowed_commands: Shell commands explicitly permitted.
        blocked_commands: Shell commands always blocked (regardless of path).
        max_output_bytes: Maximum bytes from any single command.
        max_runtime_seconds: Timeout per command.
    """
    workspace_root: str = "."
    allowed_commands: set[str] = field(default_factory=lambda: {
        # File operations
        "ls", "cat", "head", "tail", "wc", "find", "grep", "rg",
        "file", "stat", "tree",
        # Git
        "git",
        # Python / tools
        "python", "python3", "pip", "uv",
        "pytest", "ruff", "mypy", "black", "isort",
        "maturin", "cargo", "go", "npm", "npx",
        # System info
        "echo", "date", "which", "hostname", "uname",
        "ps", "env", "printenv",
        # Network reads only
        "curl", "wget",
        # Nix
        "nix", "nix-shell", "nix-env",
    })
    blocked_commands: set[str] = field(default_factory=lambda: {
        # Destructive
        "rm", "rmdir", "mv",  # mv can be destructive (overwrite)
        "dd", "mkfs", "fdisk",
        # Privilege escalation
        "sudo", "su", "doas",
        # System modification
        "chmod", "chown", "chgrp",
        "systemctl", "service",
        # Network servers / risky
        "nc", "ncat", "telnet",
        "ssh", "scp",
        # Fork bombs / resource exhaustion
        ":()", "yes",
    })
    max_output_bytes: int = 10_000_000  # 10MB
    max_runtime_seconds: int = 30

    # Patterns that are blocked even in allowed commands
    _dangerous_patterns: list[str] = field(default_factory=lambda: [
        r"rm\s+-rf?\s+[/~]",    # rm -rf / or ~
        r">\s*/dev/",           # overwrite device files
        r"mkfs\.",              # filesystem creation
        r"dd\s+if=",            # disk duplication
        r"fork\s+bomb",         # fork bombs
        r"eval\s",              # eval injection
        r"\$\(",                # command substitution (potential injection)
        r"`[^`]+`",            # backtick substitution
    ])


# ═══════════════════════════════════════════════════════════
# Safety Sandbox
# ═══════════════════════════════════════════════════════════

class SafetySandbox:
    """Isolates execution of dangerous commands.

    Usage:
        sandbox = SafetySandbox()
        result = sandbox.validate_command("ls -la src/")
        if result.is_success():
            # safe to execute
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()

    def validate_command(self, command: str) -> Result[str, SafetyError]:
        """Validate a shell command before execution.

        Checks:
          1. Base command is not in blocked list.
          2. Base command is in allowed list (or explicitly permitted).
          3. Paths accessed are within the workspace.
          4. No dangerous patterns detected.

        Returns:
            Success with the sanitized command, or Failure with details.
        """
        stripped = command.strip()
        if not stripped:
            return Failure(SafetyError(
                "EMPTY_COMMAND",
                "Empty command provided",
            ))

        # Split into base command and args
        parts = stripped.split()
        base_cmd = parts[0]

        # Strip path prefix for comparison (e.g., /usr/bin/git → git)
        base_name = os.path.basename(base_cmd)

        # 1. Blocklist check
        if base_name in self.config.blocked_commands:
            return Failure(SafetyError(
                "BLOCKED_COMMAND",
                f"Command '{base_name}' is blocked for safety",
                detail=f"Full command: {stripped}",
                recoverable=False,
                suggestion=(
                    f"'{base_name}' can cause data loss or system damage. "
                    "Use a safer alternative or request explicit permission."
                ),
            ))

        # 1a. Check for destructive flags on allowed commands
        result = self._check_dangerous_flags(base_name, parts)
        if isinstance(result, Failure):
            return result

        # 2. Dangerous pattern check (regex)
        result = self._check_dangerous_patterns(stripped)
        if isinstance(result, Failure):
            return result

        # 3. Allowlist + path validation
        if base_name in self.config.allowed_commands:
            return self._validate_paths(stripped, parts)

        # 4. Check if the base command has a full path in allowed set
        for allowed in self.config.allowed_commands:
            if base_cmd == allowed or base_name == os.path.basename(allowed):
                return self._validate_paths(stripped, parts)

        # 5. Unknown command — may be safe, but flag it
        return Failure(SafetyError(
            "UNKNOWN_COMMAND",
            f"Command '{base_name}' is not in the allowlist",
            detail=f"Full command: {stripped}",
            recoverable=True,
            suggestion=(
                f"Add '{base_name}' to allowed_commands if it's safe, "
                "or use a permitted alternative."
            ),
        ))

    def _check_dangerous_flags(
        self, base_cmd: str, parts: list[str],
    ) -> Result[str, SafetyError]:
        """Check for destructive flags on otherwise-allowed commands."""
        # git push --force to main/master is dangerous
        if base_cmd == "git":
            has_force = "--force" in parts or "-f" in parts
            has_main = "main" in parts or "master" in parts
            has_push = "push" in parts
            if has_push and has_force and has_main:
                return Failure(SafetyError(
                    "DESTRUCTIVE_FLAG",
                    "git push --force to main/master is blocked",
                    detail=" ".join(parts),
                    recoverable=True,
                    suggestion="Use --force-with-lease or push to a feature branch.",
                ))

        # pip uninstall
        if base_cmd in ("pip", "pip3", "uv") and any(
            p in parts for p in ("uninstall", "remove")
        ):
            return Failure(SafetyError(
                "DESTRUCTIVE_SUBCOMMAND",
                f"{base_cmd} uninstall/remove is blocked",
                detail=" ".join(parts),
                recoverable=True,
                suggestion="Uninstall packages manually or use --dry-run first.",
            ))

        return Success("ok")

    def _check_dangerous_patterns(
        self, command: str,
    ) -> Result[str, SafetyError]:
        """Check for dangerous regex patterns in the command."""
        for pattern in self.config._dangerous_patterns:
            if re.search(pattern, command):
                return Failure(SafetyError(
                    "DANGEROUS_PATTERN",
                    f"Command matches dangerous pattern: {pattern}",
                    detail=command,
                    recoverable=False,
                    suggestion="Rewrite without destructive patterns.",
                ))
        return Success("ok")

    def _validate_paths(
        self, command: str, parts: list[str],
    ) -> Result[str, SafetyError]:
        """Ensure all file paths in the command are within the workspace."""
        workspace = Path(self.config.workspace_root).resolve()

        for part in parts:
            # Skip flags, operators, pipes
            if part.startswith("-") or part in ("|", "&&", "||", ";", ">"):
                continue
            # Skip URLs
            if part.startswith(("http://", "https://")):
                continue
            # Check if part looks like a path
            if "/" in part or "\\" in part or "." in part:
                try:
                    resolved = Path(part).resolve()
                    if not str(resolved).startswith(str(workspace)):
                        # Allow read-only access to system paths (cat, ls, etc.)
                        read_only_cmds = {
                            "ls", "cat", "head", "tail", "file", "stat",
                            "wc", "find", "grep", "rg", "tree",
                        }
                        base = parts[0] if parts else ""
                        if os.path.basename(base) in read_only_cmds:
                            # Read-only — allow but warn
                            logger.debug(
                                "Read-only access outside workspace: %s → %s",
                                part, resolved,
                            )
                            continue
                        return Failure(SafetyError(
                            "PATH_TRAVERSAL",
                            f"Path '{part}' is outside the workspace",
                            detail=(
                                f"Resolved: {resolved}\n"
                                f"Workspace: {workspace}"
                            ),
                            recoverable=True,
                            suggestion=(
                                "Only access files within the workspace. "
                                "Use relative paths."
                            ),
                        ))
                except (OSError, ValueError):
                    pass  # Not a valid path, skip

        return Success(command)

    def is_write_safe(self, path: str | Path) -> Result[str, SafetyError]:
        """Check if writing to a path is safe."""
        target = Path(path).resolve()
        workspace = Path(self.config.workspace_root).resolve()

        if not str(target).startswith(str(workspace)):
            return Failure(SafetyError(
                "WRITE_OUTSIDE_WORKSPACE",
                f"Write to '{target}' is outside workspace '{workspace}'",
                recoverable=False,
                suggestion="Only write files within the project directory.",
            ))

        # Block writes to hidden/system files
        dangerous_targets = [
            ".git/config", ".git/HEAD", ".env", ".envrc",
            "flake.nix", "flake.lock",
        ]
        for dangerous in dangerous_targets:
            if str(target).endswith(dangerous):
                return Failure(SafetyError(
                    "PROTECTED_FILE",
                    f"Write to protected file '{target}' blocked",
                    detail=f"File matches protected pattern: {dangerous}",
                    recoverable=True,
                    suggestion="Modify this file manually or request explicit permission.",
                ))

        return Success(str(target))


# ═══════════════════════════════════════════════════════════
# Deception detection
# ═══════════════════════════════════════════════════════════

class DeceptionDetector:
    """Detects potential deception in agent outputs.

    Checks for:
    - Fabricated success messages (reporting success when there's evidence of failure)
    - Inconsistency between tool results and agent claims
    - Placeholder/template text in final output
    """

    # Phrases that suggest the agent fabricated a result
    _FABRICATION_MARKERS: list[str] = [
        "the file has been updated successfully",
        "the changes have been applied",
        "the test passes",
        "the build succeeds",
        "everything works correctly",
    ]

    # Evidence that contradicts success claims
    _CONTRADICTION_MARKERS: list[str] = [
        "error:", "traceback", "exception:", "failed:",
        "cannot ", "unable to", "permission denied",
        "command not found", "no such file",
    ]

    def check_claim_against_evidence(
        self,
        claim: str,
        tool_outputs: list[str],
    ) -> list[SafetyError]:
        """Check if the agent's claim matches the tool evidence.

        Args:
            claim: The agent's final statement/claim.
            tool_outputs: Raw outputs from tools the agent ran.

        Returns:
            List of deception warnings (empty if clean).
        """
        warnings: list[SafetyError] = []

        claim_lower = claim.lower()

        # Check: does claim assert success while tool outputs show errors?
        has_success_claim = any(
            m in claim_lower for m in self._FABRICATION_MARKERS
        )
        if has_success_claim:
            for output in tool_outputs:
                output_lower = output.lower()
                for marker in self._CONTRADICTION_MARKERS:
                    if marker in output_lower:
                        warnings.append(SafetyError(
                            "DECEPTION_DETECTED",
                            (
                                "Agent claims success but tool output "
                                "shows errors"
                            ),
                            detail=(
                                f"Claim: {claim[:200]}\n"
                                f"Evidence: "
                                f"{output[:200]}"
                            ),
                            recoverable=True,
                            suggestion=(
                                "Re-run the failing step and report "
                                "the actual result."
                            ),
                        ))
                        return warnings  # one is enough

        # Check: placeholder text
        placeholder_markers = [
            "todo", "fixme", "implement later", "your code here",
            "...", "insert solution",
        ]
        for marker in placeholder_markers:
            if marker in claim_lower:
                warnings.append(SafetyError(
                    "PLACEHOLDER_OUTPUT",
                    f"Agent output contains placeholder '{marker}'",
                    detail=claim[:200],
                    recoverable=True,
                    suggestion="Complete the implementation instead of leaving placeholders.",
                ))

        return warnings


# ═══════════════════════════════════════════════════════════
# Safety Validator (unified pipeline)
# ═══════════════════════════════════════════════════════════

class SafetyValidator:
    """Runs all safety checks in sequence.

    Usage:
        validator = SafetyValidator()
        
        # Before shell execution
        result = validator.validate_command("rm -rf /")
        if isinstance(result, Failure):
            print(f"Blocked: {result.error.message}")
        
        # Before file write
        result = validator.validate_write("src/main.py")
        if isinstance(result, Failure):
            print(f"Blocked: {result.error.message}")
        
        # After agent finishes
        warnings = validator.check_deception(agent_claim, tool_outputs)
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.sandbox = SafetySandbox(config)
        self.deception = DeceptionDetector()

    def validate_command(self, command: str) -> Result[str, SafetyError]:
        """Full command validation pipeline."""
        return self.sandbox.validate_command(command)

    def validate_write(self, path: str | Path) -> Result[str, SafetyError]:
        """Check if writing to a path is safe."""
        return self.sandbox.is_write_safe(path)

    def check_deception(
        self,
        claim: str,
        tool_outputs: list[str],
    ) -> list[SafetyError]:
        """Run deception detection on agent output."""
        return self.deception.check_claim_against_evidence(
            claim, tool_outputs,
        )
