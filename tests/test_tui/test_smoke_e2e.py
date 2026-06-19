"""
End-to-end smoke tests for TUI v5.

Runs the actual Textual app headless with a pilot to verify:
- App mounts without errors
- Core widgets are present in DOM
- Slash commands work (/help, /ctx, /clear, /model)
- Key bindings work (Ctrl+M model selector)
- Conversation components render correctly
"""

from __future__ import annotations

import pytest

pytest_plugins = ("pytest_asyncio",)


# ---------------------------------------------------------------------------
# App mount
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_mounts():
    """App starts and main widgets are rendered."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.5)

        assert len(app.screen_stack) >= 1
        assert app.query_one("Header") is not None
        assert app.query_one("#conv") is not None
        assert app.query_one("#task-input") is not None
        assert app.query_one("#status-bar") is not None


# ---------------------------------------------------------------------------
# Input / TextArea
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_textarea_accepts_input():
    """TextArea widget accepts typing."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "Hello agent!"
        await pilot.pause(0.1)
        assert ta.text == "Hello agent!"


@pytest.mark.asyncio
async def test_textarea_multi_line():
    """TextArea supports multiple lines."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "line one\nline two\nline three"
        await pilot.pause(0.1)
        assert ta.text.count("\n") == 2


# ---------------------------------------------------------------------------
# Autocomplete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_autocomplete_on_slash():
    """Typing / shows autocomplete popup with commands."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "/"
        await pilot.pause(0.2)

        ac = app.query_one("#autocomplete")
        assert ac.has_class("-visible")
        items = list(ac.query("ListView ListItem"))
        assert len(items) > 1


@pytest.mark.asyncio
async def test_autocomplete_filters():
    """Autocomplete filters commands as you type."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "/mo"
        await pilot.pause(0.2)

        ac = app.query_one("#autocomplete")
        assert ac.has_class("-visible")
        items = list(ac.query("ListView ListItem"))
        assert len(items) >= 1
        text = str(items[0].children[0].render()) if items else ""
        assert "model" in text.lower()


@pytest.mark.asyncio
async def test_autocomplete_hides_without_slash():
    """Without / prefix, autocomplete is hidden."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "hello world"
        await pilot.pause(0.2)

        ac = app.query_one("#autocomplete")
        assert not ac.has_class("-visible")


# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slash_help():
    """Typing /help and submitting shows help in conversation."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "/help"
        await pilot.pause(0.1)
        await pilot.press("ctrl+enter")
        await pilot.pause(0.3)

        # Help should be in conversation
        conv = app.query_one("#conv")
        assert len(list(conv.children)) > 0


@pytest.mark.asyncio
async def test_slash_clear():
    """/clear clears the conversation."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        conv = app.query_one("#conv")
        conv.add_system("Test message")
        await pilot.pause(0.1)
        assert len(list(conv.children)) > 0

        ta = app.query_one("#task-input")
        ta.text = "/clear"
        await pilot.press("ctrl+enter")
        await pilot.pause(0.2)

        # Conversation should be cleared
        conv_children = list(conv.children)
        # Only Autocomplete (if mounted as child of conv) remains
        assert len(conv_children) == 0 or all(
            c.__class__.__name__ == "Autocomplete"
            for c in conv_children
        )


@pytest.mark.asyncio
async def test_slash_model():
    """/model sets the default model."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        assert app._model == "qwen3:14b"

        ta = app.query_one("#task-input")
        ta.text = "/model deepseek-r1:7b"
        await pilot.press("ctrl+enter")
        await pilot.pause(0.3)

        assert app._model == "deepseek-r1:7b"


@pytest.mark.asyncio
async def test_slash_model_without_args():
    """/model without args opens model selector overlay."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "/model"
        await pilot.press("ctrl+enter")
        await pilot.pause(0.5)

        top = app.screen_stack[-1]
        assert "Model" in type(top).__name__


@pytest.mark.asyncio
async def test_slash_unknown():
    """Unknown slash command shows warning."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "/nonexistent"
        await pilot.press("ctrl+enter")
        await pilot.pause(0.3)

        # Should not crash


# ---------------------------------------------------------------------------
# Key bindings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ctrl_m_opens_model_select():
    """Ctrl+M opens ModelSelect overlay."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        await pilot.press("ctrl+m")
        await pilot.pause(0.4)

        top = app.screen_stack[-1]
        assert "Model" in type(top).__name__


@pytest.mark.asyncio
async def test_escape_dismisses_overlay():
    """Escape dismisses overlays."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        await pilot.press("ctrl+m")
        await pilot.pause(0.3)

        await pilot.press("escape")
        await pilot.pause(0.3)

        # Only _default + MainScreen remain
        assert len(app.screen_stack) <= 2


# ---------------------------------------------------------------------------
# Conversation components
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conversation_user_message():
    """User messages appear in conversation."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        conv = app.query_one("#conv")
        conv.add_user("Hello")
        await pilot.pause(0.1)

        children = list(conv.children)
        assert any("UserMessage" in c.__class__.__name__ for c in children)


@pytest.mark.asyncio
async def test_conversation_thought():
    """Thought messages appear."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        conv = app.query_one("#conv")
        # Use the internal method
        from ai_workspace.tui.v5.conversation import AgentThought
        # Direct mount
        conv.mount(AgentThought("test thought", step=1))
        await pilot.pause(0.1)

        assert any("AgentThought" in c.__class__.__name__ for c in conv.children)


@pytest.mark.asyncio
async def test_conversation_tool_call():
    """Tool call widget works."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        conv = app.query_one("#conv")
        conv.add_tool_call("test_tool", '"arg1"', step=1)
        await pilot.pause(0.1)

        assert any("ToolCall" in c.__class__.__name__ for c in conv.children)


@pytest.mark.asyncio
async def test_conversation_streaming():
    """Streaming agent response appends tokens."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        conv = app.query_one("#conv")
        conv.start_response()
        conv.append_token("Hello")
        conv.append_token(" world")
        await pilot.pause(0.1)

        # AgentResponse should exist with content
        from ai_workspace.tui.v5.conversation import AgentResponse
        for c in conv.children:
            if isinstance(c, AgentResponse):
                assert "Hello world" in c.content
                break
        else:
            pytest.fail("No AgentResponse found")


# ---------------------------------------------------------------------------
# Status bar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_bar_updates():
    """Status bar shows/hides correctly."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        sb = app.query_one("#status-bar")
        assert not sb.has_class("-visible")

        app._show_status("[#D4A853]● Agent running[/]", visible=True)
        await pilot.pause(0.1)

        assert sb.has_class("-visible")
        # Check content via render()
        rendered = sb.render()
        assert "Agent" in str(rendered)
