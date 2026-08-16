# Ostranauts Game API Reference

> Decompiled from Assembly-CSharp.dll — for C# mod development

---

## CondOwner (The Unified Object System)

Almost everything in the game is a `CondOwner`. Items, crew, containers, rooms, ships — all are `CondOwner` instances.

### Key Properties
```csharp
public string strID           // Unique ID (e.g., "ICO12345")
public string strName         // Internal name
public string strNameFriendly  // Display name
public string strCODef        // Definition ID (e.g., "ItmBackpack02a")
public Transform tf           // Unity transform
public Ship ship              // Ship this CO belongs to
public bool bDestroyed        // Is destroyed
public bool bAlive            // Is alive
public Container objContainer // Container component (if any)
public Slots compSlots        // Slot component (if any)
public List<Interaction> aQueue  // Interaction queue
public List<Priority> aPriorities // Priority list
public Room currentRoom       // Current room
public CondOwner objCOParent  // Parent CO
public bool Selected          // Is currently selected
public bool Highlight         // Is highlighted
public Item Item              // Item component (cached)
public Crew Crew              // Crew component (cached)
public Pathfinder Pathfinder  // Pathfinder component (cached)
```

### Conditions (Stat/Is/Dc/Thresh)
```csharp
public bool HasCond(string strName)              // Check if has condition
public bool HasCond(string strName, bool isThreshold)
public double GetCondAmount(string strName)       // Get condition value
public void SetCondAmount(string strName, double dAmount, double dAge = 0.0)
public void AddCondAmount(string strName, double fAmount, double fAge = 0.0, float fCondRuleTrack = 0f)
public void ZeroCondAmount(string strName)        // Remove condition
public bool IsThreshold(string condName)
public void AddCondRule(string strCondRule, bool bApplyEffects = true)
```

### Interaction Queue
```csharp
public bool QueueInteraction(CondOwner objTarget, Interaction objInteraction, bool bInsert = false)
public void ClearInteraction(Interaction objInteraction, bool bCancelling = false)
public Interaction GetInteraction(string strN = null, CondOwner objTarget = null)
public Interaction GetInteractionCurrent()
public int QueueCount                          // Number of queued interactions
public bool bBusy                              // Has queued interactions
```

### Inventory / Containment
```csharp
public CondOwner AddCO(CondOwner objCO, bool bEquip, bool bOverflow, bool bIgnoreLocks)
public CondOwner RemoveCO(CondOwner objCO, bool bForce = false)
public int CanStackOnItem(CondOwner objIncoming)  // Returns stack space available
public CondOwner DropCO(CondOwner objCO, bool bAllowLocked, Ship objShipRef = null, ...)
public CondOwner RootParent(string strCond = null)
public Slot GetSlotParent()
public List<CondOwner> GetLotCOs(bool bSubItems)
public void AddLotCO(CondOwner co)
public CondOwner RemoveLotCO(CondOwner co)
public int LotCount
```

### Tickers (Timed Events)
```csharp
public void AddTicker(JsonTicker jtNew)
public JsonTicker RemoveTicker(string strTicker)
public void SetTicker(string strTicker, float fTimeLeft)
public double GetTickerTimeleft(string strTicker)
public JsonTicker GetTicker(string strTicker)
public bool HasTickers()
```

### Pledges
```csharp
public void AddPledge(Pledge2 pledge)
public void RemovePledge(Pledge2 pledge)
public bool HasPledge(Pledge2 pledge)
public List<Pledge2> GetPledgesOfType(JsonPledge jp)
```

### Other
```csharp
public void Destroy()
public void SetData(JsonCondOwner jid, bool bLoot = true, JsonCondOwner jCOSave = null)
public void UpdateManual(int maxRepeats = 10)
public void EndTurn()
public void LogMessage(string strMsg, string strColor, string strID)
public void SetHighlight(float fAmount)
public void ModeSwitch(CondOwner coNew, Vector3 vDropPos)
public void Use(string strUseCase)
```

---

