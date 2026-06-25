# Análise Profunda: Projetos Externos vs ai-workspace

> **Data:** 2026-06-25
> **Fontes:** HKUDS/DeepTutor, volcengine/OpenViking, context-labs/HALO, Tracer-Cloud/OpenSRE, santifer/career-ops
> **Objetivo:** Extrair padrões, arquiteturas e ideias implementáveis no aiw

---

## Sumário Executivo

| Projeto | Stars | Licença | Stack | Maturidade | O que tem de único |
|---------|-------|---------|-------|------------|-------------------|
| **DeepTutor** | 20k+ | Apache 2.0 | Python + Next.js | v1.4.12 (jun/26) | Persistent Memory L1/L2/L3, Partners com SOUL.md, Multi-engine RAG |
| **OpenViking** | 26k | AGPL-3.0 | Python + Rust | Alpha | Context DB como filesystem, tiered loading L0/L1/L2, retrieval trajectories |
| **HALO** | 984 | MIT | TypeScript + Python | Alpha | RLM-based trace analyzer, self-improvement loop, OTel compat |
| **OpenSRE** | 7.5k | Apache 2.0 | Python | Public Alpha | 60+ tools catalog, command registry, synthetic eval scenarios |
| **Career-Ops** | 55k | MIT | JavaScript + Go | v2+ (prod) | Batch worker pattern, Bubble Tea dashboard, SKILL.md validation |

---

## 1. DeepTutor (HKUDS/DeepTutor) — O Mais Relevante

**Stars:** 20k+ | **Licença:** Apache 2.0 ✅ | **Stack:** Python + Next.js 16

### Arquitetura

DeepTutor é um "agent-native learning workspace" — a visão é quase idêntica à do aiw, mas com **6 meses de head start** e ~200k linhas de código. O core agent loop é um **async generator** (mesmo padrão do aiw).

### O que podemos usar

#### 1.1 Persistent Memory L1/L2/L3 **← JÁ IMPORTAMOS (phase2-1-persistent-memory)**

DeepTutor popularizou o conceito de memória em 3 camadas:
- **L1**: Append-only traces (eventos crus)
- **L2**: Fatos curados por "superfície" (tópico)
- **L3**: Síntese cross-surface (perfil, preferências, escopo)

**Status no aiw:** Já implementado via merge do branch `phase2-1-persistent-memory`. O padrão L1/L2/L3 está presente.

**Interseção com nosso código:**
- `agents/memory_tree.py` — execution-scoped (subgoal tree), complementar
- Novo `agents/memory.py` — PersistentMemory com L1 trace → L2 facts → L3 synthesis
- `tui/graph.py` — pode renderizar o Memory Graph (pirâmide visual L3→L2→L1)

**O que falta:** Conectar PersistentMemory com o agente loop real — hoje ele existe como módulo mas não é chamado automaticamente pós-sessão.

#### 1.2 Partners / SOUL.md **← JÁ IMPORTAMOS (phase2-1-persistent-memory)**

DeepTutor permite "consultar um Partner" de dentro de qualquer turno de chat. Cada Partner tem:
- `SOUL.md` — personalidade, expertise, regras de comportamento
- Workspace privado com memória, skills, KB isolados
- Política de ferramentas (allow/deny)
- Binding opcional com canal IM (Matrix, Slack, Telegram)

**Status no aiw:** Já implementado via merge. `agents/partner.py` existe.

**O que falta:** Integração com o `/agents` CLI, canal IM (Matrix bridge), e `consult_subagent` tool no loop principal.

#### 1.3 Multi-Engine RAG **← JÁ IMPORTAMOS (phase2-1-persistent-memory)**

DeepTutor permite escolher engine por KB: LlamaIndex, PageIndex, GraphRAG, LightRAG, LightRAG Server, Obsidian vault.

**Status no aiw:** Já temos o `RetrievalEngine` abstrato com suporte a múltiplos engines. `knowledge/rag.py` + `knowledge/store.py`.

**O que usar deles:** O adaptador **LightRAG** (knowledge graph) e **Obsidian vault** (read-in-place, sem re-index). DeepTutor tem implementações de referência para ambos.

#### 1.4 ChatOrchestrator Unificado

DeepTutor tem um **único loop** que roda Chat, Quiz, Research, Solve, Mastery Path. O aiw tem **4 entry points separados** (`loop.py`, `router.py`, `orchestrator.py`, `swarm.py`).

**O que fazer:** Adicionar um conceito de `Capability` (declara quais tools precisa, quais params de modelo, quais fontes de contexto). O `AgentLoop` dispatches para a capability certa sem mudar o loop. Isso reduz a necessidade de `router.py` + `orchestrator.py` como entry points separados.

#### ⚠️ Riscos / Atenção

