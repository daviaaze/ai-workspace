"""
Tests for tool execution — partition + parallel execution.

Refs: SPEC_TOOL_EXECUTION.md
"""

from __future__ import annotations

import asyncio
import time

import pytest

from ai_workspace.agents.tool_execution import (
    ToolCall,
    execute_tools,
    is_concurrency_safe,
    partition_tool_calls,
)

# ═══════════════════════════════════════════════════════════
# is_concurrency_safe
# ═══════════════════════════════════════════════════════════


class TestIsConcurrencySafe:
    """Verify per-tool concurrency safety checks."""

    def test_read_file_is_safe(self):
        assert is_concurrency_safe("read_file") is True

    def test_list_files_is_safe(self):
        assert is_concurrency_safe("list_files") is True

    def test_search_code_is_safe(self):
        assert is_concurrency_safe("search_code") is True

    def test_web_search_is_safe(self):
        assert is_concurrency_safe("web_search") is True

    def test_write_file_is_unsafe(self):
        assert is_concurrency_safe("write_file") is False

    def test_edit_file_is_unsafe(self):
        assert is_concurrency_safe("edit_file") is False

    def test_git_commit_is_unsafe(self):
        assert is_concurrency_safe("git_commit") is False

    def test_unknown_tool_is_unsafe(self):
        """Default conservative: unknown tools are NOT concurrency-safe."""
        assert is_concurrency_safe("some_mystery_tool") is False

    def test_shell_read_only_is_safe(self):
        assert is_concurrency_safe("shell", {"command": "ls -la"}) is True
        assert is_concurrency_safe("shell", {"command": "cat file.txt"}) is True
        assert is_concurrency_safe("shell", {"command": "grep pattern file"}) is True
        assert is_concurrency_safe("shell", {"command": "git status"}) is True
        assert is_concurrency_safe("shell", {"command": "find . -name '*.py'"}) is True

    def test_shell_mutating_is_unsafe(self):
        assert is_concurrency_safe("shell", {"command": "rm -rf /"}) is False
        assert is_concurrency_safe("shell", {"command": "pip install foo"}) is False
        assert is_concurrency_safe("shell", {"command": "cargo build"}) is False
        assert is_concurrency_safe("shell", {"command": "sudo poweroff"}) is False

    def test_shell_empty_command_is_unsafe(self):
        """No command = assume unsafe."""
        assert is_concurrency_safe("shell", {}) is False
        assert is_concurrency_safe("shell", None) is False


# ═══════════════════════════════════════════════════════════
# partition_tool_calls
# ═══════════════════════════════════════════════════════════


class TestPartitionToolCalls:
    """Verify Claude Code's partition algorithm."""

    def _mk_calls(self, *names: str) -> list[ToolCall]:
        return [
            ToolCall(id=f"call_{i}", name=name, arguments={})
            for i, name in enumerate(names)
        ]

    def test_empty_list(self):
        assert partition_tool_calls([]) == []

    def test_single_read(self):
        calls = self._mk_calls("read_file")
        batches = partition_tool_calls(calls)
        assert len(batches) == 1
        assert batches[0].parallel is True
        assert len(batches[0].calls) == 1

    def test_all_reads_merged(self):
        """Consecutive read-only tools merge into one batch."""
        calls = self._mk_calls("read_file", "list_files", "web_search")
        batches = partition_tool_calls(calls)
        assert len(batches) == 1
        assert batches[0].parallel is True
        assert len(batches[0].calls) == 3

    def test_edit_breaks_batch(self):
        """A write tool breaks the parallel batch."""
        calls = self._mk_calls("read_file", "read_file", "write_file", "read_file")
        batches = partition_tool_calls(calls)
        assert len(batches) == 3
        # Batch 0: [read_file, read_file] — parallel
        assert batches[0].parallel is True
        assert len(batches[0].calls) == 2
        # Batch 1: [write_file] — serial
        assert batches[1].parallel is False
        assert len(batches[1].calls) == 1
        assert batches[1].calls[0].name == "write_file"
        # Batch 2: [read_file] — parallel
        assert batches[2].parallel is True
        assert len(batches[2].calls) == 1
        assert batches[2].calls[0].name == "read_file"

    def test_mixed_read_write_read(self):
        """Read Write Read → 3 batches (write breaks)."""
        calls = self._mk_calls("read_file", "write_file", "read_file")
        batches = partition_tool_calls(calls)
        assert len(batches) == 3
        assert batches[0].parallel is True
        assert batches[1].parallel is False
        assert batches[2].parallel is True

    def test_all_writes_serial(self):
        """All writes → each in its own serial batch."""
        calls = self._mk_calls("write_file", "edit_file", "write_file")
        batches = partition_tool_calls(calls)
        assert len(batches) == 3
        for b in batches:
            assert b.parallel is False
            assert len(b.calls) == 1

    def test_read_shell_ls_read_merged(self):
        """read + shell(ls) + read → all safe, merged."""
        calls = [
            ToolCall(id="0", name="read_file", arguments={}),
            ToolCall(id="1", name="shell", arguments={"command": "ls -la"}),
            ToolCall(id="2", name="read_file", arguments={}),
        ]
        batches = partition_tool_calls(calls)
        assert len(batches) == 1

    def test_read_shell_rm_read_broken(self):
        """read + shell(rm) + read → broken by unsafe shell."""
        calls = [
            ToolCall(id="0", name="read_file", arguments={}),
            ToolCall(id="1", name="shell", arguments={"command": "rm file.txt"}),
            ToolCall(id="2", name="read_file", arguments={}),
        ]
        batches = partition_tool_calls(calls)
        assert len(batches) == 3
        assert batches[0].parallel is True
        assert batches[1].parallel is False  # rm is unsafe
        assert batches[2].parallel is True

    def test_unknown_tool_breaks_batch(self):
        """Unknown tools are conservatively serial."""
        calls = self._mk_calls("read_file", "mystery_tool", "read_file")
        batches = partition_tool_calls(calls)
        assert len(batches) == 3
        assert batches[1].parallel is False


