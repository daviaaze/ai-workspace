# Spec: Context Management — Visualize, Curate, Optimize

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** peekctx, ContextLens, contextspy, Cursor @-mentions, ACE optimizer

---

## 🎯 O que o usuário quer

Três capacidades integradas:

1. **Ver** o que o agente está usando como contexto (arquivos, tools, histórico)
2. **Modificar** esse contexto manualmente (adicionar/remover/priorizar)
3. **Aprender** com runs passadas para otimizar automaticamente

---

## 🔍 Ferramentas existentes que fazem isso

### peekctx — "See what Claude sees"

TUI em Go que lê os arquivos JSONL do Claude Code e mostra:

```
┌─ Token Usage Bar ─────────────────────────────────────────────┐
│ ████████████████████████████████░░░░░░░░░░░░░░░░  68% (87K/128K) │
│ Compaction estimate: ~32K free                                  │
├─ File Tree ────────────────────────────────────────────────────┤
│ src/                                                           │
│ ├─ agents/                                                     │
│ │  ├─ orchestrator.py    12.4K tokens  ● healthy               │
│ │  ├─ router.py           8.2K tokens  ⚠ drifted (changed!)    │
│ │  └─ loop.py             5.1K tokens  ◐ stale (pre-compact)   │
│ ├─ core/                                                       │
│ │  └─ cost.py            15.3K tokens  ● healthy               │
│ └─ tui/                                                        │
│    └─ app.py             28.1K tokens  ⚠ drifted               │
├─ File Context (press Enter) ───────────────────────────────────│
│ │ orchestrator.py  Interaction Timeline                        │
│ │ 12:03:45  Read (full)       → 412 lines                      │
│ │ 12:04:12  Edit (L142-L156)  → "fixed auth bug"               │
│ │ 12:05:01  Grep "middleware" → 3 matches                      │
└─────────────────────────────────────────────────────────────────┘
```

**Funcionalidades:**
- Token usage bar com estimativa de compactação
- File tree com token counts
- Drift detection (⚠ arquivo mudou no disco desde que foi lido)
- Stale detection (◐ arquivo só conhecido via summary de compactação)
- Interaction timeline (cada read/write/edit no arquivo)
- Live watch mode (auto-refresh a cada 2s)
- 8 temas + custom themes
- Filtros: all / drifted / stale / problems

### ContextLens — "py-spy for LLM prompts"

Profiler Python que analisa traces de agentes:

```
Context Composition by Region
Region              Tokens    Cost (USD)   Share
assistant_message   11,490    $0.0345      ###....... 25.5%
tool_result         10,333    $0.0310      ##........ 22.9%
tool_schema          9,450    $0.0284      ##........ 21.0%
retrieved_content    5,805    $0.0174      #......... 12.9%
user_message         4,740    $0.0142      #......... 10.5%
system               3,240    $0.0097       #.........  7.2%
TOTAL               45,058    $0.1352

Re-billing: 43,185 tokens (95.8%) re-billing waste → $0.1296 recoverable

Top Waste Findings
#   Type              Sev.   Wasted Tokens  Cost      Fix
1   duplicate         medium     7,084     $0.0213   Cache or externalize...
2   redundant_ret     medium     5,805     $0.0174   Use a re-ranker...
3   unused_schema     low        3,150     $0.0095   Remove send_email...
```

**5 detectores de desperdício:**
| Detector | O que acha |
|----------|-----------|
| Duplicate | Mesmo bloco re-enviado verbatim em múltiplos turns |
| Near-Duplicate | >85% similaridade Jaccard entre blocos distintos |
| Stale Tool Result | Output de tool nunca referenciado depois |
| Unused Tool Schema | Tool definida todo turn mas nunca chamada |
| Redundant Retrieval | Chunk recuperado com <15% overlap com output |

### contextspy — "Live token dashboard"

Proxy MITM que intercepta requests LLM e mostra dashboard web:

