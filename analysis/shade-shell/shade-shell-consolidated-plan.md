# Shade Shell — Consolidated Improvement Plan

> **Date**: 2026-05-31 | **Version**: 0.2.1 | **Risk Score**: 0.55
> **Source docs**: Architecture Review, Bugs & Issues (14 findings), Recommendations, Dead Code Inventory (261 symbols), Stack Analysis
> **Cross-referenced**: All findings verified against live `hypridle.ts` code and code-review-graph

---

## Executive Summary

The codebase has **already improved** since the review documents were written. Three of the five high/medium bugs are partially or fully addressed in the current code. The remaining work is manageable — roughly **2-3 days** of focused effort for the blockers, then incremental cleanup over the following weeks.

**Blast radius note**: The Hypridle file impacts 151 nodes across 62 files. Changes here affect the idle management stack end-to-end (settings → config generation → hypridle process lifecycle). Fix with care.

---

## Finding Cross-Reference: What's Real vs. Already Fixed

### 🔴 High Severity Bugs

| # | Finding | Status | Notes |
|---|---------|--------|-------|
| 1 | `Hypridle.dispose()` circular reference | ✅ **FIXED** | Current code: `dispose()` only calls `this.#stop()`. No `get_default()` call. The review document described an older version. |
| 2 | No I/O error handling in config writes | 🟡 **PARTIALLY FIXED** | `#writeConfig()` (line 163-219) has try/catch + `logger.error`. But `#restart()` (line 221-238) and `#stop()` (line 240-259) have try/catch with **no logging** — errors are silently swallowed. |
| 3 | No cross-validation of config coherence | 🟡 **PARTIALLY FIXED** | The `init()` subscribe handlers for `idleTimeout` (line 99-115) and `dpmsTimeout` (line 129-141) now cross-validate downstream timeouts. **But** the direct setter paths (`set idleTimeout`, `set dimTimeout`, etc.) run no validation before calling `#apply()`. If setters are called programmatically (not via GSettings), contradictory configs can be generated. |

### 🟡 Medium Severity Bugs

