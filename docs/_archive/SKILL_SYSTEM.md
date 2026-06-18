# Skill System — Pi-Compatible Workflows as Agent Tasks

> **Data:** 2026-06-16 | **Status:** ✅ Implemented | **Arquivo:** `skills/loader.py`
> **Skills disponíveis:** 13 (12 project + 1 user)

---

## 🎯 Problema

Pi tem 12 skills (debug, feature-dev, commit, pre-review, nixfiles, etc.) definidas como SKILL.md com
workflows estruturados. O aiw tinha agentes genéricos mas nenhuma forma de carregar e executar esses
workflows pré-definidos. Cada skill define um processo específico que o agente deve seguir — sem elas,
o agente improvisa.

---

## 🧠 Solução: SkillLoader

Um carregador que descobre SKILL.md files de diretórios padrão, extrai os passos do workflow,
e os injeta como task descriptions para agentes crewAI.

### Arquitetura

```
pi-setup/skills/          ~/.agents/skills/        ~/.pi/agent/skills/
      │                         │                         │
      └─────────────────────────┼─────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │     SkillLoader        │
                    │                        │
                    │  discover() → 13 skills│
                    │  get(name)  → Skill    │
                    │  run(name, task) → str │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   build_task_desc()   │
                    │                        │
                    │  Workflow steps +      │
                    │  rules + user task     │
                    │  → formatted prompt   │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    crewAI Agent        │
                    │    + tools             │
                    │    → kickoff()         │
                    └───────────────────────┘
```

### Formato SKILL.md

```markdown
---
name: debug
description: Hypothesis-driven debugging. Use when tests are failing...
---

# Debug Workflow

## Workflow

1. **Understand** — read errors and stack traces...
2. **Hypothesize** — list 2-3 most likely causes...
3. **Instrument** — add targeted logs...
...
```

O parser extrai:
- **Frontmatter**: `name`, `description` (obrigatório)
- **Workflow steps**: formato `1. **Nome** — descrição` ou bullets sob `## Phase`
- **Fallback**: corpo inteiro se nenhum formato reconhecido

---

## 📋 Skills Disponíveis

| Skill | Fonte | Passos | Descrição |
|-------|-------|--------|-----------|
| `commit` | project | 14 | Conventional commit seguro |
| `create-pr` | project | 11 | PR com tabela de testes |
| `daily` | project | 4 | Notas de stand-up diárias |
| `debug` | project | 15 | Debugging com hipóteses |
| `deep-research` | project | 8 | Pesquisa profunda recursiva |
| `deploy-checklist` | project | 3 | Checklist de deploy |
| `desloppify` | project | 10 | Limpeza de artefatos de IA |
| `feature-dev` | project | 13 | Feature end-to-end |
| `learn` | project | 3 | Persistir convenções/padrões |
| `nixfiles` | project | 5 | Gerenciar config NixOS |
| `onboard` | project | 13 | Analisar repo novo |
| `pre-review` | project | 21 | Self-review antes do PR |
| `docs-keeper` | user | 15 | Auditoria de documentação |

As skills `debug`, `feature-dev`, `commit`, `create-pr`, `desloppify`, `pre-review`, `nixfiles` e
`deep-research` cobrem o ciclo completo de desenvolvimento: pesquisar → implementar → debugar →
limpar → revisar → commitar → abrir PR.

---

## 🔗 CLI

```bash
# Listar skills
aiw skill list

# Executar uma skill
aiw skill run debug "tests failing in test_store.py"
aiw skill run feature-dev "add user authentication flow"
aiw skill run commit
aiw skill run pre-review
```

### Exemplo de execução

```
$ aiw skill run debug "test_store.py:12 fails with AssertionError"

🛠️  Skill: debug
Hypothesis-driven debugging. Use when tests are failing...
Provider: ollama | Model: qwen3:14b

Workflow:
  1. Understand: read errors and stack traces...
  2. Hypothesize: list 2-3 most likely causes...
  3. Instrument: add targeted logs...
  ...

[Agent executes each step using filesystem, git, shell, and test tools]
```

---

## 🧩 Integração com o TUI

O `AgentWorker` aceita qualquer task description — skills são injetadas como descrições formatadas.
No TUI, o usuário pode digitar `skill:debug tests failing` na barra de comando e o agente segue o
workflow estruturado.

A integração completa (skill picker no SpawnDialog, `:skill <name>` no command bar) está planejada
mas não implementada. Hoje o fluxo é via CLI ou digitando `skill:<name> <task>` na barra do TUI.

---

## 📁 Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `src/ai_workspace/skills/loader.py` | SkillLoader — descoberta, parsing, execução |
| `src/ai_workspace/skills/__init__.py` | Exports |
| `src/ai_workspace/cli.py` | `aiw skill list` e `aiw skill run` |
| `pi-setup/skills/*/SKILL.md` | 12 skills do projeto |
| `~/.agents/skills/docs-keeper/SKILL.md` | 1 skill do usuário |

---

## 🔮 Extensões Futuras

- **Skill picker no TUI**: `Ctrl+S` abre lista de skills, Enter seleciona
- **Skill templates**: Criar novas skills via `aiw skill create <name>`
- **Skill chaining**: `feature-dev → desloppify → pre-review → commit → create-pr`
- **Skill-specific tools**: Algumas skills podem precisar de ferramentas específicas
  (ex: `nixfiles` precisa de acesso ao diretório de configuração NixOS)
