"""Tests for rag_tool.py — RAG tool definition and handler."""

from __future__ import annotations

from unittest.mock import patch

from ai_workspace.agents.rag_tool import (
    RetrieveKnowledgeCrewTool,
    get_rag_tool,
    handle_retrieve_knowledge,
)


class TestToolDefinition:
    def test_tool_definition_has_correct_structure(self):
        """_RAG_TOOL_DEFINITION is a valid function-calling schema."""
        from ai_workspace.agents.rag_tool import _RAG_TOOL_DEFINITION

        assert _RAG_TOOL_DEFINITION["type"] == "function"
        assert _RAG_TOOL_DEFINITION["function"]["name"] == "retrieve_knowledge"
        assert "query" in _RAG_TOOL_DEFINITION["function"]["parameters"]["properties"]
        assert _RAG_TOOL_DEFINITION["function"]["parameters"]["required"] == ["query"]

    def test_tool_definition_description_not_empty(self):
        from ai_workspace.agents.rag_tool import _RAG_TOOL_DEFINITION

        desc = _RAG_TOOL_DEFINITION["function"]["description"]
        assert len(desc) > 20

    def test_k_param_has_default(self):
        from ai_workspace.agents.rag_tool import _RAG_TOOL_DEFINITION

        k_props = _RAG_TOOL_DEFINITION["function"]["parameters"]["properties"].get("k", {})
        assert k_props.get("default") == 5


class TestGetRagTool:
    def test_returns_tuple(self):
        result = get_rag_tool()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_tool_definition(self):
        tool_def, _ = get_rag_tool()
        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "retrieve_knowledge"

    def test_second_element_has_handler(self):
        _, handlers = get_rag_tool()
        assert "retrieve_knowledge" in handlers
        assert callable(handlers["retrieve_knowledge"])


class TestHandleRetrieveKnowledge:
    def test_returns_context_when_found(self):
        with patch(
            "ai_workspace.knowledge.retrieve_context",
            return_value="Relevant code context here",
        ):
            result = handle_retrieve_knowledge(query="agent loop", k=3)
            assert "code context" in result

    def test_returns_no_results_message(self):
        with patch(
            "ai_workspace.knowledge.retrieve_context",
            return_value="",
        ):
            result = handle_retrieve_knowledge(query="unknown topic")
            assert "No matching documents" in result
            assert "unknown topic" in result

    def test_returns_error_message_on_exception(self):
        with patch(
            "ai_workspace.knowledge.retrieve_context",
            side_effect=ConnectionError("DB unavailable"),
        ):
            result = handle_retrieve_knowledge(query="test")
            assert "failed" in result.lower() or "unavailable" in result

    def test_k_is_capped_at_10(self):
        with patch(
            "ai_workspace.knowledge.retrieve_context",
            return_value="context",
        ) as mock_retrieve:
            handle_retrieve_knowledge(query="test", k=100)
            mock_retrieve.assert_called_once_with("test", k=10)


class TestRetrieveKnowledgeCrewTool:
    def test_tool_subclass(self):
        from ai_workspace.tools.base import Tool

        tool = RetrieveKnowledgeCrewTool()
        assert isinstance(tool, Tool)
        assert tool.name == "retrieve_knowledge"

    def test_run_calls_handler(self):
        with patch(
            "ai_workspace.agents.rag_tool.handle_retrieve_knowledge",
            return_value="result",
        ) as mock_handler:
            tool = RetrieveKnowledgeCrewTool()
            result = tool._run(query="test query", k=5)
            assert result == "result"
            mock_handler.assert_called_once_with(query="test query", k=5)
