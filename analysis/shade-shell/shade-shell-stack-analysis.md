# Shade Shell — Stack & Architecture Decision Review

> **Date**: 2026-05-31 | **Scope**: Are we using the right tools?
> **Methodology**: Research across official docs, community comparisons, production examples, and performance analysis.

---

## Executive Summary

**Verdict: Shade Shell's stack choices are solid and well-aligned with the 2025–2026 desktop shell ecosystem.** Each tool was chosen for a specific reason and the combination is coherent. Minor improvements are identified below, but no fundamental changes are warranted.

---

## 1. Stack Decision Matrix

| Layer | Shade Choice | Verdict | Notes |
|-------|-------------|---------|-------|
| **Runtime** | GJS (SpiderMonkey) | ✅ **Correct** | The only production JS runtime for GNOME. 150+ contributors, tracks Firefox ESR, used by GNOME Shell itself |
| **Language** | TypeScript | ✅ **Correct** | GJS doesn't natively run TS, but `esbuild` transpiles at build time. Type safety is essential for a 561-node codebase |
| **UI Toolkit** | GTK 4 + Libadwaita | ✅ **Correct** | GTK 3 is legacy. GTK 4 + Layer Shell is the modern stack for Wayland shells |
| **Reactive UI** | Gnim v1.9.1 (JSX) | ✅ **Correct** | Purpose-built for GTK4 + GJS by Aylur (same author as Astal). Official renderer for AGS v2+ |
| **System Backends** | Astal libraries | ✅ **Correct** | Vala/C libraries with GObject introspection. Native performance, language-agnostic. The successor to AGS v1's integrated services |
| **IPC** | D-Bus (gdbus) | ✅ **Correct** | Fastest IPC on Linux desktop. gdbus bypasses GJS startup for ~7ms invocations |
| **Build System** | Meson + esbuild | ✅ **Recommended** | Standard per Gnim docs and GNOME packaging guides |
| **Packaging** | Nix Flake | ✅ **Correct** | Used by Aylur/marble-shell, AGS docs recommend it. Fully reproducible |
| **Widget System** | gtk4-layer-shell | ✅ **Correct** | The de facto standard for anchoring windows to screen edges on Wayland |

---

## 2. Why Gnim + Astal (Not AGS CLI)

This is the most important architectural question. Shade uses **Gnim + Astal directly**, not the `ags` scaffolding CLI. This is actually the **right choice for a custom shell**:

### The Layer Cake

```
┌─────────────────────────────────────────┐
│        AGS CLI (scaffolding tool)        │  ← "npm create ags"
│  Generates project, provides CLI,        │
│  wrappers, conventions                   │
├─────────────────────────────────────────┤
│           Gnim (JSX + reactivity)        │  ← Shade uses this directly
│  createRoot, createBinding, JSX, etc.    │
├─────────────────────────────────────────┤
│       Astal libraries (backends)         │  ← Shade uses this directly
│  network, bluetooth, battery, mpris, etc │
├─────────────────────────────────────────┤
│        GTK 4 + gtk4-layer-shell          │
│        GJS (SpiderMonkey)                │
└─────────────────────────────────────────┘
```

**AGS CLI adds**: Project scaffolding, TypeScript type generation (`ags types`), built-in JSX intrinsics for Gtk widgets, migration tooling. It's useful for rapid prototyping but adds a layer of abstraction.

**Shade's approach**: Imports Gnim and Astal directly. This means:
- **More control** — direct access to GObject, GLib, Gtk APIs without AGS wrappers
- **No lock-in** — AGS CLI could change its API; Gnim and Astal are more stable
- **Slightly more boilerplate** — Shade must set up its own project structure, types, build config
- **Matches the recommended production path** — Gnim docs show direct usage for applications

### Production Examples Using the Same Stack

| Project | Stack | Stars | Notes |
|---------|-------|-------|-------|
| **Marble Shell** (Aylur) | AGS CLI + Gnim + Astal | 35 | Aylur's personal shell — the author's own daily driver |
| **ags2-shell** (TheWolfStreet) | AGS v3/Astal + Gnim | 12 | Hyprland shell, NixOS-ready |
| **Shade Shell** (caioasmuniz) | Gnim + Astal directly | — | Your project |

The pattern is validated: **Gnim + Astal is the standard stack for custom GTK4 desktop shells in 2025**.

---

## 3. Language & Runtime Choices

### GJS (✅ Good Choice)

