# Spec: RAG — Retrieval Augmented Generation

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** pgvector-python, Ollama nomic-embed-text, RRF paper, production RAG patterns

---

## 🎯 Motivação

O aiw tem `pgvector` e `psycopg2` instalados mas **zero código de RAG** no agent loop. O agente não recupera documentos do workspace. Pesquisas de produção (Cursor, Copilot) mostram que injeção de contexto do codebase é essencial para qualidade de respostas.

---

## 📐 Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                     INDEXING PIPELINE                            │
│                                                                  │
│  Arquivos (.py, .md, .json, .yaml)                              │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐                  │
│  │ Chunker  │───▶│ Embedder  │───▶│ pgvector │                  │
│  │ (semant) │    │ (nomic)   │    │  store   │                  │
│  └──────────┘    └───────────┘    └──────────┘                  │
│                                                                  │
│  Chunk strategies:                                               │
│    Python: split on def/class (AST)                              │
│    Markdown: split on ## headings                                │
│    Generic: 500 tokens, 10% overlap                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL PIPELINE                            │
│                                                                  │
│  Query: "como funciona o middleware de auth?"                    │
│       │                                                          │
│       ├──▶ Embed query (nomic-embed-text)                       │
│       │         │                                                │
│       │         ▼                                                │
│       │    ┌─────────────┐                                       │
│       │    │ Dense Search│  pgvector <=> cosine distance        │
│       │    │ top-50      │                                       │
│       │    └─────────────┘                                       │
│       │         │                                                │
│       ├──▶ ┌─────────────┐                                       │
│       │    │ BM25 Search │  PostgreSQL tsvector + ts_rank       │
│       │    │ top-50      │                                       │
│       │    └─────────────┘                                       │
│       │         │                                                │
│       ▼         ▼                                                │
│  ┌──────────────────────┐                                        │
│  │ RRF Merge (k=60)     │  Reciprocal Rank Fusion               │
│  │ top-20 candidates    │                                        │
│  └──────────────────────┘                                        │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────┐                                        │
│  │ Cross-Encoder Rerank │  ms-marco-MiniLM-L-6-v2 (opcional)    │
│  │ top-5 final          │  Fallback: score-based reorder        │
│  └──────────────────────┘                                        │
│       │                                                          │
│       ▼                                                          │
│  Context string → injected into LLM prompt                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementação

### Indexing

```python
# src/ai_workspace/knowledge/rag.py

import ollama
import psycopg
import numpy as np
from pathlib import Path
from dataclasses import dataclass

EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768  # nomic-embed-text output dimension

@dataclass
class Chunk:
    id: str
    content: str
    source_file: str
    start_line: int
    end_line: int
    language: str
    chunk_type: str  # "function", "class", "heading", "paragraph"

class DocumentIndexer:
    """Index workspace files into pgvector."""
    
    def __init__(self, db_url: str = "postgresql:///ai_workspace"):
        self.db_url = db_url
    
    def index_directory(self, path: Path, glob: str = "**/*.{py,md,json,yaml,toml}") -> int:
        """Index all matching files. Returns count of chunks created."""
        import glob as _glob
        files = list(path.glob(glob))
        count = 0
        
        for file in files:
            if self._should_skip(file):
                continue
            try:
                chunks = self._chunk_file(file)
                embeddings = self._embed_chunks(chunks)
                self._store_chunks(chunks, embeddings)
                count += len(chunks)
            except Exception as e:
                logger.warning("Failed to index %s: %s", file, e)
        
        return count
    
    def _chunk_file(self, file: Path) -> list[Chunk]:
        """Semantic chunking based on file type."""
        content = file.read_text()
        ext = file.suffix
        
        if ext == ".py":
            return self._chunk_python(content, str(file))
        elif ext == ".md":
            return self._chunk_markdown(content, str(file))
        else:
            return self._chunk_generic(content, str(file))
    
    def _chunk_python(self, content: str, source: str) -> list[Chunk]:
        """Split Python on function and class definitions."""
        import ast
        tree = ast.parse(content)
        chunks = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                chunk_text = ast.get_source_segment(content, node)
                if chunk_text and len(chunk_text) > 50:
                    chunks.append(Chunk(
                        id=f"{source}:{node.lineno}",
                        content=chunk_text,
                        source_file=source,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        language="python",
                        chunk_type=type(node).__name__,
                    ))
        return chunks
    
    def _chunk_markdown(self, content: str, source: str) -> list[Chunk]:
        """Split Markdown on ## headings."""
        import re
        sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)
        chunks = []
        line = 1
        for section in sections:
            if len(section.strip()) < 50:
                line += section.count('\n')
                continue
            chunks.append(Chunk(
                id=f"{source}:L{line}",
                content=section.strip(),
                source_file=source,
                start_line=line,
                end_line=line + section.count('\n'),
                language="markdown",
                chunk_type="heading",
            ))
            line += section.count('\n')
        return chunks
    
    def _chunk_generic(self, content: str, source: str, size: int = 500, overlap: int = 50) -> list[Chunk]:
        """Fixed-size overlapping chunks for unknown formats."""
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(content)
        chunks = []
        i = 0
        while i < len(tokens):
            chunk_tokens = tokens[i:i + size]
            chunk_text = enc.decode(chunk_tokens)
            text_start = content.find(chunk_text[:50])
            chunks.append(Chunk(
                id=f"{source}:token{i}",
                content=chunk_text,
                source_file=source,
                start_line=content[:text_start].count('\n') + 1 if text_start >= 0 else 0,
                end_line=0,
                language="text",
                chunk_type="paragraph",
            ))
            i += size - overlap
        return chunks
    
    def _embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed chunks using Ollama nomic-embed-text."""
        texts = [f"search_document: {c.content}" for c in chunks]
        embeddings = []
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            resp = ollama.embed(model=EMBED_MODEL, input=batch)
            embeddings.extend(resp.embeddings)
        return embeddings
    
    def _store_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]):
        """Store chunks and embeddings in pgvector."""
        with psycopg.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                for chunk, emb in zip(chunks, embeddings):
                    cur.execute(
                        """INSERT INTO chunks (id, content, source_file, start_line, end_line, language, chunk_type, embedding, ts_vector)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, to_tsvector('english', %s))
                           ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding""",
                        (chunk.id, chunk.content, chunk.source_file, chunk.start_line,
                         chunk.end_line, chunk.language, chunk.chunk_type,
                         np.array(emb, dtype=np.float32), chunk.content)
                    )
            conn.commit()
    
    def _should_skip(self, file: Path) -> bool:
        """Skip binary, large, or generated files."""
        skip_patterns = ['.git/', '__pycache__/', 'node_modules/', '.venv/', 'dist/', '.png', '.jpg', '.gif', '.woff']
        return any(p in str(file) for p in skip_patterns) or file.stat().st_size > 1_000_000
```

