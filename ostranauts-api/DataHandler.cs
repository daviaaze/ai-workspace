using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using JetBrains.Annotations;
using LitJson;
using Ostranauts.Core;
using Ostranauts.Ships.Commands;
using Ostranauts.Ships.Rooms;
using Ostranauts.Tools;
using Ostranauts.Tools.ExtensionMethods;
using Ostranauts.Trading;
using Ostranauts.UI.Mods;
using UnityEngine;

public static class DataHandler
{
	public static string strAssetPath;

	public const string strImagePath = "images/";

	public const string strManualsPath = "manuals/";

	public const string strDataPath = "data/";

	public const string strMeshPath = "mesh/";

	public const string strImgMissing = "missing.png";

	public const string str32 = " (32)";

	public const string str64 = " (64)";

	public static string strModFolder = "";

	public const string strModListName = "Mod Loading Order";

	public const string strEAPrefix = "Early Access Build: ";

	public const string strReleasePrefix = "Release Build: ";

	public static Action InitComplete;

	public static Action LoadComplete;

	public static string strBuild;

	public static List<string> aModPaths;

	public static Dictionary<string, JsonCond> dictConds;

	public static Dictionary<string, JsonCondOwner> dictCOs;

	public static Dictionary<string, CondTrigger> dictCTs;

	public static Dictionary<string, JsonInteraction> dictInteractions;

	public static Dictionary<string, Loot> dictLoot;

	public static Dictionary<string, JsonShip> dictShips;

	public static Dictionary<string, JsonSimple> dictSimple;

	public static Dictionary<string, CondOwner> mapCOs;

	public static Dictionary<string, JsonAd> dictAds;

	public static Dictionary<string, JsonAIPersonality> dictAIPersonalities;

	public static Dictionary<string, JsonAttackMode> dictAModes;

	private static Dictionary<string, JsonAsteroidBlueprint> dictAsteroidBlueprints;

	public static Dictionary<string, JsonAsteroidClusterBlueprint> dictAsteroidClusterBlueprints;

	public static Dictionary<string, JsonAudioEmitter> dictAudioEmitters;

	public static Dictionary<string, JsonBounty> dictBounties;

	public static Dictionary<string, JsonCareer> dictCareers;

	public static Dictionary<string, JsonCargoSpec> dictCargoSpecs;

	public static Dictionary<string, JsonChargeProfile> dictChargeProfiles;

	public static Dictionary<string, Color> dictColors;

	public static Dictionary<string, JsonComputerEntry> dictComputerEntries;

	public static Dictionary<string, CondRule> dictCondRules;

	public static Dictionary<string, string> dictCondRulesLookup;

	public static Dictionary<string, JsonContext> dictContext;

	public static Dictionary<string, JsonCOOverlay> dictCOOverlays;

	public static Dictionary<string, JsonCondOwnerSave> dictCOSaves;

	public static Dictionary<string, string> dictCrewSkins;

	public static Dictionary<string, JsonCrime> dictCrimes;

	public static Dictionary<string, DataCoCollection> dictDataCoCollections;

	public static Dictionary<string, DataCO> dictDataCOs;

	public static Dictionary<string, JsonEnvironmentMap> dictEnvironmentMaps;

	public static Dictionary<string, JsonExplosion> dictExplosions;

	public static Dictionary<string, JsonGasRespire> dictGasRespires;

	public static Dictionary<string, Dictionary<string, string>> dictGUIPropMaps;

	public static Dictionary<string, JsonGUIPropMap> dictGUIPropMapUnparsed;

	public static Dictionary<string, JsonHeadline> dictHeadlines;

	public static Dictionary<string, JsonHomeworld> dictHomeworlds;

	public static Dictionary<string, string> dictHTMLColors;

	public static Dictionary<string, JsonInteractionOverride> dictIAOverrides;

	public static Dictionary<string, JsonInstallable> dictInstallables;

	public static Dictionary<string, JsonInstallable> dictInstallables2;

	public static Dictionary<string, JsonItemDef> dictItemDefs;

	public static Dictionary<string, Texture2D> dictImages;

	public static Dictionary<string, JsonInfoNode> dictInfoNodes;

	public static Dictionary<string, JsonJobItems> dictJobitems;

	public static Dictionary<string, JsonJob> dictJobs;

	public static Dictionary<string, JsonColor> dictJsonColors;

	public static Dictionary<string, JsonCustomTokens> dictJsonTokens;

	public static Dictionary<string, JsonLedgerDef> dictLedgerDefs;

	public static Dictionary<string, JsonLifeEvent> dictLifeEvents;

	public static Dictionary<string, JsonLight> dictLights;

	public static Dictionary<string, string[]> dictManPages;

	public static Dictionary<string, JsonMarketActorConfig> dictMarketConfigs;

	public static Dictionary<string, Material> dictMaterials;

	public static Dictionary<string, JsonModInfo> dictModInfos;

	public static Dictionary<string, JsonModList> dictModList;

	public static Dictionary<string, JsonMusic> dictMusic;

	public static Dictionary<string, List<string>> dictMusicTags;

	public static Dictionary<string, JsonMusicStation> dictMusicStations;

	public static Dictionary<string, string> dictNamesFirst;

	public static Dictionary<string, string> dictNamesFull;

	public static Dictionary<string, string> dictNamesLast;

	public static Dictionary<string, string> dictNamesRobots;

	public static Dictionary<string, string> dictNamesShip;

	public static Dictionary<string, string> dictNamesShipAdjectives;

	public static Dictionary<string, string> dictNamesShipNouns;

	public static Dictionary<string, JsonParallax> dictParallax;

	public static Dictionary<string, JsonPDAAppIcon> dictPDAAppIcons;

	public static Dictionary<string, JsonPersonSpec> dictPersonSpecs;

	public static Dictionary<string, JsonPledge> dictPledges;

	public static Dictionary<string, JsonPlotBeatOverride> dictPlotBeatOverrides;

	public static Dictionary<string, JsonPlotBeat> dictPlotBeats;

	public static Dictionary<string, JsonPlotManagerSettings> dictPlotManager;

	public static Dictionary<string, JsonPlot> dictPlots;

	public static Dictionary<string, JsonPowerInfo> dictPowerInfo;

	public static Dictionary<string, JsonProductionMap> dictProductionMaps;

	public static Dictionary<string, JsonRaceTrack> dictRaceTracks;

	public static Dictionary<string, JsonRacingLeague> dictRacingLeagues;

	public static Dictionary<string, RoomSpec> dictRoomSpec;

	public static Dictionary<string, JsonRoomSpec> dictRoomSpecsTemp;

	public static Dictionary<string, JsonUserSettings> dictSettings;

	public static Dictionary<string, JsonShipAttack> dictShipAttacks;

	public static Dictionary<string, Dictionary<string, Texture2D>> dictShipImages;

	public static Dictionary<string, JsonShipSpec> dictShipSpecs;

	public static Dictionary<string, JsonSlotEffects> dictSlotEffects;

	public static Dictionary<string, JsonSlot> dictSlots;

	public static Dictionary<string, SocialStats> dictSocialStats;

	public static Dictionary<string, JsonStarSystemSave> dictStarSystems;

	public static Dictionary<string, string> dictStrings;

	public static Dictionary<string, JsonDCOCollection> dictSupersTemp;

	public static Dictionary<string, JsonTicker> dictTickers;

	public static Dictionary<string, JsonTip> dictTips;

	public static Dictionary<string, int[]> dictTraitScores;

	public static Dictionary<string, JsonTransit> dictTransit;

	public static Dictionary<string, string[]> dictVerbs;

	public static Dictionary<string, GameObject> dictVFX;

	public static Dictionary<string, JsonWound> dictWounds;

	public static Dictionary<string, JsonZoneTrigger> dictZoneTriggers;

	public static Dictionary<string, JsonCondTrigger> dictJCTs;

	public static Dictionary<string, JsonLoot> dictJLoot;

	public static Dictionary<string, List<object>> allObjects = new Dictionary<string, List<object>>();

	public static Dictionary<string, string> fileNameToPath = new Dictionary<string, string>();

	public static Dictionary<string, Type> fileToType = new Dictionary<string, Type>();

	public static Dictionary<object, string> objectToFile = new Dictionary<object, string>();

	public static HashSet<string> allFilesLoadedFrom = new HashSet<string>();

	public static HashSet<Type> allTypesLoaded = new HashSet<Type>();

	public static HashSet<string> allTypeStringsLoaded = new HashSet<string>();

	public static List<string> listCustomTokens;

	private static InteractionObjectTracker _interactionObjectTracker;

	private static CondTrigger _blankCTBackup;

	public static bool bInitialised = false;

	public static bool bLoaded = false;

	public static bool bNodeGraph = false;

	public static bool bAsyncLoaded = false;

	public static float fChanceFullname = 0.001f;

	public static int debugCOCount = 0;

	public static bool bSuppressGetErrors = false;

	public static bool bSuppressBigShips = false;

	public static List<string> nonCorresponds = new List<string>();

	public static List<string> aliases = new List<string>();

	public static List<string> languages = new List<string>();

	public static List<string> categories = new List<string>();

	public static StringBuilder loadLog = new StringBuilder();

	public static StringBuilder loadLogError = new StringBuilder();

	public static StringBuilder loadLogWarning = new StringBuilder();

	public static int toLoad;

	public static int loaded;

	public static float percentComplete;

	public static object dictWriteLock = new object();

	private static HashSet<string> allbracketText = new HashSet<string>();

	public static HashSet<string> allTokens = new HashSet<string>();

	public static void Init()
	{
		loadLog.Length = 0;
		loadLogError.Length = 0;
		loadLogWarning.Length = 0;
		if (bInitialised)
		{
			List<CondOwner> list = new List<CondOwner>(mapCOs.Values);
			foreach (CondOwner item in list)
			{
				if (!(item == null))
				{
					loadLogWarning.Append("Destroying leftover CO: ");
					loadLogWarning.Append(item.strName);
					loadLogWarning.AppendLine();
					item.Destroy();
				}
			}
			list.Clear();
			list = null;
			mapCOs.Clear();
			if (loadLogWarning.Length > 0)
			{
				UnityEngine.Debug.LogWarning(loadLogWarning.ToString());
			}
			return;
		}
		strAssetPath = Application.streamingAssetsPath + "/";
		LoadBuildVersion();
		if ((bool)ObjReader.use)
		{
			ObjReader.use.scaleFactor = new Vector3(0.0625f, 0.0625f, 0.0625f);
			ObjReader.use.objRotation = new Vector3(90f, 0f, 180f);
		}
		SetupDicts();
		if (_interactionObjectTracker == null)
		{
			_interactionObjectTracker = new InteractionObjectTracker();
		}
		dictSettings["DefaultUserSettings"] = new JsonUserSettings();
		dictSettings["DefaultUserSettings"].Init();
		if (File.Exists(Application.persistentDataPath + "/settings.json"))
		{
			JsonToData(Application.persistentDataPath + "/settings.json", dictSettings);
		}
		else
		{
			loadLogWarning.Append("WARNING: settings.json not found. Resorting to default values.");
			loadLogWarning.AppendLine();
			ResetUserSettings();
		}
		if (!dictSettings.ContainsKey("UserSettings") || dictSettings["UserSettings"] == null)
		{
			loadLogError.Append("ERROR: Malformed settings.json. Resorting to default values.");
			loadLogError.AppendLine();
			ResetUserSettings();
		}
		dictSettings["DefaultUserSettings"].CopyTo(GetUserSettings());
		dictSettings.Remove("DefaultUserSettings");
		SaveUserSettings();
		LoadMods();
		Application.SetStackTraceLogType(LogType.Log, StackTraceLogType.None);
		if (loadLog.Length > 0)
		{
			UnityEngine.Debug.Log(loadLog.ToString());
		}
		Application.SetStackTraceLogType(LogType.Log, StackTraceLogType.ScriptOnly);
		if (loadLogWarning.Length > 0)
		{
			UnityEngine.Debug.LogWarning(loadLogWarning.ToString());
		}
		if (loadLogError.Length > 0)
		{
			UnityEngine.Debug.LogError(loadLogError.ToString());
		}
		bInitialised = true;
		if (InitComplete != null)
		{
			InitComplete();
		}
	}

	private static void LoadMods()
	{
		bool flag = false;
		strModFolder = dictSettings["UserSettings"].strPathMods;
		if (string.IsNullOrEmpty(strModFolder))
		{
			strModFolder = Path.Combine(Application.dataPath, "Mods/");
			loadLogWarning.Append("WARNING: Unrecognised mod folder. Setting mod path to ");
			loadLogWarning.Append(strModFolder);
			loadLogWarning.AppendLine();
		}
		string directoryName = Path.GetDirectoryName(strModFolder);
		directoryName = Path.Combine(directoryName, "loading_order.json");
		JsonModInfo jsonModInfo = new JsonModInfo();
		jsonModInfo.strName = "Core";
		dictModInfos["core"] = jsonModInfo;
		bool flag2 = ConsoleToGUI.instance != null;
		if (flag2)
		{
			ConsoleToGUI.instance.LogInfo("Attempting to load " + directoryName + "...");
		}
		if (File.Exists(directoryName))
		{
			if (flag2)
			{
				ConsoleToGUI.instance.LogInfo("loading_order.json found. Beginning mod load.");
			}
			JsonToData(directoryName, dictModList);
			if (dictModList.TryGetValue("Mod Loading Order", out var value))
			{
				if (value.aIgnorePatterns != null)
				{
					for (int i = 0; i < value.aIgnorePatterns.Length; i++)
					{
						value.aIgnorePatterns[i] = PathSanitize(value.aIgnorePatterns[i]);
					}
				}
				SyncSteamWorkshopSubscriptions(value);
				LoadModInfos(value);
				List<string> loadOrder = value.GetLoadOrder();
				for (int j = 0; j < loadOrder.Count; j++)
				{
					string text = loadOrder[j];
					flag = true;
					JsonModInfo value2;
					if (text == "core")
					{
						LoadMod(strAssetPath, value.aIgnorePatterns, jsonModInfo);
					}
					else if (dictModInfos.TryGetValue(text, out value2) && !IsDuplicate(value2))
					{
						if (flag2)
						{
							ConsoleToGUI.instance.LogInfo("Loading mod: " + value2.strName + " from directory: " + text);
						}
						LoadMod(value2.GetDirectory(), value.aIgnorePatterns, value2);
					}
				}
			}
		}
		if (!flag)
		{
			if (flag2)
			{
				ConsoleToGUI.instance.LogInfo("No loading_order.json found. Beginning default game data load from " + strAssetPath);
			}
			JsonModList jsonModList = new JsonModList("Mod Loading Order");
			dictModList["Mod Loading Order"] = jsonModList;
			if (bSuppressBigShips)
			{
				jsonModList.aIgnorePatterns = new string[1] { "LA_" };
			}
			LoadMod(strAssetPath, jsonModList.aIgnorePatterns, jsonModInfo);
		}
	}

	private static bool IsDuplicate(JsonModInfo mod)
	{
		List<JsonModInfo> modInfoForID = GetModInfoForID(mod.strWorkshopID, mod);
		if (modInfoForID.Count == 0)
		{
			return false;
		}
		foreach (JsonModInfo item in modInfoForID)
		{
			if (item.GetStatus() == ModStatus.Loaded)
			{
				mod.SetStatus(ModStatus.Skipped);
				return true;
			}
			if (!item.GetIsDisabled() && item.IsLocalMod())
			{
				mod.SetStatus(ModStatus.Skipped);
				return true;
			}
		}
		return false;
	}