**What it is**: GNOME's official JavaScript runtime. Embeds Firefox's SpiderMonkey engine with GObject introspection bindings. Tracks Firefox ESR releases (GNOME 49 will upgrade to ESR 140).

**Advantages for Shade**:
- **Shared ecosystem** — same runtime as GNOME Shell, so any GObject library works
- **Performance** — SpiderMonkey JIT is production-grade; GNOME Shell uses it everywhere
- **No Node dependency** — GJS is self-contained; no npm at runtime
- **Active development** — 150+ contributors, regular releases

**Critical difference from GNOME Shell extensions**: Shade runs as a **standalone GJS application** (via systemd user service), NOT as a GNOME Shell extension. This is a key architectural advantage:

```
GNOME Shell Extension:          Shade Shell:
┌─────────────────────┐        ┌─────────────────┐
│   GNOME Shell (C)   │        │   Hyprland (C++) │
│  ┌───────────────┐  │        │                  │
│  │ Extension (JS) │  │        │  ┌────────────┐ │
│  │ SHARES THREAD  │  │        │  │ Shade (GJS) │ │
│  │ with compositor│  │        │  │ OWN PROCESS │ │
│  └───────────────┘  │        │  └────────────┘ │
└─────────────────────┘        └─────────────────┘
        ⚠️                            ✅
  Main loop shared              Own main loop
  with cursor/rendering         No compositor impact
```

This means the single-threaded GJS concerns that plague GNOME Shell extensions (clipboard lag, animation jank) **do not apply to Shade**.

### TypeScript via esbuild (✅ Good Choice)

**How it works**: TypeScript is transpiled to JS at build time via esbuild. GJS runs plain JS. Types come from `@girs/*` packages generated by ts-for-gir.

**Advantages**:
- esbuild is fast (Go, parallel)
- TypeScript catches GObject type errors at dev time
- The build pipeline is Meson → esbuild → single JS bundle

**Minor concern**: No `tsc --noEmit` in the build pipeline means type errors slip through to runtime. This is a recognized limitation (noted in the AGENTS.md: "TypeScript errors generally do not block the build").

**Recommendation**: Add `tsc --noEmit` as a separate `check` script (as recommended in the Recommendations doc). The `@girs/*` types need to be generated first (`pnpm run types`), then type-checking can run.

### No Semicolons (Style Choice)

Enforced by Prettier. Purely cosmetic — no functional impact. Consistent across the codebase.

---

## 4. Reactive Framework: Gnim

### What Gnim Provides

| Feature | How Shade Uses It |
|---------|-------------------|
| **JSX** | All `.tsx` widget files use JSX to construct GTK widget trees |
| **`createBinding`** | Reactive property binding from Astal/GObject sources |
| **`createComputed`** | Derived reactive values |
| **`onMount`** | Widget lifecycle hooks |
| **`@register`** / `@getter` / `@setter` / `@signal` | GObject subclass decorators |
| **`createRoot`** | Root render context |

### Not React — And That's Good

Gnim is explicitly **not a port of React**. Key differences:
- No virtual DOM — JSX compiles to direct GObject constructor calls
- No diffing/reconciliation — Gnim updates GObject properties directly via bindings
- No hooks — uses `createBinding`/`createComputed` instead (SolidJS-inspired model)
- Much lighter runtime than React would be

This means **lower overhead** than a React-based approach would have. The "SolidJS-inspired" model means reactive computations only re-run when their dependencies change, not on every render.

### Gnim Version

Shade uses **Gnim v1.9.1** (latest as of writing). Gnim is actively maintained — last npm publish was 4 months ago. It receives updates alongside Astal and AGS.

---

## 5. System Backends: Astal Libraries

### Architecture Decision

Astal was born from splitting AGS v1's monolithic services into standalone Vala/C libraries:

```
AGS v1 (deprecated):              Astal + Gnim (current):
┌─────────────────────┐          ┌──────────────────────────┐
│  AGS monolith (JS)  │          │  AstalNetwork (Vala/C)    │
│  - network          │    →     │  AstalBluetooth (Vala/C)  │
│  - bluetooth        │          │  AstalBattery (Vala/C)    │
│  - battery          │          │  AstalMpris (Vala/C)      │
│  - mpris            │          │  ... (each independent)   │
│  - audio            │          │  + CLI tools for each     │
│  - ... everything   │          │  + Gnim for frontend      │
└─────────────────────┘          └──────────────────────────┘
```

