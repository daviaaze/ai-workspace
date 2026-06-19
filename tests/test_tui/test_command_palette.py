"""Tests for the slash-command autocomplete palette."""

from __future__ import annotations

import pytest


class TestCommandPalette:
    """Unit tests for CommandPalette logic (no terminal needed)."""

    def test_registry_has_all_commands(self):
        from ai_workspace.tui.command_palette import COMMANDS
        cmds = [c[0] for c in COMMANDS]
        for expected in ["/help", "/model ", "/research ", "/tasks", "/clear", "/cost", "/quit"]:
            assert expected in cmds, f"Missing: {expected}"

    def test_filter_exact_match(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        p.filter("/help")
        assert len(p.matching) == 1
        assert p.matching[0][0] == "/help"

    def test_filter_partial(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        p.filter("/m")
        assert len(p.matching) == 1  # /model
        assert p.matching[0][0] == "/model "

    def test_filter_no_match_hides(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        p.filter("/xyz")
        assert len(p.matching) == 0

    def test_filter_non_slash_hides(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        p.filter("hello")
        assert len(p.matching) == 0

    def test_show_all(self):
        from ai_workspace.tui.command_palette import CommandPalette, COMMANDS
        p = CommandPalette()
        p.show_all()
        assert len(p.matching) == len(COMMANDS)

    def test_move_up_down(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        p.show_all()
        assert p.highlight_index == 0
        p.move_down()
        assert p.highlight_index == 1
        p.move_down()
        assert p.highlight_index == 2
        p.move_up()
        assert p.highlight_index == 1
        p.move_up()
        assert p.highlight_index == 0
        # Don't go below 0
        p.move_up()
        assert p.highlight_index == 0

    def test_selected_command(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        p.filter("/res")
        cmd = p.selected_command
        assert cmd == "/research "

    def test_selected_command_none_when_hidden(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        assert p.selected_command is None

    def test_hide_clears(self):
        from ai_workspace.tui.command_palette import CommandPalette
        p = CommandPalette()
        p.show_all()
        p.hide()
        assert len(p.matching) == 0


class TestCommandPaletteInTUI:
    """Integration tests — palette appears and functions in the real TUI."""

    async def test_palette_widget_exists(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.command_palette import CommandPalette
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            pilot.app.screen.query_one("#cmd-palette", CommandPalette)

    async def test_typing_slash_shows_palette(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.command_palette import CommandPalette
        from textual.widgets import Input
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            inp = pilot.app.screen.query_one("#task-input", Input)
            palette = pilot.app.screen.query_one("#cmd-palette", CommandPalette)

            # Type / via the input
            inp.value = "/"
            inp.action_cursor_right()  # trigger refresh
            inp.post_message(Input.Changed(inp, "/", 1))
            await pilot.pause(0.3)

            # Check palette is visible
            assert palette.visible, f"Palette should be visible, got visible={palette.visible}"

    async def test_tab_completes_command(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        from textual.widgets import Input
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            inp = pilot.app.screen.query_one("#task-input", Input)

            # Type /mod into the input and trigger changed event
            inp.value = "/mod"
            inp.cursor_position = 4
            inp.post_message(Input.Changed(inp, "/mod", 4))
            await pilot.pause(0.2)

            # Press Tab to complete
            await pilot.press("tab")
            await pilot.pause(0.2)

            assert inp.value == "/model ", f"Tab should complete to /model , got: {inp.value}"

    async def test_escape_dismisses_palette(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        from ai_workspace.tui.command_palette import CommandPalette
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Input
            inp = pilot.app.screen.query_one("#task-input", Input)
            palette = pilot.app.screen.query_one("#cmd-palette", CommandPalette)

            # Show palette
            inp.value = "/"
            inp.post_message(Input.Changed(inp, "/", 1))
            await pilot.pause(0.2)
            assert palette.visible

            # Press Escape
            await pilot.press("escape")
            await pilot.pause(0.2)
            assert not palette.visible
