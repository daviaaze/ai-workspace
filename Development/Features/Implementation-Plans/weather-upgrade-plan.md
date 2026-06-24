# Weather Widget Upgrade — Implementation Plan

> Based on the design spec at `../Backlog/quicksettings-and-widgets-plan.md`
> Covers: gradient backgrounds, hourly forecast, multi-day forecast, sunrise/sunset sun arc, detail cards, bar popover sizing

---

## Scope

**In scope:**
1. Extract weather utility functions (condition → gradient, sun position, format helpers)
2. Rewrite `src/widget/common/weatherWidget.tsx` with full layout
3. Cairo sun arc component (`Gtk.DrawingArea`)
4. Widen/improve bar weather popover
5. Update QS expander weather section
6. CSS classes for weather widgets

**Out of scope:**
- Desktop widget framework (Phase 4)
- Geolocation service improvements (1.10 — separate plan)
- Other launcher/QS changes

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/lib/weatherUtils.ts` | **Create** | Pure utility functions: condition→gradient mapping, sun position math, time formatting, wind direction |
| `src/lib/weather.ts` | **Modify** | Add `getForecastArray()`, `getSunriseTime()`, `getSunsetTime()` helper methods that wrap GWeather API |
| `src/widget/common/weatherWidget.tsx` | **Rewrite** | Full weather popover content: header, sunrise/sunset arc, hourly row, multi-day, detail cards, refresh |
| `src/widget/common/sunArc.tsx` | **Create** | Self-contained `Gtk.DrawingArea` component with Cairo sun arc rendering |
| `src/widget/bar/weather.tsx` | **Modify** | Use wider popover, integrate new `WeatherWidget` |
| `src/widget/quicksettings/expander/weather.tsx` | **Modify** | Use new `WeatherWidget` |
| `src/shade.css` | **Modify** | Add weather-specific CSS classes for gradient backgrounds, detail cards |
| `quicksettings-and-widgets-plan.md` | **Modify** | Update status to `[WIP]` |

---

## Step-by-Step Tasks

### Step 1: Create `src/lib/weatherUtils.ts`

**Purpose:** Pure utility functions extracted from weather widget logic. No GObject, no Gnim — easy to test.

**File:** `src/lib/weatherUtils.ts`

```ts
// Icon name → CSS gradient background
// Uses GWeather icon names (non-localized, consistent):
//   weather-clear, weather-few-clouds, weather-scattered-clouds,
//   weather-overcast, weather-showers, weather-storm, weather-snow, weather-fog
export function conditionGradient(iconName: string): string {
  if (iconName.includes("storm") || iconName.includes("thunder"))
    return "linear-gradient(135deg, #0f0f1a 0%, #2d1b4e 50%, #4a1942 100%)"
  if (iconName.includes("snow") || iconName.includes("sleet"))
    return "linear-gradient(135deg, #dfe6e9 0%, #b2bec3 50%, #636e72 100%)"
  if (iconName.includes("shower") || iconName.includes("rain"))
    return "linear-gradient(135deg, #1e272e 0%, #57606f 50%, #747d8c 100%)"
  if (iconName.includes("fog") || iconName.includes("mist") || iconName.includes("haze"))
    return "linear-gradient(135deg, #636e72 0%, #b2bec3 100%)"
  if (iconName.includes("overcast") || iconName.includes("cloudy"))
    return "linear-gradient(135deg, #1e272e 0%, #485460 100%)"
  if (iconName.includes("scattered"))
    return "linear-gradient(135deg, #353b48 0%, #636e72 100%)"
  if (iconName.includes("few-clouds"))
    return "linear-gradient(135deg, #2c3e50 0%, #5b86e5 40%, #b0c4de 100%)"
  // Clear / default
  return "linear-gradient(135deg, #1e3a5f 0%, #4a90d9 50%, #87ceeb 100%)"
}

// Night variant — dimmer, cooler
// Detected by icon name containing "night"
function conditionGradientNight(iconName: string): string {
  if (iconName.includes("storm") || iconName.includes("thunder"))
    return "linear-gradient(135deg, #080811 0%, #1a0f2e 50%, #2e0f2a 100%)"
  if (iconName.includes("snow") || iconName.includes("sleet"))
    return "linear-gradient(135deg, #2d3436 0%, #485460 50%, #636e72 100%)"
  if (iconName.includes("shower") || iconName.includes("rain"))
    return "linear-gradient(135deg, #0f111a 0%, #2d3436 100%)"
  if (iconName.includes("fog") || iconName.includes("mist"))
    return "linear-gradient(135deg, #2d3436 0%, #485460 100%)"
  if (iconName.includes("overcast") || iconName.includes("cloudy"))
    return "linear-gradient(135deg, #0f111a 0%, #1e272e 100%)"
  if (iconName.includes("scattered") || iconName.includes("few"))
    return "linear-gradient(135deg, #1a1a2e 0%, #2d3561 100%)"
  // Clear night / default
  return "linear-gradient(135deg, #0c0c1a 0%, #1a1a3e 50%, #2d3561 100%)"
}

