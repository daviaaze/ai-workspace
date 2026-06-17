# 📊 AI Workspace — Auditoria Completa de Documentação & Features

> **Data:** 2026-06-17 | **Status:** Report gerado por pi, com scan automático + análise manual
> **Arquivos analisados:** 28 documentos (16 ativos + 12 archive) + 58 arquivos de código + 26 arquivos de teste

---

## 🏥 HEALTH SCORE: 54/100

| Dimensão | Score | Notas |
|----------|-------|-------|
| Documentação estrutural | 🟢 88/100 | docs-keeper scan |
| Consistência doc ↔ código | 🟡 52/100 | Vários docs declaram features implementadas que não estão |
| Requisitos capturados | 🔴 30/100 | Inúmeros requisitos implícitos sem doc |
| Features completas | 🔴 35/100 | Só ~35% do roadmap está realmente feito |
| Testes de integração | 🟡 47/100 | 379 unit tests, mas testes E2E não existem |

---

## 📋 SUMÁRIO EXECUTIVO

O projeto tem **documentação extensa e bem estruturada** — mas **desconectada da realidade do código**. O resultado: um plano macro (PLANO_AIW_V2_VALIDADO) que declara Fase 0 como "✅ Feita" quando na verdade só ~60% dela funciona. As fases 1, 2, 3, 4 e 5 têm docs detalhados mas implementação zero ou fragmentada.

O projeto tenta ser um **everything agent** (CLI, TUI, Dashboard, MCP, pesquisa, cache, budget, fontes, scraping, coding), mas ainda é um **early prototype** — você não consegue rodar um `aiw search` completo com source filtering, cache, e budget enforcement de ponta a ponta.

**Recomendação principal: parar de planejar Features D+E e fechar Feature A até o fim.**

---

## 🔴 PARTE 1 — Features que NÃO FUNCIONAM (ou são só casca)

### 1.1 Declaradas "✅ DONE" mas quebradas ou inacabadas

| Feature | O doc diz | A realidade | Gravidade |
|---------|-----------|-------------|-----------|
| **Semantic Cache (Fase 0)** | "✅ Feito: embedding dual, HNSW index" | Código existe em `core/cost.py` mas o `SemanticCache` **não está integrado ao `search/deep_search.py`** — `_cached_kickoff()` existe mas toda cache lookup usa embedding do Ollama que pode não estar rodando | 🔴 ALTA |
| **Source Reputation (Fase 1)** | "✅ Feito: CRED-1 seed, composite scoring, filter no deep_search" | Schema criado em `core/sources.py`, modelo em `sources/models.py`, mas **CrediNet NUNCA foi instalado** (`credigraph` não está no pyproject.toml nem pip-installed), **cross-reference scoring NÃO está implementado**, e o **filter_sources()** no deep_search é um pseudo-código com placeholder | 🔴 ALTA |
| **Budget Enforcer** | "✅ Implementado: 3 camadas, 40 tests" | Código existe e os testes passam. Mas não está claro se o budget limita chamadas **na prática** — o `deep_search.py` tem check mas a Stack de pesquisa real não é testada E2E | 🟡 MÉDIA |
| **Smart Router** | "✅ Implementado: matriz de roteamento" | Existe `agents/router.py` (297 linhas) mas está **hardcoded para Ollama local** — não usa DeepSeek/Gemini como descrito no doc. A matriz de roteamento real (DeepSeek → Gemini) só existe no doc | 🔴 ALTA |
| **MCP Integration** | "⚠️ PARCIAL: 11 tools expostas" | `mcp_server/server.py` tem 722 linhas — é o MCP server mais completo. Mas o doc diz que o aiw deve CONSUMIR MCP tools também (FastMCP clients), e isso **não existe** | 🟡 MÉDIA |
| **Dashboard Streamlit** | "✅ Funciona" | Tem `dashboard/app.py` mas é uma página simples, NÃO tem dashboard de custos, cache hit ratio, nem gráficos de gasto por modelo como o doc da Fase 4 promete | 🟡 MÉDIA |
| **TUI v2 (redesign)** | "✅ Completamente redesenhado" | O doc `TUI_REDESIGN_v2.md` descreve um layout completamente novo (HeaderBar, DashboardView, GitPanel, 7 tabs). O código do TUI (`tui/app.py`) existe, mas o **snapshot do layout atual não foi verificado** — parece que o v2 é um DESIGN, não uma implementação | 🔴 ALTA |
| **Skill System** | "✅ Feito: 13 skills" | `skills/loader.py` existe, mas as skills (debug, feature-dev, commit, etc.) rodam de verdade? O doc `SKILL_SYSTEM.md` diz que sim, mas não há testes de integração de skills | 🟡 MÉDIA |
| **Crawl4AI scraping** | "❌ Novo (Fase 3)" vs doc principal | O `PLANO_AIW_V2_VALIDADO.md` diz ❌ novo, mas o código `tools/crawl4ai.py` (89 linhas) **já existe** e `tools/scraping_chain.py` (114 linhas) já implementa a hierarquia web_fetch → crawl4ai → headless → browser. Está no pyproject.toml como `[scrape]`. **Inconsistência de status** | 🟡 MÉDIA |
| **Diff Edit + Auto-Fix** | "Blocos 2 e 3 do coding agent" | `tools/diff_edit.py` (340 linhas) e `tools/auto_fix.py` (484 linhas) **já existem com código funcional**. Testes existem em `test_tools/test_auto_fix.py` (18 testes). Mas o `PLANO_CODING_AGENT.md` diz que são blocos ⬜ (não implementados) | 🟡 MÉDIA |
| **Code Review Graph** | "Integrar (30 min)" | `tools/code_graph.py` existe. Mas doc diz pra copiar extensão do pi — **não sabemos se foi feito** | 🟡 MÉDIA |
| **AgentOrchestrator** | "✅ Pipeline unificado" | Tem `agents/orchestrator.py` (1036 linhas). Impressionante para algo que era "Fase 2". Mas está realmente integrado com TUI, CLI, e Dashboard? Os testes só tem 17 funções. | 🟡 MÉDIA |

