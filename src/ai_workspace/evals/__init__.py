"""
Agent Eval Harness — Lightweight quality assessment for AgentLoop.

Run eval suites against the agent to measure:
- Task completion rate
- Tool call accuracy
- Response quality (keyword checks, hallucination detection)
- Latency and token usage

Refs:
- SPEC_EVAL_HARNESS.md
- GAGE, evalh, proofagent-harness
"""

from __future__ import annotations

import asyncio
import json as _json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator

from ai_workspace.agents.loop import (
    LoopParams,
    LoopPattern,
    TerminalReason,
    agent_loop,
)


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class EvalCase:
    """A single evaluation test case.

    Attributes:
        id: Unique test identifier.
        task: Natural language task for the agent.
        pattern: LoopPattern to use (default: auto-detect).
        expected_tools: Tools the agent should call (empty = no tools expected).
        expected_keywords: Keywords that should appear in the response.
        forbidden_keywords: Keywords that should NOT appear (hallucination check).
        min_confidence: Minimum confidence threshold (0.0 - 1.0).
        max_turns: Maximum turns allowed.
        max_latency_ms: Maximum acceptable latency.
    """
    id: str
    task: str
    pattern: LoopPattern | None = None
    expected_tools: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)
    min_confidence: float = 0.0
    max_turns: int = 10
    max_latency_ms: float = 60_000  # 60s


