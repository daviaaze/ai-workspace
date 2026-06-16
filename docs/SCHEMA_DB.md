# Database Architecture — AI Workspace (`aiw`)

**Data:** 2026-06-16 | **SGBD:** PostgreSQL 16 + pgvector
**Database name:** `ai_workspace`  
**Total tables:** 13 + 3 (LangGraph auto) + 4 (Huey)

---

## Visão Geral: Tabelas por Fase

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   ⚡ FASE 0  │    │  🛡️ FASE 1  │    │  🧠 FASE 2  │    │  🔧 FASE 3  │    │  📊 FASE 4  │    │  ✅ FASE 5  │
│   Custo Zero │    │   Fontes    │    │  LangGraph  │    │  Scraping   │    │  Observab.  │    │  Testes+CI  │
├─────────────┤    ├─────────────┤    ├─────────────┤    ├─────────────┤    ├─────────────┤    ├─────────────┤
│ cost_log     │    │ domain_     │    │ workflow_   │    │ (sem tabelas│    │ (sem tabelas│    │ (sem tabelas│
│ semantic_    │    │   reputation│    │   runs      │    │  próprias)  │    │  próprias)  │    │  próprias)  │
│   cache      │    │             │    │ workflow_   │    │             │    │             │    │             │
│              │    │ source_     │    │   step_logs │    │             │    │             │    │             │
│              │    │   tracking  │    │ workflow_   │    │             │    │             │    │             │
│              │    │             │    │   logs      │    │             │    │             │    │             │
│              │    │ cross_      │    │             │    │             │    │             │    │             │
│              │    │   reference_│    │             │    │             │    │             │    │             │
│              │    │   log       │    │             │    │             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       ↑                  ↑                  ↑                  ↑                  ↑                  ↑
       │                  │                  │                  │                  │                  │
       │         ┌────────┴────────┐         │                  │                  │                  │
       │         │  CRED-1 seed    │         │                  │                  │                  │
       │         │  (2.673 domín.)│         │                  │                  │                  │
       │         └─────────────────┘         │                  │                  │                  │
       │                                     │                  │                  │                  │
       │                          ┌──────────┴──────────┐       │                  │                  │
       │                          │ LangGraph auto-      │       │                  │                  │
       │                          │ creates:             │       │                  │                  │
       │                          │ checkpoints          │       │                  │                  │
       │                          │ checkpoint_writes    │       │                  │                  │
       │                          │ checkpoint_blobs     │       │                  │                  │
       │                          └─────────────────────┘       │                  │                  │
       │                                                         │                  │                  │
       │                                              ┌──────────┴──────────┐       │                  │
       │                                              │ Crawl4AI cache      │       │                  │
       │                                              │ (SQLite local)      │       │                  │
       │                                              │ OpenCLI sessions    │       │                  │
       │                                              │ (Chrome)            │       │                  │
       │                                              └─────────────────────┘       │                  │
       │                                                                              │                  │
       │                                                                   ┌──────────┴──────────┐       │
       │                                                                   │ Laminar tracing    │       │
       │                                                                   │ (external service) │       │
       │                                                                   │ Prometheus metrics │       │
       │                                                                   └─────────────────────┘       │
       │                                                                                                   │
       │                                                                                        ┌──────────┴──────────┐
       │                                                                                        │ CI/CD GitHub        │
       │                                                                                        │ Actions (externo)   │
       │                                                                                        └─────────────────────┘
       │
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              ════ TABELAS EXISTENTES ════                                           │
│                                                      (já em produção)                                                │
├──────────────────────────────┬──────────────────────────────┬──────────────────────────────┬─────────────────────────┤
│ knowledge_entries            │ research_entries             │ tasks                        │ agent_memory            │
│ (conhecimento + pgvector)    │ (pesquisas salvas)           │ (agenda + cron)              │ (memórias de agentes)   │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┴─────────────────────────┘
```

---

## ════════════════════════════════════════════════════════════
## RELACIONAMENTOS ENTRE TODAS AS TABELAS
## ════════════════════════════════════════════════════════════

```
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                        TODAS AS TABELAS DO AI WORKSPACE — RELACIONAMENTOS
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

                                        ┌──────────────────────────┐
                                        │      tasks (JÁ EXISTE)    │
                                        │──────────────────────────│
                                        │ id (PK)                  │
                                        │ title                    │
                                        │ description              │
                                        │ status                   │
                                        │ priority                 │
                                        │ tags[]                   │
                                        │ schedule (cron)          │
                                        │ last_run / next_run      │
                                        │ metadata (JSONB)         │
                                        │ created_at / updated_at  │
                                        └──────────────────────────┘

                                        ┌──────────────────────────┐
                                        │   agent_memory (JÁ EXISTE)│
                                        │──────────────────────────│
                                        │ id (PK)                  │
                                        │ agent_name               │
                                        │ memory_type (fact/learn.)│
                                        │ content                  │
                                        │ importance               │
                                        │ embedding vector(768)    │
                                        │ metadata (JSONB)         │
                                        │ created_at               │
                                        └──────────────────────────┘

                                        ┌──────────────────────────┐
                                        │ knowledge_entries (JÁ EX.)│
                                        │──────────────────────────│
                                        │ id (PK)                  │
                                        │ content                  │
                                        │ content_type             │
                                        │ title                    │
                                        │ source                   │
                                        │ tags[]                   │
                                        │ embedding vector(768)    │
                                        │ metadata (JSONB)         │
                                        │ created_at / updated_at  │
                                        └──────────────────────────┘


