# Pi Agent Configuration Review

**Date:** 2026-07-11
**Scope:** Full audit of `~/.pi/agent/settings.json`, packages, extensions, skills, rules, prompts, deploy system, and resource footprint.

---

## Token Budget Assessment

### System Prompt Overhead

| Component | Estimated Tokens | Notes |
|-----------|-----------------|-------|
| AGENTS.md (rules/00-global.md) | ~665 | 2,326 bytes — loaded every session |
| rules/01-code.md | ~258 | 902 bytes — loaded as context, conditional |
| rules/02-infra.md | ~283 | 990 bytes — loaded as context, conditional |
| Skill descriptions (9 skills) | ~360 | Name + desc only (~40/token each) in system prompt |
| Tool descriptions (9 extensions) | ~1,800 | ~200/tool avg; crg-trim registers 6 MCP tools with full param schemas |
| Package tool registrations | ~1,400 | 7 npm packages, each adds tools/skills (pi-subagents alone is substantial) |
| **Total baseline** | **~4,766** | Per session before any work begins |

### Per-Turn Waste

| Source | Tokens/Turn | Notes |
|--------|-------------|-------|
| Duplicate AGENTS.md content | ~665 | **AGENTS.md** is a symlink to **rules/00-global.md** — identical content loaded twice |
| Competing status slots | ~80 | No `quietStartup` — startup header + progress bar + terminal progress |
| Startup notifications | ~300 | Per session, `session_start` hooks fire notifications |
| Unused package overhead | ~400 | Gemini CLI provider and antigravity OAuth may not be used |
| **Total waste** | **~1,445** | Per session |

---

## Package Analysis

### 1. `npm:@juicesharp/rpiv-ask-user-question`
**Status:** ⚠️ Possibly unused
**Resources loaded:** Unknown (extension + skills likely)
**Token impact:** ~200 tokens per session (tool descriptions)
**Recommendation:** Keep — useful for structured user input. Could filter to only load `extensions` if skills aren't needed.

### 2. `npm:@juicesharp/rpiv-todo`
**Status:** ✅ Used (referenced by `daily` skill workflow)
**Resources loaded:** Unknown (likely extension + skills)
**Token impact:** ~200 tokens per session
**Recommendation:** Keep. No filtering needed.

### 3. `npm:pi-subagents`
**Status:** ✅ Used (this session is running via pi-subagents)
**Resources loaded:** Extensions (agent delegation tools), skills (subagent workflow skills)
**Token impact:** ~500+ tokens per session (subagent tool description alone is substantial)
**Recommendation:** Keep. This is critical infrastructure. Consider filtering skills if `INHERIT_SKILLS=0` is always used.

### 4. `npm:pi-mcp-adapter`
**Status:** ⚠️ Possibly unused
**Resources loaded:** MCP protocol adapter tools
**Token impact:** ~300 tokens per session
**Recommendation:** **Review.** If no MCP servers are configured, this package adds tool descriptions for zero benefit.

### 5. `npm:pi-observational-memory`
**Status:** ✅ Active (replaces default compaction)
**Resources loaded:** Extension (recall tool), compaction hook
**Token impact:** ~200 tokens per session (tool description) + operational overhead
**Recommendation:** Keep. But note: **compaction is not configured** in `settings.json`. The `compaction` key is missing entirely, so Pi may be using default compaction alongside observational-memory. This creates **overlapping compaction strategies** — a token waste issue.

### 6. `npm:@skdev-ai/pi-gemini-cli-provider`
**Status:** ❌ Likely unused
**Resources loaded:** Provider extension (registers Gemini CLI as a provider)
**Token impact:** ~200 tokens per session
**Recommendation:** **Remove.** The default provider is `atlas-cloud` with `deepseek-ai/deepseek-v4-flash`. Unless the user switches to Gemini CLI regularly, this package loads provider infrastructure that is never used.

### 7. `npm:@raquezha/antigravity`
**Status:** ❌ Likely unused
**Resources loaded:** Google OAuth authentication provider
**Token impact:** ~200 tokens per session
**Recommendation:** **Remove.** Unless using Google OAuth for authentication, this adds tool descriptions for a provider that isn't the default.

---

## Configuration Issues

### 1. Duplicate AGENTS.md / rules/00-global.md
**File:** `~/.pi/agent/`
**Current:** AGENTS.md → `rules/00-global.md` AND `rules/00-global.md` → `rules/00-global.md` (both are symlinks to the same source file)
**Problem:** The deploy script creates both `~/.pi/agent/AGENTS.md` and `~/.pi/agent/rules/00-global.md` as symlinks to the same source. Pi loads AGENTS.md automatically at session start AND rules/00-global.md as a rule context file. This doubles the token cost of the global rules (~665 extra tokens per session).
**Recommendation:** Remove the `rules/00-global.md` symlink since AGENTS.md already loads the same content. The deploy script's `ensure_root_dirs` creates `rules/` and then the loop links all `*.md` files, which includes 00-global.md. Either:
  - Exclude 00-global.md from the rules symlink loop, or
  - Keep only AGENTS.md and remove rules/00-global.md

