"""
Tests for Agent Safety — Sandbox, validation, deception detection.

Refs: SPEC_SAFETY.md
"""

from __future__ import annotations

import pytest

from ai_workspace.agents.safety import (
    DeceptionDetector,
    SafetyError,
    SafetySandbox,
    SafetyValidator,
    SandboxConfig,
)
from ai_workspace.core.result import Failure, Success


class TestSafetyError:
    """SafetyError dataclass."""

    def test_minimal(self):
        """Minimal error has required fields."""
        e = SafetyError(code="TEST", message="test error")
        assert e.code == "TEST"
        assert e.message == "test error"
        assert e.recoverable is False

    def test_with_suggestion(self):
        """Error can include recovery suggestion."""
        e = SafetyError(
            code="BLOCKED", message="blocked",
            recoverable=True, suggestion="Use alternative",
        )
        assert e.recoverable is True
        assert "alternative" in e.suggestion


class TestSandboxConfig:
    """SandboxConfig defaults."""

    def test_default_blocklist(self):
        """Blocked commands include rm, sudo, etc."""
        cfg = SandboxConfig()
        assert "rm" in cfg.blocked_commands
        assert "sudo" in cfg.blocked_commands
        assert "chmod" in cfg.blocked_commands

    def test_default_allowlist(self):
        """Allowed commands include ls, git, python, etc."""
        cfg = SandboxConfig()
        assert "ls" in cfg.allowed_commands
        assert "git" in cfg.allowed_commands
        assert "python" in cfg.allowed_commands


class TestSafetySandbox:
    """SafetySandbox command validation."""

    def test_allows_safe_command(self):
        """Simple ls within workspace is allowed."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("ls -la src/")
        assert isinstance(result, Success)

    def test_blocks_rm(self):
        """rm is in blocklist."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("rm -rf file.txt")
        assert isinstance(result, Failure)
        assert result.error.code == "BLOCKED_COMMAND"

    def test_blocks_sudo(self):
        """sudo is in blocklist."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("sudo ls")
        assert isinstance(result, Failure)
        assert result.error.code == "BLOCKED_COMMAND"

    def test_empty_command(self):
        """Empty command is rejected."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("")
        assert isinstance(result, Failure)
        assert result.error.code == "EMPTY_COMMAND"

    def test_whitespace_command(self):
        """Whitespace-only command is rejected."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("   ")
        assert isinstance(result, Failure)

    def test_allows_git_status(self):
        """git status is safe."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("git status")
        assert isinstance(result, Success)

    def test_blocks_git_push_force_main(self):
        """git push --force to main is blocked."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("git push --force origin main")
        assert isinstance(result, Failure)
        assert "DESTRUCTIVE" in result.error.code

    def test_allows_git_push_force_feature(self):
        """git push --force to feature branch is allowed."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("git push --force origin feature/x")
        assert isinstance(result, Success)

    def test_blocks_pip_uninstall(self):
        """pip uninstall is blocked."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("pip uninstall requests")
        assert isinstance(result, Failure)
        assert "DESTRUCTIVE" in result.error.code

    def test_blocks_dangerous_pattern(self):
        """rm -rf / pattern is blocked."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("find . -exec rm -rf ~/ {} \\;")
        # rm is already blocked, but the pattern check would also catch it
        assert isinstance(result, Failure)

    def test_unknown_command_recoverable(self):
        """Unknown commands are flagged but recoverable."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("unknown_tool --help")
        assert isinstance(result, Failure)
        assert result.error.recoverable is True

    def test_urls_are_skipped_in_path_check(self):
        """curl URL is not treated as path traversal."""
        sandbox = SafetySandbox()
        result = sandbox.validate_command("curl https://example.com")
        assert isinstance(result, Success)

    def test_write_safe_inside_workspace(self):
        """Writing inside workspace is safe."""
        sandbox = SafetySandbox(config=SandboxConfig(workspace_root="/tmp"))
        result = sandbox.is_write_safe("/tmp/test.py")
        assert isinstance(result, Success)

    def test_write_unsafe_outside_workspace(self):
        """Writing outside workspace is blocked."""
        sandbox = SafetySandbox(config=SandboxConfig(workspace_root="/tmp"))
        result = sandbox.is_write_safe("/etc/passwd")
        assert isinstance(result, Failure)
        assert "OUTSIDE" in result.error.code

    def test_write_protected_file_blocked(self):
        """Writing to .env is blocked."""
        sandbox = SafetySandbox(config=SandboxConfig(workspace_root="/home/proj"))
        result = sandbox.is_write_safe("/home/proj/.env")
        assert isinstance(result, Failure)
        assert "PROTECTED" in result.error.code


class TestDeceptionDetector:
    """DeceptionDetector checks agent outputs."""

    def test_no_deception_clean_output(self):
        """Clean output with no contradictions = no warnings."""
        detector = DeceptionDetector()
        warnings = detector.check_claim_against_evidence(
            "The task is complete.",
            ["file saved", "tests: 5 passed"],
        )
        assert len(warnings) == 0

    def test_detects_success_claim_with_error_evidence(self):
        """Claiming success when output shows errors = deception."""
        detector = DeceptionDetector()
        warnings = detector.check_claim_against_evidence(
            "The test passes successfully.",
            ["FAILED: test_auth.py::test_login - AssertionError"],
        )
        assert len(warnings) >= 1
        assert warnings[0].code == "DECEPTION_DETECTED"

    def test_detects_placeholder_text(self):
        """TODO/FIXME placeholders flagged."""
        detector = DeceptionDetector()
        warnings = detector.check_claim_against_evidence(
            "Here is the solution: TODO implement later",
            ["output ok"],
        )
        assert len(warnings) >= 1
        assert "PLACEHOLDER" in warnings[0].code

    def test_no_false_positive(self):
        """Normal success claims without error evidence pass."""
        detector = DeceptionDetector()
        warnings = detector.check_claim_against_evidence(
            "The changes have been applied successfully",
            ["pytest: 10 passed in 2.34s"],
        )
        assert len(warnings) == 0


class TestSafetyValidator:
    """SafetyValidator runs the full pipeline."""

    def test_validate_command_delegates(self):
        """Validator delegates to sandbox for commands."""
        validator = SafetyValidator()
        result = validator.validate_command("ls")
        assert isinstance(result, Success)

    def test_validate_write_delegates(self):
        """Validator delegates to sandbox for writes."""
        validator = SafetyValidator(
            config=SandboxConfig(workspace_root="/tmp"),
        )
        result = validator.validate_write("/tmp/ok.py")
        assert isinstance(result, Success)

    def test_check_deception_delegates(self):
        """Validator delegates to deception detector."""
        validator = SafetyValidator()
        warnings = validator.check_deception(
            "TODO: fix this",
            ["no errors"],
        )
        assert len(warnings) >= 1