### 1.2 Declaradas "❌ MISSING" ou "PENDENTE" — e seguem pendentes

| Feature | Doc status | Bloqueado por |
|---------|-----------|---------------|
| **MCP client-side (consumir tools externas)** | ❌ MISSING no GAP | Ausência de FastMCP client |
| **Laminar tracing real** | "Fase 4: Novo" | `lmnr` importado em `observability/__init__.py` mas NÃO está no pyproject.toml. API key não configurada. Não está roteando spans reais |
| **structlog em produção** | "Fase 4" | `observability/__init__.py` usa `structlog.dev.ConsoleRenderer()` em vez de `JSONRenderer()` — ou seja, logs NÃO são estruturados |
| **Alertas de budget** | "Fase 4: Novo" | Não existe código de alerta (WARNING a $0.50/dia, etc.) |
| **Multi-agent delegation (`delegate()` tool)** | ❌ PENDENTE (GAP Phase 8) | Sem código |
| **TUI state persistence** | ❌ PENDENTE | Sem código |
| **Web dashboard polish** | ❌ PENDENTE | Dashboard é uma única página simples |
| **Web search API creds** | ❌ PENDENTE | Sem DeepSeek credits |
| **Agent swarm (supervisor-worker)** | ❌ PENDENTE | Só existe supervisor agent no deep_search, não swarm genérico |
| **CI/CD GitHub Actions** | "Fase 5: Novo" | `.github/` existe mas provavelmente sem workflow |
| **Laminar dashboard próprio** | "Fase 4: Novo" | Não implementado |
| **Cross-reference scoring** | "Fase 1: 🟡 Pendente" | Tabela existe, lógica não |
| **crewAI shared memory** | "Fase 2: 🟡 Pendente" | Não integrada |
| **CrediNet** | "Fase 1: 🟡 Pendente" | `credigraph` não instalado |

---

## 📐 PARTE 2 — Requisitos Escondidos (não capturados em docs)

Estes são requisitos implícitos encontrados analisando código e docs — nunca foram explicitamente documentados como "a fazer":

### 2.1 Da análise do código