- **Escopo:** DeepTutor é focado em educação/tutoring. O aiw é um workspace de desenvolvimento. As ideias de memória e agentes são transferíveis, mas o domain model não.
- **Tamanho:** 200k linhas + Next.js frontend pesado. Não precisamos replicar o frontend — o TUI + PWA do aiw já cobrem.
- **Apache 2.0:** Permite usar código diretamente com atribuição.

---

## 2. OpenViking (volcengine/OpenViking) — Context Database

**Stars:** 26k | **Licença:** AGPL-3.0 ⚠️ | **Stack:** Python + Rust

### Arquitetura

OpenViking é um "Context Database" para agentes de IA. A inovação principal é abandonar o modelo fragmentado de vector storage e adotar um **paradigma de filesystem** para organizar memória, recursos e skills.

### O que podemos usar (como inspiração, não código — AGPL)

#### 2.1 Tiered Context Loading L0/L1/L2

OpenViking carrega contexto em 3 tiers:
- **L0**: Sempre injetado (system prompt, tarefa ativa)
- **L1**: On-demand (KB entries, resultados de tools)
- **L2**: Expandido (documentos completos, traces detalhados)

**Status no aiw:** Temos `context_manager.py` com pin/exclude/trim mas sem tiering. `compaction.py` define L1/L2/L3 mas são sobre **pace de compactação**, não tiers de carregamento.

**O que fazer:** Adicionar `ContextTier` enum e `get_context(tier)` que constrói contexto progressivamente. Isso economiza tokens significativamente — você só carrega L2 quando o agente explicitamente pede "mais detalhes".

#### 2.2 Directory-Based Retrieval

OpenViking organiza contexto por **diretórios temáticos** (como um filesystem) em vez de vector search plano. Cada KB é um diretório, cada retrieval é uma leitura de arquivo.

**O que fazer:** Adicionar `directory-based retrieval` como alternativa ao vector search. Organizar contexto por diretórios de tópicos, recuperar por hierarquia de diretório + search semântico dentro do diretório.

#### 2.3 Retrieval Trajectory Visualization

OpenViking mostra **como** o contexto foi encontrado (qual diretório, quais search terms, qual rank). Isso resolve o "unobservable context" problem.

**O que fazer:** Adicionar metadados de retrieval trajectory no `RetrievalResult`: `retrieval_path = ["KB/tech/python/", "semantic: async await", "rank: 2"]`. O TUI pode mostrar isso como breadcrumb.

#### ⚠️ AGPL-3.0

Código do OpenViking **não pode** ser copiado diretamente (AGPL contamina). Usar apenas como **inspiração arquitetural**. Nossa `docs/ATTRIBUTION.md` deve documentar as fronteiras.

---

## 3. HALO (context-labs/HALO) — Self-Improvement Loop

**Stars:** 984 | **Licença:** MIT ✅ | **Stack:** TypeScript + Python

### Arquitetura

HALO é um **RLM-based agent optimizer** que fecha o loop:

```
Coletar traces → RLM analysis → Report → Fix → Redeploy
```

O core insight: **um agente generalista (Claude Code) é a ferramenta errada para analisar traces**. Traces são longos demais e o agente overfitta em erros individuais. HALO usa um **RLM especializado** que:
1. Decompõe traces em failure modes
2. Generaliza por padrões (não overfitta)
3. Produz um relatório estruturado com recomendações concretas

### O que podemos usar diretamente

#### 3.1 HALO Engine como Pacote Python

`pip install halo-engine` — o engine HALO-RLM está disponível como pacote Python (MIT).

**O que fazer:** Adicionar como dependência opcional (`halo-engine` em `pyproject.toml` como extra). Criar um `ImprovementCycle` no aiw que:
1. Exporta traces do `TraceStore` para JSONL (formato compatível com HALO)
2. Chama `halo-engine` com os traces
3. Parseia o relatório HALO em recomendações acionáveis
4. Escreve em `memory/conventions.md` e `memory/project-patterns.md`

#### 3.2 OpenTelemetry Export

HALO suporta OTel/OpenInference nativamente. O aiw já tem `TraceStore` que escreve JSONL.

**O que fazer:** Adicionar `OpenTelemetryExporter` opcional no `TraceStore`. Isso permite:
- Importar traces do aiw no HALO Desktop App
- Usar HALO para analisar o comportamento do próprio aiw (dogfooding)
- Suportar `CATALYST_OTLP_TOKEN` e `HALO_TELEMETRY_PATH` env vars

#### 3.3 Loop Architecture

HALO tem 6 entry points na API Python (`stream_engine_async`, `run_engine`, etc.) — mesmo padrão que o aiw já usa no `AgentLoop` com `_agent_loop()` como async generator.

**O que usar:** O padrão de `AgentOutputItem` + `AgentTextDelta` para streaming de steps completos vs tokens. O aiw já faz isso, mas podemos usar o modelo de dados do HALO como referência para padronizar.

