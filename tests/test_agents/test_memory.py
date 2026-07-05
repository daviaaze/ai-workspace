"""Tests for PersistentMemory — L1/L2/L3 hierarchical memory."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_workspace.agents.memory import (
    L1Trace,
    L2Fact,
    MemoryStats,
    PersistentMemory,
    TraceEvent,
)

# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def mem() -> PersistentMemory:
    """A PersistentMemory instance backed by a temp directory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield PersistentMemory(tmp)


@pytest.fixture
def sample_events() -> list[TraceEvent]:
    """Sample trace events for testing."""
    now = datetime.now(UTC).isoformat()
    return [
        TraceEvent(
            timestamp=now,
            session_id="test-001",
            type="tool_call",
            content="read main.py",
            tool="filesystem",
            tokens=50,
        ),
        TraceEvent(
            timestamp=now,
            session_id="test-001",
            type="error",
            content="FileNotFoundError: main.py not found",
            tool="",
            tokens=20,
        ),
        TraceEvent(
            timestamp=now,
            session_id="test-001",
            type="tool_result",
            content="Fixed import path in config.py",
            tool="filesystem",
            tokens=30,
        ),
        TraceEvent(
            timestamp=now,
            session_id="test-001",
            type="thinking",
            content="Let me check the import structure...",
            tool="",
            tokens=40,
        ),
    ]


# ═══════════════════════════════════════════════════════════
# Initialization
# ═══════════════════════════════════════════════════════════


class TestInit:
    def test_default_dir(self):
        """Default dir is ~/.aiw/memory/."""
        mem = PersistentMemory()
        assert str(mem.stats().memory_dir).endswith(".aiw/memory")

    def test_custom_dir(self):
        """Custom memory dir is respected."""
        with tempfile.TemporaryDirectory() as tmp:
            mem = PersistentMemory(tmp)
            assert mem.stats().memory_dir == str(Path(tmp))

    def test_creates_directories(self):
        """L1, L2, L3 dirs are created on init."""
        with tempfile.TemporaryDirectory() as tmp:
            PersistentMemory(tmp)
            assert (Path(tmp) / "l1").is_dir()
            assert (Path(tmp) / "l2").is_dir()
            assert (Path(tmp) / "l3").is_dir()


# ═══════════════════════════════════════════════════════════
# L1 Traces
# ═══════════════════════════════════════════════════════════


class TestL1Traces:
    def test_write_and_read(self, mem: PersistentMemory, sample_events):
        """Write L1 trace then read it back."""
        mem.write_l1_trace("test-001", sample_events)
        events = mem.read_l1_events(session_id="test-001")
        assert len(events) == 4

    def test_read_filter_session(self, mem: PersistentMemory, sample_events):
        """Filter L1 reads by session ID."""
        mem.write_l1_trace("session-a", sample_events)

        events_all = mem.read_l1_events(session_id="session-a")
        assert len(events_all) == 4

        # Filter by 'since' to get 0 results
        events_since = mem.read_l1_events(since="2099-01-01")
        assert len(events_since) == 0

    def test_read_limit(self, mem: PersistentMemory, sample_events):
        """L1 read respects limit parameter."""
        mem.write_l1_trace("test-001", sample_events)
        events = mem.read_l1_events(session_id="test-001", limit=2)
        assert len(events) <= 2

    def test_read_since(self, mem: PersistentMemory, sample_events):
        """L1 read respects since parameter."""
        mem.write_l1_trace("test-001", sample_events)
        # Use a date far in the future
        events = mem.read_l1_events(since="2099-01-01")
        assert len(events) == 0

    def test_empty_read(self, mem: PersistentMemory):
        """Reading from empty store returns empty list."""
        events = mem.read_l1_events()
        assert events == []

    def test_get_l1_files(self, mem: PersistentMemory, sample_events):
        """get_l1_files returns sorted file list."""
        mem.write_l1_trace("test-001", sample_events)
        files = mem.get_l1_files()
        assert len(files) >= 1
        assert all(f.suffix == ".jsonl" for f in files)


# ═══════════════════════════════════════════════════════════
# L2 Facts
# ═══════════════════════════════════════════════════════════


