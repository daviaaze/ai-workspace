# Shade Shell — Dead Code Inventory

> **Date**: 2026-05-31 | **Total reported**: 261 symbols  
> **Important**: Many "dead" symbols are Gnim reactive closures (`createBinding`, `createComputed`) that the call graph cannot trace. **Always verify with a code search before removing.**

---

## Methodology

The graph performs static call-graph analysis. It can trace:
- Direct function calls (`foo()`)
- Imports (`import { x } from "./y"`)
- Method calls on known types

It **cannot** trace:
- Gnim `createBinding()` / `createComputed()` closures (these appear as unnamed callbacks)
- GObject property bindings created at runtime
- `GLib.idle_add()` / `GLib.timeout_add()` callbacks
- D-Bus signal callbacks registered dynamically

**Therefore**: The 261 count is inflated. The categories below separate **confirmed dead code** from **likely false positives**.

---

## 🔴 Confirmed Dead Code (Safe to Remove)

### Orphan Test Scripts (not used at runtime)

| File | Symbols | Notes |
|------|---------|-------|
| `scripts/vnc-mcp-server.py` | `screenshot`, `send_key`, `type_text`, `mouse_click`, `mouse_move`, `save_screenshot` | MCP server for VNC control — not imported by any TypeScript code |
| `scripts/agent-full-test.py` | `vncdo`, `screenshot`, `wait`, `wait_for_vnc`, `run_full_test`, `main` | Full test suite — standalone script |
| `scripts/agent-smoke-test.py` | `vncdo`, `screenshot`, `wait`, `wait_for_vnc`, `run_smoke_test`, `main` | Smoke test suite — standalone script |
| `scripts/run-vm-test.sh` | `cleanup` | Shell cleanup function in test harness |

**Recommendation**: Move all of `scripts/` to a `test/integration/` directory or remove from the repo if not actively used.

### Unused Utility Functions

| File | Symbol | Line | Notes |
|------|--------|------|-------|
| `src/lib/gjsUtils.ts` | `listLength` | 16 | `toArray` is used heavily; `listLength` has zero callers |
| `src/lib/logger.ts` | `formatTime` | 3 | Internal helper with no references in the graph |

**Recommendation**: Remove both — they add no value and confuse the utility surface.

### Unused Class (Likely)

| File | Symbol | Line | Notes |
|------|--------|------|-------|
| `src/lib/shellState.ts` | `ShellState` | 6 | Entire class and all its methods (`launcherOpen`, `launcherQuery`, `qsOpen`, `screenlocked`) have zero graph callers. However, `src/widget/index.tsx` may reference it through Gnim bindings that the graph can't trace. |

**Recommendation**: Search for `shellState` in all `.tsx` files before removing. If no imports found, safe to delete.

---

## 🟡 Likely Dead Code (Gnim Bindings — Verify First)

These classes have `get_default()` → `init()` calls in `src/widget/index.tsx::widgets()`, but the graph can't trace through that pattern. They appear dead but are likely **live**:

| Class | File | `init()` Called In | Verdict |
|-------|------|-------------------|---------|
| `Brightness` | `brightness.ts` | Not called in `widgets()` — may be used directly in QS sliders | ⚠️ Verify |
| `Inhibit` | `inhibit.ts` | `widgets()` line: `Inhibit.get_default().init(app)` | ✅ Likely live |
| `KeyboardLayout` | `keyboard.ts` | Not called in `widgets()` — may be used in bar indicator directly | ⚠️ Verify |
| `Theming` | `theming.ts` | `widgets()` line: `Theming.get_default().init(s.general)` | ✅ Likely live |
| `WindowManager` | `windowManager.ts` | Used directly in `widgets()`, `App.tsx` | ✅ Confirmed live |
| `Hypridle` | `hypridle.ts` | `widgets()` line: `Hypridle.get_default().init(s.general)` | ✅ Confirmed live |
| `NightLight` | `nightLight.ts` | `widgets()` line: `NightLight.get_default().init(...)` | ✅ Likely live |
| `ColorScheme` | `colorScheme.ts` | `widgets()` line: `ColorScheme.get_default().init(...)` | ✅ Likely live |
| `AppMixer` | `appMixer.ts` | Used directly in QS `appMixer.tsx` | ✅ Likely live |
| `Screenshot` | `screenshot.ts` | Used in QS button grid | ✅ Likely live |
| `Touchpad` | `touchpad.ts` | `widgets()` line: `Touchpad.get_default().init()` | ✅ Likely live |
| `audioAutoSwitch` | `audioAutoSwitch.ts` | `widgets()` line: `initAutoSwitch()` | ✅ Likely live |

