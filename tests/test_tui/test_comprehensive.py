"""Comprehensive TUI tests — layout, colors, clipping, content, performance.

Updated for reactive-render architecture (v6).
Widget IDs: #header, #agent-bar, #conversation, #cmd-palette, #task-input, #status-bar
"""

from __future__ import annotations

# ── Layout & Widgets ───────────────────────────────────────────────


class TestLayout:
    """Verify all required widgets exist and have correct dimensions."""

    REQUIRED = [
        "#header", "#agent-bar", "#conversation", "#cmd-palette",
        "#task-input", "#status-bar",
    ]

    async def test_all_widgets_present(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            screen = pilot.app.screen
            for wid in self.REQUIRED:
                screen.query_one(wid)  # raises NoMatches if missing

    async def test_input_is_focused_on_start(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Input
            inp = pilot.app.screen.query_one("#task-input", Input)
            assert inp.has_focus, "Input must be focused on startup"

    async def test_header_has_fixed_height(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            h = pilot.app.screen.query_one("#header", Static)
            assert h.styles.height and h.styles.height.value == 1, \
                f"header height should be 1, got {h.styles.height}"

    async def test_status_bar_has_fixed_height(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            sb = pilot.app.screen.query_one("#status-bar", Static)
            assert sb.styles.height and sb.styles.height.value == 1, \
                f"status-bar height should be 1, got {sb.styles.height}"


# ── Colors & Visual ────────────────────────────────────────────────


class TestColors:
    """Verify correct color application on widgets and rendered content."""

    async def test_input_has_explicit_text_color(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Input
            inp = pilot.app.screen.query_one("#task-input", Input)
            assert inp.styles.color is not None, \
                "Input must have explicit color to be visible"

    async def test_input_has_visible_background(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Input
            inp = pilot.app.screen.query_one("#task-input", Input)
            assert inp.styles.background is not None, \
                "Input must have explicit background"

    async def test_header_renders_content(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            h = pilot.app.screen.query_one("#header", Static)
            visual = h.render()
            # render() returns a Content object in recent Textual
            rendered = visual.plain if hasattr(visual, 'plain') else str(visual)
            assert isinstance(rendered, str), f"render must return string, got {type(rendered)}"
            assert 'aiw' in rendered, f"header must contain 'aiw', got: {rendered[:80]}"

    async def test_status_bar_renders_keys(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            sb = pilot.app.screen.query_one("#status-bar", Static)
            visual = sb.render()
            rendered = visual.plain if hasattr(visual, 'plain') else str(visual)
            assert 'F1' in rendered, "status-bar must show F1 hint"


# ── Clipping & Overflow ────────────────────────────────────────────


class TestClipping:
    """Verify content doesn't get clipped inappropriately."""

    async def test_status_bar_fits_single_line(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            sb = pilot.app.screen.query_one("#status-bar", Static)
            assert sb.styles.height and sb.styles.height.value == 1, \
                "status-bar must be exactly 1 line to avoid layout shift"

    async def test_input_has_correct_height(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Input
            inp = pilot.app.screen.query_one("#task-input", Input)
            assert inp.styles.height and inp.styles.height.value == 3, \
                f"input height should be 3, got {inp.styles.height}"


# ── Content & State ────────────────────────────────────────────────


class TestContent:
    """Verify correct data display in widgets."""

    async def test_agent_bar_hides_when_no_agents(self):
        from ai_workspace.tui.app import AgentBar, AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            ab = pilot.app.screen.query_one("#agent-bar", AgentBar)
            rendered = ab.render()
            assert rendered == "" or rendered is None or not rendered.strip(), \
                f"Agent bar should be empty when no agents, got: {repr(rendered)[:80]}"

    async def test_welcome_message_in_conversation(self):
        from textual.widgets import RichLog

        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.8)
            log = pilot.app.screen.query_one("#conversation", RichLog)
            assert len(log.lines) >= 1, f"Conversation should have welcome messages, got {len(log.lines)}"

    async def test_refresh_preserves_widgets(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            await pilot.press("f5")
            await pilot.pause(0.3)
            screen = pilot.app.screen
            screen.query_one("#header")
            screen.query_one("#task-input")
            screen.query_one("#conversation")
            screen.query_one("#status-bar")

    async def test_help_overlay_appears(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            await pilot.press("f1")
            await pilot.pause(0.3)
            from ai_workspace.tui.app import HelpScreen
            assert isinstance(pilot.app.screen, HelpScreen), "F1 should push HelpScreen"


# ── Performance ─────────────────────────────────────────────────────


class TestPerformance:
    """Verify the TUI doesn't degrade in performance."""

    async def test_startup_time_under_2_seconds(self):
        import time

        from ai_workspace.tui.app import AIWorkspaceApp
        start = time.monotonic()
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"TUI startup too slow: {elapsed:.2f}s"

    async def test_refresh_under_1_second(self):
        import time

        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            start = time.monotonic()
            await pilot.press("f5")
            await pilot.pause(0.3)
            elapsed = time.monotonic() - start
            assert elapsed < 1.0, f"Refresh too slow: {elapsed:.2f}s"

    async def test_multiple_rapid_commands(self):
        """Issue 10 commands in quick succession — no crash, no slowdown."""
        import time

        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            inp = pilot.app.screen.query_one("#task-input")
            start = time.monotonic()
            for i in range(10):
                inp.value = f"/model test-{i}"
                await inp.action_submit()
                await pilot.pause(0.05)
            elapsed = time.monotonic() - start
            assert elapsed < 5.0, f"10 commands too slow: {elapsed:.2f}s"
            assert pilot.app.m is not None
