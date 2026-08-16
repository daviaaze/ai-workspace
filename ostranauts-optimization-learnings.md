# Ostranauts Performance Optimization — Learnings

**Date**: 2026-08-16
**Game**: Ostranauts v1.0.0.9 (buildid 24663190), Unity 6000.3.10, Mono/Boehm GC, .NET Standard 2.1
**Platform**: Linux/NixOS, Steam/Proton, RX 6700 XT (DRI_PRIME=1)
**Decompiled source**: `/tmp/game_api_full/` (612 .cs files via ilspycmd 9.1.0)
**API reference**: `~/Projects/ai-workspace/ostranauts-api-reference.md` + `ostranauts-api/` folder

---

## 1. The Performance Problem

At 16x speed with 385 NPCs, the game experiences severe frame spikes (766-1639ms) from GC storms caused by 43-95MB allocation per sim step. The bottleneck is **diffuse** — no single method dominates (top resolved C# method SpanHelpers:SequenceEqual at only 0.59% of samples). The sum of tiny operations × 385 NPCs × 16 ticks/s ≈ 6160 GetWork calls/sec generates the allocation pressure.

### Hot path (per NPC per tick)
```
CrewSim.Update
  → AdvanceSim(fDelta * fTimeCoeffPause)
    → UpdateICOs()  [copies aTickers via AddRange, iterates 385+ NPCs]
      → CondOwner.UpdateManual()  [per NPC]
        → Cleanup()  [every 2s, new List<string>(dictRecentlyTried.Keys)]
        → ParseCondLoot()  [iterates aCOs, calls ParseCondEquation]
        → EndTurn()  [aCondsTemp.AddRange copy, GetInteraction calls]
        → IManUpdater.UpdateManual() loop
        → RefreshAnim()  [cheap: dictAnims lookup]
        → UpdateStats()  [cheap: only strings mapInfo on change]
        → Item.VisualizeOverlays()  [recomputes overlay math every tick]
```

### GetWork breakdown (the dominant per-NPC method, ~6160 calls/sec)
```csharp
private void GetWork()
{
    if (ship == null || !IsHumanOrRobot) return;
    FreeWillLoot.ApplyCondLoot(this, 1f);  // Loot.ApplyCondLoot instance method
    if (!HasCond("IsPlayer") && Company == CrewSim.coPlayer.Company)
    {
        Interaction interaction = DataHandler.GetInteraction("SeekSocialDeny");  // ALLOC: new Interaction every call
        interaction.objUs = this;
        interaction.objThem = CrewSim.coPlayer;
        if (interaction.Triggered(...))  // usually returns false
        {
            Pathfinder.Reset();
            QueueInteraction(interaction.objThem, interaction);
            CrewSim.objInstance.workManager.IdleAdd(this);
            return;
        }
    }
    Task2 task = CrewSim.objInstance.workManager.ClaimNextTask(this);  // ALLOC: new List<Task2> per duty, Insert(0), IndexOf
    // ... task handling ...
    if (task == null)
    {
        if (!ProcessAutoTasks())  // ALLOC: new List<CondOwner> + ship.GetCOs scan
            GetMove2();  // ALLOC: new Dictionary<string, List<CondOwner>> + ship.GetCOs × 3-5
    }
}
```

---

## 2. Allocation Audit — Key Sites Found

### Ship.GetCOs (Ship.cs:5008) — 4 allocations per call
```csharp
public List<CondOwner> GetCOs(CondTrigger objCondTrig, bool bSubObjects, bool bAllowDocked, bool bAllowLocked)
{
    CondOwnerVisitorAddToHashSet visitor = new CondOwnerVisitorAddToHashSet();  // alloc 1: visitor + new HashSet
    CondOwnerVisitor v = CondOwnerVisitorCondTrigger.WrapVisitor(visitor, objCondTrig);  // alloc 2: new wrapper
    VisitCOs(v, ...);  // alloc 3: mapICOs.Values.ToArray() inside VisitCOs
    return new List<CondOwner>(visitor.aHashSet);  // alloc 4: HashSet→List copy
}
```
- **Callers**: GetMove2 (3-5×), ProcessAutoTasks (1×), TriggeredInternal (if CTTest3rd≠null), ClaimNextTask, HandleFeedTask
- **Scale**: 5000-10000 calls/sec → 20000-40000 objects/sec
- **Fix applied**: `GetCOsOpt.dll` — reusable visitor + wrapper + HashSet (saves 3 of 4 allocs; ToArray in VisitCOs left for future)

### DataHandler.GetInteraction (DataHandler.cs:2991) — new Interaction every call
```csharp
// Returns new Interaction(dictInteractions[strName], jis) when getTrackedObject=false (default)
// Called from GetWork for "SeekSocialDeny" ~6160 times/sec — create, Triggered(), discard
```
- **Callers**: 72 total hot-path call sites (32 in CondOwner, 33 in CrewSim, 6 in WorkManager, 1 in Ship)
- **Hot names**: SeekSocialDeny, QuickWait, PickupItemStack, Walk, DropItemStack, EquipItem, PickupItem, SocialCombatExitSilent
- **Fix applied**: `SeekSocialCache.dll` — reusable Interaction instance for SeekSocialDeny with borrow flag + aQueue.Contains() queuing detection

### GetMove2 (CondOwner.cs:4250) — new Dictionary per call
```csharp
Dictionary<string, List<CondOwner>> dictionary = new Dictionary<string, List<CondOwner>>();
// Used as per-call cache for ship.GetCOs results by CondTrigger name
```
- **Scale**: called when NPC is idle (no task) — 2000-4000 calls/sec
- **Fix**: SKIPPED — local variable can't be replaced by Prefix; full method replacement too risky (1000+ lines)

### ClaimNextTask → CollectTasks (WorkManager.cs:289-410, 570)
```csharp
List<Task2> list = new List<Task2>();  // per duty per call
list.Insert(0, item);  // O(n) shift for "Owned" tasks
list.IndexOf(value.ship.strRegID);  // O(n) string search
dictionary = new Dictionary<string, List<CondOwner>>();  // per-call cache
DataHandler.GetInteraction(item.strInteraction);  // new Interaction per task
```
- **Fix applied**: `WorkClaimThrottle.dll` — idle-aware cooldown skips ClaimNextTask entirely

### EndTurn (CondOwner.cs:3113) — aCondsTemp.AddRange copy
```csharp
aCondsTemp.AddRange(aCondsTimed);  // copies timed conditions every EndTurn
foreach (Condition item in aCondsTemp) { item.Update(elapsed, this); }
aCondsTemp.Clear();
```
- aCondsTemp is reused (cleared) but AddRange still copies all elements per NPC per tick
- **Fix**: Not yet implemented — would need Transpiler to iterate directly

### ProcessAutoTasks (CondOwner.cs:3708) — new List + ship scan
```csharp
List<CondOwner> list = new List<CondOwner>();
ship.GetCOs(ctRestoreItem, bSubObjects: true, ...);  // full ship scan
```
- **Fix applied**: `GetWorkThrottle.dll` — 2.0s sim-time cooldown skips ProcessAutoTasks

### Item.VisualizeOverlays (Item.cs:235) — recomputes overlay math every tick
- Always recomputes GUIPDA.OverlayVariable, GetCondAmount, GetBasePrice, GetDamageRate, room heat, InverseLerp
- Called at end of CondOwner.UpdateManual for all 385 NPCs
- Internal MPB dirty-check only prevents SetPropertyBlock calls, not the math
- **Fix applied**: `ItemOverlayThrottle.dll` — interval+stride skip (never throttles force=true)

---

## 3. Key API Details for Harmony Patches

### Public accessibility (verified against assembly)
| Member | File:Line | Accessibility |
|--------|-----------|---------------|
| `Ship.GetCOs(CondTrigger, bool, bool, bool)` | Ship.cs:5008 | public, single overload |
| `Ship.VisitCOs(CondOwnerVisitor, bool, bool, bool)` | Ship.cs:4971 | public |
| `CondOwnerVisitorAddToHashSet.aHashSet` | visitor.cs:5 | public HashSet<CondOwner> |
| `CondOwnerVisitorCondTrigger.objCondTrig` | visitor.cs:3 | public CondTrigger |
| `CondOwnerVisitorCondTrigger.subVisitor` | visitor.cs:5 | public CondOwnerVisitor |
| `CondOwner.aQueue` | CondOwner.cs:207 | public List<Interaction> |
| `Interaction.fEpochAdded` | Interaction.cs:109 | public double |
| `StarSystem.fEpoch` | StarSystem.cs | public static double (sim-time source, pauses with game) |
| `FreeWillLoot` | CondOwner.cs:1077 | public static Loot |
| `DataHandler.GetInteraction(string, JsonInteractionSave, bool)` | DataHandler.cs:2991 | public, 3-arg overload |

### Private/inaccessible (requires reflection or Traverse)
| Member | Issue |
|--------|-------|
| `CondOwner.ProcessAutoTasks()` | private — Prefix works but can't call original from replacement |
| `CondOwner.GetMove2()` | private — Prefix works but can't call from replacement |
| `CondOwner.HandleHaulTask/HandleFeedTask` | private — can't call from Prefix replacement |
| `Ship.mapICOs` | private Dictionary<string, CondOwner> — access via AccessTools.Field |
| `JsonZone.get_aTiles()` | private getter (CS0571) — use FastReflector.CallMethod |
| `CrewSim.set_Paused` | private setter (CS0571) — use Traverse.Create |

### Reentrancy analysis
- `CondTrigger.Triggered` does NOT call `Ship.GetCOs` — safe to reuse GetCOs visitor
- `Interaction.TriggeredInternal` DOES call `DataHandler.GetInteraction` for OTHER names (chain interactions at lines 1206, 2324, 2355, 3251, 3540) — SeekSocialCache uses `_inUse` borrow flag to handle this
- `Ship.GetCOs` → `VisitCOs` → `visitor.Visit` → just adds to HashSet, no GetCOs recursion

---

## 4. Perf Mod (OstronautsPerfOpt v5.2.1) Analysis

### Decompiledd source: `/tmp/perfmod_full.cs` (4939 lines, 47 patches)

### Optimization patches (in OstranautsOpt.dll after split)
- `Patch_FirstOrDefault` — skip O(n) FirstOrDefault scans
- `UpdateICOsParallelPrepass` — parallel prepass during loading
- `UpdateICOs_NoCopy` — reuse aTickersTemp instead of AddRange copy
- `EndTurn_Throttle` — placeholder (Prefix always returns true)
- `CleanupExpire` — cleanup optimization
- `GetMove2_Cache` — **DISABLED** (full method replacement with ThreadStatic buffers, likely buggy)
- `ClaimTaskDirect_QueueStack` — use stack instead of list for AIIssueOrder
- `AICancelAll_StackSkip` — skip stack allocation
- `SaveGame_Threaded` — threaded save
- `NoAlloc patches`: UpdateCrewSkills, DeliverMessages, UpdateShip_FirstBO, UpdateManual_NoTickerLog
- `SuppressInteractionLog` — **DISABLED**

### Instrumentation patches (in OstranautsSimDiag.dll after split)
- `Patch_AdvanceSim`, `Patch_UpdateICOs`, `Patch_EndTurn`, `Patch_GetMove2`, `Patch_GetWork`, `Patch_ParseCondLoot`, `Patch_Cleanup`, `Patch_UpdateStats`, `Patch_StarSystemUpdate`, `Patch_StateReset`
- `SpikeProfiler` — background thread sampling main thread stack via `new StackTrace(mainThread, false)` every ~10ms
- `LoadingProfiler` — load-phase timing for Ship.InitShip, VisitCOs, etc.

### Plugin behavior
- `IsProfiling` constant = true (hardcoded, no config)
- Awake sets: `Time.maximumDeltaTime=0.1f`, `GCSettings.LatencyMode=LowLatency`, `ExpandHeap(128)` 3s after load, `CheckMemoryCeiling()` each frame
- Log: "All optimizations hardcoded ON. No config."

### Split into two DLLs (2026-08-16)
- `OstranautsOpt.dll` (73KB, `com.ostranauts.opt`) — 45 optimization patches + GC/heap mgmt, NO SpikeProfiler, NO DIAG report
- `OstranautsSimDiag.dll` (38KB, `com.ostranauts.simdiag`) — 10 instrumented patches + SpikeProfiler + LoadingProfiler + DIAG/SPIKE report
- Split script: `/tmp/split_mods.py` (brace-balancing parser, rewrites patch array + BepInPlugin ID + namespace)

---

## 5. Anti-Patterns Learned (the Hard Way)

### ❌ Per-call Harmony instrumentation on hot methods
Deep Profiler (com.ostranauts.profiler) patched UpdateManual, EndTurn, UpdateStats, UpdateICOs with Prefix/Postfix pairs doing `Stopwatch.Restart + lock()` on a shared global dictionary per invocation. Caused severe lock contention with 385 NPCs calling them thousands of times per frame.

### ❌ Cross-thread StackTrace(Thread, bool) sampling
"Non-intrusive" Stack Sampler patched nothing but used a background thread doing `new StackTrace(mainThread, false)` every ~8ms. Mono suspends the main thread to walk its stack — same lag as per-call lock instrumentation. Same issue with perf mod's SpikeProfiler.

### ❌ JitMapBridge address resolution during gameplay
JitMapBridge BepInEx plugin resolved perf hot addresses via `mono_jit_info_table_find` every 2s tick, making ~7951 calls that each suspend the main Unity thread. Contaminated SIM-DIAG numbers (GetWork 460-483ms vs real ~300ms). Removing it returned EndTurn to 28-63ms.

**Lesson**: ANY BepInEx in-game profiling mod that touches the main Unity thread causes severe lag in Ostranauts under Proton/Mono. Use external Linux perf + Mono jitdump only.

### ❌ Enabling disabled perf mod patches blindly
`Patch_GetMove2_Cache` and `SuppressInteractionLog` are disabled by the perf mod author for unknown reasons. Enabling without understanding why risks bugs.

### ❌ Reusing returned buffers when callers store them
Ship.GetCOs returns `List<CondOwner>` — callers store and iterate this List. If I reused a single List, all callers would share the same (overwritten) buffer. The final `new List<CondOwner>(hashSet)` must stay allocated for caller safety.

### ❌ Per-frame/per-tick instrumentation without a lock OR with a coarse lock on hot paths
Instrumenting *every* call (or even every frame) of a hot method — with **or** without a lock —
is a trap. The cost does not come only from lock contention (Deep Profiler, above): any
per-invocation work (`Stopwatch.Restart`, `lock()`, `Interlocked`, dictionary hit/miss) executed
385 NPCs × 16 ticks/s multiplies to tens of thousands of ops/sec. Correct pattern: **throttle by
sim-time cooldown** (`StarSystem.fEpoch`) or **interval+stride skip** (see GetWorkThrottle /
ItemOverlayThrottle / WorkClaimThrottle), and keep the hot path allocation-free.

### ❌ Cross-calling Harmony patches that trigger each other (reentrancy)
Two mods patching the same method (or a patch calling a method that another patch instruments)
create ordering-dependent behavior. Real case: several mods postfix `Task2.AssignHaulZone` with
`if (__result != null) return;` — if two do that, the *second* postfix never sees the result the
*first* produced (or vice-versa), depending on Harmony priority. Mitigations:
- Set explicit `[HarmonyPriority]` (High/Normal/Low) on every postfix of a shared target;
- Use a `_inUse` borrow flag when interacting with `DataHandler.GetInteraction`-style reentrancy
  (as SeekSocialCache does);
- Document which mod patches which target so overlap is visible in the roadmap.

### ❌ Decompiler artifacts that cause build errors
- `using System.Diagnostics;` conflicts with `using UnityEngine;` (Debug ambiguity) → need `using Debug = UnityEngine.Debug;` alias
- `Object` ambiguous between `UnityEngine.Object` and `object` → need `using Object = UnityEngine.Object;` alias
- `Random` ambiguous between `UnityEngine.Random` and `System.Random` → need alias
- `ThreadPriority` ambiguous → need `using ThreadPriority = System.Threading.ThreadPriority;`
- File-scoped namespace requires C# 10.0 (`<LangVersion>10.0</LangVersion>`)
- `[assembly: ...]` attributes from decompiler conflict with SDK-generated AssemblyInfo → strip them
- `(StartShip)1` should be `(PersonSpec.StartShip)1` (nested enum prefix lost)
- `Loaded nLoad` should be `Ship.Loaded nLoad` (nested enum prefix lost)
- `typeof(Loaded)` should be `typeof(Ship.Loaded)`
- `_ = null;` discard can't infer type → replace with `/* _ = null; */`
- `inputTypeForHandle - 1` enum-int arithmetic → cast: `(int)inputTypeForHandle - 1`
- `((BaseUnityPlugin)this).Logger` protected access via base type → replace with `this.Logger`

### ❌ Overlapping plugins for the same bug fix (battery example)
Three separate DLLs (`BatteryCare`, `BatteryRechargeFix`, `OstBattFix`) each patched the
battery/drop/recharge flow (`PledgeRecharge.Do`, `CondOwner.AddCO`, `CondOwner.DropCO`). They
duplicate logic, can fight on the same postfix (see cross-calling above), and make debugging
impossible (which plugin actually fixed the symptom?). **Lesson: unify related fixes into ONE
plugin** with a single Harmony instance and clearly separated internal patches.

---

## 6. C# Mod Build Patterns (NixOS-specific)

### Working csproj template
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>netstandard2.1</TargetFramework>
    <AssemblyName>MyMod</AssemblyName>
    <LangVersion>9.0</LangVersion>  <!-- or 10.0 for file-scoped namespaces -->
    <EnableDefaultCompileItems>true</EnableDefaultCompileItems>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include="BepInEx">
      <HintPath>/home/daviaaze/.local/share/Steam/steamapps/common/Ostranauts/BepInEx/core/BepInEx.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <!-- 0Harmony, Assembly-CSharp, UnityEngine, UnityEngine.CoreModule -->
  </ItemGroup>
</Project>
```

### Build command
```bash
cd /tmp/ostranauts-mods/MyMod/src
nix-shell -p dotnet-sdk_8 --run "dotnet build -c Release -o /tmp/ostranauts-mods/MyMod/out"
```

### NixOS-specific gotchas
- **HintPath must use resolved (non-symlink) path**: `~/.steam/steam` → `~/.local/share/Steam` (MSBuild doesn't follow symlinks)
- **One .cs file per plugin source directory**: auto-include gathers all .cs in src/, multiple files cause CS0111 duplicate class
- **netstandard2.1 required**: UnityEngine.CoreModule demands it (netstandard2.0 causes CS1705)
- **Additional module refs**: GUIStyle→IMGUIModule, TextAnchor→TextRenderingModule, Input→InputLegacyModule, GridLayout→GridModule
- **Container type collision**: use `global::Container` qualifier to avoid CS0119 with system namespaces
- **No NuGet PackageReference**: BepInEx.Core/HarmonyX fail (NU1101); use local DLL HintPaths

### Verifying BepInPlugin ID in built DLL
```bash
python3 -c "
data = open('MyMod.dll','rb').read()
idx = data.find(b'com.ostranauts')
print(data[idx:data.find(b'\x00',idx)].decode())
"
```

---

## 7. Final Mod Configuration (as of 2026-08-16, 10 DLLs)

| Mod | Size | Plugin ID | What it does |
|-----|------|-----------|--------------|
| OstranautsOpt.dll | 73KB | com.ostranauts.opt | 45 optimization patches + GC/heap mgmt (from split perf mod) |
| OstranautsSimDiag.dll | 39KB | com.ostranauts.simdiag | Instrumentation (optional — has the main-thread SpikeProfiler, remove for clean gameplay) |
| GetCOsOpt.dll | 5.1KB | com.ostranauts.getcosopt | Reusable visitor+wrapper+HashSet for Ship.GetCOs |
| SeekSocialCache.dll | 6.1KB | com.ostranauts.seeksocialcache | Reusable Interaction for SeekSocialDeny fire-and-forget |
| GetWorkThrottle.dll | 6KB | com.ostranauts.getworkthrottle | 2s cooldown on ProcessAutoTasks |
| ItemOverlayThrottle.dll | 5.6KB | com.ostranauts.itemoverlaythrottle | Interval+stride skip on VisualizeOverlays |
| WorkClaimThrottle.dll | 6KB | com.ostranauts.workclaimthrottle | Idle-aware cooldown on ClaimNextTask |
| BatteryCare.dll | 8.7KB | — | Battery care mod |
| BatteryRechargeFix.dll | 6.7KB | — | Battery recharge fix |
| OstBattFix.dll | 5KB | — | Battery sticky-flag / drop fix |

> ⚠️ **Consolidation note**: the three battery mods (`BatteryCare`, `BatteryRechargeFix`,
> `OstBattFix`) overlap on the same drops/recharge hooks — see §5 anti-pattern
> “Overlapping plugins for the same bug fix”. Unify into a single plugin (Frente C).

### Keybind map (from earlier session, for reference)
F5=QuickSave(Save), F6=PickupOrder(Toggle), F7=AutoDock, F8=IdlePause(Toggle), F9=QuickSave(Load), F10=QuickPickup, F11=QuickUninstall, F12=UninstallAndHaul, N=QuickNavigate, P=WorkPriority, PageUp/Down=TimeScaler+/-, Home=TimeScaler(Reset)

---

## 8. What's Left (Future Work)

### Not yet implemented
1. **VisitCOs mapICOs.Values.ToArray()** — 4th allocation in GetCOs chain. Could Prefix VisitCOs to iterate directly, but VisitCOs is called from multiple places (risky).
2. **EndTurn aCondsTemp.AddRange copy** — Transpiler to iterate aCondsTimed directly (if Update doesn't modify it during iteration).
3. **GetMove2 reusable Dictionary** — needs full method replacement or Transpiler. Perf mod's disabled Patch_GetMove2_Cache has the approach but is likely buggy.
4. **Interaction pooling for other hot names** — PickupItem, Walk, DropItemStack in HandleHaulTask/HandleFeedTask. Same borrow-flag pattern as SeekSocialCache but for multiple names.
5. **aTickers.Remove(temp_jt) O(n)** — per-NPC ticker list, swap-remove if order doesn't matter.
6. **aManUpdates.Remove(aMUDel) O(n²)** — rebuild list without nulls instead of Remove per item.

### Needs validation (as of 2026-08-16)
- ✅ GetCOsOpt and SeekSocialCache are **installed** (A8/A9). In-game validation of their net FPS
  impact is still pending (need a clean sim run, 16x, measure before/after).
- OstranautsSimDiag.dll should be REMOVED for clean gameplay (its SpikeProfiler causes the same
  main-thread-suspension lag as JitMapBridge).
- `GetMove2` (item 3) is **SKIPPED_WARNING** — full-method-replacement risk, do not enable
  `Patch_GetMove2_Cache` blindly.

### Measurement approach
- OstranautsSimDiag.dll's [DIAG]/[SPIKE] report can be used temporarily for before/after, then removed.
- External: Linux perf + the JitMapBridge approach (but JitMapBridge itself causes lag, so only for short capture bursts, not sustained gameplay).
