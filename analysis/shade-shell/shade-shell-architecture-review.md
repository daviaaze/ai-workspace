# Shade Shell — Architecture & Features Review

> **Date**: 2026-05-31 | **Version**: 0.2.1 | **Risk Score**: 0.55
> **Repo**: `/home/daviaaze/Projects/pessoal/dshell` | **License**: GPL-3.0-only

---

## 1. What Is Shade Shell?

Shade Shell is a **personal desktop shell for Hyprland** — it replaces the default GNOME Shell UI when running on the Hyprland compositor. Written in **TypeScript** and rendered with **GTK 4 / Libadwaita** via the **Gnim** reactive framework and **Astal** libraries, it runs as a **GJS application** (GNOME JavaScript / SpiderMonkey) under a **systemd user service**.

It exposes remote control commands over **D-Bus** (using `gdbus` for ~7ms invocations) and is fully packaged for **NixOS** via a Nix Flake.

### Key Metrics
| Metric | Value |
|--------|-------|
| Files | 104 |
| Total nodes | 561 |
| Total edges | 2,890 |
| Classes | 17 |
| Functions | 438 |
| Tests | 2 |
| Communities | 15 |
| Dead code symbols | 261 |

---

## 2. Architecture

### High-Level Layer Diagram

```
┌──────────────────────────────────────────────────┐
│                 main.ts (entry)                   │
│  GJS → App.runAsync → vfunc_command_line         │
│  Sets up Gettext locale, starts logger           │
├──────────────────────────────────────────────────┤
│          App.tsx (ShadeShell: Adw.Application)    │
│  - CSS provider init (GTK StyleContext)           │
│  - SettingsProvider (Gn reactive context)         │
│  - widgets() mount orchestration                  │
│  - vfunc_command_line for D-Bus commands          │
├──────────────────────────────────────────────────┤
│  widget/index.tsx (Central Orchestrator)          │
│  - Initializes 8+ services (Weather, ColorScheme, │
│    Inhibit, NightLight, Hypridle, Touchpad,       │
│    Theming, AudioAutoSwitch)                      │
│  - Sequential error-isolated widget mounting      │
│  - Exports shared reactive state (launcherOpen,   │
│    qsOpen, screenlocked)                          │
├──────────────────┬───────────────────────────────┤
│  10 UI Widgets   │   lib/ (Services & Singletons) │
│  bar             │  apps, audio, brightness,      │
│  dock            │  clipboard, fingerprint,       │
│  osd             │  geolocation, hypridle,        │
│  applauncher     │  inhibit, keyboard, logger,    │
│  quicksettings   │  monitors, nightLight,         │
│  lockscreen      │  notificationHistory,          │
│  windowswitcher  │  settings, shellState,         │
│  notifications   │  theming, time, weather,       │
│  settings        │  windowManager, appMixer,      │
│  wallpaper       │  colorScheme, audioAutoSwitch, │
│                  │  screenshot, touchpad,          │
│                  │  requestHandler, gschema,       │
│                  │  keybinds, gjsUtils             │
├──────────────────┴───────────────────────────────┤
│          common/ (Shared UI Components)           │
│  IconButton, IconMenuButton, IconInfoRow,         │
│  LinkedPopoverBox, PowerMenu, QuickToggleButton,  │
│  Slider, Notification, AudioControl, PopoverCleanup│
└──────────────────────────────────────────────────┘
```

### Dependency Flow

```
widgets (tsx UI files)
    │
    ├── imports from common/ (reusable UI atoms)
    │
    └── imports from lib/ (services, singletons, utils)
            │
            ├── Uses Astal libraries (network, bluetooth, etc.)
            ├── Uses Gnim reactive primitives (createBinding, etc.)
            └── Uses GObject/Gio/GLib bindings
```

### 15 Detected Communities

The codebase self-organizes into 15 communities (Leiden clustering on the dependency graph):

| # | Community | Size | Cohesion | Language | Description |
|---|-----------|------|----------|----------|-------------|
| 1 | `src/lib` | 186 | 0.31 | TypeScript | Core services & singletons |
| 2 | `src/widget/quicksettings` | 95 | 0.07 | TSX | Largest widget — toggles, sliders, lists |
| 3 | `src/widget/bar` | 32 | 0.01 | TSX | Top panel with indicators |
| 4 | `scripts/` | 20 | 0.51 | Python | VNC test harness (isolated) |
| 5 | `src/widget/common` | 19 | 0.06 | TSX | Shared reusable components |
| 6 | `src/widget/windowswitcher` | 18 | 0.12 | TSX | Alt-Tab style switcher |
| 7 | `src/widget/settings` | 14 | 0.00 | TSX | Preferences UI |
| 8 | `src/widget/notifications` | 10 | 0.07 | TSX | Toast notifications |
| 9 | `src/widget/dock` | 9 | 0.00 | TSX | Taskbar/dock |
| 10 | `src/widget/lockscreen` | 8 | 0.04 | TSX | Lock screen |
| 11 | `src/widget/osd` | 7 | 0.00 | TSX | On-screen display |
| 12 | `src/widget/applauncher` | 6 | 0.02 | TSX | App search launcher |
| 13 | `src` | 4 | 0.20 | TSX | Root App.tsx |
| 14 | `src/widget` | 3 | 0.17 | TSX | Mount orchestrator |
| 15 | `src/widget/wallpaper` | 2 | 0.00 | TSX | Wallpaper widget |