export function weatherGradient(iconName: string): string {
  if (iconName.includes("night")) return conditionGradientNight(iconName)
  return conditionGradient(iconName)
} 

// Format GLib unix timestamp → "06:12" or "2 PM"
export function formatTime(unixTs: number): string {
  const dt = GLib.DateTime.new_from_unix_local(unixTs)
  return dt.format("%H:%M") ?? "--:--"
}

// Format temperature with degree symbol
export function formatTemp(celsius: number): string {
  return `${Math.round(celsius)}°`
}

// Wind direction — GWeatherWindDirection enum to compass label
// GWeather returns enum values: INVALID=-1, VARIABLE=0, N=1, NNE=2, ... NNW=16
// https://gjs-docs.gnome.org/gweather40~4.0/gweather.winddirection
const WIND_DIRS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

export function windDirectionLabel(windEnum: number): string {
  if (windEnum <= 0) return "—"  // INVALID (-1) or VARIABLE (0)
  if (windEnum >= 1 && windEnum <= 16) return WIND_DIRS[windEnum - 1]
  return "—"
}

// Sunrise/set → sun position angle (0° = horizon, 90° = zenith)
// Returns fraction of day elapsed between sunrise and sunset
export function sunAngle(sunrise: number, sunset: number, now: number): number {
  const dayLength = sunset - sunrise
  if (dayLength <= 0) return -1
  const elapsed = now - sunrise
  if (elapsed < 0) return -1   // before sunrise
  if (elapsed > dayLength) return -1  // after sunset
  // Map to semicircle: 0→π where 0=sunrise, π=sunset
  const fraction = elapsed / dayLength
  return Math.sin(Math.PI * fraction) // 0 at edges, 1 at noon
}

// Check if currently within daylight hours
export function isDaytime(sunrise: number, sunset: number, now: number): boolean {
  return now >= sunrise && now <= sunset
}
```

**Dependency note:** This file imports `GLib` for `formatTime`. Add at top:
```ts
import GLib from "gi://GLib?version=2.0"
```

**Acceptance:** `weatherGradient` returns a valid CSS gradient string for any GWeather icon name (clear, cloudy, rain, snow, storm, fog, night variants).

---

### Step 2: Add forecast helpers to `src/lib/weather.ts`

**Purpose:** Expose GWeather forecast and sunrise/sunset data as clean JS values that weather widgets can consume reactively.

**Changes to `src/lib/weather.ts`:**

Add imports at top:
```ts
import { toArray } from "#/lib/gjsUtils"
```

Add these methods to the `Weather` class:

```ts
// Returns array of forecast entries for the next N hours
getHourlyForecast(hours: number = 8): Array<{
  time: number    // unix timestamp
  temp: number    // celsius
  iconName: string
}> {
  const list = this.#weather.get_forecast_list()
  if (!list) return []
  const forecasts = toArray<GWeather.Info>(list)
  const now = GLib.DateTime.new_now_local().to_unix()
  
  return forecasts
    .filter((f) => {
      const [valid, ts] = f.get_value_update()
      return valid && ts > now && ts < now + hours * 3600
    })
    .map((f) => {
      const [, ts] = f.get_value_update()
      const [, temp] = f.get_value_temp(GWeather.TemperatureUnit.CENTIGRADE)
      return {
        time: ts,
        temp,
        iconName: f.get_icon_name(),
      }
    })
    .slice(0, hours)
}