## Task2 (Hauling / Duty System)

Represents an assigned task for crew. The key method for hauling mods.

### Key Methods
```csharp
public Interaction AssignHaulZone(CondOwner coHauler, CondOwner coTarget)
// Determines where hauled items go. Returns null if no valid zone found.
// __instance.strTileShip = ship regID
// __instance.nTile = tile index

public Interaction GetIA()
public void SetIA(Interaction ia)
public bool Matches(string strIA, string strTarget)
public string GetIconName()
public Allowed GetOwnership(string strID)
public void AddOwner(string strID)
```

### Key Fields (via reflection)
```csharp
public string strTileShip    // Target ship regID
public int nTile             // Target tile index
public string strDuty        // Duty type (Haul, Work, Fight, etc.)
public string strInteraction // Interaction name
public string strName        // Task display name
public string strTargetCOID  // Target CO ID
```

---

## Interaction (Actions)

An action that can be performed by a CondOwner on another.

### Key Properties
```csharp
// All require reflection (private getters/setters):
public CondOwner objUs       // The doer
public CondOwner objThem     // The target
public string strName        // Interaction name (e.g., "Walk", "PickupItem")
public float fDuration       // How long it takes
public CondTrigger CTTestUs  // Requirements for doer
public CondTrigger CTTestThem // Requirements for target
public bool bOpener          // Is a door opener
```

### Key Methods
```csharp
public bool Triggered(CondOwner objUs, CondOwner objThem, bool bStats = false, ...)
public bool Triggered(bool bStats = false, bool bIgnoreItems = false, bool bCheckPath = false)
public void ApplyEffects(List<string> aLog = null, bool isCancelIa = false)
public void ApplyChain(List<string> aLog = null)
public Interaction Destroy()
public JsonInteractionSave GetJSONSave()
public int GetAnim(CondOwner co = null)
```

---

## Container (Item Storage)

Manages grid-based inventory for items, characters, and rooms.

### Key Properties
```csharp
public GridLayout gridLayout   // Grid dimensions (width, height)
public CondOwner CO             // The CondOwner this container belongs to
public bool Locked => CO.HasCond("IsLocked")
public TrackingCollection<CondOwner> aCOs  // Contained items (private)
```

### Key Methods
```csharp
public bool AllowedCO(CondOwner coIn)   // Check if item is allowed in
public bool CanFit(CondOwner coFit, bool bAuto, bool bSub, bool bAllowLocked)
// Returns true if item fits in remaining grid space

public static int GetSpace(CondOwner co)  // Item footprint (width * height)
public CondOwner AddCO(CondOwner objCO)
public CondOwner RemoveCO(CondOwner objCO, bool bForce = false)
public bool Contains(CondOwner co)
public List<CondOwner> GetCOs(bool bAllowLocked, CondTrigger objCondTrig = null)
public void VisitCOs(CondOwnerVisitor visitor, bool bAllowLocked)
public bool CanAddSimple(CondOwner objCO, out PairXY pairXY)
public void AddCOSimple(CondOwner objCO, PairXY pairXY)
public void Redraw()
public static void Redraw(Container container)
```

---

## Ship

Represents a ship in the game world.

### Key Properties
```csharp
public CondOwner ShipCO         // The ship's CondOwner
public ShipSitu objSS           // Ship situation (position, orbit)
public string strRegID          // Registration ID
public bool bDocked => IsDocked()
public Comms Comms
public DamageSystem DamageSystem
public WeaponsSystem WeaponsSystem
public ElectronicSystems ElectronicSystems
```

