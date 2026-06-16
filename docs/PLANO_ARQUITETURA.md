# AI Workspace — Plano de Arquitetura Resiliente

**Data:** 2026-06-16 | **Base:** `aiw` v0.1.0 (CLI + crewAI + deep search + PostgreSQL)
**Contexto:** $0 OpenRouter · Homelab NixOS · Foco em features (não modelos)

---

## ✅ Decisões Finais (16/06/2026)

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| **Provedor principal** | DeepSeek API | Mais barato (~$0.014/M). ~700 pesquisas completas com $10 |
| **Provedor free-tier** | Google Gemini | Mantido como fallback para tarefas leves (grátis: 60 req/min) |
| **Fontes com score baixo** | 🔴 Ignorar | Economiza tokens e melhora qualidade do output |
| **Orquestração** | LangGraph | Mais maduro, state graph, durable execution, checkpoint incremental |
| **Scraping principal** | Crawl4AI | Local, $0, async, markdown limpo, JS rendering |
| **Scraping complementar** | OpenCLI | Adaptadores prontos para 70+ sites, navegação em navegador real |
| **Source tracking** | CRED-1 + tracking empírico | Seed imediato de 2.673 domínios com scores |

---

## 🧭 Visão Geral

```
Onde estamos hoje                    Onde queremos chegar
──────────────────────               ──────────────────────
CLI (Typer)                          CLI + TUI + Web + Telegram
Swarm crewAI básico                  Swarm com Flows + Grafos
Deep Search pipeline                 Deep Search + Source Ranking
Ferramentas web (fetch, browser)     Ferramentas + MCP + A2A
PostgreSQL + pgvector                + Source tracking + Cache semântico
Ollama (lento) + DeepSeek API        Smart router multi-provedor ($0)
Sem observabilidade                  Laminar + Dashboards
Zero testes (⚠️)                      Testes reais
```

---

## 🚨 Restrição Nº1: Custo Zero

| Problema | Impacto | Estratégia |
|----------|---------|------------|
| $0 OpenRouter | Sem acesso a Claude/GPT-4 | Router inteligente para APIs free/baratas |
| Ollama GPU lenta (38s) | Aguardar modelo carregar | Evitar uso interativo, apenas batch |
| Homelab sem GPU forte | Modelos locais lentos | Usar APIs externas baratas (DeepSeek ~$0.014/M tokens) |

### Provedores Disponíveis com $0

| Provedor | Modelo | Custo | Bom para |
|----------|--------|-------|----------|
| **Gemini API** (free tier) | gemini-2.5-flash | **Grátis** (60 req/min, 1500/dia) | Planejamento, síntese, Q&A |
| **DeepSeek API** (pago, barato) | deepseek-chat | ~$0.014/M input tokens | Raciocínio, código |
| **Ollama** (local, grátis) | qwen3:0.5b | **$0** (roda em CPU) | Extração simples de scraping |
| **Cache (nosso)** | resposta repetida | **$0** | Qualquer pergunta repetida |
| **Crawl4AI** (nosso, local) | scraping puro | **$0** | Coleta de dados brutos |

---

## 📦 Módulos do Sistema

```
ai_workspace/
├── agents/          → Swarm de agentes (crewAI)
├── search/          → Deep search pipeline
├── sources/         → ★ NOVO: Source reputation system
├── cost/            → ★ NOVO: Cost optimization layer
├── observability/   → ★ NOVO: Tracing + métricas
├── knowledge/       → PostgreSQL + pgvector
├── providers/       → LLM provider registry
├── tools/           → Web scraping, filesystem, git, shell
├── workflow/        → DAG engine (existente)
├── mcp_server/      → MCP server registry
├── tasks/           → Huey scheduler
├── cli.py           → CLI (Typer)
├── tui/             → Textual TUI
└── dashboard/       → Streamlit dashboard
```

---

## 📋 Escopo Macro por Feature

### 1. 🔍 Busca (Search)