**This rearchitecture happened in November 2024** (AGS v2.0.0 release). Shade targets the new architecture directly — it imports Astal libraries individually via `gi://` imports.

### Why Vala/C for Backends

- **Performance**: Vala compiles to C, runs natively — no JS overhead for polling, D-Bus parsing
- **Language-agnostic**: GObject introspection means any language (JS, Python, Lua, Vala) can use them
- **Cherry-pickable**: Shade only pulls in the Astal libraries it needs (network, bluetooth, battery, mpris, notifd, wireplumber, hyprland, tray, powerprofiles, cava, auth, apps, io, astal4)
- **CLI companions**: Each Astal library has a CLI tool, enabling scripting and integration with other tools

---

## 6. Comparison With Alternatives

### Desktop Shell / Widget Frameworks

| Framework | Language | UI | Backend | Maturity | Shade Fit? |
|-----------|----------|----|---------|----------|------------|
| **AGS v3** | TypeScript | GTK4 + Gnim | Astal (Vala/C) | ⭐⭐⭐⭐⭐ | ✅ Closest cousin. Shade uses the same underlying libraries directly |
| **EWW** | Rust/Yuck | GTK3 | Custom | ⭐⭐⭐⭐ | ❌ Widgets recreated on every update (slow). Yuck config language is limited |
| **Ignis** | Python | GTK4 | Custom | ⭐⭐ | ❌ Python, less mature ecosystem, 658 stars vs AGS's 3K |
| **Fabric** | Python | GTK3 | Custom | ⭐⭐ | ❌ GTK3 (legacy), not moving to GTK4 |
| **Waybar** | C++/JSON | GTK3 | Custom | ⭐⭐⭐⭐ | ❌ Bar only — not a full shell. JSON config is limiting |
| **Quickshell** | Go | Qt6 | Custom | ⭐ | ❌ Qt, not GTK. Very new |

### Shade vs AGS v3 Directly

| Aspect | Shade | AGS v3 CLI |
|--------|-------|------------|
| **Boilerplate** | More (own project setup) | Less (`ags init` generates) |
| **Type generation** | Manual (`pnpm run types` with ts-for-gir) | `ags types` command |
| **GTK intrinsics** | Must import Gtk widgets explicitly | Built-in JSX intrinsics for Gtk widgets |
| **Control** | Full access to GObject/Gtk APIs | AGS abstractions may hide details |
| **Migration risk** | Lower (Gnim + Astal are stable) | Higher (AGS CLI API may change) |
| **Best for** | Custom shells with specific needs | Rapid prototyping, standard shells |

**Conclusion**: Shade made the right call for a **custom, full-featured shell**. If starting from scratch today, either path would work. Shade's direct approach is more flexible and has less lock-in risk.

---

## 7. Build & Packaging

### Meson + esbuild (✅ Standard)

The Gnim documentation explicitly recommends this pattern:
- Meson handles: installation paths, GSettings schema compilation, desktop entry generation, systemd service installation
- esbuild handles: TypeScript → JS bundling, CSS inlining, external GIR module handling
- No type-checking at build time (standard for esbuild)

### Nix Flake (✅ Production-Grade)

The Flake provides:
- Fully reproducible build environment
- Package derivation with proper wrappers (`GI_TYPELIB_PATH`, `LD_PRELOAD` for `gtk4-layer-shell`)
- NixOS module for systemd service management
- VM test configuration for manual testing
- Dev shell with all dependencies

Aylur/marble-shell uses the same Nix Flake pattern. The AGS documentation recommends it.

---

## 8. Performance Considerations

### Single-Threaded GJS — Mitigated

Key findings from GJS performance research:

1. **Forced GC batching (GJS 1.54+)**: GC runs are now deferred by 10 seconds, so animations that trigger GC won't suffer jank — the animation finishes before GC starts. ✅ Shade benefits from this.

2. **Property resolution caching**: GJS previously re-resolved GObject properties on every access (expensive). This was fixed — performance improvements for reading GObject properties landed in recent GNOME releases. ✅

3. **Standalone process**: Unlike GNOME Shell extensions, Shade runs in its own GJS process. Blocking operations only affect Shade, not the compositor cursor/rendering. ✅

4. **Astal backends are native**: Network polling, Bluetooth scanning, audio monitoring all happen in Vala/C code, not in the GJS thread. Only property updates cross the GObject boundary. ✅

