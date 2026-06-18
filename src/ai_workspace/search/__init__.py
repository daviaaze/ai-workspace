"""Search module - Deep recursive research engine."""

from ai_workspace.search.deep_search import DeepSearchEngine, ResearchResult, deep_search
from ai_workspace.search.research_engine import (
    ResearchEngine,
    ResearchPhase,
    ResearchTask,
    EvidenceClaim,
    ResearchReport,
    deep_research,
)

__all__ = [
    # Legacy (crewAI-based, will be deprecated)
    "DeepSearchEngine",
    "ResearchResult",
    "deep_search",
    # New (AgentLoop-based, graph swarm)
    "ResearchEngine",
    "ResearchPhase",
    "ResearchTask",
    "EvidenceClaim",
    "ResearchReport",
    "deep_research",
]
