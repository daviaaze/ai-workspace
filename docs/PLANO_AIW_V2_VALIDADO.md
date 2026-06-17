# AI Workspace v2 — Plano Validado (Junho 2026)

**Status:** Plano definitivo, revisado com pesquisa de mercado (16/06/2026)
**Princípio:** LEAN mas completo — daily driver que funciona hoje e melhora continuamente
**Stack:** Python-only, PostgreSQL + pgvector, single-node (mesh opcional futuro)

---

## 🔬 Pesquisa de Mercado: O Que Mudou

Cada decisão abaixo foi validada contra o estado da arte em Junho/2026:

| Componente | Plano anterior | Pesquisa atual | Decisão final |
|-----------|---------------|----------------|---------------|
| **Orquestração** | LangGraph (substituir crewAI) | crewAI agora é standalone (sem LangChain), 5.76x mais rápido que LangGraph, tem Flows com state/checkpoint | ✅ **Manter crewAI** como orquestrador principal. Ele já está em produção e os Flows resolvem o que LangGraph faria |
| **MCP** | MCP server registry + A2A | MCP Python SDK v2 alpha (stable Jul/2026), FastMCP trivial, CRED-1 já tem MCP server | ✅ **MCP com FastMCP** para tools padronizadas. Esperar v2 stable para produção |
| **Scraping principal** | Crawl4AI + OpenCLI | Crawl4AI: 51k+ ⭐, v0.8.9, markdown limpo, async, Playwright, deep crawling, Docker self-hosted. OpenCLI depende de extensão Chrome | ✅ **Crawl4AI** como scraping principal. OpenCLI removido (dependência Chrome, manutenção comunitária) |
| **Browser autônomo** | browser-use | v0.13 com Rust core. Cloud-hosted é muito superior ao self-hosted | 🟡 **browser-use self-hosted** apenas para fallback de navegação complexa |
| **Vector DB** | pgvector | v0.8.2, HNSW, half-precision, sparse, 12k+ ⭐. Padrão indiscutível | ✅ **PostgreSQL + pgvector**. Sem DB externo |
| **Embedding** | all-MiniLM-L6-v2 | Ainda o melhor lightweight (22.7M params, 384-dim, ~50ms CPU) | ✅ **all-MiniLM-L6-v2** com opção ONNX |
| **LLM Principal** | DeepSeek | DeepSeek V4 Flash: $0.14/$0.28 por 1M tokens. Melhor custo-benefício | ✅ **DeepSeek** (pago, barato) |
| **LLM Fallback** | Gemini free tier | Gemini 2.5 Flash-Lite: $0.10/$0.40 por 1M. Free tier: 60 req/min, 1500/dia | ✅ **Gemini free tier** para tarefas leves |
| **Source credibility** | CRED-1 + CrediNet | CRED-1: 2.672 domínios, atualização semanal, tem MCP server. WebTrust é promissor (statement-level) | ✅ **CRED-1** seed + CrediNet fallback. WebTrust como futuro |
| **Task queue** | Huey | Huey é minimalista, SQLite sem Redis. ARQ é mais rápido mas precisa Redis. Celery é pesado | ✅ **Huey** (já funciona, sem infra extra) |
| **Observabilidade** | Laminar | Laminar: open-source Apache 2.0, agent-first, SQL-native, self-hostable. Langfuse é alternativa MIT | ✅ **Laminar** para tracing. structlog para logs. Streamlit para dashboard |
| **Cache semântico** | Build próprio com pgvector | GPTCache é a lib padrão mas pesada. Redis Vector Search é rápido mas precisa Redis. Nossa escala é single-user | ✅ **Cache próprio com pgvector** (sem Redis). Simples, zero infra extra |
| **TUI** | Textual | Já em uso, funciona | ✅ **Textual** (já implementado) |
| **Web dashboard** | Streamlit vs React | Streamlit já está implementado e funcionando | ✅ **Streamlit** (simples, já funciona) |

---

## 🎯 O Que o AI Workspace FAZ

