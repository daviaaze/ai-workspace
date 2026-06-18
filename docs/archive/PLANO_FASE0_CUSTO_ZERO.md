# Fase 0 — Custo Zero: Cache Semântico + Smart Router + Budget

**Data:** 2026-06-16 | **Plano macro:** `PLANO_ARQUITETURA.md`
**Provedor principal:** DeepSeek (~$0.014/M tokens) · **Fallback:** Gemini Free (60 req/min)
**Objetivo:** Reduzir chamadas de API em ~70% e garantir gasto previsível

---

## 1. Cache Semântico

### 1.1 Funcionamento

Antes de chamar qualquer LLM, verifica se uma pergunta similar já foi respondida:

```
Usuário pergunta X
  → embedding de X (modelo local, sem custo)
  → busca no PostgreSQL por perguntas similares (cosine similarity > 0.92)
  → se achar: retorna resposta cacheada (ZERO custo)
  → se não achar: chama LLM, salva resposta no cache
```

### 1.2 Modelo de Embedding

| Requisito | Escolha | Por quê |
|-----------|---------|---------|
| Deve rodar localmente sem GPU | ✅ `sentence-transformers/all-MiniLM-L6-v2` | 80MB, roda em CPU, qualidade boa |
| Tamanho do vetor | 384 dimensões | Compatível com pgvector |
| Latência | ~50ms por query | Aceitável para cache lookup |

Alternativa mais leve: `all-MiniLM-L6-v2` (ONNX) — mesma qualidade, pode rodar via `optimum` se precisar.

### 1.3 Storage (PostgreSQL + pgvector)

```sql
-- Tabela de cache semântico
CREATE TABLE semantic_cache (
    id SERIAL PRIMARY KEY,
    query_hash TEXT UNIQUE NOT NULL,          -- MD5 da query original (lookup rápido)
    query_text TEXT NOT NULL,                 -- Query original
    embedding vector(384) NOT NULL,           -- Embedding pra busca por相似idade
    response_text TEXT NOT NULL,              -- Resposta cacheada
    response_type TEXT NOT NULL DEFAULT 'chat', -- 'chat', 'search', 'research'
    tokens_saved INT DEFAULT 0,              -- Tokens que deixaram de ser gastos
    cost_saved REAL DEFAULT 0.0,             -- Custo economizado em USD
    model_used TEXT,                          -- Modelo que gerou a resposta
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_hit TIMESTAMPTZ DEFAULT NOW(),
    hit_count INT DEFAULT 1,
    metadata JSONB DEFAULT '{}'
);

-- Índice HNSW para busca por similaridade
CREATE INDEX idx_semantic_cache_embedding 
ON semantic_cache 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Índice para lookup exato por hash
CREATE UNIQUE INDEX idx_semantic_cache_hash ON semantic_cache(query_hash);
```

### 1.4 Thresholds de Similaridade

| Threshold | Comportamento | Uso |
|-----------|--------------|-----|
| ≥ 0.95 | **Hit exato** — retorna resposta sem questionar | Mesma pergunta, mesmo contexto |
| 0.85 – 0.94 | **Hit similar** — retorna resposta com aviso "resposta similar" | Perguntas re-fraseadas |
| 0.70 – 0.84 | **Hit parcial** — usa como contexto adicional, mas gera nova resposta | Contexto enriquecido |
| < 0.70 | **Miss** — chama LLM normalmente | Pergunta nova |

### 1.5 Política de Expiração

- Cache válido por **7 dias** para respostas de chat
- Cache válido por **1 dia** para pesquisas (resultados mudam)
- Cache válido por **30 dias** para conhecimento factual estável
- Cache LRU: quando a tabela passar de 10.000 entradas, remove as menos acessadas

### 1.6 Cache Invalidation

- **Manual:** `aiw cache clear` — limpa tudo
- **Por tipo:** `aiw cache clear --type search` — limpa só pesquisas
- **Automática:** entradas com `last_hit > 30 dias` são removidas no startup

---

## 2. Smart Router (DeepSeek + Gemini)

### 2.1 Matriz de Roteamento

Cada chamada de LLM é roteada para o modelo mais barato que consegue resolver a tarefa:

| Tipo de Tarefa | Modelo Principal | Custo | Fallback | Custo Fallback | Justificativa |
|----------------|-----------------|-------|----------|----------------|---------------|
| **Planejamento** (sub-questions) | `deepseek-chat` | $0.014/M | Gemini 2.5 Flash (free) | $0 | Planejamento não precisa de raciocínio profundo |
| **Raciocínio** (análise complexa) | `deepseek-reasoner` | $0.055/M | — | — | Precisa de raciocínio, usa o melhor |
| **Síntese** (relatório final) | `deepseek-chat` | $0.014/M | Gemini 2.5 Flash (free) | $0 | Texto bem estruturado, sem necessidade de reasoning |
| **Extração de scraping** | Gemini 2.5 Flash (free) | **$0** | `deepseek-chat` | $0.014/M | Extração é simples, Gemini free resolve |
| **Classificação de fonte** | Gemini 2.5 Flash (free) | **$0** | — | — | Tarefa binária simples |
| **Chat rápido** (`aiw ask`) | Gemini 2.5 Flash (free) | **$0** | `deepseek-chat` | $0.014/M | Conversas curtas, free tier suficente |
| **Código** | `deepseek-chat` | $0.014/M | — | — | DeepSeek é excelente em código |
| **Cache hit** | — | **$0** | — | — | Não chama LLM nenhum |

### 2.2 Fallback Chain

Para cada chamada:

```
1. Cache → hit? retorna (custo: $0)
2. Modelo principal → sucesso? retorna (custo: ~$0.014/M)
3. Fallback free → sucesso? retorna (custo: $0)
4. Fallback pago alternativo → sucesso? retorna (custo: variável)
5. Timeout → erro reportado
```

### 2.3 Health Check por Provedor

```python
health = {
    "deepseek": {
        "status": "up" | "down",
        "latency_ms": 1200,
        "tokens_used_today": 50000,
        "cost_today": 0.0007,
    },
    "gemini": {
        "status": "up" | "down" | "rate_limited",
        "remaining_free_requests": 1400,  # de 1500/dia
        "latency_ms": 800,
    },
    "cache": {
        "status": "up",
        "size": 2341,
        "hit_ratio": 0.68,
        "tokens_saved": 340000,
        "cost_saved": 4.76,
    },
}
```

---

## 3. Budget Enforcer

### 3.1 Limites

| Escopo | Limite | Ação quando excede |
|--------|--------|--------------------|
| **Por chamada** | $0.01 | Rejeita se estimativa > limite |
| **Por pesquisa** | $0.05 | Avisa antes de começar pesquisa cara |
| **Por dia** | $1.00 | Bloqueia chamadas pagas, só cache + Gemini free |
| **Por mês** | $10.00 | Bloqueia tudo, notifica usuário |

### 3.2 Estimativa de Custo Antes de Chamar

```
estimated_cost = (input_tokens * model.input_price + max_output_tokens * model.output_price) / 1_000_000

Exemplo: deepseek-chat
  - input: 4K tokens × $0.00014/K = $0.00056
  - output: 1K tokens × $0.00028/K = $0.00028
  - total estimado = $0.00084
  - bem abaixo do limite de $0.01/chamada → liberado
```

### 3.3 Registro de Gastos

```sql
CREATE TABLE cost_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    provider TEXT NOT NULL,                    -- 'deepseek', 'gemini', 'cache'
    model TEXT NOT NULL,                       -- 'deepseek-chat', 'gemini-2.5-flash'
    task_type TEXT NOT NULL,                   -- 'planning', 'reasoning', 'synthesis', 'extraction'
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0,            -- em USD
    cache_hit BOOLEAN DEFAULT FALSE,
    cached_response_id INT REFERENCES semantic_cache(id),
    query_hash TEXT,
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error TEXT
);

-- Índices para dashboard de custos
CREATE INDEX idx_cost_timestamp ON cost_log(timestamp);
CREATE INDEX idx_cost_provider ON cost_log(provider);
CREATE INDEX idx_cost_task_type ON cost_log(task_type);
```

### 3.4 Circuit Breaker

| Provedor | Failure Threshold | Reset Timeout | Ação |
|----------|------------------|---------------|------|
| DeepSeek | 3 falhas consecutivas | 60 segundos | Roteia para Gemini free |
| Gemini | 5 falhas consecutivas | 30 segundos | Roteia para cache ou erro amigável |
| Cache DB | 2 falhas consecutivas | 120 segundos | Bypass do cache, chama LLM direto |

---

## 4. Integração com o Código Existente

### 4.1 Onde mexer

