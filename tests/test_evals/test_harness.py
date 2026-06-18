"""
Tests for Eval Harness — EvalCase, EvalResult, EvalRunner.

Refs: SPEC_EVAL_HARNESS.md
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_workspace.evals import (
    ALL_EVAL_SUITES,
    CODING_EVAL,
    FACT_EVAL,
    REASONING_EVAL,
    EvalCase,
    EvalResult,
    EvalRunner,
    EvalSuiteResult,
)


class TestEvalCase:
    """EvalCase dataclass."""

    def test_minimal(self):
        """Minimal case only needs id and task."""
        case = EvalCase(id="test", task="Do something")
        assert case.id == "test"
        assert case.expected_tools == []
        assert case.expected_keywords == []

    def test_with_expectations(self):
        """Full case with all checks."""
        case = EvalCase(
            id="complex",
            task="Fix the bug",
            expected_tools=["read_file", "edit_file"],
            expected_keywords=["fixed", "works"],
            forbidden_keywords=["maybe", "I think"],
            min_confidence=0.7,
            max_turns=5,
            max_latency_ms=30_000,
        )
        assert "read_file" in case.expected_tools
        assert "fixed" in case.expected_keywords
        assert "maybe" in case.forbidden_keywords


class TestEvalResult:
    """EvalResult dataclass."""

    def test_passed_result(self):
        """Passed result has all checks True."""
        result = EvalResult(
            case_id="test",
            passed=True,
            checks={"tools": True, "keywords": True},
            metrics={"tokens": 100, "latency_ms": 500.0},
        )
        assert result.passed
        assert result.to_dict()["passed"] is True

    def test_failed_result(self):
        """Failed result records which checks failed."""
        result = EvalResult(
            case_id="fail",
            passed=False,
            checks={"tools": False, "keywords": True},
        )
        assert not result.passed

    def test_to_dict_truncates_response(self):
        """to_dict truncates long responses."""
        result = EvalResult(
            case_id="long",
            passed=True,
            response="x" * 1000,
        )
        d = result.to_dict()
        assert len(d["response"]) <= 500


class TestEvalSuiteResult:
    """EvalSuiteResult aggregation."""

    def test_empty_suite(self):
        """Empty suite has zero pass rate."""
        sr = EvalSuiteResult(suite_name="empty")
        assert sr.total_cases == 0
        assert sr.pass_rate == 0.0
        assert sr.passed_count == 0

    def test_all_passed(self):
        """All-passed suite has 100% pass rate."""
        results = [
            EvalResult(case_id="a", passed=True),
            EvalResult(case_id="b", passed=True),
        ]
        sr = EvalSuiteResult(
            suite_name="perfect",
            results=results,
            pass_rate=1.0,
            total_cases=2,
        )
        assert sr.passed_count == 2
        assert "2/2" in sr.summary()

    def test_mixed(self):
        """Mixed results show in summary."""
        results = [
            EvalResult(case_id="a", passed=True),
            EvalResult(case_id="b", passed=False),
        ]
        sr = EvalSuiteResult(
            suite_name="mixed",
            results=results,
            pass_rate=0.5,
            total_cases=2,
        )
        assert sr.passed_count == 1
        assert "50%" in sr.summary()


class TestEvalRunner:
    """EvalRunner executes cases against AgentLoop."""

    @pytest.mark.asyncio
    async def test_run_dry_returns_failure(self):
        """Dry run returns all-failed results."""
        runner = EvalRunner(model="test-model")
        cases = [EvalCase(id="dry", task="test")]
        results = await runner.run_dry(cases)
        assert len(results) == 1
        assert not results[0].passed
        assert "DRY RUN" in results[0].response

    def test_prebuilt_suites_exist(self):
        """Pre-built eval suites are non-empty."""
        assert len(CODING_EVAL) > 0
        assert len(REASONING_EVAL) > 0
        assert len(FACT_EVAL) > 0

    def test_all_suites_registered(self):
        """ALL_EVAL_SUITES contains all suites."""
        assert "coding" in ALL_EVAL_SUITES
        assert "reasoning" in ALL_EVAL_SUITES
        assert "facts" in ALL_EVAL_SUITES

    def test_eval_cases_have_ids(self):
        """Every eval case has a unique id."""
        all_ids = set()
        for suite_cases in ALL_EVAL_SUITES.values():
            for case in suite_cases:
                assert case.id not in all_ids, f"Duplicate id: {case.id}"
                all_ids.add(case.id)

    def test_eval_cases_have_keywords_or_tools(self):
        """Every eval case specifies at least one expectation."""
        for suite_name, cases in ALL_EVAL_SUITES.items():
            for case in cases:
                has_expectation = (
                    case.expected_keywords
                    or case.expected_tools
                    or case.forbidden_keywords
                )
                assert has_expectation, (
                    f"Case {case.id} in {suite_name} has no expectations"
                )

    @pytest.mark.asyncio
    async def test_run_case_with_mock(self):
        """run_case with mocked agent_loop produces valid result."""
        runner = EvalRunner(model="test-model")

        async def fake_loop(params):
            class FakeEvent:
                def __init__(self, type, data):
                    self.type = type
                    self.data = data
            yield FakeEvent("token", {"text": "The capital of France is Paris."})
            yield FakeEvent("done", {"turns": 1})

        with patch("ai_workspace.evals.agent_loop", side_effect=fake_loop):
            result = await runner.run_case(EvalCase(
                id="paris",
                task="What is the capital of France?",
                expected_keywords=["Paris"],
                forbidden_keywords=["London"],
            ))

            assert result.case_id == "paris"
            assert result.passed
            assert "Paris" in result.response
