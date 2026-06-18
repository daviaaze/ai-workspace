"""Tests for context inspector logic (non-Textual parts)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from ai_workspace.agents.context_manager import (
    ContextManager,
    ContextBlock,
    BlockType,
)
from ai_workspace.tui.v5.context_inspector import (
    _token_bar,
    _status_marker,
    _drift_check,
    _is_stale,
    _format_file_tree,
)


# ---------------------------------------------------------------------------
# _token_bar
# ---------------------------------------------------------------------------


def test_token_bar_empty():
    bar = _token_bar(0, 128_000)
    assert "0/128,000t" in bar
    assert "0%" in bar


def test_token_bar_partial():
    bar = _token_bar(64_000, 128_000)
    assert "64,000" in bar
    assert "50%" in bar


def test_token_bar_near_full():
    bar = _token_bar(120_000, 128_000)
    assert "94%" in bar


def test_token_bar_over_capacity():
    bar = _token_bar(150_000, 128_000)
    assert "100%" in bar  # Clamped at 100%


# ---------------------------------------------------------------------------
# _status_marker
# ---------------------------------------------------------------------------


def test_status_marker_pinned():
    block = ContextBlock(block_id="1", block_type=BlockType.FILE_READ, content="x", pinned=True)
    marker = _status_marker(block)
    assert "P" in marker


def test_status_marker_excluded():
    block = ContextBlock(block_id="1", block_type=BlockType.FILE_READ, content="x", excluded=True)
    marker = _status_marker(block)
    assert "X" in marker


def test_status_marker_stale():
    block = ContextBlock(block_id="1", block_type=BlockType.COMPACTION, content="summary")
    marker = _status_marker(block)
    assert "S" in marker


def test_status_marker_ok():
    block = ContextBlock(block_id="1", block_type=BlockType.FILE_READ, content="x")
    marker = _status_marker(block)
    assert "*" in marker


# ---------------------------------------------------------------------------
# _is_stale
# ---------------------------------------------------------------------------


def test_is_stale_compaction_block():
    block = ContextBlock(block_id="1", block_type=BlockType.COMPACTION, content="summary")
    assert _is_stale(block) is True


def test_is_stale_file_block():
    block = ContextBlock(block_id="1", block_type=BlockType.FILE_READ, content="code")
    assert _is_stale(block) is False


# ---------------------------------------------------------------------------
# _drift_check
# ---------------------------------------------------------------------------


def test_drift_check_no_file():
    block = ContextBlock(block_id="1", block_type=BlockType.FILE_READ, content="x")
    assert _drift_check(block) is False


def test_drift_check_file_drifted(tmp_path: Path):
    f = tmp_path / "test.py"
    f.write_text("original content")

    block = ContextBlock(
        block_id="1",
        block_type=BlockType.FILE_READ,
        content="original content",
        file_path=str(f),
    )
    assert _drift_check(block) is False  # Same content

    # Change file on disk
    f.write_text("modified content")
    assert _drift_check(block) is True  # Drifted!


def test_drift_check_file_unchanged(tmp_path: Path):
    f = tmp_path / "test.py"
    f.write_text("hello world")

    block = ContextBlock(
        block_id="1",
        block_type=BlockType.FILE_READ,
        content="hello world",
        file_path=str(f),
    )
    assert _drift_check(block) is False


# ---------------------------------------------------------------------------
# _format_file_tree
# ---------------------------------------------------------------------------


def test_format_file_tree_empty():
    result = _format_file_tree([])
    assert "no files" in result.lower() or "no blocks" in result.lower()


def test_format_file_tree_with_files():
    blocks = [
        ContextBlock(block_id="1", block_type=BlockType.FILE_READ, content="x" * 100, file_path="src/auth.py"),
        ContextBlock(block_id="2", block_type=BlockType.FILE_READ, content="y" * 200, file_path="src/router.py"),
        ContextBlock(block_id="3", block_type=BlockType.FILE_READ, content="z" * 50, file_path="docs/readme.md"),
    ]
    # Refresh token estimates
    for b in blocks:
        b.refresh_tokens()

    tree = _format_file_tree(blocks)
    assert "src/" in tree
    assert "docs/" in tree
    assert "auth.py" in tree
    assert "router.py" in tree
    assert "readme.md" in tree


def test_format_file_tree_shows_tokens():
    blocks = [
        ContextBlock(block_id="1", block_type=BlockType.FILE_READ, content="x" * 400, file_path="src/big.py"),
    ]
    blocks[0].refresh_tokens()
    tree = _format_file_tree(blocks)
    # Should show token count
    assert "100t" in tree or "t" in tree.split()[-1]


def test_format_file_tree_no_files():
    """Blocks without file_path are shown with summary."""
    blocks = [
        ContextBlock(block_id="1", block_type=BlockType.TOOL_RESULT, content="result data", summary="grep result"),
    ]
    tree = _format_file_tree(blocks)
    assert "grep result" in tree


# ---------------------------------------------------------------------------
# ContextManager integration
# ---------------------------------------------------------------------------


def test_context_manager_basic():
    cm = ContextManager()
    cm.add_block(BlockType.FILE_READ, "def foo(): pass", file_path="src/foo.py")
    stats = cm.stats()
    assert stats["total_blocks"] == 1
    assert stats["total_tokens"] > 0


def test_context_manager_pin_exclude():
    cm = ContextManager()
    bid = cm.add_block(BlockType.FILE_READ, "important", importance=0.9)
    cm.pin_block(bid)
    assert cm.get_block(bid).pinned is True

    cm.unpin_block(bid)
    cm.exclude_block(bid)
    assert cm.get_block(bid).excluded is True


def test_context_manager_toggle():
    cm = ContextManager()
    bid = cm.add_block(BlockType.FILE_READ, "toggle test")
    assert cm.toggle_pin(bid) == "pinned"
    assert cm.toggle_pin(bid) == "unpinned"
    assert cm.toggle_exclude(bid) == "excluded"
    assert cm.toggle_exclude(bid) == "included"


def test_context_manager_snapshots():
    cm = ContextManager()
    cm.add_block(BlockType.FILE_READ, "block A", file_path="a.py")
    cm.add_block(BlockType.FILE_READ, "block B", file_path="b.py")

    sid = cm.save_snapshot("my snapshot")
    snapshots = cm.list_snapshots()
    assert len(snapshots) == 1

    # Modify after snapshot
    cm.add_block(BlockType.FILE_READ, "block C", file_path="c.py")
    assert cm.stats()["total_blocks"] == 3

    # Restore snapshot
    assert cm.load_snapshot(sid) is True
    assert cm.stats()["total_blocks"] == 2


def test_context_manager_budget_status():
    cm = ContextManager(context_window_tokens=1000)
    # Add a large block
    cm.add_block(BlockType.FILE_READ, "x" * 4000)  # ~1000 tokens
    bar = cm.get_budget_bar(width=20)
    assert "1000" in bar or "1,000" in bar
    assert "%" in bar


def test_context_manager_format_for_injection():
    cm = ContextManager()
    cm.add_block(BlockType.USER_MESSAGE, "Hello")
    cm.add_block(BlockType.TOOL_RESULT, "result", tool_name="read_file")
    formatted = cm.format_for_injection()
    assert "<context_window" in formatted
    assert "user message" in formatted.lower()
    assert "tool result" in formatted.lower() or "tool_result" in formatted.lower()
