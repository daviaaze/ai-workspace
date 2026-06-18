# Spec: Structured Error Handling (Result Pattern)

> **Status:** 📋 Spec | **Data:** 2026-06-18 | **Refs:** dry-python/returns, Railway Oriented Programming

---

## 🎯 Motivação

O código atual tem **239 blocos `except Exception`**, sendo que **83 usam `pass`** — erros são engolidos em silêncio. Exemplos reais:

```python
# orchestrator.py:616 — router falhou? ninguém sabe
try:
    from ai_workspace.agents.router import get_router
    get_router().mark_success(...)
except Exception:
    pass

# orchestrator.py:662 — streaming quebrou? silêncio
try:
    from ai_workspace.tui.streaming import enable_streaming
    enable_streaming(queue)
except Exception:
    pass
```

Isso causa:
- Bugs impossíveis de diagnosticar (sem log, sem stack trace)
- Comportamento "funciona às vezes" (depende de qual `except` engoliu o erro)
- Agentes externos não sabem se falhou ou não (output bonito mas vazio)
- Zero telemetria de erros (não sabemos QUAIS componentes falham)

---

## 📐 Design: Result Pattern

Baseado no [dry-python/returns](https://returns.readthedocs.io/en/stable/pages/result.html) — Railway Oriented Programming em Python.

### Core types

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")

@dataclass(frozen=True)
class Success(Generic[T]):
    value: T
    
    def is_success(self) -> bool: return True
    def is_failure(self) -> bool: return False

@dataclass(frozen=True)
class Failure(Generic[E]):
    error: E
    
    def is_success(self) -> bool: return False
    def is_failure(self) -> bool: return True

type Result[T, E] = Success[T] | Failure[E]
```

### Uso básico

```python
def find_user(user_id: int) -> Result[User, str]:
    user = db.query(User).filter(id=user_id).first()
    if user:
        return Success(user)
    return Failure(f"User {user_id} not found")

# Pattern matching (Python 3.10+)
match find_user(42):
    case Success(user):
        print(f"Found: {user.name}")
    case Failure(error):
        print(f"Error: {error}")
```

### Substituindo `except: pass`

**Antes (quebrado):**
```python
try:
    from ai_workspace.agents.router import get_router
    get_router().mark_success(model, provider)
except Exception:
    pass  # ← erro engolido
```

**Depois (com Result):**
```python
def _mark_router_success(model: str, provider: str) -> Result[None, AiWError]:
    try:
        from ai_workspace.agents.router import get_router
        get_router().mark_success(model, provider)
        return Success(None)
    except ImportError as e:
        return Failure(AiWError(
            code="ROUTER_NOT_AVAILABLE",
            message="Router module not importable",
            detail=str(e),
            recoverable=True,
        ))
    except Exception as e:
        return Failure(AiWError(
            code="ROUTER_MARK_FAILED",
            message=f"Failed to mark success for {provider}/{model}",
            detail=str(e),
            recoverable=True,
        ))

# Uso:
result = _mark_router_success("qwen3:14b", "ollama")
match result:
    case Failure(error):
        logger.warning("Router mark failed: %s", error)
        telemetry.increment("errors", component="router", code=error.code)
    case Success(_):
        pass
```

### O tipo `AiWError`

Erro estruturado compatível com output modes:

```python
@dataclass
class AiWError:
    code: str           # "PROVIDER_OFFLINE", "BUDGET_EXCEEDED", "TIMEOUT"
    message: str        # descrição humana
    detail: str = ""    # detalhe técnico (traceback, API response)
    recoverable: bool = True  # pode tentar de novo?
    suggestion: str = ""  # "Tente: ollama pull qwen3:14b"

# Catálogo de error codes
class ErrorCode:
    PROVIDER_OFFLINE = "PROVIDER_OFFLINE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    TOOL_FAILED = "TOOL_FAILED"
    SEARCH_FAILED = "SEARCH_FAILED"
    AGENT_LOOP_LIMIT = "AGENT_LOOP_LIMIT"
    STREAMING_FAILED = "STREAMING_FAILED"
    ROUTER_FAILED = "ROUTER_FAILED"
    CONFIG_INVALID = "CONFIG_INVALID"
```

---

## 🔧 Plano de migração

### Fase A: Adicionar `Result` e `AiWError` (sem quebrar nada)

1. Criar `src/ai_workspace/core/result.py` com os tipos
2. NÃO migrar código existente ainda — só disponibilizar os tipos

### Fase B: Migrar pontos críticos (baixo risco, alto impacto)

Prioridade: componentes que afetam output do usuário.

1. **Providers** (`providers/__init__.py`) — health check retorna Result
2. **Search** (`search/deep_search.py`) — `research()` retorna Result
3. **Orchestrator** (`agents/orchestrator.py`) — `run()` retorna Result

### Fase C: Eliminar `except: pass` (um por um)

Meta: 83 → 0. Cada `pass` substituído por `Failure(AiWError(...))` + log + telemetria.

```python
# Regra: todo bloco except deve:
# 1. Logar o erro (logger.warning ou logger.error)
# 2. Emitir métrica (telemetry.increment)
# 3. Retornar Failure ou levantar exceção com contexto
```

### Fase D: Integrar com output modes

```python
# No CLI, converter Result em envelope JSON/NDJSON:
match result:
    case Success(value):
        envelope = {"ok": True, "data": value}
    case Failure(error):
        envelope = {"ok": False, "error": {
            "code": error.code,
            "message": error.message,
            "recoverable": error.recoverable,
            "suggestion": error.suggestion,
        }}
```

---

## 📊 Métricas de erro (novo em `aiw telemetry`)

```json
{
  "errors": {
    "24h": 3,
    "total": 47,
    "by_component": {
      "providers": 12,
      "search": 23,
      "orchestrator": 5,
      "tui": 7
    },
    "by_code": {
      "PROVIDER_OFFLINE": 8,
      "PROVIDER_TIMEOUT": 4,
      "TOOL_FAILED": 15,
      "AGENT_LOOP_LIMIT": 3
    },
    "recoverable_pct": 78.5
  }
}
```

---

## ✅ Critérios de aceitação

- [ ] `src/ai_workspace/core/result.py` existe com `Result`, `Success`, `Failure`, `AiWError`
- [ ] `AiWError` tem `code`, `message`, `detail`, `recoverable`, `suggestion`
- [ ] `ErrorCode` cataloga todos os códigos de erro do sistema
- [ ] `aiw health` usa Result internamente — falha de provider = Failure, não `pass`
- [ ] `aiw search` usa Result — falha retorna envelope `{ok: false, error: {...}}`
- [ ] Output JSON/NDJSON inclui erros estruturados (compatível com SPEC_OUTPUT_MODES)
- [ ] `aiw telemetry -o json` mostra `errors.by_component` e `errors.by_code`
- [ ] Nenhum `except: pass` novo é introduzido (pre-commit hook)
- [ ] 83 `except: pass` existentes são migrados (meta aspiracional, não bloqueante)
- [ ] Erro sempre produz log (logger.warning no mínimo)

---

## 📚 Referências

- [dry-python/returns](https://returns.readthedocs.io/en/stable/pages/result.html) — Railway Oriented Programming, `Result`, `Success`, `Failure`, `@safe`
- [returns README](https://github.com/dry-python/returns) — exemplos de composição com `bind`, `map`, `lash`
- [ZuidVolt/result-pattern](https://github.com/ZuidVolt/result-pattern) — implementação minimalista do Result pattern
- [leodiegues/unwrappy](https://github.com/leodiegues/unwrappy) — Result + Option inspirados em Rust para Python
