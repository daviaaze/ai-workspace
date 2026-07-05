"""Knowledge module - Persistent storage, memory, Obsidian integration, multi-PC sync, RAG."""

from ai_workspace.knowledge.doc_indexer import DocCrawler, DocIndexer
from ai_workspace.knowledge.engine import (
    ENGINE_REGISTRY,
    LightRAGEngine,
    MultiEngineRetriever,
    ObsidianEngine,
    PgVectorEngine,
    RetrievalEngine,
    RetrievalResult,
    get_engine,
    list_engines,
)
from ai_workspace.knowledge.rag import (
    EMBED_DIM,
    EMBED_MODEL,
    RERANKER_METHOD,
    RERANKER_MODEL,
    DocumentIndexer,
    KnowledgeRetriever,
    Reranker,
    index_workspace,
    retrieve_context,
    search_knowledge,
    setup_schema,
)
from ai_workspace.knowledge.store import KnowledgeStore
from ai_workspace.knowledge.sync import SyncManager, create_sync_periodic_task

__all__ = [
    # Storage & Sync
    "KnowledgeStore",
    "SyncManager",
    "create_sync_periodic_task",
    # RAG
    "DocumentIndexer",
    "KnowledgeRetriever",
    "Reranker",
    "setup_schema",
    "index_workspace",
    "search_knowledge",
    "retrieve_context",
    "EMBED_MODEL",
    "EMBED_DIM",
    "RERANKER_MODEL",
    "RERANKER_METHOD",
    # Engine abstraction
    "RetrievalEngine",
    "RetrievalResult",
    "PgVectorEngine",
    "ObsidianEngine",
    "LightRAGEngine",
    "MultiEngineRetriever",
    "get_engine",
    "list_engines",
    "ENGINE_REGISTRY",
]
