"""
AI Workspace Core — Shared service layer.

All interfaces (CLI, TUI, MCP, Streamlit) call into these services.
No interface should contain business logic directly.
"""

from ai_workspace.core.cost import CostService, SemanticCache
from ai_workspace.core.sources import SourceReputationService
from ai_workspace.core.projects import ProjectManager

__all__ = ["CostService", "SemanticCache", "SourceReputationService", "ProjectManager"]
