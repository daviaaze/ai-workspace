# dshell Screenshot: GNOME Mutter Reference vs Current Approach

## How GNOME Mutter/Shell Does Screenshots

Source: `gnome-shell/js/ui/screenshot.js` (3166 lines)

### Core Architecture — "Capture-then-Crop"

GNOME captures the screen **ONCE** into a texture, displays it as a frozen
background, then **crops that frozen texture** for the final output. It NEVER
re-captures from the live compositor at output time.

```
PrintScreen pressed
  │
  ▼
async open()
  │  ① screenshot_stage_to_content()  →  frozen texture (THE freeze)
  │  ② _stageScreenshot.set_content(frozen texture)  →  background widget
  │  ③ grabHelper.grab()  →  pointer + keyboard grab
  │  ④ overlay visible (fade in 200ms)
  ▼
ScreenshotUI stays open ──────────────────────────────────────┐
  │                                                          │
  ├─ Selection (Area):  UIAreaSelector drag-rectangle        │
  ├─ Screen (Monitor):  per-monitor screen selectors         │
  └─ Window:            UIWindowSelector — each window is a  │
                        clickable CLONE (actor.paint_to_     │
                        content) with its own texture        │
                                                             │
  User clicks "Capture"                                      │
  ▼                                                          │
async _saveScreenshot()                                      │
  │  ① Area/Screen: texture = _stageScreenshot content      │
  │                  geometry = [x,y,w,h] from selector     │
  │  ② Window:     texture = window's OWN cloned texture    │
  │                geometry = null (full window)            │
  ▼                                                          │
captureScreenshot(texture, geometry, scale, cursor)          │
  │  Shell.Screenshot.composite_to_stream(                  │
  │      texture, x, y, w, h, scale, cursor, stream)        │
  │  → CROPS the already-captured frozen texture            │
  │  → writes PNG to GOutputStream                           │
  ▼                                                          │
close() ◄────────────────────────────────────────────────────┘
```

### Key Properties
1. **Freeze = internal texture** (`screenshot_stage_to_content`), NOT an external
   process. The frozen frame is a GTK/Clutter content displayed as background.
2. **Single overlay, never closes** during selection. The panel + all selectors
   are children of ONE widget, layered on the frozen background. No close→open
   transition.
3. **Capture = crop the frozen texture** via `composite_to_stream(texture, x,y,w,h)`.
   Never reads from the live compositor again → zero race conditions, content
   is exactly what the user saw.
4. **Window capture** uses each window's OWN cloned texture
   (`actor.paint_to_content`), not a compositor region crop.
5. **Coordinates are pixel offsets into the frozen texture** — no global vs
   output-relative ambiguity, no multi-monitor geometry math at capture time.

## Why dshell's Current Approach Is Fundamentally Buggy

| Aspect | GNOME Mutter (correct) | dshell current (bugged) |
|---|---|---|
| Freeze | Internal texture | External `wayfreeze` process |
| Overlay | Single, stays open | Two overlays: toolbar + region-selector |
| Transition | None | `close()` → 200ms gap → `open region-selector` |
| Capture source | Frozen texture (already captured) | **Live compositor** via `grim` |
| Area crop | `composite_to_stream(texture, x,y,w,h)` | `grim -g "x,y WxH"` |
| Window capture | Window's own texture | `grim -g` with `client.x,y,w,h` |
| Race conditions | None (frozen) | Yes: unfreeze → 150ms → grim |
| Coordinate system | Pixel offsets in frozen texture | Global compositor coords to grim -g |

### The Three Failure Modes
1. **Two-overlay transition** — closing the toolbar then opening the
   region-selector needs a 200ms freeze bridge (`#freezeKeepAlive`). Fragile.
2. **grim captures the LIVE compositor** — after `stopFreeze()`, grim captures
   whatever is on screen *now*, which may not match what the user selected
   (windows moved, animations advanced). The frozen frame the user drew on is
   gone.
3. **`grim -g` coordinate ambiguity** — grim's `-g` region in multi-monitor
   setups can be interpreted relative to the focused output rather than global
   space, producing wrong/empty captures for windows or monitors not on the
   focused output.

## Proposed Redesign: "Capture-then-Crop" on Hyprland

Replicate GNOME's architecture using tools available on Hyprland:

### Build deps available (GTK 4.22.4)
- `Gdk.Texture.new_from_filename()` ✓
- `Gdk.Texture.save_to_png()` ✓
- `Gdk.Texture.save_to_png_bytes()` ✓
- `Gdk.Texture.download()` ✓ (raw ARGB32 pixels)
- `new_sub_texture()` ✗ (not in GTK4 — use crop tool instead)

### Crop tool options
| Tool | Command | Pros | Cons |
|---|---|---|---|
| ImageMagick | `magick in.png -crop WxH+X+Y +repage out.png` | Simple, reliable | New dep (nixpkgs has it) |
| ffmpeg | `ffmpeg -i in.png -filter crop=w:h:x:y -y out.png` | Already a recording pattern | New dep |
| Native GTK+Cairo | `texture.download()` → sub-surface → `cairo_surface_write_to_png()` | No new dep | ~30 lines pixel math, fiddly mem mgmt |

### Flow
```
PrintScreen → toggleOverlay()
  │  ① grim (NO -g) → /tmp/dshell-freeze-<ts>.png   ← THE freeze
  │  ② Gdk.Texture.new_from_filename() → background Gtk.Picture
  │  ③ single overlay visible (panel + selectors on frozen bg)
  ▼
User selects area / clicks window / picks monitor  (on frozen bg)
  ▼
Capture:
  Area     → crop tool:  -crop {w}x{h}+{x}+{y}      (x,y = selection in image px)
  Window   → crop tool:  -crop {cw}x{ch}+{cx}+{cy}  (client geometry, image px)
  Monitor  → crop tool:  -crop {mw}x{mh}+{mx}+{my}  (monitor geometry, image px)
  Full     → just copy the frozen.png to output (no crop)
  ▼
wl-copy + notify + close overlay
```

### Why this fixes all three failure modes
1. **No transition** — single overlay, frozen background stays the whole time.
2. **No live recapture** — output is cropped from the frozen `grim` PNG taken
   at open time. Content is exactly what the user saw.
3. **No coordinate ambiguity** — crop offsets are pixel positions in the frozen
   image (whose (0,0) = compositor (0,0)). No `grim -g` output-relative math.

### Window selection (Hyprland can't clone window textures)
GNOME clones each window with `paint_to_content()`. Hyprland/layer-shell can't
do that. Options:
- **A)** Draw window outlines on the frozen bg using Hyprland client geometry;
  clicking a region selects that window → crop its geometry. (GNOME-like UX)
- **B)** Simpler: "Window" mode just crops the focused client's geometry from
  the frozen image (no click-to-select). Matches current UX, far more robust.

### Recording (screencast) stays separate
`wf-recorder` / `wl-screenrec` still capture the live compositor for video.
The capture-then-crop pattern only applies to still screenshots. Recording
keeps using `grim`-style live capture (or its own path).
