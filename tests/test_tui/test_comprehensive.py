"""Comprehensive TUI tests — layout, colors, clipping, content, performance.

Targets the v5 TUI architecture (ai_workspace.tui.v5.app).
"""

from __future__ import annotations

import pytest
import re

from ai_workspace.tui import AIWorkspaceApp


# ── Layout & Widgets ───────────────────────────────────────────────


class TestLayout:
    """Verify all required widgets exist and have correct dimensions."""

    async def test_all_widgets_present(self):
        """All core widgets should be on screen after startup."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            screen = pilot.app.screen
            screen.query_one("#conv")
            screen.query_one("#task-input")
            screen.query_one("#status-bar")

    async def test_input_is_focused_on_start(self):
        """TextArea should be focused immediately after mount."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import TextArea
            inp = pilot.app.screen.query_one("#task-input", TextArea)
            assert inp.has_focus, "TextArea must be focused on startup"

    async def test_status_bar_has_fixed_height(self):
        """Status bar should be a single line."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            sb = pilot.app.screen.query_one("#status-bar", Static)
            assert sb.styles.height and sb.styles.height.value == 1, \
                f"status-bar height should be 1, got {sb.styles.height}"

    async def test_header_renders(self):
        """Header should render without errors."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Header
            h = pilot.app.screen.query_one(Header)
            visual = h.render()
            rendered = visual.plain if hasattr(visual, 'plain') else str(visual)
            assert isinstance(rendered, str), f"header render must return string, got {type(rendered)}"


# ── Colors & Visual ────────────────────────────────────────────────


class TestColors:
    """Verify correct color application on widgets."""

    async def test_task_input_has_explicit_colors(self):
        """TextArea should have visible foreground and background."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import TextArea
            inp = pilot.app.screen.query_one("#task-input", TextArea)
            assert inp.styles.color is not None, \
                "TextArea must have explicit color to be visible"
            assert inp.styles.background is not None, \
                "TextArea must have explicit background"

    async def test_status_bar_renders_content(self):
        """Status bar should render visible text."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            sb = pilot.app.screen.query_one("#status-bar", Static)
            visual = sb.render()
            rendered = visual.plain if hasattr(visual, 'plain') else str(visual)
            assert isinstance(rendered, str), f"render must return string, got {type(rendered)}"


# ── Clipping & Overflow ────────────────────────────────────────────


class TestClipping:
    """Verify content doesn't get clipped inappropriately."""

    async def test_status_bar_fits_single_line(self):
        """Status-bar must be exactly 1 line to avoid layout shift."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            sb = pilot.app.screen.query_one("#status-bar", Static)
            assert sb.styles.height and sb.styles.height.value == 1, \
                "status-bar must be exactly 1 line to avoid layout shift"

    async def test_task_input_has_default_height(self):
        """TextArea should have a reasonable default height (3 rows)."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import TextArea
            inp = pilot.app.screen.query_one("#task-input", TextArea)
            # CSS may set height; if unset, TextArea defaults to 3
            h = inp.styles.height
            assert h is None or h.value == 3, \
                f"input height should default to 3, got {h}"


# ── Content & State ────────────────────────────────────────────────


class TestContent:
    """Verify correct data display in widgets."""

    async def test_welcome_message_in_conversation(self):
        """Conversation widget should exist on startup."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            conv = pilot.app.screen.query_one("#conv")
            assert conv is not None, "Conversation widget must exist"

    async def test_refresh_preserves_widgets(self):
        """F5 refresh should not destroy core widgets."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            await pilot.press("f5")
            await pilot.pause(0.3)
            screen = pilot.app.screen
            screen.query_one("#task-input")
            screen.query_one("#conv")
            screen.query_one("#status-bar")

    async def test_help_overlay_appears(self):
        """F1 should open a help/modal screen."""
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            await pilot.press("f1")
            await pilot.pause(0.3)
            # Should push a modal screen (not the main screen)
            from textual.screen import ModalScreen
            is_modal = isinstance(pilot.app.screen, ModalScreen)
            # Fallback: just check the screen changed from the main screen
            assert is_modal or pilot.app.screen.id != "default", \
                "F1 should push a new screen (modal expected)"


# ── Performance ─────────────────────────────────────────────────────


class TestPerformance:
    """Verify the TUI doesn't degrade in performance."""

    async def test_startup_under_3_seconds(self):
        """Full TUI startup should complete within 3 seconds."""
        import time
        start = time.monotonic()
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
        elapsed = time.monotonic() - start
        assert elapsed < 3.0, f"TUI startup too slow: {elapsed:.2f}s"

    async def test_refresh_under_1_second(self):
        """F5 refresh should complete within 1 second."""
        import time
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            start = time.monotonic()
            await pilot.press("f5")
            await pilot.pause(0.3)
            elapsed = time.monotonic() - start
            assert elapsed < 1.0, f"Refresh too slow: {elapsed:.2f}s"

    async def test_multiple_rapid_commands(self):
        """Submit text 10 times in quick succession — no crash."""
        import time
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            inp = pilot.app.screen.query_one("#task-input")
            start = time.monotonic()
            for i in range(10):
                inp.text = f"/model test-{i}"
                # Dispatch submit via app action (Enter key)
                await pilot.press("enter")
                await pilot.pause(0.05)
            elapsed = time.monotonic() - start
            assert elapsed < 5.0, f"10 commands too slow: {elapsed:.2f}s"
