# Fase 5 — Testes + Deploy: Qualidade e Entrega Contínua

**Data:** 2026-06-16 | **Plano macro:** `PLANO_ARQUITETURA.md`
**Estado atual:** `tests/` com fixtures + alguns testes de unidade, mas **cobertura muito baixa**

---

## 1. Estratégia de Testes

### 1.1 Pirâmide de Testes

```
        ┌──────────┐
        │  E2E (5%) │  ← Testes de fluxo completo (pesquisa real)
       ┌┴──────────┴┐
       │ Integração  │  ← DB real, LLM mockado, LangGraph completo
       │   (25%)     │
      ┌┴────────────┴┐
      │    Unidade    │  ← Lógica pura, tudo mockado
      │     (70%)     │
      └──────────────┘
```

### 1.2 O que testar em cada módulo novo

| Módulo | Teste de Unidade | Teste de Integração |
|--------|-----------------|---------------------|
| **Fase 0: Cache** | Algoritmo de similaridade, hit/miss, TTL | Cache com pgvector real, concorrência |
| **Fase 0: Router** | Matriz de roteamento, fallback chain | Router com endpoints mockados |
| **Fase 0: Budget** | Limites, circuit breaker, reset | Budget com DB real |
| **Fase 1: Source Reputation** | Algoritmo de score composto | CRED-1 seed, consulta por domínio |
| **Fase 1: CRED-1** | Parse do dataset, upsert no DB | Seed com dados reais |
| **Fase 2: LangGraph** | Nós individuais, state transitions | Grafo completo com checkpointer |
| **Fase 2: Supervisor** | Decisões de roteamento | Supervisor com estados simulados |
| **Fase 3: Crawl4AI** | — | Teste de scraping em site controlado |
| **Fase 3: OpenCLI** | Parse de output JSON | — |
| **Fase 4: Laminar** | — | Verificar spans gerados |

### 1.3 Mock de LLM para Testes

```python
# tests/conftest.py (já existe, expandir)

@pytest.fixture
def mock_deepseek():
    """Mocka chamadas DeepSeek pra não gastar dinheiro em testes."""
    with patch("openai.AsyncOpenAI") as mock:
        client = MagicMock()
        completion = MagicMock()
        completion.choices = [MagicMock()]
        completion.choices[0].message.content = '{"answer": "mock answer", "confidence": 0.9}'
        completion.usage = MagicMock()
        completion.usage.prompt_tokens = 100
        completion.usage.completion_tokens = 50
        client.chat.completions.create = AsyncMock(return_value=completion)
        mock.return_value = client
        yield mock

@pytest.fixture
def mock_gemini():
    """Mocka Gemini pra testes de fallback."""
    with patch("google.genai.aio.Client") as mock:
        yield mock
```

### 1.4 Teste do Cache Semântico

```python
# tests/test_cost/test_cache.py
import pytest
from ai_workspace.cost.cache import SemanticCache

class TestSemanticCache:
    
    async def test_cache_hit_exact_match(self, mock_embedding):
        cache = SemanticCache()
        await cache.set("Qual o melhor framework para agentes?", "LangGraph")
        
        result = await cache.get("Qual o melhor framework para agentes?")
        assert result == "LangGraph"
    
    async def test_cache_hit_similar_query(self, mock_embedding):
        cache = SemanticCache()
        await cache.set("O que é LangGraph?", "Framework de grafos...")
        
        result = await cache.get("Explique LangGraph para mim")
        assert result is not None  # similar o suficiente
        assert result.confidence > 0.85
    
    async def test_cache_miss_different_topic(self, mock_embedding):
        cache = SemanticCache()
        await cache.set("O que é Python?", "Linguagem de programação")
        
        result = await cache.get("Melhores receitas de bolo")
        assert result is None  # tópico diferente, não deve retornar
```

### 1.5 Teste do Smart Router

```python
# tests/test_cost/test_router.py
class TestSmartRouter:
    
    def test_router_selects_cheapest_model(self):
        router = SmartRouter()
        model = router.select_model("extraction")
        assert model == "gemini-2.5-flash"  # mais barato pra extração
    
    def test_router_fallback_on_failure(self):
        router = SmartRouter()
        model = router.select_fallback("reasoning")
        assert model == "deepseek-chat"  # fallback do deepseek-reasoner
    
    def test_router_never_exceeds_budget(self, mock_budget):
        router = SmartRouter(budget_enforcer=mock_budget)
        mock_budget.can_call.return_value = False
        with pytest.raises(BudgetExceededError):
            router.select_model("reasoning")
```

---

## 2. CI/CD com GitHub Actions

### 2.1 Pipeline de CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: ai_workspace_test
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install crawl4ai credigraph  # opcionais
      
      - name: Lint
        run: ruff check src/
      
      - name: Type check
        run: mypy src/
      
      - name: Test with coverage
        run: pytest tests/ --cov=ai_workspace --cov-report=xml --cov-report=term-missing
        env:
          AIW_TEST_DB_URL: postgresql://postgres:postgres@localhost:5432/ai_workspace_test
      
      - name: Upload coverage
        uses: codecov/codecov-action@v5
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
```

### 2.2 Gatilhos de Deploy

```yaml
# .github/workflows/deploy-homelab.yml
name: Deploy to Homelab
on:
  push:
    branches: [main]
  workflow_dispatch:  # manual

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Nix package
        run: nix build .#ai-workspace
      
      - name: Trigger homelab rebuild
        run: |
          curl -X POST ${{ secrets.HOMELAB_WEBHOOK_URL }} \
            -H "Authorization: Bearer ${{ secrets.HOMELAB_TOKEN }}" \
            -d '{"update": "ai-workspace"}'
```

---

## 3. Métricas de Sucesso da Fase 5

| Métrica | Atual | Meta | Como Medir |
|---------|-------|------|------------|
| Cobertura de testes | ~5% | **≥ 70%** | `pytest --cov` |
| CI passando | ❌ | ✅ | GitHub Actions status |
| Testes de cache/router/budget | 0 | **≥ 30** | `tests/test_cost/` |
| Testes de source reputation | 0 | **≥ 20** | `tests/test_sources/` |
| Testes de LangGraph | 0 | **≥ 15** | `tests/test_langgraph/` |
| Deploy automático | ❌ | ✅ | Homelab webhook |
| Lint + type check no CI | ❌ | ✅ | Ruff + mypy passando |

---

## 4. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Testes lentos por causa de LLM real | Alta | Mocks pra 95% dos testes. Só E2E usa LLM real |
| pgvector não disponível no CI | Baixa | Usar `pgvector/pgvector:pg16` service no GitHub Actions |
| Manter mocks sincronizados com API real | Média | Testes de integração semanais contra API real |
| Cobertura de testes cai com novas features | Alta | CI blocking se coverage < 70% |