**Key Observations:**
- `src/lib` is the **hub** — 25 cross-community edges connect widgets back to it
- `scripts/` has the highest internal cohesion (0.51) — tightly focused Python test harness
- Several widgets have **zero cohesion** (settings, dock, osd, wallpaper) — members don't call each other
- The architecture is a **hub-and-spoke**: all widgets connect to `lib/`, not to each other

### Cross-Community Coupling

25 edges cross community boundaries. The dominant pattern:
- **Widget → lib**: Widgets import services like `apps`, `audio`, `settings`, `time`, `gjsUtils`
- **Widget → common**: quicksettings sub-widgets use `IconButton`, `IconInfoRow`, `PowerMenu`
- **No widget-to-widget coupling** — good modular isolation

---

## 3. Feature Inventory

### Shell Widgets (10)

| Widget | Path | Key Components |
|--------|------|----------------|
| **Bar** | `src/widget/bar/` | Clock, workspaces, window title, weather button, system indicators (audio, battery, bluetooth, keyboard, network, power), system usage (CPU/RAM) |
| **Dock** | `src/widget/dock/` | Per-workspace clients with close/pin, icon from .desktop file |
| **OSD** | `src/widget/osd/` | Slider popup for brightness/volume overlay, popup notifications |
| **App Launcher** | `src/widget/applauncher/` | Fuzzy search across .desktop entries, exact match, exec launch |
| **Quick Settings** | `src/widget/quicksettings/` | **Largest widget** — button grid (bluetooth, caffeinated, idle controls, night light, power profiles, screenshot, color scheme), expander (battery, calendar, media, weather, world clock), network (AP list, password dialog, wifi popover), audio sliders, app mixer, notification list, system tray (lock, power, rotate, settings buttons), Cava visualizer |
| **Lockscreen** | `src/widget/lockscreen/` | Text + fingerprint unlock, time display |
| **Window Switcher** | `src/widget/windowswitcher/` | MRU-based Alt-Tab with icon/keyboard navigation |
| **Notifications** | `src/widget/notifications/` | Toast popups with auto-dismiss, images, action buttons |
| **Settings** | `src/widget/settings/` | Multi-page: bar config, clock/TZ, weather, network, general |
| **Wallpaper** | `src/widget/wallpaper/` | Day/night wallpaper switching with theming integration |

### System Services (20+)

| Service | File | Function |
|---------|------|----------|
| **App Launcher** | `apps.ts` | .desktop file scanning, fuzzy/exact query, icon lookup |
| **Audio** | `audio.ts` | Volume icon mapping |
| **App Mixer** | `appMixer.ts` | Per-application volume streams, capture streams |
| **Audio Auto-Switch** | `audioAutoSwitch.ts` | Auto-switch audio output on device change |
| **Brightness** | `brightness.ts` | Screen/keyboard brightness via Astal |
| **Clipboard** | `clipboard.ts` | cliphist integration — list, search, copy, delete, clear |
| **Color Scheme** | `colorScheme.ts` | Light/dark mode with daytime tracking |
| **Fingerprint** | `fingerprint.ts` | fprintd integration — verify, status tracking |
| **Geolocation** | `geolocation.ts` | GeoClue2 IP-based location detection |
| **Hypridle** | `hypridle.ts` | **New** — idle management (auto-lock, dim, DPMS, suspend) |
| **Inhibit** | `inhibit.ts` | Idle inhibition (caffeine) via D-Bus |
| **Keyboard** | `keyboard.ts` | Layout detection and cycling |
| **Logger** | `logger.ts` | Structured logging with levels, performance timing |
| **Monitors** | `monitors.ts` | GDK↔Hyprland monitor mapping service |
| **Night Light** | `nightLight.ts` | Blue light filter with auto-schedule |
| **Notification History** | `notificationHistory.ts` | Persistent notification storage, DND, app filtering |
| **Screenshot** | `screenshot.ts` | grim+slurp (screenshot), wf-recorder (video) |
| **Settings** | `settings.ts` | Reactive GSettings context (Gn `SettingsProvider`) |
| **Shell State** | `shellState.ts` | Shared global state (launcherOpen, qsOpen, screenlocked) |
| **Theming** | `theming.ts` | Matugen JSON-based dynamic color theming |
| **Time** | `time.ts` | Timezone offset formatting, city name lookup |
| **Touchpad** | `touchpad.ts` | Touchpad device management |
| **Weather** | `weather.ts` | Open-Meteo API via gweather, geolocation integration |
| **Window Manager** | `windowManager.ts` | Multi-monitor window registry (bar, wallpaper, lockscreen per monitor) |

