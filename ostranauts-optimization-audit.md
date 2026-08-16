# Ostranauts Optimization Audit — Decompiled Source Analysis

**Date**: 2026-08-16
**Status (as of 2026-08-16)**: Fixes 1–2 shipped and installed; `GetMove2` (Fix 3) explicitly SKIPPED (full-method-replacement risk); EndTurn (Fix 4) and rest ainda em aberto.
**Source**: `/tmp/game_api_full/` (612 .cs files, full Assembly-CSharp.dll decompilation)
**Hot path**: `CrewSim.Update` → `AdvanceSim` → `UpdateICOs` → (per NPC) `CondOwner.UpdateManual` → `Cleanup`/`ParseCondLoot`/`EndTurn`/`GetWork`/`GetMove2`/`UpdateStats`/`VisualizeOverlays`
**Scale factor**: 385 NPCs × 16 ticks/s ≈ 6160 calls/s per hot-path method

## Already Addressed (as of 2026-08-16)

| # | Site | Fix | Mod | Estado |
|---|------|-----|-----|------------|
| A1 | `UpdateICOs` AddRange copy of aTickers | NoCopy patch | OstranautsOpt | ✅ installed |
| A2 | `aCondsTemp` pre-sizing | PreSizeCondsTemp | OstranautsOpt | ✅ installed |
| A3 | Debug.Log string concat in UpdateManual | NoTickerLog transpiler | OstranautsOpt | ✅ installed |
| A4 | FirstOrDefault O(n) scans | FirstOrDefault skip | OstranautsOpt | ✅ installed |
| A5 | `ProcessAutoTasks` ship-scan | Cooldown throttle | GetWorkThrottle | ✅ installed |
| A6 | `Item.VisualizeOverlays` recompute | Interval+stride throttle | ItemOverlayThrottle | ✅ installed |
| A7 | `ClaimNextTask` per-tick | Idle-aware throttle | WorkClaimThrottle | ✅ installed |
| A8 | `Ship.GetCOs` — 3 allocs/call | Reusable visitor+wrapper+HashSet | GetCOsOpt | ✅ installed (was Fix 1) |
| A9 | `DataHandler.GetInteraction("SeekSocialDeny")` | Reusable Interaction (borrow flag) | SeekSocialCache | ✅ installed (was Fix 2) |

> **Como ler**: a lista A1–A9 é o estado **consolidado** de otimizações já aplicadas. Os itens
> que antigamente estavam em "Remaining"/prioridade e agora estão nesta tabela saíram do backlog
> ativo.

## Implemented Fixes (2026-08-16)

### ✅ Fix 1: Ship.GetCOs reusable visitor — `GetCOsOpt.dll`
**Plugin**: `com.ostranauts.getcosopt` (5.1KB, installed to BepInEx/plugins/)
**Source**: `/tmp/ostranauts-mods/GetCOsOpt/src/GetCOsOptPlugin.cs`
**Approach**: Harmony Prefix on `Ship.GetCOs` that reuses a static `CondOwnerVisitorAddToHashSet` (HashSet.Clear instead of new) + static `CondOwnerVisitorCondTrigger` wrapper (fields set instead of new). Saves 3 of 4 allocations per call. Final `List<CondOwner>` still allocated for caller safety.
**Safety**: No reentrancy (CondTrigger.Triggered does not call GetCOs). All visitor fields are public.

### ✅ Fix 2: SeekSocialDeny reusable Interaction — `SeekSocialCache.dll`
**Plugin**: `com.ostranauts.seeksocialcache` (6.1KB, installed to BepInEx/plugins/)
**Source**: `/tmp/ostranauts-mods/SeekSocialCache/src/SeekSocialCachePlugin.cs`
**Approach**: Prefix+Postfix on `DataHandler.GetInteraction` that reuses a single Interaction instance for "SeekSocialDeny". When Triggered returns false (common), instance is reused. When true, interaction is queued (live) and fresh one created next time. GetWork Postfix detects queuing via `aQueue.Contains()`.
**Safety**: `_inUse` borrow flag prevents reentrancy corruption. `aQueue` and `fEpochAdded` are both public.

