using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Core.AbstractionLayer.Interfaces;
using Ostranauts;
using Ostranauts.COCommands;
using Ostranauts.Components;
using Ostranauts.Condowner;
using Ostranauts.Core;
using Ostranauts.Core.Models;
using Ostranauts.Core.Tutorials;
using Ostranauts.Events;
using Ostranauts.Inventory;
using Ostranauts.ShipGUIs;
using Ostranauts.Ships;
using Ostranauts.TargetVisualization;
using Ostranauts.Tools.ExtensionMethods;
using Ostranauts.Trading;
using Ostranauts.UI.MegaToolTip;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class CondOwner : MonoBehaviour, ICondOwner
{
	public static OnUpdateWaitingRepliesEvent UpdateWaitingReplies = new OnUpdateWaitingRepliesEvent();

	public OnUpdateAutoEmergencyEvent UpdateAutoEmergency = new OnUpdateAutoEmergencyEvent();

	[SerializeField]
	private string _strID;

	public Transform tf;

	public string strName;

	public string strNameFriendly;

	public string strNameShort;

	public string strDesc;

	public string strCODef;

	public string strItemDef;

	private Item _itemComponentReference;

	private bool bTriedGettingItemRef;

	private Pathfinder _pfComponentReference;

	private bool bTriedGettingPfRef;

	private Crew _crewComponentReference;

	private bool bTriedGettingCrewRef;

	private GasContainer _gasContainerComponentReference;

	public static string STR_AI_REL_SWITCH = null;

	public static string STR_AI_REL_SWITCH_END = null;

	public static string STR_AI_REL_SWITCH_NOBODY = null;

	public string strPortraitImg;

	public Dictionary<string, string> mapInfo;

	public Vector3 vTextOffset;

	public Vector3 vBblOffset;

	private Ship _objShip;

	private HashSet<string> aMyShips;

	private List<string> aFactions;

	public List<string> aRELConds;

	public CondOwner objCOParent;

	public Condition objCondID;

	public PersonSpec pspec;

	public string strPersistentCT;

	public string strPersistentCO;

	public string strPlaceholderInstallReq;

	public string strPlaceholderInstallFinish;

	public string strSourceCO;

	public string strSourceInteract;

	public string strIdleAnim;

	public string strWalkAnim;

	public Container objContainer;

	public PairXY pairInventoryXY;

	public Dictionary<string, Condition> mapConds;

	public Dictionary<string, CondHistory> mapIAHist;

	public Dictionary<string, Vector2> mapPoints;

	public List<string> aInteractions;

	private bool bCanPatch;

	private bool bCanRepair;

	private bool bCanUndamage;

	public Dictionary<string, Dictionary<string, string>> mapGUIPropMaps;

	public Dictionary<string, IGUIHarness> mapGUIRefs;

	public Dictionary<string, JsonSlotEffects> mapSlotEffects;

	private Dictionary<string, JsonChargeProfile> mapChargeProfiles;

	private Dictionary<string, CondRule> mapCondRules;

	public Dictionary<string, string> mapAltItemDefs;

	public Dictionary<string, string> mapAltSlotImgs;

	public Dictionary<int, List<Pledge2>> dictPledges;

	public Dictionary<string, Vector3> dictSlotsLayout;

	public List<JsonLogMessage> aMessages;

	public List<string> aCondZeroes;

	public CondOwner coStackHead;

	public TrackingCollection<CondOwner> aStack;

	public TrackingCollection<CondOwner> aLot;

	private Slots _compSlots;

	public TMP_Text txtStack;

	public JsonCondOwnerSave jCOS;

	public bool bAlive;

	public bool bIgnoreKill;

	public bool bSlotLocked;

	public Slot slotNow;

	private JsonCompany objCompany;

	public int nStackLimit = 1;

	private int nRecentlyTriedMax = 6;

	public JsonShift jsShiftLast;

	private MeshRenderer mr;

	private BoxCollider mc;

	public bool bFreezeConds;

	public bool bFreezeCondRules;

	public FaceAnim2 faceRef;

	private List<JsonTicker> aTickers;

	private List<IManUpdater> aMUs;

	private List<IManUpdater> aMUDels;

	private bool bSaveMessageLog;

	public bool bLogConds = true;

	public Room currentRoom;

	public bool bDestroyed;

	private string strLastSocial;

	private double fLastICOUpdate;

	private double fLastCleanup;

	private float fCondTick = 1f;

	public List<Interaction> aQueue;

	public List<ReplyThread> aReplies;

	public List<string> aAttackIAs;

	private List<Priority> aPriorities;

	private HashSet<string> hashCondsImportant;

	private Dictionary<string, double> dictRecentlyTried;

	public List<string> aRememberIAs;

	public Dictionary<string, double> dictRememberScores;

	private float fRememberDecay = 0.5f;

	private GameObject goBracket;

	private Animator anim;

	private Powered pwr;

	private Wound wound;

	private Electrical elec;

	public Social socUs;

	private List<IManUpdater> aManUpdates;

	private List<Condition> aCondsTimed;

	private List<Condition> aCondsTemp;

	private List<AutoTask> aATsRepair;

	private List<AutoTask> aATsRestore;

	private List<AutoTask> aATsPatch;

	private static int nAnimStateID = -1;

	private static Loot _FreeWillLoot;

	private static Loot _FreeWillPenalty;

	public const string STR_US = "[us]";

	public const string STR_US_SPACE = "[us] ";

	public const string STR_THEM = "[them]";

	public const string STR_3RD = "[3rd]";

	private static double[] aDamageThresholds = new double[3] { 0.95, 0.66, 0.33 };

	public List<string> aDestructableConds;

	private static CondTrigger _ctCanAIOrder;

	private static CondTrigger _ctCanWalk;

	private static CondTrigger _ctIsProneAwake;

	private static CondTrigger _ctRestoreItem;

	private static CondTrigger _ctSuffocatingManWalk;

	private static JsonPersonSpec _jpsRelReportFactionNeg;

	private static List<string> _aAutoPauseIgnore;

	public bool debugStop;

	public const bool bDebugValidate = false;

	public const bool bDebugAIRandomChoices = false;

	private static string[] aAIRandomAvoid = new string[4] { "DropItem", "DropItemStack", "PickupItem", "PickupItemStack" };

	public double fMSRedamageAmount;

	public Dictionary<string, string[]> dictAddCondEvents = new Dictionary<string, string[]>();

	public Dictionary<string, string[]> dictRemoveCondEvents = new Dictionary<string, string[]>();

	private ProgressBar progressBar;

	private Condition _statDamageMax;

	private Condition _statDamage;

	private float _lastDamageUpdate;

	private static GameObject selectionBracket;

	public static int nEndTurnsThisFrame = 0;

	public COWorkHistoryDTO RecentWorkHistory;

	public string _emergencyReason = "";

	private Dictionary<string, int> temp_counterDict = new Dictionary<string, int>();

	private List<JsonTicker> temp_aTickersAside = new List<JsonTicker>();

	private JsonTicker temp_jt;

	private CondOwnerVisitorAddToHashSet temp_vHash = new CondOwnerVisitorAddToHashSet();

	private CondOwnerVisitorEarlyOut temp_vHash1 = new CondOwnerVisitorEarlyOut();

	private CondOwnerVisitor temp_vWrap;

	private bool _fieldsInitialized;

	[NonSerialized]
	public bool GasChanged;

	private static CondTrigger _ctPlayerCrew;

	public Action<Interaction> OnQueueInteraction;

	private StringBuilder messageLogSB;

	private static List<Slot> _emptySlotsResult;

	private bool? _isRobot;

	private bool? _isHumanOrRobot;

	private bool _hasSubCOs;

	public Item Item
	{
		get
		{
			if (!bTriedGettingItemRef && _itemComponentReference == null)
			{
				_itemComponentReference = GetComponent<Item>();
				bTriedGettingItemRef = true;
			}
			return _itemComponentReference;
		}
	}

	public Pathfinder Pathfinder
	{
		get
		{
			if (!bTriedGettingPfRef && _pfComponentReference == null)
			{
				_pfComponentReference = GetComponent<Pathfinder>();
				bTriedGettingPfRef = true;
			}
			return _pfComponentReference;
		}
	}

	public Crew Crew
	{
		get
		{
			if (!bTriedGettingCrewRef && _crewComponentReference == null)
			{
				_crewComponentReference = GetComponent<Crew>();
				bTriedGettingCrewRef = true;
			}
			return _crewComponentReference;
		}
	}

	public GasContainer GasContainer
	{
		get
		{
			if (_gasContainerComponentReference == null)
			{
				_gasContainerComponentReference = GetComponent<GasContainer>();
			}
			return _gasContainerComponentReference;
		}
	}

	public string strType { get; private set; }

	public Powered Pwr => pwr;

	public Electrical Electrical => elec;

	public Vector2 tfVector2Position => tf.position.ToVector2();

	private static CondTrigger CTPlayerCrew
	{
		get
		{
			if (_ctPlayerCrew == null)
			{
				_ctPlayerCrew = DataHandler.GetCondTrigger("TIsPlayerCrew");
			}
			return _ctPlayerCrew;
		}
	}

	public double fNextTickerSecs
	{
		get
		{
			if (aTickers == null)
			{
				return 0.0;
			}
			if (aTickers.Count > 0)
			{
				return aTickers[0].fTimeLeft * 3600.0;
			}
			return 0.0;
		}
	}

	public bool AlwaysLoad
	{
		get
		{
			if (IsHumanOrRobot)
			{
				return true;
			}
			if (objCOParent != null)
			{
				if (objCOParent.IsHumanOrRobot)
				{
					return true;
				}
				return objCOParent.AlwaysLoad;
			}
			if (coStackHead != null)
			{
				return coStackHead.AlwaysLoad;
			}
			return false;
		}
	}

	public int LotCount
	{
		get
		{
			if (aLot != null)
			{
				return aLot.Count;
			}
			return 0;
		}
	}

	public int QueueCount
	{
		get
		{
			if (aQueue != null)
			{
				return aQueue.Count;
			}
			return 0;
		}
	}

	public Ship ship
	{
		get
		{
			return _objShip;
		}
		set
		{
			_objShip = value;
			UpdateGravity();
		}
	}

	public bool Kill
	{
		get
		{
			return bAlive;
		}
		set
		{
			if (bIgnoreKill)
			{
				return;
			}
			bAlive = !value;
			string key = "Dead";
			if (bAlive)
			{
				ZeroCondAmount("IsDead");
				key = "Idle";
			}
			else
			{
				AddCondAmount("IsDead", 1.0);
				while (aQueue != null && aQueue.Count > 0)
				{
					ClearInteraction(aQueue[0]);
				}
			}
			strIdleAnim = key;
			SetAnimState(Interaction.dictAnims[key]);
			if (!bAlive)
			{
				if (HasCond("IsPlayer"))
				{
					CanvasManager.instance.GameOver(this);
				}
				else if (CrewSim.GetSelectedCrew() == this)
				{
					CrewSim.objInstance.CycleCrew();
				}
				if (HasCond("IsHuman"))
				{
					Debug.Log("#NPC# " + strID + " died.");
					if (HasCond("IsPlayerCrew") && !bFreezeCondRules)
					{
						if (ship != null && ship.LoadState >= Ship.Loaded.Edit)
						{
							List<CondOwner> list = new List<CondOwner>();
							list.AddRange(ship.GetPeople(bAllowDocked: true));
							foreach (CondOwner item in list)
							{
								item.LogMessage(FriendlyName + DataHandler.GetString("CREW_DEAD"), "Bad", strID);
							}
							AudioManager.am.SuggestMusic("Loss", bForce: true);
						}
						if (Company != null)
						{
							Company.DismissMember(strID, CrewSim.coPlayer);
						}
					}
					AIShipManager.ValidateCrew(this);
				}
				if (compSlots != null && ship != null && ship.LoadState > Ship.Loaded.Shallow)
				{
					List<CondOwner> cOs = compSlots.GetCOs("heldL");
					cOs.AddRange(compSlots.GetCOs("heldR"));
					cOs.AddRange(compSlots.GetCOs("drag"));
					DropSlottedItems(cOs);
				}
				AddCondAmount("DisallowPaperDoll", 1.0);
				if (_pfComponentReference != null)
				{
					_pfComponentReference.HideFootprints();
					_pfComponentReference.enabled = false;
				}
				BodyTemp component = GetComponent<BodyTemp>();
				if (component != null)
				{
					component.enabled = false;
				}
				Heater component2 = GetComponent<Heater>();
				if (component2 != null)
				{
					component2.enabled = false;
				}
				GasPump component3 = GetComponent<GasPump>();
				if (component3 != null)
				{
					component3.enabled = false;
				}
			}
			else
			{
				ZeroCondAmount("DisallowPaperDoll");
				if (_pfComponentReference != null)
				{
					_pfComponentReference.enabled = true;
				}
				BodyTemp component4 = GetComponent<BodyTemp>();
				if (component4 != null)
				{
					component4.enabled = true;
				}
				Heater component5 = GetComponent<Heater>();
				if (component5 != null)
				{
					component5.enabled = true;
				}
				GasPump component6 = GetComponent<GasPump>();
				if (component6 != null)
				{
					component6.enabled = true;
				}
			}
		}
	}

	public bool bBusy
	{
		get
		{
			if (bDestroyed)
			{
				return false;
			}
			if (aQueue.Count > 0)
			{
				return true;
			}
			if (objCOParent != null && objCOParent.aQueue.Count > 0)
			{
				return true;
			}
			if (GUISocialCombat2.coUs == this || GUISocialCombat2.coThem == this)
			{
				return true;
			}
			if (CrewSim.GetSelectedCrew() == this && CrewSim.bRaiseUI)
			{
				return true;
			}
			return false;
		}
	}

	public string strID
	{
		get
		{
			return _strID;
		}
		set
		{
			if (value == null)
			{
				return;
			}
			if (socUs != null)
			{
				CrewSim.system.RenameFaction(value, CrewSim.system.GetFaction(_strID), value);
			}
			if (strID != null && DataHandler.mapCOs.ContainsKey(strID) && DataHandler.mapCOs[strID] == this)
			{
				DataHandler.mapCOs.Remove(strID);
			}
			DataHandler.mapCOs[value] = this;
			if (ship != null)
			{
				ship.ChangeCOID(this, value);
			}
			CrewSim.objInstance.workManager.ChangeCOID(strID, value);
			if (Company != null)
			{
				if (Company.strName.IndexOf(_strID) >= 0)
				{
					string text = value + "'s Company";
					Company.strName = text;
				}
				if (Company.mapRoster.ContainsKey(_strID))
				{
					JsonCompanyRules value2 = Company.mapRoster[_strID];
					Company.mapRoster.Remove(_strID);
					Company.mapRoster[value] = value2;
				}
			}
			MonoSingleton<GUIRenderTargets>.Instance.UpdateName(_strID, value);
			Ledger.UpdateCOID(_strID, value);
			_strID = value;
		}
	}

	public bool Selected
	{
		get
		{
			if (bDestroyed)
			{
				return false;
			}
			if (goBracket != null)
			{
				return goBracket.activeInHierarchy;
			}
			return false;
		}
		set
		{
			if (bDestroyed || (!value && goBracket == null))
			{
				return;
			}
			if (goBracket == null && value)
			{
				goBracket = UnityEngine.Object.Instantiate(selectionBracket, tf);
				goBracket.transform.position = new Vector3(goBracket.transform.position.x, goBracket.transform.position.y, -10f);
				goBracket.SetActive(value: true);
				goBracket.transform.localScale = new Vector3(2f / tf.localScale.x, 2f / tf.localScale.y, 1f);
				if (base.gameObject.GetComponent<Crew>() != null)
				{
					goBracket.GetComponent<SpriteRenderer>().size = new Vector2(tf.GetComponent<BoxCollider>().size.x / 2f, tf.GetComponent<BoxCollider>().size.y / 2f);
				}
				else
				{
					goBracket.GetComponent<SpriteRenderer>().size = new Vector2(mr.bounds.size.x / 2f, mr.bounds.size.y / 2f);
				}
			}
			else if (goBracket != null && !value)
			{
				UnityEngine.Object.Destroy(goBracket);
				goBracket = null;
			}
		}
	}

	public bool Highlight
	{
		get
		{
			if (bDestroyed)
			{
				return false;
			}
			return base.gameObject.layer == LayerMask.NameToLayer("Tile Helpers");
		}
		set
		{
			if (!bDestroyed && base.gameObject.layer != LayerMask.NameToLayer("Ship Offscreen"))
			{
				if (value)
				{
					base.gameObject.layer = LayerMask.NameToLayer("Tile Helpers");
				}
				else
				{
					base.gameObject.layer = LayerMask.NameToLayer("Default");
				}
			}
		}
	}

	public bool HighlightObjective
	{
		get
		{
			if (bDestroyed)
			{
				return false;
			}
			return base.gameObject.layer == LayerMask.NameToLayer("Tile Helpers");
		}
		set
		{
			if (!bDestroyed)
			{
				Crew component = GetComponent<Crew>();
				if (value)
				{
					base.gameObject.layer = LayerMask.NameToLayer("Tile Helpers");
				}
				else
				{
					base.gameObject.layer = LayerMask.NameToLayer("Default");
				}
				if (component != null)
				{
					component.HighlightObjective = value;
				}
			}
		}
	}

	public bool DimLights
	{
		get
		{
			if (bDestroyed)
			{
				return false;
			}
			if (Item != null)
			{
				using List<Visibility>.Enumerator enumerator = Item.aLights.GetEnumerator();
				if (enumerator.MoveNext())
				{
					return enumerator.Current.gameObject.activeInHierarchy;
				}
			}
			if (pwr != null)
			{
				return pwr.Hide;
			}
			return false;
		}
		set
		{
			if (bDestroyed)
			{
				return;
			}
			if (Item != null)
			{
				foreach (Visibility aLight in Item.aLights)
				{
					aLight.gameObject.SetActive(!value);
					if (!value)
					{
						aLight.bRedraw = true;
					}
				}
				foreach (Transform key in Item.dictLightSprites.Keys)
				{
					key.gameObject.SetActive(!value);
				}
			}
			if (pwr != null)
			{
				pwr.Hide = value;
			}
		}
	}

	public bool Visible
	{
		get
		{
			if (bDestroyed)
			{
				return false;
			}
			return mr.enabled;
		}
		set
		{
			if (!bDestroyed)
			{
				mr.enabled = value;
				if (mc != null)
				{
					mc.enabled = value;
				}
				DimLights = !value;
				if (txtStack != null)
				{
					txtStack.gameObject.SetActive(value);
				}
			}
		}
	}

	public int StackCount
	{
		get
		{
			if (bDestroyed)
			{
				return 0;
			}
			return aStack.Count + 1;
		}
	}

	public List<CondOwner> StackAsList
	{
		get
		{
			List<CondOwner> list = new List<CondOwner>();
			list.AddRange(aStack);
			list.Add(this);
			return list;
		}
	}

	public Slots compSlots
	{
		get
		{
			return _compSlots;
		}
		private set
		{
			_compSlots = value;
		}
	}

	public string FriendlyName
	{
		get
		{
			if (strNameFriendly != null)
			{
				return strNameFriendly;
			}
			return strName;
		}
	}

	public string FirstName
	{
		get
		{
			if (pspec == null)
			{
				return strName;
			}
			if (!pspec.strFirstName.IsNullOrEmpty())
			{
				return pspec.strFirstName;
			}
			return FriendlyName;
		}
	}

	public string LastName
	{
		get
		{
			if (pspec == null)
			{
				return strName;
			}
			if (!pspec.strLastName.IsNullOrEmpty())
			{
				return pspec.strLastName;
			}
			return FriendlyName;
		}
	}

	public string ShortName
	{
		get
		{
			if (pspec != null)
			{
				return strName;
			}
			if (strNameShort != null)
			{
				return strNameShort;
			}
			return FriendlyName;
		}
	}

	public JsonCompany Company
	{
		get
		{
			return objCompany;
		}
		set
		{
			objCompany = value;
			if (value == null)
			{
				ShiftChange(JsonCompany.NullShift, bFreezeConds);
			}
			else
			{
				ShiftChange(value.GetShift(StarSystem.nUTCHour, this), bFreezeConds);
			}
			PlayerMarker.AddMarker(this);
		}
	}

	public Vector2 TLTileCoords
	{
		get
		{
			if (bDestroyed)
			{
				return default(Vector2);
			}
			Vector2 vector = tf.position;
			return new Vector2(vector.x - ((float)Item.nWidthInTiles / 2f - 0.5f) * 1f, vector.y + ((float)Item.nHeightInTiles / 2f - 0.5f) * 1f);
		}
	}

	public string Skin
	{
		get
		{
			string result = "A";
			if (faceRef != null)
			{
				Crew component = GetComponent<Crew>();
				if (component != null)
				{
					result = FaceAnim2.GetFaceGroups(component.FaceParts)[0];
				}
			}
			return result;
		}
	}

	public bool IsRobot
	{
		get
		{
			if (!_isRobot.HasValue)
			{
				CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsRobot");
				_isRobot = condTrigger.Triggered(this, null, logOutcome: false);
			}
			return _isRobot.Value;
		}
	}

	public bool IsHumanOrRobot
	{
		get
		{
			if (!_isHumanOrRobot.HasValue)
			{
				_isHumanOrRobot = HasCond("IsHuman") || HasCond("IsRobot");
			}
			return _isHumanOrRobot.Value;
		}
	}

	private static CondTrigger CTCanAIOrder
	{
		get
		{
			if (_ctCanAIOrder == null)
			{
				_ctCanAIOrder = DataHandler.GetCondTrigger("TCanAIOrder");
			}
			return _ctCanAIOrder;
		}
	}

	private static CondTrigger CTCanWalk
	{
		get
		{
			if (_ctCanWalk == null)
			{
				_ctCanWalk = DataHandler.GetCondTrigger("TCanWalk");
			}
			return _ctCanWalk;
		}
	}

	private static CondTrigger CTIsProneAwake
	{
		get
		{
			if (_ctIsProneAwake == null)
			{
				_ctIsProneAwake = DataHandler.GetCondTrigger("TIsProneAwake");
			}
			return _ctIsProneAwake;
		}
	}

	private static JsonPersonSpec JPSRelReportFactionNeg
	{
		get
		{
			if (_jpsRelReportFactionNeg == null)
			{
				_jpsRelReportFactionNeg = DataHandler.GetPersonSpec("RELReportFactionNeg");
			}
			return _jpsRelReportFactionNeg;
		}
	}

	public static Loot FreeWillLoot
	{
		get
		{
			if (_FreeWillLoot == null)
			{
				_FreeWillLoot = DataHandler.GetLoot("CONDAIFreeWillLoot");
			}
			return _FreeWillLoot;
		}
	}

	public static Loot FreeWillPenalty
	{
		get
		{
			if (_FreeWillPenalty == null)
			{
				_FreeWillPenalty = DataHandler.GetLoot("CONDAIFreeWillPenalty");
			}
			return _FreeWillPenalty;
		}
	}

	public bool HasSubCOs
	{
		get
		{
			return _hasSubCOs;
		}
		set
		{
			_hasSubCOs = value;
		}
	}

	private CondTrigger ctRestoreItem
	{
		get
		{
			if (_ctRestoreItem == null)
			{
				_ctRestoreItem = DataHandler.GetCondTrigger("TIsAIRestoreItem");
			}
			return _ctRestoreItem;
		}
	}

	private CondTrigger ctSuffocatingManWalk
	{
		get
		{
			if (_ctSuffocatingManWalk == null)
			{
				_ctSuffocatingManWalk = DataHandler.GetCondTrigger("TIsSuffocatingManWalkEmerg");
			}
			return _ctSuffocatingManWalk;
		}
	}

	public event AddCondEventHandler OnAddCond;

	public event RemoveCondEventHandler OnRemoveCond;

	private void Awake()
	{
		if (UpdateWaitingReplies == null)
		{
			UpdateWaitingReplies = new OnUpdateWaitingRepliesEvent();
		}
		if (UpdateAutoEmergency == null)
		{
			UpdateAutoEmergency = new OnUpdateAutoEmergencyEvent();
		}
		debugStop = false;
		tf = base.transform;
		fLastICOUpdate = StarSystem.fEpoch;
		fLastCleanup = StarSystem.fEpoch;
		fMSRedamageAmount = 0.0;
		aCondsTimed = new List<Condition>();
		aCondsTemp = new List<Condition>();
		aManUpdates = new List<IManUpdater>();
		mapConds = new Dictionary<string, Condition>();
		mapIAHist = new Dictionary<string, CondHistory>();
		mapPoints = new Dictionary<string, Vector2>();
		aInteractions = new List<string>();
		aMyShips = new HashSet<string>();
		aFactions = new List<string>();
		aRELConds = new List<string>();
		mapGUIPropMaps = new Dictionary<string, Dictionary<string, string>>();
		mapGUIRefs = new Dictionary<string, IGUIHarness>();
		mapCondRules = new Dictionary<string, CondRule>();
		aQueue = new List<Interaction>();
		aReplies = new List<ReplyThread>();
		aAttackIAs = new List<string>();
		aPriorities = new List<Priority>();
		hashCondsImportant = new HashSet<string>();
		aMessages = new List<JsonLogMessage>();
		aCondZeroes = new List<string>();
		aStack = new TrackingCollection<CondOwner>(delegate(bool any)
		{
			_hasSubCOs = any;
		});
		aLot = new TrackingCollection<CondOwner>(delegate(bool any)
		{
			_hasSubCOs = any;
		});
		dictRecentlyTried = new Dictionary<string, double>();
		dictRememberScores = new Dictionary<string, double>();
		dictPledges = new Dictionary<int, List<Pledge2>>();
		aRememberIAs = new List<string>();
		vTextOffset = new Vector3(0f, -0.5f, 0f);
		vBblOffset = new Vector3(0f, 1.5f, 0f);
		anim = GetComponentInChildren<Animator>();
		mr = GetComponent<MeshRenderer>();
		mc = GetComponent<BoxCollider>();
		bAlive = true;
		bIgnoreKill = false;
		if (nAnimStateID < 0)
		{
			nAnimStateID = Animator.StringToHash("AnimState");
		}
		strIdleAnim = "Idle";
		strWalkAnim = "Walk";
		jsShiftLast = JsonCompany.NullShift;
		aTickers = new List<JsonTicker>();
		aMUs = new List<IManUpdater>();
		aMUDels = new List<IManUpdater>();
		aDestructableConds = new List<string>();
		if (selectionBracket == null)
		{
			selectionBracket = Resources.Load<GameObject>("prefabSelectBracket");
		}
		Selected = false;
		strPersistentCT = null;
		strPersistentCO = null;
		strSourceCO = null;
		strSourceInteract = null;
		mapInfo = new Dictionary<string, string>();
		Transform transform = tf.Find("progressBar");
		if (transform != null)
		{
			progressBar = transform.GetComponent<ProgressBar>();
		}
		if ((bool)anim)
		{
			CrewSim.COAnimators.Add(anim);
		}
		if (STR_AI_REL_SWITCH == null)
		{
			STR_AI_REL_SWITCH = DataHandler.GetString("AI_REL_SWITCH");
			STR_AI_REL_SWITCH_END = DataHandler.GetString("AI_REL_SWITCH_END");
			STR_AI_REL_SWITCH_NOBODY = DataHandler.GetString("AI_REL_SWITCH_NOBODY");
		}
		_fieldsInitialized = true;
	}

	public static void CheckTrue(bool condition, string message)
	{
		_ = Application.isEditor;
	}

	public bool ValidateParent()
	{
		_ = Application.isEditor;
		return true;
	}

	public void ValidateParentRecursive()
	{
	}

	public void UpdateManual(int maxRepeats = 10)
	{
		if (ship == null || ship.LoadState < Ship.Loaded.Edit)
		{
			return;
		}
		if (StarSystem.fEpoch - fLastCleanup > 2.0)
		{
			Cleanup();
		}
		if (aTickers.Count > 0)
		{
			temp_jt = aTickers[0];
			while (temp_jt != null && temp_jt.fTimeLeft <= 0.0)
			{
				bool flag = false;
				if (temp_jt.strCondLoot != null)
				{
					double fCoeff = 1.0;
					if (temp_jt.strCondLootCoeff != null)
					{
						fCoeff = GetCondAmount(temp_jt.strCondLootCoeff);
					}
					ParseCondLoot(temp_jt.strCondLoot, fCoeff);
					flag = true;
				}
				if (temp_jt.bQueue || temp_jt.strCondUpdate != null)
				{
					EndTurn();
					flag = true;
				}
				if (bDestroyed)
				{
					CrewSim.RemoveTicker(this);
					break;
				}
				if (flag)
				{
					aMUDels.Clear();
					aMUs.Clear();
					foreach (IManUpdater aManUpdate in aManUpdates)
					{
						if (aManUpdate == null)
						{
							aMUDels.Add(aManUpdate);
						}
						else
						{
							aMUs.Add(aManUpdate);
						}
					}
					foreach (IManUpdater aMU in aMUs)
					{
						if (aMU == null)
						{
							aMUDels.Add(aMU);
							continue;
						}
						aMU.UpdateManual();
						if (!bDestroyed)
						{
							continue;
						}
						CrewSim.RemoveTicker(this);
						break;
					}
					foreach (IManUpdater aMUDel in aMUDels)
					{
						aManUpdates.Remove(aMUDel);
					}
				}
				if (bDestroyed)
				{
					CrewSim.RemoveTicker(this);
					break;
				}
				aTickers.Remove(temp_jt);
				if (temp_jt.bRepeat)
				{
					temp_jt.SetTimeLeft(temp_jt.fTimeLeft + temp_jt.fPeriod);
					bool flag2 = false;
					if (!string.IsNullOrEmpty(temp_jt.strName))
					{
						temp_counterDict.Increment(temp_jt.strName);
						if (temp_counterDict[temp_jt.strName] > maxRepeats)
						{
							Debug.Log("#Info# " + strName + " break UpdateManual()-While on Ticker " + temp_jt.strName + ", Too many retries this frame");
							nEndTurnsThisFrame = 0;
							temp_aTickersAside.Add(temp_jt);
							flag2 = true;
						}
					}
					if (!flag2)
					{
						AddTicker(temp_jt);
					}
				}
				if (aTickers.Count > 0)
				{
					temp_jt = aTickers[0];
					continue;
				}
				temp_jt = null;
				CrewSim.RemoveTicker(this);
			}
			foreach (JsonTicker item in temp_aTickersAside)
			{
				AddTicker(item);
			}
			temp_counterDict.Clear();
			temp_aTickersAside.Clear();
		}
		RefreshAnim();
		UpdateStats();
		if (Item != null)
		{
			Item.VisualizeOverlays();
		}
	}

	public void SetHighlight(float fAmount)
	{
		MaterialPropertyBlock materialPropertyBlock = new MaterialPropertyBlock();
		Crew component = GetComponent<Crew>();
		if (component != null)
		{
			component.SetHighlight(fAmount);
		}
		else if (mr != null)
		{
			mr.GetPropertyBlock(materialPropertyBlock);
			materialPropertyBlock.SetFloat("_Highlight", fAmount);
			mr.SetPropertyBlock(materialPropertyBlock);
			GUIInventoryItem inventoryItemFromCO = GUIInventory.GetInventoryItemFromCO(this);
			RawImage rawImage = null;
			if (inventoryItemFromCO != null)
			{
				rawImage = inventoryItemFromCO.GetComponent<RawImage>();
			}
			else if (GUIInventory.instance.PaperDollManager.mapCOIDsToGO.ContainsKey(strID))
			{
				rawImage = GUIInventory.instance.PaperDollManager.mapCOIDsToGO[strID].GetComponent<RawImage>();
			}
			if (rawImage != null)
			{
				rawImage.materialForRendering.SetFloat("_Highlight", fAmount);
			}
		}
		if (fAmount > 0f)
		{
			Highlight = true;
		}
		else
		{
			Highlight = false;
		}
	}

	public void RefreshAnim()
	{
		if (anim == null)
		{
			return;
		}
		if (bAlive && aQueue.Count > 0 && aQueue[0] != null && aQueue[0].strName != "Wait")
		{
			if (aQueue[0].strName == "Walk")
			{
				SetAnimState(Interaction.dictAnims[strWalkAnim]);
			}
			else
			{
				SetAnimState(aQueue[0].GetAnim(this));
			}
		}
		else
		{
			int value = 0;
			Interaction.dictAnims.TryGetValue(strIdleAnim, out value);
			SetAnimState(value);
		}
	}

	private void Cleanup()
	{
		foreach (string item in new List<string>(dictRecentlyTried.Keys))
		{
			if (StarSystem.fEpoch - dictRecentlyTried[item] > 60.0)
			{
				dictRecentlyTried.Remove(item);
				break;
			}
		}
		bool flag = false;
		double num = double.PositiveInfinity;
		for (int i = 0; i < aTickers.Count; i++)
		{
			if (aTickers[i].bQueue)
			{
				num = aTickers[i].fTimeLeft;
			}
			if (i >= aTickers.Count - 1)
			{
				break;
			}
			if (aTickers[i].fTimeLeft - aTickers[i + 1].fTimeLeft >= 0.0002770000137388706)
			{
				flag = true;
			}
		}
		if (aQueue.Count > 0)
		{
			Interaction interaction = aQueue[0];
			if (interaction != null && interaction.fDuration < num)
			{
				JsonTicker jsonTicker = new JsonTicker();
				jsonTicker.bQueue = true;
				jsonTicker.strName = interaction.strName;
				jsonTicker.fPeriod = interaction.fDuration;
				jsonTicker.SetTimeLeft(jsonTicker.fPeriod);
				AddTicker(jsonTicker);
			}
			else if (interaction == null)
			{
				JsonTicker jsonTicker2 = new JsonTicker();
				jsonTicker2.bQueue = true;
				jsonTicker2.strName = "Cleanup found null interaction?";
				jsonTicker2.fPeriod = 0.0;
				jsonTicker2.SetTimeLeft(jsonTicker2.fPeriod);
				AddTicker(jsonTicker2);
			}
		}
		if (flag)
		{
			aTickers.Sort((JsonTicker x, JsonTicker y) => x.fTimeLeft.CompareTo(y.fTimeLeft));
		}
		if (aQueue.Count > 0 && !aQueue[0].bUIDoesNotCancel && (aQueue[0].strRaiseUI != null || aQueue[0].strRaiseUIThem != null) && aQueue[0].bRaisedUI && !CrewSim.bRaiseUI)
		{
			foreach (JsonTicker aTicker in aTickers)
			{
				if (aTicker.strName == aQueue[0].strName && aTicker.fTimeLeft > 0.1)
				{
					AICancelCurrent();
					break;
				}
			}
		}
		if (aQueue.Count > 0 && aQueue[0].strName == "Wait")
		{
			if (aQueue[0].objThem == null || aQueue[0].objThem.ship == null || aQueue[0].objThem.ship.LoadState <= Ship.Loaded.Shallow)
			{
				AICancelCurrent();
			}
			else if (!HasCond("IsPlayer") || !CrewSim.bRaiseUI)
			{
				bool flag2 = true;
				foreach (Interaction item2 in aQueue[0].objThem.aQueue)
				{
					if (item2.objThem == this)
					{
						flag2 = false;
						break;
					}
				}
				if (flag2)
				{
					AICancelCurrent();
				}
			}
		}
		if (HasCond("IsAIAgent"))
		{
			if (!HasCond("IsRobot") && (mapIAHist == null || !mapIAHist.ContainsKey("StatEsteem") || mapIAHist["StatEsteem"].mapInteractions == null || mapIAHist["StatEsteem"].mapInteractions.Count < 100))
			{
				SetCondAmount("DebugMemoryLoss", 1.0);
			}
			else
			{
				ZeroCondAmount("DebugMemoryLoss");
			}
			if (!HasCond("IsSocialItemCleanupDone") && compSlots != null)
			{
				Slot slot = compSlots.GetSlot("social");
				if (slot != null && slot.GetOutermostCO() != null)
				{
					Dictionary<string, int> dictionary = new Dictionary<string, int>();
					List<CondOwner> cOs = slot.GetOutermostCO().GetCOs(bAllowLocked: true);
					if (cOs != null)
					{
						foreach (CondOwner item3 in cOs)
						{
							if (!(item3 == null))
							{
								if (!dictionary.ContainsKey(item3.strName))
								{
									dictionary[item3.strName] = 1;
									continue;
								}
								if (dictionary[item3.strName] < 3)
								{
									dictionary[item3.strName]++;
									continue;
								}
								dictionary[item3.strName]++;
								item3.RemoveFromCurrentHome(bForce: true);
								item3.Destroy();
							}
						}
						cOs.Clear();
					}
					dictionary.Clear();
				}
				double fAge = 1.0;
				Condition cond = DataHandler.GetCond("IsSocialItemCleanupDone");
				if (cond != null)
				{
					fAge = (double)cond.fDuration * MathUtils.Rand(0.1, 1.0, MathUtils.RandType.High);
				}
				AddCondAmount("IsSocialItemCleanupDone", 1.0, fAge);
			}
		}
		fLastCleanup = StarSystem.fEpoch;
	}

	public void Destroy()
	{
		ValidateParent();
		if ((bool)anim)
		{
			CrewSim.COAnimators.Remove(anim);
		}
		if (bDestroyed)
		{
			return;
		}
		if (this == null)
		{
			if ((object)this == null)
			{
				Debug.Log("ERROR: Destroying a null");
			}
			else
			{
				Debug.Log("ERROR: Destroying a null " + strName);
			}
			Debug.Break();
			return;
		}
		if (elec != null)
		{
			elec.CleanUp(elec.needsCleanup);
		}
		Company = null;
		jsShiftLast = null;
		if (Pathfinder != null)
		{
			Pathfinder.Destroy();
		}
		if (progressBar != null)
		{
			progressBar.Destroy();
		}
		foreach (CondOwner item in new List<CondOwner>(aStack))
		{
			item.Destroy();
		}
		new List<CondOwner>(aLot);
		foreach (CondOwner item2 in aLot)
		{
			item2.Destroy();
		}
		if (objContainer != null)
		{
			objContainer.Destroy();
			objContainer = null;
		}
		if (_compSlots != null)
		{
			_compSlots.Destroy();
			_compSlots = null;
		}
		if (CrewSim.objInstance != null)
		{
			CrewSim.objInstance.coDicts.RemoveCO(this);
			if (CrewSim.GetBracketTarget() == this)
			{
				CrewSim.objInstance.SetBracketTarget(null, bUpdateOnly: false);
			}
			try
			{
				CrewSim.objInstance.ShowBlocksAndLights(this, bShow: false);
			}
			catch (Exception ex)
			{
				Debug.Log("ERROR: " + ToString() + " \n" + ex.ToString());
			}
		}
		if (strID != null && DataHandler.mapCOs.ContainsKey(strID) && DataHandler.mapCOs[strID] == this)
		{
			DataHandler.mapCOs.Remove(strID);
		}
		foreach (Condition value in mapConds.Values)
		{
			value.Destroy();
		}
		mapConds.Clear();
		mapConds = null;
		foreach (CondHistory value2 in mapIAHist.Values)
		{
			value2.Destroy();
		}
		mapIAHist.Clear();
		mapIAHist = null;
		mapPoints.Clear();
		mapPoints = null;
		aInteractions.Clear();
		aInteractions = null;
		aMyShips.Clear();
		aMyShips = null;
		aFactions.Clear();
		aFactions = null;
		aRELConds.Clear();
		aRELConds = null;
		mapGUIPropMaps.Clear();
		mapGUIPropMaps = null;
		mapGUIRefs.Clear();
		mapGUIRefs = null;
		mapCondRules.Clear();
		mapCondRules = null;
		aMessages.Clear();
		aMessages = null;
		aCondZeroes.Clear();
		aCondZeroes = null;
		aStack.Clear();
		aStack = null;
		coStackHead = null;
		aLot.Clear();
		aLot = null;
		foreach (Interaction item3 in aQueue)
		{
			item3.Destroy();
		}
		aQueue.Clear();
		aQueue = null;
		aReplies.Clear();
		aReplies = null;
		aAttackIAs.Clear();
		aAttackIAs = null;
		foreach (Priority aPriority in aPriorities)
		{
			aPriority.Destroy();
		}
		aPriorities.Clear();
		aPriorities = null;
		if (hashCondsImportant != null)
		{
			hashCondsImportant.Clear();
		}
		hashCondsImportant = null;
		dictRecentlyTried.Clear();
		dictRecentlyTried = null;
		aRememberIAs.Clear();
		aRememberIAs = null;
		dictRememberScores.Clear();
		dictRememberScores = null;
		anim = null;
		pwr = null;
		objCondID = null;
		objCOParent = null;
		ship = null;
		aCondsTimed.Clear();
		aCondsTimed = null;
		aCondsTemp.Clear();
		aCondsTemp = null;
		aTickers.Clear();
		aTickers = null;
		aDestructableConds.Clear();
		aDestructableConds = null;
		if (goBracket != null)
		{
			UnityEngine.Object.Destroy(goBracket);
		}
		goBracket = null;
		tf = null;
		dictAddCondEvents.Clear();
		dictAddCondEvents = null;
		dictRemoveCondEvents.Clear();
		dictRemoveCondEvents = null;
		bDestroyed = true;
		UnityEngine.Object.DestroyImmediate(base.gameObject);
		ValidateParent();
	}

	public void FallAway()
	{
		if (!HasCond("IsFallingAway"))
		{
			Tile tileAtWorldCoords = ship.GetTileAtWorldCoords1(tf.position.x, tf.position.y, bAllowDocked: true);
			if (!(tileAtWorldCoords == null) && tileAtWorldCoords.IsEvaTileWithGravitation())
			{
				LogMessage(strName + DataHandler.GetString("OBJV_GRAV_LOSS"), "SignalRed", strID);
				SetCondAmount("IsFallingAway", 1.0);
				StartCoroutine(_FallAway());
			}
		}
	}

	private IEnumerator _FallAway()
	{
		double timeStart = StarSystem.fEpoch;
		double timeElapsed = 0.0;
		while (timeElapsed < 5.0)
		{
			if (ship == null || bDestroyed)
			{
				yield break;
			}
			double num = StarSystem.fEpoch - timeStart - timeElapsed;
			timeElapsed += num;
			tf.Rotate(0f, 0f, (float)num);
			tf.localScale = Vector3.one / (1f + (float)timeElapsed);
			Tile tileAtWorldCoords = ship.GetTileAtWorldCoords1(tf.position.x, tf.position.y, bAllowDocked: true);
			if (tileAtWorldCoords != null && !tileAtWorldCoords.IsEvaTileWithGravitation())
			{
				if (Item == null)
				{
					tf.localScale = Vector3.one;
				}
				else
				{
					Item.ResetTransforms(tf.position.x, tf.position.y);
				}
				ZeroCondAmount("IsFallingAway");
				yield break;
			}
			yield return null;
		}
		if (HasCond("IsPlayer"))
		{
			LogMessage(strName + DataHandler.GetString("OBJV_GRAV_LOST"), "SignalRed", strID);
			CanvasManager.instance.GameOver(this);
			yield break;
		}
		Kill = true;
		yield return null;
		RemoveFromCurrentHome(bForce: true);
		Destroy();
	}

	public void CheckInteractionFlag()
	{
		bCanUndamage = false;
		bCanRepair = false;
		bCanPatch = false;
		if (aInteractions == null || aInteractions.Count <= 0)
		{
			return;
		}
		foreach (string aInteraction in aInteractions)
		{
			if (aInteraction.Contains("Patch") && !aInteraction.Contains("Scrap"))
			{
				bCanPatch = true;
			}
			else if (aInteraction.Contains("Repair"))
			{
				bCanRepair = true;
			}
			else if (aInteraction.Contains("Undamage"))
			{
				bCanUndamage = true;
			}
		}
	}

	public void SetData(JsonCondOwner jid, bool bLoot = true, JsonCondOwnerSave jCOSIn = null)
	{
		if (jid == null)
		{
			return;
		}
		if (!_fieldsInitialized)
		{
			Awake();
		}
		jCOS = jCOSIn;
		strName = jid.strName;
		strNameFriendly = jid.strNameFriendly;
		strNameShort = jid.strNameShort;
		strDesc = jid.strDesc;
		strCODef = jid.strCODef;
		if (strCODef == null)
		{
			strCODef = jid.strName;
		}
		strItemDef = jid.strItemDef;
		strPortraitImg = jid.strPortraitImg;
		nStackLimit = Mathf.Max(1, jid.nStackLimit);
		bSaveMessageLog = jid.bSaveMessageLog;
		bSlotLocked = jid.bSlotLocked;
		strType = jid.strType;
		if (jid.aInteractions != null)
		{
			aInteractions = new List<string>(jid.aInteractions);
		}
		else
		{
			aInteractions = new List<string>();
		}
		CheckInteractionFlag();
		if (jCOSIn != null)
		{
			strSourceInteract = jCOSIn.strSourceInteract;
			strSourceCO = jCOSIn.strSourceCO;
			strPersistentCT = jCOSIn.strPersistentCT;
			strPersistentCO = jCOSIn.strPersistentCO;
			strIdleAnim = jCOSIn.strIdleAnim;
			strLastSocial = jCOSIn.strLastSocial;
			pairInventoryXY = new PairXY(jCOSIn.inventoryX, jCOSIn.inventoryY);
		}
		else
		{
			strSourceInteract = null;
			strSourceCO = null;
			strPersistentCO = null;
			strPersistentCT = null;
			strLastSocial = null;
		}
		if (jid.aSlotsWeHave != null)
		{
			compSlots = base.gameObject.AddComponent<Slots>();
			string[] aSlotsWeHave = jid.aSlotsWeHave;
			foreach (string text in aSlotsWeHave)
			{
				compSlots.AddSlot(DataHandler.GetSlot(text));
			}
		}
		if (jid.strContainerCT != null)
		{
			objContainer = base.gameObject.AddComponent<Container>();
			_ = objContainer.CO;
			objContainer.ctAllowed = DataHandler.GetCondTrigger(jid.strContainerCT);
			if (!CrewSim.bSaveUsesOldContainerGrids && jid.nContainerHeight != 0 && jid.nContainerWidth != 0)
			{
				objContainer.gridLayout = new GridLayout(jid.nContainerWidth, jid.nContainerHeight);
			}
		}
		bLogConds = false;
		string[] array = jid.aStartingCondRules;
		if (jCOSIn != null)
		{
			array = jCOSIn.aCondRules;
		}
		if (array != null)
		{
			if (array.Contains("DEFAULT"))
			{
				List<string> list = array.ToList();
				list.Remove("DEFAULT");
				JsonCondOwner condOwnerDef = DataHandler.GetCondOwnerDef(strCODef);
				if (condOwnerDef != null && condOwnerDef.aStartingCondRules != null)
				{
					list.AddRange(condOwnerDef.aStartingCondRules);
				}
				array = list.ToArray();
			}
			bool flag = bIgnoreKill;
			if (jCOSIn == null)
			{
				bIgnoreKill = true;
			}
			string[] aSlotsWeHave = array;
			foreach (string strCondRule in aSlotsWeHave)
			{
				AddCondRule(strCondRule, bApplyEffects: false);
			}
			bIgnoreKill = flag;
		}
		bFreezeCondRules = true;
		if (jid.aUpdateCommands != null)
		{
			string[] aSlotsWeHave = jid.aUpdateCommands;
			foreach (string strDef in aSlotsWeHave)
			{
				AddCommand(strDef);
			}
		}
		if (nStackLimit > 1)
		{
			AddCondAmount("IsStacking", nStackLimit - 1);
		}
		string[] array2 = jid.aStartingConds;
		bool flag2 = false;
		if (jCOSIn != null)
		{
			array2 = jCOSIn.aConds;
			flag2 = jCOSIn.aCondReveals != null && array2.Length == 2 * jCOSIn.aCondReveals.Length;
		}
		if (array2 != null)
		{
			if (array2.Contains("DEFAULT"))
			{
				List<string> list2 = array2.ToList();
				list2.Remove("DEFAULT");
				JsonCondOwner condOwnerDef2 = DataHandler.GetCondOwnerDef(strCODef);
				list2.AddRange(condOwnerDef2.aStartingConds);
				array2 = list2.ToArray();
			}
			for (int j = 0; j < array2.Length; j++)
			{
				string text2 = array2[j];
				string[] array3 = text2.Split('=');
				if (array3.Length > 1)
				{
					ZeroCondAmount(array3[0]);
				}
				string text3 = ParseCondEquation(text2);
				Condition value = null;
				if (text3 != null && mapConds != null && mapConds.TryGetValue(text3, out value))
				{
					if (flag2)
					{
						value.nDisplaySelf = jCOSIn.aCondReveals[2 * j];
						value.nDisplayOther = jCOSIn.aCondReveals[2 * j + 1];
					}
					if (value.bRemoveOnLoad)
					{
						ZeroCondAmount(text3);
					}
				}
			}
		}
		if (jCOSIn == null)
		{
			foreach (CondRule value2 in mapCondRules.Values)
			{
				AddCondRuleEffects(value2, 1f);
				if (value2.fPref != double.PositiveInfinity)
				{
					hashCondsImportant.Add(value2.strCond);
				}
			}
			bFreezeCondRules = false;
		}
		bLogConds = true;
		if (jCOSIn != null)
		{
			bFreezeConds = true;
		}
		JsonTicker[] array4 = null;
		if (jCOSIn != null)
		{
			array4 = jCOSIn.aTickers;
			JsonTicker[] array5 = new JsonTicker[aTickers.Count];
			aTickers.CopyTo(array5);
			JsonTicker[] array6 = array5;
			foreach (JsonTicker jtRemove in array6)
			{
				RemoveTicker(jtRemove);
			}
		}
		else if (jid.aTickers != null)
		{
			array4 = new JsonTicker[jid.aTickers.Length];
			for (int k = 0; k < jid.aTickers.Length; k++)
			{
				array4[k] = DataHandler.GetTicker(jid.aTickers[k]);
			}
		}
		if (array4 != null)
		{
			JsonTicker[] array6 = array4;
			foreach (JsonTicker jsonTicker in array6)
			{
				if (jsonTicker != null)
				{
					jsonTicker.SetTimeLeft(jsonTicker.fTimeLeft);
					AddTicker(jsonTicker.Clone());
				}
			}
		}
		mapSlotEffects = new Dictionary<string, JsonSlotEffects>();
		if (jid.mapSlotEffects != null)
		{
			foreach (KeyValuePair<string, string> item6 in DataHandler.ConvertStringArrayToDict(jid.mapSlotEffects))
			{
				JsonSlotEffects slotEffect = DataHandler.GetSlotEffect(item6.Value);
				if (slotEffect != null)
				{
					mapSlotEffects[item6.Key] = slotEffect;
					slotEffect.strSlotPrimary = item6.Key;
					if (slotEffect.aSlotsSecondary != null)
					{
						string[] aSlotsWeHave = slotEffect.aSlotsSecondary;
						foreach (string key in aSlotsWeHave)
						{
							mapSlotEffects[key] = slotEffect;
						}
					}
				}
				else
				{
					Debug.Log(strName + " was unable to load sloteffect Key: " + item6.Key + " Value: " + item6.Value);
				}
			}
		}
		mapChargeProfiles = new Dictionary<string, JsonChargeProfile>();
		if (jid.mapChargeProfiles != null)
		{
			foreach (KeyValuePair<string, string> item7 in DataHandler.ConvertStringArrayToDict(jid.mapChargeProfiles))
			{
				JsonChargeProfile chargeProfile = DataHandler.GetChargeProfile(item7.Value);
				if (chargeProfile != null)
				{
					mapChargeProfiles[item7.Key] = chargeProfile;
				}
			}
		}
		if (jid.mapAltItemDefs != null)
		{
			mapAltItemDefs = DataHandler.ConvertStringArrayToDict(jid.mapAltItemDefs);
		}
		else
		{
			mapAltItemDefs = new Dictionary<string, string>();
		}
		if (jid.mapAltSlotImgs != null)
		{
			mapAltSlotImgs = DataHandler.ConvertStringArrayToDict(jid.mapAltSlotImgs);
		}
		else
		{
			mapAltSlotImgs = new Dictionary<string, string>();
		}
		if (jid.dictSlotsLayout != null)
		{
			dictSlotsLayout = jid.dictSlotsLayout;
		}
		else
		{
			dictSlotsLayout = new Dictionary<string, Vector3>();
		}
		if (bLoot && jCOSIn == null)
		{
			foreach (CondOwner item8 in DataHandler.GetLoot(jid.strLoot).GetCOLoot(this, bSuppressOverride: false))
			{
				bool flag3 = false;
				if (compSlots != null && item8.mapSlotEffects.Keys.Count > 0)
				{
					foreach (string key2 in item8.mapSlotEffects.Keys)
					{
						if (compSlots.SlotItem(key2, item8))
						{
							flag3 = true;
							break;
						}
					}
				}
				if (!flag3)
				{
					CondOwner condOwner = AddCO(item8, bEquip: true, bOverflow: true, bIgnoreLocks: true);
					if (condOwner != null)
					{
						condOwner.Destroy();
					}
				}
			}
		}
		if (jid.mapPoints != null)
		{
			string[] aSlotsWeHave = jid.mapPoints;
			for (int i = 0; i < aSlotsWeHave.Length; i++)
			{
				string[] array7 = aSlotsWeHave[i].Split(',');
				float result = 0f;
				if (array7[1] == "9e99")
				{
					result = float.PositiveInfinity;
				}
				else
				{
					float.TryParse(array7[1], out result);
				}
				float result2 = 0f;
				if (array7[2] == "9e99")
				{
					result2 = float.PositiveInfinity;
				}
				else
				{
					float.TryParse(array7[2], out result2);
				}
				mapPoints[array7[0]] = new Vector2(result, result2);
			}
		}
		if (jid.jsonPI != null)
		{
			pwr = base.gameObject.AddComponent<Powered>();
			pwr.SetData(jid.jsonPI);
		}
		if (jid.mapGUIPropMaps != null)
		{
			Dictionary<string, string> dictionary = DataHandler.ConvertStringArrayToDict(jid.mapGUIPropMaps);
			foreach (string key3 in dictionary.Keys)
			{
				mapGUIPropMaps[key3] = DataHandler.GetGUIPropMap(dictionary[key3]);
			}
		}
		if (jid.aComponents != null)
		{
			string[] aSlotsWeHave = jid.aComponents;
			for (int i = 0; i < aSlotsWeHave.Length; i++)
			{
				Type type = Type.GetType(aSlotsWeHave[i]);
				base.gameObject.AddComponent(type);
			}
		}
		if (jCOSIn != null)
		{
			bAlive = jCOSIn.bAlive;
			if (jid.bSaveMessageLog)
			{
				if (jCOSIn.aMsgColors != null)
				{
					for (int l = 0; l < jCOSIn.aMsgColors.Length && l < jCOSIn.aMessages.Length; l++)
					{
						JsonLogMessage jsonLogMessage = new JsonLogMessage();
						jsonLogMessage.strName = Guid.NewGuid().ToString();
						jsonLogMessage.strMessage = jCOSIn.aMessages[l];
						jsonLogMessage.strColor = jCOSIn.aMsgColors[l];
						jsonLogMessage.strOwner = "n/a";
						if (jsonLogMessage.strMessage.IndexOf(jCOSIn.strID) == 0)
						{
							jsonLogMessage.strOwner = jCOSIn.strID;
						}
						jsonLogMessage.fTime = StarSystem.fEpoch - (double)jCOSIn.aMsgColors.Length + (double)l;
						this.aMessages.Add(jsonLogMessage);
					}
				}
				if (jCOSIn.aMessages2 != null)
				{
					JsonLogMessage[] aMessages = jCOSIn.aMessages2;
					foreach (JsonLogMessage item in aMessages)
					{
						this.aMessages.Add(item);
					}
				}
			}
			if (jCOSIn.aCondZeroes != null)
			{
				string[] aSlotsWeHave = jCOSIn.aCondZeroes;
				foreach (string item2 in aSlotsWeHave)
				{
					aCondZeroes.Add(item2);
				}
			}
			if (jCOSIn.mapDGasMols != null)
			{
				GasContainer gasContainer = GasContainer;
				if (gasContainer != null)
				{
					float result3 = 0f;
					gasContainer.fDGasTemp = jCOSIn.fDGasTemp;
					if (gasContainer.fDGasTemp == 0.0)
					{
						gasContainer.fDGasTemp = 0.001;
					}
					string[] aSlotsWeHave = jCOSIn.mapDGasMols;
					for (int i = 0; i < aSlotsWeHave.Length; i++)
					{
						string[] array8 = aSlotsWeHave[i].Split(',');
						float.TryParse(array8[1], out result3);
						gasContainer.mapDGasMols[array8[0]] = result3;
					}
				}
			}
			fLastICOUpdate = jCOSIn.fLastICOUpdate;
			fMSRedamageAmount = jCOSIn.fMSRedamageAmount;
			if (jCOSIn.aQueue != null)
			{
				JsonInteractionSave[] array9 = jCOSIn.aQueue;
				foreach (JsonInteractionSave jsonInteractionSave in array9)
				{
					Interaction interaction = DataHandler.GetInteraction(jsonInteractionSave.strName, jsonInteractionSave);
					if (interaction == null)
					{
						Debug.Log("Interaction " + jsonInteractionSave.strName + " is missing from the DataHandler. This should probably be a crash...");
						continue;
					}
					aQueue.Add(interaction);
					if (interaction.strName == "Walk" && interaction.strTargetPoint == null)
					{
						interaction.strTargetPoint = "use";
					}
				}
			}
			if (jCOSIn.aReplies != null)
			{
				ReplyThread[] array10 = jCOSIn.aReplies;
				foreach (ReplyThread replyThread in array10)
				{
					ReplyThread replyThread2 = new ReplyThread();
					replyThread2.fEpoch = replyThread.fEpoch;
					replyThread2.jis = replyThread.jis;
					replyThread2.strID = replyThread.strID;
					aReplies.Add(replyThread2);
				}
			}
			if (jCOSIn.aAttackIAs != null && !CrewSim.VersionIsOlderThan(CrewSim.aSaveVersion, new int[4] { 0, 14, 0, 12 }))
			{
				ApplyAModes(jCOSIn.aAttackIAs, bRebuildQAB: false);
			}
			if (jCOSIn.dictRecentlyTried != null)
			{
				foreach (KeyValuePair<string, double> item9 in jCOSIn.dictRecentlyTried)
				{
					dictRecentlyTried.Add(item9.Key, item9.Value);
				}
			}
			if (jCOSIn.dictRememberScores != null)
			{
				foreach (KeyValuePair<string, double> dictRememberScore in jCOSIn.dictRememberScores)
				{
					dictRememberScores.Add(dictRememberScore.Key, dictRememberScore.Value);
				}
			}
			if (jCOSIn.aRememberIAs != null)
			{
				string[] aSlotsWeHave = jCOSIn.aRememberIAs;
				foreach (string item3 in aSlotsWeHave)
				{
					aRememberIAs.Add(item3);
				}
			}
			if (jCOSIn.aMyShips != null)
			{
				string[] aSlotsWeHave = jCOSIn.aMyShips;
				foreach (string item4 in aSlotsWeHave)
				{
					aMyShips.Add(item4);
				}
			}
			if (jCOSIn.aFactions != null)
			{
				string[] aSlotsWeHave = jCOSIn.aFactions;
				foreach (string item5 in aSlotsWeHave)
				{
					aFactions.Add(item5);
				}
			}
			if (jCOSIn.mapIAHist2 != null)
			{
				this.mapIAHist = new Dictionary<string, CondHistory>();
				if (jCOSIn.mapIAHist2 != null)
				{
					this.mapIAHist = new Dictionary<string, CondHistory>();
					JsonCondHistory[] mapIAHist = jCOSIn.mapIAHist2;
					foreach (JsonCondHistory jsonCondHistory in mapIAHist)
					{
						if (!CrewSim.bSaveHasENCPoliceBoard || jsonCondHistory.strCondName.IndexOf("ENCPoliceBoard") != 0)
						{
							this.mapIAHist[jsonCondHistory.strCondName] = jsonCondHistory.GetData();
						}
					}
				}
			}
			if (jCOSIn.social != null)
			{
				socUs = base.gameObject.AddComponent<Social>();
				socUs.Init(jCOSIn.social);
			}
			bool flag4 = false;
			if (jCOSIn.cgs != null)
			{
				GUIChargenStack gUIChargenStack = base.gameObject.AddComponent<GUIChargenStack>();
				gUIChargenStack.Init(jCOSIn.cgs);
				JsonPersonSpec jsonPersonSpec = new JsonPersonSpec();
				jsonPersonSpec.bAlive = bAlive;
				int i = (jsonPersonSpec.nAgeMin = Convert.ToInt32(GetCondAmount("StatAge")));
				jsonPersonSpec.nAgeMax = i;
				if (gUIChargenStack.GetLatestCareer() != null)
				{
					jsonPersonSpec.strCareerNow = gUIChargenStack.GetLatestCareer().GetJC().strName;
				}
				jsonPersonSpec.strFirstName = gUIChargenStack.strFirstName;
				jsonPersonSpec.strLastName = gUIChargenStack.strLastName;
				jsonPersonSpec.strGender = "IsMale";
				if (HasCond("IsFemale"))
				{
					jsonPersonSpec.strGender = "IsFemale";
				}
				else if (HasCond("IsNB"))
				{
					jsonPersonSpec.strGender = "IsNB";
				}
				jsonPersonSpec.strHomeworldSet = "HW_" + gUIChargenStack.GetHomeworld().strATCCode;
				pspec = new PersonSpec(jsonPersonSpec, bNew: false);
				jsonPersonSpec.strHomeworldFind = pspec.strHomeworldNow;
				pspec.nStrata = gUIChargenStack.Strata;
				pspec.strCO = strID;
				flag4 = CrewSim.bSaveHasMissingPledgePayloads;
			}
			int num2 = 0;
			if (jCOSIn.aPledges != null)
			{
				JsonPledgeSave[] aPledges = jCOSIn.aPledges;
				foreach (JsonPledgeSave jsonPledgeSave in aPledges)
				{
					if (CrewSim.bSaveHasMissingPledgeUs && jsonPledgeSave.strUsID != jCOSIn.strID)
					{
						string strUsID = jsonPledgeSave.strUsID;
						jsonPledgeSave.strUsID = jCOSIn.strID;
						if (jsonPledgeSave.strThemID == strUsID)
						{
							jsonPledgeSave.strThemID = jsonPledgeSave.strUsID;
						}
					}
					Pledge2 pledge = PledgeFactory.Factory(jsonPledgeSave);
					if (pledge != null)
					{
						AddPledge(pledge);
						num2++;
					}
				}
			}
			if (jCOSIn.strComp != null)
			{
				Company = CrewSim.system.GetCompany(jCOSIn.strComp);
				ShiftChange(JsonCompany.NullShift, bSilent: true);
			}
			if (flag4 && num2 < 6)
			{
				Interaction interactionCurrent = GetInteractionCurrent();
				if (interactionCurrent != null && interactionCurrent.strName != null && interactionCurrent.strName.IndexOf("PSP") == 0)
				{
					flag4 = false;
				}
			}
			if (flag4 && num2 < 6)
			{
				if (pspec.strLootIAAdds == null)
				{
					if (HasCond("IsRobot"))
					{
						pspec.strLootIAAdds = "PSPIAAddNPCRobotVenus";
					}
					else if (HasCond("CareerLEOfficer"))
					{
						if (pspec.strHomeworldNow == "OKLG")
						{
							pspec.strLootIAAdds = "PSPIAAddNPCPoliceOKLG";
						}
						else if (pspec.strHomeworldNow == "VNCA" || pspec.strHomeworldNow == "VCBR" || pspec.strHomeworldNow == "VENC")
						{
							pspec.strLootIAAdds = "PSPIAAddNPCPoliceVenus";
						}
					}
					else if (!HasCond("IsPlayer"))
					{
						pspec.strLootIAAdds = "PSPIAAddNPCBasic";
					}
				}
				if (pspec.strLootIAAdds == null)
				{
					pspec.strLootIAAdds = "PSPIAAddPlayer";
				}
				Debug.LogWarning("Repairing missing pledges on " + pspec.strFirstName + " " + pspec.strLastName + ". Found: " + num2 + ". Using " + pspec.strLootIAAdds);
				foreach (string lootName in DataHandler.GetLoot(pspec.strLootIAAdds).GetLootNames())
				{
					Interaction interaction2 = DataHandler.GetInteraction(lootName);
					if (interaction2 != null)
					{
						interaction2.objUs = this;
						interaction2.objThem = this;
						if (interaction2.Triggered(bStats: false, bIgnoreItems: true))
						{
							interaction2.ApplyChain();
						}
					}
				}
			}
		}
		if (jid.strAudioEmitter != null)
		{
			JsonAudioEmitter audioEmitter = DataHandler.GetAudioEmitter(jid.strAudioEmitter);
			if (audioEmitter != null)
			{
				AudioEmitter audioEmitter2 = base.gameObject.AddComponent<AudioEmitter>();
				audioEmitter2.SetData(audioEmitter);
				audioEmitter2.RandomizePitchAll();
				audioEmitter2.FadeInSteady();
			}
		}
		SetUpBehaviours();
	}

	public void ApplyGPMChanges(string[] aGPMChanges)
	{
		if (aGPMChanges == null || aGPMChanges.Length == 0)
		{
			return;
		}
		foreach (string text in aGPMChanges)
		{
			if (string.IsNullOrEmpty(text))
			{
				continue;
			}
			string[] array = text.Split(',');
			if (array.Length >= 3 && !string.IsNullOrEmpty(array[0]) && !string.IsNullOrEmpty(array[1]))
			{
				if (array[0] == "Rename")
				{
					Rename(array[2]);
				}
				Dictionary<string, string> value = null;
				if (!mapGUIPropMaps.TryGetValue(array[0], out value))
				{
					Debug.LogWarning("GPM Not found on CO: " + array[0]);
					value = new Dictionary<string, string>();
					Debug.LogWarning("Adding new GPM to CO: " + array[0] + " : " + strName);
					mapGUIPropMaps[array[0]] = value;
				}
				value[array[1]] = array[2];
			}
		}
	}

	public string GetGPMInfo(string strGPM, string strKey)
	{
		if (string.IsNullOrEmpty(strGPM) || string.IsNullOrEmpty(strKey))
		{
			return null;
		}
		Dictionary<string, string> value = null;
		if (mapGUIPropMaps.TryGetValue(strGPM, out value))
		{
			string value2 = null;
			value.TryGetValue(strKey, out value2);
			return value2;
		}
		return null;
	}

	public void ApplyAModes(string[] aAModeIAs, bool bRebuildQAB)
	{
		if (aAModeIAs == null || aAModeIAs.Length == 0)
		{
			return;
		}
		bool flag = false;
		foreach (string text in aAModeIAs)
		{
			if (string.IsNullOrEmpty(text))
			{
				continue;
			}
			bool flag2 = text.IndexOf('-') == 0;
			string text2 = text;
			if (flag2)
			{
				text2 = text2.Substring(1);
			}
			if (DataHandler.dictInteractions.ContainsKey(text2))
			{
				if (flag2)
				{
					aAttackIAs.Remove(text2);
					flag = true;
				}
				else if (aAttackIAs.IndexOf(text2) < 0)
				{
					aAttackIAs.Add(text2);
					flag = true;
				}
				continue;
			}
			string[] array = text2.Split(';');
			if (array.Length < 2 || string.IsNullOrEmpty(array[1]))
			{
				continue;
			}
			JsonInteraction value = null;
			if (DataHandler.dictInteractions.TryGetValue(array[0], out value))
			{
				JsonInteraction jsonInteraction = value.Clone();
				jsonInteraction.strAttackMode = array[1];
				jsonInteraction.strName = text2;
				if (array.Length >= 3)
				{
					List<string> list = new List<string>(jsonInteraction.aLootItms);
					list.Add("Use," + array[2] + ",false");
					jsonInteraction.aLootItms = list.ToArray();
				}
				DataHandler.dictInteractions[text2] = jsonInteraction;
				if (flag2)
				{
					aAttackIAs.Remove(text2);
					flag = true;
				}
				else if (aAttackIAs.IndexOf(text2) < 0)
				{
					aAttackIAs.Add(text2);
					flag = true;
				}
			}
		}
		if (flag && bRebuildQAB)
		{
			MonoSingleton<GUIQuickBar>.Instance.SetDirty();
		}
	}

	public void AddCommand(string strDef)
	{
		string[] array = strDef.Split(',');
		if (array.Length == 0)
		{
			return;
		}
		if (array[0] == "GasExchange")
		{
			if (array.Length >= 4)
			{
				float result = 0f;
				float.TryParse(array[3], out result);
				GasExchange gasExchange = base.gameObject.AddComponent<GasExchange>();
				gasExchange.SetData(array[1], array[2], result);
				aManUpdates.Add(gasExchange);
			}
		}
		else if (array[0] == "Pledge")
		{
			if (array.Length >= 2)
			{
				JsonPledge pledge = DataHandler.GetPledge(array[1]);
				Pledge2 pledge2 = PledgeFactory.Factory(this, pledge);
				AddPledge(pledge2);
			}
		}
		else if (array[0] == "OnAddCond")
		{
			if (array.Length >= 7)
			{
				dictAddCondEvents[array[1]] = new string[5]
				{
					array[2],
					array[3],
					array[4],
					array[5],
					array[6]
				};
			}
		}
		else if (array[0] == "OnRemoveCond")
		{
			if (array.Length >= 7)
			{
				dictRemoveCondEvents[array[1]] = new string[5]
				{
					array[2],
					array[3],
					array[4],
					array[5],
					array[6]
				};
			}
		}
		else if (array[0] == "GasRespire2")
		{
			if (array.Length >= 3)
			{
				GasPump gasPump = base.gameObject.AddComponent<GasPump>();
				gasPump.SetData(DataHandler.GetGasRespire(array[1]), bRespire: true, bPump: false, array[2]);
				aManUpdates.Add(gasPump);
			}
		}
		else if (array[0] == "GasPump")
		{
			if (array.Length >= 3)
			{
				GasPump gasPump2 = base.gameObject.AddComponent<GasPump>();
				gasPump2.SetData(DataHandler.GetGasRespire(array[1]), bRespire: false, bPump: true, array[2]);
				aManUpdates.Add(gasPump2);
			}
		}
		else if (array[0] == "GasPressureSense")
		{
			if (array.Length >= 2)
			{
				GasPressureSense gasPressureSense = base.gameObject.AddComponent<GasPressureSense>();
				gasPressureSense.SetData(DataHandler.GetGUIPropMap(array[1]));
				aManUpdates.Add(gasPressureSense);
			}
		}
		else if (array[0] == "Sensor")
		{
			if (array.Length >= 2)
			{
				Sensor sensor = base.gameObject.AddComponent<Sensor>();
				sensor.SetData(DataHandler.GetGUIPropMap(array[1]));
				aManUpdates.Add(sensor);
			}
		}
		else if (array[0] == "Destructable")
		{
			if (array.Length >= 2)
			{
				Destructable destructable = base.gameObject.GetComponent<Destructable>();
				if (destructable == null)
				{
					destructable = base.gameObject.AddComponent<Destructable>();
					aManUpdates.Add(destructable);
				}
				destructable.SetData(array);
				if (!aDestructableConds.Contains(array[1]))
				{
					aDestructableConds.Add(array[1]);
				}
			}
		}
		else if (array[0] == "Heater")
		{
			if (array.Length >= 2)
			{
				Heater heater = base.gameObject.AddComponent<Heater>();
				heater.SetData(array[1]);
				aManUpdates.Add(heater);
			}
		}
		else if (array[0] == "Explosion")
		{
			if (array.Length >= 2)
			{
				Explosion explosion = base.gameObject.AddComponent<Explosion>();
				explosion.strType = array[1];
				aManUpdates.Add(explosion);
			}
		}
		else if (array[0] == "Wound")
		{
			if (array.Length >= 2)
			{
				wound = base.gameObject.AddComponent<Wound>();
				wound.SetData(array[1]);
				aManUpdates.Add(wound);
			}
		}
		else if (array[0] == "Electrical")
		{
			if (array.Length >= 2)
			{
				elec = base.gameObject.AddComponent<Electrical>();
				elec.SetData(array);
				aManUpdates.Add(elec);
			}
		}
		else if (array[0] == "Meat")
		{
			Meat item = base.gameObject.AddComponent<Meat>();
			aManUpdates.Add(item);
		}
		else if (array[0] == "Rotor" && array.Length >= 3)
		{
			Rotor rotor = base.gameObject.AddComponent<Rotor>();
			rotor.SetData(this, array[1], array[2]);
			aManUpdates.Add(rotor);
		}
	}

	private void AddTask(string strDuty, string strInteraction)
	{
		Task2 task = new Task2();
		task.strDuty = strDuty;
		task.strInteraction = strInteraction;
		task.strName = strInteraction + strID;
		task.strTargetCOID = strID;
		CrewSim.objInstance.workManager.AddTask(task);
	}

	public void AddPledge(Pledge2 pledge)
	{
		if (pledge == null)
		{
			return;
		}
		if (!dictPledges.ContainsKey(pledge.Priority))
		{
			dictPledges[pledge.Priority] = new List<Pledge2>();
		}
		foreach (Pledge2 item in dictPledges[pledge.Priority])
		{
			if (Pledge2.Same(pledge, item))
			{
				return;
			}
		}
		dictPledges[pledge.Priority].Add(pledge);
	}

	public void RemovePledge(Pledge2 pledge)
	{
		if (pledge == null)
		{
			return;
		}
		foreach (List<Pledge2> value in dictPledges.Values)
		{
			if (value.Contains(pledge))
			{
				value.Remove(pledge);
				break;
			}
		}
	}

	public bool HasPledge(Pledge2 pledge)
	{
		if (pledge == null)
		{
			return false;
		}
		if (!dictPledges.ContainsKey(pledge.Priority))
		{
			return false;
		}
		foreach (Pledge2 item in dictPledges[pledge.Priority])
		{
			if (Pledge2.Same(pledge, item))
			{
				return true;
			}
		}
		return false;
	}

	public bool HasPledge(JsonPledge jp, string strThemID)
	{
		if (jp == null)
		{
			return false;
		}
		if (!dictPledges.ContainsKey(jp.nPriority))
		{
			return false;
		}
		foreach (Pledge2 item in dictPledges[jp.nPriority])
		{
			if (item.Them == null)
			{
				if (strThemID != null)
				{
					return false;
				}
			}
			else if (strThemID != item.Them.strID)
			{
				return false;
			}
			if (Pledge2.Same(item, jp))
			{
				return true;
			}
		}
		return false;
	}

	public List<Pledge2> GetPledgesOfType(JsonPledge jp)
	{
		if (jp == null)
		{
			return new List<Pledge2>();
		}
		if (!dictPledges.ContainsKey(jp.nPriority))
		{
			return new List<Pledge2>();
		}
		List<Pledge2> list = new List<Pledge2>();
		foreach (Pledge2 item in dictPledges[jp.nPriority])
		{
			if (Pledge2.Same(item, jp))
			{
				list.Add(item);
			}
		}
		return list;
	}

	public void AddTicker(JsonTicker jtNew)
	{
		if (jtNew == null || double.IsInfinity(jtNew.fTimeLeft) || double.IsNaN(jtNew.fTimeLeft))
		{
			return;
		}
		if (aTickers.Count == 0)
		{
			fLastICOUpdate = StarSystem.fEpoch;
			jtNew.SetOwner(this);
			aTickers.Add(jtNew);
			if (ship != null && ship.LoadState >= Ship.Loaded.Edit)
			{
				CrewSim.AddTicker(this);
			}
			return;
		}
		if (jtNew.nClampMax > 0)
		{
			int num = 0;
			for (int i = 0; i < aTickers.Count; i++)
			{
				JsonTicker jsonTicker = aTickers[i];
				if (jsonTicker.strName == jtNew.strName)
				{
					if (num == jtNew.nClampMax)
					{
						aTickers.Remove(jsonTicker);
						i--;
					}
					else
					{
						num++;
					}
				}
			}
			if (num >= jtNew.nClampMax)
			{
				return;
			}
		}
		for (int j = 0; j < aTickers.Count; j++)
		{
			if (aTickers[j].fTimeLeft > jtNew.fTimeLeft)
			{
				jtNew.SetOwner(this);
				aTickers.Insert(j, jtNew);
				break;
			}
			if (j == aTickers.Count - 1)
			{
				jtNew.SetOwner(this);
				aTickers.Add(jtNew);
				break;
			}
		}
	}

	public JsonTicker RemoveTicker(string strTicker)
	{
		if (strTicker == null)
		{
			return null;
		}
		JsonTicker jtRemove = null;
		foreach (JsonTicker aTicker in aTickers)
		{
			if (aTicker.strName == strTicker)
			{
				jtRemove = aTicker;
				break;
			}
		}
		return RemoveTicker(jtRemove);
	}

	public JsonTicker RemoveTicker(JsonTicker jtRemove)
	{
		if (jtRemove != null)
		{
			jtRemove.SetOwner(null);
			aTickers.Remove(jtRemove);
		}
		if (aTickers.Count == 0)
		{
			CrewSim.RemoveTicker(this);
		}
		return jtRemove;
	}

	public void SetTicker(string strTicker, float fTimeLeft)
	{
		foreach (JsonTicker aTicker in aTickers)
		{
			if (aTicker.strName == strTicker && (fTimeLeft != 0f || aTicker.fTimeLeft != 0.0))
			{
				aTicker.SetTimeLeft(fTimeLeft);
				RemoveTicker(aTicker);
				AddTicker(aTicker);
				break;
			}
		}
	}

	public double GetTickerTimeleft(string strTicker)
	{
		foreach (JsonTicker aTicker in aTickers)
		{
			if (aTicker.strName == strTicker)
			{
				return aTicker.fTimeLeft;
			}
		}
		return -1.0;
	}

	public JsonTicker GetTicker(string strTicker)
	{
		if (aTickers == null)
		{
			return null;
		}
		foreach (JsonTicker aTicker in aTickers)
		{
			if (aTicker.strName == strTicker)
			{
				return aTicker;
			}
		}
		return null;
	}

	public bool HasTickers()
	{
		return aTickers.Count > 0;
	}

	public void ParseCondLoot(string strLoot, double fCoeff = 1.0)
	{
		string[] aCOs = DataHandler.GetLoot(strLoot).aCOs;
		foreach (string strDef in aCOs)
		{
			ParseCondEquation(strDef, fCoeff);
		}
	}

	public string ParseCondEquation(string strDef, double dCoeff = 1.0, float fCondRuleTrack = 0f)
	{
		if (bFreezeConds || strDef == null)
		{
			return null;
		}
		LootUnit lootUnit = Loot.ParseCondEquation(strDef);
		double num = lootUnit.fMin;
		if (lootUnit.fMax != num)
		{
			num = MathUtils.Rand(lootUnit.fMin, lootUnit.fMax, MathUtils.RandType.Flat);
		}
		if (!lootUnit.bPositive)
		{
			num = 0.0 - num;
		}
		if (lootUnit.strName != "" && num != 0.0)
		{
			AddCondAmount(lootUnit.strName, num * dCoeff, 0.0, fCondRuleTrack);
			return lootUnit.strName;
		}
		return null;
	}

	public void PostGameLoad(Ship.Loaded nLoad)
	{
		if (jCOS != null)
		{
			Crew component = base.gameObject.GetComponent<Crew>();
			if (component != null)
			{
				component.SetBodyFaceSkin(jCOS.strBodyType, jCOS.aFaceParts.Clone() as string[]);
			}
			if (jCOS.aStack != null)
			{
				List<CondOwner> list = new List<CondOwner>();
				string[] array = jCOS.aStack;
				foreach (string text in array)
				{
					CondOwner value = null;
					if (DataHandler.mapCOs.TryGetValue(text, out value))
					{
						if (value.slotNow == null)
						{
							list.Add(value);
						}
					}
					else
					{
						Debug.Log("<color=red>ERROR</color>: Missing stack item: " + jCOS.strFriendlyName + " with id: " + text);
					}
				}
				list.Add(this);
				Container container = null;
				Slot slot = slotNow;
				if (objCOParent != null)
				{
					container = objCOParent.objContainer;
				}
				Ship ship = RemoveFromCurrentHome();
				StackFromList(list);
				if (container != null)
				{
					container.AddCOSimple(this, pairInventoryXY);
				}
				else if (slot != null && slot.compSlots != null)
				{
					slot.compSlots.SlotItem(slot.strName, this);
				}
				else
				{
					ship?.AddCO(this, bTiles: true);
				}
			}
			if (jCOS.aLot != null)
			{
				string[] array = jCOS.aLot;
				foreach (string key in array)
				{
					CondOwner value2 = null;
					DataHandler.mapCOs.TryGetValue(key, out value2);
					if (value2 != null)
					{
						value2.RemoveFromCurrentHome();
						AddLotCO(value2);
					}
				}
			}
			if (Pathfinder != null && jCOS.strDestShip != null)
			{
				Pathfinder.strDestCO = jCOS.strDestCO;
				Pathfinder.strDestShip = jCOS.strDestShip;
				Pathfinder.nDestTile = jCOS.nDestTile;
			}
			if (wound != null)
			{
				wound.PostGameLoad();
			}
			jCOS = null;
		}
		if (aQueue == null)
		{
			Debug.Log("ERROR: Null aQueue on " + strName);
			return;
		}
		foreach (Interaction item in aQueue)
		{
			item.PostGameLoad();
		}
		if (nLoad < Ship.Loaded.Edit)
		{
			return;
		}
		if (aQueue.Count > 0)
		{
			Interaction interaction = aQueue[0];
			if (progressBar != null && interaction.strName != "Walk")
			{
				double num = GetTickerTimeleft(interaction.strName);
				if (num < 0.0)
				{
					num = interaction.fDuration;
				}
				bool showLongbar = interaction.strName != null && DataHandler.dictInstallables2.ContainsKey(interaction.strName);
				progressBar.Activate((float)(num * 3600.0), showLongbar, interaction);
			}
		}
		RefreshAnim();
	}

	public void EndTurn()
	{
		if (tf == null || ship == null)
		{
			return;
		}
		_ = tf.position;
		double num = StarSystem.fEpoch - fLastICOUpdate;
		if (num != 0.0)
		{
			float elapsed = Convert.ToSingle(num);
			aCondsTemp.AddRange(aCondsTimed);
			foreach (Condition item in aCondsTemp)
			{
				item.Update(elapsed, this);
			}
			aCondsTemp.Clear();
		}
		fLastICOUpdate = StarSystem.fEpoch;
		AIHandleCancels();
		bool flag = bAlive && !HasCond("Unconscious");
		CleanupReplies(flag);
		if (CrewSim.GetSelectedCrew() == this)
		{
			UpdateWaitingReplies.Invoke(aReplies);
		}
		if (!bAlive)
		{
			return;
		}
		if (Company != null)
		{
			int hourFromS = MathUtils.GetHourFromS(StarSystem.fEpoch);
			if (hourFromS != MathUtils.GetHourFromS(StarSystem.fEpoch - num))
			{
				ShiftChange(Company.GetShift(hourFromS, this), bSilent: false);
			}
		}
		bool flag2 = GUISocialCombat2.coUs == this || GUISocialCombat2.coThem == this;
		Relationship relationship = null;
		Pledge2 pld = null;
		MonoSingleton<TargetVisController>.Instance.UpdateTargetVis(this, aQueue);
		if (flag && HasCond("IsPledgeChecker") && HasPledgeEmergency(out pld))
		{
			if (pld != null && pld.Do())
			{
				if (RecentWorkHistory == null)
				{
					RecentWorkHistory = new COWorkHistoryDTO();
				}
				RecentWorkHistory.RecordPledge(pld);
			}
		}
		else if (aQueue.Count > 0)
		{
			bool flag3 = false;
			Interaction interaction = aQueue[0];
			if (interaction.strName == "Walk")
			{
				progressBar.DeactivateImmediate();
				if (Pathfinder == null || Pathfinder.InRange())
				{
					interaction.fDuration = 0.0;
				}
			}
			else if (interaction.objThem == null)
			{
				interaction.fDuration = 0.0;
			}
			else if (interaction.strName == "Wait" && interaction.fDuration > 0.0)
			{
				bool flag4 = false;
				foreach (Interaction item2 in interaction.objThem.aQueue)
				{
					if (item2.objThem == this)
					{
						flag4 = true;
						break;
					}
				}
				if (!flag4)
				{
					WaitFor(interaction.objThem, bRelease: true);
				}
			}
			else if (interaction.aSeekItemsForContract != null && interaction.aSeekItemsForContract.Count > 0)
			{
				Interaction interaction2 = null;
				interaction2 = (interaction.bEquip ? DataHandler.GetInteraction("EquipItem") : ((!interaction.bLot && !interaction.bGiveWholeStack) ? DataHandler.GetInteraction("PickupItem") : DataHandler.GetInteraction("PickupItemStack")));
				if (interaction2 != null)
				{
					interaction2.objUs = this;
					interaction2.objThem = interaction.aSeekItemsForContract[0];
					interaction2.bManual = interaction.bManual;
					QueueInteraction(interaction2.objThem, interaction2, bInsert: true);
					interaction.aSeekItemsForContract.RemoveAt(0);
					interaction.bRetestItems = true;
					interaction2.AddDependent(interaction);
					interaction = interaction2;
				}
			}
			else if (interaction.bRetestItems)
			{
				bool bGetItemBefore = interaction.bGetItemBefore;
				bool bVerboseTrigger = interaction.bVerboseTrigger;
				interaction.bGetItemBefore = false;
				interaction.bVerboseTrigger = true;
				if (!interaction.Triggered(interaction.objUs, interaction.objThem))
				{
					string text = interaction.objThem.strName;
					if (interaction.objThem.strNameFriendly != null)
					{
						text = interaction.objThem.strNameFriendly;
					}
					LogMessage(DataHandler.GetString("ERROR_CANT_DO_IA") + interaction.strTitle + ". " + interaction.FailReasons(bUsThem: false, bItems: true, bDebug: false), "Bad", strName);
					Debug.Log(DataHandler.GetString("ERROR_CANT_DO_IA") + interaction.strTitle + "; Target: " + text + ". " + interaction.FailReasons(bUsThem: false, bItems: true, bDebug: true));
					ClearInteraction(interaction);
				}
				else
				{
					interaction.bRetestItems = false;
				}
				if (interaction != null)
				{
					interaction.bGetItemBefore = bGetItemBefore;
					interaction.bVerboseTrigger = bVerboseTrigger;
				}
			}
			else
			{
				Tile tileAtWorldCoords = ship.GetTileAtWorldCoords1(tf.position.x, tf.position.y, bAllowDocked: true);
				Tile tilStart = tileAtWorldCoords;
				if (interaction.strTargetPoint != null && interaction.strTargetPoint != Interaction.POINT_REMOTE)
				{
					Vector2 pos = interaction.objThem.GetPos(interaction.strTargetPoint);
					tilStart = ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
				}
				if (Pathfinder == null)
				{
					if ((float)TileUtils.TileRange(tilStart, tileAtWorldCoords) <= interaction.fTargetPointRange)
					{
						flag3 = true;
					}
				}
				else if (interaction.strTargetPoint == null || interaction.strTargetPoint == Interaction.POINT_REMOTE || Pathfinder.InRange())
				{
					flag3 = true;
				}
				else if (!CheckWalk(interaction, interaction.objThem))
				{
					string text2 = interaction.objThem.strName;
					if (interaction.objThem.strNameFriendly != null)
					{
						text2 = interaction.objThem.strNameFriendly;
					}
					LogMessage(DataHandler.GetString("ERROR_CANT_REACH_DEST") + text2 + ".", "Bad", strName);
					Debug.Log(DataHandler.GetString("ERROR_CANT_REACH_DEST") + interaction.strName + "; Target: " + text2 + ".");
					ClearInteraction(interaction);
				}
			}
			if (flag3)
			{
				if (interaction.fEpochAdded == 0.0)
				{
					interaction.fEpochAdded = StarSystem.fEpoch;
				}
				if (pspec != null && interaction.objThem != this && interaction.objThem.pspec != null)
				{
					relationship = socUs.GetRelationship(interaction.objThem.strName);
					if (relationship == null)
					{
						relationship = socUs.AddStranger(interaction.objThem.pspec);
					}
					SwitchRELConds(relationship, bSilent: true);
				}
				if (interaction.strTeleport != null && interaction.objThem != null && interaction.objThem != this)
				{
					interaction.Teleport(Pathfinder);
				}
				interaction.SetVFX();
				interaction.PlayAudio();
				if (interaction.nLogging != Interaction.Logging.NONE && !interaction.bLogged)
				{
					if (!string.IsNullOrEmpty(interaction.strAnimTrig))
					{
						SetAnimTrigger(interaction.strAnimTrig);
					}
					if (interaction.attackMode != null && interaction.attackMode.bPlayAudioEarly && !string.IsNullOrEmpty(interaction.attackMode.strAudioAttack))
					{
						AudioEmitter component = GetComponent<AudioEmitter>();
						if (component != null)
						{
							component.StartOther(interaction.attackMode.strAudioAttack);
						}
					}
					interaction.ApplyLogging(strName, bTraitSuffix: false);
					if (progressBar != null && interaction.strName != "Walk")
					{
						bool showLongbar = interaction.strName != null && DataHandler.dictInstallables2.ContainsKey(interaction.strName);
						progressBar.Activate((float)(interaction.fDuration * 3600.0), showLongbar, interaction);
					}
					CondOwner selectedCrew = CrewSim.GetSelectedCrew();
					if (interaction.objThem == selectedCrew)
					{
						if (interaction.attackMode != null)
						{
							CrewSim.TriggerAutoPause(DataHandler.GetString("AUTOPAUSE_ATTACK_INCOMING") + interaction.strTitle + DataHandler.GetString("AUTOPAUSE_ATTACK_FROM") + interaction.objUs.FriendlyName);
						}
					}
					else if (interaction.objUs == selectedCrew && interaction.strActionGroup == "Talk" && interaction.objThem != null && !interaction.objThem.HasCond("IsInCombat"))
					{
						Interaction interactionCurrent = interaction.objThem.GetInteractionCurrent();
						if (interactionCurrent == null || interactionCurrent.strName == "Walk" || interactionCurrent.strName == "QuickWait")
						{
							interaction.objThem.AICancelAll(this);
							interaction.objThem.QueueInteraction(this, DataHandler.GetInteraction("QuickWait"));
						}
					}
					if (flag2 && interaction.strName != "Wait")
					{
						CrewSim.objInstance.CamCenter(this);
						if (CanvasManager.instance.State == CanvasManager.GUIState.SOCIAL)
						{
							GUISocialCombat2.objInstance.ThrobOn(this);
						}
					}
				}
				if ((interaction.strRaiseUI != null || interaction.strRaiseUIThem != null) && !interaction.bRaisedUI)
				{
					if (interaction.bUsePDA)
					{
						GUIPDA.UIState stateFromString = GUIPDA.GetStateFromString(GetGPMInfo(interaction.strRaiseUI, "strGUIPrefab"));
						GUIPDA.instance.State = stateFromString;
					}
					else if (interaction.strRaiseUI != null)
					{
						CrewSim.RaiseUI(interaction.strRaiseUI, this);
					}
					else
					{
						CrewSim.RaiseUI(interaction.strRaiseUIThem, interaction.objThem);
					}
					interaction.bRaisedUI = true;
				}
				if (Pathfinder != null && interaction.objThem != null && interaction.objThem != this)
				{
					LookAt(interaction.objThem);
				}
				interaction.fDuration -= num / 60.0 / 60.0;
			}
			if (!(interaction.fDuration <= 0.0))
			{
				return;
			}
			if ((interaction.strRaiseUI != null || interaction.strRaiseUIThem != null) && interaction.bRaisedUI)
			{
				CrewSim.LowerUI();
			}
			CondOwner objThem = interaction.objThem;
			if (objThem != null)
			{
				string strIAName = interaction.strName;
				bool flag5 = interaction.strName == "Wait" || interaction.strName == "Walk";
				bool bCloser = interaction.bCloser;
				Interaction interaction3 = Interact();
				if (interaction3 != null)
				{
					if (interaction3.objUs.CheckWalk(interaction3, interaction3.objThem))
					{
						interaction3.objUs.QueueInteraction(interaction3.objThem, interaction3);
					}
					else
					{
						string text3 = interaction3.objThem.strName;
						if (interaction3.objThem.strNameFriendly != null)
						{
							text3 = interaction3.objThem.strNameFriendly;
						}
						interaction3.objUs.LogMessage(DataHandler.GetString("ERROR_CANT_REACH_DEST") + text3 + ".", "Bad", strName);
						Debug.Log(DataHandler.GetString("ERROR_CANT_REACH_DEST") + interaction3.strName + "; Target: " + text3 + ".");
						interaction3 = null;
					}
				}
				if (flag2 && !flag5)
				{
					if (GUISocialCombat2.coThem != null && !GUISocialCombat2.coThem.bAlive)
					{
						GUISocialCombat2.objInstance.EndSocialCombat();
					}
					else if (interaction3 == null)
					{
						if (bCloser)
						{
							GUISocialCombat2.objInstance.EndSocialCombat();
						}
						else
						{
							GUISocialCombat2.ResetSocialCombat(this);
						}
					}
				}
				bool flag6 = false;
				foreach (ReplyThread aReply in aReplies)
				{
					if (aReply != null && (bool)objThem && aReply.Fulfills(strIAName, objThem.strID))
					{
						aReply.bDone = true;
						flag6 = true;
					}
				}
				if (flag6 && CrewSim.GetSelectedCrew() == this)
				{
					UpdateWaitingReplies.Invoke(aReplies);
				}
			}
			else
			{
				ClearInteraction(interaction);
			}
			CondOwner selectedCrew2 = CrewSim.GetSelectedCrew();
			if ((selectedCrew2 != null && selectedCrew2 == this) || MonoSingleton<GUIQuickBar>.Instance.COTarget == this || interaction.objThem == selectedCrew2)
			{
				ModuleHost.UpdateUI.Invoke();
				MonoSingleton<GUIQuickBar>.Instance.SetDirty();
			}
		}
		else
		{
			if (flag2 || !flag)
			{
				return;
			}
			if (progressBar != null)
			{
				progressBar.DeactivateImmediate();
			}
			bool flag7 = false;
			if (socUs != null && strLastSocial != null)
			{
				SwitchRELConds(null, bSilent: true);
			}
			if (ship != null && HasCond("IsPledgeChecker"))
			{
				for (int num2 = 11; num2 > 0; num2--)
				{
					if (dictPledges.ContainsKey(num2))
					{
						if (dictPledges[num2].Count == 0)
						{
							continue;
						}
						Pledge2[] array = new Pledge2[dictPledges[num2].Count];
						dictPledges[num2].CopyTo(array);
						Pledge2[] array2 = array;
						foreach (Pledge2 pledge in array2)
						{
							flag7 = pledge.Do();
							if (dictPledges[num2].Contains(pledge))
							{
								dictPledges[num2].Remove(pledge);
								dictPledges[num2].Add(pledge);
							}
							if (flag7)
							{
								if (RecentWorkHistory == null)
								{
									RecentWorkHistory = new COWorkHistoryDTO();
								}
								RecentWorkHistory.RecordPledge(pledge);
								break;
							}
						}
					}
					if (flag7)
					{
						break;
					}
				}
			}
			if (flag7 || !IsHumanOrRobot)
			{
				return;
			}
			if (nEndTurnsThisFrame > 0)
			{
				JsonTicker jsonTicker = new JsonTicker();
				jsonTicker.strName = "AINudge";
				jsonTicker.bQueue = true;
				jsonTicker.fPeriod = 2.7800000680144876E-05;
				jsonTicker.SetTimeLeft(jsonTicker.fPeriod);
				AddTicker(jsonTicker);
				return;
			}
			ZeroCondAmount("IsEmergencyOverride");
			UpdateAutoEmergency.Invoke(arg0: false, EmergencyReason.Unknown);
			if (aReplies.Count <= 0 && !HasCond("InSocialCombat"))
			{
				if (jsShiftLast.nID == 2)
				{
					GetWork();
				}
				else
				{
					GetMove2();
				}
			}
			nEndTurnsThisFrame++;
		}
	}

	public void SwitchRELConds(Relationship relNew, bool bSilent)
	{
		if (strLastSocial != null)
		{
			Relationship relationship = socUs.GetRelationship(strLastSocial);
			if (relationship != null)
			{
				if (relationship == relNew)
				{
					return;
				}
				if (!bSilent)
				{
					if (relNew != null)
					{
						Debug.Log(STR_AI_REL_SWITCH + relNew.pspec.FullName + STR_AI_REL_SWITCH_END);
						LogMessage(STR_AI_REL_SWITCH + relNew.pspec.FullName + STR_AI_REL_SWITCH_END, "Neutral", strID, "->" + relNew.pspec.strFirstName);
					}
					else
					{
						Debug.Log(STR_AI_REL_SWITCH + STR_AI_REL_SWITCH_NOBODY + STR_AI_REL_SWITCH_END);
						LogMessage(STR_AI_REL_SWITCH + STR_AI_REL_SWITCH_NOBODY + STR_AI_REL_SWITCH_END, "Neutral", strID, "->?");
					}
				}
				bool flag = bLogConds;
				if (bSilent)
				{
					bLogConds = false;
				}
				relationship.ApplyConds(this, bRemove: true);
				bLogConds = flag;
			}
			strLastSocial = null;
		}
		if (relNew != null && relNew.pspec.FullName != strLastSocial)
		{
			bool flag2 = bLogConds;
			if (bSilent)
			{
				bLogConds = false;
			}
			relNew.ApplyConds(this);
			bLogConds = flag2;
			strLastSocial = relNew.pspec.FullName;
		}
	}

	private void CleanupReplies(bool bConscious)
	{
		for (int num = aReplies.Count - 1; num >= 0; num--)
		{
			bool flag = false;
			if (DataHandler.mapCOs.TryGetValue(aReplies[num].strID, out var value) && (!bConscious || value.HasCond("Unconscious") || !value.bAlive))
			{
				Interaction interaction = DataHandler.GetInteraction("SocialCombatExitSilent");
				interaction.objUs = this;
				interaction.objThem = value;
				interaction.ApplyChain();
				flag = true;
			}
			if (flag || aReplies[num].bDone || StarSystem.fEpoch - aReplies[num].fEpoch > 30.0)
			{
				aReplies.RemoveAt(num);
			}
		}
	}

	private bool HasPledgeEmergency(out Pledge2 pld)
	{
		pld = null;
		for (int num = 11; num > 0; num--)
		{
			if (dictPledges.ContainsKey(num))
			{
				foreach (Pledge2 item in dictPledges[num])
				{
					if (item != null && item.IsEmergency())
					{
						pld = item;
						return true;
					}
				}
			}
		}
		return false;
	}

	public void ShiftChange(JsonShift js, bool bSilent)
	{
		if (jsShiftLast == null)
		{
			jsShiftLast = JsonCompany.NullShift;
		}
		if (js == null)
		{
			js = JsonCompany.NullShift;
		}
		if (js.nID != jsShiftLast.nID)
		{
			bool flag = bLogConds;
			bLogConds = !bSilent;
			Loot loot = DataHandler.GetLoot(js.strCondLoot);
			string[] aCOs = DataHandler.GetLoot(jsShiftLast.strCondLoot).aCOs;
			foreach (string strDef in aCOs)
			{
				ParseCondEquation(strDef, -1.0);
			}
			aCOs = loot.aCOs;
			foreach (string strDef2 in aCOs)
			{
				ParseCondEquation(strDef2);
			}
			jsShiftLast = js;
			if (!bSilent)
			{
				LogMessage(FriendlyName + DataHandler.GetString("SHIFT_CHANGE") + js.strName.Replace("CONDShift", "") + ".", "Neutral", strName);
			}
			PlayerMarker.AddMarker(this);
			bLogConds = flag;
		}
	}

	private void GetWork()
	{
		if (ship == null || !IsHumanOrRobot)
		{
			return;
		}
		FreeWillLoot.ApplyCondLoot(this, 1f);
		if (!HasCond("IsPlayer") && Company == CrewSim.coPlayer.Company)
		{
			Interaction interaction = DataHandler.GetInteraction("SeekSocialDeny");
			interaction.objUs = this;
			interaction.objThem = CrewSim.coPlayer;
			if (interaction.Triggered(interaction.objUs, interaction.objThem))
			{
				Pathfinder.Reset();
				QueueInteraction(interaction.objThem, interaction);
				CrewSim.objInstance.workManager.IdleAdd(this);
				return;
			}
		}
		Task2 task = CrewSim.objInstance.workManager.ClaimNextTask(this);
		if (task != null)
		{
			if (task.strInteraction == "QuickWait")
			{
				return;
			}
			if (task.strInteraction == "ACTHaulItem")
			{
				if (HandleHaulTask(task))
				{
					return;
				}
			}
			else if (task.strInteraction.StartsWith("ACTFeedItem"))
			{
				if (HandleFeedTask(task))
				{
					return;
				}
			}
			else
			{
				QueueInteraction(task.GetIA().objThem, task.GetIA());
			}
			CrewSim.objInstance.workManager.IdleRemove(this);
		}
		else
		{
			CrewSim.objInstance.workManager.IdleAdd(this);
			bool flag = HasCond("IsAIManual");
			bool flag2 = true;
			if (Company != null)
			{
				flag2 = Company.mapRoster[strID].bRestorePermission;
			}
			if ((!(!flag && flag2) || !ProcessAutoTasks()) && !HasCond("IsPlayer") && (!(CrewSim.GetSelectedCrew() == this) || !flag) && !flag)
			{
				GetMove2();
			}
		}
	}

	private bool ProcessAutoTasks()
	{
		List<CondOwner> list = new List<CondOwner>();
		if (OwnsShip(ship.strRegID))
		{
			list.AddRange(ship.GetCOs(ctRestoreItem, bSubObjects: true, bAllowDocked: false, bAllowLocked: true));
		}
		if (aATsPatch == null)
		{
			aATsPatch = new List<AutoTask>();
		}
		else
		{
			aATsPatch.Clear();
		}
		if (aATsRepair == null)
		{
			aATsRepair = new List<AutoTask>();
		}
		else
		{
			aATsRepair.Clear();
		}
		if (aATsRestore == null)
		{
			aATsRestore = new List<AutoTask>();
		}
		else
		{
			aATsRestore.Clear();
		}
		double num = 1.0;
		double num2 = 1.0;
		double num3 = 1.0;
		if (Company != null)
		{
			num = Math.Pow(10.0, Company.GetDutyLevel(this, "Patch"));
			num2 = Math.Pow(10.0, Company.GetDutyLevel(this, "Restore"));
			num3 = Math.Pow(10.0, Company.GetDutyLevel(this, "Repair"));
		}
		num += 0.0;
		num3 += 1.0;
		num2 += 2.0;
		foreach (CondOwner item in list)
		{
			if (item.bCanPatch)
			{
				foreach (string aInteraction in item.aInteractions)
				{
					if (aInteraction.Contains("Patch") && !aInteraction.Contains("Scrap"))
					{
						InsertUndamage(item, aInteraction, doRepair: true, num, aATsPatch);
						break;
					}
				}
			}
			if (item.bCanRepair)
			{
				foreach (string aInteraction2 in item.aInteractions)
				{
					if (aInteraction2.Contains("Repair"))
					{
						InsertUndamage(item, aInteraction2, doRepair: true, num3, aATsRepair);
						break;
					}
				}
			}
			if (!item.bCanUndamage)
			{
				continue;
			}
			foreach (string aInteraction3 in item.aInteractions)
			{
				if (aInteraction3.Contains("Undamage"))
				{
					InsertUndamage(item, aInteraction3, doRepair: false, num2, aATsRestore);
					break;
				}
			}
		}
		if (aATsPatch.Count + aATsRepair.Count + aATsRestore.Count > 0)
		{
			if (num > num3)
			{
				if (num3 > num2)
				{
					aATsRestore.AddRange(aATsRepair);
					aATsRestore.AddRange(aATsPatch);
				}
				else
				{
					if (num2 < num)
					{
						aATsRepair.AddRange(aATsRestore);
						aATsRepair.AddRange(aATsPatch);
					}
					else
					{
						aATsRepair.AddRange(aATsPatch);
						aATsRepair.AddRange(aATsRestore);
					}
					aATsRestore = aATsRepair;
				}
			}
			else if (num3 < num2)
			{
				aATsPatch.AddRange(aATsRepair);
				aATsPatch.AddRange(aATsRestore);
				aATsRestore = aATsPatch;
			}
			else if (num2 < num)
			{
				aATsRestore.AddRange(aATsPatch);
				aATsRestore.AddRange(aATsRepair);
			}
			else
			{
				aATsPatch.AddRange(aATsRestore);
				aATsPatch.AddRange(aATsRepair);
				aATsRestore = aATsPatch;
			}
			int num4 = Mathf.Min(aATsRestore.Count, 2);
			string text = null;
			for (int i = 0; i < num4; i++)
			{
				CondOwner co = aATsRestore[i].co;
				Interaction interaction = DataHandler.GetInteraction(aATsRestore[i].strIA);
				interaction.bHumanOnly = false;
				if (i == num4 - 1)
				{
					interaction.bVerboseTrigger = true;
				}
				dictRecentlyTried[co.strID + interaction.strName] = StarSystem.fEpoch;
				if (interaction.Triggered(this, co, bStats: false, bIgnoreItems: false, bCheckPath: true))
				{
					QueueInteraction(co, interaction);
					return true;
				}
				text = "Auto " + interaction.strTitle + " " + co.strNameFriendly + ": " + interaction.FailReasons(bUsThem: true, bItems: true, bDebug: false);
			}
			if (!string.IsNullOrEmpty(text))
			{
				if (RecentWorkHistory == null)
				{
					RecentWorkHistory = new COWorkHistoryDTO();
				}
				RecentWorkHistory.RecordFailedWorkAttempt(text);
			}
		}
		return false;
	}

	private bool HandleHaulTask(Task2 task)
	{
		Interaction iA = task.GetIA();
		if (iA == null)
		{
			return true;
		}
		CondOwner objThem = iA.objThem;
		if (objThem == null)
		{
			return true;
		}
		if (!WorkManager.CTHaul.Triggered(objThem))
		{
			return true;
		}
		Tile tile = null;
		Ship shipByRegID = CrewSim.system.GetShipByRegID(task.strTileShip);
		if (shipByRegID != null && shipByRegID.aTiles != null)
		{
			if (shipByRegID.aTiles.Count > task.nTile)
			{
				tile = shipByRegID.aTiles[task.nTile];
			}
			else if (task.AssignHaulZone(this, objThem) != null)
			{
				tile = ship.aTiles[task.nTile];
				shipByRegID = CrewSim.system.GetShipByRegID(task.strTileShip);
				if (shipByRegID == null || shipByRegID.aTiles == null)
				{
					return false;
				}
			}
		}
		if (tile == null)
		{
			if (RecentWorkHistory == null)
			{
				RecentWorkHistory = new COWorkHistoryDTO();
			}
			RecentWorkHistory.RecordFailedWorkAttempt("Haul Item, destination unreachable");
			CrewSim.objInstance.workManager.UnclaimTask(task);
			CrewSim.objInstance.workManager.IdleAdd(this);
			return true;
		}
		List<Task2> list = CrewSim.objInstance.workManager.CollectBatchHaulTasks(this, task, objThem, task.strTileShip);
		Interaction interaction = DataHandler.GetInteraction("PickupItemStack");
		QueueInteraction(objThem, interaction);
		task.strInteraction = interaction.strName;
		Dictionary<Task2, CondOwner> dictionary = new Dictionary<Task2, CondOwner>();
		foreach (Task2 item in list)
		{
			if (DataHandler.mapCOs.TryGetValue(item.strTargetCOID, out var value) && !(value == null))
			{
				Interaction interaction2 = DataHandler.GetInteraction("PickupItemStack");
				CrewSim.objInstance.workManager.ClaimBatchTask(item, interaction2, value);
				QueueInteraction(value, interaction2);
				item.strInteraction = interaction2.strName;
				dictionary[item] = value;
			}
		}
		Interaction interaction3 = DataHandler.GetInteraction("Walk");
		interaction3.strTargetPoint = "use";
		interaction3.fTargetPointRange = 0f;
		QueueInteraction(tile.coProps, interaction3);
		Interaction interaction4 = DataHandler.GetInteraction("DropItemStack");
		QueueInteraction(objThem, interaction4);
		task.SetIA(interaction4);
		foreach (KeyValuePair<Task2, CondOwner> item2 in dictionary)
		{
			Interaction interaction5 = DataHandler.GetInteraction("DropItemStack");
			QueueInteraction(item2.Value, interaction5);
			item2.Key.SetIA(interaction5);
		}
		return false;
	}

	private bool HandleFeedTask(Task2 task)
	{
		Interaction iA = task.GetIA();
		if (iA == null)
		{
			return true;
		}
		CondOwner objThem = iA.objThem;
		if (objThem == null)
		{
			return true;
		}
		if (!iA.Triggered(this, objThem, bStats: false, bIgnoreItems: false, bCheckPath: true, bFetchItems: false))
		{
			QueueInteraction(objThem, iA);
			return false;
		}
		List<CondOwner> list = ((iA.aSeekItemsForContract != null) ? new List<CondOwner>(iA.aSeekItemsForContract) : new List<CondOwner>());
		if (iA.aLootItemGiveContract != null && iA.aLootItemGiveContract.Count > 0)
		{
			foreach (CondOwner item in iA.aLootItemGiveContract)
			{
				if (!list.Contains(item))
				{
					list.Add(item);
				}
			}
		}
		Dictionary<Task2, CondOwner> dictionary = CrewSim.objInstance.workManager.CollectBatchFeedTasks(this, task, objThem, list);
		HashSet<CondOwner> hashSet = new HashSet<CondOwner>();
		foreach (CondOwner item2 in list)
		{
			hashSet.Add(item2);
		}
		foreach (CondOwner value2 in dictionary.Values)
		{
			hashSet.Add(value2);
		}
		List<CondOwner> list2 = new List<CondOwner>(hashSet);
		if (list2.Count > 0 && !CanTakeItemsSimulated(list2))
		{
			QueueInteraction(objThem, iA);
			return false;
		}
		if (iA.aSeekItemsForContract != null)
		{
			iA.aSeekItemsForContract.Clear();
			iA.bRetestItems = true;
		}
		foreach (CondOwner item3 in list2)
		{
			Interaction interaction = DataHandler.GetInteraction("PickupItem");
			QueueInteraction(item3, interaction, bInsert: true);
			interaction.AddDependent(iA);
		}
		Interaction interaction2 = DataHandler.GetInteraction("Walk");
		interaction2.strTargetPoint = "use";
		interaction2.fTargetPointRange = 0f;
		QueueInteraction(objThem, interaction2);
		iA.aLootItemGiveContract = new List<CondOwner>(list);
		QueueInteraction(objThem, iA);
		task.SetIA(iA);
		foreach (KeyValuePair<Task2, CondOwner> item4 in dictionary)
		{
			Task2 key = item4.Key;
			CondOwner value = item4.Value;
			Interaction interaction3 = DataHandler.GetInteraction(key.strInteraction);
			interaction3.aLootItemGiveContract = new List<CondOwner> { value };
			CrewSim.objInstance.workManager.ClaimBatchTask(key, interaction3, objThem);
			QueueInteraction(objThem, interaction3);
			key.SetIA(interaction3);
		}
		return false;
	}

	public CondOwner GetNearestTriggered(CondTrigger ct, List<CondOwner> aCOsHayStack, string strPersistentCO, string strUseCase, bool bManual, Interaction ia, out List<string> aOutUseFails)
	{
		aOutUseFails = new List<string>();
		if (aCOsHayStack == null)
		{
			return null;
		}
		float num = float.PositiveInfinity;
		Tile tileAtWorldCoords = CrewSim.shipCurrentLoaded.GetTileAtWorldCoords1(tf.position.x, tf.position.y, bAllowDocked: true);
		CondOwner condOwner = null;
		List<CondOwner> list = new List<CondOwner>();
		List<Tile> list2 = new List<Tile>();
		List<string> list3 = new List<string>();
		foreach (CondOwner item in aCOsHayStack)
		{
			if (!ct.Triggered(item, null, logOutcome: false))
			{
				continue;
			}
			if (!string.IsNullOrEmpty(strUseCase) && !item.Usable(strUseCase, out var strOut))
			{
				if (!string.IsNullOrEmpty(strOut))
				{
					list3.Add(strOut);
				}
				continue;
			}
			if (strPersistentCO != null && item.strID == strPersistentCO)
			{
				return item;
			}
			if (item.slotNow != null && item.objCOParent == this)
			{
				return item;
			}
			Vector2 pos = item.GetPos("use");
			Vector2 pos2 = GetPos("use");
			Tile tile = null;
			if (pos == pos2)
			{
				return item;
			}
			tile = ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
			if (tileAtWorldCoords == tile)
			{
				return item;
			}
			if (list2.IndexOf(tile) < 0)
			{
				list.Add(item);
				list2.Add(tile);
			}
		}
		list2 = null;
		bool flag = Pathfinder == null;
		int num2 = (flag ? int.MaxValue : 50);
		List<Ostranauts.Core.Models.Tuple<double, CondOwner>> list4 = null;
		if (!flag && list.Count > 10)
		{
			Vector2 b = tileAtWorldCoords.tf.position.ToVector2();
			list4 = new List<Ostranauts.Core.Models.Tuple<double, CondOwner>>();
			foreach (CondOwner item2 in list)
			{
				list4.Add(new Ostranauts.Core.Models.Tuple<double, CondOwner>(Vector2.Distance(item2.tf.position.ToVector2(), b), item2));
			}
			list4 = list4.OrderBy((Ostranauts.Core.Models.Tuple<double, CondOwner> tuple) => tuple.Item1).ToList();
			list = list4.Select((Ostranauts.Core.Models.Tuple<double, CondOwner> tuple) => tuple.Item2).ToList();
			num2 = 10;
		}
		bool bAllowAirlocks = !flag && HasAirlockPermission(bManual);
		for (int num3 = 0; num3 < list.Count; num3++)
		{
			if (num2 <= 0)
			{
				break;
			}
			CondOwner condOwner2 = list[num3];
			float num4 = 0f;
			PathResult pathResult = null;
			if (flag)
			{
				num4 = (condOwner2.tf.position - tf.position).sqrMagnitude;
			}
			else
			{
				Vector2 pos3 = condOwner2.GetPos("use");
				Tile tileAtWorldCoords2 = ship.GetTileAtWorldCoords1(pos3.x, pos3.y, bAllowDocked: true);
				if (tileAtWorldCoords == tileAtWorldCoords2)
				{
					num4 = 0f;
				}
				else
				{
					pathResult = Pathfinder.CheckGoal(tileAtWorldCoords2, 1f, condOwner2, bAllowAirlocks);
					num4 = pathResult.PathLength;
				}
			}
			if (num4 < 0f)
			{
				if (pathResult != null && ia != null)
				{
					string text = pathResult.FailReason(this);
					if (!string.IsNullOrEmpty(text))
					{
						ia.AddFailReason("items", text);
					}
					if (pathResult.bAirlockBlocked)
					{
						ia.bAirlockBlocked = pathResult.bAirlockBlocked;
					}
				}
			}
			else
			{
				if (list4 == null || num3 >= list4.Count || (double)num4 <= list4[num3].Item1 * 2.0)
				{
					num2--;
				}
				if (!(num <= num4))
				{
					num = num4;
					condOwner = condOwner2;
				}
			}
		}
		if (condOwner == null)
		{
			aOutUseFails = list3;
		}
		return condOwner;
	}

	private void InsertUndamage(CondOwner co, string strUndamageIA, bool doRepair, double fDutyWeight, List<AutoTask> aATs)
	{
		string key = co.strID + strUndamageIA;
		if (dictRecentlyTried.ContainsKey(key) || (!doRepair && co.GetIsLikeNew()))
		{
			return;
		}
		double damageState = co.GetDamageState();
		double num = (co.GetPos() - GetPos()).magnitude;
		if (num < 2.0)
		{
			num = 0.5;
		}
		double num2 = num * damageState * damageState * fDutyWeight;
		int num3 = 0;
		using (List<AutoTask>.Enumerator enumerator = aATs.GetEnumerator())
		{
			while (enumerator.MoveNext() && enumerator.Current.fWeight < num2)
			{
				num3++;
			}
		}
		aATs.Insert(num3, new AutoTask(co, strUndamageIA, num2));
	}

	public void DebugKickstart()
	{
		Debug.Log(debugStop);
		GetMove2();
	}

	public bool HasAirlockPermission(bool bManual)
	{
		bool flag = !HasCond("IsAIManual");
		if (HasCond("IsEmergencyOverride"))
		{
			return true;
		}
		if (!flag && ctSuffocatingManWalk.Triggered(this))
		{
			return true;
		}
		bool flag2 = false;
		JsonCompanyRules value = null;
		if (Company != null && Company.mapRoster.TryGetValue(strID, out value))
		{
			flag2 = value.bAirlockPermission;
		}
		if (!flag2)
		{
			return false;
		}
		if (bManual && !flag)
		{
			return true;
		}
		if (HasCond("IsAirtight") || HasCond("IsAirtightFake"))
		{
			return true;
		}
		return false;
	}

	public bool HasShoreLeave()
	{
		bool result = true;
		if (!HasCond("IsEmergencyOverride") && !HasCond("IsTempDraftedLong") && (!(CrewSim.coPlayer != null) || Company == CrewSim.coPlayer.Company || ship == null || ship != CrewSim.coPlayer.ship || !CrewSim.coPlayer.OwnsShip(ship.strRegID)))
		{
			if (Company != null)
			{
				if (Company.mapRoster.ContainsKey(strID) && !Company.mapRoster[strID].bShoreLeave)
				{
					result = false;
				}
			}
			else
			{
				result = false;
			}
		}
		return result;
	}

	private void GetMove2()
	{
		if (debugStop || aInteractions.Count == 0 || ship == null || !IsHumanOrRobot || (HasCond("IsPlayerCrew") && HasCond("IsAIManual")))
		{
			return;
		}
		float num = 0f;
		float num2 = 0f;
		CondOwner condOwner = null;
		Interaction interaction = null;
		bool flag = false;
		string text = null;
		if (socUs == null)
		{
			socUs = base.gameObject.AddComponent<Social>();
		}
		Relationship relationship = null;
		bool flag2 = CTPlayerCrew.Triggered(this);
		bool flag3 = HasAirlockPermission(bManual: false);
		Dictionary<string, List<CondOwner>> dictionary = new Dictionary<string, List<CondOwner>>();
		bool flag4 = false;
		if (flag4)
		{
			CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsAIRandomTrainerItem");
			List<CondOwner> list = null;
			if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) > 0.5)
			{
				list = ship.GetCOs(condTrigger, bSubObjects: true, bAllowDocked: false, bAllowLocked: false);
			}
			else
			{
				list = ship.GetPeople(bAllowDocked: false);
				list.Remove(this);
			}
			for (int i = 0; i < 10; i++)
			{
				if (list.Count == 0)
				{
					break;
				}
				CondOwner condOwner2 = list[MathUtils.Rand(0, list.Count - 1, MathUtils.RandType.Flat)];
				if (condOwner2.aInteractions.Count == 0)
				{
					continue;
				}
				if (socUs != null && condOwner2.socUs != null && socUs != condOwner2.socUs)
				{
					relationship = socUs.GetRelationship(condOwner2.strID);
					if (relationship != null)
					{
						SwitchRELConds(relationship, bSilent: true);
					}
				}
				interaction = ((!HasCond("IsSocialGreeted")) ? DataHandler.GetInteraction("SOCGreetAI", null, getTrackedObject: true) : DataHandler.GetInteraction(condOwner2.aInteractions[MathUtils.Rand(0, condOwner2.aInteractions.Count - 1, MathUtils.RandType.Flat)], null, getTrackedObject: true));
				if (interaction != null)
				{
					if (interaction.bOpener && !interaction.bHumanOnly && !aAIRandomAvoid.Contains(interaction.strName) && interaction.Triggered(this, condOwner2))
					{
						condOwner = condOwner2;
						Debug.Log("Random chose: " + interaction.strName + " on " + condOwner.strName);
						break;
					}
					DataHandler.ReleaseTrackedInteraction(interaction);
					interaction = null;
				}
			}
		}
		List<Priority> list2 = new List<Priority>(aPriorities);
		if (jsShiftLast != null && jsShiftLast.nID == 1 && HasCond("StatSleep") && DataHandler.GetCondTrigger("TIsSleepy").Triggered(this))
		{
			Priority item = new Priority(-500.0, mapConds["StatSleep"]);
			list2.Insert(0, item);
		}
		foreach (Priority item2 in list2)
		{
			if (flag4)
			{
				break;
			}
			if (!mapConds.ContainsValue(item2.objCond))
			{
				continue;
			}
			List<InteractionHistory> list3 = new List<InteractionHistory>();
			foreach (InteractionHistory value3 in GetCH(item2.objCond.strName).mapInteractions.Values)
			{
				if (aAIRandomAvoid.Contains(value3.strName))
				{
					continue;
				}
				Interaction interaction2 = DataHandler.GetInteraction(value3.strName, null, getTrackedObject: true);
				if (interaction2 == null || interaction2.bHumanOnly || !interaction2.bOpener || interaction2.attackMode != null || !interaction2.CTTestUs.Triggered(this))
				{
					DataHandler.ReleaseTrackedInteraction(interaction2);
					continue;
				}
				if (value3.fAverage < 0f)
				{
					if (list3.Count == 0)
					{
						list3.Add(value3);
					}
					else if (value3.fAverage <= list3[0].fAverage)
					{
						list3.Insert(0, value3);
					}
					else if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) <= 0.2)
					{
						list3.Insert(list3.Count, value3);
					}
				}
				DataHandler.ReleaseTrackedInteraction(interaction2);
			}
			foreach (InteractionHistory item3 in list3)
			{
				Interaction interaction3 = DataHandler.GetInteraction(item3.strName, null, getTrackedObject: true);
				if (interaction3.CTTestThem != null)
				{
					interaction3.CTTestThem.logReason = false;
				}
				List<CondOwner> list4;
				if (interaction3.strThemType == Interaction.TARGET_SELF)
				{
					list4 = new List<CondOwner>();
					if (interaction3.CTTestThem.Triggered(this))
					{
						list4.Add(this);
					}
				}
				else if (interaction3.strThemType == Interaction.TARGET_OTHER)
				{
					if (interaction3.PSpecTestThem != null)
					{
						list4 = new List<CondOwner>();
						PersonSpec person = ship.GetPerson(interaction3.PSpecTestThem, socUs, bForceUnrelated: false);
						if (person != null)
						{
							list4.Add(person.MakeCondOwner(PersonSpec.StartShip.OLD));
						}
					}
					else
					{
						list4 = GetCOsSafe(bAllowLocked: true, interaction3.CTTestThem);
						if (dictionary.TryGetValue(interaction3.CTTestThem.strName, out var value))
						{
							list4.AddRange(value);
						}
						else
						{
							value = ship.GetCOs(interaction3.CTTestThem, bSubObjects: false, bAllowDocked: true, bAllowLocked: false);
							dictionary.Add(interaction3.CTTestThem.strName, value);
							list4.AddRange(value);
						}
						list4.Remove(this);
					}
				}
				else
				{
					list4 = new List<CondOwner>();
				}
				if (interaction3.CTTestThem != null)
				{
					interaction3.CTTestThem.logReason = true;
				}
				for (int num3 = list4.Count - 1; num3 >= 0; num3--)
				{
					CondOwner condOwner3 = list4[num3];
					if (condOwner3 == null || condOwner3.bBusy)
					{
						list4.RemoveAt(num3);
						continue;
					}
					if (!flag2 && condOwner3.ship != null && CrewSim.coPlayer.aMyShips.Contains(condOwner3.ship.strRegID))
					{
						list4.RemoveAt(num3);
						continue;
					}
					text = condOwner3.strID + interaction3.strName;
					if (dictRecentlyTried.ContainsKey(text))
					{
						list4.RemoveAt(num3);
						continue;
					}
					bool flag5 = false;
					if (condOwner3 != this && condOwner3 == CrewSim.GetSelectedCrew())
					{
						if (GUISocialCombat2.coUs == condOwner3 || GUISocialCombat2.coThem == condOwner3)
						{
							list4.RemoveAt(num3);
							continue;
						}
						if (condOwner3.jsShiftLast != null && condOwner3.jsShiftLast.nID > 0)
						{
							flag5 = true;
						}
					}
					else if (condOwner3 != this && condOwner3.jsShiftLast != null && condOwner3.jsShiftLast.nID > 0)
					{
						flag5 = true;
					}
					if (flag5)
					{
						list4.RemoveAt(num3);
					}
				}
				int num4 = Mathf.Min(10, list4.Count);
				for (int j = 0; j < num4; j++)
				{
					int index = Mathf.RoundToInt(UnityEngine.Random.value * (float)(list4.Count - 1));
					CondOwner condOwner4 = list4[index];
					if (socUs != null && condOwner4.socUs != null && socUs != condOwner4.socUs)
					{
						relationship = socUs.GetRelationship(condOwner4.strID);
						if (relationship != null)
						{
							SwitchRELConds(relationship, bSilent: true);
						}
					}
					if (interaction3.Triggered(this, condOwner4) && (flag3 || !(interaction3.strName == "MSPortalOpenStart") || !Pathfinder.CheckPressure(condOwner4.GetPos("use"), condOwner4.ship, condOwner4.currentRoom)))
					{
						num = item3.fAverage + GetCOScore(condOwner4, item3);
						if (num < num2)
						{
							num2 = num;
							condOwner = condOwner4;
							interaction = interaction3;
						}
					}
				}
				if (interaction != interaction3)
				{
					DataHandler.ReleaseTrackedInteraction(interaction3);
				}
				if (num2 < 0f)
				{
					flag = true;
					break;
				}
			}
			if (flag)
			{
				break;
			}
		}
		if (interaction == null)
		{
			int num5 = 0;
			int num6 = 0;
			for (int k = 0; k < 3; k++)
			{
				num5 = Mathf.RoundToInt(UnityEngine.Random.value * (float)(aInteractions.Count - 1));
				interaction = DataHandler.GetInteraction(aInteractions[num5], null, getTrackedObject: true);
				if (interaction == null)
				{
					continue;
				}
				if (!interaction.bOpener)
				{
					DataHandler.ReleaseTrackedInteraction(interaction);
					continue;
				}
				if (interaction == null || interaction.bHumanOnly || interaction.attackMode != null || !interaction.CTTestUs.Triggered(this))
				{
					DataHandler.ReleaseTrackedInteraction(interaction);
					continue;
				}
				List<CondOwner> list4;
				if (interaction.strThemType == Interaction.TARGET_SELF)
				{
					list4 = new List<CondOwner> { this };
				}
				else if (interaction.strThemType == Interaction.TARGET_OTHER)
				{
					if (interaction.PSpecTestThem != null)
					{
						list4 = new List<CondOwner>();
						PersonSpec person2 = ship.GetPerson(interaction.PSpecTestThem, socUs, bForceUnrelated: false);
						if (person2 != null)
						{
							list4.Add(person2.MakeCondOwner(PersonSpec.StartShip.OLD));
						}
					}
					else
					{
						list4 = GetCOsSafe(bAllowLocked: true, interaction.CTTestThem);
						if (dictionary.TryGetValue(interaction.CTTestThem.strName, out var value2))
						{
							list4.AddRange(value2);
						}
						else
						{
							value2 = ship.GetCOs(interaction.CTTestThem, bSubObjects: false, bAllowDocked: true, bAllowLocked: false);
							dictionary.Add(interaction.CTTestThem.strName, value2);
							list4.AddRange(value2);
						}
						list4.Remove(this);
					}
				}
				else
				{
					list4 = new List<CondOwner>();
				}
				if (list4.Count == 0)
				{
					DataHandler.ReleaseTrackedInteraction(interaction);
					interaction = null;
					continue;
				}
				num6 = Mathf.RoundToInt(UnityEngine.Random.value * (float)(list4.Count - 1));
				if (!flag3 && interaction.strName == "MSPortalOpenStart" && Pathfinder.CheckPressure(list4[num6].GetPos("use"), list4[num6].ship, list4[num6].currentRoom))
				{
					DataHandler.ReleaseTrackedInteraction(interaction);
					interaction = null;
					continue;
				}
				condOwner = list4[num6];
				if (!interaction.Triggered(this, condOwner) || condOwner.bBusy || GetNetInteractionResult(interaction) > 0f)
				{
					DataHandler.ReleaseTrackedInteraction(interaction);
					interaction = null;
					condOwner = null;
					continue;
				}
				bool flag6 = false;
				if (condOwner == CrewSim.GetSelectedCrew() && condOwner != this)
				{
					if (GUISocialCombat2.coUs == condOwner || GUISocialCombat2.coThem == condOwner)
					{
						DataHandler.ReleaseTrackedInteraction(interaction);
						interaction = null;
						condOwner = null;
						continue;
					}
					if (condOwner.jsShiftLast != null && condOwner.jsShiftLast.nID > 0)
					{
						flag6 = true;
					}
				}
				else if (condOwner != this && condOwner.jsShiftLast != null && condOwner.jsShiftLast.nID > 0)
				{
					flag6 = true;
				}
				if (flag6)
				{
					Debug.Log(strName + " was going to bother " + condOwner.FriendlyName + ", but decided not to! (Case 2)");
					DataHandler.ReleaseTrackedInteraction(interaction);
					interaction = null;
					condOwner = null;
				}
				else if (interaction != null && condOwner != null)
				{
					text = condOwner.strID + interaction.strName;
					if (!dictRecentlyTried.ContainsKey(text))
					{
						break;
					}
					DataHandler.ReleaseTrackedInteraction(interaction);
					interaction = null;
					condOwner = null;
				}
			}
		}
		FreeWillLoot.ApplyCondLoot(this, 1f);
		if (interaction == null || condOwner == null)
		{
			return;
		}
		if (text == null)
		{
			Debug.Log("strRef is null in GetMove2() on " + strName);
		}
		else
		{
			dictRecentlyTried[condOwner.strID + interaction.strName] = StarSystem.fEpoch;
		}
		if (condOwner == CrewSim.GetSelectedCrew() && this != condOwner && interaction.bSocial && interaction.strRaiseUI == null && interaction.strRaiseUIThem == null)
		{
			BeatManager.GenerateSocial(interaction);
		}
		if (CheckWalk(interaction, condOwner))
		{
			DataHandler.KeepInteraction(interaction);
			QueueInteraction(condOwner, interaction);
			return;
		}
		string text2 = condOwner.strName;
		if (condOwner.strNameFriendly != null)
		{
			text2 = condOwner.strNameFriendly;
		}
		LogMessage(DataHandler.GetString("ERROR_CANT_REACH_DEST") + text2 + ".", "Bad", strName);
		Debug.Log(strName + " " + DataHandler.GetString("ERROR_CANT_REACH_DEST") + interaction.strName + "; Target: " + text2 + ".");
		DataHandler.ReleaseTrackedInteraction(interaction);
	}

	public bool CheckWalk(Interaction objInteraction, CondOwner co)
	{
		if (ship == null)
		{
			return false;
		}
		if (objInteraction == null || co == null || (!co.gameObject.activeInHierarchy && objInteraction.strTargetPoint != Interaction.POINT_REMOTE))
		{
			return false;
		}
		if (objInteraction.strTargetPoint == null || objInteraction.strTargetPoint == Interaction.POINT_REMOTE)
		{
			return true;
		}
		if (objInteraction.strTargetPoint == "random")
		{
			if (Pathfinder == null)
			{
				return false;
			}
			bool flag = false;
			for (int i = 0; i < 10; i++)
			{
				Tile tile = ship.GetRandomAtmoTile();
				if (tile == null)
				{
					tile = ship.GetRandomTile1();
				}
				if (!(tile == null) && Pathfinder.SetGoal2(tile, 0f, null, 0f, 0f, HasAirlockPermission(bManual: false)).HasPath)
				{
					flag = true;
					break;
				}
			}
			if (!flag)
			{
				return false;
			}
		}
		else if (objInteraction.strTargetPoint == "random_offship")
		{
			if (Pathfinder == null)
			{
				return false;
			}
			IReadOnlyList<Ship> allDockedShips = ship.GetAllDockedShips();
			bool flag2 = false;
			foreach (Ship item in allDockedShips)
			{
				if (!HasShoreLeave())
				{
					break;
				}
				Tile tile2 = item.GetRandomAtmoTile();
				if (tile2 == null)
				{
					tile2 = item.GetRandomTile1();
				}
				if (!(tile2 == null) && Pathfinder.SetGoal2(tile2, 0f, null, 0f, 0f, HasAirlockPermission(bManual: false)).HasPath)
				{
					flag2 = true;
					break;
				}
			}
			if (!flag2)
			{
				return false;
			}
		}
		else
		{
			Vector2 vector = co.GetPos(objInteraction.strTargetPoint);
			if (GetCORef(co) != null)
			{
				vector = tf.position;
			}
			Tile tileAtWorldCoords = ship.GetTileAtWorldCoords1(vector.x, vector.y, bAllowDocked: true);
			if (Pathfinder == null)
			{
				if ((float)TileUtils.TileRange(ship.GetTileAtWorldCoords1(tf.position.x, tf.position.y, bAllowDocked: true), tileAtWorldCoords) > objInteraction.fTargetPointRange)
				{
					return false;
				}
				return true;
			}
			if (!Pathfinder.SetGoal2(tileAtWorldCoords, objInteraction.fTargetPointRange, co, vector.x, vector.y, HasAirlockPermission(objInteraction.bManual)).HasPath)
			{
				return false;
			}
		}
		if (Pathfinder.tilDest != null && Pathfinder.tilDest != Pathfinder.tilCurrent)
		{
			Interaction interaction = DataHandler.GetInteraction("Walk");
			if (Pathfinder.coDest != null && Pathfinder.coDest.Crew != null)
			{
				if (interaction != null)
				{
					interaction.bManual = objInteraction.bManual;
					interaction.strTargetPoint = objInteraction.strTargetPoint;
					interaction.fTargetPointRange = objInteraction.fTargetPointRange;
				}
				QueueInteraction(Pathfinder.coDest, interaction, bInsert: true);
				aQueue[0].objThem = Pathfinder.coDest;
			}
			else
			{
				interaction.bManual = objInteraction.bManual;
				QueueInteraction(Pathfinder.tilDest.coProps, interaction, bInsert: true);
				aQueue[0].objThem = Pathfinder.tilDest.coProps;
				aQueue[0].strTargetPoint = objInteraction.strTargetPoint;
				aQueue[0].fTargetPointRange = 0f;
			}
		}
		return true;
	}

	public bool RemembersInteract(string strIAName)
	{
		if (strIAName == null || strIAName == "")
		{
			return false;
		}
		foreach (CondHistory value in mapIAHist.Values)
		{
			if (value.mapInteractions.ContainsKey(strIAName))
			{
				return true;
			}
		}
		return false;
	}

	public float GetNetInteractionResult(Interaction objInteraction, bool bVerbose = false)
	{
		float num = 0f;
		if (objInteraction == null)
		{
			return num;
		}
		CondHistory condHistory = null;
		InteractionHistory interactionHistory = null;
		objInteraction.aCondUsPriorities = new List<CondScore>();
		string[] array = objInteraction.strName.Split(';');
		foreach (Priority aPriority in aPriorities)
		{
			if (!mapConds.TryGetValue(aPriority.objCond.strName, out var _))
			{
				continue;
			}
			condHistory = null;
			interactionHistory = null;
			mapIAHist.TryGetValue(aPriority.objCond.strName, out condHistory);
			if (condHistory != null && !condHistory.mapInteractions.TryGetValue(objInteraction.strName, out interactionHistory) && array.Length > 1)
			{
				condHistory.mapInteractions.TryGetValue(array[0], out interactionHistory);
			}
			if (interactionHistory != null)
			{
				CondScore condScore = new CondScore(aPriority.objCond.strName);
				condScore.fTotalValue = interactionHistory.fAverage * (0f - (float)aPriority.fValue);
				num += condScore.fTotalValue;
				objInteraction.aCondUsPriorities.Add(condScore);
				if (bVerbose)
				{
					Debug.Log("GetNetInteractionResult " + objInteraction.strName + ": " + aPriority.ToString() + " = " + (0.0 - aPriority.fValue) + " * " + interactionHistory.fAverage);
				}
			}
		}
		objInteraction.aCondUsPriorities.Sort((CondScore x, CondScore y) => x.fTotalValue.CompareTo(y.fTotalValue));
		if (num == 0f && objInteraction.strActionGroup == "Ship")
		{
			num = 1f;
		}
		return num;
	}

	private float GetCOScore(CondOwner objCO, InteractionHistory objIH)
	{
		float num = 0f;
		foreach (CondScore value in objIH.mapScores.Values)
		{
			if (objCO.HasCond(value.strName))
			{
				num += value.fAverage;
			}
		}
		return num;
	}

	public void UpdateCondRecords(Condition objCond)
	{
		if (mapConds == null)
		{
			return;
		}
		if (objCond.fCount <= 0.0)
		{
			mapConds.Remove(objCond.strName);
			aCondsTimed.Remove(objCond);
			if (faceRef != null)
			{
				faceRef.RecordCond(objCond.strName, bRemove: true);
			}
			MonoSingleton<GUIRenderTargets>.Instance.UpdateFaces(this, objCond.strName, remove: true);
			if (objCond.bPersists && aCondZeroes.IndexOf(objCond.strName) < 0)
			{
				aCondZeroes.Add(objCond.strName);
			}
		}
		else if (objCond.fDuration > 0f)
		{
			mapConds[objCond.strName] = objCond;
			if (objCond.bPersists && aCondZeroes.IndexOf(objCond.strName) >= 0)
			{
				aCondZeroes.Remove(objCond.strName);
			}
		}
	}

	public void ZeroCondAmount(string strName)
	{
		AddCondAmount(strName, 0.0 - GetCondAmount(strName));
	}

	public void SetCondAmount(string strName, double dAmount, double dAge = 0.0)
	{
		double condAmount = GetCondAmount(strName);
		double fAmount = dAmount - condAmount;
		AddCondAmount(strName, fAmount, dAge);
	}

	public bool IsThreshold(string condName)
	{
		if (condName == null || condName.Length < 6)
		{
			return false;
		}
		if (condName[0] == 'T' && condName[1] == 'h' && condName[2] == 'r' && condName[3] == 'e' && condName[4] == 's' && condName[5] == 'h')
		{
			return true;
		}
		return false;
	}

	public void AddCondAmount(string strName, double fAmount, double fAge = 0.0, float fCondRuleTrack = 0f)
	{
		if (bFreezeConds || strName == null || mapConds == null || fAmount == 0.0 || double.IsNaN(fAmount))
		{
			return;
		}
		if (IsThreshold(strName))
		{
			if (!bFreezeCondRules)
			{
				CondRule value = null;
				string key = strName.Substring(6);
				mapCondRules.TryGetValue(key, out value);
				value?.ChangeThresh(this, fAmount);
			}
			return;
		}
		bool flag = false;
		if (mapConds.TryGetValue(strName, out var value2))
		{
			flag = true;
		}
		else
		{
			value2 = DataHandler.GetCond(strName);
		}
		if (value2 == null || (fAmount > 0.0 && value2.ctImmune != null && value2.ctImmune.Triggered(this)))
		{
			return;
		}
		if (value2.strAnti != null && fAmount > 0.0)
		{
			bool isThreshold = IsThreshold(value2.strAnti);
			if (HasCond(value2.strAnti, isThreshold))
			{
				double condAmount = GetCondAmount(value2.strAnti, isThreshold);
				if (condAmount > fAmount)
				{
					AddCondAmount(value2.strAnti, 0.0 - fAmount);
					return;
				}
				ZeroCondAmount(value2.strAnti);
				fAmount -= condAmount;
			}
		}
		if (value2.bRoom)
		{
			if (ship != null)
			{
				Room roomAtWorldCoords = ship.GetRoomAtWorldCoords1(tf.position, bAllowDocked: true);
				if (roomAtWorldCoords != null && roomAtWorldCoords.CO != this)
				{
					roomAtWorldCoords.CO.AddCondAmount(strName, fAmount, fAge);
				}
			}
			AddCondAmount("IsRoomStat", fAmount);
		}
		double num = value2.fCount;
		if (num < 0.0)
		{
			num = 0.0;
		}
		if (strName == "StatFatigue" && !bFreezeCondRules && HasCond("StatFatigueCoeff", isThreshold: false))
		{
			fAmount *= GetCondAmount("StatFatigueCoeff", isThreshold: false);
		}
		if (!flag && value2.bAlert && bLogConds && objCompany != null && objCompany == CrewSim.coPlayer.objCompany)
		{
			if ((double)Time.timeScale > 1.0)
			{
				CrewSim.ResetTimeScale();
			}
			if (CrewSim.GetSelectedCrew() != this)
			{
				CrewSim.GetSelectedCrew().LogMessage(CrewSim.GetSelectedCrew().strNameFriendly + " notices something is wrong with " + strNameFriendly, "Badish", CrewSim.GetSelectedCrew().strID);
			}
			if (CrewSim.GetSelectedCrew() != CrewSim.coPlayer && this != CrewSim.coPlayer)
			{
				CrewSim.coPlayer.LogMessage(CrewSim.coPlayer.strNameFriendly + " notices something is wrong with " + strNameFriendly, "Badish", CrewSim.coPlayer.strID);
			}
		}
		value2.AddAmount(this, fAmount);
		if (fAge != 0.0)
		{
			value2.SetAge((float)fAge + value2.GetAge());
		}
		if (value2.bCondRuleTrackAlways)
		{
			value2.fCondRuleTrack = value2.fCount - num;
		}
		else
		{
			value2.fCondRuleTrack = fCondRuleTrack;
		}
		value2.fCondRuleTrackTime = StarSystem.fEpoch;
		if (strName == "StatPowerMax" && Pwr != null)
		{
			Pwr.ResetMaxPower();
		}
		if (!flag && fAmount > 0.0)
		{
			if (value2.bRELOnly && aRELConds.IndexOf(value2.strName) < 0)
			{
				aRELConds.Add(value2.strName);
			}
			if (faceRef != null)
			{
				faceRef.RecordCond(value2.strName, bRemove: false);
				if (value2.pairFaceSprite != null && Crew != null && value2.pairFaceSprite.nValue >= 0 && value2.pairFaceSprite.nValue < Crew.FaceParts.Length)
				{
					Crew.FaceParts[value2.pairFaceSprite.nValue] = value2.pairFaceSprite.strName;
					MonoSingleton<GUIRenderTargets>.Instance.SetFace(this, bForce: true);
				}
			}
			MonoSingleton<GUIRenderTargets>.Instance.UpdateFaces(this, value2.strName, remove: false);
			if (value2.fDuration > 0f && !float.IsInfinity(value2.fDuration))
			{
				AddCondTicker(value2, fAge);
				aCondsTimed.Add(value2);
			}
			if (bLogConds && ((value2.nDisplaySelf == 2 && this == CrewSim.coPlayer) || (value2.nDisplayOther == 2 && this != CrewSim.coPlayer)))
			{
				string strShort = null;
				if (!string.IsNullOrEmpty(value2.strShort))
				{
					strShort = ((strName.IndexOf("Dc") != 0) ? value2.strShort : (GUIStatus.GetStatusText(value2, DataHandler.GetColor(value2.strColor)) + value2.strShort));
				}
				LogMessage(GUIStatus.GetStatusText(value2, Color.white) + GrammarUtils.GetInflectedString(value2.strDesc, this), value2.strColor, this.strName, strShort);
			}
			if (value2.bFatal)
			{
				Debug.Log("#NPC# Fatal cond " + value2.strName + " added to " + strID);
				Kill = true;
			}
			else if (!bFreezeCondRules && value2.bKO)
			{
				KO();
			}
		}
		if (flag)
		{
			if (value2.fCount <= 0.0)
			{
				if (value2.bRELOnly)
				{
					aRELConds.Remove(value2.strName);
				}
				if (faceRef != null && value2.pairFaceSprite != null && Crew != null && value2.pairFaceSprite.nValue >= 0 && value2.pairFaceSprite.nValue < Crew.FaceParts.Length)
				{
					Crew.FaceParts[value2.pairFaceSprite.nValue] = FaceAnim2.PartNameDefault(value2.pairFaceSprite.nValue);
					MonoSingleton<GUIRenderTargets>.Instance.SetFace(this, bForce: true);
				}
				if (value2.fDuration > 0f && !float.IsInfinity(value2.fDuration))
				{
					RemoveTicker(value2.strName);
					aCondsTimed.Remove(value2);
				}
				if (bLogConds && ((value2.nDisplaySelf == 2 && this == CrewSim.coPlayer) || (value2.nDisplayOther == 2 && this != CrewSim.coPlayer)))
				{
					GrammarUtils.insertNoLonger = true;
					LogMessage(GUIStatus.GetStatusText(value2, Color.white) + GrammarUtils.GetInflectedString(value2.strDesc, this), value2.strColor + "Remove", this.strName);
				}
				if (dictRemoveCondEvents.ContainsKey(value2.strName) && dictRemoveCondEvents[value2.strName] != null && DataHandler.GetCondTrigger(dictRemoveCondEvents[value2.strName][1]).Triggered(this))
				{
					if (dictRemoveCondEvents[value2.strName][0] == "AddTask")
					{
						bool result = true;
						bool.TryParse(dictRemoveCondEvents[value2.strName][4], out result);
						if (!result || (ship != null && ship == CrewSim.shipPlayerOwned))
						{
							AddTask(dictRemoveCondEvents[value2.strName][2], dictRemoveCondEvents[value2.strName][3]);
						}
					}
					else if (dictRemoveCondEvents[value2.strName][0] == "RemoveTask")
					{
						CrewSim.objInstance.workManager.RemoveTask(dictRemoveCondEvents[value2.strName][2], dictRemoveCondEvents[value2.strName][3], strID);
					}
				}
				if (value2.strName == "IsHuman" && Crew != null)
				{
					UnityEngine.Object.Destroy(Crew);
					UnityEngine.Object.Destroy(base.gameObject.GetComponent<Pathfinder>());
				}
				if (value2.strName == "IsReactorIC" && base.gameObject.GetComponent<FusionIC>() != null)
				{
					UnityEngine.Object.Destroy(base.gameObject.GetComponent<FusionIC>());
				}
				if (value2.strName == "IsAirtight" && GasContainer != null)
				{
					aManUpdates.Remove(GasContainer);
					Room roomAtWorldCoords2 = currentRoom;
					if (roomAtWorldCoords2 == null && ship != null)
					{
						roomAtWorldCoords2 = ship.GetRoomAtWorldCoords1(tf.position, bAllowDocked: false);
					}
					if (roomAtWorldCoords2 != null)
					{
						GasContainer.MergeGasContainersAndDestroy(this, roomAtWorldCoords2.CO);
					}
					else
					{
						GasContainer.MergeGasContainersAndDestroy(this, null);
					}
				}
				if (value2.strName == "IsPassiveRewarmer" && base.gameObject.GetComponent<BodyTemp>() != null)
				{
					aManUpdates.Remove(base.gameObject.GetComponent<BodyTemp>());
					UnityEngine.Object.DestroyImmediate(base.gameObject.GetComponent<BodyTemp>());
				}
				if (value2.strName == "IsCrewArmLLamp" && Crew != null)
				{
					Crew.ArmLLamp = value2.fCount;
				}
				if (value2.strName == "IsCrewArmRLamp" && Crew != null)
				{
					Crew.ArmRLamp = value2.fCount;
				}
				if (value2.strName == "IsCrewHandLLamp" && Crew != null)
				{
					Crew.HandLLamp = value2.fCount;
				}
				if (value2.strName == "IsCrewHandRLamp" && Crew != null)
				{
					Crew.HandRLamp = value2.fCount;
				}
				if (value2.strName == "IsCrewHeadLamp" && Crew != null)
				{
					Crew.HeadLamp = value2.fCount;
				}
				if (value2.strName == "IsCrewToolSpark" && Crew != null)
				{
					Crew.Sparks = false;
				}
				if (value2.strName == "IsCCTV" && base.gameObject.GetComponentInChildren<CCTV>() != null)
				{
					CCTV componentInChildren = base.gameObject.GetComponentInChildren<CCTV>();
					componentInChildren.transform.SetParent(null);
					UnityEngine.Object.Destroy(componentInChildren);
				}
				if (value2.strName == "IsTraderNPC" && base.gameObject.GetComponent<Trader>() != null)
				{
					UnityEngine.Object.Destroy(base.gameObject.GetComponent<Trader>());
				}
				if (value2.bQABRefresh && (CrewSim.GetSelectedCrew() == this || GUIMegaToolTip.Selected == this))
				{
					MonoSingleton<GUIQuickBar>.Instance.BuildButtonList();
				}
				if (!bFreezeCondRules && value2.bKO)
				{
					KOWake();
				}
			}
			else if (fAge != 0.0 && !double.IsInfinity(value2.fDuration))
			{
				RemoveTicker(value2.strName);
				AddCondTicker(value2, fAge);
			}
		}
		else if (!flag && value2.fCount > 0.0)
		{
			if (dictAddCondEvents.ContainsKey(value2.strName) && dictAddCondEvents[value2.strName] != null && DataHandler.GetCondTrigger(dictAddCondEvents[value2.strName][1]).Triggered(this))
			{
				if (dictAddCondEvents[value2.strName][0] == "AddTask")
				{
					bool result2 = true;
					bool.TryParse(dictAddCondEvents[value2.strName][4], out result2);
					if (!result2 || (ship != null && ship == CrewSim.shipPlayerOwned))
					{
						AddTask(dictAddCondEvents[value2.strName][2], dictAddCondEvents[value2.strName][3]);
					}
				}
				else if (dictAddCondEvents[value2.strName][0] == "RemoveTask")
				{
					CrewSim.objInstance.workManager.RemoveTask(dictAddCondEvents[value2.strName][2], dictAddCondEvents[value2.strName][3], strID);
				}
			}
			if ((value2.strName == "IsHuman" || value2.strName == "IsRobot") && Crew == null)
			{
				_pfComponentReference = base.gameObject.AddComponent<Pathfinder>();
				(_crewComponentReference = ((value2.strName == "IsHuman") ? base.gameObject.AddComponent<Crew>() : base.gameObject.AddComponent<Robot>())).SetData(strItemDef, 0f, 0f, 0f);
				base.gameObject.AddComponent<AwaitsReplyObserver>();
				base.gameObject.AddComponent<AutoEmergencyObserver>();
			}
			if (value2.strName == "IsReactorIC" && base.gameObject.GetComponent<FusionIC>() == null)
			{
				base.gameObject.AddComponent<FusionIC>();
			}
			if (value2.strName == "IsAirtight")
			{
				GasContainer gasContainer = base.gameObject.AddComponent<GasContainer>();
				Room roomAtWorldCoords3 = currentRoom;
				if (roomAtWorldCoords3 == null && ship != null)
				{
					roomAtWorldCoords3 = ship.GetRoomAtWorldCoords1(tf.position, bAllowDocked: false);
				}
				if (roomAtWorldCoords3 != null)
				{
					gasContainer.CarveNewGasContainerFromRoom(roomAtWorldCoords3.CO, this);
				}
				aManUpdates.Add(gasContainer);
			}
			if (value2.strName == "IsPassiveRewarmer" && base.gameObject.GetComponent<BodyTemp>() == null)
			{
				BodyTemp item = base.gameObject.AddComponent<BodyTemp>();
				aManUpdates.Add(item);
			}
			if (value2.strName == "IsCrewArmLLamp" && Crew != null)
			{
				Crew.ArmLLamp = value2.fCount;
			}
			if (value2.strName == "IsCrewArmRLamp" && Crew != null)
			{
				Crew.ArmRLamp = value2.fCount;
			}
			if (value2.strName == "IsCrewHandLLamp" && Crew != null)
			{
				Crew.HandLLamp = value2.fCount;
			}
			if (value2.strName == "IsCrewHandRLamp" && Crew != null)
			{
				Crew.HandRLamp = value2.fCount;
			}
			if (value2.strName == "IsCrewHeadLamp" && Crew != null)
			{
				Crew.HeadLamp = value2.fCount;
			}
			if (value2.strName == "IsCrewToolSpark" && Crew != null)
			{
				Crew.Sparks = true;
			}
			if (value2.strName == "IsCCTV" && base.gameObject.GetComponentInChildren<CCTV>() == null)
			{
				_ = UnityEngine.Object.Instantiate((GameObject)Resources.Load("prefabCCTV"), tf).transform;
			}
			if (value2.strName == "IsTraderNPC" && base.gameObject.GetComponent<Trader>() == null)
			{
				base.gameObject.AddComponent<Trader>();
			}
			if (value2.strName == "IsMarketActor" && base.gameObject.GetComponent<MarketActor>() == null)
			{
				base.gameObject.AddComponent<MarketActor>();
			}
			if (value2.strName.Length >= 7 && value2.strName.Substring(0, 7) == "Trigger")
			{
				if (Pathfinder != null)
				{
					Pathfinder.AddTriggerListener(OnZoneTriggerEntered);
				}
				else
				{
					Debug.Log("Tried to add zone trigger to non pathfinder: " + this.strName);
				}
			}
			if (value2.strName == "Prone")
			{
				SetAnimState(Interaction.dictAnims["Fallen"]);
				strIdleAnim = "Fallen";
				SetAnimTrigger("FallenTrigger");
				if (aQueue.Count > 0 && aQueue[0] != null)
				{
					aQueue[0].strAnim = "Fallen";
					aQueue[0].strIdleAnim = "Fallen";
				}
				if (CrewSim.GetSelectedCrew() == this && GUIMegaToolTip.Selected == null)
				{
					CrewSim.OnRightClick.Invoke(new List<CondOwner> { this });
				}
			}
			if (value2.bQABRefresh && (CrewSim.GetSelectedCrew() == this || GUIMegaToolTip.Selected == this))
			{
				MonoSingleton<GUIQuickBar>.Instance.SetDirty();
			}
		}
		UpdatePriority(value2);
		if (!bFreezeCondRules && mapCondRules.TryGetValue(value2.strName, out var value3))
		{
			value3.ChangeStat(this, num, value2.fCount);
		}
		if (aDestructableConds.Contains(value2.strName))
		{
			Destructable component = base.gameObject.GetComponent<Destructable>();
			if (component != null)
			{
				component.ScheduleDamageCheck();
			}
		}
	}

	private void AddCondTicker(Condition objCond, double fAge)
	{
		if (objCond != null && !double.IsInfinity(objCond.fDuration))
		{
			JsonTicker jsonTicker = new JsonTicker();
			jsonTicker.strCondUpdate = objCond.strName;
			jsonTicker.bRepeat = false;
			jsonTicker.fPeriod = Convert.ToDouble(objCond.fDuration);
			jsonTicker.SetTimeLeft(jsonTicker.fPeriod - fAge);
			jsonTicker.strName = objCond.strName;
			AddTicker(jsonTicker);
		}
	}

	public bool HasCond(string strName, bool isThreshold)
	{
		if (mapConds == null)
		{
			return false;
		}
		if (isThreshold)
		{
			CondRule value = null;
			string key = strName.Substring(6);
			mapCondRules.TryGetValue(key, out value);
			return value != null;
		}
		return mapConds.ContainsKey(strName);
	}

	public bool HasCond(string strName)
	{
		return HasCond(strName, IsThreshold(strName));
	}

	public double GetCondAmount(string strName)
	{
		return GetCondAmount(strName, IsThreshold(strName));
	}

	public double GetCondAmount(string strName, bool isThreshold)
	{
		if (strName == null || mapConds == null)
		{
			return 0.0;
		}
		if (isThreshold)
		{
			CondRule value = null;
			string key = strName.Substring(6);
			mapCondRules.TryGetValue(key, out value);
			return value?.Modifier ?? 0.0;
		}
		Condition value2 = null;
		if (mapConds.TryGetValue(strName, out value2))
		{
			return value2.fCount;
		}
		return 0.0;
	}

	public void CopyCondsTo(CondOwner coTarget)
	{
		foreach (KeyValuePair<string, Condition> mapCond in mapConds)
		{
			if (mapCond.Value != null)
			{
				coTarget.AddCondAmount(mapCond.Key, mapCond.Value.fCount);
			}
		}
	}

	private void OnZoneTriggerEntered(JsonZone jz)
	{
		if (jz == null)
		{
			return;
		}
		string[] categoryConds = jz.categoryConds;
		foreach (string text in categoryConds)
		{
			if (!HasCond(text))
			{
				continue;
			}
			Debug.Log("Zone triggered: " + text);
			JsonZoneTrigger zoneTrigger = DataHandler.GetZoneTrigger(text);
			if (zoneTrigger == null)
			{
				continue;
			}
			if (zoneTrigger.strRunEncounter != null)
			{
				BeatManager.RunEncounter(zoneTrigger.strRunEncounter, zoneTrigger.bRunEncounterInterrupt);
			}
			if (zoneTrigger.strApplyInteractionChain != null)
			{
				DataHandler.GetInteraction(zoneTrigger.strApplyInteractionChain)?.ApplyChain();
			}
			if (zoneTrigger.strQueueInteraction != null)
			{
				Interaction interaction = DataHandler.GetInteraction(zoneTrigger.strQueueInteraction);
				if (interaction != null && ship != null)
				{
					List<CondOwner> cOs = ship.GetCOs(interaction.CTTestThem, bSubObjects: true, bAllowDocked: true, bAllowLocked: false);
					if (cOs.Count > 0 && interaction.Triggered(this, cOs[0]))
					{
						QueueInteraction(cOs[0], interaction, zoneTrigger.bQueueInteractionInsert);
					}
				}
			}
			if (!zoneTrigger.bRemoveOnTrigger)
			{
				continue;
			}
			if (CrewSim.ZoneMenuOpen)
			{
				MonoSingleton<GUIZones>.Instance.DeleteZone(jz.strName);
				continue;
			}
			Ship loadedShipByRegId = CrewSim.GetLoadedShipByRegId(jz.strRegID);
			if (loadedShipByRegId != null)
			{
				GUIZones.DeleteTilesFromZone(jz);
				loadedShipByRegId.mapZones.Remove(jz.strName);
			}
		}
	}

	public double GetTotalMass()
	{
		double num = GetCondAmount("StatMass");
		foreach (CondOwner item in aStack)
		{
			num += item.GetTotalMass();
		}
		return num;
	}

	public string GetDiscomfortForCond(string strCond)
	{
		if (strCond == null || mapConds == null)
		{
			return null;
		}
		if (mapCondRules.ContainsKey(strCond))
		{
			CondRuleThresh[] aThresholds = mapCondRules[strCond].aThresholds;
			for (int i = 0; i < aThresholds.Length; i++)
			{
				foreach (string lootName in DataHandler.GetLoot(aThresholds[i].strLootNew).GetLootNames(null, bOnlyCOs: true))
				{
					if (mapConds.ContainsKey(lootName))
					{
						return lootName;
					}
				}
			}
		}
		return null;
	}

	public void AddCondRule(string strCondRule, bool bApplyEffects = true)
	{
		if (string.IsNullOrEmpty(strCondRule))
		{
			return;
		}
		bool flag = strCondRule.IndexOf("-") == 0;
		CondRule condRule = (flag ? CondRule.LoadSaveInfo(strCondRule.Substring(1)) : CondRule.LoadSaveInfo(strCondRule));
		if (condRule == null)
		{
			Debug.Log("Cannot " + (flag ? "remove" : "add") + " Condrule " + strCondRule + " on CO " + strName);
		}
		else if (flag)
		{
			if (bApplyEffects)
			{
				AddCondRuleEffects(condRule, -1f);
			}
			mapCondRules.Remove(condRule.strCond);
			if (condRule.fPref != double.PositiveInfinity)
			{
				hashCondsImportant.Remove(condRule.strCond);
			}
		}
		else
		{
			mapCondRules[condRule.strCond] = condRule;
			if (bApplyEffects)
			{
				AddCondRuleEffects(condRule, 1f);
			}
			if (condRule.fPref != double.PositiveInfinity)
			{
				hashCondsImportant.Add(condRule.strCond);
			}
		}
	}

	private void AddCondRuleEffects(CondRule cr, float fCoeff)
	{
		if (cr == null)
		{
			return;
		}
		CondRuleThresh currentThresh = cr.GetCurrentThresh(this);
		if (currentThresh != null)
		{
			Loot loot = DataHandler.GetLoot(currentThresh.strLootNew);
			if (loot.strName != "Blank")
			{
				loot.ApplyCondLoot(this, currentThresh.fMinAdd * fCoeff);
			}
		}
	}

	public CondRule GetCondRule(string strCond)
	{
		if (strCond == null || mapConds == null)
		{
			return null;
		}
		if (mapCondRules.ContainsKey(strCond))
		{
			return mapCondRules[strCond];
		}
		return null;
	}

	public Interaction GetInteraction(string strN = null, CondOwner objTarget = null)
	{
		if (strN == null && objTarget == null)
		{
			return null;
		}
		foreach (Interaction item in aQueue)
		{
			if (item.strName == strN)
			{
				if (objTarget == null)
				{
					return item;
				}
				if (objTarget == item.objThem)
				{
					return item;
				}
			}
			if (objTarget == item.objThem)
			{
				if (strN == null)
				{
					return item;
				}
				if (strN == item.strName)
				{
					return item;
				}
			}
		}
		return null;
	}

	public Interaction GetInteractionCurrent()
	{
		if (aQueue == null)
		{
			return null;
		}
		if (aQueue.Count == 0)
		{
			return null;
		}
		return aQueue[0];
	}

	public CondTrigger GetCTForThis()
	{
		CondTrigger condTrigger = new CondTrigger();
		condTrigger.strName = strName;
		List<string> list = new List<string>();
		foreach (string key in mapConds.Keys)
		{
			if (key.IndexOf("Is") == 0)
			{
				list.Add(key);
			}
		}
		condTrigger.aReqs = list.ToArray();
		return condTrigger;
	}

	public void AddLotCO(CondOwner co)
	{
		if (aLot.IndexOf(co) < 0)
		{
			if (co.objCOParent != null)
			{
				co.RemoveFromCurrentHome();
			}
			aLot.Add(co);
		}
		if (co == this)
		{
			Debug.Log("ERROR: Assigning self as own parent.");
		}
		co.objCOParent = this;
		co.ship = ship;
		co.tf.SetParent(tf, worldPositionStays: true);
		co.Visible = false;
		if (strPersistentCO == null)
		{
			strPersistentCO = co.strID;
		}
	}

	public CondOwner RemoveLotCO(CondOwner co)
	{
		if (aLot.IndexOf(co) < 0)
		{
			return null;
		}
		aLot.Remove(co);
		co.objCOParent = null;
		if (co.ship != null)
		{
			co.ship.RemoveCO(co, bForce: true);
		}
		else
		{
			co.tf.SetParent(null, worldPositionStays: true);
		}
		if (strPersistentCO == co.strID)
		{
			strPersistentCO = null;
		}
		return co;
	}

	public List<CondOwner> GetLotCOs(bool bSubItems)
	{
		List<CondOwner> aCOs = new List<CondOwner>();
		if (aLot != null)
		{
			aCOs.AddRange(aLot);
			if (bSubItems)
			{
				foreach (CondOwner item in aLot)
				{
					NullSafeAddRange(ref aCOs, item.GetCOs(bAllowLocked: true));
					NullSafeAddRange(ref aCOs, item.GetLotCOs(bSubItems: true));
				}
			}
		}
		return aCOs;
	}

	public CondOwner AddCO(CondOwner objCO, bool bEquip, bool bOverflow, bool bIgnoreLocks)
	{
		if (objCO == null || bDestroyed)
		{
			return null;
		}
		if (compSlots != null)
		{
			foreach (string key in objCO.mapSlotEffects.Keys)
			{
				Slot slot = compSlots.GetSlot(key);
				if (slot != null && (bEquip || slot.bHoldSlot) && compSlots.SlotItem(key, objCO))
				{
					return null;
				}
			}
		}
		CondOwner condOwner = StackCO(objCO);
		if (condOwner != null && !bOverflow)
		{
			return condOwner;
		}
		if (objContainer != null && (bIgnoreLocks || !objContainer.Locked))
		{
			condOwner = objContainer.AddCO(condOwner);
		}
		if (condOwner != null)
		{
			foreach (Slot slot2 in GetSlots(bDeep: false))
			{
				condOwner = slot2.AddCO(condOwner, bEquip: false, bOverflow: true, bIgnoreLocks);
				if (condOwner == null)
				{
					break;
				}
			}
		}
		return condOwner;
	}

	public Ship RemoveFromCurrentHome(bool bForce = false)
	{
		Ship result = ship;
		if (objCOParent != null)
		{
			if (objCOParent.aLot.IndexOf(this) >= 0)
			{
				objCOParent.RemoveLotCO(this);
				CheckTrue(objCOParent == null, "Failed to remove from parent.");
				CheckTrue(ship == null, "Failed to remove from ship.");
				return result;
			}
			objCOParent.RemoveCO(this, bForce);
			CheckTrue(objCOParent == null, "Failed to remove from parent.");
			CheckTrue(ship == null, "Failed to remove from ship.");
			return result;
		}
		if (ship != null)
		{
			if (ship.GetType() == typeof(BarterZoneShip))
			{
				((BarterZoneShip)ship).RemoveCO(this);
			}
			else
			{
				ship.RemoveCO(this, bForce);
			}
			CheckTrue(ship == null, "Failed to remove from ship.");
			return result;
		}
		return null;
	}

	public CondOwner RemoveCO(CondOwner objCO, bool bForce = false)
	{
		if (objCO == null || objCO == this || bDestroyed)
		{
			return null;
		}
		if (compSlots != null)
		{
			if (objCO.slotNow != null)
			{
				CondOwner condOwner = compSlots.UnSlotItem(objCO.slotNow.strName, objCO, bForce);
				if (condOwner != null)
				{
					return condOwner;
				}
			}
			else
			{
				foreach (Slot slot in GetSlots(bDeep: false))
				{
					if (slot != null)
					{
						CondOwner condOwner2 = slot.RemoveCO(objCO, bForce);
						if (condOwner2 != null)
						{
							return condOwner2;
						}
					}
				}
			}
		}
		if (aStack.IndexOf(objCO) >= 0)
		{
			if (objCO.ship != null)
			{
				if (objCO == this)
				{
					Debug.Log("ERROR: Assigning self as own parent.");
				}
				objCO.objCOParent = this;
				objCO.ship.RemoveCO(objCO, bForce);
			}
			objCO.objCOParent = null;
			objCO.coStackHead = null;
			objCO.Item.fLastRotation = tf.rotation.eulerAngles.z;
			objCO.tf.position = new Vector3(tf.position.x, tf.position.y, tf.position.z);
			objCO.tf.SetParent(null, worldPositionStays: true);
			if (objCOParent != null)
			{
				objCOParent.AddMass(0.0 - objCO.GetCondAmount("StatMass"));
			}
			objCO.UpdateAppearance();
			UpdateAppearance();
			return objCO;
		}
		if (objContainer != null)
		{
			CondOwner condOwner3 = objContainer.RemoveCO(objCO, bForce);
			if (condOwner3 != null)
			{
				UpdateAppearance();
				return condOwner3;
			}
		}
		if (aLot.IndexOf(objCO) >= 0)
		{
			return RemoveLotCO(objCO);
		}
		return null;
	}

	public CondOwner RootParent(string strCond = null)
	{
		if (AreWeGettingDragged(this, objCOParent))
		{
			return null;
		}
		CondOwner condOwner = objCOParent;
		CondOwner condOwner2 = null;
		while (condOwner != null)
		{
			if (strCond == null || condOwner.HasCond(strCond))
			{
				condOwner2 = condOwner;
			}
			condOwner = condOwner.objCOParent;
			if (AreWeGettingDragged(condOwner2, condOwner))
			{
				return condOwner2;
			}
		}
		return condOwner2;
	}

	private bool AreWeGettingDragged(CondOwner us, CondOwner them)
	{
		if (us == null || them == null)
		{
			return false;
		}
		if (us.Crew != null && them.Crew != null)
		{
			return true;
		}
		return false;
	}

	public Slot GetSlotParent()
	{
		CondOwner condOwner = objCOParent;
		while (condOwner != null)
		{
			if (condOwner.slotNow != null)
			{
				return condOwner.slotNow;
			}
			condOwner = condOwner.objCOParent;
		}
		return null;
	}

	public CondOwner DropCO(CondOwner objCO, bool bAllowLocked, Ship objShipRef = null, float xOffset = 0f, float yOffset = 0f, bool dropInContainersLast = true, Func<int[], int[]> sortingProvider = null, int maxDropRange = 2, bool ignoreZones = false)
	{
		if (objCO == null)
		{
			return objCO;
		}
		if (objShipRef == null)
		{
			objShipRef = ship;
		}
		if (objShipRef == null)
		{
			return objCO;
		}
		Vector3 vector = new Vector3(tf.position.x + xOffset, tf.position.y + yOffset, tf.position.z);
		JsonZone jsonZone = ((xOffset == 0f && yOffset == 0f) ? TileUtils.GetZoneFromTileRadius(objShipRef, tf.position, maxDropRange, bShuffled: true) : TileUtils.GetZoneFromTileRadius(objShipRef, vector, maxDropRange, bShuffled: true));
		Tile tileAtWorldCoords = objShipRef.GetTileAtWorldCoords1(vector.x, vector.y, bAllowDocked: true);
		int[] aTiles;
		if (tileAtWorldCoords != null && tileAtWorldCoords.jZone != null && !ignoreZones)
		{
			List<int> list = new List<int>();
			aTiles = tileAtWorldCoords.jZone.aTiles;
			foreach (int num in aTiles)
			{
				if (Array.IndexOf(jsonZone.aTiles, num) >= 0)
				{
					list.Add(num);
				}
			}
			jsonZone.aTiles = list.ToArray();
		}
		vector = ((tileAtWorldCoords != null && !tileAtWorldCoords.IsWall && !tileAtWorldCoords.IsPortal) ? tileAtWorldCoords.tf.position : vector);
		RemoveCO(objCO);
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsLootSpawnOK");
		List<CondOwner> cOsInZone = objShipRef.GetCOsInZone(jsonZone, condTrigger, bAllowLocked);
		cOsInZone.Remove(this);
		List<int> list2 = new List<int>();
		aTiles = jsonZone.aTiles;
		foreach (int num2 in aTiles)
		{
			Tile tileByIndex = objShipRef.GetTileByIndex(num2);
			if (!(tileByIndex == null) && !(tileByIndex.coProps == null) && Visibility.IsCondOwnerLOSVisibleBlocks(tileByIndex.coProps, vector, bIgnoreEndpoints: false, bIgnoreGlass: false))
			{
				list2.Add(num2);
			}
		}
		jsonZone.aTiles = list2.ToArray();
		for (int num3 = cOsInZone.Count - 1; num3 >= 0; num3--)
		{
			if (!Visibility.IsCondOwnerLOSVisibleBlocks(cOsInZone[num3], vector, bIgnoreEndpoints: false, bIgnoreGlass: false))
			{
				cOsInZone.RemoveAt(num3);
			}
		}
		if (sortingProvider != null && jsonZone.aTiles.Length != 0)
		{
			jsonZone.aTiles = sortingProvider(jsonZone.aTiles) ?? jsonZone.aTiles;
		}
		List<CondOwner> list3 = null;
		if (dropInContainersLast)
		{
			List<CondOwner> aNearbyCOs = cOsInZone.Where((CondOwner x) => x.objContainer == null && x.GetSlots(bDeep: false).Count == 0).ToList();
			list3 = TileUtils.DropCOsNearby(new List<CondOwner> { objCO }, objShipRef, jsonZone, aNearbyCOs, condTrigger, bAllowLocked);
		}
		if (list3 == null || list3.Count != 0 || !dropInContainersLast)
		{
			list3 = TileUtils.DropCOsNearby(new List<CondOwner> { objCO }, objShipRef, jsonZone, cOsInZone, condTrigger, bAllowLocked);
		}
		CondOwner result = null;
		foreach (CondOwner item in list3)
		{
			result = AddCO(item, bEquip: false, bOverflow: true, bIgnoreLocks: true);
		}
		return result;
	}

	public CondOwner GetCORef(CondOwner objCO)
	{
		if (this == null)
		{
			Debug.Log("ERROR: Getting CO from a null");
			Debug.Break();
			return null;
		}
		if (objCO == null)
		{
			return null;
		}
		if (objCO == this)
		{
			return this;
		}
		if (objCO.strCODef == strCODef && aStack.IndexOf(objCO) >= 0)
		{
			return objCO;
		}
		CondOwner condOwner = null;
		if (objContainer != null)
		{
			condOwner = objContainer.GetCORef(objCO);
		}
		if (condOwner != null)
		{
			return condOwner;
		}
		foreach (Slot slot in GetSlots(bDeep: false))
		{
			if (slot != null)
			{
				condOwner = slot.GetCORef(objCO);
				if (condOwner != null)
				{
					return condOwner;
				}
			}
		}
		return null;
	}

	public int CanStackOnItem(CondOwner objIncoming)
	{
		if (objIncoming == null)
		{
			return 0;
		}
		if (objIncoming == this)
		{
			return 0;
		}
		if (strCODef != objIncoming.strCODef)
		{
			return 0;
		}
		if (bDestroyed || objIncoming.bDestroyed)
		{
			return 0;
		}
		int val = Math.Max(nStackLimit - StackCount, 0);
		if (bFreezeConds)
		{
			val = objIncoming.StackCount;
		}
		return Math.Min(objIncoming.StackCount, val);
	}

	public static CondOwner StackFromList(List<CondOwner> aStack)
	{
		if (aStack.Count == 0)
		{
			return null;
		}
		foreach (CondOwner item in aStack)
		{
			if (item == null || item.aStack == null)
			{
				Debug.LogError("Error: Null entry in stack");
				continue;
			}
			item.aStack.Clear();
			item.coStackHead = null;
		}
		CondOwner condOwner = aStack[aStack.Count - 1];
		foreach (CondOwner item2 in aStack)
		{
			if (item2 == null || condOwner == null)
			{
				Debug.LogError("Error: Null entry in stack");
			}
			else if (item2 != condOwner)
			{
				condOwner.aStack.Add(item2);
				item2.coStackHead = condOwner;
			}
		}
		CondOwner condOwner2 = aStack[aStack.Count - 1];
		foreach (CondOwner item3 in aStack)
		{
			if (item3 == null || condOwner2 == null)
			{
				Debug.LogError("Error: Null entry in stack");
				continue;
			}
			if (item3 != condOwner2)
			{
				item3.tf.SetParent(condOwner2.tf, worldPositionStays: true);
				item3.tf.localPosition = new Vector3(0f, 0f, Container.fZSubOffset);
				item3.Visible = false;
			}
			item3.UpdateAppearance();
		}
		return condOwner;
	}

	public CondOwner PopHeadFromStack()
	{
		if (aStack.Count == 0)
		{
			RemoveFromCurrentHome();
			return null;
		}
		bool visible = Visible;
		Transform parent = tf.parent;
		Container container = null;
		PairXY pairXY = default(PairXY);
		Slot slot = slotNow;
		Ship ship = this.ship;
		if (objCOParent != null)
		{
			container = objCOParent.objContainer;
			pairXY.x = pairInventoryXY.x;
			pairXY.y = pairInventoryXY.y;
		}
		ValidateParent();
		RemoveFromCurrentHome();
		List<CondOwner> stackAsList = StackAsList;
		CheckTrue(stackAsList[stackAsList.Count - 1] == this, "top of stack is no longer head");
		stackAsList.RemoveAt(stackAsList.Count - 1);
		aStack.Clear();
		CondOwner result = StackFromList(stackAsList);
		if (stackAsList.Count > 0)
		{
			CondOwner condOwner = stackAsList[stackAsList.Count - 1];
			condOwner.ValidateParent();
			condOwner.tf.position = new Vector3(tf.position.x, tf.position.y, tf.position.z);
			if (container != null)
			{
				container.AddCOSimple(condOwner, pairXY);
				container.Redraw();
			}
			else if (slot != null && slot.compSlots != null)
			{
				slot.compSlots.SlotItem(slot.strName, condOwner);
			}
			else
			{
				if (ship != null)
				{
					ship.AddCO(condOwner, visible);
				}
				else
				{
					condOwner.tf.SetParent(parent, worldPositionStays: true);
				}
				condOwner.Visible = visible;
			}
			condOwner.UpdateAppearance();
			condOwner.ValidateParent();
		}
		UpdateAppearance();
		ValidateParent();
		return result;
	}

	public CondOwner StackCO(CondOwner objCO)
	{
		if (tf == null)
		{
			Debug.LogError("ERROR: Trying to stack " + objCO?.ToString() + " on null object " + strName);
			return objCO;
		}
		ValidateParentRecursive();
		if (objCO == null)
		{
			return null;
		}
		objCO.ValidateParentRecursive();
		if (coStackHead != null)
		{
			return coStackHead.StackCO(objCO);
		}
		if (objCO.coStackHead != null)
		{
			return StackCO(objCO.coStackHead);
		}
		int num = CanStackOnItem(objCO);
		if (num == 0)
		{
			return objCO;
		}
		if (slotNow != null && slotNow.compSlots != null && slotNow.compSlots.SlotItem(slotNow.strName, objCO))
		{
			return null;
		}
		Vector3 position = objCO.tf.position;
		Transform parent = objCO.tf.parent;
		bool visible = objCO.Visible;
		Vector3 position2 = tf.position;
		Transform parent2 = tf.parent;
		bool visible2 = Visible;
		List<CondOwner> stackAsList = StackAsList;
		List<CondOwner> stackAsList2 = objCO.StackAsList;
		List<CondOwner> list = new List<CondOwner>();
		List<CondOwner> list2 = new List<CondOwner>();
		list.AddRange(stackAsList);
		list.AddRange(stackAsList2.GetRange(stackAsList2.Count - num, num));
		list2 = stackAsList2.GetRange(0, stackAsList2.Count - num);
		foreach (CondOwner item in list)
		{
			if (!(item == null) && !item.bDestroyed)
			{
				item.aStack.Clear();
				item.coStackHead = null;
			}
		}
		foreach (CondOwner item2 in list2)
		{
			if (!item2.bDestroyed)
			{
				item2.aStack.Clear();
				item2.coStackHead = null;
			}
		}
		foreach (CondOwner item3 in list)
		{
			SetIsInOurStack(item3);
		}
		CondOwner condOwner = StackFromList(list);
		CondOwner condOwner2 = StackFromList(list2);
		if (condOwner2 != null)
		{
			condOwner2.Visible = visible;
			condOwner2.tf.position = position;
			condOwner2.tf.SetParent(parent, worldPositionStays: true);
			condOwner2.UpdateAppearance();
		}
		condOwner.Visible = visible2;
		condOwner.tf.position = position2;
		condOwner.tf.SetParent(parent2, worldPositionStays: true);
		condOwner.UpdateAppearance();
		return condOwner2;
	}

	private void SetIsInOurStack(CondOwner co)
	{
		if (co == null)
		{
			Debug.LogWarning("Warning: Attempting to set null in stack of " + strName);
			return;
		}
		co.tf.localPosition = new Vector3(0f, 0f, Container.fZSubOffset);
		if (co.ship != ship)
		{
			if (co.ship != null)
			{
				co.ship.RemoveCO(co);
			}
			if (ship != null)
			{
				ship.AddCO(co, bTiles: false);
			}
		}
		if (co.objCOParent != objCOParent)
		{
			if ((bool)co.objCOParent && co.objCOParent.objContainer != null)
			{
				co.objCOParent.objContainer.RemoveCOSimple(co);
			}
			if (objCOParent != null && objCOParent.objContainer != null && !objCOParent.objContainer.Contains(co))
			{
				objCOParent.objContainer.AddCOSimple(co, pairInventoryXY);
			}
		}
		if (co == objCOParent)
		{
			Debug.Log("ERROR: Assigning self as own parent.");
		}
		co.objCOParent = objCOParent;
	}

	public void UpdateAppearance()
	{
		if (this == null || base.gameObject == null)
		{
			if ((object)this == null)
			{
				Debug.Log("ERROR: Called UpdateAppearance a null");
			}
			else
			{
				Debug.Log("ERROR: Called UpdateAppearanceon a null " + strCODef + ":" + strName);
			}
			Debug.Break();
			return;
		}
		string text = "";
		if (mapAltItemDefs != null && mapAltItemDefs.Count > 0 && objContainer != null && Item != null)
		{
			text = objContainer.GetAltImageMatch(mapAltItemDefs);
			Item.SetAlt(text);
			GUIInventoryItem inventoryItemFromCO = GUIInventory.GetInventoryItemFromCO(this);
			if (inventoryItemFromCO != null)
			{
				GUIInventoryWindow windowData = inventoryItemFromCO.windowData;
				windowData.RemoveAndDestroy(strID);
				GUIInventoryItem.SpawnInventoryItem(strID, windowData);
			}
			Item.VisualizeOverlays();
		}
		if (slotNow != null && CrewSim.inventoryGUI.IsCOShown(RootParent("IsHuman")))
		{
			CrewSim.inventoryGUI.PaperDollManager.UpdatePaperDollImage(this);
		}
		if (txtStack == null)
		{
			if (StackCount <= 1)
			{
				return;
			}
			txtStack = ((GameObject)UnityEngine.Object.Instantiate(Resources.Load("txtStack"), tf)).GetComponent<TMP_Text>();
		}
		txtStack.transform.rotation = Quaternion.identity;
		txtStack.text = "x" + StackCount;
		bool flag = Visible && StackCount > 1;
		if (txtStack.IsActive() != flag)
		{
			txtStack.gameObject.SetActive(flag);
		}
		if (GUIInventory.instance.IsInventoryVisible)
		{
			GUIInventoryItem inventoryItemFromCO2 = GUIInventory.GetInventoryItemFromCO(this);
			if (inventoryItemFromCO2 != null)
			{
				inventoryItemFromCO2.UpdateStackText();
			}
		}
	}

	public void Use(string strUseCase)
	{
		if (strUseCase == null || !mapChargeProfiles.ContainsKey(strUseCase))
		{
			return;
		}
		JsonChargeProfile jsonChargeProfile = mapChargeProfiles[strUseCase];
		if (jsonChargeProfile.fCondAmount != 0f && jsonChargeProfile.strCondName != null)
		{
			float num = jsonChargeProfile.fCondAmount;
			List<CondOwner> list = new List<CondOwner>();
			if (jsonChargeProfile.bUseSelf)
			{
				list.Add(this);
			}
			if (jsonChargeProfile.bUseContained)
			{
				list = GetCOs(bAllowLocked: true);
			}
			if (list != null)
			{
				foreach (CondOwner item in list)
				{
					if (num <= 0f)
					{
						break;
					}
					num = UseCharge(item, jsonChargeProfile.strCondName, num, jsonChargeProfile.fDmgAmountCharge);
				}
			}
		}
		if (jsonChargeProfile.nItemAmount > 0)
		{
			int num2 = jsonChargeProfile.nItemAmount;
			List<CondOwner> list2 = GetCOs(bAllowLocked: true, jsonChargeProfile.CTItem());
			while (list2 != null && num2 > 0)
			{
				if (list2.Count == 0)
				{
					list2 = GetCOs(bAllowLocked: true, jsonChargeProfile.CTItem());
					if (list2 == null || list2.Count == 0)
					{
						break;
					}
				}
				CondOwner condOwner = list2[0];
				if (condOwner.StackCount <= num2)
				{
					num2 -= condOwner.StackCount;
					if (!jsonChargeProfile.bSkipRemove)
					{
						RemoveCO(condOwner);
						condOwner.Destroy();
					}
					list2.RemoveAt(0);
					continue;
				}
				list2 = condOwner.StackAsList;
				for (int i = 0; i < num2; i++)
				{
					if (!jsonChargeProfile.bSkipRemove)
					{
						RemoveCO(list2[i]);
						list2[i].Destroy();
					}
				}
				num2 = 0;
				list2.Clear();
			}
		}
		if (jsonChargeProfile.fDmgAmountUs != 0f)
		{
			AddCondAmount("StatDamage", jsonChargeProfile.fDmgAmountUs);
		}
	}

	private float QueryCharge(CondOwner coUsed, string strCondName, float fCondAmount)
	{
		if (coUsed == null || strCondName == null || fCondAmount == 0f)
		{
			return 0f;
		}
		fCondAmount -= (float)coUsed.GetCondAmount(strCondName);
		if (fCondAmount <= 0f)
		{
			return 0f;
		}
		int num = coUsed.StackCount - 2;
		while (num >= 0 && !(fCondAmount <= 0f))
		{
			fCondAmount = QueryCharge(coUsed.aStack[num], strCondName, fCondAmount);
			num--;
		}
		return fCondAmount;
	}

	private float UseCharge(CondOwner coUsed, string strCondName, float fCondAmount, float fDmgAmountCharge)
	{
		if (coUsed == null)
		{
			return fCondAmount;
		}
		if (fDmgAmountCharge == 0f && (strCondName == null || fCondAmount == 0f))
		{
			return fCondAmount;
		}
		if (coUsed.GetCondAmount(strCondName) >= (double)fCondAmount)
		{
			coUsed.AddCondAmount(strCondName, 0f - fCondAmount);
			if (fDmgAmountCharge != 0f && coUsed != this)
			{
				coUsed.AddCondAmount("StatDamage", fDmgAmountCharge);
			}
			fCondAmount = 0f;
		}
		else
		{
			fCondAmount -= (float)coUsed.GetCondAmount(strCondName);
			coUsed.ZeroCondAmount(strCondName);
			if (fDmgAmountCharge != 0f && coUsed != this)
			{
				coUsed.AddCondAmount("StatDamage", fDmgAmountCharge);
			}
			int num = coUsed.StackCount - 2;
			while (num >= 0 && !(fCondAmount <= 0f))
			{
				fCondAmount = UseCharge(coUsed.aStack[num], strCondName, fCondAmount, fDmgAmountCharge);
				num--;
			}
		}
		return fCondAmount;
	}

	public bool Usable(string strUseCase, out string strOut)
	{
		strOut = "";
		if (strUseCase == null || !mapChargeProfiles.ContainsKey(strUseCase))
		{
			return true;
		}
		JsonChargeProfile jsonChargeProfile = mapChargeProfiles[strUseCase];
		if (jsonChargeProfile.fCondAmount != 0f && jsonChargeProfile.strCondName != null)
		{
			float num = jsonChargeProfile.fCondAmount;
			List<CondOwner> list = new List<CondOwner>();
			if (jsonChargeProfile.bUseSelf)
			{
				list.Add(this);
			}
			if (jsonChargeProfile.bUseContained)
			{
				list = GetCOs(bAllowLocked: true);
			}
			if (list != null)
			{
				foreach (CondOwner item in list)
				{
					if (num <= 0f)
					{
						break;
					}
					num = QueryCharge(item, jsonChargeProfile.strCondName, num);
				}
			}
			if (num > 0f)
			{
				strOut = jsonChargeProfile.strCondName;
				return false;
			}
		}
		if (jsonChargeProfile.nItemAmount > 0)
		{
			int num2 = jsonChargeProfile.nItemAmount;
			List<CondOwner> cOs = GetCOs(bAllowLocked: true, jsonChargeProfile.CTItem());
			if (cOs != null)
			{
				foreach (CondOwner item2 in cOs)
				{
					if (num2 <= 0)
					{
						break;
					}
					num2 -= item2.StackCount;
				}
			}
			if (num2 > 0)
			{
				strOut = jsonChargeProfile.strItemCT;
				return false;
			}
		}
		return true;
	}

	public CondHistory GetCH(string strCond)
	{
		if (!mapIAHist.ContainsKey(strCond))
		{
			mapIAHist[strCond] = new CondHistory(strCond);
		}
		return mapIAHist[strCond];
	}

	public void AddRememberScore(string strCondName, double fCount)
	{
		if (!dictRememberScores.ContainsKey(strCondName))
		{
			dictRememberScores[strCondName] = fCount;
		}
		else
		{
			dictRememberScores[strCondName] += fCount;
		}
	}

	public void RememberLess()
	{
		List<string> list = new List<string>(dictRememberScores.Keys);
		List<string> list2 = new List<string>();
		foreach (string item in list)
		{
			dictRememberScores[item] *= fRememberDecay;
			if (Mathf.Abs((float)dictRememberScores[item]) < 0.25f)
			{
				list2.Add(item);
			}
		}
		foreach (string item2 in list2)
		{
			dictRememberScores.Remove(item2);
		}
		while (aRememberIAs.Count > 5)
		{
			aRememberIAs.RemoveAt(5);
		}
	}

	public void RememberInteractionEffectTraining(string strInteractionName)
	{
		List<string> aConds = new List<string>();
		if (strInteractionName != null)
		{
			Interaction interaction = DataHandler.GetInteraction(strInteractionName);
			if (interaction != null)
			{
				if (interaction.bHumanOnly)
				{
					return;
				}
				aConds = interaction.CTTestThem.GetAllReqNames();
			}
		}
		_RememberInteractionEffect2(aConds);
	}

	public void RememberEffects2(CondOwner objThem)
	{
		if (!bAlive || !HasCond("IsAIAgent") || HasCond("Unconscious") || !(objThem != null))
		{
			return;
		}
		List<string> list = new List<string>();
		Relationship relationship = null;
		if (objThem != this && socUs != null)
		{
			relationship = socUs.GetRelationship(objThem.strID);
		}
		if (relationship != null)
		{
			list = relationship.aReveals;
		}
		else
		{
			foreach (Condition value in objThem.mapConds.Values)
			{
				if ((value.nDisplaySelf == 2 && objThem == this) || (value.nDisplayOther == 2 && objThem != this))
				{
					list.Add(value.strName);
				}
			}
		}
		_RememberInteractionEffect2(list);
	}

	private void _RememberInteractionEffect2(List<string> aConds)
	{
		foreach (KeyValuePair<string, double> dictRememberScore in dictRememberScores)
		{
			if (!hashCondsImportant.Contains(dictRememberScore.Key))
			{
				continue;
			}
			float num = 1f;
			CondHistory cH = GetCH(dictRememberScore.Key);
			bool flag = true;
			foreach (string aRememberIA in aRememberIAs)
			{
				if (aAIRandomAvoid.Contains(aRememberIA))
				{
					continue;
				}
				cH.AddInteractionScore(aRememberIA, (float)dictRememberScore.Value * num, flag);
				if (flag)
				{
					foreach (string aCond in aConds)
					{
						cH.AddCondScore(aRememberIA, aCond, (float)dictRememberScore.Value * num, flag);
					}
					flag = false;
				}
				num *= fRememberDecay;
			}
		}
	}

	private Interaction Interact()
	{
		while (aQueue.Count > 0 && aQueue[0] == null)
		{
			ClearInteraction(aQueue[0]);
		}
		if (aQueue.Count == 0)
		{
			return null;
		}
		Interaction interaction = aQueue[0];
		bool flag = false;
		if (Pathfinder != null)
		{
			if (!Pathfinder.InRange())
			{
				flag = true;
			}
		}
		else
		{
			Vector2 pos = interaction.objThem.GetPos(interaction.strTargetPoint);
			Vector2 vector = new Vector2(tf.position.x, tf.position.y);
			float num = 1.5f + interaction.fTargetPointRange;
			if (Mathf.Abs(vector.x - pos.x) > num || Mathf.Abs(vector.y - pos.y) > num)
			{
				flag = true;
			}
		}
		if (flag)
		{
			if (interaction.bTryWalk || !CheckWalk(interaction, interaction.objThem))
			{
				ClearInteraction(interaction);
				return null;
			}
			interaction.bTryWalk = true;
		}
		if (interaction.bApplyChain)
		{
			interaction.ApplyChain();
		}
		else
		{
			interaction.ApplyEffects();
		}
		if (bDestroyed)
		{
			return null;
		}
		if (IsHumanOrRobot && interaction.strName != null && DataHandler.dictSocialStats.ContainsKey(interaction.strName))
		{
			DataHandler.dictSocialStats[interaction.strName].nUsed++;
			if (interaction.strChainStart == interaction.strName)
			{
				DataHandler.dictSocialStats[interaction.strName].nChecked++;
			}
		}
		Interaction interaction2 = null;
		if (!interaction.bApplyChain && interaction.aInverse != null && interaction.aInverse.Length != 0)
		{
			bool flag2 = false;
			bool flag3 = false;
			if (interaction.bImmediateReply || interaction.bIgnoreFeelings || pspec == null)
			{
				interaction2 = interaction.GetReply();
				if (interaction2 != null && interaction2.objUs == this)
				{
					flag2 = true;
				}
				if (pspec != null && interaction.objThem.pspec != null)
				{
					flag3 = true;
				}
			}
			else
			{
				flag3 = true;
				string text = interaction.aInverse[0];
				if (!string.IsNullOrEmpty(text))
				{
					string[] array = text.Split(',');
					if (array.Length > 1 && array[1] == "[us]")
					{
						flag2 = true;
					}
				}
			}
			if (flag3)
			{
				if (flag2)
				{
					interaction.objUs.AddReplyThread(StarSystem.fEpoch, interaction.objThem.strID, interaction);
				}
				else
				{
					interaction.objThem.AddReplyThread(StarSystem.fEpoch, strID, interaction);
				}
			}
		}
		if (CrewSim.bRaiseUI && interaction.objUs != interaction.objThem && interaction.objThem == CrewSim.GetSelectedCrew() && CanvasManager.instance.State != CanvasManager.GUIState.SOCIAL && interaction.strName != "Wait" && interaction.strName != "QuickWait" && interaction.strName != "Walk")
		{
			interaction.objThem.AICancelAll(interaction.objUs);
		}
		dictRecentlyTried[interaction.objThem.strID + interaction.strName] = StarSystem.fEpoch;
		ClearInteraction(interaction);
		if (Item != null)
		{
			Item.VisualizeOverlays();
		}
		return interaction2;
	}

	public void ModeSwitch(CondOwner coNew, Vector3 vDropPos)
	{
		ValidateParentRecursive();
		if (coNew == null)
		{
			return;
		}
		coNew.ValidateParentRecursive();
		if (elec != null)
		{
			if (coNew.elec != null)
			{
				elec.CleanUp(disconnect: false);
			}
			else
			{
				elec.CleanUp(disconnect: true);
			}
		}
		Item item = coNew.Item;
		Item item2 = Item;
		bool highlight = Highlight;
		bool dimLights = DimLights;
		Transform transform = coNew.tf;
		float fLastRotation = tf.rotation.eulerAngles.z;
		if (item2 != null)
		{
			fLastRotation = item2.fLastRotation;
		}
		if (item != null)
		{
			item.fLastRotation = fLastRotation;
			vDropPos.z = item.GetZPos();
		}
		transform.position = vDropPos;
		if (HasCond("IsAirtight") && !coNew.HasCond("IsAirtight"))
		{
			ZeroCondAmount("IsAirtight");
		}
		CondOwner condOwner = this;
		if (strPersistentCO != null && DataHandler.mapCOs.ContainsKey(strPersistentCO))
		{
			condOwner = DataHandler.mapCOs[strPersistentCO];
		}
		else if (strPersistentCT != null && aLot.Count > 0)
		{
			CondTrigger condTrigger = DataHandler.GetCondTrigger(strPersistentCT);
			foreach (CondOwner item3 in aLot)
			{
				if (condTrigger.Triggered(item3))
				{
					condOwner = item3;
					break;
				}
			}
		}
		COOverlay component = condOwner.GetComponent<COOverlay>();
		if (component != null)
		{
			string text = component.ModeSwitch(coNew.strCODef);
			if (text != null)
			{
				coNew.gameObject.AddComponent<COOverlay>().Init(text);
			}
		}
		foreach (Condition value in condOwner.mapConds.Values)
		{
			if (value.bPersists)
			{
				coNew.AddCondAmount(value.strName, value.fCount - coNew.GetCondAmount(value.strName), value.GetAge());
			}
		}
		foreach (string aCondZero in condOwner.aCondZeroes)
		{
			double condAmount = coNew.GetCondAmount(aCondZero);
			coNew.AddCondAmount(aCondZero, 0.0 - condAmount);
			if (!coNew.aCondZeroes.Contains(aCondZero))
			{
				coNew.aCondZeroes.Add(aCondZero);
			}
		}
		coNew.strID = condOwner.strID;
		foreach (KeyValuePair<string, Dictionary<string, string>> mapGUIPropMap in condOwner.mapGUIPropMaps)
		{
			coNew.mapGUIPropMaps[mapGUIPropMap.Key] = mapGUIPropMap.Value;
		}
		List<CondOwner> list = new List<CondOwner>();
		if (condOwner.objContainer != null)
		{
			list.AddRange(condOwner.objContainer.GetCOs(bAllowLocked: true));
		}
		for (int num = list.Count - 1; num >= 0; num--)
		{
			if (list[num].coStackHead != null)
			{
				list.RemoveAt(num);
			}
			else if (list[num].objCOParent != condOwner)
			{
				list.RemoveAt(num);
			}
		}
		Dictionary<CondOwner, string> dictionary = new Dictionary<CondOwner, string>();
		if (compSlots != null)
		{
			GatherSlottedItems(compSlots, dictionary);
		}
		else if (condOwner.compSlots != null)
		{
			GatherSlottedItems(condOwner.compSlots, dictionary);
		}
		Slot slot = null;
		CondOwner condOwner2 = objCOParent;
		if (HasCond("IsSlotted") && objCOParent != null && objCOParent.compSlots != null)
		{
			slot = objCOParent.compSlots.GetSlotForCO(this);
		}
		bool flag = false;
		if (HasCond("IsCheckRoom") && coNew.HasCond("IsCheckRoom") && item.nWidthInTiles == item2.nWidthInTiles && item.nHeightInTiles == item2.nHeightInTiles)
		{
			AddCondAmount("IsModeSwitching", 1.0);
			coNew.AddCondAmount("IsModeSwitching", 1.0);
			coNew.ZeroCondAmount("IsCheckRoom");
			flag = true;
		}
		if (GUISocialCombat2.coUs == this)
		{
			GUISocialCombat2.coUs = coNew;
		}
		if (GUISocialCombat2.coThem == this)
		{
			GUISocialCombat2.coThem = coNew;
		}
		bool bCheckRooms = this.ship.bCheckRooms;
		Ship ship = this.ship;
		if (aStack != null && aStack.Count > 0)
		{
			PopHeadFromStack();
		}
		else if (coStackHead != null)
		{
			coStackHead.RemoveCO(this);
		}
		else
		{
			RemoveFromCurrentHome();
		}
		if (condOwner2 == null)
		{
			Vector3 vFits = default(Vector3);
			if (!coNew.HasCond("IsInstalled") && !item.CheckFit(vDropPos, ship))
			{
				bool num2 = Vector3.Distance(vDropPos, coNew.tf.position) < 0.01f;
				ship.ShiftTorwardsClosestCrewMember(coNew, 1f);
				vDropPos = (num2 ? coNew.tf.position : vDropPos);
				if (TileUtils.TryFitItem(item, ship, vDropPos, out vFits))
				{
					vFits.z = transform.position.z;
					transform.position = vFits;
					ship.AddCO(coNew, bTiles: true);
				}
				else if (DropCO(coNew, bAllowLocked: false, ship) != null)
				{
					ship.AddCO(coNew, bTiles: true);
				}
			}
			else
			{
				ship.AddCO(coNew, bTiles: true);
			}
		}
		else if (slot != null)
		{
			if (!condOwner2.compSlots.SlotItem(slot.strName, coNew))
			{
				Debug.Log("Couldn't slot " + coNew.strName + " into " + slot.strName + " upon modeswitch!");
				CondOwner condOwner3 = condOwner2.DropCO(coNew, bAllowLocked: false);
				if (condOwner3 != null)
				{
					Debug.Log("Couldn't drop " + condOwner3.strName + " upon modeswitch!");
					ship.AddCO(coNew, bTiles: true);
				}
			}
		}
		else
		{
			CondOwner objCO = condOwner2.AddCO(coNew, bEquip: false, bOverflow: true, bIgnoreLocks: true);
			DropCO(objCO, bAllowLocked: false, ship);
		}
		foreach (CondOwner item4 in list)
		{
			item4.RemoveFromCurrentHome();
			CondOwner objCO2 = coNew.AddCO(item4, bEquip: false, bOverflow: true, bIgnoreLocks: true);
			DropCO(objCO2, bAllowLocked: false, ship);
		}
		List<CondOwner> list2 = new List<CondOwner>();
		List<CondOwner> list3 = null;
		foreach (KeyValuePair<CondOwner, string> item5 in dictionary)
		{
			item5.Key.RemoveFromCurrentHome(bForce: true);
			if (coNew.compSlots != null && coNew.compSlots.SlotItem(item5.Value, item5.Key))
			{
				continue;
			}
			if (item5.Key.bSlotLocked)
			{
				if (list3 == null)
				{
					list3 = new List<CondOwner>();
				}
				list3.Add(item5.Key);
				if (item5.Key.objContainer == null)
				{
					continue;
				}
				List<CondOwner> cOs = item5.Key.objContainer.GetCOs(bAllowLocked: false);
				if (cOs == null)
				{
					continue;
				}
				foreach (CondOwner item6 in cOs)
				{
					if (item6.bSlotLocked)
					{
						continue;
					}
					item6.RemoveFromCurrentHome();
					CondOwner condOwner4 = coNew.AddCO(item6, bEquip: true, bOverflow: true, bIgnoreLocks: true);
					if (condOwner4 != null && condOwner2 != null)
					{
						condOwner4 = condOwner2.AddCO(item6, bEquip: false, bOverflow: true, bIgnoreLocks: true);
					}
					if (condOwner4 != null)
					{
						if (!item6.HasCond("IsSolid"))
						{
							list3.Add(item6);
						}
						else if (ship != null)
						{
							DropCO(item6, bAllowLocked: false, ship);
						}
					}
				}
			}
			else
			{
				DropCO(item5.Key, bAllowLocked: false, ship);
				list2.Add(item5.Key);
			}
		}
		ReslotFailedCOs(list2, coNew);
		if (list3 != null)
		{
			foreach (CondOwner item7 in list3)
			{
				item7.Destroy();
			}
		}
		if (flag)
		{
			coNew.AddCondAmount("IsCheckRoom", 1.0);
			ship.bCheckRooms = bCheckRooms;
		}
		coNew.CheckForRename();
		CrewSim.objInstance.SetBracketTarget(strID, bUpdateOnly: true);
		if (GUIMegaToolTip.Selected == this)
		{
			CrewSim.OnRightClick.Invoke(new List<CondOwner> { coNew });
		}
		aTickers.Clear();
		while (aLot.Count > 0)
		{
			CondOwner condOwner5 = aLot[0];
			RemoveLotCO(condOwner5);
			condOwner5.Destroy();
		}
		UnityEngine.Object.Destroy(base.gameObject);
		Highlight = highlight;
		DimLights = dimLights;
		if (!AudioManager.bIgnoreCOTrans)
		{
			AudioEmitter component2 = coNew.GetComponent<AudioEmitter>();
			if (component2 != null)
			{
				component2.StartTrans();
			}
		}
		ValidateParentRecursive();
		coNew.ValidateParentRecursive();
		double condAmount2 = coNew.GetCondAmount("StatDamageMax");
		double num3 = condAmount2 * 1.0 / 8000.0;
		if (HasCond("IsSolidState"))
		{
			num3 = 0.0;
		}
		num3 += condAmount2 * fMSRedamageAmount;
		coNew.AddCondAmount("StatDamage", num3);
		item.VisualizeOverlays();
	}

	private void GatherSlottedItems(Slots compSlotsIn, Dictionary<CondOwner, string> mapSlottedSubCOs)
	{
		foreach (Slot item in compSlotsIn.GetSlotsDepthFirst(bDeep: false))
		{
			CondOwner[] aCOs = item.aCOs;
			foreach (CondOwner condOwner in aCOs)
			{
				if (!(condOwner == null))
				{
					mapSlottedSubCOs[condOwner] = item.strName;
				}
			}
		}
	}

	private void ReslotFailedCOs(IEnumerable<CondOwner> failedItems, CondOwner coNew, string rootCondition = "IsHuman")
	{
		if (coNew == null || failedItems == null)
		{
			return;
		}
		foreach (CondOwner failedItem in failedItems)
		{
			CondOwner condOwner = coNew.RootParent(rootCondition);
			if (condOwner != null && failedItem.mapSlotEffects != null && failedItem.mapSlotEffects.Count > 0)
			{
				string key = failedItem.mapSlotEffects.First().Key;
				Ship objShipRef = failedItem.RemoveFromCurrentHome();
				if (condOwner.compSlots.SlotItem(key, failedItem))
				{
					Debug.Log("<color=yellow>Reslotted " + failedItem.strName + " to " + failedItem.transform.GetPath() + "</color>");
				}
				else
				{
					Debug.Log("<color=yellow>Failed to reslot item: " + failedItem.strName + " on " + coNew.strName + " again, was supposed to go to " + coNew.transform.GetPath() + "</color>");
					DropCO(failedItem, bAllowLocked: false, objShipRef);
				}
			}
		}
	}

	public bool QueueInteraction(CondOwner objTarget, Interaction objInteraction, bool bInsert = false)
	{
		if (objInteraction == null || this == null)
		{
			return false;
		}
		objInteraction.objUs = this;
		objInteraction.objThem = objTarget;
		if (objInteraction.strChainOwner == null)
		{
			objInteraction.strChainOwner = strID;
		}
		if (bInsert)
		{
			aQueue.Insert(0, objInteraction);
		}
		else
		{
			aQueue.Add(objInteraction);
		}
		SetCondAmount("TaskBusy", 1.0);
		if (aQueue[0] == objInteraction)
		{
			float num = -1f;
			if (objInteraction.strName != "Walk" && !HasCond("IsSpaced") && Pathfinder != null)
			{
				Tile tile = Pathfinder.tilCurrent;
				if (objInteraction.strTargetPoint != null && objInteraction.strTargetPoint != Interaction.POINT_REMOTE)
				{
					Vector2 vector = objInteraction.objThem.GetPos(objInteraction.strTargetPoint);
					if (GetCORef(objInteraction.objThem) != null)
					{
						vector = tf.position;
					}
					tile = ship.GetTileAtWorldCoords1(vector.x, vector.y, bAllowDocked: true);
				}
				num = ((!(tile == Pathfinder.tilCurrent)) ? Pathfinder.SetGoal2(tile, objInteraction.fTargetPointRange, objInteraction.objThem, 0f, 0f, HasAirlockPermission(objInteraction.bManual)).PathLength : 0f);
				if (num > 0f && !CTCanWalk.Triggered(this))
				{
					string strMsg = FriendlyName + DataHandler.GetString("ERROR_STUNNED") + CTCanWalk.strFailReasonLast;
					LogMessage(strMsg, "Bad", strName);
					ClearInteraction(objInteraction);
					return false;
				}
				if (num < 0f)
				{
					string text = objInteraction.objThem.strName;
					if (objInteraction.objThem.strNameFriendly != null)
					{
						text = objInteraction.objThem.strNameFriendly;
					}
					LogMessage(DataHandler.GetString("ERROR_CANT_REACH_DEST") + text + ".", "Bad", strName);
					Debug.Log(DataHandler.GetString("ERROR_CANT_REACH_DEST") + objInteraction.strName + "; Target: " + text + ".");
					ClearInteraction(objInteraction);
					return false;
				}
				if (num == 0f && objInteraction.fDuration != 0.0 && objInteraction.strName != "Inventory")
				{
					double num2 = StarSystem.fEpoch - fLastICOUpdate;
					objInteraction.fDuration += num2 / 3600.0;
				}
			}
			if (num == 0f && objInteraction.objThem != this)
			{
				LookAt(objInteraction.objThem);
			}
			for (int i = 0; i < aTickers.Count; i++)
			{
				JsonTicker jsonTicker = aTickers[i];
				if (jsonTicker.bQueue || jsonTicker.strName == "AIAgent")
				{
					aTickers.Remove(jsonTicker);
					i--;
				}
			}
			JsonTicker jsonTicker2 = new JsonTicker();
			jsonTicker2.strName = objInteraction.strName;
			jsonTicker2.bQueue = true;
			jsonTicker2.fPeriod = objInteraction.fDuration;
			jsonTicker2.SetTimeLeft(jsonTicker2.fPeriod);
			AddTicker(jsonTicker2);
			if (jsonTicker2.fPeriod != 0.0)
			{
				jsonTicker2 = jsonTicker2.Clone();
				jsonTicker2.fPeriod = 0.0;
				jsonTicker2.SetTimeLeft(jsonTicker2.fPeriod);
				AddTicker(jsonTicker2);
			}
		}
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		if (selectedCrew != null && selectedCrew == this)
		{
			MonoSingleton<GUIQuickBar>.Instance.SetDirty();
		}
		if (OnQueueInteraction != null)
		{
			OnQueueInteraction(objInteraction);
		}
		return true;
	}

	public void ClearInteraction(Interaction objInteraction, bool bCancelling = false)
	{
		if (objInteraction == null || this == null)
		{
			return;
		}
		int num = aQueue.IndexOf(objInteraction);
		bool isHumanOrRobot = IsHumanOrRobot;
		bool flag = HasCond("IsInCombat");
		bool flag2 = CrewSim.GetSelectedCrew() == this && (flag || objInteraction.strActionGroup == "Fight") && objInteraction.objUs == this && objInteraction.fDurationOrig > 0.0;
		bool flag3 = false;
		string strReason = null;
		if (flag2)
		{
			strReason = objInteraction.strTitle + DataHandler.GetString("AUTOPAUSE_ACT_ENDED");
		}
		else if (!flag && objInteraction.strActionGroup == "Talk" && objInteraction.aInverse != null)
		{
			if (objInteraction.aInverse.Length != 0)
			{
				if (!string.IsNullOrEmpty(objInteraction.aInverse[0]))
				{
					string[] array = objInteraction.aInverse[0].Split(',');
					bool flag4 = !string.IsNullOrEmpty(objInteraction.strLootContextThem) && objInteraction.strLootContextThem != "Default";
					if ((array.Length == 1 || array[1] != "[us]") && (!AutoPauseIgnore(array[0]) || flag4))
					{
						if (objInteraction.objThem == CrewSim.GetSelectedCrew())
						{
							flag2 = true;
							flag3 = true;
							strReason = FriendlyName + DataHandler.GetString("AUTOPAUSE_NPC_REPLIED");
						}
						else if (objInteraction.objUs != CrewSim.GetSelectedCrew())
						{
							flag3 = true;
						}
					}
				}
			}
			else if (!(this == CrewSim.GetSelectedCrew()) && objInteraction.objThem == CrewSim.GetSelectedCrew() && !AutoPauseIgnore(objInteraction.strName))
			{
				flag2 = true;
				strReason = FriendlyName + DataHandler.GetString("AUTOPAUSE_NPC_REPLIED");
				flag3 = true;
			}
		}
		if (objInteraction.fDuration > 0.0 && objInteraction.aDependents != null && objInteraction.aDependents.Count > 0)
		{
			foreach (string aDependent in objInteraction.aDependents)
			{
				for (int i = num + 1; i < aQueue.Count; i++)
				{
					if (aQueue[i].objThem == null)
					{
						Debug.LogWarning("Null target on interaction " + aQueue[i].ToString());
						aQueue.RemoveAt(i);
					}
					else if (aQueue[i].strName + aQueue[i].objThem.strID == aDependent)
					{
						if (isHumanOrRobot)
						{
							CrewSim.objInstance.workManager.UnclaimTask(aQueue[i]);
						}
						aQueue.RemoveAt(i);
						break;
					}
				}
			}
		}
		if (aQueue.Remove(objInteraction))
		{
			if (isHumanOrRobot)
			{
				CrewSim.objInstance.workManager.UnclaimTask(objInteraction);
			}
			if (objInteraction != null && objInteraction.objThem != null && objInteraction.objThem.tf != null && objInteraction.strName != "Wait")
			{
				objInteraction.objThem.WaitFor(this, bRelease: true);
			}
			if (num == 0)
			{
				for (int j = 0; j < aTickers.Count; j++)
				{
					JsonTicker jsonTicker = aTickers[j];
					if (jsonTicker.bQueue)
					{
						aTickers.Remove(jsonTicker);
						j--;
					}
				}
				if (progressBar != null)
				{
					progressBar.DeactivateImmediate();
				}
			}
			if (objInteraction.bRaisedUI && (CrewSim.GetSelectedCrew() == objInteraction.objUs || CrewSim.GetSelectedCrew() == objInteraction.objThem))
			{
				CrewSim.LowerUI();
			}
		}
		if (bCancelling && objInteraction.strCancelInteraction != null)
		{
			Interaction interaction = DataHandler.GetInteraction(objInteraction.strCancelInteraction, null, getTrackedObject: true);
			if (interaction != null)
			{
				interaction.objUs = objInteraction.objUs;
				interaction.objThem = objInteraction.objThem;
				interaction.ApplyEffects(null, isCancelIa: true);
				DataHandler.ReleaseTrackedInteraction(interaction);
			}
		}
		if (aQueue.Count == 0)
		{
			ZeroCondAmount("TaskBusy");
			if (HasCond("IsAIAgent"))
			{
				JsonTicker ticker = DataHandler.GetTicker("AIAgent");
				ticker.SetTimeLeft(5E-05);
				AddTicker(ticker);
			}
		}
		else if (aQueue[0] != null)
		{
			bool flag5 = aQueue[0].objThem != null && aQueue[0].objThem.tf != null;
			if (Pathfinder != null && ship != null && !ship.bDestroyed)
			{
				Tile tile = Pathfinder.tilCurrent;
				if (GetCORef(aQueue[0].objThem) != null)
				{
					tile = tile;
				}
				else if (aQueue[0].strTargetPoint != null && objInteraction.strTargetPoint != Interaction.POINT_REMOTE && flag5)
				{
					Vector2 pos = aQueue[0].objThem.GetPos(aQueue[0].strTargetPoint);
					tile = ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
				}
				if (!Pathfinder.SetGoal2(tile, aQueue[0].fTargetPointRange, aQueue[0].objThem, 0f, 0f, HasAirlockPermission(objInteraction.bManual)).HasPath)
				{
					ClearInteraction(aQueue[0]);
					return;
				}
			}
			if (num == 0)
			{
				JsonTicker jsonTicker2 = new JsonTicker();
				jsonTicker2.strName = aQueue[0].strName;
				jsonTicker2.bQueue = true;
				jsonTicker2.fPeriod = aQueue[0].fDuration;
				jsonTicker2.SetTimeLeft(jsonTicker2.fPeriod);
				AddTicker(jsonTicker2);
				if (jsonTicker2.fPeriod != 0.0)
				{
					jsonTicker2 = jsonTicker2.Clone();
					jsonTicker2.fPeriod = 0.0;
					jsonTicker2.SetTimeLeft(jsonTicker2.fPeriod);
					AddTicker(jsonTicker2);
				}
			}
			if (aQueue[0].strThemType != Interaction.TARGET_SELF)
			{
				LookAt(aQueue[0].objThem);
			}
		}
		if (objInteraction != null)
		{
			objInteraction = objInteraction.Destroy();
		}
		if (flag2 && aQueue.Count == 0)
		{
			CrewSim.ScheduleAutoPause(0.5, strReason);
		}
		if (flag3)
		{
			QueueInteraction(this, DataHandler.GetInteraction("QuickWait"));
		}
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		if (selectedCrew != null && selectedCrew == this)
		{
			MonoSingleton<GUIQuickBar>.Instance.SetDirty();
		}
	}

	public void WaitFor(CondOwner objCO, bool bRelease)
	{
		if (objCO == null || objCO == this)
		{
			return;
		}
		Interaction interaction = null;
		foreach (Interaction item in aQueue)
		{
			if (item.strName == "Wait" && objCO == item.objThem)
			{
				interaction = item;
				break;
			}
		}
		if (!bRelease && interaction == null)
		{
			QueueInteraction(objCO, DataHandler.GetInteraction("Wait"), bInsert: true);
			if (objCOParent != null && objCOParent != objCO)
			{
				objCOParent.WaitFor(objCO, bRelease: false);
			}
		}
		if (bRelease && interaction != null)
		{
			interaction.fDuration = 0.0;
			SetTicker(interaction.strName, 0f);
			UpdateManual();
			if (objCOParent != null && objCOParent != objCO)
			{
				objCOParent.WaitFor(objCO, bRelease: true);
			}
		}
	}

	public void LookAt(CondOwner objTarget, bool bLookBack = false)
	{
		if (!(Pathfinder == null) && !(objTarget == null))
		{
			tf.rotation = Quaternion.LookRotation(Vector3.forward, objTarget.tf.position - tf.position);
			if (bLookBack)
			{
				objTarget.LookAt(this);
			}
		}
	}

	public void AICancelCurrent()
	{
		Interaction interactionCurrent = GetInteractionCurrent();
		if (interactionCurrent != null)
		{
			interactionCurrent.bCancel = true;
			JsonTicker jsonTicker = new JsonTicker();
			jsonTicker.bQueue = true;
			jsonTicker.strName = "Cleanup canceled interactions.";
			jsonTicker.fPeriod = 0.0;
			jsonTicker.SetTimeLeft(jsonTicker.fPeriod);
			AddTicker(jsonTicker);
		}
	}

	private void AIHandleCancels()
	{
		if (aQueue.Count == 0)
		{
			return;
		}
		int num = 0;
		bool flag = false;
		for (Interaction interaction = aQueue[num]; interaction != null; interaction = aQueue[num])
		{
			if (interaction.bCancel)
			{
				int count = aQueue.Count;
				ClearInteraction(interaction, bCancelling: true);
				if (count == aQueue.Count)
				{
					num++;
				}
				else if (interaction.strRaiseUI == "SocialCombat")
				{
					GUISocialCombat2.objInstance.EndSocialCombat();
				}
				flag = true;
			}
			else
			{
				num++;
			}
			if (num >= aQueue.Count)
			{
				break;
			}
		}
		if (flag && bAlive)
		{
			AddCondAmount("IsCrewToolSpark", 0.0 - GetCondAmount("IsCrewToolSpark"));
		}
	}

	public void AICancelTargeted(CondOwner coTarget)
	{
		if (aQueue == null || aQueue.Count == 0)
		{
			return;
		}
		bool flag = false;
		for (int i = 0; i < aQueue.Count; i++)
		{
			Interaction interaction = aQueue[i];
			if (interaction != null && !interaction.bCloser && !interaction.bCancel && !interaction.bIgnoreCancel && interaction.objThem == coTarget)
			{
				interaction.bCancel = true;
				flag = true;
			}
		}
		if (flag)
		{
			JsonTicker jsonTicker = new JsonTicker();
			jsonTicker.bQueue = true;
			jsonTicker.strName = "Cleanup canceled interactions.";
			jsonTicker.fPeriod = 0.0;
			jsonTicker.SetTimeLeft(jsonTicker.fPeriod);
			AddTicker(jsonTicker);
		}
	}

	public void AICancelAll(CondOwner coException = null)
	{
		if (!IsHumanOrRobot || aQueue.Count == 0)
		{
			return;
		}
		bool flag = false;
		int num = 0;
		for (Interaction interaction = aQueue[num]; interaction != null; interaction = aQueue[num])
		{
			if (!interaction.bCloser && !interaction.bCancel && !interaction.bIgnoreCancel)
			{
				CondOwner objThem = interaction.objThem;
				if (coException == null || coException != objThem || interaction.strSubUI != null)
				{
					interaction.bCancel = true;
					flag = true;
				}
			}
			num++;
			if (num >= aQueue.Count)
			{
				break;
			}
		}
		if (flag)
		{
			JsonTicker jsonTicker = new JsonTicker();
			jsonTicker.bQueue = true;
			jsonTicker.strName = "Cleanup canceled interactions.";
			jsonTicker.fPeriod = 0.0;
			jsonTicker.SetTimeLeft(jsonTicker.fPeriod);
			AddTicker(jsonTicker);
		}
	}

	public bool AIIssueOrder(CondOwner coTarget, Interaction objInt, bool bPlayerOrdered, Tile til, float fPosX = 0f, float fPosY = 0f)
	{
		if (!Kill)
		{
			return false;
		}
		if (bPlayerOrdered && HasCond("Stunned") && !CTCanAIOrder.Triggered(this))
		{
			string strMsg = FriendlyName + DataHandler.GetString("ERROR_STUNNED") + CTCanAIOrder.strFailReasonLast;
			LogMessage(strMsg, "Bad", strName);
			return false;
		}
		AICancelAll();
		if (bPlayerOrdered && !HasCond("IsPlayer"))
		{
			FreeWillPenalty.ApplyCondLoot(this, 1f);
			Interaction interaction = DataHandler.GetInteraction("SeekSocialDeny");
			interaction.objUs = this;
			interaction.objThem = CrewSim.coPlayer;
			if (interaction.Triggered(interaction.objUs, interaction.objThem, bStats: false, bIgnoreItems: false, bCheckPath: true))
			{
				Pathfinder.Reset();
				QueueInteraction(interaction.objThem, interaction);
				return true;
			}
		}
		if (coTarget != null && objInt != null)
		{
			if (Pathfinder == null)
			{
				Debug.Log($"WARNING: Order {objInt.strName} Issued to non-pathfinding object {strName} with target {coTarget.strName}.");
			}
			else
			{
				Pathfinder.Reset();
			}
			QueueInteraction(coTarget, objInt);
			if (Pathfinder != null)
			{
				Pathfinder.VisualisePath(Pathfinder.currentPath);
			}
			return true;
		}
		if (til != null)
		{
			bool flag = false;
			if (CTIsProneAwake.Triggered(this))
			{
				Interaction interaction2 = DataHandler.GetInteraction("ACTStandUp");
				interaction2.bManual = bPlayerOrdered;
				if (QueueInteraction(this, interaction2))
				{
					flag = true;
				}
			}
			if (!(CTCanWalk.Triggered(this) || flag))
			{
				string strMsg2 = FriendlyName + DataHandler.GetString("ERROR_STUNNED") + CTCanWalk.strFailReasonLast;
				LogMessage(strMsg2, "Bad", strName);
				return false;
			}
			PathResult pathResult = Pathfinder.SetGoal2(til, 0f, null, fPosX, fPosY, HasAirlockPermission(bPlayerOrdered));
			if (pathResult.HasPath)
			{
				_ = Time.realtimeSinceStartup;
				Pathfinder.VisualisePath(Pathfinder.currentPath);
				Interaction interaction3 = DataHandler.GetInteraction("Walk");
				interaction3.bManual = bPlayerOrdered;
				if (QueueInteraction(this, interaction3))
				{
					interaction3.objThem = til.coProps;
					interaction3.strTargetPoint = "use";
					interaction3.fTargetPointRange = 0f;
					return true;
				}
				LogMessage(DataHandler.GetString("AI_PATHFIND_NO_GENERAL"), "Bad", strName);
			}
			else
			{
				string text = pathResult.FailReason(this);
				if (string.IsNullOrEmpty(text))
				{
					text = DataHandler.GetString("AI_PATHFIND_NO_GENERAL");
				}
				LogMessage(text, "Bad", strName);
				if (bPlayerOrdered)
				{
					TriggerRosterPermissionTutorial(pathResult);
				}
			}
		}
		return false;
	}

	private void TriggerRosterPermissionTutorial(PathResult pr)
	{
		if (!CrewSim.objInstance.bHasSeenRosterTutorial && pr != null && pr.bAirlockBlocked && !pr.bDisembarkBlocked && !(CrewSim.coPlayer != this) && CrewSim.coPlayer.HasCond("IsAIManual"))
		{
			CrewSim.objInstance.bHasSeenRosterTutorial = CrewSim.coPlayer.HasCond("TutorialRosterShow") || CrewSim.coPlayer.HasCond("TutorialRosterComplete");
			if (!CrewSim.objInstance.bHasSeenRosterTutorial)
			{
				CrewSimTut.BeginTutorialBeat<RosterPermission>();
				CrewSim.coPlayer.AddCondAmount("TutorialRosterShow", 1.0);
				CrewSim.objInstance.bHasSeenRosterTutorial = true;
			}
		}
	}

	public void CatchUp(bool bSubItems)
	{
		double num = StarSystem.fEpoch - fLastICOUpdate;
		fLastICOUpdate = StarSystem.fEpoch;
		if (num != 0.0)
		{
			float elapsed = Convert.ToSingle(num);
			aCondsTemp.AddRange(aCondsTimed);
			foreach (Condition item in aCondsTemp)
			{
				item.Update(elapsed, this);
			}
			aCondsTemp.Clear();
		}
		if (Company != null)
		{
			int hourFromS = MathUtils.GetHourFromS(StarSystem.fEpoch);
			if (hourFromS != MathUtils.GetHourFromS(StarSystem.fEpoch - num))
			{
				ShiftChange(Company.GetShift(hourFromS, this), bSilent: false);
			}
		}
		CondOwnerVisitorCatchUp visitor = new CondOwnerVisitorCatchUp();
		VisitCOs(visitor, bAllowLocked: true);
		if (aTickers == null)
		{
			Debug.LogWarning("null aTickers found on " + strName + ". Skipping.");
			return;
		}
		List<JsonTicker> list = new List<JsonTicker>();
		foreach (JsonTicker aTicker in aTickers)
		{
			if (aTicker.bTickWhileAway)
			{
				list.Add(aTicker);
				continue;
			}
			double num2 = 0.0;
			if (aTicker.bQueue && aTicker.fPeriod > 0.0 && aQueue.Count > 0)
			{
				num2 = ((!aQueue[0].bCancel) ? (aQueue[0].fDuration - num / 3600.0) : 0.0);
				if (num < 0.0)
				{
					Debug.Log("    ********" + aQueue[0].strName + " catchup = " + num);
				}
				aQueue[0].fDuration = num2;
			}
			else if (aTicker.strCondUpdate == null || !mapConds.ContainsKey(aTicker.strCondUpdate))
			{
				num2 = aTicker.fTimeLeft % aTicker.fPeriod;
				if (num2 < 0.0)
				{
					num2 += aTicker.fPeriod;
				}
			}
			if (double.IsNaN(num2))
			{
				num2 = 0.0;
			}
			aTicker.SetTimeLeft(num2);
		}
		foreach (JsonTicker item2 in list)
		{
			RemoveTicker(item2);
			if (item2.fTimeLeft <= 0.0 && !string.IsNullOrEmpty(item2.strCondUpdate))
			{
				Condition value = null;
				if (mapConds.TryGetValue(item2.strCondUpdate, out value))
				{
					value.Update((float)(StarSystem.fEpoch - item2.fEpochStart), this);
				}
			}
			else
			{
				AddTicker(item2);
			}
		}
		if (aManUpdates == null)
		{
			Debug.LogWarning("null aManUpdates found on " + strName + ". Skipping.");
			return;
		}
		foreach (IManUpdater aManUpdate in aManUpdates)
		{
			aManUpdate.CatchUp();
		}
	}

	public int GetAnimState()
	{
		if (anim != null)
		{
			return anim.GetInteger(nAnimStateID);
		}
		return -1;
	}

	private void SetAnimState(int nState)
	{
		if (!(anim == null))
		{
			if (nState == 1)
			{
				nState = Interaction.dictAnims[strWalkAnim];
				float a = (float)(1.0 - GetCondAmount("StatMovSpeedPenalty"));
				a = Mathf.Max(a, 0.05f);
				anim.speed = a;
			}
			else
			{
				anim.speed = 1f;
			}
			if (base.gameObject.activeInHierarchy)
			{
				anim.SetInteger(nAnimStateID, nState);
			}
		}
	}

	public void SetAnimTrigger(string strTrigger)
	{
		if (anim != null)
		{
			anim.SetTrigger(strTrigger);
		}
	}

	public void LogMove(string originRegId, string destinationRegId, MoveReason moveReason, string optionalData = null)
	{
		string text = "";
		switch (moveReason)
		{
		case MoveReason.DOCKED:
			text = ((optionalData != null) ? (optionalData + DataHandler.GetString("CREW_LOG_HAULED") + strNameFriendly + DataHandler.GetString("CREW_LOG_TO") + destinationRegId + DataHandler.GetString("CREW_LOG_ABOARD") + originRegId) : (strNameFriendly + DataHandler.GetString("CREW_LOG_DOCKED") + destinationRegId + DataHandler.GetString("CREW_LOG_ABOARD") + originRegId));
			break;
		case MoveReason.ADDCREW:
			text = strNameFriendly + DataHandler.GetString("CREW_LOG_TRANSFER") + originRegId + DataHandler.GetString("CREW_LOG_TO") + destinationRegId;
			break;
		case MoveReason.ADDNEWCREW:
			text = strNameFriendly + DataHandler.GetString("CREW_LOG_REPORTSFORDUTY") + destinationRegId;
			break;
		case MoveReason.REGIONCLEANUP:
			text = strNameFriendly + DataHandler.GetString("CREW_LOG_ASSIGNMENT") + originRegId + DataHandler.GetString("CREW_LOG_RETURNSTO") + destinationRegId;
			break;
		case MoveReason.PASS:
			text = strNameFriendly + DataHandler.GetString("CREW_LOG_LEAVES") + originRegId + DataHandler.GetString("CREW_LOG_PASSENGER") + destinationRegId;
			if (optionalData != null)
			{
				text = text + DataHandler.GetString("CREW_LOG_BOUNDFOR") + optionalData;
			}
			break;
		default:
			Debug.LogWarning("No matching statement for move reason " + moveReason);
			break;
		}
		LogMessage(text, "Neutral", strName);
	}

	public void LogMessage(string strMsg, string strColor, string strOwner, string strShort = null)
	{
		if (strMsg == null || strColor == null || CrewSim.objInstance == null)
		{
			return;
		}
		bool flag = false;
		if (aMessages.Count == 0)
		{
			flag = true;
		}
		else if (aMessages[aMessages.Count - 1].strMessage == strMsg)
		{
			aMessages[aMessages.Count - 1].nCount++;
		}
		else
		{
			flag = true;
		}
		if (flag)
		{
			JsonLogMessage jsonLogMessage = new JsonLogMessage();
			jsonLogMessage.strName = Guid.NewGuid().ToString();
			jsonLogMessage.strMessage = strMsg;
			jsonLogMessage.strMessageShort = strShort;
			jsonLogMessage.strColor = strColor;
			jsonLogMessage.strOwner = strOwner;
			jsonLogMessage.fTime = StarSystem.fEpoch;
			jsonLogMessage.nCount = 1;
			aMessages.Add(jsonLogMessage);
			if (aMessages.Count > 50)
			{
				aMessages.RemoveRange(0, aMessages.Count - 50);
			}
		}
		if (CrewSim.objInstance.FinishedLoading && (GUISocialCombat2.coUs == this || GUISocialCombat2.coThem == this))
		{
			GUISocialCombat2.objInstance.UpdateCO(this);
		}
		CrewSim.objInstance.UpdateLog(this, strColor);
	}

	public string GetDebugQueue()
	{
		string text = "None\n";
		if (aQueue.Count > 0)
		{
			text = "";
			foreach (Interaction item in aQueue)
			{
				if (item == null || item.objThem == null)
				{
					text += "null\n";
					continue;
				}
				text = text + item.strName + "->" + item.objThem.strName + ": " + item.fDuration * 60.0 * 60.0;
				text += "\n";
			}
		}
		return text;
	}

	public string GetDebugPriorities()
	{
		double num = 0.0;
		string result = "None\n";
		if (aPriorities.Count > 0)
		{
			result = "";
			foreach (Priority aPriority in aPriorities)
			{
				if (aPriority == null || aPriority.objCond == null)
				{
					result += "null\n";
					continue;
				}
				result = result + aPriority.objCond.strName + ": " + Mathf.RoundToInt(Convert.ToSingle(aPriority.fValue.ToString("#.00")));
				result += "\n";
				num += aPriority.fValue;
			}
			result = "Total: " + num.ToString("#.00") + "\n" + result;
		}
		return result;
	}

	public string GetDebugTickers()
	{
		string text = "";
		foreach (JsonTicker aTicker in aTickers)
		{
			text = ((aTicker != null) ? (text + aTicker.ToString() + "\n") : (text + "null\n"));
		}
		return text;
	}

	public string GetDebugConds(string strPrefix)
	{
		List<string> list = mapConds.Keys.ToList();
		list.Sort();
		StringBuilder stringBuilder = new StringBuilder();
		foreach (string item in list)
		{
			Condition condition = mapConds[item];
			if (string.IsNullOrEmpty(strPrefix) || condition.strName.IndexOf(strPrefix) == 0)
			{
				stringBuilder.Append(condition.strName);
				stringBuilder.Append(": ");
				stringBuilder.AppendLine(condition.fCount.ToString());
			}
		}
		return stringBuilder.ToString();
	}

	public void VisitCOsEarlyOut(CondOwnerVisitor visitor, bool bAllowLocked)
	{
		if (bDestroyed)
		{
			Debug.Log("ERROR: Accessing destroyed object " + strName + " - " + strID);
			return;
		}
		if (aStack == null)
		{
			Debug.Log("ERROR: Accessing null stack on object " + strName + " - " + strID);
			return;
		}
		foreach (CondOwner item in aStack)
		{
			if (!item.bDestroyed)
			{
				visitor.Visit(item);
				item.VisitCOsEarlyOut(visitor, bAllowLocked);
			}
		}
		foreach (Slot slot in GetSlots(bDeep: false))
		{
			slot?.VisitCOs(visitor, bAllowLocked);
		}
		if (objContainer != null)
		{
			objContainer.VisitCOs(visitor, bAllowLocked);
		}
	}

	public void VisitCOs(CondOwnerVisitor visitor, bool bAllowLocked)
	{
		if (bDestroyed)
		{
			Debug.Log("ERROR: Accessing destroyed object " + strName + " - " + strID);
		}
		else
		{
			if (visitor is CondOwnerVisitorEarlyOut && ((CondOwnerVisitorEarlyOut)visitor).CO != null)
			{
				return;
			}
			if (aStack == null)
			{
				Debug.Log("ERROR: Accessing null stack on object " + strName + " - " + strID);
				return;
			}
			foreach (CondOwner item in aStack)
			{
				if (!item.bDestroyed)
				{
					visitor.Visit(item);
					item.VisitCOs(visitor, bAllowLocked);
				}
			}
			foreach (Slot slot in GetSlots(bDeep: false))
			{
				slot?.VisitCOs(visitor, bAllowLocked);
			}
			if (objContainer != null)
			{
				objContainer.VisitCOs(visitor, bAllowLocked);
			}
		}
	}

	public List<CondOwner> GetCOsEarlyOut(bool bAllowLocked, CondTrigger objCondTrig = null)
	{
		if (!HasSubCOs)
		{
			return null;
		}
		temp_vHash1.CO = null;
		temp_vWrap = CondOwnerVisitorEarlyOut.WrapVisitor(temp_vHash1, objCondTrig);
		VisitCOs(temp_vWrap, bAllowLocked);
		return new List<CondOwner> { temp_vHash1.CO };
	}

	public List<CondOwner> GetCOs(bool bAllowLocked, CondTrigger objCondTrig = null)
	{
		if (!HasSubCOs)
		{
			return null;
		}
		temp_vHash.aHashSet.Clear();
		temp_vWrap = CondOwnerVisitorCondTrigger.WrapVisitor(temp_vHash, objCondTrig);
		VisitCOs(temp_vWrap, bAllowLocked);
		return new List<CondOwner>(temp_vHash.aHashSet);
	}

	public List<CondOwner> GetCOsSafe(bool bAllowLocked, CondTrigger objCondTrig = null)
	{
		List<CondOwner> cOs = GetCOs(bAllowLocked, objCondTrig);
		if (cOs == null)
		{
			return new List<CondOwner>();
		}
		return cOs;
	}

	public static void NullSafeAddRange(ref List<CondOwner> aCOs, List<CondOwner> aAdds)
	{
		if (aAdds != null && aAdds.Count != 0)
		{
			aCOs.AddRange(aAdds);
		}
	}

	[Obsolete("GetICOs is deprecated, please use GetCOs instead.")]
	public List<CondOwner> GetICOs(bool bAllowLocked, CondTrigger ct = null)
	{
		return GetCOs(bAllowLocked, ct);
	}

	public bool IsInsideContainer()
	{
		if (slotNow != null)
		{
			return false;
		}
		if ((bool)coStackHead)
		{
			return coStackHead.IsInsideContainer();
		}
		return objCOParent != null;
	}

	public void UpdatePriority(Condition objCond)
	{
		double num = GetPrefs(objCond.strName) - objCond.fCount;
		for (int i = 0; i < aPriorities.Count; i++)
		{
			if (aPriorities[i].objCond.strName == objCond.strName)
			{
				aPriorities[i].objCond = null;
				aPriorities.RemoveAt(i);
				break;
			}
		}
		if (num >= 0.0)
		{
			return;
		}
		if (aPriorities.Count == 0)
		{
			aPriorities.Add(new Priority(num, objCond));
			return;
		}
		bool flag = false;
		for (int j = 0; j < aPriorities.Count; j++)
		{
			if (aPriorities[j].fValue >= num)
			{
				aPriorities.Insert(j, new Priority(num, objCond));
				flag = true;
				break;
			}
		}
		if (!flag)
		{
			aPriorities.Add(new Priority(num, objCond));
		}
	}

	public double GetPrefs(string strName)
	{
		double num = 0.0;
		double num2 = 0.0;
		bool flag = false;
		if (mapCondRules.TryGetValue(strName, out var value))
		{
			flag = value.fPref < double.PositiveInfinity;
			num = value.Preference;
		}
		if (mapConds.TryGetValue(strName, out var value2))
		{
			num2 = value2.fCount;
		}
		if (!flag || num2 <= num)
		{
			return num2;
		}
		if (num2 > num)
		{
			return num;
		}
		return 0.0;
	}

	public bool CanSee(CondOwner coTarget)
	{
		if (coTarget == null)
		{
			return false;
		}
		return true;
	}

	public Vector2 GetPos(string strPointName = null, bool bIgnoreParent = false)
	{
		if (!bIgnoreParent && objCOParent != null)
		{
			return objCOParent.GetPos(strPointName);
		}
		if (strPointName == "room")
		{
			Room roomAtWorldCoords = ship.GetRoomAtWorldCoords1(tf.position, bAllowDocked: false);
			if (roomAtWorldCoords != null)
			{
				return roomAtWorldCoords.GetRandomWalkableTile().tf.position;
			}
			return tf.position;
		}
		if (strPointName != null && mapPoints.TryGetValue(strPointName, out var value))
		{
			Vector3 right = tf.right;
			float num = right.x / 16f;
			float num2 = right.y / 16f;
			float num3 = tf.position.x + num * value.x - num2 * value.y;
			float num4 = tf.position.y + num2 * value.x + num * value.y;
			if (float.IsNaN(num3))
			{
				num3 = tf.position.x;
			}
			if (float.IsNaN(num4))
			{
				num4 = tf.position.y;
			}
			return new Vector2(num3, num4);
		}
		return tf.position;
	}

	public JsonCondOwnerSave GetJSONSave()
	{
		if (this == null)
		{
			if ((object)this == null)
			{
				Debug.Log("ERROR: Saving a null");
			}
			else
			{
				Debug.Log("ERROR: Saving a null " + strName + " - " + strID);
			}
			Debug.Break();
			return null;
		}
		JsonCondOwnerSave jsonCondOwnerSave = new JsonCondOwnerSave();
		jsonCondOwnerSave.strID = strID;
		jsonCondOwnerSave.strCODef = strCODef;
		jsonCondOwnerSave.bAlive = bAlive;
		if (ship != null)
		{
			jsonCondOwnerSave.strRegIDLast = ship.strRegID;
		}
		jsonCondOwnerSave.strFriendlyName = FriendlyName;
		if (Item != null)
		{
			jsonCondOwnerSave.strIMGPreview = Item.ImgOverride;
		}
		if (Company != null)
		{
			jsonCondOwnerSave.strComp = Company.strName;
			ShiftChange(JsonCompany.NullShift, bSilent: true);
		}
		List<string> list = new List<string>();
		JsonCondOwner condOwnerDef = DataHandler.GetCondOwnerDef(strCODef);
		List<string> list2 = new List<string>();
		if (condOwnerDef != null && condOwnerDef.aStartingConds != null)
		{
			list2.AddRange(condOwnerDef.aStartingConds);
		}
		int num = 0;
		string text = "";
		foreach (string key in mapConds.Keys)
		{
			if (!(key == objCondID.strName))
			{
				text = key + "=1.0x" + mapConds[key].fCount;
				list.Add(text);
				if (list2.Contains(text) || list2.Contains(text + ".0") || list2.Contains(text + ".00"))
				{
					num++;
				}
			}
		}
		if (num > 1 && num == list2.Count)
		{
			foreach (string item in list2)
			{
				if (!list.Remove(item) && !list.Remove(item + ".0"))
				{
					list.Remove(item + ".00");
				}
			}
			list.Add("DEFAULT");
			list.TrimExcess();
		}
		jsonCondOwnerSave.aConds = list.ToArray();
		list.Clear();
		List<string> list3 = new List<string>();
		if (condOwnerDef != null && condOwnerDef.aStartingCondRules != null)
		{
			list3.AddRange(condOwnerDef.aStartingCondRules);
		}
		num = 0;
		foreach (string key2 in mapCondRules.Keys)
		{
			string saveInfo = mapCondRules[key2].GetSaveInfo();
			list.Add(saveInfo);
			if (list3.Contains(saveInfo))
			{
				num++;
			}
		}
		if (num > 1 && num == list3.Count)
		{
			foreach (string item2 in list3)
			{
				list.Remove(item2);
			}
			list.Add("DEFAULT");
			list.TrimExcess();
		}
		jsonCondOwnerSave.aCondRules = list.ToArray();
		list.Clear();
		List<ReplyThread> list4 = new List<ReplyThread>();
		foreach (ReplyThread aReply in aReplies)
		{
			if (aReply != null)
			{
				list4.Add(aReply.Clone());
			}
		}
		jsonCondOwnerSave.aReplies = list4.ToArray();
		list4.Clear();
		jsonCondOwnerSave.strPersistentCT = strPersistentCT;
		jsonCondOwnerSave.strPersistentCO = strPersistentCO;
		jsonCondOwnerSave.strSourceCO = strSourceCO;
		jsonCondOwnerSave.strSourceInteract = strSourceInteract;
		jsonCondOwnerSave.strCondID = objCondID.strName;
		jsonCondOwnerSave.strIdleAnim = strIdleAnim;
		jsonCondOwnerSave.strLastSocial = strLastSocial;
		if (slotNow != null)
		{
			jsonCondOwnerSave.strSlotName = slotNow.strName;
		}
		if (bSaveMessageLog)
		{
			List<JsonLogMessage> list5 = new List<JsonLogMessage>();
			foreach (JsonLogMessage aMessage in aMessages)
			{
				list5.Add(aMessage.Clone());
			}
			jsonCondOwnerSave.aMessages2 = list5.ToArray();
			list.Clear();
		}
		jsonCondOwnerSave.aCondZeroes = aCondZeroes.ToArray();
		GasContainer gasContainer = GasContainer;
		if (gasContainer != null)
		{
			jsonCondOwnerSave.fDGasTemp = gasContainer.fDGasTemp;
			if (double.IsNaN(jsonCondOwnerSave.fDGasTemp))
			{
				jsonCondOwnerSave.fDGasTemp = 0.001;
			}
			if (gasContainer.mapDGasMols == null)
			{
				Debug.LogWarning("ERROR: null gascontainer dict on " + strName + ". Setting to empty for now.");
				gasContainer.mapDGasMols = new Dictionary<string, double>();
			}
			foreach (string key3 in gasContainer.mapDGasMols.Keys)
			{
				list.Add(key3 + "," + gasContainer.mapDGasMols[key3]);
			}
		}
		jsonCondOwnerSave.mapDGasMols = list.ToArray();
		list.Clear();
		jsonCondOwnerSave.fLastICOUpdate = fLastICOUpdate;
		jsonCondOwnerSave.fMSRedamageAmount = fMSRedamageAmount;
		List<JsonInteractionSave> list6 = new List<JsonInteractionSave>();
		foreach (Interaction item3 in aQueue)
		{
			JsonInteractionSave jSONSave = item3.GetJSONSave();
			if (jSONSave != null)
			{
				list6.Add(jSONSave);
			}
		}
		jsonCondOwnerSave.aQueue = list6.ToArray();
		list6.Clear();
		jsonCondOwnerSave.dictRecentlyTried = new Dictionary<string, double>(dictRecentlyTried);
		jsonCondOwnerSave.dictRememberScores = new Dictionary<string, double>(dictRememberScores);
		jsonCondOwnerSave.aRememberIAs = aRememberIAs.ToArray();
		if (mapIAHist != null)
		{
			List<JsonCondHistory> list7 = new List<JsonCondHistory>();
			foreach (KeyValuePair<string, CondHistory> item4 in mapIAHist)
			{
				list7.Add(item4.Value.GetJson());
			}
			jsonCondOwnerSave.mapIAHist2 = list7.ToArray();
		}
		if (Pathfinder != null)
		{
			if (Pathfinder.tilDest != null)
			{
				jsonCondOwnerSave.nDestTile = Pathfinder.tilDest.Index;
				jsonCondOwnerSave.strDestShip = Pathfinder.tilDest.coProps.ship.strRegID;
				if (Pathfinder.coDest != null)
				{
					jsonCondOwnerSave.strDestCO = Pathfinder.coDest.strID;
				}
			}
			else
			{
				jsonCondOwnerSave.nDestTile = -1;
				jsonCondOwnerSave.strDestShip = null;
				jsonCondOwnerSave.strDestCO = null;
			}
		}
		Crew component = base.gameObject.GetComponent<Crew>();
		if (component != null)
		{
			jsonCondOwnerSave.aFaceParts = component.FaceParts.Clone() as string[];
			jsonCondOwnerSave.strBodyType = component.BodyType;
		}
		if (socUs != null)
		{
			jsonCondOwnerSave.social = socUs.GetJSON();
		}
		GUIChargenStack component2 = GetComponent<GUIChargenStack>();
		if (component2 != null)
		{
			jsonCondOwnerSave.cgs = component2.GetJSON();
		}
		jsonCondOwnerSave.inventoryX = pairInventoryXY.x;
		jsonCondOwnerSave.inventoryY = pairInventoryXY.y;
		if (aTickers.Count > 0)
		{
			jsonCondOwnerSave.aTickers = new JsonTicker[aTickers.Count];
			for (int i = 0; i < aTickers.Count; i++)
			{
				jsonCondOwnerSave.aTickers[i] = aTickers[i].Clone();
			}
		}
		List<JsonPledgeSave> list8 = new List<JsonPledgeSave>();
		foreach (List<Pledge2> value in dictPledges.Values)
		{
			foreach (Pledge2 item5 in value)
			{
				list8.Add(item5.GetJSON());
			}
		}
		jsonCondOwnerSave.aPledges = list8.ToArray();
		if (aStack.Count > 0)
		{
			jsonCondOwnerSave.aStack = new string[aStack.Count];
			for (int j = 0; j < aStack.Count; j++)
			{
				jsonCondOwnerSave.aStack[j] = aStack[j].strID;
			}
		}
		if (aLot.Count > 0)
		{
			jsonCondOwnerSave.aLot = new string[aLot.Count];
			for (int k = 0; k < aLot.Count; k++)
			{
				jsonCondOwnerSave.aLot[k] = aLot[k].strID;
			}
		}
		if (aMyShips.Count > 0)
		{
			jsonCondOwnerSave.aMyShips = new string[aMyShips.Count];
			int num2 = 0;
			foreach (string aMyShip in aMyShips)
			{
				jsonCondOwnerSave.aMyShips[num2] = aMyShip;
				num2++;
			}
		}
		if (aFactions.Count > 0)
		{
			jsonCondOwnerSave.aFactions = new string[aFactions.Count];
			for (int l = 0; l < aFactions.Count; l++)
			{
				jsonCondOwnerSave.aFactions[l] = aFactions[l];
			}
		}
		if (aAttackIAs.Count > 0)
		{
			jsonCondOwnerSave.aAttackIAs = aAttackIAs.ToArray();
		}
		if (Company != null)
		{
			ShiftChange(Company.GetShift(StarSystem.nUTCHour, this), bSilent: true);
		}
		return jsonCondOwnerSave;
	}

	public void UpdateGravity()
	{
		if (!bFreezeConds && IsHumanOrRobot)
		{
			bool flag = bLogConds;
			bLogConds = false;
			if (objCOParent == this)
			{
				Debug.Log("ERROR: CO is own objCOParent: " + strCODef);
			}
			else if (objCOParent != null)
			{
				objCOParent.UpdateGravity();
			}
			double num = 0.3;
			if (ship != null)
			{
				num = ship.Gravity;
			}
			AddCondAmount("StatEncumbrance", GetCondAmount("StatMass") * num - GetCondAmount("StatEncumbrance"));
			bLogConds = flag;
		}
	}

	public void AddMass(double fMass, bool bSilent = false)
	{
		if (bFreezeConds)
		{
			return;
		}
		bool flag = bLogConds;
		bLogConds = !bSilent;
		AddCondAmount("StatMass", fMass);
		if (objCOParent == this)
		{
			Debug.Log("ERROR: CO is own objCOParent: " + strCODef);
		}
		else if (objCOParent != null)
		{
			objCOParent.AddMass(fMass);
		}
		if (GetCondAmount("IsHuman") > 0.0)
		{
			double num = 0.3;
			if (ship != null)
			{
				num = ship.Gravity;
			}
			AddCondAmount("StatEncumbrance", GetCondAmount("StatMass") * num - GetCondAmount("StatEncumbrance"));
		}
		mapInfo["StatMass"] = GetCondAmount("StatMass").ToString("#.00") + "kg";
		bLogConds = flag;
	}

	public double GetTotalPrice(CondTrigger ct, bool bIncludeStack, string targetMarket = null)
	{
		double num = GetBasePrice(targetMarket);
		List<CondOwner> cOs = GetCOs(bAllowLocked: true, ct);
		if (cOs == null)
		{
			return num;
		}
		foreach (CondOwner item in cOs)
		{
			num += item.GetTotalPrice(ct, bIncludeStack: false, targetMarket);
		}
		if (!bIncludeStack)
		{
			foreach (CondOwner item2 in aStack)
			{
				num -= item2.GetTotalPrice(ct, bIncludeStack: true, targetMarket);
			}
		}
		return num;
	}

	public double GetBasePrice(string targetMarket = null)
	{
		double num = GetCondAmount("StatBasePrice");
		if (num == 0.0)
		{
			num = Convert.ToSingle(GetCondAmount("StatMass"));
		}
		if (HasCond("IsPristine"))
		{
			num *= 1.25;
		}
		if (HasCond("StatDamageMax"))
		{
			double damageState = GetDamageState();
			num = ((damageState > aDamageThresholds[0]) ? num : ((damageState > aDamageThresholds[1]) ? (num * 0.75) : ((!(damageState > aDamageThresholds[2])) ? (num * 0.25) : (num * 0.5))));
		}
		if (HasCond("StatGasPressure"))
		{
			GasContainer component = GetComponent<GasContainer>();
			if (component != null)
			{
				float totalGasValue = component.GetTotalGasValue();
				num += (double)totalGasValue;
			}
		}
		if (mapConds.TryGetValue("StatLiqD2O", out var value) && value != null)
		{
			num += (double)GasContainer.GetGasPrice("H2") * value.fCount;
		}
		if (mapConds.TryGetValue("StatSolidHe3", out value) && value != null)
		{
			num += (double)GasContainer.GetGasPrice("He3") * value.fCount;
		}
		if (targetMarket != null)
		{
			double supplyDemandModifier = MarketManager.GetSupplyDemandModifier(this, targetMarket);
			num *= supplyDemandModifier;
		}
		return num;
	}

	public double GetDamageState()
	{
		double condAmount = GetCondAmount("StatDamageMax");
		if (condAmount > 0.0)
		{
			return 1.0 - GetCondAmount("StatDamage") / condAmount;
		}
		return 1.0;
	}

	public string GetDamageDescriptor()
	{
		if (!HasCond("StatDamageMax") || HasCond("IsFood") || HasCond("IsLiquid"))
		{
			return "";
		}
		double damageState = GetDamageState();
		if (HasCond("IsPristine"))
		{
			return DataHandler.GetString("TRADE_PRISTINE");
		}
		if (!HasCond("IsDamaged"))
		{
			string text = DataHandler.GetString("TRADE_REFURBISHED");
			if (damageState > aDamageThresholds[0])
			{
				return text + DataHandler.GetString("DAMAGE_DESC_0");
			}
			if (damageState > aDamageThresholds[1])
			{
				return text + DataHandler.GetString("DAMAGE_DESC_1");
			}
			if (damageState > aDamageThresholds[2])
			{
				return text + DataHandler.GetString("DAMAGE_DESC_2");
			}
			return text + DataHandler.GetString("DAMAGE_DESC_3");
		}
		return "";
	}

	public bool GetIsLikeNew()
	{
		if (!HasCond("StatDamageMax"))
		{
			return true;
		}
		if (GetDamageState() > aDamageThresholds[0])
		{
			return true;
		}
		return false;
	}

	public void ClaimShip(string strRegID)
	{
		if (strRegID == null)
		{
			return;
		}
		if (HasCond("IsPlayer"))
		{
			Ship shipByRegID = CrewSim.system.GetShipByRegID(strRegID);
			if (shipByRegID == null || shipByRegID.IsStation() || shipByRegID.IsStationHidden())
			{
				return;
			}
		}
		if (!aMyShips.Contains(strRegID))
		{
			aMyShips.Add(strRegID);
		}
		if (Company == null || !(socUs != null))
		{
			return;
		}
		JsonPersonSpec personSpec = DataHandler.GetPersonSpec("RELCrewSubordinate");
		foreach (string item in socUs.GetMatchingRelationsAll(personSpec))
		{
			if (!(item == strID))
			{
				CondOwner value = null;
				if (DataHandler.mapCOs.TryGetValue(item, out value))
				{
					value.ClaimShip(strRegID);
				}
			}
		}
	}

	public void UnclaimShip(string strRegID)
	{
		if (strRegID != null && aMyShips.Contains(strRegID))
		{
			aMyShips.Remove(strRegID);
		}
	}

	public bool OwnsShip(string strRegID)
	{
		if (strRegID == null)
		{
			return false;
		}
		return aMyShips.Contains(strRegID);
	}

	public HashSet<string> GetShipsOwned()
	{
		return aMyShips;
	}

	public void SetShipsOwned(HashSet<string> aOwned)
	{
		if (aOwned == null)
		{
			return;
		}
		aMyShips.Clear();
		foreach (string item in aOwned)
		{
			aMyShips.Add(item);
		}
		string text = "";
		foreach (string aMyShip in aMyShips)
		{
			text = text + aMyShip + ", ";
		}
		Debug.Log(strID + " restting ships. Now claims ship(s) " + text);
	}

	public void AddFaction(JsonFaction jf, string strIDOverride = null)
	{
		if (jf == null || aFactions.IndexOf(jf.strName) >= 0)
		{
			return;
		}
		aFactions.Add(jf.strName);
		if (socUs != null)
		{
			if (string.IsNullOrEmpty(strIDOverride))
			{
				strIDOverride = strID;
			}
			if (jf.aMembers.IndexOf(strIDOverride) < 0)
			{
				jf.aMembers.Add(strIDOverride);
			}
			JsonCompany company = CrewSim.system.GetCompany(jf.strCompany);
			if (company != null)
			{
				company.AddNewMember(strIDOverride);
				Company = company;
			}
		}
	}

	public void RemoveFaction(JsonFaction jf)
	{
		if (jf != null)
		{
			aFactions.Remove(jf.strName);
			if (socUs != null)
			{
				jf.aMembers.Remove(strID);
			}
		}
	}

	public void RemoveFaction(string strFaction)
	{
		if (string.IsNullOrEmpty(strFaction))
		{
			return;
		}
		aFactions.Remove(strFaction);
		if (!(socUs == null))
		{
			JsonFaction faction = CrewSim.system.GetFaction(strFaction);
			if (faction != null && faction.aMembers != null)
			{
				faction.aMembers.Remove(strID);
			}
		}
	}

	public bool HasFaction(string strFaction)
	{
		if (string.IsNullOrEmpty(strFaction))
		{
			return false;
		}
		return aFactions.IndexOf(strFaction) >= 0;
	}

	public void ApplyFactionReps(CondOwner coDoing, float fChange, bool bPrimary = false, bool bFactionIgnoreThemPop = false)
	{
		if (coDoing == null || coDoing == this || fChange == 0f)
		{
			return;
		}
		bool flag = coDoing == CrewSim.GetSelectedCrew();
		List<string> allFactions = coDoing.GetAllFactions();
		if (allFactions.Count == 0)
		{
			return;
		}
		if (!HasCond("IsSocial"))
		{
			if (ship == null)
			{
				return;
			}
			bool flag2 = false;
			foreach (CondOwner person in ship.GetPeople(bAllowDocked: true))
			{
				if (!(person == coDoing) && person.bAlive && !person.HasCond("Unconscious") && Visibility.IsCondOwnerLOSVisibleFromCo(coDoing, person) && person.SharesFactionsWith(this) && (!(fChange < 0f) || person.pspec == null || person.pspec.IsCOMyMother(JPSRelReportFactionNeg, coDoing)))
				{
					flag2 = true;
					break;
				}
			}
			if (!flag2)
			{
				return;
			}
		}
		foreach (string item in allFactions)
		{
			JsonFaction faction = CrewSim.system.GetFaction(item);
			if (faction == null)
			{
				continue;
			}
			foreach (string aFaction in aFactions)
			{
				JsonFaction faction2 = CrewSim.system.GetFaction(aFaction);
				if (faction2 != null)
				{
					float num = fChange;
					if (faction.aMembers.Count > 1)
					{
						num = fChange / (float)faction.aMembers.Count;
					}
					if (!bFactionIgnoreThemPop && faction2.aMembers.Count > 1)
					{
						num /= (float)faction2.aMembers.Count;
					}
					if (flag)
					{
						CrewSim.GetSelectedCrew().LogMessage(aFaction + " changed their view of " + item + " by " + num.ToString("F2"), "Neutral", strID, "Fctn:" + aFaction + " " + num.ToString("F2"));
					}
					faction2.ApplyFactionRep(faction.strName, num, bPrimary);
				}
			}
		}
	}

	public float GetFactionScore(string strFaction)
	{
		if (string.IsNullOrEmpty(strFaction))
		{
			return 0f;
		}
		float num = 0f;
		if (aFactions == null)
		{
			return num;
		}
		foreach (string aFaction in aFactions)
		{
			JsonFaction faction = CrewSim.system.GetFaction(aFaction);
			if (faction != null)
			{
				num += faction.GetFactionScore(strFaction);
			}
		}
		return num;
	}

	public float GetFactionScore(List<string> aFactionsThem)
	{
		if (aFactionsThem == null)
		{
			return 0f;
		}
		float num = 0f;
		foreach (string item in aFactionsThem)
		{
			num += GetFactionScore(item);
		}
		return num;
	}

	public List<string> GetAllFactions()
	{
		if (aFactions == null)
		{
			return new List<string>();
		}
		return new List<string>(aFactions);
	}

	public bool SharesFactionsWith(CondOwner coThem)
	{
		if (coThem == null)
		{
			return false;
		}
		foreach (string aFaction in aFactions)
		{
			if (coThem.HasFaction(aFaction))
			{
				return true;
			}
		}
		return false;
	}

	public bool SharesFactionsWith(List<JsonFaction> aFactionsThem)
	{
		if (aFactionsThem == null || aFactionsThem.Count == 0)
		{
			return false;
		}
		foreach (JsonFaction item in aFactionsThem)
		{
			if (aFactions.Contains(item.strName))
			{
				return true;
			}
		}
		return false;
	}

	public void SetFactions(List<JsonFaction> aJFs, bool bRemoveOld)
	{
		if (bRemoveOld)
		{
			aFactions.Clear();
		}
		if (aJFs == null)
		{
			return;
		}
		foreach (JsonFaction aJF in aJFs)
		{
			AddFaction(aJF);
		}
	}

	public void SetCrewZOffset()
	{
		Vector3 position = tf.position;
		position.z = 0f;
		tf.position = position;
	}

	public string GetMessageLog(int nTail = -1)
	{
		if (nTail < 1)
		{
			nTail = aMessages.Count;
		}
		int num = aMessages.Count - nTail;
		if (num < 0)
		{
			num = 0;
		}
		int count = aMessages.Count;
		if (messageLogSB == null)
		{
			messageLogSB = new StringBuilder(5000);
		}
		else
		{
			messageLogSB.Length = 0;
		}
		for (int i = num; i < count; i++)
		{
			messageLogSB.Append("<color=#");
			messageLogSB.Append(DataHandler.GetColorHTML(aMessages[i].strColor));
			messageLogSB.Append(">");
			bool num2 = aMessages[i].strOwner != strName;
			if (num2)
			{
				messageLogSB.Append("<align=\"right\"><alpha=#80>");
			}
			if (string.IsNullOrEmpty(aMessages[i].strMessageShort))
			{
				messageLogSB.Append(aMessages[i].strMessage);
			}
			else
			{
				messageLogSB.Append(LinkOpener.GetGenericLink(aMessages[i].strName, aMessages[i].strMessageShort));
			}
			if (aMessages[i].nCount > 1)
			{
				messageLogSB.Append("(x");
				messageLogSB.Append(aMessages[i].nCount);
				messageLogSB.Append(")");
			}
			if (num2)
			{
				messageLogSB.Append("<alpha=#FF></align>");
			}
			messageLogSB.Append("</color>");
			if (i + 1 == count || (i + 1 < count && string.IsNullOrEmpty(aMessages[i + 1].strMessageShort)) || aMessages[i].strOwner != aMessages[i + 1].strOwner)
			{
				messageLogSB.AppendLine();
			}
			else
			{
				messageLogSB.Append(" ");
			}
		}
		return messageLogSB.ToString();
	}

	public List<string> GetJobActions(string strJobType)
	{
		List<string> list = null;
		JsonCondOwner value = null;
		if (DataHandler.dictCOs.TryGetValue(strCODef, out value))
		{
			return value.GetJobActions(strJobType.ToLower());
		}
		if (GetComponent<COOverlay>() != null)
		{
			return GetComponent<COOverlay>().GetJobActions(strJobType);
		}
		return new List<string>();
	}

	public bool HasQueuedInteraction(string strName)
	{
		if (aQueue == null)
		{
			return false;
		}
		foreach (Interaction item in aQueue)
		{
			if (item.strName == strName)
			{
				return true;
			}
		}
		return false;
	}

	public void DebugInv(StringBuilder sb, string strPrefix)
	{
		if (aStack == null)
		{
			return;
		}
		if (aStack.Count > 0)
		{
			sb.AppendLine(strPrefix + strID + " stack contains:");
		}
		foreach (CondOwner item in aStack)
		{
			sb.AppendLine(strPrefix + strID + "->" + item.strID + ".bDestroyed = " + item.bDestroyed);
			foreach (CondOwner item2 in item.aStack)
			{
				item2.DebugInv(sb, strPrefix + strID + "->");
			}
		}
	}

	public Wound GetWoundLocation(bool bBlunt, bool bCut, string strCTTargetWound)
	{
		if (!HasCond("StatWoundFraction"))
		{
			return null;
		}
		CondTrigger condTrigger = DataHandler.GetCondTrigger(strCTTargetWound);
		if (condTrigger.IsBlank())
		{
			condTrigger = Wound.CTWound;
		}
		List<CondOwner> cOs = GetCOs(bAllowLocked: true, condTrigger);
		if (cOs == null)
		{
			return null;
		}
		List<Wound> list = new List<Wound>();
		float num = 0f;
		foreach (CondOwner item in cOs)
		{
			if (!(item == null))
			{
				Wound component = item.GetComponent<Wound>();
				if (!(component == null) && (!bBlunt || component.Bluntable) && (!bCut || component.Cuttable))
				{
					list.Add(component);
					num += component.fHitChance;
				}
			}
		}
		if (list.Count == 0)
		{
			return null;
		}
		float num2 = MathUtils.Rand(0f, num, MathUtils.RandType.Flat);
		num = 0f;
		foreach (Wound item2 in list)
		{
			num += item2.fHitChance;
			if (num2 <= num)
			{
				return item2;
			}
		}
		return null;
	}

	public List<Wound> GetAllWounds()
	{
		List<Wound> list = new List<Wound>();
		List<CondOwner> cOs = GetCOs(bAllowLocked: true, Wound.CTWound);
		if (cOs == null)
		{
			return list;
		}
		foreach (CondOwner item in cOs)
		{
			if (!(item == null))
			{
				Wound component = item.GetComponent<Wound>();
				if (!(component == null))
				{
					list.Add(component);
				}
			}
		}
		return list;
	}

	public void ResetActiveWoundsToDefault()
	{
		List<Wound> allWounds = GetAllWounds();
		if (allWounds == null || allWounds.Count == 0)
		{
			return;
		}
		bool flag = false;
		foreach (Wound item in allWounds)
		{
			if (!(item == null) && item.IsActive())
			{
				item.ResetToDefault();
				flag = true;
			}
		}
		if (flag)
		{
			ZeroCondAmount("StatBlood");
			ZeroCondAmount("StatPain");
			ZeroCondAmount("StatInfection");
		}
	}

	private void KO()
	{
		if (bAlive && !HasCond("Unconscious"))
		{
			Debug.Log("NPC KOed " + FriendlyName + " on " + ship.ToString());
			AICancelAll();
			AddCondAmount("Unconscious", 1.0);
			SetAnimState(Interaction.dictAnims["Dead"]);
			strIdleAnim = "Dead";
			if (Pathfinder != null)
			{
				Pathfinder.Reset();
			}
			if (compSlots != null && ship != null && ship.LoadState > Ship.Loaded.Shallow)
			{
				List<CondOwner> cOs = compSlots.GetCOs("heldL");
				cOs.AddRange(compSlots.GetCOs("heldR"));
				cOs.AddRange(compSlots.GetCOs("drag"));
				DropSlottedItems(cOs);
			}
			if (ship.ShipCO != null)
			{
				Interaction interaction = DataHandler.GetInteraction("Unconscious");
				QueueInteraction(ship.ShipCO, interaction, bInsert: true);
			}
			if (CrewSim.GetSelectedCrew() == this)
			{
				CrewSim.objInstance.CycleCrew();
			}
			AIShipManager.ValidateCrew(this);
		}
	}

	private void KOWake()
	{
		if (bAlive && HasCond("Unconscious") && ship.ShipCO != null)
		{
			Interaction interaction = DataHandler.GetInteraction("SeekSleepSimpleWake");
			if (interaction != null)
			{
				interaction.objUs = this;
				interaction.objThem = ship.ShipCO;
				interaction.ApplyChain();
			}
		}
	}

	public void DropSlottedItems(List<CondOwner> aCOs)
	{
		if (aCOs == null)
		{
			return;
		}
		aCOs = aCOs.Distinct().ToList();
		for (int num = aCOs.Count - 1; num >= 0; num--)
		{
			CondOwner condOwner = aCOs[num];
			if (condOwner == null || condOwner.slotNow == null)
			{
				aCOs.RemoveAt(num);
			}
			else if (condOwner.HasCond("IsHiddenInv") || condOwner.HasCond("IsSystem") || condOwner.bSlotLocked)
			{
				aCOs.RemoveAt(num);
			}
		}
		foreach (CondOwner aCO in aCOs)
		{
			CondOwner condOwner2 = DropCO(aCO, bAllowLocked: false);
			if (condOwner2 != null)
			{
				if (ship != null)
				{
					Debug.LogWarning("Unable to drop slotted item " + condOwner2.strName + ", Readding to ship");
					ship.AddCO(condOwner2, bTiles: true);
				}
				else
				{
					Debug.LogWarning("Unable to drop slotted item " + condOwner2.strName + ", Ship already null! Destroying");
					condOwner2.Destroy();
				}
			}
		}
	}

	public string PrintIAH()
	{
		string text = "";
		foreach (CondHistory value in mapIAHist.Values)
		{
			text += value.Print(strName);
		}
		return text;
	}

	public override string ToString()
	{
		return strName;
	}

	public CondOwner GetSingleOrStack(bool bWholeStack)
	{
		if (bWholeStack)
		{
			if ((bool)coStackHead)
			{
				return coStackHead;
			}
			return this;
		}
		return this;
	}

	public List<Slot> GetSlots(bool bDeep, Slots.SortOrder sortOrder = Slots.SortOrder.HELD_FIRST)
	{
		if (compSlots == null)
		{
			return _emptySlotsResult ?? (_emptySlotsResult = new List<Slot>());
		}
		return sortOrder switch
		{
			Slots.SortOrder.BY_DEPTH => compSlots.GetSlotsDepthFirst(bDeep), 
			Slots.SortOrder.CHILD_FIRST => compSlots.GetSlotsChildFirst(bDeep), 
			_ => compSlots.GetSlotsHeldFirst(bDeep), 
		};
	}

	public bool CanTakeItemsSimulated(List<CondOwner> aItems)
	{
		if (compSlots == null || aItems == null || aItems.Count == 0)
		{
			if (aItems != null)
			{
				return aItems.Count == 0;
			}
			return true;
		}
		List<Slot> slots = GetSlots(bDeep: true);
		Dictionary<Slot, int> dictionary = new Dictionary<Slot, int>();
		Dictionary<Slot, List<CondOwner>> dictionary2 = new Dictionary<Slot, List<CondOwner>>();
		Dictionary<Container, int> dictionary3 = new Dictionary<Container, int>();
		Dictionary<CondOwner, int> dictionary4 = new Dictionary<CondOwner, int>();
		foreach (CondOwner aItem in aItems)
		{
			if (aItem == null || aItem.RootParent() == this)
			{
				continue;
			}
			bool flag = false;
			for (int i = 0; i < slots.Count; i++)
			{
				Slot slot = slots[i];
				if (slot.bHide || !slot.bHoldSlot || !slot.CanFit(aItem, bAuto: false, bSub: true, checkStacks: true, bAllowLocked: false))
				{
					continue;
				}
				int num = 0;
				CondOwner[] aCOs = slot.aCOs;
				for (int j = 0; j < aCOs.Length; j++)
				{
					if (aCOs[j] == null)
					{
						num++;
					}
				}
				int num2 = 0;
				aCOs = slot.aCOs;
				foreach (CondOwner condOwner in aCOs)
				{
					if (!(condOwner == null))
					{
						int value;
						int num3 = (dictionary4.TryGetValue(condOwner, out value) ? value : 0);
						if (slot.bAllowStacks)
						{
							num2 += Math.Max(0, condOwner.CanStackOnItem(aItem) - num3);
						}
					}
				}
				int num4 = 0;
				if (slot.bAllowStacks && dictionary2.TryGetValue(slot, out var value2))
				{
					foreach (CondOwner item in value2)
					{
						int value3;
						int num5 = (dictionary4.TryGetValue(item, out value3) ? value3 : 0);
						num4 += Math.Max(0, item.CanStackOnItem(aItem) - num5);
					}
				}
				int value4;
				int num6 = (dictionary.TryGetValue(slot, out value4) ? value4 : 0);
				if (num6 < num)
				{
					if (!dictionary2.ContainsKey(slot))
					{
						dictionary2[slot] = new List<CondOwner>();
					}
					dictionary2[slot].Add(aItem);
				}
				else
				{
					if (!slot.bAllowStacks || num2 + num4 <= 0)
					{
						continue;
					}
					bool flag2 = false;
					aCOs = slot.aCOs;
					foreach (CondOwner condOwner2 in aCOs)
					{
						if (!(condOwner2 == null))
						{
							int value5;
							int num7 = (dictionary4.TryGetValue(condOwner2, out value5) ? value5 : 0);
							if (condOwner2.CanStackOnItem(aItem) > num7)
							{
								dictionary4[condOwner2] = num7 + aItem.StackCount;
								flag2 = true;
								break;
							}
						}
					}
					if (!flag2 && dictionary2.TryGetValue(slot, out value2))
					{
						foreach (CondOwner item2 in value2)
						{
							int value6;
							int num8 = (dictionary4.TryGetValue(item2, out value6) ? value6 : 0);
							if (item2.CanStackOnItem(aItem) > num8)
							{
								dictionary4[item2] = num8 + aItem.StackCount;
								flag2 = true;
								break;
							}
						}
					}
					if (!flag2)
					{
						continue;
					}
				}
				dictionary[slot] = num6 + 1;
				flag = true;
				break;
			}
			if (flag)
			{
				continue;
			}
			for (int k = 0; k < slots.Count; k++)
			{
				Slot slot2 = slots[k];
				if (slot2.bHide)
				{
					continue;
				}
				CondOwner[] aCOs = slot2.aCOs;
				foreach (CondOwner condOwner3 in aCOs)
				{
					if (condOwner3 == null || condOwner3.objContainer == null)
					{
						continue;
					}
					Container container = condOwner3.objContainer;
					if (!container.AllowedCO(aItem))
					{
						continue;
					}
					if (container.CO.HasCond("IsInfiniteContainer"))
					{
						flag = true;
						break;
					}
					int gridMaxSpace = container.gridLayout.gridMaxSpace;
					if (gridMaxSpace <= 0)
					{
						continue;
					}
					int num9 = 0;
					foreach (CondOwner containedCO in container.ContainedCOs)
					{
						if (!(containedCO.coStackHead != null))
						{
							int value7;
							int num10 = (dictionary4.TryGetValue(containedCO, out value7) ? value7 : 0);
							if (containedCO.StackCount + num10 >= containedCO.nStackLimit || containedCO.CanStackOnItem(aItem) <= num10)
							{
								num9 += Container.GetSpace(containedCO);
							}
						}
					}
					int value8;
					int num11 = (dictionary3.TryGetValue(container, out value8) ? value8 : 0);
					int space = Container.GetSpace(aItem);
					bool flag3 = false;
					foreach (CondOwner containedCO2 in container.ContainedCOs)
					{
						if (!(containedCO2.coStackHead != null))
						{
							int value9;
							int num12 = (dictionary4.TryGetValue(containedCO2, out value9) ? value9 : 0);
							if (containedCO2.CanStackOnItem(aItem) > num12)
							{
								flag3 = true;
								break;
							}
						}
					}
					if (flag3)
					{
						foreach (CondOwner containedCO3 in container.ContainedCOs)
						{
							if (!(containedCO3.coStackHead != null))
							{
								int value10;
								int num13 = (dictionary4.TryGetValue(containedCO3, out value10) ? value10 : 0);
								if (containedCO3.CanStackOnItem(aItem) > num13)
								{
									dictionary4[containedCO3] = num13 + aItem.StackCount;
									break;
								}
							}
						}
						flag = true;
						break;
					}
					if (gridMaxSpace - num9 - num11 >= space)
					{
						dictionary3[container] = num11 + space;
						flag = true;
						break;
					}
				}
				if (flag)
				{
					break;
				}
			}
			if (!flag)
			{
				return false;
			}
		}
		return true;
	}

	public double RecentlyTried(Interaction ia, bool allowIaOnly = false)
	{
		if (ia == null || ia.objThem == null)
		{
			return -1.0;
		}
		double value = -1.0;
		if (dictRecentlyTried.TryGetValue(ia.objThem.strID + ia.strName, out value))
		{
			return value;
		}
		if (allowIaOnly && dictRecentlyTried.TryGetValue(ia.strName, out value))
		{
			return value;
		}
		return -1.0;
	}

	public void AddRecentlyTried(string strRef)
	{
		if (!string.IsNullOrEmpty(strRef))
		{
			dictRecentlyTried[strRef] = StarSystem.fEpoch;
		}
	}

	private void OnDestroy()
	{
		DataHandler.debugCOCount--;
	}

	public void PrintCondRules()
	{
		foreach (CondRule value2 in mapCondRules.Values)
		{
			string text = value2.strCond + " = " + GetCondAmount(value2.strCond) + "; ";
			text = text + "CurrentThresh: " + Array.IndexOf(value2.aThresholds, value2.GetCurrentThresh(this)) + "; ";
			string value = "Dc" + value2.strCond.Replace("Stat", "");
			foreach (string key in mapConds.Keys)
			{
				if (key.IndexOf(value) >= 0)
				{
					text = text + "DC: " + key;
					break;
				}
			}
			Debug.LogWarning(text);
		}
	}

	public float CondPercentage(string numer, string denom)
	{
		double num = 0.0;
		double num2 = 0.0;
		double num3 = 0.0;
		if (numer != null && numer != "")
		{
			num2 = GetCondAmount(numer);
		}
		if (denom != null && denom != "")
		{
			num3 = GetCondAmount(denom);
		}
		if (num2 < 0.0)
		{
			num2 = 0.0;
		}
		num = ((!(num3 <= 0.0)) ? (num2 / num3) : 0.0);
		return (float)num;
	}

	public void AddReplyThread(double fEpoch, string strID, Interaction objInteraction)
	{
		if (objInteraction == null || strID == null)
		{
			return;
		}
		for (int num = aReplies.Count - 1; num >= 0; num--)
		{
			ReplyThread replyThread = aReplies[num];
			if (replyThread.strID == strID && replyThread.jis.strName == objInteraction.strName)
			{
				aReplies.RemoveAt(num);
			}
		}
		aReplies.Add(new ReplyThread
		{
			fEpoch = fEpoch,
			strID = strID,
			jis = objInteraction.GetJSONSave()
		});
		if (CrewSim.GetSelectedCrew() == this)
		{
			UpdateWaitingReplies.Invoke(aReplies);
		}
	}

	public void SetUpBehaviours()
	{
		if (!HasCond("StatInstallProgressMax"))
		{
			AddCondAmount("StatInstallProgressMax", 1000.0);
		}
		if (!HasCond("StatUninstallProgressMax"))
		{
			AddCondAmount("StatUninstallProgressMax", 1000.0);
		}
		if (!HasCond("StatRepairProgressMax"))
		{
			AddCondAmount("StatRepairProgressMax", 1000.0);
		}
		if (!HasCond("StatDamageMax") || HasCond("IsSystem"))
		{
			return;
		}
		if (!HasCond("IsDestructable") && !HasCond("IsIndestructable"))
		{
			if (HasCond("IsTechnology"))
			{
				AddCommand("Destructable,StatDamage,ACTTechDestroy,StatDamageMax,1.0");
			}
			else if (HasCond("IsMechanical"))
			{
				AddCommand("Destructable,StatDamage,ACTMechDestroy,StatDamageMax,1.0");
			}
			else
			{
				AddCommand("Destructable,StatDamage,ACTDefaultDestroy,StatDamageMax,1.0");
			}
		}
		if (HasCond("IsUndamageable") || (!HasCond("IsInstalled") && !HasCond("IsSolid")))
		{
			return;
		}
		if ((double)tf.localScale.x > 1.0 || (double)tf.localScale.y > 1.0)
		{
			if (aInteractions.IndexOf("ACTBashBig") < 0 && aInteractions.IndexOf("ACTBash") < 0)
			{
				aInteractions.Add("ACTBashBig");
			}
		}
		else if (aInteractions.IndexOf("ACTBashBig") < 0 && aInteractions.IndexOf("ACTBash") < 0)
		{
			aInteractions.Add("ACTBash");
		}
		if (!HasCond("IsDamageable"))
		{
			AddCondAmount("IsDamageable", 1.0);
		}
	}

	public void PlayHitAnim(double fDmgBlunt, double fDmgCut)
	{
		if (bAlive && !HasCond("Unconscious") && !HasCond("Prone"))
		{
			if (fDmgBlunt > 5.0 || fDmgCut > 5.0)
			{
				SetAnimTrigger("Hit");
			}
			else
			{
				SetAnimTrigger("HitLess");
			}
		}
	}

	public void BreakIn(float percentage = 1f, bool allowMultiple = false, double fRepairTarget = 0.0)
	{
		SetUpBehaviours();
		double condAmount = GetCondAmount("StatDamageMax");
		if (condAmount > 0.0 && !HasCond("IsSystem"))
		{
			bool flag = false;
			double condAmount2 = GetCondAmount("StatDamage");
			if (allowMultiple || (!CrewSim.bShipEdit && condAmount2 == 0.0))
			{
				double x = MathUtils.Rand(0.0, condAmount * (double)percentage, MathUtils.RandType.Flat);
				double num = (condAmount - condAmount2) / condAmount;
				x = ((!(fRepairTarget > num)) ? MathUtils.Clamp(x, 0.0, (num - fRepairTarget) * condAmount) : (0.0 - MathUtils.Clamp(x, 0.0, (fRepairTarget - num) * condAmount)));
				if (x != 0.0)
				{
					if (x > 0.0 && HasCond("IsPristine"))
					{
						x *= 0.75;
					}
					AddCondAmount("StatDamage", x);
					flag = true;
				}
			}
			if (flag)
			{
				if (Item != null)
				{
					Item.VisualizeOverlays();
				}
				if (Pwr != null)
				{
					Pwr.ResetCurrentToMaxPower();
				}
			}
		}
		UpdateStats();
	}

	private void UpdateStats()
	{
		if (_statDamageMax == null || _statDamage == null)
		{
			FetchDamageConds();
		}
		if (_statDamageMax != null && _statDamageMax.fCount > 0.0 && _statDamage != null)
		{
			float damageRate = GetDamageRate();
			if (_lastDamageUpdate != damageRate)
			{
				_lastDamageUpdate = damageRate;
				mapInfo["Condition"] = ((double)(1f - _lastDamageUpdate) * 100.0).ToString("#.00") + "%";
			}
		}
		else
		{
			mapInfo["Condition"] = "100%";
		}
	}

	private void FetchDamageConds()
	{
		mapConds.TryGetValue("StatDamageMax", out _statDamageMax);
		mapConds.TryGetValue("StatDamage", out _statDamage);
	}

	public float GetDamageRate()
	{
		if (_statDamageMax == null || _statDamage == null)
		{
			FetchDamageConds();
		}
		double num = 0.0;
		if (_statDamage != null)
		{
			num = _statDamage.fCount;
		}
		double num2 = ((_statDamageMax != null) ? _statDamageMax.fCount : 1.0);
		return (float)(num / num2);
	}

	public double GetDamageRemaining()
	{
		if (_statDamageMax == null || _statDamage == null)
		{
			FetchDamageConds();
		}
		double num = 0.0;
		if (_statDamage != null)
		{
			num = _statDamage.fCount;
		}
		double num2 = ((_statDamageMax != null) ? _statDamageMax.fCount : 1.0);
		return Math.Max(0.0, num2 - num);
	}

	public double GetDamage()
	{
		if (_statDamageMax == null || _statDamage == null)
		{
			FetchDamageConds();
		}
		if (_statDamage == null)
		{
			return 0.0;
		}
		return _statDamage.fCount;
	}

	public List<CondOwner> GetFollowers()
	{
		if (ship == null)
		{
			return new List<CondOwner>();
		}
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsFollowCommand");
		return ship.GetCOs(condTrigger, bSubObjects: false, bAllowDocked: true, bAllowLocked: false);
	}

	public void DebugReportCauseOfDeath()
	{
		if (!HasCond("IsDead"))
		{
			return;
		}
		List<string> list = new List<string>();
		foreach (Condition value in mapConds.Values)
		{
			if (value.bFatal)
			{
				list.Add(value.strName);
			}
		}
		Debug.Log(strName + " dead on ship: " + ((ship != null) ? ship.strRegID : "null ship") + ": " + string.Join(",", list.ToArray()));
		if (list.Count != 0)
		{
			return;
		}
		foreach (JsonLogMessage aMessage in aMessages)
		{
			Debug.Log(aMessage.strMessage);
		}
	}

	public void DebugReportCondrules()
	{
		foreach (CondRule value in mapCondRules.Values)
		{
			Debug.Log(value.strName + ": " + value.Modifier);
		}
	}

	public void DebugFixOldCondRules(bool bOnlyReport)
	{
		if (!bOnlyReport && HasCond("IsDebugCondRuleFixed01"))
		{
			return;
		}
		foreach (CondRule value in mapCondRules.Values)
		{
			List<CondRuleThresh> list = new List<CondRuleThresh>();
			CondRuleThresh[] aThresholds = value.aThresholds;
			foreach (CondRuleThresh condRuleThresh in aThresholds)
			{
				if (string.IsNullOrEmpty(condRuleThresh.strLootNew))
				{
					continue;
				}
				Loot loot = DataHandler.GetLoot(condRuleThresh.strLootNew);
				if (loot.strName == "Blank")
				{
					continue;
				}
				foreach (string lootName in loot.GetLootNames(null, bOnlyCOs: true))
				{
					if (lootName.IndexOf("Dc") == 0 && mapConds.ContainsKey(lootName))
					{
						list.Add(condRuleThresh);
						break;
					}
				}
			}
			if (list.Count <= 1)
			{
				continue;
			}
			bool flag = bLogConds;
			bLogConds = false;
			string text = "";
			foreach (CondRuleThresh item in list)
			{
				if (string.IsNullOrEmpty(item.strLootNew))
				{
					continue;
				}
				Loot loot2 = DataHandler.GetLoot(item.strLootNew);
				if (!(loot2.strName == "Blank"))
				{
					if (!bOnlyReport)
					{
						loot2.ApplyCondLoot(this, -1f);
					}
					if (text.Length > 0)
					{
						text += ", ";
					}
					text += loot2.strName;
				}
			}
			Loot loot3 = DataHandler.GetLoot(value.GetCurrentThresh(this).strLootNew);
			if (bOnlyReport)
			{
				text = text + ". Correct: " + loot3.strName;
			}
			else
			{
				if (loot3.strName != "Blank")
				{
					loot3.ApplyCondLoot(this, -1f);
				}
				text = text + ". Restoring " + loot3.strName;
			}
			bLogConds = flag;
			if (bOnlyReport)
			{
				Debug.Log("Duplicate DCs found on " + strName + ". Found: " + text);
			}
			else
			{
				Debug.Log("Duplicate DCs found on " + strName + ". Removing " + text);
			}
		}
		if (!bOnlyReport)
		{
			AddCondAmount("IsDebugCondRuleFixed01", 1.0);
		}
	}

	public double DebugAuditMass(string strPrefix, bool bFix)
	{
		double num = 0.0;
		double condAmount = GetCondAmount("StatMass");
		double num2 = 0.0;
		JsonCondOwner condOwnerDef = DataHandler.GetCondOwnerDef(strCODef);
		if (condOwnerDef != null)
		{
			string[] aStartingConds = condOwnerDef.aStartingConds;
			foreach (string text in aStartingConds)
			{
				if (text.IndexOf("StatMass") >= 0)
				{
					num = Loot.ParseCondEquation(text).fMin;
				}
			}
		}
		num2 += num;
		if (objContainer != null)
		{
			num2 += objContainer.DebugAuditMass(strPrefix, bFix);
		}
		if (compSlots != null)
		{
			num2 += compSlots.DebugAuditMass(strPrefix, bFix);
		}
		double num3 = 0.0;
		if (aStack != null)
		{
			foreach (CondOwner item in aStack)
			{
				num3 += item.DebugAuditMass(strPrefix + "\t", bFix);
			}
		}
		string text2 = "";
		if (num2 != condAmount)
		{
			text2 = "*";
		}
		Debug.Log(text2 + strPrefix + "Mass: " + condAmount + " (" + num + ") NEW: " + num2 + " " + strCODef + ":" + strID);
		if (bFix)
		{
			SetCondAmount("StatMass", num2);
		}
		return num2 + num3;
	}

	public void DebugFixOldMovSpeed(bool bOnlyReport)
	{
		if (!bOnlyReport && HasCond("IsDebugMovSpeedPenaltyFixed01"))
		{
			return;
		}
		double num = 0.0;
		num += GetCondAmount("IsBarefoot") * 0.05;
		num += GetCondAmount("Blisters") * 0.25;
		num += GetCondAmount("CrippledLeg") * 0.5;
		num += GetCondAmount("Prone") * 0.75;
		num += GetCondAmount("DcAging04") * 0.1;
		num += GetCondAmount("DcAging05") * 0.2;
		num += GetCondAmount("DcEncumbrance02") * 0.25;
		num += GetCondAmount("DcEncumbrance03") * 0.5;
		num += GetCondAmount("DcEncumbrance04") * 1.0;
		num += GetCondAmount("DcFatigue02") * 0.1;
		num += GetCondAmount("DcFatigue03") * 0.25;
		num += GetCondAmount("DcFatigue04") * 0.5;
		num += GetCondAmount("DcFatigue05") * 1.0;
		num += GetCondAmount("DcOxygen02") * 0.5;
		num += GetCondAmount("DcOxygen03") * 0.7;
		num += GetCondAmount("DcPain02") * 0.05;
		num += GetCondAmount("DcPain03") * 0.35;
		num += GetCondAmount("ChronicHerniatedDisc3") * 0.1;
		num += GetCondAmount("ChronicTornACL2") * 0.2;
		num += GetCondAmount("ChronicTornMCL2") * 0.2;
		num += GetCondAmount("ChronicTornMeniscus2") * 0.2;
		num += GetCondAmount("ChronicPatellerTendonitis2") * 0.2;
		double condAmount = GetCondAmount("StatMovSpeedPenalty");
		if (condAmount > num)
		{
			if (bOnlyReport)
			{
				Debug.Log("Found bad StatMovSpeedPenalty on " + strID + " is: " + condAmount + " should be: " + num);
			}
			else
			{
				Debug.Log("Repairing StatMovSpeedPenalty on " + strID + " from " + condAmount + " to " + num);
				SetCondAmount("StatMovSpeedPenalty", num);
			}
		}
		num = 0.0;
		num += GetCondAmount("CrippledArm") * 0.5;
		num += GetCondAmount("ChronicHerniatedDisc3") * 0.1;
		num += GetCondAmount("ChronicMangledHand") * 0.1;
		num += GetCondAmount("ChronicCarpalTunnelSyndrome2") * 0.2;
		num += GetCondAmount("ChronicTendonitis2") * 0.2;
		num += GetCondAmount("ChronicArthritis2") * 0.05;
		num += GetCondAmount("ChronicArthritis3") * 0.15;
		num += GetCondAmount("IsWearingEVASuitWorkRatePenalty") * 0.45;
		num += GetCondAmount("Pain02WorkRatePenalty") * 0.15;
		num += GetCondAmount("Pain03WorkRatePenalty") * 0.45;
		condAmount = GetCondAmount("StatWorkSpeedPenalty");
		if (condAmount > num)
		{
			if (bOnlyReport)
			{
				Debug.Log("Found bad StatWorkSpeedPenalty on " + strID + " is: " + condAmount + " should be: " + num);
			}
			else
			{
				Debug.Log("Repairing StatWorkSpeedPenalty on " + strID + " from " + condAmount + " to " + num);
				SetCondAmount("StatWorkSpeedPenalty", num);
			}
		}
		if (!bOnlyReport)
		{
			AddCondAmount("IsDebugMovSpeedPenaltyFixed01", 1.0);
		}
	}

	private bool AutoPauseIgnore(string strIA)
	{
		if (string.IsNullOrEmpty(strIA))
		{
			return false;
		}
		if (_aAutoPauseIgnore == null)
		{
			_aAutoPauseIgnore = DataHandler.GetLoot("TXTAutoPauseIgnore").GetAllLootNames();
		}
		return _aAutoPauseIgnore.IndexOf(strIA) >= 0;
	}

	public void Rename(string newName)
	{
		if (IsHumanOrRobot)
		{
			Debug.LogWarning("Trying to rename human or robot which is forbidden. Aborting.");
			return;
		}
		if (newName != null && newName != "")
		{
			Dictionary<string, string> dictionary = new Dictionary<string, string>();
			dictionary.Add("strName", newName);
			if (mapGUIPropMaps.ContainsKey("Rename"))
			{
				mapGUIPropMaps.Remove("Rename");
			}
			mapGUIPropMaps.Add("Rename", dictionary);
		}
		else
		{
			mapGUIPropMaps.Remove("Rename");
		}
		_Rename(newName);
		CrewSim.OnRightClick.Invoke(new List<CondOwner> { this });
	}

	public void CheckForRename()
	{
		if (mapGUIPropMaps.TryGetValue("Rename", out var value))
		{
			_Rename(value["strName"]);
		}
	}

	private void _Rename(string newName)
	{
		if (newName != null && newName != "")
		{
			strNameFriendly = newName;
			strNameShort = newName;
		}
		else
		{
			strNameFriendly = DataHandler.GetCOFriendlyName(strName);
			strNameShort = DataHandler.GetCOShortName(strName);
		}
	}
}
