# Spec: Graph-Structured Execution — DAG-based Agent Orchestration

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** GraSP (arXiv 2604.17870, Apr 2026), FlowBank (arXiv 2606.11290, Jun 2026)

---

## 🎯 O problema com ReAct e Plan-Execute

ReAct é linear: pensa → age → observa → repete. Se o passo 3 falha, volta do zero.
Plan-Execute decouple: planeja tudo → executa. Se o plano fica obsoleto, replaneja tudo.

**Problema:** replanejamento é O(N) — refaz tudo. Para tarefas com 20+ passos, isso é proibitivo.

---

## 📐 GraSP: Execução como DAG

Em vez de uma lista plana de passos, representar a tarefa como um **grafo direcionado acíclico (DAG)**:

```
Plano tradicional (flat):
  Step1 → Step2 → Step3 → Step4 → Step5

Plano GraSP (DAG):
        ┌─────────┐
        │  Plan   │  "Add auth to API"
        └────┬────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
  ┌─────┐ ┌─────┐ ┌─────┐
  │  A  │ │  B  │ │  C  │  A: Create middleware
  │     │ │     │ │     │  B: Add JWT validation
  └──┬──┘ └──┬──┘ └──┬──┘  C: Write tests
     │       │       │
     ▼       ▼       │
  ┌─────┐ ┌─────┐    │      D: Update routes (depende de A e B)
  │  D  │ │  E  │◄───┘      E: Run test suite (depende de B e C)
  └──┬──┘ └─────┘
     │
     ▼
  ┌─────┐
  │  F  │                    F: Deploy (depende de D)
  └─────┘

Vantagens:
- A, B, C executam em PARALELO (sem dependências entre si)
- Se B falha, só D é afetado. A e C continuam.
- Replanejamento é local: O(d^h) em vez de O(N)
  (d = depth da sub-árvore afetada, h = branching factor)
```

### Os 4 estágios do GraSP

```
1. Memory-conditioned retrieval
   └→ Busca skills relevantes no repositório

2. DAG compilation
   └→ Compila skills em DAG com pré-condições e efeitos

3. Verified execution + local repair
   └→ Executa DAG. Se nó falha, repara só a sub-árvore afetada

4. Confidence-based routing
   └→ Se DAG inteiro falha, tenta abordagem alternativa
```

### Implementação para o aiw

```python
# src/ai_workspace/agents/dag_executor.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class NodeStatus(Enum):
    PENDING = "pending"
    READY = "ready"        # dependências satisfeitas
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"    # pulado porque depende de nó falho

@dataclass
class DAGNode:
    """Nó no grafo de execução."""
    id: str
    description: str              # "Create auth middleware"
    tool: str                     # "write_file", "shell", etc.
    tool_args: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # IDs dos nós que devem executar antes
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 2

@dataclass
class DAGPlan:
    """Plano de execução como DAG."""
    task: str
    nodes: dict[str, DAGNode]     # node_id → node
    edges: list[tuple[str, str]]  # (from_id, to_id)
    
    def get_ready_nodes(self) -> list[DAGNode]:
        """Retorna nós cujas dependências estão satisfeitas."""
        ready = []
        for node in self.nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            deps_ok = all(
                self.nodes[dep].status == NodeStatus.COMPLETED
                for dep in node.dependencies
            )
            if deps_ok:
                ready.append(node)
        return ready
    
    def get_affected_nodes(self, failed_node_id: str) -> list[str]:
        """Retorna nós afetados pela falha (para reparo local)."""
        affected = {failed_node_id}
        # BFS a partir do nó falho para encontrar todos os downstream
        queue = [failed_node_id]
        while queue:
            current = queue.pop(0)
            for nid, node in self.nodes.items():
                if current in node.dependencies and nid not in affected:
                    affected.add(nid)
                    queue.append(nid)
        return list(affected)

class DAGExecutor:
    """Executa planos como DAG com paralelismo e reparo local."""
    
    async def execute(self, plan: DAGPlan) -> dict:
        """Executa o DAG. Retorna resultados por nó."""
        results = {}
        
        while True:
            ready = plan.get_ready_nodes()
            if not ready:
                # Verifica se terminou ou travou
                pending = [n for n in plan.nodes.values() if n.status == NodeStatus.PENDING]
                if not pending:
                    break  # todos processados
                # Alguns nós têm dependências quebradas
                for n in pending:
                    n.status = NodeStatus.SKIPPED
                break
            
            # Executa nós prontos em paralelo
            tasks = [self._execute_node(node) for node in ready]
            node_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for node, result in zip(ready, node_results):
                if isinstance(result, Exception):
                    node.status = NodeStatus.FAILED
                    node.error = str(result)
                    # Reparo local: reseta só a sub-árvore afetada
                    if node.retries < node.max_retries:
                        affected = plan.get_affected_nodes(node.id)
                        for nid in affected:
                            plan.nodes[nid].status = NodeStatus.PENDING
                            plan.nodes[nid].retries += 1
                else:
                    node.status = NodeStatus.COMPLETED
                    node.result = str(result)
                    results[node.id] = result
        
        return results
    
    async def _execute_node(self, node: DAGNode) -> str:
        """Executa um nó individual (usa AgentLoop internamente)."""
        # Chama o AgentLoop com a tool específica
        ...
    
    @staticmethod
    async def compile_plan(task: str, tools: list, model: str = "qwen3:14b") -> DAGPlan:
        """Usa LLM para compilar tarefa em DAG."""
        prompt = f"""Break down this task into a DAG of subtasks.
For each subtask, specify:
- id: unique identifier
- description: what to do
- tool: which tool to use
- dependencies: list of subtask IDs that must complete first

Output as JSON:
{{
  "nodes": [
    {{"id": "A", "description": "...", "tool": "write_file", "dependencies": []}},
    {{"id": "B", "description": "...", "tool": "shell", "dependencies": ["A"]}}
  ]
}}

Task: {task}
Available tools: {', '.join(t.name for t in tools)}
"""
        # ... chama LLM, parse JSON, constrói DAGPlan
        ...
```