### ⏸️ Fix 3: GetMove2 reusable Dictionary — SKIPPED
**Reason**: GetMove2 Dictionary is a local variable — can't be replaced by Prefix. Requires full method replacement (1000+ lines of social logic) or fragile Transpiler. The perf mod's disabled `Patch_GetMove2_Cache` already does full replacement with `[ThreadStatic]` buffers but is likely buggy (hence disabled). GetCOs fix already reduces GetCOs cost within GetMove2.

## Remaining Optimization Candidates (as of 2026-08-16)

> ✅ **Itens 1 e 2 movidos para a tabela “Already Addressed”** (A8/A9) — já implementados e
> instalados. O item 3 (`GetMove2`) segue **SKIPPED_WARNING** (risco de substituição total de
> método). Os demais (4–13) continuam em backlog de otimização.

### 🔴 HIGH IMPACT

#### ✅ 1. `Ship.GetCOs` — 3 allocations per call — **DONE (GetCOsOpt, A8)**
**File**: `Ship.cs:5008`
```csharp
public List<CondOwner> GetCOs(CondTrigger objCondTrig, bool bSubObjects, bool bAllowDocked, bool bAllowLocked)
{
    CondOwnerVisitorAddToHashSet condOwnerVisitorAddToHashSet = new CondOwnerVisitorAddToHashSet();  // alloc 1: new visitor + new HashSet
    CondOwnerVisitor visitor = CondOwnerVisitorCondTrigger.WrapVisitor(condOwnerVisitorAddToHashSet, objCondTrig);  // alloc 2: new wrapper
    VisitCOs(visitor, bSubObjects, bAllowDocked, bAllowLocked);
    return new List<CondOwner>(condOwnerVisitorAddToHashSet.aHashSet);  // alloc 3: HashSet→List copy
}
```
**Callers**: GetMove2 (3-5×), ProcessAutoTasks (1×), TriggeredInternal (if CTTest3rd≠null), ClaimNextTask/CollectTasks, HandleFeedTask
**Scale**: potentially 5000-10000 calls/s → 15000-30000 objects/sec
**Fix**: Harmony Prefix that replaces with a reusable per-ship visitor (cleared, not re-newed) + returns the HashSet directly (or uses a pooled List). The visitor + HashSet can be `static` thread-local or per-ship fields cleared at start.
**Estimated GC reduction**: ~15-30% of per-step allocation

#### ✅ 2. `DataHandler.GetInteraction("SeekSocialDeny")` — 6160 Interaction objects/sec — **DONE (SeekSocialCache, A9)**
**File**: `DataHandler.cs:2991` (called from `CondOwner.cs:3654`)
```csharp
// In GetWork (called every tick for every NPC):
Interaction interaction = DataHandler.GetInteraction("SeekSocialDeny");  // new Interaction every call
interaction.objUs = this;
interaction.objThem = CrewSim.coPlayer;
if (interaction.Triggered(interaction.objUs, interaction.objThem))  // usually returns false
```
**Scale**: 385 NPCs × 16 ticks = 6160 new Interaction objects/sec, each created, Triggered()'d, and discarded
**Fix**: Harmony Prefix on `GetWork` that caches the `Triggered()` result per-NPC with a 2-5s sim-time cooldown. If recently checked and not triggered, skip creating the Interaction entirely. Social desire doesn't change frame-to-frame.
**Estimated GC reduction**: significant chunk of the 43-95MB/step allocation

