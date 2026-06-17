---
name: ui-design
description: Systematic UI/UX design workflow from requirements through wireframes to implementation. Use when the user asks to design a UI, build a frontend, create a dashboard, style a page, design a component, review UX, or implement a design system.
compatibility: Requires aiw MCP server for browser-based design review and component library lookup. Works standalone for text-based design work.
metadata:
  phases: research, wireframe, component-design, implementation, review
  tools: html, css, react, tailwind, shadcn, streamlit, textual
---

# UI Design Workflow

A systematic process for designing and implementing user interfaces, from requirements gathering to production-ready code. Covers web (React/Tailwind/shadcn), Python (Streamlit/Textual TUI), and design system creation.

## When to Use

- User asks to "design a UI", "build a dashboard", "create a page"
- User says "style this", "make it look better", "improve UX"
- User wants a design system or component library
- User asks to "review the UI", "audit accessibility"
- User needs frontend code generated from a description

## Quick Reference

| Phase | Duration | Output |
|-------|----------|--------|
| [Phase 1: Understand](#phase-1-understand) | 3-5 min | Requirements doc, user flows |
| [Phase 2: Design](#phase-2-design) | 5-10 min | Wireframes, component tree, style guide |
| [Phase 3: Component Design](#phase-3-component-design) | 10-20 min | Component specs, states, accessibility |
| [Phase 4: Implement](#phase-4-implement) | 15-30 min | Production code |
| [Phase 5: Review](#phase-5-review) | 5 min | Accessibility audit, responsive check |

---

## Phase 1: Understand

### 1.1 Gather Requirements

Ask these questions before designing anything:

- **What is the user trying to accomplish?** (Jobs-to-be-done, not feature list)
- **Who is the user?** (Role, technical level, frequency of use)
- **What device/context?** (Desktop, mobile, tablet, terminal, embedded)
- **What's the data?** (What information is shown? Real-time? Historical?)
- **What are the actions?** (CRUD, search, navigate, configure, monitor)
- **Are there constraints?** (Brand colors, existing design system, framework, performance)

### 1.2 Map User Flows

```
Entry → Step 1 → Step 2 → ... → Goal
         ↓
      Edge case → Recovery path
```

Document the primary flow and note:
- Error states
- Empty states
- Loading states
- Edge cases (first use, power user, accessibility)

### 1.3 Check Existing Context

```bash
# Search knowledge base for past UI work
aiw kb search "UI design dashboard" --limit 5

# Check if a design system exists
find . -name "tailwind.config.*" -o -name "theme.*" -o -name "design-system.*" 2>/dev/null
```

Read any existing design system docs. See [references/design-systems.md](references/design-systems.md) for common patterns.

---

## Phase 2: Design

### 2.1 Choose the Stack

Based on requirements from Phase 1:

| Use Case | Recommended Stack |
|----------|-------------------|
| Web dashboard (data-heavy) | React + Tailwind + shadcn/ui + recharts |
| Web app (forms, CRUD) | React + Tailwind + shadcn/ui + react-hook-form |
| Landing / marketing page | HTML + Tailwind CSS |
| Python dashboard | Streamlit + plotly |
| Terminal UI | Textual (Python) |
| Prototype / demo | HTML + Tailwind (fastest to iterate) |
| Existing codebase | Match existing stack |

### 2.2 Create Wireframe (Text or ASCII)

For quick communication, use ASCII wireframes:

```
┌─────────────────────────────────────────────┐
│  🔍 Search...                    [⚙️ Settings] │  ← Header
├───────────┬─────────────────────────────────┤
│           │                                 │
│  Nav      │         Main Content            │
│  Item 1   │                                 │
│  Item 2   │  ┌─────────┐ ┌─────────┐       │
│  Item 3   │  │ Card 1  │ │ Card 2  │       │
│           │  └─────────┘ └─────────┘       │
│           │                                 │
│           │  ┌─────────────────────────┐    │
│           │  │    Table / Chart        │    │
│           │  └─────────────────────────┘    │
├───────────┴─────────────────────────────────┤
│  Status bar                          v1.0   │  ← Footer
└─────────────────────────────────────────────┘
```

### 2.3 Define Component Tree

```
Page
├── Header
│   ├── SearchBar
│   └── SettingsButton
├── Sidebar
│   └── NavMenu
│       └── NavItem[] (repeating)
├── MainContent
│   ├── StatsRow
│   │   └── StatCard[] (repeating)
│   └── DataTable
│       ├── TableHeader
│       ├── TableRow[] (repeating)
│       └── Pagination
└── Footer
```

### 2.4 Establish Visual Language

Use the [references/design-tokens.md](references/design-tokens.md) checklist to define:

- **Colors**: Primary, secondary, accent, neutral, success, warning, error
- **Typography**: Font family, scale (text-xs → text-4xl), weights
- **Spacing**: Base unit (4px), scale (xs/sm/md/lg/xl/2xl)
- **Border radius**: none, sm, md, lg, full
- **Shadows**: none, sm, md, lg, xl
- **Dark mode**: Color mappings for each token

If using Tailwind, design tokens map directly to `tailwind.config.*` extensions.

---

## Phase 3: Component Design

### 3.1 Component Spec Format

For each component, document:

```
Component: StatCard
Purpose: Display a single KPI metric with trend indicator
---

States:
  - loading: Skeleton pulse
  - loaded:  Value + label + trend arrow
  - error:   "Failed to load" with retry button
  - empty:   "No data" with illustration

Props:
  - label: string
  - value: number | string
  - trend?: "up" | "down" | "neutral"
  - changePercent?: number
  - loading?: boolean
  - error?: string

Accessibility:
  - Role: region (or article if standalone)
  - aria-label: "{label}: {value}"
  - Color contrast: 4.5:1 minimum on text
  - Focus: Not interactive (no tab stop)

Variants:
  - default: Light background, dark text
  - compact: Smaller padding, smaller font
  - emphasis: Accent color background
```

### 3.2 Accessibility Checklist (per component)

From [references/accessibility.md](references/accessibility.md):

- [ ] Semantic HTML (`<button>`, not `<div onclick>`)
- [ ] Keyboard navigation (Tab, Enter, Escape, Arrow keys)
- [ ] Focus indicators (visible outline, logical order)
- [ ] Screen reader labels (`aria-label`, `aria-describedby`)
- [ ] Color contrast ≥ 4.5:1 (text) / 3:1 (large text)
- [ ] Not color-only (icons, patterns, text alongside color)
- [ ] Reduced motion (`prefers-reduced-motion`)
- [ ] Touch targets ≥ 44×44px (mobile)
- [ ] Form labels and error messages connected via `aria-describedby`

### 3.3 Responsive Design Strategy

| Breakpoint | Width | Typical Layout |
|------------|-------|----------------|
| Mobile | < 640px | Single column, hamburger nav, stacked cards |
| Tablet | 640-1024px | 2-column, collapsible sidebar |
| Desktop | > 1024px | Full layout, persistent sidebar, 3-4 column grids |

For each page, note which components change at each breakpoint and how.

Use Tailwind breakpoints: `sm:` (640), `md:` (768), `lg:` (1024), `xl:` (1280), `2xl:` (1536).

---

## Phase 4: Implement

### 4.1 Implementation Principles

1. **Semantic HTML first** — Use correct elements, then style
2. **Mobile-first CSS** — Base styles for mobile, `md:` / `lg:` for larger
3. **Component isolation** — Each component is self-contained with its states
4. **Progressive enhancement** — Core functionality works without JS, JS enhances
5. **Design tokens as the source of truth** — Colors/spacing from config, not hardcoded
6. **Test with real content** — Long names, edge-case numbers, empty states

### 4.2 Implementation Order

1. **Layout shell** — Header, sidebar, footer, main area (no content)
2. **Component stubs** — Skeleton/loading versions of each component
3. **One component at a time** — Full implementation with all states
4. **Wire up data** — Connect to API/mock data
5. **Polish** — Animations, transitions, micro-interactions
6. **Review** — Run through Phase 5 checklist

### 4.3 Code Generation Patterns

#### Tailwind + React (shadcn/ui)

```tsx
// Use shadcn/ui components as building blocks
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatCardProps {
  label: string;
  value: number | string;
  trend?: "up" | "down" | "neutral";
  loading?: boolean;
}

export function StatCard({ label, value, trend, loading }: StatCardProps) {
  if (loading) return <Skeleton className="h-24 w-full" />;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <p className={cn(
            "text-xs mt-1",
            trend === "up" && "text-green-600",
            trend === "down" && "text-red-600",
          )}>
            {trend === "up" ? "↑" : "↓"} from last period
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

#### Streamlit (Python)

```python
import streamlit as st

def stat_card(label: str, value, trend: str | None = None, key: str = ""):
    """Render a KPI stat card in Streamlit."""
    with st.container(border=True, key=key):
        st.metric(
            label=label,
            value=value,
            delta=f"{trend} from last period" if trend else None,
        )
```

#### Textual TUI (Python)

```python
from textual.widgets import Static
from textual.containers import Horizontal, Vertical

class StatCard(Vertical):
    """A KPI stat card for terminal dashboards."""

    def compose(self):
        yield Static("Loading...", id="label")
        yield Static("--", id="value")
        yield Static("", id="trend")

    def update(self, label: str, value: str, trend: str = ""):
        self.query_one("#label").update(label)
        self.query_one("#value").update(value)
        if trend:
            self.query_one("#trend").update(f"{'↑' if 'up' in trend else '↓'} {trend}")
```

### 4.4 Use the MCP Tools

When the aiw MCP server is active, leverage these tools:

```
search_knowledge → Find past UI patterns and design decisions
read_file        → Check existing components for consistency
write_file       → Create new component files
run_shell        → Run linters (eslint, prettier, ruff)
run_tests        → Run component tests
```

---

## Phase 5: Review

### 5.1 Self-Review Checklist

- [ ] Every component has loading, empty, error, and loaded states
- [ ] Keyboard navigation works (Tab through the page without a mouse)
- [ ] Screen reader announces content correctly (use VoiceOver/NVDA)
- [ ] All text meets 4.5:1 contrast ratio
- [ ] Responsive at mobile, tablet, and desktop widths
- [ ] No layout shift on data load (use skeletons/fixed dimensions)
- [ ] Touch targets ≥ 44×44px on mobile
- [ ] Forms have labels, error messages, and validation states
- [ ] Focus order is logical and visible
- [ ] Dark mode works (if implemented)
- [ ] Motion respects `prefers-reduced-motion`
- [ ] No hardcoded colors/spacing (use design tokens)
- [ ] Components match the existing codebase style

### 5.2 Accessibility Audit Commands

```bash
# Check color contrast
npx axe-cli https://localhost:3000  # or use axe DevTools browser extension

# Lighthouse audit
npx lighthouse https://localhost:3000 --view

# ESLint accessibility rules
npx eslint --ext .tsx --rule 'jsx-a11y/alt-text: error' src/
```

### 5.3 Visual Review

- Take screenshots at 3 breakpoints (320px, 768px, 1440px)
- Compare with wireframes from Phase 2
- Check with real data — long names, large numbers, empty states
- Test with browser zoom at 200%
- Verify dark mode (toggle OS setting)

---

## Design Tokens Reference

For detailed token scales, see [references/design-tokens.md](references/design-tokens.md).

Quick color palette generator:

```
Primary:    Blue-600  (#2563eb)  →  hover: Blue-700, text-on-primary: white
Secondary:  Slate-600 (#475569)  →  hover: Slate-700
Accent:     Violet-500 (#8b5cf6) →  hover: Violet-600
Success:    Green-600 (#16a34a)
Warning:    Amber-500 (#f59e0b)
Error:      Red-600   (#dc2626)
Background: White / Slate-50 (light), Slate-950 (dark)
Surface:    White / Slate-100 (light), Slate-900 (dark)
Text:       Slate-900 (light), Slate-100 (dark)
Muted:      Slate-500 (light), Slate-400 (dark)
Border:     Slate-200 (light), Slate-800 (dark)
```

---

## Quick Recipes

### Dashboard
```
Phase 1 → Identify 3-5 KPIs, define filters, note refresh rate
Phase 2 → StatsRow + FilterBar + ChartArea + DataTable
Phase 3 → StatCard, FilterDropdown, TimeSeriesChart, PaginatedTable
Phase 4 → shadcn/ui Card + recharts + @tanstack/react-table
```

### Form Page
```
Phase 1 → List all fields, validation rules, multi-step or single-page
Phase 2 → FormLayout + SectionGroup + FieldRow + ActionBar
Phase 3 → TextInput, Select, DatePicker, Toggle, SubmitButton
Phase 4 → react-hook-form + zod + shadcn/ui Form components
```

### Settings Page
```
Phase 1 → Group settings by category, note defaults, permissions
Phase 2 → SettingsLayout + CategoryNav + SettingsGroup + SaveBar
Phase 3 → SettingsGroup, ToggleSetting, SelectSetting, InputSetting
Phase 4 → shadcn/ui + react-hook-form with dirty-state tracking
```

### Data Table
```
Phase 1 → Columns, sort/filter/search, pagination, row actions
Phase 2 → TableToolbar + DataTable + Pagination
Phase 3 → TableHeader (sortable), TableRow, TableCell, PaginationBar
Phase 4 → @tanstack/react-table + shadcn/ui Table
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Layout shifts on load" | Fix dimensions with skeletons or `min-h-*` classes |
| "Colors look off in dark mode" | Check `dark:` prefix on all color classes |
| "Component doesn't match rest of app" | Read existing components first (use `find`/`grep`), copy patterns |
| "Mobile layout is broken" | Start with mobile-first base styles, add `md:` breakpoints up |
| "Too many props on one component" | Split into sub-components, use composition |
| "Focus outline is missing" | Never use `outline-none` without a replacement focus style |
| "Text overflows on long content" | Use `truncate`, `break-words`, or scroll containers |

---

## Resources

- [Design tokens reference](references/design-tokens.md) — Color scales, spacing, typography
- [Accessibility checklist](references/accessibility.md) — WCAG 2.1 AA compliance
- [Component patterns](references/component-patterns.md) — Common UI patterns and anti-patterns
- [Design systems](references/design-systems.md) — shadcn/ui, Tailwind, Material, Ant
