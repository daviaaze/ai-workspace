# Shade Shell — Gnim v1.9.1 vs v2.0.0 Differences

> **Date**: 2026-05-31
> **Shade uses**: Gnim v1.9.1 (`gnim`, `gnim/gobject`, `gnim-schemas`)
> **Latest**: Gnim v2.0.0-alpha.11 (`gnim`, `gnim/gobject`, `gnim/dbus`, `gnim/i18n`, `gnim/schema`, `@gnim-js/gtk4`, `@gnim-js/gtk3`, `@gnim-js/gnome-shell`)

---

## TL;DR

Gnim v2 is a **ground-up rewrite** with a Rust-based reactive core (`@gnim-js/linux-x64` native binary). It standardizes on an `Accessor<T>` interface, replaces `createBinding`/`createComputed` with `bind`/`computed`, switches to stage 3 TC39 decorators, and adds an extensible renderer system. It is **still alpha** (`2.0.0-alpha.11`) and requires **GJS ≥ 1.83.0**. Shade should **not migrate now** but should track the alpha releases for future migration planning.

---

## 1. Import Paths & Package Structure

### v1.9.1 (Current)
```
gnim                  → createBinding, createComputed, createState, createRoot,
                         For, With, Fragment, JSX, Accessor, onMount, onCleanup
gnim/gobject          → GObject (default export), register, getter, setter, signal
gnim-schemas          → createSettings, Schema, defineSchemaList
```

### v2.0.0-alpha
```
gnim                  → createState, computed, bind, effect, createRoot, createContext,
                         createAccessor, createStore, connectSignal, prop, untrack,
                         onCleanup, isAccessor, getScope,
                         For, With, Fragment, Portal, JSX, Accessor, CCProps
gnim/gobject          → register, property, signal, gtype, Object (named export)
                         ParamSpec, ParamFlags, SignalFlags, AccumulatorType
gnim/dbus             → Service, iface, methodAsync, signal, property (DBus decorators)
gnim/i18n             → createDomain, fmt, gettext, ngettext
gnim/schema           → Schema, Enum, Flags, defineSchemaList, createSettings
gnim/fetch            → fetch polyfill for GJS
@gnim-js/gtk4         → render, style, keyframes, getSlot, ClassList, ClassValue
```

**Key change**: `gnim-schemas` is now built-in as `gnim/schema`. `gnim/dbus`, `gnim/i18n`, `gnim/fetch` are all new. GTK4-specific rendering is in a separate `@gnim-js/gtk4` package.

---

## 2. Reactive API: v1 → v2 Migration Map

| v1.9.1 | v2.0.0 | Notes |
|--------|--------|-------|
| `createBinding(obj, "prop")` | `bind(obj, "prop")` | Renamed. v2 supports chaining: `bind(obj, "a", "b", "c")` |
| `createComputed(fn)` | `computed(fn)` | Renamed. v2 adds `equals` option for custom equality |
| `createState(init)` | `createState(init)` | Same signature. v2 adds `StateOptions.equals` |
| `onMount(cb)` | `onMount(cb)` (internal) / `effect(fn)` | `effect` runs after scope returns; `onMount` is still available but for internal use |
| `onCleanup(cb)` | `onCleanup(cb)` | Same |
| `createRoot(fn)` | `createRoot(fn)` | Same, but v2 has explicit `Scope` hierarchy |
| `Accessor<T>` | `Accessor<T>` | v2 adds `.peek()`, `.as()`, `.subscribe()` methods |
| (none) | `createAccessor(get, subscribe)` | v2: raw accessor factory |
| (none) | `createContext(default)` | v2: new context API |
| (none) | `createStore(obj)` | v2: reactive store with nested accessor properties |
| (none) | `effect(fn)` | v2: side-effect that auto-tracks + re-runs |
| (none) | `connectSignal(obj, sig, handler)` | v2: type-safe signal connection with auto-cleanup |
| (none) | `prop(maybeAccessor, fallback?)` | v2: normalizes `T | Accessor<T>` to `Accessor<T>` |
| (none) | `isAccessor(value)` | v2: type guard |
| (none) | `untrack(fn)` | v2: read without tracking dependencies |
| (none) | `getScope()` | v2: access current reactive scope |
| `For` | `For` | Same, but v2 has key-based memoization |
| `With` | `With` | Same, but v2 uses `Accessor<T>` directly |
| `Fragment` | `Fragment` | Same |
| (none) | `Portal` | v2: render children to different mount point |