---

## 📊 FlowBank: Otimização de workflows

FlowBank complementa GraSP com uma abordagem de **precompute-and-reuse**:

```
Fase 1: DiverseFlow — gera portfólio diverso de workflows
  └→ Explora espaço de soluções, cobre queries sub-atendidas

Fase 2: CuraFlow — comprime portfólio, remove redundância
  └→ Mantém conjunto mínimo de workflows complementares

Fase 3: Matching — roteia query → melhor workflow
  └→ Bipartite graph: query-workflow edge prediction
```

### Como aplicar ao aiw

Nosso `suggest_pattern()` atual é uma heurística simples. Com FlowBank:

```python
class WorkflowBank:
    """Portfólio de workflows otimizados (FlowBank-inspired)."""
    
    def __init__(self):
        self.workflows: dict[str, DAGPlan] = {}  # workflow_id → DAG
        self.query_workflow_scores: dict = {}     # histórico de sucesso
    
    def match(self, task: str) -> DAGPlan:
        """Encontra o melhor workflow para a tarefa."""
        # Similaridade semântica + histórico de sucesso
        ...
    
    def learn(self, task: str, workflow: DAGPlan, success: bool):
        """Aprende com resultado para melhorar matching futuro."""
        ...
```

---

## 📊 Resultados dos papers

**GraSP vs baselines:**
| Baseline | GraSP improvement |
|----------|------------------|
| ReAct | +19 pontos (reward) |
| Reflexion | +15 pontos |
| Plan-Execute | +12 pontos |

**FlowBank vs alternatives:**
| Métrica | Single workflow | Per-query synthesis | **FlowBank** |
|---------|----------------|--------------------|-------------|
| Performance | baseline | +5% | **+12%** |
| Latency | 1x | 3x (sintetiza toda vez) | **1.2x** (precomputado) |
| Cost | 1x | 2.5x | **1.1x** |

---

## 🔗 Integração com specs existentes

| Spec | Como GraSP/FlowBank complementa |
|------|-------------------------------|
| `SPEC_AGENT_LOOP.md` | Adiciona modo `DAG` ao `LoopPattern` |
| `SPEC_TOOL_EXECUTION.md` | Paralelismo natural do DAG (nós independentes) |
| `SPEC_MEMORY_TREE.md` | DAG + árvore de estado = execução estruturada + memória estruturada |

---

## ✅ Critérios de aceitação

- [ ] `DAGPlan` e `DAGNode` implementados
- [ ] `DAGExecutor.execute()` com paralelismo e reparo local
- [ ] `DAGExecutor.compile_plan()` gera DAG a partir de linguagem natural
- [ ] Reparo local: falha no nó X → só reseta sub-árvore de X
- [ ] `WorkflowBank` com match + learn
- [ ] Integrado como `LoopPattern.DAG` no AgentLoop
- [ ] Testes com tarefas complexas (10+ passos com dependências)

---

## 📚 Referências

- [GraSP paper (arXiv 2604.17870)](https://arxiv.org/abs/2604.17870) — graph-structured skills, Apr 2026
- [FlowBank paper (arXiv 2606.11290)](https://arxiv.org/pdf/2606.11290) — query-adaptive workflows, Jun 2026
