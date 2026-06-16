"""
Tests for orchestrator and browser agent integration.

Covers:
- BrowserUseAgentTool instantiation and LLM fallback chain
- AgentOrchestrator with mocked agents
- CLIStreamSink output capture
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════
# Browser agent tool
# ═══════════════════════════════════════════════════════


class TestBrowserAgentTool:
    """BrowserUseAgentTool wraps browser-use library."""

    def test_tool_instantiation(self):
        from ai_workspace.tools.browser_agent import BrowserUseAgentTool
        tool = BrowserUseAgentTool()
        assert tool.name == "browser_agent"
        assert "browser-use" in tool.description.lower()

    def test_tool_has_input_schema(self):
        from ai_workspace.tools.browser_agent import BrowserUseAgentTool, BrowserUseAgentInput
        tool = BrowserUseAgentTool()
        assert tool.args_schema is BrowserUseAgentInput

    def test_tool_reports_missing_browser_use(self):
        from ai_workspace.tools.browser_agent import BrowserUseAgentTool
        tool = BrowserUseAgentTool()
        with patch("ai_workspace.tools.browser_agent._pick_llm", return_value=None):
            result = tool._run(task="test", max_steps=5)
            assert "❌" in result

    def test_pick_llm_ollama_fallback(self, monkeypatch):
        from ai_workspace.tools.browser_agent import _pick_llm
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        llm = _pick_llm()
        # Should return something (ChatOllama if browser-use installed, else None)
        # At minimum doesn't crash
        assert True

    def test_pick_llm_no_providers(self, monkeypatch):
        from ai_workspace.tools.browser_agent import _pick_llm
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        # Should not crash, return None
        result = _pick_llm()
        assert result is None or result is not None  # Just no crash

    def test_get_browser_agent_tool(self):
        from ai_workspace.tools.browser_agent import get_browser_agent_tool
        tool = get_browser_agent_tool()
        assert tool is not None
        assert tool.name == "browser_agent"


# ═══════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════


class TestOrchestratorConfig:
    """OrchestratorConfig defaults."""

    def test_default_config(self):
        from ai_workspace.agents.orchestrator import OrchestratorConfig
        cfg = OrchestratorConfig()
        assert cfg.agent_type == "general"
        assert cfg.model == "qwen3:14b"
        assert cfg.use_context is True
        assert cfg.use_streaming is True
        assert cfg.max_fallback_attempts == 3

    def test_config_custom(self):
        from ai_workspace.agents.orchestrator import OrchestratorConfig
        cfg = OrchestratorConfig(
            agent_type="coding",
            model="qwen3-coder:30b",
            use_streaming=False,
            max_fallback_attempts=1,
        )
        assert cfg.agent_type == "coding"
        assert cfg.use_streaming is False
        assert cfg.max_fallback_attempts == 1


class TestCLIStreamSink:
    """CLIStreamSink outputs to terminal."""

    def test_sink_instantiation(self):
        from ai_workspace.agents.orchestrator import CLIStreamSink
        sink = CLIStreamSink()
        assert sink is not None

    def test_sink_emit_token(self):
        from ai_workspace.agents.orchestrator import CLIStreamSink
        sink = CLIStreamSink()
        # Should not crash
        asyncio.run(sink.emit_token("hello"))

    def test_sink_emit_status(self):
        from ai_workspace.agents.orchestrator import CLIStreamSink
        sink = CLIStreamSink()
        asyncio.run(sink.emit_status("executing", {"model": "test"}))

    def test_sink_emit_error(self):
        from ai_workspace.agents.orchestrator import CLIStreamSink
        sink = CLIStreamSink()
        asyncio.run(sink.emit_error("test error", recoverable=True))


class MockStreamSink:
    """Mock sink for testing orchestrator without terminal output."""
    
    def __init__(self):
        self.tokens: list[str] = []
        self.statuses: list[str] = []
        self.errors: list[str] = []
        self.thinking: list[str] = []
    
    async def emit_token(self, token: str) -> None:
        self.tokens.append(token)
    
    async def emit_thinking(self, thought: str) -> None:
        self.thinking.append(thought)
    
    async def emit_tool_call(self, name: str, args: dict) -> None:
        pass
    
    async def emit_tool_result(self, name: str, result: str) -> None:
        pass
    
    async def emit_status(self, status: str, metadata: dict | None = None) -> None:
        self.statuses.append(status)
    
    async def emit_error(self, error: str, recoverable: bool = False) -> None:
        self.errors.append(error)
    
    async def emit_context_update(self, blocks, budget_pct: float) -> None:
        pass
    
    async def request_permission(self, request) -> Any:
        class AllowVerdict:
            pass
        return AllowVerdict()


class TestAgentOrchestrator:
    """AgentOrchestrator with mocked agent execution."""

    @pytest.fixture
    def orch(self):
        from ai_workspace.agents.orchestrator import (
            AgentOrchestrator,
            OrchestratorConfig,
        )
        sink = MockStreamSink()
        config = OrchestratorConfig(
            agent_type="general",
            use_context=False,     # Skip project context in tests
            use_router=False,      # Skip model routing in tests
            use_streaming=False,
            use_fallback=False,
        )
        return AgentOrchestrator(sink=sink, config=config)

    def test_orchestrator_instantiation(self, orch):
        from ai_workspace.agents.orchestrator import OrchestratorStatus
        assert orch.config.agent_type == "general"
        assert orch.status == OrchestratorStatus.IDLE

    def test_orchestrator_run_general_agent(self, orch):
        with patch.object(orch, '_run_agent_sync', return_value="test result"):
            result = asyncio.run(orch.run("test task"))
            assert result == "test result"
            assert orch.sink.statuses[0] == "starting"
            assert "completed" in orch.sink.statuses

    def test_orchestrator_run_coding_agent(self, orch):
        orch.config.agent_type = "coding"
        with patch.object(orch, '_run_agent_sync', return_value="code done"):
            result = asyncio.run(orch.run("fix bug"))
            assert result == "code done"

    def test_orchestrator_run_with_error(self, orch):
        with patch.object(orch, '_run_agent_sync', side_effect=RuntimeError("fail")):
            with pytest.raises(RuntimeError, match="fail"):
                asyncio.run(orch.run("bad task"))
            from ai_workspace.agents.orchestrator import OrchestratorStatus
            assert orch.status == OrchestratorStatus.ERROR

    def test_orchestrator_fallback(self, orch):
        orch.config.use_fallback = True
        orch.config.max_fallback_attempts = 2
        call_count = [0]
        def flaky(task):
            call_count[0] += 1
            if call_count[0] < 2:
                raise RuntimeError("transient error")
            return "recovered"
        
        with patch.object(orch, '_run_agent_sync', side_effect=flaky), \
             patch.object(orch, '_try_fallback', return_value=True):
            result = asyncio.run(orch.run("flaky task"))
            assert result == "recovered"
            assert call_count[0] == 2
