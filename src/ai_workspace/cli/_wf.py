"""CLI commands — `aiw wf`."""

from ai_workspace.cli._app import app, console
from rich.table import Table
from rich.panel import Panel
import typer


# Workflow commands

def _get_db_url() -> str:
    """Get the database URL from environment or default."""
    import os
    return os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")


wf_app = typer.Typer(help="DAG-based workflow execution")
app.add_typer(wf_app, name="wf")


@wf_app.command(name="list")
def wf_list():
    """List available workflows."""
    from ai_workspace.workflow import WorkflowRegistry

    table = Table(title=" Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    
    # Auto-detect descriptions from workflow classes
    descriptions = {}
    for name in WorkflowRegistry.list():
        wf_cls = WorkflowRegistry.get(name)
        if wf_cls and wf_cls.__doc__:
            # First line of docstring after the title
            lines = wf_cls.__doc__.strip().split("\n")
            # Skip blank lines after the title
            for line in lines:
                stripped = line.strip()
                if stripped:
                    # Grab the first meaningful description line
                    descriptions[name] = stripped[:80]
                    break
    
    for name in WorkflowRegistry.list():
        table.add_row(name, descriptions.get(name, ""))

    console.print(table)


@wf_app.command(name="run")
def wf_run(
    name: str = typer.Argument(..., help="Workflow name"),
    query: str | None = typer.Option(None, "--query", "-q", help="Query for research workflows"),
    depth: int = typer.Option(2, "--depth", "-d", help="Research depth"),
    input_json: str | None = typer.Option(None, "--input", "-i", help="JSON input for workflow"),
    background: bool = typer.Option(False, "--background", "-b", help="Submit to worker queue and return immediately"),
):
    """Run a workflow.

    By default, runs synchronously (blocking). Use --background to submit
    to the Huey worker daemon — the workflow survives SSH disconnects.
    Check status later with: aiw wf status
    """
    from ai_workspace.workflow import WorkflowRegistry

    wf_cls = WorkflowRegistry.get(name)
    if not wf_cls:
        valid = ", ".join(WorkflowRegistry.list())
        console.print(f"[red]Unknown workflow: {name}[/]\nAvailable: {valid}")
        raise typer.Exit(1)

    wf = wf_cls()

    inputs = {}
    if input_json:
        try:
            inputs = json.loads(input_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON input: {e}[/]")
            raise typer.Exit(1)
    elif query:
        inputs = {"query": query, "depth": depth}
    else:
        console.print("[yellow]Provide --query or --input[/]")
        raise typer.Exit(1)

    if background:
        # Submit to Huey worker and return immediately
        from ai_workspace.tasks import run_workflow_task

        console.print(f"[bold cyan]Submitting workflow to background worker: {name}[/]")
        console.print(f"Inputs: {json.dumps(inputs, indent=2)}")
        console.print()

        with console.status("[cyan]Enqueuing...", spinner="dots"):
            result = run_workflow_task(workflow_name=name, inputs=inputs)

        if isinstance(result, dict) and "run_id" in result:
            console.print(f"[green] Submitted (run #{result['run_id']})[/]")
            console.print(f"  [dim]Check status: aiw wf status[/]")
            console.print(f"  [dim]View logs:    aiw wf logs {result['run_id']}[/]")
            console.print(f"  [dim]Retry if fails: aiw wf retry {result['run_id']}[/]")
        else:
            console.print(f"[green] Submitted (task queued)[/]")
            console.print(f"  [dim]Result: {result}[/]")
        return

    console.print(f"[bold cyan]Running workflow: {name}[/]")
    console.print(f"Inputs: {json.dumps(inputs, indent=2)}")
    console.print()

    with console.status(f"[cyan]Executing workflow...", spinner="dots"):
        result = wf.run_sync(**inputs)

    console.print()

    if result.status.value == "done":
        console.print(Panel(
            f"[green] Completed in {result.duration_ms:.0f}ms[/]",
            title=f"Workflow: {name}",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[red] Failed: {result.error}[/]\n\nDuration: {result.duration_ms:.0f}ms",
            title=f"Workflow: {name}",
            border_style="red",
        ))

    # Show steps
    table = Table(title=" Steps")
    table.add_column("Step", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Retries")

    for step_name, step in result.steps.items():
        status_style = {
            "done": "green", "failed": "red", "skipped": "dim",
            "running": "yellow", "pending": "dim",
        }.get(step.status.value, "white")
        table.add_row(
            step_name,
            f"[{status_style}]{step.status.value}[/]",
            f"{step.duration_ms:.0f}ms" if step.duration_ms else "-",
            str(step.retry_count),
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Run ID: {result.run_id} | View logs: aiw wf logs {result.run_id}[/]")


@wf_app.command(name="status")
def wf_status(
    name: str | None = typer.Option(None, "--name", "-n", help="Workflow name"),
    limit: int = typer.Option(20, "--limit", "-l"),
):
    """View workflow runs and their status."""
    db_url = _get_db_url()

    if name:
        from ai_workspace.workflow import WorkflowRegistry
        wf_cls = WorkflowRegistry.get(name)
        if not wf_cls:
            console.print(f"[red]Unknown workflow: {name}[/]")
            raise typer.Exit(1)

        runs = wf_cls.get_runs(limit=limit, db_url=db_url)
        title = f" Runs - {name}"
    else:
        # Show all workflows' recent runs
        from ai_workspace.workflow import WorkflowRegistry
        runs = []
        for wf_name in WorkflowRegistry.list():
            wf_cls = WorkflowRegistry.get(wf_name)
            if wf_cls:
                runs.extend(wf_cls.get_runs(limit=5, db_url=db_url))
        runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        title = f" Recent Runs (all workflows)"

    if not runs:
        console.print("[dim]No runs found[/]")
        return

    table = Table(title=title)
    table.add_column("Run ID", style="dim")
    table.add_column("Workflow")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("When")

    for r in runs[:limit]:
        status_style = {
            "done": "green", "failed": "red", "running": "yellow", "pending": "dim",
        }.get(r.get("status", ""), "white")

        created = r.get("created_at", "")
        if isinstance(created, datetime):
            created = created.strftime("%m-%d %H:%M")
        elif isinstance(created, str) and "T" in created:
            created = created[:16].replace("T", " ")

        table.add_row(
            str(r["run_id"]),
            r.get("workflow_name", "?"),
            f"[{status_style}]{r.get('status', '?')}[/]",
            f"{r.get('duration_ms', 0):.0f}ms",
            str(created),
        )

    console.print(table)


@wf_app.command(name="logs")
def wf_logs(
    run_id: int = typer.Argument(..., help="Run ID to inspect"),
    workflow_name: str | None = typer.Option(None, "--workflow", "-w", help="Workflow name (required for lookup)"),
):
    """View detailed execution logs for a workflow run."""
    # First, find the workflow name from the runs table
    if not workflow_name:
        from ai_workspace.knowledge import KnowledgeStore
        store = get_store(db_url=_get_db_url())
        store.initialize()
        c = store.conn.cursor()
        c.execute("SELECT workflow_name FROM workflow_runs WHERE run_id = %s", (run_id,))
        row = c.fetchone()
        store.close()
        if row:
            workflow_name = row[0]
        else:
            console.print(f"[red]Run {run_id} not found[/]")
            raise typer.Exit(1)

    from ai_workspace.workflow import WorkflowRegistry
    wf_cls = WorkflowRegistry.get(workflow_name)
    if not wf_cls:
        console.print(f"[red]Unknown workflow: {workflow_name}[/]")
        raise typer.Exit(1)

    logs = wf_cls.get_run_logs(run_id, db_url=_get_db_url())

    if not logs:
        console.print(f"[dim]No logs found for run {run_id}[/]")
        return

    console.print(f"[bold]Logs for Run #{run_id} ({workflow_name})[/]\n")

    table = Table(title=" Execution Logs")
    table.add_column("Step", style="cyan")
    table.add_column("Attempt")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Error")

    for log in logs:
        status_style = {
            "done": "green", "failed": "red", "running": "yellow",
        }.get(log.get("status", ""), "white")
        error = log.get("error") or ""
        table.add_row(
            log.get("step_name", "?"),
            str(log.get("attempt", 0)),
            f"[{status_style}]{log.get('status', '?')}[/]",
            f"{log.get('duration_ms', 0):.0f}ms",
            error[:80],
        )

    console.print(table)

    # Show output for completed steps
    for log in logs:
        if log.get("status") == "done" and log.get("output"):
            output = log["output"]
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    pass
            console.print(Panel(
                json.dumps(output, indent=2, default=str)[:1000],
                title=f" Output: {log.get('step_name', '?')}",
                border_style="blue",
            ))


@wf_app.command(name="retry")
def wf_retry(
    run_id: int = typer.Argument(..., help="Run ID to retry"),
    workflow_name: str | None = typer.Option(None, "--workflow", "-w", help="Workflow name"),
):
    """Retry a failed workflow run from the last completed step."""
    if not workflow_name:
        from ai_workspace.knowledge import KnowledgeStore
        store = get_store(db_url=_get_db_url())
        store.initialize()
        c = store.conn.cursor()
        c.execute("SELECT workflow_name FROM workflow_runs WHERE run_id = %s", (run_id,))
        row = c.fetchone()
        store.close()
        if row:
            workflow_name = row[0]
        else:
            console.print(f"[red]Run {run_id} not found[/]")
            raise typer.Exit(1)

    from ai_workspace.workflow import WorkflowRegistry
    wf_cls = WorkflowRegistry.get(workflow_name)
    if not wf_cls:
        console.print(f"[red]Unknown workflow: {workflow_name}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]Retrying run #{run_id} ({workflow_name})...[/]")


@wf_app.command(name="result")
def wf_result(
    task_id: str = typer.Argument(..., help="Task ID from --background submission"),
):
    """Get the result of a background workflow task."""
    from huey.api import Result as HueyResult
    from ai_workspace.tasks import huey

    try:
        result = HueyResult(huey, task_id)
        if result() is not None:
            data = result()
            if isinstance(data, dict):
                console.print(Panel(
                    json.dumps(data, indent=2, default=str),
                    title=f" Task Result: {task_id}",
                ))
            else:
                console.print(str(data))
        else:
            console.print("[yellow]Task not yet completed or not found[/]")
            console.print(f"[dim]Check worker status: systemctl --user status aiw-worker[/]")
    except Exception as e:
        console.print(f"[red]Could not retrieve result: {e}[/]")


@wf_app.command(name="stats")
def wf_stats(
    name: str = typer.Argument(..., help="Workflow name"),
):
    """Show statistics for a workflow."""
    from ai_workspace.workflow import WorkflowRegistry

    wf_cls = WorkflowRegistry.get(name)
    if not wf_cls:
        valid = ", ".join(WorkflowRegistry.list())
        console.print(f"[red]Unknown workflow: {name}[/]\nAvailable: {valid}")
        raise typer.Exit(1)

    stats = wf_cls.get_run_stats(db_url=_get_db_url())

    table = Table(title=f" Stats - {name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total runs", str(stats.get("total", 0)))
    table.add_row("Completed", f"[green]{stats.get('completed', 0)}[/]")
    table.add_row("Failed", f"[red]{stats.get('failed', 0)}[/]" if stats.get("failed", 0) > 0 else str(stats.get("failed", 0)))
    table.add_row("Running", f"[yellow]{stats.get('running', 0)}[/]" if stats.get("running", 0) > 0 else "0")
    table.add_row("Avg duration", f"{stats.get('avg_duration_ms', 0):.0f}ms")
    table.add_row("Avg success duration", f"{stats.get('avg_success_duration_ms', 0):.0f}ms")
    table.add_row("First run", str(stats.get("first_run", "-"))[:19])
    table.add_row("Last run", str(stats.get("last_run", "-"))[:19])

    console.print(table)
