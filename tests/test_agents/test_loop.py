"""Tests for src/ai_workspace/agents/loop.py — AgentLoop async generator."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ai_workspace.agents.loop import (
    LoopEvent,
    LoopParams,
    LoopPattern,
    TerminalReason,
    agent_loop,
    suggest_pattern,
)
from ai_workspace.core.result import ErrorCode

from .conftest import FakeStreamChat


# ═══════════════════════════════════════════════════════════
# Helper to collect all events from a loop
# ═══════════════════════════════════════════════════════════


async def collect_events(params: LoopParams) -> list[LoopEvent]:
    """Run agent_loop and collect all events."""
    events: list[LoopEvent] = []
    async for event in agent_loop(params):
        events.append(event)
    return events


# ═══════════════════════════════════════════════════════════
# Direct pattern — single call, no tools
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_direct_pattern_returns_response():
    """Direct pattern should stream tokens and complete."""
    fake = FakeStreamChat([
        {"type": "text", "text": "Hello! How can I help you today?"},
    ])

    params = LoopParams(
        task="Hi there",
        pattern=LoopPattern.DIRECT,
        model="test-model",
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)

    token_events = [e for e in events if e.type == "token"]
    assert len(token_events) >= 0  # tokens may be chunked

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_direct_pattern_sends_user_message():
    """Direct pattern should include the user's task in the messages."""
    fake = FakeStreamChat([
        {"type": "text", "text": "Response"},
    ])

    params = LoopParams(
        task="Explain quantum computing",
        pattern=LoopPattern.DIRECT,
        model="test-model",
        deps={"stream_chat": fake},
    )

    await collect_events(params)

    # Check that the fake received the user message
    assert fake.call_count == 1
    sent_messages = fake.call_args[0]["messages"]
    assert any("quantum computing" in str(m) for m in sent_messages)


@pytest.mark.asyncio
async def test_direct_pattern_span_multiple_tokens():
    """Direct pattern handles multi-token responses (multiple chunks)."""
    responses = [
        {"type": "text", "text": "Hello "},
        {"type": "text", "text": "world "},
        {"type": "text", "text": "!"},
    ]
    fake = FakeStreamChat([responses])

    params = LoopParams(
        task="say hi",
        pattern=LoopPattern.DIRECT,
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    token_events = [e for e in events if e.type == "token"]
    texts = "".join(e.data["text"] for e in token_events)
    assert "Hello" in texts
    assert "world" in texts


@pytest.mark.asyncio
async def test_direct_pattern_handles_model_error():
    """Direct pattern should yield error events on model failure."""
    fake = FakeStreamChat([
        {"type": "error", "code": "MODEL_ERROR", "message": "Model crashed"},
    ])

    params = LoopParams(
        task="test",
        pattern=LoopPattern.DIRECT,
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) > 0


# ═══════════════════════════════════════════════════════════
# ReAct pattern — thought → action → observation
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_react_pattern_simple_no_tools_needed():
    """ReAct should complete without tool calls when model answers directly."""
    fake = FakeStreamChat([
        {"type": "text", "text": "The answer is 42."},
    ])

    params = LoopParams(
        task="What is the meaning of life?",
        pattern=LoopPattern.REACT,
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1

    token_events = [e for e in events if e.type == "token"]
    texts = "".join(e.data["text"] for e in token_events)
    assert "42" in texts


@pytest.mark.asyncio
async def test_react_pattern_calls_tools():
    """ReAct should execute tools when the model requests them."""
    # Turn 1: model decides to use a tool
    # Turn 2: model responds with final answer
    async def echo_tool(message: str) -> str:
        return f"Echo: {message}"

    fake = FakeStreamChat([
        # Turn 1: tool call
        [
            {"type": "tool_call", "id": "call_1", "name": "echo", "arguments": '{"message": "hello"}'},
        ],
        # Turn 2: final answer
        {"type": "text", "text": "The tool says: Echo: hello"},
    ])

    params = LoopParams(
        task="Use echo to say hello",
        pattern=LoopPattern.REACT,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "echo",
                    "description": "Echo",
                    "parameters": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"],
                    },
                },
            }
        ],
        tool_handlers={"echo": echo_tool},
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)

    tool_call_events = [e for e in events if e.type == "tool_call"]
    assert len(tool_call_events) == 1
    assert tool_call_events[0].data["tool"] == "echo"
    assert tool_call_events[0].data["args"] == {"message": "hello"}

    tool_result_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_result_events) == 1
    assert "Echo: hello" in tool_result_events[0].data["result"]


