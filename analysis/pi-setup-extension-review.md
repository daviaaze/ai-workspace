# Pi Setup Extension Review

## Summary
- **Total extensions:** 9
- **Issues found:** 28 (4 Critical / 14 Warning / 10 Info)
- **Estimated token waste per session:** ~1,500–2,500 tokens (one-time startup + per-turn overhead)

### Severity Legend
| Severity | Meaning |
|----------|---------|
| 🔴 Critical | Violates core Pi best practice; causes token waste every session; security risk |
| 🟡 Warning | Notable antipattern, moderate token waste, or maintainability concern |
| ℹ️ Info | Suggestion for improvement; low impact today |

---

## Per-Extension Findings

### 1. `auto-commit.ts`
**Score:** 🟡

**Issues:**
- 🟡 [Warning] **`console.error` on session_shutdown failure** — Line 25 logs `console.error` instead of using `ctx.ui.notify`. This writes to stderr, wasting tokens and not showing in Pi TUI. Official examples never use `console.log`/`console.error`.

**Lines of concern:** 25
**Current code:**
```ts
console.error("[auto-commit] Failed:", err);
```
**Suggested fix:**
```ts
ctx.ui.notify(`[auto-commit] Failed: ${err instanceof Error ? err.message : err}`, "error");
```
**Token impact:** ~50 tokens per failure event (rare, but wastes tokens on error path)

**Correct:**
- ✅ Silent startup — no startup notifications
- ✅ Proper `session_shutdown` lifecycle hook
- ✅ No `isToolCallEventType` needed (not a tool_call handler)
- ✅ Clean working tree check before committing
- ✅ Uses `--no-verify` to skip hooks

---

### 2. `crg-trim.ts`
**Score:** 🟡

**Issues:**
- 🟡 [Warning] **Startup notification on failure** — Lines 282-283 and 289 call `ctx.ui.notify()` in `session_start` handler with warning/error. Official Pi examples never show startup notifications. Startup should be silent; the user discovers unavailability when they try to use a tool.
- 🟡 [Warning] **Import from wrong package** — Lines 11-12 import from `@mariozechner/pi-coding-agent` and `@mariozechner/pi-ai`. All other extensions import from `@earendil-works/pi-coding-agent`. This will cause build failures or type mismatches.
- 🟡 [Warning] **System prompt injection every turn** — Lines 370-403 inject ~300 tokens of graph guidelines into the system prompt on every `before_agent_start` event. This is unnecessary repetition — the guidelines don't change between turns.
- ℹ️ [Info] **No `ctx.hasUI` guard on commands** — Lines 348 and 358 use `ctx.ui.notify()` in command handlers without checking `ctx.hasUI`. Commands are interactive-only, but adding the guard is defensive.
- ℹ️ [Info] **Hardcoded binary paths** — Lines 262-263 hardcode Nix profile paths for binary discovery. This is fragile across distros. The `findExecutable` function is a good pattern but the hardcoded paths could be extracted to a shared utility.

**Lines of concern:** 11-12, 282-283, 289, 370-403
**Current code (lines 11-12):**
```ts
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { StringEnum } from "@mariozechner/pi-ai";
```
**Suggested fix:**
```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { StringEnum } from "@earendil-works/pi-ai";
```

**Current code (lines 282-283):**
```ts
ctx.ui.notify("[crg-trim] code-review-graph not found. Install: pip install code-review-graph", "warning");
```
**Suggested fix:** Remove startup notification. Let the user discover via `/crg-status` command or tool execution errors.

**Token impact:**
- ~300 tokens/turn for repeated system prompt injection (×20 turns = 6,000 tokens per session)
- ~300 tokens for 6 tool registrations in system prompt
- **Total: ~600 tokens per session** (one-time tool registration + per-turn injection)

**Correct:**
- ✅ Proper MCP client implementation with timeout handling
- ✅ `session_shutdown` cleanup
- ✅ `formatResult` with structured `details` return
- ✅ Tool descriptions with `promptSnippet` and `promptGuidelines`
- ✅ Clean `before_agent_start` pattern (despite verbosity)

---

### 3. `git-checkpoint.ts`
**Score:** 🟢

**Issues:**
- ℹ️ [Info] **`tool_result` handler fragility** — Lines 22-28 track `currentEntryId` in a `tool_result` handler. If `tool_result` fires more than once before `turn_start`, only the last entry is tracked. This is a minor race condition.

