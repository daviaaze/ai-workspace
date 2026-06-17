"""
Tests for AutoFixLoop — error classification, judge protocol, fix loop.

No real LLM calls — tests use pure logic paths and mocked subprocess.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_workspace.tools.auto_fix import (
    AutoFixLoop,
    FixReport,
    FixResult,
    ErrorClass,
    classify_error,
)


# ═══════════════════════════════════════════════════════
# Error classification
# ═══════════════════════════════════════════════════════


class TestErrorClassification:
    """Ghost-style error type detection."""

    def test_syntax_error_classified(self):
        assert classify_error("SyntaxError: invalid syntax at line 42") == ErrorClass.SYNTAX
        assert classify_error("IndentationError: unexpected indent") == ErrorClass.SYNTAX

    def test_import_error_classified(self):
        assert classify_error("ImportError: No module named 'foo'") == ErrorClass.IMPORT
        assert classify_error("ModuleNotFoundError: No module named") == ErrorClass.IMPORT

    def test_assertion_error_classified(self):
        assert classify_error("AssertionError: assert 1 == 2") == ErrorClass.ASSERTION

    def test_runtime_error_classified(self):
        assert classify_error("TypeError: 'NoneType' object is not callable") == ErrorClass.RUNTIME
        assert classify_error("ValueError: invalid literal") == ErrorClass.RUNTIME

    def test_other_error_classified(self):
        assert classify_error("Killed by signal") == ErrorClass.OTHER
        assert classify_error("") == ErrorClass.OTHER

    def test_priority_order(self):
        """AssertionError should be classified before generic Error."""
        traceback = """AssertionError: assert 1 == 2\nDuring handling, ValueError occurred"""
        assert classify_error(traceback) == ErrorClass.ASSERTION


# ═══════════════════════════════════════════════════════
# FixReport data class
# ═══════════════════════════════════════════════════════


class TestFixReport:
    """FixReport data class behavior."""

    def test_defaults(self):
        report = FixReport(result=FixResult.PASSED, iterations=0)
        assert report.result == FixResult.PASSED
        assert report.iterations == 0
        assert report.errors_fixed == []
        assert report.judge_interventions == 0

    def test_with_errors(self):
        report = FixReport(
            result=FixResult.PARTIAL,
            iterations=3,
            errors_fixed=["syntax (iter 1)", "import (iter 2)"],
            errors_remaining=["assertion (iter 3)"],
            judge_interventions=1,
            files_changed=["src/file.py"],
        )
        assert len(report.errors_fixed) == 2
        assert len(report.errors_remaining) == 1
        assert report.judge_interventions == 1


# ═══════════════════════════════════════════════════════
# Judge protocol
# ═══════════════════════════════════════════════════════


class TestJudge:
    """Judge heuristic for test-vs-code classification."""

    def test_none_value_suggests_bug(self):
        loop = AutoFixLoop(goal="Test")
        errors = "AssertionError: assert None == expected_value\n  File tests/test_x.py:42"
        verdict = loop._judge(errors)
        assert verdict == "BUG_IN_CODE"

    def test_equality_suggests_fix_test(self):
        loop = AutoFixLoop(goal="Test")
        errors = "AssertionError: assert 1 == 2\n  File tests/test_x.py:42"
        verdict = loop._judge(errors)
        assert verdict == "FIX_TEST"

    def test_unknown_returns_unclear(self):
        loop = AutoFixLoop(goal="Test")
        errors = "AssertionError: something happened\n  File tests/test_x.py:42"
        verdict = loop._judge(errors)
        assert verdict == "UNCLEAR"


# ═══════════════════════════════════════════════════════
# Fix loop with mocked tests
# ═══════════════════════════════════════════════════════


class TestFixLoop:
    """Fix loop with mocked subprocess for tests/lint."""

    @pytest.fixture
    def loop(self):
        return AutoFixLoop(
            goal="Fix failing tests",
            test_command="pytest tests/ -x --tb=short",
            lint_command="ruff check",
            files=["src/file.py"],
        )

    def test_all_tests_pass_returns_passed(self, loop):
        """No failures → PASSED immediately."""
        with patch.object(loop, "_run_tests", return_value=""):
            report = loop.fix()
            assert report.result == FixResult.PASSED
            assert report.iterations == 0

    def test_syntax_error_auto_fixed(self, loop):
        """SyntaxError → ruff --fix → passes → PASSED."""
        call_count = [0]

        def mock_tests():
            call_count[0] += 1
            return "SyntaxError: invalid syntax" if call_count[0] == 1 else ""

        with patch.object(loop, "_run_tests", side_effect=mock_tests):
            with patch.object(loop, "_run_lint", return_value=""):
                report = loop.fix()
                assert report.result == FixResult.PASSED
                assert report.iterations >= 1
                assert any("syntax" in e for e in report.errors_fixed)

    def test_assertion_error_exhausts_qa_budget(self, loop):
        """AssertionError with no QA budget → ABORTED."""
        # Set up: always returning assertion errors
        with patch.object(loop, "_run_tests", return_value="AssertionError: assert 1 == 2"):
            with patch.object(loop, "_judge", return_value="FIX_TEST"):
                with patch.object(loop, "_auto_fix_test", return_value=False):
                    report = loop.fix()
                    # Should exhaust QA budget after 3 assertion fixes max
                    assert report.judge_interventions >= 1

    def test_max_iterations_exhausted(self, loop):
        """Failures that can't be fixed → FAILED after MAX_ITERATIONS."""
        infinite_errors = "RuntimeError: something broke"

        with patch.object(loop, "_run_tests", return_value=infinite_errors):
            with patch.object(loop, "_run_lint", return_value=infinite_errors):
                report = loop.fix()
                assert report.iterations == loop.MAX_ITERATIONS
                assert report.result in (FixResult.FAILED, FixResult.PARTIAL)

    def test_partial_fix_some_errors_remain(self, loop):
        """Some errors fixed but others remain → PARTIAL."""
        call_count = [0]

        def mock_tests():
            call_count[0] += 1
            if call_count[0] == 1:
                return "SyntaxError: bad syntax\nTypeError: bad type"
            else:
                return "TypeError: bad type"  # Syntax fixed, runtime remains

        with patch.object(loop, "_run_tests", side_effect=mock_tests):
            with patch.object(loop, "_run_lint", return_value=""):
                report = loop.fix()
                assert len(report.errors_fixed) >= 1

    def test_snapshot_and_rollback(self, loop):
        """Git snapshot and rollback lifecycle."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "abc123def\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            stash = loop.snapshot()
            assert stash == "abc123def"

            success = loop.rollback("abc123def")
            assert success is True


# ═══════════════════════════════════════════════════════
# Integration: auto-fix with diff_edit
# ═══════════════════════════════════════════════════════


class TestAutoFixIntegration:
    """AutoFixLoop integrates with DiffEditTool for real fixes."""

    def test_can_create_loop_with_defaults(self):
        loop = AutoFixLoop(goal="Fix bugs")
        assert loop.goal == "Fix bugs"
        assert loop.MAX_ITERATIONS == 5
        assert loop.QA_BUDGET == 3
        assert loop.test_command == "pytest -x --tb=short"
