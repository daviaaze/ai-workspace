"""Agents module — Agent loop, orchestration, and crewAI integration."""


def __getattr__(name: str):
    _imports = {
        # Agent loop (Phase 1 — no external deps)
        "agent_loop": "ai_workspace.agents.loop",
        "coding_agent_loop": "ai_workspace.agents.loop",
        "LoopParams": "ai_workspace.agents.loop",
        "LoopEvent": "ai_workspace.agents.loop",
        "LoopPattern": "ai_workspace.agents.loop",
        "TerminalReason": "ai_workspace.agents.loop",
        "suggest_pattern": "ai_workspace.agents.loop",
        "Capability": "ai_workspace.agents.loop",
        "get_capability": "ai_workspace.agents.loop",
        "suggest_capability": "ai_workspace.agents.loop",
        "BUILTIN_CAPABILITIES": "ai_workspace.agents.loop",
        "CAPABILITY_CHAT": "ai_workspace.agents.loop",
        "CAPABILITY_RESEARCH": "ai_workspace.agents.loop",
        "CAPABILITY_CODE": "ai_workspace.agents.loop",
        "CAPABILITY_SOLVE": "ai_workspace.agents.loop",
        "CAPABILITY_WRITE": "ai_workspace.agents.loop",
        "PersistentMemory": "ai_workspace.agents.memory",
        "TraceEvent": "ai_workspace.agents.memory",
        "L1Trace": "ai_workspace.agents.memory",
        "L2Fact": "ai_workspace.agents.memory",
        "MemoryStats": "ai_workspace.agents.memory",
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
        # Improvement cycle (HALO-inspired, Phase 1.2)
        "ImprovementCycle": "ai_workspace.agents.improvement",
        "ImprovementReport": "ai_workspace.agents.improvement",
        "TraceAnalyzer": "ai_workspace.agents.improvement",
        "ReportApplier": "ai_workspace.agents.improvement",
    }
    if name in _imports:
        import importlib
        mod = importlib.import_module(_imports[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "agent_loop", "coding_agent_loop", "LoopParams", "LoopEvent", "LoopPattern", "TerminalReason",
    "suggest_pattern",
    "Capability", "get_capability", "suggest_capability",
    "BUILTIN_CAPABILITIES",
    "CAPABILITY_CHAT", "CAPABILITY_RESEARCH", "CAPABILITY_CODE",
    "CAPABILITY_SOLVE", "CAPABILITY_WRITE",
    "PersistentMemory", "TraceEvent", "L1Trace", "L2Fact", "MemoryStats",
    "ImprovementCycle", "ImprovementReport", "TraceAnalyzer", "ReportApplier",
    "SwarmConfig", "create_researcher", "create_coder", "create_analyst",
    "create_writer", "create_planner", "research_crew", "code_review_crew",
    "daily_planning_crew",
]
