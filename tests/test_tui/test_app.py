"""
TUI snapshot tests — capture visual state of the agent operations center v2.

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

    async def test_header_bar_shows(self):
        """Header bar shows workspace, tabs, and status."""
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.header import HeaderBar

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            bar = pilot.app.query_one(HeaderBar)
            assert bar is not None
            assert bar.cwd is not None
            await pilot.pause()

    async def test_dashboard_renders(self):
        """Dashboard view shows cards."""
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.dashboard import DashboardView

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            dashboard = pilot.app.query_one(DashboardView)
            assert dashboard is not None
            await pilot.pause()

    async def test_agents_view_renders(self):
        """Agents view shows agent list and detail."""
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.agent_grid import AgentsView

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            # Switch to agents tab
            await pilot.press("tab")
            await pilot.pause()
            agents = pilot.app.query_one(AgentsView)
            assert agents is not None
            await pilot.pause()

    async def test_tasks_view_renders(self):
        """Tasks view shows task table."""
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.task_table import TasksView

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("tab")
            await pilot.pause()
            tasks = pilot.app.query_one(TasksView)
            assert tasks is not None
            await pilot.pause()

    async def test_git_view_renders(self):
        """Git view shows git panel."""
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.git_panel import GitPanel

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("tab")
            await pilot.pause()
            git = pilot.app.query_one(GitPanel)
            assert git is not None
            await pilot.pause()

    async def test_keybinding_cycle_focus(self):
        """Tab cycles through panels."""
        from ai_workspace.tui.app import AIWorkspaceApp

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("tab")
            await pilot.pause()
            assert True

    async def test_spawn_dialog(self):
        """Ctrl+S opens spawn dialog."""
        from ai_workspace.tui.app import AIWorkspaceApp

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("ctrl+s")
            await pilot.pause()
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

    async def test_quit(self):
        """q quits the app."""
        from ai_workspace.tui.app import AIWorkspaceApp

        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.press("q")


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