// Returns daily forecast entries (grouped by day)
getDailyForecast(days: number = 5): Array<{
  date: number        // unix timestamp at noon
  tempMax: number
  tempMin: number
  iconName: string
  dayName: string     // "Mon", "Tue", etc.
}> {
  const list = this.#weather.get_forecast_list()
  if (!list) return []
  const forecasts = toArray<GWeather.Info>(list)
  if (forecasts.length === 0) return []

  // Group by day (using date only, ignoring time)
  const dayMap = new Map<string, GWeather.Info[]>()
  for (const f of forecasts) {
    const [, ts] = f.get_value_update()
    const dt = GLib.DateTime.new_from_unix_local(ts)
    const dayKey = dt.format("%Y-%m-%d")
    if (!dayKey) continue
    if (!dayMap.has(dayKey)) dayMap.set(dayKey, [])
    dayMap.get(dayKey)!.push(f)
  }

  // Skip today (index 0 = today's forecast, we want future days)
  const entries = Array.from(dayMap.entries())
  entries.shift() // remove today
  return entries.slice(0, days).map(([_, fs]) => {
    let tempMax = -Infinity
    let tempMin = Infinity
    const [, ts] = fs[0].get_value_update()
    const dt = GLib.DateTime.new_from_unix_local(ts)

    // Use the middle forecast entry's icon as representative
    const midIcon = fs[Math.floor(fs.length / 2)].get_icon_name()

    for (const f of fs) {
      const [, max] = f.get_value_temp_max(GWeather.TemperatureUnit.CENTIGRADE)
      const [, min] = f.get_value_temp_min(GWeather.TemperatureUnit.CENTIGRADE)
      if (max > tempMax) tempMax = max
      if (min < tempMin) tempMin = min
    }

    return {
      date: ts,
      tempMax,
      tempMin,
      iconName: midIcon,
      dayName: dt.format("%a") ?? "---",
    }
  })
}

// Get sunrise unix timestamp
getSunriseTime(): number {
  const [, ts] = this.#weather.get_value_sunrise()
  return ts
}

// Get sunset unix timestamp
getSunsetTime(): number {
  const [, ts] = this.#weather.get_value_sunset()
  return ts
}

// Get current conditions details
getDetails(): {
  windSpeed: number
  windDirection: number    // GWeatherWindDirection enum (1-16: N, NNE, ..., NNW)
  humidity: number         // relative humidity percentage
  pressure: number         // hPa
} {
  // GWeather SpeedUnit: 0=MS, 1=KMH, 2=MPH, 3=KNOTS, 4=BEAUFORT
  // GJS maps GIR out-params to return values: [isValid, speed, dir]
  const [, speed, dir] = this.#weather.get_value_wind(GWeather.SpeedUnit.KMH)
  // get_humidity() returns a formatted string like "55%" — parse the number
  const humStr = this.#weather.get_humidity()
  const humidity = humStr ? parseFloat(humStr) : 0
  const [, pressure] = this.#weather.get_value_pressure(GWeather.PressureUnit.HPA)
  return {
    windSpeed: speed,
    windDirection: dir,
    humidity,
    pressure,
  }
}
```

**GIR Notes — Verify in build:**
- `get_forecast_list()` returns `GLib.SList<GWeather.Info>`, convertible via `toArray()`
- `get_value_wind(unit)` — returns `[boolean, speedKMH, GWeatherWindDirection]` where direction is an **enum** (INVALID=-1, VARIABLE=0, N=1, NNE=2, ..., NNW=16), NOT degrees
- `get_humidity()` — returns a `utf8` string directly (e.g. "55%"). **There is no** `get_value_humidity()` in GWeather 4.0.
- `get_value_pressure(unit)` — returns `[boolean, hpa]`
- `get_value_temp(unit)` — returns `[boolean, celsius]`
- `get_value_temp_max(unit)` — returns `[boolean, celsius]`
- `get_value_temp_min(unit)` — returns `[boolean, celsius]`

**Acceptance:** Weather singleton exposes all 4 new methods; forecast data is populated after `update()` completes.

---

### Step 3: Create sunrise/sunset arc component `src/widget/common/sunArc.tsx`

**Purpose:** A self-contained `Gtk.DrawingArea` that draws a Cairo sun position arc. Receives sunrise/sunset/now timestamps and renders the arc with sun dot.

**File:** `src/widget/common/sunArc.tsx`

```tsx
import Cairo from "gi://cairo?version=1.0"
import GLib from "gi://GLib?version=2.0"
import Gtk from "gi://Gtk?version=4.0"
import { toArray } from "#/lib/gjsUtils"

interface SunArcProps {
  sunrise: number
  sunset: number
  now: number
}

