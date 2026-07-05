"""
Retrieval Augmented Generation (RAG) for AI Workspace.

Three components:
  DocumentIndexer  — chunk files, embed with Qwen3-Embedding, store in pgvector.
  KnowledgeRetriever — hybrid search (dense + BM25 + RRF merge + rerank).
  Reranker — cross-encoder reranking (Ollama → sentence-transformers → keyword).

Refs:
- SPEC_RAG.md
- pgvector-python RAG example
- RRF (Reciprocal Rank Fusion) paper
"""

from __future__ import annotations

import ast as _ast
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("aiw.rag")


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

EMBED_MODEL: str = "batiai/qwen3-embedding:8b"
"""Ollama model for embeddings. Must be pulled beforehand."""

EMBED_DIM: int = 1792
"""Output dimension of batiai/qwen3-embedding:8b."""

RERANKER_MODEL: str = "batiai/qwen3-reranker:8b"
"""Ollama model for cross-encoder reranking. Must be pulled beforehand."""

RERANKER_METHOD: str = "auto"
"""Reranker backend: 'auto' (try ollama → cross-encoder → keyword),
'llm' (Ollama /api/rerank), 'cross-encoder' (sentence-transformers),
or 'keyword' (overlap fallback).
"""

DEFAULT_DB_URL: str = os.environ.get(
    "AIW_DATABASE_URL",
    "postgresql://localhost:5439/aiw_rag?host=/tmp/aiw-pg",
)
"""Default PostgreSQL connection URL."""

# Files/dirs to skip during indexing
SKIP_PATTERNS: list[str] = [
    ".git/", "__pycache__/", "node_modules/", ".venv/", "dist/",
    ".png", ".jpg", ".gif", ".woff", ".woff2", ".ttf",
    ".pyc", ".so", ".dylib", ".dll",
]
MAX_FILE_SIZE: int = 1_000_000  # Skip files larger than 1MB


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class Chunk:
    """A document chunk with metadata for retrieval."""
    id: str
    content: str
    source_file: str
    start_line: int = 0
    end_line: int = 0
    language: str = "text"
    chunk_type: str = "paragraph"


# ═══════════════════════════════════════════════════════════
# Reranker
# ═══════════════════════════════════════════════════════════

