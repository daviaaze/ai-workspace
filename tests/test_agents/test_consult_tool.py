"""Tests for agents/consult_tool.py — consult_subagent tool for Partners."""

import pytest

from ai_workspace.agents.consult_tool import CONSULT_TOOL_DEF, consult_handler


# ═══════════════════════════════════════════════════════════
# Tool Definition
# ═══════════════════════════════════════════════════════════


class TestConsultToolDef:
    def test_tool_def_structure(self):
        assert CONSULT_TOOL_DEF["type"] == "function"
        assert "function" in CONSULT_TOOL_DEF

    def test_tool_name(self):
        assert CONSULT_TOOL_DEF["function"]["name"] == "consult_subagent"

    def test_has_description(self):
        desc = CONSULT_TOOL_DEF["function"]["description"]
        assert len(desc) > 0
        assert "Partner" in desc or "partner" in desc

    def test_parameters_schema(self):
        params = CONSULT_TOOL_DEF["function"]["parameters"]
        assert params["type"] == "object"
        assert "partner_name" in params["properties"]
        assert "query" in params["properties"]
        assert "partner_name" in params["required"]
        assert "query" in params["required"]

    def test_partner_name_is_string(self):
        props = CONSULT_TOOL_DEF["function"]["parameters"]["properties"]
        assert props["partner_name"]["type"] == "string"

    def test_query_is_string(self):
        props = CONSULT_TOOL_DEF["function"]["parameters"]["properties"]
        assert props["query"]["type"] == "string"


# ═══════════════════════════════════════════════════════════
# consult_handler
# ═══════════════════════════════════════════════════════════


class TestConsultHandler:
    def test_partner_not_found(self):
        result = consult_handler(partner_name="nonexistent", query="hello")
        assert "not found" in result.lower() or "Nonexistent" in result

    def test_partner_not_found_shows_available(self):
        result = consult_handler(partner_name="nonexistent", query="hello")
        # Should mention available partners or (none)
        assert "available" in result.lower() or "(none)" in result

    def test_handler_with_no_partners(self, monkeypatch):
        """When no partners exist, should return helpful message."""
        from ai_workspace.agents import partner as partner_mod
        monkeypatch.setattr(partner_mod.Partner, "list_all", staticmethod(lambda: []))
        result = consult_handler(partner_name="test", query="hello")
        assert "not found" in result.lower() or "(none)" in result

    def test_handler_returns_string(self):
        result = consult_handler(partner_name="any", query="test")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_handler_exception_safety(self, monkeypatch):
        """Handler should not raise, always return a string."""
        from ai_workspace.agents import partner as partner_mod
        original = partner_mod.Partner.list_all
        monkeypatch.setattr(
            partner_mod.Partner, "list_all",
            staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("db down"))),
        )
        result = consult_handler(partner_name="x", query="y")
        assert isinstance(result, str)
        assert "failed" in result.lower() or "error" in result.lower()
