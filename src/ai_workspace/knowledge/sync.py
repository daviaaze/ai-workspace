"""
Multi-PC knowledge base sync module.

Architecture:
  thinkbook Tailscale homelab (PostgreSQL central)
  thinkbook git GitHub (Obsidian vault)
  homelab   git GitHub (Obsidian vault)

This module adds:
- Automatic DB connection switching (local vs remote)
- Obsidian vault git sync
- Offline queue: store locally when disconnected, flush when reconnected
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_workspace.knowledge import KnowledgeStore


class SyncManager:
    """Manages multi-PC sync for the AI Workspace knowledge base."""

    def __init__(
        self,
        primary_db_url: str | None = None,
        local_db_url: str | None = None,
        vault_path: str | None = None,
        vault_repo_url: str | None = None,
    ):
        # Primary = homelab PostgreSQL (via Tailscale)
        self.primary_db_url = primary_db_url or os.getenv(
            "AIW_PRIMARY_DB_URL",
            "postgresql://ai_workspace@dvision-homelab:5432/ai_workspace",
        )
        
        # Local fallback (SQLite for offline)
        self.local_db_url = local_db_url or os.getenv(
            "AIW_LOCAL_DB_URL",
            "postgresql:///ai_workspace",
        )
        
        self.vault_path = Path(vault_path or os.getenv(
            "AIW_OBSIDIAN_VAULT",
            str(Path.home() / "Documents" / "Obsidian"),
        ))
        
        self.vault_repo_url = vault_repo_url or os.getenv(
            "AIW_VAULT_REPO",
            "git@github.com:daviaaze/ai-workspace-vault.git",
        )
        
        self._offline_queue: list[dict[str, Any]] = []
        self._offline_queue_path = Path.home() / ".ai-workspace" / "offline_queue.jsonl"

    def is_primary_available(self) -> bool:
        """Check if the primary (homelab) database is reachable."""
        try:
            import socket
            host = self.primary_db_url.split("@")[1].split(":")[0] if "@" in self.primary_db_url else "localhost"
            port = int(self.primary_db_url.split(":")[-1].split("/")[0]) if ":" in self.primary_db_url.split("@")[-1] else 5432
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def get_store(self) -> KnowledgeStore:
        """Get the appropriate store (primary if available, local fallback)."""
        if self.is_primary_available():
            return KnowledgeStore(db_url=self.primary_db_url)
        else:
            return KnowledgeStore(db_url=self.local_db_url)

    async def sync_knowledge(self, direction: str = "both") -> dict[str, Any]:
        """
        Sync knowledge between local and primary.
        
        Directions:
        - "push": local → primary
        - "pull": primary → local
        - "both": bidirectional
        """
        result = {"pushed": 0, "pulled": 0, "offline_queue_flushed": 0}
        
        if not self.is_primary_available():
            return {"error": "Primary database not available", "queued": len(self._offline_queue)}
        
        primary = KnowledgeStore(db_url=self.primary_db_url)
        local = KnowledgeStore(db_url=self.local_db_url)
        
        try:
            primary.initialize()
            local.initialize()
            
            if direction in ("push", "both"):
                # Push local knowledge to primary
                entries = local.search_knowledge("", limit=1000)
                for entry in entries:
                    try:
                        primary.add_knowledge(
                            content=entry["content"],
                            content_type=entry.get("content_type", "note"),
                            title=entry.get("title"),
                            source=f"{os.uname().nodename}:{entry.get('source', '')}",
                            tags=entry.get("tags"),
                            metadata=entry.get("metadata"),
                        )
                        result["pushed"] += 1
                    except Exception:
                        pass  # Skip duplicates
                
                # Push research
                c = local.conn.cursor()
                c.execute("SELECT * FROM research_entries ORDER BY created_at DESC LIMIT 100")
                for row in c.fetchall():
                    try:
                        primary.conn.cursor().execute(
                            """INSERT INTO research_entries 
                               (query, summary, detailed_report, sources, confidence, sub_questions, tags, created_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            row[1:],
                        )
                        result["pushed"] += 1
                    except Exception:
                        pass
                primary.conn.commit()
                c.close()
            
            if direction in ("pull", "both"):
                # Pull primary knowledge to local
                entries = primary.search_knowledge("", limit=500)
                for entry in entries:
                    try:
                        local.add_knowledge(
                            content=entry["content"],
                            content_type=entry.get("content_type", "note"),
                            title=entry.get("title"),
                            source=entry.get("source", "homelab"),
                            tags=entry.get("tags"),
                            metadata=entry.get("metadata"),
                        )
                        result["pulled"] += 1
                    except Exception:
                        pass
                
                # Pull agent memories
                for agent_name in ["continuous-learner", "default"]:
                    memories = primary.recall(agent_name, "%", limit=100)
                    for mem in memories:
                        try:
                            local.remember(
                                agent_name=agent_name,
                                content=mem["content"],
                                memory_type=mem.get("memory_type", "fact"),
                                importance=mem.get("importance", 0.5),
                                metadata=mem.get("metadata"),
                            )
                            result["pulled"] += 1
                        except Exception:
                            pass
            
            # Flush offline queue
            if self._offline_queue:
                result["offline_queue_flushed"] = await self._flush_queue()
        
        finally:
            local.close()
            primary.close()
        
        return result

    async def _flush_queue(self) -> int:
        """Flush offline queue to primary DB."""
        flushed = 0
        primary = KnowledgeStore(db_url=self.primary_db_url)
        primary.initialize()
        
        try:
            for entry in self._offline_queue:
                try:
                    op = entry.get("op")
                    if op == "add_knowledge":
                        primary.add_knowledge(**entry["args"])
                    elif op == "save_research":
                        primary.save_research(**entry["args"])
                    elif op == "remember":
                        primary.remember(**entry["args"])
                    elif op == "add_task":
                        primary.add_task(**entry["args"])
                    flushed += 1
                except Exception:
                    pass
            
            primary.conn.commit()
            self._offline_queue.clear()
        
        finally:
            primary.close()
        
        # Persist cleared queue
        self._save_queue()
        
        return flushed

    def enqueue_offline(self, op: str, **kwargs) -> None:
        """Queue an operation for later when offline."""
        self._offline_queue.append({
            "op": op,
            "args": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save_queue()

    def _save_queue(self) -> None:
        """Persist offline queue to disk."""
        self._offline_queue_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._offline_queue_path, "w") as f:
            for entry in self._offline_queue:
                f.write(json.dumps(entry) + "\n")

    def _load_queue(self) -> None:
        """Load offline queue from disk."""
        if self._offline_queue_path.exists():
            with open(self._offline_queue_path) as f:
                self._offline_queue = [
                    json.loads(line) for line in f if line.strip()
                ]

    async def sync_vault(self) -> dict[str, Any]:
        """Sync Obsidian vault via git (auto-commit + pull --rebase + push)."""
        import subprocess
        
        result = {"committed": 0, "pulled": False, "pushed": False}
        
        if not self.vault_path.exists():
            # Clone if doesn't exist
            subprocess.run(
                ["git", "clone", self.vault_repo_url, str(self.vault_path)],
                check=False,
            )
            result["cloned"] = True
            return result
        
        try:
            # Add and commit local changes
            subprocess.run(
                ["git", "-C", str(self.vault_path), "add", "-A"],
                check=True, capture_output=True,
            )
            
            commit_result = subprocess.run(
                ["git", "-C", str(self.vault_path), "commit", "-m",
                 f"auto-sync: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} [{os.uname().nodename}]"],
                check=False, capture_output=True, text=True,
            )
            
            if "nothing to commit" not in commit_result.stdout + commit_result.stderr:
                result["committed"] = 1
            
            # Pull with rebase (avoid merge commits)
            pull_result = subprocess.run(
                ["git", "-C", str(self.vault_path), "pull", "--rebase", "origin", "main"],
                check=False, capture_output=True, text=True,
            )
            result["pulled"] = pull_result.returncode == 0
            
            # Push
            push_result = subprocess.run(
                ["git", "-C", str(self.vault_path), "push", "origin", "main"],
                check=False, capture_output=True, text=True,
            )
            result["pushed"] = push_result.returncode == 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result


# Periodic sync task (runs every hour via Huey)

def create_sync_periodic_task(huey_instance=None):
    """Create a periodic sync task. Call from scheduler module."""
    if huey_instance is None:
        from ai_workspace.tasks import huey as h
        huey_instance = h
    
    from huey import crontab
    
    @huey_instance.periodic_task(crontab(minute=30))  # Every hour at :30
    def periodic_multi_pc_sync():
        """Hourly sync: knowledge base + vault across PCs."""
        manager = SyncManager()
        manager._load_queue()
        
        results = {}
        
        # Sync knowledge base
        try:
            kb_result = asyncio.run(manager.sync_knowledge("both"))
            results["knowledge_base"] = kb_result
        except Exception as e:
            results["knowledge_base"] = {"error": str(e)}
        
        # Sync vault (every 6 hours to avoid excessive git operations)
        current_hour = datetime.now(timezone.utc).hour
        if current_hour % 6 == 0:
            try:
                vault_result = asyncio.run(manager.sync_vault())
                results["vault"] = vault_result
            except Exception as e:
                results["vault"] = {"error": str(e)}
        
        return results
    
    return periodic_multi_pc_sync