### Domínio do aiw
| Feature | Descrição |
|---------|-----------|
| **Deep research** | Pesquisa multi-camada com fontes rankeadas, cross-reference, cache semântico |
| **Knowledge store** | PostgreSQL + pgvector: notas, pesquisas, memórias de agentes, busca semântica |
| **Task management** | Tarefas com cron, status tracking, assignee (agent/human) |
| **Agent orchestration** | crewAI Flows: supervisor-worker, state management, checkpoint |
| **Web scraping** | Crawl4AI: markdown limpo para LLM, JS rendering, async, $0 |
| **Source reputation** | CRED-1 + tracking empírico: score 0.0-1.0 por domínio |
| **Cost optimization** | Cache semântico, smart router DeepSeek→Gemini, budget enforcer |
| **MCP tools** | Ferramentas padronizadas via FastMCP (scraping, busca, knowledge, git) |
| **TUI** | Terminal como operations center: multi-painel, agent lanes, atalhos |
| **Scheduled workflows** | daily_briefing, continuous_learning, backups via Huey + systemd |
| **Obsidian sync** | Bidirectional: DB ↔ vault markdown |

### O que NÃO é job do aiw (domínio do pi)
| Feature | Por que não |
|---------|------------|
| Code editing / debugging | pi tem graph tools, safety extensions, TDD skill |
| Code review | pi tem impact_radius, detect_changes, review context |
| Git management (commit/PR/branch) | pi tem conventional commits, PR creation |
| NixOS configuration | pi tem nixfiles skill com system context |
| Permission gates (runtime) | pi extensions fazem safety em nível de runtime |
| Test generation | pi tem TDD skill com codebase awareness |

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Workspace (aiw)                        │
│                                                              │
│  Interfaces:                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ CLI/TUI   │  │ MCP Server   │  │ Streamlit Dashboard   │  │
│  │ (Textual) │  │ (FastMCP)    │  │ (mobile, monitoring)  │  │
│  └─────┬─────┘  └──────┬───────┘  └───────────┬───────────┘  │
│        │               │                      │               │
│        └───────────────┼──────────────────────┘               │
│                        │                                      │
│  ┌─────────────────────▼──────────────────────────────────┐  │
│  │              crewAI Flows + Agents                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │  │
│  │  │ Research │  │  Source  │  │  Cost Optimizer    │    │  │
│  │  │ Pipeline │  │ Ranker   │  │  (cache + router)  │    │  │
│  │  └──────────┘  └──────────┘  └────────────────────┘    │  │
│  └─────────────────────┬──────────────────────────────────┘  │
│                        │                                      │
│  ┌─────────────────────▼──────────────────────────────────┐  │
│  │                    Data Layer                            │  │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌──────────┐  │  │
│  │  │ PostgreSQL        │  │ Huey Tasks   │  │ Markdown │  │  │
│  │  │ + pgvector        │  │ (SQLite)     │  │ memory/  │  │  │
│  │  └──────────────────┘  └──────────────┘  └──────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                              │
│  Tools (via MCP):                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│  │ Crawl4AI │ │ DeepSeek │ │ Gemini   │ │ browser-use   │   │
│  │ (scrape) │ │ (LLM)    │ │ (fallback)│ │ (navigation)  │   │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Roadmap por Fases (Revisado)

### FASE 0 — CUSTO ZERO (1-2 semanas) ← COMEÇAR AQUI

**Objetivo:** Custo médio por pesquisa < $0.001. 70% de cache hit rate.

