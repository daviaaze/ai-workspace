"""AI Workspace CLI — `aiw` command.

This is a package that exposes `app` (a typer.Typer) as the main entry point.
Commands are organized into domain modules imported here.
"""

from ai_workspace.cli._app import app
from ai_workspace.cli._main import *  # noqa: F401, F403 — attach main commands

__all__ = ["app"]
