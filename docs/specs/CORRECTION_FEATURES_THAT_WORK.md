# Correção: Features que FUNCIONAM em produção

> **Status:** 📋 Análise revisada | **Data:** 2026-06-18
> **Refs:** Kimi K2.6, Claude Code, Cursor, pi

---

## 🔴 Onde eu errei na análise anterior

Eu comparei nossas specs com projetos que **falharam** (Stitch, Grinta, AIAgentMinder), mas ignorei que sistemas bem-sucedidos (Claude Code, Kimi, Cursor, pi) implementam exatamente essas features como **core capabilities**.

A diferença crucial: Stitch/Grinta/AIAgentMinder construíram ferramentas **externas** (wrappers, hooks, frameworks). Claude Code/Kimi/Cursor construíram essas capacidades **dentro** do agente.

---

## ✅ Features que funcionam (evidência de produção)

### 1. Deep Search → FUNCIONA (Kimi, Claude Code, Cursor)

| Sistema | Implementação |
|---------|--------------|
| **Kimi K2.6** | Deep Research: 10,000+ word reports, task decomposition, specialized sub-agents |
| **Claude Code** | Agent com web_search + web_fetch tools. Pesquisa iterativa. |
| **Cursor** | WebSearch + WebFetch tools no agente |
| **pi** | Não tem nativamente (usa MCP tools) |

**O que ESTAVA errado na nossa implementação:** O pipeline de 7 etapas com crewAI (planner→supervisor→researcher×N→filter→synthesize→critic). Isso é um pré-processador pesado.

**O que é CORRETO:** ReAct agent com web tools. O agente decide a profundidade. Kimi faz exatamente isso: "decomposes your request into sub-tasks, uses 20+ tools as needed, autonomous execution."

**Ação:** `SPEC_AGENT_LOOP.md` já cobre isso. Substituir `deep_search.py` por ReAct agent com web tools. NÃO matar a feature — consertar a implementação.

### 2. Agent Swarm / DAG Execution → FUNCIONA (Kimi, Claude Code)

| Sistema | Implementação |
|---------|--------------|
| **Kimi K2.6** | Agent Swarm: até 300 sub-agents em paralelo, 4.5x mais rápido, 1,500+ tool calls |
| **Claude Code** | Task tool: spawn sub-agents, worktree isolation, dynamic workflows, agent teams |
| **Cursor** | Task tool: spawn sub-agents paralelos |
| **pi** | Não tem swarm nativo |

**Kimi Swarm numbers:**
- 100 sub-agents em paralelo
- 1,500+ tool calls por tarefa
- 4.5x mais rápido que execução sequencial
- Self-organizing: agentes decidem como paralelizar

**O que é CORRETO:** Nossa spec `SPEC_DAG_EXECUTION.md` está alinhada com Kimi e Claude Code. O DAG executor é o mecanismo certo. NÃO matar — priorizar para Fase 3+.

### 3. Context Compaction → FUNCIONA (Claude Code, pi)

| Sistema | Implementação |
|---------|--------------|
| **Claude Code** | 5-level pipeline (3,960 linhas em `src/services/compact/`) |
| **pi** | `contextTransform()` no agent-loop.ts |
| **Cursor** | Auto-summarization quando contexto enche |

**O que é CORRETO:** Nossa spec `SPEC_CONTEXT_COMPACTION.md` é diretamente inspirada no Claude Code. Não é "otimização prematura" — é essencial para tarefas longas. Prioridade: Fase 2 (depois do AgentLoop funcionar).

### 4. Memory Tree → FUNCIONA (alinhado com pesquisa de ponta)

O paper Mage (Jun 2026) mostra +7.8-20.4pp em task success e -55% tokens. Não é validado em produção ainda, mas a direção é correta. Adiar para Fase 4+, não matar.

---

## 🆕 Features do Kimi que não tínhamos considerado

### Document Generation

Kimi gera:
- **Word** (.docx) — edição e geração
- **PDF** — geração e conversão
- **Markdown** — edição e geração
- **Excel/CSV** — análise de dados, visualização
- **PPT** — geração automática de slides
- **Websites** — geração e deploy de web apps

