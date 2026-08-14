# Fase 4 — Observabilidade: Tracing, Métricas, Dashboard de Custos

**Data:** 2026-06-16 | **Plano macro:** `PLANO_ARQUITETURA.md`

---

## 1. Stack de Observabilidade

| Camada | Ferramenta | O que monitora | Custo |
|--------|-----------|---------------|-------|
| **Tracing de LLM** | Laminar | Cada chamada de LLM: tokens, latency, custo, modelo | Open source (Apache 2.0) |
| **Métricas de infra** | OpenTelemetry + Prometheus | DB, cache, taxa de erro, throughput | Open source |
| **Dashboard** | Streamlit (já existe) | Gastos, cache hit ratio, performance | Já temos |
| **Alertas** | Budget enforcer (Fase 0) | Estouro de orçamento | $0 (código nosso) |
| **Logs estruturados** | Python `logging` + JSON | Erros, warnings, debug | $0 |

---

## 2. Laminar Tracing

### 2.1 O que é

Laminar é uma plataforma open source de observabilidade pra agentes AI. Rust-based, OpenTelemetry nativo, query SQL.

### 2.2 Integração

```python
from lmnr import Laminar as LaminarTracer

LaminarTracer.initialize(project_api_key="...")

# Tracing automático de chamadas OpenAI/DeepSeek
# Só de instanciar, já captura:
# - Input/output tokens
# - Latência
# - Modelo usado
# - Custo estimado
```

### 2.3 @observe Decorator

```python
from lmnr import observe

@observe(name="research_pipeline")
async def run_research(query: str) -> ResearchResult:
    # Tudo aqui dentro é traçado automaticamente
    plan = await planner.plan(query)
    results = await researcher.research(plan)
    report = await synthesizer.synthesize(results)
    return report

@observe(name="llm_call")
async def call_llm(messages: list, model: str) -> str:
    # Cada chamada vira um span filho
    response = await client.chat.completions.create(
        model=model, messages=messages
    )
    return response.choices[0].message.content
```

### 2.4 Métricas Traçadas por Chamada LLM

```
Span: llm_call
├── input_tokens: 450
├── output_tokens: 120
├── model: deepseek-chat
├── latency_ms: 1.234
├── estimated_cost: $0.00008
├── task_type: "planning"
├── cache_hit: false
├── success: true
└── error: null
```

### 2.5 Queries SQL no Laminar

```sql
-- Gasto total nas últimas 24h
SELECT SUM(estimated_cost) 
FROM spans 
WHERE type = 'llm_call' 
  AND timestamp > NOW() - INTERVAL '24 hours'

-- Modelo mais caro
SELECT model, SUM(estimated_cost) as total_cost
FROM spans
WHERE type = 'llm_call'
GROUP BY model
ORDER BY total_cost DESC

-- Latência média por modelo
SELECT model, AVG(latency_ms) as avg_latency, COUNT(*) as calls
FROM spans
WHERE type = 'llm_call'
GROUP BY model
```

---

## 3. Métricas do PostgreSQL (cost_log + fonte própria)

Além do Laminar, usamos nossas **próprias tabelas** pra métricas que o tracing não captura:

### 3.1 O que cada tabela monitora

| Tabela | Métricas | Criada em |
|--------|----------|-----------|
| `cost_log` | Gasto por chamada, provedor, modelo, tarefa | Fase 0 |
| `semantic_cache` | Hit ratio, tokens saved, cost saved | Fase 0 |
| `domain_reputation` | Domínios trackeados, score médio | Fase 1 |
| `checkpoints` (LangGraph) | Duração por nó, steps por pesquisa | Fase 2 |
| `research_results` | Pesquisas completadas, tokens, fontes | Já existe |

### 3.2 Dashboard Consolidado (Streamlit)

