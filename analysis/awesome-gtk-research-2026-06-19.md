# Awesome GTK Research — UI Concepts, Architecture & Inspiration for Shade

> Date: 2026-06-19  
> Source: [valpackett/awesome-gtk](https://github.com/valpackett/awesome-gtk)  
> Focus: Desktop shell patterns, GTK4/libadwaita UI concepts, architectural ideas

---

## 1. Fellow Desktop Shell Projects — Direct Peers

These projects are the closest to Shade in purpose (Wayland desktop shell with GTK4). Each has distinct architectural choices worth studying.

### 1.1 Matshell — Closest Tech Stack Sibling

**Stack:** TypeScript + Astal + Gnim + AGS — **same as Shade**  
**Repo:** [Neurarian/matshell](https://github.com/Neurarian/matshell)  
**Stars:** ~66

#### Architecture
- TypeScript with JSX (Gnim), Astal for system backends
- Uses **Matugen** for dynamic Material Design theming
- Supports **Hyprland** and **River** via automatic compositor detection
- **NixOS/Home-Manager module** for declarative config
- Config hot-reload via `config.json`

#### Widgets/Components
- **Status Bar** — workspace management, system tray, CPU/mem monitoring, clock
- **Music Player** — media controls, album art theming, CAVA audio visualizer library
- **System Menu** — WiFi scanning, Bluetooth, brightness, audio, battery, power profiles, notification center with DND
- **Logout Menu** — wlogout-style but in AGS
- **Multimodal Launcher** — fuzzy search + frecency-ranking for apps, clipboard, wallpapers
- **OSD** — audio, brightness, Bluetooth connection tracking
- **GPU-accelerated** rendering via GSK

#### 🔥 Ideas for Shade
- **Matugen/color-scheme-driven theming** — Shade has `ColorScheme` and `Theming` libs already; Matshell's Matugen integration is a reference for full Material You dynamic theming
- **Frecency launcher** — smart ranking by frequency + recency (Shade's applauncher could benefit)
- **CAVA visualizer library** — a nice optional music widget addon
- **Config hot-reload** — live config changes without restart
- **Multi-compositor support pattern** — `utils/compositor/detector.ts`

---

### 1.2 Wayle — Most Full-Featured Rust Shell

**Stack:** Rust + GTK4 + Relm4  
**Repo:** [wayle-rs/wayle](https://github.com/wayle-rs/wayle)  
**Stars:** ~551

#### Architecture
- Written in Rust using **Relm4** (Elm-like architecture for GTK4)
- **Modular bar system** with per-monitor layouts, groups, classes
- Config via `config.toml`, settings GUI (`wayle-settings`), and CLI (`wayle config`)
- **Live reload** — changes to config.toml apply instantly
- Service crates: `wayle-audio`, `wayle-battery`, `wayle-bluetooth`, etc. (reusable across projects)

#### Modules (bar system)
| Module | Description |
|--------|-------------|
| dashboard | System overview panel |
| clock | Time display |
| volume | Audio controls |
| network | WiFi/Ethernet manager |
| bluetooth | BT device manager |
| battery | Power status |
| cpu, ram, storage | System monitors |
| media | MPRIS media player |
| systray | System tray |
| hyprland_workspaces / niri_workspaces | Compositor workspace |
| cava | Audio visualizer |
| notification | Notification center popup |
| weather | Weather display |
| window_title | Active window title |
| custom | Shell-backed custom modules |
| idle_inhibit, power, brightness, microphone, etc. | System controls |

#### 🔥 Ideas for Shade
- **Modular bar module schema** — Wayle's config-driven module system is a gold standard; Shade's bar could adopt a similar declarative layout
- **Per-monitor layouts** — different bar layouts per monitor
- **Triple config surface** — file + GUI + CLI (Shade has gsettings, Wayle adds CLI editing)
- **`wayle-services` pattern** — reusable backend crates; this maps to Astal's approach but worth studying the abstraction
- **Shell-backed custom modules** — users can write their own bar modules using shell scripts

---

### 1.3 LumenShell — ChromeOS-Inspired, Multi-Process

**Stack:** Vala + GTK4 + Wayfire plugins (C++)  
**Repo:** [exynoxx/LumenShell](https://github.com/exynoxx/LumenShell)

#### Architecture (Unique Approach)
- **Each component is an independent process** — no shared in-process state
- Coordination via **DBus** + **Wayfire IPC** + shared config files
- Built from a single Meson tree
- GPU-accelerated via GSK

#### Components
| Binary | Purpose |
|--------|---------|
| `lumen-panel` | Bottom/top bar: running apps + floating tray (WiFi, BT, battery, sound, clock) |
| `lumen-desktop` | App drawer (search bar + paginated tile grid) replacing traditional desktop |
| `lumen-osd` | DBus-driven OSD pill (volume, brightness, mic, caps-lock, display) |
| `lumen-notifications` | `org.freedesktop.Notifications` server — top-right banner stack |
| `lumen-lockscreen` | macOS-style blurred card, PAM auth, `ext-session-lock-v1` |
| `lumen-session` | Headless daemon — monitor layout on hotplug via `wlr-output-management-v1` |
| `lumen-settings` | GTK4/Adwaita config app |

#### 🔥 Ideas for Shade
- **Dedicated OSD process** — LumenShell's separate OSD process for volume/brightness/mic indicators is clean
- **`ext-session-lock-v1` lockscreen** — Shade has a lockscreen; see how LumenShell implements PAM auth + session lock
- **Desktop peek (Win+D)** — sliding windows to corners to reveal desktop
- **Floating rounded tray** — LumenShell's tray expands into paged content
- **Wayfire plugin pattern** — if Shade ever extends Hyprland itself

---

### 1.4 Other Notable Shell Projects

| Project | Stack | Key Idea |
|---------|-------|----------|
| [caffyne-shell](https://github.com/caffyne-org/caffyne-shell) | Python/Fabric | Drag-and-drop panel, Matugen Material theming |
| [gtkshell](https://github.com/dawsers/gtkshell) | C++/GTK4 | Multi-threaded bar, reference for `scroll` modules |
| [Fabric](https://github.com/Fabric-Development/fabric) | Python/GTK3 | Desktop widget framework, 1325★ — signals-based, high-level widget system |

---

## 2. GTK4 Apps with Notable UI for Shade's Widgets

### 2.1 System Monitoring Widgets

| App | Stack | Relevance |
|-----|-------|-----------|
| **Mission Center** | Rust/GTK4 | CPU/Mem/Disk/Network/GPU — per-thread CPU, process list, hardware-accelerated graphs |
| **Resources** (GNOME) | Rust/GTK4 | CPU, memory, GPUs, network, block devices — official GNOME |
| **Monitorets** | Python/GTK4 | Desktop widget-style resource monitor |
| **Inspector** | Python/GTK4 | System info: USB, disk, PCIe, networks, motherboard/CPU |
| **GNOME System Monitor** | C++/GTK4 | Process viewer with tree |
| **GNOME Usage** | Vala/GTK4 | Simplified resource usage |

**For Shade:** Mission Center's per-core CPU graphs, GPU monitoring, and hardware-accelerated rendering patterns could inspire Shade's `systemUsage.tsx` bar widget. Resources shows the official GNOME approach.

### 2.2 Network & WiFi Management

| App | Stack | Relevance |
|-----|-------|-----------|
| **overskride** | Rust/GTK4 | Bluetooth + Obex manager — clean device list, pairing flow |
| **adw-network** | Rust/GTK4/libadwaita | Modern WiFi manager with hotspot workflow |
| **nmrs-gui** | Rust/GTK4 | NetworkManager frontend, Wayland-native |
| **wifi-manager** | Rust/GTK4/layer-shell | WiFi + BT manager for Wayland compositors, brightness/volume sliders |

**For Shade:** Shade already has `network.tsx` and `bluetooth.tsx` indicators. These projects show how full management panels (scan, connect, password dialogs) look in libadwaita. Overskride's BT device list UX is a good reference for Shade's Quick Settings bluetooth section.

### 2.3 Media Player / MPRIS

| App | Stack | Relevance |
|-----|-------|-----------|
| **Amberol** | Rust/GTK4/libadwaita | Minimalist music player — clean track list, album art |
| **Decibels** (GNOME) | GJS/TS/GTK4 | Official GNOME audio player — waveform view |
| **Muzika** | GJS/TS/GTK4 | Customizable home screen, Google Music — **same stack as Shade** |
| **Gapless (G4Music)** | Vala/GTK4 | High-perf, ReplayGain, Pipewire, MPRIS control |
| **Resonance** | Rust/GTK4 | MPRIS, Discord presence, Last.fm |
| **Turntable** | Vala/GTK4 | MPRIS-enabled, scrobbling — good reference for MPRIS integration |

**For Shade:** Shade's media widget in Quick Settings could take cues from Amberol's clean Now Playing UI or Muzika's TypeScript/GJS widget patterns. Decibels is official GNOME and uses Shade's exact stack (GJS + TypeScript).

### 2.4 Notification UX

| App | Stack | Relevance |
|-----|-------|-----------|
| **GNOME Notifications** | — | System notification design |
| **LumenShell notifications** | Vala | Top-right banner stack with click-to-dismiss |
| **Fragments** (Transmission client) | Rust/GTK4 | Notification integration for downloads |

**For Shade:** Shade already has `notifications.tsx`. The LumenShell top-right banner stack and clear-all pattern is a good reference for Shade's notification center.

### 2.5 Launcher / Picker

| App | Stack | Relevance |
|-----|-------|-----------|
| **Walker** | Rust/GTK4 | Customizable app launcher for Wayland — 1000+ stars |
| **Sherlock** | Rust/GTK4 | App/command launcher for Hyprland with async widgets and plugins |
| **Matshell picker** | TS/Astal | Frecency-based multimodal launcher (apps, clipboard, wallpapers) |

**For Shade:** Sherlock is purpose-built for Hyprland and is closest to what Shade's applauncher does. Walker is the most popular GTK launcher. Matshell's frecency ranking is interesting.

---

## 3. Architectural Patterns to Study

### 3.1 Config Surface Strategy

| Project | Config Method | Hot-Reload |
|---------|--------------|------------|
| **Shade** | GSettings (dconf) | ? |
| **Wayle** | config.toml + GUI + CLI | Yes (file watch) |
| **Matshell** | config.json | Yes (file watch) |
| **LumenShell** | Shared JSON + GTK settings app | Restart affected binary |

**Recommendation:** Consider adding a `config.toml` file surface alongside GSettings for power users, with Wayle's live-reload pattern. The GTK settings GUI can remain as the primary interface.

### 3.2 Process Architecture

| Project | Process Model | IPC |
|---------|--------------|-----|
| **Shade** | Single process (all widgets) | D-Bus for commands |
| **LumenShell** | Multi-process (each component separate) | DBus + Wayfire IPC |
| **Wayle** | Single process | Direct in-process |
| **Matshell** | Single process | Direct in-process |

Shade's single-process model is fine — LumenShell's multi-process approach introduces complexity. But Shade's D-Bus command dispatcher (`requestHandler.ts`) is already well-designed for external control.

### 3.3 Widget Mount & Error Isolation

Shade's architecture is already strong here — sequential mount with `safe()` wrappers and per-widget error isolation. This is the same pattern used by LumenShell's independent processes but without the IPC overhead.

### 3.4 Theming Architecture

| Project | Approach |
|---------|----------|
| **Shade** | CSS + `ColorScheme` lib + `Theming` lib, night light integration |
| **Matshell** | Matugen → SCSS templates → dynamic Material You |
| **Wayle** | Color tokens + theme files + palettes |
| **LumenShell** | JSON theme file |

Matshell's Matugen pipeline is the most relevant for Shade since both use the same stack. The flow: wallpaper → Matugen → material color extraction → SCSS variables → compiled CSS → GTK CSS provider.

---

## 4. Specific UI Concepts for Shade

### 4.1 Bar Layout
- **Wayle's config-driven layout** — declarative `[[bar.layout]]` with `left/center/right` and per-monitor overrides
- **LumenShell's floating tray** — rounded tray area on the right that expands into paged content
- **Matshell's adaptive layout** — auto-switches between desktop and laptop widget sets
- **System tray** — Shade doesn't seem to have one yet; Matshell has SysTray via `libastal-tray`

### 4.2 Quick Settings Panel
- **Wayle's dashboard** — system overview with audio, network, BT, brightness
- **Matshell's sidebar** — hardware controls, weather, notes, clock, actions in a slide-out panel
- **LumenShell's paged tray** — paginated content sections for different control groups

### 4.3 OSD
- **LumenShell OSD** — separate process, DBus-driven, watches sysfs for hardware key changes
- **Wayle OSD** — built-in, configurable
- Shade has `osd.tsx` already — could add mic mute, caps-lock, display mode OSD events

### 4.4 Lockscreen
- **LumenShell lockscreen** — macOS-style blurred desktop, PAM auth, `ext-session-lock-v1`
- Shade has a lockscreen — ensure it uses `ext-session-lock-v1` properly

### 4.5 Desktop / Wallpaper
- **LumenShell's `lumen-desktop`** — app drawer replaces traditional desktop
- **Matshell wallpaper picker** — thumbnail grid with frecency
- **Damask / HydraPaper** — wallpaper utilities with multi-monitor support

---

## 5. Tech Stack References (Same Stack as Shade)

These projects use **GJS + TypeScript + GTK4 + libadwaita** — the closest to Shade's tech:

| Project | Lessons |
|---------|---------|
| **Decibels** (GNOME Audio Player) | Official GNOME GJS/TS app, waveform view, GStreamer integration |
| **Muzika** | Music player with customizable home screen — complex TS widget patterns |
| **Foliate** | EPUB reader — complex page layout with GJS |
| **Tangram** | Pinned tab browser — multi-pane layout |
| **Polari** | IRC client — conversation list + message view + input |
| **Matshell** | Desktop shell with same stack — most relevant |
| **Workbench** | GNOME dev tool for experimenting with GTK — good for prototyping |
| **Sticky Notes** | Simple sticky notes — good example of minimalist TS widget |
| **Share** | File sharing with QR codes — drag-and-drop pattern |
| **Oh My SVG** | SVG optimizer — clean utility UI |

Shade's template at [nyx-lyb3ra/gnome-ts-template](https://github.com/nyx-lyb3ra/gnome-ts-template) is useful for bootstrapping new widgets.

---

## 6. Recommendations for Shade

### Priority (High Impact, Low Effort)
1. **System tray** (StatusNotifier) — `libastal-tray` integration, present in both Matshell and Wayle
2. **Weather widget in bar** — Shade already has `weather.ts` lib and `weather.tsx` bar widget, but Matshell's OpenWeatherMap integration is worth comparing
3. **Workspace indicator styling** — Matshell's themed workspace pills show how to make workspaces look polished

### Medium Term
4. **Frecency-based launcher** — replace simple app search with frecency ranking (Matshell pattern)
5. **Config hot-reload** — file-watch based config changes (Wayle pattern)
6. **Per-monitor bar layouts** — different bar layouts per monitor
7. **Music widget improvements** — album art theming, CAVA visualizer options
8. **Network scanning in Quick Settings** — full WiFi scan + connect flow

### Ambition
9. **Material You dynamic theming** — Matugen integration for wallpaper-based color schemes
10. **Multi-compositor support** — automatic compositor detection (Matshell's `utils/compositor/detector.ts`)
11. **Custom bar modules** — users can write their own (Wayle's shell-backed modules)
12. **Dedicated OSD daemon** — for mic mute, caps-lock, display mode events

---

## 7. Key Projects to Watch

| Project | Stars | Why |
|---------|-------|-----|
| [Wayle](https://github.com/wayle-rs/wayle) | 551 | Most complete GTK4 desktop shell, modular architecture |
| [Matshell](https://github.com/Neurarian/matshell) | 68 | Same stack as Shade, Material Design, Matugen theming |
| [Fabric](https://github.com/Fabric-Development/fabric) | 1325 | Widget framework, signals-based, good for reference |
| [LumenShell](https://github.com/exynoxx/LumenShell) | New | ChromeOS-inspired, multi-process, Wayfire plugins |
| [Walker](https://github.com/abenz1267/walker) | 1000+ | GTK4 Wayland launcher — good for applauncher reference |
| [Mission Center](https://missioncenter.io) | High | GTK4 system monitor — for systemUsage.tsx inspiration |

---

*Compiled from awesome-gtk (300+ GTK4/3 apps), direct repo analysis, and web research. See `awesome-gtk/README.md` for the full app catalog.*
