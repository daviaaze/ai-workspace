# Design Systems Reference

Quick reference for popular design systems and when to use each.

## shadcn/ui (React + Tailwind)

**Best for:** React apps, dashboards, SaaS products
**Philosophy:** Copy-paste components (not a dependency), fully customizable
**URL:** https://ui.shadcn.com

### Setup
```bash
npx shadcn@latest init
# Choose: Tailwind v4, CSS variables, Slate + Blue color scheme

npx shadcn@latest add button card dialog dropdown-menu form input
npx shadcn@latest add select separator sheet skeleton table tabs
npx shadcn@latest add toast toggle tooltip
```

### Key Components

| Component | Use |
|-----------|-----|
| `Card` | Container for grouped content |
| `Dialog` | Modal for confirmations, forms |
| `Sheet` | Slide-out panel (mobile-friendly sidebar) |
| `DropdownMenu` | Context menus, overflow actions |
| `Command` | ⌘K command palette, searchable select |
| `DataTable` | Sortable, filterable, paginated table |
| `Form` | react-hook-form + zod integration |

### Theming
```css
/* globals.css — shadcn/ui uses CSS variables */
:root {
  --background: 0 0% 100%;
  --foreground: 222 47% 11%;
  --primary: 221 83% 53%;
  --primary-foreground: 0 0% 100%;
  --secondary: 210 40% 96%;
  --muted: 210 40% 96%;
  --muted-foreground: 215 16% 47%;
  --border: 214 32% 91%;
  --radius: 0.5rem;  /* 8px */
}
```

## Tailwind CSS Utility Patterns

### Common Layout Classes

```html
<!-- Page container -->
<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

<!-- Card grid -->
<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">

<!-- Flex row with gap -->
<div class="flex items-center gap-2">

<!-- Stack (flex column) -->
<div class="flex flex-col gap-4">

<!-- Two-column layout -->
<div class="flex flex-col lg:flex-row gap-8">
  <aside class="w-full lg:w-64 shrink-0">
  <main class="flex-1 min-w-0">

<!-- Centered content -->
<div class="flex items-center justify-center min-h-screen">

<!-- Truncate text -->
<p class="truncate">
```

### Interactive Element Patterns

```html
<!-- Button variants -->
<button class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50">

<!-- Input -->
<input class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50">

<!-- Badge -->
<span class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold">
```

## Streamlit (Python)

**Best for:** Data dashboards, ML demos, internal tools
**Philosophy:** Python-only, no HTML/CSS needed, rapid iteration

### Layout
```python
import streamlit as st

st.set_page_config(page_title="Dashboard", layout="wide")

# Sidebar
with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Date range")

# Main content - columns
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Revenue", "$12,345", "↑ 12%")
with col2:
    st.metric("Users", "1,234", "↓ 3%")

# Tabs
tab1, tab2 = st.tabs(["Chart", "Table"])
with tab1:
    st.line_chart(data)

# Container with border
with st.container(border=True):
    st.subheader("Section Title")
    st.write("Content")

# Expander
with st.expander("Advanced Settings"):
    st.slider("Threshold", 0, 100, 50)
```

### Custom CSS in Streamlit
```python
st.markdown("""
<style>
  .stMetric { background: #f8fafc; padding: 1rem; border-radius: 8px; }
  .stMetric label { font-size: 0.875rem; color: #64748b; }
</style>
""", unsafe_allow_html=True)
```

## Textual TUI (Python Terminal UI)

**Best for:** Terminal dashboards, CLI tools
**Philosophy:** CSS-like styling for terminal apps

### Basic App Structure
```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Horizontal, Vertical, Grid

class Dashboard(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
    }
    #sidebar {
        width: 30;
        background: $surface;
        border-right: solid $primary;
    }
    StatCard {
        height: 5;
        border: solid $primary;
        padding: 1;
    }
    .metric-value { text-style: bold; color: $accent; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(Static("Nav Item 1"), Static("Nav Item 2"), id="sidebar"),
            Vertical(
                Grid(
                    StatCard("Revenue", "$12,345"),
                    StatCard("Users", "1,234"),
                    StatCard("Churn", "2.3%"),
                    StatCard("NPS", "72"),
                ),
            ),
        )
        yield Footer()
```

### Textual Theme Colors
```
$primary      $secondary    $accent
$background   $surface      $panel
$text         $text-muted   $text-disabled
$success      $warning      $error
```

## Ant Design (React)

**Best for:** Enterprise apps, complex forms, Chinese market
**Philosophy:** Complete design system, opinionated, large bundle

### When to Use
- Enterprise/internal tools with complex table/form requirements
- Teams that want everything out of the box
- Chinese market (excellent i18n)

### When NOT to Use
- Consumer-facing apps (large bundle)
- Designs that deviate significantly from Ant's style
- Projects where bundle size matters (antd is ~200KB+)

## Material UI (React)

**Best for:** Apps following Material Design spec
**Philosophy:** Google's design language, comprehensive

### When to Use
- Android companion apps
- Teams already familiar with Material Design
- Need all components in one library

## Choosing a Design System

```
Start here → Do you already have a design system?
  ├─ Yes → Use it. Don't mix.
  └─ No → What's your stack?
      ├─ React → shadcn/ui (80% of cases)
      ├─ React + enterprise tables/forms → Ant Design
      ├─ React + Material look → MUI
      ├─ Python dashboard → Streamlit
      ├─ Python terminal → Textual
      ├─ Landing page → Tailwind CSS only
      └─ Rapid prototype → HTML + Tailwind
```

## CSS-in-JS vs Tailwind Decision Tree

```
Is bundle size critical?
  ├─ Yes → Tailwind (no runtime JS, ~4KB gzipped after purge)
  └─ No → What do teammates prefer?

Do you ship a component library?
  ├─ Yes → CSS-in-JS (runtime style injection, no build step for consumers)
  └─ No → Tailwind (co-located styles, faster iteration)

Is there tight design system conformance required?
  ├─ Yes → Tailwind (design tokens in config, no escape)
  └─ No → Either works
```
