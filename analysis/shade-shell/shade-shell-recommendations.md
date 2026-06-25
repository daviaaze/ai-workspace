# Shade Shell — Recommendations & Action Items

> **Date**: 2026-05-31 | **Version**: 0.2.1
> **Context**: Full codebase review following Hypridle feature addition

---

## Priority Tiers

| Tier | Label | Timeframe | Gates |
|------|-------|-----------|-------|
| **P0** | Blockers | Before merge to main | Must fix or main is broken |
| **P1** | Immediate | This sprint | Prevents regressions |
| **P2** | Short-term | Next 2-4 weeks | Improves stability |
| **P3** | Medium-term | This quarter | Raises quality bar |
| **P4** | Strategic | Next 2 quarters | Architectural improvements |

---

## P0 — Blockers (Fix Before Merging Hypridle Branch)

### P0.1 Fix `Hypridle.dispose()` circular reference

**File**: `src/lib/hypridle.ts` lines 202-208  
**Effort**: Small (1 line change)  
**Risk if skipped**: Use-after-dispose on GObject, potential crash

```typescript
// Replace:
Hypridle.get_default()

// With one of:
// Option A: Null the singleton first
Hypridle.instance = null

// Option B: Remove the call entirely if it's vestigial
// (dispatch already ran, nothing to re-init)
```

### P0.2 Add I/O error handling to Hypridle config writes

**File**: `src/lib/hypridle.ts`  
**Effort**: Small (try/catch around write_file + hyprctl dispatch)  
**Risk if skipped**: Silent config corruption, unhandled exceptions

```typescript
private #apply() {
  try {
    const config = this.#generateConfig()
    AstalIO.write_file(CONFIG_PATH, config)
    // dispatch hyprctl...
  } catch (e) {
    logger.error("hypridle", "Failed to apply config:", e)
  }
}
```

### P0.3 Cross-validate Hypridle settings coherence

**File**: `src/lib/hypridle.ts`  
**Effort**: Small (add `#validate()` method)  
**Risk if skipped**: Invalid `hypridle.conf` with logical contradictions

```typescript
private #validate() {
  // Enforce: dimTimeout < idleTimeout < dpmsTimeout
  if (this.#dimEnabled && this.#dimTimeout >= this.#idleTimeout) {
    this.#dimTimeout = Math.max(30, this.#idleTimeout - 10)
  }
  if (this.#dpmsEnabled && this.#dpmsTimeout <= this.#idleTimeout) {
    this.#dpmsTimeout = this.#idleTimeout + 10
  }
}
```

---

## P1 — Immediate (This Sprint)

### P1.1 Guard Hypridle.init() against double-init

**File**: `src/lib/hypridle.ts` lines 84-131  
**Effort**: Small (call `#cleanup()` or `dispose()` at top of `init`)

**Why**: If `init()` is called twice (settings reload, widget remount after crash), old subscriptions leak and duplicate callbacks fire.

### P1.2 Add error boundary to Hypridle `#apply()` debounce

**File**: `src/lib/hypridle.ts`  
**Effort**: Small (wrap body in try/catch, re-arm debounce on failure)

**Why**: If `#apply()` throws, the debounce ID is lost and subsequent triggers won't execute the watcher.

### P1.3 Add timeout guard for Notifd initialization

**File**: `src/widget/notifications/` or wherever `Notifd.get_default()` is invoked  
**Effort**: Small (GLib.timeout_add alongside idle_add, log warning on stall)

**Why**: If notification D-Bus handshake hangs indefinitely, the widget silently never initializes.

---

## P2 — Short-Term (2-4 Weeks)

### P2.1 Add smoke tests for Hypridle

**Effort**: Medium  
**Approach**: Write GJS unit tests that:
- Verify config generation produces valid hypridle.conf syntax
- Verify setter clamping logic
- Verify `dispose()` cleans up subscriptions

### P2.2 Add smoke tests for requestHandler

**Effort**: Small  
**Approach**: Test D-Bus command routing with mocked Gio.ApplicationCommandLine

### P2.3 Run type-checking in CI

