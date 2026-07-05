"""
Tool Execution — Concurrent & Streaming.

Partitions tool calls into concurrent-safe batches and executes them
with bounded parallelism. Direct port of Claude Code's toolOrchestration.ts.

Algorithm (from Claude Code Ch7):
1. Partition tool calls into batches (parallel vs serial)
2. Execute each batch: parallel -> asyncio.gather with semaphore,
                      serial   -> sequential await
3. Yield results in original call order

Refs:
- SPEC_TOOL_EXECUTION.md
- Claude Code toolOrchestration.ts
- Claude Code Ch7: Concurrent Tool Execution
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("aiw.tool_exec")

# Same default as Claude Code
MAX_CONCURRENCY = 10


# ═══════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════


@dataclass
class ToolCall:
    """A parsed tool call from the model."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Batch:
    """A group of tool calls — either all parallel or all serial."""
    parallel: bool
    calls: list[ToolCall]


@dataclass
class ToolResult:
    """Result from executing a single tool."""
    call_id: str
    name: str
    content: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


# ═══════════════════════════════════════════════════════════
# Tool concurrency safety
# ═══════════════════════════════════════════════════════════

# Read-only tools (always safe to run in parallel)
_READ_ONLY_TOOLS: set[str] = {
    "read_file",
    "list_files",
    "search_code",
    "web_search",
    "web_fetch",
    "headless_browser",
    "paginated_scraper",
    "git_status",
    "git_diff",
    "git_log",
    "retrieve_knowledge",
}

# Mutating tools (never safe to run in parallel)
_MUTATING_TOOLS: set[str] = {
    "write_file",
    "edit_file",
    "git_commit",
    "git_branch",
    "git_checkout",
}

# Shell commands that are always read-only
_READ_ONLY_SHELL_PREFIXES: tuple[str, ...] = (
    "ls", "cat", "head", "tail", "wc", "grep", "find",
    "git status", "git diff", "git log", "git branch",
    "which", "type", "echo", "pwd", "whoami", "date",
    "python -c", "node -e", "cargo --version",
    "du", "df", "ps", "env", "printenv",
)


def is_concurrency_safe(tool_name: str, arguments: dict[str, Any] | None = None, read_only_prefixes: tuple[str, ...] = _READ_ONLY_SHELL_PREFIXES) -> bool:
    """Decide if THIS specific tool call can run in parallel.

    NOT a global property of the tool — depends on the arguments.
    Follows Claude Code's isConcurrencySafe() semantics.

    Args:
        tool_name: Name of the tool being called.
        arguments: Parsed arguments dict (for context-aware checks like shell).
        read_only_prefixes: Tuple of shell command prefixes that are read-only.
    """
    if tool_name in _MUTATING_TOOLS:
        return False

    if tool_name in _READ_ONLY_TOOLS:
        return True

    # Shell — check if command is read-only
    if tool_name == "shell" and arguments:
        command = arguments.get("command", "")
        cmd_stripped = command.strip()
        for prefix in read_only_prefixes:
            if cmd_stripped.startswith(prefix):
                return True
        return False

    # Default conservative: unsafe
    return False


# ═══════════════════════════════════════════════════════════
# Partition algorithm (Claude Code toolOrchestration.ts)
# ═══════════════════════════════════════════════════════════


def partition_tool_calls(
    calls: list[ToolCall],
    concurrency_check: Callable[[str, dict[str, Any] | None], bool] = is_concurrency_safe,
) -> list[Batch]:
    """Partition tool calls into concurrent-safe batches.

    Algorithm: walk the array in order. Consecutive safe tools
    accumulate in the same batch. Any unsafe tool breaks the batch
    and runs serially.

    Example:
      Input:  [Read, Read, Grep, Edit, Read]
      Output: [
          Batch(parallel=True,  calls=[Read, Read, Grep]),
          Batch(parallel=False, calls=[Edit]),
          Batch(parallel=True,  calls=[Read]),
      ]
    """
    if not calls:
        return []

    batches: list[Batch] = []

    for call in calls:
        safe = concurrency_check(call.name, call.arguments)

        if safe and batches and batches[-1].parallel:
            # Extend current parallel batch
            batches[-1].calls.append(call)
        else:
            batches.append(Batch(parallel=safe, calls=[call]))

    return batches


# ═══════════════════════════════════════════════════════════
# Execution
# ═══════════════════════════════════════════════════════════


async def execute_tools(
    calls: list[ToolCall],
    handlers: dict[str, Callable[..., Any]],
    max_concurrency: int = MAX_CONCURRENCY,
) -> AsyncGenerator[ToolResult, None]:
    """Execute tool calls with partitioning and bounded parallelism.

    Pipeline:
    1. Partition → batches (concurrent vs serial)
    2. Execute each batch:
       - Concurrent: asyncio.gather with semaphore
       - Serial: await sequentially
    3. Yield results in original call order.

    Args:
        calls: List of tool calls from the model.
        handlers: Dict mapping tool_name -> handler function.
        max_concurrency: Max parallel tool executions (default 10).
    """
    batches = partition_tool_calls(calls)

    for batch in batches:
        if batch.parallel:
            # Execute in parallel with concurrency limit
            sem = asyncio.Semaphore(max_concurrency)

            async def _run_one(call: ToolCall) -> ToolResult:
                async with sem:
                    return await _execute_single(call, handlers)

            results = await asyncio.gather(*[_run_one(c) for c in batch.calls])
            for r in results:
                yield r
        else:
            # Execute sequentially
            for call in batch.calls:
                result = await _execute_single(call, handlers)
                yield result


async def _execute_single(
    call: ToolCall,
    handlers: dict[str, Callable[..., Any]],
) -> ToolResult:
    """Execute a single tool call."""
    handler = handlers.get(call.name)
    if handler is None:
        return ToolResult(
            call_id=call.id,
            name=call.name,
            content=f"Error: Unknown tool '{call.name}'",
            error=f"unknown_tool: {call.name}",
        )

    try:
        # Normalize arguments — may be JSON string, dict, or raw value
        args = call.arguments
        if isinstance(args, str):
            import json as _json
            try:
                args = _json.loads(args)
            except (_json.JSONDecodeError, TypeError):
                pass  # keep as string, try as keyword arg

        # Call handler with appropriate unpacking
        if isinstance(args, dict):
            result = handler(**args)
        elif isinstance(args, str):
            # Try common web tool param names
            for key in ("url", "query", "path", "command"):
                try:
                    result = handler(**{key: args})
                    break
                except TypeError:
                    continue
            else:
                result = handler(args)
        else:
            result = handler(args)
        if asyncio.iscoroutine(result):
            content = str(await result)
        else:
            content = str(result)
        return ToolResult(call_id=call.id, name=call.name, content=content)
    except Exception as exc:
        logger.warning("Tool %s failed: %s", call.name, exc)
        return ToolResult(
            call_id=call.id,
            name=call.name,
            content=f"Error executing {call.name}: {exc}",
            error=str(exc),
        )
