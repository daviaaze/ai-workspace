using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using Ostranauts.Condowner;
using Ostranauts.Core;
using Ostranauts.Core.Models;
using Ostranauts.Objectives;
using Ostranauts.Systems;
using Ostranauts.Tools.ExtensionMethods;
using UnityEngine;

public class Interaction
{
	public enum Logging
	{
		NONE,
		GROUP,
		ROOM,
		SHIP
	}

	public enum MoveType
	{
		DEFAULT,
		GAMBIT,
		GAMBIT_FAIL,
		GAMBIT_PASS,
		SOCIAL_CORE,
		STAKES,
		COMMAND,
		GIG,
		TOGGLE
	}

	public readonly Guid id;

	private static readonly string[] _aDefault = new string[0];

	public string strName;

	public string strTitle;

	public string strDesc;

	public string strTooltip;

	public string strTargetPoint;

	public float fTargetPointRange;

	public float fForcedChance;

	public string strAnim;

	public string strAnimTrig;

	public string strBubble;

	public string strColor;

	public string strDuty;

	public string strChainStart;

	public string strThemType;

	public string strRaiseUI;

	public string strRaiseUIThem;

	public string strSubUI;

	public string strLedgerDef;

	public string strLootContextUs;

	public string strLootContextThem;

	public string strImage;

	public string strMapIcon;

	public string strIdleAnim;

	public string strCancelInteraction;

	public string strUseCase;

	public JsonAttackMode attackMode;

	public string strAttackerName;

	public string strIAHit;

	public string strIAMiss;

	public string strActionGroup;

	public int nQabOrderPriority;

	public string strChainOwner;

	public double fDuration;

	public double fDurationOrig;

	public double fEpochAdded;

	public float fRotation;

	public string strTeleport;

	private Ostranauts.Core.Models.Tuple<string, string> teleportRegIDTarget;

	public string[] aInverse;

	private string[] aLoSReactions;

	public List<TokenData> aReplacements;

	private string[] aAModesAddedUs;

	private string[] aAModesAddedThem;

	private string[] aGPMChangesUs;

	private string[] aGPMChangesThem;

	private string[] aCustomInfos;

	public Loot LootCTsUs;

	public Loot LootCTsThem;

	public Loot LootCTs3rd;

	public Loot LootCondsUs;

	public Loot LootCondsThem;

	public Loot LootConds3rd;

	public Loot LootVFXUs;

	public Loot LootVFXThem;

	public Loot LootAudioUs;

	public Loot LootAudioThem;

	public CondTrigger CTTestUs;

	public CondTrigger CTTestThem;

	public CondTrigger CTTestRoom;

	public CondTrigger CTTest3rd;

	public JsonPersonSpec PSpecTestThem;

	public JsonPersonSpec PSpecTest3rd;

	public JsonShipSpec ShipTestUs;

	public JsonShipSpec ShipTestThem;

	public JsonShipSpec ShipTest3rd;

	public string strLootItmAddUs;

	public string strLootItmAddThem;

	public string strLootCTsRemoveUs;

	public string strLootItmRemoveThem;

	public string strLootCTsGive;

	public string strLootCTsUse;

	public string strLootCTsTake;

	public string strLootCTsLacks;

	public string strLootItmInputs;

	public string strCTThemMultCondUs;

	public string strCTThemMultCondTools;

	public Loot objLootModeSwitch;

	public Loot objLootModeSwitchThem;

	public Loot LootReveals;

	public List<CondOwner> aLootItemGiveContract;

	public List<CondOwner> aLootItemUseContract;

	public List<CondOwner> aLootItemRemoveContract;

	public List<CondOwner> aLootItemTakeContract;

	public List<CondOwner> aSeekItemsForContract;

	public List<string> aDependents;

	public List<string> aSocialChangelog;

	public JsonInteractionSave jis;

	public List<CondScore> aCondUsPriorities;

	private Dictionary<string, List<string>> mapFails;

	public bool bTargetOwned;

	public bool bEquip;

	public bool bLot;

	public bool bPassThrough;

	public bool bRecheckAllPlots;

	public bool bRecheckThisPlot;

	public string strSetPlot;

	public bool b3rdReset;

	public bool bVFXSpawned;

	public bool bAudioPlayed;

	public string strPlot;

	public string strStartInstall;

	public string strPledgeAdd;

	public string strPledgeAddThem;

	public string strMusic;

	public bool bForceMusic;

	public Logging nLogging;

	public MoveType nMoveType;

	public string strCrime;

	public string strFactionTest = "ALWAYS";

	public string strFactionTestName;

	public string strFactionScoreChangeLoot;

	public float fFactionScoreChangeLoot;

	public float fFactionScoreChangeThem;

	public float fFactionScoreChangeUs;

	public bool bFactionIgnoreThemPop;

	public Loot LootAddFactionsUs;

	public Loot LootAddFactionsThem;

	public Loot LootAddCondRulesUs;

	public Loot LootAddCondRulesThem;

	public string strLootRELChangeThemSeesUs;

	public string strLootRELChangeThemSees3rd;

	public string strLootRELChangeUsSeesThem;

	public string strLootRELChangeUsSees3rd;

	public string strLootRELChange3rdSeesThem;

	public string strLootRELChange3rdSeesUs;

	public string strAchievementUnlock;

	private CondOwner objUsTemp;

	private CondOwner objThemTemp;

	private CondOwner obj3rdTemp;

	private Vector2 ptRef;

	private string strUsID;

	private string strThemID;

	private string str3rdID;

	public bool bPause;

	public bool bSocial;

	public bool bImmediateReply;

	public bool bIgnoreFeelings;

	public bool bIgnoreCancel;

	public bool bRandomInverse;

	public bool bOpener;

	public bool bGamit;

	public bool bCloser;

	public bool bLogged;

	public bool bRaisedUI;

	public bool bUIDoesNotCancel;

	public bool bUsePDA;

	public bool bTryWalk;

	public bool bGetItemBefore;

	public bool bDestroyItem = true;

	public bool bHumanOnly;

	public bool bAIOnly;

	public bool bGiveWholeStack;

	public bool bRemoveWholeStack;

	public bool bModeSwitchCheckFit;

	public bool bNoWait;

	public bool bNoWalk;

	public bool bNoRemember;

	public bool bVerboseTrigger;

	public bool bHardCode;

	public bool bInterrupt;

	public bool bCancel;

	public bool bRetestItems;

	public bool bManual;

	public bool bAirlockBlocked;

	public bool bApplyChain;

	public string strSocialCombatPreview;

	private float fCTThemModifierUs = 1f;

	private float fCTThemModifierTools = 1f;

	private float fCTThemModifierPenalty;

	private bool bCTThemModifierCalculated;

	private static CondTrigger ctNotCarried = null;

	public static readonly string TARGET_SELF = "Self";

	public static readonly string TARGET_OTHER = "Other";

	public static readonly string POINT_REMOTE = "remote";

	private static string STR_COMBAT_MISSED = null;

	private static string STR_TASK_RATE_START = null;

	private static string STR_TASK_RATE_END = null;

	private static string STR_IA_FAIL_DEFAULT = null;

	private static string STR_IA_FAIL_FACTION = null;

	private static string STR_IA_FAIL_LOS_END = null;

	private static string STR_IA_FAIL_LOS_START = null;

	private static string STR_IA_FAIL_MONEY = null;

	private static string STR_IA_FAIL_NO_EQUIP = null;

	private static string STR_IA_FAIL_INV_SPACE = null;

	private static string STR_IA_FAIL_OWNED_US = null;

	private static string STR_IA_FAIL_PATH_END = null;

	private static string STR_IA_FAIL_PATH_START = null;

	private static string STR_IA_FAIL_PLAYER = null;

	private static string STR_IA_FAIL_AI = null;

	private static string STR_IA_FAIL_RANGE_END = null;

	private static string STR_IA_FAIL_RANGE_START = null;

	private static string STR_IA_FAIL_THEM = null;

	private static string STR_IA_FAIL_US = null;

	private static string STR_ERROR_NO_ROOM_INV = null;

	public static string STR_GUI_REFUEL_PORT_SUFFIX = null;

	public static string STR_GUI_FINANCE_LOG_RECEIVED = null;

	public const string FT_ALWAYS = "ALWAYS";

	public const string FT_DIFFERENT = "DIFFERENT";

	public const string FT_SAME = "SAME";

	public const string FT_LIKES = "LIKES";

	public const string FT_DISLIKES = "DISLIKES";

	public const string FT_NOTDISLIKES = "NOTDISLIKES";

	public static readonly Dictionary<string, int> dictAnims = new Dictionary<string, int>
	{
		{ "Idle", 0 },
		{ "Walk", 1 },
		{ "Use", 2 },
		{ "Dead", 3 },
		{ "Sitting", 4 },
		{ "Defecating", 5 },
		{ "Tooling", 6 },
		{ "Sleeping", 7 },
		{ "Talk", 8 },
		{ "Angry", 9 },
		{ "Yes", 10 },
		{ "No", 11 },
		{ "Tablet", 12 },
		{ "Burpee", 13 },
		{ "Clapping", 14 },
		{ "Bash", 15 },
		{ "Spaced1", 16 },
		{ "HypoxicSpaced", 17 },
		{ "Bartending", 18 },
		{ "Pull", 19 },
		{ "Pull_Single", 20 },
		{ "TakeHit", 21 },
		{ "ShootPistol", 22 },
		{ "Surrender", 23 },
		{ "Punch", 24 },
		{ "Block", 25 },
		{ "Dodge", 26 },
		{ "Fallen", 27 },
		{ "Squat", 28 }
	};

	public string strSetPlotObjective { get; set; }

	public string[] aTickersUs { get; set; }

	public string[] aTickersThem { get; set; }

	public string[] aSocialPrereqs { get; set; }

	public string[] aSocialPrereqsFound { get; set; }

	public string[] aSocialNew { get; set; }

	public CondOwner objUs
	{
		get
		{
			if ((objUsTemp == null || objUsTemp.tf == null || objUsTemp.ship == null) && strUsID != null)
			{
				DataHandler.mapCOs.TryGetValue(strUsID, out objUsTemp);
			}
			return objUsTemp;
		}
		set
		{
			if (!(value == null))
			{
				strUsID = value.strID;
				objUsTemp = value;
			}
		}
	}

	public CondOwner objThem
	{
		get
		{
			if ((objThemTemp == null || objThemTemp.tf == null || objThemTemp.ship == null) && strThemID != null)
			{
				DataHandler.mapCOs.TryGetValue(strThemID, out objThemTemp);
			}
			return objThemTemp;
		}
		set
		{
			if (!(value == null))
			{
				strThemID = value.strID;
				objThemTemp = value;
			}
		}
	}

	public CondOwner obj3rd
	{
		get
		{
			if ((obj3rdTemp == null || obj3rdTemp.tf == null || obj3rdTemp.ship == null) && str3rdID != null)
			{
				DataHandler.mapCOs.TryGetValue(str3rdID, out obj3rdTemp);
			}
			return obj3rdTemp;
		}
		set
		{
			if (!(value == null))
			{
				str3rdID = value.strID;
				obj3rdTemp = value;
			}
		}
	}

	public Dictionary<string, List<TokenData>> stringsToTokens { get; set; }

	public Interaction()
	{
	}

	public Interaction(JsonInteraction jsonIn, JsonInteractionSave jis = null)
	{
		id = Guid.NewGuid();
		SetData(jsonIn, jis);
	}

	public void ResetObject(JsonInteraction jsonIn, JsonInteractionSave jis = null)
	{
		objUsTemp = null;
		objThemTemp = null;
		obj3rdTemp = null;
		strUsID = null;
		strThemID = null;
		str3rdID = null;
		SetData(jsonIn, jis);
	}

