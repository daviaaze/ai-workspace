# AI Workspace v2 — Arquitetura Resiliente e Econômica

> ⚠️ **SUPERSEDED (2026-06-16):** Este documento foi substituído por [`PLANO_AIW_V2_VALIDADO.md`](./PLANO_AIW_V2_VALIDADO.md).
> O plano validado remove LangGraph (mantém crewAI Flows), OpenCLI, open_deep_research, A2A, Go server, NATS mesh, React. Python-only com crewAI, Crawl4AI, PostgreSQL+pgvector, MCP.
> Mantido como referência histórica das restrições de custo zero.

---

# (HISTÓRICO) AI Workspace v2 — Arquitetura Resiliente e Econômica

**Data:** 2026-06-16
**Contexto:** $0 OpenRouter, foco em features (não modelos), homelab NixOS

---

## ⚠️ Restrições Atuais

| Recurso | Status | Estratégia |
|---------|--------|------------|
| OpenRouter | $0 esgotado | Usar modelos **free tier** via API direta (Gemini free, DeepSeek barato) |
| GPU local | Lenta (38s load) | Evitar Ollama para uso interativo. Usar apenas para batches noturnos |
| Orçamento | Zero | Cache semântico + routing inteligente + ferramentas locais sem LLM |

---

## 🎯 Stack de Features

| Feature | Tecnologia | Justificativa |
|---------|-----------|---------------|
| **Busca** | Firecrawl (API/self-hosted) + Crawl4AI (local) | Markdown limpo pra LLM, JavaScript rendering |
| **Orquestração** | CrewAI Flows + LangGraph | Grafos de estado, execução durável, checkpoint |
| **Comunicação** | MCP + A2A | Protocolos padrão da indústria (Anthropic + Google + OpenAI) |
| **Swarm** | CrewAI Swarm + Handoff | Agentes com papéis, delegação hierárquica |
| **Web Scraping** | Crawl4AI + browser-use | Local, sem custo de API |
| **Deep Research** | open_deep_research + multi-step | Pesquisa iterativa com verificação |
| **Observabilidade** | Laminar (OpenTelemetry) | Tracing, custos, métricas SQL |
| **Performance/Economia** | AgentFuse + cache semântico | 70%+ redução de tokens |

---

## 🏗️ Arquitetura em Camadas

```
┌────────────────────────────────────────────────────────────┐
│                     🧑 USUÁRIO                             │
│           CLI · TUI · Web · Telegram/Slack                │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│                1️⃣  API GATEWAY (Typer/Next.js)             │
│            Roteamento · Autenticação · Rate Limit          │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│             2️⃣  COST OPTIMIZATION LAYER                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Cache        │  │ Smart Router  │  │ Circuit Breaker │  │
│  │ Semântico    │  │ (modelo mais  │  │ (orçamento por  │  │
│  │ (AgentFuse)  │  │ barato que    │  │ sessão)         │  │
│  │              │  │ resolve)      │  │                  │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│             3️⃣  ORCHESTRATOR (CrewAI Flows)                │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Planner      │  │ Supervisor   │  │ Resumability     │  │
│  │ (decompõe    │  │ (delega      │  │ (checkpoint p/   │  │
│  │ tarefas)     │  │ sub-tarefas) │  │ falhas)          │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│             4️⃣  AGENT SWARM                                 │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Research  │ │ Browser  │ │ Coder    │ │ Data Analyst │  │
│  │ Agent     │ │ Agent    │ │ Agent    │ │ Agent        │  │
│  │ (web      │ │ (browser-│ │ (FS, git,│ │ (pattern     │  │
│  │ search,   │ │ use,     │ │ shell)   │ │ recognition) │  │
│  │ scraping) │ │ scraping)│ │          │ │              │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│                                                             │
│  Comunicação: MCP (tools) + A2A (agent-to-agent)           │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│             5️⃣  TOOLS & INFRA                              │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Crawl4AI │ │ Firecrawl│ │browser-  │ │ PostgreSQL   │  │
│  │ (scraper)│ │ (search) │ │use       │ │ + pgvector   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │ Huey     │ │ NATS     │ │ Laminar  │                   │
│  │ (tasks)  │ │ (bus)    │ │(observ.) │                   │
│  └──────────┘ └──────────┘ └──────────┘                   │
└────────────────────────────────────────────────────────────┘
```

---

## 💰 Estratégia de Custo Zero

### 1. Cache Semântico (AgentFuse-like)

```python
# Cache de respostas similares usando embeddings
cache = SemanticCache(
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    similarity_threshold=0.92,
    storage=PostgresCache(connection_string=AIW_DB_URL)
)

# Antes de chamar LLM:
cached = cache.get(query)
if cached:
    return cached  # Zero custo!

# Depois de chamar LLM:
cache.set(query, response)
```

