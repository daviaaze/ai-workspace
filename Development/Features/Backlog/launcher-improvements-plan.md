# Launcher Improvement Plan

> Goal: Transform the applauncher into a multimodal frecency-ranked launcher
> with clipboard history (with images), command execution, and nixpkgs app search.

---

## Phase 1 — Frecency Scorer (Small, additive)

**Files:** `+ src/lib/frecency.ts`, + 3 lines in `appButton.tsx`, + 3 lines in `clipboardButton.tsx`

A simple persistent store (JSON at `~/.cache/shade/frecency.json`) tracking:

```ts
interface FrecencyEntry {
  id: string        // app entry path, clipboard id, or command string
  label: string     // display name
  category: "app" | "clipboard" | "command" | "nixpkgs"
  frequency: number
  lastUsed: number  // unix ms
}
```

Score formula:
```
score = frequency × (2 − e^(−days_since_last_use × 0.3))
```

- Apps less than 1 day old get ~2× boost over frequency alone
- Apps not used in 30 days decay to ~1×
- Ties broken by lastUsed (most recent first)

**Touch points:**
- `appButton.tsx` — replace `application.frequency += 1` with `frecency.record("app", entry, app.name)`
- `clipboardButton.tsx` — add `frecency.record("clipboard", item.id, preview)` on copy
- Launcher `index.tsx` — sort results by frecency score instead of fuzzy match order

---

## Phase 2 — Clipboard with Image Support

**Files:** `src/lib/clipboard.ts`, `src/widget/applauncher/clipboardButton.tsx`

### Changes to `ClipboardItem`

```ts
interface ClipboardItem {
  id: string
  text: string
  mimeType: string         // "text/plain", "image/png", "image/jpeg", etc.
  hasImage: boolean
  timestamp: number
  thumbnailPath?: string   // ~/.cache/shade/clipboard-thumbs/<id>.png
}
```

### Pipeline

1. `getClipboardHistory()` — parse `cliphist list` lines. `cliphist` already stores images and shows them as `[[binary data image/png]]` in the list output. Detect these lines and set `hasImage = true`.

2. On demand — `cliphist decode <id> | convert -resize 200x200 - [thumb_path]` to generate a thumbnail. Cache it.

3. `clipboardButton.tsx` — when `hasImage`, render `<Gtk.Picture file={thumbnailPath}>` instead of the text preview + generic icon.

**cliphist already persists to disk** (`~/.local/share/cliphist/`) — no changes needed for persistence. The only gap is decoding images for display.

---

## Phase 3 — Command Runner

**Files:** `src/widget/applauncher/index.tsx`

Add a third launcher mode triggered by `!` prefix:

```
!cp ~/file.txt ~/backup/
```

### Behavior

| Input | Mode |
|-------|------|
| `text` | App search (frecency-ranked) |
| `>text` | Clipboard search |
| `!command` | Command execution |

### Flow (command mode)

1. User types `!some command`
2. Results area shows a preview of the command being run
3. On `Enter`:
   - Execute via `Process.subprocessv(command.split(" "))` for long-running
   - Or `Process.exec()` for quick commands
4. Show stdout/stderr in a small inline output panel (max 5 lines)
5. Show notification on completion or error

### Bonus

Auto-detect: if the text contains `/`, `.`, or spaces and doesn't match any app, suggest running it as a command even without `!` prefix (like GNOME Alt+F2). This is a stretch goal for Phase 3.

---

## Phase 4 — Nixpkgs App Search

**Files:** `+ src/lib/nixpkgsIndex.ts`, + lines in `index.tsx`

### Pre-generated Index

Generate from nixpkgs:
```bash
nix search nixpkgs "^" --json | \
  python3 filter_top_level.py > ~/.cache/shade/nixpkgs-index.json
```

Result: **3.7 MB**, **24,623 packages**, ~10ms search.

### Launcher Mode

Add a `nix:` prefix:

```
nix:fire    → shows firefox, firefox-esr, firebird, etc.
nix:wez     → shows wezterm
```

### Search

Load the JSON into memory on launcher open (single `JSON.parse`), search `pname` + `description` locally.

### Execution

When user selects a result:
```ts
GLib.spawn_command_line_async(
  `uwsm-app -t service -- nix run nixpkgs#${pname}`
)
```

### Refresh

- Ship with a starter index (generated once, committed or bundled)
- Optional: systemd user timer for weekly refresh
- `launcherUtils refresh-nixpkgs` CLI command

### Fallback

If `nix run` fails (e.g., package has no `mainProgram`), show a brief inline error: "This package has no runnable entry point."

---

## Summary

| Phase | Effort | Key Files | Dependencies |
|-------|--------|-----------|-------------|
| 1. Frecency | ~50 lines | `+frecency.ts`, `appButton.tsx`, `index.tsx` | None |
| 2. Clipboard images | ~80 lines | `clipboard.ts`, `clipboardButton.tsx` | `imagemagick` (for thumbnail resize) |
| 3. Command runner | ~60 lines | `index.tsx` | None |
| 4. Nixpkgs search | ~120 lines | `+nixpkgsIndex.ts`, `index.tsx` | Nix (for `nix run`), pre-built index |