### Potential Bottlenecks

| Area | Risk | Mitigation |
|------|------|-----------|
| Large reactive graphs | `createComputed` can cascade re-evaluations | Gnim tracks precise dependencies (SolidJS model), not full re-render |
| CSS parsing | GTK CSS provider costs at startup | Single CSS file, loaded once |
| D-Bus busy wait | `Notifd.get_default()` blocks | Already deferred via `GLib.idle_add` |
| File I/O in main loop | Synchronous `AstalIO.write_file` | Should use `AstalIO.write_file_async` for large writes |
| Hyprland IPC | Every `hyprctl` call spawns a process | Could batch queries or use Hyprland socket directly |

---

## 9. Concrete Recommendations

### Stay On Current Stack (✅)

| Tool | Keep? | Why |
|------|-------|-----|
| GJS | ✅ | No viable alternative for GTK4 + JS |
| TypeScript | ✅ | Essential for a 500+ node codebase |
| Gnim | ✅ | The standard JSX layer for GTK4/GJS |
| Astal | ✅ | Native backends, actively maintained |
| GTK4 | ✅ | GTK3 is end-of-life for new shells |
| Meson + esbuild | ✅ | Recommended build pattern |
| Nix Flake | ✅ | Reproducible, production-grade |
| gtk4-layer-shell | ✅ | Only game in town for Wayland layer shell |
| gdbus | ✅ | Fastest IPC option |

### Improve (Without Replacing)

1. **Add `tsc --noEmit` type-checking** to the dev workflow — would catch GObject type errors before runtime
2. **Consider AstalIO.write_file_async** for Hypridle config writes instead of synchronous
3. **Monitor reactive graph depth** — deeply nested `createComputed` chains could cause cascading re-evaluations. Gnim's precise dependency tracking should handle this, but it's worth profiling complex widgets (Quick Settings is 95 nodes)
4. **Consider using Hyprland's Unix socket** directly instead of spawning `hyprctl` for batch queries (e.g., workspace list, client list)
5. **Generate and commit `@girs` types** to the repo — currently they're generated on-demand via `pnpm run types` but not tracked. Committing them would make editor support work out of the box

### Do Not Switch To

- **AGS CLI**: Shade has already invested in direct Gnim + Astal usage. Switching now would be a lateral move with migration cost and no clear benefit
- **EWW/Ignis/Fabric**: Different languages, different ecosystems. No reason to migrate
- **GNOME Shell extensions**: Different architecture — extensions share the compositor thread, Shade has its own process

---

## 10. Ecosystem Health Check

| Component | Status | Risk |
|-----------|--------|------|
| GJS | Active (GNOME project, 150+ contributors) | Very low |
| Gnim | Active (Aylur, npm: v1.9.1, 4 months ago) | Low |
| Astal | Active (Aylur, frequent releases) | Low |
| gtk4-layer-shell | Active (wmww, 179 stars) | Low |
| ts-for-gir | Active (gjsify org) | Low |
| esbuild | Active (Evan Wallace, extremely popular) | Very low |
| Meson | Active (GNOME/FreeDesktop standard) | Very low |

The entire stack sits on well-maintained, actively developed foundations. No component is abandoned or at risk of bitrot.

---

## 11. Key References

| Resource | URL |
|----------|-----|
| GJS Guide | https://gjs.guide/ |
| GJS GitHub | https://github.com/GNOME/gjs |
| Astal Documentation | https://aylur.github.io/astal/ |
| Gnim Documentation | https://aylur.github.io/gnim/ |
| AGS Framework | https://aylur.github.io/ags/ |
| Marble Shell (reference impl) | https://github.com/Aylur/marble-shell |
| gtk4-layer-shell | https://github.com/wmww/gtk4-layer-shell |
| ts-for-gir | https://github.com/gjsify/ts-for-gir |
| TypeScript GJS docs | https://gjsify.github.io/docs/ |
| AGS v2.0 Release (Astal split) | https://github.com/Aylur/ags/releases/tag/v2.0.0 |

---

**Bottom Line**: Shade Shell's architecture and tool choices are **well-justified, modern, and aligned with the 2025 Wayland desktop shell ecosystem**. Every layer — from GJS runtime through Gnim reactivity to Astal backends to Nix packaging — was chosen for solid reasons and there are no obviously better alternatives. The main improvement opportunities are operational (type-checking, async I/O, profiling), not architectural.
