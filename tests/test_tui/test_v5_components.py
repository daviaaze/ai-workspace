"""Tests for TUI v5 component logic — typed message widgets."""

from __future__ import annotations

import pytest

from ai_workspace.tui.v5.conversation import (
    AgentThought,
    ToolCall,
    UserMessage,
    AgentResponse,
    AgentError,
    SystemMessage,
)


# ---------------------------------------------------------------------------
# UserMessage
# ---------------------------------------------------------------------------


class TestUserMessage:

    def test_renders_with_prefix(self):
        m = UserMessage("Hello")
        rendered = str(m.render())
        assert "▸" in rendered
        assert "Hello" in rendered


# ---------------------------------------------------------------------------
# AgentThought
# ---------------------------------------------------------------------------


class TestAgentThought:

    def test_without_step(self):
        m = AgentThought("thinking text")
        rendered = str(m.render())
        assert "thinking text" in rendered

    def test_with_step(self):
        m = AgentThought("thinking text", step=1)
        rendered = str(m.render())
        assert "Step" in rendered
        assert "1" in rendered or "1:" in rendered


# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------


class TestToolCall:

    @pytest.mark.asyncio
    async def test_mounts_and_shows_header(self):
        from textual.app import App
        from textual.containers import Vertical

        class TestApp(App):
            def compose(self):
                with Vertical():
                    yield ToolCall("list_files", '{"path": "."}', step=1)

        app = TestApp()
        async with app.run_test(size=(80, 20)) as pilot:
            await pilot.pause(0.2)
            tc = app.screen.query_one("ToolCall")
            header = tc.query_one(".tool-header")
            rendered = str(header.render())
            assert "list_files" in rendered

    def test_expands_on_click(self):
        tc = ToolCall("read_file", "test.txt")
        assert not tc.has_class("-expanded")
        tc.on_click()
        assert tc.has_class("-expanded")
        tc.on_click()
        assert not tc.has_class("-expanded")

    @pytest.mark.asyncio
    async def test_set_result_shows_expanded(self):
        from textual.app import App
        from textual.containers import Vertical

        class TestApp(App):
            def compose(self):
                with Vertical():
                    yield ToolCall("test", "arg", step=1)

        app = TestApp()
        async with app.run_test(size=(80, 20)) as pilot:
            await pilot.pause(0.2)
            tc = app.screen.query_one("ToolCall")
            tc.set_result("some result text")
            assert tc.has_class("-expanded")


# ---------------------------------------------------------------------------
# AgentResponse (streaming)
# ---------------------------------------------------------------------------


class TestAgentResponse:

    def test_initial_empty(self):
        r = AgentResponse()
        assert r.content == ""
        rendered = r.render()
        assert not str(rendered).strip() or not rendered

    def test_append_token_updates_content(self):
        r = AgentResponse()
        r.append_token("Hello ")
        assert r.content == "Hello "
        r.append_token("world")
        assert r.content == "Hello world"

    def test_append_token_escapes_brackets(self):
        r = AgentResponse()
        r.append_token("[list[0]]")
        # Brackets should be escaped for safe rendering
        assert r.content == "[list[0]]"


# ---------------------------------------------------------------------------
# AgentError
# ---------------------------------------------------------------------------


class TestAgentError:

    def test_renders_with_prefix(self):
        m = AgentError("Something failed")
        rendered = m.render()
        assert "✗" in rendered or "Error" in rendered or "Something failed" in rendered


# ---------------------------------------------------------------------------
# SystemMessage
# ---------------------------------------------------------------------------


class TestSystemMessage:

    def test_renders_with_prefix(self):
        m = SystemMessage("System info")
        rendered = str(m.render())
        assert "--" in rendered
        assert "System info" in rendered
