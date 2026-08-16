using HarmonyLib;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace SmartPick.Patches
{
    /// <summary>
    /// Smart Pick - finds the smallest compatible container for hauled items
    /// instead of just dropping them on the ground in a stockpile zone.
    /// </summary>
    [HarmonyPatch(typeof(Container))]
    public static class ContainerPatches
    {
        /// <summary>
        /// Helper: Get remaining space in a container
        /// </summary>
        public static int GetRemainingSpace(Container container)
        {
            if (container == null || container.gridLayout == null)
                return 0;

            int maxSpace = container.gridLayout.gridMaxSpace;
            int usedSpace = 0;

            foreach (var co in container.ContainedCOs)
            {
                if (co == null) continue;
                if (co.coStackHead != null) continue;
                usedSpace += Container.GetSpace(co);
            }

            return Mathf.Max(0, maxSpace - usedSpace);
        }

        /// <summary>
        /// Helper: Check if a container can accept an item
        /// </summary>
        public static bool CanAcceptItem(Container container, CondOwner item)
        {
            if (container == null || item == null) return false;
            if (container.Locked) return false;

            // Check if item is allowed by container's filter
            if (!container.AllowedCO(item)) return false;

            // Check if item fits in container
            return container.CanFit(item, false, true, false);
        }

        /// <summary>
        /// Helper: Find the smallest container that can fit an item
        /// </summary>
        public static Container FindSmallestContainer(CondOwner item, List<Container> containers)
        {
            Container best = null;
            int bestSpace = int.MaxValue;

            foreach (var container in containers)
            {
                if (!CanAcceptItem(container, item)) continue;

                int remaining = GetRemainingSpace(container);
                if (remaining < bestSpace)
                {
                    bestSpace = remaining;
                    best = container;
                }
            }

            return best;
        }
    }
}
