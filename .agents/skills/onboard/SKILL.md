---
name: onboard
description: Analyze a new repository and create a project context note in the workspace. Use when entering a new codebase, starting work on a new project, or the user says onboard, analyze this repo, or understand this project.
---

# Onboard Workflow

## Trigger
Onboard, analyze this repo, understand this project, entering a new codebase.

## Workflow

1. **Identify** — determine repo name, primary language, framework.
2. **Structure** — map the repo layout with `find_path`/`ls`; identify frameworks, build system, and config files.
3. **Architecture** — infer module structure from the directory tree and import graph (`grep` for cross-module references).
4. **Hotspots** — find the most-connected files by grepping for who imports each module; flag large files as refactoring candidates.
5. **Execution paths** — locate entrypoints (`grep` for `def main`, routes, handlers, CLI entrypoints) and trace the critical flows.
6. **Document** — create or update a project note with role, commands, setup notes, hotspots, and gotchas.
7. **Commit** — stage the workspace note and commit with `docs(projects): onboard <repo-name>`.

## Output Shape

```markdown
# <repo-name>

**Path:** <repo path>
**Role:**

## Read First
- repo README
- repo-local AGENTS.md
- relevant workspace notes

## Common Commands
| Task | Command |
|---|---|

## Local Setup Notes
- 

## Review Hotspots
- 

## Known Gotchas
- 
```

## Exit Points
- After graph build
- After architecture overview
- After workspace note creation
