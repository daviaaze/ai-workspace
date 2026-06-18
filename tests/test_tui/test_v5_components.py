"""Tests for TUI v5 component logic.

Tests the data structures and rendering logic that work without
a running Textual app context. Widget lifecycle methods that require
an active app (mount, remove_children) are guarded in the implementation.
"""

from __future__ import annotations

import pytest

from ai_workspace.tui.v5.conversation import ConversationEntry
from ai_workspace.tui.v5.agent_monitor import AgentMonitor


# ---------------------------------------------------------------------------
# ConversationEntry rendering
# ---------------------------------------------------------------------------


class TestConversationEntry:

    def test_user_message(self):
        e = ConversationEntry(role="user", content="Hello, fix the bug")
        rendered = e.render()
        assert "You:" in rendered
        assert "fix the bug" in rendered

    def test_agent_result(self):
        e = ConversationEntry(role="result", content="The bug is in auth.py", agent_name="agent-1")
        rendered = e.render()
        assert "agent-1" in rendered
        assert "auth.py" in rendered

    def test_agent_thought(self):
        e = ConversationEntry(role="thought", content="I need to read the file", step=2)
        rendered = e.render()
        assert "Step 2" in rendered
        assert "read the file" in rendered

    def test_agent_action(self):
        e = ConversationEntry(role="action", content='"auth.py"', tool_name="read_file", step=1)
        rendered = e.render()
        assert "Step 1" in rendered
        assert "read_file" in rendered

    def test_agent_observation(self):
        e = ConversationEntry(role="observation", content="def login(): pass", step=1)
        rendered = e.render()
        assert "Step 1" in rendered
        assert "def login" in rendered

    def test_observation_truncated(self):
        long_content = "data " * 200
        e = ConversationEntry(role="observation", content=long_content)
        rendered = e.render()
        assert len(rendered) < len(long_content) + 100

    def test_error(self):
        e = ConversationEntry(role="error", content="Tool execution failed")
        rendered = e.render()
        assert "Error:" in rendered
        assert "Tool execution failed" in rendered

    def test_system(self):
        e = ConversationEntry(role="system", content="Agent spawned")
        rendered = e.render()
        assert "Agent spawned" in rendered

    def test_unknown_role(self):
        e = ConversationEntry(role="custom", content="Raw text")
        rendered = e.render()
        assert "Raw text" in rendered


# ---------------------------------------------------------------------------
# AgentMonitor data logic (widget guards NoActiveAppError)
# ---------------------------------------------------------------------------


class TestAgentMonitorLogic:

    def test_empty_monitor(self):
        monitor = AgentMonitor()
        assert monitor.agents == []

    def test_upsert_new_agent(self):
        monitor = AgentMonitor()
        monitor.upsert_agent("agent-1", type="coding", status="running", task="Fix auth", step=2)
        assert len(monitor.agents) == 1
        assert monitor.agents[0]["name"] == "agent-1"
        assert monitor.agents[0]["type"] == "coding"
        assert monitor.agents[0]["status"] == "running"

    def test_upsert_updates_existing(self):
        monitor = AgentMonitor()
        monitor.upsert_agent("agent-1", status="running", step=1)
        monitor.upsert_agent("agent-1", status="running", step=2, pct=50)
        assert len(monitor.agents) == 1
        assert monitor.agents[0]["step"] == 2
        assert monitor.agents[0]["pct"] == 50

    def test_upsert_multiple_agents(self):
        monitor = AgentMonitor()
        monitor.upsert_agent("agent-1", type="coding")
        monitor.upsert_agent("agent-2", type="research")
        assert len(monitor.agents) == 2

    def test_remove_agent(self):
        monitor = AgentMonitor()
        monitor.upsert_agent("agent-1")
        monitor.upsert_agent("agent-2")
        monitor.remove_agent("agent-1")
        assert len(monitor.agents) == 1
        assert monitor.agents[0]["name"] == "agent-2"

    def test_remove_nonexistent(self):
        monitor = AgentMonitor()
        monitor.upsert_agent("agent-1")
        monitor.remove_agent("agent-2")
        assert len(monitor.agents) == 1

    def test_upsert_preserves_other(self):
        monitor = AgentMonitor()
        monitor.upsert_agent("a", status="idle")
        monitor.upsert_agent("b", status="idle")
        monitor.upsert_agent("a", status="running")
        a = [ag for ag in monitor.agents if ag["name"] == "a"][0]
        b = [ag for ag in monitor.agents if ag["name"] == "b"][0]
        assert a["status"] == "running"
        assert b["status"] == "idle"