export const SunArc = ({ sunrise, sunset, now }: SunArcProps) => {
  // Handle invalid/unset timestamps (initial loading)
  if (!sunrise || !sunset || sunrise <= 0 || sunset <= 0) {
    return <Gtk.Box heightRequest={30} /> as unknown as Gtk.DrawingArea
  }

  const isDay = now >= sunrise && now <= sunset
  const dayLength = sunset - sunrise
  const fraction = dayLength > 0 ? (now - sunrise) / dayLength : 0

  const draw = (_area: Gtk.DrawingArea, cr: Cairo.Context, w: number, h: number) => {
    const pad = 8
    const arcW = w - pad * 2
    const arcH = h * 0.65
    const cx = w / 2
    const cy = h * 0.85
    const rx = arcW / 2
    const ry = arcH

    // ── Background fill below the arc (ground area) ──
    cr.moveTo(cx - rx, cy)
    cr.arc(cx - rx, cy, rx, ry, 0, Math.PI)
    cr.closePath()
    if (isDay) {
      // Amber/orange gradient for daytime
      cr.setSourceRGBA(1.0, 0.65, 0.2, 0.12)
    } else {
      cr.setSourceRGBA(0.2, 0.2, 0.4, 0.12)
    }
    cr.fill()

    // ── Arc line ──
    cr.moveTo(cx - rx, cy)
    cr.arc(cx - rx, cy, rx, ry, 0, Math.PI)
    cr.setSourceRGBA(1, 1, 1, isDay ? 0.4 : 0.2)
    cr.setLineWidth(1.5)
    cr.stroke()

    // ── Horizon line ──
    cr.moveTo(pad, cy)
    cr.lineTo(w - pad, cy)
    cr.setSourceRGBA(1, 1, 1, 0.15)
    cr.setLineWidth(1)
    cr.stroke()

    // ── Sun position dot ──
    if (isDay && fraction >= 0 && fraction <= 1) {
      const angle = Math.PI * (1 - fraction)  // 0=sunrise, π=sunset
      const sx = cx - rx * Math.cos(angle)
      const sy = cy - ry * Math.sin(angle)

      // Glow
      cr.arc(sx, sy, 10, 0, 2 * Math.PI)
      cr.setSourceRGBA(1.0, 0.7, 0.1, 0.2)
      cr.fill()

      // Sun dot
      cr.arc(sx, sy, 5, 0, 2 * Math.PI)
      cr.setSourceRGBA(1.0, 0.8, 0.1, 1.0)
      cr.fill()
    }

    // ── Sunrise time label (left) ──
    const sunriseLabel = formatTimeShort(sunrise)
    cr.selectFontFace("sans-serif", Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL)
    cr.setFontSize(9)
    cr.setSourceRGBA(1, 1, 1, 0.7)
    
    const extents = cr.textExtents(sunriseLabel)
    cr.moveTo(pad, cy + ry - extents.y_advance + 6)
    cr.showText(sunriseLabel)

    // Icon for sunrise (small circle)
    cr.arc(pad + 4, cy + ry - extents.y_advance + 9, 3, 0, 2 * Math.PI)
    cr.setSourceRGBA(1.0, 0.6, 0.1, 0.7)
    cr.fill()

    // ── Sunset time label (right) ──
    const sunsetLabel = formatTimeShort(sunset)
    const extents2 = cr.textExtents(sunsetLabel)
    cr.setSourceRGBA(1, 1, 1, 0.7)
    cr.moveTo(w - pad - extents2.x_advance, cy + ry - extents2.y_advance + 6)
    cr.showText(sunsetLabel)

    // Icon for sunset
    cr.arc(w - pad - 4, cy + ry - extents2.y_advance + 9, 3, 0, 2 * Math.PI)
    cr.setSourceRGBA(0.8, 0.3, 0.1, 0.7)
    cr.fill()

    // ── "Daylight: Xh Ym" label ──
    const hours = Math.floor(dayLength / 3600)
    const minutes = Math.floor((dayLength % 3600) / 60)
    const daylightLabel = `Daylight: ${hours}h ${minutes}m`
    cr.setFontSize(8)
    cr.setSourceRGBA(1, 1, 1, 0.5)
    const extents3 = cr.textExtents(daylightLabel)
    cr.moveTo(cx - extents3.x_advance / 2, h - 4)
    cr.showText(daylightLabel)
  }

  const area = (
    <Gtk.DrawingArea
      hexpand
      heightRequest={100}
      widthRequest={280}
    />
  ) as Gtk.DrawingArea

  area.set_draw_func(draw)
  return area
}

