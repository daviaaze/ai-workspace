"""AI Workspace CLI — `aiw` command."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ai_workspace.providers import chat_sync
from ai_workspace.knowledge import KnowledgeStore
from ai_workspace.core.db import get_store

from ai_workspace.cli._app import app, console

# Extracted CLI modules (typer groups registered in each)
from ai_workspace.cli._memory import *  # noqa: F401, F403 — aiw memory
from ai_workspace.cli._source import *  # noqa: F401, F403 — aiw source
from ai_workspace.cli._session import *  # noqa: F401, F403 — aiw session
from ai_workspace.cli._tools import *  # noqa: F401, F403 — aiw tool
from ai_workspace.cli._schedule import *  # noqa: F401, F403 — aiw schedule
from ai_workspace.cli._skill import *  # noqa: F401, F403 — aiw skill
from ai_workspace.cli._obsidian import *  # noqa: F401, F403 — aiw obsidian
from ai_workspace.cli._cache import *  # noqa: F401, F403 — aiw cache
from ai_workspace.cli._wf import *  # noqa: F401, F403 — aiw wf
from ai_workspace.cli._research import *  # noqa: F401, F403 — aiw research
from ai_workspace.cli._projects import *  # noqa: F401, F403 — aiw project

# Search commands (extracted to cli._search)
from ai_workspace.cli._search import *  # noqa: F401, F403

# Agent commands (extracted to cli._agent)
from ai_workspace.cli._agent import *  # noqa: F401, F403

# Ask & Chat commands (extracted to cli._ask)
from ai_workspace.cli._ask import *  # noqa: F401, F403

# System commands (extracted to cli._system)
from ai_workspace.cli._system import *  # noqa: F401, F403
from ai_workspace.cli._tasks import *  # noqa: F401, F403
from ai_workspace.cli._kb import *  # noqa: F401, F403
from ai_workspace.cli._rules import *  # noqa: F401, F403
from ai_workspace.cli._trace import *  # noqa: F401, F403
from ai_workspace.cli._eval import *  # noqa: F401, F403
from ai_workspace.cli._mcp import *  # noqa: F401, F403
from ai_workspace.cli._partner import *  # noqa: F401, F403
from ai_workspace.cli._context_fs import *  # noqa: F401, F403


# Workflow tail command — follow progress in real-time

@wf_app.command(name="tail")
def wf_tail(
    run_id: int = typer.Argument(..., help="Run ID to follow"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Polling interval in seconds"),
    timeout: float = typer.Option(300.0, "--timeout", "-t", help="Max time to wait"),
):
    """Follow a workflow run's progress in real-time (polls DB).

    Shows step output as it completes. Like 'tail -f' for workflows.
    Press Ctrl+C to stop.
    """
    import time
    from ai_workspace.knowledge import KnowledgeStore

    store = get_store(db_url=_get_db_url())
    store.initialize()

    # Get workflow name
    c = store.conn.cursor()
    c.execute("SELECT workflow_name, status FROM workflow_runs WHERE run_id = %s", (run_id,))
    row = c.fetchone()
    c.close()

    if not row:
        store.close()
        console.print(f"[red]Run #{run_id} not found[/]")
        return

    wf_name, status = row
    console.print(f"[bold cyan]Following workflow #{run_id} ({wf_name})...[/]")
    console.print(f"[dim]Status: {status} | Polling every {interval}s | Press Ctrl+C to stop[/]\n")

    seen_ids = set()
    start = time.time()

    try:
        while time.time() - start < timeout:
            c = store.conn.cursor()
            c.execute(
                """SELECT id, step_name, status, attempt, duration_ms, left(output::text, 500) as output,
                          left(error::text, 200) as error, created_at
                   FROM workflow_step_logs
                   WHERE run_id = %s
                   ORDER BY id""",
                (run_id,),
            )
            logs = c.fetchall()
            c.close()

            for log in logs:
                log_id = log[0]
                if log_id in seen_ids:
                    continue
                seen_ids.add(log_id)

                step_name, status, attempt, dur, output, error, ts = log[1:8]

                if status == "running":
                    console.print(f"  [yellow]⟳[/] {step_name} (attempt {attempt + 1})...")
                elif status == "done":
                    icon = ""
                    dur_str = f" {dur:.0f}ms" if dur else ""
                    console.print(f"  {icon} [green]{step_name}[/]{dur_str}")
                    if output and len(output) > 10:
                        # Show a preview of the output
                        preview = output[:300].replace("\\n", "\n    ")
                        console.print(f"    [dim]{preview}...[/]")
                elif status == "failed":
                    console.print(f"   [red]{step_name}[/] failed: {error}")

            # Check if run finished
            c = store.conn.cursor()
            c.execute(
                "SELECT status, duration_ms, error FROM workflow_runs WHERE run_id = %s",
                (run_id,),
            )
            run_row = c.fetchone()
            c.close()

            if run_row and run_row[0] in ("done", "failed"):
                final_status = run_row[0]
                final_dur = run_row[1] or 0
                final_error = run_row[2]

                console.print()
                if final_status == "done":
                    console.print(Panel(
                        f"[green] Workflow completed in {final_dur:.0f}ms[/]",
                        border_style="green",
                    ))
                else:
                    console.print(Panel(
                        f"[red] Workflow failed: {final_error}[/]",
                        border_style="red",
                    ))
                    console.print(f"  [dim]Retry: aiw wf retry {run_id}[/]")

                console.print(f"[dim]View report: aiw research view <id>[/]")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped[/]")
    finally:
        store.close()