#### ⚠️ Riscos

- HALO ainda é alpha (v0.x). A API pode mudar.
- Depende de `gpt-5.4-mini` por padrão (OpenAI). Precisamos testar com Ollama/DeepSeek.
- O RLM engine é útil mas não substitui eval harness próprio — é complementar.

---

## 4. OpenSRE (Tracer-Cloud/opensre) — TUI/CLI Patterns

**Stars:** 7.5k | **Licença:** Apache 2.0 ✅ | **Stack:** Python

### Arquitetura

OpenSRE é um framework para construir AI SRE agents. Tem 60+ integrações com ferramentas de infraestrutura. A relevância para o aiw não é o domínio (SRE), mas os **padrões de interação**.

### O que podemos usar

#### 4.1 Command Registry Pattern

OpenSRE tem um sistema modular de slash commands:
```
app/cli/interactive_shell/command_registry/
  ├── agents.py, alerts.py, session_cmds.py, settings_cmds.py
  ├── types.py (classe base), slash_catalog.py, suggestions.py
```

**Status no aiw:** `tui/command_palette.py` tem 6 comandos hardcoded.

**O que fazer:** Substituir por command registry pattern (classe base + self-registering). Adicionar comandos inspirados no OpenSRE: `/resume`, `/cost`, `/sessions`, `/agents`.

#### 4.2 Integration Catalog

OpenSRE tem um catálogo de 60+ integrações com categorias, verificação, roadmap links.

**Status no aiw:** `tools/marketplace.py` (322 linhas) mas sem catálogo categorizado.

**O que fazer:** Estender `marketplace.py` com registry categorizado (LLMs, Observability, Infrastructure, Databases, etc.). Adicionar `/integrations verify` para testar conectividade.

#### 4.3 Synthetic Eval Scenarios

OpenSRE tem suites de RCA (root cause analysis) sintéticas com scoring.

**Status no aiw:** `evals/` tem 3 suites com 6 casos, todos estáticos.

**O que fazer:** Adicionar geração de cenários sintéticos: define failure modes, deixa o agente investigar, scored por resposta correta. Pattern: `Scenario(symptoms, expected_rca, required_evidence, red_herrings)` → scored.

#### 4.4 PII Masking

OpenSRE tem `IdentifierMasker` que escaneia mensagens por IPs, hostnames, account IDs, API keys → replace com placeholders → restore no output.

**Status no aiw:** `agents/safety.py` foca em deception detection, não PII.

**O que fazer:** Adicionar `IdentifierMasker` no aiw, gateado por provider (só para cloud, não Ollama local).

---

## 5. Career-Ops (santifer/career-ops) — Batch Processing & Dashboard

**Stars:** 55k | **Licença:** MIT ✅ | **Stack:** JavaScript + Go

### Arquitetura

Career-Ops é um sistema de busca de empregos multi-agente. Tem 14 skill modes, um dashboard em Go (Bubble Tea), geração de PDF, batch processing. O que é relevante para o aiw não é o domínio (job search), mas os **padrões de engenharia**.

### O que podemos usar

#### 5.1 Batch Worker Pattern

Career-Ops tem `batch/batch-runner.sh` + `batch/batch-prompt.md` — um padrão simples de workers paralelos:
- Shared context (`batch-prompt.md`)
- N tasks paralelas (N instances do agente)
- Coletor de resultados

**Status no aiw:** `agents/swarm.py` usa crewAI, que é YAML-driven e rígido.

**O que fazer:** Adicionar `BatchSwarm` leve:
```python
class BatchSwarm:
    def run(self, tasks: list[str], context: str, workers: int = 4) -> list[Result]:
        # Cada worker recebe contexto isolado do ContextManager
        # Tasks rodam em paralelo via asyncio
        # Resultados mergeados por collector function
```

#### 5.2 Bubble Tea Dashboard Patterns

Career-Ops tem um dashboard em Go com Bubble Tea que implementa:
- Filter tabs (por status, por superfície, por modelo)
- Sort modes
- Grouped/flat view
- Lazy-loaded previews
- Inline status changes

**Status no aiw:** `tui/dashboard.py` tem display básico de status de agente.

**O que fazer:** Adaptar esses patterns para o Textual TUI do aiw. Filter tabs e lazy-loaded previews são diretos em Textual. O aiw já usa cores Catppuccin.

#### 5.3 SKILL.md Validation

**Status no aiw:** Já temos SKILL.md como formato de skill (herdado do pi). Career-Ops valida o pattern com milhares de usuários.

**O que validar:** Nosso formato de SKILL.md está alinhado com o que a comunidade usa. Career-Ops confirma que o pattern de `baking instructions` declarativos funciona em escala.

---

## Mapa de Interseção: O Que Já Temos vs O Que Falta

