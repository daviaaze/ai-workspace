"""Tests for TUI keybindings: ESC cancels agent, Ctrl+C clears input."""

from __future__ import annotations

import asyncio

import pytest

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_escape_cancels_running_agent():
    """ESC calls _cancel_agent when agent is running."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        # Simula agente rodando com uma task real
        async def fake_task():
            # Just exists so _agent_task.done() returns False
            await asyncio.sleep(10)

        app._agent_running = True
        app._agent_task = asyncio.create_task(fake_task())

        await pilot.press("escape")
        await pilot.pause(0.2)

        assert not app._agent_running


@pytest.mark.asyncio
async def test_escape_focuses_input_when_idle():
    """ESC focuses input when no agent is running."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        app._agent_running = False

        await pilot.press("escape")
        await pilot.pause(0.1)

        # Input should have focus
        ta = app.query_one("#task-input")
        assert app.focused == ta


@pytest.mark.asyncio
async def test_ctrl_c_clears_input():
    """Ctrl+C clears the TextArea."""
    from ai_workspace.tui.v5.app import AIWorkspaceApp

    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        ta = app.query_one("#task-input")
        ta.text = "some text here"
        await pilot.pause(0.1)

        await pilot.press("ctrl+c")
        await pilot.pause(0.1)

        assert ta.text == ""