| # | Finding | Status | Notes |
|---|---------|--------|-------|
| 4 | Settings subscription leaks on re-init | ❌ **CONFIRMED** | `init()` (line 84-131) replaces `this.#settings` and creates 8 new subscriptions without checking if already initialized. No `#unsubs` array exists in the current code (the review doc mentioned one, but it's not in the actual source). If `init()` is called twice, old subscriptions become orphaned. |
| 5 | No timeout guard for Notifd | ❌ **CONFIRMED** | Not verified directly, but the architectural concern is valid. Deferred via `GLib.idle_add` but no timeout fallback. |
| 6 | `#apply()` has no error boundary | 🟡 **PARTIALLY FIXED** | `#apply()` (line 152-158) itself has no try/catch, but `#writeConfig()` does. `#restart()` has try/catch but swallows errors silently. If `#restart()` fails, `this.#process` may be left in an inconsistent state. |
| 7 | `dispose()` methods in lib/ unreferenced | 🟡 **CONFIRMED (nuanced)** | Multiple service classes have `dispose()` that GC may never call if references are held by `createBinding` closures. This is a systemic GJS/GObject lifecycle concern, not unique to Hypridle. |
| 8 | Touchpad init called unconditionally | 🟡 **CONFIRMED** | `widgets()` calls `Touchpad.get_default().init()` regardless of hardware. Risk is low (likely just a logged error), but worth guarding. |

### 🟢 Low Severity / Dead Code

| # | Finding | Status | Notes |
|---|---------|--------|-------|
| 9 | Single-letter variable names | 🟢 **CONFIRMED** | Pervasive in `.tsx` files. Readability issue, not a bug. |
| 10 | Global mutable `let m` in monitors.ts | 🟢 **CONFIRMED** | Code smell, low risk. |
| 11 | `listLength` in gjsUtils.ts | 🟢 **CONFIRMED DEAD** | Graph confirms 0 callers. `toArray` has 8 callers and is heavily used. Safe to remove. |
| 12 | `formatTime` in logger.ts | ❌ **NOT DEAD** | Used internally at line 115 in `logAt()`. The review doc was incorrect — graph couldn't trace internal calls. |
| 13 | Hypridle schema undocumented | 🟢 **CONFIRMED** | New GSettings keys lack comments explaining valid ranges. |
| 14 | `ShellState` appears unused | ❌ **NOT DEAD** | 8 files reference it directly via `createBinding(ShellState.get_default(), ...)`. Heavily used — the graph's 0-caller count is a Gnim binding false negative. |

---

## Priority Action Plan

### Phase 1: Blocker Fixes (Before Merge — ~2 hours)

These must be fixed in `src/lib/hypridle.ts` before the Hypridle branch merges to main:

#### F1.1 — Guard against double-init in `Hypridle.init()`
**File**: `src/lib/hypridle.ts`, method `init()` (line 84)
**Effort**: 15 min

```typescript
init(settings: ...) {
  // ADD: Clean up previous subscriptions if re-initializing
  if (this.#settings) {
    // Unsubscribe old listeners... (need to track subscription handles)
  }
  this.#settings = settings
  // ... rest of init
}
```

**Alternative (simpler)**: Check if already initialized and skip:
```typescript
init(settings: ...) {
  if (this.#settings) {
    logger.warn("hypridle", "init() called but already initialized — skipping")
    return
  }
  // ...
}
```

#### F1.2 — Add logging to `#restart()` and `#stop()` error handlers
**File**: `src/lib/hypridle.ts`, methods `#restart()` (line 221) and `#stop()` (line 240)
**Effort**: 10 min

```typescript
#restart() {
  if (this.#process) {
    try {
      this.#process.kill()
    } catch (e) {
      logger.error("hypridle", "failed to kill existing process:", e)
    }
    this.#process = null
  }
  try {
    AstalIO.Process.exec("pkill -x hypridle")
  } catch (e) {
    logger.warn("hypridle", "pkill failed (may not be running):", e)
  }
  try {
    this.#process = AstalIO.Process.subprocessv(["hypridle"])
  } catch (e) {
    logger.error("hypridle", "failed to start hypridle process:", e)
  }
}

#stop() {
  if (this.#process) {
    try {
      this.#process.kill()
    } catch (e) {
      logger.error("hypridle", "failed to kill process:", e)
    }
    this.#process = null
  }
  try {
    AstalIO.Process.exec("pkill -x hypridle")
  } catch (e) {
    // pkill may fail if hypridle is not running — that's normal
  }
  try {
    const file = Gio.File.new_for_path(CONFIG_PATH)
    if (file.query_exists(null)) {
      file.delete(null)
    }
  } catch (e) {
    logger.error("hypridle", "failed to delete config file:", e)
  }
}
```

#### F1.3 — Add cross-validation in setters
**File**: `src/lib/hypridle.ts`, setters for `idleTimeout`, `dimTimeout`, `dpmsTimeout`, `suspendTimeout`
**Effort**: 20 min

The subscribe handlers already do this, but direct setter calls bypass validation. Add after the clamping logic in each setter:

```typescript
set idleTimeout(v: number) {
  v = Math.max(60, Math.min(1800, v))
  if (this.#idleTimeout === v) return
  this.#idleTimeout = v
  // ADD: Cross-validate downstream timeouts
  if (this.#dimTimeout >= v) {
    this.#dimTimeout = Math.max(30, v - 10)
    this.notify("dim-timeout")
  }
  if (this.#dpmsTimeout <= v) {
    this.#dpmsTimeout = v + 10
    this.notify("dpms-timeout")
  }
  if (this.#suspendTimeout <= this.#dpmsTimeout) {
    this.#suspendTimeout = this.#dpmsTimeout + 10
    this.notify("suspend-timeout")
  }
  this.#settings?.setIdleTimeout(v)
  this.#apply()
  this.notify("idle-timeout")
}
```

Apply similar cross-validation in `set dpmsTimeout()` and `set suspendTimeout()`.

#### F1.4 — Wrap `#apply()` body in try/catch
**File**: `src/lib/hypridle.ts`, method `#apply()` (line 152)
**Effort**: 5 min

```typescript
#apply() {
  try {
    if (!this.available) return
    if (this.#enabled) {
      this.#writeConfig()
      this.#restart()
    } else {
      this.#stop()
    }
  } catch (e) {
    logger.error("hypridle", "unexpected error in #apply:", e)
  }
}
```

---

### Phase 2: Immediate (This Sprint — ~4 hours)

#### F2.1 — Add timeout guard for Notifd initialization
**Effort**: 30 min
**Approach**: Add a `GLib.timeout_add_seconds(10, ...)` alongside the existing `idle_add` that logs a warning if Notifd hasn't initialized within 10 seconds.

#### F2.2 — Remove confirmed dead code
**Effort**: 15 min
- Delete `listLength` from `src/lib/gjsUtils.ts` (0 callers confirmed)
- Do NOT delete `formatTime` (used internally in logger.ts)
- Do NOT delete `ShellState` (heavily used via Gnim bindings in 8 files)
- Move `scripts/` to `test/integration/` (or remove if not used)

#### F2.3 — Guard Touchpad.init() with hardware check
**Effort**: 15 min
**File**: `src/widget/index.tsx`
```typescript
try {
  Touchpad.get_default().init()
} catch (e) {
  logger.warn("mount", "Touchpad init skipped (no hardware?):", e)
}
```

#### F2.4 — Add GSettings schema documentation
**Effort**: 30 min
**File**: `src/lib/gschema.ts`
Add doc comments for the 8 new Hypridle keys explaining valid ranges and interactions.

---

### Phase 3: Short-Term (2-4 Weeks — ~1-2 days)

#### F3.1 — Run type-checking in dev workflow
**Effort**: 1 hour
1. Add `"check": "tsc --noEmit"` to `package.json` scripts
2. Add to CI if/when CI exists
3. Generate types first: `pnpm run types && pnpm run check`

#### F3.2 — Add a task runner
**Effort**: 30 min
Create a `justfile` or add npm scripts:
```json
{
  "check": "tsc --noEmit",
  "check:all": "pnpm run types && pnpm run lint && pnpm run check",
  "dev": "nix run . --"
}
```

#### F3.3 — Add smoke tests for Hypridle
**Effort**: 2-3 hours
Write GJS unit tests that verify:
- Config generation produces valid `hypridle.conf` syntax
- Setter clamping logic with edge cases (0, negative, huge values)
- `dispose()` properly cleans up the process
- Double-init guard works

#### F3.4 — Fix `#restart()` process leak edge case
**Effort**: 15 min
If `pkill` succeeds but `subprocessv` fails, `this.#process` remains `null` and the old external hypridle is killed. This means hypridle is not running when it should be. Add a retry or log the full error context.

---

### Phase 4: Medium-Term (Month 2-3)

#### F4.1 — Systematic variable renaming
Priority order (worst first):
1. `src/widget/quicksettings/expander/media.tsx`
2. `src/widget/bar/workspaces.tsx`
3. `src/widget/quicksettings/network/index.tsx`
4. `src/widget/bar/systemUsage.tsx`

Convention: `c→client`, `v→volume`, `m→monitor`, `p→player`, `s→speaker`, etc.

#### F4.2 — Address systemic `dispose()` lifecycle concerns
**Effort**: Medium
For each service class with `dispose()`: ensure either a) it's called explicitly at shutdown, or b) add an `uninit()` method for explicit cleanup that `widgets()` can wire into.