### 2. Smart Router (AgentOpt-like)

| Tipo de Tarefa | Provedor | Modelo | Custo |
|---------------|----------|--------|-------|
| Research planning | Gemini API (free) | gemini-2.5-flash | **Grátis** |
| Web scraping extraction | Crawl4AI + LLM local | qwen3:0.5b | **$0** (CPU) |
| Code generation | DeepSeek API | deepseek-chat | $0.014/100k tokens |
| Deep reasoning | DeepSeek API | deepseek-reasoner | $0.055/100k tokens |
| Simple Q&A | Cache | — | **$0** |
| Data analysis | Gemini API (free) | gemini-2.5-flash | **Grátis** |

### 3. Budget Enforcement

```python
class BudgetEnforcer:
    """Impede estouro de orçamento por sessão/período."""
    
    DAILY_BUDGET = 0.50  # $0.50/dia (DeepSeek é muito barato)
    
    def can_call(self, estimated_cost: float) -> bool:
        today_spent = self.get_today_spent()
        return (today_spent + estimated_cost) <= self.DAILY_BUDGET
    
    def log_call(self, model: str, tokens: int, cost: float):
        # Salva no PostgreSQL para consulta
        ...
```

---

## 🔄 Fluxo de Execução Resiliente

### Deep Research com fallback automático

```
1. Usuário: "Pesquise X"
2. Cache → hit? → retorna resposta cacheada
3. Gemini API (free) → planeja sub-questões
4. Para cada sub-questão:
   a. Crawl4AI + browser-use → scrape (zero custo)
   b. Extração via modelo mais barato disponível
   c. Se DeepSeek falhar → tenta Gemini free
   d. Se Gemini falhar → tenta Ollama local (lento mas grátis)
5. Síntese com Gemini free
6. Salva no cache + PostgreSQL
7. Retorna relatório
```

### Circuit Breaker por provedor

```python
circuit_breakers = {
    "deepseek": CircuitBreaker(failure_threshold=3, reset_timeout=60),
    "gemini": CircuitBreaker(failure_threshold=5, reset_timeout=30),
    "ollama": CircuitBreaker(failure_threshold=2, reset_timeout=120),
}
```

---

## 📊 Observabilidade (Laminar + OpenTelemetry)

### Métricas coletadas

| Métrica | Onde | Como |
|---------|------|------|
| Tokens por chamada | Laminar | `@observe` decorator |
| Custo por sessão | BudgetEnforcer | SQL query |
| Cache hit ratio | SemanticCache | `cache.hit_ratio` |
| Latência por provedor | OpenTelemetry | Span durations |
| Erros por agente | crewAI events | Error callbacks |
| Throughput | Huey stats | Task completion rate |

### Dashboard (Streamlit)

```python
# pages/cost_dashboard.py
st.subheader("💰 Gastos Hoje")
st.metric("Total gasto", f"${today_spent:.4f}")
st.metric("Cache hit ratio", f"{cache.hit_ratio:.1%}")
st.metric("Requisições hoje", daily_requests)
```

---

## 🧪 Plano de Implementação

### Fase 1 (Agora) — Fundação Resiliente
- [x] Cache semântico (SemanticCache)
- [x] Smart router multi-provedor
- [x] Circuit breaker com fallback
- [x] Budget enforcer

### Fase 2 — Ferramentas Locais (Custo Zero)
- [ ] Integrar Crawl4AI como ferramenta crewAI
- [ ] Integrar browser-use como ferramenta
- [ ] Configurar Firecrawl self-hosted
- [ ] Web scraping tools como MCP servers

### Fase 3 — Observabilidade
- [ ] Integrar Laminar tracing
- [ ] Dashboard de custos
- [ ] Alertas de budget

### Fase 4 — Comunicação entre Agentes
- [ ] MCP server registry
- [ ] A2A agent discovery
- [ ] Ponte MCP ↔ A2A

---

## 🔗 Referências

| Repo | Uso no projeto |
|------|---------------|
| [crewAI](https://github.com/crewAIInc/crewAI) | Agent swarm + Flows |
| [Firecrawl](https://github.com/firecrawl/firecrawl) | Web search + scraping |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | Scraping local (zero $) |
| [browser-use](https://github.com/browser-use/browser-use) | Browser agent |
| [Laminar](https://github.com/lmnr-ai/lmnr) | Observabilidade |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Ferramentas padronizadas |
| [A2A](https://github.com/a2aproject/A2A) | Comunicação entre agentes |
| [AgentFuse](https://github.com/vinaybudideti/agentfuse) | Cache semântico (inspiração) |
| [AgentOpt](https://github.com/AgentOptimizer/agentopt) | Smart routing (inspiração) |