| # | Tarefa | Status | Detalhe |
|---|--------|--------|---------|
| 0.1 | **Semantic cache com pgvector** | ✅ Feito | Embedding dual (Ollama nomic-embed-text 768-dim + sentence-transformers 384-dim). Tabela `semantic_cache` com HNSW index. Hash lookup + cosine similarity. Threshold: ≥0.95 hit exato, ≥0.85 hit similar. |
| 0.2 | **Smart router DeepSeek→Gemini** | ✅ Feito | `SmartRouter` em `agents/router.py`. Matriz de roteamento por task_type + complexity detection. Fallback chain automático. Integrado no AgentWorker e Orchestrator. |
| 0.3 | **Budget enforcer** | ✅ Feito | `BudgetEnforcer` + `CircuitBreaker` + `BudgetExceededError`. Limites: $0.01/call, $1.00/dia, $10.00/mês. Circuit breaker por provider (deepseek 3/60s, gemini 5/30s, ollama 2/120s). `aiw budget` command. |
| 0.4 | **Configurar DeepSeek como padrão** | ✅ Feito | `--provider deepseek` já funciona no `aiw search` e `aiw ask` |
| 0.5 | **Integrar cache no deep_search** | ✅ Feito | `_cached_kickoff()` com cache + budget check antes de cada chamada LLM |
| 0.6 | **Corrigir `aiw ask`** | ✅ Corrigido | Ollama agora usa `/api/chat` nativo (não `/v1`). Timeout 300s. Streaming funcional. |

**Métrica de sucesso:** Cache hit ≥ 60%, custo/pesquisa ≤ $0.001. ✅ Infraestrutura completa, 40 testes, 318 total.

---

### FASE 1 — QUALIDADE DAS FONTES (1-2 semanas)

**Objetivo:** Toda fonte tem score. Fontes com score < 0.4 são ignoradas (economiza tokens).

| # | Tarefa | Status | Detalhe |
|---|--------|--------|---------|
| 1.1 | **Database de source reputation** | ✅ Feito | Tabelas: `domain_reputation`, `source_tracking`, `cross_reference_log`. Composite scoring com pesos: CRED-1 (0.40) + empírico (0.30) + cross-ref (0.20) + user (0.10) |
| 1.2 | **Seed CRED-1** (2.672 domínios) | ✅ Feito | `aiw source seed` + `scripts/download_cred1.py`. Upsert semanal via Huey pendente. |
| 1.3 | **CrediNet fallback** | 🟡 Pendente | `pip install credigraph` necessário. Cache 7 dias. Só consulta se não está no CRED-1. |
| 1.4 | **Algoritmo de score composto** | ✅ Feito | Pesos configuráveis em `SourceReputationService`. Threshold: ≥0.60 trust, ≥0.40 warn, <0.40 ignore. Manual seed de 20 domínios confiáveis. |
| 1.5 | **Cross-reference scoring** | 🟡 Tabela existe | Tabela `cross_reference_log` criada, lógica de cross-ref pendente. |
| 1.6 | **Filtro no deep_search** | ✅ Feito | Step 2.5 filtra fontes com score < 0.4 antes do synthesizer. Registra uso via `record_use()`. |
| 1.7 | **CLI de feedback** | ✅ Feito | `aiw source check/endorse/flag/stats/seed` |
| 1.8 | **Seed manual de fontes confiáveis** | ✅ Feito | 20 domínios: arXiv, GitHub, Wikipedia, Reuters, Nature, etc. Score ≥ 0.85. |

**Métrica de sucesso:** 100% das fontes com score, 10-30% descartadas por baixa qualidade

---

### FASE 2 — AGENTES + ORQUESTRAÇÃO (2-3 semanas)

**Objetivo:** Pipeline de pesquisa resiliente com state management, supervisor, human-in-the-loop.

**Nova decisão:** Manter crewAI (não migrar para LangGraph). crewAI Flows já oferecem:
- State management entre passos
- Event-driven execution (`@start`, `@listen`, `@router`)
- Checkpoint/persistência
- Human-in-the-loop
- 5.76x mais rápido que LangGraph em benchmarks
- Sem dependência do ecossistema LangChain