class Reranker:
    """Cross-encoder reranker with automatic backend selection.

    Pipeline tries in order:
      1. Ollama /api/rerank (GPU — Qwen3-Reranker on remote machine)
      2. sentence-transformers cross-encoder (CPU local)
      3. Keyword overlap (last resort)

    Configure via ``RERANKER_METHOD`` constant or ``method`` kwarg.
    """

    def __init__(
        self,
        method: str = RERANKER_METHOD,
        ollama_model: str = RERANKER_MODEL,
        cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        ollama_host: str | None = None,
    ):
        self.method = method
        self.ollama_model = ollama_model
        self.cross_encoder_model = cross_encoder_model
        self.ollama_host = ollama_host or os.getenv(
            "OLLAMA_HOST", "http://localhost:11434"
        )
        self._pipeline: list[str] = self._resolve_pipeline()
        self._cross_encoder: Any = None
        self._httpx_client: Any = None

    def _resolve_pipeline(self) -> list[str]:
        """Resolve which backends to try, in order."""
        if self.method == "llm":
            return ["ollama"]
        elif self.method == "cross-encoder":
            return ["cross_encoder"]
        elif self.method == "keyword":
            return ["keyword"]
        else:  # auto
            return ["ollama", "cross_encoder", "keyword"]

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Re-rank candidates by relevance to query.

        Args:
            query: The search query.
            candidates: List of result dicts with ``content`` key.

        Returns:
            Same candidates sorted by relevance (descending).
        """
        if not candidates:
            return candidates

        for backend in self._pipeline:
            try:
                if backend == "ollama":
                    return self._rerank_ollama(query, candidates)
                elif backend == "cross_encoder":
                    return self._rerank_cross_encoder(query, candidates)
                elif backend == "keyword":
                    return self._rerank_keyword(query, candidates)
            except ImportError:
                logger.debug(
                    "Reranker backend '%s' not available, trying next", backend
                )
                continue
            except Exception as exc:
                logger.warning(
                    "Reranker backend '%s' failed: %s, trying next",
                    backend, exc,
                )
                continue

        # Ultimate fallback: no-op (keep original RRF order)
        logger.warning("All reranker backends failed — returning original order")
        return candidates

    # ── Backend: Ollama /api/rerank ───────────────────────

    def _rerank_ollama(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Re-rank via Ollama /api/rerank endpoint (Qwen3-Reranker on GPU)."""
        import httpx

        documents = [c.get("content", "") for c in candidates]
        url = f"{self.ollama_host}/api/rerank"

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                url,
                json={
                    "model": self.ollama_model,
                    "query": query,
                    "documents": documents,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            raise RuntimeError("Ollama rerank returned empty results")

        # Map results back to candidates by index
        for entry in results:
            idx = entry.get("index")
            score = entry.get("relevance_score", 0.0)
            if idx is not None and 0 <= idx < len(candidates):
                candidates[idx]["score"] = score

        return sorted(
            candidates, key=lambda x: x.get("score", 0.0), reverse=True
        )

    # ── Backend: sentence-transformers cross-encoder ──────

    def _rerank_cross_encoder(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Re-rank via a local cross-encoder (CPU, small model)."""
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]
            self._cross_encoder = CrossEncoder(
                self.cross_encoder_model,
                device="cpu",
            )

        pairs = [
            [query, c.get("content", "")] for c in candidates
        ]
        scores = self._cross_encoder.predict(pairs)  # type: ignore[union-attr]

        for i, score in enumerate(scores):
            candidates[i]["score"] = float(score)

        return sorted(
            candidates, key=lambda x: x.get("score", 0.0), reverse=True
        )

    # ── Backend: keyword overlap (original fallback) ──────

    @staticmethod
    def _rerank_keyword(
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Score-based reranking with exact keyword match boost."""
        query_terms = set(query.lower().split())
        for candidate in candidates:
            content = candidate.get("content", "")
            content_terms = set(content.lower().split())
            overlap = len(query_terms & content_terms)
            base_score = candidate.get("score", 0.0)
            candidate["score"] = base_score * (1.0 + 0.1 * overlap)

        return sorted(
            candidates, key=lambda x: x.get("score", 0.0), reverse=True
        )


# ═══════════════════════════════════════════════════════════
# SQL Schema
# ═══════════════════════════════════════════════════════════

def setup_schema(db_url: str = DEFAULT_DB_URL) -> None:
    """Create the RAG schema in PostgreSQL.

    Idempotent — safe to call multiple times.

    Args:
        db_url: PostgreSQL connection URL.
    """
    import psycopg2
    from pgvector.psycopg2 import register_vector

    conn = psycopg2.connect(db_url)
    try:
        register_vector(conn)
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source_file TEXT NOT NULL,
                start_line INTEGER DEFAULT 0,
                end_line INTEGER DEFAULT 0,
                language TEXT DEFAULT 'text',
                chunk_type TEXT DEFAULT 'paragraph',
                embedding vector(1792),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Add ts_vector if missing
        cur.execute("""
            ALTER TABLE chunks ADD COLUMN IF NOT EXISTS
                ts_vector tsvector
        """)
        # Indexes (idempotent via IF NOT EXISTS)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_tsvector_idx ON chunks
                USING GIN (ts_vector)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS chunks_source_idx ON chunks
                (source_file)
        """)
        conn.commit()
        logger.info("RAG schema ready")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# Document Indexer
# ═══════════════════════════════════════════════════════════

class DocumentIndexer:
    """Index workspace files into pgvector.

    Usage:
        indexer = DocumentIndexer()
        count = indexer.index_directory(Path("src"))
    """

    def __init__(self, db_url: str = DEFAULT_DB_URL):
        self.db_url = db_url
        self._ollama: Any = None
        self._psycopg2: Any = None
        self._register_vector: Any = None

    def _ensure_imports(self) -> None:
        """Lazy-import heavy dependencies."""
        if self._ollama is None:
            import ollama
            self._ollama = ollama
        if self._psycopg2 is None:
            import psycopg2
            self._psycopg2 = psycopg2
        if self._register_vector is None:
            from pgvector.psycopg2 import register_vector
            self._register_vector = register_vector

    def index_directory(
        self,
        path: Path,
        glob: str = "**/*.{py,md}",
    ) -> int:
        """Index all matching files. Returns count of chunks created."""
        self._ensure_imports()
        files = sorted(
            f for f in path.glob(glob)
            if f.is_file() and not self._should_skip(f)
        )
        total = 0
        for file in files:
            try:
                chunks = self._chunk_file(file)
                if not chunks:
                    continue
                embeddings = self._embed_chunks(chunks)
                self._store_chunks(chunks, embeddings)
                total += len(chunks)
                logger.debug("Indexed %s: %d chunks", file.name, len(chunks))
            except Exception as exc:
                logger.warning("Failed to index %s: %s", file, exc)

        return total

    def _should_skip(self, file: Path) -> bool:
        """Skip binary, large, or generated files."""
        path_str = str(file)
        if any(p in path_str for p in SKIP_PATTERNS):
            return True
        try:
            if file.stat().st_size > MAX_FILE_SIZE:
                return True
        except OSError:
            return True
        return False

    # ── Chunking ─────────────────────────────────────────

    def _chunk_file(self, file: Path) -> list[Chunk]:
        """Dispatch to appropriate chunker based on file extension."""
        content = file.read_text()
        source = str(file)

        if file.suffix == ".py":
            return self._chunk_python(content, source)
        elif file.suffix in (".md", ".mdx"):
            return self._chunk_markdown(content, source)
        else:
            return self._chunk_generic(content, source)

    def _chunk_python(self, content: str, source: str) -> list[Chunk]:
        """Split Python source on function and class definitions (AST).

        Returns chunks for each top-level and nested function/class.
        Falls back to fixed-size chunking for files without def/class.
        """
        chunks: list[Chunk] = []

        # Only process top-level nodes to avoid excessive nesting
        try:
            tree = _ast.parse(content)
            for node in _ast.iter_child_nodes(tree):
                if isinstance(
                    node,
                    (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef),
                ):
                    chunk_text = _ast.get_source_segment(content, node)
                    if chunk_text and len(chunk_text.strip()) > 50:
                        chunks.append(Chunk(
                            id=f"{source}:L{node.lineno}",
                            content=chunk_text,
                            source_file=source,
                            start_line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                            language="python",
                            chunk_type=type(node).__name__,
                        ))
        except SyntaxError:
            pass  # Fall through to fallback chunker

        # Fallback: fixed-size chunks if AST parsing found nothing
        if not chunks:
            chunks = self._chunk_generic(content, source, language="python")

        return chunks

    def _chunk_markdown(self, content: str, source: str) -> list[Chunk]:
        """Split Markdown on headings (## and #).

        Each heading section becomes a chunk. Skip empty/tiny sections.
        """
        # Split on headings (## or #) keeping the delimiter
        sections = re.split(r"(?=^#{1,3}\s)", content, flags=re.MULTILINE)
        chunks: list[Chunk] = []
        line = 1
        for section in sections:
            section_lines = section.count("\n") + 1
            if len(section.strip()) < 50:
                line += section_lines
                continue
            chunks.append(Chunk(
                id=f"{source}:L{line}",
                content=section.strip(),
                source_file=source,
                start_line=line,
                end_line=line + section_lines,
                language="markdown",
                chunk_type="heading",
            ))
            line += section_lines
        return chunks

    def _chunk_generic(
        self,
        content: str,
        source: str,
        size: int = 500,
        overlap: int = 50,
        language: str = "text",
    ) -> list[Chunk]:
        """Fixed-size overlapping token chunks for unknown formats.

        Uses simple tokenization (split on whitespace) as a fallback
        when tiktoken is not available.
        """
        # Simple tokenization: approximate tokens by whitespace
        words = content.split()
        if not words:
            return []

        chunks: list[Chunk] = []
        i = 0
        while i < len(words):
            chunk_words = words[i:i + size]
            chunk_text = " ".join(chunk_words)
            # Approximate line number
            prefix_text = " ".join(words[:i])
            start_line = prefix_text.count("\n") + 1 if prefix_text else 1
            end_line = start_line + chunk_text.count("\n")

            chunks.append(Chunk(
                id=f"{source}:tok{i}",
                content=chunk_text,
                source_file=source,
                start_line=start_line,
                end_line=end_line,
                language=language,
                chunk_type="paragraph",
            ))
            i += max(1, size - overlap)

        return chunks

    # ── Embedding ─────────────────────────────────────────

    def _embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed chunks using Ollama Qwen3-Embedding.

        Uses the recommended 'search_document' prefix for better quality.
        Batches embeddings in groups of 20 to avoid timeouts.
        """
        self._ensure_imports()
        texts = [f"search_document: {c.content}" for c in chunks]
        embeddings: list[list[float]] = []
        batch_size = 20

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            resp = self._ollama.embed(
                model=EMBED_MODEL,
                input=batch,
            )
            embeddings.extend(resp.get("embeddings", []))

        return embeddings

    # ── Storage ───────────────────────────────────────────

    def _store_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Store chunks and their embeddings in pgvector.

        Uses ON CONFLICT (id) to handle re-indexing of the same file.
        """
        self._ensure_imports()
        conn = self._psycopg2.connect(self.db_url)
        try:
            self._register_vector(conn)
            cur = conn.cursor()
            for chunk, emb in zip(chunks, embeddings):
                emb_array = np.array(emb, dtype=np.float32)
                cur.execute(
                    """
                    INSERT INTO chunks (
                        id, content, source_file, start_line, end_line,
                        language, chunk_type, embedding, ts_vector
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, to_tsvector('english', %s)
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        ts_vector = to_tsvector('english', EXCLUDED.content),
                        updated_at = NOW()
                    """,
                    (
                        chunk.id, chunk.content, chunk.source_file,
                        chunk.start_line, chunk.end_line,
                        chunk.language, chunk.chunk_type,
                        emb_array, chunk.content,
                    ),
                )
            conn.commit()
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════
# Knowledge Retriever
# ═══════════════════════════════════════════════════════════

class KnowledgeRetriever:
    """Hybrid search: dense (vector) + sparse (BM25/tsvector) + RRF merge.

    Usage:
        retriever = KnowledgeRetriever()
        results = retriever.retrieve("auth middleware", k=5)
        context = retriever.retrieve_context("auth middleware")
    """

    def __init__(self, db_url: str = DEFAULT_DB_URL):
        self.db_url = db_url
        self._ollama: Any = None
        self._psycopg2: Any = None
        self._register_vector: Any = None
        self._reranker: Reranker | None = None

    def _ensure_imports(self) -> None:
        """Lazy-import heavy dependencies."""
        if self._ollama is None:
            import ollama
            self._ollama = ollama
        if self._psycopg2 is None:
            import psycopg2
            self._psycopg2 = psycopg2
        if self._register_vector is None:
            from pgvector.psycopg2 import register_vector
            self._register_vector = register_vector
        if self._reranker is None:
            self._reranker = Reranker()

    def retrieve(
        self,
        query: str,
        k: int = 5,
        strategy: str = "hybrid",
    ) -> list[dict[str, Any]]:
        """Retrieve the most relevant chunks for a query.

        Pipeline:
          1. Dense search (pgvector cosine distance) → top-50
          2. Sparse search (BM25 via tsvector) → top-50
          3. RRF merge → top-20
          4. Score-based rerank → top-k

        Args:
            query: Natural language query.
            k: Number of results to return.
            strategy: 'hybrid' (default), 'dense' (vector only),
                      or 'sparse' (BM25 only).

        Returns:
            List of dicts with keys: id, content, source_file,
            start_line, end_line, score.
        """
        self._ensure_imports()

        if strategy == "dense":
            return self._dense_search(query, k)
        elif strategy == "sparse":
            return self._sparse_search(query, k)
        else:
            # Hybrid: merge dense + sparse via RRF
            dense = self._dense_search(query, 50)
            sparse = self._sparse_search(query, 50)
            merged = self._rrf_merge(dense, sparse, k_rrf=60)[:20]
            return self._rerank(query, merged)[:k]

    # ── Dense search (vector) ─────────────────────────────

    def _dense_search(
        self,
        query: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Vector similarity search via pgvector."""
        q_emb = self._embed_query(query)

        conn = self._psycopg2.connect(self.db_url)
        try:
            self._register_vector(conn)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, content, source_file, start_line, end_line,
                       1 - (embedding <=> %s) AS score
                FROM chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (q_emb, q_emb, limit),
            )
            return [
                {
                    "id": r[0],
                    "content": r[1],
                    "source_file": r[2],
                    "start_line": r[3],
                    "end_line": r[4],
                    "score": float(r[5]),
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    # ── Sparse search (BM25 via tsvector) ─────────────────

    def _sparse_search(
        self,
        query: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Full-text search via PostgreSQL tsvector."""
        conn = self._psycopg2.connect(self.db_url)
        try:
            self._register_vector(conn)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, content, source_file, start_line, end_line,
                       ts_rank(ts_vector, plainto_tsquery('english', %s)) AS score
                FROM chunks
                WHERE ts_vector @@ plainto_tsquery('english', %s)
                ORDER BY score DESC
                LIMIT %s
                """,
                (query, query, limit),
            )
            return [
                {
                    "id": r[0],
                    "content": r[1],
                    "source_file": r[2],
                    "start_line": r[3],
                    "end_line": r[4],
                    "score": float(r[5]) if r[5] else 0.0,
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    # ── RRF Merge ─────────────────────────────────────────

    @staticmethod
    def _rrf_merge(
        list_a: list[dict[str, Any]],
        list_b: list[dict[str, Any]],
        k_rrf: int = 60,
    ) -> list[dict[str, Any]]:
        """Reciprocal Rank Fusion — combines two ranked lists.

        Formula: score(id) = sum(1 / (k + rank_i + 1)) for each list i.

        Args:
            list_a: First ranked result list.
            list_b: Second ranked result list.
            k_rrf: Smoothing constant (default 60, per paper).

        Returns:
            Merged list sorted by descending RRF score.
        """
        rrf_scores: dict[str, float] = {}
        item_map: dict[str, dict[str, Any]] = {}

        for rank, item in enumerate(list_a):
            item_id = item["id"]
            rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + 1.0 / (
                k_rrf + rank + 1
            )
            if item_id not in item_map:
                item_map[item_id] = item

        for rank, item in enumerate(list_b):
            item_id = item["id"]
            rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + 1.0 / (
                k_rrf + rank + 1
            )
            if item_id not in item_map:
                item_map[item_id] = item

        # Merge RRF score into items
        merged = []
        for item_id, score in rrf_scores.items():
            item = dict(item_map[item_id])
            item["score"] = score
            merged.append(item)

        return sorted(merged, key=lambda x: x["score"], reverse=True)

    # ── Rerank ────────────────────────────────────────────

    def _rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Re-rank candidates using cross-encoder via Reranker class.

        Pipeline: tries Ollama /api/rerank (GPU) → sentence-transformers
        (CPU) → keyword overlap (last resort).

        Args:
            query: Original search query.
            candidates: Candidate items with 'score' and 'content' keys.

        Returns:
            Re-ranked list sorted by relevance (descending).
        """
        self._ensure_imports()
        assert self._reranker is not None
        return self._reranker.rerank(query, candidates)

    # ── Utilities ─────────────────────────────────────────

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed a search query using Qwen3-Embedding.

        Uses the 'search_query' prefix (different from 'search_document'
        used during indexing) for asymmetric embedding quality.
        """
        self._ensure_imports()
        resp = self._ollama.embed(
            model=EMBED_MODEL,
            input=f"search_query: {query}",
        )
        embeddings = resp.get("embeddings", [])
        if not embeddings:
            raise RuntimeError(
                "Ollama embedding returned empty. "
                f"Check that '{EMBED_MODEL}' is pulled: ollama pull {EMBED_MODEL}"
            )
        return np.array(embeddings[0], dtype=np.float32)

    def retrieve_context(
        self,
        query: str,
        k: int = 5,
    ) -> str:
        """Retrieve and format results as context string for LLM injection.

        Args:
            query: Search query.
            k: Number of results.

        Returns:
            Formatted context string, or empty string if no results.
        """
        results = self.retrieve(query, k=k)
        if not results:
            return ""

        parts = ["=== RELEVANT CONTEXT FROM WORKSPACE ===\n"]
        for r in results:
            source_ref = (
                f"{r['source_file']}"
                f"{':' + str(r['start_line']) if r.get('start_line') else ''}"
            )
            parts.append(f"// {source_ref}")
            parts.append(r["content"][:2000])
            parts.append("")  # blank line between chunks

        return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
# Convenience functions
# ═══════════════════════════════════════════════════════════

def index_workspace(
    path: Path | str | None = None,
    *,
    db_url: str = DEFAULT_DB_URL,
    glob: str = "**/*.{py,md}",
) -> int:
    """Index a directory into the RAG knowledge base.

    Args:
        path: Directory to index (default: current working directory).
        db_url: PostgreSQL connection URL.
        glob: File glob pattern.

    Returns:
        Number of chunks created.
    """
    if path is None:
        path = Path.cwd()
    elif isinstance(path, str):
        path = Path(path)

    setup_schema(db_url)
    indexer = DocumentIndexer(db_url=db_url)
    return indexer.index_directory(path, glob=glob)


def search_knowledge(
    query: str,
    *,
    k: int = 5,
    strategy: str = "hybrid",
    db_url: str = DEFAULT_DB_URL,
) -> list[dict[str, Any]]:
    """Search the RAG knowledge base.

    Args:
        query: Natural language query.
        k: Number of results.
        strategy: 'hybrid', 'dense', or 'sparse'.
        db_url: PostgreSQL connection URL.

    Returns:
        List of result dicts.
    """
    retriever = KnowledgeRetriever(db_url=db_url)
    return retriever.retrieve(query, k=k, strategy=strategy)


def retrieve_context(
    query: str,
    *,
    k: int = 5,
    db_url: str = DEFAULT_DB_URL,
) -> str:
    """Retrieve formatted context for LLM prompt injection.

    Args:
        query: Search query.
        k: Number of results.
        db_url: PostgreSQL connection URL.

    Returns:
        Formatted context string.
    """
    retriever = KnowledgeRetriever(db_url=db_url)
    return retriever.retrieve_context(query, k=k)
