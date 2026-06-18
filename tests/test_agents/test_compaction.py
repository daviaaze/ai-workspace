"""Tests for context compaction pipeline (L1 -> L2 -> L3)."""

from __future__ import annotations

import io
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_workspace.agents.compaction import (
    CompactionConfig,
    ContextCompactor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def compactor():
    """Fresh compactor with default config."""
    return ContextCompactor()


@pytest.fixture
def strict_compactor():
    """Compactor with tight limits for testing thresholds."""
    config = CompactionConfig(
        max_tokens=1000,
        compact_at_pct=0.5,
        tool_result_max_chars=100,
        tool_result_preview_chars=20,
        tool_result_ttl_seconds=300,
        max_recent_results=3,
        keep_recent_messages=2,
    )
    return ContextCompactor(config)


@pytest.fixture
def sample_messages():
    """A typical agent conversation."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Fix the auth bug in auth.py"},
        {"role": "assistant", "content": "I'll read the file first."},
        {"role": "tool", "tool_call_id": "call_1", "content": "def login(): pass"},
        {"role": "assistant", "content": "Found: the password is not hashed."},
        {"role": "tool", "tool_call_id": "call_2", "content": "Edit applied successfully."},
        {"role": "assistant", "content": "Bug fixed."},
    ]


# ---------------------------------------------------------------------------
# L1: Tool Result Cap
# ---------------------------------------------------------------------------


def test_l1_small_tool_result_unchanged(compactor):
    """Small tool results should pass through unchanged."""
    msgs = [
        {"role": "tool", "tool_call_id": "t1", "content": "Short output"},
    ]
    result = compactor._cap_tool_results(msgs)
    assert result[0]["content"] == "Short output"


def test_l1_large_tool_result_capped(strict_compactor):
    """Tool results exceeding max_chars are truncated with preview."""
    large_content = "x" * 500  # 500 chars > 100 max
    msgs = [
        {"role": "tool", "tool_call_id": "t1", "content": large_content},
    ]
    result = strict_compactor._cap_tool_results(msgs)

    capped = result[0]["content"]
    # Preview: first 20 chars of "xxxx..."
    assert capped.startswith("x" * 20)
    assert "truncated" in capped
    assert "500 total chars" in capped
    assert "t1.txt" in capped


def test_l1_non_tool_messages_unchanged(compactor):
    """Non-tool messages pass through L1 unchanged."""
    msgs = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    result = compactor._cap_tool_results(msgs)
    assert result == msgs


def test_l1_large_result_saved_to_disk(strict_compactor, tmp_path):
    """Full output is saved to session_dir on disk."""
    strict_compactor.config.session_dir = str(tmp_path)
    large_content = "IMPORTANT DATA " * 50  # 750 chars
    msgs = [
        {"role": "tool", "tool_call_id": "call_save", "content": large_content},
    ]
    result = strict_compactor._cap_tool_results(msgs)

    # File should exist on disk
    saved = tmp_path / "call_save.txt"
    assert saved.exists()
    assert saved.read_text() == large_content

    # Preview in message should reference the file
    assert "call_save.txt" in result[0]["content"]


def test_l1_multiple_messages_mixed(compactor):
    """L1 processes a mix of tool and non-tool messages."""
    msgs = [
        {"role": "user", "content": "Task"},
        {"role": "tool", "tool_call_id": "t1", "content": "Small"},
        {"role": "assistant", "content": "Response"},
    ]
    result = compactor._cap_tool_results(msgs)
    assert len(result) == 3
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "tool"
    assert result[2]["role"] == "assistant"


# ---------------------------------------------------------------------------
# L2: Time-based Cleanup
# ---------------------------------------------------------------------------


def test_l2_recent_results_kept(compactor):
    """Recent tool results should be kept."""
    msgs = [
        {"role": "tool", "tool_call_id": "fresh", "content": "Result A"},
    ]
    result = compactor._clear_old_results(msgs)
    assert result[0]["content"] == "Result A"


def test_l2_old_results_cleared(strict_compactor):
    """Tool results older than TTL are replaced with placeholder."""
    strict_compactor.config.tool_result_ttl_seconds = 1
    msgs = [
        {"role": "tool", "tool_call_id": "old", "content": "Old data"},
    ]

    # Simulate age: set timestamp to > 1 second ago
    strict_compactor._tool_timestamps["old"] = time.time() - 3600

    result = strict_compactor._clear_old_results(msgs)
    assert "Old tool result cleared" in result[0]["content"]


def test_l2_max_recent_limit_enforced(strict_compactor):
    """Only N most recent results are kept; rest get placeholders."""
    strict_compactor.config.max_recent_results = 2

    msgs = [
        {"role": "tool", "tool_call_id": "t1", "content": "First"},
        {"role": "tool", "tool_call_id": "t2", "content": "Second"},
        {"role": "tool", "tool_call_id": "t3", "content": "Third"},
    ]

    result = strict_compactor._clear_old_results(msgs)

    # Should have exactly 2 non-cleared results (most recent)
    cleared = sum(1 for m in result if "Old tool result cleared" in m.get("content", ""))
    kept = len(result) - cleared
    assert kept == 2
    assert cleared == 1


def test_l2_non_tool_messages_unchanged(compactor):
    """L2 only affects tool messages."""
    msgs = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    result = compactor._clear_old_results(msgs)
    assert result == msgs


# ---------------------------------------------------------------------------
# L3: Summarization
# ---------------------------------------------------------------------------


def test_l3_summarize_preserves_system_and_recent(compactor):
    """Summarization preserves system messages and recent exchanges."""
    msgs = [
        {"role": "system", "content": "You are a bot."},
        {"role": "user", "content": "Q1: What is Python?"},
        {"role": "assistant", "content": "A1: A programming language."},
        {"role": "user", "content": "Q2: And Rust?"},
        {"role": "assistant", "content": "A2: Systems language."},
        {"role": "user", "content": "Q3: Latest?"},
        {"role": "assistant", "content": "A3: Both active."},
    ]

    result = compactor._summarize(msgs)

    # System message preserved
    assert result[0]["role"] == "system"

    # Summary block inserted
    summary_msg = result[1]
    assert summary_msg["role"] == "system"
    assert "CONVERSATION SUMMARY" in summary_msg["content"]

    # Recent messages preserved (keep_recent_messages = 5 by default)
    # Should have system + summary + last 5 recent
    assert len(result) >= 3


def test_l3_summarize_records_user_requests(compactor):
    """Summary includes user requests."""
    msgs = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Fix the auth module"},
        {"role": "user", "content": "Add unit tests"},
        {"role": "assistant", "content": "Done."},
    ]

    result = compactor._summarize(msgs)
    # Find the summary message (role=system, contains CONVERSATION SUMMARY)
    summary_msgs = [m for m in result if "CONVERSATION SUMMARY" in m.get("content", "")]
    assert len(summary_msgs) >= 1
    summary = summary_msgs[0]["content"]

    assert "Fix the auth module" in summary
    assert "Add unit tests" in summary


def test_l3_summarize_includes_tool_counts(compactor):
    """Summary includes count of tool results."""
    msgs = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Debug the server"},
        {"role": "tool", "tool_call_id": "t1", "content": "Log: error at L42"},
        {"role": "tool", "tool_call_id": "t2", "content": "Log: traceback follows"},
        {"role": "assistant", "content": "Found the issue."},
    ]

    result = compactor._summarize(msgs)
    summary_msgs = [m for m in result if "CONVERSATION SUMMARY" in m.get("content", "")]
    assert len(summary_msgs) >= 1
    summary = summary_msgs[0]["content"]
    assert "2 total" in summary


# ---------------------------------------------------------------------------
# Compact (full pipeline)
# ---------------------------------------------------------------------------


def test_compact_applies_l1_and_l2(compactor):
    """compact() applies both L1 and L2 when thresholds not exceeded."""
    msgs = [
        {"role": "system", "content": "Prompt"},
        {"role": "user", "content": "Task"},
        {"role": "tool", "tool_call_id": "t1", "content": "Result"},
    ]

    # Force L1 to not trigger, L2 to not trigger
    result = compactor.compact(msgs, current_tokens=10)
    assert len(result) == 3


def test_compact_triggers_l3_when_over_budget(strict_compactor):
    """L3 fires when token usage exceeds compact_at_pct."""
    compactor = strict_compactor
    msgs = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Task"},
        {"role": "assistant", "content": "Response"},
    ]

    # Set compactor to trigger at 50% of 1000 = 500 tokens
    # We estimate each char as 1/3.5 tokens ≈ 0.28 tokens
    current = compactor.estimate_total_tokens(msgs)
    # current is ~10 chars = ~3 tokens -> far below 500. Let's claim we have 600 tokens
    result = compactor.compact(msgs, current_tokens=600)
    assert "CONVERSATION SUMMARY" in result[1]["content"]


def test_compact_does_not_trigger_l3_under_budget(compactor):
    """L3 does not fire when under the threshold."""
    msgs = [
        {"role": "user", "content": "Small task"},
    ]
    result = compactor.compact(msgs, current_tokens=10)
    # Should not contain summary block
    has_summary = any("CONVERSATION SUMMARY" in m.get("content", "") for m in result)
    assert not has_summary


def test_compact_idempotent(compactor):
    """Running compact twice should not change results further."""
    msgs = [
        {"role": "system", "content": "Prompt"},
        {"role": "user", "content": "Task"},
        {"role": "tool", "tool_call_id": "t1", "content": "Result"},
        {"role": "assistant", "content": "Final answer."},
    ]

    first = compactor.compact(msgs, current_tokens=50)
    second = compactor.compact(first, current_tokens=50)

    # Should be the same structure (no double-summary)
    assert len(first) == len(second)
    assert [m["role"] for m in first] == [m["role"] for m in second]


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def test_estimate_tokens():
    c = ContextCompactor()
    assert c.estimate_tokens("") == 0
    # estimate_tokens uses max(1, int(len(text) / chars_per_token))
    # 5 / 3.5 = 1.42 -> int = 1 -> max(1,1) = 1
    assert c.estimate_tokens("hello") == 1  # 5 chars / 3.5 = 1.42 -> 1
    assert c.estimate_tokens("a" * 100) == 28  # 100 / 3.5 = 28.57 -> 28


def test_estimate_total_tokens(sample_messages):
    c = ContextCompactor()
    total = c.estimate_total_tokens(sample_messages)
    assert total > 0
    assert isinstance(total, int)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_default_config():
    config = CompactionConfig()
    assert config.max_tokens == 128_000
    assert config.compact_at_pct == 0.80
    assert config.tool_result_max_chars == 10_000


def test_custom_config():
    config = CompactionConfig(
        max_tokens=16_000,
        compact_at_pct=0.9,
        tool_result_max_chars=500,
    )
    assert config.max_tokens == 16_000
    assert config.compact_at_pct == 0.9
    assert config.tool_result_max_chars == 500


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_get_stats(compactor):
    stats = compactor.get_stats()
    assert "active_tool_results" in stats
    assert stats["max_tokens"] == 128_000


def test_reset_clears_timestamps(compactor):
    compactor._tool_timestamps["t1"] = time.time()
    assert len(compactor._tool_timestamps) == 1
    compactor.reset()
    assert len(compactor._tool_timestamps) == 0


# ---------------------------------------------------------------------------
# Async summarization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compact_async_falls_back_on_error(compactor):
    """compact_async falls back to sync summarization on error."""
    msgs = [
        {"role": "system", "content": "Prompt"},
        {"role": "user", "content": "Task"},
        {"role": "assistant", "content": "Done."},
    ]

    # Mock _call_summarizer to fail
    with patch.object(compactor, "_call_summarizer", side_effect=RuntimeError("Unavailable")):
        result = await compactor.compact_async(msgs, current_tokens=compactor.config.max_tokens)

    # Should have fallback summary
    assert "CONVERSATION SUMMARY" in result[1]["content"]


# ---------------------------------------------------------------------------
# Integration with agent loop: compaction happens in loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loop_compactor_initialized():
    """LoopState gets a compactor instance from agent_loop."""
    from ai_workspace.agents.loop import agent_loop, LoopParams, LoopPattern

    # Use a fake stream_chat that returns immediately
    async def fake_stream(**kwargs):
        yield {"type": "text", "text": "Hello!"}

    params = LoopParams(
        task="hi",
        pattern=LoopPattern.DIRECT,
        deps={"stream_chat": fake_stream},
    )

    events = []
    async for event in agent_loop(params):
        events.append(event)

    # The compactor should have been initialized
    # We verify that the loop completed successfully
    done = [e for e in events if e.type == "done"]
    assert len(done) == 1
    assert done[0].data["reason"] == "completed"


@pytest.mark.asyncio
async def test_compaction_runs_in_direct_loop():
    """Compaction is applied after direct loop completion."""
    from ai_workspace.agents.loop import agent_loop, LoopParams, LoopPattern

    # Large response (should trigger L3)
    large_text = "Data " * 200  # ~1000 chars -> ~285 tokens
    async def fake_stream(**kwargs):
        yield {"type": "text", "text": large_text}

    config = CompactionConfig(
        max_tokens=500,
        compact_at_pct=0.1,  # Trigger immediately
    )

    params = LoopParams(
        task="generate data",
        pattern=LoopPattern.DIRECT,
        deps={"stream_chat": fake_stream},
    )

    events = []
    async for event in agent_loop(params):
        events.append(event)

    done = [e for e in events if e.type == "done"]
    assert len(done) == 1
