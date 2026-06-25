# AI Workspace Research Brief — 2026-06-09

> Cross-referencing PI platform capabilities, AI workspace best practices, and
> third-party ecosystems against our current ai-workspace setup.

---

## 1. Current State Assessment

### ✅ What We Have Right

| Area | Status |
|------|--------|
| `AGENTS.md` context file | ✅ Loaded every session — workspace path, conventions, graph tools |
| Skills catalog | ✅ 8 shipped skills with SKILL.md files in `pi-setup/skills/` |
| Custom extension (`custom-docs`) | ✅ Docs indexing/search in Knowledge-Base |
| Code-review-graph extension | ✅ Managed via Nix, works in project repos |
| Prompt templates | ✅ 10 templates in `~/.pi/agent/prompts/` (backed up to pi-setup) |
| Git hooks & template | ✅ Pre-commit hook + .gitmessage (from upgrade) |
| Modular pi-setup | ✅ Restructured, deploy.sh ready |
| Memory system | ✅ Conventions, patterns, learning log |

### 🐛 Known Issues

| Issue | Status |
|-------|--------|
| Stale `.backup` / `.hm-backup` in extensions/ | ✅ Cleaned |
| Prompt templates not backed up to pi-setup | ✅ Backed up to `pi-setup/prompts/` |
| `feature-tester` extension from Lux project | Still present (38KB, unrelated) |
| No custom theme | Still using defaults |
| No third-party PI packages installed | Untapped potential |

---

## 2. PI Platform: What's Available We're Not Using

### Extensions (We Have 2, PI Supports Unlimited)

Our current: `code-review-graph` + `custom-docs`

**High-value extensions we could build or install:**

| Extension | Value |
|-----------|-------|
| **Plan mode** | Read-only exploration — safe analysis without accidental changes |
| **Git checkpoint** | Auto-stash at each assistant turn, restore on `/fork` |
| **Permission gate** | Confirm before `rm -rf`, `sudo`, destructive commands |
| **Protected paths** | Block writes to `.env`, `node_modules/`, etc. |
| **Auto-commit-on-exit** | Commit changes when session ends |
| **Todo list** | Persistent session-level todos the LLM manages |
| **Session name** | Auto-name sessions from first prompt |
| **Handoff** | Goal-driven context transfer between sessions |
| **Custom footer** | Show thinking level, model, branch in footer |

### Packages on npm/git We Could Install

| Package | What It Gives Us | Source |
|---------|------------------|--------|
| `danchamorro/pi-toolkit` | 24 extensions, 34 skills, agent modes | GitHub |
| `aldoborrero/pi-agent-kit` | 33 extensions, 6 agent definitions | GitHub |
| `ruizrica/agent-pi` | 43 extensions, 11 themes, 20+ skills | GitHub |
| `jayshah5696/pi-agent-extensions` | Sessions picker, ask_user tool, handoff | GitHub |
| `fgladisch/pi-skills` | Advanced skill library | GitHub |

### Prompt Templates We Have

Already have 10 solid ones: `review`, `explain`, `test`, `research`, `refactor`, `adr`, `analyze`, `feature`, `learn`, `summarize`.

**Potential additions:**
| Template | Trigger | Purpose |
|----------|---------|---------|
| `debug` | `/debug` | Hypothesis-driven debug workflow |
| `pr` | `/pr` | Create PR description |
| `changelog` | `/changelog` | Generate changelog from git log |
| `onboard` | `/onboard` | Quick project onboarding |

### Custom Theme

PI themes hot-reload. We could create a custom theme with our preferred colors —
dark mode with better contrast for the editor, custom accent colors, etc.

---

## 3. AI Workspace Best Practices (2026 Landscape)

### Key Trends

**1. AGENTS.md is the universal standard**
All major tools (Claude Code, Codex, Cursor, Copilot) now use AGENTS.md/CLAUDE.md.
Our setup follows this well — but the research suggests structured sections with
clear boundaries between "rules," "context," and "workflows" works best.

**2. Progressive disclosure**
Skills descriptions are always in context; full instructions load on-demand.
We already follow this pattern correctly.

**3. Isolated workspaces for parallel agents**
Git worktrees + spec-scoped tasks + automated review gates.
We have the `using-git-worktrees` skill ✓

**4. MCP-based knowledge bases**
AKB (Agent Knowledge Base) and Context Palace serve docs over MCP.
Our `custom-docs` extension is conceptually similar but uses local markdown files
instead of MCP — simpler, no server dependency.

**5. Structured task management**
YAML frontmatter tasks with state tracking, priorities, dependencies.
We already use markdown-based feature tickets (Templates/feature-ticket.md).

**6. Session journaling**
Append-only daily logs preserve full history.
Our `memory/learning-log.md` follows this pattern.

### Gaps vs Best Practices

| Gap | Severity | Quick Fix? |
|-----|----------|------------|
| No plan mode (read-only exploration) | Medium | Install package or build extension |
| No git checkpointing on each turn | Low | 50-line extension |
| No permission gate for dangerous commands | Low | 30-line extension |
| Third-party packages not explored | Medium | Try `pi install` |
| No custom theme | Low | Copy + tweak default theme |
| AGENTS.md could be more structured | Low | Minor edit |
| No auto-commit-on-exit | Medium | 40-line extension |
| No session auto-naming | Low | 15-line extension |

---

## 4. Recommended Next Steps

### Tier 1 — Quick Wins (30 min total)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | Install one PI package to explore the ecosystem | 5 min | High |
| 2 | Add `debug` + `pr` prompt templates | 10 min | Medium |
| 3 | Create custom theme from default dark theme | 10 min | Low |
| 4 | Build session auto-naming extension | 5 min | Medium |

### Tier 2 — Valuable Builds (2-3 hours)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 5 | Build git checkpoint extension | 30 min | High |
| 6 | Build permission gate extension | 20 min | High |
| 7 | Build plan-mode extension | 1-2 hr | High |
| 8 | Package custom-docs as a proper PI package | 30 min | Medium |

### Tier 3 — Strategic

| # | Action | Why |
|---|--------|-----|
| 9 | Explore `danchamorro/pi-toolkit` or `ruizrica/agent-pi` | See what full-featured setup looks like |
| 10 | Create a PI package from our `pi-setup/` for homelab distribution | npm-installable workspace |
| 11 | Add MCP-based knowledge base (AKB) if needed for multi-agent | Future-proofing |
| 12 | Set up session publishing (OSS sessions on Hugging Face) | Community contribution |

---

## 5. Key Sources

- **PI official docs:** `/nix/store/.../pi-monorepo/docs/` (extensions, skills, packages, TUI, SDK)
- **PI examples:** `/nix/store/.../pi-monorepo/examples/extensions/` (60+ example extensions)
- **danchamorro/pi-toolkit:** GitHub — 24 extensions, 34 skills, safety guardrails
- **ruizrica/agent-pi:** GitHub — 43 extensions, 11 themes, 6 modes
- **aldoborrero/pi-agent-kit:** GitHub — 33 extensions, 6 agent definitions
- **fgladisch/pi-skills:** GitHub — Advanced skill library
- **jayshah5696/pi-agent-extensions:** GitHub — sessions, ask_user, handoff
- **Augment Code (2026):** Multi-agent coding workspace guide
- **amux.io (2026):** Agentic engineering — parallel AI coding agents
- **youngju.dev (2026):** AI coding workflow best practices — AGENTS.md, skills, MCP deep dive