---

## 3. GObject Decorators: Major API Change

### v1.9.1 — Experimental Decorators (What Shade Uses)

```typescript
import GObject, { register, getter, setter, signal } from "gnim/gobject"

@register({ GTypeName: "MyClass" })
class MyClass extends GObject.Object {
  @getter(Boolean)
  get enabled() { return this.#enabled }

  @setter(Boolean)
  set enabled(v: boolean) { /* ... */ this.notify("enabled") }

  @signal([GObject.TYPE_STRING], GObject.TYPE_NONE)
  failed(_reason: string) {}
}
```

### v2.0.0-alpha — Stage 3 TC39 Decorators

```typescript
import { register, property, signal } from "gnim/gobject"
import GObject from "gi://GObject?version=2.0"

@register
class MyClass extends GObject.Object {
  @property(String) enabled: string = ""

  @signal(String)
  failed(reason: string): void {
    console.log(reason)
  }
}
```

**Key differences:**
- `@getter`/`@setter` → merged into single `@property(type)` decorator
- Property values stored behind the scenes (no `#private` needed)
- `this.notify("prop-name")` still required under the hood but auto-generated
- Uses stage 3 decorator proposal (`{declare: true}` style), not TypeScript experimental
- `Object` is a named export now, not default
- `ParamSpec`, `ParamFlags` etc. are re-exported from `gnim/gobject`
- `signal()` decorator is type-safe: the decorator signature IS the signal signature
- Backward-incompatible: v1 decorators won't compile with v2

---

## 4. Component Patterns: JSX Changes

### v1.9.1

```tsx
// Widget functions receive settings directly
const MyWidget = () => {
  const network = AstalNetwork.get_default()
  const wifi = createBinding(network, "wifi")
  const ssid = createComputed(() => wifi()?.ssid ?? "Disconnected")

  return (
    <Gtk.Box css="padding: 8px;">
      <Gtk.Label label={ssid} />
    </Gtk.Box>
  )
}
```

### v2.0.0-alpha

```tsx
// Cleaner, type-safe bindings, CSS as prop
import { render } from "@gnim-js/gtk4"

const MyWidget = () => {
  const network = AstalNetwork.get_default()
  const wifi = bind(network, "wifi")
  const ssid = computed(() => wifi()?.ssid ?? "Disconnected")

  return (
    <Gtk.Box css="padding: 8px;">
      <Gtk.Label label={ssid} />
    </Gtk.Box>
  )
}

// Render with explicit root
render(() => <MyWidget />, app.activeWindow)
```

### New v2 JSX Features

| Feature | Description |
|---------|-------------|
| `css` prop | Inline CSS on any `Gtk.Widget` — `css="padding: 8px; background: @theme_bg_color;"` |
| `class` prop | Dynamic class list — `class={["card", active() && "active"]}` |
| `slot` prop | Named slots for CenterBox, Paned, Overlay — `slot="start"` |
| `Portal` | Render children into a different mount point — `<Portal mount={app}><Gtk.Window/></Portal>` |
| `style()` / `keyframes()` | CSS-in-JS for GTK — from `@gnim-js/gtk4` |
| `For` keyed memoization | Automatic diff-based updates when list items change |

---

## 5. Architecture Differences

### v1.9.1: GJS-native reactive engine
- Reactive system is pure TypeScript running in GJS
- `createBinding` tracks GObject `notify` signals
- `createComputed` auto-detects accessed accessors
- No native dependencies beyond GJS

### v2.0.0-alpha: Hybrid TypeScript + Rust core
- Optional native binary: `@gnim-js/linux-x64` (Rust, via napi-rs?)
- Core reactive engine potentially offloaded to native code
- `Scope`-based ownership model (SolidJS-inspired)
- Pluggable `Renderer` abstraction (gtk4, gtk3, gnome-shell)
- `createRenderer()` returns `{ render }` — explicit render function
- Much stronger TypeScript types (conditional types, template literals)

---

## 6. What Shade Files Would Need Migration

Based on current imports, **every file that imports from `gnim`** would need changes:

### Files importing `createBinding` (most impacted)
~50+ occurrences across ~30 files. Every `createBinding(obj, "prop")` becomes `bind(obj, "prop")`.

### Files importing `createComputed`
~15+ occurrences. Every `createComputed(fn)` becomes `computed(fn)`.

