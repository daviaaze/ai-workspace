"""CLI commands — `aiw projects`."""

from ai_workspace.cli._app import app, console
from rich.panel import Panel
import typer


# Project commands — multi-agent coding with git worktrees

project_app = typer.Typer(help="Manage coding projects with git worktrees")
app.add_typer(project_app, name="project")


@project_app.command()
def create(
    name: str = typer.Argument(..., help="Project name"),
    description: str = typer.Option("", "--description", "-d", help="Project description"),
    repo: list[str] = typer.Option([], "--repo", "-r", help="Repository: name=path (repeatable)"),
):
    """Create a new coding project with optional git repositories."""
    import os as _os
    from ai_workspace.core.projects import ProjectManager

    pm = ProjectManager()
    pm.initialize()

    repos = []
    for r in repo:
        if "=" in r:
            repo_name, repo_path = r.split("=", 1)
        else:
            repo_name = os.path.basename(r.rstrip("/"))
            repo_path = r
        repos.append({"name": repo_name.strip(), "path": _os.path.abspath(repo_path.strip())})

    project = pm.create_project(name, description, repos)
    console.print(f"[green] Project '{name}' created[/]")
    console.print(f"  Repos: {len(project.repos)}")
    for r in project.repos:
        console.print(f"    • {r.name} → {r.path}")


@project_app.command(name="list")
def project_list():
    """List all coding projects."""
    from datetime import datetime, timezone
    from ai_workspace.core.projects import ProjectManager

    pm = ProjectManager()
    projects = pm.list_projects()

    if not projects:
        console.print("[dim]No projects yet. Create one with: aiw project create <name>[/]")
        return

    for p in projects:
        agent_info = f"{len(p.agents)} active agents" if p.agents else "no active agents"
        console.print(f"[bold]{p.name}[/] — {p.description or 'no description'} — [dim]{agent_info}[/]")
        for r in p.repos:
            console.print(f"   {r.name} → {r.path}")
        for a in p.agents:
            elapsed = ""
            if a.started_at:
                try:
                    st = datetime.fromisoformat(a.started_at.replace("Z", "+00:00"))
                    delta = datetime.now(timezone.utc) - st
                    elapsed = f" ({delta.seconds // 60}m ago)"
                except Exception:
                    pass
            console.print(f"   [cyan]{a.name}[/] [{a.branch}] — {a.task[:60]}…{elapsed}")
        console.print()


@project_app.command()
def spawn(
    project_name: str = typer.Argument(..., help="Project to spawn agent in"),
    repo_name: str = typer.Argument("main", help="Repository within the project"),
    task: str = typer.Option(..., "--task", "-t", help="Coding task for the agent"),
    agent_name: str = typer.Option("", "--name", "-n", help="Agent name (auto-generated if empty)"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="LLM model for coding"),
):
    """Spawn a coding agent in an isolated git worktree."""
    from datetime import datetime
    from ai_workspace.core.projects import ProjectManager
    from ai_workspace.agents.swarm import SwarmConfig, coding_crew

    pm = ProjectManager()
    pm.initialize()

    if not agent_name:
        agent_name = f"agent-{datetime.now().strftime('%H%M%S')}"

    # Create worktree
    console.print(f"[dim]Creating worktree for {agent_name}...[/]")
    wt = pm.create_worktree(project_name, agent_name, repo_name, task, model)
    console.print(f"[green] Worktree: {wt.worktree_path}[/]")
    console.print(f"[green] Branch: {wt.branch}[/]")
    console.print()

    # Spawn coding crew in the worktree
    console.print(f"[bold cyan]Spawning coding agent in worktree...[/]")
    cfg = SwarmConfig(coder_model=f"ollama/{model}")
    crew = coding_crew(task_description=task, cfg=cfg, working_dir=wt.worktree_path)

    try:
        result = crew.kickoff()
        summary = str(result)[:500]
        console.print()
        console.print(Panel(summary, title=f" {agent_name} Complete"))

        # Update DB
        c = pm.conn.cursor()
        c.execute(
            "UPDATE project_agents SET status = 'completed', completed_at = NOW(), summary = %s "
            "WHERE project_name = %s AND agent_name = %s",
            (summary, project_name, agent_name),
        )
    except Exception as e:
        console.print(f"[red] Agent failed: {e}[/]")
        c = pm.conn.cursor()
        c.execute(
            "UPDATE project_agents SET status = 'failed', summary = %s "
            "WHERE project_name = %s AND agent_name = %s",
            (str(e)[:500], project_name, agent_name),
        )


@project_app.command()
def cleanup(
    project_name: str = typer.Argument(..., help="Project name"),
    agent_name: str = typer.Option("", "--agent", "-a", help="Agent to clean up (all completed if empty)"),
):
    """Clean up completed agent worktrees."""
    from psycopg2.extras import RealDictCursor
    from ai_workspace.core.projects import ProjectManager

    pm = ProjectManager()

    if agent_name:
        pm.cleanup_worktree(project_name, agent_name)
        console.print(f"[green] Cleaned up {agent_name}[/]")
    else:
        # Clean all completed agents
        c = pm.conn.cursor(cursor_factory=RealDictCursor)
        c.execute(
            "SELECT agent_name FROM project_agents WHERE project_name = %s AND status = 'completed'",
            (project_name,),
        )
        for row in c.fetchall():
            pm.cleanup_worktree(project_name, row["agent_name"])
            console.print(f"[green] Cleaned up {row['agent_name']}[/]")
