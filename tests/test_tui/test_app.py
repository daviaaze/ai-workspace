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
        from ai_workspace.tui.app import AgentBar
        bar = AgentBar()
        assert bar.render() == ""


class TestTUI:
    """Integration tests requiring a real terminal."""

    async def test_tui_mounts_widgets(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.8)
            ms = pilot.app.screen
            assert ms.query_one("#header")
            assert ms.query_one("#agent-bar")
            assert ms.query_one("#conversation")
            assert ms.query_one("#task-input")
            assert ms.query_one("#status-bar")

    async def test_help_screen_pushes(self):
        from ai_workspace.tui.app import AIWorkspaceApp, HelpScreen
        async with AIWorkspaceApp().run_test(size=(80, 30)) as pilot:
            await pilot.pause(0.5)
            initial = len(pilot.app.screen_stack)
            pilot.app.push_screen(HelpScreen())
            await pilot.pause(0.2)
            assert len(pilot.app.screen_stack) == initial + 1
            await pilot.press("escape")
            await pilot.pause(0.2)
            assert len(pilot.app.screen_stack) == initial

    async def test_all_slash_commands_dont_crash(self):
        """Every slash command handler must run without exceptions.
        
        Also verifies that self.m works even when overlays are active.
        """
        from ai_workspace.tui.app import AIWorkspaceApp, HelpScreen
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            inp = pilot.app.screen.query_one("#task-input")
            initial_stack = len(pilot.app.screen_stack)

            # /help opens overlay
            inp.value = "/help"
            await inp.action_submit()
            await pilot.pause(0.2)
            assert len(pilot.app.screen_stack) == initial_stack + 1
            # self.m must still find MainScreen even with overlay active
            assert pilot.app.m is not None

            # Dismiss and test other commands
            await pilot.press("escape")
            await pilot.pause(0.1)

            for cmd in ["/model", "/tasks", "/clear", "/cost", "/nonexistent"]:
                inp.value = cmd
                await inp.action_submit()
                await pilot.pause(0.15)
                # self.m must work after each command
                assert pilot.app.m is not None
