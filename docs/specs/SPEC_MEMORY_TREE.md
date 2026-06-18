# Spec: Memory as Execution State — Hierarchical State Tree

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** Mage (arXiv 2606.06090, Microsoft + USTC 2026), AutoAgent (arXiv 2603.09716)

---

## 🎯 O problema

RAG tradicional organiza memória por **similaridade semântica**. Funciona pra QA, mas **falha para agentes**. Por quê?

```
Agente executando tarefa longa (100+ passos):

Passo 1: lê auth.py         ─┐
Passo 2: edita auth.py       ├─ branch A (correto)
Passo 3: testa auth.py      ─┘
Passo 4: lê database.py     ─┐
Passo 5: edita database.py   ├─ branch A
Passo 6: ERRO na migration  ─┘
Passo 7: rollback            ─┐
Passo 8: tenta approach B    ├─ branch B (correção)
Passo 9: edita database.py   ─┘

RAG tradicional recupera "auth.py" e "database.py" por similaridade.
Mistura passos do branch A (errados) com branch B (corrigidos).
Resultado: contaminação → agente repete o erro.
```

**O paper Mage mostra:** sistemas baseados em similaridade têm desempenho **pior** que simplesmente manter tudo em contexto. Eles fragmentam a trajetória de execução e misturam traces válidos com errôneos.

---

## 📐 A solução: Árvore de estado de execução

Em vez de um flat vector store, organizar a memória como uma **árvore hierárquica** onde cada nó representa um estado de execução:

```
Root
├── Subgoal 1: "Fix auth middleware"
│   ├── Step 1.1: read auth.py
│   ├── Step 1.2: edit auth.py (L142-L156)
│   └── Step 1.3: test → ✓ PASSED
│       └── Summary: "Auth middleware fixed. Changed JWT validation..."
│
├── Subgoal 2: "Update database schema"
│   ├── Step 2.1: read database.py
│   ├── Step 2.2: edit database.py ──→ ❌ ERROR: migration failed
│   │   └── Branch B (recovery):
│   │       ├── Step 2.3b: rollback migration
│   │       └── Step 2.4b: new approach → ✓ PASSED
│   │           └── Summary: "Schema updated via ALTER TABLE instead of..."
│   └── Summary: "Database schema updated. Failed approach A (migration),
│                  succeeded with approach B (ALTER TABLE)."
│
└── Active path: Root → Subgoal 1 → Subgoal 2 (Branch B)
    Context = summaries dos subgoals completos + trace recente do ativo
```

### Quatro operações (do paper)

| Operação | O que faz | Quando |
|----------|-----------|--------|
| **Grow** | Adiciona novos passos ao nó ativo | Toda tool call |
| **Compress** | Sumariza subgoal completo, libera tokens | Subgoal concluído |
| **Maintain** | Valida summaries periodicamente | Background |
| **Revise** | Restaura boundary, cria novo branch | Erro detectado |

### Integração com Context Compaction

```
Nossa spec existente (SPEC_CONTEXT_COMPACTION.md):
  L1: Tool Result Cap
  L2: Time-based Cleanup  
  L3: Summarize (LLM rápido)

Nova spec (Mage):
  L4: Hierarchical State Tree ← adiciona estrutura
       Em vez de summarizar tudo flat, organiza em árvore
       Subgoals completos viram summaries
       Branches de erro são isolados
```

### Implementação