| # | Requisito oculto | Onde foi inferido | Impacto |
|---|-----------------|-------------------|---------|
| H1 | **Ollama como provedor PRIMÁRIO, não DeepSeek** — `SmartRouter` está hardcoded para Ollama local, apesar do plano validado dizer que DeepSeek é principal. O router não sabe rotear pesquisa → deepseek, extração → gemini free como o doc promete | `agents/router.py:1-50` | 🔴 ALTA — se Ollama cair ou não tiver GPU, tudo quebra |
| H2 | **Semantic Cache depende de Ollama estar rodando** — o embedding primário é `nomic-embed-text` via Ollama. Se Ollama cair, o fallback é `sentence-transformers` mas o código não fallbacka automaticamente | `core/cost.py:SemanticCache` | 🔴 ALTA — cache é a camada 1, se ela quebrar o custo dispara |
| H3 | **Não existe tratamento de rate-limit do Gemini** — o doc da Fase 0 promete Gemini free tier como fallback, mas o código não tem lógica de rate-limit (60 req/min, 1500/dia) | Ausência em `agents/router.py` e `providers/__init__.py` | 🟡 MÉDIA |
| H4 | **`aiw ask` está funcionando mas ainda depende do Ollama** — a correção do timeout resolveu o path `/api/chat`, mas não há fallback para DeepSeek/Gemini se Ollama não estiver disponível | `providers/__init__.py` | 🟡 MÉDIA |
| H5 | **O `deep_search` tem 7 ferramentas registradas mas NENHUMA é testada em integração** — web_fetch, headless_browser, paginated_scraper, crawl4ai, mercado_livre, olx, code_search. Todas registradas, mas o fluxo real (pesquisa → scrape → filter → synthesize) nunca foi testado E2E | `search/deep_search.py` | 🔴 ALTA |
| H6 | **Não existe health check dos providers** — o doc da Fase 0 descreve `health = {"deepseek": {"status": "up"|"down", ...}}`. Isso não está implementado | Ausência no código | 🟡 MÉDIA |
| H7 | **Cache invalidation NÃO é automática** — o doc promete TTL de 7/1/30 dias com limpeza, mas o `cleanup_expired(30)` é manual e está em `core/cost.py`. Não há cron/task rodando isso | `core/cost.py:SemanticCache` | 🟡 MÉDIA |
| H8 | **Seed CRED-1 foi feito mas não há task Huey de atualização semanal** — o doc da Fase 1 promete "toda segunda-feira às 06:00". O script `knowledge/seed.py` existe mas não está agendado | `tasks/scheduler.py` | 🟡 MÉDIA |
| H9 | **TUI não é testável em CI** — 15 testes de TUI, mas todos pulados no CI (precisam de terminal). A cobertura real do TUI é ~0% | `test_tui/test_app.py` | 🟡 MÉDIA |
| H10 | **Browser agent depende de Nix flake customizado** — `browser-use` empacotado em `flake.nix`, mas se a derivação quebrar em atualização do nixpkgs, o agente perde navegação autônoma | `flake.nix`, `tools/browser_agent.py` | 🟡 MÉDIA |
| H11 | **Connection pool é ThreadedConnectionPool mas NÃO tem health check/reconnect** — se o PostgreSQL cair e voltar, o pool não reconecta automaticamente | `core/db.py` | 🔴 ALTA |
| H12 | **Não há testes E2E de NENHUM fluxo**: search completo, cache → LLM → report, TUI spawn agent → executa → retorna, etc. | Ausência em `tests/` | 🔴 ALTA |

### 2.2 Dos docs que descrevem features sem estimativa de esforço