class TestL2Facts:
    def test_write_and_read(self, mem: PersistentMemory):
        """Write L2 facts then read them back."""
        facts = [
            L2Fact(
                surface="coding",
                title="Error: file not found",
                body="FileNotFoundError on main.py — fixed path",
                source_session="test-001",
                source_timestamp="2026-06-24T12:00:00",
                tags=["error"],
            ),
        ]
        mem.write_l2_facts("coding", facts, append=False)

        read = mem.read_l2_facts("coding")
        assert len(read) >= 1
        assert "Error: file not found" in read[0]["title"]

    def test_append_facts(self, mem: PersistentMemory):
        """Writing facts to existing surface appends."""
        first = [L2Fact("coding", "Fact 1", "Body 1", "s1", "ts", ["fix"])]
        second = [L2Fact("coding", "Fact 2", "Body 2", "s2", "ts", ["pattern"])]

        mem.write_l2_facts("coding", first, append=False)
        mem.write_l2_facts("coding", second, append=True)

        facts = mem.read_l2_facts("coding")
        assert len(facts) == 2

    def test_overwrite_facts(self, mem: PersistentMemory):
        """Writing with append=False overwrites existing facts."""
        first = [L2Fact("coding", "Fact 1", "Body 1", "s1", "ts")]
        second = [L2Fact("coding", "Fact 2", "Body 2", "s2", "ts")]

        mem.write_l2_facts("coding", first, append=False)
        mem.write_l2_facts("coding", second, append=False)

        facts = mem.read_l2_facts("coding")
        assert len(facts) == 1
        assert facts[0]["title"] == "Fact 2"

    def test_list_surfaces(self, mem: PersistentMemory):
        """list_l2_surfaces returns all surface names."""
        mem.write_l2_facts("coding", [L2Fact("coding", "T", "B", "s1", "ts")])
        mem.write_l2_facts("research", [L2Fact("research", "T", "B", "s1", "ts")])

        surfaces = mem.list_l2_surfaces()
        assert "coding" in surfaces
        assert "research" in surfaces

    def test_empty_surface(self, mem: PersistentMemory):
        """Non-existent surface returns empty list."""
        facts = mem.read_l2_facts("nonexistent")
        assert facts == []

    def test_get_l2_context(self, mem: PersistentMemory):
        """get_l2_context returns formatted context string."""
        mem.write_l2_facts(
            "coding",
            [L2Fact("coding", "Fact One", "Body content", "s1", "ts")],
        )
        ctx = mem.get_l2_context(["coding"])
        assert "Fact One" in ctx
        assert "Body content" in ctx
        assert "Coding" in ctx  # Header uses title()

    def test_get_l2_context_empty(self, mem: PersistentMemory):
        """get_l2_context with no data returns empty string."""
        ctx = mem.get_l2_context(["nonexistent"])
        assert ctx == ""

    def test_get_l2_context_all_surfaces(self, mem: PersistentMemory):
        """get_l2_context with None surfaces reads all."""
        mem.write_l2_facts("coding", [L2Fact("coding", "T", "B", "s1", "ts")])
        ctx = mem.get_l2_context()
        assert "Coding" in ctx  # Header uses title()


# ═══════════════════════════════════════════════════════════
# L3 Synthesis
# ═══════════════════════════════════════════════════════════


class TestL3:
    def test_write_and_read_profile(self, mem: PersistentMemory):
        """Write and read profile L3."""
        mem.write_l3_profile("User is a developer working on Python projects.")
        content = mem.read_l3("profile")
        assert "developer" in content
        assert "Python" in content

    def test_write_and_read_recent(self, mem: PersistentMemory):
        """Write and read recent L3."""
        mem.write_l3_recent("Recent activities: fixed imports, refactored CLI.")
        content = mem.read_l3("recent")
        assert "CLI" in content

    def test_write_and_read_scope(self, mem: PersistentMemory):
        """Write and read scope L3."""
        mem.write_l3_scope("Current scope: Phase 2 implementation.")
        content = mem.read_l3("scope")
        assert "Phase 2" in content

    def test_list_l3_files(self, mem: PersistentMemory):
        """list_l3_files returns L3 file list."""
        mem.write_l3_profile("Profile.")
        mem.write_l3_recent("Recent.")
        files = mem.list_l3_files()
        assert len(files) >= 2

    def test_read_nonexistent(self, mem: PersistentMemory):
        """Reading non-existent L3 returns empty string."""
        content = mem.read_l3("nonexistent")
        assert content == ""

    def test_consolidate_l3(self, mem: PersistentMemory):
        """Consolidation generates recent and scope L3 files."""
        mem.write_l2_facts(
            "coding",
            [L2Fact("coding", "Fixed imports", "Resolved import path", "s1", "ts")],
        )

        result = mem.consolidate_l3()
        assert "recent" in result
        assert "scope" in result
        # Surface name is title-cased in output ("Coding"), check case-insensitively
        assert "coding" in result["recent"].lower()

    def test_consolidate_l3_empty(self, mem: PersistentMemory):
        """Consolidation with no L2 facts still generates output."""
        result = mem.consolidate_l3()
        assert result["recent"] != ""


# ═══════════════════════════════════════════════════════════
# Consolidation (L1 → L2 heuristic)
# ═══════════════════════════════════════════════════════════