	private void SetData(JsonInteraction jsonIn, JsonInteractionSave jis = null)
	{
		if (jsonIn == null)
		{
			return;
		}
		if (STR_COMBAT_MISSED == null)
		{
			STR_COMBAT_MISSED = DataHandler.GetString("COMBAT_MISSED");
			STR_TASK_RATE_START = DataHandler.GetString("TASK_RATE_START");
			STR_TASK_RATE_END = DataHandler.GetString("TASK_RATE_END");
			STR_IA_FAIL_DEFAULT = DataHandler.GetString("IA_FAIL_DEFAULT");
			STR_IA_FAIL_FACTION = DataHandler.GetString("IA_FAIL_FACTION");
			STR_IA_FAIL_LOS_END = DataHandler.GetString("IA_FAIL_LOS_END");
			STR_IA_FAIL_LOS_START = DataHandler.GetString("IA_FAIL_LOS_START");
			STR_IA_FAIL_MONEY = DataHandler.GetString("IA_FAIL_MONEY");
			STR_IA_FAIL_NO_EQUIP = DataHandler.GetString("IA_FAIL_NO_EQUIP");
			STR_IA_FAIL_INV_SPACE = DataHandler.GetString("IA_FAIL_INV_SPACE");
			STR_IA_FAIL_OWNED_US = DataHandler.GetString("IA_FAIL_OWNED_US");
			STR_IA_FAIL_PATH_END = DataHandler.GetString("IA_FAIL_PATH_END");
			STR_IA_FAIL_PATH_START = DataHandler.GetString("IA_FAIL_PATH_START");
			STR_IA_FAIL_PLAYER = DataHandler.GetString("IA_FAIL_PLAYER");
			STR_IA_FAIL_AI = DataHandler.GetString("IA_FAIL_AI");
			STR_IA_FAIL_RANGE_END = DataHandler.GetString("IA_FAIL_RANGE_END");
			STR_IA_FAIL_RANGE_START = DataHandler.GetString("IA_FAIL_RANGE_START");
			STR_IA_FAIL_THEM = DataHandler.GetString("IA_FAIL_THEM");
			STR_IA_FAIL_US = DataHandler.GetString("IA_FAIL_US");
			STR_ERROR_NO_ROOM_INV = DataHandler.GetString("ERROR_NO_ROOM_INV");
			STR_GUI_REFUEL_PORT_SUFFIX = DataHandler.GetString("GUI_REFUEL_PORT_SUFFIX");
			STR_GUI_FINANCE_LOG_RECEIVED = DataHandler.GetString("GUI_FINANCE_LOG_RECEIVED");
		}
		this.jis = jis;
		strName = jsonIn.strName;
		strTitle = jsonIn.strTitle;
		strDesc = jsonIn.strDesc;
		strTooltip = jsonIn.strTooltip;
		strTargetPoint = jsonIn.strTargetPoint;
		fTargetPointRange = jsonIn.fTargetPointRange;
		fForcedChance = jsonIn.fForcedChance;
		strAnim = jsonIn.strAnim;
		strAnimTrig = jsonIn.strAnimTrig;
		strBubble = jsonIn.strBubble;
		strColor = jsonIn.strColor;
		if (strColor == null || strColor == "")
		{
			strColor = "Neutral";
		}
		strDuty = jsonIn.strDuty;
		strThemType = jsonIn.strThemType;
		strRaiseUI = jsonIn.strRaiseUI;
		strRaiseUIThem = jsonIn.strRaiseUIThem;
		bUIDoesNotCancel = jsonIn.bUIDoesNotCancel;
		strSubUI = jsonIn.strSubUI;
		strLedgerDef = jsonIn.strLedgerDef;
		strLootContextUs = jsonIn.strContextLootUs;
		strLootContextThem = jsonIn.strContextLootThem;
		strCTThemMultCondUs = jsonIn.strCTThemMultCondUs;
		strCTThemMultCondTools = jsonIn.strCTThemMultCondTools;
		strImage = jsonIn.strImage;
		strMapIcon = jsonIn.strMapIcon;
		NewChainGuid();
		bPause = jsonIn.bPause;
		bSocial = jsonIn.bSocial;
		bImmediateReply = jsonIn.bImmediateReply;
		bIgnoreFeelings = jsonIn.bIgnoreFeelings;
		bIgnoreCancel = jsonIn.bIgnoreCancel;
		bRandomInverse = jsonIn.bRandomInverse;
		bOpener = jsonIn.bOpener;
		bGamit = jsonIn.bGambit;
		bCloser = jsonIn.bCloser;
		bHardCode = jsonIn.bHardCode;
		bApplyChain = jsonIn.bApplyChain;
		bInterrupt = jsonIn.bInterrupt;
		bUsePDA = jsonIn.bUsePDA;
		nLogging = (Logging)jsonIn.nLogging;
		nMoveType = (MoveType)jsonIn.nMoveType;
		strCrime = jsonIn.strCrime;
		strFactionTest = jsonIn.strFactionTest;
		strFactionTestName = jsonIn.strFactionTestName;
		strFactionScoreChangeLoot = jsonIn.strFactionScoreChangeLoot;
		fFactionScoreChangeLoot = jsonIn.fFactionScoreChangeLoot;
		fFactionScoreChangeThem = jsonIn.fFactionScoreChangeThem;
		fFactionScoreChangeUs = jsonIn.fFactionScoreChangeUs;
		bFactionIgnoreThemPop = jsonIn.bFactionIgnoreThemPop;
		bTargetOwned = jsonIn.bTargetOwned;
		bEquip = jsonIn.bEquip;
		bLot = jsonIn.bLot;
		bPassThrough = jsonIn.bPassThrough;
		bRecheckAllPlots = jsonIn.bRecheckAllPlots;
		bRecheckThisPlot = jsonIn.bRecheckThisPlot;
		strSetPlotObjective = jsonIn.strSetPlotObjective;
		strSetPlot = jsonIn.strSetPlot;
		b3rdReset = jsonIn.b3rdReset;
		strStartInstall = jsonIn.strStartInstall;
		strPledgeAdd = jsonIn.strPledgeAdd;
		strPledgeAddThem = jsonIn.strPledgeAddThem;
		strMusic = jsonIn.strMusic;
		bForceMusic = jsonIn.bForceMusic;
		bLogged = false;
		bRaisedUI = false;
		bTryWalk = false;
		bCancel = false;
		bRetestItems = false;
		bManual = false;
		bModeSwitchCheckFit = jsonIn.bModeSwitchCheckFit;
		bHumanOnly = jsonIn.bHumanOnly;
		bAIOnly = jsonIn.bAIOnly;
		bNoWait = jsonIn.bNoWait;
		bNoWalk = jsonIn.bNoWalk;
		bNoRemember = jsonIn.bNoRemember;
		fDuration = jsonIn.fDuration;
		fDurationOrig = fDuration;
		fRotation = jsonIn.fRotation;
		strPlot = null;
		if (!string.IsNullOrEmpty(strSetPlot))
		{
			strPlot = strSetPlot;
		}
		strTeleport = jsonIn.strTeleport;
		if (!string.IsNullOrEmpty(jsonIn.strTeleportRegID))
		{
			teleportRegIDTarget = new Ostranauts.Core.Models.Tuple<string, string>(jsonIn.strTeleportRegID, "us");
		}
		if (teleportRegIDTarget != null && !string.IsNullOrEmpty(jsonIn.strTeleportTarget))
		{
			teleportRegIDTarget.Item2 = jsonIn.strTeleportTarget;
		}
		strIdleAnim = jsonIn.strIdleAnim;
		strCancelInteraction = jsonIn.strCancelInteraction;
		strUseCase = jsonIn.strUseCase;
		if (jsonIn.strAttackMode != null)
		{
			attackMode = DataHandler.GetAttackMode(jsonIn.strAttackMode);
			if (attackMode != null)
			{
				fTargetPointRange = attackMode.fRange;
				strIAHit = jsonIn.strIAHit;
				strIAMiss = jsonIn.strIAMiss;
				strAttackerName = jsonIn.strAttackerName;
			}
		}
		strActionGroup = jsonIn.strActionGroup;
		nQabOrderPriority = jsonIn.nQabOrderPriority;
		aLoSReactions = jsonIn.aLoSReactions ?? _aDefault;
		aAModesAddedUs = jsonIn.aAModesAddedUs ?? _aDefault;
		aAModesAddedThem = jsonIn.aAModesAddedThem ?? _aDefault;
		aGPMChangesUs = jsonIn.aGPMChangesUs ?? _aDefault;
		aGPMChangesThem = jsonIn.aGPMChangesThem ?? _aDefault;
		aCustomInfos = jsonIn.aCustomInfos ?? _aDefault;
		aInverse = jsonIn.aInverse ?? _aDefault;
		if (LootCTsUs == null)
		{
			LootCTsUs = DataHandler.GetLoot(jsonIn.LootCTsUs);
		}
		if (LootCTsThem == null)
		{
			LootCTsThem = DataHandler.GetLoot(jsonIn.LootCTsThem);
		}
		if (LootCTs3rd == null)
		{
			LootCTs3rd = DataHandler.GetLoot(jsonIn.LootCTs3rd);
		}
		if (LootCondsUs == null)
		{
			LootCondsUs = DataHandler.GetLoot(jsonIn.LootCondsUs);
		}
		if (LootCondsThem == null)
		{
			LootCondsThem = DataHandler.GetLoot(jsonIn.LootCondsThem);
		}
		if (LootConds3rd == null)
		{
			LootConds3rd = DataHandler.GetLoot(jsonIn.LootConds3rd);
		}
		if (LootVFXUs == null)
		{
			LootVFXUs = DataHandler.GetLoot(jsonIn.LootVFXUs);
		}
		if (LootVFXThem == null)
		{
			LootVFXThem = DataHandler.GetLoot(jsonIn.LootVFXThem);
		}
		if (LootAudioUs == null)
		{
			LootAudioUs = DataHandler.GetLoot(jsonIn.LootAudioUs);
		}
		if (LootAudioThem == null)
		{
			LootAudioThem = DataHandler.GetLoot(jsonIn.LootAudioThem);
		}
		if (LootAddFactionsUs == null)
		{
			LootAddFactionsUs = DataHandler.GetLoot(jsonIn.LootAddFactionsUs);
		}
		if (LootAddFactionsThem == null)
		{
			LootAddFactionsThem = DataHandler.GetLoot(jsonIn.LootAddFactionsThem);
		}
		if (LootAddCondRulesUs == null)
		{
			LootAddCondRulesUs = DataHandler.GetLoot(jsonIn.LootAddCondRulesUs);
		}
		if (LootAddCondRulesThem == null)
		{
			LootAddCondRulesThem = DataHandler.GetLoot(jsonIn.LootAddCondRulesThem);
		}
		if (CTTestUs == null || CTTestUs.ValuesWereChanged)
		{
			CTTestUs = DataHandler.GetCondTrigger(jsonIn.CTTestUs);
			CTTestUs.ValuesWereChanged = false;
		}
		if (CTTestThem == null || CTTestThem.ValuesWereChanged)
		{
			CTTestThem = DataHandler.GetCondTrigger(jsonIn.CTTestThem);
			CTTestThem.ValuesWereChanged = false;
		}
		if (CTTestRoom == null || CTTestRoom.ValuesWereChanged)
		{
			CTTestRoom = DataHandler.GetCondTrigger(jsonIn.CTTestRoom);
			CTTestRoom.ValuesWereChanged = false;
		}
		if (jsonIn.CTTest3rd != null && (CTTest3rd == null || CTTest3rd.ValuesWereChanged))
		{
			CTTest3rd = DataHandler.GetCondTrigger(jsonIn.CTTest3rd);
			CTTest3rd.ValuesWereChanged = false;
		}
		if (jsonIn.PSpecTestThem != null && jsonIn.PSpecTestThem != "")
		{
			PSpecTestThem = DataHandler.GetPersonSpec(jsonIn.PSpecTestThem);
		}
		if (jsonIn.PSpecTest3rd != null && jsonIn.PSpecTest3rd != "")
		{
			PSpecTest3rd = DataHandler.GetPersonSpec(jsonIn.PSpecTest3rd);
		}
		if (jsonIn.ShipTestUs != null && jsonIn.ShipTestUs != "")
		{
			ShipTestUs = DataHandler.GetShipSpec(jsonIn.ShipTestUs);
		}
		if (jsonIn.ShipTestThem != null && jsonIn.ShipTestThem != "")
		{
			ShipTestThem = DataHandler.GetShipSpec(jsonIn.ShipTestThem);
		}
		if (jsonIn.ShipTest3rd != null && jsonIn.ShipTest3rd != "")
		{
			ShipTest3rd = DataHandler.GetShipSpec(jsonIn.ShipTest3rd);
		}
		if (jsonIn.aLootItms != null)
		{
			string[] aLootItms = jsonIn.aLootItms;
			foreach (string text in aLootItms)
			{
				if (text == null)
				{
					continue;
				}
				string[] array = text.Split(',');
				if (array.Length < 2)
				{
					continue;
				}
				string text2 = array[0].ToLower();
				switch (text2)
				{
				case "addus":
					strLootItmAddUs = array[1];
					continue;
				case "addthem":
					strLootItmAddThem = array[1];
					continue;
				case "removethem":
					strLootItmRemoveThem = array[1];
					continue;
				case "take":
					strLootCTsTake = array[1];
					continue;
				}
				if (array.Length < 3)
				{
					continue;
				}
				switch (text2)
				{
				case "use":
					strLootCTsUse = array[1];
					bGetItemBefore = Convert.ToBoolean(array[2]);
					continue;
				case "lacks":
					strLootCTsLacks = array[1];
					bGetItemBefore = Convert.ToBoolean(array[2]);
					continue;
				case "input":
					strLootItmInputs = array[1];
					bGetItemBefore = Convert.ToBoolean(array[2]);
					continue;
				}
				if (array.Length >= 4)
				{
					if (text2 == "give")
					{
						strLootCTsGive = array[1];
						bGetItemBefore = Convert.ToBoolean(array[2]);
						bGiveWholeStack = Convert.ToBoolean(array[3]);
					}
					else if (text2 == "removeus")
					{
						strLootCTsRemoveUs = array[1];
						bGetItemBefore = Convert.ToBoolean(array[2]);
						bDestroyItem = Convert.ToBoolean(array[3]);
						bRemoveWholeStack = Convert.ToBoolean(array[4]);
					}
				}
			}
		}
		if (objLootModeSwitch == null && !string.IsNullOrEmpty(jsonIn.objLootModeSwitch))
		{
			Loot loot = DataHandler.GetLoot(jsonIn.objLootModeSwitch);
			if (loot.strName != "Blank")
			{
				objLootModeSwitch = loot;
			}
		}
		if (objLootModeSwitchThem == null && !string.IsNullOrEmpty(jsonIn.objLootModeSwitchThem))
		{
			Loot loot2 = DataHandler.GetLoot(jsonIn.objLootModeSwitchThem);
			if (loot2.strName != "Blank")
			{
				objLootModeSwitchThem = loot2;
			}
		}
		if (LootReveals == null && !string.IsNullOrEmpty(jsonIn.LootReveals))
		{
			Loot loot3 = DataHandler.GetLoot(jsonIn.LootReveals);
			if (loot3.strName != "Blank")
			{
				LootReveals = loot3;
			}
		}
		if (jsonIn.aSocialPrereqs == null)
		{
			aSocialPrereqs = _aDefault;
		}
		else
		{
			aSocialPrereqs = jsonIn.aSocialPrereqs;
		}
		if (aSocialPrereqs.Length != 0)
		{
			aSocialPrereqsFound = new string[aSocialPrereqs.Length];
		}
		else
		{
			aSocialPrereqsFound = _aDefault;
		}
		if (jsonIn.aSocialNew == null)
		{
			aSocialNew = _aDefault;
		}
		else
		{
			aSocialNew = jsonIn.aSocialNew;
		}
		strLootRELChangeThemSeesUs = jsonIn.strLootRELChangeThemSeesUs;
		strLootRELChangeThemSees3rd = jsonIn.strLootRELChangeThemSees3rd;
		strLootRELChangeUsSeesThem = jsonIn.strLootRELChangeUsSeesThem;
		strLootRELChangeUsSees3rd = jsonIn.strLootRELChangeUsSees3rd;
		strLootRELChange3rdSeesUs = jsonIn.strLootRELChange3rdSeesUs;
		strLootRELChange3rdSeesThem = jsonIn.strLootRELChange3rdSeesThem;
		strAchievementUnlock = jsonIn.strAchievementUnlock;
		aTickersUs = jsonIn.aTickersUs;
		aTickersThem = jsonIn.aTickersThem;
		strSocialCombatPreview = jsonIn.strSocialCombatPreview;
		if (ctNotCarried == null)
		{
			ctNotCarried = DataHandler.GetCondTrigger("TIsNotCarried");
		}
		if (jis != null)
		{
			strUsID = jis.objUs;
			strThemID = jis.objThem;
			str3rdID = jis.obj3rd;
		}
	}

	public void PostGameLoad()
	{
		if (jis == null)
		{
			return;
		}
		strChainOwner = jis.strChainOwner;
		strChainStart = jis.strChainStart;
		strPlot = jis.strPlot;
		bLogged = jis.bLogged;
		bRaisedUI = jis.bRaisedUI;
		bManual = jis.bManual;
		bTryWalk = jis.bTryWalk;
		bCancel = jis.bCancel;
		bRetestItems = jis.bRetestItems;
		objUs = DataHandler.mapCOs[jis.objUs];
		if (!(objThem == null) && DataHandler.mapCOs.ContainsKey(jis.objThem))
		{
			objThem = DataHandler.mapCOs[jis.objThem];
		}
		CondOwner value;
		if (jis.aLootItemGiveContract != null)
		{
			string[] array = jis.aLootItemGiveContract;
			foreach (string text in array)
			{
				if (DataHandler.mapCOs.TryGetValue(text, out value) && value != null)
				{
					if (aLootItemGiveContract == null)
					{
						aLootItemGiveContract = new List<CondOwner>();
					}
					aLootItemGiveContract.Add(value);
				}
				else
				{
					Debug.Log(objUs.strID + " has invalid aLootItemGiveContract CO on interaction " + strName + ": " + text);
				}
			}
		}
		if (jis.aLootItemUseContract != null)
		{
			string[] array = jis.aLootItemUseContract;
			foreach (string text2 in array)
			{
				if (DataHandler.mapCOs.TryGetValue(text2, out value) && value != null)
				{
					if (aLootItemUseContract == null)
					{
						aLootItemUseContract = new List<CondOwner>();
					}
					aLootItemUseContract.Add(value);
				}
				else
				{
					Debug.LogWarning(objUs.strID + " has invalid aLootItemUseContract CO on interaction " + strName + ": " + text2);
				}
			}
		}
		if (jis.aLootItemRemoveContract != null)
		{
			string[] array = jis.aLootItemRemoveContract;
			foreach (string text3 in array)
			{
				if (DataHandler.mapCOs.TryGetValue(text3, out value) && value != null)
				{
					if (aLootItemRemoveContract == null)
					{
						aLootItemRemoveContract = new List<CondOwner>();
					}
					aLootItemRemoveContract.Add(value);
				}
				else
				{
					Debug.LogWarning("Interaction " + strName + ", could not find CO with id: " + text3);
				}
			}
		}
		if (jis.aLootItemTakeContract != null)
		{
			string[] array = jis.aLootItemTakeContract;
			foreach (string text4 in array)
			{
				if (DataHandler.mapCOs.TryGetValue(text4, out value) && value != null)
				{
					if (aLootItemTakeContract == null)
					{
						aLootItemTakeContract = new List<CondOwner>();
					}
					aLootItemTakeContract.Add(value);
				}
				else
				{
					Debug.LogWarning("Interaction " + strName + ", could not find CO with id: " + text4);
				}
			}
		}
		if (jis.aSeekItemsForContract != null)
		{
			string[] array = jis.aSeekItemsForContract;
			foreach (string text5 in array)
			{
				if (DataHandler.mapCOs.TryGetValue(text5, out value) && value != null)
				{
					if (aSeekItemsForContract == null)
					{
						aSeekItemsForContract = new List<CondOwner>();
					}
					aSeekItemsForContract.Add(value);
				}
				else
				{
					Debug.LogWarning("Interaction " + strName + ", could not find CO with id: " + text5);
				}
			}
		}
		if (jis.aDependents != null)
		{
			string[] array = jis.aDependents;
			foreach (string item in array)
			{
				if (aDependents == null)
				{
					aDependents = new List<string>();
				}
				aDependents.Add(item);
			}
		}
		if (jis.aSocialPrereqsFound != null)
		{
			aSocialPrereqsFound = jis.aSocialPrereqsFound.Clone() as string[];
		}
		if (Array.IndexOf(JsonCompanyRules.aDutiesNew, strDuty) >= 0)
		{
			CrewSim.objInstance.workManager.AddClaimedTask(this);
		}
		jis = null;
	}

	private void NewChainGuid()
	{
		strChainStart = strName;
		strChainOwner = null;
	}

	private string[] GetCTStrList(string strIn)
	{
		List<CondTrigger> cTLoot = DataHandler.GetLoot(strIn).GetCTLoot(null);
		string[] array = new string[cTLoot.Count];
		for (int i = 0; i < cTLoot.Count; i++)
		{
			array[i] = cTLoot[i].strName;
		}
		return array;
	}

	public bool IsPlayerNoticed()
	{
		if (nLogging >= Logging.GROUP)
		{
			if (objUs == CrewSim.GetSelectedCrew() || objThem == CrewSim.GetSelectedCrew())
			{
				return true;
			}
			if (nLogging == Logging.ROOM)
			{
				Room currentRoom = CrewSim.GetSelectedCrew().currentRoom;
				if (currentRoom != null)
				{
					return objUs.ship.GetPeopleInRoom(currentRoom).Contains(CrewSim.GetSelectedCrew());
				}
			}
			else if (nLogging == Logging.SHIP && objUs.ship == CrewSim.GetSelectedCrew().ship)
			{
				return true;
			}
		}
		return false;
	}

	private bool IsSocialCombatReply()
	{
		if (objThem == objUs)
		{
			if (GUISocialCombat2.coUs == objUs && strSubUI != null)
			{
				return true;
			}
			return false;
		}
		if (GUISocialCombat2.coUs == objUs && GUISocialCombat2.coThem == objThem)
		{
			return true;
		}
		if (GUISocialCombat2.coThem == objUs && GUISocialCombat2.coUs == objThem)
		{
			return true;
		}
		return false;
	}

	private CondOwner ParseInteractionString(string strPart, CondOwner[] cos = null)
	{
		if (cos == null)
		{
			cos = new CondOwner[3] { objUs, objThem, obj3rd };
		}
		return strPart switch
		{
			"[us]" => cos[0], 
			"[them]" => cos[1], 
			"[3rd]" => cos[2], 
			_ => null, 
		};
	}

