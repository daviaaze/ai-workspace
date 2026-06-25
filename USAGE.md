# AI Workspace — Usage Guide

## What This Is

A curated PI coding agent setup with skills, extensions, and a workspace knowledge base. This is the "treasure map" for the agent — everything it needs to work effectively across projects.

## How Skills Work

Skills are Markdown files with YAML frontmatter. PI loads them **on-demand** — when a user message matches a skill's `description` field, PI suggests that skill. Skills define workflows with phases, exit points, and tool suggestions.

Skills live in two locations:

| Location | Purpose | Managed by |
|---|---|---|
| `~/.pi/agent/skills/` | **Your skills** — custom, authored by you | You (manual) |
| `~/.agents/skills/` | **Installed skills** — from PI skill registry | `pi /skill:install` |

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
