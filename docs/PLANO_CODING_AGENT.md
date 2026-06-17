# AI Workspace — Plano Coding Agent

**Data:** 2026-06-16 | **Status:** Em planejamento
**Contexto:** O pi já faz coding (edit, search, shell, git). Este plano adiciona
as 4 camadas que transformam o agente de "bom" em "excelente".

---

## 🎯 Visão

Um agente de código que:

1. **Entende** o codebase via grafo estrutural (AST + dependências)
2. **Edita** com precisão cirúrgica (search/replace diffs, validação)
3. **Auto-corrige** falhas (edit → lint → test → fix loop)
4. **Respeita** convenções do projeto (.aiwrules)

Tudo rodando **local**, com ferramentas que já existem, sem depender de SaaS.

---

## 📦 O que já está pronto

| Componente | Fonte | Ferramentas |
|-----------|-------|------------|
| **Code Graph** | `../code-review-graph/` | 30 MCP tools: AST, impact radius, communities, flows, semantic search |
| **Pi Extension** | `../code-review-graph/pi-extension/` | Integração nativa pi ↔ MCP server |
| **Filesystem tools** | `ai_workspace/tools/filesystem.py` | read_file, write_file, edit_file, list_dir, search_code |
| **Git tools** | `ai_workspace/tools/git.py` | git_status, git_diff, git_log, git_commit, git_branch, gh_create_pr |
| **Shell sandbox** | `ai_workspace/tools/shell.py` | shell_exec com allowlist |
| **Web tools** | `ai_workspace/tools/web_fetch.py`, `headless_browser.py`, `paginated_scraper.py`, `crawl4ai.py` | web_fetch, headless_browser, paginated_scraper, crawl4ai_scrape |
| **Marketplace** | `ai_workspace/tools/marketplace.py` | mercado_livre_search, olx_search |
| **MCP server** | `ai_workspace/mcp_server/server.py` | 11 tools expostas pra agentes externos |
| **Lint/Test** | `mcp_server/server.py` | run_tests, lint_check |

---

## 🏗️ Arquitetura Alvo

```
┌─────────────────────────────────────────────────────────────────┐
│                      PI CODING AGENT                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Bloco 1: Codebase Graph (code-review-graph)    ✅       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ │   │
│  │  │ AST     │ │ Impact   │ │ Semantic │ │ Architecture │ │   │
│  │  │ Parser  │ │ Radius   │ │ Search   │ │ Overview     │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Bloco 2: Diff Edit Format                       ✅      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                  │   │
│  │  │ Fuzzy    │ │ Multi-   │ │ Syntax   │                  │   │
│  │  │ Match    │ │ Edit     │ │ Validate  │                  │   │
│  │  └──────────┘ └──────────┘ └──────────┘                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Bloco 3: Auto-Fix Loop                           ✅      │   │
│  │  ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌───────┐  │   │
│  │  │ EDIT │──▶│ LINT │──▶│ TEST │──▶│PASS? │──▶│ JUDGE │  │   │
│  │  └──────┘   └──────┘   └──────┘   └──┬───┘   └───┬───┘  │   │
│  │       ▲                              │ fail       │      │   │
│  │       └──────────────────────────────┘           │      │   │
│  │                                     auto-fix     │ alert │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Bloco 4: Project Rules (.aiwrules)              ⬜      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                  │   │
│  │  │ .aiwrules│ │ Auto-    │ │ Per-     │                  │   │
│  │  │ Loader   │ │ Inject   │ │ Project  │                  │   │
│  │  └──────────┘ └──────────┘ └──────────┘                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Backend (aiw): Knowledge Store · Deep Search · Task Scheduler   │
│  Backend (crg): SQLite Graph DB · Tree-sitter · Embeddings       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📐 Bloco 1: Codebase Graph → INTEGRAR

**O que:** Conectar o `code-review-graph` (já pronto) ao workspace atual.

**Ações:**

### 1.1 Build do grafo para ai-workspace
```bash
cd /home/daviaaze/Projects/ai-workspace
code-review-graph build
# Gera .code-review-graph/graph.db com AST, edges, communities
```

### 1.2 Deploy da pi extension
```bash
# Copiar a extension do code-review-graph para o pi
cp ../code-review-graph/pi-extension/code-review-graph.ts \
   ~/.pi/agent/extensions/code-review-graph.ts
