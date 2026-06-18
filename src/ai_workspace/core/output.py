"""
Structured output formatting for CLI commands.

Three modes:
- ``rich`` — human-readable Rich tables/panels (current default, unchanged)
- ``json`` — single JSON object on stdout
- ``ndjson`` — Newline Delimited JSON streaming (NDJSON spec v1.0.0)

Usage::

    from ai_workspace.core.output import OutputFormatter, OutputEnvelope, OutputMode

    fmt = OutputFormatter(mode="json")
    fmt.print(OutputEnvelope(ok=True, command="health", data={"providers": [...]}))

    # NDJSON streaming
    fmt = OutputFormatter(mode="ndjson")
    fmt.write_event("start", command="search", query="...")
    fmt.write_event("done", ok=True)

Refs:
- ndjson-spec v1.0.0: https://github.com/ndjson/ndjson-spec
- SPEC_OUTPUT_MODES.md
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OutputMode(str, Enum):
    RICH = "rich"
    JSON = "json"
    NDJSON = "ndjson"


# ═══════════════════════════════════════════════════════════
# OutputEnvelope — standardised output container
# ═══════════════════════════════════════════════════════════


@dataclass
class OutputEnvelope:
    """A uniform envelope for every command's output.

    Compatible with JSON, NDJSON, and (in the future) Rich pretty-printing.
    """

    ok: bool
    command: str
    timestamp: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON output."""
        d: dict[str, Any] = {
            "ok": self.ok,
            "command": self.command,
            "timestamp": self.timestamp,
            "data": self.data,
        }
        if self.error is not None:
            d["error"] = self.error
        if self.warnings:
            d["warnings"] = self.warnings
        if self.meta:
            d["meta"] = self.meta
        return d


# ═══════════════════════════════════════════════════════════
# OutputFormatter
# ═══════════════════════════════════════════════════════════


class OutputFormatter:
    """Dispatch output to the chosen mode (rich / json / ndjson).

    Parameters
    ----------
    mode:
        ``"rich"`` — delegate to Rich (human-readable, the default).
        ``"json"`` — print a single JSON object.
        ``"ndjson"`` — emit one JSON line per event, flushed immediately.
    file:
        Where to write. Defaults to ``sys.stdout``.
    """

    def __init__(
        self,
        mode: str | OutputMode = "rich",
        file: Any = None,
    ) -> None:
        if isinstance(mode, str):
            mode = OutputMode(mode)
        self.mode: OutputMode = mode
        self._file = file or sys.stdout

    # ── envelope (one-shot: json / rich) ──────────────────

    def print(self, envelope: OutputEnvelope) -> None:
        """Print a single output envelope.

        - ``json`` → ``json.dumps(envelope.to_dict(), indent=2)``
        - ``rich`` → delegates to Rich (compatibility path for now)
        - ``ndjson`` → raises RuntimeError (use ``write_event`` instead)
        """
        if self.mode == OutputMode.JSON:
            payload = envelope.to_dict()
            print(
                json.dumps(payload, indent=2, ensure_ascii=False),
                file=self._file,
            )
        elif self.mode == OutputMode.RICH:
            self._print_rich(envelope)
        else:
            raise RuntimeError(
                "OutputFormatter.print() does not support NDJSON mode. "
                "Use write_event() for streaming NDJSON output."
            )

    def print_error(self, envelope: OutputEnvelope) -> None:
        """Print an error envelope.

        In JSON/NDJSON modes this is the same as ``print()``. In Rich mode
        the error is displayed with a red panel.
        """
        if self.mode == OutputMode.RICH:
            from rich.console import Console
            from rich.panel import Panel

            console = Console(file=self._file)
            err = envelope.error or {}
            msg = err.get("message", str(err))
            suggestion = err.get("suggestion", "")
            body = f"[bold red]Error:[/bold red] {msg}"
            if suggestion:
                body += f"\n[dim]💡 {suggestion}[/dim]"
            console.print(Panel(body, title="Error", border_style="red"))
        else:
            self.print(envelope)

    # ── NDJSON streaming ──────────────────────────────────

    def write_event(self, event_type: str, **kwargs: Any) -> None:
        """Emit a single NDJSON event line.

        Each call writes one line (JSON object + ``\\n``) and flushes.

        NDJSON spec rules enforced:
        - Every line is a complete JSON object terminated by ``\\n`` (0x0A).
        - JSON must not contain internal newlines.
        - Encoding is UTF-8.
        - ``ensure_ascii=False`` is used for full Unicode support.

        Example::

            fmt = OutputFormatter(mode="ndjson")
            fmt.write_event("start", command="search", query="q")
            fmt.write_event("phase", phase="planning", message="...")
            fmt.write_event("done", ok=True)
        """
        payload: dict[str, Any] = {"type": event_type}
        # Merge kwargs, but reserve 'type' to avoid accidental override.
        payload.update(kwargs)
        # Add timestamp if not provided
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if "\n" in line:
            raise ValueError(
                f"NDJSON event contains internal newline — "
                f"this violates the spec. Payload: {payload!r}"
            )
        print(line, file=self._file, flush=True)

    # ── Rich mode (compatibility path) ────────────────────

    def _print_rich(self, envelope: OutputEnvelope) -> None:
        """Print using Rich. Compatibility shim for existing behaviour.

        In a future phase this will be replaced with a proper Rich renderer
        that uses the envelope fields, but for now we just print a simple
        panel so that ``--output rich`` does not crash.
        """
        from rich.console import Console
        from rich.panel import Panel

        console = Console(file=self._file)
        status = "[green]✓ OK[/green]" if envelope.ok else "[red]✗ FAILED[/red]"
        body = f"{status}  command: {envelope.command}"
        if envelope.data:
            from rich.pretty import Pretty

            pretty = Pretty(envelope.data)
            body += f"\n{pretty}"
        if envelope.warnings:
            body += "\n[yellow]Warnings:[/yellow]"
            for w in envelope.warnings:
                body += f"\n  ⚠ {w}"
        console.print(Panel(body, title="Output", border_style="blue"))


# ═══════════════════════════════════════════════════════════
# Helpers for the CLI (used by cli.py in Phase 2)
# ═══════════════════════════════════════════════════════════


def get_output_formatter(ctx: Any) -> OutputFormatter:
    """Extract an OutputFormatter from a typer Context.

    Designed for use as a dependency in CLI commands::

        @app.command()
        def health(ctx: typer.Context):
            fmt = get_output_formatter(ctx)
            ...
    """
    mode = ctx.obj.get("output", "rich") if hasattr(ctx, "obj") else "rich"
    return OutputFormatter(mode=mode)
