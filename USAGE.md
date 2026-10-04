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
| Starting something new | `onboard` → `feature-dev` |
| Fixing a bug | `debug` |
| Creating a PR | `pre-review` → `commit` → `create-pr` |
| Learning from mistakes | `learn` |

## Host and Profile Configuration

The former AIW application and its MCP server are not required. This repository
does not bundle or activate agent extensions. Models, credentials, permissions
and safety extensions are managed by the active OMP host/profile configuration.

## How to Maintain

- **Keep it lean** — don't add a skill if an existing one covers the need
- **Merge, don't sprawl** — if two skills overlap, merge them
- **Use `learn` to persist** — corrections and patterns go to `memory/`
- **Commit workspace changes** — all workspace docs are git-tracked