#### ⏸️ 3. `GetMove2` — new Dictionary per call — **SKIPPED_WARNING: full-method replacement risk**
**File**: `CondOwner.cs:4250`
```csharp
private void GetMove2()
{
    // ...
    Dictionary<string, List<CondOwner>> dictionary = new Dictionary<string, List<CondOwner>>();  // alloc every call
    // ... used as per-call cache for ship.GetCOs results by CondTrigger name
}
```
**Scale**: GetMove2 called when NPC is idle (no task) — potentially 2000-4000 calls/s
**Fix**: Reuse a per-CondOwner `temp_dictGetMove2` field (Cleared at start, not re-allocated). Same pattern as `temp_aTickersAside`/`temp_counterDict` already used in UpdateManual.
**Estimated GC reduction**: ~5-10% of per-step allocation

### 🟡 MEDIUM IMPACT

#### 4. `EndTurn` — `aCondsTemp.AddRange(aCondsTimed)` copy
**File**: `CondOwner.cs:3124`
```csharp
aCondsTemp.AddRange(aCondsTimed);  // copies all timed conditions every EndTurn
foreach (Condition item in aCondsTemp) { item.Update(elapsed, this); }
aCondsTemp.Clear();
```
**Note**: Copy exists because `Condition.Update` may modify `aCondsTimed`. If safe to iterate directly (or use a snapshot-free approach), this copy is avoidable.
**Fix**: Transpiler removing AddRange + iterating aCondsTimed directly (if Update doesn't add/remove from aCondsTimed), or use index-based iteration with count snapshot.

#### 5. `TriggeredInternal` — List + GetCOs for 3rd-party check — ✅ NON-ISSUE (verificado)
`SeekSocialDeny` **NÃO tem `CTTest3rd`** (apenas `CTTestUs`/`CTTestThem` — confirmado no interactions.json). Como este hotspot é alcançado só via `SeekSocialDeny.Triggered()`, o caminho 3rd-party que aloca `List`+`GetCOs` nunca é atingido aqui. Fix é não-issue para este caso.
> Cave: outros interactions com CTTest3rd ainda alocam — avaliar em demanda.

#### 6. `ClaimNextTask` — Dictionary + GetDockedships + IndexOf
**File**: `WorkManager.cs:289-410`
```csharp
dictionary = new Dictionary<string, List<CondOwner>>();  // per-call cache
dictionary[key] = value2.ship.GetCOs(...);  // allocates via GetCOs
// ...
list.IndexOf(value.ship.strRegID)  // O(n) string search
list.IndexOf(item.strTileShip)     // O(n) string search
interaction = DataHandler.GetInteraction(item.strInteraction);  // new Interaction
```
**Fix**: WorkClaimThrottle already skips during cooldown. When it runs, use `HashSet<string>` for docked-ship lookups instead of `List.IndexOf`.

> **⏸️ SKIPPED_WARNING (avaliado 2026-08-16):** o `Dictionary`/cache é **local de método** — inacessível por Prefix/Postfix; exigiria full-method replacement (mesma classe da GetMove2). `WorkClaimThrottle` já reduz a frequência; ganho marginal vs. risco de regression.

#### 7. `HandleHaulTask` — Dictionary + 5× GetInteraction
**File**: `CondOwner.cs:3860+`
```csharp
new COWorkHistoryDTO();
Interaction interaction = DataHandler.GetInteraction("PickupItemStack");  // ×5 different names
Dictionary<Task2, CondOwner> dictionary = new Dictionary<Task2, CondOwner>();
```
**Fix**: Reuse Dictionary; cache/reuse Interaction objects for common names.

> **⏸️ SKIPPED_WARNING (avaliado 2026-08-16):** locals de método + heap aliasing; exige Transpiler fragile em hot-path pesado. Deferido — risco de regression > ganho. `GetCOsOpt`/`SeekSocialCache` já mitigam parte do custo.

#### 8. `HandleFeedTask` — List + HashSet + List copies
**File**: `CondOwner.cs:3937+`
```csharp
new List<CondOwner>(iA.aSeekItemsForContract)  // copy
new HashSet<CondOwner>()                       // alloc
new List<CondOwner>(hashSet)                   // HashSet→List copy
new List<CondOwner>(list)                      // copy
DataHandler.GetInteraction("PickupItem")       // alloc
DataHandler.GetInteraction("Walk")              // alloc
```
**Fix**: Reuse temp collections; pool Interaction objects.

> **⏸️ SKIPPED_WARNING (avaliado 2026-08-16):** mesmo caso do #7 — locals + Transpiler em hot-path. Deferido como backlog.

#### 9. `aTickers.Remove(temp_jt)` — O(n) per ticker
**File**: `CondOwner.cs:1325`
```csharp
aTickers.Remove(temp_jt);  // O(n) scan inside while loop processing aTickers[0]
```
**Note**: This is the per-CondOwner aTickers list (not the global CrewSim.aTickers). The perf mod's NoCopy patch targets the global copy but may not address this per-NPC Remove.
**Fix**: Swap-remove (if order doesn't matter) or use Queue<JsonTicker>.

> **⏸️ SKIPPED_WARNING (avaliado 2026-08-16):** `aTickers` é **fila ordenada por `fTimeLeft`** (mantida via `Insert`/`Sort`; `aTickers[0]` é o próximo a disparar). Swap-remove QUEBRARIA a ordenação do scheduler. Trocar por `RemoveAt(0)` só evita a varredura por igualdade (ainda O(n) por shift) — ganho nulo, risco de Transpiler desnecessário. Abandonado.

### 🟢 LOW IMPACT

#### 10. `aManUpdates.Remove(aMUDel)` — O(n²) potential
**File**: `CondOwner.cs:1317`
```csharp
foreach (IManUpdater aMUDel in aMUDels) { aManUpdates.Remove(aMUDel); }  // O(n) per removal
```
**Fix**: Use swap-remove or rebuild list without nulls.

#### 11. `Interaction.aSeekItemsForContract.RemoveAt(0)` — O(n) shift
**File**: `CondOwner.cs:3208`
**Fix**: Use Queue instead of List, or swap-remove.

#### 12. `UpdateStats` — ToString allocation
**File**: `CondOwner.cs:9559`
```csharp
mapInfo["Condition"] = ((1f - _lastDamageUpdate) * 100.0).ToString("#.00") + "%";
```
**Note**: Already gated by change check. Low priority.

#### 13. `CleanupReplies` — GetInteraction("SocialCombatExitSilent")
**File**: `CondOwner.cs:3570`
**Note**: Conditional (only when replies need cleanup). Low priority.

## Priority Ranking for New Mods (as of 2026-08-16)

| Priority | Fix | Effort | Est. Impact | Estado |
|----------|-----|--------|-------------|--------|
| ✅ 1 | GetCOs reusable visitor (Prefix) | Medium | High — 15-30% GC | **DONE — GetCOsOpt** |
| ✅ 2 | SeekSocialDeny Triggered cache (Prefix on GetWork) | Low | High — 6160 obj/sec | **DONE — SeekSocialCache** |
| ⏸️ 3 | GetMove2 reusable Dictionary (Transpiler/Prefix) | Medium | Medium — 5-10% GC | **SKIPPED_WARNING** (full-method replacement risk) |
| 4 | EndTurn AddRange→direct iteration | Low | Medium | backlog |
| 5 | TriggeredInternal CTTest3rd cache | Low | Medium (se CTTest3rd ≠ null) | backlog |
| 6 | HandleHaulTask/HandleFeedTask reuse | Medium | Medium | backlog |
| 7 | aTickers swap-remove | Low | Low-Medium | backlog |
| 8 | aManUpdates remove O(n²) | Low | Low | backlog |
| 9 | UpdateStats ToString | Low | Low | backlog |
| 10 | CleanupReplies GetInteraction | Low | Low | backlog |
