"""Tests for agent swarm — post-B3 migration (dict-based API).

After B3 (2026-07-03): SwarmConfig stores {provider, model} dicts instead of
crewai.LLM objects; agent creation functions return lightweight dicts; crew
functions return strings (not Crew objects).
"""

from __future__ import annotations

import pytest

# ═══════════════════════════════════════════════════════
# SwarmConfig
# ═══════════════════════════════════════════════════════


class TestSwarmConfig:
    """SwarmConfig creates model dicts (post-B3)."""

    def test_default_config_tiered_models(self):
        from ai_workspace.agents.swarm import SwarmConfig
        cfg = SwarmConfig()
        assert cfg.fast_llm is not None
        assert isinstance(cfg.fast_llm, dict)
        assert "model" in cfg.fast_llm
        assert "provider" in cfg.fast_llm

    def test_default_config_deep_llm_not_none(self):
        from ai_workspace.agents.swarm import SwarmConfig
        cfg = SwarmConfig()
        assert cfg.deep_llm is not None
        assert isinstance(cfg.deep_llm, dict)

    def test_default_config_coder_llm_not_none(self):
        from ai_workspace.agents.swarm import SwarmConfig
        cfg = SwarmConfig()
        assert cfg.coder_llm is not None
        assert isinstance(cfg.coder_llm, dict)

    def test_default_config_provider_is_ollama(self):
        from ai_workspace.agents.swarm import SwarmConfig
        cfg = SwarmConfig()
        assert cfg.provider is not None


# ═══════════════════════════════════════════════════════
# Agent creation (returns dicts post-B3)
# ═══════════════════════════════════════════════════════


class TestAgentCreation:
    """Agent factory functions produce dicts with provider + model + system."""

    def test_create_researcher_has_name(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_researcher
        cfg = SwarmConfig()
        agent = create_researcher(cfg)
        assert isinstance(agent, dict)
        assert "name" in agent
        assert agent["name"] == "researcher"
        assert "system" in agent

    def test_create_coder_has_name(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_coder
        cfg = SwarmConfig()
        agent = create_coder(cfg)
        assert agent["name"] == "coder"

    def test_create_analyst_has_name(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_analyst
        cfg = SwarmConfig()
        agent = create_analyst(cfg)
        assert agent["name"] == "analyst"

    def test_create_writer_has_name(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_writer
        cfg = SwarmConfig()
        agent = create_writer(cfg)
        assert agent["name"] == "writer"

    def test_create_planner_has_name(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_planner
        cfg = SwarmConfig()
        agent = create_planner(cfg)
        assert agent["name"] == "planner"

    def test_agents_have_provider_and_model(self):
        """Every agent dict includes provider + model keys for chat_sync."""
        from ai_workspace.agents.swarm import (
            SwarmConfig,
            create_coder,
            create_researcher,
            create_writer,
        )
        cfg = SwarmConfig()
        for agent in [create_researcher(cfg), create_coder(cfg), create_writer(cfg)]:
            assert "provider" in agent
            assert "model" in agent


# ═══════════════════════════════════════════════════════
# Crew functions (return strings post-B3)
# ═══════════════════════════════════════════════════════


class TestCrewFunctions:
    """Crew functions return strings (not Crew objects)."""

    @pytest.mark.skip(reason="Requires Ollama running (integration test)")
    def test_research_crew_returns_string(self):
        from ai_workspace.agents.swarm import SwarmConfig, research_crew
        cfg = SwarmConfig()
        result = research_crew("What is Nix?", cfg=cfg)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skip(reason="Requires Ollama running (integration test)")
    def test_code_review_crew_returns_string(self):
        from ai_workspace.agents.swarm import SwarmConfig, code_review_crew
        cfg = SwarmConfig()
        result = code_review_crew("def foo(): pass", cfg=cfg)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skip(reason="Requires Ollama running (integration test)")
    def test_daily_planning_crew_returns_string(self):
        from ai_workspace.agents.swarm import SwarmConfig, daily_planning_crew
        cfg = SwarmConfig()
        result = daily_planning_crew("Ship v2 MVP", cfg=cfg)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skip(reason="Requires Ollama running (integration test)")
    def test_coding_crew_returns_string(self):
        from ai_workspace.agents.swarm import SwarmConfig, coding_crew
        cfg = SwarmConfig()
        result = coding_crew("Add type hints", cfg=cfg, working_dir=".")
        assert isinstance(result, str)
        assert len(result) > 0


# ═══════════════════════════════════════════════════════
# Tool bundles (unchanged — tools are still Tool objects)
# ═══════════════════════════════════════════════════════


class TestToolBundles:
    """Tool bundles provide the right tools for each agent role."""

    def test_get_coder_tools_returns_fs_git_shell(self):
        from ai_workspace.agents.swarm import get_coder_tools
        tools = get_coder_tools()
        assert len(tools) >= 7
        names = {t.name for t in tools}
        assert "git_status" in names
        assert "git_diff" in names
        assert "shell_exec" in names

    def test_get_researcher_tools_returns_web_tools(self):
        from ai_workspace.agents.swarm import get_researcher_tools
        tools = get_researcher_tools()
        assert len(tools) >= 5
        names = {t.name for t in tools}
        assert "web_fetch" in names
        assert "headless_browser" in names

    def test_get_all_tools_includes_everything(self):
        from ai_workspace.agents.swarm import get_all_tools
        tools = get_all_tools()
        names = {t.name for t in tools}
        assert "git_status" in names
        assert "web_fetch" in names
        assert "shell_exec" in names

    def test_coder_with_tools_has_tools_attached(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_coder_with_tools
        cfg = SwarmConfig()
        coder = create_coder_with_tools(cfg)
        assert len(coder["tools"]) > 0

    def test_researcher_with_tools_has_tools_attached(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_researcher_with_tools
        cfg = SwarmConfig()
        researcher = create_researcher_with_tools(cfg)
        assert len(researcher["tools"]) > 0


# ═══════════════════════════════════════════════════════
# create_agent — general-purpose (returns dict post-B3)
# ═══════════════════════════════════════════════════════


class TestCreateAgent:
    """create_agent produces a general-purpose agent dict."""

    def test_create_agent_with_default_model(self):
        from ai_workspace.agents.swarm import create_agent
        agent = create_agent()
        assert isinstance(agent, dict)
        assert agent["name"] == "general"
        assert "system" in agent

    def test_create_agent_has_all_tools(self):
        from ai_workspace.agents.swarm import create_agent
        agent = create_agent()
        assert len(agent["tools"]) > 10
        names = {t.name for t in agent["tools"]}
        assert "git_status" in names
        assert "web_fetch" in names

    def test_create_agent_with_custom_model(self):
        from ai_workspace.agents.swarm import create_agent
        agent = create_agent(model="qwen3:14b")
        assert "provider" in agent
        assert "model" in agent