**Lines of concern:** 22-28
**Current code:**
```ts
pi.on("tool_result", async (_event, ctx) => {
  try {
    const leaf = ctx.sessionManager.getLeafEntry();
    if (leaf) currentEntryId = leaf.id;
  } catch {
    // session manager not available yet
  }
});
```
**Suggested fix:** Consider tracking the entry ID in `before_agent_start` instead (which fires once per turn before the agent starts):
```ts
pi.on("before_agent_start", async (event) => {
  currentEntryId = event.entryId;
});
```

**Token impact:** Minimal — handler does negligible work per tool result

**Correct:**
- ✅ Silent startup — no startup notifications
- ✅ Proper `session_before_fork` lifecycle hook
- ✅ `agent_end` cleanup clears checkpoints
- ✅ `ctx.hasUI` guard on interactive features
- ✅ `ctx.ui.select` and `ctx.ui.notify` proper patterns
- ✅ No `console.log` — clean
- ✅ Working tree check before stashing (debouncing)

---

### 4. `login.ts`
**Score:** 🟢

**Issues:**
- ℹ️ [Info] **`error: any` type annotation** — Line 48 uses `any` type for the caught error. Should use `unknown` to be type-safe.
- ℹ️ [Info] **No `ctx.hasUI` guard** — Line 43 uses `ctx.ui.notify()` without checking `ctx.hasUI`. Low risk since commands are interactive, but defensive.

**Lines of concern:** 48
**Current code:**
```ts
} catch (error: any) {
```
**Suggested fix:**
```ts
} catch (error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  ctx.ui.notify(`Save failed: ${message}`, "error");
```

**Token impact:** Minimal — runs only on `/set-key` command invocation

**Correct:**
- ✅ Silent startup — no startup notifications
- ✅ Clean command handler pattern
- ✅ No `console.log`
- ✅ Secure storage in `pi.paths.agent/auth.json`

---

### 5. `permission-gate.ts`
**Score:** 🟢

**Issues:**
- 🟡 [Warning] **Safe-patterns bypass for dangerous commands** — Lines 69-70 check `SAFE_PATTERNS` before `DANGEROUS_PATTERNS`. A command like `sudo ls` would match the safe pattern `^ls` and be skipped entirely, bypassing the `sudo` check. This is a minor security bypass.

**Lines of concern:** 69-70
**Current code:**
```ts
if (SAFE_PATTERNS.some((p) => p.test(cmd))) return;
```
**Suggested fix:** Check dangerous patterns first, then safe patterns:
```ts
// Check dangerous patterns first — these take priority
if (DANGEROUS_PATTERNS.some((p) => p.test(cmd))) { ... }
if (SENSITIVE_PATTERNS.some((p) => p.test(cmd))) { ... }
// Only then skip safe commands
if (SAFE_PATTERNS.some((p) => p.test(cmd))) return;
```

**Token impact:** Minimal — handler only fires on `tool_call`, does fast regex

**Correct:**
- ✅ Silent startup — no startup notifications
- ✅ Uses `isToolCallEventType("bash", event)` — proper pattern
- ✅ Uses `ctx.hasUI` to guard interactive confirmation
- ✅ No `console.log`
- ✅ Clean 60-line structure (close to official 40-line example)
- ✅ Returns `{ block: true, reason }` on blocked commands

---

### 6. `protected-paths.ts`
**Score:** 🟢

**Issues:**
- 🟡 [Warning] **Broad bash command regex matching** — Lines 60-65 test the full command string against `PROTECTED_PATTERNS`. This could produce false positives for commands like `echo "credentials"` or `cat secret.yaml`. Consider parsing the command more precisely.
- ℹ️ [Info] **Slightly verbose compared to official example** — Official example is 30 lines; this is 93 lines. The extra bash command protection is a valid extension, but the regex approach is broad.

**Lines of concern:** 60-65
**Current code:**
```ts
for (const pattern of PROTECTED_PATTERNS) {
  if (pattern.test(cmd)) {
```
**Suggested fix:** For bash commands, only check for redirection/pipe/write operations targeting protected paths, not the command string itself:
```ts
// Only check for write operations targeting protected paths
const writeOps = /([>|]\s*|\b(?:rm|mv|cp|chmod|chown)\s+)(\S+)/g;
let match;
while ((match = writeOps.exec(cmd)) !== null) {
  if (isProtected(match[2])) { ... }
}
```