| # | Tarefa | Status | Detalhe |
|---|--------|--------|---------|
| 2.1 | **Migrar deep_search para crewAI Flow** | ❌ Refatorar | Substituir DAG engine customizado (`workflow/engine.py`) por crewAI Flow com state tracking |
| 2.2 | **Adicionar supervisor agent** | ❌ Novo | Decide: continuar pesquisando, ir pra síntese, ou parar. Baseado em: remaining sub-questions, qualidade das respostas, remaining steps |
| 2.3 | **Source filter como nó do flow** | ❌ Novo | Nó que filtra fontes antes do synthesizer (Fase 1) |
| 2.4 | **Critic agent** | ❌ Novo | Revisa qualidade do relatório. Decide: aprovar ou pedir revisão |
| 2.5 | **Human-in-the-loop** | ❌ Novo | Pausa antes de finalizar relatório. `aiw research review <id>` para aprovar/rejeitar |
| 2.6 | **Pydantic structured output** | ❌ Novo | Substituir `_parse_json_safe()` frágil por `output_pydantic` em todas as tasks |
| 2.7 | **Memória compartilhada entre agentes** | ❌ Novo | crewAI já tem Memory nativa. Integrar com `agent_memory` table |
| 2.8 | **YAML config para agentes** | 🟡 Parcial | Mover definições de agentes para `config/agents.yaml` e `config/tasks.yaml` |

**Métrica de sucesso:** Pesquisas com checkpoint 100%, tempo médio < 1min, human-in-the-loop ativo

---

### FASE 3 — SCRAPING + FERRAMENTAS (1-2 semanas)

**Objetivo:** Scraping de qualquer site sem API externa paga. Ferramentas padronizadas via MCP.

**Nova decisão:** Crawl4AI como scraping principal. OpenCLI removido (depende de extensão Chrome proprietária, manutenção comunitária incerta). browser-use apenas como fallback.

| # | Tarefa | Status | Detalhe |
|---|--------|--------|---------|
| 3.1 | **Crawl4AI como ferramenta principal** | ❌ Novo | `pip install crawl4ai`. AsyncWebCrawler com markdown output. Cache by URL. JS rendering com Playwright |
| 3.2 | **browser-use como fallback** | ❌ Novo | Apenas para sites que exigem navegação multi-passo (login, formulários). Limitado a 10 steps |
| 3.3 | **MCP servers para ferramentas** | 🟡 Parcial | Crawl4AI MCP server, Knowledge MCP server, Source Reputation MCP server. Usar FastMCP |
| 3.4 | **MCP tools como funções no crewAI** | ❌ Novo | Agentes crewAI podem chamar MCP tools diretamente |
| 3.5 | **Hierarquia de scraping** | ❌ Novo | WebFetchTool → Crawl4AI → HeadlessBrowserTool → browser-use. Sempre tentar o mais barato primeiro |
| 3.6 | **Remover OpenCLI do plano** | ✅ Decisão | Dependência Chrome + manutenção comunitária. Crawl4AI cobre 90% dos casos |

**Métrica de sucesso:** ≥ 90% de sucesso em scraping. Zero APIs externas pagas para scraping.

---

### FASE 4 — OBSERVABILIDADE (1 semana)

**Objetivo:** Saber exatamente onde cada centavo é gasto. Debug rápido de falhas.

**Nova decisão:** Laminar (open-source, Apache 2.0, agent-first) para tracing. structlog para logs. Streamlit para dashboard.

| # | Tarefa | Status | Detalhe |
|---|--------|--------|---------|
| 4.1 | **Laminar tracing** | ❌ Novo | `@observe` em chamadas LLM + crewAI flows. Spans: tokens, latency, cost, model, cache_hit |
| 4.2 | **Dashboard de custos (Streamlit)** | 🟡 Parcial | Página já existe. Adicionar: cache hit ratio, gasto por modelo, gasto diário/mensal |
| 4.3 | **Logs estruturados (structlog)** | ❌ Novo | JSON lines. Níveis: DEBUG (dev), INFO (normal), WARNING (recuperável), ERROR (falha), CRITICAL (sistema quebrado) |
| 4.4 | **Alertas de budget** | ❌ Novo | WARNING a $0.50/dia, BLOCK a $1.00/dia. Notificação no TUI banner |

**Métrica de sucesso:** 100% chamadas LLM traçadas, debug de falha < 5min

---

### FASE 5 — TESTES + DEPLOY (contínuo)