	public Interaction GetReply()
	{
		Interaction interaction = null;
		List<Interaction> list = new List<Interaction>();
		float num = 0f;
		float num2 = 0f;
		List<Interaction> list2 = new List<Interaction>();
		List<string> list3 = new List<string>();
		if (aInverse != null)
		{
			list3.AddRange(aInverse);
		}
		bool bNoSwap = false;
		bool flag = IsSocialCombatReply();
		bool flag2 = false;
		if (bSocial && (CrewSim.GetSelectedCrew() == objUs || CrewSim.GetSelectedCrew() == objThem))
		{
			flag2 = true;
		}
		if (list3.Count == 0)
		{
			if (!flag || !(objThem == GUISocialCombat2.coUs) || !(strName != "Wait") || bCloser)
			{
				return null;
			}
			list3.AddRange(objUs.aInteractions);
			bNoSwap = true;
		}
		StringBuilder stringBuilder = new StringBuilder();
		bool flag3 = false;
		bool flag4 = false;
		foreach (string item in list3)
		{
			string[] array = item.Split(',');
			Interaction interaction2 = DataHandler.GetInteraction(array[0]);
			if (interaction2 == null)
			{
				continue;
			}
			AssignReplyRoles(interaction2, array, bNoSwap);
			if (flag2 && !flag3)
			{
				stringBuilder.Append(interaction2.objUs.strName);
				stringBuilder.Append(" replying to ");
				stringBuilder.Append(strName);
				stringBuilder.Append(" (");
				stringBuilder.Append(strDesc);
				stringBuilder.AppendLine("):");
				flag3 = true;
			}
			if (stringBuilder.Length > 0)
			{
				interaction2.bVerboseTrigger = true;
			}
			bool num3 = interaction2.Triggered(interaction2.objUs, interaction2.objThem, bStats: true);
			bool flag5 = MathUtils.Rand(0f, 1f, MathUtils.RandType.Flat) <= interaction2.fForcedChance;
			if (!num3)
			{
				if (stringBuilder.Length > 0)
				{
					stringBuilder.Append("FAILED: ");
					stringBuilder.Append(interaction2.strTitle);
					stringBuilder.Append("(");
					stringBuilder.Append(interaction2.strName);
					stringBuilder.Append(")");
					stringBuilder.Append(": Reasons. ");
					stringBuilder.AppendLine(interaction2.FailReasons(bUsThem: true, bItems: true, bDebug: true));
				}
				continue;
			}
			if (stringBuilder.Length > 0)
			{
				if (flag5)
				{
					stringBuilder.Append("FORCED: ");
				}
				else
				{
					stringBuilder.Append("PASSED: ");
				}
				stringBuilder.Append(interaction2.strTitle);
				stringBuilder.Append("(");
				stringBuilder.Append(interaction2.strName);
				stringBuilder.Append(")");
				stringBuilder.AppendLine(": Passed.");
			}
			if (flag && interaction2.objUs == GUISocialCombat2.coUs)
			{
				list2.Add(interaction2);
				continue;
			}
			num = interaction2.objUs.GetNetInteractionResult(interaction2);
			if (interaction2.objUs.RecentlyTried(interaction2, allowIaOnly: true) >= 0.0)
			{
				num = ((!(num < 0f)) ? (num * 100f) : (num * -0.01f));
			}
			if (flag5)
			{
				if (!flag4 || num < num2)
				{
					list.Clear();
					num2 = num;
				}
				list.Add(interaction2);
				if (stringBuilder.Length > 0)
				{
					stringBuilder.AppendLine("FORCED");
				}
				break;
			}
			if (bIgnoreFeelings)
			{
				if (list.Count == 0)
				{
					list.Add(interaction2);
					if (stringBuilder.Length > 0)
					{
						stringBuilder.AppendLine("BEST ONLY");
					}
				}
			}
			else if (list.Count == 0 || num == num2)
			{
				num2 = num;
				list.Add(interaction2);
				if (stringBuilder.Length > 0)
				{
					if (list.Count == 0)
					{
						stringBuilder.Append("BEST 1ST ");
					}
					else
					{
						stringBuilder.Append("BEST ADD ");
					}
					stringBuilder.AppendLine(num2.ToString());
				}
			}
			else if (num < num2)
			{
				foreach (Interaction item2 in list)
				{
					if (DataHandler.dictSocialStats.ContainsKey(item2.strName))
					{
						DataHandler.dictSocialStats[item2.strName].nLowScored++;
					}
				}
				list.Clear();
				num2 = num;
				list.Add(interaction2);
				if (stringBuilder.Length > 0)
				{
					stringBuilder.Append("BEST REPLACE ");
					stringBuilder.AppendLine(num2.ToString());
				}
			}
			else if (DataHandler.dictSocialStats.ContainsKey(interaction2.strName))
			{
				DataHandler.dictSocialStats[interaction2.strName].nLowScored++;
			}
		}
		if (flag && (GUISocialCombat2.coUs == objUs || GUISocialCombat2.coThem == objUs))
		{
			GUISocialCombat2.strSubUI = strSubUI;
		}
		if (flag && list2.Count > 0)
		{
			GUISocialCombat2.objInstance.SetData(list2[0].objUs, list2[0].objThem, bPause: true, list2);
		}
		if (stringBuilder.Length > 0)
		{
			Debug.Log(stringBuilder.ToString());
		}
		if (list.Count > 0)
		{
			interaction = ((!bRandomInverse) ? list[0] : list[MathUtils.Rand(0, list.Count, MathUtils.RandType.Flat)]);
		}
		if (interaction != null)
		{
			interaction.strChainOwner = strChainOwner;
			interaction.strChainStart = strChainStart;
			interaction.strPlot = strPlot;
		}
		return interaction;
	}

	public void AssignReplyRoles(Interaction iaReply, string[] aParts, bool bNoSwap)
	{
		if (iaReply == null || aParts == null)
		{
			return;
		}
		CondOwner condOwner = objThem;
		CondOwner condOwner2 = objUs;
		CondOwner condOwner3 = (iaReply.b3rdReset ? null : obj3rd);
		CondOwner[] array = new CondOwner[3] { objUs, objThem, obj3rd };
		CondOwner[] array2 = new CondOwner[3] { condOwner, condOwner2, condOwner3 };
		for (int i = 1; i < aParts.Length; i++)
		{
			if (i < array.Length)
			{
				CondOwner condOwner4 = ParseInteractionString(aParts[i], array);
				array2[i - 1] = ((condOwner4 != null) ? condOwner4 : array[i - 1]);
			}
		}
		condOwner = array2[0];
		condOwner2 = array2[1];
		condOwner3 = array2[2];
		if (bNoSwap)
		{
			CondOwner condOwner5 = condOwner;
			condOwner = condOwner2;
			condOwner2 = condOwner5;
		}
		iaReply.objUs = condOwner;
		iaReply.objThem = condOwner2;
		iaReply.obj3rd = condOwner3;
	}

	public void LogSocial(string strName, string strRel, string strEvent)
	{
		if (strName != null && strRel != null)
		{
			if (aSocialChangelog == null)
			{
				aSocialChangelog = new List<string>();
			}
			aSocialChangelog.Add(strName);
			aSocialChangelog.Add(strRel);
			aSocialChangelog.Add(strEvent);
		}
	}

	public void AddDependent(Interaction act)
	{
		if (act != null)
		{
			if (aDependents == null)
			{
				aDependents = new List<string>();
			}
			string text = "";
			if (act.objThem != null)
			{
				text = act.objThem.strID;
			}
			aDependents.Add(act.strName + text);
		}
	}

	public void AddFailReason(string strKey, string strReason)
	{
		if (mapFails == null)
		{
			mapFails = new Dictionary<string, List<string>>();
		}
		if (!string.IsNullOrEmpty(strKey) && !string.IsNullOrEmpty(strReason))
		{
			if (mapFails.ContainsKey(strKey))
			{
				mapFails[strKey].Add(strReason);
				return;
			}
			mapFails[strKey] = new List<string> { strReason };
		}
	}

