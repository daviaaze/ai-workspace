# Quick Settings & Desktop Widgets Improvement Plan

> Covers: brightness slider fix, idle control simplification, weather upgrade, desktop widget inspiration

---

## Phase 1 — Brightness Slider Fix (Small)

**Problem:** The `Slider` component wraps the icon in a `<Gtk.Button onClicked={props.setMutted}>`. For brightness, `setMutted` is never passed, so clicking the icon does nothing.

**Files:** `src/widget/common/slider.tsx`, `src/widget/quicksettings/sliders.tsx`

**Fix — cycle through preset values:**

Add an `onIconClick` prop to slider (optional). When passed, the icon button cycles through predefined values. When not passed, the icon is rendered as a static `<Gtk.Image>` (no button wrapper).

| Click | Brightness |
|-------|-----------|
| 1     | 25%       |
| 2     | 50%       |
| 3     | 75%       |
| 4     | 100%      |
| 5     | 25% (wrap)|

Implementation in `Slider`:
```tsx
// If onIconClick is provided, wrap in button; otherwise static icon
{props.onIconClick ? (
  <Gtk.Button onClicked={props.onIconClick}>
    <Gtk.Image iconName={props.icon} />
  </Gtk.Button>
) : (
  <Gtk.Image iconName={props.icon} />
)}
```

**Affects:** Only the brightness slider — audio sliders already pass `setMutted` (mute/unmute), which is correct.

> Decision: make the icon cycle brightness — it's more interactive than a dead static icon.

---

## Phase 2 — Simplify Idle Controls (Small)

**Problem:** 
- The "Auto Lock Off" icon (`system-unlock-screen-symbolic`) doesn't render correctly in the icon theme
- Having both auto-lock toggle AND auto-sleep toggle in Quick Settings is confusing
- Settings panel already has full idle management with granular controls

**Current state:**
| Widget | File | What it does |
|--------|------|-------------|
| Auto Lock toggle | `button-grid/idleControls.tsx` | Toggle hypridle enabled, popover with sliders |
| Auto Sleep toggle | `button-grid/caffeinated.tsx` | Keep awake / auto sleep, popover with durations |

**Changes:**

1. **Remove `idleControls.tsx` from Quick Settings** — delete it from `button-grid/index.tsx`

2. **Rename `caffeinated.tsx`** to handle the combined role:
   - Label: "Auto Sleep" (default state — sleep is enabled)
   - When inhibited: "Keep Awake" with timer
   - Keep the popover with duration choices
   - Remove the auto-lock toggle entirely from Quick Settings

3. **Settings panel already has idle management** — `settings/general.tsx` has a full "Idle Management" section with Auto Lock, Dim, DPMS, and Suspend controls. No changes needed there — it's already the right place.

**Result:** Quick Settings now has exactly one button: Auto Sleep (which doubles as "Keep Awake" when inhibited). All fine-grained idle configuration lives in Settings.

---

## Phase 3 — Weather Widget Improvements

- **Status:** `[WIP]`

**Current state:** 
- Bar: icon + temperature, click opens popover with GWeather widget
- Backend: `lib/weather.ts` uses GWeather (libgweather) with auto-location via geolocation

**Inspiration from ecosystem:**

| Source | Pattern | Apply to Shade |
|--------|---------|---------------|
| **Mousam** | Dynamic gradient background based on conditions | Popover/window background shifts color by weather |
| **Mousam** | Hourly forecast cards (temp + icon + time) | Hourly row below current conditions |
| **Mousam** | Multi-day forecast (hi/lo, icon, day name) | 5-day row in popover |
| **Mousam** | Compact "at a glance" mode | Optional minimal widget view |
| **Mousam** | Wind speed, humidity, UV, pressure cards | Detail cards below forecast |
| **GNOME Weather** | Location name display | Show city name in heading |
| **GNOME Weather / iOS** | Sunrise/sunset times with visual arc | Sun position arc or simple time row |

**Proposed architecture:**

```
┌─────────────────────────────────┐
│  🌤️  São Paulo                   │  ← gradient bg (blue for clear)
│  24°C  Feels like 26°            │
│  Clear sky                       │
├─────────────────────────────────┤
│  Now  2PM  3PM  4PM  5PM  6PM   │  ← hourly forecast row
│  ☀️   ☀️    🌤️   ⛅   ⛅   ☁️   │
│  24°  25°  23°  22°  20°  18°  │
├─────────────────────────────────┤
│  Mon  Tue  Wed  Thu  Fri        │  ← multi-day forecast
│  ☀️   ⛅    ☁️    🌧️   ☀️       │
│  25/18  23/17  20/16  21/17  .. │
├─────────────────────────────────┤
│        ☀️                        │  ← sunrise/sunset arc
│      ╱    ╲       sun position   │
│  🌅 ─        ─ 🌇               │
│  06:12        18:34              │
│  Sunrise      Sunset             │
│  Daylight: 12h 22m               │
├─────────────────────────────────┤
│  💨 Wind: 12 km/h               │  ← detail cards
│  💧 Humidity: 65%               │
│  ☀️ UV Index: 6 (High)          │
│  🌡️ Pressure: 1013 hPa          │
└─────────────────────────────────┘
```