**Isso é relevante para o aiw?** Parcialmente. Nosso foco é terminal/coding, não office. Mas:
- Markdown generation ✅ (já fazemos)
- CSV/table generation 🟡 (útil para output de pesquisa)
- PPT/Word/PDF ❌ (fora do escopo terminal)

### Skill System

Kimi K2.6: "Turn Your Documents Into Reusable Skills and Let 50+ Agents Execute Them"

Nós já temos `skills/loader.py` que carrega pi-compatible skills. Mas o Kimi leva além:
- Documentos viram skills automaticamente
- Sub-skill discovery (agente descobre novas capacidades)
- 50+ agentes executando skills em paralelo

### Claw (Cloud Automation)

5,000+ skills para automação cloud. Fora do nosso escopo (somos local-first).

---

## 📊 Matriz atualizada: O que sistemas reais implementam

| Feature | Claude Code | Kimi K2.6 | Cursor | pi | aiw (planejado) |
|---------|------------|-----------|--------|-----|-----------------|
| Agent Loop | ✅ query.ts | ✅ | ✅ ReAct | ✅ agent-loop.ts | ✅ SPEC_AGENT_LOOP |
| Deep Search | ✅ tools | ✅ 10K words | ✅ tools | ⚠️ MCP | ✅ ReAct + tools |
| Agent Swarm | ✅ Task tool | ✅ 300 agents | ✅ Task tool | ❌ | 🟡 SPEC_DAG_EXEC |
| Context Compaction | ✅ 5-level | ✅ | ✅ auto | ✅ transform | ✅ SPEC_COMPACTION |
| Memory Tree | ❌ | ❌ | ❌ | ❌ | 🟡 SPEC_MEMORY_TREE |
| Doc Generation | ❌ | ✅ Word/PDF/PPT | ❌ | ❌ | 🆕 Markdown+CSV |
| Skill System | ✅ hooks | ✅ doc→skill | ✅ SKILL.md | ✅ skills | ✅ existente |
| TUI | ✅ terminal | ✅ web | ✅ IDE | ✅ próprio | ✅ SPEC_TUI_V5 |
| BYOK/Local | ❌ cloud | ❌ cloud | ❌ cloud | ✅ local | ✅ Ollama $0 |
| MCP | ✅ nativo | ❌ | ✅ nativo | ❌ | ✅ SPEC_MCP_TOOL |

---

## 📋 Roadmap revisado (baseado em evidência)

```
Fase 0: Limpeza (hoje)
  └─ Remover código morto, arquivar docs velhos

Fase 1: Fundações (2-3 dias)
  ├─ AgentLoop (ReAct + Direct)
  ├─ OutputFormatter (JSON/NDJSON)
  ├─ Result/AiWError
  └─ Provider streaming nativo

Fase 2: TUI + Contexto (2-3 dias)
  ├─ TUI v5 (AgentMonitor + Conversation + HelpBar)
  ├─ Context Compaction L1+L3 (validado por Claude Code)
  └─ Context Inspector (F4 overlay)

Fase 3: Search + RAG + Swarm (3-4 dias)
  ├─ Deep Search via ReAct agent (substitui pipeline 7 etapas)
  ├─ RAG simples (embedding search) — validado por Cursor
  └─ Agent Swarm básico (Task tool como Claude Code)

Fase 4: Qualidade + Escala (2-3 dias)
  ├─ Eval Harness (métricas objetivas)
  ├─ Memory Tree (Mage paper)
  ├─ DAG Execution (GraSP + FlowBank)
  └─ Document generation (Markdown tables, CSV reports)

Fase 5: Polish (1-2 dias)
  ├─ Context Compaction L2+L4+L5
  ├─ RAG com RRF + rerank
  └─ MCP agent tools
```

---

## 🎯 O que NÃO mudou

O MVP (Fase 1+2) continua o mesmo. A diferença é que agora temos um roadmap claro para Fase 3+ baseado no que Kimi, Claude Code e Cursor já validaram em produção. Não estamos mais adivinhando.