| # | Requisito oculto | Doc fonte | Esforço estimado |
|---|-----------------|-----------|-----------------|
| H13 | **Gemini free tier integration real** — chamar API do Gemini, tratar rate-limit, fallback do DeepSeek | Fase 0 §2.2 | 2-3 dias |
| H14 | **Health check dashboard em tempo real** — status dos providers, cache hit ratio ao vivo | Fase 0 §2.3 | 1 dia |
| H15 | **Hierarquia de scraping completa** — WebFetchTool → Crawl4AI → HeadlessBrowser → browser-use com fallback automático | Fase 3 §3.5 | 3-4 dias |
| H16 | **Laminar self-hosted** — deploy do Laminar (Rust binary + PostgreSQL), não só o client Python | Fase 4 §2 | 2 dias |
| H17 | **Prometheus + OpenTelemetry metrics** — doc da Fase 4 menciona mas zero código | Fase 4 §1 | 3-5 dias |
| H18 | **Streamlit dashboard completo** — página de custos, cache, fontes, agentes, pesquisa. Doc da Fase 4 descreve 4 cards + 2 gráficos + tabela | Fase 4 §3.2 | 2-3 dias |
| H19 | **CI/CD pipeline** — lint (ruff), type check (mypy), tests (pytest --cov), deploy hook. Não implementado | Fase 5 §5.4 | 1-2 dias |
| H20 | **`.aiwrules` auto-injection no pi** — o doc `PLANO_CODING_AGENT.md` Bloco 4 descreve a extensão pi que injeta `.aiwrules` no system prompt. A extensão `.ts` não foi verificada | Bloco 4 §4.4 | 2-3 horas |

---

## 🗂️ PARTE 3 — Problemas de Documentação

### 3.1 Inconsistências doc ↔ doc

| # | Problema | Docs envolvidos |
|---|----------|----------------|
| D1 | **GAP_ANALYSIS diz que MCP é "MISSING" (status antigo "❌") mas depois corrige pra "⚠️ PARCIAL"** — confuso, o leitor não sabe o status real | `GAP_ANALYSIS_AIW_VS_PI.md` tabela #10 |
| D2 | **PLANO_AIW_V2 diz "Fase 0: 100% ✅ Feito"**, mas várias sub-tarefas da Fase 0 ainda estão pendentes (Gemini integration, health check, cache cleanup automático, rate-limit) | `PLANO_AIW_V2_VALIDADO.md` §FASE 0 |
| D3 | **PLANO_AIW_V2 diz "Fase 1: 1.3 CrediNet 🟡 Pendente", "1.5 Cross-ref 🟡 Pendente"**, mas na seção de métricas da Fase 1 o doc declara "Fontes com score: 100%" como meta já batida — mas cross-ref não funciona | `PLANO_AIW_V2_VALIDADO.md` §FASE 1 |
| D4 | **PLANO_CODING_AGENT.md diz que Diff Edit (Bloco 2) e Auto-Fix (Bloco 3) são ⬜ (não implementados)**, mas o código `tools/diff_edit.py` (340 linhas) e `tools/auto_fix.py` (484 linhas) já existem com testes. Ou o doc está desatualizado, ou o código é placeholder | `PLANO_CODING_AGENT.md` vs `tools/diff_edit.py` + `tools/auto_fix.py` |
| D5 | **BUDGET_ENFORCEMENT.md diz que `_cached_kickoff()` está no `deep_search.py`**, mas o deep_search tem lógica de cache/budget **diferente** do que o doc descreve. O doc mostra fluxo com `cache.get()` → `router.select_model()` → `budget.can_call()`, mas o código não segue essa ordem | `BUDGET_ENFORCEMENT.md` vs `search/deep_search.py` |
| D6 | **TOOLS_RESEARCH_REPORT.md (Abril 2026) recomenda browser-use self-hosted como "primary"**, mas o PLANO_AIW_V2_VALIDADO (Junho 2026) decide Crawl4AI como principal e browser-use como fallback. Report desatualizado | `TOOLS_RESEARCH_REPORT.md` vs `PLANO_AIW_V2_VALIDADO.md` |
| D7 | **README.md diz "318 tests, 0 failures"**, mas rodamos `grep` agora e tem 379 tests. E o BUILD_LOG diz 278 tests. 3 números diferentes! | `README.md`, `BUILD_LOG.md`, contagem real |
| D8 | **PLANO_FASE0_CUSTO_ZERO.md detalha uma tabela `cost_log` com campos específicos**, mas o `BUDGET_ENFORCEMENT.md` descreve uma versão diferente. Precisa consolidar | `PLANO_FASE0` vs `BUDGET_ENFORCEMENT` |

