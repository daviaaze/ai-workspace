"""Agents module — Agent loop, orchestration, and crewAI integration."""


def __getattr__(name: str):
    _imports = {
        # Agent loop (Phase 1 — no external deps)
        "agent_loop": "ai_workspace.agents.loop",
        "LoopParams": "ai_workspace.agents.loop",
        "LoopEvent": "ai_workspace.agents.loop",
        "LoopPattern": "ai_workspace.agents.loop",
        "TerminalReason": "ai_workspace.agents.loop",
        "suggest_pattern": "ai_workspace.agents.loop",
        # Swarm / crewAI (requires crewai package)
        "SwarmConfig": "ai_workspace.agents.swarm",
        "create_researcher": "ai_workspace.agents.swarm",
        "create_coder": "ai_workspace.agents.swarm",
        "create_analyst": "ai_workspace.agents.swarm",
        "create_writer": "ai_workspace.agents.swarm",
        "create_planner": "ai_workspace.agents.swarm",
        "research_crew": "ai_workspace.agents.swarm",
        "code_review_crew": "ai_workspace.agents.swarm",
        "daily_planning_crew": "ai_workspace.agents.swarm",
    }
    if name in _imports:
        import importlib
        mod = importlib.import_module(_imports[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "agent_loop", "LoopParams", "LoopEvent", "LoopPattern", "TerminalReason",
    "suggest_pattern",
    "SwarmConfig", "create_researcher", "create_coder", "create_analyst",
    "create_writer", "create_planner", "research_crew", "code_review_crew",
    "daily_planning_crew",
]
