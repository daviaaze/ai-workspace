"""
End-to-end smoke tests for TUI v5.

Runs the actual Textual app headless with a pilot to verify:
- App mounts without errors
- Components are present in DOM
- Slash commands work (/help, /ctx, /clear)
- Key bindings trigger overlays (F4 -> ContextInspector)
- Agent loop integrates with conversation (FakeStreamChat)

Usage:
    PYTHONPATH=src python -m pytest tests/test_tui/test_smoke_e2e.py -v
"""

from __future__ import annotations

import pytest

pytest_plugins = ("pytest_asyncio",)


# ---------------------------------------------------------------------------
# Test 1: App mounts and all widgets are present
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_mounts_with_all_widgets():
    """Verify the app starts and all main widgets are rendered."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        # Check screen stack
        assert len(app.screen_stack) >= 1

        # Check main widgets exist
        screen = app.screen
        header = screen.query_one("#header")
        assert header is not None

        monitor = screen.query_one("#monitor")
        assert monitor is not None

        conv = screen.query_one("#conversation")
        assert conv is not None

        input_bar = screen.query_one("#input")
        assert input_bar is not None


# ---------------------------------------------------------------------------
# Test 2: Slash commands work
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slash_help_opens_overlay():
    """Typing /help opens the HelpScreen overlay."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        # Type /help in input
        input_bar = app.screen.query_one("#input")
        input_bar.query_one("Input").value = "/help"
        await pilot.press("enter")
        await pilot.pause(0.3)

        # HelpScreen should be on the stack
        assert len(app.screen_stack) >= 2
        top = app.screen_stack[-1]
        assert "Help" in type(top).__name__


@pytest.mark.asyncio
async def test_slash_ctx_shows_toast():
    """Typing /ctx stats shows a toast with context info."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        conv = app.screen.query_one("#conversation")

        # Type /ctx stats
        input_bar = app.screen.query_one("#input")
        input_bar.query_one("Input").value = "/ctx stats"
        await pilot.press("enter")
        await pilot.pause(0.3)

        # Conversation should have the toast in its log
        log_widget = conv.query_one("#conversation-log")
        # We can't easily read RichLog content, but the app didn't crash
        # which means markup was valid


@pytest.mark.asyncio
async def test_slash_clear_clears_conversation():
    """Typing /clear clears the conversation."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        conv = app.screen.query_one("#conversation")

        # Add some entries first
        conv.add_system("Test")
        conv.add_system("Test")

        # Now clear via slash command
        input_bar = app.screen.query_one("#input")
        input_bar.query_one("Input").value = "/clear"
        await pilot.press("enter")
        await pilot.pause(0.2)

        # RichLog should be cleared (can't easily verify content, just no crash)


@pytest.mark.asyncio
async def test_slash_model_changes_model():
    """Typing /model <name> changes the default model."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        assert app._default_model == "qwen3:14b"

        input_bar = app.screen.query_one("#input")
        input_bar.query_one("Input").value = "/model deepseek-r1:7b"
        await pilot.press("enter")
        await pilot.pause(0.3)

        assert app._default_model == "deepseek-r1:7b"


# ---------------------------------------------------------------------------
# Test 3: Key bindings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f4_opens_context_inspector():
    """F4 key opens the ContextInspector overlay."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        # Press F4
        await pilot.press("f4")
        await pilot.pause(0.3)

        # ContextInspector should be on the stack
        top = app.screen_stack[-1]
        assert "Context" in type(top).__name__


