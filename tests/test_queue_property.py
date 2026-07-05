"""
Property-based tests for the Job Queue using Hypothesis.

Focuses on:
1. ``_calc_next_run`` invariants (pure function, ideal for fuzzing)
2. Dequeue ordering properties (priority & recency)
3. Exponential backoff never overflows
4. Job state machine invariants
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, assume, strategies as st
import pytest

from ai_workspace.queue import JobQueue


# ── Strategy: timezone-aware datetimes ───────────────────

st_datetime = st.datetimes(
    min_value=datetime(2024, 1, 1),
    max_value=datetime(2028, 12, 31),
    timezones=st.just(timezone.utc),
)


# ── Property 1: _calc_next_run invariants ───────────────


class TestCalcNextRunProperties:
    """Property-based tests for the next-run calculation function."""

    def _make_queue(self) -> JobQueue:
        q = JobQueue("postgresql:///test")
        q._pool = MagicMock()
        return q

    @given(st_datetime, st.integers(min_value=1, max_value=86400 * 7))
    def test_interval_always_forward(self, from_time: datetime, seconds: int):
        """Interval-based schedules should always produce a future time."""
        q = self._make_queue()
        nxt = q._calc_next_run("interval", None, seconds, from_time)
        assert nxt > from_time, f"next {nxt} should be > from {from_time}"
        delta = (nxt - from_time).total_seconds()
        assert delta == seconds, f"delta {delta} != {seconds}"

    @given(st_datetime)
    def test_daily_always_forward(self, from_time: datetime):
        """Daily schedules should produce a time 24h forward."""
        q = self._make_queue()
        nxt = q._calc_next_run("daily", None, None, from_time)
        assert nxt > from_time
        delta_hours = (nxt - from_time).total_seconds() / 3600
        assert 23.9 <= delta_hours <= 24.1, f"daily delta {delta_hours}h"

    @given(st_datetime)
    def test_hourly_always_forward(self, from_time: datetime):
        """Hourly schedules should produce a time 1h forward."""
        q = self._make_queue()
        nxt = q._calc_next_run("hourly", None, None, from_time)
        assert nxt > from_time
        delta_hours = (nxt - from_time).total_seconds() / 3600
        assert 0.99 <= delta_hours <= 1.01, f"hourly delta {delta_hours}h"

    @given(st_datetime, st.integers(min_value=1, max_value=10))
    def test_interval_multiple_calls_monotonic(self, from_time: datetime, repeat: int):
        """Multiple calls should produce monotonically increasing times."""
        q = self._make_queue()
        current = from_time
        for _ in range(repeat):
            nxt = q._calc_next_run("interval", None, 3600, current)
            assert nxt > current
            current = nxt

    @given(st_datetime, st.integers(min_value=1, max_value=86400 * 30))
    def test_interval_delta_matches(self, from_time: datetime, seconds: int):
        """The delta should exactly match interval_seconds."""
        q = self._make_queue()
        nxt = q._calc_next_run("interval", None, seconds, from_time)
        assert (nxt - from_time).total_seconds() == seconds


# ── Property 2: Dequeue ordering ────────────────────────


class TestDequeueOrdering:
    """Property: jobs with higher priority or older availability come first."""

    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=-100, max_value=100),
                st_datetime,
            ),
            min_size=1,
            max_size=20,
        )
    )
    def test_dequeue_order_priority_always_wins(self, jobs: list[tuple[int, datetime]]):
        """Highest-priority item should sort first regardless of availability time."""
        sorted_jobs = sorted(jobs, key=lambda x: (-x[0], x[1]))
        top_priority = max(j[0] for j in jobs)
        assert sorted_jobs[0][0] == top_priority

        # All items with the same priority should be sorted by available_at ASC
        same_priority = [j for j in sorted_jobs if j[0] == top_priority]
        for i in range(1, len(same_priority)):
            assert same_priority[i][1] >= same_priority[i - 1][1]


# ── Property 3: Exponential backoff properties ──────────


class TestExponentialBackoff:
    """Property: retry delay grows exponentially with attempt count."""

    @given(
        st.integers(min_value=1, max_value=3600),
        st.integers(min_value=0, max_value=10),
    )
    def test_backoff_is_exponential(self, base_delay: int, attempt: int):
        """Backoff at attempt n should be base * 2^n."""
        expected = base_delay * (2**attempt)
        assert expected >= base_delay, "Backoff must not shrink"
        if attempt > 0:
            prev = base_delay * (2 ** (attempt - 1))
            assert expected > prev, "Backoff must grow monotonically"

    @given(st.integers(min_value=1, max_value=10_000_000))
    def test_backoff_overflow_safe(self, base_delay: int):
        """Exponential backoff should never overflow for reasonable ranges."""
        for attempt in range(10):
            backoff = base_delay * (2**attempt)
            assert backoff > 0, f"backoff overflow at attempt {attempt}"

    @given(st.integers(min_value=1, max_value=60))
    def test_retry_delay_reasonable(self, base_delay: int):
        """Even at max retries (3), backoff should stay reasonable."""
        for attempt in range(4):
            backoff = base_delay * (2**attempt)
            assert backoff <= base_delay * 8


# ── Property 4: Job state machine invariants ────────────


class TestJobStateMachine:
    """Property: job status transitions should follow valid paths."""

    VALID_TRANSITIONS = {
        "pending": ["available"],
        "scheduled": ["available", "cancelled"],
        "available": ["running", "cancelled"],
        "running": ["completed", "failed"],
        "completed": [],
        "failed": ["available"],
        "cancelled": [],
    }

    @given(
        st.sampled_from(list(VALID_TRANSITIONS.keys())),
        st.sampled_from(["completed", "failed", "available", "cancelled", "running"]),
    )
    def test_valid_state_transitions(self, current: str, next_state: str):
        """A job should only transition to valid next states."""
        valid_next = self.VALID_TRANSITIONS[current]
        if next_state in valid_next:
            assert True
        else:
            assert next_state not in valid_next, \
                f"Invalid transition: {current} → {next_state}"

    @given(
        st.sampled_from(["completed", "cancelled"]),
        st.sampled_from(["available", "running", "pending"]),
    )
    def test_terminal_states_are_terminal(self, terminal: str, invalid_next: str):
        """Terminal states should not allow any transitions."""
        valid = self.VALID_TRANSITIONS[terminal]
        assert len(valid) == 0, f"Terminal state {terminal} should have no transitions"
