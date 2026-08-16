using BepInEx;
using BepInEx.Logging;
using HarmonyLib;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace SmartPick
{
    [BepInPlugin("com.smartpick.plugin", "Smart Pick", "1.0.0")]
    public class SmartPickPlugin : BaseUnityPlugin
    {
        internal static ManualLogSource Logger;
        private Harmony _harmony;

        private void Awake()
        {
            Logger = base.Logger;
            Logger.LogInfo("Smart Pick plugin loaded!");

            _harmony = new Harmony("com.smartpick.plugin");
            _harmony.PatchAll(typeof(SmartPickPlugin).Assembly);
        }

        private void OnDestroy()
        {
            _harmony?.UnpatchSelf();
        }
    }
}
