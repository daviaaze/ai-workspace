"""AI Workspace CLI — `aiw` command."""



from __future__ import annotations

from ai_workspace.cli._agent import *  # noqa: F401, F403
from ai_workspace.cli._ask import *  # noqa: F401, F403
from ai_workspace.cli._cache import *  # noqa: F401, F403 — aiw cache
from ai_workspace.cli._context_fs import *  # noqa: F401, F403
from ai_workspace.cli._docs import *  # noqa: F401, F403
from ai_workspace.cli._eval import *  # noqa: F401, F403
from ai_workspace.cli._kb import *  # noqa: F401, F403
from ai_workspace.cli._loop import *  # noqa: F401, F403
from ai_workspace.cli._mcp import *  # noqa: F401, F403

# Extracted CLI modules (typer groups registered in each)
from ai_workspace.cli._memory import *  # noqa: F401, F403 — aiw memory
from ai_workspace.cli._obsidian import *  # noqa: F401, F403 — aiw obsidian
from ai_workspace.cli._partner import *  # noqa: F401, F403
from ai_workspace.cli._projects import *  # noqa: F401, F403 — aiw project
from ai_workspace.cli._queue import *  # noqa: F401, F403
from ai_workspace.cli._research import *  # noqa: F401, F403 — aiw research
from ai_workspace.cli._rules import *  # noqa: F401, F403
from ai_workspace.cli._schedule import *  # noqa: F401, F403 — aiw schedule
from ai_workspace.cli._search import *  # noqa: F401, F403
from ai_workspace.cli._session import *  # noqa: F401, F403 — aiw session
from ai_workspace.cli._skill import *  # noqa: F401, F403 — aiw skill
from ai_workspace.cli._source import *  # noqa: F401, F403 — aiw source
from ai_workspace.cli._system import *  # noqa: F401, F403
from ai_workspace.cli._tasks import *  # noqa: F401, F403
from ai_workspace.cli._tools import *  # noqa: F401, F403 — aiw tool
from ai_workspace.cli._trace import *  # noqa: F401, F403
from ai_workspace.cli._wf import *  # noqa: F401, F403 — aiw wf
from ai_workspace.cli._worktree import *  # noqa: F401, F403
