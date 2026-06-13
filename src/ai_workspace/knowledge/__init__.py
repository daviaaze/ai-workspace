"""Knowledge module - Persistent storage, memory, Obsidian integration, multi-PC sync."""

from ai_workspace.knowledge.store import KnowledgeStore
from ai_workspace.knowledge.sync import SyncManager, create_sync_periodic_task

__all__ = ["KnowledgeStore", "SyncManager", "create_sync_periodic_task"]