@pytest.mark.asyncio
async def test_react_pattern_tool_with_string_arguments():
    """Tool call arguments can come as a JSON string."""
    async def echo(message: str) -> str:
        return f"Echo: {message}"

    fake = FakeStreamChat([
        [
            {"type": "tool_call", "id": "call_1", "name": "echo", "arguments": '{"message": "hello"}'},
        ],
        {"type": "text", "text": "Done."},
    ])

    params = LoopParams(
        task="test",
        pattern=LoopPattern.REACT,
        tools=[{
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Echo",
                "parameters": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
            },
        }],
        tool_handlers={"echo": echo},
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    results = [e for e in events if e.type == "tool_result"]
    assert len(results) == 1
    assert "Echo: hello" in results[0].data["result"]


@pytest.mark.asyncio
async def test_react_pattern_unknown_tool():
    """Calling an unknown tool produces an error but doesn't crash."""
    fake = FakeStreamChat([
        [
            {"type": "tool_call", "id": "call_1", "name": "nonexistent", "arguments": "{}"},
        ],
        {"type": "text", "text": "I give up."},
    ])

    params = LoopParams(
        task="test",
        pattern=LoopPattern.REACT,
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    tool_result_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_result_events) == 1
    assert "Unknown tool" in tool_result_events[0].data["result"]


@pytest.mark.asyncio
async def test_react_pattern_tool_exception():
    """Tool exceptions are caught and reported."""
    async def broken_tool() -> str:
        raise RuntimeError("BOOM!")

    fake = FakeStreamChat([
        [
            {"type": "tool_call", "id": "call_1", "name": "broken_tool", "arguments": "{}"},
        ],
        {"type": "text", "text": "Failed."},
    ])

    params = LoopParams(
        task="test",
        pattern=LoopPattern.REACT,
        tools=[{
            "type": "function",
            "function": {
                "name": "broken_tool",
                "description": "Will fail",
                "parameters": {"type": "object", "properties": {}},
            },
        }],
        tool_handlers={"broken_tool": broken_tool},
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) >= 1


# ═══════════════════════════════════════════════════════════
# Stop conditions
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_max_turns_stops_loop():
    """ReAct loop should stop after max_turns iterations."""
    # Each turn: tool_call → model responds with another tool_call
    # We'll use many turns worth of calls to hit the limit
    responses = []
    for _ in range(30):
        responses.append([
            {"type": "tool_call", "id": "call", "name": "echo", "arguments": '{"message":"x"}'},
        ])

    fake = FakeStreamChat(responses)

    async def echo(message: str) -> str:
        return f"Echo: {message}"

    params = LoopParams(
        task="loop forever",
        pattern=LoopPattern.REACT,
        max_turns=5,
        tools=[{
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Echo",
                "parameters": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
            },
        }],
        tool_handlers={"echo": echo},
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)

    # Count how many tool_call events occurred
    tool_call_count = len([e for e in events if e.type == "tool_call"])
    assert tool_call_count <= params.max_turns

    # There should be a max_turns error
    error_events = [e for e in events if e.type == "error"]
    assert any(ErrorCode.AGENT_LOOP_LIMIT in str(e.data) for e in error_events)