**Effort**: Medium  
**Approach**:
1. Generate GIR types (`pnpm run types`)
2. Add `tsc --noEmit` to a `check` script
3. Add to `flake.nix` devShell's `shellHook`

### P2.4 Add a `justfile` or Makefile for common tasks

**Effort**: Small  
**Tasks to include**:
```makefile
lint:     pnpm run lint
types:    pnpm run types && tsc --noEmit
build:    meson setup build --wipe && meson compile -C build
dev:      nix run . --
test-vm:  nix run .#nixosConfigurations.vm...
```

---

## P3 — Medium-Term (This Quarter)

### P3.1 Refactor single-letter variable names in .tsx files

**Effort**: Large (touches virtually every widget)  
**Approach**: Incremental, file by file. Priority order:
1. `src/widget/quicksettings/expander/media.tsx` (most opaque)
2. `src/widget/bar/workspaces.tsx`
3. `src/widget/quicksettings/network/index.tsx`
4. Other files as encountered

**Naming convention to adopt**:
```
p → player      (mpris player binding)
c → client      (hyprland client binding)
v → volume      (volume binding)
m → monitor     (monitor reference)
w → weather     (weather data)
s → speaker     (audio device)
d → device      (generic device)
t → temperature or timezone
```

### P3.2 Clean up dead code

**Effort**: Medium  
**Candidates for removal** (after verification):
| File | Symbol | Notes |
|------|--------|-------|
| `src/lib/shellState.ts` | `ShellState` | Verify not used via Gnim bindings |
| `src/lib/gjsUtils.ts::listLength` | `listLength` | Confirmed unused |
| `scripts/` | All Python files | Move to a `test/` directory outside source tree |
| `src/lib/monitors.ts::m` | Top-level `let m` | If unused, remove; if used, rename |

### P3.3 Write Playwright E2E tests for critical flows

**Effort**: Large  
**Critical flows to test**:
1. App launcher: open, type search, select app, launch
2. Quick settings: open, toggle WiFi, close
3. Lock screen: lock, unlock via text
4. Notifications: receive, dismiss, DND toggle

**Infrastructure**: Use the existing NixOS VM as test target.

### P3.4 Extract common/ into a shared design system

**Effort**: Medium  
**Rationale**: `IconButton`, `IconMenuButton`, `IconInfoRow`, `Slider`, `QuickToggleButton` are reused across all widgets. Extracting them into a documented design system reduces duplication and ensures visual consistency.

---

## P4 — Strategic (Next 2 Quarters)

### P4.1 Establish minimum test coverage policy

**Rule**: Every new service class requires at least a smoke test validating:
- `get_default()` singleton pattern
- Core initialization success
- `dispose()` resource cleanup

### P4.2 Document the D-Bus API

**Effort**: Medium  
**File**: Create `docs/dbus-api.md`  
**Content**: Document every command in `requestHandler.ts`, its parameters, and expected behavior.

### P4.3 Design a widget plugin system

**Effort**: Large  
**Rationale**: The `WindowManager` already has a registry pattern for bars, wallpapers, lockscreens, dock. A formal plugin API would allow community widgets without modifying core code.

### P4.4 Add CI/CD pipeline

**Effort**: Large  
**Components**:
- Nix build validation on every PR
- TypeScript type-checking
- E2E tests on NixOS VM (self-hosted runner)
- Linting

---

## Summary Action Plan

```
Week 1-2 (P0+P1):
  ├── Fix Hypridle.dispose() circular reference
  ├── Add I/O error handling
  ├── Cross-validation of settings
  ├── Guard against double-init
  └── Error boundary for #apply()

Week 3-4 (P2):
  ├── Add smoke tests for Hypridle + requestHandler
  ├── Add justfile for common tasks
  └── Set up tsc --noEmit in dev workflow

Month 2-3 (P3):
  ├── Begin variable renaming (prioritize opaque files)
  ├── Dead code cleanup
  └── Playwright E2E scaffolding

Quarter 3-4 (P4):
  ├── Document D-Bus API
  ├── Design plugin system RFC
  └── Set up CI/CD
```
