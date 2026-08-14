# Research: Features That Failed — Lessons from Production

> **Status:** 📋 Research notes | **Data:** 2026-06-18
> **Refs:** Stitch v2 postmortem, AIAgentMinder v0.7.0, Grinta Coding Agent

---

## 🔴 Caso 1: Stitch — "Deletamos nosso regex classifier"

**O que era:** Um engine de 150 regex patterns que classificava erros de CI em 9 categorias (lint, types, build, etc.) com confidence scores. Cada categoria mapeava para uma estratégia de fix.

**Por que foi construído:** Modelos eram caros e ruins em logs não estruturados. Pré-processar = economizar tokens.

**Por que foi deletado (Mar 2026):**
1. Modelos ficaram melhores em ler logs brutos
2. Claude e GPT ficaram mais baratos por token
3. O classifier não cobria novas linguagens (Elixir, Rust) → caía no bucket "unknown" → modelo resolvia sozinho
4. O fallback (modelo bruto) funcionava melhor que o caminho especializado

**A lição:**
> "The abstractions you build to help the model often stop helping once the model gets good enough. If you own both the preprocessor and the prompt, you will reach a point where the preprocessor is making the prompt worse."

**Aplicação ao aiw:** Nosso DeepSearchEngine (7 etapas: planner→supervisor→researcher×N→filter→synthesize→critic) é exatamente esse tipo de preprocessor. O modelo já consegue pesquisar sozinho com web tools. O pipeline adiciona latência e pontos de falha.

---

## 🔴 Caso 2: AIAgentMinder — "Deletei 80% do meu produto"

**O que era:** Sistema de hooks que injetavam PROGRESS.md, DECISIONS.md, SPRINT.md e arquivos de guidance no contexto do Claude Code em cada sessão.

**Por que foi construído:** Claude Code não tinha memória entre sessões. O tool resolvia isso com git-tracked markdown files + lifecycle hooks.

**Por que foi deletado (2026):**
1. Claude Code lançou auto-memory (escreve MEMORY.md automaticamente)
2. Session Memory: sumarização contínua em background
3. `.claude/rules/` com glob-scoped file targeting
4. `--continue` e `--resume` nativos

**A análise do próprio Claude sobre o tool:**
> "80% do que AIAgentMinder faz agora é coberto nativamente. Cada token gasto em injeção redundante é um token não disponível para código real."

**A lição:**
> "O problema que você está resolvendo pode ser absorvido pela plataforma. Construa sobre APIs públicas, não sobre hacks de contexto."

**Aplicação ao aiw:** Nossos specs de context compaction e memory tree devem ser construídos como extensões do AgentLoop, não como hacks de injeção. Se o modelo/plataforma evoluir, podemos remover sem perder funcionalidade core.

---

## 🔴 Caso 3: Grinta Coding Agent — "The Killed Darlings"

**O que era:** Várias features complexas de planejamento multi-agente.

**O que foi abandonado:**
1. Deep multi-agent planning frameworks
2. Pipeline de coordenação complexo

**Por que:**
- Alto custo de tokens
- Execução lenta
- Maior superfície para "objective drift" (agentes se perdem do objetivo original)
- ReAct simples + tools era suficiente para maioria dos casos

**A lição:**
> "Deep planning frameworks add token cost, slow execution, and increase surface area for objective drift. Simple ReAct + tools handles most cases."

**Aplicação ao aiw:** Nossa spec `SPEC_DAG_EXECUTION.md` (GraSP/FlowBank) é exatamente isso. Promissora como pesquisa, mas não para v0.2. ReAct + tools cobre 90% dos casos.

---

## 🟡 Caso 4: "We spent 6 months building advanced features. Our customers used zero."

**O que era:** Time passou 6 meses construindo features "avançadas" de AI. 

**O que aconteceu:** Clientes usaram zero delas. Preferiam as features simples que já existiam.

**A lição:**
> "Builders over-index on 'wow' features. Users want boring, practical tools that fit their workflow."

**Aplicação ao aiw:** Nossos specs mais "wow" (DAG execution, memory tree, GraSP) são exatamente isso. O MVP deve ser: TUI mostrando agentes + chat + busca simples. O resto é risco de desperdício.

---

## 📊 Padrões que emergem dos 4 casos

| Padrão | O que significa para nós |
|--------|-------------------------|
| **Pré-processadores viram dívida** | DeepSearch pipeline → substituir por ReAct agent |
| **Plataforma absorve features** | Não construir sobre hacks de injeção de contexto |
| **Planejamento profundo é frágil** | ReAct > Plan-Execute para MVP |
| **Usuários querem simples** | TUI + chat + busca > DAG + memory tree |

---

## ✅ O que os sobreviventes fizeram certo

| Projeto | O que manteve | Por que |
|---------|--------------|--------|
| Stitch v2 | "Coarse and honest" preprocessing (só decide se roda o job) + agente com tools | Simplicidade > inteligência artificial |
| AIAgentMinder v0.7.0 | Só os 20% que estendem capacidades (não duplicam) | Foco no valor único |
| Aider | Git-integrated, atomic commits | Uma coisa bem feita |
| Claude Code | Single entry point, async generator | Arquitetura mínima, máxima flexibilidade |

---

## 📚 Referências

- [Stitch: Deleting our regex classifier](https://stitch-agent.dev/blog/deleting-our-regex-classifier/) Mar 2026
- [AIAgentMinder: Deleted 80% of my project](https://lwalden.dev/posts/aiagentminder-v070-native-memory-migration/) 2026
- [Grinta: The Killed Darlings](https://github.com/josephsenior/Grinta-Coding-Agent) 2026
- [What AI Builders Want vs What People Want](https://dev.to/jimrusk/what-ai-agent-builders-want-to-build-vs-what-people-actually-want-5gp6) 2026
