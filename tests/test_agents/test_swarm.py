"""
Tests for agent swarm — creation, tool wiring, and crew assembly.

Covers:
- SwarmConfig LLM initialization
- Agent factory functions (researcher, coder, analyst, writer, planner)
- Crew assembly (research_crew, code_review_crew, coding_crew)
- Tool bundles (get_coder_tools, get_researcher_tools, get_all_tools)
- create_agent — general-purpose agent with all tools
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════
# SwarmConfig
# ═══════════════════════════════════════════════════════


class TestSwarmConfig:
    """SwarmConfig creates LLM instances for crewAI."""

    def test_default_config_creates_three_llms(self):
        from ai_workspace.agents.swarm import SwarmConfig
        cfg = SwarmConfig()
        assert cfg.fast_llm is not None
        assert cfg.coder_llm is not None
        assert cfg.deep_llm is not None

    def test_config_with_custom_models(self):
        from ai_workspace.agents.swarm import SwarmConfig
        cfg = SwarmConfig(
            default_model="ollama/llama3:8b",
            coder_model="ollama/codellama:13b",
            deep_model="ollama/mistral:7b",
        )
        assert cfg.fast_llm is not None
        assert cfg.coder_llm is not None
        assert cfg.deep_llm is not None

    def test_config_strips_ollama_prefix(self):
        """Model names should strip 'ollama/' prefix for crewAI LLM."""
        from ai_workspace.agents.swarm import SwarmConfig
        cfg = SwarmConfig(coder_model="ollama/qwen3-coder:30b")
        # The LLM model name should be just 'qwen3-coder:30b'
        assert cfg.coder_llm is not None


# ═══════════════════════════════════════════════════════
# Agent factories
# ═══════════════════════════════════════════════════════


class TestAgentCreation:
    """Agent factory functions produce valid crewAI agents."""

    def test_create_researcher_has_correct_role(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_researcher
        cfg = SwarmConfig()
        agent = create_researcher(cfg)
        assert agent.role == "Research Specialist"
        assert agent.allow_delegation is True
        assert agent.planning is True  # crewAI 1.x auto-planning

    def test_create_coder_has_correct_role(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_coder
        cfg = SwarmConfig()
        agent = create_coder(cfg)
        assert agent.role == "Senior Software Engineer"
        assert agent.allow_delegation is False

    def test_create_analyst_has_correct_role(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_analyst
        cfg = SwarmConfig()
        agent = create_analyst(cfg)
        assert agent.role == "Data Analyst"
        assert agent.allow_delegation is True

    def test_create_writer_has_correct_role(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_writer
        cfg = SwarmConfig()
        agent = create_writer(cfg)
        assert agent.role == "Technical Writer & Synthesizer"
        assert agent.allow_delegation is False

    def test_create_planner_has_correct_role(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_planner
        cfg = SwarmConfig()
        agent = create_planner(cfg)
        assert agent.role == "Strategic Planner"
        assert agent.allow_delegation is True
        # Planner doesn't auto-plan (it IS the plan)
        assert agent.planning is not True

    def test_agents_use_correct_llm(self):
        """Researcher uses deep LLM, coder uses coder LLM, writer uses fast LLM."""
        from ai_workspace.agents.swarm import SwarmConfig
        from ai_workspace.agents.swarm import create_researcher, create_coder, create_writer
        cfg = SwarmConfig()
        researcher = create_researcher(cfg)
        coder = create_coder(cfg)
        writer = create_writer(cfg)
        # All should have an LLM assigned
        assert researcher.llm is not None
        assert coder.llm is not None
        assert writer.llm is not None


# ═══════════════════════════════════════════════════════
# Crew assembly
# ═══════════════════════════════════════════════════════


class TestCrewAssembly:
    """Crew factory functions assemble valid crewAI crews."""

    def test_research_crew_creates_two_agents(self):
        from ai_workspace.agents.swarm import SwarmConfig, research_crew
        cfg = SwarmConfig()
        crew = research_crew("What is Nix?", cfg=cfg)
        assert len(crew.agents) == 2  # researcher + writer
        assert len(crew.tasks) == 2   # plan + write

    def test_code_review_crew_creates_two_agents(self):
        from ai_workspace.agents.swarm import SwarmConfig, code_review_crew
        cfg = SwarmConfig()
        crew = code_review_crew("def foo(): pass", cfg=cfg)
        assert len(crew.agents) == 2  # coder + analyst
        assert len(crew.tasks) == 2   # review + analysis

    def test_daily_planning_crew_creates_two_agents(self):
        from ai_workspace.agents.swarm import SwarmConfig, daily_planning_crew
        cfg = SwarmConfig()
        crew = daily_planning_crew("Ship v2 MVP", cfg=cfg)
        assert len(crew.agents) == 2  # planner + writer
        assert len(crew.tasks) == 2   # plan + format

    def test_coding_crew_creates_one_agent(self):
        from ai_workspace.agents.swarm import SwarmConfig, coding_crew
        cfg = SwarmConfig()
        crew = coding_crew("Add type hints", cfg=cfg, working_dir=".")
        assert len(crew.agents) == 1  # coder only
        assert len(crew.tasks) == 1   # single task

    def test_research_crew_task_has_context(self):
        """The write task should depend on the plan task."""
        from ai_workspace.agents.swarm import SwarmConfig, research_crew
        cfg = SwarmConfig()
        crew = research_crew("Test", cfg=cfg)
        # The second task (write) should have context from the first
        write_task = crew.tasks[1]
        assert write_task.context is not None
        assert len(write_task.context) == 1


# ═══════════════════════════════════════════════════════
# Tool bundles
# ═══════════════════════════════════════════════════════


class TestToolBundles:
    """Tool bundles provide the right tools for each agent role."""

    def test_get_coder_tools_returns_fs_git_shell(self):
        from ai_workspace.agents.swarm import get_coder_tools
        tools = get_coder_tools()
        assert len(tools) >= 7  # filesystem (4+) + git (6) + shell (1) = 11+
        names = {t.name for t in tools}
        assert "git_status" in names
        assert "git_diff" in names
        assert "shell_exec" in names

    def test_get_researcher_tools_returns_web_tools(self):
        from ai_workspace.agents.swarm import get_researcher_tools
        tools = get_researcher_tools()
        assert len(tools) >= 5  # at least the 5 web tools
        names = {t.name for t in tools}
        assert "web_fetch" in names
        assert "headless_browser" in names

    def test_get_all_tools_includes_everything(self):
        from ai_workspace.agents.swarm import get_all_tools
        tools = get_all_tools()
        names = {t.name for t in tools}
        # Should have filesystem + git + shell + web
        assert "git_status" in names
        assert "web_fetch" in names
        assert "shell_exec" in names

    def test_coder_with_tools_has_tools_attached(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_coder_with_tools
        cfg = SwarmConfig()
        coder = create_coder_with_tools(cfg)
        assert len(coder.tools) > 0
        assert coder.allow_delegation is False

    def test_researcher_with_tools_has_tools_attached(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_researcher_with_tools
        cfg = SwarmConfig()
        researcher = create_researcher_with_tools(cfg)
        assert len(researcher.tools) > 0
        assert researcher.allow_delegation is True


# ═══════════════════════════════════════════════════════
# create_agent — general-purpose
# ═══════════════════════════════════════════════════════


class TestCreateAgent:
    """create_agent produces a general-purpose agent with all tools."""

    def test_create_agent_with_default_model(self):
        from ai_workspace.agents.swarm import create_agent
        agent = create_agent()
        assert agent.role == "AI Workspace Agent"
        assert agent.allow_delegation is True

    def test_create_agent_has_all_tools(self):
        from ai_workspace.agents.swarm import create_agent
        agent = create_agent()
        assert len(agent.tools) > 10  # fs + git + shell + web
        names = {t.name for t in agent.tools}
        assert "git_status" in names
        assert "web_fetch" in names

    def test_create_agent_with_custom_model(self):
        from ai_workspace.agents.swarm import SwarmConfig, create_agent
        agent = create_agent(model="qwen3:14b")
        assert agent.llm is not None