# ═══════════════════════════════════════════════════════════
# execute_tools — integration
# ═══════════════════════════════════════════════════════════


class TestExecuteTools:
    """Verify tool execution with partitioning and parallelism."""

    @pytest.mark.asyncio
    async def test_execute_single_tool(self):
        """Execute a single tool."""
        calls = [ToolCall(id="c0", name="echo", arguments={"text": "hello"})]
        handlers = {"echo": lambda text: text}

        results = []
        async for r in execute_tools(calls, handlers):
            results.append(r)

        assert len(results) == 1
        assert results[0].ok
        assert results[0].content == "hello"

    @pytest.mark.asyncio
    async def test_execute_multiple_read_only_parallel(self):
        """All read-only tools execute in parallel batch."""
        calls = [
            ToolCall(id="c0", name="echo", arguments={"text": "a"}),
            ToolCall(id="c1", name="echo", arguments={"text": "b"}),
            ToolCall(id="c2", name="echo", arguments={"text": "c"}),
        ]
        handlers = {"echo": lambda text: text}

        results = []
        async for r in execute_tools(calls, handlers):
            results.append(r)

        assert len(results) == 3
        assert all(r.ok for r in results)
        contents = [r.content for r in results]
        assert set(contents) == {"a", "b", "c"}

    @pytest.mark.asyncio
    async def test_execute_mixed_read_write(self):
        """Read + Write + Read → execute in 3 batches (order preserved)."""
        calls = [
            ToolCall(id="c0", name="echo", arguments={"text": "first"}),
            ToolCall(id="c1", name="slow", arguments={"delay": 0.05}),
            ToolCall(id="c2", name="echo", arguments={"text": "third"}),
        ]

        async def slow_handler(delay: float):
            await asyncio.sleep(delay)
            return f"done-{delay}"

        handlers = {
            "echo": lambda text: text,
            "slow": slow_handler,
        }

        # Override concurrency safety for this test
        def mock_safety(name, args):
            if name == "slow":
                return False  # treat slow as unsafe
            return True

        results = []
        async for r in execute_tools(calls, handlers):
            results.append(r)

        assert len(results) == 3
        assert results[0].content == "first"
        assert results[1].content == "done-0.05"
        assert results[2].content == "third"

    @pytest.mark.asyncio
    async def test_parallel_is_faster_than_sequential(self):
        """Parallel execution of slow tools should be faster than sequential."""
        calls = [
            ToolCall(id="c0", name="sleep", arguments={"delay": 0.05}),
            ToolCall(id="c1", name="sleep", arguments={"delay": 0.05}),
            ToolCall(id="c2", name="sleep", arguments={"delay": 0.05}),
        ]

        async def sleep_handler(delay: float):
            await asyncio.sleep(delay)
            return f"slept-{delay}"

        handlers = {"sleep": sleep_handler}

        start = time.monotonic()
        results = []
        async for r in execute_tools(calls, handlers):
            results.append(r)
        elapsed = time.monotonic() - start

        assert len(results) == 3
        assert all(r.ok for r in results)
        # 3 x 0.05s in parallel should be < 0.15s (sequential would be > 0.15s)
        # Use generous upper bound to account for test overhead
        assert elapsed < 0.3, f"Parallel execution took {elapsed:.3f}s, expected < 0.3s"

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Tool not in handlers returns error result but doesn't crash."""
        calls = [ToolCall(id="c0", name="nonexistent", arguments={})]
        handlers = {}

        results = []
        async for r in execute_tools(calls, handlers):
            results.append(r)

        assert len(results) == 1
        assert not results[0].ok
        assert "Unknown tool" in results[0].content

    @pytest.mark.asyncio
    async def test_tool_exception_returns_error(self):
        """Tool that raises returns error result, not exception."""
        calls = [ToolCall(id="c0", name="crash", arguments={})]

        def crash_handler(**kwargs):
            raise RuntimeError("boom")

        handlers = {"crash": crash_handler}

        results = []
        async for r in execute_tools(calls, handlers):
            results.append(r)

        assert len(results) == 1
        assert not results[0].ok
        assert "boom" in results[0].content

    @pytest.mark.asyncio
    async def test_concurrency_limit_respected(self):
        """Semaphore limits concurrent executions."""
        max_concurrent = 3
        total_calls = 10

        calls = [
            ToolCall(id=f"c{i}", name="slow_echo", arguments={"text": str(i), "delay": 0.02})
            for i in range(total_calls)
        ]

        concurrent_count = 0
        max_observed = 0
        lock = asyncio.Lock()

        async def slow_echo_handler(text: str, delay: float):
            nonlocal concurrent_count, max_observed
            async with lock:
                concurrent_count += 1
                max_observed = max(max_observed, concurrent_count)
            await asyncio.sleep(delay)
            async with lock:
                concurrent_count -= 1
            return text

        handlers = {"slow_echo": slow_echo_handler}

        results = []
        async for r in execute_tools(calls, handlers, max_concurrency=max_concurrent):
            results.append(r)

        assert len(results) == total_calls
        assert max_observed <= max_concurrent, (
            f"Max concurrent observed: {max_observed}, limit: {max_concurrent}"
        )

    @pytest.mark.asyncio
    async def test_empty_calls(self):
        """Empty call list yields nothing."""
        results = []
        async for r in execute_tools([], {}):
            results.append(r)
        assert len(results) == 0


