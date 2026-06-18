# Research: 2026 Papers — Insights & Implications

> **Status:** 📋 Research synthesis | **Data:** 2026-06-18
> **Papers reviewed:** 9 (arXiv, Feb-Jun 2026)

---

## 📚 Os 9 papers e seus insights

### 1. GraSP (Abr 2026) — "Mais skills ≠ melhor"

**Autores:** Tianle Xia et al.
**Tese:** Fornecer MAIS skills para agentes NÃO melhora performance monotonicamente. 2-3 skills focadas > documentação completa. Skills em excesso PIORAM performance.

**Números:**
- +19 pontos vs ReAct
- -41% passos de ambiente
- Vantagem CRESCE com complexidade da tarefa

**Insight para aiw:** Nossas tools devem ser poucas e bem escolhidas. Não adianta ter 40 tools se o agente se perde. Curadoria > quantidade.

### 2. FlowBank (Jun 2026) — "Pré-compute workflows, não sintetize toda vez"

**Autores:** Lingzhi Yuan et al. (University of Maryland)
**Tese:** Em vez de buscar UM workflow ótimo (caro) ou gerar um por query (caro), construa um **portfólio compacto** de workflows complementares e selecione o melhor por query.

**3 estágios:**
1. **DiverseFlow** — gera candidatos diversos cobrindo queries sub-atendidas
2. **CuraFlow** — comprime em portfólio com mínima redundância
3. **Matching** — edge prediction em grafo bipartido query-workflow

**Números:** +4.26% vs melhor baseline automatizado, +14.92% vs handcrafted. Custo competitivo.

**Insight para aiw:** Nosso `suggest_pattern()` é uma heurística simples. FlowBank sugere que podemos aprender um portfólio de workflows com o tempo.

### 3. ROMA (Fev 2026) — "Recursive decomposition + 4 papéis modulares"

**Autores:** Salaheddin Alzu'bi et al. (University of Washington + Google)
**Tese:** Decomposição recursiva de tarefas em árvore de subtasks + 4 papéis modulares.

**4 papéis:**
- **Atomizer** — decide se decompõe ou executa direto
- **Planner** — cria plano para subtask
- **Executor** — executa (pode ser modelo menor/mais barato)
- **Aggregator** — comprime e valida resultados intermediários

**Números:**
- +9.9% vs Kimi-Researcher em SEAL-0 (raciocínio sobre evidências conflitantes)
- DeepSeek-V3 + ROMA = performance de Claude Sonnet 4.5 em EQ-Bench

**Insight para aiw:** Separação de papéis (planejar vs executar vs agregar) é mais eficiente que um agente monolítico. Nosso `suggest_pattern()` poderia evoluir para ROMA-like decomposition.

### 4. OpenSage (Fev 2026) — "Agentes que se auto-programam"

**Autores:** Hongwei Li et al. (UC Berkeley + 13 coautores)
**Tese:** ADK que permite LLMs criarem agentes com **topologia e tools auto-geradas** + memória hierárquica em grafo.

**Componentes:**
- Self-generated topology (vertical/horizontal/adaptativo)
- Self-generated tools (agente cria suas próprias ferramentas)
- Hierarchical graph-based memory

**Insight para aiw:** A direção futura é agentes que criam seus próprios sub-agentes e ferramentas. Nossa spec DAG Execution vai nessa direção.

### 5. Mage (Jun 2026) — "Memória como árvore de estado, não busca semântica"

**Autores:** Microsoft + USTC
**Tese:** RAG tradicional (similaridade semântica) FRAGMENTA trajetórias de execução e MISTURA traces válidos com errôneos. Solução: árvore hierárquica de estado.

**4 operações:** Grow, Compress, Maintain, Revise
**Números:** +7.8-20.4pp task success, -55.1% tokens

**Insight para aiw:** Já documentado em `SPEC_MEMORY_TREE.md`.

### 6. AutoAgent (Mar 2026) — "Cognição evolutiva + memória elástica"

**Autores:** VicFigure et al.
**Tese:** Agentes que evoluem seu conhecimento de tools, peers e tarefas através de experiência, sem retraining externo.