### Key Methods
```csharp
public bool IsDocked(bool bCheck = true)
public List<ValueTuple<string, string>> GetAvailableDockingPorts(Ship shipOther, bool bCheckDocked)
public void PositionShipsAtAirlock(Ship shipA, Ship shipB, string strPortA, string strPortB)
// Docks two ships together

public List<CondOwner> GetPeople(bool bAllowDocked)
public List<CondOwner> GetPeopleInRoom(Room room, CondTrigger ct = null)
public List<CondOwner> GetZones(string strCond, CondTrigger ct = null)
// Get stockpile zones: GetZones("IsZoneStockpile", ...)

public Room GetRoomAtWorldCoords1(Vector2 vPos, bool bAllowDocked)
public Tile GetTileAtWorldCoords1(float x, float y, bool bAllowDocked)
public void VisitCOs(CondTrigger objCondTrig, bool bSubObjects, bool bAllowDocked, bool bAllowLocked, Action<CondOwner> visitor)
public void VisitCOs(CondOwnerVisitor visitor, bool bSubObjects, bool bAllowDocked, bool bAllowLocked)

public void AddCO(CondOwner objICO, bool bTiles)
public void RemoveCO(CondOwner objICO, bool bForce = false)
public CondOwner DropCO(CondOwner objCO, Vector2 nearPosition)
public void ResetMass()
public void UpdatePower()
public void UpdateSensors()
public void UpdateTiles(CondOwner objICO, bool bRemove, bool skipRepositioning = false)
public bool BGItemFits(Item itm)
public void BGItemAdd(Item itm)
public void BGItemRemove(Item itm)
```

---

## CrewSim (Game Manager)

The main game simulation manager. Singleton at `CrewSim.objInstance`.

### Key Properties
```csharp
public static CrewSim objInstance           // Singleton instance
public static CondOwner GetSelectedCrew()   // Currently selected crew
public static CondOwner coPlayer            // Player character
public static bool bRaiseUI                 // UI is raised
public static bool bLoaded                  // Game is loaded
public GameObject goPaintJob                // Job paint UI root

// Events:
public static UnityEvent OnGameFinishedLoading
public static UnityEvent OnGameEnd
public static UnityEvent OnTimeScaleUpdated
public static UnityEvent OnSceneFinishedLoading
```

### Key Methods
```csharp
public static CondOwner GetSelectedCrew()
public static CondOwner GetBracketTarget()
public static void AddTicker(CondOwner co)
public static void RemoveTicker(CondOwner co)

public CondOwner GetRandomCrew(Tile til = null)
public void SetBracketTarget(string strID, bool bUpdateOnly, bool noAuto = false)
public void SetPaused(bool value)            // Via Traverse (private setter)
public void ResetTimeScale()
public void CycleCrew()

// Save/Load:
public void LoadGame(string fileName, string strShipsFolder, Dictionary<string, byte[]> dictFiles = null)
public void LoadGame(SaveInfo saveInfo)
```

### WorkManager (nested in CrewSim)
```csharp
// Handles job assignment and duty management
```

---

## DataHandler (Data Registry)

Loads and manages all game data (JSON + mods).

### Key Static Properties
```csharp
public static Dictionary<string, CondOwner> mapCOs  // All live CondOwners
public static bool bLoaded                             // Data is loaded
public static Dictionary<string, JsonCondOwner> dictCondOwnerDefs
public static Dictionary<string, JsonInteraction> dictInteractions
public static Dictionary<string, JsonCondTrigger> dictCondTriggers
public static Dictionary<string, JsonItemDef> dictItemDefs
```

### Key Methods
```csharp
public static CondOwner GetCondOwnerDef(string strID)
public static Interaction GetInteraction(string strName, JsonInteractionSave jis = null, bool bCheckMods = true)
public static CondTrigger GetCondTrigger(string strName)
public static ItemDef GetItemDef(string strName)
public static Loot GetLoot(string strName)
public static string GetString(string strName)
public static JsonCondOwner GetCondOwnerDef(string strID)
public static PersonSpec GetPersonSpec(string strName)

// Save/Load:
public static string SaveFileExists(string strFileName)
public static JsonGameSave LoadSaveFile(string strFileName)
public static JsonGameSave LoadSaveFile(string strFileName, Dictionary<string, byte[]> dictFiles)
```

---

## GUIComputer2 (Nav Station Computer)

The nav station computer UI. Shows ship modules, nav data, etc.