function formatTimeShort(unixTs: number): string {
  const dt = GLib.DateTime.new_from_unix_local(unixTs)
  return dt.format("%H:%M") ?? "--:--"
}
```

**Acceptance:** Component renders a curved arc with horizon line, sun dot positioned correctly between sunrise/sunset labels. Daylight duration shown below.

---

### Step 4: Rewrite `src/widget/common/weatherWidget.tsx`

**Purpose:** Complete weather popover with all sections.

**File:** `src/widget/common/weatherWidget.tsx` (full rewrite)

```tsx
import GWeather from "gi://GWeather?version=4.0"
import GLib from "gi://GLib?version=2.0"
import Gtk from "gi://Gtk?version=4.0"
import { createBinding, createState, onCleanup } from "gnim"
import WeatherLib from "#/lib/weather"
import { weatherGradient, formatTemp, formatTime, windDirectionLabel } from "#/lib/weatherUtils"
import { SunArc } from "#/widget/common/sunArc"

export const WeatherIcon = () => {
  const weather = WeatherLib.get_default()
  return (
    <Gtk.Box spacing={4} halign={Gtk.Align.CENTER}>
      <Gtk.Image
        iconName={createBinding(weather, "info").as((w) => w?.get_icon_name() ?? "")}
        pixelSize={20}
      />
      <Gtk.Label
        label={createBinding(weather, "info").as((w) =>
          w?.is_valid() ? w.get_temp_summary() : "—",
        )}
      />
    </Gtk.Box>
  )
}