### Já implementado (via merges phase2 + save-port)

| Conceito | Projeto Fonte | Onde está no aiw | Status |
|----------|--------------|------------------|--------|
| Persistent Memory L1/L2/L3 | DeepTutor | `agents/memory.py` | ✅ Module exists |
| Partners / SOUL.md | DeepTutor | `agents/partner.py` | ✅ Module exists |
| Multi-engine RAG | DeepTutor | `knowledge/rag.py`, `knowledge/store.py` | ✅ |
| BatchSwarm | DeepTutor/Career-Ops | `agents/swarm.py` (BatchSwarm) | ✅ |
| PII Safety | DeepTutor | `agents/safety.py` (PIIMasker) | ✅ |
| OTel Tracing | HALO | `observability/__init__.py` (TraceStore) | ✅ Já escreve JSONL |
| Skill system | Career-Ops | SKILL.md + `pi-setup/skills/` | ✅ |

### Falta implementar (oportunidades reais)

| Oportunidade | Projeto Fonte | Esforço | Impacto | Prioridade |
|-------------|--------------|---------|---------|------------|
| **ImprovementCycle (TraceStore → EvalCase → recomendações)** | HALO | 3-4 dias | Alto | 🔴 Alta |
| **OpenTelemetryExporter (traces compatíveis HALO)** | HALO | 2 dias | Médio | 🟠 Média |
| **Command Registry (em vez de hardcoded)** | OpenSRE | 2-3 dias | Médio | 🟠 Média |
| **Tiered Context Loading (L0/L1/L2)** | OpenViking | 4-6 dias | Alto | 🔴 Alta |
| **Retrieval Trajectory Visualization** | OpenViking | 2-3 dias | Médio | 🟡 Baixa |
| **Synthetic Eval Scenarios** | OpenSRE | 3-4 dias | Médio | 🟠 Média |
| **IdentifierMasker (PII para cloud)** | OpenSRE | 1-2 dias | Médio | 🟡 Baixa |
| **Dashboard filter tabs + lazy previews** | Career-Ops | 3-5 dias | Médio | 🟡 Baixa |
| **Capability concept (unificar loop)** | DeepTutor | 4-5 dias | Alto | 🟠 Média |
| **Partner CLI + IM bridge** | DeepTutor | 5-7 dias | Alto | 🟠 Média |

---

## Recomendações

### Fase 1 (Agora — 1 semana)
1. **ImprovementCycle** — Conectar TraceStore → EvalCase → recomendações em `agents/improvement.py`. Usar `halo-engine` como backend opcional. **Maior impacto com menor esforço.**
2. **Command Registry** — Refatorar `tui/command_palette.py` para registry pattern. Abre caminho para `/resume`, `/cost`, `/sessions`.
3. **OpenTelemetryExporter** — Adicionar export OTLP opcional no `TraceStore`. Permite dogfooding com HALO.

### Fase 2 (Próximas 2 semanas)
4. **Tiered Context Loading** — Adicionar `ContextTier` L0/L1/L2 em `context_manager.py`. Economia real de tokens.
5. **Capability Concept** — Harmonizar `loop.py`/`router.py`/`orchestrator.py` com dispatch por capability.
6. **Synthetic Evals** — Adicionar geração de cenários sintéticos em `evals/synthetic/`.

### Fase 3 (Depois)
7. **Partner CLI** — `partners list`, `partners create`, `partners chat`
8. **Dashboard filter tabs** — Melhorias de UX no TUI
9. **PII Masker** — Segurança para cloud providers
10. **Retrieval Trajectory** — Metadados de busca no RAG

---

## Riscos e Atenções

| Risco | Projeto | Mitigação |
|-------|---------|-----------|
| **AGPL-3.0** | OpenViking | Não copiar código. Inspirar-se na arquitetura apenas. Documentar em `ATTRIBUTION.md`. |
| **API instável** | HALO (alpha) | Usar `halo-engine` como dependência opcional (extra), não core. Isolar com adapter pattern. |
| **Feature creep** | Todos | Phase-gated delivery. Cada fase deve ship antes de começar a próxima. |
| **Overengineering** | DeepTutor | Não replicar o frontend Next.js. Focar no que o TUI + CLI já cobrem. |
| **Dependência externa** | HALO engine | HALO depende de OpenAI por padrão. Testar com Ollama local antes de integrar. |

---

## Links

- DeepTutor: https://github.com/HKUDS/DeepTutor | https://deeptutor.info
- OpenViking: https://github.com/volcengine/OpenViking | https://openviking.ai
- HALO: https://github.com/context-labs/HALO | https://inference.net/products/halo
- OpenSRE: https://github.com/Tracer-Cloud/opensre | https://www.opensre.com
- Career-Ops: https://github.com/santifer/career-ops