```python
# src/ai_workspace/agents/memory_tree.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class NodeStatus(Enum):
    ACTIVE = "active"        # Em execução
    COMPLETED = "completed"  # Sucesso
    FAILED = "failed"        # Erro (branch morto)
    COMPRESSED = "compressed"  # Sumarizado

@dataclass
class StateNode:
    """Nó na árvore de estado de execução."""
    id: str
    parent_id: Optional[str]
    subgoal: str                      # "Fix auth middleware"
    status: NodeStatus = NodeStatus.ACTIVE
    steps: list[dict] = field(default_factory=list)   # passos brutos
    summary: str = ""                  # preenchido ao comprimir
    tokens: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    children: list['StateNode'] = field(default_factory=list)

class MemoryTree:
    """Árvore hierárquica de estado de execução (baseado no Mage)."""
    
    def __init__(self, max_active_tokens: int = 80_000):
        self.root = StateNode(id="root", parent_id=None, subgoal="Session")
        self.active_path: list[str] = ["root"]  # IDs do caminho ativo
        self.max_active_tokens = max_active_tokens
        self._node_index: dict[str, StateNode] = {"root": self.root}
    
    def grow(self, step: dict) -> None:
        """Adiciona passo ao nó ativo."""
        current = self._get_active_node()
        current.steps.append(step)
        current.tokens += len(str(step)) // 4
    
    def start_subgoal(self, description: str) -> str:
        """Inicia novo subgoal como filho do nó ativo."""
        parent = self._get_active_node()
        node = StateNode(
            id=f"subgoal-{len(self._node_index)}",
            parent_id=parent.id,
            subgoal=description,
        )
        parent.children.append(node)
        self._node_index[node.id] = node
        self.active_path.append(node.id)
        return node.id
    
    def complete_subgoal(self, success: bool = True) -> str:
        """Finaliza subgoal ativo e gera summary."""
        node = self._get_active_node()
        node.status = NodeStatus.COMPLETED if success else NodeStatus.FAILED
        node.summary = self._generate_summary(node)
        # Sobe um nível
        if len(self.active_path) > 1:
            self.active_path.pop()
        return node.summary
    
    def revise(self, error_description: str) -> str:
        """Cria branch de recovery a partir do nó atual."""
        parent = self._get_active_node()
        branch = StateNode(
            id=f"branch-{len(self._node_index)}",
            parent_id=parent.id,
            subgoal=f"Recovery: {error_description[:80]}",
        )
        parent.children.append(branch)
        self._node_index[branch.id] = node
        self.active_path[-1] = branch.id
        return branch.id
    
    def get_context(self) -> str:
        """Constrói contexto para o LLM a partir do caminho ativo."""
        parts = []
        tokens = 0
        
        for node_id in self.active_path:
            node = self._node_index[node_id]
            if node.status == NodeStatus.COMPRESSED:
                # Subgoal completo → só o summary
                parts.append(f"[Subgoal: {node.subgoal}]\n{node.summary}")
                tokens += len(node.summary) // 4
            elif node.status == NodeStatus.ACTIVE:
                # Subgoal ativo → passos recentes + summaries dos irmãos
                recent = node.steps[-10:]  # últimos 10 passos
                parts.append(f"[Active: {node.subgoal}]\n" + 
                            "\n".join(str(s) for s in recent))
                tokens += len(str(recent)) // 4
            # FAILED nodes são ignorados (não contaminam)
        
        # Se estourar budget, comprimir subgoals completos
        if tokens > self.max_active_tokens:
            self._compress_completed()
        
        return "\n\n".join(parts)
    
    def _compress_completed(self) -> None:
        """Comprime subgoals completos para liberar tokens."""
        for node_id, node in self._node_index.items():
            if node.status == NodeStatus.COMPLETED and node.summary == "":
                node.summary = self._generate_summary(node)
                node.status = NodeStatus.COMPRESSED
                node.steps = []  # libera passos brutos
    
    def _get_active_node(self) -> StateNode:
        return self._node_index[self.active_path[-1]]
    
    def _generate_summary(self, node: StateNode) -> str:
        """Gera summary de um subgoal (usa LLM rápido)."""
        # Similar ao L3 do ContextCompactor
        steps_text = "\n".join(str(s)[:200] for s in node.steps)
        # ... chama modelo rápido para summarizar
        return f"Completed {node.subgoal}. {len(node.steps)} steps."
```

---

## 📊 Resultados do paper

| Métrica | RAG tradicional | Long-context | **Mage** |
|---------|----------------|-------------|----------|
| Task success rate | baseline | +3-5pp | **+7.8-20.4pp** |
| Token consumption | médio | alto | **-55.1% vs long-context** |

---

## 🔗 Como isso melhora o aiw

| Spec existente | Como Mage complementa |
|---------------|----------------------|
| `SPEC_CONTEXT_COMPACTION.md` | Adiciona estrutura hierárquica (não só flat) |
| `SPEC_CONTEXT_MANAGEMENT.md` | Visualização da árvore no Context Inspector |
| `SPEC_RAG.md` | RAG para conhecimento estático, Mage para estado dinâmico |
| `SPEC_EVAL_HARNESS.md` | MemoryArena benchmark para avaliar memória |

---

## ✅ Critérios de aceitação

- [ ] `MemoryTree` implementado com 4 operações (grow, start_subgoal, complete_subgoal, revise)
- [ ] `get_context()` retorna apenas caminho ativo + summaries
- [ ] Branches de erro são isolados (não contaminam branches bons)
- [ ] Compressão automática quando tokens > limite
- [ ] Integrado com `AgentLoop` (state.memory_tree)
- [ ] Testes: `tests/test_agents/test_memory_tree.py`

---

## 📚 Referências

- [Mage paper (arXiv 2606.06090)](https://arxiv.org/html/2606.06090v1) — Microsoft + USTC, Jun 2026
- [AutoAgent paper (arXiv 2603.09716)](https://arxiv.org/pdf/2603.09716) — elastic memory orchestration
