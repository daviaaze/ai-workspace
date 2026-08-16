# Ostranauts Mod Replacement Plan

> Game version: **1.0.0.9** | BepInEx: **5.4.23.5**
> Last updated: 2026-08-11

## Summary

18 Steam Workshop mods are installed but most target old game versions (0.15.x or 1.0.0.x). This plan categorizes each mod by **replacement strategy** and **priority**, then provides implementation details.

---

## Modding System Overview

Ostranauts supports two mod types:

### 1. Data Mods (JSON)
- **Location**: `Ostranauts_Data/Mods/YourModName/`
- **What they can do**: Add/modify items, interactions, conditions, pledges, loot tables, ships, rooms, jobs, careers, music, sprites
- **No code required** — pure JSON files
- **Load order**: Controlled by `loading_order.json`
- **Override system**: Later mods override earlier ones with same `strName`

### 2. C# Mods (BepInEx + Harmony)
- **Location**: `BepInEx/plugins/YourMod.dll`
- **What they can do**: Patch game code at runtime, add UI, intercept methods, add new systems
- **Requires**: Visual Studio 2022, .NET desktop dev + Game dev with Unity workloads
- **Harmony patch types**: Prefix (before), Postfix (after), Transpiler (IL code), Finalizer

### 3. Hybrid Mods (DLL + JSON)
- Some mods use a DLL plugin for logic AND JSON data files for content
- Example: SmarterHauling has C# patches + `Autoload.Meta.toml` + JSON data

---

## Replacement Categories

### Category A: Data-Only Replacements (JSON)
These mods add items/systems that can be fully expressed as JSON data:

| Mod | Author | Old Ver | Replacement Strategy |
|-----|--------|---------|---------------------|
| **Solar Panels** | Edgaras Malevic | 0.1.8 | Add solar panel items + power conditions + installable |
| **EVA Lockers** | Edgar Malevic | 0.1.6 | Add locker items + storage interactions |
| **Props** | Edgar Malevic | 0.1.8 | Add prop items (3D models) + condowner overlays |
| **Ship's Water** | Valtorra | 0.14.1 | Add water items + interactions + conditions |
| **Auto Airlock** | mrkmg | 1.0.4 | Add airlock controller item + pump item + interactions |
| **Pickup Order** | mrkmg | 1.0.1 | Add "Pick" job/pledge via JSON |

### Category B: C# Required (BepInEx/Harmony)
These mods need code patches for UI, automation, or game logic:

| Mod | Author | Old Ver | Replacement Strategy |
|-----|--------|---------|---------------------|
| **Auto Dock** | mrkmg | 1.3.0 | Patch `NavStation` to auto-docking when target locked |
| **Smart Orders** | mrkmg | 3.0.0 | Patch hauling AI for batch item collection |
| **Idle Pause** | mrkmg | 1.3.0 | Patch game loop to pause when selected actor idle |
| **Peeky** | mrkmg | 1.1.0 | Patch tooltip system to show container contents on hover |
| **Visor Tasks** | mrkmg | 1.0.0 | Patch visor overlay to keep task markers visible |
| **Auto Navigate** | mrkmg | 1.2.0 | Patch `NavStation` for auto-navigation to locked target |
| **Uninstall and Haul** | brokenSens | 1.2.9 | Patch job system for UHAL order |
| **Battery Charge Fix** | brokenSens | 1.0.5 | Patch battery swap behavior to use chargers |
| **AstroAPI** | Hvizeu | 0.6.3 | Rebuild as shared library mod |
| **Astro UI** | Hvizeu | 0.5.1 | Rebuild UI scaling system |

### Category C: Already Have Replacements
These Thunderstore mods already replace workshop functionality:

| Workshop Mod | Thunderstore Replacement |
|-------------|------------------------|
| Smart Orders (partial) | **SmarterHauling** (batch hauling + container prefs) |
| (dependency) | **LaunchControl** (shared toolkit) |

---

## Data Mod JSON Reference

### Item Structure
```json
[{
  "strName": "ItmMyItem",
  "strImg": "ItmMyItem",
  "strImgNorm": "ItmMyItemn",
  "strImgDamaged": "",
  "strDmgColor": "DamageTintDefault",
  "fZScale": 0.25,
  "nCols": 3,
  "aSocketAdds": ["TILItemAdds", "TILItemAdds", "TILItemAdds"],
  "aSocketForbids": ["Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "TILItemForbids", "TILItemForbids", "TILItemForbids", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank"],
  "aSocketReqs": ["Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank", "Blank"]
}]
```

### COOverlay Structure
```json
[{
  "strName": "ItmMyItem",
  "strNameFriendly": "My Item",
  "strDesc": "Description here.",
  "strImg": "ItmMyItem",
  "strImgNorm": "ItmMyItemn",
  "strPortraitImg": "ItmMyItem",
  "strCOBase": "ItmTool01"
}]
```

### Interaction Structure
```json
[{
  "strName": "ACTMyAction",
  "strTitle": "My Action",
  "strDesc": "[us] [does something] to [them].",
  "strTooltip": "Tooltip description",
  "strActionGroup": "Work",
  "strTargetPoint": "use",
  "strDuty": "Repair",
  "strUseCase": "Normal",
  "fTargetPointRange": 1,
  "strIdleAnim": "Tooling",
  "strMapIcon": "IcoRepair",
  "fDuration": 2.7e-05,
  "strThemType": "Other",
  "nLogging": 1,
  "bIgnoreFeelings": true,
  "bHumanOnly": true,
  "LootCTsUs": "CTToolSparkOn",
  "LootCTsThem": null
}]
```