**Token impact:** Minimal — handler only fires on `tool_call`

**Correct:**
- ✅ Silent startup — no startup notifications
- ✅ Uses `isToolCallEventType` for write, edit, and bash events
- ✅ Uses `ctx.hasUI` to guard interactive confirmation
- ✅ No `console.log`
- ✅ Proper `{ block: true, reason }` return for non-interactive mode

---

### 7. `rtk.ts`
**Score:** 🔴

**Issues:**
- 🔴 [Critical] **4× `console.warn` calls** — Lines 20, 24, 29, 60 use `console.warn` instead of `ctx.ui.notify()`. This is the most severe violation in the codebase. Official Pi examples never log to console. Each `console.warn` wastes tokens if stderr is captured.
- 🔴 [Critical] **Startup-time side effect** — Lines 17-30 run `rtk --version` as a fire-and-forget promise during module evaluation, not in a lifecycle hook. This means the version probe runs even if the extension is loaded but unused. The result is not awaited.
- 🟡 [Warning] **Unawaited promise** — The `.then()` chain on lines 17-30 is not awaited by any lifecycle hook. If the extension is loaded, the probe runs, but there's no guarantee it completes before the first `tool_call` event.
- 🟡 [Warning] **Mixed language in notification** — Line 48 uses Portuguese `compactou` instead of English. Extension code should be consistently in English.
- 🟡 [Warning] **Optional chaining on `ctx.ui`** — Lines 48, 60 use `ctx.ui?.notify?.(...)` with optional chaining on both `ctx.ui` and `notify`. This suggests uncertainty about the API. The correct pattern is `ctx.ui.notify(...)` guarded by `ctx.hasUI` if needed.
- 🟡 [Warning] **`console.warn` passes through command without notification** — Line 60 logs the error but doesn't notify the user that the rewrite failed. The command passes through silently.
- ℹ️ [Info] **`require` usage in modern codebase** — Line 25 uses `require("node:child_process")` instead of top-level `import`. This is a legacy pattern.

**Lines of concern:** 17-30, 48, 60
**Current code (lines 17-30):**
```ts
pi.exec("rtk", ["--version"], { timeout: REWRITE_TIMEOUT_MS }).then((ver) => {
  if (ver.code !== 0) {
    console.warn("[rtk] rtk binary not found in PATH — extension disabled")
    return
  }
  const parsed = parseSemver(ver.stdout.replace(/^rtk\s+/, ""))
  if (parsed) {
    const [major, minor] = parsed
    if (major === 0 && minor < MIN_SUPPORTED_RTK_MINOR) {
      console.warn(`[rtk] rtk ${ver.stdout.trim()} is too old (need >= 0.23.0) — extension disabled`)
      return
    }
  }
}).catch((err) => {
  console.warn(`[rtk] version probe failed: ${err.message}`)
})
```
**Suggested fix:**
```ts
pi.on("session_start", async (_event, ctx) => {
  try {
    const ver = await pi.exec("rtk", ["--version"], { timeout: REWRITE_TIMEOUT_MS });
    if (ver.code !== 0) {
      // Extension silently disabled — no startup notification
      enabled = false;
      return;
    }
    const parsed = parseSemver(ver.stdout.replace(/^rtk\s+/, ""));
    if (parsed) {
      const [major, minor] = parsed;
      if (major === 0 && minor < MIN_SUPPORTED_RTK_MINOR) {
        enabled = false;
        return;
      }
    }
    enabled = true;
  } catch (err) {
    enabled = false;
  }
});
```

**Token impact:** ~100 tokens per turn for `rtk rewrite` subprocess call. The `console.warn` calls waste ~50 tokens if stderr is captured.

**Correct:**
- ✅ Uses `isToolCallEventType("bash", event)` — proper pattern
- ✅ Passes `ctx.signal` to rewrite function — abort support
- ✅ `pi.exec` with timeout — proper timeout handling
- ✅ Fail-open pattern — never blocks execution on error
- ✅ `nix build` custom fallback (line 55) — useful extension

---

### 8. `session-name.ts`
**Score:** 🟢

**Issues:**
- ℹ️ [Info] **Word boundary truncation edge case** — Line 19 splits on space and slices `-1` (last element removed). If the truncated string has no spaces, `slice(0, -1)` returns an empty array, resulting in `"..."` as the name.