**Implementation approach:**

1. **Gradient background** — Compute from GWeather sky condition code. Map cleanly:
   - Clear → warm amber/blue gradient
   - Few clouds → lighter blue/white
   - Overcast → grey-blue
   - Rain/snow → dark slate
   Apply as CSS on the popover box.

2. **Hourly forecast** — GWeather.Info has `get_forecast_list()` which returns `GWeather.Info[]` for future times. Filter to next 6–8 hours, show as horizontal scrollable row.

3. **Multi-day** — From forecast list, group by day, extract min/max temp and dominant condition.

4. **Sunrise/sunset** — GWeather.Info exposes `get_value_sunrise()` and `get_value_sunset()` (already used in `colorScheme.ts` for auto dark mode). Two visual options:

   **Option A — Sun arc (richer, ✅ CHOSEN):**
   - `Gtk.DrawingArea` with a Cairo-drawn semicircle arc
   - Sun dot positioned along the arc based on current time relative to sunrise/sunset
   - Sunrise time on the left, sunset time on the right
   - Arc filled below horizon line in amber/orange gradient
   - "Daylight: Xh Ym" label below
   - After sunset: arc is dimmed/grey, show "Next sunrise: 06:12"

   **Option B — Simple row (minimal):**
   - Two `IconInfoRow` side by side:
     - `sunrise-symbolic` + "06:12" + "Sunrise"
     - `sunset-symbolic` + "18:34" + "Sunset"
   - "Daylight: 12h 22m" label below

   Data extraction:
   ```ts
   const [sunriseValid, sunriseUnix] = weather.info.get_value_sunrise()
   const [sunsetValid, sunsetUnix] = weather.info.get_value_sunset()
   const sunrise = GLib.DateTime.new_from_unix_local(sunriseUnix)
   const sunset = GLib.DateTime.new_from_unix_local(sunsetUnix)
   const daylightSecs = sunsetUnix - sunriseUnix
   ```

5. **Details** — GWeather.Info exposes wind, humidity, pressure, visibility. Add collapsible detail cards.

**Files changed:**
- `src/widget/common/weatherWidget.tsx` — complete upgrade
- `src/widget/bar/weather.tsx` — widen popover, maybe use a `Gtk.Window` for more space
- `src/lib/weather.ts` — add helper methods for forecast access

---

## Phase 4 — Desktop Widget Framework (Blueprint, Future)

**Concept:** A system where users can place small info widgets on their desktop wallpaper layer. Built with Astal windows at the `BACKGROUND` layer.

**Widget candidates (from awesome-gtk research):**

| Widget | Data Source | Visual |
|--------|------------|--------|
| **Weather card** | GWeather (already in Shade) | Gradient bg card with temp + icon + forecast mini-row |
| **System monitor** | `/proc` or sysfs | Mini CPU/RAM/Net graph cards (Mission Center style) |
| **Clock** | GLib.DateTime | Large text clock with date, option for world clocks |
| **Now Playing** | AstalMpris | Album art + track info + controls (Sherlock MprisTile style) |
| **Bluetooth battery** | AstalBluetooth | Per-device battery bars, especially dual earbud (BudsLink style) |
| **Calendar** | GLib | Month grid with today highlighted |
| **Sticky notes** | Local JSON store | Colored note cards with markdown (Folio/Apostrophe pattern) |
| **Pomodoro timer** | Local | Countdown with work/break phases (Solanum/Flowtime style) |

**Architecture:**
- Each widget is a standalone `.tsx` file in `src/widget/desktop/`
- Mounted via a `DesktopWidget` registry — user picks which ones show
- Positioned manually or auto-tiled in a grid
- Config persisted to GSettings

**Not implementing now** — this is a blueprint for the future. Phase 3 (weather) is the concrete next step.

---

## Summary

| Phase | Effort | Key files | Ready? |
|-------|--------|-----------|--------|
| 1. Brightness cycle | ~20 lines | `slider.tsx`, `sliders.tsx` | ✅ Ready |
| 2. Idle simplify | ~15 lines (remove + rename) | `idleControls.tsx`, `caffeinated.tsx`, `button-grid/index.tsx` | ✅ Ready |
| 3. Weather upgrade | ~250 lines | `weatherUtils.ts`, `weather.ts`, `sunArc.tsx`, `weatherWidget.tsx`, `weather.tsx`, `shade.css` | ✅ Ready, implementation in progress |
| 4. Desktop widgets | Blueprint only | New `src/widget/desktop/` | 📋 Future |