### Pledge Structure
```json
[{
  "strName": "AIMyBehavior",
  "strNameFriendly": "My Behavior",
  "strType": "repeat",
  "strIATrigger": "MyTriggerCondition",
  "aIAEnd": ["PLGMyBehaviorFinished"],
  "strThemID": null,
  "nPriority": 11
}]
```

### CondTrigger Structure
```json
[{
  "strName": "CTMyTrigger",
  "strCondName": "",
  "fChance": 1.0,
  "fCount": 1.0,
  "aReqs": [],
  "aForbids": [],
  "aTriggers": [],
  "bAND": true
}]
```

### Loot Structure
```json
[{
  "strName": "LootMyItems",
  "aCOs": ["ItmMyItem=1.0x1"],
  "aLoots": [],
  "strType": "item"
}]
```

---

## C# Mod Development Reference

### Template Plugin Structure
```csharp
[BepInPlugin("com.yourname.yourmod", "Your Mod", "1.0.0")]
public class YourModPlugin : BaseUnityPlugin
{
    internal static new ManualLogSource Logger;
    private Harmony _harmony;

    private void Awake()
    {
        Logger = base.Logger;
        _harmony = new Harmony("com.yourname.yourmod");
        _harmony.PatchAll(typeof(YourModPlugin).Assembly);
    }
}
```

### Harmony Patch Types
```csharp
// Prefix - runs before original method, can skip original with return false
[HarmonyPatch(typeof(TargetClass), "TargetMethod")]
[HarmonyPrefix]
static bool Prefix(TargetClass __instance, ref float __result) { /* ... */ }

// Postfix - runs after original method
[HarmonyPatch(typeof(TargetClass), "TargetMethod")]
[HarmonyPostfix]
static void Postfix(TargetClass __instance, ref float __result) { /* ... */ }

// Transpiler - modifies IL code (advanced)
[HarmonyPatch(typeof(TargetClass), "TargetMethod")]
[HarmonyTranspiler]
static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions) { /* ... */ }
```

### Key Game Classes to Patch
| Class | Purpose |
|-------|---------|
| `Item` | Item objects and behavior |
| `CondOwner` | Base class for objects with conditions |
| `DataHandler` | Loads game data from JSON |
| `Character` | Crew members and AI |
| `Ship` | Ship systems and structure |
| `Interaction` | Player actions and interactions |

### Required NuGet References
- `BepInEx.BaseLib`
- `BepInEx.Core`
- `HarmonyX`
- `UnityEngine.Modules` (for Unity types)

### .csproj Setup
```xml
<PropertyGroup>
    <AssemblyName>YourModName</AssemblyName>
    <RootNamespace>YourNamespace.YourModName</RootNamespace>
    <GameDir>D:\Steam\steamapps\common\Ostranauts</GameDir>
</PropertyGroup>
<Reference Include="Assembly-CSharp">
    <HintPath>$(GameDir)\Ostranauts_Data\Managed\Assembly-CSharp.dll</HintPath>
</Reference>
```

---

## Implementation Priority

### Phase 1: Quick Wins (Data Mods)
1. **Solar Panels** — Add solar panel items, power conditions, installable
2. **EVA Lockers** — Add locker items with storage interactions
3. **Auto Airlock** — Add airlock controller + pump items
4. **Pickup Order** — Add "Pick" job via JSON pledge

### Phase 2: Quality of Life (C# Mods)
5. **Idle Pause** — Simple Harmony patch on game loop
6. **Battery Charge Fix** — Patch battery swap interaction
7. **Peeky** — Patch tooltip system

### Phase 3: Advanced Systems (C# Mods)
8. **Smart Orders** — Patch hauling AI (or enhance SmarterHauling)
9. **Auto Dock** — Patch NavStation
10. **Auto Navigate** — Patch NavStation
11. **Visor Tasks** — Patch visor overlay
12. **Uninstall and Haul** — Patch job system

### Phase 4: Framework Mods
13. **AstroAPI** — Shared library
14. **Astro UI** — UI scaling system

### Phase 5: Cosmetic (Data Mods)
15. **Props** — Add prop items + condowner overlays
16. **Ship's Water** — Add water system items + interactions

---

## Tools Needed for C# Mods

| Tool | Purpose | Download |
|------|---------|----------|
| **Visual Studio 2022 Community** | C# IDE | https://visualstudio.microsoft.com/ |
| **dnSpy** | Decompile game code | https://github.com/dnSpy/dnSpy/releases |
| **BepInEx 5.x** | Mod loader | https://github.com/BepInEx/BepInEx/releases |
| **Git** | Version control | https://git-scm.com/ |
| **tcli** | Thunderstore publishing | `dotnet tool install -g tcli` |

---

## Notes

- **Solar Panels** source: https://github.com/EsMM27/SolarPanels_Ostranauts (can study for reference)
- **SmarterHauling** source: https://github.com/bitMuse-Ostranauts/SmarterHauling (hybrid mod example)
- **LaunchControl** source: https://github.com/bitMuse-Ostranauts/LaunchControl (C# mod example)
- **TemplateExample**: https://github.com/bitMuse-Ostranauts/TemplateExample (starter template)
- **Ostranauts Wiki**: https://ostranauts.wiki.gg/wiki/Modding
- **Base game data reference**: `Ostranauts_Data/StreamingAssets/data/` (30+ data types)
