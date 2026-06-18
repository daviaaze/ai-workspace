# Spec: Eval Harness — Agent Quality Assessment

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** GAGE, evalh, proofagent-harness, agent-eval-harness

---

## 🎯 Motivação

Sem métricas objetivas, cada mudança no agente é tiro no escuro. Precisamos saber:
- A mudança X melhorou ou piorou a qualidade?
- O novo provider Y é melhor que o atual?
- O AgentLoop com ReAct é melhor que Direct para coding?

Ferramentas open-source de referência:

| Ferramenta | Diferencial |
|-----------|-------------|
| [GAGE](https://github.com/HiThink-Research/GAGE) | Unified engine, datasets, metrics, replay |
| [evalh](https://github.com/regokan/evalh) | Config-driven YAML, LLM-as-judge, drift detection |
| [proofagent-harness](https://github.com/ProofAgent-ai/proofagent-harness) | Pytest-style, multi-turn adversarial, multi-juror |
| [agent-eval-harness](https://github.com/Siddharth-1001/agent-eval-harness) | Tool success rate, hallucination detection, latency/cost |

---

## 📐 Design minimalista

Não precisamos de um framework completo. Algo simples, Python-native, integrável ao `pytest`:

```python
# tests/test_evals/test_coding.py

import pytest
from ai_workspace.agents.loop import agent_loop, LoopParams, LoopPattern

# ═══════════════════════════════════════════════════════════
# Test cases: task → expected behavior
# ═══════════════════════════════════════════════════════════

CODING_TASKS = [
    {
        "id": "simple_fix",
        "task": "In the file src/example.py, change the function name from 'foo' to 'bar'",
        "expected": {
            "tool_calls": ["read_file", "edit_file"],
            "min_confidence": 0.7,
        },
    },
    {
        "id": "explain_code",
        "task": "Explain what this function does: def add(a, b): return a + b",
        "expected": {
            "tool_calls": [],  # deve responder sem tools
            "contains_keywords": ["adds", "sum", "returns"],
        },
    },
]

RESEARCH_TASKS = [
    {
        "id": "simple_fact",
        "task": "What is the capital of France?",
        "expected": {
            "contains": "Paris",
            "no_hallucination": True,
        },
    },
]

# ═══════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════

@dataclass
class EvalResult:
    task_id: str
    passed: bool
    metrics: dict
    trace: list[dict]  # eventos do loop
    latency_ms: float
    cost: float
    tokens: int

class AgentEvaluator:
    """Run eval tasks and collect metrics."""
    
    def __init__(self, provider: str = "ollama", model: str = "qwen3:14b"):
        self.provider = provider
        self.model = model
    
    async def evaluate(self, task: dict) -> EvalResult:
        """Run a single eval task."""
        import time
        start = time.monotonic()
        
        params = LoopParams(
            task=task["task"],
            pattern=LoopPattern.REACT,
            model=self.model,
            provider=self.provider,
            stream=False,
        )
        
        trace = []
        result_text = []
        
        async for event in agent_loop(params):
            trace.append({"type": event.type, "data": event.data})
            if event.type == "token":
                result_text.append(event.data.get("text", ""))
        
        full_result = "".join(result_text)
        elapsed = (time.monotonic() - start) * 1000
        
        # Check expectations
        passed, metrics = self._check(task["expected"], trace, full_result)
        
        return EvalResult(
            task_id=task["id"],
            passed=passed,
            metrics=metrics,
            trace=trace,
            latency_ms=elapsed,
            cost=0.0,  # seria calculado pelo CostService
            tokens=len(full_result) // 4,
        )
    
    def _check(self, expected: dict, trace: list, result: str) -> tuple[bool, dict]:
        """Check if agent behavior matches expectations."""
        checks = {}
        
        # Tool calls check
        if "tool_calls" in expected:
            actual_tools = [e["data"].get("tool") for e in trace if e["type"] == "tool_call"]
            expected_tools = expected["tool_calls"]
            checks["tools_match"] = set(expected_tools).issubset(set(actual_tools))
        
        # Content checks
        if "contains" in expected:
            checks["contains"] = expected["contains"].lower() in result.lower()
        
        if "contains_keywords" in expected:
            checks["keywords"] = all(
                kw.lower() in result.lower()
                for kw in expected["contains_keywords"]
            )
        
        if "no_hallucination" in expected:
            # Simple heuristic: check for uncertainty markers
            uncertainty = ["i think", "probably", "maybe", "i'm not sure"]
            checks["no_hallucination"] = not any(
                marker in result.lower() for marker in uncertainty
            )
        
        passed = all(checks.values()) if checks else True
        return passed, checks


# ═══════════════════════════════════════════════════════════
# Pytest integration
# ═══════════════════════════════════════════════════════════

@pytest.mark.slow  # requer LLM real
@pytest.mark.parametrize("task", CODING_TASKS, ids=[t["id"] for t in CODING_TASKS])
async def test_coding_tasks(task):
    evaluator = AgentEvaluator()
    result = await evaluator.evaluate(task)
    assert result.passed, f"Failed checks: {result.metrics}"

@pytest.mark.slow
async def test_react_vs_direct_latency():
    """Benchmark: ReAct vs Direct for simple questions."""
    task = {"task": "What is 2+2?", "expected": {"contains": "4"}}
    
    # Direct
    t1 = time.monotonic()
    params = LoopParams(task=task["task"], pattern=LoopPattern.DIRECT)
    async for _ in agent_loop(params): pass
    direct_ms = (time.monotonic() - t1) * 1000
    
    # ReAct
    t2 = time.monotonic()
    params = LoopParams(task=task["task"], pattern=LoopPattern.REACT)
    async for _ in agent_loop(params): pass
    react_ms = (time.monotonic() - t2) * 1000
    
    print(f"Direct: {direct_ms:.0f}ms, ReAct: {react_ms:.0f}ms")
    # ReAct shouldn't be more than 5x slower for simple questions
    assert react_ms < direct_ms * 5
```

### CLI

```bash
# Run all evals (requer LLM real)
pytest tests/test_evals/ -m slow -v

# Run specific category
pytest tests/test_evals/test_coding.py -v

# Benchmark mode
aiw eval benchmark --provider ollama --model qwen3:14b

# Compare providers
aiw eval compare --task-set coding --providers ollama,deepseek
```

---

## 📊 Métricas coletadas

| Métrica | O que mede | Como |
|---------|-----------|------|
| **Pass rate** | % tarefas que passam | `passed / total` |
| **Tool accuracy** | % tool calls esperadas vs reais | `tools_match` |
| **Latency** | Tempo total do loop | `time.monotonic()` |
| **Token efficiency** | Tokens usados por tarefa | Estimativa |
| **Hallucination rate** | % respostas com incerteza | Heurística de marcadores |

---

## ✅ Critérios de aceitação

- [ ] `AgentEvaluator` implementado com `evaluate(task) → EvalResult`
- [ ] 3-5 coding tasks definidas
- [ ] 3-5 research tasks definidas
- [ ] Pytest integration com `@pytest.mark.slow`
- [ ] Métricas: pass rate, tool accuracy, latency, hallucination
- [ ] Funciona com modelo real (não mock)

---

## 📚 Referências

- [GAGE — unified eval engine](https://github.com/HiThink-Research/GAGE)
- [evalh — config-driven YAML harness](https://github.com/regokan/evalh)
- [proofagent-harness — pytest-style](https://github.com/ProofAgent-ai/proofagent-harness)
- [agent-eval-harness — tool + hallucination metrics](https://github.com/Siddharth-1001/agent-eval-harness)