	private bool TriggeredInternal(CondOwner objUs, CondOwner objThem, bool bStats = false, bool bIgnoreItems = false, bool bCheckPath = false, bool bFetchItems = true, List<string> aForbid3rds = null)
	{
		string sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_DEFAULT;
		if (mapFails != null)
		{
			mapFails.Clear();
		}
		AddFailReason("main", sTR_IA_FAIL_DEFAULT);
		bAirlockBlocked = false;
		if (strThemType == TARGET_SELF && objUs != objThem)
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_THEM;
				AddFailReason("us", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (strThemType == TARGET_OTHER && objUs == objThem)
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_US;
				AddFailReason("them", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (bTargetOwned && (objThem == null || (objThem.ship != null && !objUs.OwnsShip(objThem.ship.strRegID))))
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_OWNED_US;
				AddFailReason("them", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (!string.IsNullOrEmpty(strFactionTest) && strFactionTest != "ALWAYS" && objThem != null)
		{
			bool flag = false;
			switch (strFactionTest)
			{
			case "DIFFERENT":
				flag = ((!string.IsNullOrEmpty(strFactionTestName)) ? objUs.HasFaction(strFactionTestName) : objUs.SharesFactionsWith(objThem));
				break;
			case "SAME":
				flag = ((!string.IsNullOrEmpty(strFactionTestName)) ? (!objUs.HasFaction(strFactionTestName)) : (!objUs.SharesFactionsWith(objThem)));
				break;
			case "LIKES":
			{
				float num = 0f;
				num = ((!string.IsNullOrEmpty(strFactionTestName)) ? objUs.GetFactionScore(strFactionTestName) : objUs.GetFactionScore(objThem.GetAllFactions()));
				flag = (JsonFaction.GetReputation(num) & JsonFaction.Reputation.Likes) != JsonFaction.Reputation.Likes;
				break;
			}
			case "DISLIKES":
			{
				float num = 0f;
				num = ((!string.IsNullOrEmpty(strFactionTestName)) ? objUs.GetFactionScore(strFactionTestName) : objUs.GetFactionScore(objThem.GetAllFactions()));
				flag = JsonFaction.GetReputation(num) != JsonFaction.Reputation.Dislikes;
				break;
			}
			case "NOTDISLIKES":
			{
				float num = 0f;
				num = ((!string.IsNullOrEmpty(strFactionTestName)) ? objUs.GetFactionScore(strFactionTestName) : objUs.GetFactionScore(objThem.GetAllFactions()));
				flag = JsonFaction.GetReputation(num) == JsonFaction.Reputation.Dislikes;
				break;
			}
			}
			if (flag)
			{
				if (bVerboseTrigger)
				{
					sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_FACTION;
					AddFailReason("us", sTR_IA_FAIL_DEFAULT);
				}
				return false;
			}
		}
		if (bHumanOnly && objUs != CrewSim.GetSelectedCrew())
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_PLAYER;
				AddFailReason("us", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (bAIOnly && objUs == CrewSim.GetSelectedCrew())
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_AI;
				AddFailReason("us", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (ShipTestUs != null && !ShipTestUs.Matches((objUs != null) ? objUs.ship : null, objUs, (objThem != null) ? objThem.ship : null))
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = DataHandler.GetString("IA_FAIL_SHIP_WRONG");
				AddFailReason("us", sTR_IA_FAIL_DEFAULT);
				sTR_IA_FAIL_DEFAULT = DataHandler.GetString("IA_FAIL_SHIP_WRONG");
				AddFailReason("debugus", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (ShipTestThem != null && !ShipTestThem.Matches((objThem != null) ? objThem.ship : null, objThem, (objUs != null) ? objUs.ship : null))
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = DataHandler.GetString("IA_FAIL_SHIP_WRONG");
				AddFailReason("them", sTR_IA_FAIL_DEFAULT);
				sTR_IA_FAIL_DEFAULT = DataHandler.GetString("IA_FAIL_SHIP_WRONG");
				AddFailReason("debugthem", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (CTTestUs != null && !CTTestUs.Triggered(objUs, strName))
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = CTTestUs.strFailReasonLast;
				AddFailReason("us", sTR_IA_FAIL_DEFAULT);
				sTR_IA_FAIL_DEFAULT = CTTestUs.strFailReasonLast;
				AddFailReason("debugus", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (PSpecTestThem != null)
		{
			if (objUs.pspec != null)
			{
				if (!objUs.pspec.IsCOMyMother(PSpecTestThem, objThem))
				{
					if (bVerboseTrigger)
					{
						Debug.Log(!PSpecTestThem.Matches(objThem));
						AddFailReason("main", "Didn't pass ptest us");
					}
					return false;
				}
			}
			else if (!PSpecTestThem.Matches(objThem))
			{
				if (bVerboseTrigger)
				{
					AddFailReason("main", "Didn't pass ptest them");
				}
				return false;
			}
		}
		if (CTTestThem != null && !CTTestThem.Triggered(objThem))
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = CTTestThem.strFailReasonLast;
				AddFailReason("them", sTR_IA_FAIL_DEFAULT);
				sTR_IA_FAIL_DEFAULT = CTTestThem.strFailReasonLast;
				AddFailReason("debugthem", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (obj3rd != null)
		{
			if (PSpecTest3rd != null)
			{
				if (!objUs.pspec.IsCOMyMother(PSpecTest3rd, obj3rd))
				{
					return false;
				}
			}
			else if (CTTest3rd != null && !CTTest3rd.Triggered(obj3rd))
			{
				return false;
			}
		}
		else if (PSpecTest3rd != null)
		{
			PersonSpec person = StarSystem.GetPerson(PSpecTest3rd, objUs.socUs, bForceUnrelated: false, aForbid3rds, ShipTest3rd);
			if (person != null)
			{
				obj3rd = person.GetCO();
			}
			if (obj3rd == null)
			{
				return false;
			}
		}
		else if (CTTest3rd != null)
		{
			List<CondOwner> list = new List<CondOwner>();
			foreach (Ship allLoadedShip in CrewSim.system.GetAllLoadedShips())
			{
				if (ShipTest3rd == null || ShipTest3rd.Matches(allLoadedShip, objUs, (objUs != null) ? objUs.ship : null))
				{
					list.AddRange(allLoadedShip.GetCOs(CTTest3rd, bSubObjects: true, bAllowDocked: false, bAllowLocked: true));
				}
			}
			if (aForbid3rds != null)
			{
				for (int num2 = list.Count - 1; num2 >= 0; num2--)
				{
					if (aForbid3rds.Contains(list[num2].strID))
					{
						list.RemoveAt(num2);
					}
				}
			}
			if (list.Count <= 0)
			{
				if (bVerboseTrigger)
				{
					sTR_IA_FAIL_DEFAULT = CTTest3rd.strFailReasonLast;
					AddFailReason("3rd", sTR_IA_FAIL_DEFAULT);
					sTR_IA_FAIL_DEFAULT = CTTest3rd.strFailReasonLast;
					AddFailReason("debug3rd", sTR_IA_FAIL_DEFAULT);
				}
				return false;
			}
			obj3rd = list[MathUtils.Rand(0, list.Count, MathUtils.RandType.Flat)];
		}
		if (ShipTest3rd != null && obj3rd != null && !ShipTest3rd.Matches(obj3rd.ship, obj3rd, (objUs != null) ? objUs.ship : null))
		{
			if (bVerboseTrigger)
			{
				sTR_IA_FAIL_DEFAULT = DataHandler.GetString("IA_FAIL_SHIP_WRONG");
				AddFailReason("3rd", sTR_IA_FAIL_DEFAULT);
				sTR_IA_FAIL_DEFAULT = DataHandler.GetString("IA_FAIL_SHIP_WRONG");
				AddFailReason("debug3rd", sTR_IA_FAIL_DEFAULT);
			}
			return false;
		}
		if (CTTestRoom != null && !CTTestRoom.IsBlank() && objUs.ship != null)
		{
			Room roomAtWorldCoords = objUs.ship.GetRoomAtWorldCoords1(objUs.tf.position, bAllowDocked: true);
			if (roomAtWorldCoords != null && roomAtWorldCoords.CO != null && !CTTestRoom.Triggered(roomAtWorldCoords.CO, strName))
			{
				if (bVerboseTrigger)
				{
					sTR_IA_FAIL_DEFAULT = CTTestRoom.strFailReasonLast;
					AddFailReason("room", sTR_IA_FAIL_DEFAULT);
					sTR_IA_FAIL_DEFAULT = CTTestRoom.strFailReasonLast;
					AddFailReason("debugroom", sTR_IA_FAIL_DEFAULT);
				}
				return false;
			}
		}
		for (int i = 0; i < aSocialPrereqs.Length; i++)
		{
			if (objUs.socUs == null)
			{
				return false;
			}
			JsonPersonSpec personSpec = DataHandler.GetPersonSpec(aSocialPrereqs[i]);
			string matchingRelation = objUs.socUs.GetMatchingRelation(personSpec);
			if (matchingRelation == null)
			{
				return false;
			}
			aSocialPrereqsFound[i] = matchingRelation;
		}
		if (!(strTargetPoint == POINT_REMOTE))
		{
			if (bNoWalk)
			{
				if (objThem.ship.LoadState < Ship.Loaded.Edit)
				{
					if (bVerboseTrigger)
					{
						sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_LOS_START + objThem.FriendlyName + STR_IA_FAIL_LOS_END;
						AddFailReason("main", sTR_IA_FAIL_DEFAULT);
					}
					return false;
				}
				bool flag2 = true;
				bool flag3 = objUs.GetCORef(objThem) != null;
				Tile tileAtWorldCoords = objUs.ship.GetTileAtWorldCoords1(objUs.tf.position.x, objUs.tf.position.y, bAllowDocked: true);
				Tile tile = tileAtWorldCoords;
				if (strTargetPoint != null && strTargetPoint != POINT_REMOTE && !flag3)
				{
					Vector2 pos = objThem.GetPos(strTargetPoint);
					tile = objUs.ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
					flag2 = (float)TileUtils.TileRange(tileAtWorldCoords, tile) <= fTargetPointRange;
				}
				if (!flag2)
				{
					if (bVerboseTrigger)
					{
						sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_RANGE_START + objThem.FriendlyName + STR_IA_FAIL_RANGE_END;
						AddFailReason("main", sTR_IA_FAIL_DEFAULT);
					}
					return false;
				}
				if (!Visibility.IsCondOwnerLOSVisibleBlocks(objThem, tileAtWorldCoords.tf.position))
				{
					if (bVerboseTrigger)
					{
						sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_LOS_START + objThem.FriendlyName + STR_IA_FAIL_LOS_END;
						AddFailReason("main", sTR_IA_FAIL_DEFAULT);
					}
					return false;
				}
			}
			else if (bCheckPath)
			{
				Pathfinder pathfinder = objUs.Pathfinder;
				if (pathfinder != null)
				{
					Tile tilDestNew = pathfinder.tilCurrent;
					if (strTargetPoint != null && strTargetPoint != POINT_REMOTE && objUs.GetCORef(objThem) == null)
					{
						Vector2 pos2 = objThem.GetPos(strTargetPoint);
						tilDestNew = objUs.ship.GetTileAtWorldCoords1(pos2.x, pos2.y, bAllowDocked: true);
					}
					bool bAllowAirlocks = objUs.HasAirlockPermission(bManual);
					PathResult pathResult = pathfinder.CheckGoal(tilDestNew, fTargetPointRange, objThem, bAllowAirlocks);
					if (!pathResult.HasPath)
					{
						if (bVerboseTrigger)
						{
							sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_PATH_START + objThem.FriendlyName + STR_IA_FAIL_PATH_END;
							AddFailReason("main", sTR_IA_FAIL_DEFAULT);
							sTR_IA_FAIL_DEFAULT = pathResult.FailReason(objUs);
							if (!string.IsNullOrEmpty(sTR_IA_FAIL_DEFAULT))
							{
								AddFailReason("main", sTR_IA_FAIL_DEFAULT);
							}
						}
						if (pathResult.bAirlockBlocked)
						{
							bAirlockBlocked = pathResult.bAirlockBlocked;
						}
						return false;
					}
				}
			}
		}
		if (strLedgerDef != null)
		{
			JsonLedgerDef ledgerDef = DataHandler.GetLedgerDef(strLedgerDef);
			if (ledgerDef != null && ledgerDef.bPaid && string.IsNullOrEmpty(ledgerDef.strPayorOverride) && objUs.GetCondAmount(ledgerDef.strCurrency) < (double)ledgerDef.fAmount)
			{
				if (bVerboseTrigger)
				{
					sTR_IA_FAIL_DEFAULT = STR_IA_FAIL_MONEY;
					AddFailReason("them", sTR_IA_FAIL_DEFAULT);
				}
				return false;
			}
		}
		if (bIgnoreItems)
		{
			return true;
		}
		aLootItemGiveContract = null;
		aLootItemUseContract = null;
		aLootItemRemoveContract = null;
		aLootItemTakeContract = null;
		aSeekItemsForContract = new List<CondOwner>();
		if (strLootItmInputs != null)
		{
			bool flag4 = false;
			List<CondTrigger> cTLoot = DataHandler.GetLoot(strLootItmInputs).GetCTLoot(null);
			List<CondOwner> list2 = new List<CondOwner>();
			List<CondOwner> list3 = new List<CondOwner> { objThem };
			list3.AddRange(objThem.GetLotCOs(bSubItems: true));
			foreach (CondOwner item in list3)
			{
				foreach (CondTrigger item2 in cTLoot)
				{
					if (item2.Triggered(item))
					{
						item2.fCount -= item.StackCount;
					}
					if (item2.fCount <= 0f)
					{
						cTLoot.Remove(item2);
						break;
					}
				}
			}
			if (cTLoot.Count == 0)
			{
				flag4 = true;
			}
			else
			{
				HashSet<string> hashSet = new HashSet<string>();
				foreach (CondTrigger item3 in cTLoot)
				{
					hashSet.Add(item3.strName);
				}
				List<CondTrigger> list4 = new List<CondTrigger>();
				foreach (string item4 in hashSet)
				{
					list4.Add(DataHandler.GetCondTrigger(item4));
				}
				CondOwnerVisitorAddToHashSet condOwnerVisitorAddToHashSet = new CondOwnerVisitorAddToHashSet();
				CondOwnerVisitorLazyOrCondTrigger visitor = new CondOwnerVisitorLazyOrCondTrigger(condOwnerVisitorAddToHashSet, list4);
				new CondOwnerVisitorLazyOrCondTrigger(new CondOwnerVisitorAddToHashSet(), list4);
				objUs.VisitCOs(visitor, bAllowLocked: false);
				list2 = new List<CondOwner>(condOwnerVisitorAddToHashSet.aHashSet);
				objUs.ship.VisitCOs(visitor, bSubObjects: true, bAllowDocked: true, bAllowLocked: false);
				list3 = new List<CondOwner>(condOwnerVisitorAddToHashSet.aHashSet);
				foreach (CondOwner item5 in list2)
				{
					list3.Remove(item5);
				}
				list3.InsertRange(0, list2);
				list2.Clear();
				if (objThem.strPersistentCO != null)
				{
					CondOwner value = null;
					if (DataHandler.mapCOs.TryGetValue(objThem.strPersistentCO, out value) && list3.IndexOf(value) > 0)
					{
						list3.Remove(value);
						list3.Insert(0, value);
					}
				}
				list2 = CheckItemsAvailable(cTLoot, list3, objUs, bSeekFirst: false, objThem.strPersistentCO, bUseTest: false);
				if (list2 != null)
				{
					if (!bFetchItems)
					{
						flag4 = true;
					}
					else
					{
						Dictionary<string, int> dictionary = new Dictionary<string, int>();
						List<CondTrigger> list5 = new List<CondTrigger>();
						HashSet<string> hashSet2 = new HashSet<string>(cTLoot.Count);
						foreach (CondTrigger item6 in cTLoot)
						{
							if (hashSet2.Add(item6.strName))
							{
								list5.Add(item6);
							}
							int num3 = (int)Math.Ceiling(item6.fCount);
							if (dictionary.ContainsKey(item6.strName))
							{
								dictionary[item6.strName] += num3;
							}
							else
							{
								dictionary[item6.strName] = num3;
							}
						}
						foreach (CondTrigger item7 in list5)
						{
							JsonInteraction value2 = null;
							string text = "ACTFeedItem" + item7.strName;
							DataHandler.dictInteractions.TryGetValue(text, out value2);
							if (value2 == null)
							{
								Loot loot = DataHandler.GetLoot(text);
								if (loot.strName != text)
								{
									loot.strName = text;
									loot.strType = "trigger";
									loot.aCOs = new string[1] { item7.strName + "=1.0x1" };
									DataHandler.dictLoot[text] = loot;
									Debug.Log("Auto-generating Loot: " + text);
								}
								value2 = DataHandler.dictInteractions["ACTFeedItem"].Clone();
								value2.strName = text;
								if (!string.IsNullOrEmpty(objThem.strPlaceholderInstallReq))
								{
									value2.strDesc = value2.strDesc.Replace("[object]", DataHandler.GetCOShortName(objThem.strPlaceholderInstallReq));
								}
								else
								{
									value2.strDesc = value2.strDesc.Replace("[object]", item7.RulesInfo);
								}
								if (!GrammarUtils.inflectedStrings.TryGetValue(value2.strDesc, out var _))
								{
									JsonInteraction value4 = null;
									if (DataHandler.dictInteractions.TryGetValue("ACTFeedItem", out value4))
									{
										InflectedString inflectedString = GrammarUtils.inflectedStrings[value4.strDesc];
										InflectedString inflectedString2 = new InflectedString
										{
											tokens = new List<TokenData>()
										};
										inflectedString2.tokens.AddRange(inflectedString.tokens);
										if (inflectedString2.tokens.Count > 0)
										{
											inflectedString2.tokens.RemoveAt(inflectedString2.tokens.Count - 1);
										}
										GrammarUtils.inflectedStrings.TryAdd(value2.strDesc, inflectedString2);
									}
								}
								value2.aLootItms = new string[1] { "Give," + text + ",true,false" };
								value2.bLot = true;
								value2.fTargetPointRange = fTargetPointRange;
								DataHandler.dictInteractions[value2.strName] = value2;
							}
							int num4 = dictionary[item7.strName];
							for (int j = 0; j < num4; j++)
							{
								Task2 task = new Task2();
								task.strName = value2.strName;
								task.strInteraction = value2.strName;
								task.strTargetCOID = objThem.strID;
								if (CrewSim.objInstance.workManager.taskUpstream != null)
								{
									task.CopyFrom(CrewSim.objInstance.workManager.taskUpstream);
									task.strDuty = CrewSim.objInstance.workManager.taskUpstream.strDuty;
								}
								else
								{
									task.strDuty = "Haul";
								}
								task.bManual = false;
								CrewSim.objInstance.workManager.AddTask(task, num4);
							}
							sTR_IA_FAIL_DEFAULT = "Items required first. Adding tasks now.";
							AddFailReason("main", sTR_IA_FAIL_DEFAULT);
						}
					}
				}
			}
			list3 = null;
			list2 = null;
			cTLoot = null;
			if (!flag4)
			{
				if (bStats && DataHandler.dictSocialStats.ContainsKey(strName))
				{
					DataHandler.dictSocialStats[strName].nMissingItem++;
				}
				return false;
			}
		}
		if (strLootCTsLacks != null)
		{
			List<CondOwner> list3 = objUs.GetCOs(bAllowLocked: false);
			List<CondOwner> list2 = new List<CondOwner>();
			CondTrigger condTrigger = DataHandler.GetCondTrigger("TIs[us]");
			List<CondOwner> list6 = null;
			if (strLootCTsLacks == "CT[them]" || strLootCTsLacks == "CT[3rd]")
			{
				if (strLootCTsLacks == "CT[them]")
				{
					list6 = ((!(objThem == null) && list3.Contains(objThem)) ? new List<CondOwner> { objThem } : null);
				}
				else if (strLootCTsLacks == "CT[3rd]")
				{
					list6 = ((!(obj3rd == null) && list3.Contains(obj3rd)) ? new List<CondOwner> { obj3rd } : null);
				}
			}
			else
			{
				List<CondTrigger> cTLootFlat = DataHandler.GetLoot(strLootCTsLacks).GetCTLootFlat(condTrigger);
				list6 = CheckItemsAvailable(cTLootFlat, list3, objUs, bSeekFirst: false, null, bUseTest: false);
			}
			list3 = null;
			list2 = null;
			if (list6 != null)
			{
				if (bStats && DataHandler.dictSocialStats.ContainsKey(strName))
				{
					DataHandler.dictSocialStats[strName].nMissingItem++;
				}
				return false;
			}
		}
		if (strLootCTsGive != null || strLootCTsRemoveUs != null || strLootCTsUse != null)
		{
			List<CondOwner> list3 = objUs.GetCOsSafe(bAllowLocked: false);
			if (bGetItemBefore)
			{
				list3.AddRange(objUs.ship.GetCOs(ctNotCarried, bSubObjects: true, bAllowDocked: true, bAllowLocked: false));
			}
			CondTrigger condTrigger2 = DataHandler.GetCondTrigger("TIs[us]");
			List<CondTrigger> cTLootFlat2 = DataHandler.GetLoot(strLootCTsGive).GetCTLootFlat(condTrigger2);
			List<CondTrigger> cTLootFlat3 = DataHandler.GetLoot(strLootCTsUse).GetCTLootFlat(condTrigger2);
			List<CondTrigger> cTLootFlat4 = DataHandler.GetLoot(strLootCTsRemoveUs).GetCTLootFlat(condTrigger2);
			if (objThem.strPersistentCO != null)
			{
				CondOwner value5 = null;
				if (DataHandler.mapCOs.TryGetValue(objThem.strPersistentCO, out value5) && list3.IndexOf(value5) > 0)
				{
					list3.Remove(value5);
					list3.Insert(0, value5);
				}
			}
			aLootItemGiveContract = new List<CondOwner>(list3);
			List<CondOwner> list2 = objThem.GetCOs(bAllowLocked: false);
			if (list2 != null)
			{
				foreach (CondOwner item8 in list2)
				{
					aLootItemGiveContract.Remove(item8);
				}
			}
			aLootItemGiveContract = CheckItemsAvailable(cTLootFlat2, aLootItemGiveContract, objUs, bSeekFirst: true, objThem.strPersistentCO, bUseTest: false);
			aLootItemRemoveContract = CheckItemsAvailable(cTLootFlat4, list3, objUs, bSeekFirst: true, objThem.strPersistentCO, bUseTest: false);
			list3.Remove(objThem);
			aLootItemUseContract = CheckItemsAvailable(cTLootFlat3, list3, objUs, bSeekFirst: true, objThem.strPersistentCO, strUseCase != null);
			bool num5 = (cTLootFlat2.Count > 0 && aLootItemGiveContract == null) || (cTLootFlat3.Count > 0 && aLootItemUseContract == null) || (cTLootFlat4.Count > 0 && aLootItemRemoveContract == null);
			list3 = null;
			list2 = null;
			cTLootFlat2 = null;
			cTLootFlat3 = null;
			cTLootFlat4 = null;
			condTrigger2 = null;
			if (num5)
			{
				aSeekItemsForContract.Clear();
				if (bStats && DataHandler.dictSocialStats.ContainsKey(strName))
				{
					DataHandler.dictSocialStats[strName].nMissingItem++;
				}
				return false;
			}
		}
		else
		{
			aLootItemGiveContract = new List<CondOwner>();
			aLootItemUseContract = new List<CondOwner>();
			aLootItemRemoveContract = new List<CondOwner>();
		}
		if (strLootCTsTake != null)
		{
			List<CondOwner> list3 = objThem.GetCOs(bAllowLocked: false);
			CondTrigger condTrigger3 = DataHandler.GetCondTrigger("TIs[us]");
			List<CondTrigger> cTLootFlat5 = DataHandler.GetLoot(strLootCTsTake).GetCTLootFlat(condTrigger3);
			aLootItemTakeContract = CheckItemsAvailable(cTLootFlat5, list3, objUs, bSeekFirst: false, null, bUseTest: false);
			list3 = null;
			List<CondOwner> list2 = null;
		}
		else
		{
			aLootItemTakeContract = new List<CondOwner>();
		}
		if (aLootItemTakeContract == null)
		{
			if (bStats && DataHandler.dictSocialStats.ContainsKey(strName))
			{
				DataHandler.dictSocialStats[strName].nMissingItem++;
			}
			return false;
		}
		mapFails["main"][0] = "";
		return true;
	}

	public bool Triggered(CondOwner objUs, CondOwner objThem, bool bStats = false, bool bIgnoreItems = false, bool bCheckPath = false, bool bFetchItems = true, List<string> aForbid3rds = null)
	{
		if (strActionGroup == "Ship")
		{
			if (IsWithinShipRange())
			{
				return TriggeredInternal(objUs, objThem, bStats, bIgnoreItems, bCheckPath, bFetchItems: true, aForbid3rds);
			}
			return false;
		}
		return TriggeredInternal(objUs, objThem, bStats, bIgnoreItems, bCheckPath, bFetchItems, aForbid3rds);
	}

	public bool Triggered(bool bStats = false, bool bIgnoreItems = false, bool bCheckPath = false)
	{
		return Triggered(objUs, objThem, bStats, bIgnoreItems, bCheckPath);
	}

	private bool IsWithinShipRange()
	{
		if (fTargetPointRange == 0f)
		{
			return true;
		}
		if (objUs == null || objUs.ship == null || objThem == null || objThem.ship == null)
		{
			return false;
		}
		if (fTargetPointRange < 0f)
		{
			return objUs.ship.IsDockedWith(objThem.ship);
		}
		if (strThemType == TARGET_SELF && objUs == objThem)
		{
			return true;
		}
		double num = (objUs.ship.IsDockedWith(objThem.ship) ? (-1.0) : CollisionManager.GetRangeToCollisionKM(objUs.ship, objThem.ship));
		if (num < (double)fTargetPointRange)
		{
			return num >= 0.0;
		}
		return false;
	}

	private int DistFromptRef(CondOwner x, CondOwner y)
	{
		if (x == null || y == null)
		{
			return 0;
		}
		_ = ptRef;
		float distance = MathUtils.GetDistance(ptRef.y, ptRef.y, x.tf.position.x, x.tf.position.y);
		float distance2 = MathUtils.GetDistance(ptRef.y, ptRef.y, y.tf.position.x, y.tf.position.y);
		return distance.CompareTo(distance2);
	}

	private List<CondOwner> CheckItemsAvailable(List<CondTrigger> aCTsRequired, List<CondOwner> aCOsAvail, CondOwner objUs, bool bSeekFirst, string strPersistentCO, bool bUseTest)
	{
		if (aCTsRequired == null || aCTsRequired.Count == 0)
		{
			return null;
		}
		List<CondOwner> list = new List<CondOwner>();
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIs[us]");
		bool flag = true;
		Pathfinder pathfinder = objUs.Pathfinder;
		foreach (CondTrigger item in aCTsRequired)
		{
			if (item.strName == condTrigger.strName)
			{
				list.Add(objUs);
				continue;
			}
			List<string> aOutUseFails;
			CondOwner nearestTriggered = objUs.GetNearestTriggered(item, aCOsAvail, strPersistentCO, strUseCase, bManual, this, out aOutUseFails);
			if (nearestTriggered == null)
			{
				flag = false;
				if (!bVerboseTrigger)
				{
					break;
				}
				AddFailReason("items", item.RulesInfo);
				if (aOutUseFails == null || aOutUseFails.Count <= 0)
				{
					continue;
				}
				foreach (string item2 in aOutUseFails)
				{
					AddFailReason("specs", item2);
				}
			}
			else
			{
				list.Add(nearestTriggered);
				if (!bUseTest)
				{
					aCOsAvail?.Remove(nearestTriggered);
				}
			}
		}
		if (!flag)
		{
			return null;
		}
		if (flag)
		{
			if (bSeekFirst)
			{
				List<CondOwner> list2 = new List<CondOwner>();
				foreach (CondOwner item3 in list)
				{
					if (item3 == objUs || !(objUs.GetCORef(item3) == null))
					{
						continue;
					}
					bool flag2 = false;
					foreach (Slot slot in objUs.GetSlots(bDeep: true))
					{
						if (!slot.bHide && slot.CanFit(item3, bAuto: true, bSub: true, checkStacks: false, bAllowLocked: false))
						{
							flag2 = true;
							break;
						}
					}
					if (!flag2)
					{
						objUs.LogMessage(STR_IA_FAIL_INV_SPACE + item3.strNameFriendly, "Bad", strName);
						if (!objUs.HasCond("IsAIManual"))
						{
							Pledge2 pledge = PledgeFactory.Factory(objUs, DataHandler.GetPledge("AIFreeUpSpace"));
							objUs.AddPledge(pledge);
						}
						return null;
					}
					Vector2 pos = item3.GetPos("use");
					Tile tileAtWorldCoords = objUs.ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
					if (pathfinder == null)
					{
						if ((float)TileUtils.TileRange(objUs.ship.GetTileAtWorldCoords1(objUs.tf.position.x, objUs.tf.position.y, bAllowDocked: true), tileAtWorldCoords) > fTargetPointRange)
						{
							flag = false;
							if (bVerboseTrigger)
							{
								AddFailReason("items", "Can't reach " + item3.strName);
							}
							break;
						}
						list2.Add(item3);
					}
					else
					{
						bool bAllowAirlocks = objUs.HasAirlockPermission(bManual);
						PathResult pathResult = pathfinder.CheckGoal(tileAtWorldCoords, fTargetPointRange, item3, bAllowAirlocks);
						if (!pathResult.HasPath)
						{
							flag = false;
							if (bVerboseTrigger)
							{
								AddFailReason("items", "Can't reach " + item3.strName);
								string text = pathResult.FailReason(objUs);
								if (!string.IsNullOrEmpty(text))
								{
									AddFailReason("items", text);
								}
							}
							if (pathResult.bAirlockBlocked)
							{
								bAirlockBlocked = pathResult.bAirlockBlocked;
							}
							break;
						}
					}
					list2.Add(item3);
				}
				if (flag)
				{
					aSeekItemsForContract.AddRange(list2);
				}
				else
				{
					list = null;
				}
			}
		}
		else
		{
			list = null;
		}
		return list;
	}

	private InteractionRangeData ParseRangesFromInteractionString(string rangeSubString)
	{
		InteractionRangeData interactionRangeData = new InteractionRangeData();
		if (string.IsNullOrEmpty(rangeSubString))
		{
			return interactionRangeData;
		}
		rangeSubString = rangeSubString.Replace("[", "").Replace("]", "");
		string[] array = rangeSubString.Split('=');
		if (array[0] != "range" && array[0] != "nolos")
		{
			return interactionRangeData;
		}
		interactionRangeData.UseLoS = array[0] == "range";
		if (array.Length != 2)
		{
			return interactionRangeData;
		}
		string[] array2 = array[1].Split('-');
		if (array2.Length == 1)
		{
			float.TryParse(array2[0], out interactionRangeData.MaxRange);
		}
		else if (array2.Length == 2)
		{
			float.TryParse(array2[0], out interactionRangeData.MinRange);
			float.TryParse(array2[1], out interactionRangeData.MaxRange);
		}
		return interactionRangeData;
	}

	private void ApplyLosInteraction(string[] loSReactions)
	{
		if (loSReactions == null || loSReactions.Length == 0)
		{
			return;
		}
		foreach (string text in loSReactions)
		{
			if (string.IsNullOrEmpty(text))
			{
				continue;
			}
			string[] array = text.Split(',');
			Interaction interaction = DataHandler.GetInteraction(array[0]);
			if (interaction == null)
			{
				break;
			}
			InteractionRangeData rangeData = ParseRangesFromInteractionString(array.LastOrDefault());
			IEnumerable<CondOwner> cOSInRange = GetCOSInRange(objUs, objThem, rangeData, interaction.CTTestThem);
			if (cOSInRange == null)
			{
				continue;
			}
			bool flag = false;
			foreach (CondOwner item in cOSInRange)
			{
				CondOwner condOwner = objUs;
				CondOwner condOwner2 = objThem;
				CondOwner[] array2 = new CondOwner[3] { item, condOwner, condOwner2 };
				CondOwner[] array3 = new CondOwner[3] { item, condOwner, condOwner2 };
				for (int j = 1; j < array.Length; j++)
				{
					if (j < array2.Length)
					{
						CondOwner condOwner3 = ParseInteractionString(array[j], array2);
						array3[j - 1] = ((condOwner3 != null) ? condOwner3 : array2[j - 1]);
					}
				}
				CondOwner current = array3[0];
				condOwner = array3[1];
				condOwner2 = array3[2];
				if (flag)
				{
					interaction = DataHandler.GetInteraction(array[0]);
				}
				interaction.objUs = current;
				interaction.objThem = condOwner;
				interaction.obj3rd = condOwner2;
				if (interaction.Triggered(interaction.objUs, interaction.objThem, bStats: false, bIgnoreItems: true))
				{
					interaction.ApplyChain();
				}
				flag = true;
			}
		}
	}

	private IEnumerable<CondOwner> GetCOSInRange(CondOwner coLosUs, CondOwner coLosThem, InteractionRangeData rangeData, CondTrigger ctTestUs)
	{
		if (coLosUs == null)
		{
			return null;
		}
		List<CondOwner> list = new List<CondOwner>();
		if (ctTestUs.RequiresHumans)
		{
			foreach (CondOwner person in coLosUs.ship.GetPeople(bAllowDocked: true))
			{
				if (ctTestUs.Triggered(person))
				{
					list.Add(person);
				}
			}
		}
		else
		{
			list = coLosUs.ship.GetCOs(ctTestUs, bSubObjects: false, bAllowDocked: true, bAllowLocked: false);
		}
		List<CondOwner> list2 = new List<CondOwner>();
		float num = rangeData.MaxRange * rangeData.MaxRange;
		float num2 = rangeData.MinRange * rangeData.MinRange;
		foreach (CondOwner item in list)
		{
			if (item == coLosUs || item == coLosThem)
			{
				continue;
			}
			float distanceSquared = MathUtils.GetDistanceSquared(coLosUs, item);
			if (!(distanceSquared > num) && !(distanceSquared < num2))
			{
				if (!rangeData.UseLoS && coLosThem.currentRoom == item.currentRoom)
				{
					list2.Add(item);
				}
				else if (Visibility.IsCondOwnerLOSVisibleFromCo(coLosUs, item) || (coLosThem != null && Visibility.IsCondOwnerLOSVisibleFromCo(coLosThem, item)))
				{
					list2.Add(item);
				}
			}
		}
		return list2;
	}

	public void ApplyEffects(List<string> aLog = null, bool isCancelIa = false)
	{
		if (objUs == null)
		{
			Debug.Log("Warning: Interaction " + strName + " has null objUs. Aborting.");
			return;
		}
		if (objThem == null)
		{
			Debug.LogWarning("Warning: Interaction " + strName + " has null objThem. Aborting.");
			return;
		}
		if (bPause && !CrewSim.bSoakTest)
		{
			CrewSim.Paused = true;
		}
		aLog?.Add(GrammarUtils.GenerateDescription(this));
		if (strChainStart != null)
		{
			CrewSim.objInstance.workManager.CompleteTask(strChainStart, objUs.strID, objThem.strID);
		}
		else
		{
			CrewSim.objInstance.workManager.CompleteTask(strName, objUs.strID, objThem.strID);
		}
		if (strIdleAnim != null)
		{
			string animFor = strIdleAnim;
			Pathfinder pathfinder = objUs.Pathfinder;
			if (pathfinder != null)
			{
				animFor = pathfinder.GetAnimFor(strIdleAnim);
			}
			objUs.strIdleAnim = animFor;
		}
		if (strTeleport != null && objThem != null && objThem != objUs)
		{
			Teleport(objUs.Pathfinder, isCancelIa);
		}
		Relationship relationship = null;
		Relationship relationship2 = null;
		if (objUs.socUs != null && objThem.socUs != null && objUs.socUs != objThem.socUs)
		{
			relationship2 = objThem.socUs.GetRelationship(objUs.strName);
			if (relationship2 == null)
			{
				relationship2 = objThem.socUs.AddStranger(objUs.pspec);
			}
			relationship = objUs.socUs.GetRelationship(objThem.strName);
			if (relationship == null)
			{
				relationship = objUs.socUs.AddStranger(objThem.pspec);
			}
			objUs.SwitchRELConds(relationship, bSilent: true);
			objThem.SwitchRELConds(relationship2, bSilent: true);
		}
		if (LootAddCondRulesUs != null)
		{
			foreach (string lootName in LootAddCondRulesUs.GetLootNames())
			{
				objUs.AddCondRule(lootName);
			}
		}
		if (LootAddCondRulesThem != null)
		{
			foreach (string lootName2 in LootAddCondRulesThem.GetLootNames())
			{
				objThem.AddCondRule(lootName2);
			}
		}
		CalcRate();
		if (aLootItemUseContract != null)
		{
			foreach (CondOwner item2 in aLootItemUseContract)
			{
				if (item2 != null)
				{
					item2.Use(strUseCase);
				}
			}
			aLootItemUseContract = null;
		}
		ApplyLootCT(LootCTsUs, relationship, objUs, objThem, 1f);
		ApplyLootConds(LootCondsUs, relationship, objUs, objThem, 1f);
		ApplyLootCT(LootCTsThem, relationship2, objThem, objUs, fCTThemModifierUs * fCTThemModifierTools * (1f - fCTThemModifierPenalty));
		ApplyLootConds(LootCondsThem, relationship2, objThem, objUs, fCTThemModifierUs * fCTThemModifierTools * (1f - fCTThemModifierPenalty));
		ApplyLosInteraction(aLoSReactions);
		objUs.ApplyAModes(aAModesAddedUs, bRebuildQAB: true);
		objThem.ApplyAModes(aAModesAddedThem, bRebuildQAB: true);
		objUs.ApplyGPMChanges(aGPMChangesUs);
		objThem.ApplyGPMChanges(aGPMChangesThem);
		if (obj3rd != null)
		{
			ApplyLootCT(LootCTs3rd, null, obj3rd, null, 1f);
			ApplyLootConds(LootConds3rd, null, obj3rd, null, 1f);
		}
		if (aLootItemRemoveContract != null)
		{
			foreach (CondOwner item3 in aLootItemRemoveContract)
			{
				if (item3 == null)
				{
					continue;
				}
				CondOwner singleOrStack = item3.GetSingleOrStack(bRemoveWholeStack);
				if (singleOrStack != null)
				{
					Container container = null;
					Ship ship = singleOrStack.ship;
					CondOwner objCOParent = singleOrStack.objCOParent;
					if (objCOParent != null)
					{
						container = objCOParent.objContainer;
					}
					if (!bRemoveWholeStack && singleOrStack.aStack.Count > 0)
					{
						singleOrStack.PopHeadFromStack();
					}
					else
					{
						ship = singleOrStack.RemoveFromCurrentHome();
					}
					if (!bDestroyItem)
					{
						Vector2 vector = ((objCOParent != null) ? (objCOParent.tf.position - objUs.tf.position).ToVector2() : Vector2.zero);
						CondOwner condOwner = objUs.DropCO(singleOrStack, bAllowLocked: false, ship, vector.x, vector.y);
						if (condOwner != null && ship != null)
						{
							Debug.LogWarning("Could not find space for item " + singleOrStack.strName + " expanding drop zone");
							for (int i = 4; i < 10; i += 2)
							{
								if (!(condOwner != null))
								{
									break;
								}
								condOwner = objUs.DropCO(singleOrStack, bAllowLocked: false, ship, vector.x, vector.y, dropInContainersLast: true, null, i, ignoreZones: true);
							}
							if (condOwner != null)
							{
								ship.AddCO(condOwner, bTiles: true);
								Debug.LogWarning("Could not find space for item " + singleOrStack.strName + " from Interaction " + strName);
							}
						}
					}
					Container.Redraw(container);
					singleOrStack.UpdateAppearance();
				}
				if (objUs == CrewSim.coPlayer && item3.HasCond("IsSocialItem"))
				{
					CanvasManager.instance.goCanvasFloaties.GetComponent<GUISocialItemAnimator>().SpendSocialItemAnimation(item3.strName, item3.strPortraitImg);
				}
				item3.strSourceInteract = strChainStart;
				item3.strSourceCO = objUs.strID;
				if (bDestroyItem)
				{
					CrewSim.objInstance.ScheduleCODestruction(item3);
				}
			}
			aLootItemRemoveContract = null;
		}
		if (strLootItmRemoveThem != null)
		{
			CondTrigger condTrigger = DataHandler.GetCondTrigger("TIs[us]");
			List<CondTrigger> cTLootFlat = DataHandler.GetLoot(strLootItmRemoveThem).GetCTLootFlat(condTrigger);
			List<CondOwner> cOsSafe = objThem.GetCOsSafe(bAllowLocked: false);
			cOsSafe.AddRange(objThem.GetLotCOs(bSubItems: false));
			foreach (CondTrigger item4 in cTLootFlat)
			{
				if (item4 == null)
				{
					continue;
				}
				if (item4.strName == condTrigger.strName)
				{
					objThem.RemoveFromCurrentHome();
					CrewSim.objInstance.ScheduleCODestruction(objThem);
					continue;
				}
				foreach (CondOwner item5 in cOsSafe)
				{
					if (!(item5 == null) && item4.Triggered(item5))
					{
						item5.RemoveFromCurrentHome();
						CrewSim.objInstance.ScheduleCODestruction(item5);
						cOsSafe.Remove(item5);
						break;
					}
				}
			}
		}
		if (strLootItmAddUs != null)
		{
			List<CondOwner> cOsSafe = DataHandler.GetLoot(strLootItmAddUs).GetCOLoot(objUs, bSuppressOverride: false);
			string text = objUs.ShortName + " gains ";
			int num = 0;
			foreach (CondOwner item6 in cOsSafe)
			{
				if (!(item6 == null))
				{
					if (num > 0)
					{
						text += ", ";
					}
					text += item6.ShortName;
					num++;
					CondOwner condOwner2 = objUs.AddCO(item6, bEquip, bOverflow: true, bIgnoreLocks: true);
					if (condOwner2 != null)
					{
						OverflowAddCO(objUs, condOwner2);
					}
					if (objUs == CrewSim.coPlayer && item6.HasCond("IsSocialItem"))
					{
						CanvasManager.instance.goCanvasFloaties.GetComponent<GUISocialItemAnimator>().SpawnSocialItemAnimation(item6.strName, item6.strPortraitImg);
					}
					item6.strSourceInteract = strChainStart;
					item6.strSourceCO = objThem.strID;
				}
			}
			text += ".";
			if (num > 0)
			{
				objUs.LogMessage(text, "Neutral", objThem.strID);
			}
		}
		if (strLootItmAddThem != null)
		{
			List<CondOwner> cOsSafe = DataHandler.GetLoot(strLootItmAddThem).GetCOLoot(objThem, bSuppressOverride: false);
			string text2 = objThem.ShortName + " gains ";
			int num2 = 0;
			foreach (CondOwner item7 in cOsSafe)
			{
				if (!(item7 == null))
				{
					if (num2 > 0)
					{
						text2 += ", ";
					}
					text2 += item7.ShortName;
					num2++;
					CondOwner condOwner3 = objThem.AddCO(item7, bEquip, bOverflow: true, bIgnoreLocks: true);
					if (condOwner3 != null)
					{
						OverflowAddCO(objThem, condOwner3);
					}
					item7.strSourceInteract = strChainStart;
					item7.strSourceCO = objThem.strID;
				}
			}
			text2 += ".";
			if (num2 > 0)
			{
				objThem.LogMessage(text2, "Neutral", objThem.strID);
			}
		}
		if (aLootItemGiveContract != null && aLootItemGiveContract.Count > 0)
		{
			string text3 = objUs.ShortName + " gives ";
			int num3 = 0;
			bool flag = objUs != objThem;
			foreach (CondOwner item8 in aLootItemGiveContract)
			{
				if (item8 == null)
				{
					continue;
				}
				if (num3 > 0)
				{
					text3 += ", ";
				}
				text3 += item8.ShortName;
				num3++;
				flag = flag && item8 != objUs;
				CondOwner singleOrStack2 = item8.GetSingleOrStack(bGiveWholeStack);
				if (singleOrStack2 != null)
				{
					Container container2 = null;
					if (singleOrStack2.objCOParent != null)
					{
						container2 = singleOrStack2.objCOParent.objContainer;
					}
					Ship ship2 = singleOrStack2.ship;
					if (!bGiveWholeStack && singleOrStack2.aStack.Count > 0)
					{
						singleOrStack2.PopHeadFromStack();
					}
					else
					{
						ship2 = singleOrStack2.RemoveFromCurrentHome();
					}
					if (bLot)
					{
						objThem.AddLotCO(singleOrStack2);
					}
					else
					{
						CondOwner condOwner4;
						if (bEquip)
						{
							condOwner4 = objThem.AddCO(singleOrStack2, bEquip, bOverflow: false, bIgnoreLocks: false);
							if (condOwner4 != null)
							{
								objThem.LogMessage(STR_IA_FAIL_NO_EQUIP, "Bad", objThem.strID);
								condOwner4 = objThem.AddCO(singleOrStack2, bEquip, bOverflow: true, bIgnoreLocks: true);
							}
						}
						else
						{
							condOwner4 = objThem.AddCO(singleOrStack2, bEquip, bOverflow: true, bIgnoreLocks: true);
						}
						if (condOwner4 != null)
						{
							objThem.LogMessage(STR_ERROR_NO_ROOM_INV, "Bad", objThem.strID);
							ship2?.AddCO(condOwner4, bTiles: true);
						}
					}
					Container.Redraw(container2);
					Container.Redraw(objThem.objContainer);
				}
				if (objUs == CrewSim.coPlayer && item8.HasCond("IsSocialItem"))
				{
					CanvasManager.instance.goCanvasFloaties.GetComponent<GUISocialItemAnimator>().SpendSocialItemAnimation(item8.strName, item8.strPortraitImg);
				}
				item8.strSourceInteract = strChainStart;
				item8.strSourceCO = objUs.strID;
			}
			text3 = text3 + " to " + objThem.ShortName + ".";
			if (flag && num3 > 0)
			{
				objThem.LogMessage(text3, "Neutral", objThem.strID);
				objUs.LogMessage(text3, "Neutral", objUs.strID);
			}
			aLootItemGiveContract = null;
		}
		if (aLootItemTakeContract != null && aLootItemTakeContract.Count > 0)
		{
			string text4 = objUs.ShortName + " takes ";
			int num4 = 0;
			bool flag2 = objUs != objThem;
			foreach (CondOwner item9 in aLootItemTakeContract)
			{
				if (!(item9 == null))
				{
					if (num4 > 0)
					{
						text4 += ", ";
					}
					text4 += item9.ShortName;
					num4++;
					flag2 = flag2 && item9 != objThem;
					item9.RemoveFromCurrentHome();
					CondOwner condOwner5 = objUs.AddCO(item9, bEquip, bOverflow: true, bIgnoreLocks: true);
					if (condOwner5 != null)
					{
						objUs.LogMessage(STR_ERROR_NO_ROOM_INV, "Bad", objUs.strID);
						objUs.DropCO(condOwner5, bAllowLocked: false, objUs.ship);
					}
					item9.strSourceInteract = strChainStart;
					item9.strSourceCO = objThem.strID;
				}
			}
			text4 = text4 + " from " + objThem.ShortName + ".";
			if (flag2 && num4 > 0)
			{
				objThem.LogMessage(text4, "Neutral", objThem.strID);
				objUs.LogMessage(text4, "Neutral", objUs.strID);
			}
			aLootItemTakeContract = null;
		}
		if (objLootModeSwitch != null)
		{
			if (objUs.ship == null)
			{
				Debug.LogError("Error: Trying to modeswitch an object that has no ship assigned: " + objUs.ToString());
			}
			else
			{
				List<string> lootNames = objLootModeSwitch.GetLootNames();
				List<CondOwner> cOsSafe = new List<CondOwner>();
				foreach (string item10 in lootNames)
				{
					string strIDOld = objUs.strID;
					if (objUs.strPersistentCO != null)
					{
						strIDOld = objUs.strPersistentCO;
						objUs.strPersistentCO = null;
					}
					if (cOsSafe.Count == 0)
					{
						cOsSafe.Add(DataHandler.GetCondOwner(item10, null, null, !objLootModeSwitch.bSuppress, null, null, strIDOld));
					}
					else
					{
						cOsSafe.Add(DataHandler.GetCondOwner(item10, null, null, !objLootModeSwitch.bSuppress));
					}
				}
				CondOwner condOwner6 = null;
				while (cOsSafe.Count > 0)
				{
					if (condOwner6 == null)
					{
						condOwner6 = cOsSafe[0];
						objUs.ModeSwitch(condOwner6, objUs.tf.position);
						if (condOwner6 != null)
						{
							objUs = condOwner6;
						}
						cOsSafe.RemoveAt(0);
						break;
					}
					cOsSafe.RemoveAt(0);
				}
				if (condOwner6 == null)
				{
					Debug.Log("Error: CO " + objUs.strName + objUs.strID + " unable to mode switch to null. Mode loot: " + objLootModeSwitch.strName);
					return;
				}
				if (cOsSafe.Count > 0)
				{
					Ship ship3 = null;
					ship3 = ((objUs.ship != null) ? objUs.ship : ((!(objUs.objCOParent != null)) ? CrewSim.shipCurrentLoaded : ((objUs.objCOParent.ship == null) ? CrewSim.shipCurrentLoaded : objUs.objCOParent.ship)));
					JsonZone zoneFromTileRadius = TileUtils.GetZoneFromTileRadius(ship3, objUs.tf.position, 2, bShuffled: true);
					CondTrigger condTrigger2 = DataHandler.GetCondTrigger("TIsLootSpawnOK");
					List<CondOwner> cOsInZone = ship3.GetCOsInZone(zoneFromTileRadius, condTrigger2, bAllowLocked: false);
					cOsSafe = TileUtils.DropCOsNearby(cOsSafe, ship3, zoneFromTileRadius, cOsInZone, condTrigger2, bIgnoreLocks: false);
					foreach (CondOwner item11 in cOsSafe)
					{
						Vector3 position = objUs.tf.position;
						position.z = item11.tf.position.z;
						item11.tf.position = position;
						ship3.AddCO(item11, bTiles: true);
					}
				}
			}
		}
		if (objLootModeSwitchThem != null)
		{
			if (objThem.ship == null)
			{
				Debug.LogError("Error: Trying to modeswitch an object that has no ship assigned: " + objThem.ToString());
			}
			else
			{
				List<string> lootNames2 = objLootModeSwitchThem.GetLootNames();
				List<CondOwner> cOsSafe = new List<CondOwner>();
				foreach (string item12 in lootNames2)
				{
					string strIDOld2 = objThem.strID;
					if (objThem.strPersistentCO != null)
					{
						strIDOld2 = objThem.strPersistentCO;
						objThem.strPersistentCO = null;
					}
					if (cOsSafe.Count == 0)
					{
						cOsSafe.Add(DataHandler.GetCondOwner(item12, null, null, !objLootModeSwitchThem.bSuppress, null, null, strIDOld2));
					}
					else
					{
						cOsSafe.Add(DataHandler.GetCondOwner(item12, null, null, !objLootModeSwitchThem.bSuppress));
					}
				}
				CondOwner condOwner7 = null;
				while (cOsSafe.Count > 0)
				{
					if (condOwner7 == null)
					{
						condOwner7 = cOsSafe[0];
						objThem.ModeSwitch(condOwner7, objThem.tf.position);
						if (condOwner7 != null)
						{
							objThem = condOwner7;
						}
						cOsSafe.RemoveAt(0);
						break;
					}
					cOsSafe.RemoveAt(0);
				}
				if (condOwner7 == null)
				{
					Debug.Log("Error: CO " + objThem.strName + objThem.strID + " unable to mode switch to null. Mode loot: " + objLootModeSwitchThem.strName);
					return;
				}
				if (cOsSafe.Count > 0)
				{
					JsonZone zoneFromTileRadius2 = TileUtils.GetZoneFromTileRadius(objThem.ship, objThem.tf.position, 2, bShuffled: true);
					CondTrigger condTrigger3 = DataHandler.GetCondTrigger("TIsLootSpawnOK");
					List<CondOwner> cOsInZone2 = objThem.ship.GetCOsInZone(zoneFromTileRadius2, condTrigger3, bAllowLocked: false);
					cOsSafe = TileUtils.DropCOsNearby(cOsSafe, objThem.ship, zoneFromTileRadius2, cOsInZone2, condTrigger3, bIgnoreLocks: false);
					foreach (CondOwner item13 in cOsSafe)
					{
						if (!(item13 == null))
						{
							Vector3 position2 = objUs.tf.position;
							position2.z = item13.tf.position.z;
							item13.tf.position = position2;
							objThem.ship.AddCO(item13, bTiles: true);
						}
					}
				}
			}
		}
		if (aTickersUs != null)
		{
			string[] array = aTickersUs;
			foreach (string text5 in array)
			{
				if (text5[0] == '-')
				{
					objUs.RemoveTicker(text5.Substring(1));
					continue;
				}
				JsonTicker ticker = DataHandler.GetTicker(text5);
				ticker.SetTimeLeft(ticker.fTimeLeft);
				objUs.AddTicker(ticker);
			}
		}
		if (aTickersThem != null)
		{
			string[] array = aTickersThem;
			foreach (string text6 in array)
			{
				if (text6[0] == '-')
				{
					objThem.RemoveTicker(text6.Substring(1));
					continue;
				}
				JsonTicker ticker2 = DataHandler.GetTicker(text6);
				ticker2.SetTimeLeft(ticker2.fTimeLeft);
				objThem.AddTicker(ticker2);
			}
		}
		int num5 = 0;
		while (aSocialNew != null && num5 < aSocialNew.Length)
		{
			if (objUs.socUs == null)
			{
				objUs.socUs = objUs.gameObject.AddComponent<Social>();
			}
			PersonSpec personSpec = null;
			Loot loot = null;
			CondOwner condOwner8 = null;
			string[] array2 = aSocialNew[num5].Split('=');
			JsonPersonSpec personSpec2 = DataHandler.GetPersonSpec(array2[0]);
			if (personSpec2 != null)
			{
				string text7 = personSpec2.strRelSet;
				if (text7 == null || text7 == "")
				{
					text7 = "RELStranger";
				}
				loot = DataHandler.GetLoot(text7);
				bool flag3 = true;
				if (array2.Length > 1 && array2[1].ToLower() == "true")
				{
					flag3 = false;
				}
				if (flag3)
				{
					personSpec = StarSystem.GetPerson(personSpec2, objUs.socUs, bForceUnrelated: true);
				}
				if (personSpec == null)
				{
					personSpec = new PersonSpec(personSpec2, bNew: true);
				}
				condOwner8 = personSpec.GetCO();
				if (condOwner8 == null)
				{
					condOwner8 = personSpec.MakeCondOwner(PersonSpec.StartShip.OLD);
				}
				if (ChangeRelationship(text7, condOwner8, objUs, null, bDoReciprocal: true))
				{
					objUs.socUs.GetRelationship(condOwner8.strID)?.RevealDefaults();
					if (condOwner8.socUs != null)
					{
						condOwner8.socUs.GetRelationship(objUs.strID)?.RevealDefaults();
					}
					GUIChargenStack component = condOwner8.GetComponent<GUIChargenStack>();
					string text8 = "New ";
					bool flag4 = false;
					foreach (string lootName3 in loot.GetLootNames())
					{
						Condition cond = DataHandler.GetCond(lootName3);
						if (cond != null)
						{
							if (flag4)
							{
								text8 += "/";
							}
							else
							{
								flag4 = true;
							}
							text8 += cond.strNameFriendly;
						}
					}
					text8 = text8 + ": " + personSpec.FullName;
					if (component.GetLatestCareer() != null && component.GetLatestCareer().GetJC() != null)
					{
						text8 = text8 + ", " + component.GetLatestCareer().GetJC().strNameFriendly;
					}
					text8 = text8 + " from " + component.GetHomeworld().strColonyName + ".";
					aLog?.Add(text8);
				}
			}
			num5++;
		}
		ChangeRelationship(strLootRELChangeThemSeesUs, objUs, objThem, aLog);
		ChangeRelationship(strLootRELChangeThemSees3rd, obj3rd, objThem, aLog);
		ChangeRelationship(strLootRELChangeUsSeesThem, objThem, objUs, aLog);
		ChangeRelationship(strLootRELChangeUsSees3rd, obj3rd, objUs, aLog);
		ChangeRelationship(strLootRELChange3rdSeesUs, objUs, obj3rd, aLog);
		ChangeRelationship(strLootRELChange3rdSeesThem, objThem, obj3rd, aLog);
		UpdateStakes(relationship, relationship2);
		if (objUs.socUs != null && !objUs.HasCond("IsPlayer") && objThem.HasCond("IsPlayer") && objUs.bAlive && objThem.socUs != null)
		{
			List<string> list = new List<string>();
			List<string> list2 = new List<string>();
			int num6 = 0;
			foreach (string allReqName in CTTestUs.GetAllReqNames())
			{
				if (!list.Contains(allReqName))
				{
					list.Add(allReqName);
				}
			}
			if (aCondUsPriorities != null)
			{
				foreach (CondScore aCondUsPriority in aCondUsPriorities)
				{
					string discomfortForCond = objUs.GetDiscomfortForCond(aCondUsPriority.strName);
					if (discomfortForCond != null && !relationship2.aReveals.Contains(discomfortForCond))
					{
						list2.Add(discomfortForCond);
						break;
					}
				}
			}
			foreach (string aReveal in relationship2.aReveals)
			{
				if (objUs.HasCond(aReveal) && !list2.Contains(aReveal))
				{
					list2.Add(aReveal);
				}
			}
			foreach (string item14 in list)
			{
				if (objUs.HasCond(item14) && (objUs.mapConds[item14].nDisplayOther != 0 || objUs.mapConds[item14].nDisplayOther != 3) && list2.IndexOf(item14) < 0 && (num6 <= 0 || MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) < 0.5) && GUISocialCombat2.CountsAsSocialReveal(item14))
				{
					list2.Add(item14);
				}
			}
			relationship2.aReveals = list2;
			if (GUISocialCombat2.coUs == objUs || GUISocialCombat2.coThem == objUs)
			{
				GUISocialCombat2.objInstance.UpdateCO(objUs);
			}
			else
			{
				CrewSim.objInstance.UpdateLog(objUs, null);
			}
		}
		Ledger.AddLI(strLedgerDef, objUs, objThem);
		if (strPledgeAdd != null)
		{
			JsonPledge pledge = DataHandler.GetPledge(strPledgeAdd);
			if (pledge != null)
			{
				CondOwner coThem = null;
				if (pledge.strThemID == "[them]")
				{
					coThem = objThem;
				}
				else if (pledge.strThemID == "[3rd]")
				{
					coThem = obj3rd;
				}
				Pledge2 pledge2 = PledgeFactory.Factory(objUs, pledge, coThem);
				pledge2?.Us.AddPledge(pledge2);
			}
		}
		if (strPledgeAddThem != null)
		{
			JsonPledge pledge3 = DataHandler.GetPledge(strPledgeAddThem);
			if (pledge3 != null)
			{
				CondOwner coThem2 = null;
				if (pledge3.strThemID == "[them]")
				{
					coThem2 = objUs;
				}
				else if (pledge3.strThemID == "[3rd]")
				{
					coThem2 = obj3rd;
				}
				Pledge2 pledge4 = PledgeFactory.Factory(objThem, pledge3, coThem2);
				pledge4?.Us.AddPledge(pledge4);
			}
		}
		bool flag5 = true;
		if (attackMode != null)
		{
			double condAmount = objThem.GetCondAmount("StatDefense");
			double x = 50.0 - (condAmount + (double)attackMode.fTargetDefenseMod);
			x = MathUtils.Clamp(x, 0.05, 1.0);
			bool flag6 = objThem.ship != null && objThem.ship.LoadState >= Ship.Loaded.Edit;
			bool bAudio = Wound.bAudio;
			bool flag7 = false;
			string text9 = (string.IsNullOrEmpty(strAttackerName) ? objUs.ShortName : strAttackerName);
			if (flag6)
			{
				Wound.bAudio = true;
				if (!attackMode.bPlayAudioEarly && !string.IsNullOrEmpty(attackMode.strAudioAttack))
				{
					AudioEmitter component2 = objUs.GetComponent<AudioEmitter>();
					if (component2 != null)
					{
						component2.StartOther(attackMode.strAudioAttack);
					}
				}
			}
			if (attackMode.GetAttackType() == JsonAttackMode.Type.melee)
			{
				Tile tileAtWorldCoords = objUs.ship.GetTileAtWorldCoords1(objUs.tf.position.x, objUs.tf.position.y, bAllowDocked: true);
				if (strTargetPoint != null && strTargetPoint != POINT_REMOTE)
				{
					Vector2 pos = objThem.GetPos(strTargetPoint);
					Tile tileAtWorldCoords2 = objUs.ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
					flag5 = (float)TileUtils.TileRange(tileAtWorldCoords, tileAtWorldCoords2) <= fTargetPointRange;
				}
				if (!flag5)
				{
					string strMsg = objThem.ShortName + " out of range.";
					objUs.LogMessage(strMsg, "StatusRed", objUs.strName);
					if (objUs != objThem)
					{
						objThem.LogMessage(strMsg, "StatusRed", objUs.strName);
					}
				}
				else if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) > x)
				{
					string strMsg2 = text9 + STR_COMBAT_MISSED;
					objUs.LogMessage(strMsg2, "Bad", objUs.strName);
					if (objUs != objThem)
					{
						objThem.LogMessage(strMsg2, "Bad", objUs.strName);
					}
				}
				else if (objThem.HasCond("IsWoundable"))
				{
					flag7 = true;
					if (attackMode.fDmgBlunt != 0f || attackMode.fDmgCut != 0f || attackMode.fDmgEnv != 0f)
					{
						bool bBlunt = (double)attackMode.fDmgBlunt > 0.5;
						bool bCut = (double)attackMode.fDmgCut > 0.5;
						Wound woundLocation = objThem.GetWoundLocation(bBlunt, bCut, attackMode.strCTTargetWound);
						if (woundLocation != null)
						{
							Vector2 vector2 = default(Vector2);
							vector2 = ((!string.IsNullOrEmpty(strAttackerName)) ? woundLocation.Damage(attackMode, null, bUnsocket: true, text9) : woundLocation.Damage(attackMode, objUs));
							if (flag6)
							{
								if (objUs == CrewSim.GetSelectedCrew())
								{
									CrewSim.objInstance.CamShake(Mathf.Max(vector2.x, vector2.y));
								}
								objThem.PlayHitAnim(attackMode.fDmgBlunt, attackMode.fDmgCut);
							}
						}
					}
				}
				else if (objThem.HasCond("IsDamageable"))
				{
					flag7 = true;
					if (attackMode.fDmgEnv != 0f)
					{
						Destructable component3 = objThem.GetComponent<Destructable>();
						if (component3 != null)
						{
							float num7 = attackMode.fDmgEnv * (float)attackMode.GetDmgAmount(string.IsNullOrEmpty(strAttackerName) ? objUs : null);
							component3.CO.AddCondAmount("StatDamage", num7);
							component3.DamageCheck();
							component3.CO.EndTurn();
							if (flag6 && objUs == CrewSim.GetSelectedCrew())
							{
								CrewSim.objInstance.CamShake(num7 * 0.1f);
							}
						}
					}
				}
			}
			else
			{
				float fRadius = attackMode.fRange * 1f;
				Vector3 vector3 = objUs.GetPos();
				Vector3 current19 = objThem.GetPos();
				current19 -= vector3;
				Vector3 vector4 = new Vector3(current19.y, 0f - current19.x, current19.z);
				Vector2 vector5 = new Vector3(0f - current19.y, current19.x, current19.z);
				if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) > x)
				{
					string strMsg3 = objUs.ShortName + STR_COMBAT_MISSED;
					objUs.LogMessage(strMsg3, "Bad", objUs.strName);
					if (objUs != objThem)
					{
						objThem.LogMessage(strMsg3, "Bad", objUs.strName);
					}
					Vector3 target = vector4;
					if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) > 0.5)
					{
						target = vector5;
					}
					current19 = Vector3.RotateTowards(current19, target, 0.5f, 0f);
				}
				else
				{
					flag7 = true;
				}
				vector3.z = -0.25f;
				for (int k = 0; k < 1 + attackMode.nExtraRays; k++)
				{
					Vector3 target2 = vector4;
					if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) > 0.5)
					{
						target2 = vector5;
					}
					current19 = Vector3.RotateTowards(current19, target2, MathUtils.Rand(0f, MathF.PI / 180f * attackMode.fSpread, MathUtils.RandType.Low), 0f);
					objUs.ship.DamageSystem.DamageRay(vector3, current19.normalized, fRadius, 1f, attackMode, objUs, bAllowDocked: true);
				}
			}
			string text10 = strIAMiss;
			if (flag7)
			{
				text10 = strIAHit;
			}
			if (text10 != null)
			{
				Interaction interaction = DataHandler.GetInteraction(text10);
				if (interaction != null)
				{
					interaction.objUs = objUs;
					interaction.objThem = objThem;
					interaction.obj3rd = obj3rd;
					interaction.ApplyChain();
				}
			}
			Wound.bAudio = bAudio;
		}
		if (!string.IsNullOrEmpty(strCrime))
		{
			CrimeManager.LogCrime(this);
		}
		if (fFactionScoreChangeLoot != 0f && !string.IsNullOrEmpty(strFactionScoreChangeLoot))
		{
			Loot loot2 = DataHandler.GetLoot(strFactionScoreChangeLoot);
			List<string> allFactions = objUs.GetAllFactions();
			bool flag8 = CrewSim.GetSelectedCrew() == objUs;
			foreach (string item15 in allFactions)
			{
				JsonFaction faction = CrewSim.system.GetFaction(item15);
				if (faction == null)
				{
					continue;
				}
				foreach (string lootName4 in loot2.GetLootNames())
				{
					JsonFaction faction2 = CrewSim.system.GetFaction(lootName4);
					if (faction2 != null)
					{
						float num8 = fFactionScoreChangeLoot;
						if (faction.aMembers.Count > 1)
						{
							num8 = fFactionScoreChangeLoot / (float)faction.aMembers.Count;
						}
						if (!bFactionIgnoreThemPop && faction2.aMembers.Count > 1)
						{
							num8 /= (float)faction2.aMembers.Count;
						}
						if (flag8)
						{
							objUs.LogMessage(lootName4 + " changed their view of " + item15 + " by " + num8.ToString("F2"), "Neutral", objUs.strID, "Fctn:" + lootName4 + " " + num8.ToString("F2"));
						}
						faction2.ApplyFactionRep(faction.strName, num8);
					}
				}
			}
		}
		if (fFactionScoreChangeThem != 0f)
		{
			objThem.ApplyFactionReps(objUs, fFactionScoreChangeThem);
		}
		if (fFactionScoreChangeUs != 0f)
		{
			objUs.ApplyFactionReps(objThem, fFactionScoreChangeThem);
		}
		if (LootAddFactionsUs != null)
		{
			LootAddFactions(LootAddFactionsUs.GetLootNames(), objUs);
		}
		if (LootAddFactionsThem != null)
		{
			LootAddFactions(LootAddFactionsThem.GetLootNames(), objThem);
		}
		if (bInterrupt && flag5 && objThem != null)
		{
			objThem.AICancelAll();
			if (objThem == CrewSim.GetSelectedCrew())
			{
				CrewSim.LowerUI();
			}
			if (GUISocialCombat2.IsInSocialCombat(objThem))
			{
				GUISocialCombat2.objInstance.EndSocialCombat();
			}
		}
		if (strMusic != null)
		{
			AudioManager.am.SuggestMusic(strMusic, bForceMusic);
		}
		if (teleportRegIDTarget != null)
		{
			CondOwner condOwner9 = objUs;
			if (teleportRegIDTarget.Item2.ToLower().Contains("them"))
			{
				condOwner9 = objThem;
			}
			else if (teleportRegIDTarget.Item2.ToLower().Contains("3rd"))
			{
				condOwner9 = obj3rd;
			}
			string item = teleportRegIDTarget.Item1;
			if (!(item == "FERRY"))
			{
				if (item == "PLAYER")
				{
					CrewSim.objInstance.TeleportCO(condOwner9, CrewSim.coPlayer.ship.strRegID);
				}
				else
				{
					CrewSim.objInstance.TeleportCO(condOwner9, teleportRegIDTarget.Item1);
				}
			}
			else if (Ferry.ComingForCO(condOwner9.strID))
			{
				CrewSim.objInstance.TeleportCO(condOwner9, Ferry.DestForCO(condOwner9.strID), Ferry.TimeChangeForCO(condOwner9.strID));
			}
		}
		if (objUs != null)
		{
			MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(objUs.strID);
		}
		if (objThem != null)
		{
			MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(objThem.strID);
		}
		if (!string.IsNullOrEmpty(strSetPlot))
		{
			strPlot = strSetPlot;
		}
		if (bRecheckAllPlots)
		{
			PlotManager.AddPlotCheck((PlotManager.PlotTensionType)3);
		}
		else if (bRecheckThisPlot)
		{
			int nPlayerNoticed = PlotManager.nPlayerNoticed;
			PlotManager.nPlayerNoticed = 0;
			PlotManager.CheckPlot(strPlot, CrewSim.GetSelectedCrew(), (PlotManager.PlotTensionType)3);
			PlotManager.nPlayerNoticed = nPlayerNoticed;
		}
		if (!string.IsNullOrEmpty(strSetPlotObjective) && !string.IsNullOrEmpty(strPlot) && PlotManager.dictPlotsActive.TryGetValue(strPlot, out var value))
		{
			MonoSingleton<ObjectiveTracker>.Instance.UpdatePlotObjective(value, strSetPlotObjective);
		}
		if (aCustomInfos != null && aCustomInfos.Length != 0)
		{
			CrewSim.SetCustomInfos(aCustomInfos);
		}
		if (bHardCode)
		{
			_ = new string[2] { "SOCHireAllow", "SOCHire2BasicAllow" };
			if (Array.IndexOf(new string[1] { "SOCHireFire" }, strName) >= 0)
			{
				if (objUs.Company == null)
				{
					Debug.Log("Error: Null Company on " + objUs.ToString() + " with quitter: " + objThem.ToString());
				}
				else
				{
					objUs.Company.DismissMember(objThem.strID, objUs);
				}
			}
			if (Array.IndexOf(new string[2] { "SOCHireQuits", "SOCHireQuitsGlad" }, strName) >= 0)
			{
				if (objThem.Company == null)
				{
					Debug.Log("Error: Null company on " + objThem.ToString() + " with quitter: " + objUs.ToString());
				}
				else
				{
					objThem.Company.DismissMember(objUs.strID, objThem);
				}
				if (strName == "SOCHireQuits")
				{
					AudioManager.am.SuggestMusic("Loss", bForce: true);
				}
			}
			if (Array.IndexOf(new string[1] { "SOCHireQuitsMad" }, strName) >= 0)
			{
				if (objThem.Company == null)
				{
					Debug.Log("Error: Null company on " + objThem.ToString() + " with quitter: " + objUs.ToString());
				}
				else
				{
					objThem.Company.DismissMember(objUs.strID, objThem);
				}
				AudioManager.am.SuggestMusic("Loss", bForce: true);
			}
			if (Array.IndexOf(new string[2] { "PickupDragStart", "PickupDragStartNPCPledge" }, strName) >= 0 && !objUs.compSlots.SlotItem("drag", objThem))
			{
				Debug.LogWarning("Tried to drag " + objThem.strNameFriendly + " but had no drag slot!");
			}
			if (Array.IndexOf(new string[1] { "PickupDragStop" }, strName) >= 0)
			{
				if (objUs.compSlots.GetSlot("drag") != null && !objUs.HasCond("IsDragging"))
				{
					CondOwner condOwner10 = objUs.compSlots.UnSlotItem("drag");
					Vector3 zero = Vector3.zero;
					if (!(condOwner10 != null))
					{
						return;
					}
					zero = condOwner10.tf.position - objUs.tf.position;
					if (condOwner10.Item != null)
					{
						objUs.DropCO(condOwner10, bAllowLocked: false, objUs.ship, zero.x, zero.y);
					}
					else
					{
						condOwner10.tf.parent = objThem.tf.parent;
						condOwner10.ship = objThem.ship;
						condOwner10.currentRoom = objThem.currentRoom;
					}
				}
				else if (objThem.compSlots.GetSlot("drag") != null)
				{
					CondOwner condOwner11 = objThem.compSlots.UnSlotItem("drag");
					if (condOwner11 != null)
					{
						_ = condOwner11.tf.position - objThem.tf.position;
						if (condOwner11.Item != null)
						{
							objThem.DropCO(condOwner11, bAllowLocked: false, objThem.ship);
						}
						else
						{
							condOwner11.tf.parent = objThem.tf.parent;
							condOwner11.ship = objThem.ship;
							condOwner11.currentRoom = objThem.currentRoom;
						}
					}
				}
			}
			if (Array.IndexOf(new string[1] { "DropCorpse" }, strName) >= 0 && objUs.compSlots.GetSlot("drag") != null && objUs.HasCond("IsDragging"))
			{
				Ship ship4 = objUs.ship;
				CondOwner condOwner12 = objUs.compSlots.UnSlotItem("drag");
				if (ship4 != null)
				{
					ship4.AddCO(condOwner12, bTiles: true);
					condOwner12.currentRoom = ship4.GetRoomAtWorldCoords1(condOwner12.tf.position, bAllowDocked: true);
				}
			}
			if (Array.IndexOf(new string[1] { "JettisonCorpse" }, strName) >= 0)
			{
				CondOwner condOwner13 = objThem;
				condOwner13.RemoveFromCurrentHome();
				if (condOwner13 != null)
				{
					CrewSim.objInstance.ScheduleCODestruction(condOwner13);
				}
			}
			if (Array.IndexOf(new string[1] { "JettisonRobot" }, strName) >= 0)
			{
				CondOwner condOwner14 = objThem;
				condOwner14.RemoveFromCurrentHome();
				if (condOwner14 != null)
				{
					CrewSim.objInstance.ScheduleCODestruction(condOwner14);
				}
			}
			if (Array.IndexOf(new string[1] { "Strip" }, strName) >= 0)
			{
				List<CondOwner> cOs = objThem.compSlots.GetCOs();
				objThem.DropSlottedItems(cOs);
			}
			if (Array.IndexOf(new string[1] { "ShakeOff" }, strName) >= 0)
			{
				CondOwner objCO = objThem.compSlots.UnSlotItem("drag");
				objThem.DropCO(objCO, bAllowLocked: false);
			}
			if (strName.StartsWith("DeployStructure"))
			{
				Ship ship5 = objThem.RemoveFromCurrentHome(bForce: true);
				if (objThem != null)
				{
					CrewSim.objInstance.ScheduleCODestruction(objThem);
				}
				string factionBeacon = LootAddFactionsThem.GetAllLootNames().FirstOrDefault();
				CrewSim.system.DeploySignalBeacon(ship5.objSS, factionBeacon, objUs.strName, playerClaim: true);
			}
			if (Array.IndexOf(new string[1] { "ShowSocialCore" }, strName) >= 0)
			{
				GUIQuickBar.ShowSocialCore = true;
			}
			if (Array.IndexOf(new string[1] { "HideSocialCore" }, strName) >= 0)
			{
				GUIQuickBar.ShowSocialCore = false;
			}
			if (strName.Contains("PrisonEnd") && objUs != null)
			{
				objUs.ZeroCondAmount("Prone");
				objUs.ResetActiveWoundsToDefault();
				if (objUs.HasCond("Unconscious") && objUs.ship.ShipCO != null)
				{
					Interaction interaction2 = DataHandler.GetInteraction("SeekSleepSimpleWake");
					if (interaction2 != null)
					{
						interaction2.objUs = objUs;
						interaction2.objThem = objUs.ship.ShipCO;
						interaction2.ApplyChain();
					}
				}
				foreach (CondOwner value2 in DataHandler.mapCOs.Values)
				{
					if (!(value2 == null) && value2.IsHumanOrRobot && !(value2 == objUs))
					{
						value2.AICancelTargeted(objUs);
					}
				}
			}
		}
		if (!strAchievementUnlock.IsNullOrEmpty())
		{
			CrewSim.UnlockAchievement(strAchievementUnlock);
		}
	}

