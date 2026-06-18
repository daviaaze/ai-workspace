# Spec: Context Compaction — Progressive Compression Pipeline

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** Claude Code 5-level pipeline, `src/services/compact/` (3,960 lines), pi contextTransform

---

## 🎯 Motivação

Janela de contexto é finita (128K tokens no qwen3, 1M no Claude). Uma sessão real de coding gera múltiplos disso: dezenas de file reads, centenas de tool calls, milhares de linhas de output. Sem compactação, o agente:
- Esquece arquivos que já editou
- Re-lê conteúdo que já viu
- Contradiz decisões anteriores
- Estoura o limite e crasha

## 📐 O que Claude Code faz (referência)

Claude Code tem um pipeline de **5 níveis progressivos** — do mais barato ao mais caro:

```
Message History
  │
  ├─ L1: Tool Result Budget (grátis)
  │     Resultado > 50KB? → salva em disco, mantém 2KB preview
  │
  ├─ L2: History Snip (grátis)
  │     Remove wrappers repetitivos, scaffolding morto
  │
  ├─ L3: Microcompact (grátis, dual-path)
  │     Cache frio → modifica mensagens diretamente
  │     Cache quente → usa cache_edits da API (preserva cache)
  │
  ├─ L4: Context Collapse (grátis, reversível)
  │     Projeção não-destrutiva ~90% utilização
  │     Mensagens originais preservadas, view filtrada
  │
  └─ L5: Autocompact (1 API call, irreversível)
        Fork child agent → summariza em 9 seções XML
        Chain-of-Thought scratchpad → descarta raciocínio, mantém summary
```

**Princípios:**
1. **Progressivo** — mais barato primeiro, mais caro só se necessário
2. **Não-destrutivo quando possível** — L4 é reversível, L5 é último recurso
3. **Cache-aware** — L3 decide entre dois caminhos baseado em estado do cache
4. **Structured output** — L5 produz 9 seções padronizadas

---

## 📐 Design para o aiw

Nosso pipeline será mais simples (3 níveis iniciais), adequado ao nosso contexto (modelos locais, sem prompt cache pago):

```
Message History
  │
  ├─ L1: Tool Result Cap (grátis, local)
  │     tool_result > 10KB? → truncate para 2KB + nota "[truncated]"
  │     Arquivos grandes → salvar em /tmp/.aiw/sessions/{id}/tool-results/
  │
  ├─ L2: Time-based Cleanup (grátis, local)
  │     Tool results > 10 minutos atrás → "[Old tool result cleared]"
  │     Mantém N mais recentes (default: 20)
  │
  └─ L3: Summarize (1 LLM call, destrutivo)
        Quando tokens > 80% do limite → chama modelo rápido para summarizar
        Prompt: "Summarize this conversation. Keep: user requests, key decisions,
                 files modified, errors encountered, pending tasks."
        Output: structured summary que substitui mensagens antigas
```

### Implementação