```python
# src/ai_workspace/
# ├── cost/
# │   ├── __init__.py          → exports
# │   ├── cache.py             → SemanticCache (embeddings + pgvector lookup)
# │   ├── router.py            → SmartRouter (matriz de roteamento + fallback)
# │   ├── budget.py            → BudgetEnforcer (limites + circuit breaker)
# │   └── models.py            → Pydantic models dos registros de custo

# Arquivos existentes que precisam de adaptação:
# providers/__init__.py        → Adicionar router como camada antes do LLM
# search/deep_search.py        → Substituir chamada direta por router.plan()
# agents/swarm.py              → Adicionar cache nas tools dos agentes
```

### 4.2 Fluxo de uma chamada com cache + router

```python
# Como o código cliente vai usar:
from ai_workspace.cost import SemanticCache, SmartRouter, BudgetEnforcer

cache = SemanticCache()
router = SmartRouter()
budget = BudgetEnforcer()

async def ask_llm(task_type: str, prompt: str, context: dict = None):
    # 1. Verifica cache
    cached = cache.get(prompt, task_type)
    if cached:
        return cached.response
    
    # 2. Seleciona modelo mais barato
    model = router.select_model(task_type)  # 'deepseek-chat', 'gemini-2.5-flash', etc.
    
    # 3. Estima custo
    estimated = router.estimate_cost(model, prompt)
    if not budget.can_call(estimated):
        # Tenta fallback mais barato
        model = router.select_fallback(task_type)
        estimated = router.estimate_cost(model, prompt)
        if not budget.can_call(estimated):
            raise BudgetExceededError("Orçamento diário excedido")
    
    # 4. Chama LLM com circuit breaker
    response = await call_with_circuit_breaker(provider=model.provider, ...)
    
    # 5. Salva no cache (se aplicável)
    cache.set(prompt, response, task_type, model.name)
    
    # 6. Registra custo
    budget.log(model, response.tokens_used, estimated)
    
    return response
```

---

## 5. Métricas de Sucesso da Fase 0

| Métrica | Valor Atual | Meta | Como Medir |
|---------|-------------|------|------------|
| Cache hit ratio | 0% | **≥ 60%** | `cost_log` WHERE `cache_hit = TRUE` |
| Custo por pesquisa | ~$0.05 | **≤ $0.001** | `cost_log` agrupado por pesquisa |
| Custo mensal total | ~$10 | **≤ $3.00** | Soma de `cost_log` no mês |
| Latência de cache lookup | — | **< 100ms** | `duration_ms` no `cost_log` |
| Gemini free tier usado | 0% | **≥ 40%** das chamadas | Proporção de chamadas roteadas pra Gemini |

---

## 6. Prioridade de Implementação

```
1. SemanticCache (embeddings + pgvector) → ESSENCIAL pra economia
2. BudgetEnforcer (limites + cost_log)   → EVITA estouro
3. SmartRouter (matriz de roteamento)    → OTIMIZA custo
4. Circuit breaker                       → RESILIÊNCIA
5. Integração com deep_search existente  → USO REAL
6. Migração do provedor padrão pra DeepSeek → FINALIZA
```

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Gemini free rate limit (1500 req/dia) | Média | Cache reduz chamadas. Fallback pra DeepSeek se exceder |
| Embedding model muito lento em CPU | Baixa | `all-MiniLM-L6-v2` roda em ~50ms em CPU comum |
| Cache obsoleto retornando info velha | Média | TTL de 7 dias (chat) / 1 dia (search) / 30 dias (factual) |
| DeepSeek API cair | Baixa | Gemini free como fallback imediato |

---

## Anexo: Custo Realístico por Uso

Cenário: **30 pesquisas completas por dia** (~150 chamadas DeepSeek + ~100 Gemini)

| Item | Chamadas/dia | Tokens/dia | Custo/dia | Custo/mês |
|------|-------------|------------|-----------|-----------|
| DeepSeek-chat (planejamento) | 30 | 120K input | $0.0168 | $0.50 |
| DeepSeek-chat (síntese) | 30 | 180K input | $0.0252 | $0.76 |
| DeepSeek-reasoner (raciocínio) | 30 | 300K input | $0.0165 | $0.50 |
| Gemini free (extração) | 100 | 200K | **$0.00** | **$0.00** |
| Cache hits (economia) | -108 | - | -$0.041 | -$1.23 |
| **Total líquido** | **~82 chamadas** | | **~$0.018/dia** | **~$0.54/mês** |

> Com $10 de crédito, você faz **~18 meses** de uso normal, ou **~700 pesquisas completas** sem cache.