	private void OverflowAddCO(CondOwner objTarget, CondOwner coRemain)
	{
		if (coRemain == null || objTarget == null)
		{
			return;
		}
		if (objTarget.ship != null)
		{
			if (objTarget.ship.LoadState >= Ship.Loaded.Edit)
			{
				coRemain = objTarget.DropCO(coRemain, bAllowLocked: false);
				return;
			}
			CondOwner condOwner = null;
			foreach (CondOwner lotCO in objTarget.GetLotCOs(bSubItems: false))
			{
				if (lotCO.HasCond("IsLootSpawner") && lotCO.GetGPMInfo("Panel A", "strType") == "Lot Loot")
				{
					condOwner = lotCO;
					condOwner.AddLotCO(coRemain);
					Debug.Log("Adding Overflow CO: " + coRemain.strID + " to " + condOwner.strID);
					break;
				}
			}
			if (condOwner == null)
			{
				condOwner = DataHandler.GetCondOwner("SysLootSpawnerLot");
				condOwner.ApplyGPMChanges(new string[7] { "Panel A,strType,Lot Loot", "Panel A,strRange,2", "Panel A,strCount,1", "Panel A,strLoot,aLot", "Panel A,strNew,true", "Panel A,strDamaged,true", "Panel A,strDerelict,true" });
				condOwner.AddLotCO(coRemain);
				Debug.Log("Adding Overflow CO: " + coRemain.strID + " to " + condOwner.strID);
				condOwner.Item.ResetTransforms(objTarget.tf.position.x, objTarget.tf.position.y);
				objTarget.AddLotCO(condOwner);
			}
		}
		else
		{
			coRemain.RemoveFromCurrentHome();
			coRemain.Destroy();
		}
	}

