# Design Tokens Reference

Complete design token scales for building consistent UIs. Use these as a starting point — customize for your brand.

## Color Scales

### Neutral (Slate)
| Token | Hex | Tailwind | Use |
|-------|-----|----------|-----|
| neutral-50 | #f8fafc | slate-50 | Page background (light) |
| neutral-100 | #f1f5f9 | slate-100 | Surface background |
| neutral-200 | #e2e8f0 | slate-200 | Border (light mode) |
| neutral-300 | #cbd5e1 | slate-300 | Disabled border |
| neutral-400 | #94a3b8 | slate-400 | Muted text (dark mode) |
| neutral-500 | #64748b | slate-500 | Muted text (light mode) |
| neutral-600 | #475569 | slate-600 | Secondary text |
| neutral-700 | #334155 | slate-700 | Secondary hover |
| neutral-800 | #1e293b | slate-800 | Border (dark mode) |
| neutral-900 | #0f172a | slate-900 | Text (light mode), surface (dark) |
| neutral-950 | #020617 | slate-950 | Page background (dark) |

### Primary (Blue)
| Token | Hex | Tailwind | Use |
|-------|-----|----------|-----|
| primary-50 | #eff6ff | blue-50 | Primary bg (light) |
| primary-100 | #dbeafe | blue-100 | Primary hover (light) |
| primary-500 | #3b82f6 | blue-500 | Primary accent |
| primary-600 | #2563eb | blue-600 | Primary button bg |
| primary-700 | #1d4ed8 | blue-700 | Primary button hover |
| primary-900 | #1e3a5f | blue-900 | Text on light primary |

### Semantic Colors
| Token | Light | Dark | Use |
|-------|-------|------|-----|
| success | green-600 (#16a34a) | green-500 (#22c55e) | Positive, success, completed |
| warning | amber-500 (#f59e0b) | amber-400 (#fbbf24) | Attention, pending |
| error | red-600 (#dc2626) | red-500 (#ef4444) | Delete, error, critical |
| info | blue-500 (#3b82f6) | blue-400 (#60a5fa) | Information, neutral |

## Spacing Scale

Based on 4px base unit:

| Token | Value | Tailwind | Use |
|-------|-------|----------|-----|
| xs | 4px | p-1 / gap-1 | Icon padding, tight groups |
| sm | 8px | p-2 / gap-2 | Input padding, card padding (compact) |
| md | 16px | p-4 / gap-4 | Card padding, section gap |
| lg | 24px | p-6 / gap-6 | Page section margin |
| xl | 32px | p-8 / gap-8 | Major section break |
| 2xl | 48px | p-12 / gap-12 | Hero spacing |
| 3xl | 64px | p-16 | Page-level padding |

## Typography Scale

| Token | Size | Line Height | Tailwind | Use |
|-------|------|-------------|----------|-----|
| xs | 12px | 1rem (16px) | text-xs | Caption, helper text |
| sm | 14px | 1.25rem (20px) | text-sm | Secondary text, labels |
| base | 16px | 1.5rem (24px) | text-base | Body text |
| lg | 18px | 1.75rem (28px) | text-lg | Subheading |
| xl | 20px | 1.75rem (28px) | text-xl | Card title |
| 2xl | 24px | 2rem (32px) | text-2xl | Section title |
| 3xl | 30px | 2.25rem (36px) | text-3xl | Page title |
| 4xl | 36px | 2.5rem (40px) | text-4xl | Hero heading |

### Font Weights
| Weight | Tailwind | Use |
|--------|----------|-----|
| Regular (400) | font-normal | Body text |
| Medium (500) | font-medium | Emphasis, labels |
| Semibold (600) | font-semibold | Subheadings, card titles |
| Bold (700) | font-bold | Headings, CTAs |

## Border Radius

| Token | Value | Tailwind | Use |
|-------|-------|----------|-----|
| none | 0 | rounded-none | Tables, sharp containers |
| sm | 4px | rounded-sm | Inputs, small buttons |
| md | 6px | rounded-md | Cards, modals |
| lg | 8px | rounded-lg | Large cards, dialogs |
| xl | 12px | rounded-xl | Hero cards |
| full | 9999px | rounded-full | Avatars, pills, badges |

## Shadows

### Light Mode
| Token | Value | Tailwind | Use |
|-------|-------|----------|-----|
| none | none | shadow-none | Flat surfaces |
| sm | 0 1px 2px rgba(0,0,0,0.05) | shadow-sm | Subtle elevation |
| md | 0 4px 6px rgba(0,0,0,0.07) | shadow-md | Cards, dropdowns |
| lg | 0 10px 15px rgba(0,0,0,0.1) | shadow-lg | Modals |
| xl | 0 20px 25px rgba(0,0,0,0.1) | shadow-xl | Top-level modals |

### Dark Mode (colored shadows on dark bg)
Use `dark:shadow-*` with slightly colored shadows:
- `dark:shadow-[0_4px_6px_rgba(0,0,0,0.3)]`

## Transitions

| Token | Value | Tailwind | Use |
|-------|-------|----------|-----|
| fast | 100ms | duration-100 | Hover color change |
| normal | 150ms | duration-150 | Opacity, border, shadow |
| slow | 300ms | duration-300 | Modal open/close, expand |
| x-slow | 500ms | duration-500 | Page transitions |

Default easing: `ease-in-out` for most transitions, `ease-out` for appearing elements, `ease-in` for disappearing.

## Z-Index Scale

| Token | Value | Use |
|-------|-------|-----|
| base | 0 | Default |
| dropdown | 10 | Dropdown menus, autocomplete |
| sticky | 20 | Sticky headers |
| overlay | 30 | Modals, drawers, sheets |
| popover | 40 | Tooltips, popovers |
| toast | 50 | Toast notifications |
| debug | 100 | Dev overlays |

## Tailwind Config Extension

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        // Add brand colors that extend Tailwind's defaults
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
      spacing: {
        '18': '4.5rem',   // 72px — if needed
        '88': '22rem',    // 352px — if needed
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.75rem' }],  // 10px
      },
    },
  },
};
```

## CSS Custom Properties (Design Tokens as CSS vars)

```css
:root {
  /* Colors */
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-text: #ffffff;
  --color-secondary: #475569;
  --color-background: #f8fafc;
  --color-surface: #ffffff;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-border: #e2e8f0;
  --color-success: #16a34a;
  --color-warning: #f59e0b;
  --color-error: #dc2626;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* Border radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);

  /* Transitions */
  --transition-fast: 100ms ease-in-out;
  --transition-normal: 150ms ease-in-out;
  --transition-slow: 300ms ease-in-out;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
  :root {
    --color-background: #020617;
    --color-surface: #0f172a;
    --color-text: #f1f5f9;
    --color-text-muted: #94a3b8;
    --color-border: #1e293b;
  }
}
```