```
Session: coding-2026-06-18
┌─────────────────────────────────────────────────────────┐
│ Requests: 47  │  Total tokens: 1.2M  │  Cost: $0.34    │
├─────────────────────────────────────────────────────────┤
│ Token Composition Over Time                             │
│ ▓ tool_results    ▓ system    ▓ user    ▓ assistant      │
│ ████████████████████████████████████████████████████     │
│                                                         │
│ Per-Request Breakdown                                    │
│ #23  12.4K tokens  ████████░░░░  62% tool_results       │
│ #24  18.7K tokens  ████████████  78% tool_results  ⚠    │
│ #25   8.1K tokens  █████░░░░░░░  45% assistant           │
└─────────────────────────────────────────────────────────┘
```

### Cursor — Context ring + @-mentions

```
┌─ Context Ring (ao lado do input) ───────────────────────┐
│ ○○○○○○○○○●○○○  87K/200K tokens                         │
│                                                          │
│ Breakdown:                                               │
│   System prompt:     12.4K                               │
│   Conversation:      34.2K                               │
│   Rules (.mdc):       2.1K                               │
│   Open files:        28.7K                               │
│   Tools:              9.6K                               │
│                                                          │
│ @-mentions para controle granular:                       │
│   @Code(func_name)   — só a função                      │
│   @Files(path)       — arquivo inteiro                   │
│   @Folders(path)     — mapa do diretório (sem conteúdo)  │
└──────────────────────────────────────────────────────────┘
```

---

## 📐 Design para o aiw

### 1. Context Inspector (TUI overlay — F4)

Baseado no peekctx. Um overlay no TUI v5 que mostra:

```
┌─ Context Inspector ─ [agent-1] ──────────────────────────────┐
│ Token Usage                                                  │
│ ████████████████████████████░░░░░░  78% (99K/128K)          │
│ Compaction at 80% → ~2.5K free before auto-compact           │
│                                                              │
│ Files in Context                          tokens  status     │
│ ├─ src/agents/orchestrator.py             12.4K   ⚠ drifted  │
│ ├─ src/agents/router.py                    8.2K   ● ok       │
│ ├─ src/tui/app.py                         28.1K   ⚠ drifted  │
│ ├─ docs/specs/SPEC_AGENT_LOOP.md          15.3K   ● ok       │
│ └─ [summary from compaction]               3.1K   ◐ stale    │
│                                                              │
│ Tools Used This Session                                       │
│ ├─ read_file        12 calls   45.2K tokens  22% of context  │
│ ├─ grep              5 calls    2.1K tokens   1%             │
│ ├─ write_file        3 calls    1.8K tokens   1%             │
│ └─ shell             2 calls    8.4K tokens   4%  ⚠ high     │
│                                                              │
│ [a] add file  [d] remove file  [p] prioritize  [r] refresh   │
│ [t] sort by tokens  [s] sort by status  [f] filter  [q] back │
└──────────────────────────────────────────────────────────────┘
```

### 2. Context Curator (comandos do usuário)

O usuário pode modificar o que o agente "vê":

```python
# Comandos no TUI (via / ou atalhos)

# Adicionar arquivo ao contexto
/ctx add src/auth.py              # adiciona arquivo específico
/ctx add src/agents/              # adiciona diretório (mapa, não conteúdo)
/ctx add @function login          # adiciona só uma função

# Remover do contexto
/ctx remove src/tui/app.py        # remove arquivo (não será re-lido)
/ctx remove --stale               # remove todos os arquivos stale
/ctx remove --large 20k           # remove arquivos > 20KB

# Priorizar (pin)
/ctx pin src/agents/orchestrator.py   # nunca será removido na compactação
/ctx unpin src/tui/app.py

# Ver contexto atual
/ctx show                          # abre Context Inspector (F4)
/ctx stats                         # resumo rápido: 12 files, 87K tokens, 2 drifted

# Limpar contexto
/ctx clear                         # reset completo (próxima pergunta começa limpo)
/ctx compact                       # força compactação agora
```

Implementação:

```python
# src/ai_workspace/agents/context_curation.py

@dataclass
class ContextPolicy:
    """User-defined rules for what goes into context."""
    pinned_files: set[str] = field(default_factory=set)      # nunca remove
    excluded_files: set[str] = field(default_factory=set)    # nunca inclui
    max_file_size: int = 50_000                               # skip files > 50KB
    max_total_tokens: int = 100_000                           # soft limit
    auto_exclude_patterns: list[str] = field(default_factory=list)  # globs

class ContextCurator:
    """Manages what files/tools/results go into agent context."""
    
    def __init__(self, policy: ContextPolicy = None):
        self.policy = policy or ContextPolicy()
        self._files_in_context: dict[str, FileContext] = {}
        self._tool_stats: dict[str, ToolStats] = {}
    
    def should_include_file(self, path: str, size: int) -> bool:
        """Decide if a file should be included in context."""
        if path in self.policy.pinned_files:
            return True
        if path in self.policy.excluded_files:
            return False
        if size > self.policy.max_file_size:
            return False
        for pattern in self.policy.auto_exclude_patterns:
            if fnmatch(path, pattern):
                return False
        return True
    
    def add_file(self, path: str, content: str):
        """Track a file that was added to context."""
        self._files_in_context[path] = FileContext(
            path=path,
            tokens=len(content) // 4,
            added_at=time.time(),
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        )
    
    def check_drift(self) -> list[str]:
        """Return files that changed on disk since added to context."""
        drifted = []
        for path, fc in self._files_in_context.items():
            if Path(path).exists():
                current = Path(path).read_text()
                current_hash = hashlib.sha256(current.encode()).hexdigest()
                if current_hash != fc.content_hash:
                    drifted.append(path)
        return drifted
    
    def record_tool_usage(self, tool_name: str, tokens: int):
        """Track how many tokens each tool contributes."""
        if tool_name not in self._tool_stats:
            self._tool_stats[tool_name] = ToolStats(name=tool_name)
        self._tool_stats[tool_name].calls += 1
        self._tool_stats[tool_name].total_tokens += tokens
    
    def get_context_summary(self) -> dict:
        """Get current context state for display."""
        total_tokens = sum(f.tokens for f in self._files_in_context.values())
        return {
            "files": len(self._files_in_context),
            "total_tokens": total_tokens,
            "drifted": self.check_drift(),
            "pinned": len(self.policy.pinned_files),
            "tool_stats": self._tool_stats,
        }
```

### 3. Context Optimizer (aprende com histórico)

Baseado no ContextLens. Analisa runs passadas e sugere otimizações:

```python
# src/ai_workspace/agents/context_optimizer.py

@dataclass
class OptimizationReport:
    total_tokens: int
    wasted_tokens: int
    recoverable_cost: float
    findings: list[Finding]
    suggestions: list[str]

class ContextOptimizer:
    """Analyze past agent runs to find context waste."""
    
    def analyze_session(self, session_id: str) -> OptimizationReport:
        """Analyze a single session trace."""
        trace = self._load_trace(session_id)
        
        findings = []
        
        # Detector 1: Duplicate blocks
        findings.extend(self._find_duplicates(trace))
        
        # Detector 2: Stale tool results
        findings.extend(self._find_stale_results(trace))
        
        # Detector 3: Unused tools
        findings.extend(self._find_unused_tools(trace))
        
        # Detector 4: Large files that could be chunked
        findings.extend(self._find_large_files(trace))
        
        # Detector 5: Tools generating most context
        findings.extend(self._find_heavy_tools(trace))
        
        wasted = sum(f.wasted_tokens for f in findings)
        suggestions = self._generate_suggestions(findings)
        
        return OptimizationReport(
            total_tokens=trace.total_tokens,
            wasted_tokens=wasted,
            recoverable_cost=trace.total_cost * (wasted / trace.total_tokens),
            findings=findings,
            suggestions=suggestions,
        )
    
    def _find_heavy_tools(self, trace) -> list[Finding]:
        """Find tools that generate disproportionate context."""
        tool_tokens = {}
        for event in trace.events:
            if event.type == "tool_result":
                tool_tokens[event.tool] = tool_tokens.get(event.tool, 0) + event.tokens
        
        total = sum(tool_tokens.values())
        findings = []
        for tool, tokens in sorted(tool_tokens.items(), key=lambda x: x[1], reverse=True):
            pct = tokens / total * 100
            if pct > 20:  # tool representa >20% do contexto
                findings.append(Finding(
                    type="heavy_tool",
                    severity="medium" if pct > 30 else "low",
                    wasted_tokens=tokens,
                    description=f"{tool} generates {pct:.0f}% of context ({tokens:,} tokens)",
                    fix=f"Consider chunking {tool} output or using --max-results flag",
                ))
        return findings
```

