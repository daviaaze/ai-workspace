"""TUI smoke tests — catch import/CSS/syntax errors in CI."""

from __future__ import annotations

import pytest


class TestTUILaunchable:
    """Fast smoke tests that run in CI."""

    def test_tui_imports_without_errors(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        assert AIWorkspaceApp is not None

    def test_app_can_be_instantiated_headless(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        app = AIWorkspaceApp()
        assert app is not None
        assert "AI Workstation" in app.TITLE

    def test_help_screen_has_bindings(self):
        from ai_workspace.tui.app import HelpScreen
        assert len(HelpScreen.BINDINGS) >= 1

    def test_agent_status_bar_exists(self):
        from ai_workspace.tui.app import AgentStatusBar
        bar = AgentStatusBar()
        assert bar.render() == ""


@pytest.mark.skip(reason="Requires terminal")
class TestTUI:
    """Integration tests requiring a real terminal."""

    async def test_tui_mounts_widgets(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.8)
            ms = pilot.app.screen
            assert ms.query_one("#top-bar")
            assert ms.query_one("#metrics-line1")
            assert ms.query_one("#task-input")
            assert ms.query_one("#info-bar")

    async def test_help_screen_pushes(self):
        from ai_workspace.tui.app import AIWorkspaceApp, HelpScreen
        async with AIWorkspaceApp().run_test(size=(80, 30)) as pilot:
            await pilot.pause(0.5)
            pilot.app.push_screen(HelpScreen())
            await pilot.pause(0.2)
            assert len(pilot.app.screen_stack) == 2
            await pilot.press("escape")
            await pilot.pause(0.2)
            assert len(pilot.app.screen_stack) == 1
