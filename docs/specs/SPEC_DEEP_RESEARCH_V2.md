# Spec: Deep Research v2 — Graph-Based Multi-Agent Research

> **Status:** 📋 Spec (substitui deep_search.py) | **Data:** 2026-06-18
> **Refs:** DuMate (Baidu), GPT Researcher (27.8K ★), Deep-Research-Agent, STORM (Stanford), Marco (Alibaba)

---

## 🎯 O que aprendemos

### Ferramentas reais que já fazem isso

| Ferramenta | ★ | Arquitetura | Diferencial |
|-----------|-----|------------|-------------|
| **GPT Researcher** | 27.8K | Planner + Executor agents + Publisher | Mais maduro open-source. Parallel scraping. 20+ fontes. |
| **Deep-Research-Agent** | novo | Task Graph + Evidence Graph + Reflexion | Melhor arquitetura teórica. Claim provenance. |
| **STORM** (Stanford) | 18K | Pre-writing + Writing. DSPy + LangGraph | Acadêmico. Multi-perspective. |
| **DuMate** (Baidu) | paper | Graph planning + recursive 2-level + rubric | SOTA 58%. Industrial. |

### O que todos têm em comum

```
1. PLANNER → decompõe query em sub-tarefas (grafo/árvore)
2. EXECUTORS → múltiplos agentes executam em paralelo
3. VERIFICATION → validação de fontes e claims
4. SYNTHESIS → agregação em relatório com citações
```

---

## 📐 Design para o aiw

### Arquitetura

```
                          ┌─────────────────────┐
                          │    User Query        │
                          └──────────┬──────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────┐
│                    RESEARCH ENGINE                              │
│                                                                │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐     │
│  │ Planner  │───▶│ Task Graph   │───▶│ Agent Swarm      │     │
│  │ (LLM)    │    │ (DAG)        │    │ (parallel exec)  │     │
│  └──────────┘    └──────────────┘    └────────┬─────────┘     │
│                                               │                │
│                    ┌──────────────────────────┘                │
│                    ▼                                           │
│  ┌──────────────────────────────────────────────────────┐     │
│  │              Research Agents                          │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │     │
│  │  │Web Search│ │Academic  │ │Technical │ │Citation │ │     │
│  │  │ Agent    │ │Search    │ │Search    │ │Crawler  │ │     │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │     │
│  └──────────────────────┬───────────────────────────────┘     │
│                         ▼                                      │
│  ┌──────────────────────────────────────────────────────┐     │
│  │              Analysis Pipeline                        │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐     │     │
│  │  │Source    │─▶│Claim     │─▶│Evidence Graph   │     │     │
│  │  │Validator │  │Extractor │  │(provenance)     │     │     │
│  │  └──────────┘ └──────────┘ └────────┬─────────┘     │     │
│  └──────────────────────────────────────┼───────────────┘     │
│                                         │                      │
│                    ┌────────────────────┘                      │
│                    ▼                                           │
│  ┌──────────────────────────────────────┐                     │
│  │  Reflexion Loop                      │                     │
│  │  "Is evidence sufficient?"           │                     │
│  │  No → re-plan, add tasks to graph    │                     │
│  │  Yes → proceed to synthesis          │                     │
│  └──────────────────────────────────────┘                     │
│                         │                                      │
│                         ▼                                      │
│  ┌──────────────────────────────────────┐                     │
│  │  Synthesizer                          │                     │
│  │  Aggregate → Report with citations   │                     │
│  └──────────────────────────────────────┘                     │
└────────────────────────────────────────────────────────────────┘
```

### Implementação