### Retrieval

```python
class KnowledgeRetriever:
    """Hybrid search: dense + sparse + rerank."""
    
    def __init__(self, db_url: str = "postgresql:///ai_workspace"):
        self.db_url = db_url
    
    async def retrieve(self, query: str, k: int = 5, strategy: str = "hybrid") -> list[dict]:
        """
        Hybrid retrieval pipeline:
        1. Embed query → dense vector search (top-50)
        2. BM25 keyword search (top-50)
        3. RRF merge → top-20
        4. Cross-encoder rerank → top-k
        """
        # 1. Dense search
        q_emb = ollama.embed(model=EMBED_MODEL, input=f"search_query: {query}").embeddings[0]
        
        with psycopg.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                # Dense (vector similarity)
                cur.execute(
                    """SELECT id, content, source_file, 1 - (embedding <=> %s) AS score
                       FROM chunks ORDER BY embedding <=> %s LIMIT 50""",
                    (np.array(q_emb, dtype=np.float32), np.array(q_emb, dtype=np.float32))
                )
                dense_results = [{"id": r[0], "content": r[1], "source": r[2], "score": r[3]} for r in cur.fetchall()]
                
                # Sparse (BM25 via tsvector)
                cur.execute(
                    """SELECT id, content, source_file, ts_rank(ts_vector, plainto_tsquery('english', %s)) AS score
                       FROM chunks WHERE ts_vector @@ plainto_tsquery('english', %s)
                       ORDER BY score DESC LIMIT 50""",
                    (query, query)
                )
                sparse_results = [{"id": r[0], "content": r[1], "source": r[2], "score": r[3]} for r in cur.fetchall()]
        
        # 2. RRF merge
        merged = self._rrf_merge(dense_results, sparse_results, k=60)[:20]
        
        # 3. Rerank (cross-encoder fallback: simple score-based)
        final = self._rerank(query, merged)[:k]
        
        return final
    
    def _rrf_merge(self, list_a: list, list_b: list, k: int = 60) -> list:
        """Reciprocal Rank Fusion."""
        scores = {}
        for rank, item in enumerate(list_a):
            id_ = item["id"]
            scores[id_] = scores.get(id_, 0) + 1.0 / (k + rank + 1)
            if id_ not in {i["id"] for i in scores if i != id_}:
                scores[id_] = {"item": item, "score": scores[id_]}
        
        for rank, item in enumerate(list_b):
            id_ = item["id"]
            current = scores.get(id_, 0)
            if isinstance(current, dict):
                current["score"] = current["score"] + 1.0 / (k + rank + 1)
            else:
                scores[id_] = {"item": item, "score": current + 1.0 / (k + rank + 1)}
        
        sorted_items = sorted(
            [v for v in scores.values() if isinstance(v, dict)],
            key=lambda x: x["score"], reverse=True
        )
        return [s["item"] for s in sorted_items]
    
    def _rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """Simple score-based rerank. Production would use cross-encoder."""
        # Boost exact keyword matches
        query_terms = set(query.lower().split())
        for c in candidates:
            content_terms = set(c["content"].lower().split())
            overlap = len(query_terms & content_terms)
            c["score"] = c.get("score", 0) * (1 + 0.1 * overlap)
        return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
    
    async def retrieve_context(self, query: str, k: int = 5) -> str:
        """Retrieve and format as context string for LLM injection."""
        results = await self.retrieve(query, k=k)
        if not results:
            return ""
        
        parts = ["=== RELEVANT CONTEXT FROM WORKSPACE ===\n"]
        for r in results:
            parts.append(f"// {r['source']}\n{r['content'][:2000]}\n")
        return "\n".join(parts)
```