export const WeatherWidget = () => {
  const weather = WeatherLib.get_default()
  const info = createBinding(weather, "info")
  // Track 'now' every 30s so the sun arc stays current
  const [now, setNow] = createState(GLib.DateTime.new_now_local().to_unix())
  const nowTimerId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 30, () => {
    setNow(GLib.DateTime.new_now_local().to_unix())
    return GLib.SOURCE_CONTINUE
  })
  onCleanup(() => {
    if (nowTimerId) GLib.Source.remove(nowTimerId)
  })

  // Read reactive info and build data snapshots
  const locationName = info.as((w) => w?.get_location_name() ?? "—")
  const temp = info.as((w) =>
    w?.is_valid()
      ? formatTemp(w.get_value_temp(GWeather.TemperatureUnit.CENTIGRADE)[1])
      : "--°",
  )
  const feelsLike = info.as((w) =>
    w?.is_valid() ? `Feels like ${formatTemp(w.get_apparent())}` : "",
  )
  const skyDesc = info.as((w) => w?.get_sky() ?? "")
  const iconName = info.as((w) => w?.get_icon_name() ?? "weather-none-available-symbolic")

  // Gradient based on weather icon name
  const gradient = info.as((w) =>
    w?.is_valid()
      ? weatherGradient(w.get_icon_name() ?? "")
      : "linear-gradient(135deg, #1e3a5f 0%, #4a90d9 100%)",
  )

  // Sunrise/sunset
  const sunrise = info.as((w) => (w?.is_valid() ? w.get_value_sunrise()[1] : 0))
  const sunset = info.as((w) => (w?.is_valid() ? w.get_value_sunset()[1] : 0))

  // Detail data — GJS maps GIR out-params to return values:
  // get_value_wind(unit) → [isValid, speed, WindDirection] (enum 1-16, not degrees)
  // get_humidity() → string (e.g. "55%") — no out-params, no get_value_humidity() in GWeather 4.0
  // get_value_pressure(unit) → [isValid, hPa]
  const windSpeed = info.as((w) => {
    if (!w?.is_valid()) return 0
    const [, speed] = w.get_value_wind(GWeather.SpeedUnit.KMH)
    return speed
  })
  const windDir = info.as((w) => {
    if (!w?.is_valid()) return 0
    const [, , dir] = w.get_value_wind(GWeather.SpeedUnit.KMH)
    return dir  // GWeatherWindDirection enum (1-16)
  })
  const humidity = info.as((w) => {
    if (!w?.is_valid()) return 0
    const hStr = w.get_humidity()
    return hStr ? parseFloat(hStr) : 0
  })
  const pressure = info.as((w) => {
    if (!w?.is_valid()) return 0
    const [, p] = w.get_value_pressure(GWeather.PressureUnit.HPA)
    return p
  })

  // Forecast
  const hourlyForecast = info.as(() => {
    if (!info()?.is_valid()) return []
    return weather.getHourlyForecast(8)
  })
  const dailyForecast = info.as(() => {
    if (!info()?.is_valid()) return []
    return weather.getDailyForecast(5)
  })

  return (
    <Gtk.Box
      orientation={Gtk.Orientation.VERTICAL}
      cssClasses={["weather-widget"]}
      style={gradient.as((g) => `background: ${g}; border-radius: 12px;`)}
    >
      {/* ── Header: Icon + Location ── */}
      <Gtk.Box spacing={12} cssClasses={["p-12"]}>
        <Gtk.Image iconName={iconName} pixelSize={48} />
        <Gtk.Box orientation={Gtk.Orientation.VERTICAL}>
          <Gtk.Label
            cssClasses={["title-3"]}
            label={locationName}
            halign={Gtk.Align.START}
          />
          <Gtk.Label
            cssClasses={["weather-temp"]}
            label={temp}
            halign={Gtk.Align.START}
          />
          <Gtk.Label
            label={feelsLike}
            halign={Gtk.Align.START}
          />
          <Gtk.Label
            label={skyDesc}
            halign={Gtk.Align.START}
          />
        </Gtk.Box>
      </Gtk.Box>

      {/* ── Sunrise/Sunset Arc (updates every 30s via timeout) ── */}
      <Gtk.Box cssClasses={["p-8"]}>
        <SunArc
          sunrise={sunrise()}
          sunset={sunset()}
          now={now()}
        />
      </Gtk.Box>

      {/* ── Hourly Forecast ── */}
      <Gtk.Box orientation={Gtk.Orientation.VERTICAL} cssClasses={["p-8", "weather-section"]}>
        <Gtk.Label
          cssClasses={["caption", "weather-section-label"]}
          label="Hourly Forecast"
          halign={Gtk.Align.START}
        />
        <Gtk.ScrolledWindow hscrollbarPolicy={Gtk.PolicyType.AUTOMATIC}>
          <Gtk.Box spacing={8}>
            {hourlyForecast.as((forecasts) =>
              forecasts.map((f) => (
                <Gtk.Box
                  orientation={Gtk.Orientation.VERTICAL}
                  cssClasses={["weather-hourly-item"]}
                  spacing={2}
                >
                  <Gtk.Label cssClasses={["caption"]} label={formatTime(f.time)} />
                  <Gtk.Image iconName={f.iconName} pixelSize={20} />
                  <Gtk.Label label={formatTemp(f.temp)} />
                </Gtk.Box>
              )),
            )}
          </Gtk.Box>
        </Gtk.ScrolledWindow>
      </Gtk.Box>

      {/* ── Daily Forecast ── */}
      <Gtk.Box orientation={Gtk.Orientation.VERTICAL} cssClasses={["p-8", "weather-section"]}>
        <Gtk.Label
          cssClasses={["caption", "weather-section-label"]}
          label="5-Day Forecast"
          halign={Gtk.Align.START}
        />
        <Gtk.Box spacing={8} hexpand homogeneous>
          {dailyForecast.as((days) =>
            days.map((d) => (
              <Gtk.Box
                orientation={Gtk.Orientation.VERTICAL}
                cssClasses={["weather-daily-item"]}
                spacing={2}
              >
                <Gtk.Label cssClasses={["caption"]} label={d.dayName} />
                <Gtk.Image iconName={d.iconName} pixelSize={18} />
                <Gtk.Label
                  label={`${formatTemp(d.tempMax)} / ${formatTemp(d.tempMin)}`}
                  cssClasses={["weather-temp-small"]}
                />
              </Gtk.Box>
            )),
          )}
        </Gtk.Box>
      </Gtk.Box>

      {/* ── Detail Cards ── */}
      <Gtk.Box
        orientation={Gtk.Orientation.VERTICAL}
        cssClasses={["p-8", "weather-section"]}
      >
        <Gtk.Label
          cssClasses={["caption", "weather-section-label"]}
          label="Details"
          halign={Gtk.Align.START}
        />
        <Gtk.Box spacing={6} hexpand>
          {/* Wind */}
          <Gtk.Box
            orientation={Gtk.Orientation.VERTICAL}
            cssClasses={["weather-detail-card"]}
            hexpand
          >
            <Gtk.Image iconName="weather-windy-symbolic" pixelSize={16} />
            <Gtk.Label
              label={windSpeed.as((s) => `${s.toFixed(0)} km/h`)}
              cssClasses={["weather-detail-value"]}
            />
            <Gtk.Label
              label={windDir.as((d) => windDirectionLabel(d))}
              cssClasses={["caption"]}
            />
          </Gtk.Box>
          {/* Humidity */}
          <Gtk.Box
            orientation={Gtk.Orientation.VERTICAL}
            cssClasses={["weather-detail-card"]}
            hexpand
          >
            <Gtk.Image iconName="weather-temp-symbolic" pixelSize={16} />
            <Gtk.Label
              label={humidity.as((h) => `${h.toFixed(0)}%`)}
              cssClasses={["weather-detail-value"]}
            />
            <Gtk.Label label="Humidity" cssClasses={["caption"]} />
          </Gtk.Box>
          {/* Pressure */}
          <Gtk.Box
            orientation={Gtk.Orientation.VERTICAL}
            cssClasses={["weather-detail-card"]}
            hexpand
          >
            <Gtk.Image iconName="weather-temp-symbolic" pixelSize={16} />
            <Gtk.Label
              label={pressure.as((p) => `${p.toFixed(0)} hPa`)}
              cssClasses={["weather-detail-value"]}
            />
            <Gtk.Label label="Pressure" cssClasses={["caption"]} />
          </Gtk.Box>
        </Gtk.Box>
      </Gtk.Box>

      {/* ── Refresh Button ── */}
      <Gtk.Button
        onClicked={() => weather.info.update()}
        iconName="view-refresh-symbolic"
        cssClasses={["flat", "weather-refresh"]}
      />
    </Gtk.Box>
  )
}
```

**Important GJS caveat:** The `forecasts.map(...)` inside the Gnim `as()` callback will need to handle the `GWeather.Info` objects from the GSList correctly. Each item's getters are standard GObject method calls and should work.

**Note:** If `<For>` is needed instead of `.map()`, use the `<For>` component from Gnim. Check how other widgets iterate — the `expander` doesn't use `<For>`, but `apList.tsx` does. For simplicity, use `.map()` inside `as()` as shown above. If runtime errors occur, switch to `<For>`.

**Acceptance:** Weather popover shows header, sun arc, hourly row, 5-day row, 3 detail cards, and refresh button. All values update reactively when weather data refreshes.

---

### Step 5: Update bar popover `src/widget/bar/weather.tsx`

**Purpose:** Widen the bar weather popover to accommodate the richer layout. Currently uses `Gtk.Popover` with `popover-padded-lg`.

**Changes:**

```tsx
import Weather from "#/lib/weather"
import Gdk from "gi://Gdk?version=4.0"
import Gtk from "gi://Gtk?version=4.0"
import { Accessor, createBinding } from "gnim"
import { usePopoverCleanup } from "#/widget/common/popoverCleanup"
import { WeatherWidget } from "#/widget/common/weatherWidget"
import GWeather from "gi://GWeather?version=4.0"

