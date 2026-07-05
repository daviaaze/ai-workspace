"""
Agent Observability — Diff tracking, trace storage, state inspection.

Three layers:
  1. Execution Trace — already covered by LoopEvent streaming
  2. Code-Level Diff — what CHANGED in files (DiffTracker)
  3. State Inspector — full session record for post-mortem (TraceStore)

Refs:
- SPEC_OBSERVABILITY.md
- Observability Gap (arXiv 2603.26942, CHI 2026)
"""

from __future__ import annotations

import difflib
import json as _json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.observability")

TRACE_DIR: Path = Path.home() / ".aiw" / "traces"


# ═══════════════════════════════════════════════════════════
# DiffTracker — code-level file change tracking
# ═══════════════════════════════════════════════════════════

@dataclass
class FileSnapshot:
    """A file's state at a point in the agent's execution."""
    path: str
    content: str
    timestamp: float
    agent_step: int


class DiffTracker:
    """Tracks all file changes during agent execution.

    Usage:
        tracker = DiffTracker()
        tracker.snapshot("src/main.py", step=1)   # before edit
        # ... agent edits file ...
        tracker.snapshot("src/main.py", step=3)   # after edit
        diff = tracker.get_diff("src/main.py", 1, 3)
    """

    def __init__(self):
        self.snapshots: dict[str, list[FileSnapshot]] = {}

    def snapshot(self, path: str, step: int) -> None:
        """Capture a file's current state at a given agent step."""
        resolved = Path(path).resolve()
        path_str = str(resolved)

        if not resolved.exists():
            return

        try:
            content = resolved.read_text()
        except Exception as exc:
            logger.debug("Failed to snapshot %s: %s", path, exc)
            return

        snap = FileSnapshot(
            path=path_str,
            content=content,
            timestamp=time.monotonic(),
            agent_step=step,
        )

        if path_str not in self.snapshots:
            self.snapshots[path_str] = []
        self.snapshots[path_str].append(snap)

    def get_diff(self, path: str, step_a: int, step_b: int) -> str:
        """Generate a unified diff between two snapshots."""
        resolved = str(Path(path).resolve())
        # Try resolved first, fall back to original path
        snaps = self.snapshots.get(
            resolved, self.snapshots.get(path, []),
        )

        a = next(
            (s for s in snaps if s.agent_step == step_a), None,
        )
        b = next(
            (s for s in snaps if s.agent_step == step_b), None,
        )

        if not a or not b:
            return f"No snapshots for step {step_a} or {step_b}"

        diff = difflib.unified_diff(
            a.content.splitlines(keepends=True),
            b.content.splitlines(keepends=True),
            fromfile=f"{path} (step {step_a})",
            tofile=f"{path} (step {step_b})",
        )
        return "".join(diff)

    def get_summary(self) -> dict[str, Any]:
        """Summary of all tracked changes."""
        changes: dict[str, int] = {}
        for path_str, snaps in self.snapshots.items():
            if len(snaps) > 1:
                changes[path_str] = len(snaps) - 1

        return {
            "files_modified": len(self.snapshots),
            "total_snapshots": sum(
                len(s) for s in self.snapshots.values()
            ),
            "changes": changes,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage."""
        return {
            path: [
                {
                    "path": s.path,
                    "content": s.content,
                    "timestamp": s.timestamp,
                    "agent_step": s.agent_step,
                }
                for s in snaps
            ]
            for path, snaps in self.snapshots.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiffTracker:
        """Deserialize from storage."""
        tracker = cls()
        for path, snaps in data.items():
            tracker.snapshots[path] = [
                FileSnapshot(**s) for s in snaps
            ]
        return tracker


# ═══════════════════════════════════════════════════════════
# AgentTrace — full execution record
# ═══════════════════════════════════════════════════════════

@dataclass
class AgentTrace:
    """Complete record of an agent execution session.

    Attributes:
        session_id: Unique session identifier.
        task: Original task description.
        model: LLM model used.
        provider: LLM provider.
        steps: Ordered list of execution steps.
        files_modified: Files changed during execution.
        tools_called: Tool name -> call count.
        tokens_used: Total tokens consumed.
        cost: Estimated cost (USD).
        errors: Error messages encountered.
        diff_tracker: File change history.
        duration_ms: Total execution time.
    """
    session_id: str
    task: str = ""
    model: str = ""
    provider: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    tools_called: dict[str, int] = field(default_factory=dict)
    tokens_used: int = 0
    cost: float = 0.0
    errors: list[dict[str, Any]] = field(default_factory=list)
    diff_tracker_data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def record_step(
        self,
        step_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Record an execution step."""
        step: dict[str, Any] = {
            "type": step_type,
            "timestamp": time.monotonic(),
        }
        if data:
            step["data"] = data

        if step_type == "tool_call":
            tool_name = (data or {}).get("tool", "unknown")
            self.tools_called[tool_name] = (
                self.tools_called.get(tool_name, 0) + 1
            )
        elif step_type == "error":
            self.errors.append(data or {})

        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON storage."""
        d = asdict(self)
        d["step_count"] = len(self.steps)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentTrace:
        """Deserialize from JSON storage."""
        return cls(
            session_id=data.get("session_id", ""),
            task=data.get("task", ""),
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            steps=data.get("steps", []),
            files_modified=data.get("files_modified", []),
            tools_called=data.get("tools_called", {}),
            tokens_used=data.get("tokens_used", 0),
            cost=data.get("cost", 0.0),
            errors=data.get("errors", []),
            diff_tracker_data=data.get("diff_tracker_data", {}),
            duration_ms=data.get("duration_ms", 0.0),
        )


# ═══════════════════════════════════════════════════════════
# TraceStore — persistent trace storage
# ═══════════════════════════════════════════════════════════

class TraceStore:
    """Save and load agent execution traces (JSON on disk)."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or TRACE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, trace: AgentTrace) -> Path:
        """Persist a trace to disk. Returns the file path."""
        path = self.base_dir / f"{trace.session_id}.json"
        data = trace.to_dict()
        # Truncate large diff contents for storage
        if "diff_tracker_data" in data:
            for snaps in data["diff_tracker_data"].values():
                for snap in snaps:
                    snap["content"] = snap.get("content", "")[:5000]
        path.write_text(_json.dumps(data, indent=2, default=str))
        logger.debug("Trace saved: %s (%d steps)", path, len(trace.steps))
        return path

    def load(self, session_id: str) -> AgentTrace | None:
        """Load a trace from disk."""
        path = self.base_dir / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = _json.loads(path.read_text())
            return AgentTrace.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to load trace %s: %s", session_id, exc)
            return None

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List saved sessions with summaries."""
        sessions = []
        for p in sorted(
            self.base_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )[:limit]:
            try:
                data = _json.loads(p.read_text())
                sessions.append({
                    "session_id": data.get("session_id", p.stem),
                    "task": (data.get("task", "") or "")[:80],
                    "model": data.get("model", ""),
                    "steps": data.get("step_count", len(data.get("steps", []))),
                    "tokens": data.get("tokens_used", 0),
                    "errors": len(data.get("errors", [])),
                    "duration_ms": data.get("duration_ms", 0),
                })
            except Exception:
                sessions.append({
                    "session_id": p.stem,
                    "task": "(corrupt)",
                    "model": "",
                    "steps": 0,
                    "tokens": 0,
                    "errors": 0,
                    "duration_ms": 0,
                })
        return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a trace from disk."""
        path = self.base_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False


# ═══════════════════════════════════════════════════════════
# Convenience
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# OpenTelemetry Exporter (optional, HALO-compatible)
# ═══════════════════════════════════════════════════════════

class OTelExporter:
    """Optional OpenTelemetry exporter for agent traces.

    When configured, emits spans compatible with OpenInference format
    so traces can be ingested by HALO, Arize, Langfuse, or any OTel
    collector.

    Configure via environment variables:
      CATALYST_OTLP_TOKEN     — If set, uploads over OTLP
      CATALYST_OTLP_ENDPOINT  — OTLP endpoint base URL
      HALO_TELEMETRY_PATH     — Local fallback file path

    Usage::

        exporter = OTelExporter()
        trace = AgentTrace(session_id="...")
        ... run agent ...
        exporter.export(trace)

    This is a no-op if no OTel environment is configured.
    """

    def __init__(self) -> None:
        self._enabled = False
        self._endpoint = os.environ.get("CATALYST_OTLP_ENDPOINT", "")
        self._token = os.environ.get("CATALYST_OTLP_TOKEN", "")
        self._fallback_path_str = os.environ.get("HALO_TELEMETRY_PATH", "")

        if self._token or self._endpoint or self._fallback_path_str:
            self._enabled = True

    @property
    def enabled(self) -> bool:
        """Whether this exporter has any destination configured."""
        return self._enabled

    def export(self, trace: AgentTrace) -> bool:
        """Export a trace to configured destinations.

        Returns True if export was attempted (even if it failed).
        """
        if not self._enabled:
            return False

        exported = False

        # Local JSONL fallback
        if self._fallback_path_str:
            exported |= self._export_local(trace)

        # OTLP export (requires opentelemetry-api package)
        if self._token or self._endpoint:
            exported |= self._export_otlp(trace)

        return exported

    def _export_local(self, trace: AgentTrace) -> bool:
        """Write trace to local JSONL file (HALO-compatible format)."""
        try:
            path = Path(self._fallback_path_str)
            path.parent.mkdir(parents=True, exist_ok=True)

            record = {
                "session_id": trace.session_id,
                "task": trace.task,
                "model": trace.model,
                "provider": trace.provider,
                "timestamp": time.time(),
                "steps": len(trace.steps),
                "tokens_used": trace.tokens_used,
                "cost": trace.cost,
                "errors": len(trace.errors),
                "duration_ms": trace.duration_ms,
                "tools_called": trace.tools_called,
            }

            with open(path, "a") as f:
                f.write(_json.dumps(record) + "\n")

            logger.debug("OTel fallback: wrote trace to %s", path)
            return True

        except Exception as exc:
            logger.warning("OTel local export failed: %s", exc)
            return False

    def _export_otlp(self, trace: AgentTrace) -> bool:
        """Export trace via OTLP protocol.

        This is a best-effort export — if the opentelemetry packages
        aren't installed, it silently skips.
        """
        try:
            # Lazy import — OTel packages are optional
            from opentelemetry import trace as otel_trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
        except ImportError:
            logger.debug(
                "OTLP export skipped: install opentelemetry packages. "
                "pip install opentelemetry-api opentelemetry-sdk "
                "opentelemetry-exporter-otlp-proto-http"
            )
            return False

        try:
            resource = Resource.create({
                "service.name": "aiw",
                "service.version": "0.2.0",
            })

            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            endpoint = self._endpoint or "https://telemetry.inference.net"

            exporter = OTLPSpanExporter(
                endpoint=f"{endpoint}/v1/traces",
                headers=headers,
            )

            provider = SDKTracerProvider(resource=resource)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            otel_trace.set_tracer_provider(provider)

            tracer = otel_trace.get_tracer("aiw.observability")

            with tracer.start_as_current_span(
                f"agent.{trace.session_id[:16]}",
                attributes={
                    "session_id": trace.session_id,
                    "task": trace.task[:500],
                    "model": trace.model,
                    "provider": trace.provider,
                    "steps": len(trace.steps),
                    "tokens_used": trace.tokens_used,
                    "cost": trace.cost,
                    "errors": len(trace.errors),
                    "duration_ms": trace.duration_ms,
                },
            ) as span:
                span.set_status(otel_trace.StatusCode.OK if not trace.errors else otel_trace.StatusCode.ERROR)

            processor.shutdown()
            logger.debug("OTLP export via %s", endpoint)
            return True

        except Exception as exc:
            logger.warning("OTLP export failed: %s", exc)
            return False


# ═══════════════════════════════════════════════════════════
# Convenience
# ═══════════════════════════════════════════════════════════

def trace_agent_loop(session_id: str) -> tuple[AgentTrace, DiffTracker]:
    """Create trace + diff tracker for an AgentLoop session.

    Usage in agent_loop callers::

        trace, diff_tracker = trace_agent_loop("session-abc")
        params = LoopParams(...)
        async for event in agent_loop(params):
            trace.record_step(event.type, event.data)
            if event.type == "tool_result":
                # Snapshot files after tool execution
                pass    # caller handles this
        trace_store.save(trace)
    """
    trace = AgentTrace(session_id=session_id)
    diff_tracker = DiffTracker()
    return trace, diff_tracker
