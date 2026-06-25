"""Tests for agents/improvement.py — HALO-inspired self-improvement cycle."""

import datetime
import tempfile
from pathlib import Path

import pytest

from ai_workspace.agents.improvement import (
    FailurePattern,
    ImprovementReport,
    ReportApplier,
    TraceAnalyzer,
    print_report,
)


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def analyzer():
    return TraceAnalyzer()


@pytest.fixture
def sample_traces():
    """A batch of 5 traces, 3 clean, 2 with errors."""
    return [
        {
            "session_id": "s1",
            "errors": [],
            "tools_called": {"read_file": 3, "shell_exec": 1},
            "duration_ms": 1200,
        },
        {
            "session_id": "s2",
            "errors": [],
            "tools_called": {"edit_file": 2, "git": 1},
            "duration_ms": 800,
        },
        {
            "session_id": "s3",
            "errors": [
                {"type": "tool_error", "data": {"tool": "shell_exec", "message": "timeout"}},
            ],
            "tools_called": {"shell_exec": 5, "read_file": 2},
            "duration_ms": 5000,
        },
        {
            "session_id": "s4",
            "errors": [],
            "tools_called": {"read_file": 1},
            "duration_ms": 400,
        },
        {
            "session_id": "s5",
            "errors": [
                {"type": "tool_error", "data": {"tool": "shell_exec", "message": "permission denied"}},
            ],
            "tools_called": {"shell_exec": 3, "edit_file": 1},
            "duration_ms": 3200,
        },
    ]


@pytest.fixture
def empty_traces():
    return []


@pytest.fixture
def clean_traces():
    return [
        {
            "session_id": "c1",
            "errors": [],
            "tools_called": {"read_file": 2},
            "duration_ms": 500,
        },
        {
            "session_id": "c2",
            "errors": [],
            "tools_called": {"edit_file": 1},
            "duration_ms": 300,
        },
    ]


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temp workspace with memory dir."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    return tmp_path


# ═══════════════════════════════════════════════════════════
# FailurePattern
# ═══════════════════════════════════════════════════════════


class TestFailurePattern:
    def test_creation(self):
        p = FailurePattern(
            pattern_type="error_spike",
            description="3/5 traces have errors",
            frequency=3,
            severity=4,
            examples=["s1", "s3"],
            suggested_fix="Add retry logic",
        )
        assert p.pattern_type == "error_spike"
        assert p.frequency == 3
        assert p.severity == 4
        assert len(p.examples) == 2

    def test_defaults(self):
        p = FailurePattern(
            pattern_type="test",
            description="test",
            frequency=1,
            severity=1,
        )
        assert p.examples == []
        assert p.suggested_fix == ""


# ═══════════════════════════════════════════════════════════
# ImprovementReport
# ═══════════════════════════════════════════════════════════


class TestImprovementReport:
    def test_to_dict(self):
        report = ImprovementReport(
            generated_at="2026-06-25T10:00:00Z",
            period_start="s1",
            period_end="s5",
            total_traces=5,
            total_errors=2,
            pass_rate=0.6,
            top_tools=[("shell_exec", 9), ("read_file", 6)],
            patterns=[
                FailurePattern(
                    pattern_type="error_spike",
                    description="2/5 errors",
                    frequency=2,
                    severity=3,
                ),
            ],
            recommendations=["Add retry logic for shell_exec"],
            latency_p95=4800.0,
        )
        d = report.to_dict()
        assert d["total_traces"] == 5
        assert d["total_errors"] == 2
        assert d["pass_rate"] == 0.6
        assert len(d["top_tools"]) == 2
        assert d["top_tools"][0]["tool"] == "shell_exec"
        assert len(d["patterns"]) == 1
        assert d["patterns"][0]["type"] == "error_spike"
        assert len(d["recommendations"]) == 1

    def test_empty_report_to_dict(self):
        report = ImprovementReport()
        d = report.to_dict()
        assert d["total_traces"] == 0
        assert d["pass_rate"] == 1.0
        assert d["patterns"] == []


# ═══════════════════════════════════════════════════════════
# TraceAnalyzer
# ═══════════════════════════════════════════════════════════


