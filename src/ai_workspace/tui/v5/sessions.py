"""Lightweight session storage for the TUI — JSON files, no PostgreSQL needed."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path


def _sessions_dir() -> Path:
    p = Path.home() / ".aiw" / "tui-sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_session(session_id: str, history: list[dict], model: str, summary: str | None = None) -> None:
    """Save a conversation session to a JSON file."""
    path = _sessions_dir() / f"{session_id}.json"
    data = {
        "id": session_id,
        "model": model,
        "summary": summary or "No summary",
        "created_at": datetime.now().isoformat() if not path.exists() else _load_meta(path).get("created_at"),
        "updated_at": datetime.now().isoformat(),
        "entry_count": len(history),
        "messages": history,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _load_meta(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def list_sessions(limit: int = 20) -> list[dict]:
    """List recent sessions."""
    sessions = []
    for path in sorted(_sessions_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = json.loads(path.read_text())
        sessions.append({
            "id": data["id"],
            "model": data.get("model", "?"),
            "summary": data.get("summary", "No summary")[:80],
            "created_at": data.get("created_at", "")[:19],
            "entry_count": data.get("entry_count", 0),
        })
        if len(sessions) >= limit:
            break
    return sessions


def load_session(session_id: str) -> list[dict] | None:
    """Load messages from a saved session."""
    path = _sessions_dir() / f"{session_id}.json"
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("messages", [])
    return None


def delete_session(session_id: str) -> None:
    """Delete a saved session."""
    path = _sessions_dir() / f"{session_id}.json"
    if path.exists():
        path.unlink()


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def export_session(session_id: str) -> str:
    """Export session to readable text."""
    messages = load_session(session_id)
    if not messages:
        return "Session not found"
    lines = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        truncated = content[:500] + "..." if len(content) > 500 else content
        lines.append(f"[{role.upper()}]\n{truncated}\n")
    return "\n".join(lines)
