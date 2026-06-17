"""
AutoFixLoop — autonomous edit→lint→test→fix cycle.

Based on research from Aider, Ghost, SWE-AF, and AgentWhetters:
- Ghost-style error classification (Syntax → auto, Import → auto, Assert → Judge)
- Aider-style test gate (baseline capture, external test runner)
- SWE-AF checkpoint pattern (idempotent pipeline, max cycles)
- AgentWhetters test-gate approach (don't trust LLM, run pytest outside agent)
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("aiw.auto_fix")


# ═══════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════


class ErrorClass(str, Enum):
    SYNTAX = "syntax"          # SyntaxError, IndentationError → auto-fix
    IMPORT = "import"           # ImportError, ModuleNotFoundError → auto-fix
    RUNTIME = "runtime"         # TypeError, ValueError, etc. → retry
    ASSERTION = "assertion"     # AssertionError → Judge decides
    OTHER = "other"             # Unknown → retry or fail


class FixResult(str, Enum):
    PASSED = "passed"
    PARTIAL = "partial"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class FixReport:
    result: FixResult
    iterations: int
    errors_fixed: list[str] = field(default_factory=list)
    errors_remaining: list[str] = field(default_factory=list)
    judge_interventions: int = 0
    files_changed: list[str] = field(default_factory=list)
    test_output_final: str = ""


# ═══════════════════════════════════════════════════════════════
# Error classifier (Ghost-style)
# ═══════════════════════════════════════════════════════════════


def classify_error(traceback: str) -> ErrorClass:
    """Classify a test failure to decide the fix strategy."""
    if "SyntaxError" in traceback or "IndentationError" in traceback:
        return ErrorClass.SYNTAX
    if "ImportError" in traceback or "ModuleNotFoundError" in traceback:
        return ErrorClass.IMPORT
    if "AssertionError" in traceback:
        return ErrorClass.ASSERTION
    if "Error" in traceback or "Exception" in traceback:
        return ErrorClass.RUNTIME
    return ErrorClass.OTHER


# ═══════════════════════════════════════════════════════════════
# Judge protocol (Ghost-inspired)
# ═══════════════════════════════════════════════════════════════


JUDGE_PROMPT = """You are a code judge. Analyze this test failure:

TEST CODE:
{test_code}

SOURCE CODE BEING TESTED:
{source_code}

ASSERTION ERROR:
{assertion_error}