┌──────────────────────────┐                              ┌──────────────────────────┐
│   cost_log (FASE 0)      │◄──────── optional ──────────│  semantic_cache (FASE 0) │
│──────────────────────────│                              │──────────────────────────│
│ id (PK)                  │                              │ id (PK)                  │
│ timestamp                │        ┌─────────────────────│ query_hash (UNIQUE)      │
│ provider (deepseek/gemini│        │ FK cost_log         │ query_text               │
│ model                    │────────┘ cached_response_id  │ embedding vector(384)    │
│ task_type                │                              │ response_text            │
│ input_tokens             │                              │ response_type            │
│ output_tokens            │                              │ tokens_saved             │
│ cost (USD)               │                              │ cost_saved               │
│ cache_hit (bool)         │                              │ model_used               │
│ cached_response_id (FK)  │                              │ created_at               │
│ query_hash               │                              │ last_hit                 │
│ duration_ms              │                              │ hit_count                │
│ success                  │                              │ metadata (JSONB)         │
│ error                    │                              └──────────────────────────┘
└──────────┬───────────────┘
           │
           │ (cada pesquisa gera N entradas em cost_log)
           │
           ▼
┌──────────────────────────┐        ┌──────────────────────────┐
│ research_entries (JÁ EX.)│        │   workflow_runs (FASE 2) │
│──────────────────────────│        │──────────────────────────│
│ id (PK) ◄────────────────┼────────│ run_id (PK)              │
│ query                    │  FK    │ workflow_name            │
│ summary                  │        │ status                   │
│ detailed_report          │        │ started_at / finished_at │
│ sources[]                │        │ duration_ms              │
│ confidence               │        │ input (JSONB)            │
│ sub_questions (JSONB)    │        │ steps (JSONB)            │
│ tags[]                   │        │ error                    │
│ created_at               │        │ created_at               │
└──────────┬───────────────┘        └────────────┬─────────────┘
           │                                     │
           │ FK                                  │ FK
           │                                     │
           ▼                                     ▼
┌──────────────────────────┐        ┌──────────────────────────┐        ┌──────────────────────────┐
│ source_tracking (FASE 1) │        │   workflow_step_logs     │        │    workflow_logs         │
│──────────────────────────│        │      (FASE 2)            │        │      (FASE 2)            │
│ id (PK)                  │        │──────────────────────────│        │──────────────────────────│
│ url                      │        │ id (PK)                  │        │ id (PK)                  │
│ domain ──────────┐       │        │ run_id (FK)              │        │ run_id (FK)              │
│ title             │      │        │ step_name                │        │ timestamp                │
│ snippet           │      │        │ attempt                  │        │ level                    │
│ score_at_time     │      │        │ status                   │        │ step_name                │
│ first_used        │      │        │ started_at / finished_at │        │ message                  │
│ last_used         │      │        │ duration_ms              │        │ extra (JSONB)            │
│ times_used        │      │        │ output (JSONB)           │        │ created_at               │
│ was_accurate      │      │        │ error                    │        └──────────────────────────┘
│ verified_by       │      │        │ created_at               │
│ research_id (FK) ─┘      │        └──────────────────────────┘
│ sub_question             │
│ created_at               │
└──────────┬───────────────┘
           │ FK
           │
           ▼
┌──────────────────────────┐        ┌──────────────────────────┐
│ domain_reputation (F1)   │        │ cross_reference_log (F1) │
│──────────────────────────│        │──────────────────────────│
│ domain (PK)              │        │ id (PK)                  │
│                          │        │ research_id ─────────────┼───► research_entries.id
│ cred1_score              │        │ claim_hash               │
│ cred1_category           │        │ claim_summary            │
│ cred1_sources            │        │ sources_agreeing         │
│ cred1_last_updated       │        │ sources_disagreeing      │
│                          │        │ total_sources            │
│ credinet_credible        │        │ agreement_ratio          │
│ credinet_last_checked    │        │ consensus                │
│                          │        │ created_at               │
│ times_used               │        └──────────────────────────┘
│ times_accurate           │
│ times_inaccurate         │
│ accuracy_rate            │
│ cross_ref_score          │
│ cross_ref_samples        │
│ user_rating              │
│ user_flags               │
│ user_endorsements        │
│ composite_score          │
│ composite_updated        │
│ first_seen / last_seen   │
│ notes                    │
└──────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                          LANGSMITH/LANGRAPH AUTO-CREATED TABLES (PostgreSQL)
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│     checkpoints      │     │  checkpoint_writes   │     │   checkpoint_blobs   │
│──────────────────────│     │──────────────────────│     │──────────────────────│
│ thread_id            │     │ thread_id            │     │ thread_id            │
│ checkpoint_ns        │     │ checkpoint_ns        │     │ checkpoint_ns        │
│ checkpoint_id        │     │ checkpoint_id        │     │ channel               │
│ parent_checkpoint_id │     │ task_id              │     │ version               │
│ type                 │     │ idx                  │     │ type                  │
│ checkpoint (JSONB)   │     │ channel              │     │ blob                  │
│ metadata (JSONB)     │     │ type                 │     └──────────────────────┘
└──────────────────────┘     │ value                │
                             └──────────────────────┘
  Criadas automaticamente pelo PostgresSaver do LangGraph. Armazenam o estado
  do StateGraph a cada nó executado, permitindo resume de qualquer ponto.


═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                    HUEY TASK QUEUE (SQLite — $HOME/.ai-workspace/tasks.db)
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   kv     │     │ schedule │     │   task   │     │ counter  │
│──────────│     │──────────│     │──────────│     │──────────│
│ queue    │     │ ...      │     │ ...      │     │ ...      │
│ key      │     │          │     │          │     │          │
│ value    │     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘

  Geridas automaticamente pelo SqliteHuey. Não precisam de migração ou cuidado manual.


═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                          ÍNDICES PRINCIPAIS
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────┬──────────────────────────┬───────────────────────────────────────────────────────┐
│ Tabela                                  │ Índice                   │ Tipo / Observação                                    │
├─────────────────────────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────┤
│ semantic_cache                          │ idx_semantic_cache_embed │ HNSW em embedding vector(384) cosine_ops              │
│ semantic_cache                          │ idx_semantic_cache_hash  │ UNIQUE B-tree em query_hash (lookup O(1))             │
│ cost_log                                │ idx_cost_timestamp       │ B-tree em timestamp (dashboard de gastos por período) │
│ cost_log                                │ idx_cost_provider        │ B-tree em provider                                   │
│ cost_log                                │ idx_cost_task_type       │ B-tree em task_type                                  │
│ domain_reputation                       │ idx_domain_composite     │ B-tree em composite_score                            │
│ domain_reputation                       │ idx_domain_cred1         │ B-tree em cred1_score                                │
│ domain_reputation                       │ idx_domain_accuracy      │ B-tree em accuracy_rate                              │
│ source_tracking                         │ idx_source_tracking_dom  │ B-tree em domain (FK lookup)                         │
│ source_tracking                         │ idx_source_tracking_url  │ B-tree em url (dedup)                                │
│ source_tracking                         │ idx_source_tracking_acc  │ B-tree em was_accurate (métricas)                   │
│ cross_reference_log                     │ idx_cross_ref_claim      │ B-tree em claim_hash                                 │
│ cross_reference_log                     │ idx_cross_ref_research   │ B-tree em research_id (FK)                           │
│ knowledge_entries                       │ idx_knowledge_embedding  │ IVFFlat em embedding vector(768) cosine_ops          │
│ workflow_runs                           │ idx_workflow_runs_status │ B-tree em (workflow_name, status, created_at)        │
│ workflow_step_logs                      │ idx_workflow_step_run    │ B-tree em (run_id, created_at)                       │
│ workflow_logs                           │ idx_workflow_logs_run    │ B-tree em (run_id, timestamp)                        │
└─────────────────────────────────────────┴──────────────────────────┴───────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                     FLUXO DE DADOS: DA PERGUNTA AO RELATÓRIO
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

   query do usuário
        │
        ▼
   ┌─────────────┐
   │ semantic_   │ ── HIT? ──► retorna resposta cacheada, insere cost_log (cache_hit=true, cost=$0)
   │ cache       │
   │ (Fase 0)    │ ── MISS? ──► continua...
   └─────────────┘
        │
        ▼
   ┌─────────────┐
   │ budget      │ ── excedeu? ──► BudgetExceededError
   │ enforcer    │
   │ (Fase 0)    │ ── OK? ──► continua...
   └─────────────┘
        │
        ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                      LangGraph StateGraph                        │
   │                         (Fase 2)                                 │
   │                                                                  │
   │   planner ──► supervisor ──► researcher ──► source_filter        │
   │       │            ▲             │               │               │
   │       │            │             │               ▼               │
   │       │            └─────────────┘       ┌───────────────┐       │
   │       │                                  │ smart_router  │       │
   │       │                                  │ (Fase 0)      │       │
   │       │                                  └───────┬───────┘       │
   │       │                                          │               │
   │       │                               ┌──────────▼──────────┐    │
   │       │                               │  web_fetch / crawl4ai│   │
   │       │                               │  / opencli / browser │   │
   │       │                               │  (Fase 3)            │   │
   │       │                               └──────────┬──────────┘    │
   │       │                                          │               │
   │       │                               ┌──────────▼──────────┐    │
   │       │                               │  domain_reputation  │    │
   │       │                               │  (Fase 1)           │    │
   │       │                               │  score < 0.4? ──►   │    │
   │       │                               │  IGNORE (economiza) │    │
   │       │                               └──────────┬──────────┘    │
   │       │                                          │               │
   │       │                            ┌─────────────▼───────────┐    │
   │       │                            │ source_tracking (log)   │    │
   │       │                            │ (Fase 1)                │    │
   │       │                            └─────────────┬───────────┘    │
   │       │                                          │               │
   │       └────────── synthesizer ──► critic ──► human_review        │
   │                          │            │           │               │
   │                          │            │    ┌──────▼──────┐        │
   │                          │            │    │  APPROVED?  │        │
   │                          │            │    └──────┬──────┘        │
   │                          │            │     NO    │   YES         │
   │                          │            └───────────┘    │          │
   │                          │                              │          │
   └──────────────────────────┼──────────────────────────────┘          │
                              │                                         │
                              ▼                                         │
   ┌─────────────────────────────────────────────────────────────────┐  │
   │                      RESULTADO FINAL                             │  │
   │                                                                  │  │
   │  ┌─────────────────┐   ┌──────────────────┐   ┌───────────────┐ │  │
   │  │ research_entries │   │ cross_reference_ │   │    cost_log   │ │  │
   │  │ (relatório)      │   │ log (Fase 1)     │   │ (custo final) │ │  │
   │  └─────────────────┘   └──────────────────┘   └───────────────┘ │  │
   │                                                                  │  │
   │  ┌─────────────────────────┐                                     │  │
   │  │ semantic_cache          │  ← salva resposta pra próxima vez   │  │
   │  │ (Fase 0)                │                                     │  │
   │  └─────────────────────────┘                                     │  │
   │                                                                  │  │
   │  ┌─────────────────────────┐                                     │  │
   │  │ domain_reputation       │  ← atualiza accuracy_rate se        │  │
   │  │ (Fase 1)                │     usuário der feedback            │  │
   │  └─────────────────────────┘                                     │  │
   └─────────────────────────────────────────────────────────────────┘  │
                                                                        │
   ┌────────────────────────────────────────────────────────────────────┘
   │
   ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                    OBSERVABILIDADE (Fase 4)                       │
   │                                                                  │
   │  ┌───────────────┐   ┌──────────────────┐   ┌─────────────────┐ │
   │  │ Laminar       │   │ Dashboard        │   │ Logs            │ │
   │  │ (tracing)     │   │ Streamlit        │   │ structlog       │ │
   │  │               │   │ (cost_log + DB)  │   │ (JSON lines)    │ │
   │  └───────────────┘   └──────────────────┘   └─────────────────┘ │
   └──────────────────────────────────────────────────────────────────┘
```

---

## ════════════════════════════════════════════════════════════
## DETALHAMENTO DE CADA TABELA
## ════════════════════════════════════════════════════════════

### 📦 TABELAS EXISTENTES (já em produção)

```sql
-- ═══ knowledge_entries — Base de conhecimento com busca vetorial ═══
CREATE TABLE knowledge_entries (
    id          SERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'note',
    title       VARCHAR(500),
    source      VARCHAR(500),
    tags        TEXT[] DEFAULT '{}',
    embedding   vector(768),                    -- pgvector pra busca semântica
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
-- Índice: IVFFlat em embedding vector_cosine_ops (lists=100)

-- ═══ research_entries — Resultados de pesquisa salvos ═══
CREATE TABLE research_entries (
    id              SERIAL PRIMARY KEY,
    query           TEXT NOT NULL,
    summary         TEXT,
    detailed_report TEXT,
    sources         TEXT[] DEFAULT '{}',
    confidence      REAL DEFAULT 0.0,
    sub_questions   JSONB DEFAULT '[]',
    tags            TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ═══ tasks — Gerenciador de tarefas com cron ═══
CREATE TABLE tasks (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    status      VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed, failed
    priority    INTEGER DEFAULT 0,
    tags        TEXT[] DEFAULT '{}',
    schedule    VARCHAR(100),                    -- cron expression
    last_run    TIMESTAMPTZ,
    next_run    TIMESTAMPTZ,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
-- Usado pelo Huey periodic_task + scheduler.py

-- ═══ agent_memory — Memória persistente de agentes (estilo mem0) ═══
CREATE TABLE agent_memory (
    id          SERIAL PRIMARY KEY,
    agent_name  VARCHAR(100) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,            -- 'fact', 'preference', 'learning'
    content     TEXT NOT NULL,
    importance  REAL DEFAULT 0.5,
    embedding   vector(768),
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ═══ workflow_runs — Execuções de workflows (engine DAG atual) ═══
CREATE TABLE workflow_runs (
    run_id          SERIAL PRIMARY KEY,
    workflow_name   VARCHAR(200) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    duration_ms     FLOAT DEFAULT 0,
    input           JSONB DEFAULT '{}',
    steps           JSONB DEFAULT '{}',           -- {step_name: StepResult}
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
-- Índice: (workflow_name, status, created_at)

-- ═══ workflow_step_logs — Log de cada passo do workflow ═══
CREATE TABLE workflow_step_logs (
    id          SERIAL PRIMARY KEY,
    run_id      INTEGER NOT NULL REFERENCES workflow_runs(run_id),
    step_name   VARCHAR(200) NOT NULL,
    attempt     INTEGER DEFAULT 1,
    status      VARCHAR(20) NOT NULL,
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms FLOAT DEFAULT 0,
    output      JSONB,
    error       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ═══ workflow_logs — Logs estruturados por workflow ═══
CREATE TABLE workflow_logs (
    id          SERIAL PRIMARY KEY,
    run_id      INTEGER NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level       VARCHAR(20) NOT NULL,             -- debug, info, warning, error
    step_name   VARCHAR(200),
    message     TEXT NOT NULL,
    extra       JSONB DEFAULT '{}'
);
-- Índice: (run_id, timestamp)
```

---

### 🆕 FASE 0 — Custo Zero

```sql
-- ═══ semantic_cache — Cache semântico com pgvector ═══
CREATE TABLE semantic_cache (
    id              SERIAL PRIMARY KEY,
    query_hash      TEXT UNIQUE NOT NULL,             -- MD5 da query original
    query_text      TEXT NOT NULL,
    embedding       vector(384) NOT NULL,             -- all-MiniLM-L6-v2
    response_text   TEXT NOT NULL,
    response_type   TEXT NOT NULL DEFAULT 'chat',     -- chat, search, research
    tokens_saved    INT DEFAULT 0,
    cost_saved      REAL DEFAULT 0.0,
    model_used      TEXT,                             -- modelo que gerou a resposta
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_hit        TIMESTAMPTZ DEFAULT NOW(),
    hit_count       INT DEFAULT 1,
    metadata        JSONB DEFAULT '{}'
);
-- Índice HNSW: embedding vector_cosine_ops (m=16, ef_construction=64)
-- Índice UNIQUE: query_hash

-- ═══ cost_log — Registro de todos os gastos com LLM ═══
CREATE TABLE cost_log (
    id                  SERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ DEFAULT NOW(),
    provider            TEXT NOT NULL,               -- deepseek, gemini, cache
    model               TEXT NOT NULL,               -- deepseek-chat, gemini-2.5-flash
    task_type           TEXT NOT NULL,               -- planning, reasoning, synthesis, extraction
    input_tokens        INT DEFAULT 0,
    output_tokens       INT DEFAULT 0,
    cost                REAL NOT NULL DEFAULT 0.0,
    cache_hit           BOOLEAN DEFAULT FALSE,
    cached_response_id  INT REFERENCES semantic_cache(id),
    query_hash          TEXT,
    duration_ms         INT,
    success             BOOLEAN DEFAULT TRUE,
    error               TEXT
);
-- Índices: timestamp, provider, task_type
```

---

### 🆕 FASE 1 — Source Ranking

```sql
-- ═══ domain_reputation — Reputação consolidada por domínio ═══
-- Seeded com CRED-1 (2.673 domínios) + CrediNet + tracking empírico
CREATE TABLE domain_reputation (
    domain              TEXT PRIMARY KEY,            -- normalizado (ex: "infowars.com")

    -- CRED-1 dataset
    cred1_score         REAL,                        -- 0.0-1.0
    cred1_category      TEXT,                        -- fake, unreliable, conspiracy, mixed, satire, rumor, reliable
    cred1_sources       INT DEFAULT 0,               -- quantas listas independentes flagaram
    cred1_score_age     REAL,                        -- score parcial (idade)
    cred1_score_cat     REAL,                        -- score parcial (categoria)
    cred1_score_factcheck REAL,                      -- score parcial (fact-checking)
    cred1_score_iffy    REAL,                        -- score parcial (Iffy.news)
    cred1_score_safebrowsing REAL,                   -- score parcial (Safe Browsing)
    cred1_score_tranco  REAL,                        -- score parcial (popularidade Tranco)
    cred1_last_updated  TIMESTAMPTZ,

    -- CrediNet fallback
    credinet_credible   BOOLEAN,
    credinet_last_checked TIMESTAMPTZ,

    -- Tracking empírico (nosso)
    times_used          INT DEFAULT 0,
    times_accurate      INT DEFAULT 0,
    times_inaccurate    INT DEFAULT 0,
    accuracy_rate       REAL DEFAULT NULL,           -- times_accurate / (times_accurate + times_inaccurate)

    -- Cross-reference
    cross_ref_score     REAL DEFAULT NULL,
    cross_ref_samples   INT DEFAULT 0,

    -- User feedback
    user_rating         REAL DEFAULT NULL,           -- -1.0 a 1.0
    user_flags          INT DEFAULT 0,
    user_endorsements   INT DEFAULT 0,

    -- Score composto final
    composite_score     REAL DEFAULT 0.5,
    composite_updated   TIMESTAMPTZ DEFAULT NOW(),

    -- Metadados
    first_seen          TIMESTAMPTZ DEFAULT NOW(),
    last_seen           TIMESTAMPTZ DEFAULT NOW(),
    notes               TEXT
);
-- Índices: composite_score, cred1_score, accuracy_rate

-- ═══ source_tracking — Tracking individual de URLs usadas ═══
CREATE TABLE source_tracking (
    id              SERIAL PRIMARY KEY,
    url             TEXT NOT NULL,
    domain          TEXT NOT NULL REFERENCES domain_reputation(domain),
    title           TEXT DEFAULT '',
    snippet         TEXT DEFAULT '',

    -- Snapshot do score no momento do uso
    score_at_time   REAL DEFAULT 0.5,

    -- Uso
    first_used      TIMESTAMPTZ DEFAULT NOW(),
    last_used       TIMESTAMPTZ DEFAULT NOW(),
    times_used      INT DEFAULT 1,

    -- Validação posterior
    was_accurate    BOOLEAN,                         -- NULL = não verificado ainda
    verified_by     TEXT DEFAULT '',                  -- user, cross_ref, auto

    -- Pesquisa associada
    research_id     INT REFERENCES research_entries(id),
    sub_question    TEXT DEFAULT ''
);
-- Índices: domain, url, was_accurate

-- ═══ cross_reference_log — Concordância entre fontes sobre claims ═══
CREATE TABLE cross_reference_log (
    id                  SERIAL PRIMARY KEY,
    research_id         INT REFERENCES research_entries(id),
    claim_hash          TEXT NOT NULL,
    claim_summary       TEXT NOT NULL,
    sources_agreeing    INT DEFAULT 0,
    sources_disagreeing INT DEFAULT 0,
    total_sources       INT DEFAULT 0,
    agreement_ratio     REAL DEFAULT 0.0,
    consensus           TEXT DEFAULT '',              -- agrees, disagrees, inconclusive
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
-- Índices: claim_hash, research_id
```

---

### 🆕 FASE 2 — LangGraph (não precisa de tabelas novas)

As tabelas `workflow_runs`, `workflow_step_logs` e `workflow_logs` **já existem** do engine DAG atual e serão **reaproveitadas** pelo LangGraph.

O LangGraph também cria 3 tabelas automaticamente via `PostgresSaver`:
- **checkpoints** — estado do grafo a cada nó (thread_id, checkpoint_id, checkpoint JSONB)
- **checkpoint_writes** — saída de cada canal (channel, value)
- **checkpoint_blobs** — blobs grandes (blob)

---

### FASE 3 — Scraping (sem tabelas próprias)

Crawl4AI usa **cache em memória/arquivo** local. OpenCLI usa **sessões do Chrome**. browser-use não persiste. Todos os resultados de scraping vão para as tabelas de pesquisa existentes.

---

### FASE 4 — Observabilidade (sem tabelas próprias)

Laminar é serviço externo. Prometheus é externo. Dashboard Streamlit lê de `cost_log`, `semantic_cache`, `domain_reputation` e `workflow_runs`.

Logs estruturados via `structlog` são emitidos para stdout/stderr em JSON lines.

---

### FASE 5 — Testes + Deploy (sem tabelas próprias)

CI/CD via GitHub Actions. Cobertura monitorada via Codecov. Tudo externo ao banco.

---

## ════════════════════════════════════════════════════════════
## MIGRAÇÕES: O QUE MUDAR NO DB ATUAL
## ════════════════════════════════════════════════════════════

### Tabelas NOVAS (a serem criadas)

| Fase | Tabela | Depende de | Seed inicial |
|------|--------|-----------|-------------|
| 0 | `semantic_cache` | pgvector | Vazia (preenche com uso) |
| 0 | `cost_log` | — | Vazia |
| 1 | `domain_reputation` | — | **CRED-1**: 2.673 domínios + manual seed de confiáveis |
| 1 | `source_tracking` | `domain_reputation`, `research_entries` | Vazia |
| 1 | `cross_reference_log` | `research_entries` | Vazia |

### Tabelas EXISTENTES (sem alteração estrutural)

| Tabela | Uso atual | Uso pós-migração |
|--------|----------|-----------------|
| `knowledge_entries` | Knowledge base com pgvector | **Igual** — continua igual |
| `agent_memory` | Memórias de agentes | **Igual** — o LangGraph usa suas próprias tabelas |
| `tasks` | Tarefas com cron | **Igual** — Huey continua gerenciando |
| `research_entries` | Resultados de pesquisa | **Igual** — mas agora é populado pelo LangGraph |

### Tabelas REAPROVEITADAS (com ajuste de FK ou coluna nova)

| Tabela | Mudança | Motivo |
|--------|---------|--------|
| `workflow_runs` | Nenhuma estrutural | LangGraph `PostgresSaver` gerencia separadamente. Esta tabela serve como **log de execução alto nível** |
| `workflow_step_logs` | Nenhuma estrutural | Continua como tabela de log de passos (o LangGraph não sobrescreve) |
| `workflow_logs` | Nenhuma estrutural | Continua como log estruturado |
| `research_entries` | Adicionar FK opcional pra `source_tracking` | Já existe FK implícita via `source_tracking.research_id` |

### Tabelas que o LangGraph CRIA AUTOMATICAMENTE

Estas **não precisam ser criadas manualmente** — o `PostgresSaver` do LangGraph as cria no primeiro uso:

| Tabela | Finalidade |
|--------|-----------|
| `checkpoints` | Estado do StateGraph a cada nó |
| `checkpoint_writes` | Saída de cada canal do grafo |
| `checkpoint_blobs` | Blobs grandes (documentos, etc.) |

---

## ════════════════════════════════════════════════════════════
## DIAGRAMA DE CHAVES ESTRANGEIRAS (FK) COMPLETO
## ════════════════════════════════════════════════════════════

```
cost_log.cached_response_id  ──────►  semantic_cache.id            (optional, NULL se cache miss)

source_tracking.domain       ──────►  domain_reputation.domain     (required, todo domínio precisa ter score)
source_tracking.research_id  ──────►  research_entries.id          (optional, qual pesquisa usou esta fonte)

cross_reference_log.research_id ───►  research_entries.id          (optional, qual pesquisa gerou este cross-ref)

workflow_step_logs.run_id    ──────►  workflow_runs.run_id         (required, cada passo pertence a um run)

domain_reputation.domain     ◄──────  source_tracking.domain        (FK reversa: 1 domínio tem N URLs)
research_entries.id          ◄──────  source_tracking.research_id   (FK reversa: 1 pesquisa tem N fontes)
research_entries.id          ◄──────  cross_reference_log.research_id (FK reversa: 1 pesquisa tem N cross-refs)
```

---

## ════════════════════════════════════════════════════════════
## TAMANHO ESTIMADO DO BANCO
## ════════════════════════════════════════════════════════════

| Tabela | Linhas iniciais | Crescimento/mês | Tamanho estimado (1 ano) |
|--------|----------------|-----------------|--------------------------|
| `semantic_cache` | 0 | ~1.000 | ~10 MB |
| `cost_log` | 0 | ~3.000 | ~5 MB |
| `domain_reputation` | 2.673 (seed) | ~500 | ~2 MB |
| `source_tracking` | 0 | ~2.000 | ~3 MB |
| `cross_reference_log` | 0 | ~500 | ~1 MB |
| `knowledge_entries` | ~15 (atual) | ~200 | ~5 MB |
| `research_entries` | ~79 (atual) | ~300 | ~10 MB |
| `agent_memory` | ~33 (atual) | ~100 | ~2 MB |
| `workflow_runs` | ~10 (atual) | ~300 | ~3 MB |
| `workflow_step_logs` | ~50 (atual) | ~1.500 | ~5 MB |
| `workflow_logs` | ~100 (atual) | ~3.000 | ~10 MB |
| `tasks` | ~2 (atual) | ~50 | ~1 MB |
| **TOTAL** | **~2.900** | **~11.450/mês** | **~60 MB** |

> Banco de ~60 MB/ano — perfeitamente leve para PostgreSQL no homelab.