### Files importing from `gnim/gobject`
~10 files. `@getter`/`@setter` → `@property`. `GObject` default import → `Object` named import.

### Files importing from `gnim-schemas`
~2 files (`gschema.ts`, `settings.ts`). `gnim-schemas` → `gnim/schema`.

### Files passing Accessors in JSX props
All `.tsx` files. v2 Accessors must be unwrapped via `value()` in JSX or use `prop()` helper.

### Rough migration estimate
| Category | Files affected | Effort per file |
|----------|---------------|-----------------|
| `createBinding` → `bind` rename | ~30 | Low (search/replace) |
| `createComputed` → `computed` rename | ~15 | Low |
| `@getter`/`@setter` → `@property` | ~10 | Medium (rewrite property definitions) |
| `gnim-schemas` → `gnim/schema` | ~2 | Medium |
| JSX prop patterns | ~40 | Medium (Accessor unwrapping) |
| Build system changes | `meson.build` | Low (new packages) |
| Type changes | All `.tsx` | Medium (stricter types) |

**Total estimated effort**: 3-5 days for a full migration of Shade's ~104 files.

---

## 7. Should Shade Migrate?

### Arguments For Migrating

| Pro | Weight |
|-----|--------|
| Type-safe `bind()` with chaining catches errors at compile time | 🟢 Strong |
| `@property` decorator is simpler than `@getter`/`@setter` pair | 🟢 Medium |
| `effect()` + `onCleanup()` is cleaner than ad-hoc subscription management | 🟢 Strong |
| `connectSignal()` with auto-cleanup prevents signal leaks | 🟢 Strong |
| Native Rust core may improve reactive performance | 🟡 Unproven |
| `createStore()` simplifies multi-field state | 🟢 Medium |
| `css`/`class` JSX props reduce boilerplate CSS files | 🟢 Medium |
| `Portal` could simplify multi-window widget mounting | 🟢 Medium |
| Inline `gnim/schema` eliminates `gnim-schemas` dependency | 🟢 Medium |
| GSconnect GNOME 49 compatibility already suggests GJS API changes coming | 🟡 Awareness |

### Arguments Against Migrating (Now)

| Con | Weight |
|-----|--------|
| **v2 is alpha** (`2.0.0-alpha.11`) — APIs may still change | 🔴 Critical |
| Requires **GJS ≥ 1.83.0** — may not be available on all distros | 🟡 Medium |
| Native Rust binary (`@gnim-js/linux-x64`) — introduces build complexity | 🟡 Medium |
| Stage 3 decorators may not be supported in all TypeScript/tsc versions | 🟡 Medium |
| Migration touches **every file** — 3-5 days of work | 🔴 High |
| No migration guide from v1 → v2 (v1 is being deprecated in favor of v2) | 🔴 High |
| AGS v3 migration guide exists but it's for AGS users, not direct Gnim users | 🟡 Medium |
| Shade is stable on v1.9.1 — no pressing bugs from the reactive layer | 🟢 Low urgency |

---

## 8. Recommended Migration Strategy

