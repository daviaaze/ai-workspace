# Model Fallback / Smart Router — Cross-Provider Intelligence

> **Data:** 2026-06-17 | **Status:** ✅ Implemented (v2) | **Arquivos:** `agents/router.py` (372 linhas), `providers/__init__.py`

---

## 🎯 Problema

Cada provedor de LLM tem características diferentes: Ollama é grátis mas limitado, DeepSeek é barato e bom, Gemini tem free tier. Sem um roteador inteligente, o sistema usa sempre o mesmo modelo — gastando dinheiro desnecessário ou caindo quando um provedor falha.

---

## 🧠 Solução: SmartRouter com Fallback Cross-Provider

```
Tarefa entra
     │
     ▼
┌─────────────────────────┐
│ 1. check_availability() │  ← Probe providers
│    Ollama: HTTP ping     │     (API keys + health)
│    DeepSeek: API key?    │
│    Gemini: API key?      │
│    OpenRouter: API key?  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. route(task, type)    │  ← Select best model
│    Detect complexity     │
│    Apply routing rules   │
│    Build fallback chain  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. Execute with primary │
│    Success? → mark_ok   │
│    Failure? → fallback  │
└───────────┬─────────────┘
            │ fail
            ▼
┌─────────────────────────┐
│ 4. fallback(decision)   │  ← Next in chain
│    Disable failed model  │
│    Return next available │
│    Repeat até exaustão   │
└─────────────────────────┘
```

---

## 📊 Matriz de Roteamento

| Task Type | 1ª escolha | 2ª | 3ª | 4ª | 5ª |
|-----------|-----------|----|----|----|-----|
| **Coding** | ollama/qwen3:14b ($0) | ollama/qwen3.5:9b | ollama/codellama | deepseek/deepseek-chat | openrouter/claude |
| **Research** | ollama/qwen3:14b ($0) | deepseek/deepseek-chat | ollama/qwen3.5:9b | gemini/2.5-flash | openrouter/claude |
| **Planning** | ollama/ministral-3:8b ($0) | ollama/qwen3:14b | gemini/2.5-flash | deepseek/deepseek-chat | — |
| **Synthesis** | ollama/qwen3:14b ($0) | deepseek/deepseek-chat | gemini/2.5-flash | ollama/qwen3.5:9b | — |
| **Extraction** | gemini/2.5-flash-lite ($0) | gemini/2.5-flash | ollama/ministral-3:8b | ollama/qwen3.5:9b | deepseek/deepseek-chat |
| **Classification** | gemini/2.5-flash-lite ($0) | ollama/ministral-3:8b | gemini/2.5-flash | — | — |
| **Chat** | ollama/ministral-3:8b ($0) | ollama/qwen3.5:9b | ollama/qwen3:14b | gemini/2.5-flash | deepseek/deepseek-chat |

### Complexidade ajusta a ordem

| Complexidade | Coding | Research |
|-------------|--------|----------|
| SIMPLE | ollama first | ollama first |
| MODERATE | ollama first | ollama first |
| **COMPLEX** | **deepseek first** | **deepseek first** (usa reasoner) |

---

## 📦 Custos por Provedor

| Provider | Model | Input $/1M | Output $/1M |
|----------|-------|-----------|-------------|
| Ollama | qwen3:14b | $0 | $0 |
| Ollama | ministral-3:8b | $0 | $0 |
| DeepSeek | deepseek-chat | $0.14 | $0.28 |
| DeepSeek | deepseek-reasoner | $0.55 | $2.19 |
| Gemini | 2.5-flash (free tier) | $0 (60/min) | $0 |
| OpenRouter | claude-3.7-sonnet | $3.00 | $15.00 |

---

## 🔗 Integrações

- **AgentWorker**: `check_availability_sync()` → `route()` → executa → `fallback()` se falhar
- **DeepSearch**: `_estimate_llm_cost()` consulta o router para custo real
- **CLI**: `aiw health` mostra status de todos os providers
- **ProviderRegistry**: Gemini, DeepSeek, Ollama, OpenRouter, Kimi, NVIDIA