### Infrastructure

| Component | Details |
|-----------|---------|
| **D-Bus** | Remote commands via `gdbus` (lightweight ~7ms) and `requestHandler.ts` |
| **systemd** | User service (`shade-shell.service`) auto-starts on login |
| **GSettings** | Full schema in `gschema.ts` — all settings persisted via dconf |
| **Nix Flake** | Package derivation, NixOS module, dev shell, VM test config |
| **Keybindings** | `keybinds.ts` — hyprctl dispatch for keyboard shortcuts |
| **CSS** | Global `shade.css` + inline widget CSS; heavy use of Libadwaita classes |

---

## 4. Tech Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Language** | TypeScript | GJS runtime (SpiderMonkey), ES modules |
| **UI Toolkit** | GTK 4 + Libadwaita | Layer Shell windows (gtk4-layer-shell) |
| **Reactive** | Gnim v1.9.1 | JSX for GTK4, `createBinding`, `createComputed` |
| **Schema** | gnim-schemas v0.3 | GSettings schema generation from TS |
| **Build** | Meson + esbuild | No type-checking at build time |
| **Pkg Manager** | pnpm | Node deps only (build-time) |
| **Environment** | Nix Flake | Reproducible builds, NixOS module |
| **IPC** | D-Bus | `gdbus` for remote commands |
| **Astal Libraries** | apps, auth, battery, bluetooth, hyprland, mpris, network, notifd, powerprofiles, tray, wireplumber, cava, astal4, io | All system integrations |

---

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Singleton pattern** (`static get_default()`) for all services | Single source of truth, GObject lifecycle integration |
| **Sequential widget mount with error isolation** | One crashing widget shouldn't kill the shell |
| **gdbus for remote commands** | ~7ms vs ~1s for spawning full GJS binary |
| **No network list in Settings** | UX owned by Quick Settings panel |
| **Defer Notifd via idle_add** | Avoids 25s D-Bus main loop block |
| **No automated tests (by choice)** | Manual testing via NixOS VM only |
| **No semicolons** | Enforced by Prettier |
| **`any` allowed** | `no-explicit-any` ESLint rule disabled |

---

## 6. Code Quality Patterns

### ✅ Strengths
- **Consistent GObject discipline** — Proper `@getter`/`@setter`/`@signal` with kebab-case `notify()`
- **Reactive patterns** — All widgets use `createBinding`/`createComputed` for reactivity
- **Performance instrumentation** — Built-in `perf.start()/stop()` throughout mount and operations
- **Reproducible builds** — Nix Flake with fully pinned inputs
- **Error resilience** — `safe()` wrapper prevents cascading widget failures
- **Cross-cutting concerns isolated** — Settings, logging, window management in dedicated singletons

### ⚠️ Concerns
- **Single-letter variable names** (e.g., `c`, `v`, `p`, `m`, `t`) pervasive in `.tsx` reactive code
- **261 dead code symbols** — inflated by untraced reactive closures, but real dead code exists
- **0 TypeScript tests** — only 2 Python-based VNC smoke tests
- **No CI/CD** — no automated validation of any kind
- **No type-checking** in the build pipeline — esbuild bundles without verification
- **`GLib.List` iteration** requires explicit `toArray()` conversion throughout

---

## 7. Test Coverage

| Metric | Value |
|--------|-------|
| Total nodes in graph | 561 |
| Test nodes | 2 |
| **TypeScript tests** | **0** |
| Python smoke tests | 2 (`scripts/agent-*.py`) |
| Manual testing | NixOS VM (`nix run .#nixosConfigurations.vm...`) |

This is a **recognized project decision** — "No automated tests" is documented in the Decision Log. All verification is manual.

---

## 8. Key Files Reference

| File | Purpose | Notes |
|------|---------|-------|
| `src/main.ts` | Entry point | GJS bootstrap, Gettext, app.runAsync |
| `src/App.tsx` | Root App | `ShadeShell` class, CSS init, settings provider |
| `src/widget/index.tsx` | Mount orchestrator | Service init + widget mount with error isolation |
| `src/lib/hypridle.ts` | **New** | Idle management (209 lines) |
| `src/lib/settings.ts` | Reactive settings | `SettingsProvider`, `useSettings` Gn context |
| `src/lib/windowManager.ts` | Window registry | Per-monitor window tracking |
| `src/lib/requestHandler.ts` | CLI dispatcher | D-Bus command routing |
| `src/lib/gschema.ts` | GSettings schema | All user-configurable settings |
| `meson.build` | Build system | esbuild bundling with GIR exclusions |
| `flake.nix` | Nix flake | Package, module, dev shell, VM |
| `package.json` | pnpm config | Scripts, deps, Prettier config |
