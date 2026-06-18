# Research: What Users Actually Want from AI Coding Agents

> **Status:** 📋 Research notes | **Data:** 2026-06-18
> **Refs:** JetBrains survey (Apr 2026), Ivern survey (312 devs, Apr 2026), Stack Overflow 2026

---

## 📊 Dados consolidados de múltiplas fontes

### Adoção de ferramentas (Abril 2026)

| Ferramenta | Uso diário | Uso semanal | Tentou e parou |
|-----------|-----------|-------------|----------------|
| GitHub Copilot | 68% | 12% | 7% |
| Cursor | 52% | 18% | 9% |
| ChatGPT (code) | 45% | 28% | 10% |
| Claude (web) | 38% | 24% | 4% |
| Claude Code | 34% | 22% | 5% |
| Windsurf | 21% | 14% | 11% |
| Gemini CLI | 16% | 19% | 8% |
| OpenCode | 8% | 12% | 4% |

**Tendência:** 73% usam 2+ ferramentas (era 48% em Out/2025). Multi-tool é o novo normal.

### Satisfação (JetBrains, Abr 2026)

| Ferramenta | Satisfação | NPS |
|-----------|-----------|-----|
| Claude Code | 91% | 54 |
| Cursor | 85% | 41 |
| GitHub Copilot | 78% | 32 |

### Economia de tempo

| Setup | Horas salvas/semana |
|-------|-------------------|
| Single tool | 5.2h |
| 2 tools (manual) | 7.1h |
| 3+ tools (manual) | 6.8h (⚠ pior que 2!) |
| **Multi-agent coordenado** | **11.4h** |

**Lição:** Mais ferramentas ≠ mais produtividade. Coordenação é o multiplicador.

### Dores (Ivern, 312 devs)

| Dor | % |
|-----|---|
| Perder track do que cada agente faz | 62% |
| Copy-paste de contexto entre tools | 58% |
| Gastar tempo gerenciando agentes | 47% |
| Agentes sobrescrevendo mudanças | 41% |
| Estilo de código inconsistente | 39% |
| Perdeu trabalho por conflito | 18% |

### Preferência de pricing

| Modelo | Usa hoje | Prefere |
|--------|---------|---------|
| Subscription (flat) | 54% | 38% |
| **BYOK (pay per use)** | 36% | **48%** |
| Free only | 10% | 14% |

**BYOK adoption dobrou** (18%→36%) em 3 meses. 48% preferem mas só 36% usam → gap de 12pp.

### Gastos mensais

| Faixa | Subscription | BYOK |
|-------|-------------|------|
| $0 | 10% | 8% |
| **$1-10** | 15% | **42%** |
| $11-30 | 38% | 35% |
| $31-50 | 25% | 10% |
| $51+ | 12% | 5% |

**Mediana BYOK: $8/mês. Mediana subscription: $25/mês.**

### Features mais pedidas (ainda não existem)

1. Coordenação entre múltiplos agentes
2. Dashboard unificado de gestão
3. Cross-agent context sharing
4. Automated task routing
5. BYOK flexibility

### Tipos de tarefa: single vs multi-agent (nota 0-10)

| Tarefa | Single | Multi | Diferença |
|--------|--------|-------|-----------|
| Code review | 5.5 | **8.8** | +3.3 |
| Refactoring | 6.5 | **8.6** | +2.1 |
| Feature impl | 6.8 | **8.5** | +1.7 |
| Testing | 5.2 | **8.3** | +3.1 |
| Bug fixing | 7.2 | **8.1** | +0.9 |
| Research | 8.0 | 8.2 | +0.2 |
| Documentation | 7.5 | 7.8 | +0.3 |

**Lição:** Multi-agent brilha em tarefas complexas (review, refactor, test). Single tool é competitivo em tarefas simples (research, docs).

---

## 📋 O que isso significa para o aiw

### Alinhamento forte (nossas specs atacam dores reais)
- 62% "perder track" → Context Inspector (SPEC_CONTEXT_MANAGEMENT)
- 58% "copy-paste contexto" → MCP interoperability (SPEC_AGENT_MCP_TOOL)
- 47% "gerenciar agentes" → TUI dashboard (SPEC_TUI_V5)
- 48% preferem BYOK → Ollama-first, $0 (nossa arquitetura)

### Oportunidade não atacada
- 39% "estilo inconsistente" → **Nova spec:** Code Style Enforcement
  - Agente aplica `.editorconfig`, `ruff`, `prettier` automaticamente
  - Verificação pós-edição: "esse código segue o estilo do projeto?"

### Preço certo
- Mediana BYOK: $8/mês
- Nosso custo (Ollama): $0 + DeepSeek opcional (~$0.0004/1K)
- **Posicionamento de preço imbatível**

---

## 📚 Referências

- [JetBrains: Which AI Coding Tools Do Developers Actually Use?](https://blog.jetbrains.com/research/2026/04/which-ai-coding-tools-do-developers-actually-use-at-work/) Abr 2026
- [Ivern: State of AI Agents 2026](https://ivern.ai/blog/state-of-ai-agents-developer-survey-2026) Abr 2026, n=312
- [Claude Code NPS #2](https://sdd.sh/2026/04/claude-code-is-now-the-%232-ai-coding-tool-at-work-and-has-the-best-nps-in-the-industry/) Abr 2026
- [Stack Overflow Survey 2026](https://cadence.withremote.ai/blog/stack-overflow-survey-2026) 2026
