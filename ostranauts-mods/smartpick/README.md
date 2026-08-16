# Smart Pick Mod for Ostranauts

Makes crew pick up loose items and store them in the smallest compatible
container instead of dropping them on the ground in stockpile zones.

## Requirements

- BepInEx 5.4.23.5+ must be installed
- Game version 1.0.0.9

## How It Works

The mod patches `Task2.AssignHaulZone` with a Harmony Postfix that:
1. Checks if the original method found a valid stockpile zone
2. If not, searches all containers in the ship
3. Finds containers that accept the item (via `Container.AllowedCO`)
4. Checks which have space (via `Container.CanFit`)
5. Selects the smallest container (least remaining space)
6. Routes the haul target to that container

This means if you have a backpack inside a bin, items will be stored
in the backpack first (smallest container) before the bin.

## Build

```bash
cd smartpick
nix-shell -p dotnet-sdk_8 --run "dotnet build -c Release"
```

Output: `bin/Release/netstandard2.1/SmartPick.dll`

## Installation

Copy `SmartPick.dll` to `BepInEx/plugins/`

## Data Mod

The `SmartPick` data mod adds:
- `ACTSmartPickItem` interaction for manual smart picking
- `SmartPickQueued` condition to mark items
- `AISmartPickLooseItems` pledge for AI behavior

Place in `Ostranauts_Data/Mods/SmartPick/` and add to `loading_order.json`.