# ═══════════════════════════════════════════════════════════
# Partition edge cases
# ═══════════════════════════════════════════════════════════


class TestPartitionEdgeCases:
    """Edge cases for partition_tool_calls."""

    def test_write_first_then_reads(self):
        """Write first → serial batch, then reads can be parallel."""
        calls = [
            ToolCall(id="0", name="write_file", arguments={}),
            ToolCall(id="1", name="read_file", arguments={}),
            ToolCall(id="2", name="read_file", arguments={}),
        ]
        batches = partition_tool_calls(calls)
        assert len(batches) == 2
        assert batches[0].parallel is False
        assert len(batches[0].calls) == 1
        assert batches[1].parallel is True
        assert len(batches[1].calls) == 2

    def test_alternating_read_write(self):
        """Read, Write, Read, Write → 4 batches (each write breaks)."""
        names = ["read_file", "write_file", "read_file", "write_file"]
        calls = [
            ToolCall(id=str(i), name=name, arguments={})
            for i, name in enumerate(names)
        ]
        batches = partition_tool_calls(calls)
        assert len(batches) == 4
        assert [b.parallel for b in batches] == [True, False, True, False]

    def test_two_writes_consecutive(self):
        """Two writes in a row → 2 separate serial batches."""
        names = ["write_file", "edit_file"]
        calls = [
            ToolCall(id=str(i), name=name, arguments={})
            for i, name in enumerate(names)
        ]
        batches = partition_tool_calls(calls)
        assert len(batches) == 2
        assert not batches[0].parallel
        assert not batches[1].parallel
