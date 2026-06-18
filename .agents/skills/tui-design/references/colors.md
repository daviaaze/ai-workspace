# Textual Colors Reference

## Built-in ANSI Colors (Textual 8.x)

These are the ONLY `$`-prefixed color names that work in Textual 8.x CSS:

| Token | Typical RGB | Usage |
|-------|------------|-------|
| `$text` | `#e0e0e0` (dark) / `#1e1e1e` (light) | Primary text |
| `$text` 40% | Dimmed text (CSS only) | Secondary text |
| `$primary` | `#0178d4` | Primary accent |
| `$secondary` | `#9269fb` | Secondary accent |
| `$accent` | `#ff6a13` | Highlight/accent |
| `$error` | `#e53935` | Errors, destructive actions |
| `$warning` | `#ff9100` | Warnings |
| `$success` | `#43a047` | Success states |
| `$background` | `#1e1e1e` (dark) / `#f5f5f5` (light) | Page background |
| `$surface` | `#252525` (dark) / `#ffffff` (light) | Card/panel background |
| `$panel` | `#2d2d2d` (dark) / `#ededed` (light) | Inset panel |
| `$boost` | `#333333` (dark) / `#e0e0e0` (light) | Elevated surface |

## What Does NOT Exist

These DO NOT work — they will crash with `ColorParseError`:
- `$text-muted`
- `$text-disabled`
- `$dimmed`
- `$subtle`
- `$secondary-text`

## Opacity in CSS vs Python

### CSS (works):
```css
color: $text 40%;        /* ✅ 40% opacity */
background: $primary 20%; /* ✅ 20% opacity tint */
border: solid $error 50%; /* ✅ semi-transparent border */
```

### Python (does NOT work):
```python
widget.styles.color = "$text 40%"  # ❌ CRASHES
widget.styles.background = "$primary 20%"  # ❌ CRASHES
```

### Python (works):
```python
widget.styles.color = "#888888"           # hex
widget.styles.color = "grey"              # color name
widget.styles.color = "rgb(128,128,128)"  # rgb
widget.styles.color = "rgba(255,0,0,0.5)" # rgba
```

## Color Names (Python styles.color)

These English color names work in `widget.styles.color`:
- `"black"`, `"white"`, `"red"`, `"green"`, `"blue"`
- `"yellow"`, `"cyan"`, `"magenta"`, `"grey"`, `"gray"`
- `"darkred"`, `"darkgreen"`, `"darkblue"`
- `"orange"`, `"purple"`, `"pink"`, `"brown"`

## ANSI Color Numbers

Use ANSI color numbers for precise control:
```python
widget.styles.color = "ansi_245"  # Grey from 256-color palette
widget.styles.background = "ansi_17"  # Dark blue
```