```

### 1.3 Configurar auto-update
O code-review-graph já detecta mudanças via git hooks. Verificar se o hook está ativo:
```bash
ls .git/hooks/post-commit  # Deve chamar code-review-graph update
```

**Resultado esperado:** 30 ferramentas de grafo disponíveis no pi, incluindo:
- `get_impact_radius` — blast radius de mudanças
- `query_graph callers_of/callees_of/tests_for` — rastreamento de dependências
- `semantic_search_nodes` — busca semântica por símbolos
- `get_architecture_overview` — visão arquitetural
- `detect_changes` — análise de risco de mudanças

**Esforço:** 30 minutos

---

## ✂️ Bloco 2: Diff Edit Format

**O que:** Evoluir o `EditFileTool` atual (exact match) com fuzzy matching,
múltiplos edits atômicos, e validação pós-edição.

### 2.1 Inspiração: Aider EditBlockCoder

O Aider usa search/replace blocks no prompt do LLM:

```
src/ai_workspace/tools/filesystem.py
<<<<<<< SEARCH
def _resolve_safe(path):
    return Path(path).resolve()
=======
def _resolve_safe(path: str, workspace: str | None = None) -> Path:
    if workspace is None:
        workspace = _default_workspace()
    base = Path(workspace).resolve()
    target = (base / path).resolve()
    target.relative_to(base)  # raises ValueError if outside
    return target
>>>>>>> REPLACE
```

### 2.2 API planejada

```python
class DiffEditInput(BaseModel):
    edits: list[EditBlock]     # Múltiplos edits atômicos
    # Cada EditBlock: {file: str, search: str, replace: str}

class DiffEditTool(BaseTool):
    name: str = "diff_edit"
    description: str = (
        "Apply one or more search/replace edits to files. "
        "Each edit block contains a SEARCH block (exact text to find) "
        "and a REPLACE block (new text). Multiple edits are applied "
        "atomically — all succeed or all roll back."
    )
```

### 2.3 Features

| Feature | Descrição |
|---------|-----------|
| **Multi-edit atômico** | Até 20 edits em uma chamada. Se qualquer um falhar, rollback de todos |
| **Fuzzy matching** | Se exact match falha, tenta: (1) ignorar whitespace, (2) normalizar indentação, (3) buscar por similaridade |
| **Git snapshot** | Antes de cada batch, `git stash` pra desfazer se necessário |
| **Syntax validate** | Após editar, roda `ruff check --fix` ou `python -m py_compile` |
| **Context lines** | Aceita `context_before` e `context_after` pra desambiguar matches múltiplos |

### 2.4 Arquivos

```
src/ai_workspace/tools/diff_edit.py   ← NOVO (~200 linhas)
tests/test_tools/test_diff_edit.py    ← NOVO (~150 linhas)
```

**Esforço:** 2-3 dias

---

## 🔁 Bloco 3: Auto-Fix Loop

**O que:** Orquestra o ciclo edit → lint → test → fix com classificação de erro
e budget por fase.

### 3.1 Inspirações

| Fonte | Padrão | O que copiamos |
|-------|--------|---------------|
| **AgentWhetters** (SWE-bench 1º) | Flat loop + test gate mecânico | Test gate não confia no LLM: roda pytest fora do agente, filtra baseline |
| **Aider** | --auto-test flag | Roda test command, captura exit code, injeta falha no prompt, re-tenta |
| **Ghost** | Judge protocol | Classifica erros: SyntaxError→auto-fix, AssertionError→Judge decide |
| **SWE-AF** | Verify-fix loop c/ checkpoint | Pipeline idempotente, max_cycles, checkpoint entre fases |

### 3.2 Máquina de estados

```
                    ┌─────────┐
                    │  START   │
                    └────┬────┘
                         │
               ┌─────────▼─────────┐
               │ 1. SNAPSHOT GIT   │ ← git stash + tag checkpoint
               └─────────┬─────────┘
                         │
               ┌─────────▼─────────┐
               │ 2. BASELINE TESTS │ ← captura falhas pré-existentes
               └─────────┬─────────┘
                         │
                    ┌────▼────┐  iter < MAX_ITERATIONS (5)
                    │ 3. EDIT  │◄──────────────────────────┐
                    └────┬────┘                            │
                         │ LLM gera diff_edit + reasoning   │
                         │ (usa code-review-graph pra       │
                         │  get_impact_radius antes)        │
                         │                                  │
                    ┌────▼────┐                             │
                    │ 4. LINT  │──fail──► auto-fix ─────────┘
                    └────┬────┘  (ruff --fix)
                         │ pass
                    ┌────▼────┐
                    │ 5. TEST  │  roda pytest -x --tb=short
                    └────┬────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
          ✅            ❌             │
      ALL PASS    FAIL (classifica)     │
           │             │             │
           │     ┌───────┴───────┐     │
           │     │               │     │
           │  SyntaxError    AssertionError
           │  ImportError     RuntimeError
           │     │               │
           │  auto-fix      ┌────▼────┐
           │  (ajusta        │  JUDGE  │
           │   imports,      │  (LLM   │
           │   typos)        │  secundário)
           │     │           └────┬────┘
           │     │           ┌────┴────┐
           │     └───────────┤ "bug no │  "teste errado"
           │                 │  código" │      │
           │                 └────┬─────┘      │
           │                      │            │
           │                   🚨 ALERTA     auto-fix
           │                   (aborta)         │
           │                                   │
           │     iter >= MAX ┌─────────────────┘
           │          │      │
           │     ┌────▼──────▼────┐
           │     │ 6. QA BUDGET   │  QA_BUDGET = 3 turnos extras
           │     └────┬───────────┘
           │          │ esgotou
           │     ┌────▼────┐
           │     │ 7. GIT  │  rollback se tudo falhou
           │     │  RESET  │
           │     └────┬────┘
           │          │
           └──────────┴──────────▶ ✅ DONE (ou ❌ FAILED)
