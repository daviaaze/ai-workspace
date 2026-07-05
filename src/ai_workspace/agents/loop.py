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
from collections.abc import AsyncGenerator, Callable
from datetime import UTC
from typing import Any

from ai_workspace.agents.patterns import (  # re-export for backward compat
    LoopPattern,
    suggest_pattern,
)
from ai_workspace.agents.types import LoopEvent, LoopParams, LoopState, TerminalReason

__all__ = ["suggest_pattern"]  # prevent ruff F401 from dropping re-export
from ai_workspace.core.result import ErrorCode

logger = logging.getLogger("aiw.loop")


# (types, patterns, capabilities imported from agents/patterns.py,
#  agents/capabilities.py, and agents/types.py)


# ── Default system prompts ──────────────────────────────────

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

    # Inject tiered context (L0/L1) from TieredContextLoader
    if state.tiered_ctx is not None:
        tiered_text = state.tiered_ctx.get_context(tier="L1")
        if tiered_text:
            system = f"{system}\n\n{tiered_text}"
    # Fallback: inject memory tree context if available
    elif state.memory_tree is not None:
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

    # Inject tiered context (L0/L1) from TieredContextLoader
    if state.tiered_ctx is not None:
        tiered_text = state.tiered_ctx.get_context(tier="L1")
        if tiered_text:
            system = f"{system}\n\n{tiered_text}"
    # Fallback: inject memory tree context if available
    elif state.memory_tree is not None:
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
    tool_handlers = dict(params.tool_handlers)

    # Auto-register consult_subagent tool if Partner agents are available
    try:
        from ai_workspace.agents.consult_tool import CONSULT_TOOL_DEF, consult_handler
        if "consult_subagent" not in tool_handlers:
            tool_handlers["consult_subagent"] = consult_handler
            # Add tool definition to params.tools if not already present
            if not any(t.get("function", {}).get("name") == "consult_subagent" for t in params.tools):
                params.tools = list(params.tools) + [CONSULT_TOOL_DEF]
    except ImportError:
        pass

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
            )
            from ai_workspace.agents.tool_execution import (
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
# Plan-Execute pattern
# ═══════════════════════════════════════════════════════════


_PLAN_EXECUTE_SYSTEM_PROMPT = (
    "You are a planning agent. Given a task, produce a JSON plan "
    "with steps to accomplish it. Each step should be an object with "
    '"step" (description), "tool" (tool name or empty), and "args" (dict).\n'
    "Respond ONLY with a JSON object: {\"steps\": [{\"step\": \"...\", \"tool\": \"...\", \"args\": {}}]}"
)


async def _run_plan_execute(
    params: LoopParams,
    state: LoopState,
    stream_chat: Callable[..., AsyncGenerator[dict, None]],
    emit: EmitFn,
) -> TerminalReason:
    """Plan-Execute: plan once, execute steps sequentially.

    Phase 1: Ask LLM to produce a JSON plan.
    Phase 2: Execute each step (tool call or LLM call).
    Phase 3: Synthesize final answer from results.
    """
    import json as _json_mod

    system = params.system_prompt or _PLAN_EXECUTE_SYSTEM_PROMPT
    if state.tiered_ctx is not None:
        tiered_text = state.tiered_ctx.get_context(tier="L1")
        if tiered_text:
            system = f"{system}\n\n{tiered_text}"

    start_time = time.monotonic()

    def _check_stop_conditions() -> TerminalReason | None:
        """Return a TerminalReason if a stop condition is triggered, else None."""
        if state.aborted:
            return TerminalReason.USER_ABORT
        if state.turn_count >= params.max_turns:
            emit(LoopEvent(type="error", data={
                "code": ErrorCode.AGENT_LOOP_LIMIT,
                "message": f"Reached max turns ({params.max_turns})",
                "recoverable": False,
            }))
            return TerminalReason.MAX_TURNS
        if state.token_count >= params.max_tokens:
            emit(LoopEvent(type="error", data={
                "code": ErrorCode.AGENT_TOKEN_BUDGET,
                "message": f"Token budget exceeded ({params.max_tokens})",
                "recoverable": False,
            }))
            return TerminalReason.TOKEN_BUDGET
        if time.monotonic() - start_time > params.timeout:
            emit(LoopEvent(type="error", data={
                "code": ErrorCode.AGENT_LOOP_TIMEOUT,
                "message": f"Global timeout ({params.timeout}s)",
                "recoverable": False,
            }))
            return TerminalReason.TIMEOUT
        return None

    # ── Phase 1: Generate Plan ────────────────────────────
    emit(LoopEvent(type="phase", data={"phase": "planning", "message": "Generating plan..."}))

    plan_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Create a plan for: {params.task}"},
    ]

    plan_text = ""
    try:
        async for chunk in stream_chat(
            model=params.model, messages=plan_messages,
            temperature=0.3, tools=None, provider=params.provider,
        ):
            if chunk.get("type") == "text":
                plan_text += chunk.get("text", "")
                emit(LoopEvent(type="token", data={"text": chunk.get("text", "")}))
    except Exception as exc:
        emit(LoopEvent(type="error", data={"code": ErrorCode.MODEL_ERROR, "message": str(exc)}))
        return TerminalReason.MODEL_ERROR

    # Parse plan
    steps = []
    try:
        # Extract JSON from response (may be wrapped in markdown)
        json_start = plan_text.find("{")
        json_end = plan_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            plan_obj = _json_mod.loads(plan_text[json_start:json_end])
            steps = plan_obj.get("steps", [])
    except (ValueError, KeyError):
        steps = [{"step": plan_text, "tool": "", "args": {}}]

    if not steps:
        steps = [{"step": params.task, "tool": "", "args": {}}]

    emit(LoopEvent(type="phase", data={"phase": "executing", "message": f"Executing {len(steps)} steps..."}))

    # ── Phase 2: Execute Steps ────────────────────────────
    results = []
    for i, step in enumerate(steps):
        # Check stop conditions before each step
        stop_reason = _check_stop_conditions()
        if stop_reason:
            return stop_reason

        step_desc = step.get("step", "")
        tool_name = step.get("tool", "")
        tool_args = step.get("args", {})

        emit(LoopEvent(type="phase", data={"phase": f"step_{i+1}", "message": step_desc}))

        if tool_name and tool_name in params.tool_handlers:
            # Execute tool directly
            try:
                handler = params.tool_handlers[tool_name]
                result = handler(**tool_args)
                if asyncio.iscoroutine(result):
                    result_text = str(await result)
                else:
                    result_text = str(result)

                results.append({"step": step_desc, "result": result_text[:2000]})
                emit(LoopEvent(type="tool_call", data={"tool": tool_name, "args": tool_args}))
                emit(LoopEvent(type="tool_result", data={"tool": tool_name, "result": result_text[:500]}))
            except Exception as exc:
                results.append({"step": step_desc, "error": str(exc)})
                emit(LoopEvent(type="error", data={"code": ErrorCode.TOOL_FAILED, "message": str(exc)}))
        else:
            # No tool or unknown tool — use LLM
            step_messages = [
                {"role": "system", "content": "Execute this step and report the result."},
                {"role": "user", "content": step_desc},
            ]
            step_result = ""
            try:
                async for chunk in stream_chat(
                    model=params.model, messages=step_messages,
                    temperature=params.temperature, tools=None, provider=params.provider,
                ):
                    if chunk.get("type") == "text":
                        step_result += chunk.get("text", "")
            except Exception as exc:
                emit(LoopEvent(type="error", data={
                    "code": ErrorCode.MODEL_ERROR,
                    "message": f"Step execution failed: {exc}",
                    "recoverable": True,
                }))
            results.append({"step": step_desc, "result": step_result[:2000]})

        state.turn_count += 1

    # ── Phase 3: Synthesize ───────────────────────────────
    emit(LoopEvent(type="phase", data={"phase": "synthesizing", "message": "Synthesizing results..."}))

    results_text = "\n".join(
        f"Step {i+1}: {r.get('step', '')}\nResult: {r.get('result', r.get('error', 'N/A'))}"
        for i, r in enumerate(results)
    )
    synth_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Task: {params.task}\n\nStep results:\n{results_text}\n\nSynthesize a final answer."},
    ]

    try:
        async for chunk in stream_chat(
            model=params.model, messages=synth_messages,
            temperature=params.temperature, tools=None, provider=params.provider,
        ):
            if chunk.get("type") == "text":
                text = chunk.get("text", "")
                state.final_response += text
                emit(LoopEvent(type="token", data={"text": text}))
    except Exception as exc:
        emit(LoopEvent(type="error", data={"code": ErrorCode.MODEL_ERROR, "message": str(exc)}))
        return TerminalReason.MODEL_ERROR

    state.messages = [{"role": "user", "content": params.task}, {"role": "assistant", "content": state.final_response}]

    if state.compactor:
        state.messages = state.compactor.compact(
            state.messages, state.compactor.estimate_total_tokens(state.messages),
        )

    return TerminalReason.COMPLETED


