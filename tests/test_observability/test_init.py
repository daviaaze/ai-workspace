"""
Tests for Agent Observability — DiffTracker, AgentTrace, TraceStore.

Refs: SPEC_OBSERVABILITY.md
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_workspace.observability import (
    AgentTrace,
    DiffTracker,
    FileSnapshot,
    TraceStore,
    trace_agent_loop,
)


class TestFileSnapshot:
    """FileSnapshot dataclass."""

    def test_defaults(self):
        """Snapshot captures path, content, timing."""
        snap = FileSnapshot(
            path="src/main.py",
            content="def foo(): pass",
            timestamp=100.0,
            agent_step=3,
        )
        assert snap.path == "src/main.py"
        assert "def foo" in snap.content
        assert snap.timestamp == 100.0
        assert snap.agent_step == 3


class TestDiffTracker:
    """DiffTracker captures file changes."""

    def test_no_snapshots_summary(self):
        """Empty tracker has zero changes."""
        tracker = DiffTracker()
        summary = tracker.get_summary()
        assert summary["files_modified"] == 0
        assert summary["total_snapshots"] == 0

    def test_single_snapshot_no_changes(self):
        """One snapshot = zero changes tracked."""
        tracker = DiffTracker()
        tracker.snapshots["test.py"] = [
            FileSnapshot(
                path="test.py", content="v1", timestamp=1.0,
                agent_step=1,
            ),
        ]
        summary = tracker.get_summary()
        assert summary["total_snapshots"] == 1
        assert summary["changes"] == {}  # no changes (only 1 snapshot)

    def test_two_snapshots_one_change(self):
        """Two snapshots = 1 change."""
        tracker = DiffTracker()
        tracker.snapshots["test.py"] = [
            FileSnapshot(path="test.py", content="v1", timestamp=1.0, agent_step=1),
            FileSnapshot(path="test.py", content="v2", timestamp=2.0, agent_step=3),
        ]
        summary = tracker.get_summary()
        assert summary["files_modified"] == 1
        assert summary["changes"]["test.py"] == 1

    def test_get_diff(self):
        """get_diff returns unified diff."""
        tracker = DiffTracker()
        tracker.snapshots["test.py"] = [
            FileSnapshot(path="test.py", content="line1\nline2\n", timestamp=1.0, agent_step=1),
            FileSnapshot(path="test.py", content="line1\nCHANGED\nline2\n", timestamp=2.0, agent_step=2),
        ]
        diff = tracker.get_diff("test.py", 1, 2)
        assert "CHANGED" in diff
        assert "test.py" in diff

    def test_get_diff_missing(self):
        """Missing snapshot returns error message."""
        tracker = DiffTracker()
        diff = tracker.get_diff("nonexistent.py", 1, 2)
        assert "No snapshots" in diff

    def test_serialization_roundtrip(self):
        """to_dict + from_dict roundtrip."""
        tracker = DiffTracker()
        tracker.snapshots["f.py"] = [
            FileSnapshot(path="f.py", content="x", timestamp=1.0, agent_step=1),
        ]
        data = tracker.to_dict()
        restored = DiffTracker.from_dict(data)
        assert len(restored.snapshots) == 1
        assert restored.snapshots["f.py"][0].content == "x"

    def test_snapshot_nonexistent_file(self):
        """Snapshot of missing file is no-op."""
        tracker = DiffTracker()
        tracker.snapshot("/nonexistent/file.py", step=1)
        assert len(tracker.snapshots) == 0


class TestAgentTrace:
    """AgentTrace records execution steps."""

    def test_empty_trace(self):
        """Empty trace has correct defaults."""
        trace = AgentTrace(session_id="test-1")
        assert trace.session_id == "test-1"
        assert trace.steps == []
        assert trace.tools_called == {}

    def test_record_step(self):
        """record_step adds to steps list."""
        trace = AgentTrace(session_id="test-1")
        trace.record_step("tool_call", {"tool": "read_file"})
        trace.record_step("error", {"message": "file not found"})

        assert len(trace.steps) == 2
        assert trace.tools_called["read_file"] == 1
        assert len(trace.errors) == 1

    def test_record_multiple_tool_calls(self):
        """Multiple calls to same tool increment count."""
        trace = AgentTrace(session_id="test-1")
        trace.record_step("tool_call", {"tool": "shell"})
        trace.record_step("tool_call", {"tool": "shell"})
        trace.record_step("tool_call", {"tool": "read_file"})

        assert trace.tools_called["shell"] == 2
        assert trace.tools_called["read_file"] == 1

    def test_serialization_roundtrip(self):
        """to_dict + from_dict preserves all fields."""
        trace = AgentTrace(
            session_id="s1",
            task="Fix bug",
            model="qwen3:14b",
            provider="ollama",
            tokens_used=500,
            cost=0.0,
            duration_ms=1234.5,
        )
        trace.record_step("token", {"text": "hello"})

        data = trace.to_dict()
        restored = AgentTrace.from_dict(data)

        assert restored.session_id == "s1"
        assert restored.task == "Fix bug"
        assert restored.tokens_used == 500
        assert restored.duration_ms == 1234.5
        assert len(restored.steps) == 1


class TestTraceStore:
    """TraceStore saves and loads traces to disk."""

    def test_save_and_load(self):
        """Trace saved to disk can be loaded back."""
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(base_dir=Path(tmp))
            trace = AgentTrace(
                session_id="test-session",
                task="Research X",
                model="test-model",
                tokens_used=100,
            )
            trace.record_step("tool_call", {"tool": "web_search"})

            path = store.save(trace)
            assert path.exists()

            loaded = store.load("test-session")
            assert loaded is not None
            assert loaded.session_id == "test-session"
            assert loaded.tokens_used == 100
            assert len(loaded.steps) == 1

    def test_load_nonexistent(self):
        """Loading missing trace returns None."""
        store = TraceStore()
        result = store.load("nonexistent-id")
        assert result is None

    def test_list_sessions(self):
        """list_sessions returns summaries."""
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(base_dir=Path(tmp))
            store.save(AgentTrace(session_id="a", task="T1", model="m1"))
            store.save(AgentTrace(session_id="b", task="T2", model="m2"))

            sessions = store.list_sessions()
            assert len(sessions) >= 2
            ids = {s["session_id"] for s in sessions}
            assert "a" in ids
            assert "b" in ids

    def test_delete(self):
        """delete removes trace from disk."""
        with tempfile.TemporaryDirectory() as tmp:
            store = TraceStore(base_dir=Path(tmp))
            store.save(AgentTrace(session_id="del-me"))
            assert store.load("del-me") is not None

            assert store.delete("del-me") is True
            assert store.load("del-me") is None

    def test_delete_nonexistent(self):
        """Deleting missing trace returns False."""
        store = TraceStore()
        assert store.delete("no-such-id") is False


class TestTraceAgentLoop:
    """Convenience function for creating trace + diff tracker."""

    def test_creates_both(self):
        """trace_agent_loop returns trace and tracker."""
        trace, tracker = trace_agent_loop("session-1")
        assert isinstance(trace, AgentTrace)
        assert isinstance(tracker, DiffTracker)
        assert trace.session_id == "session-1"