**Estado atual:** Deep search com sub-questions crewAI, suporte Ollama + DeepSeek
**O que falta:**
- Integrar **Firecrawl** ou **Crawl4AI** como ferramenta de busca (Markdown limpo, JS rendering)
- Busca multi-provedor: Google Search via Gemini grounding (grátis), DuckDuckGo, Bing
- **Cache semântico** de resultados de busca (evitar re-scraping)
- **Source ranking** nas respostas (ver Escopo 5)

### 2. 🧭 Orquestração (Orchestration)

**Estado atual:** Workflow engine DAG próprio + crewAI básico
**O que falta:**
- Migrar para **crewAI Flows** (`@start`, `@listen`, `@persist`) — substitui engine DAG customizado
- **Checkpoint** automático — se falhar, retoma de onde parou
- **Guardrails** — validar output antes de prosseguir
- Structured output com **Pydantic** (substituir JSON parsing frágil)

### 3. 🗣️ Comunicação entre Agentes

**Estado atual:** Só handoff básico do crewAI
**O que falta:**
- **MCP** (Model Context Protocol) — agentes acessam ferramentas padronizadas
- **A2A** (Agent-to-Agent) — agentes descobrem e delegam tarefas entre si
- **mcp-a2a-bridge** — ponte entre os dois protocolos
- **Registro de MCP servers** (catálogo de ferramentas disponíveis)

### 4. 🐝 Agent Swarm

**Estado atual:** 5 agentes (researcher, coder, analyst, writer, planner) em crews fixas
**O que falta:**
- **Supervisor-worker** — agente coordenador delega sub-tarefas
- **Swarm dinâmico** — spawn de agentes especializados sob demanda
- **Handoff hierárquico** — agente X passa pra agente Y quando necessário
- **Memória compartilhada** entre agentes da mesma swarm

### 5. 🌐 Web Scraping

**Estado atual:** WebFetchTool + HeadlessBrowserTool + PaginatedScraperTool (custom)
**O que falta:**
- **Crawl4AI** — scraper LLM-friendly, async, markdown estruturado, JS rendering
- **browser-use** — agente de navegador real (autônomo)
- **Firecrawl self-hosted** — API de busca + scraping em escala
- **Source reputation** em todo conteúdo scrapado

### 6. 📚 Online Research (Deep Research)

**Estado atual:** Pipeline plan → research → synthesize (recursivo)
**O que falta:**
- **open_deep_research** (LangChain) — pesquisa iterativa multi-camada
- **Source ranking** em cada claim do relatório final
- **Cross-reference** — "3 fontes independentes confirmam X"
- **Relatório com confidence score por seção**

### 7. 📊 Observabilidade

**Estado atual:** Nenhuma (só logs no console)
**O que falta:**
- **Laminar** — tracing OpenTelemetry, queries SQL, custo por chamada
- **Métricas:** tokens gastos, cache hit ratio, latência por provedor
- **Dashboard de custos** (Streamlit): gasto diário, por modelo, por agente
- **Alertas** de budget (circuit breaker automático)

### 8. ⚡ Performance / Economia

**Estado atual:** $0 no bolso
**O que falta:**
- **Cache semântico** (AgentFuse-like) — ~70% redução de tokens
- **Smart router** (AgentOpt-like) — cada tarefa usa o modelo mais barato que resolve
- **Circuit breaker** por provedor — se falha, tenta próximo
- **Budget enforcer** — limite diário de gasto

### 9. ⭐ Sistema de Reputação de Fontes (★ NOVO)

**Estado atual:** Não existe
**O que precisa:**
- **Domain-level:** seed com CRED-1 (2.673 domínios com score) + CrediNet API
- **Tracking empírico:** acurácia histórica por fonte
- **Cross-reference:** quanto mais fontes concordam, maior o score
- **User feedback:** `aiw source flag <url> --bad` + TUI
- **Output:** semáforo verde/amarelo/vermelho por fonte no relatório

---

## 🗺️ Roadmap por Fases

