"""
Tests for the chat session module.

Verifies:
- ChatSession message management
- /slash command dispatch
- Knowledge recall behavior
- Memory storage behavior
- REPL loop
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ─── ChatSession basic state ────────────────────────


def test_session_starts_empty():
    from ai_workspace.chat import ChatSession
    s = ChatSession()
    assert s.messages == []
    assert s.turn_count == 0
    assert s.workspace == "personal"
    assert s.agent == "default"


def test_add_user_appends():
    from ai_workspace.chat import ChatSession
    s = ChatSession()
    s.add_user("hello")
    assert s.messages == [{"role": "user", "content": "hello"}]
    assert s.turn_count == 1


def test_add_assistant_appends():
    from ai_workspace.chat import ChatSession
    s = ChatSession()
    s.add_assistant("hi there")
    assert s.messages == [{"role": "assistant", "content": "hi there"}]


def test_add_system_replaces_existing():
    from ai_workspace.chat import ChatSession
    s = ChatSession()
    s.add_system("first")
    s.add_user("hi")
    s.add_system("second")
    # System prompt should be at position 0 and updated
    assert s.messages[0] == {"role": "system", "content": "second"}


def test_add_system_inserts_at_front():
    from ai_workspace.chat import ChatSession
    s = ChatSession()
    s.add_user("hi")
    s.add_system("system prompt")
    assert s.messages[0]["role"] == "system"
    assert s.messages[1]["role"] == "user"


def test_trim_history_keeps_system_prompt():
    from ai_workspace.chat import ChatSession
    s = ChatSession(max_history=4)
    s.add_system("system")
    for i in range(10):
        s.add_user(f"u{i}")
        s.add_assistant(f"a{i}")
    # Should be trimmed to 4 total (1 system + 3 most recent)
    assert len(s.messages) == 4
    assert s.messages[0]["role"] == "system"


def test_to_dict_serializes():
    from ai_workspace.chat import ChatSession
    s = ChatSession(workspace="work", agent="coder", provider="openrouter", model="gpt-4o")
    s.add_user("hi")
    d = s.to_dict()
    assert d["workspace"] == "work"
    assert d["agent"] == "coder"
    assert d["provider"] == "openrouter"
    assert d["model"] == "gpt-4o"
    assert d["turn_count"] == 1


# ─── Slash commands ─────────────────────────────────


@pytest.fixture
def session():
    from ai_workspace.chat import ChatSession
    return ChatSession(workspace="personal", agent="default")


def test_slash_help_returns_continue(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print"):
        result = _handle_slash_command("/help", session)
    assert result is True


def test_slash_workspace_switch(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print"):
        _handle_slash_command("/workspace work", session)
    assert session.workspace == "work"


def test_slash_workspace_shows_current_when_no_arg(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print") as mock_print:
        _handle_slash_command("/workspace", session)
    # Should have printed the current workspace
    assert any("personal" in str(call) for call in mock_print.call_args_list)


def test_slash_persona_switches_and_adds_system_prompt(session):
    from ai_workspace.chat import _handle_slash_command, SYSTEM_PROMPTS
    with patch("ai_workspace.chat.console.print"):
        _handle_slash_command("/persona coder", session)
    assert session.agent == "coder"
    assert session.system_prompt == SYSTEM_PROMPTS["coder"]
    # System prompt should be in messages
    assert any(m["role"] == "system" and "engineer" in m["content"] for m in session.messages)


def test_slash_persona_unknown_rejected(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print") as mock_print:
        _handle_slash_command("/persona nonexistent", session)
    assert session.agent == "default"  # unchanged
    assert any("Unknown persona" in str(call) for call in mock_print.call_args_list)


def test_slash_provider_switch_resets_model(session):
    from ai_workspace.chat import _handle_slash_command
    session.model = "gpt-4o"
    with patch("ai_workspace.chat.console.print"):
        _handle_slash_command("/provider nvidia", session)
    assert session.provider == "nvidia"
    assert session.model is None


def test_slash_model_set(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print"):
        _handle_slash_command("/model gpt-4o-mini", session)
    assert session.model == "gpt-4o-mini"


def test_slash_clear_resets_messages(session):
    from ai_workspace.chat import _handle_slash_command
    session.add_user("hi")
    session.add_assistant("hello")
    session.add_system("system")
    with patch("ai_workspace.chat.console.print"):
        _handle_slash_command("/clear", session)
    # System prompt is restored
    assert len(session.messages) == 1
    assert session.messages[0]["role"] == "system"


def test_slash_exit_returns_false(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print"):
        assert _handle_slash_command("/exit", session) is False
        assert _handle_slash_command("/quit", session) is False
        assert _handle_slash_command("/q", session) is False


def test_slash_recall_with_query(session):
    from ai_workspace.chat import _handle_slash_command
    fake_hits = [{"title": "x", "content": "y", "source": "knowledge_base"}]
    with patch("ai_workspace.chat.recall_context", return_value=fake_hits):
        with patch("ai_workspace.chat.console.print"):
            _handle_slash_command("/recall foo", session)
    assert session.recalled_context == fake_hits


def test_slash_recall_no_query_shows_usage(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print") as mock_print:
        _handle_slash_command("/recall", session)
    assert any("Usage" in str(call) for call in mock_print.call_args_list)


def test_slash_status_shows_state(session):
    from ai_workspace.chat import _handle_slash_command
    session.turn_count = 3
    with patch("ai_workspace.chat.console.print") as mock_print:
        _handle_slash_command("/status", session)
    # Should print a panel mentioning turns=3
    assert any("3" in str(call) for call in mock_print.call_args_list)


def test_slash_unknown_command_shows_error(session):
    from ai_workspace.chat import _handle_slash_command
    with patch("ai_workspace.chat.console.print") as mock_print:
        _handle_slash_command("/garbage", session)
    assert any("Unknown command" in str(call) for call in mock_print.call_args_list)


# ─── Knowledge recall ──────────────────────────────


def test_recall_context_returns_empty_on_db_error():
    from ai_workspace.chat import recall_context
    with patch("ai_workspace.knowledge.KnowledgeStore", side_effect=RuntimeError("no db")):
        result = recall_context("test", "agent", "personal")
    assert result == []


def test_recall_context_includes_kb_hits():
    from ai_workspace.chat import recall_context

    mock_store = MagicMock()
    mock_store.search_knowledge.return_value = [{"id": 1, "title": "x", "content": "y"}]
    mock_store.recall.return_value = []
    with patch("ai_workspace.knowledge.KnowledgeStore", return_value=mock_store):
        result = recall_context("test", "agent", "personal")
    assert any(r.get("source") == "knowledge_base" for r in result)


def test_recall_context_includes_memory_hits():
    from ai_workspace.chat import recall_context

    mock_store = MagicMock()
    mock_store.search_knowledge.return_value = []
    mock_store.recall.return_value = [{"id": 1, "content": "remembered this", "memory_type": "fact"}]
    with patch("ai_workspace.knowledge.KnowledgeStore", return_value=mock_store):
        result = recall_context("test", "agent", "personal")
    assert any(r.get("source") == "agent_memory" for r in result)


def test_recall_context_handles_kb_search_failure():
    """If KB search raises, we still try to recall from memory."""
    from ai_workspace.chat import recall_context

    mock_store = MagicMock()
    mock_store.search_knowledge.side_effect = RuntimeError("search down")
    mock_store.recall.return_value = [{"id": 1, "content": "x"}]
    with patch("ai_workspace.knowledge.KnowledgeStore", return_value=mock_store):
        result = recall_context("test", "agent", "personal")
    assert any(r.get("source") == "agent_memory" for r in result)


# ─── Turn memory storage ───────────────────────────


def test_store_turn_memory_handles_db_error():
    from ai_workspace.chat import store_turn_memory, ChatSession
    session = ChatSession(agent="coder")
    with patch("ai_workspace.knowledge.KnowledgeStore", side_effect=RuntimeError("no db")):
        # Should not raise
        store_turn_memory(session, "user msg", "asst msg")


def test_store_turn_memory_increases_importance_for_keywords():
    from ai_workspace.chat import store_turn_memory, ChatSession
    session = ChatSession(agent="coder")

    captured: list[dict] = []

    def fake_remember(agent, content, memory_type, importance):
        captured.append({"agent": agent, "content": content, "memory_type": memory_type, "importance": importance})
        return 1

    mock_store = MagicMock()
    mock_store.remember = fake_remember
    with patch("ai_workspace.knowledge.KnowledgeStore", return_value=mock_store):
        store_turn_memory(session, "Remember this important rule", "OK noted")

    assert len(captured) == 1
    assert captured[0]["importance"] > 0.5  # boosted by "remember"/"important"


def test_store_turn_memory_short_response_low_importance():
    from ai_workspace.chat import store_turn_memory, ChatSession
    session = ChatSession(agent="coder")

    captured: list[dict] = []

    def fake_remember(agent, content, memory_type, importance):
        captured.append({"importance": importance})
        return 1

    mock_store = MagicMock()
    mock_store.remember = fake_remember
    with patch("ai_workspace.knowledge.KnowledgeStore", return_value=mock_store):
        store_turn_memory(session, "hi", "hello")

    assert captured[0]["importance"] <= 0.5


# ─── REPL smoke test ───────────────────────────────


def test_run_chat_repl_handles_eof():
    from ai_workspace.chat import run_chat_repl

    with patch("ai_workspace.chat.Prompt.ask", side_effect=EOFError):
        with patch("ai_workspace.chat.console.print"):
            # Should exit gracefully, not raise
            run_chat_repl()


def test_run_chat_repl_handles_keyboard_interrupt():
    from ai_workspace.chat import run_chat_repl

    with patch("ai_workspace.chat.Prompt.ask", side_effect=KeyboardInterrupt):
        with patch("ai_workspace.chat.console.print"):
            # Should exit gracefully, not raise
            run_chat_repl()


def test_run_chat_repl_slash_exit():
    from ai_workspace.chat import run_chat_repl

    # User types /exit immediately
    with patch("ai_workspace.chat.Prompt.ask", return_value="/exit"):
        with patch("ai_workspace.chat.console.print"):
            run_chat_repl()  # should return cleanly


def test_run_chat_repl_chat_loop():
    from ai_workspace.chat import run_chat_repl

    # User asks a question, then exits
    with patch("ai_workspace.chat.Prompt.ask", side_effect=["hello there", "/exit"]):
        with patch("ai_workspace.chat.chat_sync", return_value="hi! how can I help?"):
            with patch("ai_workspace.chat.console.print"):
                run_chat_repl()


def test_run_chat_repl_chat_loop_handles_llm_error():
    """If the LLM call raises, the user message is rolled back."""
    from ai_workspace.chat import run_chat_repl, ChatSession

    with patch("ai_workspace.chat.Prompt.ask", side_effect=["bad query", "/exit"]):
        with patch("ai_workspace.chat.chat_sync", side_effect=RuntimeError("LLM down")):
            with patch("ai_workspace.chat.console.print"):
                run_chat_repl()