### Key Methods
```csharp
public override void Init(CondOwner coSelf, Dictionary<string, string> mapGPMData, string strGPMKey)
public IEnumerator ShowNAVDevices(CondOwner coAutoSelect)
public override void SaveAndClose()
```

### UI Elements (private, via reflection)
```csharp
// Buttons: btnLeftUp, btnRightUp, btnDetailsExit
// Canvas groups: cgDel, cgMoveL, cgMoveR
```

---

## GUIPDA (PDA Interface)

The PDA with apps: home, inventory, zones, goals, roster, social, gigs.

### Key Methods
```csharp
public static void OpenApp(string appName)
public void ToggleNAV(string strRegID = null)
public void ShowJobPaintUI(string btn)      // Opens job paint screen
public void HideJobPaintUI()
public void ShowJobOptions(string strType)
public void ToggleTasks()
public void AddTask(Task2 task)
public void RemoveTask(Task2 task)
public void ToggleGig(bool bShow)
public void ToggleGigNexus()
public void ShowGig(JsonJobSave jjs, GUIPDAGigRow ggr)
public void RefreshHotbar()
```

### Properties
```csharp
public bool JobsActive => ...   // Job paint is showing
```

---

## GigManager (Job System)

Manages available gigs/contracts.

### Key Static Properties
```csharp
public static List<JsonJobSave> aJobs    // All available jobs
```

### Key Methods
```csharp
public static void Init(JsonJobSave[] aJobsIn)
```

---

## Powered (Battery/Charging Component)

For items that use power (batteries, suits, etc.).

> **Workflow completo / bug do `Forbidden: Carried`:** veja [`ostranauts-battery-workflow.md`](./ostranauts-battery-workflow.md)

### Key Properties
```csharp
public float PowerRechargeAmount    // How fast it recharges
public CondTrigger ctRecharge       // Recharge CondTrigger
public bool IsReadyRecharge => ...  // Ready to recharge
```

### Key Methods
```csharp
public void Recharge()
public JsonPowerInfo jsonPI          // Power info
```

---

## JsonZone (Zone Data)

Represents a room or zone on a ship.

### Key Properties
```csharp
public string strName
public int[] aTiles                 // Tile indices in this zone
public CondTrigger ctCond           // Zone condition/type
public List<CondOwner> aCOs         // COs in zone (via reflection)
```

---

## Room

A room on a ship.

### Key Properties
```csharp
public CondOwner CO                 // Room's CondOwner
public string strRegID
```

### Key Methods
```csharp
```

---

## Item Component

The Item component attached to CondOwners that are items.

### Key Properties
```csharp
public int nWidthInTiles
public int nHeightInTiles
public List<Visibility> aLights
public Dictionary<Transform, SpriteRenderer> dictLightSprites
```

---

## JsonJobSave (Gig Data)

Represents a saved gig/contract.

### Key Properties
```csharp
public string strJobName
public string strJobItems
public bool bTaken
public bool bInvalid
public double fEpochOfferExpired
public string strClientID
public string strThemID
```

### Key Methods
```csharp
public Interaction GetInteractionDo(CondOwner coClient, CondOwner coPlayer)
public JsonJobSave Clone()
public void set_bInvalid(bool value)
```

---

## GUIOrbitDraw (Navigation Orbit UI)

The orbit/navigation display.

### Key Static Methods
```csharp
public static void ImportNavDataCO(CondOwner coDevice, CondOwner coNavData)
// Navigate to a target
```

---

## GUILoadingPopUp (Tooltip/Popup)

Shows tooltip popups on screen.

### Key Static Methods
```csharp
public static void ShowTooltip(string strMessage, string strTitle)
public static void ShowTooltip(string strMessage, string strTitle, float fDuration)
```

---

## LoadManager (Save/Load)

Manages game saves.

### Key Methods
```csharp
public void SaveGame(string saveName, int autosaveCounter = 0, bool useThreading = false)
public IEnumerator DoLoadGame(string fileName, string strShipsFolder, Dictionary<string, byte[]> dictFiles = null)
```

