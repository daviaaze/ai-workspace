"""
AI Workspace Core — Shared service layer.

All interfaces (CLI, TUI, MCP, Streamlit) call into these services.
No interface should contain business logic directly.
"""

# All imports are lazy so the package is usable even when optional
# dependencies (psycopg2, etc.) are not installed.


def __getattr__(name: str):
    _imports = {
        "CostService": "ai_workspace.core.cost",
        "SemanticCache": "ai_workspace.core.cost",
        "SourceReputationService": "ai_workspace.core.sources",
        "ProjectManager": "ai_workspace.core.projects",
        # New Phase 1 modules
        "OutputFormatter": "ai_workspace.core.output",
        "OutputEnvelope": "ai_workspace.core.output",
        "OutputMode": "ai_workspace.core.output",
        "Success": "ai_workspace.core.result",
        "Failure": "ai_workspace.core.result",
        "Result": "ai_workspace.core.result",
        "AiWError": "ai_workspace.core.result",
        "ErrorCode": "ai_workspace.core.result",
    }
    if name in _imports:
        import importlib
        mod = importlib.import_module(_imports[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CostService", "SemanticCache", "SourceReputationService", "ProjectManager",
    "OutputFormatter", "OutputEnvelope", "OutputMode",
    "Success", "Failure", "Result", "AiWError", "ErrorCode",
]