```

### 3.3 API planejada

```python
from dataclasses import dataclass, field
from enum import Enum

class ErrorClass(str, Enum):
    SYNTAX = "syntax"        # SyntaxError, IndentationError
    IMPORT = "import"         # ImportError, ModuleNotFoundError
    RUNTIME = "runtime"       # TypeError, ValueError, etc.
    ASSERTION = "assertion"   # AssertionError
    OTHER = "other"           # Qualquer outro

class FixResult(str, Enum):
    PASSED = "passed"         # Todos os testes passaram
    PARTIAL = "partial"       # Alguns passaram, alguns falharam
    FAILED = "failed"         # Nada passou
    ABORTED = "aborted"       # Judge detectou bug no código fonte

@dataclass
class FixReport:
    result: FixResult
    iterations: int
    errors_fixed: list[str]
    errors_remaining: list[str]
    judge_interventions: int       # quantas vezes o Judge bloqueou
    files_changed: list[str]
    test_output_final: str


class AutoFixLoop:
    """Ciclo edit→lint→test→fix com classificação de erro e budget."""

    def __init__(
        self,
        test_command: str = "pytest -x --tb=short",
        lint_command: str = "ruff check",
        max_iterations: int = 5,
        qa_budget: int = 3,
        use_judge: bool = True,
    ):
        ...

    async def fix(
        self,
        goal: str,
        files: list[str] | None = None,
        extra_context: str = "",
    ) -> FixReport:
        """
        Args:
            goal: "Fix the 12 failing tests in test_store.py"
            files: Escopo opcional (None = repo inteiro)
            extra_context: Dicas adicionais pro LLM
        """
        ...
```

### 3.4 Classificação de erros (Ghost-style)

```python
def classify_error(traceback: str) -> ErrorClass:
    """Classifica um erro de teste pra decidir rota."""
    if "SyntaxError" in traceback or "IndentationError" in traceback:
        return ErrorClass.SYNTAX
    if "ImportError" in traceback or "ModuleNotFoundError" in traceback:
        return ErrorClass.IMPORT
    if "AssertionError" in traceback:
        return ErrorClass.ASSERTION
    if "Error" in traceback:
        return ErrorClass.RUNTIME
    return ErrorClass.OTHER
