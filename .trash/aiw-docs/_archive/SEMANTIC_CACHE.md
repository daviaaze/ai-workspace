# Semantic Cache — pgvector HNSW + Dual Embedding

> **Data:** 2026-06-17 | **Status:** ✅ Implemented | **Arquivos:** `core/cost.py` (SemanticCache), `search/deep_search.py` (_cached_kickoff)

---

## 🎯 Problema

Cada chamada de LLM custa dinheiro (DeepSeek ~$0.00014/1K tokens) e tempo (latência de rede). Muitas perguntas são repetidas ou similares — pagar por elas de novo é desperdício.

---

## 🧠 Solução: Cache Semântico com pgvector HNSW

```
Usuário pergunta X
     │
     ▼
┌─────────────────────────┐
│ 1. Hash lookup (MD5)    │  O(1) — gratis
│    Exata? → retorna     │
└───────────┬─────────────┘
            │ miss
            ▼
┌─────────────────────────┐
│ 2. Embedding            │
│    Ollama nomic-embed   │  (768-dim, GPU)
│    ↓ fallback           │
│    sentence-transformers│  (384-dim → pad 768)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. pgvector HNSW search │  Cosine similarity
│    ≥ 0.95 → hit exato   │  (retorna sem questionar)
│    0.85-0.94 → similar  │  (retorna com aviso)
│    < 0.85 → miss        │  (chama LLM)
└───────────┬─────────────┘
            │ miss
            ▼
┌─────────────────────────┐
│ 4. Chama LLM            │  Via SmartRouter
│    (orçamento ok?)      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 5. Salva no cache       │  Proxima vez: hit
└─────────────────────────┘
```

---

## 📦 Componentes

### Embedding Backends (auto-detecção)

| Backend | Dim | Velocidade | Quando usar |
|---------|-----|-----------|-------------|
| Ollama `nomic-embed-text` | 768 | GPU, ~10ms | Primário — se Ollama estiver rodando |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | CPU, ~50ms | Fallback automático — padding 384→768 |

### Thresholds de Similaridade

| Range | Comportamento | Exemplo |
|-------|--------------|---------|
| ≥ 0.95 | **Hit exato** — retorna sem questionar | Mesma pergunta, mesmo contexto |
| 0.85 – 0.94 | **Hit similar** — retorna com aviso | Pergunta re-fraseada |
| 0.70 – 0.84 | **Hit parcial** — contexto adicional | Ideia similar, contexto diferente |
| < 0.70 | **Miss** — chama LLM | Pergunta nova |

### TTL (Time-To-Live)

| Tipo | Validade | Motivo |
|------|----------|--------|
| Chat | 7 dias | Conversas são efêmeras |
| Search | 1 dia | Resultados de pesquisa mudam |
| Factual | 30 dias | Conhecimento estável |

---

## 🗄️ Schema

```sql
CREATE TABLE semantic_cache (
    id              SERIAL PRIMARY KEY,
    query_hash      TEXT UNIQUE NOT NULL,       -- MD5 (O(1) exact lookup)
    query_text      TEXT NOT NULL,
    embedding       vector(768) NOT NULL,       -- HNSW index
    response_text   TEXT NOT NULL,
    response_type   TEXT NOT NULL DEFAULT 'chat',
    tokens_saved    INT DEFAULT 0,
    cost_saved      REAL DEFAULT 0.0,
    model_used      TEXT,
    similarity      REAL DEFAULT 1.0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_hit        TIMESTAMPTZ DEFAULT NOW(),
    hit_count       INT DEFAULT 1
);

-- HNSW index (2x faster than IVFFlat)
CREATE INDEX idx_semantic_cache_embedding
ON semantic_cache
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 💰 Economia Estimada

Cenário: 30 pesquisas/dia (~150 chamadas LLM)

| Sem cache | Com cache (60% hit) |
|-----------|-------------------|
| ~$0.54/dia | ~$0.22/dia |
| ~$16/mês | ~$6.50/mês |
| 150 chamadas/dia | ~60 chamadas/dia |

---

## 🔗 Integrações

- **DeepSearch**: `_cached_kickoff()` — cache check antes de cada chamada
- **BudgetEnforcer**: `record_success(cache_hit=True)` — custo $0 registrado
- **CLI**: `aiw cache clear` — limpeza manual, `aiw health` — stats
