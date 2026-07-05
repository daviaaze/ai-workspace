"""Tests for TUI v5 overlay components that are still connected."""

from __future__ import annotations

import pytest

pytest_plugins = ("pytest_asyncio",)


# ===================================================================
# Model Select (Ctrl+M)
# ===================================================================


class TestModelSelect:

    @pytest.mark.asyncio
    async def test_opens_via_binding(self):
        """Ctrl+M opens model selector."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+m")
            await pilot.pause(0.4)

            top = app.screen_stack[-1]
            assert "Model" in type(top).__name__

    @pytest.mark.asyncio
    async def test_shows_model_list(self):
        """Model selector shows model list."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+m")
            await pilot.pause(0.5)

            top = app.screen_stack[-1]
            lv = top.query_one("#model-list")
            assert len(list(lv.children)) > 0

    @pytest.mark.asyncio
    async def test_escape_dismisses(self):
        """Escape closes model selector."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("ctrl+m")
            await pilot.pause(0.3)
            assert len(app.screen_stack) == 2

            await pilot.press("escape")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 1


# ===================================================================
# Context Inspector (F4)
# ===================================================================


class TestContextInspector:

    @pytest.mark.asyncio
    async def test_opens_via_binding(self):
        """F4 opens context inspector."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f4")
            await pilot.pause(0.4)

            top = app.screen_stack[-1]
            assert "Context" in type(top).__name__

    @pytest.mark.asyncio
    async def test_shows_token_bar(self):
        """Context inspector renders."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f4")
            await pilot.pause(0.3)

            assert app.screen.query_one("#inspector-box") is not None

    @pytest.mark.asyncio
    async def test_dismisses(self):
        """Escape closes context inspector."""
        from ai_workspace.tui.v5.app import AIWorkspaceApp

        app = AIWorkspaceApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause(0.3)

            await pilot.press("f4")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 2

            await pilot.press("escape")
            await pilot.pause(0.2)
            assert len(app.screen_stack) == 1


# ===================================================================
# StatCard (used by Dashboard)
# ===================================================================


class TestStatCard:

    @pytest.mark.asyncio
    async def test_labels_and_values_update(self):
        """StatCard updates via reactive."""
        from textual.app import App
        from textual.containers import Vertical

        from ai_workspace.tui.v5.dashboard import StatCard

        class TestApp(App):
            def compose(self):
                with Vertical():
                    yield StatCard(id="test")

        app = TestApp()
        async with app.run_test(size=(40, 10)) as pilot:
            await pilot.pause(0.2)

            card = app.screen.query_one("#test")
            card.label = "Agents"
            await pilot.pause(0.1)
            card.value = "42"
            await pilot.pause(0.1)

            assert card.label == "Agents"
            assert card.value == "42"


# ===================================================================
# Autocomplete widget (unit test)
# ===================================================================


@pytest.mark.asyncio
async def test_autocomplete_filter():
    """Autocomplete filters commands."""
    from textual.app import App

    from ai_workspace.tui.v5.app import Autocomplete

    class TestApp(App):
        def compose(self):
            yield Autocomplete(id="ac")

    app = TestApp()
    async with app.run_test(size=(80, 20)) as pilot:
        await pilot.pause(0.2)

        ac = app.screen.query_one("#ac")
        ac.filter("/mo")
        assert ac.has_class("-visible")

        items = list(ac.query("ListView ListItem"))
        assert len(items) >= 1

        ac.filter("not a command")
        assert not ac.has_class("-visible")
