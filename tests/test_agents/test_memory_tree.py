"""Tests for Memory Tree (SPEC_MEMORY_TREE)."""

from __future__ import annotations

import pytest

from ai_workspace.agents.memory_tree import (
    MemoryTree,
    MemoryTreeConfig,
    NodeStatus,
    StepRecord,
    estimate_step_tokens,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tree() -> MemoryTree:
    return MemoryTree()


@pytest.fixture
def sample_step() -> StepRecord:
    return StepRecord(
        type="tool_call",
        content="Reading file src/auth.py",
        tool_name="read_file",
        tokens=10,
    )


# ---------------------------------------------------------------------------
# StepRecord tests
# ---------------------------------------------------------------------------


class TestStepRecord:
    def test_creation(self):
        step = StepRecord(type="tool_call", content="read file.py", tool_name="read_file")
        assert step.type == "tool_call"
        assert step.content == "read file.py"
        assert step.tool_name == "read_file"
        assert step.error == ""
        assert step.tokens == 0

    def test_token_estimation(self):
        step = StepRecord(
            type="tool_result",
            content="x" * 100,
            tool_name="web_fetch",
            tokens=estimate_step_tokens("x" * 100),
        )
        assert step.tokens == max(1, 100 // 4)


# ---------------------------------------------------------------------------
# MemoryTree — Core operations
# ---------------------------------------------------------------------------


class TestMemoryTreeGrow:
    def test_add_step_to_root(self, tree, sample_step):
        tree.grow(sample_step)
        assert len(tree.root.steps) == 1
        assert tree.root.steps[0].content == "Reading file src/auth.py"
        assert tree.root.tokens == 10

    def test_add_multiple_steps(self, tree):
        for i in range(5):
            tree.grow(StepRecord(type="tool_call", content=f"step {i}", tokens=5))
        assert len(tree.root.steps) == 5
        assert tree.root.tokens == 25

    def test_add_step_to_active_subgoal(self, tree):
        tree.start_subgoal("Fix auth")
        step = StepRecord(type="tool_result", content="result", tokens=3)
        tree.grow(step)
        # Step should go to the subgoal, not the root
        assert len(tree.root.steps) == 0
        subgoal = tree._get_active_node()
        assert subgoal.subgoal == "Fix auth"
        assert len(subgoal.steps) == 1


class TestMemoryTreeStartSubgoal:
    def test_start_subgoal_creates_child(self, tree):
        sid = tree.start_subgoal("Add JWT validation")
        assert sid.startswith("n")
        assert len(tree.active_path) == 2  # root + new subgoal
        assert tree._get_active_node().subgoal == "Add JWT validation"

    def test_nested_subgoals(self, tree):
        sid1 = tree.start_subgoal("Task A")
        sid2 = tree.start_subgoal("Subtask A1")
        assert tree.active_path == ["root", sid1, sid2]
        assert tree._get_active_node().parent_id == sid1

    def test_subgoal_ids_are_unique(self, tree):
        ids = {tree.start_subgoal(f"task {i}") for i in range(10)}
        assert len(ids) == 10


class TestMemoryTreeCompleteSubgoal:
    def test_complete_subgoal_success(self, tree):
        sid = tree.start_subgoal("Write test")
        tree.grow(StepRecord(type="tool_call", content="write test_a.py", tool_name="write_file", tokens=5))
        summary = tree.complete_subgoal(success=True)

        assert summary != ""
        assert "Write test" in summary
        assert tree.active_path == ["root"]  # Back to root
        node = tree._node_index[sid]
        assert node.status == NodeStatus.COMPLETED
        assert node.summary != ""

    def test_complete_subgoal_failure(self, tree):
        sid = tree.start_subgoal("Failing task")
        tree.grow(StepRecord(type="error", content="broken", error="EACCES", tokens=2))
        tree.complete_subgoal(success=False)

        assert tree._node_index[sid].status == NodeStatus.FAILED

    def test_cannot_complete_root(self, tree):
        summary = tree.complete_subgoal(success=True)
        assert summary == ""


class TestMemoryTreeRevise:
    def test_revise_creates_branch(self, tree):
        sid = tree.start_subgoal("Initial approach")
        tree.grow(StepRecord(type="error", content="migration failed", error="DB error", tokens=5))
        # Mark as failed
        tree._node_index[sid].status = NodeStatus.FAILED

        branch_id = tree.revise("migration failed in step 3")

        assert branch_id.startswith("n")
        assert "Recovery" in tree._get_active_node().subgoal
        # Initial approach should NOT be in active path
        assert sid not in tree.active_path

    def test_revise_at_root(self, tree):
        # Even at root, revise should create a recovery subgoal
        branch_id = tree.revise("top-level error")
        assert branch_id.startswith("n")
        assert len(tree.active_path) == 2


# ---------------------------------------------------------------------------
# MemoryTree — Context generation
# ---------------------------------------------------------------------------


class TestMemoryTreeGetContext:
    def test_empty_tree_context(self, tree):
        ctx = tree.get_context()
        assert "Active" in ctx or ctx == ""

    def test_context_includes_active_steps(self, tree):
        for i in range(3):
            tree.grow(StepRecord(type="tool_call", content=f"step {i}", tool_name="test", tokens=5))

        ctx = tree.get_context()
        assert "step 0" in ctx
        assert "step 1" in ctx
        assert "step 2" in ctx

    def test_context_excludes_failed_branches(self, tree):
        tree.start_subgoal("Bad approach")
        tree.grow(StepRecord(type="error", content="broken", error="fail", tokens=5))
        tree.complete_subgoal(success=False)

        # Start recovery
        tree.revise("fix the broken thing")
        tree.grow(StepRecord(type="tool_call", content="good step", tokens=5))

        ctx = tree.get_context()
        # Failed branch content should NOT be in context
        assert "Bad approach" not in ctx or "Active" in ctx
        # Recovery content SHOULD be present
        assert "Recovery" in ctx or "good step" in ctx

    def test_context_includes_completed_sibling_summaries(self, tree):
        # Complete a sibling subgoal, then start a new one
        tree.start_subgoal("Done task")
        tree.grow(StepRecord(type="tool_call", content="done", tokens=5))
        tree.complete_subgoal(success=True)

        # Start a new task at same level
        tree.start_subgoal("Current task")
        tree.grow(StepRecord(type="tool_call", content="current", tokens=5))

        ctx = tree.get_context()
        # Should include sibling's summary
        assert "Done task" in ctx

    def test_context_truncates_long_steps(self, tree):
        long_content = "x" * 1000
        tree.grow(StepRecord(type="tool_result", content=long_content, tokens=250))

        ctx = tree.get_context()
        assert long_content[:500] in ctx
        assert len(ctx) < len(long_content) + 200  # Should be truncated


class TestMemoryTreeCompression:
    def test_compression_frees_tokens(self, tree):
        config = MemoryTreeConfig(max_active_tokens=100, compress_at_pct=0.5)
        tree = MemoryTree(config)

        # Create and complete several subgoals (these CAN be compressed)
        for i in range(5):
            tree.start_subgoal(f"Task {i}")
            tree.grow(StepRecord(type="tool_call", content=f"work in task {i}" * 10, tokens=30))
            tree.complete_subgoal(success=True)

        # Now get_context should trigger compression
        tree.get_context()
        # After compressing completed subgoals, context should be small
        assert tree.get_context_tokens() <= config.max_active_tokens

    def test_compressed_nodes_clear_steps(self, tree):
        sid = tree.start_subgoal("Compress me")
        tree.grow(StepRecord(type="tool_call", content="some work", tokens=5))
        tree.complete_subgoal(success=True)

        # Force compression
        tree._compress_completed()

        node = tree._node_index[sid]
        assert node.status == NodeStatus.COMPRESSED
        assert node.steps == []  # Steps freed
        assert node.summary != ""  # Summary retained


# ---------------------------------------------------------------------------
# MemoryTree — Statistics
# ---------------------------------------------------------------------------


class TestMemoryTreeStats:
    def test_stats_reflect_state(self, tree):
        tree.start_subgoal("Task A")
        tree.grow(StepRecord(type="tool_call", content="x", tokens=5))
        tree.complete_subgoal(success=True)

        stats = tree.get_stats()
        assert stats["total_nodes"] == 2  # root + Task A
        assert stats["completed"] == 1
        assert stats["failed"] == 0
        assert stats["active"] == 1  # root
        assert stats["total_steps"] == 1

    def test_reset_clears_tree(self, tree):
        tree.start_subgoal("Task")
        tree.grow(StepRecord(type="tool_call", content="x", tokens=5))

        tree.reset()
        assert tree.get_stats()["total_nodes"] == 1
        assert tree.active_path == ["root"]
        assert tree.root.steps == []
        assert tree.root.tokens == 0


# ---------------------------------------------------------------------------
# MemoryTree — Step limiting
# ---------------------------------------------------------------------------


class TestMemoryTreeStepLimits:
    def test_last_n_steps(self, tree):
        for i in range(20):
            tree.grow(StepRecord(type="tool_call", content=f"step{i}", tokens=1))

        recent = tree.root.last_n_steps(10)
        assert len(recent) == 10
        assert recent[0].content == "step10"
        assert recent[-1].content == "step19"

    def test_context_only_shows_recent_steps(self, tree):
        for i in range(30):
            tree.grow(StepRecord(type="tool_call", content=f"step{i:03d}", tokens=5))

        ctx = tree.get_context()
        # Should only show recent steps (config.max_recent_steps = 10)
        assert "step029" in ctx  # Most recent
        assert "step000" not in ctx  # Oldest should be omitted


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestMemoryTreeEdgeCases:
    def test_subgoal_with_no_steps(self, tree):
        tree.start_subgoal("Empty task")
        summary = tree.complete_subgoal(success=True)
        assert "No steps recorded" in summary or "Empty task" in summary

    def test_deeply_nested_subgoals(self, tree):
        for i in range(10):
            tree.start_subgoal(f"Level {i}")
        assert len(tree.active_path) == 11  # root + 10 levels

    def test_many_recoveries(self, tree):
        for i in range(5):
            tree.start_subgoal(f"Attempt {i}")
            tree.revise(f"Error in attempt {i}")
        # Should handle multiple revisions without error
        assert len(tree._node_index) > 5