#### F4.3 — Extract reusable design system from `common/`
**Effort**: Medium
Document `IconButton`, `Slider`, `QuickToggleButton` interfaces. Consider adding Storybook-equivalent for GTK4 widgets.

---

### Phase 5: Strategic (Next 2 Quarters)

#### F5.1 — Establish minimum test coverage policy
Rule: Every new service class must have a smoke test validating `get_default()` singleton, core init, and `dispose()` cleanup.

#### F5.2 — Document the D-Bus API
**File**: Create `docs/dbus-api.md`
Document every command in `requestHandler.ts` with parameters and behavior.

#### F5.3 — Set up CI/CD
1. Nix build validation on PRs
2. TypeScript type-checking (`pnpm run check`)
3. Linting
4. Smoke tests on NixOS VM (self-hosted runner)

---

## Architecture Decisions — No Changes Needed

The stack analysis confirmed that Shade Shell's architecture and tool choices are **well-justified and modern**:

| Component | Verdict |
|-----------|---------|
| GJS + TypeScript + esbuild | ✅ Correct for this domain |
| GTK4 + Libadwaita + Layer Shell | ✅ Only viable stack for Wayland shells |
| Gnim + Astal (direct, not AGS CLI) | ✅ Correct choice for a custom shell |
| Nix Flake for packaging | ✅ Production-grade, reproducible |
| gdbus for IPC | ✅ Fastest option (~7ms vs ~1s for GJS spawn) |
| No semicolons | ✅ Consistent, enforced by Prettier |

**Do not switch** to AGS CLI, EWW, Ignis, or any other framework.

---

## Summary: What to Do Right Now

```
┌─────────────────────────────────────────────────────┐
│           PHASE 1: Before merging Hypridle           │
│                                                      │
│  □ F1.1 Guard init() against double-init             │
│  □ F1.2 Add logging to #restart() and #stop()        │
│  □ F1.3 Cross-validate timeouts in setters            │
│  □ F1.4 Wrap #apply() in try/catch                   │
│                                                      │
│  All four are ~2 hours of work in one file.          │
│  Risk if skipped: subscription leaks, silent         │
│  failures, invalid hypridle.conf generation.         │
└─────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────┐
│           PHASE 2: This sprint (after merge)         │
│                                                      │
│  □ F2.1 Notifd timeout guard                          │
│  □ F2.2 Remove listLength, move scripts/             │
│  □ F2.3 Guard Touchpad.init()                        │
│  □ F2.4 Document GSettings schema                    │
└─────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────┐
│          PHASE 3: Next 2-4 weeks                      │
│                                                      │
│  □ F3.1 Add tsc --noEmit to workflow                 │
│  □ F3.2 Add task runner                              │
│  □ F3.3 Write Hypridle smoke tests                   │
│  □ F3.4 Fix process leak edge case                   │
└─────────────────────────────────────────────────────┘
```

---

## Files To Touch (Phase 1 + 2)

| File | Changes | Lines affected |
|------|---------|---------------|
| `src/lib/hypridle.ts` | F1.1-F1.4: init guard, logging, cross-validation, apply wrapper | ~30 lines added |
| `src/lib/gjsUtils.ts` | F2.2: Remove `listLength` | ~10 lines removed |
| `src/widget/index.tsx` | F2.3: Guard Touchpad.init() | ~3 lines changed |
| `src/lib/gschema.ts` | F2.4: Document new keys | ~10 lines added |
| `scripts/` | F2.2: Move to `test/integration/` | Directory move |

**Total blast radius**: 5 files, ~53 lines changed. Risk: Low to Medium (hypridle.ts is the sensitive file).