export const WeatherButton = ({
  vertical,
  visible = true,
}: {
  vertical: Accessor<boolean>
  visible?: boolean | Accessor<boolean>
}) => {
  const weather = createBinding(Weather.get_default(), "info")

  return (
    <Gtk.MenuButton
      direction={vertical.as((v) =>
        v ? Gtk.ArrowType.RIGHT : Gtk.ArrowType.UP,
      )}
      cursor={Gdk.Cursor.new_from_name("pointer", null)}
      visible={visible}
      $={usePopoverCleanup}
      popover={
        (
          <Gtk.Popover
            valign={Gtk.Align.CENTER}
            halign={Gtk.Align.CENTER}
            cssClasses={[]}
            hasArrow={false}
            widthRequest={320}      // ← NEW: wider popover
          >
            <Gtk.Box cssClasses={[]}>   {/* ← REMOVED popover-padded-lg */}
              <WeatherWidget />
            </Gtk.Box>
          </Gtk.Popover>
        ) as Gtk.Popover
      }
    >
      <Gtk.Box
        orientation={vertical.as((v) =>
          v ? Gtk.Orientation.VERTICAL : Gtk.Orientation.HORIZONTAL,
        )}
        spacing={4}
      >
        <Gtk.Image
          pixelSize={22}
          iconName={weather.as((w) => w?.get_icon_name() ?? "")}
        />
        <Gtk.Label
          cssClasses={["heading"]}
          label={weather.as((w) =>
            w
              ? w
                  .get_value_temp(GWeather.TemperatureUnit.CENTIGRADE)[1]
                  .toFixed() + "°C"
              : "",
          )}
        />
      </Gtk.Box>
    </Gtk.MenuButton>
  )
}
```

**Changes from current:**
- Add `widthRequest={320}` to the popover
- Remove `popover-padded-lg` css class (the widget now handles its own padding)

**Acceptance:** Bar weather popover is 320px wide, showing the full weather widget.

---

### Step 6: Update QS expander weather `src/widget/quicksettings/expander/weather.tsx`

**Purpose:** Use the new `WeatherWidget` in the QS expander section.

**Changes:**

```tsx
import Gtk from "gi://Gtk?version=4.0"
import { WeatherWidget } from "#/widget/common/weatherWidget"

