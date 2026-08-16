# Ostranauts Modding Quick Reference

## Essential APIs for Common Tasks

### 🎯 Finding Things

```csharp
// All live objects
DataHandler.mapCOs[strID] -> CondOwner

// Definitions
DataHandler.GetCondOwnerDef(strID) -> JsonCondOwner
DataHandler.GetInteraction(strName) -> Interaction
DataHandler.GetCondTrigger(strName) -> CondTrigger
DataHandler.GetItemDef(strName) -> ItemDef

// Ship
condOwner.ship -> Ship
ship.ShipCO -> CondOwner
ship.strRegID -> string
ship.GetZones("IsZoneStockpile", ...) -> List<CondOwner>

// Selected crew
CrewSim.GetSelectedCrew() -> CondOwner
CrewSim.objInstance -> CrewSim
```

### 🔄 Interaction Flow

```csharp
// Create an interaction
var ia = DataHandler.GetInteraction("PickupItem", null, true);

// Set target (reflection)
ia.set_objThem(targetCO);           // Private setter - use Traverse
Traverse.Create(ia).Method("set_objThem", new object[] { targetCO }).GetValue();

// Queue on crew
crew.QueueInteraction(targetCO, ia, false);

// Trigger directly
ia.Triggered(crew, targetCO);
```

### 📦 Container / Inventory

```csharp
// Container component
var container = condOwner.objContainer;
var grid = container.gridLayout;  // GridLayout(width, height)
var coFit = container.CanFit(item, false, false, false);
var allowed = container.AllowedCO(item);
var contents = container.GetCOs(true, null);

// Item footprint
Container.GetSpace(item) -> int  // width * height
```

### 🚢 Ship Operations

```csharp
// Docking
var ports = ship.GetAvailableDockingPorts(otherShip, false);
CrewSim.objInstance.PositionShipsAtAirlock(shipA, shipB, portA, portB);
ship.IsDocked(false) -> bool

// Navigation
GUIOrbitDraw.ImportNavDataCO(coDevice, coNavData);

// Ship from CondOwner
var ship = condOwner.ship;
var shipCO = ship.ShipCO;
```

### ⚡ Power / Batteries

> **Mapa completo do workflow de bateria (bug Forbidden:Carried, PledgeRecharge, give-contract):**
> veja [`ostranauts-battery-workflow.md`](./ostranauts-battery-workflow.md)

```csharp
// Powered component
var pwr = condOwner.pwr;  // Powered component
pwr.PowerRechargeAmount -> float
pwr.ctRecharge -> CondTrigger
pwr.Recharge();
var jsonPI = pwr.jsonPI;  // JsonPowerInfo
```

### 📋 Job / Duty System

```csharp
// Task2 for hauling
task.AssignHaulZone(coHauler, coTarget) -> Interaction
task.strTileShip -> string  // Target ship regID
task.nTile -> int           // Target tile index

// Job paint UI
GUIPDA.ShowJobPaintUI(string btn);
GUIPDA.HideJobPaintUI();

// Gig manager
GigManager.aJobs -> List<JsonJobSave>
GigManager.Init(JsonJobSave[]);
```

### 🎮 Game State

```csharp
// Game state
CrewSim.bLoaded -> bool
CrewSim.bRaiseUI -> bool
Time.timeScale -> float
CrewSim.ResetTimeScale();
CrewSim.SetPaused(bool);  // Via reflection

// Save/Load
var savePath = Application.persistentDataPath + "/saves/";
LoadManager.SaveGame("saveName");
CrewSim.objInstance.DoLoadGame(...);
```

### 💬 UI / Notifications

```csharp
// Tooltip popup
GUILoadingPopUp.ShowTooltip("Message", "Title");
GUILoadingPopUp.ShowTooltip("Message", "Title", 3f);

// PDA
GUIPDA.OpenApp("Inventory");

// Nav station
GUIComputer2.Show();
```

### 🧩 Conditions

```csharp
// Check conditions
co.HasCond("IsCarried")
co.HasCond("IsInstalled")
co.HasCond("IsLocked")

// Get/set
co.GetCondAmount("IsStacking")
co.SetCondAmount("IsCarried", 1.0);
co.AddCondAmount("IsStacking", 1.0);
co.ZeroCondAmount("IsCarried");

// Important conds for containers
"IsLocked", "IsCarried", "IsInstalled", "IsStacking"
"IsZoneStockpile", "IsZoneCrewQuarters"
```

### 🪞 Reflection Helpers

```csharp
// Private fields
Traverse.Create(obj).Field("_fieldName").GetValue<T>()
Traverse.Create(obj).Field("_fieldName").SetValue(value)

// Private properties
Traverse.Create(obj).Property("PropertyName").GetValue<T>()
Traverse.Create(obj).Property("PropertyName").SetValue(value)

// Private methods
Traverse.Create(obj).Method("MethodName", new object[] { arg }).GetValue()
```

### 🔧 Harmony Patches

```csharp
// Prefix (can skip original)
static bool Prefix(ref bool __result) { return true; }

// Postfix (modify result)
static void Postfix(ref bool __result) { __result = true; }

// Instance access
static void Postfix(TargetType __instance) { ... }
```

## Common Pitfalls

1. **Private setters**: `Interaction.set_objThem`, `Interaction.set_objUs`, `CrewSim.set_Paused` — need Traverse.Create
2. **Private getters**: `Interaction.get_objThem`, `Interaction.get_objUs` — same
3. **Static vs Instance**: `CrewSim.objInstance` for instance, `CrewSim.GetSelectedCrew()` for static
4. **DLL References**: Use absolute Linux paths (`/home/daviaaze/.local/share/Steam/...`) not symlinks (`~/.steam/steam/...`)
5. **NuGet unavailable**: Can't use PackageReference for BepInEx — must reference local DLLs
6. **MSBuild**: Needs `<LangVersion>9.0</LangVersion>` for `new()` target-typed expressions
