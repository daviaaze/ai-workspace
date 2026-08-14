# Spec: Agent Observability — Code-Level Traces & State Inspection

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** Observability Gap (arXiv 2603.26942, CHI 2026), ContextLens, contextspy

---

## 🎯 O problema

O paper do CHI 2026 demonstrou: **feedback humano apenas no output = 0% de sucesso.**

O agente teve zero sucesso em tarefas de código quando o humano só via o resultado final. Por quê?

```
Código do agente          Output visível         O que humano vê
─────────────────────────────────────────────────────────────────
bug lógico sutil      →   resultado parece ok   →  "parece certo"
estado intermediário  →   mapeamento many-to-one → não detecta erro
decisão errada        →   output final ambíguo  →  aprova sem saber
```

**O gap:** Bugs estão no CÓDIGO e ESTADO DE EXECUÇÃO, mas avaliação humana é só no OUTPUT. O mapeamento many-to-one entre estados internos e outputs visíveis **impede feedback efetivo**.

Quando os pesquisadores injetaram **code-level observability** (mostraram o código gerado + estado intermediário), o agente **convergiu**. A diferença foi de 0% para funcional.

---

## 📐 Design: 3 camadas de observabilidade

### Camada 1: Execution Trace (cada passo visível)

Já coberto pelo AgentLoop events + TUI Conversation. Cada step mostra:
- 🤔 Thought (raciocínio do agente)
- 🔧 Action (tool chamada + argumentos)
- 👁 Observation (resultado da tool)
- ⏱ Timing (quanto tempo levou)

### Camada 2: Code-Level Diff (o que MUDOU no código)

Mostrar diffs exatos do que o agente escreveu/editou:

```python
# src/ai_workspace/observability/diff_tracker.py

import difflib
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileSnapshot:
    """Snapshot de um arquivo em um ponto no tempo."""
    path: str
    content: str
    timestamp: float
    agent_step: int  # qual step do agente fez a mudança

class DiffTracker:
    """Rastreia todas as mudanças em arquivos durante execução do agente."""
    
    def __init__(self):
        self.snapshots: dict[str, list[FileSnapshot]] = {}  # path → snapshots
    
    def snapshot(self, path: str, step: int):
        """Tira snapshot de um arquivo antes/depois de modificação."""
        if Path(path).exists():
            content = Path(path).read_text()
            snap = FileSnapshot(
                path=path,
                content=content,
                timestamp=time.time(),
                agent_step=step,
            )
            if path not in self.snapshots:
                self.snapshots[path] = []
            self.snapshots[path].append(snap)
    
    def get_diff(self, path: str, step_a: int, step_b: int) -> str:
        """Gera diff entre dois snapshots."""
        snaps = self.snapshots.get(path, [])
        a = next((s for s in snaps if s.agent_step == step_a), None)
        b = next((s for s in snaps if s.agent_step == step_b), None)
        if not a or not b:
            return "No snapshots available"
        
        diff = difflib.unified_diff(
            a.content.splitlines(keepends=True),
            b.content.splitlines(keepends=True),
            fromfile=f"{path} (step {step_a})",
            tofile=f"{path} (step {step_b})",
        )
        return "".join(diff)
    
    def get_summary(self) -> dict:
        """Resumo de todas as mudanças."""
        return {
            "files_modified": len(self.snapshots),
            "total_snapshots": sum(len(s) for s in self.snapshots.values()),
            "changes": {
                path: len(snaps) - 1  # número de mudanças por arquivo
                for path, snaps in self.snapshots.items()
                if len(snaps) > 1
            }
        }
```

### Camada 3: State Inspector (debugging interativo)

Permite inspecionar o estado do agente em qualquer ponto:

```python
# src/ai_workspace/observability/state_inspector.py

@dataclass
class AgentTrace:
    """Registro completo de uma execução do agente."""
    session_id: str
    task: str
    steps: list[LoopStep]
    files_modified: list[str]
    tools_called: dict[str, int]      # tool → count
    tokens_used: int
    cost: float
    errors: list[AiWError]
    safety_blocks: list[SafetyError]
    deception_warnings: list[DeceptionWarning]
    diff_tracker: DiffTracker
    timeline: list[TimelineEvent]

class TraceStore:
    """Armazena e recupera traces de execuções passadas."""
    
    def save(self, trace: AgentTrace):
        """Salva trace completo em disco/DB."""
        path = Path(f"~/.aiw/traces/{trace.session_id}.json").expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace.to_dict(), indent=2))
    
    def load(self, session_id: str) -> AgentTrace:
        """Carrega trace para análise/post-mortem."""
        ...
    
    def list_sessions(self) -> list[dict]:
        """Lista todas as sessões com resumo."""
        ...
    
    def compare(self, session_a: str, session_b: str) -> dict:
        """Compara duas execuções (útil para A/B testing de prompts/models)."""
        ...
```

