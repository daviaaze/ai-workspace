"""PostgreSQL/pgvector-backed knowledge base with Obsidian vault sync."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

# Workspace root for markdown memory files
_WORKSPACE_ROOT = Path(os.environ.get("AIW_WORKSPACE", Path.home() / "Projects" / "pessoal" / "ai-workspace"))


class KnowledgeStore:
    """Persistent knowledge base using PostgreSQL + pgvector."""

    def __init__(
        self,
        db_url: str | None = None,
        obsidian_vault: str | None = None,
    ):
        self.db_url = db_url or os.getenv(
            "AIW_DB_URL",
            "postgresql:///ai_workspace",
        )
        self.obsidian_vault = Path(obsidian_vault) if obsidian_vault else None
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            # Try pool first (transparent — no caller changes needed)
            try:
                from ai_workspace.core.db import get_connection
                self._conn = get_connection(self.db_url)
            except Exception:
                self._conn = psycopg2.connect(self.db_url)
                self._conn.autocommit = True
        return self._conn

    def initialize(self) -> None:
        """Create tables and extensions if they don't exist."""
        c = self.conn.cursor()
        c.execute("CREATE EXTENSION IF NOT EXISTS vector")
        c.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                content_type VARCHAR(50) DEFAULT 'note',
                title VARCHAR(500),
                source VARCHAR(500),
                tags TEXT[] DEFAULT '{}',
                embedding vector(1792),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
            ON knowledge_entries USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS research_entries (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                summary TEXT,
                detailed_report TEXT,
                sources TEXT[] DEFAULT '{}',
                confidence REAL DEFAULT 0.0,
                sub_questions JSONB DEFAULT '[]',
                tags TEXT[] DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                priority INTEGER DEFAULT 0,
                tags TEXT[] DEFAULT '{}',
                schedule VARCHAR(100),  -- cron expression
                last_run TIMESTAMPTZ,
                next_run TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS agent_memory (
                id SERIAL PRIMARY KEY,
                agent_name VARCHAR(100) NOT NULL,
                memory_type VARCHAR(50) NOT NULL,  -- 'fact', 'preference', 'learning'
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                embedding vector(1792),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        c.close()



    def add_knowledge(
        self,
        content: str,
        content_type: str = "note",
        title: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Add a knowledge entry."""
        c = self.conn.cursor()
        c.execute(
            """INSERT INTO knowledge_entries
               (content, content_type, title, source, tags, metadata)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (content, content_type, title, source, tags or [], json.dumps(metadata or {})),
        )
        entry_id = c.fetchone()[0]
        c.close()
        return entry_id

    def search_knowledge(
        self,
        query: str,
        content_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search knowledge entries (text-based)."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)

        conditions = ["content ILIKE %s"]
        params: list[Any] = [f"%{query}%"]

        if content_type:
            conditions.append("content_type = %s")
            params.append(content_type)

        if tags:
            conditions.append("tags && %s")
            params.append(tags)

        where = " AND ".join(conditions)
        c.execute(
            f"SELECT * FROM knowledge_entries WHERE {where} ORDER BY created_at DESC LIMIT %s",
            params + [limit],
        )
        results = [dict(r) for r in c.fetchall()]
        c.close()
        return results

    def vector_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        content_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Vector similarity search."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT id, content, title, content_type, tags,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM knowledge_entries
            WHERE embedding IS NOT NULL
        """
        params: list[Any] = [query_embedding]

        if content_type:
            query += " AND content_type = %s"
            params.append(content_type)

        query += " ORDER BY similarity DESC LIMIT %s"
        params.append(limit)

        c.execute(query, params)
        results = [dict(r) for r in c.fetchall()]
        c.close()
        return results



    def save_research(self, query: str, report: dict) -> int:
        """Save a research result."""
        c = self.conn.cursor()
        c.execute(
            """INSERT INTO research_entries
               (query, summary, detailed_report, sources, confidence, sub_questions)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (
                query,
                report.get("summary", ""),
                report.get("detailed_report", ""),
                report.get("sources", []),
                report.get("confidence", 0.0),
                json.dumps(report.get("sub_questions", [])),
            ),
        )
        rid = c.fetchone()[0]
        c.close()
        return rid

    def get_research_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent research history."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute(
            "SELECT * FROM research_entries ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        results = [dict(r) for r in c.fetchall()]
        c.close()
        return results



    def add_task(
        self,
        title: str,
        description: str = "",
        priority: int = 0,
        tags: list[str] | None = None,
        schedule: str | None = None,
    ) -> int:
        """Add a task (optionally recurring via cron schedule)."""
        c = self.conn.cursor()
        c.execute(
            """INSERT INTO tasks (title, description, priority, tags, schedule)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (title, description, priority, tags or [], schedule),
        )
        tid = c.fetchone()[0]
        c.close()
        return tid

    def get_tasks(
        self,
        status: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get tasks, optionally filtered."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)

        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("status = %s")
            params.append(status)
        if tags:
            conditions.append("tags && %s")
            params.append(tags)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        c.execute(
            f"SELECT * FROM tasks{where} ORDER BY priority DESC, created_at DESC LIMIT %s",
            params + [limit],
        )
        results = [dict(r) for r in c.fetchall()]
        c.close()
        return results

    def update_task_status(self, task_id: int, status: str) -> None:
        """Update task status."""
        c = self.conn.cursor()
        c.execute(
            "UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, task_id),
        )
        c.close()

    def get_due_tasks(self) -> list[dict[str, Any]]:
        """Get tasks that are due to run (scheduled + not completed)."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""
            SELECT * FROM tasks
            WHERE schedule IS NOT NULL
              AND status != 'completed'
              AND (next_run IS NULL OR next_run <= NOW())
            ORDER BY priority DESC
        """)
        results = [dict(r) for r in c.fetchall()]
        c.close()
        return results



    def remember(
        self,
        agent_name: str,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: dict | None = None,
    ) -> int:
        """Store a memory for an agent."""
        c = self.conn.cursor()
        c.execute(
            """INSERT INTO agent_memory (agent_name, memory_type, content, importance, metadata)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (agent_name, memory_type, content, importance, json.dumps(metadata or {})),
        )
        mid = c.fetchone()[0]
        c.close()
        return mid

    def recall(
        self,
        agent_name: str,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search agent memories."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)

        conditions = ["agent_name = %s", "content ILIKE %s"]
        params: list[Any] = [agent_name, f"%{query}%"]

        if memory_type:
            conditions.append("memory_type = %s")
            params.append(memory_type)

        where = " AND ".join(conditions)
        c.execute(
            f"SELECT * FROM agent_memory WHERE {where} ORDER BY importance DESC, created_at DESC LIMIT %s",
            params + [limit],
        )
        results = [dict(r) for r in c.fetchall()]
        c.close()
        return results

    def get_facts(self, agent_name: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get all facts remembered about/for an agent."""
        return self.recall(agent_name, "%", memory_type="fact", limit=limit)



    # Mapping from memory_type to markdown file
    MEMORY_FILES: dict[str, str] = {
        "convention": "memory/conventions.md",
        "pattern": "memory/project-patterns.md",
        "learning": "memory/learning-log.md",
    }

    def get_memory_path(self, memory_type: str) -> Path:
        """Get the markdown file path for a memory type."""
        rel_path = self.MEMORY_FILES.get(memory_type, f"memory/{memory_type}.md")
        return _WORKSPACE_ROOT / rel_path

    def append_memory_markdown(self, memory_type: str, entry: dict[str, Any]) -> Path:
        """Append a learning entry to the appropriate markdown memory file.

        Args:
            memory_type: One of 'convention', 'pattern', 'learning'
            entry: Dict with 'title', 'content', and optional 'tags', 'importance'

        Returns:
            Path to the written file
        """
        filepath = self.get_memory_path(memory_type)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        title = entry.get("title", "Untitled")
        content = entry.get("content", "")
        tags = entry.get("tags", [])

        tag_line = ""
        if tags:
            tag_line = f"tags: [{', '.join(tags)}]\n"

        entry_md = f"\n---\n## {title}\n*{timestamp}*  {tag_line}\n\n{content}\n"

        with open(filepath, "a") as f:
            f.write(entry_md)

        return filepath

    def read_memory_markdown(self, memory_type: str) -> str:
        """Read a markdown memory file. Returns '' if it doesn't exist."""
        filepath = self.get_memory_path(memory_type)
        if filepath.exists():
            return filepath.read_text()
        return ""

    def list_memory_files(self) -> list[dict[str, Any]]:
        """List all markdown memory files and their stats."""
        results = []
        for mem_type, rel_path in self.MEMORY_FILES.items():
            filepath = _WORKSPACE_ROOT / rel_path
            if filepath.exists():
                content = filepath.read_text()
                results.append({
                    "type": mem_type,
                    "path": str(rel_path),
                    "size": len(content),
                    "entries": content.count("\n## "),
                })
        return results



    def sync_to_obsidian(
        self,
        vault_path: str | None = None,
        category: str = "knowledge",
    ) -> int:
        """Sync knowledge entries to Obsidian vault as markdown files."""
        vault = Path(vault_path or self.obsidian_vault) if (vault_path or self.obsidian_vault) else None
        if not vault:
            raise ValueError("No Obsidian vault path configured")

        entries = self.search_knowledge("", content_type=category, limit=1000)
        count = 0

        for entry in entries:
            filename = f"{entry.get('title', 'note-' + str(entry['id']))}.md"
            filepath = vault / filename

            content = f"""---
id: {entry['id']}
type: {entry.get('content_type', 'note')}
tags: {json.dumps(entry.get('tags', []))}
created: {entry['created_at'].isoformat() if isinstance(entry['created_at'], datetime) else entry['created_at']}
source: {entry.get('source', 'ai-workspace')}
---

# {entry.get('title', f'Note {entry["id"]}')}

{entry['content']}
"""
            filepath.write_text(content)
            count += 1

        return count

    def import_from_obsidian(
        self,
        vault_path: str | None = None,
    ) -> int:
        """Import markdown notes from Obsidian vault into knowledge store."""
        vault = Path(vault_path or self.obsidian_vault) if (vault_path or self.obsidian_vault) else None
        if not vault:
            raise ValueError("No Obsidian vault path configured")

        count = 0
        for md_file in vault.glob("**/*.md"):
            if md_file.name.startswith("."):
                continue

            content = md_file.read_text()
            title = md_file.stem

            self.add_knowledge(
                content=content,
                content_type="obsidian_note",
                title=title,
                source=str(md_file.relative_to(vault)),
            )
            count += 1

        return count

    def close(self):
        if self._conn and not self._conn.closed:
            try:
                from ai_workspace.core.db import return_connection
                return_connection(self._conn)
            except Exception:
                self._conn.close()
