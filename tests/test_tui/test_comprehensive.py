"""Comprehensive TUI tests — layout, colors, clipping, content, performance."""

from __future__ import annotations

import pytest

# ── Layout & Widgets ───────────────────────────────────────────────


class TestLayout:
    """Verify all required widgets exist and have correct dimensions."""

    REQUIRED = [
        "#top-bar",
        "#metrics-line1", "#metrics-line2",
        "#agents",
        "#body", "#research-section", "#tasks-section", "#output",
        "#task-input", "#info-bar",
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

    async def test_metrics_lines_have_fixed_height(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            m1 = pilot.app.screen.query_one("#metrics-line1", Static)
            m2 = pilot.app.screen.query_one("#metrics-line2", Static)
            # Both metrics bars must be exactly 1 line high (no clipping)
            assert m1.styles.height and m1.styles.height.value == 1, \
                f"metrics-line1 height should be 1, got {m1.styles.height}"
            assert m2.styles.height and m2.styles.height.value == 1, \
                f"metrics-line2 height should be 1, got {m2.styles.height}"

    async def test_top_bar_has_fixed_height(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            tb = pilot.app.screen.query_one("#top-bar", Static)
            assert tb.styles.height and tb.styles.height.value == 1, \
                f"top-bar height should be 1, got {tb.styles.height}"


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

    async def test_top_bar_renders_content(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            tb = pilot.app.screen.query_one("#top-bar", Static)
            visual = tb.render()
            # Must contain "aiw" branding and current path
            assert hasattr(visual, 'markup'), \
                "top-bar render must produce markup"
            assert 'aiw' in visual.markup, \
                f"top-bar must contain 'aiw', got: {visual.markup[:80]}"

    async def test_metrics_render_has_color_spans(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            from rich.text import Span
            m1 = pilot.app.screen.query_one("#metrics-line1", Static)
            visual = m1.render()
            # Check that color spans exist (not just plain text)
            if isinstance(visual, str):
                # If render returned a plain string, markup hasn't been processed
                assert False, \
                    "metrics-line1 render should return Content, not plain str"
            assert len(visual.spans) > 0, \
                "metrics must have color spans applied"

    async def test_info_bar_renders_keys(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            ib = pilot.app.screen.query_one("#info-bar", Static)
            visual = ib.render()
            markup = visual.markup if hasattr(visual, 'markup') else str(visual)
            assert 'model' in markup, "info-bar must show model"
            assert 'help' in markup.lower(), "info-bar must show help hint"


# ── Clipping & Overflow ────────────────────────────────────────────


class TestClipping:
    """Verify content doesn't get clipped inappropriately."""

    async def test_metrics_content_fits_width(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            m1 = pilot.app.screen.query_one("#metrics-line1", Static)
            m2 = pilot.app.screen.query_one("#metrics-line2", Static)
            # In a 100-char terminal, metrics should fit
            v1 = m1.render()
            v2 = m2.render()
            text1 = v1.markup if hasattr(v1, 'markup') else str(v1)
            text2 = v2.markup if hasattr(v2, 'markup') else str(v2)
            # Strip markup to get plain text length
            import re
            plain1 = re.sub(r"\[[^\]]*\]", "", text1)
            plain2 = re.sub(r"\[[^\]]*\]", "", text2)
            assert len(plain1) <= 100, \
                f"metrics-line1 plain text too long: {len(plain1)} chars"
            assert len(plain2) <= 100, \
                f"metrics-line2 plain text too long: {len(plain2)} chars"

    async def test_info_bar_fits_single_line(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            ib = pilot.app.screen.query_one("#info-bar", Static)
            assert ib.styles.height and ib.styles.height.value == 1, \
                "info-bar must be exactly 1 line to avoid layout shift"


# ── Content & State ────────────────────────────────────────────────


class TestContent:
    """Verify correct data display in widgets."""

    async def test_research_section_shows_entries_or_placeholder(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            rs = pilot.app.screen.query_one("#research-section", Static)
            content = rs.render()
            text = content.markup if hasattr(content, 'markup') else str(content)
            # Must have either data entries or the "no research" placeholder
            assert len(text) > 5, "research section should not be empty"

    async def test_tasks_section_shows_entries_or_placeholder(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            from textual.widgets import Static
            ts = pilot.app.screen.query_one("#tasks-section", Static)
            content = ts.render()
            text = content.markup if hasattr(content, 'markup') else str(content)
            assert len(text) > 3, "tasks section should not be empty"

    async def test_agent_bar_hides_when_no_agents(self):
        from ai_workspace.tui.app import AIWorkspaceApp, AgentStatusBar
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            ab = pilot.app.screen.query_one("#agents", AgentStatusBar)
            rendered = ab.render()
            # On startup with no agents, should render empty
            assert rendered == "" or rendered is None or not rendered.strip(), \
                f"Agent bar should be empty when no agents, got: {repr(rendered)[:80]}"

    async def test_refresh_preserves_widgets(self):
        from ai_workspace.tui.app import AIWorkspaceApp
        async with AIWorkspaceApp().run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            # Trigger F5 refresh
            await pilot.press("f5")
            await pilot.pause(0.3)
            # All widgets must still be queryable after refresh
            from ai_workspace.tui.app import MainScreen
            screen = pilot.app.screen
            screen.query_one("#top-bar")
            screen.query_one("#metrics-line1")
            screen.query_one("#task-input")


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
            # self.m must still work
            assert pilot.app.m is not None