	private void LootAddFactions(List<string> aFactions, CondOwner target)
	{
		if (aFactions == null || target == null)
		{
			return;
		}
		foreach (string aFaction in aFactions)
		{
			if (aFaction.IndexOf("-") == 0)
			{
				target.RemoveFaction(CrewSim.system.GetFaction(aFaction.Substring(1)));
			}
			else
			{
				target.AddFaction(CrewSim.system.GetFaction(aFaction));
			}
		}
	}

	private void UpdateStakes(Relationship relUs, Relationship relThem)
	{
		if (strLootContextUs == "Default" || strLootContextThem == "Default")
		{
			if ((objUs == CrewSim.coPlayer || objThem == CrewSim.coPlayer) && objUs.socUs != null)
			{
				GUISocialCombat2.UpdateContext(this);
			}
			if (relUs != null && strLootContextUs != null)
			{
				relUs.strContext = strLootContextUs;
			}
			if (relThem != null && strLootContextThem != null)
			{
				relThem.strContext = strLootContextThem;
			}
		}
		else
		{
			if (relUs != null && strLootContextUs != null)
			{
				relUs.strContext = strLootContextUs;
			}
			if (relThem != null && strLootContextThem != null)
			{
				relThem.strContext = strLootContextThem;
			}
			if ((objUs == CrewSim.coPlayer || objThem == CrewSim.coPlayer) && objUs.socUs != null)
			{
				GUISocialCombat2.UpdateContext(this);
			}
		}
	}

