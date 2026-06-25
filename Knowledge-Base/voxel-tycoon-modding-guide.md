# Voxel Tycoon Modding Guide — Best Practices & Guidelines

> **Based on:** Decompiled game source analysis + Route Highlighter Mod review  
> **Game Version:** Current Steam build (as of 2026-05-22)  
> **Target Framework:** .NET Standard 2.1  
> **Unity Version:** 2022 LTS (inferred from API surface)

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Project Structure](#2-project-structure)
3. [Core Game Architecture](#3-core-game-architecture)
4. [Mod Entry Point](#4-mod-entry-point)
5. [Managers — Background Systems](#5-managers--background-systems)
6. [Windows — UI Framework](#6-windows--ui-framework)
7. [Tools — Interactive Modes](#7-tools--interactive-modes)
8. [Hotkeys & Input](#8-hotkeys--input)
9. [Working with Game Data](#9-working-with-game-data)
10. [Reflection for Resilience](#10-reflection-for-resilience)
11. [Harmony Patching](#11-harmony-patching)
12. [Common Pitfalls](#12-common-pitfalls)
13. [Testing Checklist](#13-testing-checklist)
14. [Reference — Key Types](#14-reference--key-types)

---

## 1. Getting Started

### 1.1 Prerequisites

```bash
# .NET SDK 8.0 (builds netstandard2.1)
nix shell nixpkgs#dotnet-sdk_8 --command dotnet --version

# Game installation path
export VoxelTycoonManagedLibraryDirectory="$HOME/.steam/steam/steamapps/common/VoxelTycoon/VoxelTycoon_Data/Managed"
```

### 1.2 Minimal Project Structure

```
MyMod/
├── MyMod.csproj              # netstandard2.1, references game DLLs
├── mod.json                  # Pack metadata (REQUIRED)
├── MyModEntry.cs             # Mod class (entry point)
├── MyModManager.cs           # Manager<T> for background logic
└── Directory.Build.props     # Shared MSBuild properties (optional)
```

### 1.3 mod.json Format

```json
{
  "Title": "My Awesome Mod",
  "Description": "Does cool things",
  "Tags": [ "Gameplay", "UI" ],
  "Hidden": false
}
```

**Critical:** Keys must match `LocalPack.Metadata`: `Title`, `Description`, `Tags`, `Hidden`. Wrong keys = mod won't appear in the list.

### 1.4 Install Path

```bash
GAME_DIR="$HOME/.local/share/Steam/steamapps/common/VoxelTycoon"
cp bin/Release/netstandard2.1/MyMod.dll mod.json "$GAME_DIR/Content/MyMod/"
```

**Must restart the game** — mods load at startup via `PackFetcher.AddLocalPacks()`.

---

## 2. Project Structure

### 2.1 Naming Conventions

| Pattern | Example | Purpose |
|---------|---------|---------|
| `*Manager.cs` | `RouteHighlighterManager` | Background system with Update loop |
| `*Tool.cs` | `RouteHighlighterTool` | Interactive mode (ITool) |
| `*Window.cs` | `RouteViewWindow` | UI window (RichWindow/MonoBehaviour) |
| `*Info.cs` / `*Alert.cs` | `RouteAlert` | Plain data classes |
| `*Patches.cs` | `RouteViewPatches` | Harmony patch collections |
| `*Settings.cs` | `RouteHighlighterSettings` | SettingsMod subclass |
| `*Hotkeys.cs` | `RouteHighlighterHotkeys` | Static hotkey configuration |

### 2.2 File Organization

```
# Good — one concern per file
RouteHighlighterMod.cs       # Entry point only
RouteHighlighterManager.cs   # Speed overlays only
RouteMonitorManager.cs       # Route analysis only
RouteViewWindow.cs           # Route view UI only

# Bad — mixing concerns
Mod.cs                       # Entry point + manager + window all in one
```

---

## 3. Core Game Architecture

### 3.1 Type Hierarchy

```
MonoBehaviour
  ├── Manager<T>           → Singleton, has OnUpdate(), OnLateUpdate()
  │     └── YourManager
  ├── Building
  │     └── VehicleStation → PassengerCount, Name, transform
  ├── TrackUnit            → base vehicle, Path (field!), Points (field!)
  │     └── Vehicle        → Velocity, VelocityLimit, Route, Schedule
  └── Window
        ├── Frame          → Base for all UI frames
        ├── MovingFrame    → Draggable
        └── RichWindow     → Title bar, close button, content container
```

### 3.2 Manager<T> — The Singleton Pattern

```csharp
public class MyManager : Manager<MyManager>
{
    // Called once when Manager<T>.Initialize() is invoked
    protected override void OnInitialize() { }

    // Called every frame via UpdateBehaviour
    protected override void OnUpdate() { }

    // Called every frame after Update
    protected override void OnLateUpdate() { }

    // Access anywhere:
    // MyManager.Current.DoSomething();
}
```

**Rules:**
- Call `MyManager.Initialize()` from `Mod.OnGameStarting()`
- Never call `new MyManager()` — use `Initialize()`
- `Current` is null until `Initialize()` is called
- `Current` is set to null on deinitialize

### 3.3 LazyManager<T> — Lazy Singleton

```csharp
// Auto-creates on first access
var manager = LazyManager<TrackUnitManager>.Current;
```

**Used by:** `TrackUnitManager`, `BuildingManager`, `VehicleDestinationLocationManager`, etc.

### 3.4 Lifecycle Order

```
Mod.Initialize()          → Mod entry point created
Mod.OnModsInitialized()   → All mods loaded, patch here
Mod.OnGameStarting()      → World loading begins, init managers
Mod.OnGameStarted()       → World ready, add UI buttons
[Game Running]
Manager<T>.OnUpdate()     → Every frame
Mod.OnUpdate()            → Every frame
Mod.OnLateUpdate()        → After all Updates
[Game Exit]
Mod.Deinitialize()        → Cleanup
Manager<T>.OnDeinitialize() → Cleanup
```

---

## 4. Mod Entry Point

### 4.1 Minimal Mod Class

```csharp
using VoxelTycoon.Modding;
using VoxelTycoon.Serialization;

namespace MyMod
{
    public class MyMod : Mod
    {
        protected override void OnModsInitialized()
        {
            // Harmony patches go here (all mods loaded)
            MyPatches.Initialize();
        }

        protected override void OnGameStarting()
        {
            // Initialize background systems
            MyManager.Initialize();
        }

        protected override void OnGameStarted()
        {
            // Add UI buttons, toolbar items
            MyUI.Initialize();
        }

        protected override void Read(StateBinaryReader reader)
        {
            // Load persisted state
            MyManager.Current.Enabled = reader.ReadBool();
        }

        protected override void Write(StateBinaryWriter writer)
        {
            // Save state
            writer.WriteBool(MyManager.Current.Enabled);
        }
    }
}
```

### 4.2 Persistence Rules

- `Read/Write` are called on save/load
- Use `StateBinaryReader/Writer` (NOT standard .NET serialization)
- Write version byte first for future compatibility:

```csharp
private const int SaveVersion = 1;

protected override void Write(StateBinaryWriter writer)
{
    writer.WriteByte(SaveVersion);
    writer.WriteBool(MyManager.Current.Enabled);
}

protected override void Read(StateBinaryReader reader)
{
    int version = reader.ReadByte();
    if (version >= 1)
    {
        MyManager.Current.Enabled = reader.ReadBool();
    }
}
```

---

## 5. Managers — Background Systems

### 5.1 When to Use Manager<T>

Use `Manager<T>` when you need:
- An Update loop (checked every frame)
- Global state that persists for the game session
- A singleton accessible from anywhere

### 5.2 When NOT to Use Manager<T>

Don't use `Manager<T>` for:
- One-shot initialization → use `Mod.OnGameStarted()`
- UI-only state → keep in Window class
- Static configuration → use static class

### 5.3 Manager Best Practices

```csharp
public class MyManager : Manager<MyManager>
{
    // Public state with safe defaults
    public bool Enabled { get; set; } = true;

    // Private collections
    private readonly List<GameObject> _pool = new List<GameObject>();
    private float _lastUpdateTime;

    protected override void OnUpdate()
    {
        base.OnUpdate();

        // Throttle expensive operations
        if (Time.time - _lastUpdateTime < UpdateInterval)
            return;
        _lastUpdateTime = Time.time;

        // Always wrap in try-catch to prevent crashing the game
        try
        {
            DoWork();
        }
        catch (Exception ex)
        {
            Debug.LogError($"[MyMod] Manager error: {ex.Message}");
        }
    }

    private void DoWork()
    {
        // Null-check ALL game API calls
        var companies = CompanyManager.Current?.GetAll();
        if (companies == null) return;

        // Convert struct collections to List before iterating
        var list = companies.Value.ToList();
        foreach (var company in list)
        {
            // ...
        }
    }
}
```

### 5.4 Global Hotkeys in Managers

**Correct:** Check hotkeys in `Manager<T>.OnUpdate()`

```csharp
protected override void OnUpdate()
{
    base.OnUpdate();

    var hotkey = (Hotkey)MyHotkeys.ToggleKey;
    if (ToolHelper.IsHotkeyDown(hotkey))
    {
        Enabled = !Enabled;
    }
}
```

**Wrong:** Checking in `ITool.OnUpdate()` — only runs when tool is active!

---

## 6. Windows — UI Framework

### 6.1 RichWindow (Recommended)

The game provides `RichWindow` with proper chrome:

```csharp
using VoxelTycoon.UI.Windows;

public class MyWindow : RichWindow
{
    protected internal override void InitializeFrame()
    {
        base.InitializeFrame();
        base.Title = "My Window";
        base.Width = 400f;   // Implicitly converts to Constraint
        base.Height = 300f;

        BuildContent();
    }

    private void BuildContent()
    {
        var ct = base.ContentContainer;
        if (ct == null) return;

        // Add Panel background
        var bgPanel = ct.gameObject.AddComponent<Panel>();
        UIColors.RichWindow.ContentBackground.Apply(bgPanel);
        bgPanel.CornersType = PanelCornerType.Round5;
        bgPanel.EnabledCorners = PanelCorners.Bottom;

        // Add layout group
        LayoutHelper.MakeLayoutGroup(
            ct,
            LayoutHelper.Orientation.Vertical,
            new RectOffset(11, 11, 6, 6),
            4f,
            TextAnchor.UpperLeft,
            LayoutHelper.ChildSizing.ChildControlsWidth | LayoutHelper.ChildSizing.ChildControlsHeight
        );

        // Add content...
    }
}
```

### 6.2 Opening Windows

```csharp
// Create or find existing
var window = UIManager.Current.FindWindow<MyWindow>();
if (window == null)
{
    window = UIManager.Current.CreateWindow<MyWindow>();
}

// Show or bring to front
window.ShowOrHighlight();
```

### 6.3 Window Rules

| Rule | Why |
|------|-----|
| Use `override` not `new` for `InitializeFrame()` | Ensures polymorphic call |
| Use `protected internal override void InitializeFrame()` | Matches base signature exactly |
| Access `ContentContainer` (not `transform`) for content | Proper layout integration |
| Set `Width`/`Height` before adding content | Layout calculates correctly |
| Use `Panel` + `UIColors` for backgrounds | Matches game visual style |
| Use `R.Fonts.OpenSans.*` for text | Consistent typography |

### 6.4 Common Mistake: OnUpdate in Windows

```csharp
// WRONG — Window doesn't have OnUpdate()
public class MyWindow : RichWindow
{
    protected override void OnUpdate()  // ← This won't be called!
    {
        // ...
    }
}

// CORRECT — Use MonoBehaviour.Update()
public class MyWindow : RichWindow
{
    private void Update()  // ← Called every frame by Unity
    {
        // Refresh logic here
    }
}

// CORRECT — Use a timer in the Manager
public class MyManager : Manager<MyManager>
{
    protected override void OnUpdate()
    {
        // Find window and refresh it
        var window = UIManager.Current.FindWindow<MyWindow>();
        window?.Refresh();
    }
}
```

---

## 7. Tools — Interactive Modes

### 7.1 ITool Interface

```csharp
public interface ITool
{
    void Activate();           // Called when tool becomes active
    bool OnUpdate();           // Called every frame, return true to complete
    bool Deactivate(bool soft); // Called when tool is deactivated
}
```

### 7.2 Tool Usage Patterns

**Pattern A: Toggle something (simple)**

```csharp
public class ToggleTool : ITool
{
    public void Activate()
    {
        MyManager.Current.Enabled = !MyManager.Current.Enabled;
    }

    public bool OnUpdate() => true;  // Complete immediately
    public bool Deactivate(bool soft) => true;
}
```

**Pattern B: Interactive mode (complex)**

```csharp
public class MyInteractiveTool : ITool
{
    public void Activate()
    {
        // Setup cursor, preview, etc.
    }

    public bool OnUpdate()
    {
        // Handle input, update preview
        if (Input.GetMouseButtonDown(0))
        {
            // Do the thing
            return true;  // Complete
        }
        return false;  // Keep running
    }

    public bool Deactivate(bool soft)
    {
        // Cleanup
        return true;  // Allow deactivation
    }
}
```

### 7.3 Toolbar Integration

```csharp
Toolbar.Current.AddButton(
    FontIcon.FaSolid("\uf0f6"),  // Icon
    "My Tool",                    // Tooltip title
    () => UIManager.Current.SetTool(new MyTool())  // Action
);
```

### 7.4 Important: Tools vs Buttons

The mod's current tools (`RouteHighlighterTool`, `RouteDashboardTool`, `RouteViewTool`) are **misusing** the tool system. They only serve as toolbar button wrappers — their `Activate()` opens a window, then they immediately complete.

**Better approach:** Use `Toolbar.Current.AddButton()` with a direct action:

```csharp
// Instead of creating a do-nothing tool:
Toolbar.Current.AddButton(
    FontIcon.FaSolid("\uf0f6"),
    "Route View",
    () => RouteMonitorManager.Current.ToggleRouteViewWindow()
);
```

**Only create an `ITool` if you need:**
- Cursor changes
- World interaction (clicking on tiles)
- Preview rendering
- Escape/right-click to cancel

---

## 8. Hotkeys & Input

### 8.1 Hotkey Struct

```csharp
// Simple key
var hotkey = new Hotkey(KeyCode.H);

// Key with modifier
var hotkey = new Hotkey(KeyCode.H, KeyModifier.Shift);

// Two-key combo
var hotkey = new Hotkey(
    new HotkeyValue(KeyCode.LeftControl, KeyModifier.None),
    new HotkeyValue(KeyCode.H, KeyModifier.None)
);
```

### 8.2 Persisting Hotkeys

```csharp
public static class MyHotkeys
{
    private const string PrefKey = "MyMod_Hotkey";
    private const string PrefMod = "MyMod_HotkeyMod";

    private static Setting<Hotkey>? _setting;

    public static Setting<Hotkey> ToggleKey
    {
        get
        {
            if (_setting == null)
            {
                var saved = LoadHotkey(PrefKey, PrefMod);
                _setting = new Setting<Hotkey>(saved ?? new Hotkey(KeyCode.H));
                _setting.Subscribe(h => SaveHotkey(PrefKey, PrefMod, h), raiseImmediately: false);
            }
            return _setting;
        }
    }

    private static void SaveHotkey(string keyPref, string modPref, Hotkey hotkey)
    {
        if (hotkey.Value.HasValue)
        {
            PlayerPrefs.SetInt(keyPref, (int)hotkey.Value.Value.Code);
            PlayerPrefs.SetInt(modPref, (int)hotkey.Value.Value.Modifier);
        }
        else
        {
            PlayerPrefs.DeleteKey(keyPref);
            PlayerPrefs.DeleteKey(modPref);
        }
        PlayerPrefs.Save();
    }

    private static Hotkey? LoadHotkey(string keyPref, string modPref)
    {
        if (!PlayerPrefs.HasKey(keyPref)) return null;
        return new Hotkey(
            (KeyCode)PlayerPrefs.GetInt(keyPref),
            (KeyModifier)PlayerPrefs.GetInt(modPref)
        );
    }
}
```

### 8.3 Checking Hotkeys

```csharp
// In Manager<T>.OnUpdate():
var hotkey = (Hotkey)MyHotkeys.ToggleKey;
if (ToolHelper.IsHotkeyDown(hotkey))
{
    // Toggle feature
}
```

**`ToolHelper.IsHotkeyDown()`:**
- Plays the hotkey sound automatically
- Handles modifier keys correctly
- Returns true only on the frame the key is pressed

---

## 9. Working with Game Data

### 9.1 Immutable Collections — CRITICAL

The game uses **value-type (struct) collections** that do NOT implement `IEnumerable`:

```csharp
// WRONG — won't compile (no IEnumerable)
foreach (var company in CompanyManager.Current.GetAll()) { }

// CORRECT — convert to List first
var companies = CompanyManager.Current?.GetAll();
if (companies == null) return;
var list = companies.Value.ToList();
foreach (var company in list) { }
```

| Type | Kind | Access Pattern |
|------|------|---------------|
| `ImmutableList<T>` | Struct | `.ToList()` before foreach |
| `ImmutableUniqueList<T>` | Struct | `.ToList()` before foreach |
| `Nullable<ImmutableList<T>>` | Nullable struct | Check `.HasValue`, use `.Value.ToList()` |

### 9.2 Accessing Vehicles and Routes

```csharp
// Get all companies
var companies = CompanyManager.Current?.GetAll();
if (companies == null) return;

foreach (var company in companies.Value.ToList())
{
    if (company == null) continue;

    // Get all track units for this company
    var trackUnits = TrackUnitManager.Current?.GetAll(company);
    if (!trackUnits.HasValue) continue;

    foreach (var unit in trackUnits.Value.ToList())
    {
        // Filter to vehicles with routes
        if (unit is Vehicle vehicle && vehicle.Route != null && !vehicle.Route.IsDead)
        {
            var route = vehicle.Route;
            string name = route.Name;
            Color color = route.Color;
            int vehicleCount = route.Vehicles.Count;

            // Access schedule tasks
            var tasks = vehicle.Schedule.GetTasks().ToList();
            foreach (var task in tasks)
            {
                if (task is VehicleStationTask stationTask)
                {
                    var station = stationTask.Destination?.Location?.VehicleStation;
                    if (station != null)
                    {
                        // Use station.Name (NOT DisplayName — doesn't exist!)
                        string stationName = station.Name;
                    }
                }
            }
        }
    }
}
```

### 9.3 Vehicle Properties Reference

```csharp
Vehicle vehicle = ...;

// Speed
float currentSpeed = vehicle.Velocity;        // Current speed
float maxSpeed = vehicle.VelocityLimit;       // Max possible speed
float speedRatio = vehicle.Velocity01;        // 0-1 ratio

// Route
VehicleRoute route = vehicle.Route;           // May be null
bool hasRoute = route != null;
bool routeDead = route?.IsDead ?? false;

// Schedule
VehicleSchedule schedule = vehicle.Schedule;
bool hasTasks = !schedule.IsEmpty;
VehicleTask currentTask = schedule.CurrentTask;

// Economics
float buyTime = vehicle.BuyTime;              // World time when bought
double moneyEarned = vehicle.MoneyEarnedCounter.Sum();
double runningCosts = vehicle.RunningCostsCounter.Sum();

// Consist
VehicleConsist consist = vehicle.Consist;
ImmutableList<VehicleUnit> units = consist.Units;
```

### 9.4 Station Properties Reference

```csharp
VehicleStation station = ...;

// Identity
string name = station.Name;                   // Use this, NOT DisplayName
int vehicleCount = station.VehicleCount;

// Passengers (passenger stations only)
int waiting = station.PassengerCount;         // 0 for freight-only

// Location
City closestCity = station.ClosestCity;

// Platforms
VehicleStationPlatform[] platforms = station.Platforms;
```

**Important:** `VehicleStation` does NOT have `DisplayName`. Use `Name` (inherited from `Building`).

---

## 10. Reflection for Resilience

### 10.1 Why Use Reflection

The game's API is **not officially documented**. Property/field names may change between updates. Reflection lets you discover members at runtime.

### 10.2 Reflection Cache Pattern

```csharp
public class MyManager : Manager<MyManager>
{
    private readonly Dictionary<Type, MemberInfoCache> _reflectionCache = new();

    private class MemberInfoCache
    {
        public PropertyInfo? SomeProperty;
        public FieldInfo? SomeField;
    }

    private MemberInfoCache GetCache(Type type)
    {
        if (!_reflectionCache.TryGetValue(type, out var cache))
        {
            cache = new MemberInfoCache();
            _reflectionCache[type] = cache;

            // Try known members from decompilation first (fast path)
            cache.SomeProperty = type.GetProperty("KnownProperty",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);

            // Fallback: scan all members (slow path, runs once)
            if (cache.SomeProperty == null)
            {
                foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                {
                    if (prop.Name.Contains("Some", StringComparison.OrdinalIgnoreCase))
                    {
                        cache.SomeProperty = prop;
                        break;
                    }
                }
            }
        }
        return cache;
    }
}
```

### 10.3 Critical: Fields vs Properties

From decompilation, many "obvious" members are actually **fields**:

| Member | Type | Access |
|--------|------|--------|
| `TrackUnit.Path` | `PathCollection` | **protected field** |
| `TrackUnit.Points` | `List<TrackUnitPoint>` | **protected field** |
| `TrackUnit.FrontBound` | `TrackPosition` | **protected set property** |
| `Vehicle.Velocity` | `float` | **private set property** |
| `Vehicle.Route` | `VehicleRoute` | **get-only property** (backs to `_route` field) |

**Rule:** Always check decompiled source to know if something is a field or property. `GetProperty()` won't find fields!

---

## 11. Harmony Patching

### 11.1 Setup

```csharp
using HarmonyLib;

public static class MyPatches
{
    private static bool _initialized;

    public static void Initialize()
    {
        if (_initialized) return;

        try
        {
            var harmony = new Harmony("MyMod.MyPatches");

            // Patch a method
            var original = AccessTools.Method(
                typeof(TargetType),
                "MethodName",
                new[] { typeof(ArgType) }
            );

            if (original != null)
            {
                var postfix = typeof(MyPatches).GetMethod(
                    nameof(Postfix_MethodName),
                    BindingFlags.NonPublic | BindingFlags.Static
                );
                harmony.Patch(original, postfix: new HarmonyMethod(postfix));
            }

            _initialized = true;
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"[MyMod] Harmony init error: {ex.Message}");
        }
    }
}
```

### 11.2 Common Patch Patterns

**Postfix — run after original:**

```csharp
private static void Postfix_MethodName(TargetType __instance)
{
    // __instance is the 'this' of the patched method
    // Modify state, add listeners, etc.
}
```

**Prefix — run before original (can skip):**

```csharp
private static bool Prefix_MethodName(TargetType __instance)
{
    // Return false to skip original method
    return true;
}
```

### 11.3 Accessing Private Members

```csharp
// Field
var fieldValue = AccessTools.Field(typeof(TargetType), "_privateField")
    ?.GetValue(instance);

// Property
var propValue = AccessTools.Property(typeof(TargetType), "PrivateProperty")
    ?.GetValue(instance);

// Method
var result = AccessTools.Method(typeof(TargetType), "PrivateMethod")
    ?.Invoke(instance, new object[] { arg1, arg2 });
```

### 11.4 Harmony Best Practices

| Rule | Why |
|------|-----|
| Use unique Harmony ID | `new Harmony("Author.ModName.Patches")` |
| Wrap in try-catch | Failed patches shouldn't crash the game |
| Check `original != null` before patching | Method might not exist in this version |
| Use `AccessTools` instead of `typeof().GetMethod()` | Handles generics, overloads better |
| Store `_initialized` flag | Prevent double-patching on save reload |

### 11.5 Critical: Verify Member Names

**Always verify field/property names in decompiled source before patching.**

```csharp
// WRONG — _vehicle doesn't exist as a field
var vehicle = AccessTools.Field(typeof(VehicleWindowScheduleTab), "_vehicle")
    ?.GetValue(scheduleTab) as Vehicle;  // ← Returns null!

// CORRECT — Vehicle is a public property
var vehicle = scheduleTab.Vehicle;  // ← Direct access works!
```

---

## 12. Common Pitfalls

### 12.1 The Nullable Struct Trap

```csharp
// WRONG — direct null check on struct
var companies = CompanyManager.Current.GetAll();
if (companies == null)  // ← This is Nullable<ImmutableUniqueList<Company>>
    return;

// CORRECT — check HasValue or use ?. operator
var companies = CompanyManager.Current?.GetAll();
if (companies == null) return;  // Nullable has no value
var list = companies.Value.ToList();  // Unwrap
```

### 12.2 The IEnumerable Trap

```csharp
// WRONG — ImmutableList<T> is not IEnumerable
foreach (var item in schedule.GetTasks()) { }  // ← Won't compile!

// CORRECT
foreach (var item in schedule.GetTasks().ToList()) { }
```

### 12.3 The Wrong OnUpdate Trap

```csharp
// WRONG — Window doesn't have OnUpdate()
public class MyWindow : RichWindow
{
    protected override void OnUpdate() { }  // ← Never called
}

// CORRECT
public class MyWindow : RichWindow
{
    private void Update() { }  // ← Unity calls this
}
```

### 12.4 The DisplayName Trap

```csharp
// WRONG — DisplayName doesn't exist on VehicleStation
string name = station.DisplayName?.ToString();

// CORRECT — Use Name (inherited from Building)
string name = station.Name;
```

### 12.5 The Reflection Field/Property Trap

```csharp
// WRONG — looking for property when it's a field
var pathProp = typeof(TrackUnit).GetProperty("Path");  // ← null

// CORRECT
var pathField = typeof(TrackUnit).GetField("Path",
    BindingFlags.NonPublic | BindingFlags.Instance);  // ← found!
```

### 12.6 The Tool Misuse Trap

```csharp
// WRONG — creating ITool just for a button
public class OpenWindowTool : ITool
{
    public void Activate() { /* open window */ }
    public bool OnUpdate() => true;
    public bool Deactivate(bool soft) => true;
}
Toolbar.Current.AddButton(icon, "Open", () => UIManager.Current.SetTool(new OpenWindowTool()));

// CORRECT — direct action
Toolbar.Current.AddButton(icon, "Open", () => OpenWindow());
```

### 12.7 The InitializeFrame Signature Trap

```csharp
// WRONG — 'new' hides the base method
protected internal new void InitializeFrame()

// CORRECT — override for polymorphism
protected internal override void InitializeFrame()
```

---

## 13. Testing Checklist

Before releasing your mod, verify:

### Build & Install
- [ ] `dotnet build -c Release` — 0 errors
- [ ] Mod appears in Settings → Mods list
- [ ] No exceptions in `Player.log` on startup

### Functionality
- [ ] Toolbar button visible and clickable
- [ ] Hotkeys work (test each one)
- [ ] Hotkeys survive game restart
- [ ] Windows open/close correctly
- [ ] Windows have proper title bar and close button
- [ ] Multiple windows can coexist

### Data & State
- [ ] Mod reads game data correctly (vehicles, routes, stations)
- [ ] No null reference exceptions during gameplay
- [ ] Save/load persists mod state
- [ ] Mod handles empty worlds (no vehicles/routes)

### Performance
- [ ] No frame drops when mod is active
- [ ] Throttled updates (not every frame for expensive ops)
- [ ] Object pooling for frequently created/destroyed objects

### Compatibility
- [ ] Works with other mods loaded
- [ ] Works after save/load cycle
- [ ] Graceful degradation if game API changes

---

## 14. Reference — Key Types

### 14.1 Game Types Quick Reference

| Type | Namespace | Key Members |
|------|-----------|-------------|
| `Vehicle` | `VoxelTycoon.Tracks` | `Velocity`, `VelocityLimit`, `Route`, `Schedule`, `BuyTime`, `MoneyEarnedCounter`, `RunningCostsCounter`, `Consist`, `Units` |
| `VehicleRoute` | `VoxelTycoon.Tracks.Tasks` | `Name`, `Color`, `Id`, `Vehicles`, `IsDead` |
| `VehicleStation` | `VoxelTycoon.Tracks` | `Name`, `PassengerCount`, `VehicleCount`, `Platforms`, `ClosestCity` |
| `VehicleSchedule` | `VoxelTycoon.Tracks` | `GetTasks()`, `CurrentTask`, `IsEmpty`, `TraverseOrder` |
| `VehicleStationTask` | `VoxelTycoon.Tracks.Tasks` | `Destination`, `Behavior`, `GetSubTasks()` |
| `TrackUnit` | `VoxelTycoon.Tracks` | `Path` (field), `Points` (field), `FrontBound`, `RearBound`, `Company` |
| `Company` | `VoxelTycoon` | `Name`, `Color`, `Id` |
| `Manager<T>` | `VoxelTycoon` | `Current`, `Initialize()`, `OnUpdate()`, `OnLateUpdate()` |
| `UIManager` | `VoxelTycoon.UI` | `Current`, `CreateWindow<T>()`, `FindWindow<T>()`, `SetTool()` |
| `Toolbar` | `VoxelTycoon.Game.UI.ModernUI` | `Current`, `AddButton()` |
| `RichWindow` | `VoxelTycoon.UI.Windows` | `Title`, `Width`, `Height`, `ContentContainer`, `InitializeFrame()` |
| `NotificationManager` | `VoxelTycoon.Notifications` | `Current`, `PushWarning()`, `PushCritical()` |

### 14.2 Collection Types

| Type | Kind | Iteration |
|------|------|-----------|
| `ImmutableList<T>` | Struct | `.ToList()` then foreach |
| `ImmutableUniqueList<T>` | Struct | `.ToList()` then foreach |
| `UniqueList<T>` | Class | Direct foreach |
| `List<T>` | Class | Direct foreach |

### 14.3 Important Struct Semantics

```csharp
// Hotkey — has nullable Value/Value2
Hotkey hotkey = new Hotkey(KeyCode.H);
KeyCode code = hotkey.Value.Value.Code;  // double .Value for nullable

// Setting<T> — mutable wrapper with implicit conversion T
Setting<Hotkey> setting = new Setting<Hotkey>(hotkey);
Hotkey value = setting;  // implicit conversion
setting.Value = newHotkey;  // explicit set

// Constraint — implicit float conversion
Window.Width = 400f;  // converts to Constraint.Fixed(400f)
```

---

## Appendix A: Decompilation Tips

To discover game APIs:

1. **Get game DLLs:** From `VoxelTycoon_Data/Managed/`
2. **Decompile with ILSpy:** Open `VoxelTycoon.dll`, `UnityEngine.*.dll`
3. **Search for types:** Use ILSpy's search or `grep -r "class Vehicle" ./Decompiled`
4. **Check inheritance:** Look at base classes for available members
5. **Verify access modifiers:** `public`/`protected`/`private`/`internal`
6. **Distinguish fields vs properties:** Fields have `{ get; set; }` syntax

### Key DLLs to Reference

```xml
<!-- In .csproj -->
<Reference Include="VoxelTycoon" />
<Reference Include="UnityEngine.CoreModule" />
<Reference Include="UnityEngine.UI" />
<Reference Include="UnityEngine.PhysicsModule" />
<Reference Include="UnityEngine.TextRenderingModule" />
<Reference Include="UnityEngine.IMGUIModule" />
<Reference Include="0Harmony" />  <!-- For patching -->
```

---

## Appendix B: Example — Minimal Working Mod

```csharp
// MyMod.csproj → builds to MyMod.dll
// mod.json → pack metadata

// MyMod.cs
using VoxelTycoon.Modding;
using VoxelTycoon.Serialization;

namespace MyMod
{
    public class MyMod : Mod
    {
        protected override void OnGameStarting()
        {
            MyManager.Initialize();
        }
    }
}

// MyManager.cs
using UnityEngine;
using VoxelTycoon;
using VoxelTycoon.Tools;
using VoxelTycoon.Tracks;

namespace MyMod
{
    public class MyManager : Manager<MyManager>
    {
        public bool Enabled { get; set; } = true;

        protected override void OnUpdate()
        {
            base.OnUpdate();

            var hotkey = new Hotkey(KeyCode.H);
            if (ToolHelper.IsHotkeyDown(hotkey))
            {
                Enabled = !Enabled;
                Debug.Log($"[MyMod] Enabled: {Enabled}");
            }
        }
    }
}
```

---

*This guide was generated from decompiled source analysis and real mod review. Always verify against your specific game version.*