	private static void LoadModInfos(JsonModList jml)
	{
		List<string> list = jml.aLoadOrder.ToList();
		for (int i = 0; i < list.Count; i++)
		{
			JsonModInfo.Context context = JsonModList.ParseLoadingOrderEntry(list[i]);
			string path = context.Path;
			if (path == "core")
			{
				continue;
			}
			if (string.IsNullOrEmpty(path))
			{
				loadLogError.Append("ERROR: Invalid mod folder specified: ");
				loadLogError.Append(path);
				loadLogError.Append("; Skipping...");
				loadLogError.AppendLine();
				continue;
			}
			string text = "";
			if (Path.IsPathRooted(path))
			{
				text = path + "/";
			}
			else
			{
				string text2 = path.TrimStart(Path.DirectorySeparatorChar);
				text2 = path.TrimStart(Path.AltDirectorySeparatorChar);
				text2 += "/";
				text = Path.GetDirectoryName(strModFolder);
				text = Path.Combine(text, text2);
			}
			Dictionary<string, JsonModInfo> dictionary = new Dictionary<string, JsonModInfo>();
			string text3 = Path.Combine(text, "mod_info.json");
			if (File.Exists(text3))
			{
				JsonToData(text3, dictionary);
				if (dictionary.Count < 1)
				{
					JsonModInfo jsonModInfo = new JsonModInfo();
					jsonModInfo.SetDisabled(context.IsDisabled);
					jsonModInfo.SetEditMode(context.EditMode);
					jsonModInfo.strName = path;
					dictionary[jsonModInfo.strName] = jsonModInfo;
					loadLogWarning.Append("WARNING: Missing mod_info.json in folder: ");
					loadLogWarning.Append(path);
					loadLogWarning.Append("; Using default name: ");
					loadLogWarning.Append(jsonModInfo.strName);
					loadLogWarning.AppendLine();
				}
				using Dictionary<string, JsonModInfo>.ValueCollection.Enumerator enumerator = dictionary.Values.GetEnumerator();
				if (enumerator.MoveNext())
				{
					JsonModInfo current = enumerator.Current;
					dictModInfos[path] = current;
					current.SetDirectory(text);
					current.SetDirectoryShort(path);
					current.SetDisabled(context.IsDisabled);
					current.SetEditMode(context.EditMode);
				}
			}
			else
			{
				UnityEngine.Debug.LogWarning("Skipped loading mod: " + path + " Cannot find mod folder on drive");
				List<string> list2 = jml.aLoadOrder.ToList();
				list2.Remove(path);
				jml.aLoadOrder = list2.ToArray();
				SaveModList();
			}
		}
	}

	public static List<JsonModInfo> GetModInfoForID(string id, JsonModInfo mod = null)
	{
		List<JsonModInfo> list = new List<JsonModInfo>();
		if (string.IsNullOrEmpty(id))
		{
			return list;
		}
		foreach (var (_, jsonModInfo2) in dictModInfos)
		{
			if (jsonModInfo2 != null && !(jsonModInfo2.strWorkshopID != id) && jsonModInfo2 != mod)
			{
				list.Add(jsonModInfo2);
			}
		}
		return list;
	}

	private static void SyncSteamWorkshopSubscriptions(JsonModList jml)
	{
		List<JsonModInfo> subscribedInstalledMods = MonoSingleton<SteamWorkshopManager>.Instance.GetSubscribedInstalledMods();
		if (subscribedInstalledMods != null && subscribedInstalledMods.Count != 0 && jml.SyncLoadOrderWithWorkshop(subscribedInstalledMods))
		{
			SaveModList();
		}
	}

	private static void SetupDicts()
	{
		dictImages = new Dictionary<string, Texture2D>();
		dictColors = new Dictionary<string, Color>();
		dictHTMLColors = new Dictionary<string, string>();
		dictJsonColors = new Dictionary<string, JsonColor>();
		dictLights = new Dictionary<string, JsonLight>();
		dictShips = new Dictionary<string, JsonShip>(256);
		dictShipImages = new Dictionary<string, Dictionary<string, Texture2D>>();
		dictConds = new Dictionary<string, JsonCond>(2048);
		dictItemDefs = new Dictionary<string, JsonItemDef>(1024);
		dictCTs = new Dictionary<string, CondTrigger>(4096);
		dictCOs = new Dictionary<string, JsonCondOwner>();
		dictDataCoCollections = new Dictionary<string, DataCoCollection>();
		dictCOSaves = new Dictionary<string, JsonCondOwnerSave>();
		dictInteractions = new Dictionary<string, JsonInteraction>(8192);
		dictLoot = new Dictionary<string, Loot>(8192);
		dictProductionMaps = new Dictionary<string, JsonProductionMap>();
		dictMarketConfigs = new Dictionary<string, JsonMarketActorConfig>();
		dictCargoSpecs = new Dictionary<string, JsonCargoSpec>();
		dictGasRespires = new Dictionary<string, JsonGasRespire>();
		dictPowerInfo = new Dictionary<string, JsonPowerInfo>();
		dictGUIPropMaps = new Dictionary<string, Dictionary<string, string>>();
		dictNamesFirst = new Dictionary<string, string>();
		dictNamesLast = new Dictionary<string, string>();
		dictNamesRobots = new Dictionary<string, string>();
		dictNamesFull = new Dictionary<string, string>();
		dictNamesShip = new Dictionary<string, string>();
		dictNamesShipAdjectives = new Dictionary<string, string>();
		dictNamesShipNouns = new Dictionary<string, string>();
		dictManPages = new Dictionary<string, string[]>();
		dictHomeworlds = new Dictionary<string, JsonHomeworld>();
		dictCareers = new Dictionary<string, JsonCareer>();
		dictLifeEvents = new Dictionary<string, JsonLifeEvent>();
		dictPersonSpecs = new Dictionary<string, JsonPersonSpec>();
		dictShipSpecs = new Dictionary<string, JsonShipSpec>();
		dictTraitScores = new Dictionary<string, int[]>();
		dictRoomSpec = new Dictionary<string, RoomSpec>();
		dictStrings = new Dictionary<string, string>();
		dictSlotEffects = new Dictionary<string, JsonSlotEffects>();
		dictSlots = new Dictionary<string, JsonSlot>();
		dictTickers = new Dictionary<string, JsonTicker>();
		dictCondRules = new Dictionary<string, CondRule>();
		dictMaterials = new Dictionary<string, Material>();
		dictAudioEmitters = new Dictionary<string, JsonAudioEmitter>(512);
		dictCrewSkins = new Dictionary<string, string>();
		dictAds = new Dictionary<string, JsonAd>();
		dictHeadlines = new Dictionary<string, JsonHeadline>();
		dictMusicTags = new Dictionary<string, List<string>>();
		dictMusic = new Dictionary<string, JsonMusic>();
		dictMusicStations = new Dictionary<string, JsonMusicStation>();
		dictComputerEntries = new Dictionary<string, JsonComputerEntry>();
		dictCOOverlays = new Dictionary<string, JsonCOOverlay>(2048);
		dictDataCOs = new Dictionary<string, DataCO>();
		dictLedgerDefs = new Dictionary<string, JsonLedgerDef>();
		dictPledges = new Dictionary<string, JsonPledge>();
		dictJobitems = new Dictionary<string, JsonJobItems>();
		dictJobs = new Dictionary<string, JsonJob>();
		dictBounties = new Dictionary<string, JsonBounty>();
		dictSettings = new Dictionary<string, JsonUserSettings>();
		dictModList = new Dictionary<string, JsonModList>();
		dictModInfos = new Dictionary<string, JsonModInfo>();
		aModPaths = new List<string>();
		dictInstallables2 = new Dictionary<string, JsonInstallable>(2048);
		dictAIPersonalities = new Dictionary<string, JsonAIPersonality>();
		dictTransit = new Dictionary<string, JsonTransit>();
		dictPlotManager = new Dictionary<string, JsonPlotManagerSettings>();
		dictStarSystems = new Dictionary<string, JsonStarSystemSave>();
		dictParallax = new Dictionary<string, JsonParallax>();
		dictContext = new Dictionary<string, JsonContext>();
		dictChargeProfiles = new Dictionary<string, JsonChargeProfile>();
		dictWounds = new Dictionary<string, JsonWound>();
		dictAModes = new Dictionary<string, JsonAttackMode>();
		dictPDAAppIcons = new Dictionary<string, JsonPDAAppIcon>();
		dictZoneTriggers = new Dictionary<string, JsonZoneTrigger>();
		dictTips = new Dictionary<string, JsonTip>();
		dictCrimes = new Dictionary<string, JsonCrime>();
		dictPlots = new Dictionary<string, JsonPlot>();
		dictPlotBeats = new Dictionary<string, JsonPlotBeat>();
		dictRaceTracks = new Dictionary<string, JsonRaceTrack>();
		dictRacingLeagues = new Dictionary<string, JsonRacingLeague>();
		dictInfoNodes = new Dictionary<string, JsonInfoNode>();
		dictInstallables = new Dictionary<string, JsonInstallable>(2048);
		dictIAOverrides = new Dictionary<string, JsonInteractionOverride>();
		dictPlotBeatOverrides = new Dictionary<string, JsonPlotBeatOverride>();
		dictVerbs = new Dictionary<string, string[]>();
		dictJsonTokens = new Dictionary<string, JsonCustomTokens>();
		listCustomTokens = new List<string>();
		dictJCTs = new Dictionary<string, JsonCondTrigger>();
		dictJLoot = new Dictionary<string, JsonLoot>();
		dictSupersTemp = new Dictionary<string, JsonDCOCollection>();
		dictRoomSpecsTemp = new Dictionary<string, JsonRoomSpec>();
		dictSimple = new Dictionary<string, JsonSimple>();
		dictGUIPropMapUnparsed = new Dictionary<string, JsonGUIPropMap>();
		dictShipAttacks = new Dictionary<string, JsonShipAttack>();
		dictAsteroidBlueprints = new Dictionary<string, JsonAsteroidBlueprint>();
		dictAsteroidClusterBlueprints = new Dictionary<string, JsonAsteroidClusterBlueprint>();
		dictEnvironmentMaps = new Dictionary<string, JsonEnvironmentMap>();
		dictExplosions = new Dictionary<string, JsonExplosion>();
		dictVFX = new Dictionary<string, GameObject>();
		mapCOs = new Dictionary<string, CondOwner>();
	}

	public static void LoadBuildVersion()
	{
		try
		{
			TextAsset textAsset = (TextAsset)Resources.Load("version", typeof(TextAsset));
			strBuild = "Release Build: " + textAsset.text;
			loadLog.Append("#Info# Getting build info.");
			loadLog.AppendLine();
			loadLog.Append(strBuild);
			loadLog.AppendLine();
		}
		catch (Exception ex)
		{
			UnityEngine.Debug.LogError(loadLog.ToString() + "\n" + ex.Message + "\n" + ex.StackTrace.ToString());
		}
	}

	private static void BuildMarketDCOCollection(Dictionary<string, JsonDCOCollection> jCollections)
	{
		if (dictDataCoCollections == null)
		{
			dictDataCoCollections = new Dictionary<string, DataCoCollection>();
		}
		foreach (KeyValuePair<string, JsonCOOverlay> dictCOOverlay in dictCOOverlays)
		{
			BuildDataCO(dictCOOverlay.Key, dictCOOverlay.Value, null);
		}
		foreach (KeyValuePair<string, JsonCondOwner> dictCO in dictCOs)
		{
			BuildDataCO(dictCO.Key, null, dictCO.Value);
		}
		foreach (KeyValuePair<string, JsonDCOCollection> jCollection in jCollections)
		{
			DataCoCollection value = new DataCoCollection(jCollection.Value);
			dictDataCoCollections.TryAdd(jCollection.Key, value);
		}
		BuildHealthLibrary();
		dictSupersTemp.Clear();
	}

	public static DataCoCollection GetDataCoCollection(string name)
	{
		if (string.IsNullOrEmpty(name) || !dictDataCoCollections.TryGetValue(name, out var value))
		{
			return null;
		}
		return value;
	}

	public static DataCoCollection GetDataCoCollectionForCO(string coName)
	{
		foreach (KeyValuePair<string, DataCoCollection> dictDataCoCollection in dictDataCoCollections)
		{
			if (dictDataCoCollection.Value.IsPartOfCollection(coName))
			{
				return dictDataCoCollection.Value;
			}
		}
		return new DataCoCollection(new JsonDCOCollection
		{
			strName = "NoCollection"
		});
	}

	public static void ResetUserSettings()
	{
		dictSettings["UserSettings"] = new JsonUserSettings();
		dictSettings["UserSettings"].Init();
	}

	public static void SaveUserSettings()
	{
		DataToJsonStreaming(dictSettings, "/settings.json", bPersistent: true);
	}

	public static void SaveModList()
	{
		string directoryName = Path.GetDirectoryName(strModFolder);
		directoryName = Path.Combine(directoryName, "loading_order.json");
		DataToJsonStreaming(dictModList, directoryName, bPersistent: true);
	}

	public static void UpdateModList(string modPath, bool isDisabled)
	{
		if (dictModList.TryGetValue("Mod Loading Order", out var value))
		{
			value.UpdateLoadOrder(modPath, isDisabled);
			SaveModList();
		}
	}

	public static void SaveModInfo(JsonModInfo modInfo)
	{
		if (modInfo == null || string.IsNullOrEmpty(modInfo.GetDirectory()))
		{
			UnityEngine.Debug.LogWarning("ModInfo is null or directory is empty");
			return;
		}
		string path = Path.Combine(modInfo.GetDirectory(), "mod_info.json");
		try
		{
			dictModInfos[modInfo.GetDirectoryShort()] = modInfo;
			string contents = CreateJsonFromData(new Dictionary<string, JsonModInfo> { [modInfo.strName] = modInfo.Clone() });
			File.WriteAllText(path, contents);
		}
		catch (Exception ex)
		{
			UnityEngine.Debug.LogWarning("Failed to save mod_info.json: " + ex.Message);
		}
	}

	public static JsonModInfo LoadModInfoFromFolder(string folderPath)
	{
		string path = Path.Combine(folderPath, "mod_info.json");
		if (File.Exists(path))
		{
			try
			{
				using List<JsonModInfo>.Enumerator enumerator = JsonMapper.ToObject<List<JsonModInfo>>(File.ReadAllText(path)).GetEnumerator();
				if (enumerator.MoveNext())
				{
					return enumerator.Current;
				}
			}
			catch (Exception ex)
			{
				UnityEngine.Debug.LogWarning("Failed to load mod_info.json from " + folderPath + ": " + ex.Message);
			}
		}
		return new JsonModInfo
		{
			strName = Path.GetFileName(folderPath)
		};
	}

	public static JsonUserSettings GetUserSettings()
	{
		if (!dictSettings.ContainsKey("UserSettings") || dictSettings["UserSettings"] == null)
		{
			UnityEngine.Debug.LogError("ERROR: UserSettings not found.");
			return null;
		}
		return dictSettings["UserSettings"];
	}

	public static void OpenFolder(string strPath)
	{
		strPath = strPath.Replace("/", "\\");
		Process.Start("explorer.exe", "/select," + strPath);
	}

	public static void TryOpenModFolder()
	{
		try
		{
			string directoryName = Path.GetDirectoryName(strModFolder);
			Directory.CreateDirectory(directoryName);
			string path = Path.Combine(directoryName, "loading_order.json");
			if (!File.Exists(path))
			{
				JsonModList jsonModList = new JsonModList("Mod Loading Order");
				string contents = CreateJsonFromData(new Dictionary<string, JsonModList> { [jsonModList.strName] = jsonModList });
				File.WriteAllText(path, contents);
			}
			Application.OpenURL(directoryName);
		}
		catch (Exception ex)
		{
			UnityEngine.Debug.LogError(ex.Message + "\n" + ex.StackTrace.ToString());
		}
	}

