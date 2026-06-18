# Research: Planning & Deep Research — What the 2026 Papers Say

> **Status:** 📋 Research synthesis | **Data:** 2026-06-18
> **Papers:** DuMate, Marco, Ptah, DualGraph, S1-DeepResearch, Planning Survey (ICAPS 2026)

---

## 🎯 O estado da arte em Deep Research (Jun 2026)

### DuMate-DeepResearch (Baidu, 15 autores, Jun 2026)

O sistema mais completo. **58% no DeepResearch Bench** (SOTA).

**4 problemas que resolve:**
1. Planejamento de longo horizonte com escopo sub-especificado
2. Gargalo de decompor tarefas em um único agente
3. Risco de alucinação em síntese longa
4. Falta de auditabilidade do processo

**3 mecanismos-chave:**

**1. Planejamento dinâmico baseado em grafo**
```
Query inicial → roadmap coarse
  │
  ├─ Reflete sobre gaps → expande nós
  ├─ Re-planeja quando evidência contradiz
  ├─ Backtracking quando beco sem saída
  └─ Ramificação paralela para ângulos independentes
```

**2. Design recursivo de 2 níveis**
```
Outer Agent (planner)
  │
  ├─ Decompõe query em sub-tarefas
  ├─ Para cada sub-tarefa complexa:
  │   └─ Inner Search Agent (executor)
  │       ├─ Roda seu PRÓPRIO loop de planejamento
  │       ├─ Isola ruído de retrieval
  │       └─ Estabiliza execução longa
  └─ Sintetiza resultados
```

**3. Otimização baseada em rubrica**
- Gera critérios de qualidade dinamicamente por tarefa
- Usa rubricas como scaffolding para síntese
- Critério de parada adaptativo (não para até rubrica satisfeita)

### Marco DeepResearch (Alibaba, Mar 2026)

**Verificação em 3 níveis:**
1. **QA Synthesis:** Verificação durante geração de dados de treino
2. **Trajectory Construction:** Injeção de padrões de verificação nos trajectories
3. **Test-time:** Usa o próprio agente como verificador em inference

**Resultado:** Modelo de 8B supera modelos de 30B em benchmarks (BrowseComp). **600 tool calls máximo.**

### Ptah (Verifiable Multimodal DR)

Multi-agente com verifier-agent hooks. Cada etapa tem verificação de factual grounding.

### DualGraph (Fev 2026)

**Separa conhecimento de estrutura:**
- Knowledge Graph: exploração de conteúdo
- Outline Graph: estrutura do documento
- Mantém coerência em síntese longa sem misturar os dois

### S1-DeepResearch (Jun 2026)

**"Beyond Search, Toward Real-World Long-Horizon Research"**
- Não é só busca → é raciocínio sobre o que encontrou
- Agentes que pensam sobre gaps de conhecimento

---

## 📐 O que os papers dizem sobre PLANEJAMENTO

### ICAPS 2026: "Planning in the LLM Era"

**A grande mudança:** De "LLM como planejador" para "LLM como **gerador de planejadores**".

```
Antes (2024-2025):
  Query → LLM gera plano → executa
  
  Problema: planos não confiáveis, não verificáveis,
  caros (LLM chamado toda vez)

Agora (2026):
  Família de problemas → LLM gera solver simbólico → 
  verificado → reutilizado eficientemente
  
  Vantagem: confiável, verificável, barato em inference
```

**3 categorias de geração de planejadores:**
1. LLM → PDDL (Planning Domain Definition Language)
2. LLM → código (Python planner)
3. LLM → heurística de busca (MCTS guide)

**Insight:** "LLMs não são bons planejadores. São bons **construtores** de planejadores."

---

## 📊 Padrões que emergem

### Como fazer Deep Research direito (consenso dos papers)

| Princípio | Fonte | Implementação |
|-----------|-------|---------------|
| **Planejamento dinâmico, não estático** | DuMate, ROMA | Grafo que expande, revisa, faz backtrack |
| **Verificação em cada etapa** | Marco, Ptah | Verifier agent, rubric-based stopping |
| **Separação planner/executor** | DuMate, ROMA, FlowBank | Outer planeja, Inner executa |
| **Memória estruturada** | DualGraph, Mage | Separa conteúdo de estrutura |
| **Recursão** | DuMate, ROMA | Sub-agentes com próprio loop |
| **Construir, não improvisar** | ICAPS 2026 | Gerar solvers verificados |

### Anti-padrões identificados

| Erro | Paper | Consequência |
|------|-------|-------------|
| Plano único e estático | DuMate | Não se adapta a nova evidência |
| Agente monolítico | DuMate, ROMA | Gargalo de contexto, perda de foco |
| Sem verificação | Marco | Erros propagam, output não confiável |
| LLM como planejador direto | ICAPS 2026 | Caro, não confiável, não reutilizável |

---

## 🎯 O que isso significa para o aiw

### Nossa spec atual vs estado da arte

| Nossa spec | Alinhamento com papers | Ação |
|-----------|----------------------|------|
| `SPEC_AGENT_LOOP.md` (ReAct) | ✅ Base correta | Manter ReAct como executor |
| `SPEC_DAG_EXECUTION.md` | ✅ Alinhado com DuMate (graph-based planning) | Subir prioridade |
| `SPEC_MEMORY_TREE.md` | ✅ Alinhado com DualGraph + Mage | Manter |
| `deep_search.py` (7 etapas) | ❌ Anti-padrão: plano estático, monolítico | **Substituir** |
| `SPEC_RAG.md` | ⚠️ Falta verificação | Adicionar verification layer |

### Nova spec necessária: Deep Research v2

```python
# Baseado no DuMate + Marco + ROMA

class DeepResearchEngine:
    """Multi-agent deep research com planejamento dinâmico."""
    
    async def research(self, query: str) -> ResearchReport:
        # 1. Outer Agent: planejamento dinâmico em grafo
        roadmap = await self._build_roadmap(query)
        
        # 2. Para cada nó do grafo:
        results = []
        for node in roadmap.parallel_nodes():
            # Inner Search Agent com próprio loop
            result = await self._research_node(node)
            # Verificação
            if not await self._verify(result, node.rubric):
                roadmap.refine(node)  # re-planeja
                result = await self._research_node(node)
            results.append(result)
        
        # 3. Síntese com verificação
        report = await self._synthesize(results, roadmap)
        if not await self._verify_report(report):
            # Refina até rubrica satisfeita
            ...
        
        return report
```

---

## 📚 Novos papers adicionados

- DuMate-DeepResearch: [arXiv 2606.07299](https://arxiv.org/abs/2606.07299) — Baidu, Jun 2026, SOTA 58%
- Marco DeepResearch: [arXiv 2603.28376](https://arxiv.org/abs/2603.28376) — Alibaba, Mar 2026, 8B > 30B
- Ptah: [arXiv 2605.29861](https://arxiv.org/abs/2605.29861) — Verifiable multimodal DR
- DualGraph: [arXiv 2602.13830](https://arxiv.org/abs/2602.13830) — Knowledge + Outline graphs
- S1-DeepResearch: [arXiv 2606.15367](https://arxiv.org/abs/2606.15367) — Beyond search
- Planning Survey: [arXiv 2605.21902](https://arxiv.org/abs/2605.21902) — ICAPS 2026
