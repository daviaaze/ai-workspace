# Plan: GetWork Idle-Throttle Mod (Ostranauts)

**Status:** Plan finalized — awaiting go-ahead to implement.

## User decisions (locked)
- **Cooldown:** 2.0s sim-seconds (aggressive)
- **Scope:** ProcessAutoTasks only (surgical, zero behavior change to task-claiming)
- **Profiling:** Mono jitdump + Linux `perf` (JetBrains dotTrace ruled out — can't reach a Proton/Wine release build; it needs Unity Editor launch or a dev build)
**Goal:** Cut work-shift sim lag by skipping redundant `GetWork()` re-scans for idle NPCs.

---

## 1. Problem (evidence-backed)

| Evidence | Source | Finding |
|---|---|---|
| Linux `perf` | external 30s capture, 12k samples | ~95% of CPU is managed Mono `[JIT]`, native engine negligible |
| Perf mod SIM-DIAG | managed method timings | `GetWork` = 121–147ms (2nd biggest after `AdvanceSim`) |
| Decompiled `CondOwner.GetWork` | `/tmp/game_api_full/CondOwner.cs:3645` | Called every `EndTurn` for every work-shift NPC |
| Decompiled `EndTurn` | `CondOwner.cs:3113` | Calls `GetWork()` when `jsShiftLast.nID == 2` (work shift), else `GetMove2()` |
| User gameplay observation | "free hours = way better lag" | Confirms `GetWork` is the work-shift overhead (free hours skips it) |
| Perf mod `Patch_GetWork` | decompiled `/tmp/perfmod_full.cs:3602` | **Only INSTRUMENTS** (timing/alloc for SIM-DIAG). Does NOT throttle. |

**Root cause:** `GetWork()` runs every turn for all 385 NPCs during work shifts. Each call, even when no task exists, re-runs `FreeWillLoot.ApplyCondLoot`, creates a `SeekSocialDeny` interaction, calls `workManager.ClaimNextTask`, and on the idle path allocates `new List<CondOwner>()` + scans `ship.GetCOs(ctRestoreItem...)` (full ship item scan). Nothing is cached between turns.

---

## 2. Approach (finalized — ProcessAutoTasks-only)

A single Harmony `Prefix` on `CondOwner.ProcessAutoTasks` (private bool, line 3708) that **skips the ship-scan** when the NPC recently scanned and found nothing, for a 2.0s sim-time cooldown.

**Why ProcessAutoTasks, not full GetWork:** GetWork still runs every turn to claim tasks (`workManager.ClaimNextTask` — cheap queue check) and wander (`GetMove2`). Only the expensive idle-path — `ProcessAutoTasks`'s `new List<CondOwner>()` + full `ship.GetCOs(ctRestoreItem, ...)` ship scan — is throttled. Zero behavior change for task pickup; only auto-restore-task discovery is delayed up to 2s.

- **Time source:** `StarSystem.fEpoch` (`public static double`, verified line 25) — sim-time, pauses correctly with the game.
- **Skip logic:** Prefix checks `fEpoch - _lastScan[co] < 2.0` → if true, **return false** (skip original, signal "no auto-task found" → GetWork falls through to GetMove2 wander).
- **Record on run:** when ProcessAutoTasks actually runs (cooldown expired), Postfix records `_lastScan[co] = fEpoch`.
- **Cleanup:** Postfix on `CondOwner.Destroy()` (line 1573) removes the dict entry.

**Anchor verification (all confirmed public in real assembly):**
- `StarSystem.fEpoch` — `public static double` (line 25) — direct access, no reflection
- `CondOwner.ProcessAutoTasks` — `private bool` (line 3708) — Harmony patches private fine
- `CondOwner.Destroy()` — `public void` (line 1573) — cleanup hook

---

## 3. Design decisions (finalized before coding)

1. **Dictionary, no locks.** `GetWork` runs single-threaded on the main sim thread → plain `Dictionary<CondOwner, float>`, no `lock()`. (Avoids the sampler disaster.)
2. **Zero allocation on fast path.** Dict lookup is O(1); Prefix/Postfix allocate nothing per call. (Avoids GC churn we'd be trying to fix.)
3. **Cooldown in sim-seconds** (default 1.0s). Configurable.
4. **Scope:** apply to all human/robot NPCs on work shift. `GetWork` already early-returns for non-human/robot, so no extra guard needed.
5. **Harmony priority:** if perf mod is reinstalled alongside, set `[HarmonyPriority(Priority.High)]` on our Prefix so it runs before the perf mod's instrumentation Prefix (our skip short-circuits before timing starts — meaning SIM-DIAG would under-report, which is fine/expected).
6. **Behavior change (acceptable):** idle NPCs re-scan for tasks only every `CooldownSecs` instead of every turn. Task pickup latency increases by up to CooldownSecs (1s). NPCs keep walking queued paths during cooldown.

---

## 4. Profiling approach (finalized — Mono jitdump + perf)

**Ruled out:** JetBrains dotTrace — can't reach a Proton/Wine release build (requires Unity Editor launch or a dev build; Linux attach is .NET Core 3.0+/.NET 5 native only, not Mono-under-Wine).

**Chosen:** Mono jitdump + Linux `perf` — gives a real flamegraph with **C# method names**, no per-call instrumentation overhead (unlike perf mod's SIM-DIAG which adds Prefix/Postfix timing to every GetWork/UpdateICOs/EndTurn).

**Measurement protocol (before/after):**
1. Relaunch game with `MONO_ENV_OPTIONS="--jitdump --jitmap"` in Steam launch options (alongside existing `DRI_PRIME=1 mangohud ... %command%`).
2. Work-shift scenario, capture: `perf record -F 99 -p <pid> -g --call-graph dwarf -- sleep 30`
3. Inject JIT symbols: `perf inject --jit -i perf.data -o perf.jit.data`
4. Report: `perf report -i perf.jit.data` or `perf script` → flamegraph with `CondOwner.ProcessAutoTasks` named.
5. **Before:** note ProcessAutoTasks sample share. **After (throttle installed):** re-capture, confirm share drops and frametime improves.

**Fallback if Unity's embedded Mono ignores `--jitdump` (no `/tmp/perf-<pid>.map` or `jit-*.dump` appears):** write a one-shot symbol-map-dump BepInEx mod that walks Mono's JIT method table at startup and writes `/tmp/perf-<pid>.map` (address→name), then idles with **zero runtime cost**. This is the `vvuk/mono-jitdump` pattern adapted as a startup-only mod.

**Worst-case fallback:** if neither yields names, measure with raw perf `[JIT]` sample-share comparison + MangoHud frametime (before/after total sim cost) — still valid proof the throttle worked, just without per-method attribution.

---

## 5. Implementation checklist (when approved)

- [ ] Create `/tmp/ostranauts-mods/GetWorkThrottle/src/GetWorkThrottlePlugin.cs`
  - `[BepInPlugin("com.ostranauts.getworkthrottle", "GetWork ProcessAutoTasks Throttle", "1.0.0")]`
  - `ConfigEntry<double> CooldownSecs` (default 2.0)
  - `static Dictionary<CondOwner, double> _lastScan` (no locks — main sim thread only)
  - `[HarmonyPatch(typeof(CondOwner), "ProcessAutoTasks")] Prefix`: returns `false` (skip) + sets `result=false` when `StarSystem.fEpoch - _lastScan[co] < CooldownSecs`
  - `[HarmonyPatch(typeof(CondOwner), "ProcessAutoTasks")] Postfix`: record `_lastScan[co] = StarSystem.fEpoch` (ran for real)
  - `[HarmonyPatch(typeof(CondOwner), "Destroy")] Postfix`: `_lastScan.Remove(__instance)`
- [ ] Create `.csproj` — netstandard2.1, LangVersion 9.0, HintPaths using **resolved** `/home/daviaaze/.local/share/Steam/...` (not the `~/.steam/steam` symlink — MSBuild doesn't follow it).
  - References: BepInEx.dll, 0Harmony.dll (BepInEx/core), UnityEngine.dll + CoreModule, Assembly-CSharp.dll (game Managed)
- [ ] Build: `nix-shell -p dotnet-sdk_8 --run "dotnet build -c Release"`
- [ ] Verify BepInEx framework still installed (doorstop `winhttp.dll` + `doorstop_config.ini` + `BepInEx/core/`) — we only removed the perf mod DLL, framework should be intact.
- [ ] Install DLL to `BepInEx/plugins/`
- [ ] Baseline: `perf record` during work shift (with `MONO_ENV_OPTIONS=--jitdump` if it yields names, else raw [JIT] share + MangoHud frametime)
- [ ] After: same scenario, confirm ProcessAutoTasks share dropped + frametime improved
- [ ] Correctness: crew still claim workManager tasks every turn (unthrottled); auto-restore tasks picked up within 2s; no stuck NPCs; no NullReferenceException in Player.log; dict entry count stable (cleanup works)

---

## 6. Risks / anti-patterns (lessons applied)

| Past failure | Mitigation in this plan |
|---|---|
| Per-call `lock()` on hot path destroyed frametime | Single-threaded dict, NO locks |
| `Stopwatch` + dict write per call | No timing in Prefix/Postfix; only a dict read/write |
| Cross-thread `StackTrace(Thread)` sampler stalled game | No threading — main thread only |
| CS1061/CS0571 from inaccessible members | `StarSystem.fEpoch` + `aQueue` verified PUBLIC; no reflection needed |
| MSBuild ignores `~/.steam/steam` symlink for HintPath | Use resolved `/home/daviaaze/.local/share/Steam/...` paths |
| `WaitForSeconds` coroutine froze when paused (IdlePause bug) | Using sim-time `fEpoch`, not coroutines — pauses correctly |
| Decompilation showed members not actually public | All 3 anchors verified public in actual assembly |