```python
# src/ai_workspace/agents/compaction.py

from dataclasses import dataclass, field
from typing import Literal
import time
import json
from pathlib import Path

@dataclass
class CompactionConfig:
    max_tokens: int = 128_000           # Limite da janela
    compact_at_pct: float = 0.80        # Dispara L3 aos 80%
    tool_result_max_chars: int = 10_000 # L1: cap por resultado
    tool_result_preview_chars: int = 2_000  # L1: preview mantido
    tool_result_ttl_seconds: int = 600  # L2: 10 minutos
    max_recent_results: int = 20        # L2: manter N recentes
    summary_model: str = "qwen3.5:9b"  # L3: modelo rápido e barato
    session_dir: str = "/tmp/.aiw/sessions"

class ContextCompactor:
    """Progressive context compaction for long agent sessions."""
    
    def __init__(self, config: CompactionConfig = None):
        self.config = config or CompactionConfig()
        self._tool_timestamps: dict[str, float] = {}  # tool_id → timestamp
    
    def compact(self, messages: list[dict], current_tokens: int) -> list[dict]:
        """Apply progressive compaction. Returns compacted messages."""
        
        # L1: Cap tool results
        messages = self._cap_tool_results(messages)
        
        # L2: Clear old tool results
        messages = self._clear_old_results(messages)
        
        # L3: Summarize if near limit
        pct = current_tokens / self.config.max_tokens
        if pct >= self.config.compact_at_pct:
            messages = self._summarize(messages)
        
        return messages
    
    def _cap_tool_results(self, messages: list[dict]) -> list[dict]:
        """L1: Cap large tool results. Save full output to disk."""
        result = []
        for msg in messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if len(content) > self.config.tool_result_max_chars:
                    tool_id = msg.get("tool_call_id", "unknown")
                    # Save full output
                    self._save_tool_result(tool_id, content)
                    # Keep preview
                    msg = {**msg, "content": (
                        content[:self.config.tool_result_preview_chars] +
                        f"\n... [truncated {len(content)} chars. Full output: "
                        f"{self.config.session_dir}/{tool_id}.txt]"
                    )}
            result.append(msg)
        return result
    
    def _clear_old_results(self, messages: list[dict]) -> list[dict]:
        """L2: Replace tool results older than TTL with placeholder."""
        now = time.time()
        # Track timestamps
        for i, msg in enumerate(messages):
            if msg.get("role") == "tool":
                tid = msg.get("tool_call_id", str(i))
                if tid not in self._tool_timestamps:
                    self._tool_timestamps[tid] = now
        
        # Keep only N most recent, clear old ones
        recent = sorted(self._tool_timestamps.items(), key=lambda x: x[1], reverse=True)
        keep_ids = {tid for tid, ts in recent[:self.config.max_recent_results]}
        
        result = []
        for msg in messages:
            if msg.get("role") == "tool":
                tid = msg.get("tool_call_id", "")
                if tid not in keep_ids:
                    result.append({**msg, "content": "[Old tool result cleared]"})
                    continue
            result.append(msg)
        return result
    
    async def _summarize(self, messages: list[dict]) -> list[dict]:
        """L3: Summarize conversation using a fast/cheap model."""
        summary = await self._call_summarizer(messages)
        
        # Keep system + last 5 messages + summary
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent_msgs = messages[-5:]
        
        return system_msgs + [{
            "role": "system",
            "content": f"[CONVERSATION SUMMARY]\n{summary}\n[/CONVERSATION SUMMARY]"
        }] + recent_msgs
    
    async def _call_summarizer(self, messages: list[dict]) -> str:
        """Call fast model to summarize."""
        from ai_workspace.providers import ProviderRegistry
        
        # Build summarization prompt
        conversation_text = "\n".join(
            f"[{m.get('role')}]: {str(m.get('content', ''))[:500]}"
            for m in messages
            if m.get("role") != "system"
        )
        
        prompt = f"""Summarize this conversation. Keep ONLY:
1. User's original requests and intents
2. Key technical decisions made
3. Files that were modified (with paths)
4. Errors encountered and how they were resolved
5. Pending tasks not yet completed

Be concise. This summary will replace the original messages to save context space.

Conversation:
{conversation_text[:20000]}
"""
        
        registry = ProviderRegistry()
        provider = registry.get("ollama")
        response = await provider.chat(
            model=self.config.summary_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response
    
    def _save_tool_result(self, tool_id: str, content: str):
        """Save full tool output to disk."""
        path = Path(self.config.session_dir) / f"{tool_id}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    
    def get_stats(self) -> dict:
        """Return compaction statistics."""
        return {
            "active_tool_results": len(self._tool_timestamps),
            "session_dir": self.config.session_dir,
            "compact_at_pct": self.config.compact_at_pct,
        }
```

### Integração no AgentLoop

```python
# agents/loop.py — adicionar ao loop principal

class LoopState:
    # ... existing fields ...
    compactor: ContextCompactor = field(default_factory=ContextCompactor)
    current_tokens: int = 0

async def agent_loop(params: LoopParams):
    state = LoopState()
    
    while True:
        # ... existing loop logic ...
        
        # After each turn, check compaction
        state.current_tokens = _estimate_tokens(state.messages)
        state.messages = state.compactor.compact(state.messages, state.current_tokens)
        
        # ... continue loop ...
```

---

## 📊 Comparação com Claude Code

| Nível | Claude Code | aiw (nosso) |
|-------|------------|-------------|
| L1 | 50KB cap + disk persist | 10KB cap + disk persist |
| L2 | History Snip (feature-gated) | Time-based cleanup (10min TTL) |
| L3 | Microcompact (dual-path, cache-aware) | ❌ Não implementado (sem prompt cache) |
| L4 | Context Collapse (não-destrutivo) | ❌ Não implementado (complexo) |
| L5 | Autocompact (9-section XML, CoT) | Summarize (LLM rápido, prompt simples) |

---

## ✅ Critérios de aceitação

- [ ] `ContextCompactor` implementado com 3 níveis
- [ ] L1: tool results > 10KB são truncados com preview
- [ ] L2: tool results > 10min são substituídos por placeholder
- [ ] L3: summarização dispara a 80% do limite de tokens
- [ ] Integrado no AgentLoop (chamado a cada turno)
- [ ] Testes: `tests/test_agents/test_compaction.py`
  - `test_cap_large_tool_result`
  - `test_clear_old_results`
  - `test_summarize_triggers_at_threshold`
  - `test_summary_preserves_user_intent`

---

## 📚 Referências

- [Claude Code 5-Level Compression Pipeline](https://harrisonsec.com/blog/claude-code-context-engineering-compression-pipeline/) — análise detalhada
- [Context Compaction — Inside Claude Code](https://y-agent.github.io/inside-claude-code/04-context-compaction.html) — visão geral
- [Claude Code `compact.ts`](https://github.com/claude-code-best/claude-code/blob/632f3e19/src/commands/compact/compact.ts) — código fonte
- [Compaction deep dive v2.1.68](https://gist.github.com/sam-saffron-jarvis/9d8e291c4e696ac7948702d6c4884448) — prompts e thresholds