### 3.2 Convenções de nomenclatura quebradas

| Arquivo | Problema | Sugestão |
|---------|----------|----------|
| `SEARCH_KNOWLEDGE_FORMAT_REQUIREMENT.md` | Sem prefixo reconhecido | `REQUIREMENT_SEARCH_KNOWLEDGE_FORMAT.md` ou `FEATURE_SEARCH_KNOWLEDGE.md` |
| `TUI_REDESIGN_v2.md` | Sem prefixo, mistura design + status | `PLANO_TUI_V2.md` ou `FEATURE_TUI_V2.md` |
| `TOOLS_RESEARCH_REPORT.md` | Prefixo `TOOLS_` não está na convenção | `RESEARCH_TOOLS.md` |

### 3.3 Docs órfãos ou redundantes

| Arquivo | Situação |
|---------|----------|
| `archive/PLANO_ARQUITETURA.md` | Tem `⚠️ ATUALIZADO` no header mas está no archive — inconsistente. O conteúdo fala de LangGraph como se ainda fosse opção |
| `archive/PLANO_FASE3_SCRAPING.md` | Diz `⚠️ ATUALIZADO` mas menciona OpenCLI como se ainda estivesse no escopo |
| `archive/PLANO_FASE2_LANGGRAPH.md` | Corretamente marcado SUPERSEDED ✅ |
| `archive/IMPROVEMENT_PLAN.md` | Lista 15+ itens como "todo" que já foram feitos. Devia ser atualizado ou arquivado com status final |
| `archive/SCHEMA_DB.md` | Descreve tabelas que podem estar desatualizadas vs o schema atual. Se o schema real está no código, este doc é redundante |

---

## 🎯 PARTE 4 — Proposições: O Que Fazer Agora

### 4.1 PRIORIDADE 0 — Fechar a Fase 0 de Verdade (1-2 semanas)

A Fase 0 é o **gargalo existencial**: sem cache real + router funcional, cada pesquisa gasta ~$0.05 e o custo escala linearmente. O doc declara "✅ Feito" mas **não está**.

| # | Ação | Esforço | Bloqueia |
|---|------|---------|----------|
| P0.1 | **Consertar o SmartRouter pra usar DeepSeek como principal e Gemini como fallback** — não Ollama. O router atual é um mock que só sabe Ollama. Implementar a matriz de roteamento do doc da Fase 0 | 2 dias | Tudo que depende de LLM pago |
| P0.2 | **Integrar SemanticCache de verdade no deep_search** — hoje o código de cache existe mas não é chamado no fluxo real de pesquisa. Garantir que antes de cada chamada LLM o cache é consultado | 1 dia | Economia de custo |
| P0.3 | **Adicionar fallback automático sentence-transformers quando Ollama não está disponível** — o cache não pode depender de GPU/Ollama | 0.5 dia | Resiliência do cache |
| P0.4 | **Implementar tratamento de rate-limit do Gemini** — 60 req/min, 1500/dia. Se estourar, fallback pra DeepSeek | 1 dia | Gemini como fallback real |
| P0.5 | **Teste E2E: `aiw search "algo"` → cache miss → DeepSeek → resposta → cache salva** | 1 dia | Confiança no sistema |
| P0.6 | **Health check automático dos providers** — status up/down, latência, tokens usados hoje | 0.5 dia | Debug de falhas |

**Métrica de saída:** Rodar `aiw search` 10x com a mesma query e ver cache hit ≥ 60%.

---

### 4.2 PRIORIDADE 1 — Completar Source Reputation (1 semana)

| # | Ação | Esforço |
|---|------|---------|
| P1.1 | **Instalar `credigraph` e integrar como fallback do CRED-1** | 0.5 dia |
| P1.2 | **Implementar cross-reference scoring** — o algoritmo está descrito em `PLANO_FASE1_SOURCE_RANKING.md §6.2`, só precisa codar | 2 dias |
| P1.3 | **Agendar atualização semanal do CRED-1 via Huey** | 0.5 dia |
| P1.4 | **Integrar `filter_sources()` de verdade no deep_search** | 1 dia |
| P1.5 | **Teste E2E: pesquisa com fontes de baixa qualidade são filtradas** | 1 dia |