```python
# src/ai_workspace/search/research_engine.py (NOVO, substitui deep_search.py)

from dataclasses import dataclass, field
from enum import Enum
import asyncio

class ResearchPhase(Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REFLECTING = "reflecting"
    SYNTHESIZING = "synthesizing"

@dataclass
class ResearchTask:
    """Nó no grafo de pesquisa."""
    id: str
    question: str
    dependencies: list[str] = field(default_factory=list)
    agent_type: str = "web_search"  # web_search, academic, technical, citation
    status: str = "pending"
    findings: list[dict] = field(default_factory=list)
    confidence: float = 0.0

@dataclass
class EvidenceClaim:
    """Claim extraída de uma fonte com proveniência."""
    text: str
    source_url: str
    source_title: str
    relevance_score: float
    verification_status: str = "unverified"  # unverified, verified, contradicted

@dataclass
class ResearchReport:
    query: str
    summary: str
    sections: list[dict]
    claims: list[EvidenceClaim]
    sources: list[str]
    confidence: float
    trace: list[dict]  # audit trail

class ResearchEngine:
    """
    Deep Research v2 — Graph-based multi-agent research.
    
    Inspirado por: DuMate (Baidu), GPT Researcher, STORM (Stanford),
    Deep-Research-Agent, Marco (Alibaba).
    """
    
    def __init__(
        self,
        model: str = "qwen3:14b",
        provider: str = "ollama",
        max_parallel: int = 5,
        max_depth: int = 3,
    ):
        self.model = model
        self.provider = provider
        self.max_parallel = max_parallel
        self.max_depth = max_depth
    
    async def research(
        self, query: str, progress: callable = None
    ) -> ResearchReport:
        """Main entry point."""
        if progress:
            progress(ResearchPhase.PLANNING, "Building research plan...")
        
        # 1. Planejamento: construir Task Graph
        tasks = await self._plan(query)
        
        if progress:
            progress(ResearchPhase.PLANNING, f"Plan: {len(tasks)} sub-tasks")
        
        # 2. Execução: agent swarm em paralelo
        if progress:
            progress(ResearchPhase.EXECUTING, "Researching...")
        
        tasks = await self._execute_parallel(tasks, progress)
        
        # 3. Verificação: validar fontes e extrair claims
        if progress:
            progress(ResearchPhase.VERIFYING, "Verifying sources...")
        
        claims = await self._verify_and_extract(tasks)
        
        # 4. Reflexão: evidência suficiente?
        if progress:
            progress(ResearchPhase.REFLECTING, "Checking completeness...")
        
        if not await self._is_sufficient(claims, query):
            # Re-planeja: adiciona tarefas para gaps
            gap_tasks = await self._identify_gaps(claims, query)
            gap_tasks = await self._execute_parallel(gap_tasks, progress)
            tasks.extend(gap_tasks)
            claims = await self._verify_and_extract(tasks)
        
        # 5. Síntese
        if progress:
            progress(ResearchPhase.SYNTHESIZING, "Writing report...")
        
        report = await self._synthesize(query, tasks, claims)
        
        return report
    
    async def _plan(self, query: str) -> list[ResearchTask]:
        """Planner agent: decompõe query em Task Graph."""
        from ai_workspace.agents.loop import agent_loop, LoopParams, LoopPattern
        
        prompt = f"""Break down this research query into specific sub-questions.
For each, specify:
- id: short identifier
- question: the specific question to research
- dependencies: list of task IDs that must complete first (empty if independent)
- agent_type: 'web_search' (general), 'academic' (papers), 'technical' (docs/specs)

Output as JSON array. Max {self.max_parallel} parallel tasks.

Query: {query}"""
        
        params = LoopParams(task=prompt, pattern=LoopPattern.DIRECT, model=self.model, provider=self.provider)
        result = ""
        async for event in agent_loop(params):
            if event.type == "token":
                result += event.data.get("text", "")
        
        # Parse JSON plan
        import json, re
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            plan_data = json.loads(match.group())
            return [
                ResearchTask(
                    id=t["id"],
                    question=t["question"],
                    dependencies=t.get("dependencies", []),
                    agent_type=t.get("agent_type", "web_search"),
                )
                for t in plan_data
            ]
        return [ResearchTask(id="main", question=query, agent_type="web_search")]
    
    async def _execute_parallel(
        self, tasks: list[ResearchTask], progress: callable = None
    ) -> list[ResearchTask]:
        """Executa tasks em paralelo via AgentLoop ReAct."""
        # Particiona por dependências (como SPEC_DAG_EXECUTION)
        ready = [t for t in tasks if not t.dependencies]
        sem = asyncio.Semaphore(self.max_parallel)
        
        async def research_task(task: ResearchTask) -> ResearchTask:
            async with sem:
                from ai_workspace.agents.loop import agent_loop, LoopParams, LoopPattern
                
                search_prompt = f"""Research this question thoroughly. Use web search tools to find current, accurate information. Gather facts, data, and expert opinions.

Question: {task.question}

Provide findings with sources (URLs)."""
                
                params = LoopParams(
                    task=search_prompt,
                    pattern=LoopPattern.REACT,
                    tools=[WebSearchTool(), WebFetchTool()],
                    model=self.model,
                    provider=self.provider,
                    max_turns=5,
                )
                
                result = ""
                async for event in agent_loop(params):
                    if event.type == "token":
                        result += event.data.get("text", "")
                    if event.type == "tool_result":
                        task.findings.append(event.data)
                
                task.status = "completed"
                task.confidence = 0.7  # estimativa
                return task
        
        results = await asyncio.gather(*[research_task(t) for t in ready])
        return list(results)
    
    async def _verify_and_extract(self, tasks: list[ResearchTask]) -> list[EvidenceClaim]:
        """Extrai claims com proveniência dos resultados."""
        claims = []
        for task in tasks:
            for finding in task.findings:
                if "url" in finding:
                    claims.append(EvidenceClaim(
                        text=finding.get("content", "")[:500],
                        source_url=finding["url"],
                        source_title=finding.get("title", "Unknown"),
                        relevance_score=0.7,
                    ))
        return claims
    
    async def _is_sufficient(self, claims: list[EvidenceClaim], query: str) -> bool:
        """Verifica se evidência coletada é suficiente."""
        # Simplificado: pelo menos 3 fontes distintas
        unique_sources = len(set(c.source_url for c in claims))
        has_contradiction = self._detect_contradictions(claims)
        return unique_sources >= 3 and not has_contradiction
    
    async def _identify_gaps(self, claims: list[EvidenceClaim], query: str) -> list[ResearchTask]:
        """Identifica gaps e cria novas tasks."""
        # Simplificado: se menos de 3 fontes, busca mais
        return [ResearchTask(
            id="gap-1",
            question=f"Find additional sources for: {query}",
            agent_type="web_search",
        )]
    
    def _detect_contradictions(self, claims: list[EvidenceClaim]) -> bool:
        """Detecta contradições entre claims (simplificado)."""
        # Produção: usar LLM-as-judge para comparar claims
        return False
    
    async def _synthesize(
        self, query: str, tasks: list[ResearchTask], claims: list[EvidenceClaim]
    ) -> ResearchReport:
        """Synthesizer: agrega findings em relatório."""
        from ai_workspace.agents.loop import agent_loop, LoopParams, LoopPattern
        
        findings_text = "\n\n".join(
            f"## {t.question}\n" + "\n".join(
                f"- [{c.source_title}]({c.source_url}): {c.text[:300]}"
                for c in claims
                if c.source_url in [f.get("url", "") for f in t.findings]
            )
            for t in tasks
        )
        
        prompt = f"""Synthesize these research findings into a comprehensive report.

Original query: {query}

Findings:
{findings_text[:10000]}

Write a report with:
1. Executive summary (2-3 sentences)
2. Key findings (bullet points with citations)
3. Detailed analysis
4. Sources used"""
        
        params = LoopParams(task=prompt, pattern=LoopPattern.DIRECT, model=self.model, provider=self.provider)
        result = ""
        async for event in agent_loop(params):
            if event.type == "token":
                result += event.data.get("text", "")
        
        return ResearchReport(
            query=query,
            summary=result[:500],
            sections=[{"title": "Report", "content": result}],
            claims=claims,
            sources=list(set(c.source_url for c in claims)),
            confidence=0.8,
            trace=[{"phase": p.value, "tasks": len(tasks)} for p in ResearchPhase],
        )
```