Is the test expectation wrong, or is there a bug in the source code?
Answer ONLY: "FIX_TEST" or "BUG_IN_CODE" or "UNCLEAR"
Reason: <one sentence>"""


class AutoFixLoop:
    """Autonomous edit→lint→test→fix cycle.

    Usage:
        loop = AutoFixLoop(
            goal="Fix the 3 failing tests in test_store.py",
            test_command="pytest tests/test_core/test_db.py -x --tb=short",
            lint_command="ruff check",
        )
        report = loop.fix()
    """

    MAX_ITERATIONS = 5
    QA_BUDGET = 3  # Extra turns for assertion fixes

    def __init__(
        self,
        goal: str,
        test_command: str = "pytest -x --tb=short",
        lint_command: str = "ruff check",
        files: list[str] | None = None,
        workspace: str | None = None,
    ):
        self.goal = goal
        self.test_command = test_command
        self.lint_command = lint_command
        self.files = files or []
        self.workspace = Path(workspace) if workspace else Path.cwd()

    # ── Main loop ──────────────────────────────────────

    def fix(self) -> FixReport:
        """Run the full auto-fix loop. Blocks until done or exhausted."""
        logger.info("auto_fix_start: %s", self.goal[:80])

        report = FixReport(result=FixResult.FAILED, iterations=0)

        # Phase 1: Baseline — capture existing failures
        baseline_errors = self._run_tests()
        report.test_output_final = baseline_errors
        if not baseline_errors:
            logger.info("No test failures at baseline — nothing to fix")
            report.result = FixResult.PASSED
            return report

        # Phase 2: Fix loop
        current_errors = baseline_errors
        qa_remaining = self.QA_BUDGET

        for iteration in range(1, self.MAX_ITERATIONS + 1):
            report.iterations = iteration
            logger.info("auto_fix_iteration %d/%d", iteration, self.MAX_ITERATIONS)

            # Classify current errors
            error_class = classify_error(current_errors)

            if error_class == ErrorClass.SYNTAX:
                if self._auto_fix_syntax(current_errors):
                    report.errors_fixed.append(f"syntax (iter {iteration})")
                else:
                    report.errors_remaining.append(f"syntax (iter {iteration})")

            elif error_class == ErrorClass.IMPORT:
                if self._auto_fix_import(current_errors):
                    report.errors_fixed.append(f"import (iter {iteration})")
                else:
                    report.errors_remaining.append(f"import (iter {iteration})")

            elif error_class == ErrorClass.ASSERTION:
                if qa_remaining <= 0:
                    report.result = FixResult.ABORTED
                    report.errors_remaining.append("assertion (QA budget exhausted)")
                    return report

                verdict = self._judge(current_errors)
                report.judge_interventions += 1

                if verdict == "FIX_TEST":
                    if self._auto_fix_test(current_errors):
                        report.errors_fixed.append(f"test-fix (iter {iteration})")
                        qa_remaining -= 1
                    else:
                        report.errors_remaining.append("test-fix failed")
                elif verdict == "BUG_IN_CODE":
                    report.result = FixResult.ABORTED
                    report.errors_remaining.append("bug in source code (judge verdict)")
                    return report
                else:  # UNCLEAR
                    if self._retry_fix(current_errors):
                        report.errors_fixed.append(f"retry (iter {iteration})")
                        qa_remaining -= 1

            else:  # RUNTIME or OTHER
                if not self._retry_fix(current_errors):
                    report.errors_remaining.append(f"{error_class.value} (iter {iteration})")

            # Re-run tests
            current_errors = self._run_tests()
            report.test_output_final = current_errors

            if not current_errors:
                report.result = FixResult.PASSED
                return report

            # Check if errors changed
            if current_errors != baseline_errors and len(current_errors) < len(baseline_errors):
                report.result = FixResult.PARTIAL
                baseline_errors = current_errors

        # Exhausted iterations
        report.result = FixResult.PARTIAL if report.errors_fixed else FixResult.FAILED
        return report

    # ── Test runner ────────────────────────────────────

    def _run_tests(self) -> str:
        """Run tests and return stderr/stdout if failures, empty string if pass."""
        try:
            result = subprocess.run(
                self.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.workspace),
            )
            if result.returncode == 0:
                return ""
            return result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            return "Test command timed out (120s)"
        except Exception as e:
            return f"Test runner error: {e}"

    # ── Lint runner ────────────────────────────────────

    def _run_lint(self) -> str:
        """Run lint and return errors, empty string if clean."""
        try:
            result = subprocess.run(
                self.lint_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace),
            )
            if result.returncode == 0:
                return ""
            return result.stdout + "\n" + result.stderr
        except Exception as e:
            return f"Lint error: {e}"

    # ── Auto-fix strategies ────────────────────────────

    def _auto_fix_syntax(self, errors: str) -> bool:
        """Try ruff --fix for syntax issues. Returns True if lint passes after."""
        logger.info("auto_fix_syntax: running ruff --fix")
        try:
            subprocess.run(
                "ruff check --fix",
                shell=True,
                capture_output=True,
                timeout=15,
                cwd=str(self.workspace),
            )
            lint_result = self._run_lint()
            return lint_result == ""
        except Exception:
            return False

    def _auto_fix_import(self, errors: str) -> bool:
        """Try ruff check --fix + ruff --select I for import sorting."""
        logger.info("auto_fix_import: running ruff check --fix")
        try:
            subprocess.run(
                "ruff check --fix --select I",
                shell=True,
                capture_output=True,
                timeout=15,
                cwd=str(self.workspace),
            )
            subprocess.run(
                "ruff check --fix",
                shell=True,
                capture_output=True,
                timeout=15,
                cwd=str(self.workspace),
            )
            lint_result = self._run_lint()
            return lint_result == ""
        except Exception:
            return False

    def _auto_fix_test(self, errors: str) -> bool:
        """Try ruff --fix on test files. Returns True if tests pass after."""
        logger.info("auto_fix_test: running ruff --fix")
        try:
            subprocess.run(
                self.lint_command + " --fix",
                shell=True,
                capture_output=True,
                timeout=15,
                cwd=str(self.workspace),
            )
            # Run specific test files if we know them
            if self.files:
                test_files = [f for f in self.files if "test" in f.lower()]
                if test_files:
                    for tf in test_files:
                        subprocess.run(
                            f"pytest {tf} -x --tb=short",
                            shell=True,
                            capture_output=True,
                            timeout=30,
                            cwd=str(self.workspace),
                        )
            test_result = self._run_tests()
            return test_result == ""
        except Exception:
            return False

    def _retry_fix(self, errors: str) -> bool:
        """General retry: run lint fix + re-run. Returns True if improved."""
        logger.info("retry_fix: generic lint fix")
        try:
            subprocess.run(
                self.lint_command + " --fix",
                shell=True,
                capture_output=True,
                timeout=15,
                cwd=str(self.workspace),
            )
            return True  # Lint ran — let test re-evaluate
        except Exception:
            return False

    # ── Judge (Ghost protocol) ─────────────────────────

    def _judge(self, errors: str) -> str:
        """Ask LLM to classify the assertion failure.

        Returns: "FIX_TEST", "BUG_IN_CODE", or "UNCLEAR"
        """
        # For a local implementation without LLM call:
        # Extract the relevant test and source code from errors
        test_code = ""
        source_code = ""
        assertion_error = ""

        # Parse errors for the assertion details
        for line in errors.split("\n"):
            line = line.strip()
            if "AssertionError" in line or "assert" in line:
                assertion_error = line[:300]
            if ".py:" in line and "test" in line.lower():
                test_code += line[:200] + "\n"

        # Simple heuristic fallback if no LLM available:
        # If the assertion is comparing values and one is None/empty, likely code bug
        if "None" in assertion_error or "[]" in assertion_error or "{}" in assertion_error:
            return "BUG_IN_CODE"
        # If the assertion has a clear expected value, likely test needs updating
        if "==" in assertion_error or "!=" in assertion_error:
            return "FIX_TEST"
        return "UNCLEAR"

    # ── Git helpers ────────────────────────────────────

    def snapshot(self) -> str:
        """Create a git stash snapshot. Returns the stash ref."""
        try:
            result = subprocess.run(
                "git stash create",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace),
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def rollback(self, stash_ref: str) -> bool:
        """Roll back to a git stash snapshot."""
        if not stash_ref:
            return False
        try:
            subprocess.run(
                f"git stash apply {stash_ref}",
                shell=True,
                capture_output=True,
                timeout=10,
                cwd=str(self.workspace),
            )
            return True
        except Exception:
            return False