### Methods on Live Classes That May Be Dead

Even on "live" classes, individual methods may be unused:

| Class | Potentially Dead Methods | Notes |
|-------|------------------------|-------|
| `Brightness` | `kbd`, `screen` | May be used in QS sliders via bindings |
| `Clipboard` | `item`, `copyClipboardItem`, `deleteClipboardItem`, `clearClipboardHistory`, `formatClipboardPreview` | These are likely used in clipboard UI (not yet built?) |
| `FingerprintAuth` | `available`, `verifying` | Used in lockscreen UI |
| `Geolocation` | `latitude`, `longitude`, `available`, `locationChanged`, `found` | Used in weather service via bindings |
| `KeyboardLayout` | `parseLayoutName`, `layout`, `available`, `layoutChanged`, `k`, `cycle`, `dispose` | Used in bar indicator |
| `MonitorService` | `Gdk2HyprMonitor`, `m`, `monitors` | Used throughout widgets |
| `NotificationHistory` | `add`, `h`, `setLimit`, `setIgnoredApps`, `a`, `history` | Used in notification list UI |
| `Weather` | `info`, `location` | Used in QS expander and bar |
| `WindowManager` | `bars`, `wallpapers`, `lockscreens`, `quicksettings`, `osd`, `applauncher`, `notifications`, `settings`, `dock`, `b`, `w`, `l` | Used in App.tsx and widget index |

---

## 🟢 Gnim Reactive Closures (False Positives)

The vast majority of dead code reports (probably ~200/261) come from `.tsx` widget files. These are:

- `createBinding(obj, "prop")` — creates a reactive getter function
- `createComputed(() => ...)` — creates a computed value function
- `onMount(() => ...)` — mount lifecycle callback
- Component function definitions that Gnim renders via JSX

All of these are **live** — they're invoked by the Gnim reactive runtime, not by direct function calls. The graph can't trace them.

### Most Affected Files

| File | Reported Dead | Actual Status |
|------|--------------|---------------|
| `src/widget/quicksettings/` | ~95 | All Gnim closures — live |
| `src/widget/bar/` | ~32 | All Gnim closures — live |
| `src/widget/dock/` | ~9 | All Gnim closures — live |
| `src/widget/notifications/` | ~10 | All Gnim closures — live |
| `src/widget/osd/` | ~7 | All Gnim closures — live |
| `src/widget/applauncher/` | ~6 | All Gnim closures — live |
| `src/widget/lockscreen/` | ~8 | All Gnim closures — live |
| `src/widget/windowswitcher/` | ~18 | All Gnim closures — live |
| `src/widget/settings/` | ~14 | All Gnim closures — live |
| `src/widget/wallpaper/` | ~2 | All Gnim closures — live |
| `src/widget/common/` | ~19 | All Gnim closures — live |

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Confirmed dead (scripts) | 20 symbols | Move to `test/` or remove |
| Confirmed dead (utilities) | 2 symbols | Remove immediately |
| Likely dead (shellState) | ~5 symbols | Verify, then remove |
| False positives (Gnim closures) | ~200 symbols | Ignore — graph limitation |
| Unresolved (methods on live classes) | ~34 symbols | Verify individually |

**Net dead code to clean**: ~27 symbols across 3 areas (scripts, utilities, shellState).

---

## Recommended Cleanup PR

```bash
# One PR removing confirmed dead code:
git rm scripts/vnc-mcp-server.py
git rm scripts/agent-full-test.py
git rm scripts/agent-smoke-test.py
git rm scripts/run-vm-test.sh
# Or move to:
# git mv scripts/ test/integration/

# Then in src/:
# Remove listLength from gjsUtils.ts
# Remove formatTime from logger.ts (or verify internal use)
# Verify shellState.ts, then remove if truly unused
```