**Objetivo:** Cobertura ≥ 70%, CI/CD, deploy automático no homelab.

| # | Tarefa | Status | Detalhe |
|---|--------|--------|---------|
| 5.1 | **Testes de unidade (módulos novos)** | 🔴 0% | Cache, router, budget, source reputation, scraping. Usar mocks para LLM |
| 5.2 | **Testes de integração** | 🔴 0% | DB real (pgvector), crewAI flows com mock de LLM |
| 5.3 | **Testes E2E** | 🔴 0% | Fluxo completo: search → cache → source filter → report. 5% da suíte |
| 5.4 | **CI/CD GitHub Actions** | ❌ Novo | Lint (ruff), type check (mypy), tests (pytest --cov), deploy hook |
| 5.5 | **NixOS module update** | ✅ Feito | Já funciona no homelab. Manter atualizado |

**Métrica de sucesso:** Cobertura ≥ 70%, CI passando, deploy automático

---

### FORA DO ESCOPO (explicitamente)

Estas features foram consideradas e **rejeitadas** para manter o foco LEAN:

| Feature | Motivo da rejeição |
|---------|-------------------|
| **Go HTTP server** | Python-only é suficiente. Sem benefício para single-user |
| **NATS mesh / multi-node** | Single-node cobre 100% do uso atual. Complexidade desnecessária |
| **React/Vue Web Dashboard** | Streamlit já funciona. PWA complexo sem ganho real |
| **Multi-channel messaging (Slack/Telegram/WhatsApp)** | Muito esforço para pouco uso. Telegram bot pode ser adicionado depois |
| **MinIO/S3 object store** | Só necessário com mesh |
| **A2A protocol** | MCP cobre comunicação agente↔ferramenta. A2A só com multi-agentes especializados |
| **Context Workbench (A/B testing de contextos)** | Overengineering para single-user |
| **Monoflake IDs** | SERIAL do PostgreSQL é suficiente |
| **OpenCLI** | Substituído por Crawl4AI (mais simples, sem Chrome extension) |
| **Redis/Valkey L2 cache** | pgvector L1 cache é suficiente para single-user. Redis adiciona infra desnecessária |
| **Múltiplos workspaces** | Single workspace atende 100% do uso. Adicionar depois se necessário |

---

## 📊 Database Schema (Consolidado)

### Tabelas Existentes (manter)
- `knowledge_entries` — base de conhecimento com pgvector
- `agent_memory` — memórias de agentes (facts, preferences, learnings)
- `tasks` — gerenciador de tarefas com cron
- `research_entries` — resultados de pesquisa
- `workflow_runs`, `workflow_step_logs`, `workflow_logs` — execução de workflows

### Tabelas Novas (criar)

**Fase 0:**
- `semantic_cache` — cache semântico com pgvector HNSW
- `cost_log` — registro de gastos com LLM

**Fase 1:**
- `domain_reputation` — reputação por domínio (CRED-1 + empírico)
- `source_tracking` — tracking individual de URLs
- `cross_reference_log` — concordância entre fontes

### Índices (adicionar aos existentes)
```sql
-- HNSW é superior a IVFFlat para nosso volume
CREATE INDEX ON semantic_cache USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX ON knowledge_entries USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Índices para queries frequentes
CREATE INDEX ON cost_log (timestamp);
CREATE INDEX ON cost_log (provider, task_type);
CREATE INDEX ON domain_reputation (composite_score);
CREATE INDEX ON source_tracking (domain);
CREATE INDEX ON cross_reference_log (research_id);
```

---

## 📐 Estrutura do Código (Alvo)

