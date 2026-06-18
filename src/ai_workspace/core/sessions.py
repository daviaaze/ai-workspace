"""
SessionStore — persistent agent sessions with tree structure.

Adapted from pi's session-format.md + session-manager.js.
Uses PostgreSQL as the primary store, supporting:
- JSONL entry format compatible with pi
- Tree structure via id/parentId
- Compaction entries with file operation tracking
- Session branching and switching
- Import/export from pi's JSONL format

Schema:
  sessions         — session metadata (id, cwd, created_at, etc.)
  session_entries   — individual entries forming a conversation tree
    entry types: session, message, compaction, branch_summary,
                 model_change, thinking_level_change
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

from ai_workspace.knowledge import KnowledgeStore


CURRENT_SESSION_VERSION = 3
SESSION_DIR = Path.home() / ".aiw" / "sessions"

# Compaction settings (pi defaults, battle-tested)
DEFAULT_COMPACTION_SETTINGS = {
    "enabled": True,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000,
}


@dataclass
class SessionEntry:
    """A single entry in a session conversation tree."""
    id: str
    session_id: str
    parent_id: str | None
    entry_type: str  # session, message, compaction, branch_summary, model_change, thinking_level_change
    role: str | None = None  # user, assistant, system, tool_result
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tokens_used: int = 0
    
    def to_json(self) -> str:
        """Serialize to JSON line (pi-compatible)."""
        return json.dumps({
            "id": self.id,
            "parentId": self.parent_id,
            "type": self.entry_type,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "tokens": self.tokens_used,
        }, default=str)


@dataclass
class ActiveSession:
    """Metadata for an active session."""
    id: str
    cwd: str
    model: str = "qwen3:14b"
    thinking_level: str = "medium"
    version: int = CURRENT_SESSION_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    entry_count: int = 0
    total_tokens: int = 0
    compaction_count: int = 0
    label: str | None = None


class SessionStore:
    """Manages persistent agent sessions with tree-structured entries.
    
    Uses PostgreSQL as primary storage. Can export/import to pi's JSONL format
    for interoperability.
    """
    
    def __init__(self, db_url: str | None = None):
        if db_url is None:
            db_url = "postgresql://ai_workspace:ai_workspace@localhost:2284/ai_workspace"
        self.db_url = db_url
        self.conn = psycopg2.connect(db_url)
        self.conn.autocommit = True
        psycopg2.extras.register_uuid()
    
    def initialize(self) -> None:
        """Create session tables if they don't exist."""
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                cwd TEXT NOT NULL DEFAULT '.',
                model TEXT NOT NULL DEFAULT 'qwen3:14b',
                thinking_level TEXT NOT NULL DEFAULT 'medium',
                version INTEGER NOT NULL DEFAULT 3,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                entry_count INTEGER NOT NULL DEFAULT 0,
                total_tokens BIGINT NOT NULL DEFAULT 0,
                compaction_count INTEGER NOT NULL DEFAULT 0,
                label TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS session_entries (
                id TEXT NOT NULL,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                parent_id TEXT,
                entry_type TEXT NOT NULL,
                role TEXT,
                content TEXT,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                tokens_used INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (session_id, id)
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_entries_parent
            ON session_entries(session_id, parent_id)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_entries_created
            ON session_entries(session_id, created_at)
        """)
        c.close()
    
    
    def create_session(
        self,
        cwd: str = ".",
        model: str = "qwen3:14b",
        label: str | None = None,
    ) -> ActiveSession:
        """Create a new agent session."""
        session_id = str(uuid.uuid4()).replace("-", "")[:16]
        
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO sessions (id, cwd, model, label)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (session_id, cwd, model, label))
        c.close()
        
        # Create the session header entry (pi-compatible)
        self._add_entry(
            session_id=session_id,
            entry_id=session_id,
            parent_id=None,
            entry_type="session",
            role="system",
            content=None,
            metadata={"version": CURRENT_SESSION_VERSION, "cwd": cwd, "model": model},
        )
        
        return ActiveSession(id=session_id, cwd=cwd, model=model, label=label)
    
    def get_session(self, session_id: str) -> ActiveSession | None:
        """Get session metadata."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
        row = c.fetchone()
        c.close()
        if not row:
            return None
        return ActiveSession(
            id=row[0], cwd=row[1], model=row[2], thinking_level=row[3],
            version=row[4], created_at=row[5].isoformat() if row[5] else "",
            updated_at=row[6].isoformat() if row[6] else "",
            entry_count=row[7], total_tokens=row[8], compaction_count=row[9],
            label=row[10],
        )
    
    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent sessions."""
        c = self.conn.cursor()
        c.execute("""
            SELECT id, cwd, model, label, entry_count, updated_at
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT %s
        """, (limit,))
        rows = c.fetchall()
        c.close()
        return [
            {
                "id": r[0], "cwd": r[1], "model": r[2], "label": r[3],
                "entry_count": r[4], "updated_at": r[5].isoformat() if r[5] else "",
            }
            for r in rows
        ]
    
    def update_session(self, session_id: str, **kwargs) -> None:
        """Update session metadata."""
        if not kwargs:
            return
        sets = [f"{k} = %s" for k in kwargs]
        values = list(kwargs.values()) + [session_id]
        c = self.conn.cursor()
        c.execute(f"UPDATE sessions SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", values)
        c.close()
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its entries."""
        c = self.conn.cursor()
        c.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        c.close()
    
    
    def _add_entry(
        self,
        session_id: str,
        entry_id: str,
        parent_id: str | None,
        entry_type: str,
        role: str | None = None,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        tokens: int = 0,
    ) -> SessionEntry:
        """Internal: add a raw entry to a session."""
        meta_json = json.dumps(metadata or {}, default=str)
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO session_entries (id, session_id, parent_id, entry_type, role, content, metadata, tokens_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, id) DO NOTHING
        """, (entry_id, session_id, parent_id, entry_type, role, content[:100_000] if content else None, meta_json, tokens))
        
        # Update session stats
        c.execute("""
            UPDATE sessions 
            SET entry_count = entry_count + 1, 
                total_tokens = total_tokens + %s,
                updated_at = NOW()
            WHERE id = %s
        """, (tokens, session_id))
        c.close()
        
        return SessionEntry(
            id=entry_id, session_id=session_id, parent_id=parent_id,
            entry_type=entry_type, role=role, content=content,
            metadata=metadata or {}, tokens_used=tokens,
        )
    
    def add_message(
        self,
        session_id: str,
        role: str,  # user, assistant, system
        content: str,
        parent_id: str | None = None,
        tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> SessionEntry:
        """Add a message entry to the session."""
        entry_id = str(uuid.uuid4()).replace("-", "")[:12]
        return self._add_entry(
            session_id=session_id,
            entry_id=entry_id,
            parent_id=parent_id,
            entry_type="message",
            role=role,
            content=content,
            metadata=metadata,
            tokens=tokens,
        )
    
    def add_tool_call(
        self,
        session_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: str | None = None,
        parent_id: str | None = None,
    ) -> tuple[SessionEntry, str]:
        """Add a tool call and its result as paired entries."""
        call_id = str(uuid.uuid4()).replace("-", "")[:12]
        
        # Tool call entry
        call_entry = self._add_entry(
            session_id=session_id,
            entry_id=call_id,
            parent_id=parent_id,
            entry_type="message",
            role="tool_call",
            content=json.dumps(tool_args, default=str),
            metadata={"tool_name": tool_name, "tool_args": tool_args},
        )
        
        # Tool result entry (linked to call)
        result_id = str(uuid.uuid4()).replace("-", "")[:12]
        result_entry = self._add_entry(
            session_id=session_id,
            entry_id=result_id,
            parent_id=call_id,
            entry_type="message",
            role="tool_result",
            content=tool_result,
            metadata={"tool_name": tool_name, "call_id": call_id},
        )
        
        return call_entry, result_id
    
    def add_compaction(
        self,
        session_id: str,
        summary: str,
        tokens_before: int,
        parent_id: str | None = None,
        first_kept_entry_id: str | None = None,
    ) -> SessionEntry:
        """Add a compaction entry (like pi's context compaction)."""
        entry_id = str(uuid.uuid4()).replace("-", "")[:12]
        meta = {
            "tokens_before": tokens_before,
            "first_kept_entry_id": first_kept_entry_id,
        }
        entry = self._add_entry(
            session_id=session_id,
            entry_id=entry_id,
            parent_id=parent_id,
            entry_type="compaction",
            role="system",
            content=summary,
            metadata=meta,
            tokens=0,  # Compaction doesn't consume context tokens (it saves them)
        )
        
        # Update compaction count
        c = self.conn.cursor()
        c.execute("""
            UPDATE sessions SET compaction_count = compaction_count + 1, updated_at = NOW()
            WHERE id = %s
        """, (session_id,))
        c.close()
        
        return entry
    
    def add_branch_summary(
        self,
        session_id: str,
        summary: str,
        from_entry_id: str,
        parent_id: str | None = None,
    ) -> SessionEntry:
        """Add a branch summary (when returning from a sub-session)."""
        entry_id = str(uuid.uuid4()).replace("-", "")[:12]
        return self._add_entry(
            session_id=session_id,
            entry_id=entry_id,
            parent_id=parent_id,
            entry_type="branch_summary",
            role="system",
            content=summary,
            metadata={"from_id": from_entry_id},
        )
    
    def add_model_change(
        self,
        session_id: str,
        model: str,
        parent_id: str | None = None,
    ) -> SessionEntry:
        """Record a model change in the session."""
        entry_id = str(uuid.uuid4()).replace("-", "")[:12]
        entry = self._add_entry(
            session_id=session_id,
            entry_id=entry_id,
            parent_id=parent_id,
            entry_type="model_change",
            role="system",
            content=model,
        )
        self.update_session(session_id, model=model)
        return entry
    
    
    def get_entries(
        self,
        session_id: str,
        limit: int = 200,
        before_entry_id: str | None = None,
        entry_types: list[str] | None = None,
    ) -> list[SessionEntry]:
        """Get session entries ordered by creation time."""
        c = self.conn.cursor()
        query = """
            SELECT id, session_id, parent_id, entry_type, role, content, metadata, created_at, tokens_used
            FROM session_entries
            WHERE session_id = %s
        """
        params: list[Any] = [session_id]
        
        if before_entry_id:
            query += " AND created_at < (SELECT created_at FROM session_entries WHERE session_id = %s AND id = %s)"
            params.extend([session_id, before_entry_id])
        
        if entry_types:
            placeholders = ", ".join(["%s"] * len(entry_types))
            query += f" AND entry_type IN ({placeholders})"
            params.extend(entry_types)
        
        query += " ORDER BY created_at ASC LIMIT %s"
        params.append(limit)
        
        c.execute(query, params)
        rows = c.fetchall()
        c.close()
        
        return [
            SessionEntry(
                id=r[0], session_id=r[1], parent_id=r[2],
                entry_type=r[3], role=r[4], content=r[5],
                metadata=r[6] if isinstance(r[6], dict) else json.loads(r[6] or "{}"),
                created_at=r[7].isoformat() if r[7] else "",
                tokens_used=r[8],
            )
            for r in rows
        ]
    
    def get_conversation_tree(self, session_id: str, leaf_entry_id: str | None = None) -> list[SessionEntry]:
        """Walk the conversation tree from root to leaf, following parentId chain.
        
        Handles compaction: if a compaction entry is encountered,
        includes it but skips summarized entries before it.
        """
        entries = self.get_entries(session_id, limit=500)
        if not entries:
            return []
        
        by_id = {e.id: e for e in entries}
        
        if leaf_entry_id and leaf_entry_id in by_id:
            # Walk backwards from leaf to root
            path = []
            current = by_id[leaf_entry_id]
            while current:
                path.append(current)
                if current.parent_id and current.parent_id in by_id:
                    current = by_id[current.parent_id]
                else:
                    break
            path.reverse()
            
            # Check for compaction entries along the path
            compacted_entries = []
            first_kept = None
            for entry in path:
                if entry.entry_type == "compaction":
                    compacted_entries.append(entry)
                    # Get the first kept entry after this compaction
                    meta = entry.metadata if isinstance(entry.metadata, dict) else {}
                    first_kept = meta.get("first_kept_entry_id")
            
            if first_kept and first_kept in by_id:
                # Only include entries from first_kept onward
                result = []
                include = False
                for entry in path:
                    if entry.id == first_kept:
                        include = True
                    if include:
                        result.append(entry)
                # Prepend compaction summaries
                return compacted_entries + result
            
            return path
        
        # No leaf — return all entries ordered
        return entries
    
    def get_last_n_messages(
        self,
        session_id: str,
        n: int = 10,
    ) -> list[dict[str, Any]]:
        """Get the last N messages for quick context injection."""
        entries = self.get_entries(session_id, limit=n * 3)
        messages = []
        for e in entries:
            if e.entry_type == "message" and e.role in ("user", "assistant"):
                messages.append({
                    "id": e.id,
                    "role": e.role,
                    "content": e.content,
                    "created_at": e.created_at,
                })
        return messages[-n:]
    
    def get_estimated_tokens(self, session_id: str) -> int:
        """Get total tokens used in a session."""
        c = self.conn.cursor()
        c.execute("SELECT total_tokens FROM sessions WHERE id = %s", (session_id,))
        row = c.fetchone()
        c.close()
        return row[0] if row else 0
    
    def should_compact(
        self,
        session_id: str,
        context_window: int = 128_000,
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """Check if the session needs compaction (pi's shouldCompact logic)."""
        if settings is None:
            settings = DEFAULT_COMPACTION_SETTINGS
        if not settings.get("enabled", True):
            return False
        
        tokens = self.get_estimated_tokens(session_id)
        return tokens > context_window - settings["reserveTokens"]
    
    
    def export_jsonl(self, session_id: str, path: Path | None = None) -> Path:
        """Export a session to pi-compatible JSONL format."""
        if path is None:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            path = SESSION_DIR / f"{session_id}.jsonl"
        
        entries = self.get_entries(session_id, limit=10_000)
        with open(path, "w") as f:
            for entry in entries:
                f.write(entry.to_json() + "\n")
        
        return path
    
    def import_jsonl(self, path: Path, session_id: str | None = None) -> str:
        """Import a session from pi's JSONL format."""
        if session_id is None:
            session_id = str(uuid.uuid4()).replace("-", "")[:16]
        
        c = self.conn.cursor()
        
        # Create session header
        c.execute("""
            INSERT INTO sessions (id, cwd)
            VALUES (%s, '.')
            ON CONFLICT DO NOTHING
        """, (session_id,))
        
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                entry_id = obj.get("id", str(uuid.uuid4()).replace("-", "")[:12])
                parent_id = obj.get("parentId")
                entry_type = obj.get("type", "message")
                role = obj.get("role", "system")
                content = obj.get("content") or obj.get("summary")
                metadata = obj.get("details") or obj.get("metadata", {})
                tokens = obj.get("tokens", 0)
                
                meta_json = json.dumps(metadata, default=str) if isinstance(metadata, dict) else "{}"
                c.execute("""
                    INSERT INTO session_entries (id, session_id, parent_id, entry_type, role, content, metadata, tokens_used)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, id) DO NOTHING
                """, (entry_id, session_id, parent_id, entry_type, role, content[:100_000] if content else None, meta_json, tokens))
        
        c.close()
        return session_id
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