### 2. Missing `compaction` configuration
**File:** `settings.json`
**Current:** Not set
**Problem:** The `pi-observational-memory` package is installed (which replaces default compaction with a tiered system), but no `compaction` block exists in `settings.json`. This means Pi may use default compaction settings alongside observational-memory, creating overlapping/conflicting memory management strategies.
**Recommendation:** Add explicit compaction config:
```json
{
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  }
}
```

### 3. Missing `quietStartup`
**File:** `settings.json`
**Current:** Not set (defaults to `false`)
**Problem:** Startup header is shown every session, adding ~200-300 tokens of visible output and UI noise.
**Recommendation:** Add `"quietStartup": true` to reduce session startup bloat.

### 4. Invalid `theme` value
**File:** `settings.json`
**Current:** `"theme": "light/dark"`
**Problem:** `"light/dark"` is not a standard Pi theme name. Pi expects either `"light"`, `"dark"`, or a valid custom theme path. The slash format may cause theme loading to fail silently, falling back to default.
**Recommendation:** Set to `"light"` or `"dark"` based on preference, or use a valid custom theme path.

### 5. Overly large `enabledModels` list
**File:** `settings.json`
**Current:** 37 model entries across 4 providers (opencode 19, opencode-go 13, atlas-cloud 2, kimi-coding 3)
**Problem:** The model selector UI has 37 entries. Most are variants of the same models from different providers. The `opencode` and `opencode-go` providers alone account for 32 entries. Many of these are unlikely to be used (e.g., `big-pickle`, `north-mini-code-free`, `nemotron-3-ultra-free`).
**Recommendation:** Trim to 5-10 most-used models. The rest can be added on demand via `/model` or Pi's model discovery. Suggested keep-list:
  - `atlas-cloud/deepseek-ai/deepseek-v4-flash` (default)
  - `atlas-cloud/deepseek-ai/deepseek-v4-pro` (full model)
  - `opencode-go/deepseek-v4-flash` (backup)
  - `opencode-go/qwen3.7-plus` or similar
  - `opencode-go/kimi-k2.7-code`
  - `opencode-go/gemini-3.1-pro-preview` or similar

### 6. 106 models in models.json (27KB)
**File:** `~/.pi/agent/models.json`
**Current:** 106 model entries in the atlas-cloud provider, totaling 27KB
**Problem:** This file is read every session to populate the model selector. 27KB is significant for a configuration file that the user may only use 2-3 models from.
**Recommendation:** Trim to 15-20 most-used models. The models-profile.json in pi-setup is the source of truth — it can be kept full for reference, but the deployed models.json should be lean.

### 7. `doubleEscapeAction: "tree"`
**File:** `settings.json`
**Current:** `"doubleEscapeAction": "tree"`
**Problem:** Double-escape opens the tree view. This is a valid setting but may not be the user's preferred behavior. The "tree" action is typically used for file navigation, but if the user rarely uses the tree, it's wasted keybind.
**Recommendation:** Consider `"doubleEscapeAction": "minimize"` for session management, or keep as-is if the tree is actively used.

### 8. Settings-profile doesn't match actual settings.json
**File:** `pi-setup/settings-profile.json` vs `~/.pi/agent/settings.json`
**Current:** The profile has no `compaction`, `quietStartup`, `enabledModels`, `showHardwareCursor`, `terminal`, `hideThinkingBlock`, `defaultThinkingLevel`, `lastChangelogVersion`, or `enableInstallTelemetry`.
**Problem:** The profile is missing several keys that the actual settings.json has. The deploy script does a "skip if exists" merge, so the profile is only used for initial setup. But if the user ever needs to regenerate, they'd lose settings.
**Recommendation:** Sync the profile with actual settings. Add all missing keys to settings-profile.json.

---

## Extension Analysis

### 1. `crg-trim.ts` (18,337 bytes)
**Status:** ✅ Active
**Token impact:** High — 6 MCP tools registered with full parameter schemas, plus MCP transport overhead
**Recommendation:** This is the leanest version (trimmed from 28+ to 6 tools), but it's still 18KB. Consider whether all 6 tools are needed every session. The MCP server startup also adds latency. No change needed — but if token budget is tight, consider inlining the 6 tools as native Pi tools instead of MCP.