```
src/ai_workspace/
├── agents/              → Agentes crewAI (swarm.py, config/*.yaml)
├── search/              → Deep search pipeline (deep_search.py)
├── sources/             → Source reputation (reputation.py, cred1.py, scoring.py)
├── cost/                → Cache + router + budget (cache.py, router.py, budget.py)
├── knowledge/           → PostgreSQL + pgvector (store.py)
├── providers/           → LLM providers (__init__.py)
├── tools/               → Web scraping, filesystem, shell
├── mcp_server/          → MCP servers (FastMCP)
├── workflow/            → crewAI Flows (substitui engine.py customizado)
├── tasks/               → Huey scheduler (scheduler.py)
├── tui/                 → Textual TUI (app.py)
├── dashboard/           → Streamlit (app.py)
├── observability/       → Laminar + structlog + metrics
├── cli.py               → CLI (Typer)
└── rules/               → Behavioral rules for agents
```

---

## 🔄 Fluxo Completo de uma Pesquisa (End-to-End)

```
Usuário: aiw search "melhores ferramentas MCP para scraping em 2026"
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. SEMANTIC CACHE (Fase 0)                                   │
│    embedding = all-MiniLM-L6-v2(query)                       │
│    SELECT * FROM semantic_cache                              │
│    WHERE embedding <=> query_embedding < 0.05                │
│    LIMIT 1                                                    │
│    → HIT? retorna resposta cacheada (custo: $0, latência: <100ms) │
│    → MISS? continua                                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. BUDGET CHECK (Fase 0)                                     │
│    estimated_cost = tokens × model_price                     │
│    → Excedeu? BudgetExceededError ou fallback Gemini free    │
│    → OK? continua                                             │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. CREWAI FLOW (Fase 2)                                      │
│                                                               │
│    planner (DeepSeek) → sub-questions [3-5]                  │
│        │                                                      │
│        ▼                                                      │
│    supervisor → decide: research_more / filter_sources / end │
│        │                                                      │
│        ├──→ researcher (DeepSeek) → pesquisa sub-question    │
│        │       └──→ Crawl4AI scrape URLs                    │
│        │       └──→ source reputation check (Fase 1)         │
│        │       └──→ score < 0.4? IGNORE                      │
│        │       └──→ extract answer via LLM                   │
│        │       └──→ volta pro supervisor                     │
│        │                                                      │
│        └──→ (loop até todas sub-questions respondidas)       │
│                                                               │
│    source_filter → filtra fontes com score < 0.4             │
│        │                                                      │
│        ▼                                                      │
│    synthesizer (DeepSeek) → relatório consolidado            │
│        │                                                      │
│        ▼                                                      │
│    critic (Gemini free) → revisa qualidade                   │
│        │                                                      │
│        ├──→ revise → volta pro synthesizer                   │
│        └──→ approve → continua                               │
│                                                               │
│    human_review → PAUSA (aguarda aprovação)                  │
│        │                                                      │
│        ├──→ approved → END                                   │
│        └──→ rejected → volta pro synthesizer                 │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. PERSISTÊNCIA                                              │
│    → INSERT INTO research_entries (report, sources, cost)    │
│    → INSERT INTO semantic_cache (query, response, embedding) │
│    → UPDATE domain_reputation (accuracy_rate)                │
│    → INSERT INTO cost_log (tokens, cost, model)              │
│    → INSERT INTO cross_reference_log (claims, agreement)     │
└──────────────────────────────────────────────────────────────┘
```

---

## 📈 Métricas de Sucesso (Revisadas)

| Métrica | Atual | Meta Fase 0 | Meta Fase 1 | Meta Fase 2 | Meta Final |
|---------|-------|-------------|-------------|-------------|------------|
| Cache hit ratio | 0% | ≥ 60% | ≥ 60% | ≥ 65% | ≥ 70% |
| Custo por pesquisa | ~$0.05 | ≤ $0.001 | ≤ $0.001 | ≤ $0.001 | ≤ $0.001 |
| Custo mensal total | ~$10 (OpenRouter) | ≤ $3 | ≤ $3 | ≤ $3 | ≤ $3 |
| Fontes com score | 0% | 0% | 100% | 100% | 100% |
| Fontes ignoradas (score < 0.4) | 0% | 0% | 10-30% | 10-30% | 10-30% |
| Pesquisas com checkpoint | 0% | 0% | 0% | 100% | 100% |
| Tempo médio de pesquisa | ~2min | ~1.5min | ~1.5min | < 1min | < 45s |
| Test coverage | ~5% | ~5% | ~10% | ~30% | ≥ 70% |
| Tokens economizados (cache) | 0 | ≥ 100K/dia | ≥ 150K/dia | ≥ 200K/dia | ≥ 250K/dia |