	public static void LoadBigShips(string strFolderPath)
	{
		ModLoader modLoader = new ModLoader();
		LoadManager.LoadingQueue.Add(modLoader);
		LoadManager.LastScheduledMod = modLoader;
		string[] array = fileToType.Keys.ToArray();
		string[] array2 = array;
		for (int i = 0; i < array2.Length; i++)
		{
			UnityEngine.Debug.Log(array2[i]);
		}
		strFolderPath += "data/";
		LoadModJsons(strFolderPath + "ships/", dictShips, array);
		MonoSingleton<LoadManager>.Instance.BeginDataHanderLoadThreads();
	}

	private static void LoadMod(string strFolderPath, string[] aIgnorePatterns, JsonModInfo jmi)
	{
		ModLoader modLoader = new ModLoader
		{
			JsonModInfo = jmi
		};
		LoadManager.LoadingQueue.Add(modLoader);
		LoadManager.LastScheduledMod = modLoader;
		if (!Directory.Exists(strFolderPath + "data/"))
		{
			UnityEngine.Debug.LogError("ERROR: Mod folder not found: " + strFolderPath + "data/");
			jmi.SetStatus(ModStatus.Missing);
			return;
		}
		bool num = ConsoleToGUI.instance != null;
		int num2 = 0;
		if (num)
		{
			num2 = ConsoleToGUI.instance.ErrorCount;
			ConsoleToGUI.instance.LogInfo("Begin loading data from: " + strFolderPath);
		}
		aModPaths.Insert(0, strFolderPath);
		strFolderPath += "data/";
		LoadModJsons(strFolderPath + "ships/", dictShips, aIgnorePatterns);
		LoadModJsons(strFolderPath + "ads/", dictAds, aIgnorePatterns);
		LoadModJsons(strFolderPath + "ai_training/", dictAIPersonalities, aIgnorePatterns);
		LoadModJsons(strFolderPath + "attackmodes/coAttacks", dictAModes, aIgnorePatterns);
		LoadModJsons(strFolderPath + "attackmodes/shipAttacks", dictShipAttacks, aIgnorePatterns);
		LoadModJsons(strFolderPath + "audioemitters/", dictAudioEmitters, aIgnorePatterns);
		LoadModJsons(strFolderPath + "blueprints/asteroids/", dictAsteroidBlueprints, aIgnorePatterns);
		LoadModJsons(strFolderPath + "blueprints/clusters/", dictAsteroidClusterBlueprints, aIgnorePatterns);
		LoadModJsons(strFolderPath + "jobs/bounties/", dictBounties, aIgnorePatterns);
		LoadModJsons(strFolderPath + "careers/", dictCareers, aIgnorePatterns);
		LoadModJsons(strFolderPath + "chargeprofiles/", dictChargeProfiles, aIgnorePatterns);
		LoadModJsons(strFolderPath + "colors/", dictJsonColors, aIgnorePatterns);
		LoadModJsons(strFolderPath + "conditions/", dictConds, aIgnorePatterns);
		Dictionary<string, JsonSimple> condsSimple = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "conditions_simple/", condsSimple, aIgnorePatterns);
		LoadModJsons(strFolderPath + "condowners/", dictCOs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "condrules/", dictCondRules, aIgnorePatterns);
		LoadModJsons(strFolderPath + "condtrigs/", dictCTs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "context/", dictContext, aIgnorePatterns);
		LoadModJsons(strFolderPath + "cooverlays/", dictCOOverlays, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictSimpleCrewSkins = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "crewskins/", dictSimpleCrewSkins, aIgnorePatterns);
		LoadModJsons(strFolderPath + "crime/", dictCrimes, aIgnorePatterns);
		LoadModJsons(strFolderPath + "blueprints/environments/", dictEnvironmentMaps, aIgnorePatterns);
		LoadModJsons(strFolderPath + "explosions/", dictExplosions, aIgnorePatterns);
		LoadModJsons(strFolderPath + "gasrespires/", dictGasRespires, aIgnorePatterns);
		LoadModJsons(strFolderPath + "guipropmaps/", dictGUIPropMapUnparsed, aIgnorePatterns);
		LoadModJsons(strFolderPath + "headlines/", dictHeadlines, aIgnorePatterns);
		LoadModJsons(strFolderPath + "homeworlds/", dictHomeworlds, aIgnorePatterns);
		LoadModJsons(strFolderPath + "info/", dictInfoNodes, aIgnorePatterns);
		LoadModJsons(strFolderPath + "installables/", dictInstallables, aIgnorePatterns);
		LoadModJsons(strFolderPath + "interaction_overrides/", dictIAOverrides, aIgnorePatterns);
		LoadModJsons(strFolderPath + "interactions/", dictInteractions, aIgnorePatterns);
		LoadModJsons(strFolderPath + "items/", dictItemDefs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "jobitems/", dictJobitems, aIgnorePatterns);
		LoadModJsons(strFolderPath + "jobs/jobs/", dictJobs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "ledgerdefs/", dictLedgerDefs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "lifeevents/", dictLifeEvents, aIgnorePatterns);
		LoadModJsons(strFolderPath + "lights/", dictLights, aIgnorePatterns);
		LoadModJsons(strFolderPath + "loot/", dictLoot, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictSimpleManPages = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "manpages/", dictSimpleManPages, aIgnorePatterns);
		LoadModJsons(strFolderPath + "market/Markets/", dictMarketConfigs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "market/CoCollections/", dictSupersTemp, aIgnorePatterns);
		LoadModJsons(strFolderPath + "market/Production/", dictProductionMaps, aIgnorePatterns);
		LoadModJsons(strFolderPath + "market/CargoSpecs/", dictCargoSpecs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "music/", dictMusic, aIgnorePatterns);
		LoadModJsons(strFolderPath + "music_stations/", dictMusicStations, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictFirst = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "names_first/", dictFirst, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictFull = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "names_full/", dictFull, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictLast = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "names_last/", dictLast, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictRobots = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "names_robots/", dictRobots, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictShipNames = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "names_ship/", dictShipNames, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictShipAdjectives = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "names_ship_adjectives/", dictShipAdjectives, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictShipNouns = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "names_ship_nouns/", dictShipNouns, aIgnorePatterns);
		LoadModJsons(strFolderPath + "parallax/", dictParallax, aIgnorePatterns);
		LoadModJsons(strFolderPath + "pda_apps/", dictPDAAppIcons, aIgnorePatterns);
		LoadModJsons(strFolderPath + "personspecs/", dictPersonSpecs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "pledges/", dictPledges, aIgnorePatterns);
		LoadModJsons(strFolderPath + "plot_beat_overrides/", dictPlotBeatOverrides, aIgnorePatterns);
		LoadModJsons(strFolderPath + "plot_beats/", dictPlotBeats, aIgnorePatterns);
		LoadModJsons(strFolderPath + "plot_manager/", dictPlotManager, aIgnorePatterns);
		LoadModJsons(strFolderPath + "plots/", dictPlots, aIgnorePatterns);
		LoadModJsons(strFolderPath + "powerinfos/", dictPowerInfo, aIgnorePatterns);
		LoadModJsons(strFolderPath + "racing/leagues/", dictRacingLeagues, aIgnorePatterns);
		LoadModJsons(strFolderPath + "racing/tracks/", dictRaceTracks, aIgnorePatterns);
		LoadModJsons(strFolderPath + "rooms/", dictRoomSpecsTemp, aIgnorePatterns);
		LoadModJsons(strFolderPath + "shipspecs/", dictShipSpecs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "slot_effects/", dictSlotEffects, aIgnorePatterns);
		LoadModJsons(strFolderPath + "slots/", dictSlots, aIgnorePatterns);
		LoadModJsons(strFolderPath + "star_systems/", dictStarSystems, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictStringsTemp = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "strings/", dictStringsTemp, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tickers/", dictTickers, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tips/", dictTips, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tokens/", dictJsonTokens, aIgnorePatterns);
		Dictionary<string, JsonSimple> dictTraitsTemp = new Dictionary<string, JsonSimple>();
		LoadModJsons(strFolderPath + "traitscores/", dictTraitsTemp, aIgnorePatterns);
		LoadModJsons(strFolderPath + "transit/", dictTransit, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tsv/output/stakes/condtrigs/", dictJCTs, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tsv/output/stakes/loot/", dictJLoot, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tsv/output/stakes/interactions/", dictInteractions, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tsv/output/stakes/conditions/", dictConds, aIgnorePatterns);
		LoadModJsons(strFolderPath + "tsv/output/stakes/contexts/", dictContext, aIgnorePatterns);
		LoadModJsons(strFolderPath + "wounds/", dictWounds, aIgnorePatterns);
		LoadModJsons(strFolderPath + "zone_triggers/", dictZoneTriggers, aIgnorePatterns);
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseGUIPropMaps();
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseConditionsSimple(condsSimple);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseTraitScores(dictTraitsTemp);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictStringsTemp, dictStrings);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictSimpleCrewSkins, dictCrewSkins);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictFirst, dictNamesFirst);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictFull, dictNamesFull);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictLast, dictNamesLast);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictRobots, dictNamesRobots);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictShipNames, dictNamesShip);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictShipNouns, dictNamesShipNouns);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseSimpleIntoStringDict(dictShipAdjectives, dictNamesShipAdjectives);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseManPages(dictSimpleManPages);
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseMusic();
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseJDictLoots();
		});
		modLoader.PerModPostLoadAsyncOkay.Add(delegate
		{
			ParseJDictCTs();
		});
		if (jmi.GetStatus() == ModStatus.Missing)
		{
			jmi.SetStatus(ModStatus.Missing);
		}
		else if ((bool)ConsoleToGUI.instance && num2 < ConsoleToGUI.instance.ErrorCount)
		{
			jmi.SetStatus(ModStatus.Error);
		}
		else
		{
			jmi.SetStatus(ModStatus.Loaded);
		}
	}

	public static void LoadModJsons<TJson>(string strFolderPath, Dictionary<string, TJson> dict, string[] aIgnorePatterns)
	{
		if (!Directory.Exists(strFolderPath))
		{
			return;
		}
		string[] files = Directory.GetFiles(strFolderPath, "*.json", SearchOption.AllDirectories);
		foreach (string strIn in files)
		{
			string strFileTemp = PathSanitize(strIn);
			bool flag = false;
			if (aIgnorePatterns != null)
			{
				foreach (string value in aIgnorePatterns)
				{
					if (strFileTemp.IndexOf(value) >= 0)
					{
						flag = true;
						break;
					}
				}
			}
			if (flag)
			{
				UnityEngine.Debug.LogWarning("Ignore Pattern match: " + strFileTemp + "; Skipping...");
				continue;
			}
			FileLoader fileLoader = ((!(typeof(TJson) == typeof(JsonShip))) ? LoadManager.LastScheduledMod.AddDelegate(delegate
			{
				JsonToData(strFileTemp, dict);
			}) : LoadManager.LastScheduledMod.AddShip(delegate
			{
				JsonToData(strFileTemp, dict);
			}));
			fileLoader.fileName = strFileTemp;
		}
	}

	public static void PostModLoadMainThread()
	{
		BuildMarketDCOCollection(dictSupersTemp);
		ParseRoomSpecs(dictRoomSpecsTemp);
		foreach (KeyValuePair<string, JsonInstallable> dictInstallable in dictInstallables)
		{
			Installables.Create(dictInstallable.Value);
		}
		GenerateSkillChatter();
	}

	public static void AllPostLoadAsync()
	{
		foreach (KeyValuePair<string, JsonInteractionOverride> dictIAOverride in dictIAOverrides)
		{
			dictIAOverride.Value.Generate();
		}
		foreach (KeyValuePair<string, JsonPlotBeatOverride> dictPlotBeatOverride in dictPlotBeatOverrides)
		{
			dictPlotBeatOverride.Value.Generate();
		}
		foreach (CondTrigger value in dictCTs.Values)
		{
			value.PostInit();
		}
		dictSocialStats = new Dictionary<string, SocialStats>();
		foreach (JsonInteraction value2 in dictInteractions.Values)
		{
			if (value2.bSocial)
			{
				dictSocialStats[value2.strName] = new SocialStats(value2.strName);
			}
		}
		UnpackTokens();
		PrepareConditionDescriptions();
		PrepareInteractionInflections();
		JsonRaceTrack.GenerateWaypointIds(dictRaceTracks);
	}

	private static void GenerateSkillChatter()
	{
		JsonInteraction value = null;
		JsonInteraction value2 = null;
		CondTrigger value3 = null;
		dictInteractions.TryGetValue("SOCAskCareer", out value2);
		dictInteractions.TryGetValue("SOCTellSkill_TEMP", out value);
		dictCTs.TryGetValue("TIsSOCTalkSkillTEMPUs", out value3);
		if (value == null || value3 == null || value2 == null)
		{
			return;
		}
		List<string> list = new List<string>();
		foreach (string lootName in GetLoot("CONDSocialGUIFilterSkills").GetLootNames())
		{
			JsonInteraction jsonInteraction = value.Clone();
			CondTrigger condTrigger = value3.Clone();
			Condition cond = GetCond(lootName);
			condTrigger.strName = "TIsSOCTalk" + lootName + "Us";
			condTrigger.aReqs = new string[1] { lootName };
			jsonInteraction.strName = "SOCTell" + lootName;
			jsonInteraction.strTitle = cond.strNameFriendly;
			jsonInteraction.strDesc = cond.strDesc;
			jsonInteraction.CTTestUs = condTrigger.strName;
			dictInteractions[jsonInteraction.strName] = jsonInteraction;
			dictCTs[condTrigger.strName] = condTrigger;
			list.Add(jsonInteraction.strName);
		}
		string[] aInverse = value2.aInverse;
		foreach (string item in aInverse)
		{
			list.Add(item);
		}
		value2.aInverse = list.ToArray();
	}

	public static void ApplyOverride(object objOrig, string[] aValues)
	{
		if (objOrig == null || aValues == null || aValues.Length == 0)
		{
			return;
		}
		Type type = objOrig.GetType();
		foreach (string text in aValues)
		{
			if (string.IsNullOrEmpty(text))
			{
				continue;
			}
			string[] array = text.Split('|');
			if (array.Length != 2)
			{
				continue;
			}
			string message = text;
			PropertyInfo property = type.GetProperty(array[0]);
			try
			{
				if (array[1] == "null")
				{
					property.SetValue(objOrig, null, null);
				}
				else if (property.PropertyType == typeof(string[]))
				{
					property.SetValue(objOrig, Convert.ChangeType(new string[1] { array[1] }, property.PropertyType), null);
				}
				else
				{
					property.SetValue(objOrig, Convert.ChangeType(array[1], property.PropertyType), null);
				}
			}
			catch (Exception ex)
			{
				UnityEngine.Debug.Log(message);
				UnityEngine.Debug.Log(ex.Message);
			}
		}
	}

	public static string PathSanitize(string strIn)
	{
		if (strIn == null)
		{
			return null;
		}
		strIn = strIn.Replace("\\", "/");
		strIn = strIn.Replace("//", "/");
		return strIn;
	}

	public static void ScheduleJsonLoad<TJson>(object o, string strFile, Dictionary<string, TJson> outputDictionary)
	{
		JsonMapper.ToObject<TJson[]>(File.ReadAllText(strFile, Encoding.UTF8));
	}

	public static void JsonToData<TJson>(string strFile, Dictionary<string, TJson> dict)
	{
		StringBuilder stringBuilder = new StringBuilder(70);
		stringBuilder.Length = 0;
		try
		{
			string json = File.ReadAllText(strFile, Encoding.UTF8);
			stringBuilder.AppendLine("Converting json into Array...");
			TJson[] array = JsonMapper.ToObject<TJson[]>(json);
			if (bNodeGraph)
			{
				lock (dictWriteLock)
				{
					if (array.Length != 0)
					{
						Type type = array[0].GetType();
						allTypesLoaded.Add(type);
						allTypeStringsLoaded.Add(type.ToString());
						fileToType[Path.GetFileNameWithoutExtension(strFile)] = type;
					}
					allFilesLoadedFrom.Add(Path.GetFileNameWithoutExtension(strFile));
					fileNameToPath[Path.GetFileNameWithoutExtension(strFile)] = strFile;
				}
			}
			TJson[] array2 = array;
			for (int i = 0; i < array2.Length; i++)
			{
				TJson val = array2[i];
				stringBuilder.Append("Getting key: ");
				string text = null;
				PropertyInfo property = val.GetType().GetProperty("strName");
				if (property == null)
				{
					JsonLogger.ReportProblem("strName is missing", ReportTypes.FailingString);
				}
				text = property.GetValue(val, null).ToString();
				stringBuilder.AppendLine(text);
				lock (dictWriteLock)
				{
					if (!dict.TryAdd(text, val))
					{
						dict[text] = val;
					}
					if (bNodeGraph)
					{
						objectToFile.Add(val, strFile);
						if (allObjects.ContainsKey(text))
						{
							allObjects[text].Add(val);
							continue;
						}
						allObjects[text] = new List<object> { val };
					}
				}
			}
			array = null;
		}
		catch (Exception ex)
		{
			lock (new object())
			{
				LoadManager.JsonLogErrorExceptions.Add(delegate
				{
					JsonLogger.ReportProblem(strFile, ReportTypes.SourceInfo);
				});
			}
			string text2 = ((stringBuilder.Length <= 1000) ? stringBuilder.ToString() : stringBuilder.ToString(stringBuilder.Length - 1000, 1000));
			UnityEngine.Debug.LogError("Error reading file: " + strFile);
			UnityEngine.Debug.LogError(text2 + "\n" + ex.Message + "\n" + ex.StackTrace.ToString());
		}
		if (strFile.IndexOf("osSGv1") >= 0)
		{
			UnityEngine.Debug.Log(stringBuilder);
		}
	}

	public static void JsonToData<TJson>(string strFile, Dictionary<string, TJson> dict, Dictionary<string, byte[]> dictFiles)
	{
		UnityEngine.Debug.Log("#Info# Loading json: " + strFile + " from byte array.");
		StringBuilder stringBuilder = new StringBuilder(70);
		try
		{
			byte[] array = dictFiles[strFile];
			string json = Encoding.UTF8.GetString(array);
			stringBuilder.AppendLine("Converting json into Array...");
			TJson[] array2 = JsonMapper.ToObject<TJson[]>(json);
			if (array2 == null)
			{
				stringBuilder.AppendLine("null aList found in " + strFile + "(" + array.Length + " bytes) converting to object. Skipping.");
				return;
			}
			TJson[] array3 = array2;
			for (int i = 0; i < array3.Length; i++)
			{
				TJson val = array3[i];
				stringBuilder.Append("Getting key: ");
				string text = null;
				PropertyInfo property = val.GetType().GetProperty("strName");
				if (property == null)
				{
					JsonLogger.ReportProblem("strName is missing", ReportTypes.FailingString);
				}
				text = property.GetValue(val, null).ToString();
				stringBuilder.AppendLine(text);
				if (dict.ContainsKey(text))
				{
					UnityEngine.Debug.Log("Warning: Trying to add " + text + " twice.");
					dict[text] = val;
				}
				else
				{
					dict.Add(text, val);
				}
			}
			array2 = null;
		}
		catch (Exception ex)
		{
			JsonLogger.ReportProblem(strFile, ReportTypes.SourceInfo);
			string text2 = ((stringBuilder.Length <= 1000) ? stringBuilder.ToString() : stringBuilder.ToString(stringBuilder.Length - 1000, 1000));
			UnityEngine.Debug.LogError(text2 + "\n" + ex.Message + "\n" + ex.StackTrace.ToString());
		}
		if (strFile.IndexOf("osSGv1") >= 0)
		{
			UnityEngine.Debug.Log(stringBuilder);
		}
	}

	public static void TxtToData(string strFile, List<string> aListOut, bool format)
	{
		UnityEngine.Debug.Log("Loading text: " + strFile);
		string text = "";
		try
		{
			string text2 = File.ReadAllText(strFile);
			text += "Converting txt file into Array...\n";
			if (format)
			{
				text2 = Regex.Replace(text2, "\\r\\n?|\\n", "");
				string[] array = text2.Split(',');
				foreach (string item in array)
				{
					aListOut.Add(item);
				}
			}
			else
			{
				aListOut.Add(text2);
			}
		}
		catch (Exception ex)
		{
			UnityEngine.Debug.Log(text + "\n" + ex.Message + "\n" + ex.StackTrace.ToString());
		}
	}

	public static string CreateJsonFromData<TJson>(Dictionary<string, TJson> dictData)
	{
		StringBuilder stringBuilder = new StringBuilder();
		JsonWriter jsonWriter = new JsonWriter(stringBuilder);
		jsonWriter.PrettyPrint = true;
		jsonWriter.IndentValue = 2;
		List<TJson> list = new List<TJson>();
		foreach (KeyValuePair<string, TJson> dictDatum in dictData)
		{
			list.Add(dictDatum.Value);
		}
		JsonMapper.ToJson(list, jsonWriter);
		string result = stringBuilder.ToString();
		list.Clear();
		list = null;
		stringBuilder = null;
		jsonWriter = null;
		return result;
	}

	public static Exception DataToJsonStreaming<TJson>(Dictionary<string, TJson> dictData, string strFilename, bool bPersistent, string persistenPath = "")
	{
		strFilename = ReplaceInvalidCharacters(strFilename);
		string text = strAssetPath + "data/" + strFilename;
		if (bPersistent)
		{
			strFilename = strFilename.TrimStart(Path.DirectorySeparatorChar);
			strFilename = strFilename.TrimStart(Path.AltDirectorySeparatorChar);
			text = (string.IsNullOrEmpty(persistenPath) ? Path.Combine(Application.persistentDataPath, strFilename) : Path.Combine(persistenPath, strFilename));
		}
		if (IllegalFileString(text))
		{
			return new IOException("Illegal path or file");
		}
		string directoryName = Path.GetDirectoryName(text);
		try
		{
			Directory.CreateDirectory(directoryName);
			using StreamWriter writer = new StreamWriter(text);
			JsonWriter jsonWriter = new JsonWriter(writer);
			jsonWriter.PrettyPrint = true;
			jsonWriter.IndentValue = 2;
			List<TJson> list = new List<TJson>();
			foreach (KeyValuePair<string, TJson> dictDatum in dictData)
			{
				list.Add(dictDatum.Value);
			}
			JsonMapper.ToJson(list, jsonWriter);
		}
		catch (IOException result)
		{
			return result;
		}
		return null;
	}

	public static void WriteFile(string strFilename, string strContents)
	{
		string text = strAssetPath + "data/" + strFilename;
		if (!IllegalFileString(text))
		{
			Directory.CreateDirectory(Path.GetDirectoryName(text));
			File.WriteAllText(text, strContents);
		}
	}

	public static void WriteFilePersistent(string strFilename, string strContents)
	{
		strFilename = ReplaceInvalidCharacters(strFilename);
		strFilename = strFilename.TrimStart(Path.DirectorySeparatorChar);
		strFilename = strFilename.TrimStart(Path.AltDirectorySeparatorChar);
		string text = Path.Combine(Application.persistentDataPath, strFilename);
		if (!IllegalFileString(text))
		{
			Directory.CreateDirectory(Path.GetDirectoryName(text));
			File.WriteAllText(text, strContents);
		}
	}

	public static void RemoveFile(string strFullPathFileName)
	{
		if (string.IsNullOrEmpty(strFullPathFileName))
		{
			return;
		}
		try
		{
			if (File.Exists(strFullPathFileName))
			{
				File.Delete(strFullPathFileName);
			}
		}
		catch (Exception ex)
		{
			UnityEngine.Debug.LogWarning("Could not remove file " + strFullPathFileName + " Error: " + ex);
		}
	}

	public static void CopyFile(string strFullPathFileName, string destinationFolder, string newFileName, bool overwrite = false)
	{
		if (string.IsNullOrEmpty(strFullPathFileName) || string.IsNullOrEmpty(destinationFolder))
		{
			return;
		}
		try
		{
			if (File.Exists(strFullPathFileName))
			{
				if (!Directory.Exists(destinationFolder))
				{
					Directory.CreateDirectory(destinationFolder);
				}
				File.Copy(strFullPathFileName, destinationFolder + newFileName, overwrite);
			}
		}
		catch (Exception ex)
		{
			UnityEngine.Debug.LogWarning("Could not copy file " + strFullPathFileName + " Error: " + ex);
		}
	}

	private static string ReplaceInvalidCharacters(string name, bool revert = false)
	{
		foreach (KeyValuePair<char, char> item in new Dictionary<char, char>
		{
			{ '|', '%' },
			{ '*', '§' }
		})
		{
			char c = (revert ? item.Value : item.Key);
			char newChar = (revert ? item.Key : item.Value);
			if (name.Contains(c))
			{
				name = name.Replace(c, newChar);
			}
		}
		return name;
	}

	public static bool IllegalFileString(string strPathAndFile)
	{
		if (strPathAndFile.Contains("../") || strPathAndFile.Contains("..\\"))
		{
			UnityEngine.Debug.LogError("ERROR: Cannot write file " + strPathAndFile + "\nFilename contains illegal characters.");
			return true;
		}
		return false;
	}

	public static void AddPNG(string strFileName, Texture2D bmp)
	{
		if (strFileName != null && !(bmp == null))
		{
			dictImages[strFileName] = bmp;
			bmp.name = strFileName;
		}
	}

	public static Texture2D LoadPNG(string strFileName, bool bNorm, bool alwaysLoadFreshInstance = false)
	{
		Texture2D value = null;
		if (string.IsNullOrEmpty(strFileName))
		{
			strFileName = "null";
		}
		foreach (string aModPath in aModPaths)
		{
			string path = aModPath + "images/" + strFileName;
			if (!alwaysLoadFreshInstance && dictImages.TryGetValue(strFileName, out value) && value != null)
			{
				path = null;
				return value;
			}
			if (File.Exists(path))
			{
				byte[] data = File.ReadAllBytes(path);
				value = new Texture2D(2, 2, TextureFormat.ARGB32, mipChain: false);
				value.filterMode = FilterMode.Point;
				value.wrapMode = TextureWrapMode.Clamp;
				value.LoadImage(data);
				if (bNorm)
				{
					value = ShaderSetup.NormalPNGtoDXTnm(value);
				}
				dictImages[strFileName] = value;
				data = null;
				path = null;
				value.name = strFileName;
				return value;
			}
		}
		if (!bSuppressGetErrors)
		{
			UnityEngine.Debug.Log("#Info# Unable to load PNG: " + strFileName);
		}
		value = Resources.Load("Sprites/missing") as Texture2D;
		dictImages[strFileName] = value;
		value.name = "missing.png";
		return value;
	}

	public static Dictionary<string, Texture2D> LoadPNGFolder(string directoryPath, bool bNorm)
	{
		Dictionary<string, Texture2D> dictionary = new Dictionary<string, Texture2D>();
		try
		{
			foreach (string aModPath in aModPaths)
			{
				string path = aModPath + "images/" + directoryPath;
				if (!Directory.Exists(path))
				{
					continue;
				}
				foreach (string item in Directory.GetFiles(path, "*.png", SearchOption.AllDirectories).ToList())
				{
					string fileName = Path.GetFileName(item);
					dictionary.Add(Path.GetFileNameWithoutExtension(item), LoadPNG(directoryPath + fileName, bNorm));
				}
			}
		}
		catch (Exception ex)
		{
			UnityEngine.Debug.LogWarning("Could not load png folder " + ex.Message);
		}
		return dictionary;
	}

	public static GameObject[] LoadOBJ(string strFileName)
	{
		string text = strAssetPath + "mesh/" + strFileName;
		if (!File.Exists(text))
		{
			UnityEngine.Debug.Log("Unable to load mesh: " + text);
			return null;
		}
		return ObjReader.use.ConvertFile(text, useMtl: true);
	}

	public static string SaveFileExists(string strFileName)
	{
		string text = strFileName;
		if (!File.Exists(strFileName))
		{
			if (!File.Exists(text))
			{
				UnityEngine.Debug.Log("Error: Unable to find save file: " + text);
				return null;
			}
		}
		else
		{
			text = strFileName;
		}
		return text;
	}

	public static JsonGameSave LoadSaveFile(string strFileName)
	{
		string text = SaveFileExists(strFileName);
		if (text == null)
		{
			return null;
		}
		Dictionary<string, JsonGameSave> dictionary = new Dictionary<string, JsonGameSave>();
		JsonToData(text, dictionary);
		using (Dictionary<string, JsonGameSave>.ValueCollection.Enumerator enumerator = dictionary.Values.GetEnumerator())
		{
			if (enumerator.MoveNext())
			{
				return enumerator.Current;
			}
		}
		UnityEngine.Debug.Log("Error: Unable to parse save file: " + text);
		return null;
	}

	public static JsonGameSave LoadSaveFile(string strFileName, Dictionary<string, byte[]> dictFiles)
	{
		if (dictFiles == null)
		{
			return LoadSaveFile(strFileName);
		}
		if (string.IsNullOrEmpty(strFileName) || dictFiles.Count == 0)
		{
			UnityEngine.Debug.Log("Error: Invalid save file: " + strFileName);
			return null;
		}
		Dictionary<string, JsonGameSave> dictionary = new Dictionary<string, JsonGameSave>();
		JsonToData(strFileName, dictionary, dictFiles);
		using (Dictionary<string, JsonGameSave>.ValueCollection.Enumerator enumerator = dictionary.Values.GetEnumerator())
		{
			if (enumerator.MoveNext())
			{
				return enumerator.Current;
			}
		}
		UnityEngine.Debug.Log("Error: Unable to parse save file: " + strFileName);
		return null;
	}

	public static string ConvertStringToFileSafe(string strIn)
	{
		if (strIn == null)
		{
			return null;
		}
		char[] invalidFileNameChars = Path.GetInvalidFileNameChars();
		foreach (char oldChar in invalidFileNameChars)
		{
			strIn = strIn.Replace(oldChar, '-');
		}
		if (strIn.Length > 0 && strIn[strIn.Length - 1] == '.')
		{
			strIn = strIn.Replace(strIn[strIn.Length - 1], '-');
		}
		return strIn;
	}

	public static void CreateSimpleConditionFromString(string str)
	{
		_ = dictConds["Simple"];
		JsonCond jsonCond = new JsonCond();
		jsonCond.strName = str;
		jsonCond.strNameFriendly = str;
		jsonCond.strDesc = str;
		jsonCond.strColor = "Neutral";
		jsonCond.nDisplaySelf = 2;
		jsonCond.nDisplayOther = 2;
		dictConds.TryAdd(str, jsonCond);
	}

	private static void ParseConditionsSimple(Dictionary<string, JsonSimple> dictSimple)
	{
		foreach (KeyValuePair<string, JsonSimple> item in dictSimple)
		{
			for (int i = 0; i < item.Value.aValues.Length - 1; i += 7)
			{
				JsonCond jsonCond = dictConds["Simple"];
				JsonCond jsonCond2 = new JsonCond();
				jsonCond2.strName = item.Value.aValues[i];
				jsonCond2.strNameFriendly = item.Value.aValues[i + 1];
				jsonCond2.strDesc = item.Value.aValues[i + 2];
				jsonCond2.aNext = jsonCond.aNext;
				jsonCond2.strColor = item.Value.aValues[i + 5];
				jsonCond2.bResetTimer = jsonCond.bResetTimer;
				int result = 0;
				if (int.TryParse(item.Value.aValues[i + 3], out result))
				{
					jsonCond2.nDisplaySelf = result;
				}
				result = 0;
				if (int.TryParse(item.Value.aValues[i + 4], out result))
				{
					jsonCond2.nDisplayOther = result;
				}
				bool result2 = false;
				if (bool.TryParse(item.Value.aValues[i + 6], out result2))
				{
					jsonCond2.bInvert = result2;
				}
				jsonCond2.bFatal = jsonCond.bFatal;
				jsonCond2.bRemoveAll = jsonCond.bRemoveAll;
				jsonCond2.aNext = jsonCond.aNext;
				jsonCond2.fDuration = jsonCond.fDuration;
				dictConds[jsonCond2.strName] = jsonCond2;
			}
		}
	}

	private static void ParseSimpleIntoStringDict(Dictionary<string, JsonSimple> dictSimple, Dictionary<string, string> dict)
	{
		if (dict == null)
		{
			UnityEngine.Debug.LogError("ERROR: Trying to parse JsonSimple dictionary into null dictionary. Aborting.");
			return;
		}
		if (dictSimple == null)
		{
			UnityEngine.Debug.LogError("ERROR: Trying to parse null dictionary into <string, string> dictionary. Aborting.");
			return;
		}
		using Dictionary<string, JsonSimple>.Enumerator enumerator = dictSimple.GetEnumerator();
		if (enumerator.MoveNext())
		{
			dict = ConvertStringArrayToDict(enumerator.Current.Value.aValues, dict);
		}
	}

	private static void ParseManPages(Dictionary<string, JsonSimple> dict)
	{
		using (Dictionary<string, JsonSimple>.Enumerator enumerator = dict.GetEnumerator())
		{
			if (enumerator.MoveNext())
			{
				KeyValuePair<string, JsonSimple> current = enumerator.Current;
				dictManPages[current.Value.strName] = current.Value.aValues;
			}
		}
		dictSimple.Clear();
	}

	private static void ParseTraitScores(Dictionary<string, JsonSimple> dict)
	{
		using Dictionary<string, JsonSimple>.Enumerator enumerator = dict.GetEnumerator();
		if (!enumerator.MoveNext())
		{
			return;
		}
		string[] aValues = enumerator.Current.Value.aValues;
		for (int i = 0; i < aValues.Length; i++)
		{
			string[] array = aValues[i].Split(',');
			if (!dictConds.ContainsKey(array[0]))
			{
				UnityEngine.Debug.Log("Warning: Trait score " + array[0] + " refers to non-existent condition.");
				continue;
			}
			dictTraitScores[array[0]] = new int[2]
			{
				Convert.ToInt32(array[1]),
				Convert.ToInt32(array[2])
			};
		}
	}

	private static void ParseGUIPropMaps()
	{
		foreach (KeyValuePair<string, JsonGUIPropMap> item in dictGUIPropMapUnparsed)
		{
			dictGUIPropMaps[item.Key] = ConvertStringArrayToDict(item.Value.dictGUIPropMap);
		}
	}

	public static void ParseMusic()
	{
		foreach (KeyValuePair<string, JsonMusic> item in dictMusic)
		{
			string[] strTags = item.Value.strTags;
			if (strTags == null || strTags.Length == 0)
			{
				continue;
			}
			string[] array = strTags;
			foreach (string text in array)
			{
				if (text != null)
				{
					if (!dictMusicTags.ContainsKey(text))
					{
						dictMusicTags[text] = new List<string>();
					}
					dictMusicTags[text].Add(item.Key);
				}
			}
		}
	}

	private static void ParseJDictLoots()
	{
		foreach (JsonLoot value in dictJLoot.Values)
		{
			Loot loot = Loot.CloneFromJSON(value);
			if (loot.strName != null)
			{
				dictLoot.TryAdd(loot.strName, loot);
			}
		}
	}

	private static void ParseJDictCTs()
	{
		foreach (JsonCondTrigger value in dictJCTs.Values)
		{
			CondTrigger condTrigger = CondTrigger.CloneFromJSON(value);
			if (condTrigger.strName != null)
			{
				dictCTs.TryAdd(condTrigger.strName, condTrigger);
			}
		}
		foreach (CondTrigger value2 in dictCTs.Values)
		{
			value2.PostInit();
		}
	}

	private static void ParseRoomSpecs(Dictionary<string, JsonRoomSpec> jsonRoomSpecs)
	{
		foreach (KeyValuePair<string, JsonRoomSpec> jsonRoomSpec in jsonRoomSpecs)
		{
			RoomSpec roomSpec = new RoomSpec(jsonRoomSpec.Value);
			dictRoomSpec.Add(roomSpec.strName, roomSpec);
		}
		dictRoomSpecsTemp.Clear();
	}

	public static Dictionary<string, string> ConvertStringArrayToDict(string[] aStrings, Dictionary<string, string> dict = null)
	{
		if (dict == null)
		{
			dict = new Dictionary<string, string>();
		}
		if (aStrings != null)
		{
			for (int i = 0; i < aStrings.Length - 1; i += 2)
			{
				if (aStrings.Length <= i + 1)
				{
					dict[aStrings[i]] = "";
					break;
				}
				dict[aStrings[i]] = aStrings[i + 1];
			}
		}
		return dict;
	}

	public static Dictionary<string, double> ConvertStringArrayToDictDouble(string[] aStrings, Dictionary<string, double> dict = null)
	{
		if (dict == null)
		{
			dict = new Dictionary<string, double>();
		}
		if (aStrings != null)
		{
			for (int i = 0; i < aStrings.Length - 1; i += 2)
			{
				if (aStrings.Length <= i + 1)
				{
					dict[aStrings[i]] = 0.0;
					break;
				}
				double result = 0.0;
				double.TryParse(aStrings[i + 1], out result);
				dict[aStrings[i]] = result;
			}
		}
		return dict;
	}

	public static string[] ConvertDictToStringArray(Dictionary<string, string> dict)
	{
		List<string> list = new List<string>();
		if (dict != null)
		{
			foreach (string key in dict.Keys)
			{
				list.Add(key);
				list.Add(dict[key]);
			}
		}
		return list.ToArray();
	}

	public static string[] ConvertDictToStringArray(Dictionary<string, double> dict)
	{
		List<string> list = new List<string>();
		if (dict != null)
		{
			foreach (string key in dict.Keys)
			{
				list.Add(key);
				list.Add(dict[key].ToString());
			}
		}
		return list.ToArray();
	}

	public static void GetFullName(string strGender, out string strFirstName, out string strLastName)
	{
		if (dictNamesFull.Count > 0 && UnityEngine.Random.Range(0f, 1f) < fChanceFullname)
		{
			List<string> list = new List<string>(dictNamesFull.Keys);
			string text = list[UnityEngine.Random.Range(0, list.Count)];
			int num = 50;
			int num2 = 0;
			while (strGender != "IsNB" && dictNamesFull[text] != strGender)
			{
				text = list[UnityEngine.Random.Range(0, list.Count)];
				num2++;
				if (num2 >= num)
				{
					break;
				}
			}
			string[] array = text.Split('|');
			strFirstName = array[0];
			strLastName = array[1];
			dictNamesFull.Remove(text);
		}
		else
		{
			strFirstName = GetName(bFirst: true, strGender);
			strLastName = GetName(bFirst: false, strGender);
		}
	}

	public static string GetName(bool bFirst, string strGender)
	{
		string text = "NoName";
		if (strGender == "Robot")
		{
			text = GetRandomStringFrom(dictNamesRobots.Keys);
		}
		else if (bFirst)
		{
			if (dictNamesFirst.Count > 0)
			{
				text = "";
				int num = 1;
				int num2 = 0;
				if (UnityEngine.Random.Range(0, 100) < 15)
				{
					num++;
				}
				List<string> list = new List<string>(dictNamesFirst.Keys);
				string text2 = "";
				int num3 = 50;
				int num4 = 0;
				while (num2 < num)
				{
					text2 = list[UnityEngine.Random.Range(0, list.Count)];
					if (NameMatchesGender(text2, strGender))
					{
						if (text.Length > 0)
						{
							text += " ";
						}
						text += text2;
						num2++;
					}
					num4++;
					if (num4 >= num3)
					{
						break;
					}
				}
			}
		}
		else
		{
			text = GetRandomStringFrom(dictNamesLast.Keys);
		}
		if (text == null)
		{
			text = "";
		}
		return new CultureInfo("en-US", useUserOverride: false).TextInfo.ToTitleCase(text.ToLower());
	}

	public static string GetRandomStringFrom(IEnumerable<string> aSource)
	{
		if (aSource != null)
		{
			List<string> list = aSource.ToList();
			if (list.Count <= 0)
			{
				return null;
			}
			int index = UnityEngine.Random.Range(0, list.Count - 1);
			return list[index];
		}
		return null;
	}

	private static bool NameMatchesGender(string strName, string strGender)
	{
		if (!dictNamesFirst.ContainsKey(strName))
		{
			return false;
		}
		if (strGender == "IsNB" || dictNamesFirst[strName] == strGender)
		{
			return true;
		}
		return false;
	}

	public static string EmbellishName(string strName, bool bFirst, string strGender)
	{
		float num = MathUtils.Rand(0f, 1f, MathUtils.RandType.Flat);
		if (bFirst)
		{
			if (num <= 0.5f)
			{
				strName = strName + " " + GetName(bFirst, strGender);
			}
			else if (num <= 1f)
			{
				strName = GetInitials(strName, ". ");
			}
		}
		else if (num <= 0.4f)
		{
			strName = GetName(bFirst, strGender) + "-" + strName;
		}
		else if (num <= 0.7f)
		{
			if (strName.IndexOf(GetString("NAME_EMBELLISH_SUFFIX1")) < 0)
			{
				strName = strName + " " + GetString("NAME_EMBELLISH_SUFFIX1");
			}
		}
		else if (num <= 1f && strName.IndexOf(GetString("NAME_EMBELLISH_SUFFIX2")) < 0)
		{
			strName = strName + " " + GetString("NAME_EMBELLISH_SUFFIX2");
		}
		return strName;
	}

	public static string GetInitials(string names, string separator)
	{
		return new Regex("\\s*([^\\s])[^\\s]*\\s*").Replace(names, "$1" + separator).ToUpper();
	}

	public static string GetShipName()
	{
		string text = "NoName";
		if (UnityEngine.Random.Range(0f, 1f) > 0.6f)
		{
			return GetRandomStringFrom(dictNamesShip.Keys);
		}
		text = GetRandomStringFrom(dictNamesShipAdjectives.Keys);
		return text + " " + GetRandomStringFrom(dictNamesShipNouns.Keys);
	}

	public static string GetColorHTML(string strName)
	{
		string value = null;
		if (!dictHTMLColors.TryGetValue(strName, out value))
		{
			value = ColorUtility.ToHtmlStringRGB(GetColor(strName));
			dictHTMLColors[strName] = value;
		}
		return value;
	}

	public static Color GetColor(string strName)
	{
		if (dictColors.ContainsKey(strName))
		{
			return dictColors[strName];
		}
		if (!dictJsonColors.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Color not found: " + strName);
			return Color.magenta;
		}
		dictColors[strName] = dictJsonColors[strName].GetColor();
		return dictColors[strName];
	}

	public static string GetString(string strName, bool allowEmpty = false)
	{
		if (string.IsNullOrEmpty(strName))
		{
			if (!allowEmpty)
			{
				return "UNKNOWN_STRING";
			}
			return "";
		}
		if (!dictStrings.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load string: " + strName);
			if (!allowEmpty)
			{
				return "UNKNOWN_STRING";
			}
			return "";
		}
		return dictStrings[strName];
	}

	[NotNull]
	public static Loot GetLoot(string strName)
	{
		if (strName == null)
		{
			return new Loot();
		}
		if (!dictLoot.ContainsKey(strName))
		{
			if (!string.IsNullOrEmpty(strName))
			{
				UnityEngine.Debug.Log("#Info# Unable to load Loot: " + strName);
			}
			return new Loot();
		}
		return dictLoot[strName];
	}

	public static Condition GetCond(string strName)
	{
		if (strName == null)
		{
			return null;
		}
		if (dictConds.TryGetValue(strName, out var value) && value != null)
		{
			return new Condition(dictConds[strName]);
		}
		return null;
	}

	public static JsonAsteroidClusterBlueprint GetAsteroidClusterBlueprint(string strName)
	{
		if (!dictAsteroidClusterBlueprints.ContainsKey(strName))
		{
			if (!string.IsNullOrEmpty(strName))
			{
				UnityEngine.Debug.Log("Unable to load Asteroid Cluster Blueprint: " + strName);
			}
			return null;
		}
		return dictAsteroidClusterBlueprints[strName];
	}

	public static JsonAsteroidBlueprint GetAsteroidBlueprint(string strName)
	{
		if (!dictAsteroidBlueprints.ContainsKey(strName))
		{
			if (!string.IsNullOrEmpty(strName))
			{
				UnityEngine.Debug.Log("Unable to load Asteroid Blueprint: " + strName);
			}
			return null;
		}
		return dictAsteroidBlueprints[strName];
	}

	public static JsonLight GetLight(string strName)
	{
		if (strName != null && dictLights.ContainsKey(strName) && dictLights[strName] != null)
		{
			return dictLights[strName];
		}
		return null;
	}

	public static JsonItemDef GetItemDef(string strName)
	{
		if (strName != null && dictItemDefs.ContainsKey(strName))
		{
			return dictItemDefs[strName];
		}
		UnityEngine.Debug.Log("Unable to load Item Def: " + strName);
		return null;
	}

	public static Producer GetProductionMap(string name)
	{
		if (dictProductionMaps.TryGetValue(name, out var value) && value != null)
		{
			return new Producer(value);
		}
		return null;
	}

	public static MarketActorConfig GetMarketConfig(string jConfigName)
	{
		if (string.IsNullOrEmpty(jConfigName))
		{
			return null;
		}
		if (dictMarketConfigs.TryGetValue(jConfigName, out var value))
		{
			return new MarketActorConfig(value);
		}
		UnityEngine.Debug.LogError("MarketConfig not found: " + jConfigName);
		return null;
	}

	public static List<JsonCargoSpec> GetCargoRequirements(string[] names)
	{
		if (names == null || names.Length == 0 || dictCargoSpecs == null)
		{
			return null;
		}
		List<JsonCargoSpec> list = null;
		foreach (string key in names)
		{
			if (dictCargoSpecs.TryGetValue(key, out var value))
			{
				if (list == null)
				{
					list = new List<JsonCargoSpec>();
				}
				list.Add(value);
			}
		}
		return list;
	}

	public static CondOwner GetCondOwner(string strCO)
	{
		return GetCondOwner(strCO, null, null, bLoot: true);
	}

	public static CondOwner GetCondOwner(string strCO, string strIDOld)
	{
		return GetCondOwner(strCO, null, null, bLoot: true, null, null, strIDOld);
	}

	public static CondOwner GetCondOwner(string strCO, string strName, string strPortraitImg, bool bLoot, string strPrefab = null, JsonCondOwnerSave jcos = null, string strIDOld = null, Transform parent = null)
	{
		if (strCO == null && strName == null)
		{
			UnityEngine.Debug.Log("Unable to load null CO.");
			return null;
		}
		if (strName != null && jcos == null)
		{
			if (mapCOs.ContainsKey(strName))
			{
				return mapCOs[strName];
			}
			if (dictCOSaves.ContainsKey(strName))
			{
				return GetCondOwner(dictCOSaves[strName].strCODef, strName, null, bLoot: false, null, dictCOSaves[strName]);
			}
		}
		if (strCO == null)
		{
			UnityEngine.Debug.Log("Unable to load null CO.");
			return null;
		}
		JsonCOOverlay jsonCOOverlay = null;
		if (!dictCOs.ContainsKey(strCO))
		{
			if (!dictCOOverlays.ContainsKey(strCO))
			{
				UnityEngine.Debug.Log("Unable to load CO: " + strCO);
				return null;
			}
			jsonCOOverlay = dictCOOverlays[strCO];
			strCO = jsonCOOverlay.strCOBase;
		}
		CondOwner condOwner = null;
		string text = GetNextID();
		string text2 = strName;
		if (strName == null)
		{
			strName = strCO + text;
		}
		if (strIDOld != null)
		{
			text = strIDOld;
			if (jcos != null)
			{
				strName = jcos.strCondID;
			}
		}
		else if (jcos != null)
		{
			text = jcos.strID;
			strName = jcos.strCondID;
		}
		JsonCondOwner value = null;
		if (!dictCOs.TryGetValue(strCO, out value))
		{
			string text3 = "Unable to load base CO: " + strCO;
			if (jsonCOOverlay != null)
			{
				text3 = text3 + " for COOverlay " + jsonCOOverlay.strName;
			}
			UnityEngine.Debug.Log(text3);
			return null;
		}
		if (value.strType.ToLower() == "item")
		{
			if (strPrefab == null)
			{
				strPrefab = "prefabQuad";
			}
			GameObject mesh = GetMesh(strPrefab, parent);
			mesh.AddComponent<Item>().SetData(value.strItemDef, 0f, 0f);
			condOwner = mesh.AddComponent<CondOwner>();
			condOwner.strID = text;
			condOwner.SetData(value, bLoot, jcos);
			if (strPortraitImg != null)
			{
				condOwner.strPortraitImg = strPortraitImg;
			}
			condOwner.Item.VisualizeOverlays();
		}
		else if (value.strType.ToLower() == "crew")
		{
			GameObject mesh = GetMesh("prefabCrew2");
			condOwner = mesh.AddComponent<CondOwner>();
			condOwner.strID = strName;
			condOwner.SetData(value, bLoot, jcos);
			if (strPortraitImg != null)
			{
				condOwner.strPortraitImg = strPortraitImg;
			}
			condOwner.strName = strName;
			condOwner.strNameFriendly = strName;
		}
		else if (value.strType.ToLower().Contains("robot"))
		{
			GameObject mesh = GetMesh("prefab" + value.strType);
			condOwner = mesh.AddComponent<CondOwner>();
			condOwner.strID = strName;
			condOwner.SetData(value, bLoot, jcos);
			if (strPortraitImg != null)
			{
				condOwner.strPortraitImg = strPortraitImg;
			}
			condOwner.strName = strName;
			condOwner.strNameFriendly = strName;
		}
		else if (value.strType.ToLower() == "ship")
		{
			if (!string.IsNullOrEmpty(text2))
			{
				strName = text2;
			}
			GameObject mesh = new GameObject(strName);
			if (parent != null)
			{
				mesh.transform.SetParent(parent);
			}
			condOwner = mesh.AddComponent<CondOwner>();
			condOwner.SetData(value, bLoot, jcos);
			condOwner.strID = "CO-" + strName;
			condOwner.strName = "CO-" + strName;
			if (jcos != null)
			{
				jcos.strCondID = strName;
			}
		}
		condOwner.gameObject.name = condOwner.ToString();
		JsonCond jsonIn = dictConds["UniqueID"];
		condOwner.objCondID = new Condition(jsonIn);
		condOwner.objCondID.strName = strName;
		if (jcos != null)
		{
			condOwner.objCondID.strName = jcos.strCondID;
		}
		condOwner.objCondID.fCount = 1.0;
		condOwner.mapConds[condOwner.objCondID.strName] = condOwner.objCondID;
		mapCOs[condOwner.strID] = condOwner;
		if (jsonCOOverlay != null)
		{
			condOwner.gameObject.AddComponent<COOverlay>().Init(jsonCOOverlay.strName);
		}
		debugCOCount++;
		return condOwner;
	}

	private static void BuildDataCO(string strCO, JsonCOOverlay jcoo, JsonCondOwner jco)
	{
		string key = strCO;
		if (jcoo != null)
		{
			key = jcoo.strName;
			strCO = jcoo.strCOBase;
		}
		if (jco != null || dictCOs.TryGetValue(strCO, out jco))
		{
			JsonItemDef itemDef = GetItemDef(jco.strItemDef);
			dictDataCOs[key] = new DataCO(jco, jcoo, itemDef);
		}
	}

	private static void BuildHealthLibrary()
	{
		Dictionary<string, double> dictionary = new Dictionary<string, double>();
		foreach (KeyValuePair<string, DataCO> dictDataCO in dictDataCOs)
		{
			double maxHealth = dictDataCO.Value.GetMaxHealth();
			dictionary[dictDataCO.Key] = maxHealth;
		}
	}

	public static DataCO GetDataCO(string strCO)
	{
		if (string.IsNullOrEmpty(strCO))
		{
			return null;
		}
		if (dictDataCOs.TryGetValue(strCO, out var value))
		{
			return value;
		}
		if (dictCOOverlays.TryGetValue(strCO, out var value2))
		{
			strCO = value2.strCOBase;
		}
		if (!dictCOs.TryGetValue(strCO, out var value3))
		{
			return null;
		}
		JsonItemDef itemDef = GetItemDef(value3.strItemDef);
		value = new DataCO(value3, value2, itemDef);
		dictDataCOs[strCO] = value;
		return value;
	}

	public static CondOwner GetCOPlaceholder(CondOwner coCursor, CondOwner coTarget, string strInstallIA)
	{
		JsonItemDef value = null;
		if (coCursor == null)
		{
			UnityEngine.Debug.Log("Unable to load COPlaceholder: Cursor is null.");
			return null;
		}
		if (coTarget == null || !dictItemDefs.TryGetValue(coCursor.strItemDef, out value))
		{
			UnityEngine.Debug.Log("Unable to load COPlaceholder: " + coCursor.strItemDef + " with target " + coTarget);
			return null;
		}
		CondOwner condOwner = null;
		string nextID = GetNextID();
		JsonCondOwner jid = dictCOs["Placeholder"];
		GameObject mesh = GetMesh("prefabQuadPlaceholder");
		JsonCOOverlay value2 = null;
		dictCOOverlays.TryGetValue(coCursor.strName, out value2);
		condOwner = mesh.AddComponent<CondOwner>();
		condOwner.strID = nextID;
		condOwner.SetData(jid, bLoot: false);
		condOwner.strName = coCursor.strName + "_Placeholder";
		condOwner.strNameFriendly = coCursor.FriendlyName + " Placeholder";
		condOwner.strPortraitImg = value.strImg;
		if (value2 != null)
		{
			condOwner.strPortraitImg = value2.strPortraitImg;
		}
		foreach (KeyValuePair<string, Vector2> mapPoint in coCursor.mapPoints)
		{
			condOwner.mapPoints[mapPoint.Key] = mapPoint.Value;
		}
		Item item = mesh.AddComponent<Item>();
		item.bPlaceholder = true;
		item.SetData(coCursor.strItemDef, 0f, 0f);
		condOwner.gameObject.name = condOwner.ToString();
		if (value2 != null)
		{
			item.SetAlt(value2.strImg, value2.strImgNorm, value2.strImgDamaged, value2.strDmgColor);
		}
		condOwner.transform.position = coCursor.transform.position;
		item.fLastRotation = coCursor.transform.rotation.eulerAngles.z;
		condOwner.gameObject.AddComponent<Placeholder>().Init(coCursor, coTarget, strInstallIA);
		Destructable component = coTarget.GetComponent<Destructable>();
		if (component != null)
		{
			Destructable destructable = condOwner.gameObject.GetComponent<Destructable>();
			if (destructable == null)
			{
				destructable = condOwner.gameObject.AddComponent<Destructable>();
			}
			else
			{
				destructable.ClearChecks();
			}
			destructable.CopyFrom(component);
			foreach (DestCheck aCheck in component.aChecks)
			{
				condOwner.SetCondAmount(aCheck.strDamageCond, coTarget.GetCondAmount(aCheck.strDamageCond));
				condOwner.SetCondAmount(aCheck.strDamageCondMax, coTarget.GetCondAmount(aCheck.strDamageCondMax));
				if (!condOwner.aDestructableConds.Contains(aCheck.strDamageCond))
				{
					condOwner.aDestructableConds.Add(aCheck.strDamageCond);
				}
			}
		}
		COOverlay component2 = coTarget.GetComponent<COOverlay>();
		if (component2 != null)
		{
			condOwner.gameObject.AddComponent<COOverlay>().strName = component2.strName;
		}
		JsonCond jsonIn = dictConds["UniqueID"];
		condOwner.objCondID = new Condition(jsonIn);
		condOwner.objCondID.strName = condOwner.strName;
		condOwner.mapConds[condOwner.objCondID.strName] = condOwner.objCondID;
		mapCOs[condOwner.strID] = condOwner;
		if (condOwner.Item != null)
		{
			condOwner.Item.VisualizeOverlays();
		}
		return condOwner;
	}

	public static Item GetBackground(string strCOName)
	{
		if (strCOName == null)
		{
			UnityEngine.Debug.Log("Unable to load null background.");
			return null;
		}
		JsonCondOwner value = null;
		JsonCOOverlay value2 = null;
		if (dictCOOverlays.TryGetValue(strCOName, out value2))
		{
			dictCOs.TryGetValue(value2.strCOBase, out value);
		}
		if (value == null && !dictCOs.TryGetValue(strCOName, out value))
		{
			string text = "Unable to load base CO: " + strCOName;
			if (value2 != null)
			{
				text = text + " for COOverlay " + value2.strName;
			}
			UnityEngine.Debug.Log(text);
			return null;
		}
		JsonItemDef value3 = null;
		if (!dictItemDefs.TryGetValue(value.strItemDef, out value3))
		{
			UnityEngine.Debug.Log("Unable to load background: " + strCOName);
			return null;
		}
		GameObject mesh = GetMesh("prefabQuad");
		Item item = mesh.AddComponent<Item>();
		item.SetData(value3.strName, 0f, 0f);
		if (value2 != null)
		{
			item.SetAlt(value2.strImg, value2.strImgNorm, value2.strImgDamaged, value2.strDmgColor);
		}
		mesh.name = strCOName;
		return item;
	}

	public static RoomSpec GetRoomDef(string strName)
	{
		if (string.IsNullOrEmpty(strName))
		{
			return null;
		}
		RoomSpec value = null;
		dictRoomSpec.TryGetValue(strName, out value);
		return value;
	}

	public static CondTrigger GetCondTrigger(string strName)
	{
		if (strName != null && dictCTs.TryGetValue(strName, out var value))
		{
			return value.Clone();
		}
		if (!string.IsNullOrEmpty(strName))
		{
			UnityEngine.Debug.Log("No such CT: " + strName);
		}
		if (_blankCTBackup == null && dictCTs["Blank"] != null)
		{
			_blankCTBackup = dictCTs["Blank"].Clone();
		}
		if (dictCTs["Blank"] == null && _blankCTBackup != null)
		{
			dictCTs["Blank"] = _blankCTBackup.Clone();
		}
		return dictCTs["Blank"];
	}

	public static JsonCondOwner GetCondOwnerDef(string strName)
	{
		if (strName == null || !dictCOs.ContainsKey(strName))
		{
			JsonCOOverlay value = null;
			if (strName != null)
			{
				dictCOOverlays.TryGetValue(strName, out value);
			}
			if (value != null && value.strCOBase != null && dictCOs.ContainsKey(value.strCOBase))
			{
				return dictCOs[value.strCOBase];
			}
			UnityEngine.Debug.Log("No such CO: " + strName);
			return null;
		}
		return dictCOs[strName];
	}

	public static JsonLedgerDef GetLedgerDef(string strName)
	{
		if (strName == null || !dictLedgerDefs.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such LedgerDef: " + strName);
			return null;
		}
		return dictLedgerDefs[strName];
	}

	public static Type GetCommand(string name)
	{
		name = "Ostranauts.Ships.Commands." + name;
		Type type = Type.GetType(name);
		if (type != null && type.IsClass && type.GetInterfaces().Contains(typeof(ICommand)))
		{
			return type;
		}
		return null;
	}

	public static JsonPledge GetPledge(string strName)
	{
		if (strName == null || !dictPledges.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Pledge: " + strName);
			return null;
		}
		return dictPledges[strName];
	}

	public static JsonParallax GetParallax(string strName)
	{
		if (strName == null || !dictParallax.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Parallax: " + strName);
			return null;
		}
		return dictParallax[strName];
	}

	public static JsonZoneTrigger GetZoneTrigger(string strName)
	{
		if (strName == null || !dictZoneTriggers.ContainsKey(strName))
		{
			if (!string.IsNullOrEmpty(strName))
			{
				UnityEngine.Debug.Log("No such zone trigger: " + strName);
			}
			return null;
		}
		return dictZoneTriggers[strName];
	}

	public static JsonChargeProfile GetChargeProfile(string strName)
	{
		if (strName == null || !dictChargeProfiles.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Chargeprofile: " + strName);
			return null;
		}
		return dictChargeProfiles[strName];
	}

	public static JsonWound GetWound(string strName)
	{
		if (strName == null || !dictWounds.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Wound: " + strName);
			return null;
		}
		return dictWounds[strName];
	}

	public static JsonAttackMode GetAttackMode(string strName)
	{
		if (strName == null || !dictAModes.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such AttackMode: " + strName);
			return dictAModes["AModeBlank"];
		}
		return dictAModes[strName];
	}

	public static JsonShipAttack GetShipAttack(string strName)
	{
		if (strName == null || !dictShipAttacks.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such AttackMode: " + strName);
			return null;
		}
		return dictShipAttacks[strName];
	}

	public static JsonContext GetContext(string strName)
	{
		if (strName == null || !dictContext.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Context: " + strName);
			return null;
		}
		return dictContext[strName];
	}

	public static JsonJob GetJob(string strName)
	{
		if (strName == null || !dictJobs.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Job: " + strName);
			return null;
		}
		return dictJobs[strName];
	}

	public static JsonBounty GetBounty(string strName)
	{
		if (!string.IsNullOrEmpty(strName) && dictBounties.TryGetValue(strName, out var value))
		{
			return value;
		}
		UnityEngine.Debug.Log("No such Bounty: " + strName);
		return null;
	}

	public static JsonTransit GetTransitConnections(string shipOrigin)
	{
		if (dictTransit == null || shipOrigin == null)
		{
			return null;
		}
		if (shipOrigin.Contains("|"))
		{
			shipOrigin = shipOrigin.Substring(0, shipOrigin.IndexOf("|") + 1);
		}
		JsonTransit value = null;
		dictTransit.TryGetValue(shipOrigin, out value);
		return value;
	}

	public static JsonCrime GetCrime(string strName)
	{
		if (strName == null || !dictCrimes.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Crime: " + strName);
			return null;
		}
		return dictCrimes[strName];
	}

	public static JsonPlot GetPlot(string strName)
	{
		if (strName == null || !dictPlots.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Plot: " + strName);
			return null;
		}
		return dictPlots[strName];
	}

	public static JsonPlotBeat GetPlotBeat(string strName)
	{
		if (strName == null || !dictPlotBeats.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such PlotBeat: " + strName);
			return null;
		}
		return dictPlotBeats[strName];
	}

	public static JsonExplosion GetExplosion(string strName)
	{
		if (strName == null || !dictExplosions.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Explosion: " + strName);
			return null;
		}
		return dictExplosions[strName];
	}

	public static JsonEnvironmentMap GetEnvironmentMap(double condValue)
	{
		string text = ((int)Math.Floor(condValue)).ToString();
		if (dictEnvironmentMaps.TryGetValue(text, out var value))
		{
			return value;
		}
		UnityEngine.Debug.Log("No Environment Map with ID: " + text);
		return null;
	}

	public static JsonRaceTrack GetRaceTrack(string strName)
	{
		if (strName == null || !dictRaceTracks.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such Racetrack: " + strName);
			return null;
		}
		return dictRaceTracks[strName];
	}

	public static JsonRacingLeague GetRaceLeague(string strName)
	{
		if (strName == null || !dictRacingLeagues.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such League: " + strName);
			return null;
		}
		return dictRacingLeagues[strName];
	}

	public static JsonJobItems GetJobItems(string strName)
	{
		if (strName == null || !dictJobitems.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such JobItems: " + strName);
			return null;
		}
		return dictJobitems[strName];
	}

	public static string GetCOShortName(string strCOName)
	{
		if (strCOName == null)
		{
			return null;
		}
		string result = strCOName;
		JsonCOOverlay value = null;
		dictCOOverlays.TryGetValue(strCOName, out value);
		if (value != null && value.strNameShort != null)
		{
			result = value.strNameShort;
		}
		else
		{
			JsonCondOwner condOwnerDef = GetCondOwnerDef(strCOName);
			if (condOwnerDef != null && condOwnerDef.strNameShort != null)
			{
				result = condOwnerDef.strNameShort;
			}
		}
		return result;
	}

	public static string GetCOFriendlyName(string strCOName)
	{
		if (strCOName == null)
		{
			return null;
		}
		string result = strCOName;
		JsonCOOverlay value = null;
		dictCOOverlays.TryGetValue(strCOName, out value);
		if (value != null && value.strNameFriendly != null)
		{
			result = value.strNameFriendly;
		}
		else
		{
			JsonCondOwner condOwnerDef = GetCondOwnerDef(strCOName);
			if (condOwnerDef != null && condOwnerDef.strNameFriendly != null)
			{
				result = condOwnerDef.strNameFriendly;
			}
		}
		return result;
	}

	public static string GetCondFriendlyName(string strCondName)
	{
		if (strCondName == null)
		{
			return null;
		}
		string result = strCondName;
		if (dictConds.ContainsKey(strCondName))
		{
			JsonCond jsonCond = dictConds[strCondName];
			if (jsonCond != null && jsonCond.strNameFriendly != null)
			{
				result = jsonCond.strNameFriendly;
			}
		}
		return result;
	}

	public static bool TryGetInteraction(string strName, out Interaction interaction, JsonInteractionSave jis = null, bool getTrackedObject = false)
	{
		if (strName == null || !dictInteractions.ContainsKey(strName))
		{
			interaction = null;
			return false;
		}
		interaction = ((getTrackedObject && _interactionObjectTracker != null) ? _interactionObjectTracker.GetObject(dictInteractions[strName], jis) : new Interaction(dictInteractions[strName], jis));
		return true;
	}

	public static Interaction GetInteraction(string strName, JsonInteractionSave jis = null, bool getTrackedObject = false)
	{
		if (strName == null || !dictInteractions.ContainsKey(strName))
		{
			if (strName != "" && strName != null)
			{
				UnityEngine.Debug.Log("#Info# No such Interaction: " + strName);
			}
			return null;
		}
		if (!getTrackedObject || _interactionObjectTracker == null)
		{
			return new Interaction(dictInteractions[strName], jis);
		}
		return _interactionObjectTracker.GetObject(dictInteractions[strName], jis);
	}

	private static void UnpackTokens()
	{
		foreach (KeyValuePair<string, JsonCustomTokens> dictJsonToken in dictJsonTokens)
		{
			if (dictJsonToken.Value.type.IsNullOrEmpty())
			{
				continue;
			}
			switch (dictJsonToken.Value.type)
			{
			case "aliases":
			{
				if (dictJsonToken.Value.tokens == null)
				{
					break;
				}
				aliases.AddRange(dictJsonToken.Value.tokens);
				int num = 0;
				string[] tokens2 = dictJsonToken.Value.tokens;
				foreach (string key in tokens2)
				{
					if (!GrammarUtils.entityMap.TryGetValue(key, out var _))
					{
						GrammarUtils.SentenceEntity sentenceEntity = new GrammarUtils.SentenceEntity();
						if (dictJsonToken.Value.tokens2 != null && num < dictJsonToken.Value.tokens2.Length)
						{
							sentenceEntity.pspec = dictJsonToken.Value.tokens2[num][0];
						}
						GrammarUtils.entityMap.Add(key, sentenceEntity);
					}
					num++;
				}
				break;
			}
			case "categories":
			{
				if (dictJsonToken.Value.tokens == null || dictJsonToken.Value.tokens2 == null || dictJsonToken.Value.tokens.Length != dictJsonToken.Value.tokens2.Length)
				{
					break;
				}
				for (int j = 0; j < dictJsonToken.Value.tokens.Length; j++)
				{
					if (!categories.Contains(dictJsonToken.Value.tokens[j]))
					{
						categories.Add(dictJsonToken.Value.tokens[j]);
					}
					GrammarUtils.partsOfSpeechStr.TryAdd(dictJsonToken.Value.tokens[j], dictJsonToken.Value.tokens2[j]);
				}
				break;
			}
			case "verbs":
			{
				if (dictJsonToken.Value.tokens2 == null)
				{
					break;
				}
				string[][] tokens = dictJsonToken.Value.tokens2;
				foreach (string[] array in tokens)
				{
					if (!string.IsNullOrEmpty(array[0]))
					{
						string[] array2 = ((array.Length != 1) ? array : new string[2]
						{
							array[0],
							array[0].Remove(array[0].Length - 1)
						});
						if (!dictVerbs.TryAdd(array2[0], array2))
						{
							dictVerbs[array2[0]] = array2;
						}
					}
				}
				break;
			}
			}
		}
	}

	private static void PrepareConditionDescriptions()
	{
		foreach (KeyValuePair<string, JsonCond> dictCond in dictConds)
		{
			if (!dictCond.Value.strDesc.IsNullOrEmpty())
			{
				PrepareInflectedString(dictCond.Value, dictCond.Value.strDesc);
			}
		}
	}

	private static void PrepareInteractionInflections()
	{
		foreach (KeyValuePair<string, JsonInteraction> dictInteraction in dictInteractions)
		{
			if (!dictInteraction.Value.strTooltip.IsNullOrEmpty())
			{
				PrepareInflectedString(dictInteraction.Value, dictInteraction.Value.strTooltip);
			}
			if (!dictInteraction.Value.strDesc.IsNullOrEmpty())
			{
				PrepareInflectedString(dictInteraction.Value, dictInteraction.Value.strDesc);
			}
		}
	}

	private static void PrepareToken(ref TokenData t, string[] args)
	{
		t.args = args.ToList();
		foreach (string text in args)
		{
			if (aliases.Contains(text))
			{
				t.alias = text;
				t.output = GrammarUtils.AttemptProperName;
			}
			else if (categories.Contains(text))
			{
				t.category = text;
				t.output = GrammarUtils.AttemptSubstitution;
			}
			else if (languages.Contains(text))
			{
				t.lang = text;
			}
			else if (dictVerbs.ContainsKey(text))
			{
				t.output = GrammarUtils.Verb;
				t.verbForms = dictVerbs[text];
			}
			switch (text)
			{
			case "regID":
				t.output = GrammarUtils.RegID;
				break;
			case "shipfriendly":
				t.output = GrammarUtils.ShipFriendly;
				break;
			case "captain":
				t.output = GrammarUtils.Captain;
				break;
			case "data":
				t.output = GrammarUtils.Data;
				break;
			case "txt1":
				t.output = GrammarUtils.Regurg;
				t.regurg = "[txt1]";
				break;
			case "itm":
				t.output = GrammarUtils.Regurg;
				t.regurg = "[itm]";
				break;
			case "x":
				t.output = GrammarUtils.Regurg;
				t.regurg = "[x]";
				break;
			case "object":
				t.output = GrammarUtils.Regurg;
				t.regurg = "[object]";
				break;
			case "purple":
				t.output = GrammarUtils.Regurg;
				t.regurg = "[purple]";
				break;
			case "prereq0":
				t.output = GrammarUtils.Regurg;
				t.regurg = "[prereq0]";
				break;
			case "firstname":
				t.output = GrammarUtils.FirstName;
				break;
			case "fullname":
				t.output = GrammarUtils.ProperName;
				break;
			case "shipname":
				t.output = GrammarUtils.ShipName;
				break;
			case "surname":
				t.output = GrammarUtils.AttemptSurname;
				break;
			case "age":
				t.output = GrammarUtils.GetAge;
				break;
			case "homeworld":
				t.output = GrammarUtils.GetHomeworld;
				break;
			case "custom":
				t.output = GrammarUtils.Custom;
				if (t.args.Count > 2)
				{
					string[] collection = t.args[2].Split('|');
					t.args.RemoveAt(2);
					t.args.AddRange(collection);
				}
				break;
			}
		}
	}

	private static void PrepareInflectedString(object o, string s)
	{
		string alias = "none";
		int num = s.IndexOf('[');
		int num2 = s.IndexOf(']');
		int num3 = 0;
		List<TokenData> list = new List<TokenData>();
		while (num != -1 && num2 != -1)
		{
			num3++;
			if (num3 > 100)
			{
				UnityEngine.Debug.Log("There's a mistaken bracket in " + s);
				break;
			}
			string text = s.Substring(num + 1, num2 - num - 1);
			string[] array = text.Split('-');
			TokenData t = new TokenData
			{
				start = num,
				end = num2,
				alias = alias
			};
			if (array.Length >= 1)
			{
				PrepareToken(ref t, array);
			}
			if (t.output == null)
			{
				UnityEngine.Debug.LogWarning("token made without output: " + text);
				_ = bNodeGraph;
				if (!nonCorresponds.Contains(text))
				{
					UnityEngine.Debug.Log(text + " " + s);
					nonCorresponds.Add(text);
				}
				num = s.IndexOf('[', num2);
				num2 = s.IndexOf(']', num2 + 1);
			}
			else
			{
				list.Add(t);
				alias = t.alias;
				num = s.IndexOf('[', num2);
				num2 = s.IndexOf(']', num2 + 1);
			}
		}
		if (list.Count > 0)
		{
			GrammarUtils.inflectedStrings.TryAdd(s, new InflectedString
			{
				tokens = list
			});
		}
	}

	private static void PrepareInflectedString(string s)
	{
		int num = s.IndexOf('[');
		int num2 = s.IndexOf(']');
		int num3 = 0;
		List<TokenData> list = new List<TokenData>();
		while (num != -1 && num2 != -1)
		{
			num3++;
			if (num3 > 100)
			{
				UnityEngine.Debug.Log("There's a fucked up bracket in " + s);
				break;
			}
			string text = s.Substring(num + 1, num2 - num - 1);
			allbracketText.Add(text);
			bool flag = listCustomTokens.Contains(text);
			bool flag2 = false;
			if (!flag)
			{
				flag2 = dictVerbs.ContainsKey(text);
			}
			bool num4 = flag2 || flag;
			string[] array = text.Split('-');
			if (num4)
			{
				continue;
			}
			if (text.Contains('-'))
			{
				if (dictVerbs.ContainsKey(array[1]))
				{
					flag2 = true;
					text = array[1];
					_ = array[0];
				}
				continue;
			}
			if (!nonCorresponds.Contains(text))
			{
				UnityEngine.Debug.Log(text + " " + s);
				nonCorresponds.Add(text);
			}
			num = s.IndexOf('[', num2);
			num2 = s.IndexOf(']', num2 + 1);
		}
		if (list.Count > 0)
		{
			GrammarUtils.inflectedStrings.TryAdd(s, new InflectedString
			{
				tokens = list
			});
		}
	}

	public static void ReleaseTrackedInteraction(Interaction trackedInteraction)
	{
		if (_interactionObjectTracker != null)
		{
			_interactionObjectTracker.ReleaseObject(trackedInteraction);
		}
	}

	public static void KeepInteraction(Interaction trackedInteraction)
	{
		if (_interactionObjectTracker != null)
		{
			_interactionObjectTracker.UntrackObject(trackedInteraction);
		}
	}

	public static JsonGasRespire GetGasRespire(string strName)
	{
		if (strName == null || !dictGasRespires.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such GasRespire: " + strName);
			return null;
		}
		return dictGasRespires[strName];
	}

	public static JsonPowerInfo GetPowerInfo(string strName)
	{
		if (strName == null || !dictPowerInfo.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such PowerInfo: " + strName);
			return null;
		}
		return dictPowerInfo[strName];
	}

	public static Dictionary<string, string> GetGUIPropMap(string strName)
	{
		if (strName == null || !dictGUIPropMaps.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("No such GUIPropMap: " + strName);
			return null;
		}
		Dictionary<string, string> dictionary = dictGUIPropMaps[strName];
		Dictionary<string, string> dictionary2 = new Dictionary<string, string>();
		foreach (KeyValuePair<string, string> item in dictionary)
		{
			dictionary2[item.Key] = item.Value;
		}
		return dictionary2;
	}

	public static JsonLifeEvent GetLifeEvent(string strName)
	{
		if (strName == null || !dictLifeEvents.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Life Event: " + strName);
			return null;
		}
		return dictLifeEvents[strName];
	}

	public static JsonCareer GetCareer(string strName)
	{
		if (strName == null || !dictCareers.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Career: " + strName);
			return null;
		}
		return dictCareers[strName];
	}

	public static JsonHomeworld GetHomeworld(string strName)
	{
		if (strName == null || !dictHomeworlds.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Homeworld: " + strName);
			return null;
		}
		return dictHomeworlds[strName];
	}

	public static JsonPersonSpec GetPersonSpec(string strName, bool bSuppressLog = false)
	{
		if (strName == null || !dictPersonSpecs.ContainsKey(strName))
		{
			if (strName != "" && strName != null)
			{
				UnityEngine.Debug.Log("Unable to load Person Spec: " + strName);
			}
			return null;
		}
		return dictPersonSpecs[strName];
	}

	public static JsonShipSpec GetShipSpec(string strName)
	{
		if (strName == null || !dictShipSpecs.ContainsKey(strName))
		{
			if (strName != "" && strName != null)
			{
				UnityEngine.Debug.Log("Unable to load Ship Spec: " + strName);
			}
			return null;
		}
		return dictShipSpecs[strName];
	}

	public static JsonSlot GetSlot(string strName)
	{
		if (strName == null || !dictSlots.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Slot: " + strName);
			return null;
		}
		return dictSlots[strName];
	}

	public static JsonSlotEffects GetSlotEffect(string strName)
	{
		if (strName == null || !dictSlotEffects.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Slot_Effect: " + strName);
			return null;
		}
		return dictSlotEffects[strName].Clone();
	}

	public static JsonTicker GetTicker(string strName)
	{
		if (strName == null || !dictTickers.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Ticker: " + strName);
			return null;
		}
		JsonTicker jsonTicker = dictTickers[strName].Clone();
		jsonTicker.fEpochStart = StarSystem.fEpoch;
		return jsonTicker;
	}

	public static GameObject GetVFX(string strName)
	{
		if (string.IsNullOrEmpty(strName))
		{
			return null;
		}
		GameObject value = null;
		if (dictVFX.TryGetValue(strName, out value))
		{
			return value;
		}
		value = Resources.Load(strName) as GameObject;
		dictVFX[strName] = value;
		return value;
	}

	public static JsonShip GetShip(string strName)
	{
		if (strName == null || !dictShips.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Ship: " + strName);
			return null;
		}
		return dictShips[strName];
	}

	public static JsonShipConstructionTemplate GetShipConstructionTemplate(JsonShip jShip)
	{
		if (string.IsNullOrEmpty(jShip.strTemplateName))
		{
			return new JsonShipConstructionTemplate(jShip, 100);
		}
		JsonShip ship = GetShip(jShip.strTemplateName);
		if (ship == null)
		{
			return new JsonShipConstructionTemplate(jShip, 100);
		}
		return ship.GetCurrentConstructionTemplate(jShip.nConstructionProgress);
	}

	public static Dictionary<string, byte[]> GetShipImageByteArrays(string strName)
	{
		if (string.IsNullOrEmpty(strName))
		{
			return null;
		}
		if (dictShipImages.TryGetValue(strName, out var value))
		{
			if (value == null)
			{
				return null;
			}
			Dictionary<string, byte[]> dictionary = new Dictionary<string, byte[]>();
			{
				foreach (KeyValuePair<string, Texture2D> item in value)
				{
					if (!(item.Value == null))
					{
						dictionary.Add(item.Key, item.Value.EncodeToPNG());
					}
				}
				return dictionary;
			}
		}
		return null;
	}

	public static CondRule GetCondRule(string strName)
	{
		if (strName == null || !dictCondRules.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load CondRule: " + strName);
			return null;
		}
		return dictCondRules[strName].Clone();
	}

	public static JsonAudioEmitter GetAudioEmitter(string strName)
	{
		if (strName == null || !dictAudioEmitters.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load AudioEmitter: " + strName);
			return null;
		}
		return dictAudioEmitters[strName];
	}

	public static string GetCrewSkin(string strName)
	{
		if (strName == null || !dictCrewSkins.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load Crew Skin: " + strName);
			return "01";
		}
		return dictCrewSkins[strName];
	}

	public static JsonCOOverlay GetCOOverlay(string strName)
	{
		if (strName == null || !dictCOOverlays.ContainsKey(strName))
		{
			UnityEngine.Debug.Log("Unable to load COOverlay: " + strName);
			return null;
		}
		return dictCOOverlays[strName];
	}

	public static JsonAd GetAd()
	{
		int count = dictAds.Keys.Count;
		if (count == 0)
		{
			UnityEngine.Debug.Log("No ads found.");
			return new JsonAd
			{
				strName = "blank",
				strDesc = "blank"
			};
		}
		JsonAd[] array = new JsonAd[count];
		dictAds.Values.CopyTo(array, 0);
		count = MathUtils.Rand(0, array.Length, MathUtils.RandType.Flat);
		return array[count];
	}

	public static JsonHeadline GetHeadline()
	{
		int count = dictHeadlines.Keys.Count;
		if (count == 0)
		{
			UnityEngine.Debug.Log("No ads found.");
			return new JsonHeadline
			{
				strName = "blank",
				strDesc = "blank",
				strRegion = "blank"
			};
		}
		JsonHeadline[] array = new JsonHeadline[count];
		dictHeadlines.Values.CopyTo(array, 0);
		count = MathUtils.Rand(0, array.Length, MathUtils.RandType.Flat);
		return array[count];
	}

	public static string GetTrackForTag(string strTag)
	{
		if (strTag == null || !dictMusicTags.ContainsKey(strTag))
		{
			UnityEngine.Debug.Log("No such music tag found: " + strTag);
			return null;
		}
		if (dictMusicTags[strTag].Count == 0)
		{
			UnityEngine.Debug.Log("No music found for tag: " + strTag);
			return null;
		}
		int index = MathUtils.Rand(0, dictMusicTags[strTag].Count, MathUtils.RandType.Flat, strTag);
		return dictMusicTags[strTag][index];
	}

	public static string GetMusicForStation(string strRegID)
	{
		if (dictMusicStations == null || string.IsNullOrEmpty(strRegID))
		{
			return null;
		}
		JsonMusicStation value = null;
		dictMusicStations.TryGetValue(strRegID, out value);
		return value?.strMusicTag;
	}

	public static GameObject GetMesh(string strType, Transform parent = null)
	{
		if (parent == null)
		{
			GameObject gameObject = UnityEngine.Object.Instantiate(Resources.Load(strType)) as GameObject;
			if (gameObject != null)
			{
				return gameObject;
			}
			return UnityEngine.Object.Instantiate(Resources.Load("prefabQuad")) as GameObject;
		}
		GameObject gameObject2 = UnityEngine.Object.Instantiate(Resources.Load(strType), parent) as GameObject;
		if (gameObject2 != null)
		{
			return gameObject2;
		}
		return UnityEngine.Object.Instantiate(Resources.Load("prefabQuad"), parent) as GameObject;
	}

	public static Material GetMaterial(Renderer rend, string strImg, string strImgNorm = "blank", string strImgDamaged = "blank", string strDmgColor = "blank")
	{
		string text = strImg + strImgNorm + strImgDamaged + strDmgColor;
		if (dictMaterials.TryGetValue(text, out var value))
		{
			return value;
		}
		value = new Material(rend.material);
		value.SetTexture("_MainTex", LoadPNG(strImg + ".png", bNorm: false));
		value.mainTextureScale = new Vector2(1f, 1f);
		value.mainTextureOffset = default(Vector2);
		if (strImgNorm != "blank")
		{
			value.SetTexture("_BumpMap", LoadPNG(strImgNorm + ".png", bNorm: true));
			value.SetTextureScale("_BumpMap", new Vector2(1f, 1f));
			value.SetTextureOffset("_BumpMap", default(Vector2));
		}
		if (strImgDamaged != "blank")
		{
			if (strImgDamaged == "")
			{
				value.SetFloat("_DmgPresent", 0f);
			}
			else
			{
				value.SetTexture("_DmgTex", LoadPNG(strImgDamaged + ".png", bNorm: false));
				value.SetTextureScale("_DmgTex", new Vector2(1f, 1f));
				value.SetTextureOffset("_DmgTex", default(Vector2));
				value.SetFloat("_DmgPresent", 1f);
			}
		}
		else
		{
			value.SetFloat("_DmgPresent", 0f);
		}
		value.SetVector("_WearCol", Item.GetWearColor(strDmgColor, strImgDamaged));
		value.name = text;
		dictMaterials[text] = value;
		return value;
	}

	public static Material GetMaterialSheet(Renderer rend, string strImg, int nIndex, string strImgNorm = "blank", string strImgDamaged = "blank", string strDmgColor = "blank", int tileWidth = 1, int tileHeight = 1)
	{
		string text = strImg + "Sheet" + nIndex + strImgNorm + strImgDamaged + strDmgColor;
		if (dictMaterials.TryGetValue(text, out var value))
		{
			return value;
		}
		value = new Material(rend.material);
		value.name = text;
		value.SetTexture("_MainTex", LoadPNG(strImg + ".png", bNorm: false));
		float num = 1f * (float)tileWidth * 16f / (float)value.GetTexture("_MainTex").width;
		float num2 = 1f * (float)tileHeight * 16f / (float)value.GetTexture("_MainTex").height;
		value.mainTextureScale = new Vector2(num, num2);
		int num3 = MathUtils.RoundToInt(1f / num);
		int num4 = MathUtils.RoundToInt(1f / num2);
		int num5 = Mathf.FloorToInt(nIndex / num3);
		int num6 = Mathf.FloorToInt(nIndex % num3);
		value.mainTextureOffset = new Vector2(num * (float)num6, num2 * (float)num5);
		if (strImgNorm != "blank")
		{
			value.SetTexture("_BumpMap", LoadPNG(strImgNorm + ".png", bNorm: true));
			value.SetTextureScale("_BumpMap", new Vector2(num, num2));
			value.SetTextureOffset("_BumpMap", new Vector2(num * (float)num6, num2 * (float)num5));
		}
		if (strImgDamaged != "blank")
		{
			if (strImgDamaged == "")
			{
				value.SetFloat("_DmgPresent", 0f);
			}
			else
			{
				value.SetTexture("_DmgTex", LoadPNG(strImgDamaged + ".png", bNorm: false));
				value.SetTextureScale("_DmgTex", new Vector2(num, num2));
				value.SetTextureOffset("_DmgTex", new Vector2(num * (float)num6, num2 * (float)num5));
				value.SetFloat("_DmgPresent", 1f);
				value.SetFloat("_Rows", num4);
				value.SetFloat("_Columns", num3);
			}
		}
		else
		{
			value.SetFloat("_DmgPresent", 0f);
		}
		value.SetVector("_WearCol", Item.GetWearColor(strDmgColor, strImgDamaged));
		dictMaterials[text] = value;
		return value;
	}

	public static IEnumerable GetAudio(string strPath)
	{
		strPath = "file:///" + strAssetPath + "/audio/sfx/AlarmMaster01.ogg";
		WWW www = new WWW(strPath);
		yield return www;
		if (www.error != null)
		{
			UnityEngine.Debug.Log(www.error);
		}
		AudioClip audioClip = www.GetAudioClip(threeD: false, stream: true);
		if (audioClip != null && audioClip.isReadyToPlay)
		{
			AudioSource audioSource = new AudioSource();
			audioSource.clip = audioClip;
			audioSource.transform.SetParent(CrewSim.objInstance.transform);
			audioSource.Play();
		}
	}

	public static string GetNextID()
	{
		return Guid.NewGuid().ToString();
	}

	public static JsonComputerEntry GetEntry(string name)
	{
		return dictComputerEntries[name];
	}

	public static void WordCount()
	{
		File.Delete("words.txt");
		File.AppendAllText("words.txt", AppendDictWords(new string[4] { "make", "model", "designation", "dimensions" }, dictShips));
		File.AppendAllText("words.txt", AppendDictWords(new string[2] { "strNameFriendly", "strDesc" }, dictConds));
		File.AppendAllText("words.txt", AppendDictWords(new string[2] { "strNameFriendly", "strDesc" }, dictCOs));
		File.AppendAllText("words.txt", AppendDictWords(new string[2] { "strTitle", "strDesc" }, dictInteractions));
		File.AppendAllText("words.txt", AppendDictWords(new string[1] { "strColonyName" }, dictHomeworlds));
		File.AppendAllText("words.txt", AppendDictWords(new string[1] { "strNameFriendly" }, dictCareers));
		File.AppendAllText("words.txt", AppendDictWords(new string[1] { "strDesc" }, dictAds));
		File.AppendAllText("words.txt", AppendDictWords(new string[3] { "strName", "strDesc", "strRegion" }, dictHeadlines));
		File.AppendAllText("words.txt", AppendDictWords(new string[1] { "strNameFriendly" }, dictCOOverlays));
		File.AppendAllText("words.txt", AppendDictWords(new string[1] { "strDesc" }, dictLedgerDefs));
		File.AppendAllText("words.txt", AppendDictWords(new string[1] { "strFriendlyName" }, dictJobitems));
		StringBuilder stringBuilder = new StringBuilder();
		foreach (Dictionary<string, string> value2 in dictGUIPropMaps.Values)
		{
			if (value2.ContainsKey("strFriendlyName"))
			{
				stringBuilder.AppendLine(value2["strFriendlyName"]);
			}
			if (value2.ContainsKey("strTitle"))
			{
				stringBuilder.AppendLine(value2["strTitle"]);
			}
			if (value2.ContainsKey("strBrand"))
			{
				stringBuilder.AppendLine(value2["strBrand"]);
			}
			if (value2.ContainsKey("strBrandSub"))
			{
				stringBuilder.AppendLine(value2["strBrandSub"]);
			}
		}
		foreach (string key in dictNamesFirst.Keys)
		{
			stringBuilder.AppendLine(key);
		}
		foreach (string key2 in dictNamesLast.Keys)
		{
			stringBuilder.AppendLine(key2);
		}
		foreach (string key3 in dictNamesFull.Keys)
		{
			stringBuilder.AppendLine(key3);
		}
		foreach (string key4 in dictNamesShip.Keys)
		{
			stringBuilder.AppendLine(key4);
		}
		foreach (string key5 in dictNamesShipAdjectives.Keys)
		{
			stringBuilder.AppendLine(key5);
		}
		foreach (string key6 in dictNamesShipNouns.Keys)
		{
			stringBuilder.AppendLine(key6);
		}
		string[] array = dictManPages["Manual Pages"];
		foreach (string value in array)
		{
			stringBuilder.AppendLine(value);
		}
		foreach (string value3 in dictStrings.Values)
		{
			stringBuilder.AppendLine(value3);
		}
		File.AppendAllText("words.txt", stringBuilder.ToString());
	}

	private static string AppendDictWords<TJson>(string[] aFields, Dictionary<string, TJson> dict)
	{
		StringBuilder stringBuilder = new StringBuilder();
		foreach (TJson value2 in dict.Values)
		{
			foreach (string name in aFields)
			{
				PropertyInfo property = value2.GetType().GetProperty(name);
				if (property == null)
				{
					continue;
				}
				object value = property.GetValue(value2, null);
				if (value != null)
				{
					string text = value.ToString();
					if (text != null && text != "")
					{
						stringBuilder.AppendLine(text);
					}
				}
			}
		}
		return stringBuilder.ToString();
	}

	public static bool IsNameRegistered(KeyValuePair<string, IEnumerable> kvp)
	{
		IDictionary[] array = new IDictionary[13]
		{
			dictCTs, dictLoot, dictInteractions, dictConds, dictCOs, dictPersonSpecs, dictCondRules, dictItemDefs, dictTickers, dictShips,
			dictLifeEvents, dictCOOverlays, dictShipSpecs
		};
		for (int i = 0; i < array.Length; i++)
		{
			Type[] genericArguments = array[i].GetType().GetGenericArguments();
			if (kvp.Value == null || genericArguments[1] == kvp.Value)
			{
				if (array[i].Contains(kvp.Key))
				{
					return true;
				}
				continue;
			}
			foreach (object item in kvp.Value)
			{
				if (genericArguments[1].Equals(item) && array[i].Contains(kvp.Key))
				{
					return true;
				}
			}
		}
		return false;
	}

	public static void ScanDictionaries()
	{
		if (dictCondRulesLookup == null)
		{
			dictCondRulesLookup = new Dictionary<string, string>();
			foreach (CondRule value in dictCondRules.Values)
			{
				if (!string.IsNullOrEmpty(value.strName) && !string.IsNullOrEmpty(value.strCond))
				{
					dictCondRulesLookup[value.strCond] = value.strName;
				}
			}
		}
		dictLoot.Verify();
		dictInteractions.Verify();
		dictConds.Verify();
		dictCTs.Verify();
		dictCOs.Verify();
	}

	public static JsonTip GetTip()
	{
		int count = dictTips.Keys.Count;
		if (count == 0)
		{
			return null;
		}
		JsonTip[] array = new JsonTip[count];
		dictTips.Values.CopyTo(array, 0);
		count = MathUtils.Rand(0, array.Length, MathUtils.RandType.Flat, "LoadTip");
		return array[count];
	}
}