### 4. Integração no TUI v5

```
┌─ Header ──────────────────────────────────────────────────────────┐
│  aiw  ~/project  qwen3:14b  ⚡1 agent  💰$0.005  ●●●●○○○○ 78%  │
│                                                         ↑        │
│                                              context ring (Cursor) │
├────────────────────────────────────────────────────────────────────┤
│  Conversation                                                      │
│  ...                                                               │
├────────────────────────────────────────────────────────────────────┤
│  /ctx add  /ctx remove  /ctx stats  /ctx compact    F4 inspect  │
└────────────────────────────────────────────────────────────────────┘
```

Overlays:
- `F4` → Context Inspector (baseado no peekctx)
- `/ctx show` → mesma tela
- `/ctx optimize` → roda ContextOptimizer e mostra relatório

---

## 📊 Fluxo de aprendizado

```
Session 1: 45K tokens, 96% waste (ContextLens)
  │
  ▼
Optimizer: "read_file gera 42% do contexto. Shell gera 18%."
  │
  ▼
User action: /ctx policy max_file_size=20000  (reduz arquivos grandes)
             /ctx policy auto_exclude="*.lock,*.min.js"
  │
  ▼
Session 2: 28K tokens, 72% waste (melhorou)
  │
  ▼
Optimizer: "Ainda 15% em tool_results duplicados. Sugestão: cache."
  │
  ▼
Session 3: 18K tokens, 45% waste
  │
  ▼
... converge para ótimo ao longo do tempo
```

---

## ✅ Critérios de aceitação

### Context Inspector (F4 overlay)
- [ ] Mostra token usage bar com estimativa de compactação
- [ ] Lista arquivos no contexto com tokens e status (ok/drifted/stale)
- [ ] Mostra tools usadas com contagem e % do contexto
- [ ] Detecta drift (arquivo mudou no disco)
- [ ] Detecta stale (pré-compactação)
- [ ] Filtros: all / drifted / stale / problems
- [ ] Ordenação: por tokens / status / path

### Context Curator (/ctx commands)
- [ ] `/ctx add <path>` — adiciona arquivo ao contexto
- [ ] `/ctx remove <path>` — remove arquivo
- [ ] `/ctx pin <path>` — marca como permanente
- [ ] `/ctx stats` — resumo rápido
- [ ] `/ctx policy` — configura regras automáticas

### Context Optimizer (aprendizado)
- [ ] Analisa trace de sessão e detecta desperdício
- [ ] 5 detectores: duplicates, stale results, unused tools, large files, heavy tools
- [ ] Gera sugestões acionáveis ("reduza X para ganhar Y tokens")
- [ ] CLI: `aiw context optimize <session_id>`

### Context Ring (header)
- [ ] Indicador visual de uso de contexto (●●●●○○○○ 78%)
- [ ] Clicável para abrir breakdown rápido

---

## 📚 Referências

- [peekctx](https://github.com/jeremyengland/peekctx) — TUI context inspector for Claude Code
- [ContextLens](https://github.com/HarshalSant/contextlens) — LLM prompt profiler, 5 waste detectors
- [contextspy](https://github.com/RimantasZ/contextspy) — live token dashboard proxy
- [Cursor Context Management](https://cursor.com/docs/agent/prompting) — context ring, @-mentions
- [ACE optimizer](https://github.com/ace-agent/ace) — system prompt optimization
