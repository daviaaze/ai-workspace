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
                        except (json.JSONDecodeError, TypeError):
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
                        args = _json.loads(args)
                    result = handler(**args)
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
) -> AsyncGenerator[dict, None]:
    """Fallback stream_chat using the ProviderRegistry."""
    from ai_workspace.providers import ProviderRegistry

    registry = ProviderRegistry()

    provider = "ollama"
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

        kwargs: dict[str, Any] = {
            "model": actual_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

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

    # Search / comparison keywords → currently ReAct (ReWOO in Phase 2)
    search_kw = ["compare", "preço", "price", "qual melhor", "vs", "search",
                  "pesquisar", "buscar"]
    if any(kw in task_lower for kw in search_kw):
        return LoopPattern.REACT

    # Trivial single-greeting → Direct even with tools
    trivial = ["hi", "hello", "oi", "ola", "hey", "thanks", "obrigado"]
    if task_lower.strip().rstrip("!.?") in trivial:
        return LoopPattern.DIRECT

    # Default: ReAct (safe for unknown tasks with tools)
    return LoopPattern.REACT


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


def _json_dumps(obj: Any) -> str:
    import json as _json
    return _json.dumps(obj, ensure_ascii=False)