### 2. `auto-commit.ts` (1,402 bytes)
**Status:** ✅ Active
**Token impact:** Low — registers a session_shutdown hook only
**Recommendation:** Keep. Small footprint, useful functionality.

### 3. `git-checkpoint.ts` (2,191 bytes)
**Status:** ✅ Active
**Token impact:** Low — registers a before_agent_start hook for stashing
**Recommendation:** Keep. Useful for /fork workflow.

### 4. `login.ts` (1,968 bytes)
**Status:** ⚠️ Possibly unused
**Token impact:** Low — registers a `/login` command
**Recommendation:** Keep. Important for API key management, but only invoked on demand.

### 5. `permission-gate.ts` (2,584 bytes)
**Status:** ✅ Active
**Token impact:** Low — intercepts tool calls via regex matching
**Recommendation:** Keep. Safety-critical extension.

### 6. `protected-paths.ts` (2,742 bytes)
**Status:** ✅ Active
**Token impact:** Low — intercepts file operations
**Recommendation:** Keep. Safety-critical extension.

### 7. `rtk.ts` (3,422 bytes)
**Status:** ✅ Active
**Token impact:** Low — intercepts bash commands for rewriting
**Recommendation:** Keep. Token-saving extension.

### 8. `session-name.ts` (939 bytes)
**Status:** ✅ Active
**Token impact:** Minimal — registers a before_agent_start hook
**Recommendation:** Keep. Small footprint.

### 9. `workspace-search.ts` (3,298 bytes)
**Status:** ✅ Active
**Token impact:** Medium — registers a `workspace_search` tool and `/ws` command
**Recommendation:** Keep. Useful for knowledge base search.

---

## Skill Analysis

### Description Quality Assessment

| Skill | Description Quality | Risk |
|-------|-------------------|------|
| `commit` | ✅ Good — clear trigger + purpose | Low |
| `create-pr` | ✅ Good — clear trigger + purpose | Low |
| `daily` | ✅ Good — comprehensive trigger list | Low |
| `debug` | ✅ Good — clear trigger + purpose | Low |
| `deep-research` | ⚠️ Adequate — "deep, recursive research" is vague | Low |
| `desloppify` | ✅ Good — clear trigger + purpose | Low |
| `feature-dev` | ⚠️ Slightly verbose — "Start and work through a feature or task end-to-end" is fine but the skill itself is 7.6KB | Medium |
| `learn` | ✅ Good — clear trigger + purpose | Low |
| `nixfiles` | ✅ Good — clear trigger + purpose | Low |
| `onboard` | ✅ Good — clear trigger + purpose | Low |
| `pre-review` | ✅ Good — clear trigger + purpose | Low |

**Skill conflict risk:** Low. The `skill-conflict-scanner.sh` checks Jaccard similarity on descriptions and the README reports no conflicts at threshold 0.30.

**Token overhead:** ~360 tokens for 9 skill descriptions in system prompt. Acceptable.

---

## Prompt Analysis

### Prompt Inventory (12 total)

| Prompt | Size | Stale? | Notes |
|--------|------|--------|-------|
| `adr.md` | 357 B | ✅ Fresh | Architecture Decision Records |
| `analyze.md` | 530 B | ✅ Fresh | Codebase deep analysis |
| `debug.md` | 783 B | ✅ Fresh | Hypothesis-driven debugging |
| `explain.md` | 292 B | ✅ Fresh | Code explanation |
| `feature.md` | 500 B | ✅ Fresh | Feature kickoff |
| `learn.md` | 381 B | ✅ Fresh | Save learning |
| `pr.md` | 735 B | ✅ Fresh | PR description |
| `refactor.md` | 447 B | ✅ Fresh | Refactoring planner |
| `research.md` | 395 B | ✅ Fresh | Research spike |
| `review.md` | 451 B | ✅ Fresh | Code review |
| `summarize.md` | 200 B | ✅ Fresh | Summarization |
| `test.md` | 479 B | ✅ Fresh | Test generation |

**Assessment:** All 12 prompts are small, fresh, and relevant. Prompts are not loaded into the system prompt — they're only invoked on demand via `/prompt-name`. No issues.

---

## Deploy System Analysis

### `deploy.sh`
**Strengths:**
- Dry-run mode (`--dry-run` flag)
- Backup before overwrite (`backup_if_needed` function)
- Uses symlinks (not copies) — source of truth stays in repo
- `set -euo pipefail` for safety
- Clear, structured output