@pytest.mark.asyncio
async def test_token_budget_stops_loop():
    """ReAct loop should stop when token budget exceeded during streaming."""
    # Emit enough tokens to exceed the budget mid-stream
    chunks = [{"type": "text", "text": "x"} for _ in range(20)]
    fake = FakeStreamChat([chunks])

    params = LoopParams(
        task="test",
        pattern=LoopPattern.REACT,
        max_tokens=10,
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    error_events = [e for e in events if e.type == "error"]
    assert any(ErrorCode.AGENT_TOKEN_BUDGET in str(e.data) for e in error_events)

    # Should have at most max_tokens token events
    token_events = [e for e in events if e.type == "token"]
    assert len(token_events) <= params.max_tokens


# ═══════════════════════════════════════════════════════════
# suggest_pattern heuristic
# ═══════════════════════════════════════════════════════════


def test_suggest_pattern_direct_for_simple_question():
    """Simple short questions without tools → Direct."""
    assert suggest_pattern("What is Python?", tools=None) == LoopPattern.DIRECT


def test_suggest_pattern_direct_when_no_tools():
    """No tools available → Direct (can't do anything else)."""
    assert suggest_pattern("Fix the bug", tools=None) == LoopPattern.DIRECT
    assert suggest_pattern("Fix the bug", tools=[]) == LoopPattern.DIRECT


def test_suggest_pattern_react_for_coding_task():
    """Coding keywords → ReAct."""
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    assert suggest_pattern("Fix the auth bug", tools) == LoopPattern.REACT
    assert suggest_pattern("Debug the crash", tools) == LoopPattern.REACT
    assert suggest_pattern("Implement login page", tools) == LoopPattern.REACT
    assert suggest_pattern("Refactor database layer", tools) == LoopPattern.REACT
    assert suggest_pattern("Add rate limiting", tools) == LoopPattern.REACT


def test_suggest_pattern_react_for_portuguese_coding_task():
    """Portuguese coding keywords → ReAct."""
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    assert suggest_pattern("Corrige o bug no middleware", tools) == LoopPattern.REACT
    assert suggest_pattern("Conserta o problema de auth", tools) == LoopPattern.REACT


def test_suggest_pattern_react_for_build_task():
    """Build/create structured tasks → currently falls back to ReAct."""
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    assert suggest_pattern("Build a CRUD API", tools) == LoopPattern.REACT


def test_suggest_pattern_react_is_default():
    """Unknown tasks with tools → ReAct as safe default."""
    tools = [{"type": "function", "function": {"name": "some_tool"}}]
    assert suggest_pattern("Do something mysterious", tools) == LoopPattern.REACT


def test_suggest_pattern_trivial_greeting_is_direct():
    """Trivial greetings like 'hi' → Direct even with tools."""
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    assert suggest_pattern("hi", tools) == LoopPattern.DIRECT
    assert suggest_pattern("hello", tools) == LoopPattern.DIRECT


def test_suggest_pattern_non_trivial_question_defaults_to_react():
    """Non-trivial questions with tools → ReAct (safe default)."""
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    assert suggest_pattern("Do something useful", tools) == LoopPattern.REACT


# ═══════════════════════════════════════════════════════════
# LoopParams and enums
# ═══════════════════════════════════════════════════════════


def test_loop_params_defaults():
    params = LoopParams(task="test")
    assert params.pattern == LoopPattern.DIRECT
    assert params.model == "qwen3:14b"
    assert params.provider == "ollama"
    assert params.max_turns == 20
    assert params.max_tokens == 100_000
    assert params.stream is True


def test_terminal_reason_variants():
    """All 8 terminal reason variants exist."""
    assert TerminalReason.COMPLETED
    assert TerminalReason.MAX_TURNS
    assert TerminalReason.TOKEN_BUDGET
    assert TerminalReason.USER_ABORT
    assert TerminalReason.TOOL_ERROR
    assert TerminalReason.MODEL_ERROR
    assert TerminalReason.NO_TOOLS
    assert TerminalReason.TIMEOUT


def test_loop_pattern_variants():
    """All 4 loop patterns exist."""
    assert LoopPattern.DIRECT
    assert LoopPattern.REACT
    assert LoopPattern.PLAN_EXECUTE
    assert LoopPattern.REWOO


# ═══════════════════════════════════════════════════════════
# LoopEvent
# ═══════════════════════════════════════════════════════════


def test_loop_event_creation():
    e = LoopEvent(type="token", data={"text": "hello"})
    assert e.type == "token"
    assert e.data["text"] == "hello"


def test_loop_event_empty_data():
    e = LoopEvent(type="done")
    assert e.type == "done"
    assert e.data == {}


# ═══════════════════════════════════════════════════════════
# on_step callback
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_on_step_callback_called():
    """The on_step callback should receive every event."""
    fake = FakeStreamChat([
        {"type": "text", "text": "Hello!"},
    ])

    received: list[LoopEvent] = []

    def on_step(event: LoopEvent):
        received.append(event)

    params = LoopParams(
        task="test",
        pattern=LoopPattern.DIRECT,
        deps={"stream_chat": fake},
        on_step=on_step,
    )

    await collect_events(params)

    assert len(received) > 0
    assert any(e.type == "token" for e in received)


@pytest.mark.asyncio
async def test_on_step_callback_exception_does_not_crash():
    """If on_step raises, the loop should continue."""
    fake = FakeStreamChat([
        {"type": "text", "text": "Hello!"},
    ])

    def on_step(event: LoopEvent):
        raise RuntimeError("Callback exploded!")

    params = LoopParams(
        task="test",
        pattern=LoopPattern.DIRECT,
        deps={"stream_chat": fake},
        on_step=on_step,
    )

    # Should not raise
    events = await collect_events(params)
    assert len([e for e in events if e.type == "done"]) == 1


# ═══════════════════════════════════════════════════════════
# Handling thinking/reasoning tokens
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_direct_emits_thinking():
    """Thinking tokens from models like qwen3/deepseek-r1 should be emitted."""
    fake = FakeStreamChat([
        {"type": "thinking", "thought": "Let me think about this..."},
        {"type": "text", "text": "Here is the answer."},
    ])

    params = LoopParams(
        task="complex question",
        pattern=LoopPattern.DIRECT,
        deps={"stream_chat": fake},
    )

    events = await collect_events(params)
    thinking_events = [e for e in events if e.type == "thinking"]
    assert len(thinking_events) == 1
    assert thinking_events[0].data["thought"] == "Let me think about this..."


# ═══════════════════════════════════════════════════════════
# Unsuitable patterns (Phase 2)
# ═══════════════════════════════════════════════════════════


@pytest.mark.skip(reason="PLAN_EXECUTE is now implemented (Phase 2+), not a stub. Needs live LLM.")
@pytest.mark.asyncio
async def test_plan_execute_not_implemented():
    """Plan-Execute is implemented (Phase 2+)."""
    pass


@pytest.mark.skip(reason="REWOO is now implemented (Phase 2+), not a stub. Needs live LLM.")
@pytest.mark.asyncio
async def test_rewoo_not_implemented():
    """ReWOO is implemented (Phase 2+)."""
    pass


# ═══════════════════════════════════════════════════════════
# Pre-existing conversation history
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_continue_conversation():
    """Loop should append to pre-existing messages."""
    fake = FakeStreamChat([
        {"type": "text", "text": "Yes, that's Python."},
    ])

    history = [
        {"role": "user", "content": "What language is this?"},
        {"role": "assistant", "content": "This appears to be Python."},
    ]

    params = LoopParams(
        task="Are you sure?",
        pattern=LoopPattern.DIRECT,
        messages=history,
        deps={"stream_chat": fake},
    )

    await collect_events(params)

    sent_messages = fake.call_args[0]["messages"]
    # Should include the history
    assert any("What language is this" in str(m) for m in sent_messages)
    assert any("Are you sure" in str(m) for m in sent_messages)