class TestConsolidation:
    def test_extracts_errors(self, mem: PersistentMemory, sample_events):
        """Error events are extracted as L2 facts."""
        facts = mem.consolidate_l2("coding", "test-001", sample_events)
        assert any("Error" in f.title for f in facts)

    def test_deduplicates(self, mem: PersistentMemory):
        """Duplicate error messages produce one fact."""
        now = datetime.now(UTC).isoformat()
        events = [
            TraceEvent(now, "s1", "error", "Connection refused", "", 10),
            TraceEvent(now, "s1", "error", "Connection refused", "", 10),
        ]
        facts = mem.consolidate_l2("coding", "s1", events)
        # Only one fact because dedup key is same
        assert len(facts) == 1

    def test_skips_thinking(self, mem: PersistentMemory, sample_events):
        """Thinking events don't become L2 facts."""
        facts = mem.consolidate_l2("coding", "test-001", sample_events)
        thinking_facts = [f for f in facts if "thinking" in f.title.lower()]
        assert len(thinking_facts) == 0

    def test_empty_events(self, mem: PersistentMemory):
        """No events produces no facts."""
        facts = mem.consolidate_l2("coding", "test-001", [])
        assert facts == []


# ═══════════════════════════════════════════════════════════
# Stats & Summary
# ═══════════════════════════════════════════════════════════


class TestStats:
    def test_stats_initial(self, mem: PersistentMemory):
        """Initial stats are all zeros."""
        stats = mem.stats()
        assert stats.l1_files == 0
        assert stats.l1_events == 0
        assert stats.l2_facts == 0
        assert stats.l3_files == 0
        assert stats.total_sessions == 0

    def test_stats_after_writes(self, mem: PersistentMemory, sample_events):
        """Stats reflect written data."""
        mem.write_l1_trace("test-001", sample_events)
        facts = mem.consolidate_l2("coding", "test-001", sample_events)
        mem.write_l2_facts("coding", facts)
        mem.write_l3_profile("Test profile.")

        stats = mem.stats()
        assert stats.l1_files >= 1
        assert stats.l1_events >= 4
        assert stats.l2_facts >= 1
        assert stats.l3_files >= 1
        assert stats.total_sessions >= 1
        assert stats.storage_bytes > 0

    def test_summary_format(self, mem: PersistentMemory, sample_events):
        """Summary contains expected sections."""
        mem.write_l1_trace("test-001", sample_events)
        summary = mem.summary()
        assert "Persistent Memory" in summary
        assert "L1" in summary
        assert "L3" in summary


# ═══════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_large_content(self, mem: PersistentMemory):
        """Very long event content is truncated at 2000 chars."""
        now = datetime.now(UTC).isoformat()
        long_content = "x" * 5000
        events = [TraceEvent(now, "s1", "tool_call", long_content, "tool", 100)]
        mem.write_l1_trace("big-session", events)

        read = mem.read_l1_events(session_id="big-session")
        assert len(read) == 1
        assert len(read[0]["content"]) == 2000  # Truncated

    def test_special_chars_in_facts(self, mem: PersistentMemory):
        """Facts with special characters are handled."""
        fact = L2Fact(
            surface="coding",
            title="Unicode: ñ, é, 中文",
            body="Special chars: 💡 → idea, ✓ → check",
            source_session="s1",
            source_timestamp="ts",
            tags=["unicode"],
        )
        mem.write_l2_facts("coding", [fact])
        facts = mem.read_l2_facts("coding")
        assert "Unicode" in facts[0]["title"]

    def test_concurrent_writes(self, mem: PersistentMemory):
        """Multiple sessions can write to the same daily file."""
        now = datetime.now(UTC).isoformat()
        mem.write_l1_trace("s1", [
            TraceEvent(now, "s1", "tool_call", "Session 1", "tool", 10),
        ])
        mem.write_l1_trace("s2", [
            TraceEvent(now, "s2", "tool_call", "Session 2", "tool", 10),
        ])

        events = mem.read_l1_events()
        assert len(events) == 2

    def test_corrupt_json_line(self, mem: PersistentMemory):
        """Corrupt lines in JSONL file are skipped."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        path = Path(mem.stats().memory_dir) / "l1" / f"{today}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write one good line and one bad
        with open(path, "w") as f:
            f.write('{"valid": true}\n')
            f.write("not json\n")

        events = mem.read_l1_events()
        assert len(events) == 1
        assert events[0]["valid"] is True


# ═══════════════════════════════════════════════════════════
# L1Trace dataclass
# ═══════════════════════════════════════════════════════════


class TestL1Trace:
    def test_add_event(self):
        """add_event increments token count."""
        trace = L1Trace(session_id="s1", surface="coding")
        trace.add_event(TraceEvent("ts", "s1", "tool_call", "content", "tool", 50))
        trace.add_event(TraceEvent("ts", "s1", "error", "err", "", 20))
        assert len(trace.events) == 2
        assert trace.total_tokens == 70


# ═══════════════════════════════════════════════════════════
# MemoryStats dataclass
# ═══════════════════════════════════════════════════════════


class TestMemoryStats:
    def test_defaults(self):
        """Default stats are all zeros."""
        stats = MemoryStats()
        assert stats.l1_files == 0
        assert stats.storage_bytes == 0
        assert stats.memory_dir == ""
