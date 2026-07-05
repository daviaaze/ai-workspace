"""
Improvement Cycle — Self-Improving Agent Loop (HALO-inspired).

Collects agent execution traces, analyzes them for failure patterns, and
produces actionable recommendations that feed back into agent configuration
and memory.

Inspired by HALO's "Collect traces → RLM analysis → Report → Fix → Redeploy"
pattern, but adapted for aiw's architecture:
  - Uses a regular LLM with structured prompts (not a specialized RLM)
  - Writes recommendations to workspace memory files (conventions, patterns)
  - Can be run on-demand or scheduled (weekly/monthly)

Flow:
  1. TraceSource reads traces from TraceStore (observability)
  2. TraceAnalyzer identifies patterns: failures, tool misuse, latency issues
  3. ReportGenerator produces structured improvement report
  4. RecommendationApplier writes actionable items to workspace memory
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.improvement")


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class FailurePattern:
    """A recurring failure observed across multiple traces.

    Attributes:
        pattern_type: Category of failure (tool_misuse, error_spike, prompt_issue, etc.)
        description: Human-readable description of the pattern.
        frequency: How many traces exhibit this pattern.
        severity: Estimated impact (1-5, 5=critical).
        examples: Example trace IDs for reference.
        suggested_fix: Recommended remediation.
    """
    pattern_type: str
    description: str
    frequency: int
    severity: int  # 1-5
    examples: list[str] = field(default_factory=list)
    suggested_fix: str = ""


@dataclass
class ImprovementReport:
    """Full improvement analysis report.

    Attributes:
        generated_at: Timestamp of report generation.
        period_start: Start of analysis period.
        period_end: End of analysis period.
        total_traces: Number of traces analyzed.
        total_errors: Total errors across all traces.
        pass_rate: Fraction of traces with no errors.
        top_tools: Most frequently called tools.
        patterns: Recurring failure patterns.
        recommendations: Actionable recommendations for memory files.
        latency_p95: 95th percentile latency (ms).
    """
    generated_at: str = ""
    period_start: str = ""
    period_end: str = ""
    total_traces: int = 0
    total_errors: int = 0
    pass_rate: float = 1.0
    top_tools: list[tuple[str, int]] = field(default_factory=list)
    patterns: list[FailurePattern] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    latency_p95: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "period": {
                "start": self.period_start,
                "end": self.period_end,
            },
            "total_traces": self.total_traces,
            "total_errors": self.total_errors,
            "pass_rate": round(self.pass_rate, 3),
            "top_tools": [
                {"tool": t, "count": c} for t, c in self.top_tools
            ],
            "patterns": [
                {
                    "type": p.pattern_type,
                    "description": p.description,
                    "frequency": p.frequency,
                    "severity": p.severity,
                    "examples": p.examples,
                    "suggested_fix": p.suggested_fix,
                }
                for p in self.patterns
            ],
            "recommendations": self.recommendations,
            "latency_p95_ms": round(self.latency_p95, 1),
        }


# ═══════════════════════════════════════════════════════════
# Trace Analysis
# ═══════════════════════════════════════════════════════════

class TraceAnalyzer:
    """Analyze agent traces for patterns, failures, and optimization opportunities."""

    def analyze_traces(self, traces: list[dict[str, Any]]) -> ImprovementReport:
        """Analyze a batch of traces and produce an improvement report.

        This is a heuristic analysis pass. For deeper analysis, use
        ``analyze_with_llm()`` which delegates to a model.
        """
        now = datetime.datetime.now(datetime.UTC).isoformat()
        total_errors = 0
        error_free = 0
        all_tools: dict[str, int] = {}
        latencies: list[float] = []
        patterns: list[FailurePattern] = []
        recommendations: list[str] = []

        trace_count = len(traces)

        # Determine period boundaries
        [t.get("duration_ms", 0) for t in traces]  # not timestamps, approximate
        period_start = traces[-1].get("session_id", "unknown") if traces else "unknown"
        period_end = traces[0].get("session_id", "unknown") if traces else "unknown"

        for trace in traces:
            errors = trace.get("errors", [])
            tools = trace.get("tools_called", {})
            latency = trace.get("duration_ms", 0)

            if errors:
                total_errors += len(errors)
            else:
                error_free += 1

            for tool_name, count in tools.items():
                all_tools[tool_name] = all_tools.get(tool_name, 0) + count

            if latency:
                latencies.append(latency)

        # Pass rate
        pass_rate = error_free / trace_count if trace_count > 0 else 1.0

        # Top tools
        top_tools = sorted(all_tools.items(), key=lambda x: -x[1])[:10]

        # P95 latency
        latency_p95 = 0.0
        if latencies:
            sorted_latencies = sorted(latencies)
            idx = int(len(sorted_latencies) * 0.95)
            latency_p95 = sorted_latencies[min(idx, len(sorted_latencies) - 1)]

        # Pattern detection: frequent errors
        error_traces = [t for t in traces if t.get("errors")]
        if len(error_traces) >= 2:
            patterns.append(FailurePattern(
                pattern_type="error_spike",
                description=f"{len(error_traces)}/{trace_count} traces contain errors "
                            f"({total_errors} total errors)",
                frequency=len(error_traces),
                severity=4 if pass_rate < 0.7 else 2,
                examples=[t.get("session_id", "") for t in error_traces[:5]],
                suggested_fix="Review error patterns in the trace details. "
                              "Consider adding retry logic or improving prompt constraints.",
            ))

        # Pattern detection: tool misuse (calls with errors)
        error_tools: dict[str, int] = {}
        for trace in traces:
            for err in trace.get("errors", []):
                tool = err.get("data", {}).get("tool", "") if isinstance(err, dict) else ""
                if tool:
                    error_tools[tool] = error_tools.get(tool, 0) + 1
        if error_tools:
            worst_tool = max(error_tools, key=error_tools.get)
            patterns.append(FailurePattern(
                pattern_type="tool_misuse",
                description=f"Tool '{worst_tool}' is associated with "
                            f"{error_tools[worst_tool]} errors",
                frequency=error_tools[worst_tool],
                severity=3,
                examples=[],
                suggested_fix=f"Review the '{worst_tool}' tool implementation "
                              f"and usage patterns. Consider adding validation.",
            ))

        # Pattern detection: high latency
        if latency_p95 > 30_000:  # >30s P95
            patterns.append(FailurePattern(
                pattern_type="latency_warning",
                description=f"P95 latency is {latency_p95:.0f}ms — "
                            f"above the 30s threshold",
                frequency=len([l for l in latencies if l > 30_000]),
                severity=2,
                examples=[],
                suggested_fix="Consider model optimizations: smaller model, "
                              "lower max_tokens, or streaming responses.",
            ))

        # Generate recommendations based on patterns
        if patterns:
            recommendations.append(
                f"Run `aiw improve` weekly to track {len(patterns)} "
                f"identified patterns"
            )

        if top_tools:
            most_used = top_tools[0][0]
            recommendations.append(
                f"Most-used tool '{most_used}' — consider adding "
                f"caching or batching for performance"
            )

        return ImprovementReport(
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            total_traces=trace_count,
            total_errors=total_errors,
            pass_rate=pass_rate,
            top_tools=top_tools,
            patterns=patterns,
            recommendations=recommendations,
            latency_p95=latency_p95,
        )

    async def analyze_with_llm(
        self,
        traces: list[dict[str, Any]],
        llm_prompt: str = "Diagnose errors and suggest improvements for this agent harness.",
    ) -> ImprovementReport:
        """Analyze traces using an LLM for deeper insight.

        Uses the configured provider to run a structured analysis.
        Falls back to heuristic analysis on failure.
        """
        # Start with heuristic analysis
        report = self.analyze_traces(traces)

        if not traces:
            return report

        try:
            from ai_workspace.providers import ProviderRegistry, chat_sync
        except Exception:
            logger.warning("Provider registry unavailable, using heuristic analysis only")
            return report

        # Prepare trace summaries for LLM (truncated to avoid token overflow)
        trace_summaries = []
        for t in traces[:20]:  # Limit to 20 traces
            trace_summaries.append({
                "session_id": t.get("session_id", "?"),
                "task": (t.get("task", "") or "")[:200],
                "model": t.get("model", ""),
                "steps": len(t.get("steps", [])),
                "tools_called": t.get("tools_called", {}),
                "errors": len(t.get("errors", [])),
                "tokens": t.get("tokens_used", 0),
                "duration_ms": t.get("duration_ms", 0),
            })

        system_prompt = """You are an AI agent improvement analyst. Your job is to:
1. Review agent execution traces
2. Identify recurring failure patterns, tool misuse, and optimization opportunities
3. Propose specific, actionable recommendations

Focus on patterns that appear across MULTIPLE traces — single-instance issues
are less important than systemic problems.

Output format:
PATTERNS:
- [type]: [description] (frequency: N, severity: 1-5)
  Fix: [specific suggestion]

RECOMMENDATIONS:
- [actionable item 1]
- [actionable item 2]

CONVENTIONS_UPDATE:
[optional update for memory/conventions.md]

PATTERNS_UPDATE:
[optional update for memory/project-patterns.md]"""

        user_prompt = f"""Analyze these {len(trace_summaries)} agent execution traces.

LLM prompt for analysis: {llm_prompt}

Traces:
{json.dumps(trace_summaries, indent=2)}

Heuristic analysis already identified:
- Pass rate: {report.pass_rate:.0%}
- Total errors: {report.total_errors}
- P95 latency: {report.latency_p95:.0f}ms
- Top tools: {[t for t, _ in report.top_tools[:5]]}
- Patterns found: {len(report.patterns)}

Please provide deeper insights and specific recommendations."""

        try:
            registry = ProviderRegistry()
            # Find first available provider with an API key
            provider_name, provider_cfg = None, None
            for name, cfg in registry.providers.items():
                if cfg.api_key:
                    provider_name, provider_cfg = name, cfg
                    break

            if provider_name is None:
                logger.warning("No configured provider found for LLM analysis")
                return report

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = chat_sync(
                provider=provider_name,
                model=provider_cfg.default_model or "",
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
            )

            content = ""
            if hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content or ""

            if content:
                # Extract additional recommendations from LLM response
                llm_recs = self._parse_llm_response(content, trace_summaries)
                report.recommendations.extend(llm_recs.get("recommendations", []))
                if llm_recs.get("conventions_update"):
                    report.recommendations.append(
                        f"CONVENTIONS: {llm_recs['conventions_update'][:500]}"
                    )
                if llm_recs.get("patterns_update"):
                    report.recommendations.append(
                        f"PATTERNS: {llm_recs['patterns_update'][:500]}"
                    )

        except Exception as exc:
            logger.warning("LLM analysis failed, using heuristic only: %s", exc)

        return report

    def _parse_llm_response(
        self,
        content: str,
        trace_summaries: list[dict],
    ) -> dict[str, list[str]]:
        """Extract structured data from LLM response text."""
        result: dict[str, list[str]] = {
            "recommendations": [],
            "conventions_update": [],
            "patterns_update": [],
        }

        current_section = ""
        for line in content.split("\n"):
            stripped = line.strip()
            upper = stripped.upper()

            if upper.startswith("RECOMMENDATIONS") or upper.startswith("RECOMMENDATION"):
                current_section = "recommendations"
                continue
            elif upper.startswith("CONVENTIONS_UPDATE") or stripped.startswith("### CONVENTIONS"):
                current_section = "conventions_update"
                continue
            elif upper.startswith("PATTERNS_UPDATE") or stripped.startswith("### PATTERNS"):
                current_section = "patterns_update"
                continue
            elif upper.startswith("PATTERNS"):
                current_section = "patterns"  # skip inline patterns, extract only recs
                continue

            if stripped.startswith("- ") and current_section in result:
                text = stripped[2:].strip()
                if text:
                    result[current_section].append(text)

        return result


# ═══════════════════════════════════════════════════════════
# Report Application
# ═══════════════════════════════════════════════════════════

class ReportApplier:
    """Applies improvement report findings to workspace memory files.

    Writes to:
      - memory/learning-log.md (date-tagged entries for problems and solutions)
      - memory/conventions.md (derived rules and standards)
      - memory/project-patterns.md (reusable workflow patterns)
    """

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or Path(
            os.environ.get("AIW_WORKSPACE", Path.home() / "Projects" / "pessoal" / "ai-workspace")
        )
        self.memory_dir = self.workspace_root / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def apply(self, report: ImprovementReport) -> int:
        """Apply findings to workspace files.

        Returns the number of files modified.
        """
        modified = 0

        if self._update_learning_log(report):
            modified += 1
        if self._update_conventions(report):
            modified += 1
        if self._update_project_patterns(report):
            modified += 1
        if self._write_full_report(report):
            modified += 1

        return modified

    def _update_learning_log(self, report: ImprovementReport) -> bool:
        """Add date-tagged entries to learning-log.md for each pattern."""
        if not report.patterns:
            return False

        path = self.memory_dir / "learning-log.md"
        path.read_text() if path.exists() else ""
        today = datetime.date.today().isoformat()
        new_entries: list[str] = []

        for pattern in report.patterns:
            if pattern.severity < 3:
                continue  # Only log significant patterns
            entry = (
                f"\n## {today} — Improvement Analysis: {pattern.pattern_type}\n\n"
                f"**What happened**: {pattern.description}\n\n"
                f"**Frequency**: {pattern.frequency} traces  |  "
                f"**Severity**: {pattern.severity}/5\n\n"
                f"**Fix**: {pattern.suggested_fix}\n"
                f"**Examples**: {', '.join(pattern.examples[:3])}\n"
            )
            new_entries.append(entry)

        if not new_entries:
            return False

        with open(path, "a") as f:
            f.write("\n" + "\n---\n".join(new_entries) + "\n")

        logger.info("Updated learning-log.md with %d new entries", len(new_entries))
        return True

    def _update_conventions(self, report: ImprovementReport) -> bool:
        """Update memory/conventions.md with derived rules."""
        if not report.recommendations:
            return False

        path = self.memory_dir / "conventions.md"
        existing = path.read_text() if path.exists() else ""
        today = datetime.date.today().isoformat()

        # Only add new conventions (deduplicate by checking if similar text exists)
        new_rules = []
        for rec in report.recommendations:
            if rec not in existing:
                entry = f"- (derived {today}) {rec}\n"
                new_rules.append(entry)

        if not new_rules:
            return False

        mode = "a" if path.exists() else "w"
        with open(path, mode) as f:
            if not path.exists() or path.stat().st_size == 0:
                f.write("# Conventions\n\nAuto-derived from agent improvement analysis.\n\n")
            f.write(f"## Improvement Cycle — {today}\n")
            f.writelines(new_rules)
            f.write("\n")

        logger.info("Updated conventions.md with %d new rules", len(new_rules))
        return True

    def _update_project_patterns(self, report: ImprovementReport) -> bool:
        """Update memory/project-patterns.md with reusable patterns."""
        if not report.patterns and not report.recommendations:
            return False

        path = self.memory_dir / "project-patterns.md"
        path.read_text() if path.exists() else ""
        today = datetime.date.today().isoformat()

        new_content = []

        if report.top_tools:
            tools_text = ", ".join(f"{t} ({c}x)" for t, c in report.top_tools[:5])
            new_content.append(f"- {today} — Top tools: {tools_text}")

        if report.latency_p95 > 0:
            new_content.append(
                f"- {today} — P95 latency {report.latency_p95:.0f}ms "
                f"({report.total_traces} traces, "
                f"{report.pass_rate:.0%} pass rate)"
            )

        if not new_content:
            return False

        mode = "a" if path.exists() else "w"
        with open(path, mode) as f:
            if not path.exists() or path.stat().st_size == 0:
                f.write("# Project Patterns\n\nOperational metrics from agent improvement cycles.\n\n")
            f.write(f"## {today}\n")
            f.writelines(f"{item}\n" for item in new_content)
            f.write("\n")

        logger.info("Updated project-patterns.md with %d new entries", len(new_content))
        return True

    def _write_full_report(self, report: ImprovementReport) -> bool:
        """Write the full JSON report to disk for later reference."""
        reports_dir = self.memory_dir / "improvement-reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.date.today().isoformat()
        path = reports_dir / f"{today}.json"

        # Avoid overwriting same-day reports
        if path.exists():
            import hashlib
            content_hash = hashlib.md5(
                json.dumps(report.to_dict(), sort_keys=True).encode()
            ).hexdigest()[:8]
            path = reports_dir / f"{today}-{content_hash}.json"

        path.write_text(json.dumps(report.to_dict(), indent=2))
        logger.info("Wrote full improvement report to %s", path)
        return True


# ═══════════════════════════════════════════════════════════
# Improvement Cycle (orchestrator)
# ═══════════════════════════════════════════════════════════

class ImprovementCycle:
    """Full self-improvement cycle: collect → analyze → apply.

    Usage::

        cycle = ImprovementCycle()
        report = await cycle.run()  # Analyzes recent traces
        cycle.run_sync()            # Synchronous variant

    Or from CLI::

        aiw improve                    # Run full cycle
        aiw improve --days 7           # Last 7 days of traces
        aiw improve --llm-prompt "..." # Custom analysis focus
    """

    def __init__(
        self,
        trace_dir: Path | None = None,
        workspace_root: Path | None = None,
    ):
        self.trace_dir = trace_dir  # None = use TraceStore default
        self.analyzer = TraceAnalyzer()
        self.applier = ReportApplier(workspace_root=workspace_root)

    def collect_traces(self, days: int = 7, max_traces: int = 100) -> list[dict[str, Any]]:
        """Collect recent traces from TraceStore.

        Args:
            days: How many days of traces to include.
            max_traces: Maximum number of traces to analyze.

        Returns:
            List of trace dicts, most recent first.
        """
        from ai_workspace.observability import TraceStore

        store = TraceStore(base_dir=self.trace_dir) if self.trace_dir else TraceStore()
        sessions = store.list_sessions(limit=max_traces)

        traces = []
        for session in sessions:
            trace = store.load(session["session_id"])
            if trace:
                traces.append(trace.to_dict())

        return traces[:max_traces]

    async def run(
        self,
        days: int = 7,
        max_traces: int = 100,
        use_llm: bool = False,
        llm_prompt: str = "Diagnose errors and suggest improvements for this agent harness.",
    ) -> ImprovementReport:
        """Run the full improvement cycle.

        Args:
            days: How many days of traces to analyze.
            max_traces: Maximum number of traces to include.
            use_llm: Whether to use LLM analysis (vs heuristic only).
            llm_prompt: Custom prompt for LLM analysis.

        Returns:
            The generated improvement report.
        """
        logger.info("Starting improvement cycle (days=%d, max_traces=%d)", days, max_traces)

        # 1. Collect
        traces = self.collect_traces(days=days, max_traces=max_traces)
        logger.info("Collected %d traces", len(traces))

        if not traces:
            logger.info("No traces to analyze — run some agent tasks first!")
            return ImprovementReport(
                generated_at=datetime.datetime.now(datetime.UTC).isoformat(),
                total_traces=0,
                recommendations=["No traces available. Run agents first, then re-run improvement cycle."],
            )

        # 2. Analyze
        if use_llm:
            report = await self.analyzer.analyze_with_llm(traces, llm_prompt=llm_prompt)
        else:
            report = self.analyzer.analyze_traces(traces)

        logger.info(
            "Analysis complete: %d patterns, %d recommendations",
            len(report.patterns),
            len(report.recommendations),
        )

        # 3. Apply
        modified_files = self.applier.apply(report)
        logger.info("Applied findings to %d files", modified_files)

        return report

    def run_sync(
        self,
        days: int = 7,
        max_traces: int = 100,
    ) -> ImprovementReport:
        """Synchronous variant for CLI use."""
        import asyncio
        return asyncio.run(self.run(days=days, max_traces=max_traces, use_llm=False))


# ═══════════════════════════════════════════════════════════
# Convenience
# ═══════════════════════════════════════════════════════════

def print_report(report: ImprovementReport) -> None:
    """Print a human-readable improvement report to console."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    if report.total_traces == 0:
        console.print("[yellow]No traces to analyze.[/]")
        return

    console.print(Panel("[bold]Agent Improvement Report[/]", title=f" {report.total_traces} traces"))

    # Summary metrics
    summary = Table(show_header=False)
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value")
    summary.add_row("Traces Analyzed", str(report.total_traces))
    summary.add_row("Pass Rate", f"{report.pass_rate:.0%}")
    summary.add_row("Total Errors", str(report.total_errors))
    summary.add_row("P95 Latency", f"{report.latency_p95:.0f}ms")
    summary.add_row("Patterns Found", str(len(report.patterns)))
    console.print(summary)

    # Top tools
    if report.top_tools:
        tools_table = Table(title=" Top Tools")
        tools_table.add_column("Tool", style="cyan")
        tools_table.add_column("Calls")
        for tool, count in report.top_tools[:5]:
            tools_table.add_row(tool, str(count))
        console.print(tools_table)

    # Failure patterns
    if report.patterns:
        for p in report.patterns:
            severity_color = {
                1: "green", 2: "green", 3: "yellow",
                4: "red", 5: "bold red",
            }.get(p.severity, "white")
            console.print(
                f"\n[{severity_color}]{p.pattern_type}[/] (sev {p.severity}/5, "
                f"freq {p.frequency}x): {p.description}"
            )
            if p.suggested_fix:
                console.print(f"  [dim]Fix:[/] {p.suggested_fix}")
    else:
        console.print("\n[green]No significant failure patterns found.[/]")

    # Recommendations
    if report.recommendations:
        console.print("\n[bold]Recommendations:[/]")
        for rec in report.recommendations:
            console.print(f"  • {rec}")

    console.print(f"\n[dim]Generated: {report.generated_at}[/]")
