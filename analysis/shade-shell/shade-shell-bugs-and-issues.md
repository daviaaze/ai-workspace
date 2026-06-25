# Shade Shell — Bugs, Risks & Issues

> **Date**: 2026-05-31 | **Version**: 0.2.1 | **Risk Score**: 0.55
> **Scope**: Full codebase review + recent `Hypridle` changes

---

## 🔴 High Severity

### 1. `Hypridle.dispose()` Circular Singleton Reference

**File**: `src/lib/hypridle.ts` ~line 202-208  
**Severity**: 🔴 High  
**Impact**: Potential use-after-dispose or stale singleton state

```typescript
// In dispose():
Hypridle.get_default() // ← returns this.instance which IS this (the object being disposed!)
```

`dispose()` is called during GObject cleanup. When it calls `get_default()`, it returns `this.instance` — which is the object currently being disposed. If `dispose()` is called via GJS GC at an unexpected time, this creates a circular reference back to a partially-destroyed object. Any subsequent property access on the returned singleton would operate on a disposed GObject.

**Fix**: Remove the `get_default()` call from `dispose()`, or null out `static instance` before calling dispatch.

---

### 2. No File I/O Error Handling in Hypridle Config Generation

**File**: `src/lib/hypridle.ts`  
**Severity**: 🔴 High  
**Impact**: Silent config corruption or crash on disk-full / permission error

```typescript
// #generateConfig() writes to ~/.config/hypr/hypridle.conf
AstalIO.write_file(CONFIG_PATH, config)
// Also: hyprctl dispatch commands via AstalIO.Process.exec_async
```

There are no `try/catch` blocks around file writes or hyprctl dispatches. If:
- `~/.config/hypr/` doesn't exist
- Disk is full
- Permissions are wrong
- `hyprctl` is not on PATH

...the error is silently swallowed or causes an unhandled GJS exception that may crash the widget.

**Fix**: Wrap both file I/O and process execution in try/catch with logging.

---

### 3. No Validation of Config Coherence

**File**: `src/lib/hypridle.ts`  
**Severity**: 🔴 High (logical)  
**Impact**: Can generate invalid `hypridle.conf` with contradictory settings

The individual setter validations are independent:
- `idleTimeout`: clamped to `[60, 1800]`
- `dimTimeout`: clamped to `[30, idleTimeout - 10]`
- `dpmsTimeout`: clamped to `[idleTimeout + 10, 3600]`

But there's no cross-validation when settings change simultaneously. If a user rapidly changes settings (e.g., via GSettings keys), the generated config could have:
- `dimTimeout > idleTimeout` (if dim was set first, then idle was lowered)
- `dpmsTimeout < dimTimeout` (if dpms was lowered below the current dim + idle gap)

**Fix**: Add a `#validate()` method called after all setters that ensures `dimTimeout < idleTimeout < dpmsTimeout`.

---

## 🟡 Medium Severity

### 4. Settings Subscription Leaks on Re-init

**File**: `src/lib/hypridle.ts` ~line 84-131  
**Severity**: 🟡 Medium  
**Impact**: Memory leak and duplicate callbacks after settings reload

```typescript
init(settings: ...) {
  // Stores 8+ subscription unsub functions in this.#unsubs
  // BUT: does not check if already initialized
  this.#settings = settings
  const unsubs: Array<() => void> = []
  unsubs.push(settings.autoLockEnabled.subscribe(...))
  unsubs.push(settings.idleTimeout.subscribe(...))
  // ... 6 more subscriptions
  this.#unsubs = unsubs  // ← replaces any previous array without unsubscribing
}
```

If `init()` is called twice (e.g., settings schema reload, or widgets re-mount after a crash recovery), the old subscription callbacks are never unsubscribed. They'll fire alongside the new ones, causing duplicate config writes and potential race conditions.

**Fix**: Call `dispose()` at the start of `init()` to clean up previous subscriptions.

---

### 5. `Notifd.get_default()` Has No Timeout Guard

**File**: Referenced in widget mount patterns  
**Severity**: 🟡 Medium  
**Impact**: Indefinite block if D-Bus handshake hangs

The project correctly defers `Notifd.get_default()` via `GLib.idle_add` per Invariant #2. However, there's no timeout guard — if the D-Bus handshake never completes (e.g., notification daemon is hung), the idle callback simply never fires. The notifications widget silently never initializes.