---

### 4.3 PRIORIDADE 2 — Documentation Cleanup (2-3 dias)

| # | Ação | Esforço |
|---|------|---------|
| P2.1 | **Atualizar GAP_ANALYSIS com status REAL de cada feature** — auditar código e corrigir ✅/⚠️/❌ | 3 horas |
| P2.2 | **Atualizar README.md** — número de testes, stack atual, roadmap realista | 1 hora |
| P2.3 | **Unificar descrição do schema de custo** — consolidar `PLANO_FASE0` + `BUDGET_ENFORCEMENT` em um doc único | 2 horas |
| P2.4 | **Criar docs faltantes para features implementadas** (docs-keeper flag 5 gaps):
  - `FEATURE_INTERACTIVE_SESSION.md` — MessageQueue + AgentWorker
  - `FEATURE_PERMISSION_SYSTEM.md` — PermissionGate + PermissionModal
  - `FEATURE_CONTEXT_AWARENESS.md` — ContextBundle + ContextManager + Workbench
  - `FEATURE_MODEL_FALLBACK.md` — SmartRouter + retry
  - `FEATURE_SEMANTIC_CACHE.md` — pgvector HNSW cache | 2 dias |
| P2.5 | **Atualizar PLANO_CODING_AGENT.md** — Blocos 2 e 3 têm código! Corrigir status | 1 hora |
| P2.6 | **Mover docs do archive que estão ATUALIZADO para active/** — ou atualizar o status neles | 1 hora |
| P2.7 | **Renomear docs sem convenção** — `SEARCH_KNOWLEDGE_FORMAT_REQUIREMENT.md` → `REQUIREMENT_SEARCH_KNOWLEDGE.md`, `TUI_REDESIGN_v2.md` → `PLANO_TUI_V2.md` | 15 min |
| P2.8 | **Consolidar arquivos de plano de fase** — `PLANO_FASE0/1/4` têm 90% de overlap com `PLANO_AIW_V2_VALIDADO.md`. Manter os planos detalhados como referência ou mesclar. Decisão: mesclar tudo no master plan, deletar duplicados | 3 horas |

---

### 4.4 PRIORIDADE 3 — Testes que Faltam (2 semanas)

| # | Ação | Esforço |
|---|------|---------|
| P3.1 | **Teste E2E do fluxo de pesquisa completo** — `aiw search` com mock de LLM + DB real. Validar cache, budget, source filter, report | 2 dias |
| P3.2 | **Testes de integração do source reputation** — CRED-1 seed, CrediNet fallback, scoring | 1 dia |
| P3.3 | **Testes de integração do scraping chain** — web_fetch → crawl4ai → headless → browser | 1 dia |
| P3.4 | **Teste E2E do TUI** — spawn agent, ver output, send message, verify response. Usar `pytest-textual-snapshot` ou headless mode | 2 dias |
| P3.5 | **Testes de resiliência** — DB cai e volta, Ollama cai, DeepSeek falha 3x → circuit breaker abre. Simular falhas | 2 dias |
| P3.6 | **CI/CD no GitHub Actions** — lint + type check + tests em PR | 1 dia |

---

### 4.5 PRIORIDADE 4 — Features Novas (3-4 semanas, apenas depois das prioridades acima)

Só começar estas depois que Fase 0 e Fase 1 estiverem 100% completas e testadas:

| # | Feature | Esforço |
|---|---------|---------|
| P4.1 | **Laminar tracing real** — self-hosted + integrar no deep_search e agent worker | 3 dias |
| P4.2 | **Dashboard de custos completo** (Streamlit) — cache hit ratio, gasto por modelo, gráficos | 2 dias |
| P4.3 | **MCP client tools** — agentes crewAI consumindo MCP tools externas | 3 dias |
| P4.4 | **Multi-agent delegation** — `delegate()` tool no AgentOrchestrator | 3 dias |
| P4.5 | **TUI state persistence** — restaurar lanes/outputs ao reabrir | 2 dias |
| P4.6 | **Agent swarm supervisor-worker** | 4 dias |

---

## 📊 PARTE 5 — Métricas e Riscos

### 5.1 Métricas atuais vs declaradas

| Métrica | Doc declara | Realidade | Gap |
|---------|-------------|-----------|-----|
| Cache hit ratio | "≥ 60%" (meta Fase 0) | **0%** (não integrado) | 🔴 |
| Custo por pesquisa | "≤ $0.001" (meta Fase 0) | **~$0.05** (sem cache/router real) | 🔴 |
| Fontes com score | "100%" (meta Fase 1) | **~30%** (só CRED-1 seed, sem CrediNet, sem cross-ref) | 🔴 |
| Pesquisas com checkpoint | "100%" (meta Fase 2) | **0%** (não implementado) | 🔴 |
| Test coverage | "≥ 70%" (meta Fase 5) | **~29%** (BUILD_LOG) | 🟡 |
| Tempo médio de pesquisa | "< 1min" (meta Fase 2) | **~2min** (medido a dedo, sem tracing) | 🟡 |

### 5.2 Riscos principais

| Risco | Prob | Impacto | Mitigação |
|-------|------|---------|-----------|
| **Ollama cair e todo o sistema parar** | Média | 🔴 Crítico | P0.1 — implementar fallback DeepSeek/Gemini |
| **Burst de pesquisas sem cache = $10-$50 gastos em minutos** | Média | 🔴 Crítico | P0.2 — integrar cache antes de qualquer LLM call |
| **PostgreSQL reiniciar e agent quebrar sem reconectar** | Baixa | 🔴 Crítico | P0.6 — health check + reconnect no pool |
| **CRED-1 desatualizado, fontes de misinformation passando** | Média | 🟡 Médio | P1.1 + P1.2 — CrediNet + cross-ref |
| **Gemini rate-limit não tratado → loop infinito de retry** | Alta | 🟡 Médio | P0.4 |
| **DeepSeek API key não configurada → sistema usa só Ollama** | Alta | 🟡 Médio | P0.1 — health check + fallback chain |

---

## ✅ PARTE 6 — Plano de Ação (Ordem de Execução)

```
SEMANA 1-2: Fechar Fase 0 de verdade
  ├── Dia 1-2: P0.1 (SmartRouter DeepSeek+Gemini real)
  ├── Dia 3:   P0.2 + P0.3 (Cache integration + fallback embedding)
  ├── Dia 4:   P0.4 (Gemini rate-limit)
  ├── Dia 5:   P0.5 (Teste E2E search)
  └── Dia 6:   P0.6 (Health check)

SEMANA 3: Completar Fase 1
  ├── Dia 1:   P1.1 (credigraph)
  ├── Dia 2-3: P1.2 (cross-reference scoring)
  ├── Dia 4:   P1.3 + P1.4 (Huey schedule + filter_sources)
  └── Dia 5:   P1.5 (Teste E2E source filter)

SEMANA 4: Documentation cleanup
  ├── Dia 1-2: P2.1-P2.8 (atualizar todos os docs)
  └── Dia 3-5: P3.1-P3.6 (testes E2E + CI/CD)

SEMANA 5+: Novas features (só depois do básico funcionar)
```

---

## 📝 Resumo: 3 Coisas Que Precisam Acontecer HOJE

1. **Parar de declarar features como "✅ DONE" quando o código não está integrado** — cache, router, source filter são exemplos. O doc passou na frente do código.

2. **Escolher UMA feature e levar até o fim** — hoje o projeto tem 15 features "quase prontas". Melhor ter 3 que funcionam 100% (pesquisa com cache + budget + source filter) do que 15 que funcionam 50%.

3. **Fazer UM teste E2E** — `aiw search "tema qualquer"`, rodar de verdade, ver o output. Se quebrar no meio (cache miss, Ollama offline, fonte não filtrada), consertar. Depois automatizar.

---

> **Gerado por:** pi (coding agent), via docs-keeper skill v2 + análise manual de 28 docs + 58 arquivos de código.
> **Próximo passo:** Revisar este report com o humano e definir prioridades.
