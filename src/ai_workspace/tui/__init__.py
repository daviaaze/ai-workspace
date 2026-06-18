"""TUI module — AI Workstation interfaces (Textual).

Uses lazy imports to avoid pulling in crewAI + numpy at import time.
"""

import importlib

_imports = {
    "AIWorkspaceApp": "ai_workspace.tui.app",
    "run_tui": "ai_workspace.tui.app",
}


def __getattr__(name: str):
    if name in _imports:
        mod = importlib.import_module(_imports[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AIWorkspaceApp",
    "run_tui",
]