### Agent Tool

```python
# Registrado como tool no AgentLoop:
class RetrieveKnowledgeTool:
    name = "retrieve_knowledge"
    description = (
        "Search the workspace knowledge base for relevant code, docs, and context. "
        "Use this BEFORE answering technical questions about the codebase. "
        "Returns the most relevant chunks with source file references."
    )
    
    async def run(self, query: str) -> str:
        """Agent calls this when it needs workspace context."""
        retriever = KnowledgeRetriever()
        return await retriever.retrieve_context(query)
```

### CLI

```bash
# Index current directory
aiw kb index                          # indexa **/*.{py,md,json,yaml}
aiw kb index --path src/              # indexa subdiretório específico
aiw kb index --glob "**/*.rs"         # indexa arquivos Rust

# Search
aiw kb search "auth middleware"       # busca híbrida
aiw kb search "auth" --k 10           # top-10 resultados
aiw kb search "auth" --strategy dense # só vetorial

# Stats
aiw kb stats                          # chunks, files, disk usage
```

### Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy search

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source_file TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    language TEXT DEFAULT 'text',
    chunk_type TEXT DEFAULT 'paragraph',
    embedding vector(768),
    ts_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast ANN search
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks 
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- GIN index for BM25-style full text search
CREATE INDEX IF NOT EXISTS chunks_tsvector_idx ON chunks USING GIN (ts_vector);

-- Index for source file lookup
CREATE INDEX IF NOT EXISTS chunks_source_idx ON chunks (source_file);
```

---

## 📊 Custo

Todo o pipeline é **custo zero** com Ollama local:

| Etapa | Modelo | Custo |
|-------|--------|-------|
| Embedding (index) | ollama/nomic-embed-text | $0 |
| Embedding (query) | ollama/nomic-embed-text | $0 |
| BM25 (pgvector) | PostgreSQL built-in | $0 |
| Rerank (score-based) | Python CPU | $0 |
| Storage | PostgreSQL local | $0 |

---

## 🔗 Integração

- **Agent Loop**: `RetrieveKnowledgeTool` registrada como tool padrão
- **TUI**: `aiw kb index` no startup (background) + `aiw kb search` via `/kb` command
- **MCP**: `retrieve_knowledge` exposta como MCP tool

---

## ✅ Critérios de aceitação

- [ ] `aiw kb index` indexa workspace e popula pgvector
- [ ] `aiw kb search "query"` retorna chunks relevantes
- [ ] Hybrid search (dense + BM25) funciona
- [ ] RRF merge combina resultados corretamente
- [ ] `RetrieveKnowledgeTool` registrada no AgentLoop
- [ ] Agente usa `retrieve_knowledge` antes de responder perguntas técnicas
- [ ] Schema SQL cria tabelas e índices corretamente
- [ ] Ollama `nomic-embed-text` disponível (ou fallback claro)
- [ ] Testes com documentos de exemplo

---

## 📚 Referências

- [pgvector-python RAG example](https://github.com/pgvector/pgvector-python/blob/master/examples/rag/example.py) — código oficial
- [Ollama embeddings docs](https://docs.langchain.com/oss/python/integrations/embeddings/ollama) — API reference
- [Production RAG with FastAPI + pgvector](https://dev.to/martin_palopoli/how-i-built-a-production-rag-pipeline-with-fastapi-pgvector-and-cross-encoder-reranking-j2o) — implementação real
- [ESousa97/py-rag-engine](https://github.com/ESousa97/py-rag-engine) — hybrid search RRF implementation
