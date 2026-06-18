"""Knowledge module - Persistent storage, memory, Obsidian integration, multi-PC sync, RAG."""

from ai_workspace.knowledge.store import KnowledgeStore
from ai_workspace.knowledge.sync import SyncManager, create_sync_periodic_task
from ai_workspace.knowledge.rag import (
    DocumentIndexer,
    KnowledgeRetriever,
    setup_schema,
    index_workspace,
    search_knowledge,
    retrieve_context,
    EMBED_MODEL,
    EMBED_DIM,
)

__all__ = [
    # Storage & Sync
    "KnowledgeStore",
    "SyncManager",
    "create_sync_periodic_task",
    # RAG
    "DocumentIndexer",
    "KnowledgeRetriever",
    "setup_schema",
    "index_workspace",
    "search_knowledge",
    "retrieve_context",
    "EMBED_MODEL",
    "EMBED_DIM",
]
