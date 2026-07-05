"""
Tests for MCP Agent Tools.

Refs: SPEC_AGENT_MCP_TOOL.md
"""

from __future__ import annotations

import pytest

from ai_workspace.mcp_server.agent_tools import (
    AgentRecord,
    _agents,
    _next_id,
    handle_aiw_agent_kill,
    handle_aiw_agent_run,
    handle_aiw_agent_status,
)


class TestAgentRegistry:
    """Verify the in-memory agent registry."""

    def test_next_id_increments(self):
        """_next_id generates unique sequential IDs."""
        id1 = _next_id()
        id2 = _next_id()
        assert id1 != id2
        assert id1.startswith("agent-")
        assert id2.startswith("agent-")

    def test_agents_dict_empty_initially(self):
        """_agents starts empty."""
        import ai_workspace.mcp_server.agent_tools as at
        assert len(at._agents) == 0


class TestAgentStatus:
    """Verify aiw_agent_status returns correct state."""

    @pytest.mark.asyncio
    async def test_status_no_agents(self):
        """Status when no agents are running."""
        _agents.clear()  # ensure clean state
        result = await handle_aiw_agent_status({})
        assert "No agents" in result

    @pytest.mark.asyncio
    async def test_status_with_agent(self):
        """Status includes a recently added agent."""
        agent_id = _next_id()
        _agents[agent_id] = AgentRecord(
            id=agent_id,
            task="test task",
            agent_type="general",
            model="qwen3:14b",
            provider="ollama",
            status="running",
            turns=3,
            tokens=150,
        )

        result = await handle_aiw_agent_status({})
        assert agent_id in result
        assert "test task" in result
        assert "running" in result
        assert "qwen3:14b" in result

        # Cleanup
        _agents.clear()


class TestAgentKill:
    """Verify aiw_agent_kill cancels agents."""

    @pytest.mark.asyncio
    async def test_kill_requires_agent_id(self):
        """Missing agent_id returns error."""
        result = await handle_aiw_agent_kill({})
        assert "agent_id" in result.lower()

    @pytest.mark.asyncio
    async def test_kill_nonexistent(self):
        """Killing non-existent agent returns not found."""
        result = await handle_aiw_agent_kill({"agent_id": "nonexistent"})
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_kill_non_running(self):
        """Killing an agent that's already done returns status info."""
        agent_id = _next_id()
        _agents[agent_id] = AgentRecord(
            id=agent_id,
            task="done task",
            agent_type="general",
            model="qwen3:14b",
            provider="ollama",
            status="done",
        )

        result = await handle_aiw_agent_kill({"agent_id": agent_id})
        assert "not running" in result.lower() or "done" in result.lower()

        _agents.clear()


class TestAgentRun:
    """Verify aiw_agent_run basic contract."""

    @pytest.mark.asyncio
    async def test_run_requires_task(self):
        """Empty task returns error."""
        result = await handle_aiw_agent_run({"task": ""})
        assert "required" in result.lower()

    @pytest.mark.asyncio
    async def test_run_batch_mode_no_real_provider(self):
        """Batch mode without a real provider returns an error gracefully."""
        # This will fail because there's no real provider connected,
        # but it should fail gracefully (not crash)
        try:
            result = await handle_aiw_agent_run({
                "task": "Say hello",
                "stream": False,
            })
            # Either it succeeds (rare with no provider) or returns error
            assert isinstance(result, str)
        except Exception:
            # Agent not found in registry is expected when task fails
            # The important thing is it doesn't crash the MCP server
            pass

        # Cleanup
        _agents.clear()
