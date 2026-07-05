"""Tool base class — local namespace for agent-callable tools.

This module provides a single import path (``ai_workspace.tools.base.Tool``)
for all workspace tools, decoupling them from the upstream crewai package
while remaining wire-compatible with CrewAI's ``BaseTool`` surface.

Phase B1 (this file): ``Tool`` subclasses ``crewai.tools.BaseTool`` so
behaviour is unchanged — tools just import from a local name and lose the
direct ``crewai`` import in their files.

Phase B5+: CrewAI is now an optional dependency. When not installed,
a minimal Pydantic ``_BaseTool`` is used (sufficient for single-agent
``agent_loop``-based execution).
"""

from __future__ import annotations

__all__ = ["Tool", "BaseTool"]

try:
    from crewai.tools import BaseTool

    Tool = BaseTool
except ImportError:
    import logging

    from pydantic import BaseModel

    logger = logging.getLogger("aiw.tools.base")

    logger.debug(
        "crewai[tools] not installed — using minimal Tool base. "
        "Install with: pip install 'ai-workspace[crewai]'"
    )

    class Tool(BaseModel):
        """Minimal tool base (fallback when crewai[tools] not installed).

        Mirrors the subset of ``crewai.tools.BaseTool`` that ``agent_loop``
        actually uses: ``name``, ``description``, ``args_schema``, and
        ``_run()``.
        """

        name: str = ""
        description: str = ""
        args_schema: type[BaseModel] | None = None

        def _run(self, **kwargs) -> str:
            """Execute the tool (override in subclasses)."""
            return f"{self.name} executed"

    BaseTool = Tool

__all__ = ["Tool", "BaseTool"]
