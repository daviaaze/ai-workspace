# Accessibility Checklist (WCAG 2.1 AA)

Every UI component must pass this checklist before it's considered complete.

## Perceivable

### Text Alternatives
- [ ] Images have meaningful `alt` text (decorative images use `alt=""`)
- [ ] SVG icons have `aria-label` or `<title>` element
- [ ] Charts/graphs have text description or data table alternative
- [ ] Video has captions, audio has transcript

### Adaptable
- [ ] Content has semantic structure (h1→h6 hierarchy, not just bold text)
- [ ] Reading order is logical when CSS is removed
- [ ] Forms use `<label>` elements (not just placeholder text)
- [ ] Tables use `<th>` for headers with `scope="col"` or `scope="row"`

### Distinguishable
- [ ] Text contrast ≥ 4.5:1 against background (3:1 for large text ≥18px bold)
- [ ] UI components contrast ≥ 3:1 against adjacent colors
- [ ] Information is not conveyed by color alone (add icons, text, patterns)
- [ ] Focus indicators are visible (≥ 3:1 contrast, ≥ 2px thick)
- [ ] Text can be resized to 200% without loss of content
- [ ] No images of text except logos

## Operable

### Keyboard Accessible
- [ ] All functionality works with keyboard alone (no mouse required)
- [ ] Tab order is logical (follows visual layout)
- [ ] No keyboard traps (can Tab in AND out of every component)
- [ ] Skip-to-content link at top of page
- [ ] Custom keyboard shortcuts don't conflict with browser/AT shortcuts

### Enough Time
- [ ] No auto-advancing content (or user can pause/stop)
- [ ] Session timeouts have warning and extension option

### Seizures and Physical Reactions
- [ ] No content flashes more than 3 times per second
- [ ] Animations respect `prefers-reduced-motion` media query

### Navigable
- [ ] Page has descriptive `<title>`
- [ ] Multiple ways to find content (nav, search, sitemap for large sites)
- [ ] Current page/section is indicated in navigation
- [ ] Link text is descriptive (not "click here" or "read more")

### Input Modalities
- [ ] Touch targets are ≥ 44×44px (AAA: 44×44px)
- [ ] No reliance on complex gestures (pinch, swipe) without alternatives
- [ ] Pointer cancellation: action fires on pointer-up, not pointer-down (can abort)

## Understandable

### Readable
- [ ] Language declared (`<html lang="en">`)
- [ ] Parts in different language marked (`<span lang="fr">`)

### Predictable
- [ ] Navigation is consistent across pages
- [ ] Components that do the same thing are labeled consistently
- [ ] No unexpected changes of context on focus or input

### Input Assistance
- [ ] Required fields are marked (use `required` + visual indicator, not just color)
- [ ] Labels and instructions are provided
- [ ] Error messages are descriptive (what's wrong + how to fix)
- [ ] Error suggestions are provided where possible
- [ ] Forms prevent errors where possible (input type, constraints, confirmation)
- [ ] Form errors are announced to screen readers (`role="alert"`)

## Robust

### Compatible
- [ ] HTML validates (no duplicate IDs, proper nesting)
- [ ] ARIA roles, states, and properties are valid
- [ ] Name, role, value are computable for all UI components
- [ ] Status messages announced via `aria-live` regions (polite for updates, assertive for errors)

## Quick Testing Script

```bash
# Automated checks
npx axe-cli https://localhost:3000 --stdout
npx pa11y https://localhost:3000

# Manual checks
# 1. Tab through entire page without touching the mouse
# 2. Turn on screen reader (VoiceOver: Cmd+F5, NVDA: free download)
# 3. Zoom browser to 200%
# 4. Turn on high contrast mode in OS settings
# 5. Unplug mouse, navigate by keyboard only
```

## Common ARIA Patterns

### Button (not actually a button)
```html
<div role="button" tabindex="0" aria-pressed="false" onclick="...">Like</div>
```

### Modal Dialog
```html
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Delete</h2>
  <p>Are you sure?</p>
  <button>Cancel</button>
  <button>Delete</button>
</div>
```
**Must trap focus inside modal and restore focus on close.**

### Tab Panel
```html
<div role="tablist" aria-label="Settings">
  <button role="tab" aria-selected="true" aria-controls="panel-1">General</button>
  <button role="tab" aria-selected="false" aria-controls="panel-2">Security</button>
</div>
<div role="tabpanel" id="panel-1" aria-labelledby="tab-1">...</div>
```

### Disclosure (Accordion)
```html
<button aria-expanded="false" aria-controls="section-1">Section 1</button>
<div id="section-1" role="region" hidden>...</div>
```

### Alert (live region)
```html
<div role="alert" aria-live="assertive">Error: Invalid email address</div>
```

### Progress Bar
```html
<div role="progressbar" aria-valuenow="65" aria-valuemin="0" aria-valuemax="100"
     aria-label="Upload progress">65%</div>
```

## Screen Reader Text (visually hidden)

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

## Focus Styles

```css
/* Never do this: */
*:focus { outline: none; }

/* Instead, provide a visible focus style: */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: 2px;
}

/* Or for Tailwind: */
/* Use focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 */
```

## Color Contrast Quick Reference

| Foreground | Background | Ratio | Pass? |
|------------|------------|-------|-------|
| #000000 (black) | #ffffff (white) | 21:1 | ✅ |
| #64748b (slate-500) | #ffffff (white) | 4.6:1 | ✅ (AA text) |
| #94a3b8 (slate-400) | #ffffff (white) | 3.0:1 | ❌ (fails text, passes large text) |
| #2563eb (blue-600) | #ffffff (white) | 4.5:1 | ✅ (just barely) |
| #16a34a (green-600) | #ffffff (white) | 4.5:1 | ✅ (just barely) |
| #dc2626 (red-600) | #ffffff (white) | 4.5:1 | ✅ (just barely) |
| #f59e0b (amber-500) | #ffffff (white) | 2.5:1 | ❌ (never use amber on white) |
| #ffffff (white) | #2563eb (blue-600) | 4.5:1 | ✅ |

**Rule of thumb:** At Tailwind's default 600 shade level, most colors barely pass 4.5:1 on white. For text smaller than 18px, bump to 700 shade for safety, especially for red and green.