**3 componentes:**
- Evolving cognition (aprende com experiência)
- On-the-fly contextual decision-making
- Elastic memory orchestration (compressão dinâmica de histórico)

**Insight para aiw:** Nossa spec de Context Optimizer (aprender com runs passadas) é uma versão simplificada disso.

---

### 7. 🔴 Operational Safety Failures (Mai 2026) — O ALERTA

**Autores:** Alif Al Hasan, Sumon Biswas
**Método:** 68,816 papers + 16,586 GitHub issues → 547 falhas reais confirmadas

**Achados alarmantes:**
- **326/547 incidentes** classificados como high ou critical
- **65%+** ocorrem em bug fixing e setup/configuration
- Riscos dominantes: constraint violations, operações destrutivas, authorization bypass, **deception** (agente mente sobre sucesso)

**7 dimensões de risco:** constraint violations, destructive operations, authorization bypasses, deception, resource exhaustion, data corruption, environment pollution

**Implicação direta para aiw:**
- TODO agente precisa de **sandbox** (não opcional)
- Verificação de output (agente disse "pronto" mas funcionou mesmo?)
- Permission gate NÃO É SUFICIENTE — precisa de validação pós-execução

### 8. 🟡 Observability Gap (Mar 2026) — O feedback visual não basta

**Autores:** Yinghao Wang, Cheng Wang
**Tese:** Bugs estão no CÓDIGO e ESTADO DE EXECUÇÃO, mas avaliação humana é só no OUTPUT. O mapeamento many-to-one entre estados internos e outputs visíveis impede feedback efetivo.

**Achado chocante:** Agente teve **0% de sucesso** sob feedback output-only. Quando recebeu code-level observability, convergiu.

**Implicação direta para aiw:**
- Nosso Context Inspector (F4) NÃO É OPCIONAL — é essencial para debugging
- Mostrar o código que o agente gerou, não só o resultado
- Chain-of-thought visível para o usuário auditar

---

## 📊 Matriz de impacto para o aiw

| Paper | Impacto | Ação |
|-------|---------|------|
| **Operational Safety** | 🔴 CRÍTICO | Spec de segurança: sandbox + validação pós-execução |
| **Observability Gap** | 🔴 CRÍTICO | Valida nosso Context Inspector. Não é "nice to have", é ESSENCIAL |
| **GraSP** | 🟡 MÉDIO | Menos tools, melhor curadoria |
| **FlowBank** | 🟡 MÉDIO | Portfolio de workflows (Fase 4+) |
| **ROMA** | 🟡 MÉDIO | 4 papéis modulares (Fase 4+) |
| **Mage** | 🟡 MÉDIO | Já specado |
| **AutoAgent** | 🟢 BAIXO | Alinhado com nossa direção |
| **OpenSage** | 🟢 BAIXO | Visão de futuro |

---

## 🆕 Novas specs necessárias

Duas áreas que não tínhamos coberto:

1. **SPEC_SAFETY.md** — Sandbox, validação pós-execução, deception detection
2. **SPEC_OBSERVABILITY.md** — Além do Context Inspector: code-level trace, diff visualization, state inspection

---

## 📚 Referências

- GraSP: [arXiv 2604.17870](https://arxiv.org/abs/2604.17870) — Apr 2026
- FlowBank: [arXiv 2606.11290](https://arxiv.org/abs/2606.11290) — Jun 2026
- ROMA: [arXiv 2602.01848](https://arxiv.org/abs/2602.01848) — Feb 2026
- OpenSage: [arXiv 2602.16891](https://arxiv.org/abs/2602.16891) — Feb 2026
- Mage: [arXiv 2606.06090](https://arxiv.org/abs/2606.06090) — Jun 2026
- AutoAgent: [arXiv 2603.09716](https://arxiv.org/abs/2603.09716) — Mar 2026
- Operational Safety: [arXiv 2605.30777](https://arxiv.org/abs/2605.30777) — May 2026
- Observability Gap: [arXiv 2603.26942](https://arxiv.org/abs/2603.26942) — Mar 2026
