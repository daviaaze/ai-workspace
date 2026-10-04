# AI Workspace — Usage Guide

## What This Is

A workspace for OMP-compatible agent skills and a knowledge base — a reference for working effectively across projects.

## How Skills Work

Skills are Markdown files with YAML frontmatter. OMP loads them on-demand when their descriptions match a task; skills define workflows, phases, and tool suggestions.

Skills may be available from these locations:

| Location | Purpose |
|---|---|
| `.omp/skills/` | Project skills maintained with this workspace |
| `~/.omp/agent/skills/` | User-authored OMP skills |
| `~/.agents/skills/` | User-level skills shared across agent tools |

## Quick Reference: Most-Used Skills

| Task | Skill |
|---|---|
| Starting something new | `brainstorming` → `authoring` → `delivery` |
| Fixing a bug | `debug` or `systematic-debugging` |
| Creating a PR | `code-review` → `commit` → `create-pr` |
| Learning from mistakes | `learn` |

## Safety Extensions (Always Active)

- **permission-gate** — confirms before dangerous bash commands
- **protected-paths** — blocks writes to .env, secrets, SSH keys
- **git-checkpoint** — auto-stashes at each turn for `/fork` recovery
- **session-name** — auto-names sessions from first prompt
- **auto-commit** — commits changes when session ends

## How to Maintain

- **Keep it lean** — don't add a skill if an existing one covers the need
- **Merge, don't sprawl** — if two skills overlap, merge them
- **Use `learn` to persist** — corrections and patterns go to `memory/`
- **Commit workspace changes** — all workspace docs are git-tracked