@dataclass
class EvalResult:
    """Result of a single eval case execution.

    Attributes:
        case_id: The test case that was run.
        passed: Whether all checks passed.
        checks: Individual check results {check_name: passed_bool}.
        metrics: Quantitative metrics (tokens, turns, latency).
        trace: Full event trace for debugging.
        response: Final agent response text.
    """
    case_id: str
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize for reporting."""
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "checks": self.checks,
            "metrics": self.metrics,
            "response": self.response[:500],
        }


@dataclass
class EvalSuiteResult:
    """Aggregate results for an eval suite.

    Attributes:
        suite_name: Name of the eval suite.
        results: Per-case results.
        pass_rate: Fraction of cases that passed.
        total_cases: Number of cases executed.
        avg_latency_ms: Average latency across all cases.
        avg_tokens: Average tokens per case.
    """
    suite_name: str
    results: list[EvalResult] = field(default_factory=list)
    pass_rate: float = 0.0
    total_cases: int = 0
    avg_latency_ms: float = 0.0
    avg_tokens: float = 0.0

    @property
    def passed_count(self) -> int:
        """Number of passed cases."""
        return sum(1 for r in self.results if r.passed)

    def summary(self) -> str:
        """Human-readable summary string."""
        return (
            f"[{self.suite_name}] "
            f"{self.passed_count}/{self.total_cases} passed "
            f"({self.pass_rate:.0%}) | "
            f"avg {self.avg_latency_ms:.0f}ms | "
            f"avg {self.avg_tokens:.0f} tokens"
        )


# ═══════════════════════════════════════════════════════════
# Eval Runner
# ═══════════════════════════════════════════════════════════

class EvalRunner:
    """Executes eval suites against the AgentLoop.

    Usage:
        runner = EvalRunner(model="qwen3:14b")
        result = await runner.run_case(EvalCase(
            id="simple_math",
            task="What is 2+2?",
            expected_keywords=["4"],
        ))
        assert result.passed
    """

    def __init__(
        self,
        model: str = "qwen3:14b",
        provider: str = "ollama",
    ):
        self.model = model
        self.provider = provider

    async def run_case(self, case: EvalCase) -> EvalResult:
        """Execute a single eval case.

        Runs the agent with the task and checks the response
        against all expectations.

        Args:
            case: The eval case definition.

        Returns:
            EvalResult with pass/fail and detailed checks.
        """
        t0 = time.monotonic()
        trace: list[dict[str, Any]] = []
        response_parts: list[str] = []
        tools_called: list[str] = []
        turns = 0
        errors: list[str] = []

        pattern = case.pattern or LoopPattern.DIRECT
        params = LoopParams(
            task=case.task,
            pattern=pattern,
            model=self.model,
            provider=self.provider,
            stream=True,
            max_turns=case.max_turns,
        )

        try:
            async for event in agent_loop(params):
                trace.append({
                    "type": event.type,
                    "data": event.data,
                })

                if event.type == "token":
                    response_parts.append(event.data.get("text", ""))
                elif event.type == "tool_call":
                    tools_called.append(event.data.get("tool", ""))
                elif event.type == "done":
                    turns = event.data.get("turns", 0)
                elif event.type == "error":
                    errors.append(event.data.get("message", ""))

        except Exception as exc:
            errors.append(str(exc))

        latency_ms = (time.monotonic() - t0) * 1000
        response = "".join(response_parts)

        # ── Run checks ───────────────────────────────────
        checks: dict[str, bool] = {}

        # Tool call check
        if case.expected_tools:
            checks["tools_called"] = all(
                tool in tools_called for tool in case.expected_tools
            )
        else:
            checks["tools_called"] = True  # no expectation

        # Keyword check
        if case.expected_keywords:
            response_lower = response.lower()
            checks["keywords"] = all(
                kw.lower() in response_lower
                for kw in case.expected_keywords
            )
        else:
            checks["keywords"] = True

        # Forbidden keyword check (anti-hallucination)
        if case.forbidden_keywords:
            response_lower = response.lower()
            checks["no_hallucination"] = not any(
                kw.lower() in response_lower
                for kw in case.forbidden_keywords
            )
        else:
            checks["no_hallucination"] = True

        # Confidence check (heuristic: response must not be empty)
        has_response = len(response.strip()) > 0
        checks["has_response"] = has_response

        # Error check
        checks["no_errors"] = len(errors) == 0

        # Latency check
        checks["latency"] = latency_ms <= case.max_latency_ms

        # Turns check
        checks["turns"] = turns <= case.max_turns

        # Overall
        passed = all(checks.values())

        return EvalResult(
            case_id=case.id,
            passed=passed,
            checks=checks,
            metrics={
                "tokens": len(response.split()),
                "turns": turns,
                "latency_ms": round(latency_ms, 1),
                "tool_calls": len(tools_called),
                "errors": len(errors),
            },
            trace=trace,
            response=response,
        )

    async def run_suite(
        self,
        name: str,
        cases: list[EvalCase],
    ) -> EvalSuiteResult:
        """Execute a suite of eval cases and aggregate results.

        Args:
            name: Suite name for reporting.
            cases: List of eval case definitions.

        Returns:
            Aggregated suite result.
        """
        results = []
        for case in cases:
            result = await self.run_case(case)
            results.append(result)

        # Aggregate metrics
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        latencies = [
            r.metrics["latency_ms"] for r in results
            if "latency_ms" in r.metrics
        ]
        tokens_list = [
            r.metrics["tokens"] for r in results
            if "tokens" in r.metrics
        ]

        return EvalSuiteResult(
            suite_name=name,
            results=results,
            pass_rate=passed / total if total > 0 else 0.0,
            total_cases=total,
            avg_latency_ms=(
                sum(latencies) / len(latencies) if latencies else 0.0
            ),
            avg_tokens=(
                sum(tokens_list) / len(tokens_list) if tokens_list else 0.0
            ),
        )

    async def run_dry(
        self,
        cases: list[EvalCase],
    ) -> list[EvalResult]:
        """Run eval cases in dry-run mode (no LLM calls).

        Returns results with all checks failing — useful for
        validating eval case definitions before running against
        a real model.
        """
        results = []
        for case in cases:
            results.append(EvalResult(
                case_id=case.id,
                passed=False,
                checks={k: False for k in [
                    "tools_called", "keywords", "no_hallucination",
                    "has_response", "no_errors", "latency", "turns",
                ]},
                metrics={
                    "tokens": 0, "turns": 0,
                    "latency_ms": 0, "tool_calls": 0, "errors": 1,
                },
                response="[DRY RUN — no LLM called]",
            ))
        return results


# ═══════════════════════════════════════════════════════════
# Pre-built eval suites
# ═══════════════════════════════════════════════════════════

CODING_EVAL: list[EvalCase] = [
    EvalCase(
        id="explain_simple_function",
        task=(
            "Explain what this Python function does in one sentence: "
            "def add(a, b): return a + b"
        ),
        expected_keywords=["add", "sum"],
        pattern=LoopPattern.DIRECT,
    ),
    EvalCase(
        id="explain_list_comprehension",
        task=(
            "What does this code do? [x*2 for x in range(10) if x % 2 == 0]"
        ),
        expected_keywords=["even", "double", "multiply"],
        pattern=LoopPattern.DIRECT,
    ),
]

REASONING_EVAL: list[EvalCase] = [
    EvalCase(
        id="simple_math",
        task="If a train travels 60 miles in 2 hours, what is its speed?",
        expected_keywords=["30", "mph", "miles per hour"],
        forbidden_keywords=["I don't know"],
    ),
    EvalCase(
        id="logic_puzzle",
        task=(
            "If all dogs are mammals and all mammals are animals, "
            "are all dogs animals? Answer yes or no and explain."
        ),
        expected_keywords=["yes"],
        forbidden_keywords=["I'm not sure"],
    ),
]

FACT_EVAL: list[EvalCase] = [
    EvalCase(
        id="capital_city",
        task="What is the capital of France?",
        expected_keywords=["Paris"],
        forbidden_keywords=["London", "Berlin", "Madrid"],
    ),
    EvalCase(
        id="python_version_released",
        task="In what year was Python 3.0 first released?",
        expected_keywords=["2008"],
        forbidden_keywords=["I don't know exactly"],
    ),
]

# All suites combined
ALL_EVAL_SUITES: dict[str, list[EvalCase]] = {
    "coding": CODING_EVAL,
    "reasoning": REASONING_EVAL,
    "facts": FACT_EVAL,
}


# ═══════════════════════════════════════════════════════════
# Convenience functions
# ═══════════════════════════════════════════════════════════

async def run_all_evals(
    model: str = "qwen3:14b",
    provider: str = "ollama",
    suites: list[str] | None = None,
) -> dict[str, EvalSuiteResult]:
    """Run all eval suites against a model.

    Args:
        model: Model to evaluate.
        provider: Provider name.
        suites: Subset of suites to run (default: all).

    Returns:
        Dict of suite_name -> EvalSuiteResult.
    """
    runner = EvalRunner(model=model, provider=provider)
    results: dict[str, EvalSuiteResult] = {}

    suite_names = suites or list(ALL_EVAL_SUITES.keys())
    for name in suite_names:
        cases = ALL_EVAL_SUITES.get(name, [])
        if cases:
            results[name] = await runner.run_suite(name, cases)

    return results