**Lines of concern:** 18-19
**Current code:**
```ts
const name = firstLine.length > 50
  ? firstLine.substring(0, 47).split(" ").slice(0, -1).join(" ") + "..."
  : firstLine;
```
**Suggested fix:** Handle the edge case where no word boundary is found:
```ts
const name = firstLine.length > 50
  ? (firstLine.substring(0, 47).split(" ").slice(0, -1).join(" ") || firstLine.substring(0, 47)) + "..."
  : firstLine;
```

**Token impact:** Minimal — runs once per session

**Correct:**
- ✅ Silent startup — no startup notifications
- ✅ Uses `before_agent_start` — proper lifecycle hook
- ✅ No `console.log`
- ✅ 24 lines, focused, single responsibility
- ✅ Skips if name already set

---

### 9. `workspace-search.ts`
**Score:** 🟡

**Issues:**
- 🟡 [Warning] **Hardcoded workspace path** — Line 24 hardcodes `resolve(homedir(), "Projects/pessoal/ai-workspace")`. This should use a shared configuration or `pi.paths` to avoid duplication across extensions.
- 🟡 [Warning] **No output truncation** — The `searchWorkspace` function returns raw grep output without truncation. BP #7 requires tools to truncate output. The tool description doesn't document truncation limits.
- 🟡 [Warning] **Synchronous child process** — Line 42 uses `execFileSync` which blocks the event loop. This is a Pi extension running in the main process — blocking the event loop freezes the UI.
- 🟡 [Warning] **Excessive buffer size** — Line 44 sets `maxBuffer: 10 * 1024 * 1024` (10MB). This is excessive for grep output and wastes memory.
- 🟡 [Warning] **System `grep` dependency** — Uses system `grep` command. Not cross-platform (Windows). Other extensions use `pi.exec` — this one should too.
- ℹ️ [Info] **No `ctx.signal` support** — The `execute` function signature doesn't use `_signal` or `_onUpdate`. The sync `execFileSync` can't be aborted.

**Lines of concern:** 24, 42-44, 51-52, 72-73
**Current code (lines 24, 42-44):**
```ts
const WORKSPACE_ROOT =
  process.env.WORKSPACE ||
  resolve(homedir(), "Projects/pessoal/ai-workspace");
```
```ts
const output = execFileSync("grep", [
  "-rin",
  "--include=*.md",
  "-m", String(maxResults),
  searchPattern,
  fullPath,
], { encoding: "utf-8", maxBuffer: 10 * 1024 * 1024 });
```
**Suggested fix:** Use async `pi.exec` with truncation and abort support:
```ts
async function searchWorkspace(query: string, maxResults = 10, signal?: AbortSignal): Promise<string> {
  const results: string[] = [];
  const searchPattern = query.replace(/['"\\]/g, "\\$&");
  let resultCount = 0;

  for (const dir of SEARCH_DIRS) {
    if (signal?.aborted) break;
    const fullPath = resolve(WORKSPACE_ROOT, dir);
    try {
      const { stdout } = await pi.exec("grep", [
        "-rin", "--include=*.md",
        "-m", String(maxResults),
        searchPattern, fullPath,
      ], { timeout: 10_000, signal });
      const lines = stdout.trim().split("\n");
      for (const line of lines.slice(0, maxResults - resultCount)) {
        const [file, num, ...text] = line.split(":");
        const relPath = relative(WORKSPACE_ROOT, file);
        const snippet = text.join(":").trim().substring(0, 200);
        results.push(`${relPath}:${num}: ${snippet}`);
        resultCount++;
      }
    } catch { /* dir may not exist */ }
    if (resultCount >= maxResults) break;
  }
  // Truncate if too long
  const output = results.join("\n");
  if (output.length > 5000) {
    return output.substring(0, 5000) + "\n... (truncated, results limited to 5000 chars)";
  }
  return output || `No results found for "${query}" in workspace.`;
}
```

**Token impact:** ~200-500 tokens per search result output. Without truncation, large results could add 1,000+ tokens per search.

**Correct:**
- ✅ Silent startup — no startup notifications
- ✅ Tool registration with `name`, `label`, `description`, `promptSnippet`, `parameters`
- ✅ Returns `details: { query: params.query }` — structured metadata
- ✅ `/ws` command for user interaction

---

## Cross-Cutting Concerns

### Antipatterns Found