	private bool ChangeRelationship(string strLootRELChange, CondOwner coRelative, CondOwner coUs, List<string> aLog = null, bool bDoReciprocal = false)
	{
		if (coRelative == null || coUs == null || coUs.pspec == null || coUs.socUs == null || coRelative.pspec == null || coRelative.socUs == null)
		{
			return false;
		}
		bool result = false;
		List<string> lootNames = DataHandler.GetLoot(strLootRELChange).GetLootNames();
		if (lootNames.Count > 0)
		{
			foreach (string item2 in lootNames)
			{
				if (item2.IndexOf("-") == 0)
				{
					result = true;
					coUs.socUs.RemovePerson(coRelative.pspec, new List<string> { item2.Substring(1) });
					if (bDoReciprocal)
					{
						string reciprocalREL = Relationship.GetReciprocalREL(item2.Substring(1));
						coRelative.socUs.RemovePerson(coUs.pspec, new List<string> { reciprocalREL });
					}
					continue;
				}
				Condition cond = DataHandler.GetCond(item2);
				if (cond == null)
				{
					continue;
				}
				coUs.socUs.AddPerson(new Relationship(coRelative.pspec, new List<string> { item2 }, new List<string> { "Became " + cond.strNameFriendly + " during: " + strTitle }));
				result = true;
				if (aLog != null)
				{
					string item = coRelative.strName + " becomes a " + cond.strNameFriendly + " to " + coUs.strName + ".";
					aLog.Add(item);
				}
				LogSocial(coRelative.strName, item2, strTitle);
				if (bDoReciprocal)
				{
					string reciprocalREL2 = Relationship.GetReciprocalREL(item2);
					cond = DataHandler.GetCond(reciprocalREL2);
					if (cond != null)
					{
						coRelative.socUs.AddPerson(new Relationship(coUs.pspec, new List<string> { reciprocalREL2 }, new List<string> { "Became " + cond.strNameFriendly + " during: " + strTitle }));
					}
				}
			}
		}
		return result;
	}

	public void ApplyChain(List<string> aLog = null)
	{
		if (!(objUs == null) && !(objThem == null))
		{
			ApplyLogging(objUs.strName, bTraitSuffix: true);
			ApplyEffects(aLog);
			GetReply()?.ApplyChain();
		}
	}

	public void ApplyLogging(string strOwner, bool bTraitSuffix)
	{
		if (nLogging == Logging.NONE || bLogged)
		{
			return;
		}
		string strMsg = GrammarUtils.GenerateDescription(this, log: true);
		List<CondOwner> list = new List<CondOwner>();
		switch (nLogging)
		{
		case Logging.SHIP:
			if (objUs.ship != null)
			{
				list.AddRange(objUs.ship.GetPeople(bAllowDocked: true));
			}
			break;
		case Logging.GROUP:
			list.Add(objUs);
			if (strThemType == TARGET_OTHER)
			{
				list.Add(objThem);
			}
			break;
		case Logging.ROOM:
			if (objUs.currentRoom != null)
			{
				list.AddRange(objUs.ship.GetPeopleInRoom(objUs.currentRoom));
			}
			if (!list.Contains(objUs))
			{
				list.Add(objUs);
			}
			if (!list.Contains(objThem))
			{
				list.Add(objThem);
			}
			break;
		}
		foreach (CondOwner item in list)
		{
			item.LogMessage(strMsg, strColor, strOwner);
		}
		bLogged = true;
	}

