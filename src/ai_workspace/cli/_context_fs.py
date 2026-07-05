"""CLI commands — `aiw context-fs`."""

from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.table import Table

from ai_workspace.cli._app import app, console

# Context FS commands


context_fs_app = typer.Typer(
    help="RAGFS: context as filesystem (OpenViking experiment)",
    no_args_is_help=True,
)
app.add_typer(context_fs_app, name="context-fs")


@context_fs_app.command(name="ls")
def context_fs_ls(
    path: str = typer.Argument("/", help="Virtual path to list"),
):
    """List entries in the context filesystem.

    Example paths:
        /         — root (kb/, memory/, trace/, info)
        /kb/      — knowledge bases
        /memory/  — L1/L2/L3 tiers
        /trace/   — session traces
    """
    from ai_workspace.context_fs import VirtualContextFS

    fs = VirtualContextFS()
    entries = fs.ls(path)

    if not entries:
        console.print(f"[dim]No entries at {path}[/]")
        return

    table = Table(title=f" RAGFS: {path}")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Size")

    for e in entries:
        icon = "📁" if e["type"] == "dir" else "📄"
        size_str = str(e["size"]) if e["size"] else "—"
        desc = e.get("desc", "")
        name = f"{e['name']}  {desc}" if desc else e["name"]
        table.add_row(f"{icon} {name}", e["type"], size_str)

    console.print(table)


@context_fs_app.command(name="cat")
def context_fs_cat(
    path: str = typer.Argument(..., help="Virtual path to read"),
):
    """Read content from the context filesystem.

    Examples:
        aiw context-fs cat /info              — FS overview
        aiw context-fs cat /memory/l1/        — recent traces
        aiw context-fs cat /kb/search/config  — search KBs
    """
    from ai_workspace.context_fs import VirtualContextFS

    fs = VirtualContextFS()
    try:
        content = fs.read(path)
        console.print(Markdown(f"# RAGFS: {path}\n\n{content}"))
    except FileNotFoundError:
        console.print(f"[red]Path not found: {path}[/]")
        raise typer.Exit(1)


@context_fs_app.command(name="write")
def context_fs_write(
    path: str = typer.Argument(..., help="Virtual path to write"),
    content: str = typer.Argument(..., help="Content to write"),
):
    """Write content to the context filesystem (stores to memory).

    Example:
        aiw context-fs write /memory/l2/mylearning "Learned X about Y"
    """
    from ai_workspace.context_fs import VirtualContextFS

    fs = VirtualContextFS()
    dest = fs.write(path, content)
    console.print(f"[green]Written to:[/] {dest}")


@context_fs_app.command(name="mount")
def context_fs_mount(
    mountpoint: str = typer.Argument(
        ..., help="Directory to mount the context FS",
    ),
):
    """Mount RAGFS as a FUSE filesystem (requires fusepy).

    Example:
        sudo mkdir -p /mnt/ragfs && sudo chown $USER /mnt/ragfs
        aiw context-fs mount /mnt/ragfs
    """
    from ai_workspace.context_fs import mount_fuse

    try:
        console.print(f"[yellow]Mounting RAGFS at {mountpoint}...[/]")
        console.print("[dim]Press Ctrl+C to unmount.[/]")
        mount_fuse(mountpoint)
    except ImportError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1)
    except RuntimeError as exc:
        console.print(f"[red]Mount failed: {exc}[/]")
        raise typer.Exit(1)