---

## Common Condition Types

| Condition | Description |
|-----------|-------------|
| `IsHuman` | Is a human |
| `IsRobot` | Is a robot |
| `IsPlayer` | Is the player character |
| `IsPlayerCrew` | Is player-controlled crew |
| `IsCarried` | Is being carried |
| `IsInstalled` | Is installed in a slot |
| `IsLocked` | Container is locked |
| `IsStacking` | Item is stackable |
| `IsZoneStockpile` | Zone is a stockpile |
| `IsDead` | Is dead |
| `IsDestroyed` | Is destroyed |
| `IsAirlockController` | Is an airlock controller |
| `IsAirlockPump` | Is an airlock pump |
| `IsAirlockDoor` | Is an airlock door |

---

## Common Interaction Names

| Interaction | Description |
|-------------|-------------|
| `Walk` | Walk to location |
| `PickupItem` | Pick up an item |
| `PickupItemStack` | Pick up a stack |
| `DropItem` | Drop an item |
| `DropItemStack` | Drop a stack |
| `ACTHaulItem` | Haul item to storage |
| `Uninstall` | Uninstall an item |
| `Install` | Install an item |
| `Use` | Use an item |
| `Open` | Open a door/container |
| `Close` | Close a door/container |
| `Talk` | Talk to someone |
| `Fight` | Fight someone |
| `Work` | Perform work |
| `Wait` | Wait |

---

## Harmony Patch Patterns

### Prefix (before method runs)
```csharp
[HarmonyPatch(typeof(TargetType), "MethodName")]
public static class PatchClass
{
    static bool Prefix(TargetType __instance, ref bool __result)
    {
        // Return true to run original, false to skip
        return true;
    }
}
```

### Postfix (after method runs)
```csharp
[HarmonyPatch(typeof(TargetType), "MethodName")]
public static class PatchClass
{
    static void Postfix(TargetType __instance, ref bool __result)
    {
        // __result can be modified
    }
}
```

### Accessing Private Members
```csharp
// Fields:
Traverse.Create(__instance).Field("fieldName").GetValue<T>()
Traverse.Create(__instance).Field("fieldName").SetValue(value)

// Properties:
Traverse.Create(__instance).Property("PropertyName").GetValue<T>()

// Methods:
Traverse.Create(__instance).Method("MethodName", new object[] { arg }).GetValue()
```

---

## Mod Setup Template

```csharp
[BepInPlugin("com.yourmod.plugin", "Your Mod", "1.0.0")]
public class YourModPlugin : BaseUnityPlugin
{
    public void Awake()
    {
        var harmony = new Harmony("com.yourmod.harmony");
        harmony.PatchAll();
        Logger.LogInfo("Your Mod loaded!");
    }
}
```

### csproj Template
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>netstandard2.1</TargetFramework>
    <AssemblyName>YourMod</AssemblyName>
    <LangVersion>9.0</LangVersion>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include="BepInEx">
      <HintPath>/home/daviaaze/.local/share/Steam/steamapps/common/Ostranauts/BepInEx/core/BepInEx.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <Reference Include="0Harmony">
      <HintPath>/home/daviaaze/.local/share/Steam/steamapps/common/Ostranauts/BepInEx/core/0Harmony.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <Reference Include="Assembly-CSharp">
      <HintPath>/home/daviaaze/.local/share/Steam/steamapps/common/Ostranauts/Ostranauts_Data/Managed/Assembly-CSharp.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <Reference Include="UnityEngine">
      <HintPath>/home/daviaaze/.local/share/Steam/steamapps/common/Ostranauts/Ostranauts_Data/Managed/UnityEngine.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <Reference Include="UnityEngine.CoreModule">
      <HintPath>/home/daviaaze/.local/share/Steam/steamapps/common/Ostranauts/Ostranauts_Data/Managed/UnityEngine.CoreModule.dll</HintPath>
      <Private>False</Private>
    </Reference>
  </ItemGroup>
</Project>
```