### Phase 1: Monitor (Now — v2 stable release)
- Watch the [Aylur/gnim](https://github.com/Aylur/gnim/tree/v2) repo for a stable `v2.0.0` release
- Subscribe to [Aylur/ags releases](https://github.com/Aylur/ags/releases) — Gnim v2 releases are announced there
- Test v2 in a branch with a single widget to gauge effort
- Wait for community migration guides and examples

### Phase 2: Prepare (After v2 stable)
- Pin GJS version to ≥ 1.83.0 in Nix flake
- Generate fresh `@girs` types for v2's stricter type requirements
- Create a migration branch
- Migrate `gnim-schemas` → `gnim/schema` first (isolated, low risk)
- Migrate one service class (`@getter`/`@setter` → `@property`) as a test

### Phase 3: Full Migration
1. **Rename-only changes** first: `createBinding` → `bind`, `createComputed` → `computed`
2. **Decorator rewrite**: `@getter`/`@setter` pairs → `@property` single decorator
3. **Reactive cleanup**: Replace manual subscription patterns with `effect()` + `onCleanup()`
4. **JSX enhancement**: Adopt `css` prop, `class` prop, `Portal` where beneficial
5. **Signal connections**: Replace manual `connect()`/`disconnect()` with `connectSignal()`
6. **Testing**: Full manual test pass on NixOS VM

### Phase 4: Optional Enhancements
- Adopt `createStore()` for multi-field reactive state
- Use `gnim/dbus` for any custom D-Bus services
- Use `gnim/i18n` for translatable strings
- Explore `@gnim-js/gtk4` `style()`/`keyframes()` for CSS-in-JS

---

## 9. Ecosystem Context

### Gnim v2 is part of the bigger Aylur ecosystem restructuring

```
2024 (AGS v1)          →  2024-2025 (Astal split)  →  2025-2026 (Gnim v2)
─────────────────          ──────────────────────      ───────────────────
AGS monolith (JS)          Astal (Vala/C libraries)    Gnim v2 (Rust core)
- Everything in JS         - Network, Bluetooth, etc   - Native reactive engine
- No TS support            - Cherry-pickable           - Stage 3 decorators
                           - CLI tools for each        - Pluggable renderers
                           - Gnim v1 (JSX + reactivity) - Separate gtk4/gtk3 pkgs
```

Shade currently uses:
- **Astal** (the Vala/C backend libraries) — ✅ latest
- **Gnim v1.9.1** (the JSX + reactivity engine) — ⚠️ one major version behind

This is **intentional and correct** — v1.9.1 is stable and v2 is alpha. Aylur's own **Marble Shell** likely uses v2 alpha, but that's because Aylur is the author and needs to dogfood.

### Key version compatibility

| Component | Shade | Latest Stable | Latest Alpha |
|-----------|-------|---------------|--------------|
| Gnim | 1.9.1 | 1.9.1 (npm) | 2.0.0-alpha.11 |
| gnim-schemas | 0.3.0 | 0.3.0 | (merged into gnim/schema) |
| AGS CLI | not used | 3.1.2 | — |

---

## 10. API Cheat Sheet: v1 → v2 Quick Reference

```typescript
// === REACTIVE PRIMITIVES ===

// v1
import { createBinding, createComputed, createState } from "gnim"
const val = createBinding(obj, "prop")
const derived = createComputed(() => val() * 2)
const [state, setState] = createState(0)

// v2
import { bind, computed, createState } from "gnim"
const val = bind(obj, "prop")                    // renamed + chaining
const derived = computed(() => val() * 2)         // renamed
const [state, setState] = createState(0)          // same


// === ACCESSOR METHODS ===

// v1
val()                    // read (tracks)
// no peek method
// no as method
// no subscribe method

// v2
val()                    // read (tracks)
val.peek()              // read (no tracking) — NEW
val.as(x => x * 2)      // map/transform — NEW
val.subscribe(cb)       // explicit subscribe — NEW


// === GOBJECT DECORATORS ===

// v1
import GObject, { register, getter, setter } from "gnim/gobject"
@register({ GTypeName: "Foo" })
class Foo extends GObject.Object {
  @getter(Boolean) get enabled() { ... }
  @setter(Boolean) set enabled(v) { ...; this.notify("enabled") }
}

// v2
import { register, property, Object } from "gnim/gobject"
@register
class Foo extends Object {
  @property(Boolean) enabled: boolean = false     // single decorator!
  // this.notify("enabled") handled automatically
}


// === EFFECTS & CLEANUP ===

// v1
onMount(() => {
  const id = obj.connect("signal", handler)
  onCleanup(() => obj.disconnect(id))
})

// v2
connectSignal(obj, "signal", handler)             // auto-cleanup — NEW
effect(() => {                                     // replaces onMount for reactivity
  console.log("value changed:", val())
})


// === JSX ===

// v1
<Gtk.Box>
  <Gtk.Label css="padding: 8px;" label={derived} />
</Gtk.Box>

// v2
<Gtk.Box>
  <Gtk.Label css="padding: 8px;" label={derived} />     // same
</Gtk.Box>
// OR (new features):
<Gtk.Box css="padding: 8px">                            // css as prop
  <Gtk.Label class={["my-class", active() && "active"]} /> // dynamic classes
</Gtk.Box>
```

---

## Bottom Line

**Do not migrate now.** Gnim v2 is alpha and contains breaking changes across virtually every import. The current v1.9.1 stack is stable, well-tested, and fully functional for Shade. However, **start tracking v2 releases** — when v2.0.0 ships as stable, the migration will be worth the effort for the improved type safety, cleaner API, and native performance.

The estimated migration is 3-5 days touching 30+ files. Plan for it as a dedicated effort when v2 stabilizes.