### CLI

```bash
# Deep research (substitui aiw search)
aiw research "python vs rust performance 2026"

# Com opções
aiw research "query" --depth 3 --parallel 5 --model deepseek-chat

# Output NDJSON (já compatível com SPEC_OUTPUT_MODES)
aiw research "query" -o ndjson | jq 'select(.type=="phase")'
```

### Integração

| Spec | Como conecta |
|------|-------------|
| `SPEC_AGENT_LOOP.md` | Cada research agent usa ReAct loop |
| `SPEC_DAG_EXECUTION.md` | Task Graph = DAG com dependências |
| `SPEC_TOOL_EXECUTION.md` | Execução paralela com semaphore |
| `SPEC_MEMORY_TREE.md` | Evidence Graph = árvore de claims |
| `SPEC_OUTPUT_MODES.md` | NDJSON streaming de fases |
| `SPEC_SAFETY.md` | Source Validator = verification layer |

---

## 📊 Comparação com o que tínhamos

| Aspecto | deep_search.py (atual) | ResearchEngine (novo) |
|---------|----------------------|----------------------|
| Arquitetura | Pipeline 7 etapas linear | Task Graph + Agent Swarm |
| Paralelismo | Nenhum | Sim (semaphore) |
| Verificação | Source filter básico | Evidence Graph + proveniência |
| Adaptabilidade | Plano estático | Reflexion loop (re-planeja) |
| Auditabilidade | Nenhuma | Audit trail completo |
| Dependência | crewAI | AgentLoop próprio |
| Complexidade | 600 linhas monolíticas | ~200 linhas modulares |

---

## ✅ Critérios de aceitação

- [ ] `ResearchEngine` implementado com planner + executor + verifier + synthesizer
- [ ] Task Graph com dependências (DAG)
- [ ] Execução paralela de sub-tasks (Agent Swarm)
- [ ] Evidence Graph com proveniência de claims
- [ ] Reflexion loop: re-planeja se evidência insuficiente
- [ ] Substitui `deep_search.py` completamente
- [ ] CLI: `aiw research "query"` funcional
- [ ] Testes com queries conhecidas

---

## 📚 Referências

- [GPT Researcher](https://github.com/assafelovic/gpt-researcher) — 27.8K ★, planner + executor pattern
- [Deep-Research-Agent](https://github.com/YashNuhash/Deep-Research-Agent) — Task Graph + Evidence Graph
- [STORM (Stanford)](https://github.com/stanford-oval/storm) — 18K ★, multi-perspective
- [DuMate (Baidu)](https://arxiv.org/abs/2606.07299) — SOTA 58%, recursive 2-level
- [Marco (Alibaba)](https://arxiv.org/abs/2603.28376) — verification-centric, 8B > 30B
