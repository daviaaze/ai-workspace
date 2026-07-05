# Conventions

Rules and standards for PI sessions.

## Tone
- Concise, professional
- Use plain English
- Present trade-offs before choosing
- No assumptions — ask when unclear

## Code Quality
- Minimum code that solves the problem
- No speculative abstractions
- Touch only what the request requires
- Match existing style
- Verify with tests before declaring done

## Graph Tools (Mandatory)
- **Before exploring**: `semantic_search_nodes` or `query_graph`
- **Before reviewing**: `detect_changes` + `get_review_context`
- **Before modifying**: `get_impact_radius`
- **For architecture**: `get_architecture_overview` + `list_communities`
- Fallback to read/bash ONLY when graph tools don't cover the need

## Escalation
- **STOP**: prod DB migrations, infra apply, force push, delete branches, modify CI/CD
- **CONFIRM**: commit, push non-main, create PR, install deps, destructive local DB ops
- **GO**: read files, run tests, lint, format, dev server, stage files

## Nix Project Conventions (extracted 2026-06-09)

From analysis of 61 nixfiles sessions:

- **Before running bash in a Nix context**, read the relevant `.nix` file first. Bash failures average 5–17 per session, mostly from Nix build errors or missing tools.
- **Package definitions need 5–15 build iterations.** Budget time for this — it's inherent to Nix packaging, not a failure of approach.
- **Changes to `overlays.nix` affect ALL hosts.** Run `nix flake check` before committing overlay changes.
- **Use `nix build --keep-failed`** when debugging package builds to inspect intermediate artifacts.
- **`performance.nix` and `hardware.nix` are host-specific.** Test on the actual machine, not in CI, before finalizing.

## Debugging
- **Always check runtime logs first**: `journalctl --user _COMM=shade-shell -f` before making assumptions about what's broken
- **Never remove debug prints before the fix is verified in logs.** Keep them at least one restart cycle after the fix seems to work
- **Read the logs line by line** to trace the actual execution path. Do not guess what the code is doing — the logs tell you
- **When the user reports a bug, go check the logs immediately.** Do not ask them to run commands or paste output for me

## Skills-First Workflow
- Before any action, check available skills for a relevant one.
- If a skill matches, follow it exactly.
- If no skill matches, improvise but inform the user and ask if a new skill should be created.

### Skill Catalog

> Full catalog at `pi-setup/skills/SKILL_CATALOG.md` — 28+ skills categorized by workflow phase.

Before any action, check available skills for a relevant one. If a skill matches, follow it exactly.
If no skill matches, improvise but inform the user and ask if a new skill should be created.

The eight skills shipped with this workspace are:
`commit`, `create-pr`, `debug`, `desloppify`, `feature-dev`, `learn`, `onboard`, `pre-review`.

### Custom Extensions

| Extension | Location | Purpose |
|---|---|---|
| `custom-docs` | `~/.pi/agent/extensions/custom-docs/` | Index/search external documentation. `/docs add <url>` → `/docs crawl` → agent uses `search_docs` to find answers. Index stored in `Knowledge-Base/.docs-index/`. |
| `session-name` | `pi-setup/extensions/` | Auto-names sessions from first prompt |
| `permission-gate` | `pi-setup/extensions/` | Confirms before dangerous bash commands (`rm -rf`, `sudo`, etc.) |
| `git-checkpoint` | `pi-setup/extensions/` | Auto-stashes on each turn, offers restore on `/fork` |
| `auto-commit` | `pi-setup/extensions/` | Auto-commits all changes when PI session ends |
| `protected-paths` | `pi-setup/extensions/` | Blocks writes to .env, secrets, SSH keys, node_modules |
| `feature-tester` | `pi-setup/extensions/feature-tester/` | Playwright-powered screenshot/walkthrough/E2E tools (project-specific, not globally loaded) |

> Full catalog with skill and prompt template listings: `pi-setup/skills/SKILL_CATALOG.md`

## Workspace Commits
- Verify branch ≠ `main`/`master` before commit (always work on a topic branch or confirm with user)
- Stage only the files the skill modified — respect `.gitignore`
- Use conventional commits with scope: `docs(memory):`, `feat(workspace):`, `refactor(templates):`
- Keep commits single-concern
- No AI co-authorship
- **CONFIRM** before push — workspace is local-only for now

## Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `security:`
- No AI co-authorship
- Verify branch != `main`/`master` before commit
- Keep commits single-concern

---
## Nix Flakes are Awesome
*2026-07-03 20:10 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 20:10 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 20:21 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 20:21 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 20:30 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 20:30 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 21:10 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 21:10 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 21:53 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 21:53 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 21:58 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 21:58 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:04 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:04 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:08 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:08 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:11 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:11 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:17 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:17 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:19 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:19 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:20 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:20 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:22 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:22 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:24 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:24 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:30 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:30 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:32 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:32 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:35 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:35 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:51 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:51 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:54 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:54 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 22:57 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 22:57 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 23:00 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 23:00 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 23:04 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 23:04 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-03 23:06 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-03 23:06 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 00:33 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 00:33 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 00:58 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 00:58 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 19:55 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 19:55 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 19:57 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 19:57 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 20:04 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 20:04 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 20:07 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 20:07 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 20:09 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 20:09 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 20:11 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 20:11 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 20:14 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 20:14 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 20:18 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 20:18 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 20:22 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 20:22 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 21:06 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 21:06 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 21:18 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 21:18 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 21:35 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 21:35 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 21:41 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 21:41 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 21:45 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 21:45 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-04 22:55 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-04 22:55 UTC*  

Test content

---
## Nix Flakes are Awesome
*2026-07-05 00:50 UTC*  tags: [nix, devops]


Flakes provide reproducible builds and pin dependencies.

---
## Test Convention
*2026-07-05 00:50 UTC*  

Test content
