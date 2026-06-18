# Budget Enforcement — Cost Control Layer

> **Data:** 2026-06-16 | **Status:** ✅ Implemented | **Arquivo:** `core/cost.py`
> **Tests:** `tests/test_core/test_cost.py` (40 tests)

---

## 🎯 Problema

Cada chamada de LLM custa dinheiro real. Sem controle, um agente em loop ou uma pesquisa profunda pode gastar
dólares em minutos. O cache semântico reduz ~70% das chamadas, mas não impede estouro nas chamadas que
precisam ir pro LLM.

---

## 🧠 Solução: Três Camadas de Proteção

```
Chamada de LLM iminente
     │
     ▼
┌─────────────────────┐
│ 1. SEMANTIC CACHE   │  ← pgvector HNSW (cosine similarity)
│    Hash lookup O(1)  │     Hit? → retorna cacheada ($0)
│    + vector search   │     Miss? → continua
└─────────┬───────────┘
          │ miss
          ▼
┌─────────────────────┐
│ 2. BUDGET ENFORCER  │  ← Limites por chamada/dia/mês
│    $0.01 / call      │     Excedeu? → BudgetExceededError
│    $1.00 / day       │     OK? → continua
│    $10.00 / month    │
└─────────┬───────────┘
          │ ok
          ▼
┌─────────────────────┐
│ 3. CIRCUIT BREAKER  │  ← Proteção por provedor
│    DeepSeek: 3 falhas│     Circuito aberto? → bloqueia
│    Gemini:   5 falhas│     Fechado? → chama LLM
│    Ollama:   2 falhas│
└─────────┬───────────┘
          │
          ▼
     Chama LLM → registra custo no cost_log
```

---

## 📦 Componentes

### SemanticCache (`core/cost.py`)

Cache semântico com busca vetorial no PostgreSQL + pgvector.

| Feature | Detalhe |
|---------|---------|
| **Embedding primário** | Ollama `nomic-embed-text` (768-dim, GPU, grátis) |
| **Embedding fallback** | `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU) |
| **Lookup rápido** | MD5 hash → O(1) exact match |
| **Lookup semântico** | pgvector HNSW cosine similarity ≥ 0.85 |
| **Índice** | HNSW (m=16, ef_construction=64) — 2x mais rápido que IVFFlat |
| **TTL** | 7 dias (chat), 1 dia (search), 30 dias (factual) |
| **Limpeza** | `aiw cache clear` ou `cleanup_expired(30)` automático |

### BudgetEnforcer

| Limite | Valor | Quando excede |
|--------|-------|---------------|
| Por chamada | $0.01 | Rejeita antes de chamar |
| Diário | $1.00 | Bloqueia chamadas pagas, só cache + Ollama |
| Mensal | $10.00 | Bloqueia tudo |

### CircuitBreaker

Máquina de estados por provedor:

```
closed ──[N falhas]──→ open ──[timeout]──→ half_open ──[sucesso]──→ closed
                           ↑                                    │
                           └──────[falha no probe]──────────────┘
```

| Provedor | Threshold | Timeout |
|----------|-----------|---------|
| DeepSeek | 3 falhas | 60s |
| Gemini | 5 falhas | 30s |
| Ollama | 2 falhas | 120s |

### SmartRouter (`agents/router.py`)

Roteamento inteligente por tipo de tarefa + complexidade:

| Task Type | Modelo preferido | Fallback |
|-----------|-----------------|----------|
| Coding | qwen3:14b (local) | deepseek-chat |
| Research | qwen3:14b (local) | deepseek-chat |
| Chat rápido | ministral-3:8b (local) | qwen3.5:9b |
| Geral | qwen3:14b (local) | deepseek-chat |

Auto-detecção de complexidade: SIMPLE (arquivo único) → MODERATE (multi-arquivo) → COMPLEX (refactor/arquitetura).

---

## 🔗 Integração

| Entry point | Budget check | Cost log |
|-------------|:-----------:|:--------:|
| `cli.py ask` | ✅ Antes da API call | ✅ Success + failure |
| `deep_search.py` `_cached_kickoff` | ✅ BudgetExceededError | ✅ budget.record_success/failure |
| `tui/worker.py` `_execute_with_fallback` | ✅ Antes do agente | ✅ Success + failure |
| `tui/worker.py` `_run_research_agent` | ✅ Via deep_search | ✅ Herdado |

---

## 📊 CLI

```bash
aiw budget
```

```
💰 Budget Status
┌───────────────────────┬──────────────────────────┐
│ Metric                │ Value                    │
├───────────────────────┼──────────────────────────┤
│ 🟢 Today              │ $0.0042 / $1.00 (0.4%)   │
│ 🟢 This month         │ $0.1337 / $10.00 (1.3%)  │
│ 📦 Cache entries      │ 42                       │
│ 📦 Cache hits         │ 128                      │
│ 📦 Tokens saved       │ 50,000                   │
│ 📦 Cost saved         │ $0.75                    │
│ ⚡ Circuits            │                          │
│   🟢 deepseek          │ closed                  │
│   🟢 gemini            │ closed                  │
│   🟢 ollama            │ closed                  │
└───────────────────────┴──────────────────────────┘
```

---

## 📁 Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `src/ai_workspace/core/cost.py` | SemanticCache, CostLog, CircuitBreaker, BudgetEnforcer, CostService |
| `src/ai_workspace/agents/router.py` | SmartRouter com task routing + complexity detection |
| `src/ai_workspace/search/deep_search.py` | `_cached_kickoff()` com budget check |
| `src/ai_workspace/cli.py` | `aiw budget` + `aiw ask` com cache/budget |
| `src/ai_workspace/tui/worker.py` | Budget check no AgentWorker |
| `tests/test_core/test_cost.py` | 40 testes (CircuitBreaker, BudgetEnforcer, SemanticCache) |
