# Spec: Output Modes (--output json | ndjson)

> **Status:** 📋 Spec | **Data:** 2026-06-18 | **Refs:** ndjson-spec v1.0.0, kubectl `-o json`, gh CLI `--json`, typer docs

---

## 🎯 Motivação

Todo comando `aiw` hoje usa Rich (tabelas Unicode, emojis). Isso é ilegível para:
- **Agentes** (pi, outro aiw) — não parseiam bordas ANSI/Unicode
- **Scripts** — `grep`, `jq`, pipelines Unix quebram
- **MCP clients** — esperam JSON estruturado, não texto formatado

Ferramentas que já fazem isso:
- `kubectl get pods -o json` — Kubernetes ([cli-runtime/pkg/genericclioptions/print_flags.go](https://github.com/kubernetes/cli-runtime))
- `gh pr list --json number,title` — GitHub CLI ([cli/cli/pkg/cmdutil/json_flags.go](https://github.com/cli/cli))
- `systemctl --output=json` — systemd 250+
- `docker ps --format '{{json .}}'` — Docker

---

## 📐 Design

### Flag global

```bash
aiw health --output json       # JSON objeto único
aiw health --output ndjson     # NDJSON streaming (evento por linha)
aiw health -o json             # alias curto
aiw health                     # default: rich (compatível)
```

### NDJSON: por que e como

NDJSON (Newline Delimited JSON) é o padrão certo para streaming. Especificação oficial: [ndjson-spec v1.0.0](https://github.com/ndjson/ndjson-spec) (2014).

**Regras do spec (RFC-style):**
- Cada linha é um objeto JSON válido terminado por `\n` (0x0A)
- JSON interno NÃO pode conter newlines (tudo em uma linha)
- Encoding MUST ser UTF-8
- Media type: `application/x-ndjson`

**Por que NDJSON em vez de JSON array:**
- O consumidor pode processar cada evento assim que chega (não espera o array fechar)
- `jq` lê nativamente: `aiw search -o ndjson | jq 'select(.type=="research_done")'`
- Se o processo morrer no meio, os eventos já emitidos são válidos
- Permite logs + progresso + resultado final no mesmo stream

**Exemplo de consumo por agente:**
```python
import json, subprocess

proc = subprocess.Popen(
    ["aiw", "search", "python vs rust", "-o", "ndjson"],
    stdout=subprocess.PIPE, text=True
)
for line in proc.stdout:
    event = json.loads(line)
    if event["type"] == "research_done":
        print(f"Sub-question done: confidence={event['confidence']}")
    elif event["type"] == "done":
        break
```

---

## 📋 Schemas por comando

### `aiw health -o json`

```json
{
  "ok": true,
  "command": "health",
  "timestamp": "2026-06-18T15:30:00Z",
  "data": {
    "providers": [
      {"provider": "ollama", "status": "online", "model": "qwen3:14b", "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0},
      {"provider": "deepseek", "status": "online", "model": "deepseek-chat", "cost_per_1k_input": 0.00014, "cost_per_1k_output": 0.00028}
    ],
    "cache": {"entries": 10, "hits": 31, "tokens_saved": 6049},
    "budget": {"daily": {"spent": 0.005, "limit": 1.0, "pct": 0.5}, "monthly": {"spent": 0.0056, "limit": 10.0, "pct": 0.06}},
    "sources": {"domains_tracked": 2694, "cred1_coverage": 0}
  },
  "warnings": ["codellama:13b is offline"],
  "meta": {"version": "0.1.0", "duration_ms": 234}
}
```

### `aiw search "query" -o ndjson`

Streaming linha por linha. O agente consumidor lê cada evento em tempo real:

```
{"type":"start","command":"search","query":"python vs rust","provider":"ollama","model":"qwen3:14b","timestamp":"..."}
{"type":"phase","phase":"planning","message":"Generating research plan..."}
{"type":"plan","questions":["What are the core design...","How does memory...",...],"total":5}
{"type":"phase","phase":"supervising","message":"Supervisor reviewing plan..."}
{"type":"plan_refined","questions":["Core design...","Practical trade-offs...","..."],"total":4,"removed":1,"reason":"merged duplicate"}
{"type":"phase","phase":"researching","current":1,"total":4}
{"type":"research_start","current":1,"question":"Core design philosophy and memory management..."}
{"type":"tool_call","current":1,"tool":"web_search","args":{"query":"python rust design philosophy memory management"}}
{"type":"tool_result","current":1,"tool":"web_search","result_preview":"Python uses reference counting..."}
{"type":"research_done","current":1,"confidence":0.85,"sources":["https://...","https://..."],"duration_ms":3420}
{"type":"phase","phase":"researching","current":2,"total":4}
...
{"type":"phase","phase":"synthesizing","message":"Compiling final report..."}
{"type":"done","ok":true,"confidence":0.82,"duration_ms":45230,"sources":["..."]}
```

### `aiw budget -o json`

```json
{
  "ok": true,
  "command": "budget",
  "data": {
    "today": {"spent": 0.005, "limit": 1.0, "pct": 0.5},
    "month": {"spent": 0.0056, "limit": 10.0, "pct": 0.06},
    "cache": {"entries": 10, "hits": 31, "tokens_saved": 6049, "cost_saved": 0.0007},
    "circuits": {"deepseek": "closed", "gemini": "closed", "ollama": "closed"},
    "limits": {"per_call": 0.01, "per_day": 1.0, "per_month": 10.0}
  }
}
```

### `aiw telemetry -o json`

```json
{
  "ok": true,
  "command": "telemetry",
  "data": {
    "research": {"24h": 1, "total": 81, "avg_confidence": 0.67},
    "tasks": {"done": 1, "pending": 0, "total": 2},
    "memories": {"total": 61, "24h": 13},
    "knowledge": {"entries": 15},
    "errors": {"24h": 3, "by_component": {"providers": 1, "search": 2}},
    "latency": {"avg_ms": 3420, "p50_ms": 2800, "p95_ms": 8900}
  }
}
```

---

## 🔧 Implementação

### Local: `src/ai_workspace/core/output.py` (novo)

Baseado no padrão do typer (flag `--json` como `Annotated[bool, typer.Option]`) e no ndjson-spec.

### Integração no CLI (`cli.py`)

```python
# Callback global — adiciona --output a TODOS os comandos
@app.callback()
def main(
    ctx: typer.Context,
    output: Annotated[str, typer.Option(
        "--output", "-o",
        help="Output format: rich (default), json, ndjson"
    )] = "rich",
):
    if output not in ("rich", "json", "ndjson"):
        raise typer.BadParameter(f"Invalid output format: {output}. Use: rich, json, ndjson")
    ctx.ensure_object(dict)
    ctx.obj["output"] = output
```

### Exemplo de uso em comando existente

```python
@app.command()
def health(ctx: typer.Context):
    mode = ctx.obj.get("output", "rich")
    
    # Coleta dados (mesmo para todos os modos)
    providers = _collect_providers()
    cache = _collect_cache()
    budget = _collect_budget()
    
    if mode == "rich":
        _print_health_rich(providers, cache, budget)  # código existente
    elif mode == "json":
        envelope = {
            "ok": True, "command": "health",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"providers": providers, "cache": cache, "budget": budget},
            "meta": {"version": "0.1.0"}
        }
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
    elif mode == "ndjson":
        _emit_ndjson({"type": "start", "command": "health"})
        for p in providers:
            _emit_ndjson({"type": "provider", **p})
        _emit_ndjson({"type": "cache", **cache})
        _emit_ndjson({"type": "budget", **budget})
        _emit_ndjson({"type": "done", "ok": True})
```

---

## ✅ Critérios de aceitação

- [ ] `aiw health -o json | jq .ok` retorna `true`
- [ ] `aiw health -o ndjson | wc -l` > 1 (múltiplos eventos)
- [ ] `aiw health -o ndjson | jq -s '.[] | select(.type=="provider")'` lista providers
- [ ] `aiw health` (sem flag) = output Rich igual hoje
- [ ] Stderr NUNCA contém JSON — só logs/erros
- [ ] JSON usa `ensure_ascii=False` (suporte a UTF-8)
- [ ] NDJSON: cada linha é JSON válido (testar com `jq .` por linha)
- [ ] NDJSON: sem newlines dentro dos objetos JSON
- [ ] Erro produz `{"ok": false, "error": {...}}` em qualquer modo
- [ ] `aiw search -o ndjson` faz streaming — eventos aparecem antes do fim

---

## 📚 Referências

- [ndjson-spec v1.0.0](https://github.com/ndjson/ndjson-spec) — especificação oficial do formato
- [kubernetes/cli-runtime print_flags.go](https://github.com/kubernetes/cli-runtime/blob/master/pkg/genericclioptions/print_flags.go) — padrão `-o json` do kubectl
- [cli/cli json_flags.go](https://github.com/cli/cli/blob/b07f955c23fb54c400b169d39255569e240b324e/pkg/cmdutil/json_flags.go) — padrão `--json` do gh CLI
- [typer docs](https://typer.tiangolo.com/) — Annotated options pattern
- `jq` — processador NDJSON nativo: `jq 'select(.type=="done")'`
