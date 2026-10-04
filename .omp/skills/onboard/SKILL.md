---
name: onboard
description: Analyze a new repository and create a project context note in the workspace. Use when entering a new codebase, starting work on a new project, or the user says onboard, analyze this repo, or understand this project.
---

# Onboard Workflow

## Trigger
Onboard, analyze this repo, understand this project, entering a new codebase.

## Workflow

1. **Identify** — determine repo name, primary language, framework.
2. **Graph build** — run `build_or_update_graph` to index the codebase.
3. **Architecture** — `get_architecture_overview` + `list_communities` for module structure.
4. **Hotspots** — `get_hub_nodes` for most connected files, `get_bridge_nodes` for chokepoints.
5. **Execution paths** — `list_flows` for critical entry points, `find_large_functions` for refactoring candidates.
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