```
FASE 0 — CUSTO ZERO (1-2 semanas) ← CRÍTICO
┌────────────────────────────────────────────────────────────────┐
│ □ Cache semântico (reduz ~70% das chamadas)                   │
│ □ Smart router multi-provedor (DeepSeek principal + Gemini free)│
│ □ Budget enforcer (limite diário em $)                         │
│ □ Circuit breaker com fallback (DeepSeek → Gemini → cache)     │
│ □ DeepSeek API configurado como provedor PADRÃO                │
│ □ Gemini API free tier como fallback GRÁTIS                    │
│ □ OpenRouter removido da configuração padrão (só se quiser)    │
│                                                                │
│ Meta: Custo médio por pesquisa = $0.001                        │
└────────────────────────────────────────────────────────────────┘

FASE 1 — QUALIDADE DAS FONTES (1-2 semanas)
┌────────────────────────────────────────────────────────────────┐
│ □ Source tracking database (PostgreSQL)                        │
│ □ CRED-1 dataset integrado (2.673 domínios com scores)         │
│ □ CrediNet API integrada (fallback de classificação)           │
│ □ Cross-reference scoring (fontes que concordam)               │
│ □ User feedback: aiw source flag <url> --bad                  │
│ □ Assessment por fonte no relatório                            │
│ □ 🔴 Ignorar fontes com score < threshold (economiza tokens)   │
│ □ OpenCLI adapters para fontes conhecidas (ex: arXiv, HN)      │
│                                                                │
│ Meta: 100% das fontes com score de credibilidade               │
└────────────────────────────────────────────────────────────────┘

FASE 2 — AGENTES + ORQUESTRAÇÃO (2-3 semanas)
┌────────────────────────────────────────────────────────────────┐
│ □ LangGraph: state graph da aplicação                          │
│ □ LangGraph: durable execution + checkpoint incremental        │
│ □ LangGraph: supervisor-worker pattern                         │
│ □ LangGraph: human-in-the-loop (aprovação antes de ações)      │
│ □ Pydantic structured output (substituir JSON parsing frágil)  │
│ □ Guardrails por tarefa (validação de output)                  │
│ □ Swarm dinâmico (spawn de agentes sob demanda)                │
│ □ open_deep_research integrado como nó do grafo                │
│ □ Memória compartilhada entre agentes                          │
│                                                                │
│ Meta: Pipeline resiliente com auto-recuperação em falhas       │
└────────────────────────────────────────────────────────────────┘

FASE 3 — SCRAPING + FERRAMENTAS (1-2 semanas)
┌────────────────────────────────────────────────────────────────┐
│ □ Crawl4AI como ferramenta principal de scraping               │
│ □ OpenCLI como ferramenta complementar (70+ sites adaptados)   │
│ □ browser-use como agente de navegador autônomo                │
│ □ MCP server registry (ferramentas padronizadas)               │
│ □ MCP tools expostas como nós do LangGraph                     │
│ □ A2A protocol (comunicação entre agentes)                     │
│ □ mcp-a2a-bridge (ponte entre protocolos)                      │
│                                                                │
│ Meta: Scraping em qualquer site sem depender de API externa    │
└────────────────────────────────────────────────────────────────┘

FASE 4 — OBSERVABILIDADE (1 semana)
┌────────────────────────────────────────────────────────────────┐
│ □ Laminar tracing (@observe em chamadas LLM + LangGraph)       │
│ □ Custo por pesquisa armazenado no PostgreSQL                  │
│ □ Dashboard de custos (Streamlit): gasto diário, por modelo    │
│ □ Cache hit ratio monitorado                                   │
│ □ Alertas de budget excessivo                                  │
│                                                                │
│ Meta: Saber exatamente onde cada centavo é gasto               │
└────────────────────────────────────────────────────────────────┘

FASE 5 — TESTES + DEPLOY (contínuo)
┌────────────────────────────────────────────────────────────────┐
│ □ Testes de unidade para cada módulo novo                      │
│ □ Testes de integração (DB real)                               │
│ □ CI/CD no GitHub Actions                                      │
│ □ NixOS module atualizado                                      │
│ □ Documentação atualizada                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Dependências Externas

| Ferramenta | Uso | Licença | Fase |
|-----------|-----|---------|------|
| [DeepSeek API](https://platform.deepseek.com/) | Provedor PRINCIPAL | Pago (~$0.014/M) | Fase 0 |
| [Gemini API](https://ai.google.dev/) | Fallback FREE | Grátis (60 req/min) | Fase 0 |
| [CRED-1](https://github.com/aloth/cred-1) | Source credibility dataset | CC BY 4.0 | Fase 1 |
| [CrediNet](https://github.com/credi-net/CrediNet) | Domain credibility | CC BY 4.0 | Fase 1 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Orquestração stateful | MIT | Fase 2 |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | Web scraping local | Apache 2.0 | Fase 3 |
| [OpenCLI](https://github.com/jackwener/OpenCLI) | Scraping via adapters (70+ sites) | MIT | Fase 3 |
| [browser-use](https://github.com/browser-use/browser-use) | Browser agent | MIT | Fase 3 |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Ferramentas padronizadas | MIT | Fase 3 |
| [Laminar](https://github.com/lmnr-ai/lmnr) | Observabilidade | Apache 2.0 | Fase 4 |

---

## 📈 Métricas de Sucesso

| Métrica | Atual | Meta | Como medir |
|---------|-------|------|------------|
| Custo por pesquisa | ~$0.05 (OpenRouter) | **$0.001** (cache + routing) | Laminar |
| Cache hit ratio | 0% | **>60%** | Métrica do cache |
| Fontes com score no relatório | 0% | **100%** | Output do Source Reputation |
| Test coverage | ~5% | **>70%** | pytest-cov |
| Tempo de resposta (pesquisa simples) | ~2min | **<30s** | CLI + Laminar |

---

## ✅ Decisões Tomadas (16/06/2026)

| Decisão | Escolha |
|---------|--------|
| **Provedor principal** | ✅ DeepSeek (pago, barato) |
| **Provedor free-tier fallback** | ✅ Gemini API (grátis) |
| **Fontes com score baixo** | ✅ 🔴 Ignorar (economiza tokens) |
| **Orquestração** | ✅ LangGraph (longo prazo) |
| **Scraping principal** | ✅ Crawl4AI |
| **Scraping complementar** | ✅ OpenCLI (70+ sites adaptados) |
| **Source tracking** | ✅ CRED-1 + tracking empírico |

---

## 🔗 Próximos Passos

1. Você revisa e aprova esse plano
2. Ajustamos escopo e prioridades
3. Começamos pela **Fase 0** (cache + routing + budget) — crítico por causa do $0
4. Ou pela **Fase 1** (Source Reputation) — se qualidade é prioridade máxima

Qual caminho você quer seguir?

## 📐 Documentos de Especificação

| Documento | Conteúdo |
|-----------|----------|
| [SCHEMA_DB.md](./SCHEMA_DB.md) | ⭐ **Arquitetura completa das tabelas** — diagrama, relacionamentos FK, fluxo de dados, índices, tamanho estimado |
| [PLANO_FASE0_CUSTO_ZERO.md](./PLANO_FASE0_CUSTO_ZERO.md) | Cache semântico, smart router, budget enforcer, circuit breaker |
| [PLANO_FASE1_SOURCE_RANKING.md](./PLANO_FASE1_SOURCE_RANKING.md) | CRED-1, domain reputation, cross-reference, score composto |
| [PLANO_FASE2_LANGGRAPH.md](./PLANO_FASE2_LANGGRAPH.md) | StateGraph, supervisor, durable execution, human-in-the-loop |
| [PLANO_FASE3_SCRAPING.md](./PLANO_FASE3_SCRAPING.md) | Crawl4AI, OpenCLI, browser-use, MCP, A2A |
| [PLANO_FASE4_OBSERVABILIDADE.md](./PLANO_FASE4_OBSERVABILIDADE.md) | Laminar tracing, dashboard de custos, logs estruturados |
| [PLANO_FASE5_TESTES_DEPLOY.md](./PLANO_FASE5_TESTES_DEPLOY.md) | Pirâmide de testes, mocks, CI/CD, deploy automático |