```

### 3.5 Judge Protocol

Quando um AssertionError ocorre, o Judge (LLM secundário, modelo mais barato)
analisa:

1. O teste que falhou (código fonte do teste)
2. O código sendo testado
3. A mensagem de assertion

E decide:

| Veredito | Ação |
|----------|------|
| **"Fix test"** | O teste tem expectativa errada → auto-fix ajusta o teste |
| **"Bug in code"** | O código fonte tem bug → 🚨 ALERTA, não modifica o teste |
| **"Unclear"** | Não tem certeza → tenta fix conservador, se falhar alerta |

```python
JUDGE_PROMPT = """You are a code judge. Analyze this test failure:

TEST CODE:
{test_code}

SOURCE CODE BEING TESTED:
{source_code}

ASSERTION ERROR:
{assertion_error}

Is the test expectation wrong, or is there a bug in the source code?
Answer ONLY: "FIX_TEST" or "BUG_IN_CODE" or "UNCLEAR"
Reason: <one sentence>
"""
```

### 3.6 Integração com code-review-graph

Antes de cada edição, o loop consulta o grafo:

```python
# Antes de editar: qual o blast radius?
impact = graph.get_impact_radius(changed_files=["src/file.py"])
if impact["total_impacted"] > 50:
    # Alerta: mudança de alto impacto — sugerir revisão manual
    ...

# Antes de editar função X: quem chama X?
callers = graph.query_graph(pattern="callers_of", target="function_x")
# Injeta no prompt: "Cuidado: function_x é chamada por A, B, C"

# Depois de editar: quais fluxos afetados?
flows = graph.get_affected_flows(changed_files=["src/file.py"])
```

### 3.7 Arquivos

```
src/ai_workspace/tools/auto_fix.py    ← NOVO (~400 linhas)
tests/test_tools/test_auto_fix.py     ← NOVO (~250 linhas)
```

**Esforço:** 3-4 dias

---

## 📋 Bloco 4: Project Rules (.aiwrules)

**O que:** Arquivo de convenções que o agente lê antes de qualquer ação.

### 4.1 Inspiração: Cline .clinerules + Aider .aider.conf.yml

### 4.2 Formato

```yaml
# .aiwrules — AI Workspace Rules
# O agente lê este arquivo antes de qualquer ação de código.

project:
  name: "AI Workspace"
  language: python
  python_version: "3.12+"
  package_manager: uv

style:
  formatter: ruff
  line_length: 100
  quote_style: double  # " vs '
  type_hints: always    # always | optional | never

testing:
  framework: pytest
  async_mode: auto      # pytest-asyncio mode
  coverage_target: 80   # percent

architecture:
  # Regras que o agente DEVE seguir
  rules:
    - "Use Pydantic v2.BaseModel, not v1"
    - "Use crewAI Flows for orchestration, not raw Agent loops"
    - "Database connections must use connection pooling (psycopg2.pool)"
    - "Never use print() for logging — use structlog"
    - "Never hardcode API keys — use pydantic-settings"
    - "All new tools must live in src/ai_workspace/tools/"
    - "Tests mirror src structure under tests/"

  # Padrões que o agente DEVE usar
  patterns:
    tool: "class {Name}Tool(BaseTool): name='{snake}' description='...'"
    test: "async def test_{name}(): ..."
    migration: "Semantic version in graph.db via migrations.py"

  # O que o agente NUNCA deve fazer
  never:
    - "Don't remove type hints"
    - "Don't use async without asyncio_mode=auto in pytest"
    - "Don't import from crewai.tools.BaseTool directly — use ai_workspace.tools"
    - "Don't modify pyproject.toml dependencies without asking"
    - "Don't push to main without PR review"

git:
  commit_style: conventional  # conventional | simple
  branch_naming: "feature/{description}"  # padrão de branch
  pr_template: ".github/pull_request_template.md"
```

### 4.3 Implementação

```python
# src/ai_workspace/tools/rules.py

import yaml
from pathlib import Path
from typing import Any

class ProjectRules:
    """Carrega e expõe as regras do .aiwrules."""

    def __init__(self, workspace_root: Path | None = None):
        self.root = workspace_root or Path.cwd()
        self.rules_path = self.root / ".aiwrules"
        self._rules: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        """Carrega as regras do arquivo YAML."""
        if not self.rules_path.exists():
            return {}
        with open(self.rules_path) as f:
            self._rules = yaml.safe_load(f)
        return self._rules

    def to_system_prompt(self) -> str:
        """Converte regras em texto injetável no system prompt."""
        if not self._rules:
            return ""

        lines = ["\n## Project Rules (.aiwrules)\n"]

        arch = self._rules.get("architecture", {})
        if rules := arch.get("rules", []):
            lines.append("### You MUST:")
            for r in rules:
                lines.append(f"- {r}")

        if patterns := arch.get("patterns", []):
            lines.append("\n### Use these patterns:")
            for name, tmpl in patterns.items():
                lines.append(f"- `{name}`: `{tmpl}`")

        if never := arch.get("never", []):
            lines.append("\n### You MUST NOT:")
            for n in never:
                lines.append(f"- {n}")

        return "\n".join(lines)