1. **Console logging in production (2 extensions)** — `auto-commit.ts` (console.error) and `rtk.ts` (console.warn ×4). Official Pi examples never log to console. These waste tokens and clutter logs.

2. **Startup notifications (1 extension)** — `crg-trim.ts` calls `ctx.ui.notify()` in `session_start` on failure. Official examples are silent at startup.

3. **Hardcoded paths (1 extension)** — `workspace-search.ts` hardcodes the workspace path instead of using a shared config or `pi.paths`.

4. **No shared configuration library** — No extension exports a shared utility. The workspace path is hardcoded in `workspace-search.ts`. Other extensions that might need paths (e.g., `crg-trim.ts` for binary discovery) duplicate logic.

5. **Import inconsistency (1 extension)** — `crg-trim.ts` imports from `@mariozechner/pi-coding-agent` instead of `@earendil-works/pi-coding-agent` used by all other extensions.

6. **Synchronous blocking calls (1 extension)** — `workspace-search.ts` uses `execFileSync` which blocks the event loop. Pi extensions should be async.

7. **Fire-and-forget promises (1 extension)** — `rtk.ts` runs version probe as unawaited promise during module evaluation.

### Token Optimization Opportunities

| Opportunity | Extensions Affected | Est. Token Savings |
|-------------|-------------------|-------------------|
| Stop `console.warn`/`console.error` | auto-commit, rtk | ~50 tokens/session |
| Move `before_agent_start` injection to first start only | crg-trim | ~300 tokens/turn (×20 = 6,000/session) |
| Remove startup notifications | crg-trim | ~100 tokens/session |
| Truncate workspace search output | workspace-search | ~200-500 tokens/search |
| **Total potential savings** | | **~6,500 tokens/session** |

### Architecture Recommendations

1. **Create a shared configuration utility** — Extract `WORKSPACE_ROOT` resolution, binary path discovery, and version probing into a shared module (e.g., `pi-setup/lib/shared.ts`). This eliminates duplication across extensions.

2. **Standardize imports** — All extensions should import from `@earendil-works/pi-coding-agent`. Fix `crg-trim.ts` to use the correct package.

3. **Adopt a startup checklist** — Every extension should follow this checklist:
   - [ ] Silent startup (no `ctx.ui.notify()` in `session_start` or factory)
   - [ ] No `console.log`/`console.warn`/`console.error`
   - [ ] Uses `ctx.hasUI` guard for interactive features
   - [ ] Uses `ctx.signal` for abort support
   - [ ] Cleans up in `session_shutdown`
   - [ ] Uses `isToolCallEventType()` for event narrowing
   - [ ] Truncates tool output and documents limits

4. **Consolidate status/footer usage** — Currently no extension uses `ctx.ui.setStatus()` or `ctx.ui.setFooter()`. This is good — no competing footers. Keep it that way.

5. **Async everywhere** — Replace `execFileSync` with `pi.exec` in `workspace-search.ts` for non-blocking operation.

---

## Priority Queue

1. **[P0] Fix `rtk.ts` console.warn calls** — Replace with `ctx.ui.notify()` or remove. Move version probe to `session_start`. This is the most critical violation.
2. **[P0] Fix `rtk.ts` fire-and-forget startup side effect** — Move version probe to `session_start` lifecycle hook.
3. **[P1] Fix `crg-trim.ts` import package** — Change `@mariozechner/pi-coding-agent` to `@earendil-works/pi-coding-agent`.
4. **[P1] Fix `workspace-search.ts` synchronous blocking** — Replace `execFileSync` with async `pi.exec`.
5. **[P1] Add output truncation to `workspace-search.ts`** — Document and enforce truncation limits per BP #7.
6. **[P2] Fix `auto-commit.ts` console.error** — Replace with `ctx.ui.notify()`.
7. **[P2] Fix `permission-gate.ts` safe-patterns bypass** — Check dangerous patterns before safe patterns.
8. **[P2] Optimize `crg-trim.ts` system prompt injection** — Only inject graph guidelines on first `before_agent_start` or cache them.
9. **[P3] Fix `session-name.ts` word boundary edge case** — Handle empty array from `slice(0, -1)`.
10. **[P3] Create shared configuration utility** — Extract hardcoded paths and binary discovery into a shared module.
11. **[P3] Fix `login.ts` `error: any` type** — Use `unknown` type for caught errors.