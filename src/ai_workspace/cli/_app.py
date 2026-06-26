"""Shared app and console for CLI commands.

Defined in a separate module to avoid circular imports when submodules
attach commands via @app.command() or app.add_typer().
"""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="aiw",
    help="AI Workspace - Deep search, agent swarm, knowledge base",
    no_args_is_help=True,
)
console = Console()
