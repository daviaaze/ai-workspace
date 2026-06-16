"""
TUI snapshot tests — capture visual state of the agent operations center.

Uses Textual's run_test() + pytest-textual-snapshot for SVG screenshots.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Requires terminal — run with: pytest tests/test_tui/ -k tui --snapshot-update")
class TestTUI:
    """TUI visual tests using Textual's testing framework."""

    async def test_app_launches(self):
        """Verify the TUI app starts without errors."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            assert pilot.app is not None
            assert "AI Workspace" in pilot.app.TITLE
            await pilot.pause()

    async def test_status_bar_shows_data(self):
        """Status bar shows workspace, tasks, agents."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            from ai_workspace.tui.widgets import StatusBar
            bar = pilot.app.query_one(StatusBar)
            assert bar.workspace is not None
            assert bar.tasks_total >= 0
            await pilot.pause()

    async def test_task_panel_renders(self):
        """Task panel shows demo tasks."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            from ai_workspace.tui.widgets import TaskPanel
            panel = pilot.app.query_one(TaskPanel)
            assert panel is not None
            await pilot.pause()

    async def test_keybinding_cycle_focus(self):
        """Tab cycles through panels."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("tab")
            await pilot.pause()
            # Should not crash
            assert True

    async def test_spawn_dialog(self):
        """Ctrl+S opens spawn dialog."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("ctrl+s")
            await pilot.pause()
            # SpawnDialog should appear
            from ai_workspace.tui.app import SpawnDialog
            dialog = pilot.app.query_one(SpawnDialog)
            assert dialog is not None

    async def test_command_palette(self):
        """: opens command palette."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press(":")
            await pilot.pause()
            from ai_workspace.tui.widgets import CommandPalette
            cp = pilot.app.query_one(CommandPalette)
            assert cp is not None

    async def test_toggle_thinking(self):
        """Ctrl+T toggles thinking visibility."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("ctrl+t")  # Once: focused agent
            await pilot.pause()
            await pilot.press("ctrl+t")  # Twice: all agents
            await pilot.pause()
            await pilot.press("ctrl+t")  # Again: hide all
            await pilot.pause()
            assert True  # No crash

    async def test_quit(self):
        """q or Ctrl+C quits the app."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("q")
            # App should exit cleanly


@pytest.mark.skip(reason="Snapshot comparison — run with: pytest tests/test_tui/ --snapshot-update")
class TestTUISnapshots:
    """Visual regression tests that compare SVG snapshots."""

    async def test_default_layout_snapshot(self, snapshot):
        """Snapshot of the default TUI layout."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert snapshot == pilot.app.screen._render()

    async def test_spawn_dialog_open_snapshot(self, snapshot):
        """Snapshot with spawn dialog open."""
        from ai_workspace.tui.app import AIWorkspaceApp
        
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("ctrl+s")
            await pilot.pause()
            assert snapshot == pilot.app.screen._render()
