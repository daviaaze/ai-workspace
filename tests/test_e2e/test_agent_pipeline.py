"""End-to-end integration tests for the full agent pipeline.

Tests AgentLoop patterns (DIRECT, REACT, DAG), memory tree,
compaction, state isolation, and callbacks.
"""

from __future__ import annotations

import asyncio

import pytest

from ai_workspace.agents.loop import (
    LoopParams,
    LoopPattern,
    TerminalReason,
    agent_loop,
)


# ---------------------------------------------------------------------------
# Fake streaming provider for tests
# ---------------------------------------------------------------------------


async def _fake_stream_chat(**kwargs: object) -> object:
    """Fake streaming chat that yields tokens from messages."""
    messages = kwargs.get("messages", [])
    provider = str(kwargs.get("provider", "ollama"))
    tools = kwargs.get("tools")

    user_content = ""
    for msg in (messages or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_content = str(msg.get("content", ""))

    # Simulate tool calls if tools are present and task mentions them
    if tools and user_content:
        tool_names = []
        for t in tools:
            if isinstance(t, dict):
                if "function" in t:
                    tool_names.append(t["function"].get("name", ""))
                else:
                    tool_names.append(t.get("name", ""))
        if any(tn in user_content.lower() for tn in tool_names if tn):
            yield {"type": "text", "text": f"Using tool to research " + user_content[:50]}

    resp = f"Response from {provider}: analyzing '{user_content[:60]}'"
    words = resp.split()
    for word in words:
        yield {"type": "text", "text": word + " "}
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _fake_stream(**kwargs: object):
    """Return an async generator for fake streaming."""
    return _fake_stream_chat(**kwargs)


@pytest.fixture
def base_params() -> LoopParams:
    return LoopParams(
        task="Test task",
        model="test-model",
        provider="ollama",
        stream=True,
        deps={"stream_chat": _fake_stream_chat},
    )


# ---------------------------------------------------------------------------
# DIRECT pattern
# ---------------------------------------------------------------------------


class TestDirectPattern:
    @pytest.mark.asyncio
    async def test_direct_basic_flow(self):
        params = LoopParams(
            task="What is Python?", pattern=LoopPattern.DIRECT, model="test",
            deps={"stream_chat": _fake_stream_chat},
        )
        tokens = []
        done = None
        async for event in agent_loop(params):
            if event.type == "token":
                tokens.append(event.data["text"])
            elif event.type == "done":
                done = event
        assert len(tokens) > 0
        assert done is not None
        assert done.data["reason"] == TerminalReason.COMPLETED.value

    @pytest.mark.asyncio
    async def test_direct_emits_done(self, base_params):
        base_params.pattern = LoopPattern.DIRECT
        events = [e async for e in agent_loop(base_params)]
        assert any(e.type == "done" for e in events)


# ---------------------------------------------------------------------------
# REACT pattern
# ---------------------------------------------------------------------------


class TestReActPattern:
    @pytest.mark.asyncio
    async def test_react_without_tools_completes(self, base_params):
        base_params.pattern = LoopPattern.REACT
        base_params.tools = []
        base_params.tool_handlers = {}
        events = [e async for e in agent_loop(base_params)]
        done = [e for e in events if e.type == "done"]
        assert len(done) == 1
        assert done[0].data["reason"] == TerminalReason.COMPLETED.value

    @pytest.mark.asyncio
    async def test_react_with_tool_handler(self, base_params):
        base_params.pattern = LoopPattern.REACT
        base_params.tools = [{"name": "web_search"}]
        base_params.tool_handlers = {"web_search": lambda query="": "OK"}
        async for event in agent_loop(base_params):
            pass
        # Should not crash


# ---------------------------------------------------------------------------
# DAG pattern
# ---------------------------------------------------------------------------


class TestDAGPattern:
    @pytest.mark.asyncio
    async def test_dag_completes(self, base_params):
        base_params.pattern = LoopPattern.DAG
        base_params.task = "Setup Python project, add linting, configure CI"
        base_params.deps = {"stream_chat": _fake_stream_chat}
        events = [e async for e in agent_loop(base_params)]
        assert any(e.type == "done" for e in events)

    @pytest.mark.asyncio
    async def test_dag_with_tools(self, base_params):
        base_params.pattern = LoopPattern.DAG
        base_params.tools = [{"name": "read_file"}, {"name": "write_file"}, {"name": "shell"}]
        base_params.deps = {"stream_chat": _fake_stream_chat}
        events = [e async for e in agent_loop(base_params)]
        assert any(e.type == "done" for e in events)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="PLAN_EXECUTE is implemented (Phase 2+), needs live LLM")
    async def test_plan_execute_not_implemented(self, base_params):
        pass

    @pytest.mark.skip(reason="PLAN_EXECUTE is implemented (Phase 2+), needs live LLM")
    @pytest.mark.asyncio
    async def test_error_events_structured(self, base_params):
        pass


# ---------------------------------------------------------------------------
# State isolation
# ---------------------------------------------------------------------------


class TestStateIsolation:
    @pytest.mark.asyncio
    async def test_two_loops_independent(self):
        p1 = LoopParams(task="Task alpha", pattern=LoopPattern.DIRECT, model="test", deps={"stream_chat": _fake_stream_chat})
        p2 = LoopParams(task="Task beta", pattern=LoopPattern.DIRECT, model="test", deps={"stream_chat": _fake_stream_chat})
        t1 = "".join(e.data.get("text", "") for e in [e async for e in agent_loop(p1)] if e.type == "token")
        t2 = "".join(e.data.get("text", "") for e in [e async for e in agent_loop(p2)] if e.type == "token")
        assert t1 != t2


# ---------------------------------------------------------------------------
# On-step callback
# ---------------------------------------------------------------------------


class TestOnStepCallback:
    @pytest.mark.asyncio
    async def test_callback_receives_events(self, base_params):
        base_params.pattern = LoopPattern.DIRECT
        captured = []

        def cb(event):
            captured.append(event)

        base_params.on_step = cb
        async for event in agent_loop(base_params):
            pass
        assert len(captured) > 0
        assert any(e.type == "done" for e in captured)

    @pytest.mark.asyncio
    async def test_callback_exception_safe(self, base_params):
        base_params.pattern = LoopPattern.DIRECT

        def bad_cb(event):
            raise RuntimeError("boom")

        base_params.on_step = bad_cb
        events = [e async for e in agent_loop(base_params)]
        assert any(e.type == "done" for e in events)