export const Weather = () => {
  return (
    <Gtk.Box
      cssClasses={["card", "p-12"]}
      orientation={Gtk.Orientation.VERTICAL}
    >
      <Gtk.Label
        cssClasses={["title-3"]}
        label={"Weather"}
        halign={Gtk.Align.CENTER}
      />
      <WeatherWidget />
    </Gtk.Box>
  )
}
```

Just remove the duplicate, unused import and let it use the new `WeatherWidget`.

**Acceptance:** QS expander shows the upgraded weather widget inside a card.

---

### Step 7: Add CSS classes to `src/shade.css`

**Purpose:** Styling for weather gradient backgrounds, detail cards, hourly/daily items.

```css
/* ═══════════════════════════════════════════════════════════════════════════
   WEATHER WIDGET
   ═══════════════════════════════════════════════════════════════════════════ */

.weather-widget {
  border-radius: 12px;
  min-width: 280px;
}

.weather-temp {
  font-size: 2em;
  font-weight: 700;
}

.weather-temp-small {
  font-size: 0.8em;
}

.weather-section {
  border-top: 1px solid alpha(var(--window-fg-color), 0.1);
}

.weather-section-label {
  margin-bottom: 4px;
  opacity: 0.7;
}

.weather-hourly-item {
  min-width: 48px;
  padding: 4px 8px;
  background: alpha(var(--window-fg-color), 0.05);
  border-radius: 8px;
}

.weather-daily-item {
  padding: 4px 8px;
  background: alpha(var(--window-fg-color), 0.05);
  border-radius: 8px;
}

.weather-detail-card {
  padding: 8px;
  background: alpha(var(--window-fg-color), 0.06);
  border-radius: 8px;
}

.weather-detail-value {
  font-weight: 600;
  font-size: 1em;
}

.weather-refresh {
  margin: 4px;
}
```

**Acceptance:** Weather sections are visually separated, detail cards have rounded backgrounds, forecast items are compact pill-like containers.

---

### Step 8: Update backlog status

**Purpose:** Mark the weather upgrade as `[WIP]` in the plan doc.

**Change in `quicksettings-and-widgets-plan.md`:**
Under `## Summary`, change Phase 3 row:
```
| 3. Weather upgrade | ~250 lines | `weatherUtils.ts`, `weather.ts`, `sunArc.tsx`, `weatherWidget.tsx`, `weather.tsx`, `shade.css` | ✅ Ready, implementation in progress |
```

And in the `## Phase 3` section header:
```
- **Status:** `[WIP]`
```

---

## Build Order & Dependencies

```
Step 1 (weatherUtils.ts) ─► Step 2 (weather.ts helpers)
                                      │
                                      ▼
                               Step 3 (sunArc.tsx)
                                      │
                                      ▼
                               Step 4 (weatherWidget.tsx)
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                    Step 5 (bar popover)    Step 6 (QS expander)
                          │
                          ▼
                     Step 7 (CSS) ─► Step 8 (docs)
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `w?.is_valid()` is false | Show "--°" for temp, "—" for location, hide forecast sections |
| `get_forecast_list()` returns null | Hourly/daily sections show empty state |
| Sun arc with `now` before sunrise | Show "Next sunrise: HH:MM", draw dim arc |
| Sun arc with `now` after sunset | Show "Next sunrise: HH:MM", draw dim arc, dim sun dot |
| Single timezone / no DST | GWeather handles all normalization internally |
| Very cold temps (-20°C) | `formatTemp` handles negative numbers correctly |
| Widget in QS vs bar popover | Same `WeatherWidget` reused in both; bar has `widthRequest:320` |
| Refresh button during update | Calls `weather.info.update()` — GWeather batches updates internally |

## Testing

Since the project has no automated test framework, verify via NixOS VM:

```bash
# After build:
nix run .#nixosConfigurations.vm...

# In VM, open bar weather popover and QS weather expander
# Verify:
# 1. Gradient background matches current conditions
# 2. Sunrise/sunset arc shows correct times
# 3. Sun dot position updates with time
# 4. Hourly forecast shows next 8 hours
# 5. Daily forecast shows 5 days
# 6. Detail cards show wind/humidity/pressure
# 7. Refresh button triggers update
# 8. All sections handle null/loading states
```

Check journalctl for errors:
```bash
journalctl --user _COMM=shade-shell --boot 0 -n 100 --no-pager | grep -iE "weather|cairo|drawing|error"
```
