# Component Patterns

Common UI patterns and their implementation approaches across different stacks.

## Pattern Catalog

### 1. Data Display

#### Stat Card (KPI)
```
Purpose: Display a single metric with label, value, and trend
States: loading | loaded | error | empty
```

**Tailwind/React:**
```tsx
<div className="rounded-lg border bg-card p-6">
  <p className="text-sm font-medium text-muted-foreground">{label}</p>
  <p className="text-2xl font-bold mt-1">{value}</p>
  {trend && <TrendBadge direction={trend} value={changePercent} />}
</div>
```

**Streamlit:**
```python
st.metric(label=label, value=value, delta=delta_str)
```

#### Data Table
```
Purpose: Display rows of structured data with sort, filter, pagination
States: loading (skeleton rows) | loaded | empty ("No results") | error
Anti-pattern: Horizontal scroll for >5 columns on mobile — use card layout instead
```

**Key decisions:**
- Client-side vs server-side pagination
- Fixed columns or responsive collapse
- Row selection: checkbox, click, or none
- Inline editing vs modal editing

#### Empty State
```
Purpose: Show when there's no data, with helpful guidance
Must include: Illustration/icon, title, description, CTA button
```

```tsx
<div className="flex flex-col items-center justify-center py-12 text-center">
  <InboxIcon className="h-12 w-12 text-muted-foreground/50" />
  <h3 className="mt-4 text-lg font-semibold">No items yet</h3>
  <p className="mt-1 text-sm text-muted-foreground">
    Get started by creating your first item.
  </p>
  <Button className="mt-4">Create Item</Button>
</div>
```

### 2. Forms

#### Form Layout Principles
- Single column for most forms (faster scanning)
- Group related fields in sections
- Labels ABOVE inputs (faster completion)
- Required fields marked with asterisk + "(required)" text
- Submit button aligned with input left edge
- Placeholders are supplementary hints, not labels

#### Form Validation Pattern
```
1. Validate on blur (field-level errors)
2. Validate on submit (all errors at once)
3. Show inline errors near field (not just toast)
4. Announce errors to screen reader
5. Scroll to first error on submit
6. Disable submit while submitting (prevent double-submit)
```

#### Multi-step Form / Wizard
```
Purpose: Break long forms into sequential steps
Must have: Step indicator, back button, save progress
```

```tsx
const steps = ["Account", "Profile", "Billing", "Confirm"];
// Show: StepIndicator + current step content
// Track: completed steps, current step, dirty state per step
```

### 3. Navigation

#### Sidebar Navigation Pattern
```
Use when: 5-15 navigation items, complex hierarchy
Collapse to: Hamburger menu on mobile (< 768px)
```

```tsx
<aside className="w-64 border-r bg-background">
  <nav>
    {items.map(item =>
      <NavItem key={item.href} icon={item.icon} active={isActive} />
    )}
  </nav>
</aside>
```

#### Top Navigation Pattern
```
Use when: 3-7 items, simple structure
Collapse to: Hamburger menu on mobile
```

#### Breadcrumb Pattern
```
Use when: Deeply nested pages (3+ levels)
Format: Home > Section > Subsection > Current Page
```

#### Tab Navigation Pattern
```
Use when: 2-6 related views within same page
Anti-pattern: Tabs inside tabs — use separate pages
```

### 4. Feedback

#### Toast Notifications
```
Levels: Info (neutral), Success (green), Warning (amber), Error (red)
Position: Bottom-right (desktop), bottom-center (mobile)
Duration: 5s for info/success, persist for errors
Stack: Multiple toasts stack vertically
Action: "Undo" link for destructive actions
```

#### Loading States Hierarchy
1. **Skeleton** (preferred) — Shape placeholder with pulse animation
2. **Spinner** — For indeterminate wait < 2s
3. **Progress bar** — For determinate wait (upload, processing)
4. **Full page loading** — Only for initial app load

#### Confirmation Dialog
```
Use for: Destructive actions (delete, discard changes, logout)
Must have: Title, description, cancel button, confirm button (red for destructive)
Focus trap: Focus should be on cancel button by default
```

### 5. Content Layout

#### Dashboard Grid
```
Desktop: 3-4 columns (cards), 12-column grid for charts
Tablet:  2 columns
Mobile:  1 column, cards stack vertically
```

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  <StatCard />
  <StatCard />
  <ChartCard className="md:col-span-2 lg:col-span-2" />
  <TableCard className="md:col-span-2 lg:col-span-4" />
</div>
```

#### Card Grid
```
Use when: Displaying a collection of similar items (products, articles, profiles)
Pattern: Responsive grid, consistent card height, hover state
```

```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
  {items.map(item => <ItemCard key={item.id} {...item} />)}
</div>
```

#### Split Pane (Master-Detail)
```
Use when: List of items + detail view of selected item
Desktop: Side-by-side (list 30-40% width)
Mobile:  List → tap → detail (full-width, back button)
```

### 6. Common Anti-Patterns

| Anti-Pattern | Why it's bad | Fix |
|-------------|--------------|-----|
| `outline: none` without replacement | Keyboard users can't see focus | Use `focus-visible:ring-2` |
| Placeholder as label | Disappears on input, not read by SR reliably | Always use `<label>` |
| Color-only status indicators | Colorblind users can't distinguish | Add icon + text label |
| Infinite scroll without "load more" | No footer access, no "end" signal | Show "Load more" button or pagination |
| `overflow: hidden` on body for modals | Scroll position lost when modal closes | Use `position: fixed` + preserve scroll |
| Carousel without controls | User can't stop/pause | Add pause button + manual navigation dots |
| Tiny click targets (<44px) | Hard to tap on mobile | min-width/min-height: 44px |
| Dropdown with 50+ items | Can't scan or find items quickly | Add search/filter to dropdown |
| Disabled button with no explanation | User doesn't know why | Show tooltip or help text explaining why |
| `alert()` for errors | Ugly, blocks UI, not dismissible | Inline error messages or toast |