```

### 4.4 Integração no pi

A extension do aiw (`~/.pi/agent/extensions/aiw/index.ts`) injeta as regras
no system prompt via `before_agent_start`:

```typescript
pi.on("before_agent_start", async (event) => {
    const rulesPath = resolve(event.cwd, ".aiwrules");
    if (existsSync(rulesPath)) {
        const rules = readFileSync(rulesPath, "utf-8");
        // Parse YAML e converter em texto
        // Inject no system prompt
    }
});
```

### 4.5 Arquivos

```
.aiwrules                              ← NOVO (template na raiz)
src/ai_workspace/tools/rules.py        ← NOVO (~100 linhas)
tests/test_tools/test_rules.py         ← NOVO (~80 linhas)
```

**Esforço:** 1 dia

---

## 📅 Timeline

```
SEMANA 1                     SEMANA 2
│                            │
├─ Bloco 1: Integrar CRG ────┤
│  (30 min)                  │
│                            │
├─ Bloco 4: .aiwrules ───────┤
│  (1 dia)                   │
│                            │
├─ Bloco 2: Diff Edit ───────┤ (já implementado)
│  (início)                  │  (conclusão)              │
│                            │                           │
│                            ├─ Bloco 3: Auto-Fix ───────┼─── Bloco 3: Auto-Fix ────┤
│                            │  (início)                 │  (conclusão)             │
```

| Bloco | O que | Esforço | Depende de |
|-------|-------|---------|------------|
| 1 | Integrar code-review-graph | 30 min | Nada |
| 4 | .aiwrules | 1 dia | Nada |
| 2 | Diff Edit Format | 2-3 dias | Bloco 1 (graph ajuda) |
| 3 | Auto-Fix Loop | 3-4 dias | Blocos 1 + 2 |

---

## 🔗 Dependências externas

| Dependência | Já temos? | Ação |
|------------|----------|------|
| `code-review-graph` (Python) | ✅ Instalado no .venv | Buildar grafo (`code-review-graph build`) |
| `code-review-graph` pi extension | ✅ Pronto em `../code-review-graph/pi-extension/` | Copiar pra `~/.pi/agent/extensions/` |
| `tree-sitter` language pack | ✅ Nix result linkado | Verificar se Python acessa |
| `networkx` | ✅ No .venv | Nada |
| `pyyaml` | ✅ No .venv | Nada |
| `pytest` | ✅ No .venv | Corrigir libstdc++ numpy issue |

---

## 📊 Métricas de sucesso

| Métrica | Alvo | Como medir |
|---------|------|------------|
| **Build do grafo** | < 30s para repo de 200 arquivos | `time code-review-graph build` |
| **Precisão do diff edit** | > 95% de edits aplicados sem conflito | Testes com cenários de edição |
| **Auto-fix rate** | > 60% de falhas de teste corrigidas automaticamente | Rodar contra testes quebrados do projeto |
| **Judge accuracy** | > 80% de concordância com decisão humana | Validar contra 50 casos conhecidos |
| **Tempo de ciclo** | < 3 min por iteração (edit+lint+test) | Timing do loop completo |

---

## 🚀 Ordem de execução recomendada

1. **Agora:** Conectar code-review-graph (build + extension) — 30 min
2. **Agora:** Criar `.aiwrules` template — 15 min
3. **Próxima sessão:** Implementar Diff Edit Format
4. **Depois:** Implementar Auto-Fix Loop

---

> **Nota:** Este plano complementa `PLANO_AIW_V2_VALIDADO.md`. O aiw segue como backend
> de pesquisa + conhecimento. O coding agent é a camada que roda no pi, consumindo
> ferramentas do aiw + code-review-graph + as 4 novas camadas deste plano.