	private void ApplyLootCT(Loot LootCTs, Relationship relUs, CondOwner coUs, CondOwner coThem, float fCoeff)
	{
		if (coUs == null)
		{
			return;
		}
		Dictionary<string, double> dictionary = null;
		if (LootCTs != null && LootCTs.strName != "Blank")
		{
			List<CondTrigger> cTLoot = LootCTs.GetCTLoot(null);
			if (relUs != null)
			{
				dictionary = new Dictionary<string, double>();
			}
			foreach (CondTrigger item in cTLoot)
			{
				if (item == null || !item.Triggered(coUs))
				{
					continue;
				}
				item.ApplyChanceID(bAdd: true, coUs, fCoeff);
				if (!bNoRemember)
				{
					coUs.AddRememberScore(item.strCondName, item.fCount * fCoeff);
				}
				if (dictionary != null)
				{
					if (!dictionary.ContainsKey(item.strCondName))
					{
						dictionary[item.strCondName] = item.fCount * fCoeff;
					}
					else
					{
						dictionary[item.strCondName] += item.fCount * fCoeff;
					}
				}
			}
		}
		if (coUs == objUs && !bHumanOnly && !bNoRemember)
		{
			coUs.aRememberIAs.Insert(0, strName);
		}
		coUs.RememberEffects2(coThem);
		if (coUs == objUs)
		{
			coUs.RememberLess();
		}
		relUs?.StoreIAConds(coUs, dictionary, coThem);
	}

	private void ApplyLootConds(Loot LootConds, Relationship relUs, CondOwner coUs, CondOwner coThem, float fCoeff)
	{
		if (coUs == null)
		{
			return;
		}
		Dictionary<string, double> dictionary = null;
		if (LootConds != null && LootConds.strName != "Blank")
		{
			Dictionary<string, double> condLoot = LootConds.GetCondLoot(fCoeff, null);
			if (relUs != null)
			{
				dictionary = new Dictionary<string, double>();
			}
			foreach (KeyValuePair<string, double> item in condLoot)
			{
				coUs.AddCondAmount(item.Key, item.Value);
				coUs.AddRememberScore(item.Key, item.Value);
				if (dictionary != null)
				{
					if (!dictionary.ContainsKey(item.Key))
					{
						dictionary[item.Key] = item.Value;
					}
					else
					{
						dictionary[item.Key] += item.Value;
					}
				}
			}
		}
		if (coUs == objUs && !bHumanOnly && !bNoRemember)
		{
			coUs.aRememberIAs.Insert(0, strName);
		}
		coUs.RememberEffects2(coThem);
		if (coUs == objUs)
		{
			coUs.RememberLess();
		}
		relUs?.StoreIAConds(coUs, dictionary, coThem);
	}

	public string GetTextLinked(CondOwner coHighlight = null, string strOpen = null, string strClose = null)
	{
		GrammarUtils.highlight = coHighlight;
		string text = GrammarUtils.GetInflectedString(strDesc, this);
		if (aSocialPrereqsFound != null)
		{
			for (int i = 0; i < aSocialPrereqsFound.Length; i++)
			{
				text = text.Replace("[prereq" + i + "]", aSocialPrereqsFound[i]);
			}
		}
		return text;
	}

	public string GetDataPayload()
	{
		Loot loot = LootCTsUs;
		CondOwner condOwner = objUs;
		if (LootCTsUs != null && LootCTsUs.strName != "Blank" && (LootCTsUs.strType == "trigger" || LootCTsUs.strType == "data"))
		{
			loot = LootCTsUs;
			condOwner = objUs;
		}
		else if (LootCTsThem != null && LootCTsThem.strName != "Blank" && (LootCTsThem.strType == "trigger" || LootCTsThem.strType == "data"))
		{
			loot = LootCTsThem;
			condOwner = objThem;
		}
		string text = "";
		if (loot == null || loot.strName == "Blank" || condOwner == null || condOwner.ship == null)
		{
			return text;
		}
		if (loot.strType == "trigger")
		{
			List<string> lootNames = loot.GetLootNames();
			if (lootNames != null && lootNames.Count >= 1)
			{
				CondTrigger condTrigger = DataHandler.GetCondTrigger(lootNames.First());
				if (condTrigger.IsBlank())
				{
					return text;
				}
				List<CondOwner> cOs = condOwner.ship.GetCOs(condTrigger, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
				for (int i = 0; i < cOs.Count; i++)
				{
					CondOwner condOwner2 = cOs[i];
					text += condOwner2.FriendlyName;
					if (i != cOs.Count - 1)
					{
						text += ", ";
					}
				}
			}
			return text;
		}
		if (loot.strType == "data")
		{
			try
			{
				foreach (string lootName in loot.GetLootNames())
				{
					if (string.IsNullOrEmpty(lootName) || lootName == "Blank")
					{
						continue;
					}
					if (lootName.FirstOrDefault() == '+')
					{
						text += lootName.Replace("+", "");
						continue;
					}
					PropertyInfo property = typeof(Ship).GetProperty(lootName);
					if (property != null)
					{
						object value = property.GetValue(condOwner.ship, null);
						if (value != null)
						{
							string text2 = value.ToString();
							if (double.TryParse(text2, out var _))
							{
								text2 = text2.Split('.').FirstOrDefault();
							}
							text += text2;
						}
						continue;
					}
					if (typeof(Ship).GetField(lootName) != null)
					{
						FieldInfo field = typeof(Ship).GetField(lootName);
						if (!(field != null))
						{
							continue;
						}
						object value2 = field.GetValue(condOwner.ship);
						if (value2 != null)
						{
							string text3 = value2.ToString();
							if (double.TryParse(text3, out var _))
							{
								text3 = text3.Split('.').FirstOrDefault();
							}
							text += text3;
						}
						continue;
					}
					MethodInfo method = typeof(Ship).GetMethod(lootName);
					if (!(method != null))
					{
						continue;
					}
					object obj = method.Invoke(condOwner.ship, null);
					if (obj != null)
					{
						string text4 = obj.ToString();
						if (double.TryParse(text4, out var _))
						{
							text4 = text4.Split('.').FirstOrDefault();
						}
						text += text4;
					}
				}
			}
			catch (Exception)
			{
				Debug.LogWarning("Could not parse Data Loot from interaction");
			}
		}
		return text;
	}

	public string GetTextRate()
	{
		CalcRate();
		return " " + STR_TASK_RATE_START + (fCTThemModifierUs * fCTThemModifierTools * (1f - fCTThemModifierPenalty)).ToString("n1") + STR_TASK_RATE_END;
	}

	private void CalcRate()
	{
		if (strActionGroup != "Work" || bCTThemModifierCalculated)
		{
			return;
		}
		fCTThemModifierUs = 1f;
		if (strCTThemMultCondUs != null)
		{
			fCTThemModifierUs = (float)objUs.GetCondAmount(strCTThemMultCondUs);
		}
		fCTThemModifierUs = Mathf.Clamp(fCTThemModifierUs, 1f, 10f);
		fCTThemModifierTools = 1f;
		if (strCTThemMultCondTools != null)
		{
			fCTThemModifierTools = 0f;
			if (aLootItemUseContract != null)
			{
				foreach (CondOwner item in aLootItemUseContract)
				{
					if (item != null && strCTThemMultCondTools != null)
					{
						fCTThemModifierTools += (float)item.GetCondAmount(strCTThemMultCondTools);
					}
				}
			}
		}
		fCTThemModifierPenalty = (float)objUs.GetCondAmount("StatWorkSpeedPenalty");
		if ((double)fCTThemModifierPenalty > 0.99)
		{
			fCTThemModifierPenalty = 0.99f;
		}
		bCTThemModifierCalculated = true;
	}

	public int GetAnim(CondOwner co = null)
	{
		int result = dictAnims["Idle"];
		if (co != null && co.gameObject.activeInHierarchy)
		{
			result = co.GetAnimState();
		}
		if (strAnim != null && dictAnims.ContainsKey(strAnim))
		{
			result = dictAnims[strAnim];
		}
		else if (co != null && co.strIdleAnim != null && dictAnims.ContainsKey(co.strIdleAnim))
		{
			result = dictAnims[co.strIdleAnim];
		}
		return result;
	}

	public void PlayAudio()
	{
		if (bAudioPlayed)
		{
			return;
		}
		if (LootAudioUs != null && LootAudioUs.strName != "Blank")
		{
			AudioEmitter component = objUs.GetComponent<AudioEmitter>();
			if (component != null)
			{
				component.StartOther(LootAudioUs.GetLootNameSingle());
			}
		}
		if (LootAudioThem != null && LootAudioThem.strName != "Blank")
		{
			AudioEmitter component2 = objThem.GetComponent<AudioEmitter>();
			if (component2 != null)
			{
				component2.StartOther(LootAudioThem.GetLootNameSingle());
			}
		}
		bAudioPlayed = true;
	}

	public void SetVFX()
	{
		if (bVFXSpawned)
		{
			return;
		}
		if (LootVFXUs != null && LootVFXUs.strName != "Blank")
		{
			GameObject vFX = DataHandler.GetVFX(LootVFXUs.GetLootNameSingle());
			if (vFX != null)
			{
				vFX = UnityEngine.Object.Instantiate(vFX, objUs.tf);
			}
		}
		if (LootVFXThem != null && LootVFXThem.strName != "Blank")
		{
			GameObject vFX2 = DataHandler.GetVFX(LootVFXThem.GetLootNameSingle());
			if (vFX2 != null)
			{
				vFX2 = UnityEngine.Object.Instantiate(vFX2, objThem.tf);
			}
		}
		bVFXSpawned = true;
	}

	public void Teleport(Pathfinder pfUs, bool isCancelIa = false)
	{
		Vector3 vector = objThem.GetPos(strTeleport);
		if (isCancelIa)
		{
			float num = Vector3.Distance(vector, objUs.tf.position);
			float num2 = 1.41f;
			float num3 = num2 * fTargetPointRange;
			if (num > num3 && num > num2)
			{
				return;
			}
		}
		vector.z = objUs.tf.position.z;
		objUs.tf.position = vector;
		if (pfUs != null)
		{
			pfUs.ReacquireTILCurrent();
			pfUs.tilDest = null;
			pfUs.UpdateManual();
		}
		vector = objThem.tf.rotation.eulerAngles;
		vector.z += fRotation;
		objUs.tf.eulerAngles = vector;
	}

	public Interaction Destroy()
	{
		DataHandler.ReleaseTrackedInteraction(this);
		strName = null;
		strTitle = null;
		strDesc = null;
		strTargetPoint = null;
		strAnim = null;
		strAnimTrig = null;
		strBubble = null;
		strColor = null;
		strDuty = null;
		strRaiseUI = null;
		strRaiseUIThem = null;
		strSubUI = null;
		strLedgerDef = null;
		strLootContextUs = null;
		strLootContextThem = null;
		strImage = null;
		strMapIcon = null;
		aInverse = null;
		PSpecTestThem = null;
		PSpecTest3rd = null;
		strLootItmAddUs = null;
		strLootItmAddThem = null;
		strLootCTsRemoveUs = null;
		strLootItmRemoveThem = null;
		strLootCTsGive = null;
		strLootCTsUse = null;
		strLootCTsLacks = null;
		strLootCTsTake = null;
		strTeleport = null;
		teleportRegIDTarget = null;
		if (aLootItemGiveContract != null)
		{
			aLootItemGiveContract.Clear();
			aLootItemGiveContract = null;
		}
		if (aLootItemUseContract != null)
		{
			aLootItemUseContract.Clear();
			aLootItemUseContract = null;
		}
		if (aLootItemRemoveContract != null)
		{
			aLootItemRemoveContract.Clear();
			aLootItemRemoveContract = null;
		}
		if (aLootItemTakeContract != null)
		{
			aLootItemTakeContract.Clear();
			aLootItemTakeContract = null;
		}
		if (aSeekItemsForContract != null)
		{
			aSeekItemsForContract.Clear();
			aSeekItemsForContract = null;
		}
		if (aDependents != null)
		{
			aDependents.Clear();
			aDependents = null;
		}
		objUs = null;
		objThem = null;
		return null;
	}

	public JsonInteractionSave GetJSONSave()
	{
		if (objThem == null && string.IsNullOrEmpty(strThemID))
		{
			return null;
		}
		JsonInteractionSave jsonInteractionSave = new JsonInteractionSave(this);
		if (objThem != null && objThem.HasCond("IsTile"))
		{
			List<CondOwner> list = new List<CondOwner>();
			CondTrigger ct = new CondTrigger("IsFloor", new string[1] { "IsFloorGrate" }, null, null, null);
			objThem.ship.GetCOsAtWorldCoords1(objThem.tf.position, ct, bAllowDocked: true, bAllowLocked: true, list);
			if (list.Count > 0)
			{
				jsonInteractionSave.objThem = list[0].strID;
			}
			else
			{
				jsonInteractionSave.objThem = objUs.strID;
			}
			list.Clear();
			list = null;
		}
		else
		{
			jsonInteractionSave.objThem = strThemID;
		}
		jsonInteractionSave.obj3rd = str3rdID;
		List<string> list2 = new List<string>();
		if (aLootItemGiveContract != null)
		{
			foreach (CondOwner item2 in aLootItemGiveContract)
			{
				list2.Add(item2.strID);
			}
			jsonInteractionSave.aLootItemGiveContract = list2.ToArray();
			list2.Clear();
		}
		if (aLootItemRemoveContract != null)
		{
			foreach (CondOwner item3 in aLootItemRemoveContract)
			{
				list2.Add(item3.strID);
			}
			jsonInteractionSave.aLootItemRemoveContract = list2.ToArray();
			list2.Clear();
		}
		if (aLootItemTakeContract != null)
		{
			foreach (CondOwner item4 in aLootItemTakeContract)
			{
				list2.Add(item4.strID);
			}
			jsonInteractionSave.aLootItemTakeContract = list2.ToArray();
			list2.Clear();
		}
		if (aSeekItemsForContract != null)
		{
			foreach (CondOwner item5 in aSeekItemsForContract)
			{
				list2.Add(item5.strID);
			}
			jsonInteractionSave.aSeekItemsForContract = list2.ToArray();
			list2.Clear();
		}
		if (aDependents != null)
		{
			foreach (string aDependent in aDependents)
			{
				list2.Add(aDependent);
			}
			jsonInteractionSave.aDependents = list2.ToArray();
			list2.Clear();
		}
		if (aSocialPrereqsFound != null)
		{
			string[] array = aSocialPrereqsFound;
			foreach (string item in array)
			{
				list2.Add(item);
			}
			jsonInteractionSave.aSocialPrereqsFound = list2.ToArray();
			list2.Clear();
		}
		list2.Clear();
		return jsonInteractionSave;
	}

	public override string ToString()
	{
		if (strName != null)
		{
			string text = strName + ": ";
			text = ((!(objUs != null)) ? (text + "null") : (text + objUs.strName));
			text += "->";
			if (objThem != null)
			{
				return text + objThem.strName;
			}
			return text + "null";
		}
		return "";
	}

	public string FailReasons(bool bUsThem, bool bItems, bool bDebug)
	{
		StringBuilder stringBuilder = new StringBuilder();
		if (mapFails == null || mapFails["main"] == null || mapFails["main"].Count == 0)
		{
			return "";
		}
		if (mapFails.ContainsKey("main"))
		{
			foreach (string item in mapFails["main"])
			{
				stringBuilder.Append(item);
				stringBuilder.Append(" ");
			}
		}
		if (bUsThem)
		{
			if (mapFails.ContainsKey("us"))
			{
				foreach (string item2 in mapFails["us"])
				{
					stringBuilder.Append(" We are ");
					stringBuilder.Append(item2);
				}
			}
			if (mapFails.ContainsKey("them"))
			{
				foreach (string item3 in mapFails["them"])
				{
					stringBuilder.Append(" Target is ");
					stringBuilder.Append(item3);
				}
			}
			if (mapFails.ContainsKey("room"))
			{
				foreach (string item4 in mapFails["room"])
				{
					stringBuilder.Append(" Room is ");
					stringBuilder.Append(item4);
				}
			}
			if (mapFails.ContainsKey("3rd"))
			{
				foreach (string item5 in mapFails["3rd"])
				{
					stringBuilder.Append(" 3rd party is ");
					stringBuilder.Append(item5);
				}
			}
		}
		if (bItems)
		{
			if (mapFails.ContainsKey("items"))
			{
				List<string> list = new List<string>();
				List<int> list2 = new List<int>();
				foreach (string item6 in mapFails["items"])
				{
					int num = list.IndexOf(item6);
					if (num < 0)
					{
						list.Add(item6);
						list2.Add(1);
					}
					else
					{
						list2[num]++;
					}
				}
				for (int i = 0; i < list.Count; i++)
				{
					int num2 = list2[i];
					string value = list[i];
					if (num2 > 1)
					{
						stringBuilder.Append(" Missing item x");
						stringBuilder.Append(num2);
						stringBuilder.Append(": ");
						stringBuilder.Append(value);
					}
					else
					{
						stringBuilder.Append(" Missing item: ");
						stringBuilder.Append(value);
					}
				}
			}
			if (mapFails.ContainsKey("specs"))
			{
				List<string> list3 = new List<string>();
				List<int> list4 = new List<int>();
				foreach (string item7 in mapFails["specs"])
				{
					int num3 = list3.IndexOf(item7);
					if (num3 < 0)
					{
						list3.Add(item7);
						list4.Add(1);
					}
					else
					{
						list4[num3]++;
					}
				}
				for (int j = 0; j < list3.Count; j++)
				{
					int num4 = list4[j];
					string value2 = list3[j];
					if (num4 > 1)
					{
						stringBuilder.Append(" Item present but, ");
						stringBuilder.Append(num4);
						stringBuilder.Append(" x Not Enough: ");
						stringBuilder.Append(value2);
					}
					else
					{
						stringBuilder.Append(" Item present but, Not Enough: ");
						stringBuilder.Append(value2);
					}
				}
			}
		}
		if (bDebug)
		{
			if (mapFails.ContainsKey("debugus"))
			{
				foreach (string item8 in mapFails["debugus"])
				{
					stringBuilder.AppendLine();
					stringBuilder.Append(" - DEBUG US: ");
					stringBuilder.Append(item8);
				}
			}
			if (mapFails.ContainsKey("debugthem"))
			{
				foreach (string item9 in mapFails["debugthem"])
				{
					stringBuilder.AppendLine();
					stringBuilder.Append(" - DEBUG THEM: ");
					stringBuilder.Append(item9);
				}
			}
		}
		return stringBuilder.ToString();
	}
}