```python
# src/ai_workspace/dashboard/pages/costs.py
import streamlit as st
import pandas as pd
from ai_workspace.knowledge import KnowledgeStore

st.set_page_config(page_title="💰 Custos", layout="wide")
store = KnowledgeStore()

# ── Header ──
col1, col2, col3, col4 = st.columns(4)
with col1:
    today_cost = store.query("SELECT SUM(cost) FROM cost_log WHERE timestamp > NOW() - INTERVAL '24 hours'")
    st.metric("💰 Gasto Hoje", f"${today_cost:.4f}")
with col2:
    month_cost = store.query("SELECT SUM(cost) FROM cost_log WHERE timestamp > NOW() - INTERVAL '30 days'")
    st.metric("📅 Gasto no Mês", f"${month_cost:.4f}")
with col3:
    cache_hit = store.query("SELECT COUNT(*) FROM cost_log WHERE cache_hit = TRUE")
    total_calls = store.query("SELECT COUNT(*) FROM cost_log")
    ratio = cache_hit / total_calls if total_calls else 0
    st.metric("🎯 Cache Hit Ratio", f"{ratio:.1%}")
with col4:
    tokens_saved = store.query("SELECT SUM(tokens_saved) FROM semantic_cache")
    st.metric("💾 Tokens Economizados", f"{tokens_saved:,}")

# ── Gráfico: Gasto por dia ──
st.subheader("Gasto Diário")
costs = store.query("""
    SELECT DATE(timestamp) as day, SUM(cost) as total
    FROM cost_log
    WHERE timestamp > NOW() - INTERVAL '30 days'
    GROUP BY day ORDER BY day
""")
st.line_chart(costs.set_index("day"))

# ── Tabela: Gasto por modelo ──
st.subheader("Gasto por Modelo")
by_model = store.query("""
    SELECT model, SUM(cost) as total, COUNT(*) as calls, AVG(cost) as avg_cost
    FROM cost_log GROUP BY model ORDER BY total DESC
""")
st.dataframe(by_model, use_container_width=True)

# ── Últimas chamadas ──
st.subheader("Últimas Chamadas")
recent = store.query("""
    SELECT timestamp, provider, model, task_type, cost, cache_hit, success
    FROM cost_log ORDER BY timestamp DESC LIMIT 50
""")
st.dataframe(recent, use_container_width=True)
```

---

## 4. Estrutura de Logs

### 4.1 Logger Estruturado

```python
# src/ai_workspace/observability/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),  # ← JSON pra fácil parsing
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("aiw")

# Uso
logger.info("research.started", query=query, depth=depth, estimated_cost=0.002)
logger.warning("source.ignored", url=url, score=0.15, reason="CRED-1 flagged")
logger.error("provider.failed", provider="deepseek", error=str(e), fallback="gemini")
```

### 4.2 Níveis de Log

| Nível | Quando usar | Exemplo |
|-------|------------|---------|
| `DEBUG` | Desenvolvimento | Tokens de cada chamada LLM |
| `INFO` | Operação normal | Pesquisa iniciada, fonte ignorada, cache hit |
| `WARNING` | Algo errado mas recuperável | Provider fallback, fonte suspeita, rate limit |
| `ERROR` | Falha que afeta o resultado | Provider offline, DB connection lost |
| `CRITICAL` | Sistema quebrado | Budget excedido, sem providers disponíveis |

---

## 5. Alertas

### 5.1 Alertas do Budget Enforcer

| Gatilho | Ação | Canal |
|---------|------|-------|
| Gasto diário > $0.50 | Log WARNING | Console + TUI |
| Gasto diário > $1.00 | Bloqueia chamadas pagas | CLI mostra aviso |
| Gasto mensal > $8.00 | Notificação | TUI banner + log |
| Gasto mensal > $10.00 | Bloqueia tudo | `BudgetExceededError` |

### 5.2 Alertas de Performance

| Gatilho | Ação |
|---------|------|
| Cache hit ratio < 30% | Log WARNING (cache não tá sendo eficaz) |
| Latência DeepSeek > 5s | Log WARNING (rede lenta) |
| Erro rate > 10% nas últimas 50 chamadas | Circuit breaker ativa |
| Source filter ignorando > 50% das fontes | Log INFO (threshold pode estar agressivo) |

---

## 6. Métricas de Sucesso da Fase 4

| Métrica | Atual | Meta | Como Medir |
|---------|-------|------|------------|
| Chamadas LLM traçadas | 0% | 100% | Laminar spans |
| Gasto diário visível | ❌ | ✅ | Dashboard Streamlit |
| Cache hit ratio monitorado | ❌ | ✅ | Dashboard |
| Alertas de budget | ❌ | ✅ | Budget enforcer |
| Logs estruturados (JSON) | ❌ | ✅ | `structlog` configurado |
| Tempo de debug de falha | ~30min | < 5min | Tracing + logs estruturados |
