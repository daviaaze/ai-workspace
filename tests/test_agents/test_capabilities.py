"""Smoke tests for capabilities.py — pure dataclass + built-in constants."""

from __future__ import annotations

from ai_workspace.agents.capabilities import (
    CAPABILITY_CHAT,
    CAPABILITY_CODE,
    CAPABILITY_RESEARCH,
    CAPABILITY_WRITE,
    Capability,
)
from ai_workspace.agents.patterns import LoopPattern


class TestCapabilityDataclass:
    def test_default_construction(self):
        """Minimal capability uses REACT pattern, no tools."""
        c = Capability(name="test-cap")
        assert c.name == "test-cap"
        assert c.pattern == LoopPattern.REACT
        assert c.required_tools == []
        assert c.optional_tools == []
        assert c.max_turns == 20
        assert c.temperature is None

    def test_full_construction(self):
        """Capability with all fields set."""
        c = Capability(
            name="full",
            description="Full capability test",
            pattern=LoopPattern.DAG,
            required_tools=["rag", "web_search"],
            optional_tools=["web_fetch"],
            default_model="qwen3:14b",
            context_sources=["memory"],
            max_turns=5,
            temperature=0.3,
        )
        assert c.name == "full"
        assert c.description == "Full capability test"
        assert c.pattern == LoopPattern.DAG
        assert c.required_tools == ["rag", "web_search"]
        assert c.optional_tools == ["web_fetch"]
        assert c.default_model == "qwen3:14b"
        assert c.context_sources == ["memory"]
        assert c.max_turns == 5
        assert c.temperature == 0.3

    def test_mutable_fields(self):
        """List/dict fields are independent instances."""
        c1 = Capability(name="a", required_tools=["x"])
        c2 = Capability(name="b", required_tools=["y"])
        assert c1.required_tools == ["x"]
        assert c2.required_tools == ["y"]
        c1.required_tools.append("z")
        assert c1.required_tools == ["x", "z"]
        assert c2.required_tools == ["y"]  # not shared


class TestBuiltinCapabilities:
    def test_capability_chat(self):
        assert CAPABILITY_CHAT.name == "chat"
        assert CAPABILITY_CHAT.pattern == LoopPattern.DIRECT
        assert CAPABILITY_CHAT.max_turns == 10
        assert CAPABILITY_CHAT.required_tools == []

    def test_capability_research(self):
        assert CAPABILITY_RESEARCH.name == "research"
        assert CAPABILITY_RESEARCH.pattern == LoopPattern.REACT
        assert "web_search" in CAPABILITY_RESEARCH.required_tools
        assert CAPABILITY_RESEARCH.max_turns == 30

    def test_capability_code(self):
        assert CAPABILITY_CODE.name == "code"
        assert CAPABILITY_CODE.pattern == LoopPattern.REACT
        assert "filesystem" in CAPABILITY_CODE.required_tools

    def test_capability_write(self):
        assert CAPABILITY_WRITE.name == "write"
        assert CAPABILITY_WRITE.pattern == LoopPattern.DIRECT
        assert CAPABILITY_WRITE.required_tools == []

    def test_all_capabilities_have_unique_names(self):
        names = {CAPABILITY_CHAT.name, CAPABILITY_RESEARCH.name,
                 CAPABILITY_CODE.name, CAPABILITY_WRITE.name}
        assert len(names) == 4