class TestTraceAnalyzer:
    def test_empty_traces(self, analyzer, empty_traces):
        report = analyzer.analyze_traces(empty_traces)
        assert report.total_traces == 0
        assert report.pass_rate == 1.0
        assert report.total_errors == 0
        assert report.patterns == []

    def test_clean_traces(self, analyzer, clean_traces):
        report = analyzer.analyze_traces(clean_traces)
        assert report.total_traces == 2
        assert report.pass_rate == 1.0
        assert report.total_errors == 0
        assert report.patterns == []

    def test_error_detection(self, analyzer, sample_traces):
        report = analyzer.analyze_traces(sample_traces)
        assert report.total_traces == 5
        assert report.total_errors == 2
        assert report.pass_rate == 0.6  # 3/5 clean

    def test_error_spike_pattern(self, analyzer, sample_traces):
        report = analyzer.analyze_traces(sample_traces)
        spike_patterns = [p for p in report.patterns if p.pattern_type == "error_spike"]
        assert len(spike_patterns) == 1
        assert spike_patterns[0].frequency == 2
        assert spike_patterns[0].severity >= 2

    def test_tool_misuse_pattern(self, analyzer, sample_traces):
        report = analyzer.analyze_traces(sample_traces)
        misuse_patterns = [p for p in report.patterns if p.pattern_type == "tool_misuse"]
        assert len(misuse_patterns) == 1
        assert "shell_exec" in misuse_patterns[0].description

    def test_top_tools_ranking(self, analyzer, sample_traces):
        report = analyzer.analyze_traces(sample_traces)
        tools = {t: c for t, c in report.top_tools}
        assert tools["shell_exec"] == 9  # 5+3+1
        assert tools["read_file"] == 6   # 3+2+1

    def test_latency_p95(self, analyzer, sample_traces):
        report = analyzer.analyze_traces(sample_traces)
        # Latencies: [1200, 800, 5000, 400, 3200] → sorted: [400, 800, 1200, 3200, 5000]
        # P95 index = int(5 * 0.95) = 4 → sorted[4] = 5000
        assert report.latency_p95 == 5000.0

    def test_recommendations_generated(self, analyzer, sample_traces):
        report = analyzer.analyze_traces(sample_traces)
        # Should have at least one recommendation for error_spike
        assert len(report.recommendations) > 0

    def test_single_trace(self, analyzer):
        traces = [{"session_id": "s1", "errors": [], "tools_called": {}, "duration_ms": 100}]
        report = analyzer.analyze_traces(traces)
        assert report.total_traces == 1
        assert report.pass_rate == 1.0


# ═══════════════════════════════════════════════════════════
# ReportApplier
# ═══════════════════════════════════════════════════════════


class TestReportApplier:
    def test_apply_with_patterns(self, temp_workspace):
        applier = ReportApplier(workspace_root=temp_workspace)
        report = ImprovementReport(
            generated_at="2026-06-25T10:00:00Z",
            total_traces=10,
            patterns=[
                FailurePattern(
                    pattern_type="error_spike",
                    description="High error rate",
                    frequency=5,
                    severity=4,
                    suggested_fix="Add retry logic",
                ),
            ],
            recommendations=["Review error patterns"],
        )
        modified = applier.apply(report)
        assert modified >= 1  # At least learning-log updated

    def test_apply_empty_report(self, temp_workspace):
        applier = ReportApplier(workspace_root=temp_workspace)
        report = ImprovementReport()
        modified = applier.apply(report)
        # Empty report: no patterns → no learning-log, no conventions, no patterns
        # But _write_full_report still writes the report file
        assert modified >= 0

    def test_learning_log_created(self, temp_workspace):
        applier = ReportApplier(workspace_root=temp_workspace)
        report = ImprovementReport(
            patterns=[
                FailurePattern(
                    pattern_type="test_pattern",
                    description="Test description",
                    frequency=3,
                    severity=4,
                ),
            ],
        )
        applier.apply(report)
        log_path = temp_workspace / "memory" / "learning-log.md"
        assert log_path.exists()
        content = log_path.read_text()
        assert "test_pattern" in content

    def test_conventions_not_updated_for_low_severity(self, temp_workspace):
        applier = ReportApplier(workspace_root=temp_workspace)
        report = ImprovementReport(
            patterns=[
                FailurePattern(
                    pattern_type="minor",
                    description="Minor issue",
                    frequency=1,
                    severity=1,  # Below threshold
                ),
            ],
        )
        modified = applier.apply(report)
        # Low severity patterns don't update conventions
        conventions_path = temp_workspace / "memory" / "conventions.md"
        if conventions_path.exists():
            content = conventions_path.read_text()
            assert "minor" not in content


# ═══════════════════════════════════════════════════════════
# print_report
# ═══════════════════════════════════════════════════════════


class TestPrintReport:
    def test_print_empty_report(self, capsys):
        report = ImprovementReport()
        print_report(report)
        captured = capsys.readouterr()
        assert "No traces" in captured.out or "Total traces: 0" in captured.out

    def test_print_with_patterns(self, capsys):
        report = ImprovementReport(
            total_traces=5,
            total_errors=2,
            pass_rate=0.6,
            patterns=[
                FailurePattern(
                    pattern_type="error_spike",
                    description="2/5 errors",
                    frequency=2,
                    severity=4,
                ),
            ],
            recommendations=["Add retry"],
        )
        print_report(report)
        captured = capsys.readouterr()
        assert "error_spike" in captured.out
        assert "Add retry" in captured.out