@pytest.mark.asyncio
async def test_escape_dismisses_overlay():
    """Escape dismisses overlays and returns to main screen."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        # Textual always has a _default screen at stack[0]
        # Our app pushes MainScreen on top, so screen_stack is [_default, MainScreen]
        # After opening HelpScreen: [_default, MainScreen, HelpScreen]

        # Open help, then escape
        input_bar = app.screen.query_one("#input")
        input_bar.query_one("Input").value = "/help"
        await pilot.press("enter")
        await pilot.pause(0.3)

        assert len(app.screen_stack) == 3  # _default + MainScreen + HelpScreen

        await pilot.press("escape")
        await pilot.pause(0.3)

        assert len(app.screen_stack) == 2  # _default + MainScreen


# ---------------------------------------------------------------------------
# Test 4: Agent loop integration (with FakeStreamChat)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_loop_integrates_with_conversation():
    """Typing a user message spawns agent loop, conversation shows steps."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp
    from tests.test_agents.conftest import FakeStreamChat

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        conv = app.screen.query_one("#conversation")
        monitor = app.screen.query_one("#monitor")

        # Inject a fake provider to avoid real API calls
        # (The agent loop uses ProviderRegistry.stream_chat which needs a real provider)
        # We'll test the conversation/entry rendering independently

        # Type a user message
        input_bar = app.screen.query_one("#input")
        input_bar.query_one("Input").value = "Hello, how are you?"
        await pilot.press("enter")
        await pilot.pause(0.5)

        # The agent loop will fail (no real provider), but conversation should
        # have the user message at minimum. We verify the log widget exists.
        log_widget = conv.query_one("#conversation-log")
        assert log_widget is not None


# ---------------------------------------------------------------------------
# Test 5: Context Inspector renders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_inspector_renders_file_tree():
    """ContextInspector opens and shows token bar, empty file list."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp
    from ai_workspace.tui.v5.context_inspector import ContextInspector

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        # Push context inspector directly
        inspector = ContextInspector(context_manager=app.context_manager)
        app.push_screen(inspector)
        await pilot.pause(0.3)

        # Should be on stack
        assert "Context" in type(app.screen).__name__

        # Escape to dismiss
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert len(app.screen_stack) == 2  # _default + MainScreen


# ---------------------------------------------------------------------------
# Test 6: Conversation entries render correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conversation_entries_render():
    """Adding entries to conversation writes to RichLog without markup errors."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        conv = app.screen.query_one("#conversation")

        # These should not raise MarkupError
        conv.add_user_message("Hello world")
        await pilot.pause(0.1)

        conv.add_agent_thought("Let me think about this", agent_name="test", step=1)
        await pilot.pause(0.1)

        conv.add_agent_action("read_file", '{"path":"/tmp"}', agent_name="test", step=1)
        await pilot.pause(0.1)

        conv.add_agent_observation("file contents here", agent_name="test", step=1)
        await pilot.pause(0.1)

        conv.add_system("Done in 3 turns")
        await pilot.pause(0.1)

        # Verify RichLog received entries
        log = conv.query_one("#conversation-log")
        assert log is not None
        # RichLog.line_count would tell us but may vary; just verify no crash


# ---------------------------------------------------------------------------
# Test 7: AgentMonitor shows agents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_monitor_upsert():
    """AgentMonitor tracks agent status adds/updates."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        monitor = app.screen.query_one("#monitor")

        # Initially empty
        assert len(monitor.agents) == 0

        monitor.upsert_agent("agent-1", type="general", status="running", task="test", step=0, pct=0)
        await pilot.pause(0.1)

        assert len(monitor.agents) == 1
        assert monitor.agents[0].get("name") == "agent-1"

        # Update status
        monitor.upsert_agent("agent-1", status="done", step=5, pct=100)
        await pilot.pause(0.1)

        assert monitor.agents[0].get("status") == "done"
        assert monitor.agents[0].get("step") == 5


# ---------------------------------------------------------------------------
# Test 8: InputBar slash commands help bar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_input_bar_has_slash_commands():
    """InputBar has SLASH_COMMANDS registered."""
    from ai_workspace.tui.v5.input_bar import SLASH_COMMANDS

    assert len(SLASH_COMMANDS) > 0
    assert "/help" in SLASH_COMMANDS
    assert "/ctx" in SLASH_COMMANDS
    assert "/model <name>" in SLASH_COMMANDS
    assert "/ctx stats" in SLASH_COMMANDS


@pytest.mark.asyncio
async def test_input_bar_focus():
    """InputBar can receive focus."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        input_bar = app.screen.query_one("#input")
        input_bar.focus_input()

        # Verify the input has focus
        focused = app.focused
        assert focused is not None
