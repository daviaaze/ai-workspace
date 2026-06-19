"""
Agent Loop — the central execution engine.

A single async-generator function that replaces crewAI. Every interface
(CLI, TUI, MCP, SDK) calls the same ``agent_loop()`` entry point.

Architecture inspired by Claude Code's ``query.ts`` and pi's ``agent-loop.ts``:
- Async generator → backpressure, typed return, composable
- State object → carries context between iterations
- Pattern dispatch → Direct, ReAct (Plan-Execute, ReWOO in Phase 2)
- Deps injection → testable with fake providers
- Asyncio.Queue → events stream in real-time while inner pattern runs

Refs:
- SPEC_AGENT_LOOP.md
- Claude Code query.ts (Anthropic)
- pi agent-loop.ts
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable

from ai_workspace.core.result import ErrorCode

logger = logging.getLogger("aiw.loop")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════


class LoopPattern(Enum):
    """Which execution strategy to use."""

    DIRECT = "direct"
    """Single LLM call, no tools. For chat, translation, classification."""

    REACT = "react"
    """Thought → Action → Observation → repeat. For coding, debugging."""

    PLAN_EXECUTE = "plan_execute"
    """Plan once, execute steps. For structured, predictable tasks. (Phase 2+)"""

    REWOO = "rewoo"
    """Plan tools → execute all in parallel → synthesize. (Phase 2+)"""

    DAG = "dag"
    """Compile task into DAG, execute with parallel + local repair. (Phase 5+)"""


class TerminalReason(Enum):
    """Why the loop stopped."""

    COMPLETED = "completed"
    MAX_TURNS = "max_turns"
    TOKEN_BUDGET = "token_budget"
    USER_ABORT = "user_abort"
    TOOL_ERROR = "tool_error"
    MODEL_ERROR = "model_error"
    NO_TOOLS = "no_tools"
    TIMEOUT = "timeout"


# ═══════════════════════════════════════════════════════════
# Loop data classes
# ═══════════════════════════════════════════════════════════


@dataclass
class LoopEvent:
    """A single event emitted during the loop.

    The ``type`` determines the shape of ``data``:

    +---------------+-------------------------------------+
    | type          | data keys                           |
    +===============+=====================================+
    | ``token``     | ``text``                            |
    +---------------+-------------------------------------+
    | ``thinking``  | ``thought``                         |
    +---------------+-------------------------------------+
    | ``tool_call`` | ``tool``, ``args``                  |
    +---------------+-------------------------------------+
    | ``tool_result``| ``tool``, ``result``, ``error``    |
    +---------------+-------------------------------------+
    | ``error``     | ``code``, ``message``, ...          |
    +---------------+-------------------------------------+
    | ``phase``     | ``phase``, ``message``              |
    +---------------+-------------------------------------+
    | ``done``      | ``reason``, ``turns``, ``tokens``   |
    +---------------+-------------------------------------+
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopState:
    """Mutable state carried between iterations."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    token_count: int = 0
    tool_errors: int = 0
    recovery_attempts: int = 0
    aborted: bool = False
    final_response: str = ""

    # Context compaction (Phase 2)
    compactor: Any | None = None
    """ContextCompactor instance set by agent_loop after construction."""

    # Memory Tree (Phase 5+)
    memory_tree: Any | None = None
    """MemoryTree instance for hierarchical state tracking."""

    def add_message(self, role: str, content: str | None, **extra: Any) -> None:
        msg: dict[str, Any] = {"role": role}
        if content is not None:
            msg["content"] = content
        msg.update(extra)
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })


@dataclass
class LoopParams:
    """All parameters for a single agent loop invocation."""

    task: str
    pattern: LoopPattern = LoopPattern.DIRECT

    # --- Model config ---
    model: str = "qwen3:14b"
    provider: str = "ollama"
    temperature: float = 0.7

    # --- System prompt ---
    system_prompt: str = ""

    # --- Tools ---
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)

    # --- Parallel tool execution ---
    parallel_tools: bool = True
    """If True, partition tool calls into concurrent-safe batches for parallel execution."""

    # --- Limits ---
    max_turns: int = 20
    max_tokens: int = 100_000
    timeout: float = 300.0

    # --- Streaming ---
    stream: bool = True

    # --- Callbacks ---
    on_step: Callable[[LoopEvent], None] | None = None

    # --- History ---
    messages: list[dict[str, Any]] = field(default_factory=list)

    # --- Deps injection (testability) ---
    deps: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Default system prompts
# ═══════════════════════════════════════════════════════════

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer the user's question clearly and concisely. "
    "If you need to use tools, call them one at a time and observe their results."
)

_REACT_SYSTEM_PROMPT = (
    "You are a coding and research agent. Follow the ReAct pattern:\n"
    "1. **Thought**: reason about what to do next\n"
    "2. **Action**: call a tool with specific arguments\n"
    "3. **Observation**: read the tool output and decide next step\n\n"
    "Use tools to gather information, read files, run commands, and search. "
    "After gathering enough information, provide a final answer without calling more tools."
)

_CODE_AGENT_SYSTEM_PROMPT = (
    "You are an expert software engineer AI agent. Your job is to read, write, "
    "edit, and analyze code. Follow this workflow:\n\n"
    "## Rules\n"
    "1. **Read before edit**: always use read_file() before editing any file\n"
    "2. **Think before acting**: explain your reasoning before each action\n"
    "3. **One tool at a time**: call one tool, observe result, then decide next step\n"
    "4. **Verify your work**: after editing, use shell_exec() to run linters/tests\n"
    "5. **Exact edits**: use edit_file() with exact old/new strings from read_file()\n"
    "6. **Atomic writes**: use write_file() for new files (never partial writes)\n"
    "7. **Sandbox safety**: all file ops stay within the workspace\n"
    "8. **Undo available**: if an edit breaks things, use undo_edit() to revert\n\n"
    "## Available tools\n"
    "- read_file(path, offset, limit): read file with line numbers\n"
    "- write_file(path, content): create or overwrite file atomically\n"
    "- edit_file(path, old, new, replace_all): exact string replacement\n"
    "- shell_exec(command, timeout, cwd): run sandboxed shell commands\n"
    "- git(subcommand, args, write): git operations (read-only by default)\n"
    "- undo_edit(count): revert last N edits\n\n"
    "When done, provide a summary of what you changed and why."
)


# ═══════════════════════════════════════════════════════════
# Pattern runners (called via emit callback, run in a task)
# ═══════════════════════════════════════════════════════════

# Type for the emit callback: puts events on an asyncio.Queue
EmitFn = Callable[[LoopEvent], None]


async def _run_direct(
    params: LoopParams,
    state: LoopState,
    stream_chat: Callable[..., AsyncGenerator[dict, None]],
    emit: EmitFn,
) -> TerminalReason:
    """Single LLM call, no tool loop."""
    system = params.system_prompt or _DEFAULT_SYSTEM_PROMPT

    # Inject memory tree context if available
    if state.memory_tree is not None:
        mem_ctx = state.memory_tree.get_context()
        if mem_ctx:
            system = f"{system}\n\n[MEMORY CONTEXT]\n{mem_ctx}"

    messages: list[dict] = [{"role": "system", "content": system}]
    if params.messages:
        messages.extend(params.messages)
    # Always append the user's task as a new message
    messages.append({"role": "user", "content": params.task})

    try:
        async for chunk in stream_chat(
            model=params.model,
            messages=messages,
            temperature=params.temperature,
            tools=None,
            provider=params.provider,
        ):
            chunk_type = chunk.get("type", "text")
            if chunk_type == "text":
                text = chunk.get("text", "")
                state.final_response += text
                emit(LoopEvent(type="token", data={"text": text}))
            elif chunk_type == "thinking":
                emit(LoopEvent(
                    type="thinking",
                    data={"thought": chunk.get("thought", "")},
                ))
            elif chunk_type == "error":
                emit(LoopEvent(type="error", data=chunk))
                return TerminalReason.MODEL_ERROR
    except Exception as exc:
        logger.exception("Direct loop failed")
        emit(LoopEvent(
            type="error",
            data={
                "code": ErrorCode.MODEL_ERROR,
                "message": str(exc),
                "recoverable": False,
            },
        ))
        return TerminalReason.MODEL_ERROR

    state.messages = messages

    # Compact after completion
    if state.compactor:
        state.messages = state.compactor.compact(
            state.messages,
            state.compactor.estimate_total_tokens(state.messages),
        )

    return TerminalReason.COMPLETED


async def _run_react(
    params: LoopParams,
    state: LoopState,
    stream_chat: Callable[..., AsyncGenerator[dict, None]],
    emit: EmitFn,
) -> TerminalReason:
    """ReAct loop: iterate until the model provides a final answer."""
    system = params.system_prompt or _REACT_SYSTEM_PROMPT

    # Inject memory tree context if available
    if state.memory_tree is not None:
        mem_ctx = state.memory_tree.get_context()
        if mem_ctx:
            system = f"{system}\n\n[MEMORY CONTEXT — previous subgoals and results]\n{mem_ctx}"

    messages: list[dict] = [{"role": "system", "content": system}]
    if params.messages:
        messages.extend(params.messages)
    # Always append the user's task as a new message
    messages.append({"role": "user", "content": params.task})

    state.messages = messages
    start_time = time.monotonic()
    tool_handlers = params.tool_handlers

    while True:
        # ── Check stop conditions ────────────────────────────
        if state.aborted:
            return TerminalReason.USER_ABORT

        if state.turn_count >= params.max_turns:
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.AGENT_LOOP_LIMIT,
                    "message": f"Reached max turns ({params.max_turns})",
                    "recoverable": False,
                },
            ))
            return TerminalReason.MAX_TURNS

        if state.token_count >= params.max_tokens:
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.AGENT_TOKEN_BUDGET,
                    "message": f"Token budget exceeded ({params.max_tokens})",
                    "recoverable": False,
                },
            ))
            return TerminalReason.TOKEN_BUDGET

        if time.monotonic() - start_time > params.timeout:
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.AGENT_LOOP_TIMEOUT,
                    "message": f"Global timeout ({params.timeout}s)",
                    "recoverable": False,
                },
            ))
            return TerminalReason.TIMEOUT

        # ── Call model ───────────────────────────────────────
        emit(LoopEvent(
            type="phase",
            data={"phase": "thinking", "turn": state.turn_count + 1},
        ))

        tool_calls: list[dict] = []
        turn_text: list[str] = []

        try:
            async for chunk in stream_chat(
                model=params.model,
                messages=messages,
                temperature=params.temperature,
                tools=params.tools if params.tools else None,
                provider=params.provider,
            ):
                chunk_type = chunk.get("type", "text")

                if chunk_type == "text":
                    text = chunk.get("text", "")
                    turn_text.append(text)
                    state.token_count += 1
                    emit(LoopEvent(type="token", data={"text": text}))
                    # Inline token budget check (stops during streaming)
                    if state.token_count >= params.max_tokens:
                        emit(LoopEvent(
                            type="error",
                            data={
                                "code": ErrorCode.AGENT_TOKEN_BUDGET,
                                "message": f"Token budget exceeded ({params.max_tokens})",
                                "recoverable": False,
                            },
                        ))
                        return TerminalReason.TOKEN_BUDGET

                elif chunk_type == "thinking":
                    emit(LoopEvent(
                        type="thinking",
                        data={"thought": chunk.get("thought", "")},
                    ))

                elif chunk_type == "tool_call":
                    args = chunk.get("arguments", {})
                    # Normalise: parse JSON string to dict if needed
                    if isinstance(args, str):
                        try:
                            import json as _json
                            args = _json.loads(args)
                        except (_json.JSONDecodeError, TypeError):
                            pass
                    tc = {
                        "id": chunk.get("id", f"call_{len(tool_calls)}"),
                        "name": chunk["name"],
                        "arguments": args,
                    }
                    tool_calls.append(tc)
                    emit(LoopEvent(
                        type="tool_call",
                        data={"tool": tc["name"], "args": tc["arguments"]},
                    ))

                elif chunk_type == "error":
                    emit(LoopEvent(type="error", data=chunk))
                    state.tool_errors += 1
                    if state.tool_errors >= 3:
                        return TerminalReason.MODEL_ERROR

        except Exception as exc:
            logger.exception("Model call in ReAct loop failed")
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.MODEL_ERROR,
                    "message": str(exc),
                    "recoverable": False,
                },
            ))
            return TerminalReason.MODEL_ERROR

        # ── No tool calls? We're done ────────────────────────
        if not tool_calls:
            assistant_text = "".join(turn_text)
            state.final_response += assistant_text
            state.add_message("assistant", assistant_text)
            return TerminalReason.COMPLETED

        # ── Execute tools ────────────────────────────────────
        state.add_message(
            "assistant",
            "".join(turn_text) or None,
            tool_calls=[
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": (
                            tc["arguments"]
                            if isinstance(tc["arguments"], str)
                            else _json_dumps(tc["arguments"])
                        ),
                    },
                }
                for tc in tool_calls
            ],
        )

        if params.parallel_tools and len(tool_calls) > 1:
            # ── Parallel execution (partitioned) ────────────────
            from ai_workspace.agents.tool_execution import (
                ToolCall as ExecToolCall,
                execute_tools,
            )

            exec_calls = [
                ExecToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"])
                for tc in tool_calls
            ]

            async for result in execute_tools(exec_calls, tool_handlers):
                emit(LoopEvent(
                    type="phase",
                    data={
                        "phase": "executing",
                        "tool": result.name,
                        "turn": state.turn_count + 1,
                    },
                ))

                if result.error:
                    emit(LoopEvent(
                        type="error",
                        data={
                            "code": ErrorCode.TOOL_FAILED,
                            "message": f"Tool {result.name} failed: {result.error}",
                            "recoverable": True,
                        },
                    ))
                    state.tool_errors += 1
                else:
                    state.tool_errors = 0

                state.add_tool_result(result.call_id, result.content)
                emit(LoopEvent(
                    type="tool_result",
                    data={"tool": result.name, "result": result.content},
                ))

        else:
            # ── Sequential execution (fallback) ────────────────
            for tc in tool_calls:
                emit(LoopEvent(
                    type="phase",
                    data={
                        "phase": "executing",
                        "tool": tc["name"],
                        "turn": state.turn_count + 1,
                    },
                ))

                result_text: str
                try:
                    handler = tool_handlers.get(tc["name"])
                    if handler is None:
                        result_text = f"Error: Unknown tool '{tc['name']}'"
                        emit(LoopEvent(
                            type="error",
                            data={
                                "code": ErrorCode.TOOL_FAILED,
                                "message": f"Unknown tool: {tc['name']}",
                                "recoverable": True,
                            },
                        ))
                        state.tool_errors += 1
                    else:
                        args = tc["arguments"]
                        if isinstance(args, str):
                            import json as _json
                            try:
                                args = _json.loads(args)
                            except (_json.JSONDecodeError, TypeError):
                                pass  # keep as string
                        # Handle both dict (**kwargs) and raw value (wrap as 'query' or 'url')
                        if isinstance(args, dict):
                            result = handler(**args)
                        elif isinstance(args, str):
                            # Many web tools accept a single string as the primary arg
                            # Try common param names: url, query, path, command
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
                            result_text = str(await result)
                        else:
                            result_text = str(result)
                        state.tool_errors = 0
                except Exception as exc:
                    logger.warning("Tool %s failed: %s", tc["name"], exc)
                    result_text = f"Error executing {tc['name']}: {exc}"
                    emit(LoopEvent(
                        type="error",
                        data={
                            "code": ErrorCode.TOOL_FAILED,
                            "message": f"Tool {tc['name']} failed: {exc}",
                            "recoverable": True,
                        },
                    ))
                    state.tool_errors += 1

                state.add_tool_result(tc["id"], result_text)
                emit(LoopEvent(
                    type="tool_result",
                    data={"tool": tc["name"], "result": result_text},
                ))

        if state.tool_errors >= 5:
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.TOOL_FAILED,
                    "message": "Too many consecutive tool errors",
                    "recoverable": False,
                },
            ))
            return TerminalReason.TOOL_ERROR

        # Compact messages after each turn
        if state.compactor:
            messages = state.compactor.compact(
                messages,
                state.compactor.estimate_total_tokens(messages),
            )
            state.messages = messages

        state.turn_count += 1


# ═══════════════════════════════════════════════════════════
# DAG pattern — compile + execute with local repair
# ═══════════════════════════════════════════════════════════


async def _run_dag(
    params: LoopParams,
    state: LoopState,
    stream_chat: Callable[..., AsyncGenerator[dict, None]],
    emit: EmitFn,
) -> TerminalReason:
    """DAG pattern: compile task into DAG, execute with parallel + local repair.

    Uses DAGExecutor for parallel node execution. Each node runs as a
    DIRECT sub-agent call through the same stream_chat provider.
    """
    from ai_workspace.agents.dag_executor import (
        DAGExecutor,
        DAGExecutorConfig,
        DAGNode,
        compile_dag_plan,
    )

    emit(LoopEvent(
        type="phase",
        data={"phase": "compiling", "message": "Compiling task into DAG..."},
    ))

    # 1. Compile DAG from natural language
    tool_names = [t.get("name", "") if isinstance(t, dict) else getattr(t, "name", "") for t in (params.tools or [])]
    try:
        plan = await compile_dag_plan(
            task=params.task,
            stream_chat=stream_chat,
            available_tools=tool_names,
            model=params.model,
        )
    except Exception as exc:
        emit(LoopEvent(
            type="error",
            data={
                "code": ErrorCode.INTERNAL_ERROR,
                "message": f"DAG compilation failed: {exc}",
                "recoverable": False,
            },
        ))
        return TerminalReason.MODEL_ERROR

    emit(LoopEvent(
        type="phase",
        data={
            "phase": "executing",
            "message": f"Executing {len(plan.nodes)} nodes with up to {min(4, len(plan.nodes))} parallel...",
        },
    ))

    # 2. Node handler — each node is a DIRECT sub-agent call
    async def _node_handler(node: DAGNode) -> str:
        emit(LoopEvent(
            type="phase",
            data={"phase": "node_start", "node": node.id, "description": node.description},
        ))

        # Build sub-prompt with DAG context (dependencies' results as context)
        dep_results = ""
        for dep_id in node.dependencies:
            dep_node = plan.nodes.get(dep_id)
            if dep_node and dep_node.result:
                dep_results += f"\n[Result of '{dep_node.description}']: {dep_node.result[:1000]}"

        sub_task = node.description
        if dep_results:
            sub_task = f"{node.description}\n\nPrevious results (dependencies):{dep_results}"

        result_parts: list[str] = []
        async for chunk in stream_chat(
            model=params.model,
            messages=[
                {"role": "system", "content": params.system_prompt or _DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": sub_task},
            ],
            temperature=params.temperature,
            tools=None,
            provider=params.provider,
        ):
            chunk_type = chunk.get("type", "text")
            if chunk_type == "text":
                text = chunk.get("text", "")
                result_parts.append(text)
                emit(LoopEvent(type="token", data={"text": text}))
            elif chunk_type == "error":
                raise RuntimeError(f"Node {node.id} failed: {chunk.get('message', '')}")

        result = "".join(result_parts)
        emit(LoopEvent(
            type="phase",
            data={"phase": "node_done", "node": node.id, "result_len": len(result)},
        ))
        return result

    # 3. Execute DAG with parallel semaphore
    executor = DAGExecutor(DAGExecutorConfig(max_parallel=min(4, len(plan.nodes))))
    try:
        results = await executor.execute(plan, _node_handler)
    except Exception as exc:
        emit(LoopEvent(
            type="error",
            data={
                "code": ErrorCode.TOOL_FAILED,
                "message": f"DAG execution failed: {exc}",
                "recoverable": False,
            },
        ))
        return TerminalReason.MODEL_ERROR

    # 4. Synthesize final response from all results
    synthesis_prompt = f"""Task: {params.task}