**Issues:**
1. **Duplicate AGENTS.md / rules/00-global.md** (as noted above). The `ensure_root_dirs` creates `rules/`, the loop links all `*.md` files including `00-global.md`, AND the final block links AGENTS.md → rules/00-global.md. This means the same content is loaded twice.
2. **Settings merge is "skip if exists"** — if `settings.json` already exists, the profile is completely ignored. This means profile changes never propagate to the actual settings. A proper merge would be better.
3. **No validation after deploy** — the script doesn't verify symlinks are correct or run `check-consistency.sh` automatically.
4. **No `quietStartup` or `compaction` in profile** — these settings are never deployed.

### `deploy-pi-setup.sh`
**Status:** ✅ Properly deprecated, delegates to `deploy.sh`.

### `check-consistency.sh`
**Status:** ✅ Good — checks for work-scope leaks, dangling skill references, and deploy inversion. Runs via CI.

---

## Optimization Recommendations

### Quick Wins (< 5 min)

1. **[P0] Fix duplicate AGENTS.md loading**
   - Edit `deploy.sh` to skip linking `00-global.md` into `rules/` (it's already loaded as AGENTS.md)
   - Or: remove `rules/00-global.md` symlink after deploy
   - **Saves ~665 tokens per session**
   - **File:** `pi-setup/deploy.sh`

2. **[P0] Add `quietStartup: true`**
   - **File:** `settings.json` and `pi-setup/settings-profile.json`
   - **Saves ~200-300 tokens per session startup**

3. **[P1] Fix `theme` value**
   - Change `"light/dark"` → `"light"` or `"dark"`
   - **File:** `settings.json` and `pi-setup/settings-profile.json`

4. **[P1] Add `compaction` config**
   - Add explicit compaction block for observational-memory compatibility
   - **File:** `settings.json` and `pi-setup/settings-profile.json`

### Moderate Effort (15-30 min)

5. **[P1] Trim `enabledModels` from 37 → 8-10**
   - Keep only the 2-3 most-used models per provider
   - **Saves ~100 tokens per session** (model selector rendering)
   - **File:** `settings.json`

6. **[P1] Trim `models.json` from 106 → 20**
   - Keep only models actually used
   - **Saves ~20KB of config file loading**
   - **File:** `~/.pi/agent/models.json` (or update `deploy.sh` to auto-trim)

7. **[P2] Remove unused packages**
   - Remove `@skdev-ai/pi-gemini-cli-provider` and `@raquezha/antigravity` if not used
   - **Saves ~400 tokens per session**
   - **File:** `settings.json`

### Architectural Changes (1h+)

8. **[P2] Implement proper settings merge in deploy.sh**
   - Instead of "skip if exists", merge `settings-profile.json` keys into existing `settings.json`
   - Use `jq` or Python for deep merge
   - **File:** `pi-setup/deploy.sh`

9. **[P2] Add post-deploy validation**
   - Run `check-consistency.sh` automatically after deploy
   - Verify token budget is within expected range
   - **File:** `pi-setup/deploy.sh`

10. **[P2] Filter package resources**
    - Instead of loading all resources from each package, filter to only needed extensions/skills
    - Example: `pi-subagents` could filter to only load extensions (no skills)
    - **Saves ~200-300 tokens per session**
    - **File:** `settings.json`

---

## Priority Queue

- **[P0]** Fix duplicate AGENTS.md/rules/00-global.md loading — saves ~665 tokens/session
- **[P0]** Add `quietStartup: true` — saves ~200-300 tokens/session
- **[P1]** Fix `theme: "light/dark"` — broken config
- **[P1]** Add `compaction` config — prevents overlapping compaction strategies
- **[P1]** Trim `enabledModels` from 37 → 8-10 — reduces model selector bloat
- **[P1]** Trim `models.json` from 106 → 20 — reduces config file size
- **[P2]** Remove unused npm packages (gemini-cli-provider, antigravity)
- **[P2]** Implement proper settings merge in deploy.sh
- **[P2]** Add post-deploy validation
- **[P2]** Filter package resources to reduce tool count

---

## Summary

The Pi agent configuration is **well-structured and maintainable** but has several token waste issues:

**Biggest wins:** Fixing the duplicate AGENTS.md loading (P0) and adding `quietStartup` (P0) would save ~900-1,000 tokens per session — roughly **20% of the baseline system prompt overhead**.

**Configuration health:** The `compaction` and `quietStartup` settings are missing entirely, and the `theme` value is likely invalid. These are quick fixes.

**Package footprint:** Two of seven npm packages (`@skdev-ai/pi-gemini-cli-provider`, `@raquezha/antigravity`) are likely unused. Removing them saves ~400 tokens per session.

**Model bloat:** 37 enabled models and 106 model definitions in the provider config is excessive. Trimming to 10-15 would reduce UI clutter and config file size.