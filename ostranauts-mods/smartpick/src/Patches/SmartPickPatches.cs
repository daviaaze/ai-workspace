using HarmonyLib;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace SmartPick.Patches
{
    /// <summary>
    /// Patches the hauling system to prefer containers over stockpile zones.
    /// When a crew member needs to haul an item, this finds the smallest
    /// compatible container with available space instead of dropping items
    /// on the ground in a stockpile.
    /// </summary>
    [HarmonyPatch(typeof(Task2))]
    public static class SmartPickPatches
    {
        /// <summary>
        /// Postfix for AssignHaulZone - if no stockpile zone was found,
        /// try to find a container that can hold the item.
        /// </summary>
        [HarmonyPatch("AssignHaulZone")]
        [HarmonyPostfix]
        static void Postfix_AssignHaulZone(Task2 __instance, CondOwner coHauler, 
            CondOwner coTarget, Interaction __result)
        {
            // Only intervene if original method didn't find a valid zone
            if (__result != null && __instance.nTile >= 0)
                return;

            if (coHauler == null || coTarget == null)
                return;

            // Find all containers in the hauler's ship
            var containers = FindContainersInShip(coHauler.ship);
            if (containers.Count == 0)
                return;

            // Find the smallest container that can fit this item
            Container bestContainer = null;
            int bestRemainingSpace = int.MaxValue;

            foreach (var container in containers)
            {
                if (!ContainerPatches.CanAcceptItem(container, coTarget))
                    continue;

                int remaining = ContainerPatches.GetRemainingSpace(container);
                
                // Check if item physically fits (needs enough space)
                int itemSpace = Container.GetSpace(coTarget);
                if (remaining < itemSpace)
                    continue;

                // Prefer the smallest container (least remaining space)
                if (remaining < bestRemainingSpace)
                {
                    bestRemainingSpace = remaining;
                    bestContainer = container;
                }
            }

            if (bestContainer == null)
                return;

            // Set the haul target to the container's position
            Vector3 pos = bestContainer.CO.tf.position;
            Tile tile = coHauler.ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
            
            if (tile != null)
            {
                __instance.nTile = tile.Index;
                __instance.strTileShip = tile.coProps.ship.strRegID;
                SmartPickPlugin.Logger.LogDebug(
                    $"SmartPick: Routing {coTarget.strNameFriendly} to container at tile {tile.Index} (remaining space: {bestRemainingSpace})");
            }
        }

        /// <summary>
        /// Find all containers in a ship
        /// </summary>
        static List<Container> FindContainersInShip(Ship ship)
        {
            var containers = new List<Container>();
            
            if (ship == null)
                return containers;

            // Iterate all COs in the game to find containers in this ship
            foreach (var kvp in DataHandler.mapCOs)
            {
                CondOwner co = kvp.Value;
                if (co == null) continue;
                if (co.ship != ship) continue;

                Container container = co.GetComponent<Container>();
                if (container != null && !container.Locked)
                {
                    containers.Add(container);
                }
            }

            return containers;
        }
    }
}