Sub-results:
"""
    for node_id, result in results.items():
        node = plan.nodes.get(node_id)
        if node:
            synthesis_prompt += f"\n[{node.description}]: {str(result)[:2000]}"

    synthesis_prompt += "\n\nSynthesize these results into a coherent final answer."

    async for chunk in stream_chat(
        model=params.model,
        messages=[{"role": "user", "content": synthesis_prompt}],
        temperature=params.temperature,
        tools=None,
        provider=params.provider,
    ):
        chunk_type = chunk.get("type", "text")
        if chunk_type == "text":
            text = chunk.get("text", "")
            state.final_response += text
            emit(LoopEvent(type="token", data={"text": text}))
        elif chunk_type == "error":
            emit(LoopEvent(type="error", data=chunk))
            return TerminalReason.MODEL_ERROR

    emit(LoopEvent(
        type="phase",
        data={
            "phase": "done",
            "nodes_completed": len(results),
            "nodes_failed": plan.summary()["failed"],
            "nodes_skipped": plan.summary()["skipped"],
        },
    ))

    return TerminalReason.COMPLETED


# ═══════════════════════════════════════════════════════════
# Entry point — async generator with asyncio.Queue for
# real-time streaming (pattern runs in background task)
# ═══════════════════════════════════════════════════════════


async def agent_loop(
    params: LoopParams,
) -> AsyncGenerator[LoopEvent, None]:
    """The central agent loop — async generator.

    Events are streamed in real-time via an asyncio.Queue. The pattern
    runner executes in a background task while the generator drains
    events from the queue.

    Example::

        params = LoopParams(
            task="Explain this code",
            pattern=LoopPattern.DIRECT,
            model="qwen3:14b",
            stream=True,
        )
        async for event in agent_loop(params):
            if event.type == "token":
                print(event.data["text"], end="")

    The ``done`` event's ``data["reason"]`` field contains the
    TerminalReason.
    """
    state = LoopState()

    # ── Initialize context compactor ───────────────────────
    from ai_workspace.agents.compaction import ContextCompactor
    state.compactor = ContextCompactor()

    # ── Initialize memory tree ────────────────────────────
    from ai_workspace.agents.memory_tree import MemoryTree, StepRecord
    state.memory_tree = MemoryTree()

    # ── Resolve stream_chat dependency ─────────────────────
    stream_chat = _resolve_stream_chat(params)

    # ── Set up event queue for streaming ───────────────────
    queue: asyncio.Queue[LoopEvent | None] = asyncio.Queue()

    def emit(event: LoopEvent) -> None:
        """Put an event on the queue (called from inside pattern runner)."""
        queue.put_nowait(event)

    # ── Run pattern in background task ─────────────────────
    async def _run_pattern() -> TerminalReason:
        if params.pattern == LoopPattern.DIRECT:
            return await _run_direct(params, state, stream_chat, emit)
        elif params.pattern == LoopPattern.REACT:
            return await _run_react(params, state, stream_chat, emit)
        elif params.pattern == LoopPattern.PLAN_EXECUTE:
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "Plan-Execute not yet implemented (Phase 2+)",
                    "recoverable": False,
                },
            ))
            return TerminalReason.MODEL_ERROR
        elif params.pattern == LoopPattern.REWOO:
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "ReWOO not yet implemented (Phase 2+)",
                    "recoverable": False,
                },
            ))
            return TerminalReason.MODEL_ERROR
        elif params.pattern == LoopPattern.DAG:
            return await _run_dag(params, state, stream_chat, emit)
        else:
            emit(LoopEvent(
                type="error",
                data={
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": f"Unknown loop pattern: {params.pattern}",
                    "recoverable": False,
                },
            ))
            return TerminalReason.MODEL_ERROR

    async def _run_and_signal() -> TerminalReason:
        """Run the pattern and signal completion via sentinel."""
        try:
            return await _run_pattern()
        finally:
            queue.put_nowait(None)  # send sentinel

    pattern_task = asyncio.create_task(_run_and_signal())

    # ── Drain events from queue as they arrive ─────────────
    while True:
        event = await queue.get()
        if event is None:  # sentinel — pattern finished
            break

        # Grow memory tree from this event
        if state.memory_tree is not None:
            _grow_memory_tree(state.memory_tree, event)

        if params.on_step:
            try:
                params.on_step(event)
            except Exception:
                logger.warning("on_step callback failed", exc_info=True)
        yield event

    # ── Collect terminal reason and emit done ──────────────
    reason = await pattern_task

    done_event = LoopEvent(
        type="done",
        data={
            "reason": reason.value,
            "turns": state.turn_count,
            "tokens": state.token_count,
        },
    )
    if params.on_step:
        try:
            params.on_step(done_event)
        except Exception:
            pass
    yield done_event


# ═══════════════════════════════════════════════════════════
# Providers bridge
# ═══════════════════════════════════════════════════════════


def _resolve_stream_chat(
    params: LoopParams,
) -> Callable[..., AsyncGenerator[dict, None]]:
    """Resolve the ``stream_chat`` callable from deps or the provider layer."""
    if "stream_chat" in params.deps:
        return params.deps["stream_chat"]
    return _default_stream_chat


async def _default_stream_chat(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    tools: list[dict] | None = None,
    provider: str = "ollama",
) -> AsyncGenerator[dict, None]:
    """Fallback stream_chat using the ProviderRegistry."""
    from ai_workspace.providers import ProviderRegistry

    registry = ProviderRegistry()

    if provider not in registry.providers:
        for name in registry.providers:
            provider = name
            break
        else:
            yield {
                "type": "error",
                "code": ErrorCode.PROVIDER_OFFLINE,
                "message": "No providers configured",
                "recoverable": False,
            }
            return

    try:
        client = registry.get_client(provider)
        actual_model = registry.get_model(provider, model)

        if provider == "ollama":
            # Use native Ollama /api/chat (supports think=True, thinking chunks)
            async for chunk in registry.stream_chat(
                model=actual_model,
                messages=messages,
                temperature=temperature,
                tools=tools,
                provider=provider,
            ):
                yield chunk
            return

        kwargs: dict[str, Any] = {
            "model": actual_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = _normalize_tools_for_provider(tools, provider)

        response = await client.chat.completions.create(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield {
                        "type": "tool_call",
                        "id": tc.id or "",
                        "name": tc.function.name if tc.function else "",
                        "arguments": tc.function.arguments if tc.function else "{}",
                    }
            if delta.content:
                yield {"type": "text", "text": delta.content}

    except Exception as exc:
        logger.exception("default_stream_chat failed")
        yield {
            "type": "error",
            "code": ErrorCode.PROVIDER_OFFLINE,
            "message": str(exc),
            "recoverable": True,
        }


# ═══════════════════════════════════════════════════════════
# Tool normalization for provider compatibility
# ═══════════════════════════════════════════════════════════

def _normalize_tools_for_provider(
    tools: list[dict[str, Any]],
    provider: str,
) -> list[dict[str, Any]]:
    """Normalize tool definitions to OpenAI function-calling format.

    All providers use the OpenAI-compatible client, which expects
    ``{"type": "function", "function": {...}}`` format.

    crewAI BaseTool objects are converted; already-normalized dicts pass through.
    """
    # Always normalize — the OpenAI client is used for all providers

    normalized = []
    for tool in tools:
        # Already in OpenAI format? Pass through
        if isinstance(tool, dict) and "type" in tool:
            normalized.append(tool)
            continue

        # Convert BaseTool or dict with name/description/parameters
        fn_def = _tool_to_openai_function(tool)
        if fn_def:
            normalized.append(fn_def)

    return normalized


# ═══════════════════════════════════════════════════════════
# Memory Tree — event tracking
# ═══════════════════════════════════════════════════════════


def _grow_memory_tree(tree: Any, event: LoopEvent) -> None:
    """Record an event as a StepRecord in the memory tree."""
    from ai_workspace.agents.memory_tree import StepRecord, estimate_step_tokens

    event_type = event.type
    data = event.data

    if event_type == "tool_call":
        content = f"{data.get('tool', 'unknown')}({_safe_str(data.get('args', ''))[:200]})"
        tree.grow(StepRecord(
            type="tool_call",
            content=content,
            tool_name=str(data.get("tool", "unknown")),
            tokens=estimate_step_tokens(content),
        ))

    elif event_type == "tool_result":
        result = _safe_str(data.get("result", ""))
        content = result[:500]
        err = _safe_str(data.get("error", ""))
        tree.grow(StepRecord(
            type="tool_result",
            content=content,
            tool_name=str(data.get("tool", "unknown")),
            error=err,
            tokens=estimate_step_tokens(content),
        ))

    elif event_type == "thinking":
        thought = _safe_str(data.get("thought", ""))
        tree.grow(StepRecord(
            type="thinking",
            content=thought[:300],
            tokens=estimate_step_tokens(thought[:300]),
        ))

    elif event_type == "error":
        content = f"{data.get('code', 'UNKNOWN')}: {data.get('message', '')}"
        tree.grow(StepRecord(
            type="error",
            content=content[:200],
            error=_safe_str(data.get("code", "")),
            tokens=estimate_step_tokens(content),
        ))


def _safe_str(value: Any, max_len: int = 500) -> str:
    """Safely convert any value to a string, truncating if needed."""
    try:
        s = str(value)
        return s[:max_len]
    except Exception:
        return "<unstringifiable>"


def _tool_to_openai_function(
    tool: Any,
) -> dict[str, Any] | None:
    """Convert a tool definition to OpenAI function format.

    Accepts:
    - crewAI BaseTool instances (has .name, .description, .args_schema)
    - Dicts with ``name``, ``description``, ``parameters`` keys

    Returns:
        ``{"type": "function", "function": {...}}`` or None if conversion fails.
    """
    # Try dict format first
    if isinstance(tool, dict):
        func_name = tool.get("name") or tool.get("function", {}).get("name", "")
        func_desc = tool.get("description") or tool.get("function", {}).get("description", "")
        func_params = tool.get("parameters") or tool.get("function", {}).get("parameters", {})
        if func_name:
            return {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": func_desc,
                    "parameters": func_params,
                },
            }
        return None

    # Try BaseTool instance (has .name, .description, .args_schema)
    try:
        name = getattr(tool, "name", None)
        description = getattr(tool, "description", "")
        args_schema = getattr(tool, "args_schema", None)

        if not name:
            return None

        # Build JSON Schema from Pydantic model
        parameters: dict[str, Any] = {"type": "object", "properties": {}}
        required: list[str] = []

        if args_schema and hasattr(args_schema, "model_fields"):
            for field_name, field_info in args_schema.model_fields.items():
                prop: dict[str, Any] = {}
                if hasattr(field_info, "annotation"):
                    python_type = field_info.annotation
                    if python_type is str:
                        prop["type"] = "string"
                    elif python_type is int:
                        prop["type"] = "integer"
                    elif python_type is float:
                        prop["type"] = "number"
                    elif python_type is bool:
                        prop["type"] = "boolean"
                    else:
                        prop["type"] = "string"  # fallback
                if hasattr(field_info, "description") and field_info.description:
                    prop["description"] = field_info.description
                if hasattr(field_info, "default") and field_info.default is not None:
                    import inspect, json as _json
                    # Pydantic Undefined is not JSON-serializable
                    try:
                        if field_info.default is not inspect.Parameter.empty:
                            _json.dumps(field_info.default)  # test serialization
                            prop["default"] = field_info.default
                    except (TypeError, ValueError):
                        pass  # skip unserializable defaults
                if field_info.is_required():
                    required.append(field_name)
                parameters["properties"][field_name] = prop

        if required:
            parameters["required"] = required

        # Clean description: strip "Tool Name: ..." prefix from crewAI
        clean_desc = description
        if "Tool Name:" in clean_desc:
            # Extract just the description part after the schema
            lines = clean_desc.split("\n")
            for i, line in enumerate(lines):
                if "Tool Description:" in line:
                    clean_desc = " ".join(lines[i + 1:]).strip()
                    break
        # Fallback: use first line if too long
        if len(clean_desc) > 1000:
            clean_desc = clean_desc[:997] + "..."

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": clean_desc or name,
                "parameters": parameters,
            },
        }
    except Exception as exc:
        logger.debug("Failed to convert tool to OpenAI format: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════
# Pattern suggestion heuristic
# ═══════════════════════════════════════════════════════════


def suggest_pattern(
    task: str,
    tools: list[dict] | None = None,
) -> LoopPattern:
    """Suggest the best loop pattern for a given task."""
    task_lower = task.lower()

    # No tools → Direct (nothing else we can do)
    if not tools:
        return LoopPattern.DIRECT

    # Coding / debugging keywords → ReAct
    code_kw = ["fix", "debug", "implement", "refactor", "add", "change",
                "corrigir", "corrige", "conserta", "arrumar", "build",
                "criar", "generate", "scaffold", "migrate"]
    if any(kw in task_lower for kw in code_kw):
        return LoopPattern.REACT

    # Complex multi-step tasks → DAG (parallel sub-tasks with dependencies)
    dag_kw = ["and", "then", "deploy", "setup", "configure", "install",
              "e", "depois", "configurar", "instalar", "migrate", "both"]
    if any(kw in task_lower.split() for kw in dag_kw) and len(task.split()) > 15:
        return LoopPattern.DAG

    # Search / comparison keywords → REACT with tools

    # Trivial single-greeting → Direct even with tools
    trivial = ["hi", "hello", "oi", "ola", "hey", "thanks", "obrigado"]
    if task_lower.strip().rstrip("!.?") in trivial:
        return LoopPattern.DIRECT

    # Default: ReAct (safe for unknown tasks with tools)
    return LoopPattern.REACT


# ═══════════════════════════════════════════════════════════
# Convenience: coding agent preconfigured
# ═══════════════════════════════════════════════════════════


async def coding_agent_loop(
    task: str,
    *,
    model: str = "qwen3:14b",
    provider: str = "ollama",
    workspace: str = "",
) -> AsyncGenerator[LoopEvent, None]:
    """Run a coding agent with code tools (read, write, edit, shell, git, undo).

    Preconfigured with research-backed tool design:
    - str_replace_editor (exact match, atomic writes)
    - Shell sandbox (allowlist, dangerous pattern detection)
    - Git read-only by default
    - Undo stack (50 edits)
    - Path sandbox confined to workspace

    Usage::

        async for event in coding_agent_loop("Add type hints to core/cost.py"):
            if event.type == "token":
                print(event.data["text"], end="")
    """
    from ai_workspace.tools.code_tools import get_code_tools, PathSandbox, _path_sandbox

    # Configure sandbox to workspace
    if workspace:
        from pathlib import Path
        _path_sandbox.workspace = Path(workspace).resolve()

    # Get code tools with handlers (skills are injected via prompt, not tools)
    tools = get_code_tools()
    tool_handlers = {
        t.name: t._run
        for t in tools
    }

    # Inject matching skill into system prompt (pi-compatible)
    from ai_workspace.agents.skill_matcher import inject_skill_for_task
    system_prompt = inject_skill_for_task(task, _CODE_AGENT_SYSTEM_PROMPT)

    params = LoopParams(
        task=task,
        pattern=LoopPattern.REACT,
        system_prompt=system_prompt,
        tools=tools,
        tool_handlers=tool_handlers,
        model=model,
        provider=provider,
        stream=True,
        max_turns=20,
        parallel_tools=False,  # Sequential for code (order matters)
    )

    async for event in agent_loop(params):
        yield event


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


def _json_dumps(obj: Any) -> str:
    import json as _json
    return _json.dumps(obj, ensure_ascii=False)