### Integração no TUI: Trace Viewer (F5)

```
┌─ Trace Viewer — [session-abc123] ──────────────────────────────┐
│ Task: "Fix auth middleware bug"                   12 steps     │
│                                                                │
│ Timeline                           Filter: [all ▾]            │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ Step 1  🔧 read_file("auth.py")             0.3s  ✓       │ │
│ │ Step 2  🤔 Analyzing auth flow...            2.1s  ✓       │ │
│ │ Step 3  🔧 edit_file("auth.py" L142-156)    0.5s  ✓       │ │
│ │ Step 4  🔧 shell("pytest tests/test_auth")   3.2s  ✗       │ │
│ │   └─ Error: AssertionError: expected 200, got 401          │ │
│ │ Step 5  🤔 Test failed. Checking JWT config... 1.8s  ✓     │ │
│ │ Step 6  🔧 read_file("config.py")            0.2s  ✓       │ │
│ │   └─ ⚠ Deception: agent claimed config was correct          │ │
│ │ Step 7  🔧 edit_file("config.py" L8)         0.4s  ✓       │ │
│ │ Step 8  🔧 shell("pytest tests/test_auth")   2.8s  ✓       │ │
│ │ Step 9  ✅ Task completed                    0.0s  ✓       │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                │
│ Diff: auth.py (Step 1 → Step 3)                               │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ --- a/auth.py (step 1)                                     │ │
│ │ +++ b/auth.py (step 3)                                     │ │
│ │ @@ -142,7 +142,7 @@                                         │ │
│ │  def validate_token(token):                                 │ │
│ │ -    payload = jwt.decode(token, SECRET, algorithms=['HS256'])│ │
│ │ +    payload = jwt.decode(token, SECRET, algorithms=['HS256'],│ │
│ │ +                          options={'verify_exp': True})     │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                │
│ Tools: read_file×2  edit_file×2  shell×2  tokens: 4,230       │
│ Safety: 0 blocks  Deception: 1 warning  Cost: $0.0008         │
├────────────────────────────────────────────────────────────────┤
│ [j/k] navigate  [d] diff  [t] timeline  [s] stats  [q] back   │
└────────────────────────────────────────────────────────────────┘
```

### CLI

```bash
# Listar traces
aiw trace list                          # últimas 10 sessões
aiw trace list --errors                 # só sessões com erro

# Inspecionar
aiw trace show <session_id>             # resumo
aiw trace show <session_id> --steps     # timeline completa
aiw trace show <session_id> --diff      # todos os diffs

# Comparar
aiw trace diff <session_a> <session_b>   # A/B comparison

# Analisar (ContextLens-inspired)
aiw trace analyze <session_id>           # waste analysis
aiw trace optimize                      # sugestões de otimização
```

---

## 📊 O que isso resolve

| Problema do paper | Nossa solução |
|-------------------|---------------|
| "Feedback só no output" | Code-level diff (Camada 2) |
| "Mapeamento many-to-one" | State Inspector (Camada 3) |
| "Bug invisível no código" | Execution Trace + Diff |
| "Agente converge com code-level observability" | Trace Viewer (F5) |
| "Falta de memória cross-session" | TraceStore (persistência) |

---

## 🔗 Integração

| Spec relacionada | Como conecta |
|-----------------|-------------|
| `SPEC_TUI_V5.md` | F5 = Trace Viewer overlay |
| `SPEC_CONTEXT_MANAGEMENT.md` | F4 = Context Inspector, F5 = Trace Viewer |
| `SPEC_SAFETY.md` | Safety blocks + deception warnings no trace |
| `SPEC_EVAL_HARNESS.md` | Traces alimentam métricas de qualidade |
| `SPEC_OUTPUT_MODES.md` | `aiw trace show --output json` |

---

## ✅ Critérios de aceitação

- [ ] `DiffTracker` captura snapshots antes/depois de cada tool call
- [ ] `TraceStore` salva e recupera traces completos
- [ ] `AgentTrace` contém steps, diffs, erros, métricas
- [ ] Trace Viewer (F5) mostra timeline + diffs + stats
- [ ] CLI: `aiw trace list/show/diff/analyze`
- [ ] Integrado com AgentLoop (callback grava cada step)
- [ ] Testes: trace salvo contém todos os campos esperados

---

## 📚 Referências

- [Observability Gap (arXiv 2603.26942)](https://arxiv.org/abs/2603.26942) — CHI 2026, feedback paradox
- [ContextLens](https://github.com/HarshalSant/contextlens) — waste analysis pattern
- [contextspy](https://github.com/RimantasZ/contextspy) — live token dashboard