---

## 🔗 Dependências Externas

| Ferramenta | Uso | Licença | Versão alvo | Fase |
|-----------|-----|---------|------------|------|
| [crewAI](https://github.com/crewAIInc/crewAI) | Orquestração de agentes | MIT | ≥1.14 | 0-5 |
| [DeepSeek API](https://platform.deepseek.com/) | LLM principal | Pago (~$0.14/M) | V4 Flash | 0 |
| [Gemini API](https://ai.google.dev/) | LLM fallback free | Grátis (60 req/min) | 2.5 Flash-Lite | 0 |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | Web scraping | Apache 2.0 | ≥0.8.9 | 3 |
| [browser-use](https://github.com/browser-use/browser-use) | Navegador autônomo (fallback) | MIT | ≥0.13 | 3 |
| [pgvector](https://github.com/pgvector/pgvector) | Vector search no PostgreSQL | PostgreSQL | 0.8.2 | 0-5 |
| [FastMCP](https://github.com/modelcontextprotocol/python-sdk) | MCP servers | MIT | ≥1.27 (v2 estável Jul/2026) | 3 |
| [CRED-1](https://github.com/aloth/cred-1) | Dataset de credibilidade | CC BY 4.0 | v2026-04-14 | 1 |
| [CrediNet](https://github.com/credi-net/CrediNet) | API de credibilidade (fallback) | CC BY 4.0 | latest | 1 |
| [Laminar](https://github.com/lmnr-ai/lmnr) | Tracing/observabilidade | Apache 2.0 | latest | 4 |
| [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Embedding model (CPU) | Apache 2.0 | latest | 0 |
| [Huey](https://github.com/coleifer/huey) | Task queue | MIT | ≥3.0 | 0-5 |
| [Textual](https://github.com/Textualize/textual) | TUI framework | MIT | ≥8.0 | existente |
| [Streamlit](https://github.com/streamlit/streamlit) | Web dashboard | Apache 2.0 | ≥1.58 | existente |

---

## ✅ Próximos Passos Imediatos

1. **Começar Fase 0** — é o gargalo: sem cache/router, cada pesquisa gasta ~$0.05
2. **Corrigir `aiw ask`** — está quebrado e é crítico para uso diário
3. **Instalar extensão pgvector** — `CREATE EXTENSION vector;` no homelab (one-time)
4. **Instalar Crawl4AI** — `pip install crawl4ai` + `crawl4ai-setup`
5. **Atualizar Textual** — constraint `>=8.0` para usar devtools e workers

---

## 📝 Documentos Relacionados

| Documento | Status |
|-----------|--------|
| `PLANO_AIW_V2_VALIDADO.md` (este) | ✅ Definitivo |
| [`PLANO_CODING_AGENT.md`](./PLANO_CODING_AGENT.md) | ✅ Plano do coding agent (domínio pi) |
| [`BUDGET_ENFORCEMENT.md`](./BUDGET_ENFORCEMENT.md) | ✅ Feature doc — cache, budget, circuit breaker |
| [`SKILL_SYSTEM.md`](./SKILL_SYSTEM.md) | ✅ Feature doc — pi-compatible skill workflows |
| `PLANO_FASE0_CUSTO_ZERO.md` | ✅ Detalhes de implementação |
| `PLANO_FASE1_SOURCE_RANKING.md` | 🟡 Pendente de implementação |
| `PLANO_FASE4_OBSERVABILIDADE.md` | 🟢 Pendente |
| `BUILD_LOG.md` | 🟢 Log de sessão ativo |
| `GAP_ANALYSIS_AIW_VS_PI.md` | 🟢 Tracking de feature parity |

> **Arquivados:** 12 documentos históricos → `docs/archive/`