**Fix**: Add a `GLib.timeout_add` alongside the idle handler to detect stalls and log a warning.

---

### 6. Watcher/Dispatcher Pattern Has No Error Boundary

**File**: `src/lib/hypridle.ts` — the `#apply()` method  
**Severity**: 🟡 Medium  
**Impact**: Crash in watcher kills idle management

`#apply()` is a `GLib.idle_add` debounced function that writes config and dispatches to hyprctl. If either step throws, there's no recovery — the debounce ID is lost and subsequent `#apply()` calls won't work.

**Fix**: Wrap the `#apply()` body in try/catch and re-schedule on failure.

---

### 7. `dispose()` Methods in lib/ Are Unverified

**File**: Multiple files (`hypridle.ts`, `keyboard.ts`, `nightLight.ts`, `appMixer.ts`)  
**Severity**: 🟡 Medium  
**Impact**: Potential resource leaks

Six service classes have `dispose()` methods, but they're **graph-unreferenced** — no code paths call them. In GJS/GObject, `dispose()` is called by the GC during finalization, but if any reference is held (e.g., in a `createBinding`), the object is never collected and resources leak (D-Bus connections, file watchers, timers).

---

### 8. Touchpad Init Called Unconditionally

**File**: `src/widget/index.tsx`  
**Severity**: 🟡 Medium  
**Impact**: Error on desktop systems without touchpad hardware

`Touchpad.get_default().init()` is called during widget mount regardless of whether a touchpad is present. The initialization may fail silently on desktops, but could also cause unexpected D-Bus errors.

---

## 🟢 Low Severity / Code Smells

### 9. Single-Letter Variable Names Proliferate

**Scope**: All `.tsx` widget files  
**Severity**: 🟢 Low (maintenance)  
**Impact**: Dramatically reduced code readability

Representative examples:
```
src/widget/quicksettings/expander/media.tsx: id, entry, c, path, s, p, m
src/widget/bar/systemUsage.tsx: v, t
src/widget/bar/workspaces.tsx: v, ws, client, c
src/widget/quicksettings/network/index.tsx: c, icon, ssid
```

These are mostly `createBinding`/`createComputed` result variables in Gnim reactive code. While the convention keeps JSX concise, it makes the code nearly illegible without deep context.

---

### 10. Global Mutable State in monitors.ts

**File**: `src/lib/monitors.ts`  
**Severity**: 🟢 Low  
**Impact**: Threading/side-effect risk

```typescript
let m: any  // Top-level mutable export, any-typed
```

A top-level `let m` with type `any` is a potential source of hard-to-debug side effects.

---

### 11. Unused `gjsUtils.ts::listLength`

**File**: `src/lib/gjsUtils.ts` line 16  
**Severity**: 🟢 Low  
**Impact**: Dead code bloat

The `listLength` helper is never called. The only consumer of `gjsUtils.ts` is `toArray`, which is heavily used. `listLength` can be safely removed.

---

### 12. Unused `logger.ts::formatTime`

**File**: `src/lib/logger.ts` line 3  
**Severity**: 🟢 Low  

`formatTime` is defined but has no callers in the graph. It may be vestigial.

---

## ⚪ Informational / Observations

### 13. Hypridle Settings Schema Added But Not Documented

The new GSettings keys (`auto-lock-enabled`, `idle-timeout`, `screen-dim-enabled`, `screen-dim-timeout`, `dpms-enabled`, `dpms-timeout`, `suspend-enabled`, `suspend-timeout`) were added to `gschema.ts` with no corresponding documentation or comments explaining valid ranges or interactions.

### 14. The `ShellState` Singleton Appears Unused

`src/lib/shellState.ts` is a `GObject.Object` singleton with `launcherOpen`, `launcherQuery`, `qsOpen`, and `screenlocked` properties. The graph reports zero callers. The `src/widget/index.tsx` file likely creates bindings from it, but the graph can't trace Gnim reactive references. Verify before removing.

---

## Summary

| Severity | Count | Must-Fix Before Merge |
|----------|-------|----------------------|
| 🔴 High | 3 | All 3 |
| 🟡 Medium | 5 | #4 (subscription leak), #6 (error boundary) |
| 🟢 Low | 4 | Optional cleanup |
| ⚪ Info | 2 | Awareness only |

**Immediate action**: Fix Hypridle dispose circular reference (#1), add I/O error handling (#2), and add cross-setter validation (#3) before merging the Hypridle branch.