# ═══════════════════════════════════════════════════════════
# ReWOO pattern — plan tools → execute parallel → synthesize
# ═══════════════════════════════════════════════════════════


_REWOO_SYSTEM_PROMPT = (
    "You are a ReWOO planning agent. Given a task, produce a JSON list "
    "of tool calls to execute in parallel. Each entry: {\"tool\": \"name\", "
    '"args": {}, "description\": \"what this does\"}.\n'
    "Respond ONLY with: {\"plan\": [{\"tool\": \"...\", \"args\": {}, \"description\": \"...\"}]}"
)


async def _run_rewoo(
    params: LoopParams,
    state: LoopState,
    stream_chat: Callable[..., AsyncGenerator[dict, None]],
    emit: EmitFn,
) -> TerminalReason:
    """ReWOO: plan all tool calls → execute in parallel → synthesize.

    Phase 1: Plan — LLM produces a list of parallel tool calls.
    Phase 2: Execute — run all tool calls concurrently.
    Phase 3: Synthesize — feed all results to LLM for final answer.
    """
    import asyncio as _aio
    import json as _json_mod

    system = params.system_prompt or _REWOO_SYSTEM_PROMPT
    if state.tiered_ctx is not None:
        tiered_text = state.tiered_ctx.get_context(tier="L1")
        if tiered_text:
            system = f"{system}\n\n{tiered_text}"

    start_time = time.monotonic()

    def _check_stop_conditions() -> TerminalReason | None:
        """Return a TerminalReason if a stop condition is triggered, else None."""
        if state.aborted:
            return TerminalReason.USER_ABORT
        if state.turn_count >= params.max_turns:
            emit(LoopEvent(type="error", data={
                "code": ErrorCode.AGENT_LOOP_LIMIT,
                "message": f"Reached max turns ({params.max_turns})",
                "recoverable": False,
            }))
            return TerminalReason.MAX_TURNS
        if state.token_count >= params.max_tokens:
            emit(LoopEvent(type="error", data={
                "code": ErrorCode.AGENT_TOKEN_BUDGET,
                "message": f"Token budget exceeded ({params.max_tokens})",
                "recoverable": False,
            }))
            return TerminalReason.TOKEN_BUDGET
        if time.monotonic() - start_time > params.timeout:
            emit(LoopEvent(type="error", data={
                "code": ErrorCode.AGENT_LOOP_TIMEOUT,
                "message": f"Global timeout ({params.timeout}s)",
                "recoverable": False,
            }))
            return TerminalReason.TIMEOUT
        return None

    # ── Phase 1: Plan ─────────────────────────────────────
    emit(LoopEvent(type="phase", data={"phase": "planning", "message": "Planning parallel tool calls..."}))

    plan_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Plan tool calls for: {params.task}"},
    ]

    plan_text = ""
    try:
        async for chunk in stream_chat(
            model=params.model, messages=plan_messages,
            temperature=0.3, tools=None, provider=params.provider,
        ):
            if chunk.get("type") == "text":
                plan_text += chunk.get("text", "")
                emit(LoopEvent(type="token", data={"text": chunk.get("text", "")}))
    except Exception as exc:
        emit(LoopEvent(type="error", data={"code": ErrorCode.MODEL_ERROR, "message": str(exc)}))
        return TerminalReason.MODEL_ERROR

    # Parse plan
    tool_calls = []
    try:
        json_start = plan_text.find("{")
        json_end = plan_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            plan_obj = _json_mod.loads(plan_text[json_start:json_end])
            tool_calls = plan_obj.get("plan", [])
    except (ValueError, KeyError):
        tool_calls = []

    # ── Phase 2: Execute Parallel ─────────────────────────
    emit(LoopEvent(type="phase", data={"phase": "executing", "message": f"Executing {len(tool_calls)} calls in parallel..."}))

    async def _exec_one(call: dict) -> dict:
        tool_name = call.get("tool", "")
        tool_args = call.get("args", {})
        desc = call.get("description", tool_name)
        if tool_name in params.tool_handlers:
            try:
                handler = params.tool_handlers[tool_name]
                result = handler(**tool_args)
                if asyncio.iscoroutine(result):
                    result_text = str(await result)
                else:
                    result_text = str(result)
                return {"tool": tool_name, "description": desc, "result": result_text[:2000]}
            except Exception as exc:
                return {"tool": tool_name, "description": desc, "error": str(exc)}
        return {"tool": tool_name, "description": desc, "error": f"Unknown tool: {tool_name}"}

    if tool_calls:
        results = await _aio.gather(*[_exec_one(c) for c in tool_calls])
        for r in results:
            emit(LoopEvent(type="tool_call", data={"tool": r["tool"], "args": {}}))
            if "error" in r:
                emit(LoopEvent(type="error", data={"code": ErrorCode.TOOL_FAILED, "message": r["error"]}))
            else:
                emit(LoopEvent(type="tool_result", data={"tool": r["tool"], "result": r["result"][:500]}))
    else:
        results = []

    state.turn_count += 1

    # ── Phase 3: Synthesize ───────────────────────────────
    stop_reason = _check_stop_conditions()
    if stop_reason:
        return stop_reason

    emit(LoopEvent(type="phase", data={"phase": "synthesizing", "message": "Synthesizing results..."}))

    results_text = "\n".join(
        f"Tool: {r['tool']} ({r['description']})\nResult: {r.get('result', r.get('error', 'N/A'))}"
        for r in results
    ) if results else "No tool calls were executed."

    synth_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Task: {params.task}\n\nTool results:\n{results_text}\n\nProvide a final answer."},
    ]

    try:
        async for chunk in stream_chat(
            model=params.model, messages=synth_messages,
            temperature=params.temperature, tools=None, provider=params.provider,
        ):
            if chunk.get("type") == "text":
                text = chunk.get("text", "")
                state.final_response += text
                emit(LoopEvent(type="token", data={"text": text}))
    except Exception as exc:
        emit(LoopEvent(type="error", data={"code": ErrorCode.MODEL_ERROR, "message": str(exc)}))
        return TerminalReason.MODEL_ERROR

    state.messages = [{"role": "user", "content": params.task}, {"role": "assistant", "content": state.final_response}]

    if state.compactor:
        state.messages = state.compactor.compact(
            state.messages, state.compactor.estimate_total_tokens(state.messages),
        )

    return TerminalReason.COMPLETED


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
    import uuid as _uuid
    session_id = _uuid.uuid4().hex[:12]

    # ── Initialize context compactor ───────────────────────
    from ai_workspace.agents.compaction import ContextCompactor
    state.compactor = ContextCompactor()

    # ── Initialize memory tree ────────────────────────────
    from ai_workspace.agents.memory_tree import MemoryTree
    state.memory_tree = MemoryTree()

    # ── Initialize tiered context loader (OpenViking-inspired) ──
    from ai_workspace.agents.tiered_context import TieredContextLoader
    tiered_ctx = TieredContextLoader()
    tiered_ctx.set_task(params.task)
    tiered_ctx.set_system_prompt(params.system_prompt or _DEFAULT_SYSTEM_PROMPT)
    state.tiered_ctx = tiered_ctx

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
            return await _run_plan_execute(params, state, stream_chat, emit)
        elif params.pattern == LoopPattern.REWOO:
            return await _run_rewoo(params, state, stream_chat, emit)
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

    # ── Fire plugin hooks ─────────────────────────────────
    from ai_workspace.plugin_system import fire as _plugin_fire
    _plugin_fire("on_start", task=params.task)

    pattern_task = asyncio.create_task(_run_and_signal())
    while True:
        event = await queue.get()
        if event is None:  # sentinel — pattern finished
            break

        # Grow memory tree from this event
        if state.memory_tree is not None:
            _grow_memory_tree(state.memory_tree, event)

        # Collect events for L1 trace writing
        state._all_events.append(event)

        # Plugin hooks
        try:
            _plugin_fire("on_step", event=event, state=state)
        except Exception:
            pass

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
            "session_id": session_id,
            "trajectory": [
                {"tier": s.tier, "source": s.source, "query": s.query, "score": s.score, "engine": s.engine}
                for s in tiered_ctx.trajectory
            ],
        },
    )
    if params.on_step:
        try:
            params.on_step(done_event)
        except Exception:
            pass
    yield done_event

    # ── Plugin on_finish hook ────────────────────────────────
    try:
        _plugin_fire("on_finish", task=params.task, result=state.final_response, duration_s=0.0)
    except Exception:
        pass

    # ── Write L1 trace to PersistentMemory (post-session) ──
    try:
        from datetime import datetime

        from ai_workspace.agents.memory import PersistentMemory
        from ai_workspace.agents.memory import TraceEvent as L1TraceEvent
        pm = PersistentMemory()
        l1_events = []
        now = datetime.now(UTC).isoformat()
        for event in getattr(state, '_all_events', []):
            l1_events.append(L1TraceEvent(
                timestamp=event.data.get("timestamp", now),
                session_id=session_id,
                type=event.type,
                content=str(event.data)[:2000],
                tool=event.data.get("tool", ""),
                tokens=event.data.get("tokens", 0),
                metadata={"pattern": params.pattern.value, "model": params.model},
            ))
        if l1_events:
            pm.write_l1_trace(session_id, l1_events)
            logger.debug("Wrote %d L1 trace events for session %s", len(l1_events), session_id)
    except Exception as exc:
        logger.debug("Failed to write L1 trace: %s", exc)

    # ── OTel export (post-session) ───────────────────────────
    try:
        from ai_workspace.observability import AgentTrace, OTelExporter
        exporter = OTelExporter()
        if exporter.enabled:
            error_list = []
            for ev in getattr(state, '_all_events', []):
                if ev.type == "error":
                    error_list.append({"code": ev.data.get("code", ""), "message": str(ev.data)[:500]})
            trace = AgentTrace(
                session_id=session_id,
                task=params.task,
                model=params.model,
                provider=params.provider,
                steps=[],  # populated by diff tracker separately
                errors=error_list,
                tokens_used=state.token_count,
                duration_ms=0.0,  # would need start time
            )
            exporter.export(trace)
    except Exception as exc:
        logger.debug("OTel export failed: %s", exc)


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
                    import inspect
                    import json as _json
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
    from ai_workspace.tools.code_tools import _path_sandbox, get_code_tools

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
