"""
Retrieval Engine Abstraction — pluggable backends for RAG.

Inspired by DeepTutor's Knowledge Center, which lets users choose the
engine per knowledge base: vector (pgvector), graph (LightRAG), page
index (shallow), or Obsidian vault.

This module provides:

- ``RetrievalResult`` — uniform result type across all engines
- ``RetrievalEngine`` — abstract base class (the interface)
- ``PgVectorEngine`` — adapter for the existing pgvector-based RAG
- ``LightRAGEngine`` — adapter for LightRAG (graph-based retrieval)
- ``ObsidianEngine`` — adapter for reading Obsidian vaults in-place
- ``get_engine`` — factory that returns the right engine for a KB type

Usage::

    engine = get_engine("vector", kb_path="/path/to/docs")
    results = engine.retrieve("auth middleware", k=5)
    for r in results:
        print(f\"[{r.score:.2f}] {r.source}: {r.content[:100]}\")

Or with the composite orchestrator::

    engines = [get_engine("vector"), get_engine("obsidian", vault_path="...")]
    combined = MultiEngineRetriever(engines)
    results = combined.retrieve("query")  # Merges all engine results
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.knowledge.engine")


# ═══════════════════════════════════════════════════════════
# Uniform result type
# ═══════════════════════════════════════════════════════════


@dataclass
class RetrievalResult:
    """Uniform result from any retrieval engine.

    Attributes:
        id: Unique identifier within the engine.
        content: The retrieved text content.
        source: Human-readable source (file path, document name, URL).
        score: Relevance score (0-1, higher is better).
        engine: Name of the engine that produced this result.
        metadata: Additional engine-specific metadata.
    """
    id: str
    content: str
    source: str
    score: float = 0.0
    engine: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Abstract engine interface
# ═══════════════════════════════════════════════════════════


class RetrievalEngine(ABC):
    """Abstract base for all retrieval engines.

    Each engine knows how to:
    - Retrieve relevant context for a query
    - Store/index content for later retrieval
    - Report health (connected, configured, etc.)
    - Describe its capabilities

    Engines are self-contained; a KB can use multiple engines.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name (e.g. \"pgvector\", \"lightrag\")."""
        ...

    @property
    @abstractmethod
    def engine_type(self) -> str:
        """Engine type category (\"vector\", \"graph\", \"page_index\", \"obsidian\")."""
        ...

    @abstractmethod
    def retrieve(
        self,
        query: str,
        k: int = 5,
        **kwargs: Any,
    ) -> list[RetrievalResult]:
        """Retrieve the top-k most relevant results for a query.

        Args:
            query: Natural language search query.
            k: Number of results to return.
            **kwargs: Engine-specific parameters.

        Returns:
            List of RetrievalResult, sorted by descending score.
        """
        ...

    def retrieve_context(
        self,
        query: str,
        k: int = 5,
        **kwargs: Any,
    ) -> str:
        """Retrieve and format as a context string for LLM injection.

        Default implementation stitches results with source headers.
        Override for engine-specific formatting.
        """
        results = self.retrieve(query, k=k, **kwargs)
        if not results:
            return ""

        parts: list[str] = []
        for r in results:
            parts.append(f"// [{r.engine}] {r.source}")
            parts.append(r.content[:2000])
            parts.append("")
        return "\n".join(parts)

    def store(self, chunks: list[Any]) -> int:
        """Store/index content chunks for later retrieval.

        Args:
            chunks: Content chunks (engine-specific type).

        Returns:
            Number of chunks stored.
        """
        raise NotImplementedError(
            f"{self.name} engine does not support storing chunks"
        )

    def health(self) -> bool:
        """Check if the engine is ready for use.

        Returns True if configured and reachable.
        """
        return True

    def reset(self) -> None:
        """Clear engine state (for testing)."""
        pass

    def stats(self) -> dict[str, Any]:
        """Return engine statistics."""
        return {"name": self.name, "type": self.engine_type}


# ═══════════════════════════════════════════════════════════
# PgVectorEngine — existing pgvector-backed RAG
# ═══════════════════════════════════════════════════════════


class PgVectorEngine(RetrievalEngine):
    """Adapter for the existing pgvector-based retrieval.

    Wraps the ``KnowledgeRetriever`` and ``DocumentIndexer`` from
    ``rag.py`` behind the ``RetrievalEngine`` interface.

    Supports:
    - Dense search (cosine similarity via pgvector)
    - Sparse search (BM25 via tsvector)
    - Hybrid search (RRF merge of both)

    Args:
        db_url: PostgreSQL connection URL.
            Defaults to ``AIW_DATABASE_URL`` or the local dev default.
    """

    _DEFAULT_DB_URL = os.environ.get(
        "AIW_DATABASE_URL",
        "postgresql://localhost:5439/aiw_rag?host=/tmp/aiw-pg",
    )

    def __init__(self, db_url: str | None = None):
        self._db_url = db_url or self._DEFAULT_DB_URL
        self._retriever: Any = None
        self._healthy = False

    @property
    def name(self) -> str:
        return "pgvector"

    @property
    def engine_type(self) -> str:
        return "vector"

    def _ensure_retriever(self) -> Any:
        """Lazy-import and instantiate the KnowledgeRetriever."""
        if self._retriever is None:
            try:
                from ai_workspace.knowledge.rag import KnowledgeRetriever
                self._retriever = KnowledgeRetriever(db_url=self._db_url)
                self._healthy = True
            except Exception as exc:
                logger.warning("PgVectorEngine init failed: %s", exc)
                self._healthy = False
                raise
        return self._retriever

    def retrieve(
        self,
        query: str,
        k: int = 5,
        **kwargs: Any,
    ) -> list[RetrievalResult]:
        """Retrieve via pgvector hybrid search.

        Kwargs:
            strategy: ``\"hybrid\"``, ``\"dense\"``, or ``\"sparse\"``.
        """
        retriever = self._ensure_retriever()
        strategy = kwargs.get("strategy", "hybrid")

        raw = retriever.retrieve(query, k=k, strategy=strategy)

        return [
            RetrievalResult(
                id=r["id"],
                content=r["content"],
                source=f"{r['source_file']}:{r['start_line']}",
                score=r.get("score", 0.0),
                engine="pgvector",
                metadata={
                    "source_file": r["source_file"],
                    "start_line": r["start_line"],
                    "end_line": r["end_line"],
                },
            )
            for r in raw
        ]

    def store(self, chunks: list[Any]) -> int:
        """Index chunks into pgvector.

        Args:
            chunks: Expects ``list[rag.Chunk]`` objects.
        """
        try:
            from ai_workspace.knowledge.rag import (
                DocumentIndexer,
                setup_schema,
            )
            from ai_workspace.knowledge.rag import Chunk as RagChunk
        except ImportError:
            raise ImportError("pgvector packages not available")

        # Ensure schema exists
        try:
            setup_schema(self._db_url)
        except Exception as exc:
            logger.warning("Schema setup failed (may already exist): %s", exc)

        indexer = DocumentIndexer(db_url=self._db_url)

        # Import and embed
        try:
            embeds = indexer._embed_chunks(chunks)
            indexer._store_chunks(chunks, embeds)
            return len(chunks)
        except Exception as exc:
            logger.error("Failed to store chunks: %s", exc)
            raise

    def health(self) -> bool:
        """Check pgvector connectivity."""
        try:
            self._ensure_retriever()
            # Quick connectivity check
            import psycopg2
            conn = psycopg2.connect(self._db_url)
            conn.close()
            return True
        except Exception:
            return False

    def stats(self) -> dict[str, Any]:
        """Return pgvector engine stats."""
        try:
            import psycopg2
            conn = psycopg2.connect(self._db_url)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM chunks")
            count = cur.fetchone()[0]
            conn.close()
            return {
                "name": self.name,
                "type": self.engine_type,
                "chunk_count": count,
                "db_url": self._db_url,
                "healthy": self._healthy,
            }
        except Exception as exc:
            return {
                "name": self.name,
                "type": self.engine_type,
                "error": str(exc),
                "healthy": False,
            }


# ═══════════════════════════════════════════════════════════
# ObsidianEngine — read-in-place vault reader
# ═══════════════════════════════════════════════════════════

_OBSIDIAN_WIKI_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


class ObsidianEngine(RetrievalEngine):
    """Read-only engine that reads Obsidian vault notes in-place.

    No indexing required — reads markdown files directly from the vault
    directory. Uses basic keyword + filename matching for retrieval
    instead of embeddings.

    Good for: existing Obsidian vaults where you don't want to re-index.
    Not as accurate as vector search for semantic matching.

    Args:
        vault_path: Path to the Obsidian vault directory.
        extensions: File extensions to include (default: ``[\".md\"]``).
        max_file_size: Skip files larger than this (default: 500KB).
    """

    def __init__(
        self,
        vault_path: str | Path,
        extensions: list[str] | None = None,
        max_file_size: int = 500_000,
    ):
        self._vault = Path(vault_path).expanduser().resolve()
        if not self._vault.is_dir():
            raise NotADirectoryError(
                f"Obsidian vault not found: {self._vault}"
            )
        self._extensions = extensions or [".md"]
        self._max_file_size = max_file_size
        self._file_cache: dict[str, Path] = {}
        self._cache_ready = False

    @property
    def name(self) -> str:
        return "obsidian"

    @property
    def engine_type(self) -> str:
        return "page_index"

    def retrieve(
        self,
        query: str,
        k: int = 5,
        **kwargs: Any,
    ) -> list[RetrievalResult]:
        """Retrieve by keyword matching in filenames and content.

        Simple but fast: match query tokens against filenames first,
        then scan content for keyword frequency.

        Kwargs:
            include_paths: Optional list of sub-paths to restrict search.
        """
        self._ensure_cache()
        include_paths = kwargs.get("include_paths")

        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        scored: list[tuple[float, Path]] = []
        for rel_path, abs_path in self._file_cache.items():
            if include_paths:
                if not any(rel_path.startswith(p) for p in include_paths):
                    continue

            filename_score = self._score_filename(
                rel_path, query_lower, query_tokens,
            )
            if filename_score > 0.3:
                scored.append((1.0 + filename_score, abs_path))
                continue

            content_score = self._score_content(abs_path, query_tokens)
            if content_score > 0:
                scored.append((content_score, abs_path))

        # Sort by score descending, take top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:k]

        results: list[RetrievalResult] = []
        for score, path in top:
            try:
                content = path.read_text()
                # Resolve wiki links for display
                content = _OBSIDIAN_WIKI_LINK.sub(r"\1", content)
            except OSError:
                continue

            rel = path.relative_to(self._vault)
            results.append(RetrievalResult(
                id=str(rel),
                content=content[:2000],
                source=str(rel),
                score=min(score, 1.0),
                engine="obsidian",
                metadata={
                    "vault_path": str(self._vault),
                    "full_path": str(path),
                    "size": len(content),
                },
            ))

        return results

    def health(self) -> bool:
        """Check vault directory is accessible."""
        return self._vault.is_dir()

    def stats(self) -> dict[str, Any]:
        """Return vault stats."""
        self._ensure_cache()
        total_size = sum(p.stat().st_size for p in self._file_cache.values())
        return {
            "name": self.name,
            "type": self.engine_type,
            "vault_path": str(self._vault),
            "file_count": len(self._file_cache),
            "total_size_bytes": total_size,
            "healthy": self._vault.is_dir(),
        }

    def reset(self) -> None:
        """Clear file cache."""
        self._file_cache.clear()
        self._cache_ready = False

    # ── Private helpers ──────────────────────────────────

    def _ensure_cache(self) -> None:
        """Build a map of relative → absolute paths for all vault files."""
        if self._cache_ready:
            return

        for ext in self._extensions:
            for path in self._vault.rglob(f"*{ext}"):
                if path.is_file() and path.stat().st_size <= self._max_file_size:
                    rel = path.relative_to(self._vault)
                    self._file_cache[str(rel)] = path

        self._cache_ready = True
        logger.debug(
            "ObsidianEngine: cached %d files from %s",
            len(self._file_cache), self._vault,
        )

    @staticmethod
    def _trigram_overlap(a: str, b: str) -> float:
        """Compute trigram similarity between two strings (0-1).

        Helps match abbreviations like "db" ↔ "database",
        "cfg" ↔ "configuration", etc.
        """
        a_trigrams = {a[i:i+3] for i in range(len(a) - 2)}
        b_trigrams = {b[i:i+3] for i in range(len(b) - 2)}

        if not a_trigrams or not b_trigrams:
            return 0.0

        intersection = a_trigrams & b_trigrams
        return len(intersection) / max(len(a_trigrams), len(b_trigrams))

    @staticmethod
    def _abbreviation_score(short: str, long: str) -> bool:
        """Check if ``short`` is a character subsequence of ``long``.

        This catches abbreviations like "db" in "database" (d...b),
        "cfg" in "configuration" (c...f...g), etc.

        Returns True if all characters of ``short`` appear in order
        in ``long``, regardless of gaps.
        """
        it = iter(long)
        return all(char in it for char in short)

    def _score_filename(
        self,
        rel_path: str,
        query_lower: str,
        query_tokens: set[str],
    ) -> float:
        """Score a filename against the query.

        Returns 0-1 based on token overlap in the filename.
        Checks both directions: query words in filename AND
        filename words in query (e.g. "Auth" matches "authentication").
        """
        path_lower = rel_path.lower()
        # Strip extension and path separators for tokenization
        stem = Path(path_lower).stem
        path_tokens = set(
            path_lower.replace("/", " ").replace("-", " ").replace("_", " ").split()
        )

        if not path_tokens or not query_tokens:
            return 0.0

        # Exact token overlap
        overlap = len(query_tokens & path_tokens)
        if overlap > 0:
            return overlap / len(query_tokens)

        # Substring match: query tokens in filename
        for token in query_tokens:
            if token in path_lower:
                return 0.5

        # Substring match: filename stem in query tokens (len >= 2)
        if stem and len(stem) >= 2:
            for token in query_tokens:
                if stem.lower() in token or token in stem.lower():
                    return 0.4

        # Trigram similarity between stem and each query token
        if stem and len(stem) >= 2:
            for token in query_tokens:
                overlap_score = self._trigram_overlap(stem.lower(), token)
                if overlap_score > 0.2:
                    return 0.3 + overlap_score * 0.2

        # Abbreviation match: short stem in longer query token
        if stem and len(stem) >= 2 and len(stem) < max((len(t) for t in query_tokens), default=0):
            for token in query_tokens:
                if len(token) > len(stem) and self._abbreviation_score(stem, token):
                    return 0.4

        # Stem without extension, check each part
        stem_parts = stem.replace("-", " ").replace("_", " ").split()
        for part in stem_parts:
            if len(part) >= 2:
                for token in query_tokens:
                    if part.lower() in token or token in part.lower():
                        return 0.3

        return 0.0

    def _score_content(self, path: Path, query_tokens: set[str]) -> float:
        """Score file content by keyword frequency.

        Checks both exact token overlap and substring matching.
        """
        try:
            content = path.read_text().lower()
        except OSError:
            return 0.0

        content_tokens = set(content.split())
        if not content_tokens or not query_tokens:
            return 0.0

        # Exact token overlap
        exact_overlap = len(query_tokens & content_tokens)
        if exact_overlap > 0:
            return min(0.9, exact_overlap / len(query_tokens))

        # Substring matching — any query token found in content?
        for token in query_tokens:
            if len(token) > 2 and token in content:
                return 0.6

        # Stem-based matching (len >= 2)
        for qt in query_tokens:
            for ct in content_tokens:
                if len(qt) >= 2 and len(ct) >= 2 and (qt in ct or ct in qt):
                    return 0.5

        # Trigram similarity for abbreviations
        for qt in query_tokens:
            for ct in content_tokens:
                if len(qt) >= 3 and len(ct) >= 3:
                    tri_score = self._trigram_overlap(qt, ct)
                    if tri_score > 0.2:
                        return 0.4

        # Abbreviation match: short token in longer token
        for qt in query_tokens:
            for ct in content_tokens:
                short, long = (qt, ct) if len(qt) <= len(ct) else (ct, qt)
                if len(short) >= 2 and len(long) > len(short):
                    if self._abbreviation_score(short, long):
                        return 0.4

        return 0.0


# ═══════════════════════════════════════════════════════════
# LightRAGEngine — graph-based retrieval adapter
# ═══════════════════════════════════════════════════════════

# LightRAG is optional — install with: pip install lightrag-hku


class LightRAGEngine(RetrievalEngine):
    """Adapter for LightRAG (graph-based knowledge retrieval).

    LightRAG builds a knowledge graph from documents, enabling:
    - Local retrieval (entity/relation focused)
    - Global retrieval (community/topic focused)
    - Hybrid retrieval (combines both)

    This is a best-effort adapter. LightRAG must be installed separately.

    Args:
        working_dir: Directory for LightRAG data (knowledge graph storage).
        embedding_model: Embedding model for LightRAG.
                         Defaults to the engine's built-in default.
        llm_model: LLM model for LightRAG graph operations.
        kv_storage: Storage type for the knowledge graph (default: \"json\").
    """

    def __init__(
        self,
        working_dir: str | Path = "~/.aiw/lightrag",
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "qwen3:14b",
        kv_storage: str = "json",
    ):
        self._working_dir = Path(working_dir).expanduser()
        self._embedding_model = embedding_model
        self._llm_model = llm_model
        self._kv_storage = kv_storage
        self._initialized = False
        self._lightrag: Any = None

    @property
    def name(self) -> str:
        return "lightrag"

    @property
    def engine_type(self) -> str:
        return "graph"

    def _initialize(self) -> bool:
        """Lazy-init LightRAG instance.

        Returns True if LightRAG is available and initialized.
        """
        if self._initialized:
            return True

        try:
            import lightrag
            from lightrag import LightRAG as _LightRAG
            from lightrag.llm import ollama_model_complete
            from lightrag.embed import ollama_embedding
        except ImportError:
            logger.warning(
                "LightRAG not installed. Install: pip install lightrag-hku"
            )
            return False

        try:
            self._working_dir.mkdir(parents=True, exist_ok=True)

            self._lightrag = _LightRAG(
                working_dir=str(self._working_dir),
                embedding_func=ollama_embedding(
                    self._embedding_model,
                    host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                ),
                llm_model_func=ollama_model_complete(
                    self._llm_model,
                    host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                ),
            )
            self._initialized = True
            logger.debug("LightRAGEngine initialized at %s", self._working_dir)
            return True

        except Exception as exc:
            logger.warning("LightRAG init failed: %s", exc)
            return False

    @property
    def engine_type(self) -> str:
        return "graph"

    def retrieve(
        self,
        query: str,
        k: int = 5,
        **kwargs: Any,
    ) -> list[RetrievalResult]:
        """Retrieve via LightRAG knowledge graph.

        Kwargs:
            mode: ``\"local\"``, ``\"global\"``, or ``\"hybrid\"`` (default).

        Returns:
            List of RetrievalResult from graph traversal.
        """
        if not self._initialize():
            return []

        mode = kwargs.get("mode", "hybrid")

        try:
            results = self._lightrag.query(
                query,
                param={"mode": mode, "top_k": k},
            )

            if isinstance(results, str):
                text = results
            elif isinstance(results, list):
                text = "\n".join(str(r) for r in results)
            else:
                text = str(results)

            return [
                RetrievalResult(
                    id=f"{self._working_dir.stem}/q:{query[:40]}",
                    content=text[:2000],
                    source=f"lightrag:{self._working_dir.name}",
                    score=1.0,
                    engine="lightrag",
                    metadata={"mode": mode, "query": query},
                )
            ]

        except Exception as exc:
            logger.warning("LightRAG query failed: %s", exc)
            return []

    def store(self, chunks: list[Any]) -> int:
        """Insert text chunks into LightRAG knowledge graph.

        Args:
            chunks: List of ``RetrievalResult``, ``rag.Chunk``, or plain strings.
        """
        if not self._initialize():
            return 0

        stored = 0
        for chunk in chunks:
            if isinstance(chunk, str):
                text = chunk
            elif hasattr(chunk, "content"):
                text = chunk.content
            else:
                text = str(chunk)

            try:
                self._lightrag.insert(text)
                stored += 1
            except Exception as exc:
                logger.warning("LightRAG insert failed: %s", exc)

        logger.debug("LightRAGEngine: stored %d/%d chunks", stored, len(chunks))
        return stored

    def health(self) -> bool:
        """Check LightRAG is importable and dir is writable."""
        try:
            import lightrag  # noqa: F401
        except ImportError:
            return False

        try:
            self._working_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def stats(self) -> dict[str, Any]:
        """Return LightRAG engine stats."""
        return {
            "name": self.name,
            "type": self.engine_type,
            "working_dir": str(self._working_dir),
            "initialized": self._initialized,
            "healthy": self.health(),
        }


# ═══════════════════════════════════════════════════════════
# MultiEngineRetriever — combine multiple engines
# ═══════════════════════════════════════════════════════════


class MultiEngineRetriever:
    """Combine multiple engines, merge results via RRF.

    Useful when you have both a vector store and a read-in-place vault.
    Queries all engines and merges via Reciprocal Rank Fusion.

    Args:
        engines: List of ``RetrievalEngine`` instances.
    """

    def __init__(self, engines: list[RetrievalEngine]):
        if not engines:
            raise ValueError("At least one engine required")
        self._engines = engines

    @property
    def engines(self) -> list[RetrievalEngine]:
        return list(self._engines)

    def retrieve(
        self,
        query: str,
        k: int = 5,
        **kwargs: Any,
    ) -> list[RetrievalResult]:
        """Query all engines and merge results.

        Each engine retrieves top-k results independently. Results
        are merged via RRF across all engines.

        Args:
            query: Search query.
            k: Final number of results.
            **kwargs: Passed to each engine's retrieve().

        Returns:
            Top-k merged results.
        """
        all_results: list[list[RetrievalResult]] = []

        for engine in self._engines:
            try:
                results = engine.retrieve(query, k=k * 2, **kwargs)
                if results:
                    all_results.append(results)
            except Exception as exc:
                logger.warning(
                    "Engine %s failed: %s", engine.name, exc,
                )

        if not all_results:
            return []

        return self._rrf_merge(all_results)[:k]

    def retrieve_context(
        self,
        query: str,
        k: int = 5,
        **kwargs: Any,
    ) -> str:
        """Retrieve and format as LLM context string."""
        results = self.retrieve(query, k=k, **kwargs)
        if not results:
            return ""

        parts: list[str] = ["=== RELEVANT CONTEXT ===\n"]
        for r in results:
            parts.append(f"// [{r.engine}] {r.source}")
            parts.append(r.content[:2000])
            parts.append("")
        return "\n".join(parts)

    # ── RRF merge ─────────────────────────────────────────

    @staticmethod
    def _rrf_merge(
        ranked_lists: list[list[RetrievalResult]],
        k_rrf: int = 60,
    ) -> list[RetrievalResult]:
        """Reciprocal Rank Fusion across multiple ranked lists."""
        rrf_scores: dict[str, float] = {}
        item_map: dict[str, RetrievalResult] = {}

        for ranked_list in ranked_lists:
            for rank, item in enumerate(ranked_list):
                rrf_scores[item.id] = rrf_scores.get(item.id, 0.0) + 1.0 / (
                    k_rrf + rank + 1
                )
                if item.id not in item_map:
                    item_map[item.id] = item

        merged = []
        for item_id, score in rrf_scores.items():
            item = item_map[item_id]
            item.score = score
            merged.append(item)

        return sorted(merged, key=lambda x: x.score, reverse=True)

    def stats(self) -> list[dict[str, Any]]:
        """Return stats for all engines."""
        return [e.stats() for e in self._engines]

    def health(self) -> dict[str, bool]:
        """Return health for all engines."""
        return {e.name: e.health() for e in self._engines}


# ═══════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════

ENGINE_REGISTRY: dict[str, type[RetrievalEngine]] = {
    "vector": PgVectorEngine,
    "pgvector": PgVectorEngine,
    "obsidian": ObsidianEngine,
    "lightrag": LightRAGEngine,
    "graph": LightRAGEngine,
}


def get_engine(
    engine_type: str,
    **kwargs: Any,
) -> RetrievalEngine:
    """Factory: create a retrieval engine by type.

    Args:
        engine_type: One of ``\"vector\"``, ``\"pgvector\"``,
            ``\"obsidian\"``, ``\"lightrag\"``, ``\"graph\"``.
        **kwargs: Engine-specific init arguments (e.g. ``vault_path``
            for Obsidian, ``db_url`` for pgvector).

    Returns:
        An initialized ``RetrievalEngine`` instance.

    Raises:
        ValueError: If engine type is unknown.
    """
    engine_class = ENGINE_REGISTRY.get(engine_type)
    if engine_class is None:
        raise ValueError(
            f"Unknown engine type: {engine_type!r}. "
            f"Available: {list(ENGINE_REGISTRY.keys())}"
        )
    return engine_class(**kwargs)


def list_engines() -> list[dict[str, str]]:
    """List all available engine types with descriptions.

    Returns:
        List of dicts with keys: type, name, description.
    """
    return [
        {
            "type": "vector",
            "name": "PgVectorEngine",
            "description": "PostgreSQL pgvector — hybrid search with dense + sparse + RRF",
        },
        {
            "type": "obsidian",
            "name": "ObsidianEngine",
            "description": "Read-in-place Obsidian vault — no indexing, keyword-based",
        },
        {
            "type": "lightrag",
            "name": "LightRAGEngine",
            "description": "LightRAG graph-based retrieval — entity/relation graph (optional)",
        },
    ]
