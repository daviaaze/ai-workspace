using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Ostranauts.COCommands;
using Ostranauts.Core;
using Ostranauts.Core.Models;
using Ostranauts.Electrical;
using Ostranauts.Events;
using Ostranauts.Objectives;
using Ostranauts.Pathing;
using Ostranauts.Pledges;
using Ostranauts.ShipGUIs.ShipBroker;
using Ostranauts.ShipGUIs.Trade;
using Ostranauts.ShipGUIs.Utilities;
using Ostranauts.Ships;
using Ostranauts.Ships.AIPilots;
using Ostranauts.Ships.Comms;
using Ostranauts.Ships.Rooms;
using Ostranauts.Ships.Sensors;
using Ostranauts.Tools.ExtensionMethods;
using Ostranauts.Trading;
using Ostranauts.Utils;
using Ostranauts.Utils.Models;
using SolarSystem;
using UnityEngine;

public class Ship : IShip
{
	public enum Loaded
	{
		None,
		Shallow,
		Edit,
		Full
	}

	public enum Damage
	{
		New,
		Used,
		Damaged,
		Derelict
	}

	public enum Audio
	{
		RCS,
		CollisionBig,
		CollisionMed,
		CollisionSmall
	}

	public enum TypeClassification
	{
		Default,
		OrbitalStation,
		OrbitalStationUnfinished,
		GroundStation,
		GroundStationUnfinished,
		Buoy,
		Outpost,
		Waypoint,
		Projectile,
		Asteroid,
		SignalBeacon,
		SecurityOutpost,
		Infrastructure,
		Skyscraper
	}

	public enum TypeLatestStatus
	{
		None,
		Tracking,
		Impacted,
		Fired
	}

	public enum EngineMode
	{
		AUTO,
		RCS,
		MIXED,
		ROTOR
	}

	public static ManeuverEvent OnManeuver = new ManeuverEvent();

	public static DockEvent OnDock = new DockEvent();

	public const float RCS_EXHAUST_V_AU = 5.26077E-09f;

	public const float RCS_MASS_FLOW = 0.728f;

	public const float RCS_FUDGE = 100f;

	public const string MOORINGID = "MP|";

	public const string MOORINGINITIATOR = "MP|I|";

	public const string GPMRENAME = "Rename";

	public const string GPMRENAMEKEY = "strName";

	private const float USED_SHIP_DMG = 0.33f;

	public const double DMG_PER_SEC = 1.5844382307706396E-09;

	public string strRegID;

	public string strLaw;

	public string strParallax;

	public JsonShip json;

	public int nCols;

	public int nRows;

	public int nGridRotation;

	public List<Vector2> FloorPlan;

	public List<Vector2> SilhouettePoints;

	public int nCurrentWaypoint = -1;

	public float fTimeEngaged;

	private double fGravity = 0.3;

	private double _mass;

	public Vector2 vShipPos;

	public GameObject gameObject;

	private GameObject goTiles;

	public Transform tfBGs;

	public bool bDestroyed;

	private bool _proximityWarning;

	private float _proximityDistanceScaled = 1f;

	private bool _trackWarning;

	public List<string> aProxCurrent;

	public List<string> aProxIgnores;

	public List<string> aTrackCurrent;

	public List<string> aTrackIgnores;

	public float fVisibilityRangeMod = 1f;

	private float fAeroCoefficient = 1f;

	private double fFuelEfficiencyMod = 1.0;

	public List<WaypointShip> aWPs;

	public List<Tile> aTiles;

	public List<Tile> aPwrTiles;

	public List<Tile> aPwrTilesOff;

	public List<Room> aRooms;

	protected Dictionary<string, CondOwner> mapICOs;

	public Dictionary<string, string> mapIDRemap;

	private List<PersonSpec> aPeople;

	private List<CondOwner> aLocks;

	private Loaded nLoadState;

	public Damage DMGStatus;

	public Dictionary<string, JsonZone> mapZones;

	private Dictionary<string, List<Vector2>> dictBGs;

	private List<CondOwner> aRCSDistros;

	private List<CondOwner> aRCSThrusters;

	public List<CondOwner> aDocksys;

	private List<CondOwner> aO2AirPumps;

	private List<CondOwner> aCores;

	public bool bCheckRooms;

	public bool bCheckPower;

	public bool bCheckLocks;

	public bool bRemove;

	public bool bCheckTargets;

	public bool bCheckFusion;

	public bool bCheckSensors;

	public bool bCheckTowingBraces;

	public bool bChangedStatus;

	private bool bResetLocks;

	private bool bPrefill;

	public bool bBreakInUsed;

	public bool bNoCollisions = true;

	public bool bNeedsGravSet;

	protected float fRCSCount;

	public List<CondOwner> aActiveHeavyLiftRotors;

	private int nRCSDistroCount;

	private List<string> aDockingPorts = new List<string>();

	private string strPrimaryDockingPortID;

	private Dictionary<string, Ship> aDocked;

	private Dictionary<string, string> aSecuredTowBraces;

	public List<CondOwner> aNavs;

	public double fLastVisit;

	public List<CondOwner> aElectronicSystemCOs;

	public double fFirstVisit;

	public int nInitConstructionProgress;

	public string strTemplateName;

	public int nConstructionProgress = 100;

	private bool bIsUnderConstruction;

	private static readonly RaycastHit[] aHitsGetCOs = new RaycastHit[25];

	private static CondTrigger ctRCSGasCans;

	private static CondTrigger ctRCSGasInput;

	private static CondTrigger ctRCSClusterAudioEmitter;

	private static CondTrigger ctRCSDistroInstalled;

	private static CondTrigger ctDerelictSafe;

	public static CondTrigger ctNavStationOn;

	public static CondTrigger ctRadarOn;

	public static CondTrigger ctXPDR;

	public static CondTrigger ctXPDRAntOn;

	private static CondTrigger ctDocksys;

	private static CondTrigger ctPortals;

	private static CondTrigger ctWearManeuver;

	private static CondTrigger ctWearManeuverTow;

	private static CondTrigger ctWearTime;

	public static CondTrigger ctSparkable;

	private static CondTrigger ctPilotSafe;

	private static CondTrigger ctFactionCO;

	private static CondTrigger ctPermitOKLG;

	private static CondTrigger ctTowBraceSecured;

	private static CondTrigger ctO2Can;

	private static CondTrigger ctAirPump;

	private static CondTrigger ctStabilizerActiveOn;

	private static CondTrigger ctHeavyLiftRotorsInstalled;

	private static CondTrigger ctTutorialDerelict;

	private static CondTrigger ctWeaponInstalled;

	public static CondTrigger ctLootSpawner;

	public float fSpawnPrice;

	private float fWearManeuver;

	public double fLastWearEpoch;

	public double fWearAccrued;

	private int nActiveStabilizers;

	private List<JsonFaction> aFactions;

	public float fBreakInMultiplier = 1f;

	public string make = "";

	public string model = "";

	public string year = "";

	public string origin = "";

	public string description = "";

	public string designation = "";

	public string publicName = "";

	public string dimensions = "";

	public double fLastQuotedPrice;

	private string[] rating;

	protected double fShallowMass;

	public double fShallowRCSRemass;

	public double fShallowRCSRemassMax;

	public double fShallowFusionRemain;

	public double fFusionThrustMax;

	public double fFusionPelletMax;

	public double fEpochNextGrav;

	public bool bFusionReactorRunning;

	private bool bTorchDriveThrusting;

	private bool _isDespawning;

	private string _strXPDR;

	private List<JsonShipLog> aLog;

	private bool _bDoneLoading;

	public TypeClassification Classification;

	private TypeLatestStatus _latestStatus;

	public double fTimeSinceLatestStatus;

	public bool bStatusPlayed = true;

	public bool bXPDRAntenna;

	private bool bShipHidden;

	private static CondTrigger _ctRoomStats;

	private static CondTrigger _ctReactor;

	private static CondTrigger _ctHaulDest;

	public Ship shipScanTarget;

	public Ship shipStationKeepingTarget;

	public Ship shipCombatTarget;

	public string targetRegID;

	public TargetData TargetData;

	public ShipSitu shipSituTarget;

	public Ship shipUndock;

	public string strAIDespawnedAt;

	public double dLastScanTime;

	public double fAIDockingExpire;

	public double fAIPauseTimer;

	private bool bLocalAuthority;

	private bool bAIShip;

	private List<CondOwner> aSparkables;

	public string strDebugInfo;

	public static bool bDebugProjectileOutput = false;

	private double _lastAtmoUpdateTime;

	public List<Ship> CachedAllDockedShips;

	private bool _subStation;

	private double fGravAmountLast;

	private float fShallowRotorStrength = -1f;

	private readonly Vector2[] _directionVectors = new Vector2[4]
	{
		Vector2.down,
		Vector2.up,
		Vector2.left,
		Vector2.right
	};

	private List<RoomDividerDTO> _cachedRoomDividerDTOs;

	public CondOwner ShipCO { get; private set; }

	public ShipSitu objSS { get; private set; }

	public Dictionary<string, string> MarketConfigs { get; set; }

	public Comms Comms { get; private set; }

	public DamageSystem DamageSystem { get; private set; }

	public WeaponsSystem WeaponsSystem { get; private set; }

	public ElectronicSystems ElectronicSystems { get; private set; }

	public TypeLatestStatus LatestStatus
	{
		get
		{
			return _latestStatus;
		}
		set
		{
			_latestStatus = value;
			fTimeSinceLatestStatus = 0.0;
			bStatusPlayed = false;
		}
	}

	public bool IsNotAFullStation => Classification > TypeClassification.GroundStationUnfinished;

	public string strXPDR
	{
		get
		{
			return _strXPDR;
		}
		set
		{
			if (value != _strXPDR)
			{
				bChangedStatus = true;
			}
			_strXPDR = value;
		}
	}

	private CondTrigger CTRoomStats => _ctRoomStats ?? (_ctRoomStats = DataHandler.GetCondTrigger("TIsRoomStat"));

	public static CondTrigger CTReactor => _ctReactor ?? (_ctReactor = DataHandler.GetCondTrigger("TIsReactorICNAVUsable"));

	public static CondTrigger CtHaulDest => _ctHaulDest ?? (_ctHaulDest = DataHandler.GetCondTrigger("TIsValidHaulDest"));

	public int Population
	{
		get
		{
			if (aPeople != null)
			{
				return aPeople.Count;
			}
			return 0;
		}
	}

	public List<PersonSpec> People => aPeople;

	public double MaxPopulation => ShipCO.GetCondAmount("StationMaxPopulation", isThreshold: false);

	public string PrimaryDockingPortID
	{
		get
		{
			if (aDockingPorts != null && (string.IsNullOrEmpty(strPrimaryDockingPortID) || !aDockingPorts.Contains(strPrimaryDockingPortID)))
			{
				for (int i = 0; i < aDockingPorts.Count; i++)
				{
					if (!string.IsNullOrEmpty(aDockingPorts[i]) && !aDockingPorts[i].Contains("MP|"))
					{
						strPrimaryDockingPortID = aDockingPorts[i];
						break;
					}
				}
			}
			return strPrimaryDockingPortID;
		}
		set
		{
			strPrimaryDockingPortID = value;
		}
	}

	public string PrimaryDockingPortIDFriendly
	{
		get
		{
			if (string.IsNullOrEmpty(PrimaryDockingPortID) || PrimaryDockingPortID.Length < 3)
			{
				return "NONE";
			}
			string text = "";
			CondOwner cOByID = GetCOByID(PrimaryDockingPortID);
			if (cOByID != null)
			{
				text = " " + cOByID.FriendlyName;
				if (text.Length > 16)
				{
					text = text.Substring(0, 13) + "...";
				}
			}
			return PrimaryDockingPortID.Substring(0, 3).ToUpper() + text;
		}
	}

	public bool HasDockGroup => objSS?._dockGroup != null;

	public DockGroup DockGroup => objSS?._dockGroup;

	public CondOwner Reactor
	{
		get
		{
			if (aCores.Count > 0)
			{
				return aCores[0];
			}
			return null;
		}
	}

	public float CurrentRotorEfficiency
	{
		get
		{
			if (aRooms == null)
			{
				return 0f;
			}
			Room room = null;
			for (int i = 0; i < aRooms.Count; i++)
			{
				if (aRooms[i].Void)
				{
					room = aRooms[i];
					break;
				}
			}
			if (room != null)
			{
				return Mathf.Clamp((float)room.CO.GetCondAmount("StatGasPressure") / 100f, 0f, 1.5f);
			}
			return 0f;
		}
	}

	public string GetCurrentAICommandDescription
	{
		get
		{
			AIShip aIShipByRegID = AIShipManager.GetAIShipByRegID(strRegID);
			if (aIShipByRegID == null)
			{
				return "Idle";
			}
			return aIShipByRegID.ActiveCommandNameDescription;
		}
	}

	public string GetMarketStatus => MarketManager.GetStatusForShip(strRegID);

	public double GetRCSMinimumFuelAmount => 1.2 * AIShipManager.GetDeltaVNeededToTargetFullTrip(this, AIShipManager.ShipATCLast.objSS, AIShip.CalculateMaxSpeed(this)) * (double)fRCSCount * 0.7279999852180481 / RCSAccelMaxUndocked;

	public bool bDocked => IsDocked();

	public bool IsLocalAuthority
	{
		get
		{
			return bLocalAuthority;
		}
		set
		{
			bLocalAuthority = value;
			if (json != null)
			{
				json.bLocalAuthority = value;
			}
		}
	}

	public bool IsAIShip
	{
		get
		{
			return bAIShip;
		}
		set
		{
			bAIShip = value;
			if (json != null)
			{
				json.bAIShip = value;
			}
		}
	}

	public Loaded LoadState => nLoadState;

	public bool IsTemplateShip
	{
		get
		{
			if (fLastVisit != 0.0)
			{
				return false;
			}
			return true;
		}
	}

	public double Gravity
	{
		get
		{
			return fGravity;
		}
		set
		{
			bool flag = nLoadState >= Loaded.Edit;
			fGravity = value;
			float num = Mathf.Abs((float)(fGravity - fGravAmountLast));
			if (bNeedsGravSet || GUIFFWD.Active)
			{
				num = 0f;
			}
			fWearManeuver += num;
			CondTrigger ctDamage = ctWearManeuver;
			float fDmgModifier = 1f;
			bool flag2 = false;
			if (num / 9.81f > 8f)
			{
				fDmgModifier = MathUtils.Rand(0f, 288000f, MathUtils.RandType.Mid);
				flag2 = true;
			}
			if (IsDocked() && !TowBracesSecured())
			{
				fWearManeuver += num * 4f;
				ctDamage = ctWearManeuverTow;
				fDmgModifier = MathUtils.Rand(0f, 288000f, MathUtils.RandType.Mid);
				flag2 = true;
			}
			WearManeuver(ctDamage, flag, fDmgModifier);
			if (flag && !bNeedsGravSet && !GUIFFWD.Active)
			{
				float num2 = Mathf.Min(1f, num / 4f);
				if (num2 > 0.05f)
				{
					CrewSim.objInstance.CamShake(num2);
				}
				if ((double)num >= 0.3)
				{
					if (flag2)
					{
						AudioManager.am.PlayCreakAudio("TXTRandomCreakMedAudio");
					}
					else
					{
						AudioManager.am.PlayCreakAudio("TXTRandomCreakSmAudio");
					}
				}
			}
			fGravAmountLast = fGravity;
			foreach (PersonSpec aPerson in aPeople)
			{
				if (!flag)
				{
					break;
				}
				CondOwner cO = aPerson.GetCO();
				if (cO == null)
				{
					continue;
				}
				if (cO.GetCondAmount("IsHuman") > 0.0)
				{
					if (cO.HasCond("Sitting"))
					{
						CrewSim.MuteCondRule(CrewSim.GetSelectedCrew(), "StatEncumbrance");
					}
					cO.SetCondAmount("StatEncumbrance", cO.GetCondAmount("StatMass") * fGravity);
					cO.UpdateGravity();
					cO.SetCondAmount("StatGrav", fGravity);
				}
				if (num > 1f)
				{
					KnockDownCrew(cO);
				}
			}
			if (flag && !bNeedsGravSet && fGravity >= 0.33000001311302185)
			{
				TileUtils.EVAFallAwayCheck(this, 3);
			}
		}
	}

	public double RCSAccelMax
	{
		get
		{
			double num = 100f * (0.728f * RCSCount) * 5.26077E-09f;
			IReadOnlyList<Ship> allDockedShips = GetAllDockedShips();
			double num2 = Mass;
			for (int i = 0; i < allDockedShips.Count; i++)
			{
				num2 += allDockedShips[i].Mass;
			}
			return num / num2;
		}
	}

	public double RCSAccelMaxUndocked => (double)(100f * (0.728f * RCSCount) * 5.26077E-09f) / Mass;

	public double DeltaVRemainingRCS => RCSAccelMax * GetRCSRemain() / 0.7279999852180481 / (double)fRCSCount;

	public double DeltaVMaxRCS => RCSAccelMax * GetRCSMax() / 0.7279999852180481 / (double)fRCSCount;

	public CondOwner Captain
	{
		get
		{
			CondOwner captain = null;
			Comms.GetCaptain(out captain);
			return captain;
		}
	}

	public bool InAtmo
	{
		get
		{
			BodyOrbit nearestBO = CrewSim.system.GetNearestBO(objSS, StarSystem.fEpoch, bIncludePlaceholders: false);
			if (nearestBO == null)
			{
				return false;
			}
			double distance = (double)objSS.GetRadiusAU() + objSS.GetDistance(nearestBO.dXReal, nearestBO.dYReal);
			return nearestBO.GetAtmosphereAtDistance(distance).GetTotalKPA() > BodyOrbit.AtmoKPaThreshold;
		}
	}

	public double Mass
	{
		get
		{
			if (LoadState <= Loaded.Shallow)
			{
				_mass = fShallowMass + MarketManager.GetCargoMassForShip(this);
				return _mass;
			}
			if (_mass == 0.0)
			{
				_mass = GetCondAmount("StatMass", bAllowDocked: false) + MarketManager.GetCargoMassForShip(this);
			}
			return _mass;
		}
	}

	public int NavCount => aNavs.Count;

	public bool NavAIManned
	{
		get
		{
			List<CondOwner> list = new List<CondOwner>();
			if (aPeople == null)
			{
				return false;
			}
			foreach (PersonSpec aPerson in aPeople)
			{
				if (aPerson != null && ctPilotSafe.Triggered(aPerson.GetCO()))
				{
					list.Add(aPerson.GetCO());
				}
			}
			if (list.Count == 0)
			{
				return false;
			}
			if (LoadState <= Loaded.Shallow && !IsDerelict())
			{
				return true;
			}
			if (aNavs.Count == 0)
			{
				return false;
			}
			foreach (CondOwner item in list)
			{
				Interaction interactionCurrent = item.GetInteractionCurrent();
				if (interactionCurrent != null && interactionCurrent.objThem != null && aNavs.IndexOf(interactionCurrent.objThem) >= 0)
				{
					return true;
				}
			}
			return false;
		}
	}

	public bool NavPlayerManned
	{
		get
		{
			if (LoadState <= Loaded.Shallow)
			{
				return false;
			}
			if (aNavs.Count == 0)
			{
				return false;
			}
			CondOwner selectedCrew = CrewSim.GetSelectedCrew();
			if (selectedCrew == null)
			{
				return false;
			}
			Interaction interactionCurrent = selectedCrew.GetInteractionCurrent();
			if (interactionCurrent == null)
			{
				return false;
			}
			if (aNavs.IndexOf(interactionCurrent.objThem) >= 0)
			{
				return true;
			}
			return false;
		}
	}

	public bool SkilledPilot => fFuelEfficiencyMod < 1.0;

	public float RCSCount
	{
		get
		{
			return fRCSCount;
		}
		set
		{
			fRCSCount = value;
		}
	}

	public bool HasDockingPorts
	{
		get
		{
			for (int i = 0; i < aDockingPorts.Count; i++)
			{
				string text = aDockingPorts[i];
				if (text.Length < 3 || text[0] != "MP|"[0] || text[1] != "MP|"[1] || text[2] != "MP|"[2])
				{
					return true;
				}
			}
			return false;
		}
	}

	public bool proximityWarning
	{
		get
		{
			return _proximityWarning;
		}
		set
		{
			bool flag = _proximityWarning;
			_proximityWarning = value;
			if (LoadState < Loaded.Edit)
			{
				return;
			}
			if (_proximityWarning && aNavs.Count > 0)
			{
				bool flag2 = false;
				foreach (CondOwner aNav in aNavs)
				{
					aNav.SetCondAmount("IsProxAlarm", 1.0);
					if (!aNav.HasCond("IsProxMuted"))
					{
						AlarmObjective objective = new AlarmObjective(AlarmType.nav_proximity, aNav, DataHandler.GetString("OBJV_NAV_PROX_TITLE"), "TIsNavStationProxClear", strRegID, DataHandler.GetString("OBJV_NAV_PROX_DESC"));
						MonoSingleton<ObjectiveTracker>.Instance.AddObjective(objective);
						flag2 = true;
					}
				}
				if (!flag2)
				{
					return;
				}
				AudioManager.am.PlayAudioEmitter("ShipProxAlarm", bLoop: true);
				if (!flag)
				{
					BeatManager.ResetTensionTimer();
					if ((double)Time.timeScale > 1.0)
					{
						CrewSim.ResetTimeScale();
					}
				}
				return;
			}
			AudioManager.am.StopAudioEmitter("ShipProxAlarm");
			foreach (CondOwner aNav2 in aNavs)
			{
				aNav2.ZeroCondAmount("IsProxAlarm");
				MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(aNav2.strID);
			}
		}
	}

	public float proximityDistanceScaled
	{
		get
		{
			return _proximityDistanceScaled;
		}
		set
		{
			if (_proximityDistanceScaled != value)
			{
				_proximityDistanceScaled = value;
				if (_proximityWarning && LoadState >= Loaded.Edit)
				{
					AudioManager.am.TweakAudioEmitter("ShipProxAlarm", 1f - _proximityDistanceScaled + 0.5f, 1f);
				}
			}
		}
	}

	public bool trackWarning
	{
		get
		{
			return _trackWarning;
		}
		set
		{
			bool flag = _trackWarning;
			_trackWarning = value;
			if (LoadState < Loaded.Edit)
			{
				return;
			}
			if (_trackWarning && aNavs.Count > 0)
			{
				AudioManager.am.PlayAudioEmitter("ShipTrackAlarm", bLoop: true);
				foreach (CondOwner aNav in aNavs)
				{
					aNav.SetCondAmount("IsTrackAlarm", 1.0);
				}
				if (_trackWarning && !flag && (double)Time.timeScale > 1.0)
				{
					CrewSim.ResetTimeScale();
					BeatManager.ResetTensionTimer();
				}
				return;
			}
			AudioManager.am.StopAudioEmitter("ShipTrackAlarm");
			foreach (CondOwner aNav2 in aNavs)
			{
				aNav2.ZeroCondAmount("IsTrackAlarm");
				MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(aNav2.strID);
			}
		}
	}

	public bool HideFromSystem
	{
		get
		{
			return bShipHidden;
		}
		set
		{
			bShipHidden = value;
			bNoCollisions = value;
			bChangedStatus = true;
		}
	}

	public double PelletMax
	{
		get
		{
			if (Reactor != null)
			{
				fFusionPelletMax = Reactor.GetCondAmount("StatICPellMax");
			}
			if (fFusionPelletMax <= 0.0)
			{
				fFusionPelletMax = 1.0;
			}
			return fFusionPelletMax;
		}
	}

	public bool IsUnderConstruction
	{
		get
		{
			return bIsUnderConstruction;
		}
		set
		{
			bIsUnderConstruction = value;
		}
	}

	public bool IsUsingTorchDrive
	{
		get
		{
			if (LoadState == Loaded.Full)
			{
				return bTorchDriveThrusting;
			}
			if (objSS != null && objSS.HasNavData())
			{
				return objSS.NavData.IsTorching;
			}
			return false;
		}
		set
		{
			if (value != bTorchDriveThrusting)
			{
				GUIOrbitDraw.TriggerShipRedraw(strRegID);
			}
			bTorchDriveThrusting = value;
		}
	}

	public float LiftRotorsThrustStrength
	{
		get
		{
			if (fShallowRotorStrength >= 0f)
			{
				return fShallowRotorStrength;
			}
			fShallowRotorStrength = 0f;
			foreach (CondOwner aActiveHeavyLiftRotor in aActiveHeavyLiftRotors)
			{
				if (!(aActiveHeavyLiftRotor == null))
				{
					fShallowRotorStrength += Rotor.ThrustStrength(aActiveHeavyLiftRotor);
				}
			}
			return fShallowRotorStrength;
		}
		set
		{
			fShallowRotorStrength = value;
		}
	}

	public Ship(GameObject go)
	{
		gameObject = go;
		goTiles = new GameObject("goTiles");
		goTiles.transform.SetParent(go.transform, worldPositionStays: false);
		tfBGs = new GameObject("goBGs").transform;
		tfBGs.SetParent(go.transform, worldPositionStays: false);
		aDocked = new Dictionary<string, Ship>();
		mapICOs = new Dictionary<string, CondOwner>();
		mapIDRemap = new Dictionary<string, string>();
		aTiles = new List<Tile>();
		aPwrTiles = new List<Tile>();
		aPwrTilesOff = new List<Tile>();
		aRooms = new List<Room>();
		aPeople = new List<PersonSpec>();
		aLocks = new List<CondOwner>();
		aWPs = new List<WaypointShip>();
		aNavs = new List<CondOwner>();
		aElectronicSystemCOs = new List<CondOwner>();
		aCores = new List<CondOwner>();
		nCols = 0;
		nRows = 0;
		FloorPlan = new List<Vector2>();
		vShipPos = Vector2.zero;
		objSS = new ShipSitu();
		mapZones = new Dictionary<string, JsonZone>();
		dictBGs = new Dictionary<string, List<Vector2>>();
		aProxCurrent = new List<string>();
		aProxIgnores = new List<string>();
		aTrackCurrent = new List<string>();
		aTrackIgnores = new List<string>();
		aFactions = new List<JsonFaction>();
		MarketConfigs = new Dictionary<string, string>();
		aRCSDistros = new List<CondOwner>();
		aRCSThrusters = new List<CondOwner>();
		aDocksys = new List<CondOwner>();
		aO2AirPumps = new List<CondOwner>();
		aActiveHeavyLiftRotors = new List<CondOwner>();
		if (ctRCSGasCans == null)
		{
			ctRCSGasCans = DataHandler.GetCondTrigger("TIsAirtightShipCan");
		}
		if (ctRCSGasInput == null)
		{
			ctRCSGasInput = DataHandler.GetCondTrigger("TIsRCSValidInput");
		}
		if (ctRCSClusterAudioEmitter == null)
		{
			ctRCSClusterAudioEmitter = DataHandler.GetCondTrigger("TIsRCSClusterAudioEmitter");
		}
		if (ctRCSDistroInstalled == null)
		{
			ctRCSDistroInstalled = DataHandler.GetCondTrigger("TIsRCSDistroInstalledOn");
		}
		if (ctDerelictSafe == null)
		{
			ctDerelictSafe = DataHandler.GetCondTrigger("TIsDerelictSalvage");
		}
		if (ctNavStationOn == null)
		{
			ctNavStationOn = DataHandler.GetCondTrigger("TIsStationNavOn");
		}
		if (ctRadarOn == null)
		{
			ctRadarOn = DataHandler.GetCondTrigger("TIsShipSensor");
		}
		if (ctXPDR == null)
		{
			ctXPDR = DataHandler.GetCondTrigger("TIsXPDRInstalled");
		}
		if (ctXPDRAntOn == null)
		{
			ctXPDRAntOn = DataHandler.GetCondTrigger("TIsXPDRAntOn");
		}
		if (ctDocksys == null)
		{
			ctDocksys = DataHandler.GetCondTrigger("TIsDockSysInstalled");
		}
		if (ctPortals == null)
		{
			ctPortals = DataHandler.GetCondTrigger("TIsPortalInstalled");
		}
		if (ctWearManeuver == null)
		{
			ctWearManeuver = DataHandler.GetCondTrigger("TIsDestructableManeuver");
		}
		if (ctWearManeuverTow == null)
		{
			ctWearManeuverTow = DataHandler.GetCondTrigger("TIsDestructableManeuverTow");
		}
		if (ctWearTime == null)
		{
			ctWearTime = DataHandler.GetCondTrigger("TIsDestructableWearTime");
		}
		if (ctSparkable == null)
		{
			ctSparkable = DataHandler.GetCondTrigger("TIsSparkable");
		}
		if (ctPilotSafe == null)
		{
			ctPilotSafe = DataHandler.GetCondTrigger("TIsHumanAwake");
		}
		if (ctFactionCO == null)
		{
			ctFactionCO = DataHandler.GetCondTrigger("TIsNotCarried");
		}
		if (ctPermitOKLG == null)
		{
			ctPermitOKLG = DataHandler.GetCondTrigger("TIsOKLGPermitValid");
		}
		if (ctTowBraceSecured == null)
		{
			ctTowBraceSecured = DataHandler.GetCondTrigger("TIsTowingBrace01InstalledSecure");
		}
		if (ctAirPump == null)
		{
			ctAirPump = DataHandler.GetCondTrigger("TIsAirPump02Installed");
		}
		if (ctO2Can == null)
		{
			ctO2Can = DataHandler.GetCondTrigger("TIsRTAO2Installed");
		}
		if (ctStabilizerActiveOn == null)
		{
			ctStabilizerActiveOn = DataHandler.GetCondTrigger("TIsStabilizerActive01NotOff");
		}
		if (ctHeavyLiftRotorsInstalled == null)
		{
			ctHeavyLiftRotorsInstalled = DataHandler.GetCondTrigger("TIsHeavyLiftRotorNotOff");
		}
		if (ctTutorialDerelict == null)
		{
			ctTutorialDerelict = DataHandler.GetCondTrigger("TIsTutorialDerelict");
		}
		if (ctWeaponInstalled == null)
		{
			ctWeaponInstalled = DataHandler.GetCondTrigger("TIsShipWeaponInstalled");
		}
		if (ctLootSpawner == null)
		{
			ctLootSpawner = DataHandler.GetCondTrigger("TIsLootSpawner");
		}
	}

	public void Destroy(bool isDespawning = true)
	{
		if (bDestroyed)
		{
			if (Classification != TypeClassification.Projectile || bDebugProjectileOutput)
			{
				Debug.Log("Ship " + strRegID + " already destroyed. Aborting.");
			}
			return;
		}
		if (!isDespawning)
		{
			if (IsStation() && ShipCO != null && !ShipCO.HasCond("IsEnvironmentEntity"))
			{
				Debug.LogWarning(StarSystem.fEpoch + " " + strRegID + " was destroyed!");
			}
			if (Classification == TypeClassification.SignalBeacon)
			{
				CrewSim.system.RemoveSignalBeacon(strRegID, objSS.vPos);
			}
		}
		aLog = null;
		_isDespawning = isDespawning;
		if (Classification != TypeClassification.Projectile || bDebugProjectileOutput)
		{
			Debug.Log("Destroying ship " + strRegID + ".");
		}
		if (CrewSim.system != null)
		{
			CrewSim.system.RemoveShip(this);
			CrewSim.system.dictProjectiles.Remove(strRegID);
		}
		AIShipManager.UnregisterShip(this);
		CrewSim.RemoveLoadedShip(this);
		bDestroyed = true;
		shipScanTarget = null;
		targetRegID = null;
		shipStationKeepingTarget = null;
		shipCombatTarget = null;
		shipUndock = null;
		if (ShipCO != null)
		{
			ShipCO.Destroy();
		}
		ShipCO = null;
		objSS.destroy();
		objSS = null;
		aDocked.Clear();
		CachedAllDockedShips = null;
		aProxCurrent.Clear();
		aProxCurrent = null;
		aProxIgnores.Clear();
		aProxIgnores = null;
		aTrackCurrent.Clear();
		aTrackCurrent = null;
		aTrackIgnores.Clear();
		aTrackIgnores = null;
		FloorPlan.Clear();
		FloorPlan = null;
		aFactions.Clear();
		aFactions = null;
		int num = 0;
		while (mapICOs.Count != 0)
		{
			foreach (CondOwner value in mapICOs.Values)
			{
				if (value.objCOParent != null)
				{
					num++;
					continue;
				}
				value.ValidateParent();
				CondOwner.CheckTrue(value.ship == this, "CO in mapICOs but not on ship");
				RemoveCO(value);
				CondOwner.CheckTrue(value.ship == null, "Unable to remove CO during ship destroy");
				value.ValidateParent();
				if (!isDespawning && value.IsHumanOrRobot && !value.bDestroyed)
				{
					value.Kill = true;
				}
				value.Destroy();
				value.ValidateParent();
				break;
			}
			if (num > 0 && num == mapICOs.Values.Count)
			{
				Debug.LogWarning("WARNING: Unable to destroy " + mapICOs.Values.Count + " orphaned COs while destroying ship " + strRegID);
				foreach (CondOwner value2 in mapICOs.Values)
				{
					string text = " - ";
					if (value2.objCOParent != null)
					{
						text += value2.objCOParent.strID;
					}
					Debug.Log("Orphan: " + value2.strName + " - " + value2.strID + " had parent " + value2.objCOParent?.ToString() + text);
				}
				break;
			}
			num = 0;
		}
		if (Comms != null)
		{
			Comms.Destroy();
		}
		Comms = null;
		if (DamageSystem != null)
		{
			DamageSystem.Destroy();
		}
		DamageSystem = null;
		ElectronicSystems = null;
		WeaponsSystem = null;
		foreach (WaypointShip aWP in aWPs)
		{
			aWP.Destroy();
		}
		aWPs.Clear();
		aWPs = null;
		foreach (Tile aTile in aTiles)
		{
			aTile.Destroy();
			if (aTile != null)
			{
				UnityEngine.Object.Destroy(aTile.gameObject);
			}
		}
		aTiles.Clear();
		aTiles = null;
		aPwrTiles.Clear();
		aPwrTiles = null;
		aPwrTilesOff.Clear();
		aPwrTilesOff = null;
		foreach (Room aRoom in aRooms)
		{
			aRoom.Destroy();
		}
		aRooms.Clear();
		aRooms = null;
		foreach (JsonZone value3 in mapZones.Values)
		{
			value3.Destroy();
		}
		mapZones.Clear();
		mapZones = null;
		foreach (Transform tfBG in tfBGs)
		{
			if (!(tfBG == null))
			{
				Item component = tfBG.GetComponent<Item>();
				if (component != null)
				{
					CrewSim.objInstance.ShowBlocksAndLights(component, bShow: false);
				}
			}
		}
		dictBGs.Clear();
		dictBGs = null;
		aRCSDistros.Clear();
		aRCSDistros = null;
		aRCSThrusters.Clear();
		aRCSThrusters = null;
		aActiveHeavyLiftRotors.Clear();
		aActiveHeavyLiftRotors = null;
		aDocksys.Clear();
		aDocksys = null;
		aO2AirPumps.Clear();
		aO2AirPumps = null;
		aPeople.Clear();
		aPeople = null;
		goTiles = null;
		tfBGs = null;
		mapICOs = null;
		vShipPos = Vector2.zero;
		nCols = 0;
		nRows = 0;
		UnityEngine.Object.DestroyImmediate(gameObject);
	}

	public void InitShip(bool bTemplateOnly, Loaded nLoad, string strRegIDNew = null)
	{
		if (nLoad <= nLoadState || json == null)
		{
			return;
		}
		_bDoneLoading = false;
		if (Comms == null)
		{
			Comms = new Comms(this, json.commData);
		}
		if (DamageSystem == null)
		{
			DamageSystem = new DamageSystem(this);
		}
		if (ElectronicSystems == null)
		{
			ElectronicSystems = new ElectronicSystems(this);
		}
		if (WeaponsSystem == null)
		{
			WeaponsSystem = new WeaponsSystem(this);
		}
		bNoCollisions = json.bNoCollisions;
		dLastScanTime = json.dLastScanTime;
		strAIDespawnedAt = json.strAIDespawnedAt;
		bLocalAuthority = json.bLocalAuthority;
		bRemove = json.bRemove;
		bAIShip = json.bAIShip;
		if (nLoad > Loaded.Shallow)
		{
			CrewSim.bPoolVisUpdates = true;
		}
		List<CondOwner> aLootSpawners = new List<CondOwner>();
		Dictionary<string, CondOwner> dictPlaceholders = new Dictionary<string, CondOwner>();
		Dictionary<int, JsonRoom> dictionary = new Dictionary<int, JsonRoom>();
		List<JsonItem> list = new List<JsonItem>();
		bool flag = false;
		if (nLoadState == Loaded.None)
		{
			if (nLoad == Loaded.Edit)
			{
				if (json.publicName != null)
				{
					publicName = json.publicName;
				}
				else
				{
					publicName = "$TEMPLATE";
				}
				if (json.origin != null)
				{
					origin = json.origin;
				}
				else
				{
					origin = "$TEMPLATE";
				}
				if (json.description != null)
				{
					description = json.description;
				}
			}
			else
			{
				if (json.origin != null)
				{
					origin = json.origin;
				}
				if (json.description != null)
				{
					description = json.description;
				}
				if (json.publicName == null || json.publicName == "" || json.publicName == "$TEMPLATE")
				{
					publicName = DataHandler.GetShipName();
				}
				else
				{
					publicName = json.publicName;
				}
			}
			if (json.make != null)
			{
				make = json.make;
			}
			if (json.model != null)
			{
				model = json.model;
			}
			if (json.year != null)
			{
				year = json.year;
			}
			if (json.designation != null)
			{
				designation = json.designation;
			}
			if (json.dimensions != null)
			{
				dimensions = json.dimensions;
			}
			if (json.aRating != null)
			{
				rating = json.aRating;
			}
			if (json.aProxCurrent != null)
			{
				aProxCurrent = json.aProxCurrent.ToList();
			}
			if (json.aProxIgnores != null)
			{
				aProxIgnores = json.aProxIgnores.ToList();
			}
			if (json.aTrackCurrent != null)
			{
				aTrackCurrent = json.aTrackCurrent.ToList();
			}
			if (json.aTrackIgnores != null)
			{
				aTrackIgnores = json.aTrackIgnores.ToList();
			}
			if (json.aFactions != null)
			{
				aFactions = CrewSim.system.GetFactions(json.aFactions);
			}
			if (json.aMarketConfigs != null)
			{
				MarketConfigs = json.aMarketConfigs.CloneShallow();
			}
			if (json.aLog != null)
			{
				aLog = new List<JsonShipLog>();
				JsonShipLog[] array = json.aLog;
				foreach (JsonShipLog jsonShipLog in array)
				{
					if (jsonShipLog == null)
					{
						Debug.LogWarning("null ship aLog entry detected!");
					}
					else
					{
						aLog.Add(jsonShipLog.Clone());
					}
				}
			}
			_ = json.vShipPos;
			vShipPos = json.vShipPos;
			if (json.aSecuredTowBraces != null)
			{
				aSecuredTowBraces = json.aSecuredTowBraces.CloneShallow();
			}
			Classification = json.ShipType;
			strLaw = json.strLaw;
			strParallax = json.strParallax;
			fShallowMass = json.fShallowMass;
			fShallowRCSRemass = json.fShallowRCSRemass;
			fShallowRCSRemassMax = json.fShallowRCSRemassMax;
			fShallowFusionRemain = json.fShallowFusionRemain;
			fFusionThrustMax = json.fFusionThrustMax;
			fFusionPelletMax = json.fFusionPelletMax;
			fEpochNextGrav = json.fEpochNextGrav;
			fLastQuotedPrice = json.fLastQuotedPrice;
			fBreakInMultiplier = json.fBreakInMultiplier;
			fRCSCount = json.nRCSCount;
			fShallowRotorStrength = json.fShallowRotorStrength;
			if (json.aDockingPorts != null)
			{
				aDockingPorts = json.aDockingPorts.ToList();
			}
			nRCSDistroCount = json.nRCSDistroCount;
			strPrimaryDockingPortID = json.strPrimaryDockingPortID;
			fAeroCoefficient = json.fAeroCoefficient;
			bFusionReactorRunning = json.bFusionTorch;
			strXPDR = json.strXPDR;
			bXPDRAntenna = json.bXPDRAntenna;
			bShipHidden = json.bShipHidden;
			bIsUnderConstruction = json.bIsUnderConstruction;
			if (json.nConstructionProgress > 0)
			{
				nConstructionProgress = json.nConstructionProgress;
			}
			strTemplateName = json.strTemplateName;
			nInitConstructionProgress = json.nInitConstructionProgress;
			nGridRotation = json.nGridRotation;
			if (nLoad >= Loaded.Shallow && json.aShallowPSpecs != null)
			{
				list.AddRange(json.aShallowPSpecs);
			}
			if (bTemplateOnly)
			{
				if (strRegIDNew == null)
				{
					strRegID = GenerateID();
				}
				else
				{
					strRegID = strRegIDNew;
				}
				bPrefill = true;
				bResetLocks = true;
				if (json != null)
				{
					bBreakInUsed = json.bBreakInUsed;
				}
			}
			else
			{
				strRegID = json.strRegID;
				bPrefill = json.bPrefill;
				bBreakInUsed = json.bBreakInUsed;
			}
			if (json.origin == "$TEMPLATE")
			{
				Loot loot = null;
				if (strRegID[0] != '*')
				{
					DataHandler.GetLoot("TXTShipOrigin" + strRegID[0]);
					flag = true;
				}
				if (loot == null)
				{
					loot = DataHandler.GetLoot("TXTShipOrigin");
				}
				if (loot != null)
				{
					List<string> lootNames = loot.GetLootNames();
					if (lootNames != null && lootNames.Count > 0)
					{
						origin = loot.GetLootNames()[0];
					}
					else
					{
						origin = DataHandler.GetString("SHIP_ORIGIN_UNKNOWN");
					}
				}
			}
			gameObject.name = strRegID;
			DMGStatus = json.DMGStatus;
		}
		if (flag || bDebugProjectileOutput)
		{
			Debug.Log("#Info# Loading ship " + strRegID + "; Requesting: " + nLoad.ToString() + "; Currently: " + nLoadState);
		}
		if (nLoad >= Loaded.Edit)
		{
			list.AddRange(json.aItems);
			gameObject.SetActive(value: true);
			nRCSDistroCount = 0;
			fRCSCount = 0f;
			aDockingPorts.Clear();
			LiftRotorsThrustStrength = -1f;
			aActiveHeavyLiftRotors.Clear();
			if (DMGStatus != Damage.Derelict)
			{
				fLastQuotedPrice = 0.0;
			}
			if (nConstructionProgress < 100 && fFirstVisit > 0.0)
			{
				List<JsonItem> list2 = Reconstruct();
				if (list2.Count > 0)
				{
					json.aRooms = null;
					SpawnItems(list2, bTemplateOnly: true, nLoad, ref dictPlaceholders, ref aLootSpawners);
					if (aLootSpawners != null && aLootSpawners.Count > 0)
					{
						DoLootSpawners(aLootSpawners);
					}
				}
			}
		}
		if (json.aCrew != null && nLoadState == Loaded.None && (!bTemplateOnly || DMGStatus != Damage.Derelict))
		{
			list.AddRange(json.aCrew);
			JsonItem[] aItems = json.aItems;
			foreach (JsonItem jsonItem in aItems)
			{
				if (jsonItem.ForceLoad())
				{
					list.Add(jsonItem);
				}
			}
		}
		if (json.aCOs != null)
		{
			JsonCondOwnerSave[] aCOs = json.aCOs;
			foreach (JsonCondOwnerSave jsonCondOwnerSave in aCOs)
			{
				DataHandler.dictCOSaves[jsonCondOwnerSave.strID] = jsonCondOwnerSave;
			}
			json.aCOs = null;
		}
		if (ShipCO == null)
		{
			string strName = ((bTemplateOnly || json.shipCO == null) ? strRegID : json.shipCO.strCondID);
			ShipCO = DataHandler.GetCondOwner("ShipCO", strName, null, bLoot: false, null, json.shipCO, null, gameObject.transform);
			ShipCO.ship = this;
			ShipCO.ClaimShip(strRegID);
		}
		SpawnItems(list, bTemplateOnly, nLoad, ref dictPlaceholders, ref aLootSpawners);
		if (!bTemplateOnly)
		{
			publicName = json.publicName;
			strRegID = json.strRegID;
			nCurrentWaypoint = json.nCurrentWaypoint;
			fTimeEngaged = json.fTimeEngaged;
			if (nLoadState != Loaded.Shallow)
			{
				objSS = new ShipSitu(json.objSS);
				if (objSS.NavData != null)
				{
					objSS.NavData.SetShip(this);
				}
				if (nLoadState == Loaded.None)
				{
					fWearManeuver = json.fWearManeuver;
					fWearAccrued = json.fWearAccrued;
					fAIPauseTimer = json.fAIPauseTimer;
					fAIDockingExpire = json.fAIDockingExpire;
				}
			}
			fLastVisit = json.fLastVisit;
			fFirstVisit = json.fFirstVisit;
			if (json.aWPs != null)
			{
				for (int j = 0; j < json.aWPs.Length; j++)
				{
					aWPs.Add(new WaypointShip(new ShipSitu(json.aWPs[j]), json.aWPTimes[j]));
				}
			}
			if (json.aRooms != null)
			{
				for (int k = 0; k < json.aRooms.Length; k++)
				{
					if (json.aRooms[k].aTiles != null)
					{
						JsonRoom jsonRoom = json.aRooms[k];
						for (int l = 0; l < jsonRoom.aTiles.Length; l++)
						{
							dictionary[jsonRoom.aTiles[l]] = jsonRoom;
						}
					}
				}
			}
			ApplyUniqueMapConditions();
		}
		else
		{
			ApplyUniqueMapConditions();
			List<CondOwner> cOs = GetCOs(null, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
			RectifyBrokenIDs(cOs);
			foreach (string item in MarketConfigs.Keys.ToList())
			{
				if (mapIDRemap.TryGetValue(item, out var value))
				{
					string value2 = MarketConfigs[item];
					MarketConfigs.Remove(item);
					MarketConfigs[value] = value2;
					MarketManager.TraderIDUpdated(strRegID, item, value);
				}
			}
			if (json.aDockingPorts != null)
			{
				List<Clearance> list3 = new List<Clearance>();
				foreach (KeyValuePair<string, Ship> dictShip in CrewSim.system.dictShips)
				{
					if (dictShip.Value != null && dictShip.Value.Comms != null && dictShip.Value.Comms.HasClearanceWithTarget(strRegID))
					{
						list3.Add(dictShip.Value.Comms.Clearance);
					}
				}
				string[] array2 = json.aDockingPorts;
				foreach (string text in array2)
				{
					if (!mapIDRemap.TryGetValue(text, out var value3))
					{
						continue;
					}
					if (strPrimaryDockingPortID == text)
					{
						strPrimaryDockingPortID = value3;
					}
					if (aSecuredTowBraces != null && aSecuredTowBraces.ContainsValue(text))
					{
						foreach (KeyValuePair<string, string> aSecuredTowBrace in aSecuredTowBraces)
						{
							if (!(aSecuredTowBrace.Value != text))
							{
								aSecuredTowBraces[aSecuredTowBrace.Key] = value3;
								break;
							}
						}
					}
					foreach (Clearance item2 in list3)
					{
						if (item2.DockID == text)
						{
							item2.DockID = value3;
						}
					}
					if (json.aDocked != null && json.aDocked.TryGetValue(text, out var value4))
					{
						json.aDocked.Remove(text);
						json.aDocked.Add(value3, value4);
					}
				}
				list3.Clear();
			}
		}
		if (nLoad > Loaded.Shallow)
		{
			if (!string.IsNullOrEmpty(strParallax))
			{
				CrewSim.system.SetParallax(strParallax);
			}
			SetZoneData(json.aZones);
			CreateRooms(dictionary);
			TileUtils.GetPoweredTiles(this);
			if (json.aBGXs != null && json.aBGYs != null && json.aBGNames != null)
			{
				for (int m = 0; m < json.aBGNames.Length && m < json.aBGYs.Length && m < json.aBGXs.Length; m++)
				{
					if (json.aBGNames[m] == null || json.aBGXs[m] == null || json.aBGYs[m] == null)
					{
						continue;
					}
					for (int n = 0; n < json.aBGXs[m].Length; n++)
					{
						float num = json.aBGXs[m][n];
						float num2 = json.aBGYs[m][n];
						if (BGItemFits(json.aBGNames[m], num, num2))
						{
							Item background = DataHandler.GetBackground(json.aBGNames[m]);
							Vector3 position = new Vector3(tfBGs.position.x, tfBGs.position.y, background.TF.position.z);
							position.x += num;
							position.y += num2;
							background.TF.position = position;
							BGItemAdd(background);
						}
					}
				}
			}
		}
		if (json.objSS == null || !json.objSS.bIsBO)
		{
			FloorPlan = SilhouetteUtility.GetFloorVectors(json.aItems);
		}
		if (Classification != TypeClassification.Asteroid && Classification != TypeClassification.SignalBeacon)
		{
			objSS.SetSize(SilhouetteUtility.GetSilhouetteLength(FloorPlan));
		}
		CrewSim.system.AddShip(this, CrewSim.system.GetShipOwner(strRegID));
		if (bTemplateOnly)
		{
			if (nLoad == Loaded.Edit)
			{
				foreach (CondOwner item3 in aLootSpawners)
				{
					item3.GetComponent<LootSpawner>().UpdateAppearance();
				}
			}
			else if (nLoad >= Loaded.Shallow)
			{
				DoLootSpawners(aLootSpawners);
			}
		}
		else
		{
			foreach (CondOwner item4 in aLootSpawners)
			{
				item4.GetComponent<LootSpawner>().UpdateAppearance();
				item4.Visible = false;
			}
			if (json.aPlaceholders != null)
			{
				JsonPlaceholder[] aPlaceholders = json.aPlaceholders;
				foreach (JsonPlaceholder jsonPlaceholder in aPlaceholders)
				{
					if (dictPlaceholders.ContainsKey(jsonPlaceholder.strName))
					{
						CondOwner condOwner = dictPlaceholders[jsonPlaceholder.strName];
						string strID = condOwner.strID;
						CondOwner condOwner2 = DataHandler.GetCondOwner(jsonPlaceholder.strActionCO);
						CondOwner condOwner3 = DataHandler.GetCondOwner(jsonPlaceholder.strInstalledCO);
						condOwner3.tf.position = condOwner.tf.position;
						condOwner3.Item.fLastRotation = condOwner.tf.rotation.eulerAngles.z;
						condOwner2.strPersistentCO = jsonPlaceholder.strPersistentCO;
						condOwner2.strPersistentCT = jsonPlaceholder.strPersistentCT;
						CondOwner cOPlaceholder = DataHandler.GetCOPlaceholder(condOwner3, condOwner2, jsonPlaceholder.strInstallIA);
						cOPlaceholder.jCOS = condOwner.jCOS;
						condOwner.jCOS = null;
						RemoveCO(condOwner);
						condOwner.Destroy();
						condOwner2.Destroy();
						condOwner3.Destroy();
						cOPlaceholder.strID = strID;
						AddCO(cOPlaceholder, bTiles: true);
					}
				}
			}
		}
		aLootSpawners.Clear();
		aLootSpawners = null;
		dictPlaceholders.Clear();
		dictPlaceholders = null;
		if (bPrefill && nLoad >= Loaded.Edit)
		{
			PreFillRooms();
			if (ctTutorialDerelict.Triggered(ShipCO))
			{
				SetupTutorialDerelict();
				DamageAllCOs(fBreakInMultiplier);
				ShipCO.ZeroCondAmount("IsTutorialDerelict");
			}
			else if (DMGStatus == Damage.Derelict || DMGStatus == Damage.Damaged || (DMGStatus == Damage.Used && bBreakInUsed))
			{
				BreakIn();
				if (fLastQuotedPrice == 0.0)
				{
					SetDerelictValue();
				}
				bBreakInUsed = false;
			}
			else if (DMGStatus == Damage.Used)
			{
				DamageAllCOs(0.33f);
				if (ShipCO.HasCond("IsVendorShip", isThreshold: false))
				{
					ShipCO.ZeroCondAmount("IsVendorShip");
					if (Reactor != null)
					{
						FusionIC component = Reactor.GetComponent<FusionIC>();
						if (component != null)
						{
							component.SetDerelict();
						}
					}
				}
			}
			bPrefill = false;
		}
		if (nLoad == Loaded.Full)
		{
			for (int num3 = aPeople.Count - 1; num3 >= 0; num3--)
			{
				CondOwner condOwner4 = aPeople[num3].MakeCondOwner(PersonSpec.StartShip.OLD, this);
				Pathfinder pathfinder = condOwner4.Pathfinder;
				Vector2 vector = new Vector2(condOwner4.tf.position.x, condOwner4.tf.position.y);
				pathfinder.tilCurrent = GetTileAtWorldCoords1(vector.x, vector.y, bAllowDocked: true);
				if (pathfinder.tilCurrent == null)
				{
					pathfinder.tilCurrent = GetCrewSpawnTile(condOwner4);
				}
				FaceAnim2.GetPNG(condOwner4);
				if (condOwner4.currentRoom == null && pathfinder.tilCurrent != null)
				{
					condOwner4.tf.position = pathfinder.tilCurrent.tf.position;
					condOwner4.gameObject.SetActive(value: true);
					condOwner4.Visible = true;
					if (condOwner4.HasTickers())
					{
						CrewSim.AddTicker(condOwner4);
					}
					List<CondOwner> cOs2 = condOwner4.GetCOs(bAllowLocked: true);
					if (cOs2 != null)
					{
						foreach (CondOwner item5 in cOs2)
						{
							if (item5 != null && item5.HasTickers())
							{
								CrewSim.AddTicker(item5);
							}
						}
					}
					condOwner4.currentRoom = pathfinder.tilCurrent.room;
					if (condOwner4.currentRoom != null)
					{
						condOwner4.currentRoom.AddToRoom(condOwner4);
					}
				}
			}
			List<CondOwner> list4 = mapICOs.Values.ToList();
			foreach (Room aRoom in aRooms)
			{
				list4.Add(aRoom.CO);
			}
			PostGameLoad(list4, nLoad);
		}
		else if (nLoad >= Loaded.Shallow)
		{
			List<CondOwner> aCOsLoaded = mapICOs.Values.ToList();
			PostGameLoad(aCOsLoaded, nLoad);
		}
		nLoadState = nLoad;
		bCheckRooms = false;
		bCheckPower = false;
		bCheckTargets = true;
		CheckAccruedWear();
		objSS.bGrounded = Classification == TypeClassification.GroundStation || Classification == TypeClassification.GroundStationUnfinished;
		UpdatePower();
		SilhouettePoints = SilhouetteUtility.GenerateVectorPoints(FloorPlan);
		if (strRegID.Split('|').Length > 1)
		{
			HideFromSystem = true;
			_subStation = true;
		}
		if (nLoad >= Loaded.Edit)
		{
			CrewSim.AddLoadedShip(this);
		}
		if (CrewSim.objInstance.FinishedLoading || nLoad > Loaded.Shallow)
		{
			InitDocking(nLoad);
		}
		switch (nLoad)
		{
		case Loaded.Full:
		{
			bool flag2 = true;
			if (bTemplateOnly)
			{
				SetFactions(aFactions, bRemoveOld: false);
			}
			else if (CrewSim.objInstance.FinishedLoading && ShipCO.GetCondAmount("StationMaintLvl") > 0.0)
			{
				flag2 = false;
				foreach (Room aRoom2 in aRooms)
				{
					aRoom2.CO.AddCondAmount("IsGasRequiresCleaning", 1.0);
				}
			}
			CrewSim.objInstance.workManager.ShowShipTasks(strRegID);
			UpdateRating();
			Debug.Log("#Info# " + strRegID + GetRatingString());
			VisualizeOverlays();
			ElectronicSystems.UpdateSensorStates();
			if (flag2 && json.aFires != null)
			{
				string[] array2 = json.aFires;
				foreach (string strCOID in array2)
				{
					CrewSim.vfxFire.AddFireCO(strCOID);
				}
			}
			break;
		}
		default:
			ElectronicSystems.AddRandomSensors();
			break;
		case Loaded.Edit:
			break;
		}
		_bDoneLoading = true;
	}

	public void InitDocking(Loaded nLoad)
	{
		if (json == null || (json.aDocked == null && (aDocked == null || aDocked.Count <= 0)))
		{
			return;
		}
		Dictionary<string, Ship> dictionary = new Dictionary<string, Ship>();
		if (json.aDocked != null)
		{
			foreach (KeyValuePair<string, string> item in json.aDocked)
			{
				if (!mapIDRemap.TryGetValue(item.Key, out var value))
				{
					value = item.Key;
				}
				string value2 = item.Value;
				Ship shipByRegID = CrewSim.system.GetShipByRegID(value2);
				if (shipByRegID != null && !dictionary.ContainsKey(value))
				{
					dictionary.Add(value, shipByRegID);
				}
			}
		}
		if (aDocked != null)
		{
			foreach (KeyValuePair<string, Ship> item2 in aDocked)
			{
				Ship value3 = item2.Value;
				if (value3 != null && !value3.bDestroyed && !dictionary.ContainsKey(item2.Key))
				{
					dictionary.Add(item2.Key, value3);
				}
			}
			aDocked.Clear();
		}
		foreach (KeyValuePair<string, Ship> item3 in dictionary)
		{
			item3.Value.objSS.UpdateTime(StarSystem.fEpoch);
			if (nLoad == Loaded.Full)
			{
				if (item3.Key.Contains("MP|"))
				{
					bool moorLoadedToIncoming = item3.Key.Contains("MP|I|");
					CrewSim.MoorShip(new DockingPortDTO(this, item3.Key), new DockingPortDTO(item3.Value, item3.Value.GetPortIdForDockedShip(strRegID)), moorLoadedToIncoming);
				}
				else
				{
					CrewSim.DockShip(this, item3.Value.strRegID, item3.Value.GetPortIdForDockedShip(strRegID), item3.Key);
				}
				continue;
			}
			string portIdForDockedShip = item3.Value.GetPortIdForDockedShip(strRegID);
			if (string.IsNullOrEmpty(portIdForDockedShip))
			{
				LogAdd("Skipped docking with " + item3.Value.strRegID + " missing port id! Docking port us: " + item3.Key);
				Debug.LogWarning("Skipped docking with " + item3.Value.strRegID + " missing port id! Docking port us: " + item3.Key);
				if (json.aDocked != null)
				{
					json.aDocked.TryRemoveValue(item3.Value.strRegID);
				}
			}
			else if (item3.Key.Contains("MP|"))
			{
				if (item3.Key.Contains("MP|I|"))
				{
					MoorTo(item3.Value, portIdForDockedShip, item3.Key);
				}
				else
				{
					item3.Value.MoorTo(this, item3.Key, portIdForDockedShip);
				}
			}
			else
			{
				Dock(item3.Value, bSyncOnly: true, portIdForDockedShip, item3.Key);
				item3.Value.Dock(this, bSyncOnly: true, item3.Key, portIdForDockedShip);
			}
		}
	}

	private void ApplyUniqueMapConditions()
	{
		if (json.aUniques == null)
		{
			return;
		}
		CondOwner value = null;
		JsonShipUniques[] aUniques = json.aUniques;
		foreach (JsonShipUniques jsonShipUniques in aUniques)
		{
			if (mapIDRemap.ContainsKey(jsonShipUniques.strCOID))
			{
				if (DataHandler.mapCOs.TryGetValue(mapIDRemap[jsonShipUniques.strCOID], out value) && !(value.strName == "SysLootSpawner") && jsonShipUniques.aConds != null)
				{
					for (int j = 0; j < jsonShipUniques.aConds.Length; j++)
					{
						DataHandler.CreateSimpleConditionFromString(jsonShipUniques.aConds[j]);
						bool bFreezeConds = value.bFreezeConds;
						value.bFreezeConds = false;
						value.AddCondAmount(jsonShipUniques.aConds[j], 1.0);
						value.bFreezeConds = bFreezeConds;
						CrewSimTut.UniqueToStrID.TryAdd(jsonShipUniques.aConds[j], value.strID);
					}
					jsonShipUniques.strCOID = value.strID;
				}
			}
			else if (DataHandler.mapCOs.ContainsKey(jsonShipUniques.strCOID) && DataHandler.mapCOs.TryGetValue(jsonShipUniques.strCOID, out value) && !(value.strName == "SysLootSpawner") && jsonShipUniques.aConds != null)
			{
				for (int k = 0; k < jsonShipUniques.aConds.Length; k++)
				{
					DataHandler.CreateSimpleConditionFromString(jsonShipUniques.aConds[k]);
					bool bFreezeConds2 = value.bFreezeConds;
					value.bFreezeConds = false;
					value.AddCondAmount(jsonShipUniques.aConds[k], 1.0);
					value.bFreezeConds = bFreezeConds2;
					CrewSimTut.UniqueToStrID.TryAdd(jsonShipUniques.aConds[k], value.strID);
				}
				jsonShipUniques.strCOID = value.strID;
			}
		}
	}

	private void DoLootSpawners(List<CondOwner> aLootSpawners)
	{
		foreach (CondOwner aLootSpawner in aLootSpawners)
		{
			int result = 1;
			if (!aLootSpawner.mapGUIPropMaps.ContainsKey("Panel A") || !aLootSpawner.mapGUIPropMaps["Panel A"].ContainsKey("strCount"))
			{
				Debug.LogError("ERROR: Ship " + json.strName + " has bad loot spawner at " + aLootSpawner.tf.position);
				continue;
			}
			int.TryParse(aLootSpawner.mapGUIPropMaps["Panel A"]["strCount"], out result);
			aLootSpawner.Visible = false;
			if (result != 0)
			{
				aLootSpawner.GetComponent<LootSpawner>().DoLoot(this);
				aLootSpawner.mapGUIPropMaps["Panel A"]["strCount"] = "-1";
				if (CrewSim.system.GetShipOwner(strRegID) == "UNREGISTERED" && aPeople.Count > 0)
				{
					CrewSim.system.RegisterShipOwner(strRegID, aPeople[0].FullName);
					JsonFaction faction = CrewSim.system.GetFaction(aPeople[0].FullName);
					SetFactions(new List<JsonFaction> { faction }, bRemoveOld: false);
				}
			}
		}
	}

	private void SetupTutorialDerelict()
	{
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsPermitOKLGSalvage");
		CondOwner cOFirstOccurrence = GetCOFirstOccurrence(condTrigger, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		if (cOFirstOccurrence != null)
		{
			cOFirstOccurrence.SetCondAmount("IsHoursLeft", 2.0);
		}
		CondTrigger condTrigger2 = DataHandler.GetCondTrigger("TIsRackInstalled");
		CondOwner cOFirstOccurrence2 = GetCOFirstOccurrence(condTrigger2, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		if (cOFirstOccurrence2 == null)
		{
			Debug.LogWarning("Tutorial: Could not spawn equipment, container missing");
		}
		else
		{
			if (!CrewSim.coPlayer)
			{
				return;
			}
			Ship ship = CrewSim.GetSelectedCrew().ship;
			CondTrigger condTrigger3 = DataHandler.GetCondTrigger("TIsNotInstalled");
			List<string> lootNames = DataHandler.GetLoot("TutorialDerelictEquipment").GetLootNames();
			foreach (CondOwner cO in ship.GetCOs(condTrigger3, bSubObjects: true, bAllowDocked: false, bAllowLocked: false))
			{
				if (cO == null)
				{
					continue;
				}
				for (int num = lootNames.Count - 1; num >= 0; num--)
				{
					if (!(cO.strName != lootNames[num]))
					{
						lootNames.RemoveAt(num);
						break;
					}
				}
			}
			foreach (string item in lootNames)
			{
				CondOwner condOwner = DataHandler.GetCondOwner(item);
				if (condOwner == null)
				{
					Debug.LogWarning("Tutorial: Could not spawn " + item);
				}
				else
				{
					cOFirstOccurrence2.AddCO(condOwner, bEquip: false, bOverflow: true, bIgnoreLocks: true);
				}
			}
		}
	}

	private void RectifyBrokenIDs(List<CondOwner> aCOs)
	{
		if (aCOs == null)
		{
			return;
		}
		foreach (CondOwner aCO in aCOs)
		{
			if (aCO == null)
			{
				continue;
			}
			if (aCO.HasCond("IsRoom") && aCO.gameObject != null)
			{
				RemoveCO(aCO);
				UnityEngine.Object.Destroy(aCO.gameObject);
			}
			else
			{
				if (aCO.mapGUIPropMaps == null)
				{
					continue;
				}
				foreach (Dictionary<string, string> value4 in aCO.mapGUIPropMaps.Values)
				{
					if (value4 == null)
					{
						continue;
					}
					List<string> list = new List<string>();
					foreach (KeyValuePair<string, string> item2 in value4)
					{
						if (item2.Value != null && mapIDRemap.ContainsKey(item2.Value))
						{
							string value = item2.Value;
							string item = mapIDRemap[value];
							list.Add(item2.Key);
							list.Add(item);
						}
					}
					for (int i = 0; i < list.Count; i += 2)
					{
						value4[list[i]] = list[i + 1];
					}
					list.Clear();
					list = null;
				}
				Dictionary<string, string> value2 = new Dictionary<string, string>();
				if (!aCO.mapGUIPropMaps.TryGetValue("Electrical", out value2))
				{
					continue;
				}
				string value3 = null;
				string[] array2;
				if (value2.TryGetValue("inputConnections", out value3))
				{
					string[] array = value3.Split(',');
					value3 = "";
					bool flag = false;
					array2 = array;
					foreach (string text in array2)
					{
						if (!(text == "") && text != null)
						{
							ElectricalConnection electricalConnection = ElectricalConnection.FromString(text);
							if (mapIDRemap.ContainsKey(electricalConnection.originID))
							{
								electricalConnection.originID = mapIDRemap[electricalConnection.originID];
							}
							if (flag)
							{
								value3 += ",";
							}
							else
							{
								flag = true;
							}
							value3 += electricalConnection.ToString();
						}
					}
					value2["inputConnections"] = value3;
				}
				value3 = null;
				if (!value2.TryGetValue("outputConnections", out value3))
				{
					continue;
				}
				string[] array3 = value3.Split(',');
				value3 = "";
				bool flag2 = false;
				array2 = array3;
				foreach (string text2 in array2)
				{
					if (!(text2 == "") && text2 != null)
					{
						ElectricalConnection electricalConnection2 = ElectricalConnection.FromString(text2);
						if (mapIDRemap.ContainsKey(electricalConnection2.originID))
						{
							electricalConnection2.originID = mapIDRemap[electricalConnection2.originID];
						}
						if (flag2)
						{
							value3 += ",";
						}
						else
						{
							flag2 = true;
						}
						value3 += electricalConnection2.ToString();
					}
				}
				value2["outputConnections"] = value3;
			}
		}
	}

	private bool IsItemDestroyed(JsonItem objItem)
	{
		double? condAmountOverride = objItem.GetCondAmountOverride("StatDamage");
		if (condAmountOverride.HasValue)
		{
			DataCO dataCO = DataHandler.GetDataCO(objItem.strName);
			if (dataCO == null)
			{
				Debug.LogWarning("Could not find DataCo: " + objItem.strName);
				return false;
			}
			double maxHealth = dataCO.GetMaxHealth();
			if (condAmountOverride >= maxHealth && !dataCO.HasCond("IsDockSys"))
			{
				string[] obj = new string[8]
				{
					"Fully damaged; Skipped loading: ",
					objItem.strName,
					" on ship: ",
					strRegID,
					" maxH: ",
					maxHealth.ToString(),
					" vs ",
					null
				};
				double? num = condAmountOverride;
				obj[7] = num.ToString();
				Debug.Log(string.Concat(obj));
				return true;
			}
		}
		return false;
	}

	private void SpawnItems(List<JsonItem> aItemsPlusCrew, bool bTemplateOnly, Loaded nLoad, ref Dictionary<string, CondOwner> dictPlaceholders, ref List<CondOwner> aLootSpawners)
	{
		GameObject gameObject = null;
		CondOwner value = null;
		CondOwner condOwner = null;
		List<JsonItem> list = new List<JsonItem>();
		Dictionary<string, JsonItem> itemById = (from jsonItem2 in aItemsPlusCrew
			group jsonItem2 by jsonItem2.strID into x
			select x.First()).ToDictionary((JsonItem jsonItem2) => jsonItem2.strID);
		HashSet<string> hashSet = new HashSet<string>();
		foreach (JsonItem item2 in aItemsPlusCrew)
		{
			if (item2.aCondOverrides != null && !string.IsNullOrEmpty(item2.strParentID))
			{
				hashSet.Add(item2.strID);
				string item = FindRootParent(item2, itemById);
				hashSet.Add(item);
			}
		}
		foreach (JsonItem item3 in aItemsPlusCrew)
		{
			if (DataHandler.mapCOs.ContainsKey(item3.strID))
			{
				continue;
			}
			if (!bTemplateOnly && !DataHandler.dictCOSaves.ContainsKey(item3.strID) && !item3.strID.Contains("MP|"))
			{
				Debug.LogWarning("ERROR: Trying to load a CO (" + item3.strName + ") with missing save data for ship: " + strRegID + ": " + item3.strID + ". Skipping.");
			}
			else if (item3.strParentID != null || item3.strSlotParentID != null)
			{
				if (bTemplateOnly && hashSet.Contains(item3.strID))
				{
					list.Add(item3);
				}
				else if (!bTemplateOnly || item3.ForceLoad())
				{
					list.Add(item3);
				}
			}
			else
			{
				if (IsItemDestroyed(item3))
				{
					continue;
				}
				string text = item3.strID;
				bool flag = text?.Contains("MP|") ?? false;
				if (bTemplateOnly && !CrewSim.bShipEdit && !flag)
				{
					text = null;
				}
				bool bLoot = bTemplateOnly && !hashSet.Contains(item3.strID);
				gameObject = CreatePart(item3, text, bLoot);
				if (!(gameObject == null))
				{
					value = gameObject.GetComponent<CondOwner>();
					if (bTemplateOnly)
					{
						mapIDRemap[item3.strID] = value.strID;
					}
					bool bTiles = nLoad > Loaded.Shallow;
					if (value.mapGUIPropMaps != null && value.mapGUIPropMaps.ContainsKey(GUITradeBase.ASYNCIDENTIFIER))
					{
						bTiles = false;
						value.mapGUIPropMaps.Remove(GUITradeBase.ASYNCIDENTIFIER);
					}
					bool flag2 = value.HasCond("IsPlaceholder");
					if (!flag2 || aTiles.Count > 0)
					{
						AddCO(value, bTiles, flag2);
					}
					if (value.HasCond("IsLootSpawner"))
					{
						aLootSpawners.Add(value);
						value.ClaimShip(strRegID);
					}
					else if (flag2)
					{
						dictPlaceholders[value.strID] = value;
					}
					item3.ApplyOverrideCondsToCO(value);
				}
			}
		}
		int num = -1;
		int num2 = -1;
		while (list.Count > 0)
		{
			if (num2 < 0)
			{
				if (num == 0)
				{
					Debug.Log("WARNING: " + list.Count + " unprocessed sub items on ship " + strRegID);
					break;
				}
				num2 = list.Count - 1;
				num = 0;
			}
			JsonItem jsonItem = list[num2];
			num2--;
			string text2 = jsonItem.strParentID;
			if (text2 == null)
			{
				text2 = jsonItem.strSlotParentID;
			}
			if (mapICOs.ContainsKey(text2))
			{
				mapICOs.TryGetValue(text2, out value);
			}
			else
			{
				if (!mapIDRemap.ContainsKey(text2))
				{
					continue;
				}
				mapIDRemap.TryGetValue(text2, out var value2);
				mapICOs.TryGetValue(value2, out value);
				if (!mapICOs.TryGetValue(value2, out value) || value == null)
				{
					Debug.Log("WARNING: Failed to find parent, ID: " + text2 + " for item " + jsonItem.strID);
					continue;
				}
			}
			bool flag3 = jsonItem.ForceLoad() || value.pspec != null;
			if (IsItemDestroyed(jsonItem))
			{
				list.Remove(jsonItem);
				continue;
			}
			string strIDTemp = jsonItem.strID;
			if (bTemplateOnly && !flag3 && !CrewSim.bShipEdit)
			{
				strIDTemp = null;
			}
			gameObject = CreatePart(jsonItem, strIDTemp, bTemplateOnly);
			if (gameObject == null)
			{
				continue;
			}
			condOwner = gameObject.GetComponent<CondOwner>();
			if (bTemplateOnly)
			{
				mapIDRemap[jsonItem.strID] = condOwner.strID;
			}
			condOwner.tf.localPosition = new Vector3(value.tf.position.x, value.tf.position.y, Container.fZSubOffset);
			bool flag4 = true;
			if (condOwner.mapGUIPropMaps != null && condOwner.mapGUIPropMaps.ContainsKey(GUITradeBase.ASYNCIDENTIFIER))
			{
				condOwner.mapGUIPropMaps.Remove(GUITradeBase.ASYNCIDENTIFIER);
			}
			if (jsonItem.strSlotParentID != null)
			{
				if (value.compSlots == null)
				{
					Debug.LogError("ERROR: Attempting to slot " + condOwner.strCODef + " - " + condOwner.strID + " into parent with no slot: " + value.strCODef + " - " + value.strID);
					flag4 = false;
				}
				else if (condOwner.jCOS == null)
				{
					Debug.LogError("ERROR: Attempting to slot " + condOwner.strCODef + " - " + condOwner.strID + " but it has no jCOS data!");
					flag4 = false;
				}
				else if (!value.compSlots.SlotItem(condOwner.jCOS.strSlotName, condOwner))
				{
					continue;
				}
			}
			else if (value.objContainer != null && !value.objContainer.Contains(condOwner))
			{
				bool bAllowStacking = value.objContainer.bAllowStacking;
				value.objContainer.bAllowStacking = false;
				value.objContainer.AddCOSimple(condOwner, condOwner.pairInventoryXY);
				value.objContainer.bAllowStacking = bAllowStacking;
			}
			if (flag4)
			{
				mapICOs[condOwner.strID] = condOwner;
			}
			list.Remove(jsonItem);
			jsonItem.ApplyOverrideCondsToCO(condOwner);
			num++;
		}
	}

	private string FindRootParent(JsonItem item, Dictionary<string, JsonItem> itemById)
	{
		while (!string.IsNullOrEmpty(item.strParentID) && itemById.ContainsKey(item.strParentID))
		{
			item = itemById[item.strParentID];
		}
		return item.strID;
	}

	public void SyncFuel()
	{
		double rCSRemain = GetRCSRemain();
		if (rCSRemain > fShallowRCSRemass)
		{
			RemoveGasMass(Mathf.Abs((float)fShallowRCSRemass - (float)rCSRemain));
		}
	}

	private void AddMarketActorConfigToShip(CondOwner marketActorCO)
	{
		if (!(marketActorCO == null))
		{
			string marketConfig = MarketActor.GetMarketConfig(marketActorCO);
			if (!string.IsNullOrEmpty(marketConfig))
			{
				MarketConfigs[marketActorCO.strID] = marketConfig;
			}
		}
	}

	private void RemoveMarketActorConfigFromShip(CondOwner marketActorCO)
	{
		if (!(marketActorCO == null) && MarketConfigs.ContainsKey(marketActorCO.strID))
		{
			MarketConfigs.Remove(marketActorCO.strID);
		}
	}

	public double CalculateRCSFuelConsumption(double dVdiff)
	{
		double num = dVdiff * (double)fRCSCount * 0.7279999852180481 / RCSAccelMax;
		num *= fFuelEfficiencyMod;
		if (!(num < 0.01))
		{
			return num;
		}
		return 0.0;
	}

	public double CalculateRCSFuelConsumption(double dVdiff, double cachedAccelMax)
	{
		double num = dVdiff * (double)fRCSCount * 0.7279999852180481 / cachedAccelMax;
		num *= fFuelEfficiencyMod;
		if (!(num < 0.01))
		{
			return num;
		}
		return 0.0;
	}

	public double CalculateTorchFuelConsumption(double dVdiff, float fLimiter)
	{
		double num = dVdiff / (double)GetMaxTorchThrust(fLimiter);
		num *= fFuelEfficiencyMod;
		if (!(num < 0.01))
		{
			return num;
		}
		return 0.0;
	}

	protected void SetZoneData(JsonZone[] aZones)
	{
		if (aZones == null || aTiles.Count == 0)
		{
			return;
		}
		foreach (JsonZone jsonZone in aZones)
		{
			JsonZone jsonZone2 = jsonZone.Clone();
			jsonZone2.strRegID = strRegID;
			List<Tile> list = new List<Tile>();
			for (int j = 0; j < jsonZone2.aTiles.Length; j++)
			{
				int num = jsonZone2.aTiles[j];
				if (num < aTiles.Count)
				{
					if (aTiles[num] != null)
					{
						list.Add(aTiles[num]);
					}
					continue;
				}
				Debug.LogWarning("Zone tile index was bigger than available tiles on ship, Ship: " + strRegID + " Zonename: " + jsonZone2.strName);
				return;
			}
			foreach (Tile item in list)
			{
				item.SetZone(jsonZone2);
			}
			mapZones[jsonZone.strName] = jsonZone2;
		}
	}

	private void PostGameLoad(List<CondOwner> aCOsLoaded, Loaded nLoad)
	{
		foreach (CondOwner item in aCOsLoaded)
		{
			item.PostGameLoad(nLoad);
		}
		foreach (CondOwner item2 in aCOsLoaded)
		{
			item2.bFreezeConds = false;
			item2.bFreezeCondRules = false;
			if (item2.Company != null)
			{
				item2.ShiftChange(item2.Company.GetShift(StarSystem.nUTCHour, item2), bSilent: true);
			}
			if (nLoad == Loaded.Full)
			{
				item2.UpdateAppearance();
			}
		}
		if (ShipCO != null)
		{
			ShipCO.PostGameLoad(nLoad);
			ShipCO.bFreezeConds = false;
			ShipCO.bFreezeCondRules = false;
		}
		if (nLoad == Loaded.Full)
		{
			UpdateGravAndAtmo();
		}
		if (nLoad < Loaded.Edit)
		{
			return;
		}
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsFitContainerSOC");
		foreach (CondOwner cO in GetCOs(condTrigger, bSubObjects: false, bAllowDocked: false, bAllowLocked: false))
		{
			cO.RemoveFromCurrentHome(bForce: true);
			cO.Destroy();
		}
	}

	public void PostUpdate()
	{
		if (nLoadState < Loaded.Edit)
		{
			return;
		}
		if (Reactor == null || !Reactor.HasCond("IsReadyFusion"))
		{
			if (bFusionReactorRunning)
			{
				bChangedStatus = true;
			}
			bFusionReactorRunning = false;
			SetThrust(0.0);
		}
		WeaponsSystem.CheckReload();
	}

	public void UpdateGravAndAtmo()
	{
		Vector2 ptGrav = default(Vector2);
		BodyOrbit boClosest = null;
		BodyOrbit greatestGravBO = CrewSim.system.GetGreatestGravBO(objSS, StarSystem.fEpoch, ref ptGrav, ref boClosest);
		UpdateGravAndAtmo(greatestGravBO, boClosest, Vector2.zero);
	}

	public void UpdateGravAndAtmo(BodyOrbit boGrav, BodyOrbit boAtmo, Vector2 ptPORGrav)
	{
		if (boGrav == null || StarSystem.fEpoch - _lastAtmoUpdateTime < 0.33000001311302185)
		{
			return;
		}
		if (boAtmo == null)
		{
			boAtmo = boGrav;
		}
		_lastAtmoUpdateTime = StarSystem.fEpoch;
		double num = (double)objSS.GetRadiusAU() + objSS.GetDistance(boAtmo.dXReal, boAtmo.dYReal);
		fVisibilityRangeMod = 1f;
		if (num <= boAtmo.GravRadius && num > boAtmo.fParallaxRadius)
		{
			float t = Mathf.InverseLerp((float)boAtmo.fParallaxRadius, (float)boAtmo.GravRadius, (float)num);
			fVisibilityRangeMod = Mathf.Lerp((float)boAtmo.fVisibilityRangeMod, (float)boAtmo.fVisibilityRangeModGrav, t);
		}
		else if (num <= boAtmo.fParallaxRadius)
		{
			fVisibilityRangeMod = (float)boAtmo.fVisibilityRangeMod;
		}
		if (LoadState != Loaded.Full || aTiles.Count == 0)
		{
			return;
		}
		double distanceToBO = (double)objSS.GetRadiusAU() + objSS.GetDistance(boGrav.dXReal, boGrav.dYReal);
		Tile.GravField gravField = Tile.SetTileGravitationalForces(boGrav, distanceToBO);
		if (gravField > Tile.GravField.None)
		{
			TileGravWarnPlayer(gravField);
		}
		JsonAtmosphere atmosphereAtDistance = boAtmo.GetAtmosphereAtDistance(num);
		foreach (Room aRoom in aRooms)
		{
			aRoom.SyncAtmoVoid(atmosphereAtDistance);
		}
		bool flag = ptPORGrav.x == 0f && ptPORGrav.y == 0f;
		if (atmosphereAtDistance.fMicrometeoroidChance > 0f && !flag)
		{
			float num2 = MathUtils.Rand(0f, 1f, MathUtils.RandType.Flat);
			Point point = boAtmo.vVel - objSS.vVel;
			float fMult = Mathf.Max((float)(MathUtils.GetMagnitude(point.X, point.Y) / 5.013440329548757E-09), 0.5f);
			float fMicrometeoroidChance = atmosphereAtDistance.fMicrometeoroidChance;
			if (num2 < fMicrometeoroidChance)
			{
				StarSystem.SpawnMicroMeteoroid(this, fMult, resetTimeScale: true);
			}
		}
		CalculateLiftDrag(ptPORGrav);
		CheckRoomPressure();
	}

	private void CalculateLiftDrag(Vector2 ptPORGrav)
	{
		if (ptPORGrav.x != 0f || ptPORGrav.y != 0f || objSS.vAccLift.x != 0f || objSS.vAccLift.y != 0f)
		{
			float num = ((fAeroCoefficient == 0f) ? 1f : fAeroCoefficient);
			double liftCoefficient = (double)num / Mass;
			double num2 = (double)(nCols + nRows) * 0.32 / 2.0;
			if (LoadState <= Loaded.Shallow && json != null)
			{
				num2 = (double)(json.nCols + json.nRows) * 0.32 / 2.0;
			}
			float num3 = Mathf.Lerp(3f, 15f, (float)(num2 - 3.0) / 50f);
			double dragCoeffFront = num2 * (double)num3 / Math.Max(1.0, num / 100f);
			objSS.CalculateLiftDrag(liftCoefficient, dragCoeffFront, num2 * (double)num3, Mass, ptPORGrav);
		}
	}

	public void TileGravWarnPlayer(Tile.GravField warningLvl)
	{
		if (IsStation() || IsStationHidden())
		{
			return;
		}
		CondOwner condOwner = aNavs.FirstOrDefault();
		if (!(condOwner == null))
		{
			string strDisplayName = "";
			switch (warningLvl)
			{
			case Tile.GravField.NoneToWeakTransition:
				strDisplayName = DataHandler.GetString("OBJV_GRAV_NONE_TO_WEAK");
				break;
			case Tile.GravField.WeakToStrongTransition:
				strDisplayName = DataHandler.GetString("OBJV_GRAV_WEAK_TO_STRONG");
				break;
			case Tile.GravField.StrongToWeakTransition:
				strDisplayName = DataHandler.GetString("OBJV_GRAV_STRONG_TO_WEAK");
				break;
			case Tile.GravField.WeakToNoneTransition:
				strDisplayName = DataHandler.GetString("OBJV_GRAV_WEAK_TO_NONE");
				break;
			}
			AlarmObjective objective = new AlarmObjective(AlarmType.nav_gravitation, condOwner, strDisplayName);
			MonoSingleton<ObjectiveTracker>.Instance.AddObjective(objective);
		}
	}

	private void PreFillRooms()
	{
		foreach (Room aRoom in aRooms)
		{
			GasContainer gasContainer = aRoom.CO.GasContainer;
			double num = 297.0;
			double num2 = (aRoom.Void ? 0.0 : aRoom.CO.GetCondAmount("StatVolume"));
			double value = 22.0 * num2 / 0.008314000442624092 / num;
			gasContainer.mapDGasMols["StatGasMolO2"] = value;
			if (gasContainer.mapGasMols1.ContainsKey("StatGasMolO2"))
			{
				gasContainer.mapDGasMols["StatGasMolO2"] -= gasContainer.mapGasMols1["StatGasMolO2"];
			}
			value = 80.0 * num2 / 0.008314000442624092 / num;
			gasContainer.mapDGasMols["StatGasMolN2"] = value;
			if (gasContainer.mapGasMols1.ContainsKey("StatGasMolN2"))
			{
				gasContainer.mapDGasMols["StatGasMolN2"] -= gasContainer.mapGasMols1["StatGasMolN2"];
			}
			if (aRoom.Void)
			{
				gasContainer.fDGasTemp = 2.725480079650879 - gasContainer.fDGasTemp;
			}
			else
			{
				gasContainer.fDGasTemp = num - gasContainer.fDGasTemp;
			}
			if (double.IsNaN(gasContainer.fDGasTemp))
			{
				Debug.Log("fDGasTemp NaN");
			}
		}
	}

	public List<JsonShipLog> LogGet()
	{
		if (aLog == null)
		{
			aLog = new List<JsonShipLog>();
		}
		return aLog;
	}

	public void LogAdd(string strEntry, double fEpoch = 0.0, bool bShowEpoch = false)
	{
		if (!_bDoneLoading || string.IsNullOrEmpty(strEntry))
		{
			return;
		}
		if (aLog == null)
		{
			aLog = new List<JsonShipLog>();
		}
		JsonShipLog jsonShipLog = aLog.LastOrDefault();
		if (jsonShipLog != null && jsonShipLog.strEntry == strEntry)
		{
			jsonShipLog.fEpoch = fEpoch;
			jsonShipLog.nCount++;
			return;
		}
		JsonShipLog jsonShipLog2 = new JsonShipLog();
		jsonShipLog2.strEntry = strEntry;
		jsonShipLog2.fEpoch = fEpoch;
		jsonShipLog2.bShowEpoch = bShowEpoch;
		jsonShipLog2.nCount = 1;
		aLog.Add(jsonShipLog2);
		int num = 1000;
		if (aLog.Count > num)
		{
			aLog.RemoveRange(0, aLog.Count - num);
		}
	}

	public List<JsonShipLog> LogGetHeader()
	{
		List<JsonShipLog> list = new List<JsonShipLog>();
		int result = 0;
		if (!int.TryParse(year, out result))
		{
			result = MathUtils.GetYearFromS(StarSystem.fEpoch) - 1;
			year = result.ToString();
		}
		double dfAmount = (double)((float)result * 31556926f) + MathUtils.Rand(0.0, 31556926.0, MathUtils.RandType.Flat);
		list.Add(JsonShipLog.Make("Vessel Name: " + publicName));
		list.Add(JsonShipLog.Make("REGID: " + strRegID, 1.0));
		list.Add(JsonShipLog.Make("Date of Construction: " + MathUtils.GetUTCFromS(dfAmount), 2.0));
		list.Add(JsonShipLog.Make("Make: " + make, 3.0));
		list.Add(JsonShipLog.Make("Model: " + model, 4.0));
		list.Add(JsonShipLog.Make("Homeport: " + origin, 5.0));
		list.Add(JsonShipLog.Make("Designation: " + designation, 6.0));
		list.Add(JsonShipLog.Make("Total Mass: " + Mass.ToString("N0") + " kg", 7.0));
		list.Add(JsonShipLog.Make("-- -- --", 8.0));
		CondTrigger objCondTrig = new CondTrigger("PIN Locked Doors", new string[1] { "IsLockPIN" }, new string[0], new string[0], new string[0]);
		foreach (CondOwner item in GetICOs1(objCondTrig, bSubObjects: false, bAllowDocked: false, bAllowLocked: true))
		{
			Dictionary<string, string> value = null;
			item.mapGUIPropMaps.TryGetValue("Panel A", out value);
			if (value != null && value.ContainsKey("strPIN"))
			{
				string text = item.strNameFriendly + DataHandler.GetString("GUI_NAV_LOGS_PIN");
				text += value["strPIN"];
				list.Add(JsonShipLog.Make(text, 20.0));
			}
		}
		return list;
	}

	public void Sparks()
	{
		if (nLoadState < Loaded.Edit || CrewSim.Paused || DataHandler.GetUserSettings().nFlickerAmount < 0)
		{
			return;
		}
		float num = 0.02f;
		num += num * CrewSim.TimeElapsedScaled();
		num *= (float)mapICOs.Count / 1200f;
		if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) > (double)num)
		{
			return;
		}
		ctSparkable.logReason = false;
		if (aSparkables == null || aSparkables.Count == 0)
		{
			aSparkables = BuildSparkables();
		}
		while (aSparkables.Count > 0)
		{
			CondOwner condOwner = aSparkables[0];
			aSparkables.RemoveAt(0);
			if (condOwner == null || !ctSparkable.Triggered(condOwner))
			{
				continue;
			}
			Tile tileAtWorldCoords = GetTileAtWorldCoords1(condOwner.tf.position.x, condOwner.tf.position.y, bAllowDocked: false);
			if (!(tileAtWorldCoords == null) && tileAtWorldCoords.aConnectedPowerCOs.Count != 0)
			{
				double num2 = 1.0 - condOwner.GetDamageState();
				if (!(num2 < 0.5))
				{
					CrewSim.vfxSparks.AddSparkAt(condOwner.tf.position);
					float num3 = 400f;
					num2 = Mathf.Min(0.01f, Convert.ToSingle(condOwner.GetCondAmount("StatDamageMax")) / (num3 * 2f));
					condOwner.AddCondAmount("StatDamage", num2);
				}
			}
			break;
		}
	}

	private List<CondOwner> BuildSparkables()
	{
		List<CondOwner> cOs = GetCOs(ctSparkable, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		List<CondOwner> list = new List<CondOwner>();
		for (int i = 0; i < cOs.Count; i++)
		{
			int index = UnityEngine.Random.Range(0, cOs.Count);
			list.Add(cOs[index]);
		}
		return list;
	}

	public void DamageOverTime()
	{
		if (fLastWearEpoch == 0.0)
		{
			fLastWearEpoch = StarSystem.fEpoch;
		}
		else if (!(StarSystem.fEpoch - fLastWearEpoch < 300.0))
		{
			double num = 1.5844382307706396E-09 * (StarSystem.fEpoch - fLastWearEpoch);
			if (nLoadState < Loaded.Edit)
			{
				AccrueWear((float)num);
			}
			else
			{
				DamageAllCOs((float)num, allowMultiple: true);
			}
			fLastWearEpoch = StarSystem.fEpoch;
		}
	}

	private void UpdateConstructionProgress()
	{
		int num = (int)((StarSystem.fEpoch - fFirstVisit) / 86400.0);
		nConstructionProgress = nInitConstructionProgress + num;
		if (nConstructionProgress > 100)
		{
			nConstructionProgress = 100;
		}
		json.nConstructionProgress = nConstructionProgress;
	}

	private List<JsonItem> Reconstruct()
	{
		if (json == null || nConstructionProgress <= 0 || nConstructionProgress >= 100)
		{
			return new List<JsonItem>();
		}
		int nProgress = DataHandler.GetShipConstructionTemplate(json).nProgress;
		UpdateConstructionProgress();
		JsonShipConstructionTemplate shipConstructionTemplate = DataHandler.GetShipConstructionTemplate(json);
		if (shipConstructionTemplate.nProgress == nProgress)
		{
			return new List<JsonItem>();
		}
		Dictionary<string, bool> dictionary = new Dictionary<string, bool>();
		List<JsonItem> list = new List<JsonItem>();
		JsonItem jsonItem = null;
		List<JsonItem> list2 = shipConstructionTemplate.aItems.ToList();
		if (shipConstructionTemplate.aShallowPSpecs != null)
		{
			list2.AddRange(shipConstructionTemplate.aShallowPSpecs);
		}
		foreach (JsonItem item2 in list2)
		{
			bool value = false;
			if (!dictionary.TryGetValue(item2.strName, out value))
			{
				DataCO dataCO = DataHandler.GetDataCO(item2.strName);
				if (dataCO == null)
				{
					continue;
				}
				value = dataCO.HasCond("IsInstalled") || dataCO.HasCond("IsLootSpawner");
				dictionary[item2.strName] = value;
				if (jsonItem == null && dataCO.HasCond("IsDockSys"))
				{
					jsonItem = item2;
				}
			}
			if (value)
			{
				list.Add(item2.Clone());
			}
		}
		if (jsonItem == null)
		{
			Debug.Log("Could not find docksys on template, aborting reconstruction of " + strRegID);
			return new List<JsonItem>();
		}
		float offsetX = jsonItem.fX;
		float offsetY = jsonItem.fY;
		int num = 0;
		JsonItem[] aItems = json.aItems;
		foreach (JsonItem jsonItem2 in aItems)
		{
			if (!(jsonItem2.strName != jsonItem.strName))
			{
				num = ((int)(jsonItem.fRotation - jsonItem2.fRotation) % 360 + 360) % 360 / 90;
				float num2 = jsonItem.fX;
				float num3 = jsonItem.fY;
				for (int j = 0; j < num; j++)
				{
					float num4 = num2;
					num2 = num3;
					num3 = 0f - num4;
				}
				offsetX = jsonItem2.fX - num2;
				offsetY = jsonItem2.fY - num3;
				break;
			}
		}
		List<JsonItem> list3 = new List<JsonItem>();
		aItems = json.aItems;
		foreach (JsonItem item in aItems)
		{
			list3.Add(item);
		}
		List<JsonItem> list4 = new List<JsonItem>();
		foreach (JsonItem item3 in list)
		{
			bool flag = false;
			item3.Translate(offsetX, offsetY, num);
			foreach (JsonItem item4 in list3)
			{
				if (item4.Matches(item3))
				{
					flag = true;
					list3.Remove(item4);
					break;
				}
			}
			if (!flag)
			{
				list4.Add(item3);
			}
		}
		return list4;
	}

	public void DebugBreakIn()
	{
		BreakIn();
		VisualizeOverlays();
	}

	private void BreakIn()
	{
		bool bIgnoreCOTrans = AudioManager.bIgnoreCOTrans;
		AudioManager.bIgnoreCOTrans = true;
		float num = 0.025f;
		if (CrewSim.coPlayer != null && CrewSim.coPlayer.HasCond("IsDueBonusDerelict"))
		{
			float num2 = (float)(CrewSim.coPlayer.GetCondAmount("IsDueBonusDerelict") + 1.0);
			fBreakInMultiplier /= num2;
			CrewSim.coPlayer.ZeroCondAmount("IsDueBonusDerelict");
			num = 0.25f;
		}
		List<CondOwner> list = new List<CondOwner>();
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsDerelictSafe");
		float fChance = ctDerelictSafe.fChance;
		condTrigger.fChance = Mathf.Lerp(0.5f, 1f, fChance * fBreakInMultiplier);
		for (int i = 0; (float)i < fBreakInMultiplier * 10f; i++)
		{
			Tile randomTile = GetRandomTile1();
			int num3 = Mathf.RoundToInt(MathUtils.Rand(fBreakInMultiplier * 2.5f, fBreakInMultiplier * 5f, MathUtils.RandType.Flat));
			if (num3 < 1)
			{
				num3 = 1;
			}
			list = GetCOsInZone(TileUtils.GetZoneFromTileRadius(this, randomTile.tf.position, num3, bShuffled: false, bCircle: true), condTrigger, bAllowLocked: true, bAllowDocked: false);
			foreach (CondOwner item in list)
			{
				if (item.ship == this)
				{
					item.RemoveFromCurrentHome();
					item.Destroy();
				}
			}
		}
		condTrigger.fChance = fChance;
		CondTrigger condTrigger2 = DataHandler.GetCondTrigger("TIsDerelictForbid" + CollisionManager.strATCClosest);
		if (!condTrigger2.IsBlank())
		{
			list = GetCOs(condTrigger2, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
			foreach (CondOwner item2 in list)
			{
				if (item2.ship == this)
				{
					item2.RemoveFromCurrentHome();
					item2.Destroy();
				}
			}
		}
		fChance = ctDerelictSafe.fChance;
		ctDerelictSafe.fChance = Mathf.Lerp(0.5f, 1f, fChance * fBreakInMultiplier);
		list = GetCOs(ctDerelictSafe, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		ctDerelictSafe.fChance = fChance;
		foreach (CondOwner item3 in list)
		{
			if (item3.ship == this)
			{
				item3.RemoveFromCurrentHome();
				item3.Destroy();
			}
		}
		list.Clear();
		CondTrigger condTrigger3 = DataHandler.GetCondTrigger("TIsSwitch01On");
		foreach (CondOwner value in mapICOs.Values)
		{
			if (value.HasCond("IsAirtight"))
			{
				string[] aReactantNames = FusionIC.aReactantNames;
				foreach (string strName in aReactantNames)
				{
					if (value.HasCond(strName))
					{
						value.AddCondAmount(strName, (0.0 - value.GetCondAmount(strName)) * (double)MathUtils.Rand(0f, 1f, MathUtils.RandType.Flat));
					}
				}
			}
			else if (value.HasCond("StatPower"))
			{
				value.SetCondAmount("StatPower", MathUtils.Rand(0.0, value.GetCondAmount("StatPower"), MathUtils.RandType.Flat));
			}
			else if (value.HasCond("IsDoor01"))
			{
				list.Add(value);
			}
			else if (value.HasCond("IsPowerConduit") && value.HasCond("IsCollectiveElectric"))
			{
				list.Add(value);
			}
			else if (DMGStatus == Damage.Derelict)
			{
				if (value.HasCond("IsReactorIC"))
				{
					value.GetComponent<FusionIC>().SetDerelict();
				}
				else if (condTrigger3.Triggered(value))
				{
					list.Add(value);
				}
			}
		}
		Loot loot = DataHandler.GetLoot("ItmRandomDerelictConduit");
		Loot loot2 = DataHandler.GetLoot("ItmRandomDerelictDoor");
		Loot loot3 = DataHandler.GetLoot("ItmSwitch01Off");
		foreach (CondOwner item4 in list)
		{
			if (item4.HasCond("IsDoor01"))
			{
				List<CondOwner> cOLoot = loot2.GetCOLoot(null, bSuppressOverride: false);
				if (cOLoot.Count > 0)
				{
					item4.ModeSwitch(cOLoot[0], item4.tf.position);
				}
			}
			else if (item4.HasCond("IsPowerConduit") && item4.HasCond("IsCollectiveElectric"))
			{
				List<CondOwner> cOLoot2 = loot.GetCOLoot(null, bSuppressOverride: false);
				if (cOLoot2.Count > 0)
				{
					item4.ModeSwitch(cOLoot2[0], item4.tf.position);
				}
			}
			else if (condTrigger3.Triggered(item4))
			{
				List<CondOwner> cOLoot3 = loot3.GetCOLoot(null, bSuppressOverride: false);
				if (cOLoot3.Count > 0)
				{
					item4.ModeSwitch(cOLoot3[0], item4.tf.position);
				}
			}
		}
		float num4 = Mathf.Lerp(0.33f, 1.1f, fBreakInMultiplier);
		CondTrigger condTrigger4 = DataHandler.GetCondTrigger("TIsNotAMineral");
		DamageAllCOs(num4, allowMultiple: true, condTrigger4);
		DamageAllCOs(num4 * 3f, allowMultiple: true, ctDerelictSafe);
		int num5 = MathUtils.Rand((int)(fBreakInMultiplier * 4f), (int)(fBreakInMultiplier * 10f), MathUtils.RandType.Flat);
		if (num5 < 1)
		{
			num5 = 1;
		}
		JsonAttackMode attackMode = DataHandler.GetAttackMode("AModeDerelictBreakIn");
		for (int k = 0; k < num5; k++)
		{
			if (attackMode == null)
			{
				break;
			}
			DamageSystem.DamageRayRandom(attackMode, fBreakInMultiplier, null, bAllowDocked: false);
		}
		if (CrewSim.coPlayer != null && CrewSim.coPlayer.GetCondAmount("IsDueVideotapeSpawn") >= 1.0 && !CrewSim.coPlayer.HasCond("Plot_AVClub_Start_Completed"))
		{
			CondTrigger condTrigger5 = DataHandler.GetCondTrigger("TIsInstalledContainer");
			List<CondOwner> cOs = GetCOs(condTrigger5, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
			if (cOs.Count > 0)
			{
				CondOwner condOwner = DataHandler.GetCondOwner("Videotape");
				foreach (CondOwner item5 in cOs)
				{
					if ((bool)item5.objContainer && item5.objContainer.CanFit(condOwner, bAuto: true, bSub: true, bAllowLocked: true))
					{
						CrewSim.coPlayer.AddCondAmount("IsDueVideotapeSpawn", -1.0);
						CrewSim.coPlayer.AddCondAmount("VideotapeHasSpawned", 1.0);
						if (!PlotManager.IsPlotActive("Ceres"))
						{
							PlotManager.CheckPlot("Ceres", CrewSim.coPlayer, PlotManager.PlotTensionType.RELEASE, null, bForcePlot: true);
						}
						item5.AddCO(condOwner, bEquip: false, bOverflow: true, bIgnoreLocks: true);
						break;
					}
				}
				if (CrewSim.coPlayer.HasCond("IsDueVideotapeSpawn"))
				{
					condOwner.Destroy();
				}
			}
		}
		if (CrewSim.coPlayer != null)
		{
			if (CrewSim.coPlayer.GetCondAmount("StatNoMeat") >= 1.0)
			{
				CrewSim.coPlayer.AddCondAmount("StatNoMeat", -1.0);
			}
			else if (CrewSim.coPlayer.HasCond("IsDueMeatProgression"))
			{
				CrewSim.coPlayer.ZeroCondAmount("IsDueMeatProgression");
				CondTrigger condTrigger6 = DataHandler.GetCondTrigger("CTPLOT_Meat_Inert_Ready");
				CondTrigger condTrigger7 = DataHandler.GetCondTrigger("CTPLOT_Meat_Easy_Ready");
				CondTrigger condTrigger8 = DataHandler.GetCondTrigger("CTPLOT_Meat_Med_Ready");
				CondTrigger condTrigger9 = DataHandler.GetCondTrigger("CTPLOT_Meat_Hard_Ready");
				CondTrigger condTrigger10 = DataHandler.GetCondTrigger("CTPLOT_Meat_Awaken");
				float fFuel = (float)CrewSim.coPlayer.GetCondAmount("StatPlotMeat");
				if (CrewSim.eMeatState == MeatState.Dormant && condTrigger10.Triggered(CrewSim.coPlayer))
				{
					CrewSim.eMeatState = MeatState.Spread;
				}
				if (condTrigger9.Triggered(CrewSim.coPlayer))
				{
					CrewSim.GetSelectedCrew().LogMessage(CrewSim.GetSelectedCrew().strName + " is suddenly more aware of their own meat and bone.", "Meat", CrewSim.GetSelectedCrew().strID);
					for (int l = 0; l < UnityEngine.Random.Range(3, 9); l++)
					{
						SpawnMeat(fFuel);
					}
				}
				else if (condTrigger8.Triggered(CrewSim.coPlayer))
				{
					CrewSim.GetSelectedCrew().LogMessage(CrewSim.GetSelectedCrew().strName + " has a meaty lump in their throat.", "Meat", CrewSim.GetSelectedCrew().strID);
					SpawnMeat(fFuel);
				}
				else if (condTrigger7.Triggered(CrewSim.coPlayer))
				{
					CrewSim.GetSelectedCrew().LogMessage(CrewSim.GetSelectedCrew().strName + " feels like a meaty smell lingers.", "Meat", CrewSim.GetSelectedCrew().strID);
					for (int m = 0; m < UnityEngine.Random.Range(3, 9); m++)
					{
						SpawnRandom("CTPLOT_Meat_Spawnable", "ItmDocumentMeatPackaging");
					}
					for (int n = 0; n < UnityEngine.Random.Range(3, 9); n++)
					{
						SpawnRandom("CTPLOT_Meat_Spawnable", "LiquidBloodMeat");
					}
				}
				else if (condTrigger6.Triggered(CrewSim.coPlayer))
				{
					CrewSim.GetSelectedCrew().LogMessage(CrewSim.GetSelectedCrew().strName + " is craving something meaty.", "Meat", CrewSim.GetSelectedCrew().strID);
				}
				double num6 = CrewSim.coPlayer.GetCondAmount("StatMeatRate");
				if (num6 == 0.0)
				{
					num6 = 1.0;
				}
				CrewSim.coPlayer.AddCondAmount("StatNoMeat", num6);
			}
		}
		list = GetCOs(ctRCSGasCans, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		foreach (CondOwner item6 in list)
		{
			GasContainer gasContainer = item6.GasContainer;
			if (gasContainer != null)
			{
				gasContainer.BreakIn();
			}
		}
		foreach (CondOwner value2 in mapICOs.Values)
		{
			if (!value2.HasCond("IsDamaged") && value2.HasCond("IsSolid") && UnityEngine.Random.Range(0f, 1f) <= num)
			{
				value2.AddCondAmount("IsPristine", 1.0);
			}
		}
		CreateRooms();
		TileUtils.GetPoweredTiles(this);
		AudioManager.bIgnoreCOTrans = bIgnoreCOTrans;
	}

	public void SpawnMeat(float fFuel)
	{
		fFuel = ((!(CrewSim.GetSelectedCrew() != null) || !(CrewSim.GetSelectedCrew().GetCondAmount("StatMeatBlobMax") > 0.0)) ? Mathf.Min(fFuel, 50f) : Mathf.Min(fFuel, (float)CrewSim.GetSelectedCrew().GetCondAmount("StatMeatBlobMax")));
		CondTrigger condTrigger = DataHandler.GetCondTrigger("CTPLOT_Meat_Spawnable");
		Tile randomTile = GetRandomTile1();
		Ostranauts.Core.Models.Tuple<Vector2, Vector2> airlockBounds = TileUtils.GetAirlockBounds(this);
		for (int i = 0; i < 10; i++)
		{
			if (randomTile != null && TileUtils.IsTileAboveAirlock(randomTile, airlockBounds) && condTrigger.Triggered(randomTile.coProps))
			{
				break;
			}
			randomTile = GetRandomTile1();
		}
		if (randomTile == null || !TileUtils.IsTileAboveAirlock(randomTile, airlockBounds))
		{
			return;
		}
		List<CondOwner> list = new List<CondOwner>();
		list.AddRange(DataHandler.GetLoot("ItmMeat01").GetCOLoot(null, bSuppressOverride: false));
		foreach (CondOwner item in list)
		{
			item.tf.position = new Vector3(randomTile.tf.position.x, randomTile.tf.position.y, -2.5f);
			AddCO(item, bTiles: true);
			Meat meat = item.GetComponent<Meat>();
			if (meat == null)
			{
				meat = item.gameObject.AddComponent<Meat>();
			}
			meat.SpreadFast((int)fFuel);
		}
	}

	public void SpawnRandom(string strCT, string strLoot)
	{
		CondTrigger condTrigger = DataHandler.GetCondTrigger(strCT);
		Tile randomTile = GetRandomTile1();
		for (int i = 0; i < 10; i++)
		{
			if (condTrigger.Triggered(randomTile.coProps))
			{
				break;
			}
			randomTile = GetRandomTile1();
		}
		if (randomTile == null)
		{
			Debug.LogWarning("No tile in SpawnRandom!");
			return;
		}
		List<CondOwner> list = new List<CondOwner>();
		list.AddRange(DataHandler.GetLoot(strLoot).GetCOLoot(null, bSuppressOverride: false));
		if (list == null || list.Count == 0)
		{
			Debug.LogWarning("No loot in SpawnRandom!");
			return;
		}
		foreach (CondOwner item in list)
		{
			item.tf.position = new Vector3(randomTile.tf.position.x, randomTile.tf.position.y, -2.5f);
			AddCO(item, bTiles: true);
		}
	}

	public void DamageAllCOs(float fMaxAmount, bool allowMultiple = false, CondTrigger ct = null)
	{
		if (ct == null)
		{
			ct = DataHandler.GetCondTrigger("Blank");
		}
		List<CondOwner> cOs = GetCOs(ct, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		foreach (CondOwner item in cOs)
		{
			item.BreakIn(fMaxAmount, allowMultiple);
			if (selectedCrew != null && selectedCrew.ship == item.ship && item.GetDamageState() <= 0.0)
			{
				BeatManager.ResetTensionTimer();
			}
		}
	}

	public void DamageAllCOsTrend(float fMaxAmount, CondTrigger ct = null, double fRepairTarget = 0.0)
	{
		if (ct == null)
		{
			ct = DataHandler.GetCondTrigger("Blank");
		}
		List<CondOwner> cOs = GetCOs(ct, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		foreach (CondOwner item in cOs)
		{
			item.BreakIn(fMaxAmount, allowMultiple: true, fRepairTarget);
			if (selectedCrew != null && selectedCrew.ship == item.ship && item.GetDamageState() <= 0.0)
			{
				BeatManager.ResetTensionTimer();
			}
		}
	}

	public void CheckLocks()
	{
		CondOwner[] array = new CondOwner[aLocks.Count];
		aLocks.CopyTo(array);
		CondOwner[] array2 = array;
		foreach (CondOwner condOwner in array2)
		{
			if (condOwner.HasCond("IsLockPIN"))
			{
				Dictionary<string, string> value = null;
				condOwner.mapGUIPropMaps.TryGetValue("Panel A", out value);
				if (bResetLocks || (value != null && !value.ContainsKey("strPIN")))
				{
					StringBuilder stringBuilder = new StringBuilder();
					stringBuilder.Append(MathUtils.Rand(0, 10, MathUtils.RandType.Flat));
					stringBuilder.Append(MathUtils.Rand(0, 10, MathUtils.RandType.Flat));
					stringBuilder.Append(MathUtils.Rand(0, 10, MathUtils.RandType.Flat));
					stringBuilder.Append(MathUtils.Rand(0, 10, MathUtils.RandType.Flat));
					value["strPIN"] = stringBuilder.ToString();
				}
			}
		}
		aLocks.Clear();
		bCheckLocks = false;
		bResetLocks = false;
	}

	public void CheckTowingBraces()
	{
		bCheckTowingBraces = false;
		List<CondOwner> cOs = GetCOs(ctTowBraceSecured, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		if (cOs == null || cOs.Count == 0 || aDocksys == null)
		{
			aSecuredTowBraces = null;
			return;
		}
		aSecuredTowBraces = new Dictionary<string, string>();
		foreach (CondOwner item in cOs)
		{
			Vector2 pos = item.GetPos();
			foreach (CondOwner aDocksy in aDocksys)
			{
				if (!(aDocksy == null))
				{
					Vector2 pos2 = aDocksy.GetPos();
					if (Vector2.Distance(pos, pos2) <= 2f)
					{
						aSecuredTowBraces.Add(item.strID, aDocksy.strID);
					}
				}
			}
		}
	}

	public void CheckTargets()
	{
		if (json.strScanTargetID != null)
		{
			shipScanTarget = CrewSim.system.GetShipByRegID(json.strScanTargetID);
		}
		if (json.strStationKeepingTargetID != null)
		{
			shipStationKeepingTarget = CrewSim.system.GetShipByRegID(json.strStationKeepingTargetID);
		}
		if (json.strUndockID != null)
		{
			shipUndock = CrewSim.system.GetShipByRegID(json.strUndockID);
		}
		if (json.objSituScanTarget != null)
		{
			shipSituTarget = new ShipSitu(json.objSituScanTarget);
		}
		if (json.strTargetRegID != null)
		{
			targetRegID = json.strTargetRegID;
		}
		if (json.strCombatTargetID != null)
		{
			shipCombatTarget = CrewSim.system.GetShipByRegID(json.strCombatTargetID);
		}
		bCheckTargets = false;
	}

	public void ClearShipTarget()
	{
		shipScanTarget = null;
		shipSituTarget = null;
		targetRegID = null;
		TargetData = null;
	}

	public PersonSpec GetPerson(JsonPersonSpec jps, Social soc, bool bForceUnrelated, List<string> aForbids = null)
	{
		if (jps == null)
		{
			return null;
		}
		PersonSpec personSpec = null;
		if (soc != null)
		{
			personSpec = soc.GetComponent<CondOwner>().pspec;
		}
		if (nLoadState >= Loaded.Shallow && aPeople != null)
		{
			List<PersonSpec> list = null;
			foreach (PersonSpec aPerson in aPeople)
			{
				if (aPerson == null || personSpec == aPerson || (aForbids != null && aForbids.Contains(aPerson.FullName)))
				{
					continue;
				}
				if (bForceUnrelated && soc != null)
				{
					string strCTRelFind = jps.strCTRelFind;
					jps.strCTRelFind = "TRELStranger";
					bool flag = false;
					if (soc.HasPerson(aPerson))
					{
						flag = true;
					}
					else if (personSpec != null && !personSpec.IsCOMyMother(jps, aPerson.GetCO()))
					{
						flag = true;
					}
					jps.strCTRelFind = strCTRelFind;
					if (flag)
					{
						continue;
					}
				}
				else if (personSpec != null)
				{
					if (!personSpec.IsCOMyMother(jps, aPerson.GetCO()))
					{
						continue;
					}
				}
				else if (!jps.Matches(aPerson.GetCO()))
				{
					continue;
				}
				if (list == null)
				{
					list = new List<PersonSpec>();
				}
				list.Add(aPerson);
			}
			return list?[MathUtils.Rand(0, list.Count - 1, MathUtils.RandType.Flat)];
		}
		return null;
	}

	public List<CondOwner> GetPeopleInRoom(Room room, CondTrigger ct = null)
	{
		List<CondOwner> list = new List<CondOwner>();
		if (room != null)
		{
			for (int num = aPeople.Count - 1; num >= 0; num--)
			{
				CondOwner cO = aPeople[num].GetCO();
				if (!(cO == null) && cO.currentRoom == room && (ct == null || ct.Triggered(cO)) && list.IndexOf(cO) < 0)
				{
					list.Add(cO);
				}
			}
		}
		return list;
	}

	public List<CondOwner> GetPeople(bool bAllowDocked)
	{
		List<CondOwner> list = new List<CondOwner>();
		if (bDestroyed)
		{
			return list;
		}
		if (aPeople != null)
		{
			for (int num = aPeople.Count - 1; num >= 0; num--)
			{
				PersonSpec personSpec = aPeople[num];
				if (personSpec.GetCO() != null)
				{
					list.Add(personSpec.GetCO());
				}
			}
		}
		if (bAllowDocked && aDocked != null)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				Ship value = item.Value;
				if (value != null)
				{
					list.AddRange(value.GetPeople(bAllowDocked: false));
				}
			}
		}
		return list;
	}

	public List<CondOwner> GetPeople(CondTrigger ct, bool bAllowDocked)
	{
		List<CondOwner> list = new List<CondOwner>();
		if (aPeople != null)
		{
			for (int num = aPeople.Count - 1; num >= 0; num--)
			{
				CondOwner cO = aPeople[num].GetCO();
				if (ct.Triggered(cO))
				{
					list.Add(cO);
				}
			}
		}
		if (bAllowDocked && aDocked != null)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				Ship value = item.Value;
				if (value != null)
				{
					list.AddRange(value.GetPeople(ct, bAllowDocked: false));
				}
			}
		}
		return list;
	}

	public void ClearPeople()
	{
		aPeople.Clear();
	}

	public static string GenerateID(string strColony = null)
	{
		string text = "";
		string text2 = "HVEMBOJS";
		string text3 = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789";
		text = ((strColony != null) ? (text + strColony) : (text + text2.Substring(UnityEngine.Random.Range(0, text2.Length - 1), 1)));
		text += "-";
		text += text3.Substring(UnityEngine.Random.Range(0, text3.Length - 1), 1);
		text += text3.Substring(UnityEngine.Random.Range(0, text3.Length - 1), 1);
		text += text3.Substring(UnityEngine.Random.Range(0, text3.Length - 1), 1);
		if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) < 0.5)
		{
			text += text3.Substring(UnityEngine.Random.Range(0, text3.Length - 1), 1);
		}
		if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) < 0.1)
		{
			text += text3.Substring(UnityEngine.Random.Range(0, text3.Length - 1), 1);
		}
		if (CrewSim.system != null && CrewSim.system.dictShips.ContainsKey(text))
		{
			return GenerateID();
		}
		return text;
	}

	public GameObject CreatePart(JsonItem objItem, string strIDTemp, bool bLoot)
	{
		if (objItem == null)
		{
			return null;
		}
		CondOwner condOwner = null;
		if (strIDTemp != null)
		{
			if (mapICOs.ContainsKey(strIDTemp) && mapICOs[strIDTemp] != null)
			{
				condOwner = mapICOs[strIDTemp];
			}
			else if (DataHandler.mapCOs.ContainsKey(strIDTemp) && DataHandler.mapCOs[strIDTemp] != null)
			{
				condOwner = DataHandler.mapCOs[strIDTemp];
			}
		}
		if (condOwner == null)
		{
			condOwner = DataHandler.GetCondOwner(objItem.strName, strIDTemp, null, bLoot);
			if (condOwner != null && strIDTemp != null)
			{
				condOwner.strID = strIDTemp;
			}
		}
		if (condOwner == null)
		{
			return null;
		}
		Item item = condOwner.Item;
		GameObject result = condOwner.gameObject;
		condOwner.tf.position = new Vector3(objItem.fX, objItem.fY, condOwner.tf.position.z);
		if (item != null)
		{
			item.fLastRotation = objItem.fRotation;
		}
		else
		{
			condOwner.tf.rotation = Quaternion.Euler(0f, 0f, objItem.fRotation);
		}
		if (objItem.aGPMSettings != null)
		{
			for (int i = 0; i < objItem.aGPMSettings.Length; i++)
			{
				string strName = objItem.aGPMSettings[i].strName;
				foreach (KeyValuePair<string, string> item2 in DataHandler.ConvertStringArrayToDict(objItem.aGPMSettings[i].dictGUIPropMap))
				{
					if (!condOwner.mapGUIPropMaps.ContainsKey(strName))
					{
						condOwner.mapGUIPropMaps[strName] = new Dictionary<string, string>();
					}
					condOwner.mapGUIPropMaps[strName][item2.Key] = item2.Value;
				}
				if (strName == "Overrides" && condOwner.mapGUIPropMaps[strName].ContainsKey("strName"))
				{
					condOwner.strName = condOwner.mapGUIPropMaps[strName]["strName"];
				}
			}
			condOwner.CheckForRename();
		}
		return result;
	}

	protected bool UpdateTiles(CondOwner objICO, bool bRemove, bool skipRepositioning = false)
	{
		if (objICO == null)
		{
			return false;
		}
		Item item = objICO.Item;
		if (item == null)
		{
			return false;
		}
		if (objICO.Pathfinder != null)
		{
			return false;
		}
		Vector2 vector = new Vector2(-1f, 1f);
		if (objICO.HasCond("IsRoom"))
		{
			vector = Vector2.zero;
		}
		Vector3 vector2 = objICO.tf.position;
		Vector3 vector3 = vector2;
		if (vector2.x % 1f == 0f || vector2.y % 1f == 0f)
		{
			vector3 = GetClosestCrewMemberPosition(objICO.tf.position) ?? vector3;
		}
		if (item.nWidthInTiles % 2 != 0)
		{
			vector2.x = MathUtils.RoundToInt(vector2.x);
		}
		else if (vector2.x % 1f == 0f)
		{
			vector2 = MathUtils.GetClosestPosition(new Vector3[2]
			{
				new Vector3(vector2.x + 0.5f, vector2.y, vector2.z),
				new Vector3(vector2.x - 0.5f, vector2.y, vector2.z)
			}, vector3);
		}
		if (item.nHeightInTiles % 2 != 0)
		{
			vector2.y = MathUtils.RoundToInt(vector2.y);
		}
		else if (vector2.y % 1f == 0f)
		{
			vector2 = MathUtils.GetClosestPosition(new Vector3[2]
			{
				new Vector3(vector2.x, vector2.y + 0.5f, vector2.z),
				new Vector3(vector2.x, vector2.y - 0.5f, vector2.z)
			}, vector3);
		}
		if (!skipRepositioning && vector2 != objICO.tf.position)
		{
			objICO.tf.position = vector2;
		}
		Vector2 tLTileCoords = objICO.TLTileCoords;
		Vector2 vector4 = objICO.TLTileCoords + vector;
		int nLeft = (int)(0f - vector.x);
		int nTop = (int)vector.y;
		int nRight = item.nWidthInTiles - (int)vector.x;
		int nBottom = item.nHeightInTiles + (int)vector.y;
		if (aTiles.Count > 0)
		{
			nLeft = MathUtils.RoundToInt(vShipPos.x - vector4.x);
			nTop = -MathUtils.RoundToInt(vShipPos.y - vector4.y);
			nRight = Mathf.Max(0, item.nWidthInTiles - 2 * (int)vector.x - nLeft - nCols);
			nBottom = Mathf.Max(0, item.nHeightInTiles + 2 * (int)vector.y - nTop - nRows);
			nLeft = Mathf.Max(0, nLeft);
			nTop = Mathf.Max(0, nTop);
		}
		else
		{
			vShipPos = tLTileCoords;
		}
		bool result = false;
		if (!bRemove)
		{
			result = TileUtils.PadTilemap(this, goTiles, nLeft, nRight, nTop, nBottom);
		}
		else if (aTiles != null && aTiles.Count > 0)
		{
			result = TileUtils.PadTilemap(this, goTiles, nLeft, nRight, nTop, nBottom);
		}
		int num = 0;
		Tile tile = null;
		bool flag = false;
		List<Tile> list = null;
		if (item.ctSpriteSheet != null && (item.nHeightInTiles > 1 || item.nWidthInTiles > 1))
		{
			list = new List<Tile>();
		}
		for (int i = 0; i < item.nHeightInTiles; i++)
		{
			for (int j = 0; j < item.nWidthInTiles; j++)
			{
				tile = null;
				num = i * item.nWidthInTiles + j;
				if (item.aSocketAdds.Count < num - 1)
				{
					flag = true;
					break;
				}
				bool activeInHierarchy = TileUtils.goPartTiles.activeInHierarchy;
				TileUtils.goPartTiles.SetActive(value: true);
				RaycastHit[] array = Physics.RaycastAll(new Ray(new Vector3(tLTileCoords.x + (float)j, tLTileCoords.y - (float)i, -10f), Vector3.forward), 100f, 256);
				TileUtils.goPartTiles.SetActive(activeInHierarchy);
				RaycastHit[] array2 = array;
				foreach (RaycastHit raycastHit in array2)
				{
					tile = raycastHit.transform.GetComponent<Tile>();
					if (!(tile != null) || !(tile.coProps != null) || tile.coProps.ship != this)
					{
						continue;
					}
					List<string> lootNames = item.aSocketAdds[num].GetLootNames();
					CondOwner coProps = tile.coProps;
					foreach (string item4 in lootNames)
					{
						if (bRemove)
						{
							coProps.AddCondAmount(item4, -1.0);
						}
						else
						{
							coProps.AddCondAmount(item4, 1.0);
						}
					}
					tile.UpdateFlags();
					list?.Add(tile);
					break;
				}
			}
			if (flag)
			{
				break;
			}
		}
		if (item.ctSpriteSheet != null)
		{
			if (list == null)
			{
				Tile[] surroundingTiles = TileUtils.GetSurroundingTiles(tile, bCardinalOnly: true);
				item.SetSpriteSheetIndex(surroundingTiles);
				List<CondOwner> list2 = new List<CondOwner>();
				Tile[] array3 = surroundingTiles;
				foreach (Tile tile2 in array3)
				{
					if (tile2 == null || !item.ctSpriteSheet.Triggered(tile2.coProps))
					{
						continue;
					}
					GetCOsAtWorldCoords1(tile2.tf.position, null, bAllowDocked: false, bAllowLocked: true, list2);
					foreach (CondOwner item5 in list2)
					{
						Item item2 = item5.Item;
						if (!(item2 == null) && item2.ctSpriteSheet != null && !(item.ctSpriteSheet.strName != item2.ctSpriteSheet.strName))
						{
							item2.SetSpriteSheetIndex(TileUtils.GetSurroundingTiles(tile2, bCardinalOnly: true));
							break;
						}
					}
					list2.Clear();
				}
			}
			else
			{
				foreach (Tile item6 in list)
				{
					Tile[] surroundingTiles2 = TileUtils.GetSurroundingTiles(item6, bCardinalOnly: true);
					List<CondOwner> list3 = new List<CondOwner>();
					Tile[] array3 = surroundingTiles2;
					foreach (Tile tile3 in array3)
					{
						if (tile3 == null || list.Contains(tile3) || !item.ctSpriteSheet.Triggered(tile3.coProps))
						{
							continue;
						}
						GetCOsAtWorldCoords1(tile3.tf.position, null, bAllowDocked: false, bAllowLocked: true, list3);
						foreach (CondOwner item7 in list3)
						{
							Item item3 = item7.Item;
							if (!(item3 == null) && item3.ctSpriteSheet != null && !(item.ctSpriteSheet.strName != item3.ctSpriteSheet.strName))
							{
								item3.SetSpriteSheetIndex(TileUtils.GetSurroundingTiles(tile3, bCardinalOnly: true));
								break;
							}
						}
						list3.Clear();
					}
				}
			}
		}
		return result;
	}

	public void UpdateSensors()
	{
		if (ElectronicSystems != null)
		{
			ElectronicSystems.UpdateSensorStates();
		}
		bCheckSensors = false;
	}

	public void UpdatePower()
	{
		TileUtils.GetPoweredTiles(this);
		bCheckPower = false;
	}

	public void UpdateCrewSkills()
	{
		double fRangeModGunner = WeaponsSystem.fRangeModGunner;
		WeaponsSystem.fRangeModGunner = 1.0;
		fFuelEfficiencyMod = 1.0;
		if (ShipCO.HasCond("SkillOpsGunnery"))
		{
			WeaponsSystem.fRangeModGunner = 4.0;
		}
		if (ShipCO.HasCond("SkillOpsSpaceship"))
		{
			fFuelEfficiencyMod = 0.75;
		}
		if (IsStation(bIgnoreDocks: true) || IsStationHidden(bIgnoreDocks: true))
		{
			return;
		}
		if (LoadState <= Loaded.Shallow)
		{
			foreach (CondOwner person in GetPeople(bAllowDocked: false))
			{
				if (person.Kill && !person.HasCond("Unconscious"))
				{
					if (person.HasCond("SkillOpsGunnery"))
					{
						WeaponsSystem.fRangeModGunner = 4.0;
					}
					if (person.HasCond("SkillOpsSpaceship"))
					{
						fFuelEfficiencyMod = 0.75;
					}
				}
			}
		}
		else
		{
			foreach (CondOwner person2 in GetPeople(bAllowDocked: false))
			{
				if (!person2.Kill || person2.HasCond("Unconscious"))
				{
					continue;
				}
				Interaction interactionCurrent = person2.GetInteractionCurrent();
				if (interactionCurrent != null && !(interactionCurrent.strName != "GUINavStationAllow"))
				{
					if (person2.HasCond("SkillOpsGunnery"))
					{
						WeaponsSystem.fRangeModGunner = 4.0;
					}
					if (person2.HasCond("SkillOpsSpaceship"))
					{
						fFuelEfficiencyMod = 0.75;
					}
				}
			}
		}
		if (fRangeModGunner != WeaponsSystem.fRangeModGunner)
		{
			GUIOrbitDraw.TriggerArcRedraw(strRegID);
		}
	}

	public bool BGItemFits(Item itm)
	{
		if (itm == null)
		{
			return false;
		}
		Vector3 localPosition = itm.TF.localPosition;
		return BGItemFits(itm.ToString(), localPosition.x, localPosition.y);
	}

	private bool BGItemFits(string strBGName, float fX, float fY)
	{
		if (strBGName == null)
		{
			return false;
		}
		if (dictBGs.ContainsKey(strBGName))
		{
			List<Vector2> list = dictBGs[strBGName];
			if (list == null)
			{
				return true;
			}
			foreach (Vector2 item in list)
			{
				if (Mathf.Abs(fX - item.x) < 0.5f && Mathf.Abs(fY - item.y) < 0.5f)
				{
					return false;
				}
			}
		}
		return true;
	}

	public void BGItemAdd(Item itm)
	{
		if (!(itm == null))
		{
			Vector3 localPosition = itm.TF.localPosition;
			string key = itm.ToString();
			if (!dictBGs.ContainsKey(key))
			{
				dictBGs[key] = new List<Vector2>();
			}
			dictBGs[key].Add(localPosition);
			itm.TF.SetParent(tfBGs, worldPositionStays: true);
			CrewSim.objInstance.ShowBlocksAndLights(itm, bShow: true);
			if (!CrewSim.bShipEdit)
			{
				BoxCollider component = itm.GetComponent<BoxCollider>();
				component.center = new Vector3(component.center.x, component.center.y, component.center.z + 125f);
			}
		}
	}

	public void BGItemRemove(Item itm)
	{
		if (itm == null)
		{
			return;
		}
		Vector3 localPosition = itm.TF.localPosition;
		if (dictBGs.ContainsKey(itm.ToString()))
		{
			List<Vector2> list = dictBGs[itm.ToString()];
			if (list != null)
			{
				int num = -1;
				for (int i = 0; i < list.Count; i++)
				{
					Vector2 vector = list[i];
					if (Mathf.Abs(localPosition.x - vector.x) < 0.5f && Mathf.Abs(localPosition.y - vector.y) < 0.5f)
					{
						num = i;
						break;
					}
				}
				if (num >= 0)
				{
					list.RemoveAt(num);
				}
				if (list.Count == 0)
				{
					dictBGs.Remove(itm.ToString());
				}
			}
		}
		CrewSim.objInstance.ShowBlocksAndLights(itm, bShow: false);
		UnityEngine.Object.Destroy(itm.gameObject);
	}

	public void AddCO(CondOwner objICO, bool bTiles)
	{
		AddCO(objICO, bTiles, skipRepositioning: false);
	}

	private void AddCO(CondOwner objICO, bool bTiles, bool skipRepositioning)
	{
		if (objICO == null)
		{
			return;
		}
		if (mapICOs == null)
		{
			Debug.LogError("Adding CO " + objICO?.ToString() + " to null ship: " + strRegID);
			return;
		}
		bool flag = objICO.HasCond("IsModeSwitching", isThreshold: false);
		if (objICO == null || !flag)
		{
			ResetMass();
			SilhouettePoints = null;
		}
		CrewSim.objInstance.coDicts.AddCO(objICO);
		bool flag2 = false;
		if (bTiles)
		{
			flag2 = UpdateTiles(objICO, bRemove: false, skipRepositioning);
			CrewSim.objInstance.ShowBlocksAndLights(objICO, bShow: true);
		}
		List<CondOwner> aCOs = new List<CondOwner>();
		foreach (CondOwner item in objICO.aStack)
		{
			aCOs.Add(item);
			CondOwner.NullSafeAddRange(ref aCOs, item.GetCOs(bAllowLocked: true));
		}
		if (objICO.objContainer != null)
		{
			aCOs.AddRange(objICO.objContainer.GetCOs(bAllowLocked: true));
		}
		Slots compSlots = objICO.compSlots;
		if (compSlots != null)
		{
			aCOs.AddRange(compSlots.GetCOs(null, bAllowLocked: true));
		}
		Tile tileAtWorldCoords = GetTileAtWorldCoords1(objICO.tf.position.x, objICO.tf.position.y, bAllowDocked: true);
		foreach (CondOwner item2 in aCOs)
		{
			if (item2 == null)
			{
				Debug.LogError("Adding CO with null sub-co: " + objICO);
				continue;
			}
			mapICOs[item2.strID] = item2;
			item2.ship = this;
			Tile.AddToRoom(tileAtWorldCoords, item2, addEffects: true);
			if (item2.tf.parent == null && item2.slotNow != null)
			{
				item2.tf.SetParent(gameObject.transform, worldPositionStays: true);
			}
			if (item2.HasCond("IsSocial") && aPeople.IndexOf(item2.pspec) < 0)
			{
				if (item2.pspec == null)
				{
					Debug.LogError("Adding null pspec: " + item2.strName);
				}
				aPeople.Add(item2.pspec);
			}
			if (gameObject.activeInHierarchy && item2.HasTickers())
			{
				CrewSim.AddTicker(item2);
			}
			if (!CrewSim.bShipEdit && GUILocks.IsLock(item2))
			{
				bCheckLocks = true;
				aLocks.Add(item2);
			}
		}
		mapICOs[objICO.strID] = objICO;
		objICO.ship = this;
		if (objICO.objCOParent == null)
		{
			objICO.tf.SetParent(gameObject.transform, worldPositionStays: true);
		}
		Tile.AddToRoom(tileAtWorldCoords, objICO, addEffects: true);
		if (objICO.HasCond("IsSocial") && aPeople.IndexOf(objICO.pspec) < 0)
		{
			if (objICO.pspec == null)
			{
				Debug.LogError("Adding null pspec: " + objICO.strName);
			}
			aPeople.Add(objICO.pspec);
			Debug.Log("#Info# Adding " + objICO.strName + " to " + strRegID);
		}
		if (gameObject.activeInHierarchy && objICO.HasTickers())
		{
			CrewSim.AddTicker(objICO);
		}
		Pathfinder pathfinder = objICO.Pathfinder;
		if (pathfinder != null)
		{
			pathfinder.tilCurrent = tileAtWorldCoords;
		}
		objICO.gameObject.SetActive(gameObject.activeInHierarchy);
		if (objICO.objCOParent == null)
		{
			objICO.Visible = gameObject.activeInHierarchy;
		}
		if (objICO.HasCond("IsTraderNPC") || objICO.HasCond("IsMarketActor"))
		{
			AddMarketActorConfigToShip(objICO);
			if (nLoadState == Loaded.Full)
			{
				MarketManager.AddMarketActorToShip(this, objICO.strID);
			}
		}
		if (objICO.HasCond("IsPowerRecalc"))
		{
			bCheckPower = true;
		}
		if (flag2 || objICO.HasCond("IsCheckRoom"))
		{
			bCheckRooms = true;
		}
		if (!objICO.HasCond("IsShipSpecialItem"))
		{
			return;
		}
		if (!CrewSim.bShipEdit && GUILocks.IsLock(objICO))
		{
			bCheckLocks = true;
			aLocks.Add(objICO);
		}
		if (ctRCSClusterAudioEmitter.Triggered(objICO) && !aRCSThrusters.Contains(objICO))
		{
			aRCSThrusters.Add(objICO);
			if (objICO.HasCond("StatThrustStrength"))
			{
				fRCSCount += (float)objICO.GetCondAmount("StatThrustStrength");
			}
			else
			{
				fRCSCount += 1f;
			}
		}
		if (ctNavStationOn.Triggered(objICO) && aNavs.IndexOf(objICO) < 0)
		{
			aNavs.Add(objICO);
		}
		if (ctRadarOn.Triggered(objICO) && aElectronicSystemCOs.IndexOf(objICO) < 0)
		{
			aElectronicSystemCOs.Add(objICO);
			bCheckSensors = true;
		}
		if (CTReactor.Triggered(objICO) && aCores.IndexOf(objICO) < 0)
		{
			aCores.Add(objICO);
		}
		if (ctRCSDistroInstalled.Triggered(objICO) && !aRCSDistros.Contains(objICO))
		{
			aRCSDistros.Add(objICO);
			nRCSDistroCount++;
		}
		if (ctDocksys.Triggered(objICO) && !aDocksys.Contains(objICO))
		{
			if (!flag)
			{
				objICO.ZeroCondAmount("IsDockSysInUse");
			}
			if (objICO.HasCond("IsTypeB"))
			{
				aDocksys.Add(objICO);
				aDockingPorts.Add(objICO.strID);
			}
			else
			{
				aDocksys.Insert(0, objICO);
				aDockingPorts.Insert(0, objICO.strID);
			}
		}
		if (objICO.HasCond("IsTransponder"))
		{
			if (objICO.HasCond("IsDamaged"))
			{
				if (CrewSim.shipCurrentLoaded == this && CrewSim.coPlayer != null && CrewSim.coPlayer.HasCond("TutorialXPDRReplaceShow"))
				{
					Objective objective = new Objective(CrewSim.coPlayer, "Replace Broken Transponder", "TIsTutorialXPDRReplaceComplete");
					objective.strDisplayDesc = "Visit the ship broker on OKLG Commercial to replace your broken transponder.";
					objective.strDisplayDescComplete = "Replacement Transponder Purchased";
					objective.bTutorial = true;
					MonoSingleton<ObjectiveTracker>.Instance.AddObjective(objective);
					CrewSim.coPlayer.ZeroCondAmount("TutorialXPDRReplaceShow");
					CrewSim.coPlayer.AddCondAmount("TutorialXPDRReplaceWaiting", 1.0);
				}
			}
			else if (objICO.HasCond("IsInstalled"))
			{
				if (objICO.HasCond("IsReadyTransponderReset"))
				{
					objICO.ApplyGPMChanges(new string[1] { "Data,strRegID," + strRegID });
					objICO.ZeroCondAmount("IsReadyTransponderReset");
				}
				if (!objICO.HasCond("IsOff"))
				{
					strXPDR = objICO.GetGPMInfo("Data", "strRegID");
				}
			}
		}
		if (ctXPDRAntOn.Triggered(objICO))
		{
			bXPDRAntenna = true;
		}
		if (ctTowBraceSecured.Triggered(objICO))
		{
			bCheckTowingBraces = true;
		}
		if (ctAirPump.Triggered(objICO) && !aO2AirPumps.Contains(objICO) && ShipStatus.GetO2UnderPump(objICO, ctO2Can).Item2 > 0.0)
		{
			aO2AirPumps.Add(objICO);
		}
		if (ctO2Can.Triggered(objICO))
		{
			foreach (CondOwner cO in GetCOs(ctAirPump, bSubObjects: false, bAllowDocked: false, bAllowLocked: false))
			{
				if (!aO2AirPumps.Contains(cO))
				{
					Tile tileAtWorldCoords2 = GetTileAtWorldCoords1(objICO.tf.position.x, objICO.tf.position.y, bAllowDocked: false);
					Vector2 pos = cO.GetPos("GasInput");
					if (GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: false) == tileAtWorldCoords2)
					{
						aO2AirPumps.Add(cO);
						break;
					}
				}
			}
		}
		if (objICO.HasCond("IsFusionCoreModule"))
		{
			bCheckFusion = true;
		}
		if (ctHeavyLiftRotorsInstalled.Triggered(objICO))
		{
			LiftRotorsThrustStrength = -1f;
			if (!aActiveHeavyLiftRotors.Contains(objICO))
			{
				aActiveHeavyLiftRotors.Add(objICO);
			}
		}
		if (ctStabilizerActiveOn.Triggered(objICO))
		{
			nActiveStabilizers++;
		}
		if (objSS != null && objICO.HasCond("StatAeroLift"))
		{
			fAeroCoefficient += (float)objICO.GetCondAmount("StatAeroLift");
		}
		if (ctWeaponInstalled.Triggered(objICO))
		{
			WeaponsSystem.ResetWeaponData(objICO);
		}
	}

	public CondOwner DropCO(CondOwner objCO, Vector2 nearPosition)
	{
		JsonZone zoneFromTileRadius = TileUtils.GetZoneFromTileRadius(this, nearPosition, 2, bShuffled: true);
		Tile tileAtWorldCoords = GetTileAtWorldCoords1(nearPosition.x, nearPosition.y, bAllowDocked: true);
		if (tileAtWorldCoords != null && tileAtWorldCoords.jZone != null)
		{
			HashSet<int> hashSet = new HashSet<int>();
			int[] array = tileAtWorldCoords.jZone.aTiles;
			foreach (int item in array)
			{
				hashSet.Add(item);
			}
			zoneFromTileRadius.aTiles = hashSet.ToArray();
		}
		objCO.RemoveFromCurrentHome();
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsLootSpawnOK");
		List<CondOwner> cOsInZone = GetCOsInZone(zoneFromTileRadius, condTrigger, bAllowLocked: false);
		cOsInZone.Remove(objCO);
		if (true)
		{
			HashSet<int> hashSet2 = new HashSet<int>();
			int[] array = zoneFromTileRadius.aTiles;
			foreach (int num in array)
			{
				Vector2 worldCoordsAtTileIndex = GetWorldCoordsAtTileIndex1(num);
				worldCoordsAtTileIndex.x += 0.5f;
				worldCoordsAtTileIndex.y += 0.5f;
				if (Visibility.IsCondOwnerLOSVisibleBlocks(objCO, worldCoordsAtTileIndex, bIgnoreEndpoints: false, bIgnoreGlass: false))
				{
					hashSet2.Add(num);
				}
			}
			zoneFromTileRadius.aTiles = hashSet2.ToArray();
			for (int num2 = cOsInZone.Count - 1; num2 >= 0; num2--)
			{
				if (!Visibility.IsCondOwnerLOSVisibleBlocks(cOsInZone[num2], nearPosition, bIgnoreEndpoints: false, bIgnoreGlass: false))
				{
					cOsInZone.RemoveAt(num2);
				}
			}
		}
		List<CondOwner> list = TileUtils.DropCOsNearby(new List<CondOwner> { objCO }, this, zoneFromTileRadius, cOsInZone, condTrigger, bIgnoreLocks: false);
		CondOwner result = null;
		if (list.Count > 0)
		{
			result = list[0];
		}
		return result;
	}

	private void RemoveInternalFromRooms(Tile tile, CondOwner objCO)
	{
		if (bDestroyed || tile == null)
		{
			return;
		}
		if (tile.room == null)
		{
			Vector2 pos = objCO.GetPos("use");
			Tile tileAtWorldCoords = GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: false);
			if (tileAtWorldCoords != null && tileAtWorldCoords.room != null)
			{
				tileAtWorldCoords.room.RemoveFromRoom(objCO);
			}
		}
		else
		{
			tile.room.RemoveFromRoom(objCO);
		}
	}

	private void RemoveInternalSocial(CondOwner objCO)
	{
		aPeople.Remove(objCO.pspec);
		if (LoadState <= Loaded.Shallow && json != null && json.aCrew != null)
		{
			List<JsonItem> list = new List<JsonItem>();
			JsonItem[] aCrew = json.aCrew;
			foreach (JsonItem jsonItem in aCrew)
			{
				if (jsonItem.strID != objCO.strID)
				{
					list.Add(jsonItem);
				}
			}
			json.aCrew = list.ToArray();
		}
		Debug.Log("#Info# Removing " + objCO.strName + " from " + strRegID);
	}

	private void RemoveInternalItems(List<CondOwner> items)
	{
		if (items.Count == 0)
		{
			return;
		}
		Dictionary<string, bool> dictionary = new Dictionary<string, bool>(items.Count);
		foreach (CondOwner item in items)
		{
			dictionary[item.strID] = true;
		}
		JsonItem[] aItems = json.aItems;
		int num = aItems.Length;
		int num2 = 0;
		for (int i = 0; i < num; i++)
		{
			if (!dictionary.ContainsKey(aItems[i].strID))
			{
				aItems[num2] = aItems[i];
				num2++;
			}
		}
		if (num2 < num)
		{
			JsonItem[] array = new JsonItem[num2];
			Array.Copy(aItems, 0, array, 0, num2);
			json.aItems = array;
		}
	}

	protected void RemoveInternal(Tile tile, CondOwner objCO)
	{
		mapICOs.Remove(objCO.strID);
		CrewSim.RemoveTicker(objCO);
		RemoveInternalFromRooms(tile, objCO);
		if (objCO.HasCond("IsSocial"))
		{
			RemoveInternalSocial(objCO);
		}
		else if (LoadState <= Loaded.Shallow && json != null && json.aItems != null)
		{
			int num = -1;
			int num2 = 0;
			JsonItem[] aItems = json.aItems;
			foreach (JsonItem jsonItem in aItems)
			{
				if (jsonItem != null && jsonItem.strID == objCO.strID)
				{
					num = num2;
					break;
				}
				num2++;
			}
			if (num != -1)
			{
				List<JsonItem> list = new List<JsonItem>(json.aItems);
				list.RemoveAt(num);
				json.aItems = list.ToArray();
			}
		}
		objCO.ship = null;
		if (objCO.tf != null && gameObject != null && objCO.tf.parent == gameObject.transform)
		{
			objCO.tf.SetParent(null, worldPositionStays: true);
		}
	}

	protected void RemoveInternalLot(Tile tile, List<CondOwner> cosToRemove)
	{
		List<CondOwner> list = new List<CondOwner>();
		foreach (CondOwner item in cosToRemove)
		{
			mapICOs.Remove(item.strID);
			CrewSim.RemoveTicker(item);
			RemoveInternalFromRooms(tile, item);
			if (item.HasCond("IsSocial"))
			{
				RemoveInternalSocial(item);
			}
			else
			{
				list.Add(item);
			}
			item.ship = null;
			if (item.tf != null && gameObject != null && item.tf.parent == gameObject.transform)
			{
				item.tf.SetParent(null, worldPositionStays: true);
			}
		}
		if (LoadState <= Loaded.Shallow && json != null && json.aItems != null)
		{
			RemoveInternalItems(list);
		}
	}

	public bool HasRating()
	{
		if (rating != null && rating.Length >= 1)
		{
			return rating[0] != null;
		}
		return false;
	}

	public string GetRatingString()
	{
		if (!HasRating())
		{
			return "None";
		}
		string text = "";
		for (int i = 1; i < rating.Length; i++)
		{
			if (!string.IsNullOrEmpty(rating[i]))
			{
				text = ((i != 1) ? (text + "-" + rating[i]) : rating[i]);
			}
		}
		return text;
	}

	public string[] CalculateRating()
	{
		float num = 0f;
		List<CondOwner> cOs = GetCOs(DataHandler.GetCondTrigger("TIsInstalled"), bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		foreach (CondOwner item in cOs)
		{
			if (!item.HasCond("IsDamaged"))
			{
				float damageRate = item.GetDamageRate();
				num += Mathf.Clamp01(1f - damageRate);
			}
		}
		num /= (float)cOs.Count;
		string text = ((num >= 0f && (double)num <= 0.5) ? "E" : (((double)num > 0.5 && (double)num <= 0.8) ? "D" : (((double)num > 0.8 && (double)num <= 0.95) ? "C" : ((!((double)num > 0.95) || !((double)num <= 0.99)) ? "A" : "B"))));
		List<RoomSpec> roomSpecs = GetRoomSpecs();
		string text2 = "0";
		if (roomSpecs != null)
		{
			text2 = roomSpecs.Count.ToString();
		}
		double num2 = ((fRCSCount == 0f) ? 0.0 : (Mass / (double)fRCSCount));
		string text3 = "";
		text3 = ((num2 <= 0.0) ? "O" : ((num2 > 0.0 && num2 < 300.0) ? "A" : ((num2 >= 300.0 && num2 < 500.0) ? "B" : ((num2 >= 500.0 && num2 < 750.0) ? "C" : ((!(num2 >= 750.0) || !(num2 < 1500.0)) ? "E" : "D")))));
		int num3 = nCols * nRows;
		string text4 = "";
		text4 = ((num3 <= 0) ? "" : ((num3 < 250) ? "Small" : ((num3 < 900) ? "Medium" : ((num3 < 1600) ? "Lunamax" : ((num3 < 2300) ? "Ceresmax" : ((num3 < 3000) ? "Titanmax" : ((num3 >= 3700) ? "Ultra Large" : "Very Large")))))));
		string text5 = "";
		if (rating != null && rating.Length == 6)
		{
			text5 = rating[5];
		}
		string text6 = StarSystem.fEpoch.ToString();
		return new string[6] { text6, text, text2, text3, text4, text5 };
	}

	public void UpdateRating(string[] newRating = null)
	{
		rating = ((newRating != null) ? newRating : CalculateRating());
	}

	public void RemoveCO(CondOwner objCO, bool bForce = false)
	{
		if (objCO == null || !objCO.HasCond("IsModeSwitching", isThreshold: false))
		{
			ResetMass();
			SilhouettePoints = null;
		}
		if (objCO == null)
		{
			if ((object)objCO != null && objCO.strID != null)
			{
				mapICOs.Remove(objCO.strID);
			}
			aDocksys.Remove(objCO);
			return;
		}
		objCO.ValidateParent();
		CrewSim.objInstance.coDicts.RemoveCO(objCO);
		if (objCO.objCOParent != null && objCO.coStackHead == null)
		{
			if (objCO.slotNow != null)
			{
				Slots compSlots = objCO.objCOParent.compSlots;
				if (compSlots != null)
				{
					compSlots.UnSlotItem(objCO, bForce);
					objCO.ValidateParent();
					CondOwner.CheckTrue(objCO.objCOParent == null, "Unslotted but still have parent...");
				}
			}
		}
		else if (objCO.coStackHead != null)
		{
			CondOwner coStackHead = objCO.coStackHead;
			if (coStackHead.objCOParent != null)
			{
				coStackHead.objCOParent.AddMass(0.0 - objCO.GetTotalMass());
			}
			coStackHead.aStack.Remove(objCO);
			objCO.coStackHead = null;
			objCO.Item.fLastRotation = coStackHead.tf.rotation.eulerAngles.z;
			objCO.tf.position = new Vector3(coStackHead.tf.position.x, coStackHead.tf.position.y, coStackHead.tf.position.z);
			coStackHead.UpdateAppearance();
			objCO.UpdateAppearance();
		}
		else
		{
			UpdateTiles(objCO, bRemove: true);
			CrewSim.objInstance.ShowBlocksAndLights(objCO, bShow: false);
		}
		Tile tileAtWorldCoords = GetTileAtWorldCoords1(objCO.tf.position.x, objCO.tf.position.y, bAllowDocked: true);
		List<CondOwner> aCOs = new List<CondOwner>();
		if (objCO.aStack != null)
		{
			foreach (CondOwner item in objCO.aStack)
			{
				aCOs.Add(item);
				CondOwner.NullSafeAddRange(ref aCOs, item.GetCOs(bAllowLocked: true));
			}
		}
		if (objCO.objContainer != null)
		{
			aCOs.AddRange(objCO.objContainer.GetCOs(bAllowLocked: true));
		}
		Slots compSlots2 = objCO.compSlots;
		if (compSlots2 != null)
		{
			aCOs.AddRange(compSlots2.GetCOs(null, bAllowLocked: true));
		}
		aCOs.AddRange(objCO.aLot);
		RemoveInternalLot(tileAtWorldCoords, aCOs);
		RemoveInternal(tileAtWorldCoords, objCO);
		bCheckPower |= objCO.HasCond("IsPowerRecalc");
		bCheckRooms |= objCO.HasCond("IsCheckRoom");
		CrewSim.inventoryGUI.RemoveAndDestroy(objCO.strID);
		if (objCO.HasCond("IsShipSpecialItem"))
		{
			if (ctRCSClusterAudioEmitter.Triggered(objCO) && aRCSThrusters.Contains(objCO))
			{
				aRCSThrusters.Remove(objCO);
				if (objCO.HasCond("StatThrustStrength"))
				{
					fRCSCount -= (float)objCO.GetCondAmount("StatThrustStrength");
				}
				else
				{
					fRCSCount -= 1f;
				}
			}
			if (ctHeavyLiftRotorsInstalled.Triggered(objCO))
			{
				LiftRotorsThrustStrength = -1f;
				if (aActiveHeavyLiftRotors.Contains(objCO))
				{
					aActiveHeavyLiftRotors.Remove(objCO);
				}
			}
			if (ctNavStationOn.Triggered(objCO))
			{
				aNavs.Remove(objCO);
			}
			if (CTReactor.Triggered(objCO))
			{
				aCores.Remove(objCO);
			}
			if (ctRadarOn.Triggered(objCO))
			{
				aElectronicSystemCOs.Remove(objCO);
				bCheckSensors = true;
			}
			if (ctRCSDistroInstalled.Triggered(objCO) && aRCSDistros.Contains(objCO))
			{
				aRCSDistros.Remove(objCO);
				nRCSDistroCount--;
			}
			if (ctDocksys.Triggered(objCO))
			{
				if (!objCO.HasCond("IsModeSwitching", isThreshold: false))
				{
					objCO.ZeroCondAmount("IsDockSysInUse");
				}
				aDocksys.Remove(objCO);
				aDockingPorts.Remove(objCO.strID);
			}
			if (ctXPDR.Triggered(objCO) && GetCOs(ctXPDR, bSubObjects: false, bAllowDocked: false, bAllowLocked: false).Count == 0)
			{
				strXPDR = null;
			}
			if (ctXPDRAntOn.Triggered(objCO) && GetCOs(ctXPDRAntOn, bSubObjects: false, bAllowDocked: false, bAllowLocked: false).Count == 0)
			{
				bXPDRAntenna = false;
			}
			if (ctTowBraceSecured.Triggered(objCO))
			{
				bCheckTowingBraces = true;
			}
			if (ctAirPump.Triggered(objCO))
			{
				aO2AirPumps.Remove(objCO);
			}
			if (ctO2Can.Triggered(objCO))
			{
				foreach (CondOwner cO in GetCOs(ctAirPump, bSubObjects: false, bAllowDocked: false, bAllowLocked: false))
				{
					if (aO2AirPumps.Contains(cO))
					{
						Tile tileAtWorldCoords2 = GetTileAtWorldCoords1(cO.tf.position.x, cO.tf.position.y, bAllowDocked: false);
						Vector2 pos = cO.GetPos("GasInput");
						if (GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: false) == tileAtWorldCoords2)
						{
							aO2AirPumps.Remove(cO);
							break;
						}
					}
				}
			}
			if (objCO.HasCond("IsFusionCoreModule"))
			{
				bCheckFusion = true;
			}
			if (ctStabilizerActiveOn.Triggered(objCO))
			{
				nActiveStabilizers--;
			}
			if (objSS != null && objCO.HasCond("StatAeroLift"))
			{
				fAeroCoefficient -= (float)objCO.GetCondAmount("StatAeroLift");
			}
			if (ctWeaponInstalled.Triggered(objCO))
			{
				WeaponsSystem.ResetWeaponData();
			}
		}
		if (!_isDespawning && (objCO.HasCond("IsTraderNPC") || objCO.HasCond("IsMarketActor")))
		{
			RemoveMarketActorConfigFromShip(objCO);
			List<MarketItem> itemsToDrop = MarketManager.RemoveMarketActorFromShip(this, objCO.strID);
			DropCargoPodContent(objCO, itemsToDrop);
		}
		objCO.ValidateParent();
	}

	private void DropCargoPodContent(CondOwner podCO, List<MarketItem> itemsToDrop)
	{
		if (itemsToDrop == null || itemsToDrop.Count <= 0 || CrewSim.bShipEdit)
		{
			return;
		}
		List<CondOwner> list = new List<CondOwner>();
		int num = Mathf.Min(250, UnityEngine.Random.Range(0, itemsToDrop.Count / 4));
		if (MarketManager.ShowDebugLogs)
		{
			Debug.LogWarning("#Market# Dropping pod contents, trying: #" + num);
		}
		for (int i = 0; i < num; i++)
		{
			CondOwner condOwner = DataHandler.GetCondOwner(itemsToDrop[i].COName);
			if (!(condOwner == null))
			{
				float num2 = 2 + Mathf.Min(list.Count, 3);
				CondOwner condOwner2 = podCO.DropCO(condOwner, bAllowLocked: false, this, num2, num2);
				if (condOwner2 != null)
				{
					list.Add(condOwner2);
				}
			}
		}
		foreach (CondOwner item in list)
		{
			if (!(item == null))
			{
				item.Destroy();
			}
		}
	}

	public void ResetMass()
	{
		_mass = 0.0;
	}

	public void VisitCOs(CondTrigger objCondTrig, bool bSubObjects, bool bAllowDocked, bool bAllowLocked, Action<CondOwner> visitor)
	{
		CondOwnerVisitorAddToHashSet condOwnerVisitorAddToHashSet = new CondOwnerVisitorAddToHashSet();
		CondOwnerVisitor visitor2 = CondOwnerVisitorCondTrigger.WrapVisitor(condOwnerVisitorAddToHashSet, objCondTrig);
		VisitCOs(visitor2, bSubObjects, bAllowDocked, bAllowLocked);
		foreach (CondOwner item in condOwnerVisitorAddToHashSet.aHashSet)
		{
			visitor(item);
		}
	}

	public void VisitCOs(CondOwnerVisitor visitor, bool bSubObjects, bool bAllowDocked, bool bAllowLocked)
	{
		if (mapICOs == null)
		{
			return;
		}
		CondOwner[] array = mapICOs.Values.ToArray();
		foreach (CondOwner condOwner in array)
		{
			if (!(condOwner.objCOParent != null))
			{
				if (bSubObjects)
				{
					condOwner.VisitCOs(visitor, bAllowLocked);
				}
				visitor.Visit(condOwner);
			}
		}
		foreach (Room aRoom in aRooms)
		{
			visitor.Visit(aRoom.CO);
		}
		if (!bAllowDocked)
		{
			return;
		}
		IReadOnlyList<Ship> allDockedShips = GetAllDockedShips();
		if (allDockedShips == null)
		{
			return;
		}
		foreach (Ship item in allDockedShips)
		{
			item?.VisitCOs(visitor, bSubObjects, bAllowDocked: false, bAllowLocked);
		}
	}

	public List<CondOwner> GetCOs(CondTrigger objCondTrig, bool bSubObjects, bool bAllowDocked, bool bAllowLocked)
	{
		CondOwnerVisitorAddToHashSet condOwnerVisitorAddToHashSet = new CondOwnerVisitorAddToHashSet();
		CondOwnerVisitor visitor = CondOwnerVisitorCondTrigger.WrapVisitor(condOwnerVisitorAddToHashSet, objCondTrig);
		VisitCOs(visitor, bSubObjects, bAllowDocked, bAllowLocked);
		return new List<CondOwner>(condOwnerVisitorAddToHashSet.aHashSet);
	}

	public Dictionary<string, CondOwner> GetMappedCos()
	{
		return mapICOs;
	}

	public CondOwner GetCOFirstOccurrence(JsonPersonSpec jps, PersonSpec psSearcher, bool bAllowDocked)
	{
		if (mapICOs == null)
		{
			return null;
		}
		System.Random randomObjectContainer = new System.Random();
		List<PersonSpec> list = new List<PersonSpec>(aPeople);
		if (bAllowDocked)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (item.Value != null)
				{
					list.AddRange(item.Value.aPeople);
				}
			}
		}
		foreach (PersonSpec item2 in list.OrderBy((PersonSpec x) => randomObjectContainer.Next()))
		{
			if (item2 == null)
			{
				continue;
			}
			if (psSearcher == null)
			{
				if (jps == null || jps.Matches(item2.GetCO()))
				{
					return item2.GetCO();
				}
			}
			else if (psSearcher.IsCOMyMother(jps, item2.GetCO()))
			{
				return item2.GetCO();
			}
		}
		return null;
	}

	public CondOwner GetCOFirstOccurrence(CondTrigger objCondTrig, bool bSubObjects, bool bAllowDocked, bool bAllowLocked)
	{
		if (mapICOs == null)
		{
			return null;
		}
		System.Random randomObjectContainer = new System.Random();
		if (objCondTrig.RequiresHumans)
		{
			List<PersonSpec> list = new List<PersonSpec>(aPeople);
			if (bAllowDocked)
			{
				foreach (KeyValuePair<string, Ship> item in aDocked)
				{
					if (item.Value != null)
					{
						list.AddRange(item.Value.aPeople);
					}
				}
			}
			foreach (PersonSpec item2 in list.OrderBy((PersonSpec x) => randomObjectContainer.Next()))
			{
				if (item2 != null && objCondTrig.Triggered(item2.GetCO()))
				{
					return item2.GetCO();
				}
			}
			return null;
		}
		System.Random random = new System.Random();
		CondOwner[] array = mapICOs.Values.ToArray();
		for (int num = array.Length - 1; num > 0; num--)
		{
			int num2 = random.Next(num + 1);
			CondOwner condOwner = array[num];
			array[num] = array[num2];
			array[num2] = condOwner;
		}
		List<CondOwner> list2 = new List<CondOwner>();
		CondOwner[] array2 = array;
		foreach (CondOwner condOwner2 in array2)
		{
			if (condOwner2 == null || condOwner2.objCOParent != null)
			{
				continue;
			}
			if (objCondTrig.Triggered(condOwner2))
			{
				if (!bAllowDocked)
				{
					return condOwner2;
				}
				list2.Add(condOwner2);
				break;
			}
			if (!bSubObjects)
			{
				continue;
			}
			List<CondOwner> cOs = condOwner2.GetCOs(bAllowLocked, objCondTrig);
			if (cOs != null && cOs.Count != 0)
			{
				IOrderedEnumerable<CondOwner> source = cOs.OrderBy((CondOwner x) => randomObjectContainer.Next());
				if (bAllowDocked)
				{
					list2.Add(source.FirstOrDefault());
					break;
				}
				return source.FirstOrDefault();
			}
		}
		foreach (Room item3 in aRooms.OrderBy((Room x) => randomObjectContainer.Next()))
		{
			if (objCondTrig.Triggered(item3.CO))
			{
				if (!bAllowDocked)
				{
					return item3.CO;
				}
				list2.Add(item3.CO);
				break;
			}
		}
		if (bAllowDocked)
		{
			foreach (KeyValuePair<string, Ship> item4 in aDocked)
			{
				if (item4.Value != null)
				{
					CondOwner cOFirstOccurrence = item4.Value.GetCOFirstOccurrence(objCondTrig, bSubObjects, bAllowDocked: false, bAllowLocked);
					if (cOFirstOccurrence != null)
					{
						list2.Add(cOFirstOccurrence);
						break;
					}
				}
			}
		}
		if (list2.Count > 0)
		{
			return list2.OrderBy((CondOwner x) => randomObjectContainer.Next()).FirstOrDefault();
		}
		return null;
	}

	public List<CondOwner> GetICOs1(CondTrigger objCondTrig, bool bSubObjects, bool bAllowDocked, bool bAllowLocked)
	{
		return GetCOs(objCondTrig, bSubObjects, bAllowDocked, bAllowLocked);
	}

	public CondOwner GetCOByID(string strID)
	{
		if (strID == null)
		{
			return null;
		}
		CondOwner value = null;
		mapICOs.TryGetValue(strID, out value);
		return value;
	}

	public Room GetRoomByID(string strID)
	{
		if (strID == null)
		{
			return null;
		}
		foreach (Room aRoom in aRooms)
		{
			if (aRoom.CO != null && aRoom.CO.strID == strID)
			{
				return aRoom;
			}
		}
		return null;
	}

	public void GetCOsAtWorldCoords1(Vector2 vPos, CondTrigger ct, bool bAllowDocked, bool bAllowLocked, List<CondOwner> aOut)
	{
		if (aOut == null)
		{
			return;
		}
		RaycastHit[] array = Physics.RaycastAll(new Ray(new Vector3(vPos.x, vPos.y, -20f), Vector3.forward), 100f);
		Room roomAtWorldCoords = GetRoomAtWorldCoords1(vPos, bAllowDocked);
		CondOwner condOwner = null;
		CondOwner condOwner2 = null;
		if (roomAtWorldCoords != null)
		{
			condOwner = roomAtWorldCoords.CO;
		}
		foreach (RaycastHit raycastHit in array)
		{
			CondOwner component = raycastHit.transform.GetComponent<CondOwner>();
			if (condOwner == component || !(component != null) || component.ship == null)
			{
				continue;
			}
			if (component.ship != this)
			{
				if (!bAllowDocked)
				{
					continue;
				}
				if (condOwner2 == null)
				{
					Room roomAtWorldCoords2 = component.ship.GetRoomAtWorldCoords1(vPos, bAllowDocked: false);
					if (roomAtWorldCoords2 != null && (ct == null || ct.Triggered(roomAtWorldCoords2.CO, null, logOutcome: false)))
					{
						condOwner2 = roomAtWorldCoords2.CO;
					}
				}
			}
			bool flag = false;
			if (ct == null)
			{
				flag = true;
			}
			else if ((ct.strCondName == null || ct.strCondName == "") && ct.Triggered(component, null, logOutcome: false))
			{
				flag = true;
			}
			if (flag && aOut.IndexOf(component) < 0)
			{
				aOut.Add(component);
			}
		}
		if (condOwner != null && (ct == null || ct.Triggered(condOwner, null, logOutcome: false)) && aOut.IndexOf(condOwner) < 0)
		{
			aOut.Add(condOwner);
		}
		if (bAllowDocked && condOwner2 != null && aOut.IndexOf(condOwner2) < 0)
		{
			aOut.Add(condOwner2);
		}
	}

	public bool TileIndexValid(int nTileIndex)
	{
		if (0 <= nTileIndex)
		{
			return nTileIndex < aTiles.Count;
		}
		return false;
	}

	public int GetTileIndexAtWorldCoords1(Vector2 vPos)
	{
		return GetTileIndexAtWorldCoords(vPos.x, vPos.y);
	}

	public int GetTileIndexAtWorldCoords(float fX, float fY)
	{
		int num = MathUtils.RoundToInt((fX - vShipPos.x) / 1f);
		int num2 = -MathUtils.RoundToInt((fY - vShipPos.y) / 1f);
		if (num < 0 || nCols <= num)
		{
			return -1;
		}
		if (num2 < 0 || nRows <= num2)
		{
			return -1;
		}
		return num + num2 * nCols;
	}

	public Vector2 GetWorldCoordsAtTileIndex1(int nIndex)
	{
		if (nIndex < 0 || nIndex > aTiles.Count - 1)
		{
			return Vector2.zero;
		}
		Vector2 result = new Vector2(vShipPos.x, vShipPos.y);
		result.x += nIndex % nCols;
		result.y -= nIndex / nCols;
		return result;
	}

	public Tile GetTileByIndex(int index)
	{
		if (index < 0 || index >= aTiles.Count)
		{
			return null;
		}
		return aTiles[index];
	}

	public Tile GetTileAtWorldCoords1(float fX, float fY, bool bAllowDocked, bool checkIfShipTile = true)
	{
		Tile tile = null;
		int tileIndexAtWorldCoords = GetTileIndexAtWorldCoords(fX, fY);
		tile = GetTileByIndex(tileIndexAtWorldCoords);
		if (checkIfShipTile && tile != null && TileUtils.CTShipTileOrSub.Triggered(tile.coProps, null, logOutcome: false))
		{
			return tile;
		}
		if (bAllowDocked && aDocked != null)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (item.Value == null)
				{
					continue;
				}
				List<Ship> list = new List<Ship> { item.Value };
				if (item.Value.aDocked != null)
				{
					foreach (KeyValuePair<string, Ship> item2 in item.Value.aDocked)
					{
						if (item2.Value != null && !(item2.Value.strRegID == item.Value.strRegID))
						{
							list.Add(item2.Value);
						}
					}
				}
				foreach (Ship item3 in list)
				{
					Tile tileAtWorldCoords = item3.GetTileAtWorldCoords1(fX, fY, bAllowDocked: false, checkIfShipTile: false);
					if (tileAtWorldCoords != null)
					{
						if (TileUtils.CTShipTileOrSub.Triggered(tileAtWorldCoords.coProps))
						{
							return tileAtWorldCoords;
						}
						if (tile == null)
						{
							tile = tileAtWorldCoords;
						}
					}
				}
			}
		}
		return tile;
	}

	public bool GetRandomCO(out CondOwner co)
	{
		if (mapICOs == null || mapICOs.Count == 0)
		{
			co = null;
			return false;
		}
		co = mapICOs.ElementAt(UnityEngine.Random.Range(0, mapICOs.Count)).Value;
		return true;
	}

	public Room GetRandomRoom(bool bAllowDocked)
	{
		Room result = null;
		if (!bAllowDocked)
		{
			if (aRooms.Count > 0)
			{
				int index = UnityEngine.Random.Range(0, aRooms.Count);
				return aRooms[index];
			}
		}
		else
		{
			List<Room> list = new List<Room>();
			list.AddRange(aRooms);
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (item.Value != null)
				{
					list.AddRange(item.Value.aRooms);
				}
			}
			int index2 = UnityEngine.Random.Range(0, list.Count);
			if (list.Count > 0)
			{
				return list[index2];
			}
		}
		return result;
	}

	public Tile GetRandomTile1(bool bWalkable = true, bool bAllowDocked = false)
	{
		List<Tile> list = null;
		list = (bAllowDocked ? GetAllDockedTiles() : aTiles);
		if (list.Count > 0)
		{
			for (int i = 0; i < 50; i++)
			{
				int index = UnityEngine.Random.Range(0, list.Count);
				if (!bWalkable || list[index].bPassable)
				{
					return list[index];
				}
			}
			return list[0];
		}
		return null;
	}

	public Tile GetRandomAtmoTile(bool bSafeCO2 = true)
	{
		if (bDestroyed || aRooms == null)
		{
			return null;
		}
		System.Random randomObjectContainer = new System.Random();
		foreach (Room item in aRooms.OrderBy((Room x) => randomObjectContainer.Next()))
		{
			if (item != null && !item.Void && PledgeSurviveO2.CoHasO2(item.CO) && (!bSafeCO2 || PledgeSurviveCO2.CoHasSafeCO2Lvl(item.CO)))
			{
				Tile randomWalkableTile = item.GetRandomWalkableTile();
				if (randomWalkableTile != null)
				{
					return randomWalkableTile;
				}
			}
		}
		if (bSafeCO2)
		{
			return GetRandomAtmoTile(bSafeCO2: false);
		}
		return null;
	}

	public Tile GetCrewSpawnTile(CondOwner objCO)
	{
		Tile tile = null;
		using (List<CondOwner>.Enumerator enumerator = GetValidCrewSpawnersForCO(objCO).GetEnumerator())
		{
			if (enumerator.MoveNext())
			{
				tile = enumerator.Current.GetComponent<LootSpawner>().GetSpawnTile(this);
			}
		}
		if (tile == null)
		{
			tile = GetRandomAtmoTile();
			if (tile == null)
			{
				tile = GetRandomTile1();
			}
		}
		return tile;
	}

	public Vector3 GetCrewSpawnPosition(CondOwner objCO)
	{
		foreach (CondOwner item in GetValidCrewSpawnersForCO(objCO).Randomize())
		{
			if (!(item == null))
			{
				return item.GetComponent<LootSpawner>().GetSpawnPosition(this);
			}
		}
		return Vector3.zero;
	}

	private List<CondOwner> GetValidCrewSpawnersForCO(CondOwner objCO)
	{
		List<CondOwner> cOs = GetCOs(ctLootSpawner, bSubObjects: false, bAllowDocked: false, bAllowLocked: true);
		List<CondOwner> list = new List<CondOwner>();
		for (int num = cOs.Count - 1; num >= 0; num--)
		{
			string text = cOs[num].mapGUIPropMaps["Panel A"]["strType"];
			if (text == "Loot")
			{
				cOs.RemoveAt(num);
			}
			else if (!(text == "Pspec Loot") && LootSpawner.ShipMatch(this, cOs[num]))
			{
				JsonPersonSpec personSpec = DataHandler.GetPersonSpec(cOs[num].mapGUIPropMaps["Panel A"]["strLoot"]);
				if (personSpec != null && !personSpec.Matches(objCO))
				{
					cOs.RemoveAt(num);
				}
				else
				{
					int result = 1;
					int.TryParse(cOs[num].mapGUIPropMaps["Panel A"]["strCount"], out result);
					if (result >= 0)
					{
						if (result == 0)
						{
							list.Add(cOs[num]);
						}
						else
						{
							list.Insert(0, cOs[num]);
						}
					}
				}
			}
		}
		return list;
	}

	public void ValidateCrewSpawners()
	{
		if (mapICOs == null || mapICOs.Count == 0)
		{
			return;
		}
		List<CondOwner> cOs = GetCOs(ctLootSpawner, bSubObjects: false, bAllowDocked: false, bAllowLocked: true);
		CondOwner condOwner = null;
		CondOwner condOwner2 = null;
		for (int num = cOs.Count - 1; num >= 0; num--)
		{
			if (LootSpawner.ShipMatch(this, cOs[num]) && !(cOs[num].mapGUIPropMaps["Panel A"]["strType"] != "Pspec") && !(cOs[num].mapGUIPropMaps["Panel A"]["strCount"] != "0"))
			{
				if (cOs[num].mapGUIPropMaps["Panel A"]["strLoot"] == "Boarding")
				{
					condOwner = cOs[num];
				}
				else if (cOs[num].mapGUIPropMaps["Panel A"]["strLoot"] == "NotBoarding")
				{
					condOwner2 = cOs[num];
				}
			}
		}
		if (condOwner2 == null)
		{
			condOwner2 = DataHandler.GetCondOwner("SysLootSpawnerNotBoarding");
			using (List<CondOwner>.Enumerator enumerator = aNavs.GetEnumerator())
			{
				if (enumerator.MoveNext())
				{
					Vector2 pos = enumerator.Current.GetPos("use");
					condOwner2.tf.position = pos;
					Debug.Log("Warning: No valid NotBoarding lootspawner found. Adding one at " + pos);
					AddCO(condOwner2, bTiles: true);
				}
			}
			if (condOwner2.ship == null)
			{
				Tile tile = GetRandomAtmoTile();
				if (tile == null)
				{
					tile = GetRandomTile1();
				}
				if (tile == null)
				{
					tile = GetRandomTile1(bWalkable: false);
				}
				condOwner2.tf.position = tile.tf.position;
				Debug.Log("Warning: No valid NotBoarding lootspawner found. Adding one at " + tile.tf.position);
				AddCO(condOwner2, bTiles: true);
			}
		}
		if (!(condOwner == null))
		{
			return;
		}
		condOwner = DataHandler.GetCondOwner("SysLootSpawnerBoarding");
		using (List<CondOwner>.Enumerator enumerator = aDocksys.GetEnumerator())
		{
			if (enumerator.MoveNext())
			{
				Vector2 pos2 = enumerator.Current.GetPos("use");
				condOwner.tf.position = pos2;
				Debug.Log("Warning: No valid Boarding lootspawner found. Adding one at " + pos2);
				AddCO(condOwner, bTiles: true);
			}
		}
		if (condOwner.ship == null)
		{
			Tile tile2 = GetRandomAtmoTile();
			if (tile2 == null)
			{
				tile2 = GetRandomTile1();
			}
			if (tile2 == null)
			{
				tile2 = GetRandomTile1(bWalkable: false);
			}
			condOwner.tf.position = tile2.tf.position;
			Debug.Log("Warning: No valid Boarding lootspawner found. Adding one at " + tile2.tf.position);
			AddCO(condOwner, bTiles: true);
		}
		condOwner.GetComponent<LootSpawner>().UpdateAppearance();
	}

	public Room GetRoomAtWorldCoords1(Vector2 vPos, bool bAllowDocked)
	{
		Tile tileAtWorldCoords = GetTileAtWorldCoords1(vPos.x, vPos.y, bAllowDocked);
		if (tileAtWorldCoords != null)
		{
			return tileAtWorldCoords.room;
		}
		return null;
	}

	public void ShiftTorwardsClosestCrewMember(CondOwner co, float shiftDistance)
	{
		if (!(co == null))
		{
			Vector3? closestCrewMemberPosition = GetClosestCrewMemberPosition(co.tf.position);
			if (closestCrewMemberPosition.HasValue)
			{
				Vector2 v = Vector2.MoveTowards(co.tf.position.ToVector2(), closestCrewMemberPosition.Value.ToVector2(), shiftDistance);
				co.tf.position = v.ToVector3(co.tf.position.z);
			}
		}
	}

	private Vector3? GetClosestCrewMemberPosition(Vector3 originPosition)
	{
		List<CondOwner> people = GetPeople(bAllowDocked: false);
		if (people == null)
		{
			return null;
		}
		return MathUtils.GetClosestPosition(people.Select((CondOwner x) => x.tf.position).ToArray(), originPosition);
	}

	public List<JsonZone> GetZones(string strZoneCond, CondOwner coTest, bool bAllowDocked, bool includeShallowLoaded = false)
	{
		List<JsonZone> list = new List<JsonZone>();
		if (mapZones == null)
		{
			return list;
		}
		List<JsonZone> list2 = mapZones.Values.ToList();
		if (includeShallowLoaded && json != null && json.aZones != null)
		{
			JsonZone[] aZones = json.aZones;
			foreach (JsonZone jZone in aZones)
			{
				if (!list2.Any((JsonZone x) => x.strName == jZone.strName))
				{
					list2.Add(jZone);
				}
			}
		}
		foreach (JsonZone item in list2)
		{
			if (item.aTileConds == null)
			{
				Debug.LogWarning("Warning: null aTileConds on zone " + item.strName + " in ship " + strRegID);
			}
			else if ((strZoneCond == null || Array.FindIndex(item.aTileConds, (string str) => str == strZoneCond) >= 0) && item.Matches(coTest, bCheckOwner: false))
			{
				list.Add(item);
			}
		}
		if (bAllowDocked)
		{
			foreach (KeyValuePair<string, Ship> item2 in aDocked)
			{
				if (item2.Value != null)
				{
					list.AddRange(item2.Value.GetZones(strZoneCond, coTest, bAllowDocked: false, includeShallowLoaded));
				}
			}
		}
		return list;
	}

	public List<CondOwner> GetCOsInZone(string strZone, CondTrigger ct, bool bAllowLocked)
	{
		List<CondOwner> result = new List<CondOwner>();
		JsonZone value = null;
		if (!mapZones.TryGetValue(strZone, out value))
		{
			return result;
		}
		return GetCOsInZone(value, ct, bAllowLocked);
	}

	public List<CondOwner> GetCOsInZone(JsonZone jz, CondTrigger ct, bool bAllowLocked, bool bAllowDocked = true)
	{
		List<CondOwner> list = new List<CondOwner>();
		if (jz == null)
		{
			return list;
		}
		int count = aTiles.Count;
		int[] array = jz.aTiles;
		foreach (int num in array)
		{
			if (num < 0 || num >= count)
			{
				continue;
			}
			List<CondOwner> list2 = new List<CondOwner>();
			GetCOsAtWorldCoords1(aTiles[num].tf.position, ct, bAllowDocked, bAllowLocked, list2);
			foreach (CondOwner item in list2)
			{
				if (!(item.objCOParent != null) && list.IndexOf(item) < 0)
				{
					list.Add(item);
				}
			}
		}
		return list;
	}

	public bool CanZoneFitItems(JsonZone jz, List<CondOwner> coItems)
	{
		if (jz == null || coItems == null || coItems.Count == 0)
		{
			if (coItems != null)
			{
				return coItems.Count == 0;
			}
			return true;
		}
		List<CondOwner> cOsInZone = GetCOsInZone(jz, CtHaulDest, bAllowLocked: false);
		HashSet<int> hashSet = new HashSet<int>();
		foreach (CondOwner coItem in coItems)
		{
			if (coItem == null || coItem.Item == null)
			{
				continue;
			}
			bool flag = false;
			foreach (CondOwner item in cOsInZone)
			{
				if (item.CanStackOnItem(coItem) > 0)
				{
					flag = true;
					break;
				}
			}
			if (flag)
			{
				cOsInZone.Add(coItem);
				continue;
			}
			foreach (CondOwner item2 in cOsInZone)
			{
				if (!(item2 == coItem) && item2.CanStackOnItem(coItem) > 0)
				{
					flag = true;
					break;
				}
			}
			if (flag)
			{
				cOsInZone.Add(coItem);
				continue;
			}
			Vector2 vector = default(Vector2);
			if (coItem.Item.nWidthInTiles % 2 == 0)
			{
				vector.x = 0.5f;
			}
			if (coItem.Item.nHeightInTiles % 2 == 0)
			{
				vector.y = 0.5f;
			}
			int[] array = jz.aTiles;
			foreach (int num in array)
			{
				if (num >= 0 && !hashSet.Contains(num))
				{
					Vector2 vector2 = GetWorldCoordsAtTileIndex1(num) + vector;
					if (coItem.Item.CheckFit(vector2, this, null, jz))
					{
						MarkTileIndicesOccupied(hashSet, coItem, vector2);
						flag = true;
						break;
					}
				}
			}
			if (flag)
			{
				cOsInZone.Add(coItem);
				continue;
			}
			return false;
		}
		return true;
	}

	private void MarkTileIndicesOccupied(HashSet<int> occupiedTiles, CondOwner co, Vector3 vFits)
	{
		Item item = co.Item;
		float num = vFits.x - ((float)item.nWidthInTiles / 2f - 0.5f);
		float num2 = vFits.y + ((float)item.nHeightInTiles / 2f - 0.5f);
		for (int i = 0; i < item.nHeightInTiles; i++)
		{
			for (int j = 0; j < item.nWidthInTiles; j++)
			{
				int tileIndexAtWorldCoords = GetTileIndexAtWorldCoords(num + (float)j, num2 - (float)i);
				if (tileIndexAtWorldCoords >= 0)
				{
					occupiedTiles.Add(tileIndexAtWorldCoords);
				}
			}
		}
	}

	public List<CondOwner> GetCOsInLocalZone(JsonZone jz, CondTrigger ct)
	{
		List<CondOwner> list = new List<CondOwner>();
		if (jz == null)
		{
			return list;
		}
		int[] array = jz.aTiles;
		foreach (int index in array)
		{
			List<CondOwner> list2 = new List<CondOwner>();
			GetCOsAtLocalCoords(aTiles[index].tf.position, ct, list2);
			foreach (CondOwner item in list2)
			{
				if (!(item.objCOParent != null) && list.IndexOf(item) < 0)
				{
					list.Add(item);
				}
			}
		}
		return list;
	}

	private void GetCOsAtLocalCoords(Vector2 vPos, CondTrigger ct, List<CondOwner> aOut)
	{
		int num = Physics.RaycastNonAlloc(new Ray(new Vector3(vPos.x, vPos.y, -20f), Vector3.forward), aHitsGetCOs, 100f);
		for (int i = num; i < aHitsGetCOs.Length; i++)
		{
			aHitsGetCOs[i].distance = float.PositiveInfinity;
		}
		Array.Sort(aHitsGetCOs, (RaycastHit x, RaycastHit y) => x.distance.CompareTo(y.distance));
		Room roomAtWorldCoords = GetRoomAtWorldCoords1(vPos, bAllowDocked: false);
		CondOwner condOwner = null;
		if (roomAtWorldCoords != null)
		{
			condOwner = roomAtWorldCoords.CO;
		}
		for (int num2 = 0; num2 < num; num2++)
		{
			RaycastHit raycastHit = aHitsGetCOs[num2];
			if (raycastHit.transform == null)
			{
				continue;
			}
			CondOwner component = raycastHit.transform.GetComponent<CondOwner>();
			if (!(condOwner == component) && component != null && component.ship != null && component.ship == this)
			{
				bool flag = false;
				if (ct == null)
				{
					flag = true;
				}
				else if ((ct.strCondName == null || ct.strCondName == "") && ct.Triggered(component))
				{
					flag = true;
				}
				if (flag && aOut.IndexOf(component) < 0)
				{
					aOut.Add(component);
				}
			}
		}
		if (condOwner != null && (ct == null || ct.Triggered(condOwner)) && aOut.IndexOf(condOwner) < 0)
		{
			aOut.Add(condOwner);
		}
	}

	public bool ChangeCOID(CondOwner co, string strIDNew)
	{
		bool result = false;
		if (mapICOs.ContainsKey(co.strID))
		{
			mapICOs.Remove(co.strID);
			mapICOs[strIDNew] = co;
			result = true;
		}
		else
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (item.Value != null && item.Value.ChangeCOID(co, strIDNew))
				{
					result = true;
					break;
				}
			}
		}
		return result;
	}

	public bool CheckCOIDProblem(CondOwner co)
	{
		if (mapICOs == null || co == null)
		{
			return true;
		}
		CondOwner condOwner = null;
		CondOwner condOwner2 = null;
		if (mapICOs.ContainsKey(co.strID))
		{
			condOwner = mapICOs[co.strID];
		}
		if (mapICOs.Values.Contains(co))
		{
			condOwner2 = co;
		}
		return condOwner != condOwner2;
	}

	public bool CheckCOIDProblem(string strCOID)
	{
		if (mapICOs == null || strCOID == null)
		{
			return true;
		}
		CondOwner condOwner = null;
		if (mapICOs.ContainsKey(strCOID))
		{
			condOwner = mapICOs[strCOID];
		}
		if (condOwner != null)
		{
			return condOwner.ship != this;
		}
		return true;
	}

	public bool HasOpenDockingPorts()
	{
		return GetOpenDockingPorts().Count > 0;
	}

	public List<string> GetOpenDockingPorts()
	{
		List<string> list = new List<string>(aDockingPorts);
		foreach (KeyValuePair<string, Ship> dockedShipsAndPortID in GetDockedShipsAndPortIDs())
		{
			list.Remove(dockedShipsAndPortID.Key);
		}
		return list;
	}

	public List<string> GetAllDockingPorts()
	{
		return new List<string>(aDockingPorts);
	}

	public string GetPortIdForDockedShip(string regId)
	{
		if (aDocked != null && aDocked.Count > 0)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (item.Value != null && item.Value.strRegID == regId)
				{
					return item.Key;
				}
			}
		}
		if (json != null && json.aDocked != null && json.aDocked.Count > 0)
		{
			foreach (KeyValuePair<string, string> item2 in json.aDocked)
			{
				if (item2.Value != null && item2.Value == regId)
				{
					return item2.Key;
				}
			}
		}
		return null;
	}

	public List<(string portIDUs, string portIDIncoming)> GetAvailableDockingPorts(Ship incomingShip, bool earlyOut = true)
	{
		List<string> openDockingPorts = GetOpenDockingPorts();
		if (openDockingPorts.Count == 0)
		{
			return null;
		}
		List<string> openDockingPorts2 = incomingShip.GetOpenDockingPorts();
		if (openDockingPorts2.Count == 0)
		{
			return null;
		}
		Grid<DataCOWrapper> grid = GridUtils.CreateFullGrid(incomingShip);
		Grid<DataCOWrapper> grid2 = GridUtils.CreateFullGrid(this);
		List<DockingPortDTO> list = GridUtils.GatherDockingPortData(openDockingPorts, grid2);
		if (list.Count == 0)
		{
			return null;
		}
		List<(string, string)> list2 = null;
		foreach (string item in openDockingPorts2)
		{
			DockingPortDTO dockingPortDTO = GridUtils.FindDockingPort(grid, item);
			if (dockingPortDTO == null)
			{
				continue;
			}
			foreach (DockingPortDTO item2 in list)
			{
				Ostranauts.Pathing.Vector2Int dockOffset;
				int incomingDockRotation = GridUtils.GetIncomingDockRotation(item2.Rotation, dockingPortDTO.Rotation, out dockOffset);
				if (GridUtils.CanOverlay(grid2, grid, incomingDockRotation, item2.GridPos, dockingPortDTO.GridPos, dockOffset))
				{
					if (earlyOut)
					{
						return new List<(string, string)> { (item2.PortID, dockingPortDTO.PortID) };
					}
					if (list2 == null)
					{
						list2 = new List<(string, string)>();
					}
					list2.Add((item2.PortID, dockingPortDTO.PortID));
				}
			}
		}
		return list2;
	}

	public List<JsonItem> CreateMooringPorts(Ship incomingShip)
	{
		Grid<DataCOWrapper> grid = GridUtils.CreateFullGrid(incomingShip);
		Grid<DataCOWrapper> grid2 = GridUtils.CreateFullGrid(this);
		Point? point = DamageSystem.FindIntersect(grid2.Width, grid2.Height, incomingShip.objSS.vPos);
		if (!point.HasValue)
		{
			return null;
		}
		Point? point2 = incomingShip.DamageSystem.FindIntersect(grid.Width, grid.Height, objSS.vPos);
		if (!point2.HasValue)
		{
			return null;
		}
		Ostranauts.Pathing.Vector2Int vector2Int = new Ostranauts.Pathing.Vector2Int((int)point.Value.X, (int)point.Value.Y);
		Ostranauts.Pathing.Vector2Int vector2Int2 = new Ostranauts.Pathing.Vector2Int((int)point2.Value.X, (int)point2.Value.Y);
		int outFacingRotation = GridUtils.GetOutFacingRotation(vector2Int, grid2.Width, grid2.Height);
		int outFacingRotation2 = GridUtils.GetOutFacingRotation(vector2Int2, grid.Width, grid.Height);
		Ostranauts.Pathing.Vector2Int dockOffset;
		int incomingDockRotation = GridUtils.GetIncomingDockRotation(outFacingRotation, outFacingRotation2, out dockOffset);
		if (GridUtils.CanOverlay(grid2, grid, incomingDockRotation, vector2Int, vector2Int2, new Ostranauts.Pathing.Vector2Int(0, 0)))
		{
			Ostranauts.Pathing.Vector2Int vector2Int3 = GridUtils.FindCurrentOffset(this, grid2);
			Ostranauts.Pathing.Vector2Int vector2Int4 = GridUtils.FindCurrentOffset(incomingShip, grid);
			return new List<JsonItem>
			{
				new JsonItem
				{
					strName = "MooringPort",
					fX = vector2Int.x + vector2Int3.x,
					fY = vector2Int.y + vector2Int3.y,
					fRotation = outFacingRotation,
					strID = "MP|" + DataHandler.GetNextID()
				},
				new JsonItem
				{
					strName = "MooringPort",
					fX = vector2Int2.x + vector2Int4.x,
					fY = vector2Int2.y + vector2Int4.y,
					fRotation = outFacingRotation2,
					strID = "MP|I|" + DataHandler.GetNextID()
				}
			};
		}
		return null;
	}

	public bool Dock(Ship dockingTarget)
	{
		List<(string, string)> availableDockingPorts = GetAvailableDockingPorts(dockingTarget);
		if (availableDockingPorts == null || availableDockingPorts.Count == 0)
		{
			return false;
		}
		Dock(dockingTarget, bSyncOnly: false, availableDockingPorts.First().Item2, availableDockingPorts.First().Item1);
		return true;
	}

	public void ResetDockedCache()
	{
		CachedAllDockedShips = null;
		IReadOnlyList<Ship> allDockedShips = GetAllDockedShips();
		if (allDockedShips != null)
		{
			foreach (Ship item in allDockedShips)
			{
				if (item != null)
				{
					item.CachedAllDockedShips = null;
				}
			}
		}
		CachedAllDockedShips = null;
	}

	public void Dock(Ship dockingTarget, bool bSyncOnly, string dockingPortTarget, string dockingPortUs)
	{
		ResetDockedCache();
		objSS.bGrounded = Classification == TypeClassification.GroundStation || Classification == TypeClassification.GroundStationUnfinished;
		if (dockingTarget == null || dockingTarget == this || bDestroyed)
		{
			return;
		}
		if (string.IsNullOrEmpty(dockingPortTarget))
		{
			Debug.LogWarning(strRegID + " dockingPortOtherShip empty id when docking to " + dockingTarget.strRegID);
			LogAdd(strRegID + " dockingPortOtherShip empty id when docking to " + dockingTarget.strRegID);
			return;
		}
		if (string.IsNullOrEmpty(dockingPortUs))
		{
			Debug.LogWarning(strRegID + "dockingPortus empty id when docking to " + dockingTarget.strRegID);
			LogAdd(strRegID + "dockingPortus empty id when docking to " + dockingTarget.strRegID);
			return;
		}
		if (aDocked == null)
		{
			aDocked = new Dictionary<string, Ship>();
		}
		int count = aDocked.Count;
		Dictionary<string, string> dictionary = new Dictionary<string, string> { { dockingPortUs, dockingTarget.strRegID } };
		foreach (KeyValuePair<string, Ship> item in aDocked)
		{
			if (item.Value != null && !dictionary.ContainsValue(item.Value.strRegID) && !dictionary.ContainsKey(item.Key))
			{
				dictionary.Add(item.Key, item.Value.strRegID);
			}
		}
		if (json != null && json.aDocked != null)
		{
			foreach (KeyValuePair<string, string> item2 in json.aDocked)
			{
				if (!dictionary.ContainsValue(item2.Value) && !dictionary.ContainsKey(item2.Key))
				{
					dictionary.Add(item2.Key, item2.Value);
				}
			}
		}
		aDocked.Clear();
		foreach (KeyValuePair<string, string> item3 in dictionary)
		{
			Ship shipByRegID = CrewSim.system.GetShipByRegID(item3.Value);
			if (shipByRegID != null)
			{
				aDocked.Add(item3.Key, shipByRegID);
				continue;
			}
			Debug.Log("Found null ship in docked list. Removing from dict: " + item3.Value);
			CrewSim.system.RemoveShip(item3.Value);
		}
		if (json != null)
		{
			json.aDocked = dictionary.CloneShallow();
		}
		if (bSyncOnly)
		{
			SyncDockingGroups(dockingTarget);
		}
		if (bSyncOnly || aDocked.Count == count)
		{
			return;
		}
		if (CrewSim.coPlayer != null && aPeople.IndexOf(CrewSim.coPlayer.pspec) >= 0 && dockingTarget.HasDockingPorts)
		{
			AudioManager.am.PlayAudioEmitter("ShipDockClamp", bLoop: false);
		}
		if (!objSS.bIsBO)
		{
			objSS.UnlockFromBO();
		}
		UnlockFromOrbit();
		objSS.vVelX = dockingTarget.objSS.vVelX;
		objSS.vVelY = dockingTarget.objSS.vVelY;
		objSS.fA = dockingTarget.objSS.fA;
		objSS.fW = dockingTarget.objSS.fW;
		CreateDockingGroupFormation(dockingTarget, dockingPortTarget, dockingPortUs);
		foreach (KeyValuePair<string, Ship> item4 in aDocked.ToList())
		{
			if (item4.Value != null)
			{
				if (item4.Value == dockingTarget)
				{
					string dockingPortUs2 = ((item4.Value.strRegID == dockingTarget.strRegID) ? dockingPortTarget : item4.Value.GetPortIdForDockedShip(strRegID));
					item4.Value.Dock(this, bSyncOnly: false, item4.Key, dockingPortUs2);
				}
				if (item4.Value.objSS.bIsBO)
				{
					objSS.bBOLocked = true;
					objSS.strBOPORShip = item4.Value.objSS.strBOPORShip;
				}
				if (!objSS.bGrounded && (item4.Value.Classification == TypeClassification.GroundStation || item4.Value.Classification == TypeClassification.GroundStationUnfinished))
				{
					objSS.bGrounded = true;
				}
			}
		}
		AddDockingFees(dockingTarget);
		LogAdd(DataHandler.GetString("NAV_LOG_DOCK") + dockingTarget.strRegID + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
		CheckAccruedWear();
		fWearManeuver = 0f;
		OnDock.Invoke(this, dockingTarget);
	}

	private float GetAirlockRotation(string airlockID)
	{
		if (LoadState > Loaded.Shallow)
		{
			if (aDocksys == null)
			{
				return 0f;
			}
			foreach (CondOwner aDocksy in aDocksys)
			{
				if (aDocksy.strID == airlockID)
				{
					return (aDocksy.Item.fLastRotation + (float)nGridRotation) % 360f;
				}
			}
		}
		else
		{
			if (json == null || json.aItems == null)
			{
				return 0f;
			}
			JsonItem[] aItems = json.aItems;
			foreach (JsonItem jsonItem in aItems)
			{
				if (jsonItem.strID == airlockID)
				{
					return (jsonItem.fRotation + (float)nGridRotation) % 360f;
				}
			}
		}
		return 0f;
	}

	private void RebuildDockingFormation(string skipShipId = null)
	{
		if (aDocked.Count == 0)
		{
			return;
		}
		foreach (var (dockingPortOtherShip, ship2) in aDocked)
		{
			if (string.IsNullOrEmpty(skipShipId) || !(ship2.strRegID == skipShipId))
			{
				string portIdForDockedShip = ship2.GetPortIdForDockedShip(strRegID);
				if (portIdForDockedShip != null)
				{
					ship2.PlaceAtAirlocks(portIdForDockedShip, dockingPortOtherShip, this);
					ship2.RebuildDockingFormation(strRegID);
				}
			}
		}
	}

	public void PlaceAtAirlocks(string dockingPortUs, string dockingPortOtherShip, Ship dockingTarget)
	{
		float airlockRotation = GetAirlockRotation(dockingPortUs);
		float airlockRotation2 = dockingTarget.GetAirlockRotation(dockingPortOtherShip);
		ShipSitu shipSitu = dockingTarget.objSS;
		float num = shipSitu.GetRadiusAU() + objSS.GetRadiusAU() + 6.684587E-11f;
		Point normalized = shipSitu.GetDirectionVector(invert: false).normalized;
		float f = airlockRotation2 * (MathF.PI / 180f);
		Point normalized2 = new Point(normalized.X * (double)Mathf.Cos(f) - normalized.Y * (double)Mathf.Sin(f), normalized.X * (double)Mathf.Sin(f) + normalized.Y * (double)Mathf.Cos(f)).normalized;
		objSS.vBOOffsetx = normalized2.X * (double)num;
		objSS.vBOOffsety = normalized2.Y * (double)num;
		objSS.vPosx = shipSitu.vPosx + objSS.vBOOffsetx;
		objSS.vPosy = shipSitu.vPosy + objSS.vBOOffsety;
		objSS.fW = shipSitu.fW;
		objSS.fA = shipSitu.fA;
		objSS.vVelX = shipSitu.vVelX;
		objSS.vVelY = shipSitu.vVelY;
		objSS.fRot = (float)GetRequiredShipRotation(objSS.vPos, shipSitu.vPos, airlockRotation);
	}

	private double GetRequiredShipRotation(Point shipPos, Point otherPos, float dockLocalAngle)
	{
		Point point = otherPos - shipPos;
		return (Math.Atan2(0.0 - point.X, point.Y) * 57.295780181884766 - (double)dockLocalAngle) * 0.01745329238474369;
	}

	private void SyncDockingGroups(Ship dockingTarget, bool isMooringTarget = false)
	{
		DockGroup dockGroup = DockGroup;
		DockGroup dockGroup2 = dockingTarget.DockGroup;
		if (dockGroup != null && dockGroup.DockedShips.Any((DockGroupMember s) => s.RegId == dockingTarget.strRegID))
		{
			return;
		}
		if (dockGroup != null && dockGroup2 != null)
		{
			if (dockGroup != dockGroup2)
			{
				if (dockGroup.Mass > dockGroup2.Mass)
				{
					dockGroup.MergeGroups(dockGroup2);
				}
				else
				{
					dockGroup2.MergeGroups(dockGroup);
				}
			}
		}
		else if (dockGroup2 != null)
		{
			dockGroup2.AddShip(this);
		}
		else if (dockGroup != null)
		{
			dockGroup.AddShip(dockingTarget, isMooringTarget);
		}
		else
		{
			DockGroup dockGroup3 = new DockGroup();
			dockGroup3.AddShip(this);
			dockGroup3.AddShip(dockingTarget, isMooringTarget);
		}
	}

	private void CreateDockingGroupFormation(Ship dockingTarget, string dockingPortTarget, string dockingPortUs)
	{
		if (objSS == null)
		{
			return;
		}
		if (HasDockGroup && DockGroup.DockedShips.Any((DockGroupMember s) => s.RegId == dockingTarget.strRegID))
		{
			DockGroup.UpdateAnchor();
		}
		else if (!HasDockGroup && !dockingTarget.HasDockGroup)
		{
			if (dockingTarget.IsBOLockedInAnyWay(strRegID))
			{
				new DockGroup().AddShip(this);
				DockGroup.DockGroupWithBO(dockingTarget, dockingPortTarget, this, dockingPortUs);
				return;
			}
			if (IsBOLockedInAnyWay(dockingTarget.strRegID))
			{
				new DockGroup().AddShip(dockingTarget);
				dockingTarget.DockGroup.DockGroupWithBO(this, dockingPortUs, dockingTarget, dockingPortTarget);
				return;
			}
			DockGroup dockGroup = new DockGroup();
			dockGroup.AddShip(this);
			PlaceAtAirlocks(dockingPortUs, dockingPortTarget, dockingTarget);
			dockGroup.AddShip(dockingTarget);
		}
		else if (HasDockGroup && !dockingTarget.HasDockGroup)
		{
			if (dockingTarget.IsBOLockedInAnyWay(strRegID))
			{
				DockGroup.DockGroupWithBO(dockingTarget, dockingPortTarget, this, dockingPortUs);
				return;
			}
			dockingTarget.PlaceAtAirlocks(dockingPortTarget, dockingPortUs, this);
			DockGroup.AddShip(dockingTarget);
		}
		else if (!HasDockGroup && dockingTarget.HasDockGroup)
		{
			if (IsBOLockedInAnyWay(dockingTarget.strRegID))
			{
				dockingTarget.DockGroup.DockGroupWithBO(this, dockingPortUs, dockingTarget, dockingPortTarget);
				return;
			}
			PlaceAtAirlocks(dockingPortUs, dockingPortTarget, dockingTarget);
			dockingTarget.DockGroup.AddShip(this);
		}
		else if (dockingTarget.HasDockGroup && HasDockGroup)
		{
			if (dockingTarget.IsBOLockedInAnyWay(strRegID))
			{
				dockingTarget.DockGroup.MergeTargetGroupIntoUs(this, dockingPortUs, dockingTarget, dockingPortTarget);
			}
			else
			{
				DockGroup.MergeTargetGroupIntoUs(dockingTarget, dockingPortTarget, this, dockingPortUs);
			}
		}
		else
		{
			Debug.LogWarning("Unhandled group config");
		}
	}

	public void MoorTo(Ship mooringTarget, string dockingPortOtherShip, string dockingPortUs, bool bSyncOnly = false)
	{
		ResetDockedCache();
		if (mooringTarget == null || mooringTarget == this || bDestroyed)
		{
			return;
		}
		if (aDocked == null)
		{
			aDocked = new Dictionary<string, Ship>();
		}
		if (string.IsNullOrEmpty(dockingPortUs))
		{
			Debug.LogWarning(strRegID + " skipped MooringTo because dockingPortUs is empty for target " + mooringTarget.strRegID + " with ID: " + dockingPortOtherShip);
			return;
		}
		Dictionary<string, string> dictionary = new Dictionary<string, string> { { dockingPortUs, mooringTarget.strRegID } };
		foreach (KeyValuePair<string, Ship> item in aDocked)
		{
			if (item.Value != null && !dictionary.ContainsValue(item.Value.strRegID) && !dictionary.ContainsKey(item.Key))
			{
				dictionary.Add(item.Key, item.Value.strRegID);
			}
		}
		if (!aDockingPorts.Contains(dockingPortUs))
		{
			aDockingPorts.Add(dockingPortUs);
		}
		if (json.aDockingPorts == null || !json.aDockingPorts.Contains(dockingPortUs))
		{
			List<string> list = ((json.aDockingPorts != null) ? json.aDockingPorts.ToList() : new List<string>());
			list.Add(dockingPortUs);
			json.aDockingPorts = list.ToArray();
		}
		if (json != null && json.aDocked != null)
		{
			foreach (KeyValuePair<string, string> item2 in json.aDocked)
			{
				if (!dictionary.ContainsValue(item2.Value) && !dictionary.ContainsKey(item2.Key))
				{
					dictionary.Add(item2.Key, item2.Value);
				}
			}
		}
		aDocked.Clear();
		foreach (KeyValuePair<string, string> item3 in dictionary)
		{
			Ship shipByRegID = CrewSim.system.GetShipByRegID(item3.Value);
			if (shipByRegID != null)
			{
				aDocked.Add(item3.Key, shipByRegID);
				continue;
			}
			Debug.Log("Found null ship in docked list. Removing from dict: " + item3.Value);
			CrewSim.system.RemoveShip(item3.Value);
		}
		if (json != null)
		{
			json.aDocked = dictionary.CloneShallow();
		}
		if (!bSyncOnly)
		{
			UnlockFromOrbit();
			if (dockingPortUs.Contains("MP|I|"))
			{
				SyncDockingGroups(mooringTarget, isMooringTarget: true);
			}
			mooringTarget.MoorTo(this, dockingPortUs, dockingPortOtherShip, bSyncOnly: true);
			LogAdd(DataHandler.GetString("NAV_LOG_MOORED") + mooringTarget.strRegID + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
		}
	}

	public void UnMoorFrom(Ship oldMooringTarget)
	{
		ResetDockedCache();
		if (oldMooringTarget == null || oldMooringTarget.bDestroyed || oldMooringTarget == this)
		{
			return;
		}
		string portIdForDockedShip = GetPortIdForDockedShip(oldMooringTarget.strRegID);
		if (!RemoveDockedShip(oldMooringTarget))
		{
			return;
		}
		oldMooringTarget.UnMoorFrom(this);
		mapICOs.TryGetValue(portIdForDockedShip, out var value);
		if (value != null)
		{
			RemoveCO(value);
			value.Destroy();
		}
		if (!mapICOs.Remove(portIdForDockedShip))
		{
			List<JsonItem> list = json.aItems.ToList();
			for (int num = list.Count - 1; num >= 0; num--)
			{
				JsonItem jsonItem = list[num];
				if (jsonItem != null && !(jsonItem.strID != portIdForDockedShip))
				{
					list.RemoveAt(num);
					json.aItems = list.ToArray();
					break;
				}
			}
		}
		if (aDockingPorts.Contains(portIdForDockedShip))
		{
			aDockingPorts.Remove(portIdForDockedShip);
		}
		if (json.aDockingPorts != null && json.aDockingPorts.Contains(portIdForDockedShip))
		{
			List<string> list2 = json.aDockingPorts.ToList();
			list2.Remove(portIdForDockedShip);
			json.aDockingPorts = list2.ToArray();
		}
		if (!objSS.bIsBO && !objSS.bBOLocked)
		{
			Vector2 ptGrav = default(Vector2);
			BodyOrbit boClosest = null;
			BodyOrbit greatestGravBO = CrewSim.system.GetGreatestGravBO(objSS, StarSystem.fEpoch, ref ptGrav, ref boClosest);
			if (greatestGravBO != null)
			{
				objSS.strBOPORShip = greatestGravBO.strName;
			}
			else
			{
				objSS.strBOPORShip = null;
			}
			objSS.bBOLocked = false;
		}
		UnlockFromOrbit();
		if (HasDockGroup)
		{
			DockGroup.UndockShip(this);
			if (aDocked.Count > 0)
			{
				DockGroup dockGroup = new DockGroup();
				foreach (Ship allDockedShip in GetAllDockedShips())
				{
					dockGroup.AddShip(allDockedShip);
				}
				dockGroup.AddShip(this);
			}
		}
		LogAdd(DataHandler.GetString("NAV_LOG_UNMOORED") + oldMooringTarget.strRegID + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
	}

	public void Undock(Ship objShip)
	{
		ResetDockedCache();
		if (objShip == null || objShip.bDestroyed || objShip == this)
		{
			return;
		}
		if (LoadState == Loaded.Full)
		{
			UpdateRating();
		}
		if (!RemoveDockedShip(objShip))
		{
			return;
		}
		objShip.Undock(this);
		if (CrewSim.coPlayer != null && aPeople.IndexOf(CrewSim.coPlayer.pspec) >= 0 && objShip.HasDockingPorts)
		{
			AudioManager.am.PlayAudioEmitter("ShipDockUnclamp", bLoop: false);
		}
		if (!objSS.bIsBO)
		{
			objSS.vAccEx = Vector2.zero;
			BodyOrbit nearestBO = CrewSim.system.GetNearestBO(objSS, StarSystem.fEpoch, bIncludePlaceholders: false);
			bool flag = false;
			if (DMGStatus == Damage.Derelict && nearestBO != null && !NavAIManned && !NavPlayerManned)
			{
				nearestBO.UpdateTime(StarSystem.fEpoch);
				double dX = nearestBO.dVelX - objSS.vVelX;
				double dY = nearestBO.dVelY - objSS.vVelY;
				if (MathUtils.GetMagnitude(dX, dY) / 6.6845869117759804E-12 <= CollisionManager.dMaxSafeV)
				{
					objSS.LockToBO(nearestBO);
					flag = true;
				}
			}
			if (!flag)
			{
				Vector2 ptGrav = default(Vector2);
				BodyOrbit boClosest = null;
				BodyOrbit greatestGravBO = CrewSim.system.GetGreatestGravBO(objSS, StarSystem.fEpoch, ref ptGrav, ref boClosest);
				if (greatestGravBO != null)
				{
					objSS.strBOPORShip = greatestGravBO.strName;
				}
				else
				{
					objSS.strBOPORShip = null;
				}
				objSS.bBOLocked = false;
			}
		}
		UnlockFromOrbit();
		if (HasDockGroup)
		{
			DockGroup.UndockShip(this);
			if (aDocked.Count > 0)
			{
				DockGroup dockGroup = new DockGroup();
				foreach (Ship allDockedShip in GetAllDockedShips())
				{
					dockGroup.AddShip(allDockedShip);
				}
				dockGroup.AddShip(this);
			}
		}
		foreach (KeyValuePair<string, Ship> item in aDocked)
		{
			if (item.Value != null)
			{
				item.Value.Undock(objShip);
				if (item.Value.objSS.bIsBO)
				{
					objSS.bBOLocked = true;
					objSS.strBOPORShip = item.Value.objSS.strBOPORShip;
				}
			}
		}
		if (objShip.objSS.bIsBO && HasDockGroup)
		{
			RebuildDockingFormation();
			DockGroup.UpdateAnchor();
		}
		objSS.bGrounded = Classification == TypeClassification.GroundStation || Classification == TypeClassification.GroundStationUnfinished;
		if (!objSS.bGrounded)
		{
			foreach (Ship allDockedShip2 in GetAllDockedShips())
			{
				if (allDockedShip2.Classification == TypeClassification.GroundStation || allDockedShip2.Classification == TypeClassification.GroundStationUnfinished)
				{
					objSS.bGrounded = true;
					break;
				}
			}
		}
		fWearManeuver = 0f;
		RemoveDockingFees(objShip);
		LogAdd(DataHandler.GetString("NAV_LOG_UNDOCK") + objShip.strRegID + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
	}

	private bool RemoveDockedShip(Ship objShip)
	{
		bool result = false;
		if (aDocked != null)
		{
			result = aDocked.TryRemoveValue(objShip);
		}
		if (json != null && json.aDocked != null && json.aDocked.ContainsValue(objShip.strRegID))
		{
			Dictionary<string, string> dictionary = new Dictionary<string, string>();
			foreach (KeyValuePair<string, string> item in json.aDocked)
			{
				if (!(item.Value == objShip.strRegID))
				{
					dictionary.Add(item.Key, item.Value);
				}
			}
			json.aDocked = dictionary;
			result = true;
		}
		return result;
	}

	private void RemoveDockingFees(Ship objShip)
	{
		if (CrewSim.coPlayer == null || objShip == null || !objShip.objSS.bIsBO || (!(CrewSim.system.GetShipOwner(strRegID) == CrewSim.coPlayer.strID) && CrewSim.coPlayer.ship != this))
		{
			return;
		}
		List<LedgerLI> unpaidLIs = Ledger.GetUnpaidLIs(null, CrewSim.coPlayer.strID, null, bIncludeRepeating: true, strRegID);
		List<LedgerLI> list = new List<LedgerLI>();
		string value = DataHandler.GetString("GUI_REFUEL_SERVICE_DOCK");
		string value2 = DataHandler.GetString("GUI_REFUEL_SERVICE_FACILITIES");
		foreach (LedgerLI item in unpaidLIs)
		{
			if (item.Repeats != LedgerLI.Frequency.OneTime && item.strDesc != null && (item.strDesc.Contains(value) || item.strDesc.Contains(value2)))
			{
				list.Add(item);
			}
		}
		foreach (LedgerLI item2 in list)
		{
			Ledger.RemoveLI(item2);
		}
	}

	private void AddDockingFees(Ship dockingTarget)
	{
		if (dockingTarget.objSS.bIsBO && !dockingTarget.objSS.bIsNoFees && !(CrewSim.coPlayer == null) && CrewSim.coPlayer.ship == this)
		{
			CollisionManager.RefreshCurrentRegion();
			Ship nearestStationRegional = CrewSim.system.GetNearestStationRegional(objSS.vPosx, objSS.vPosy);
			string strPayee = ((nearestStationRegional == null) ? CollisionManager.strATCClosest : nearestStationRegional.strRegID) + DataHandler.GetString("GUI_REFUEL_PORT_SUFFIX");
			Ledger.AddLI(new LedgerLI(strPayee, CrewSim.coPlayer.strID, GUIStationRefuel.dictPrices["rowFuelConnect"], DataHandler.GetString("GUI_REFUEL_SERVICE_FUEL_CONNECT"), strRegID));
			Ledger.AddLI(new LedgerLI(strPayee, CrewSim.coPlayer.strID, GUIStationRefuel.dictPrices["rowLifeExchange"], DataHandler.GetString("GUI_REFUEL_SERVICE_LIFE_EXCHANGE"), strRegID));
			Ledger.AddLI(new LedgerLI(strPayee, CrewSim.coPlayer.strID, GUIStationRefuel.dictPrices["rowPowerHookup"], DataHandler.GetString("GUI_REFUEL_SERVICE_POWER_HOOKUP"), strRegID));
			float num = (float)nCols * 0.32f + (float)nRows * 0.32f;
			Ledger.AddLI(new LedgerLI(strPayee, CrewSim.coPlayer.strID, GUIStationRefuel.dictPrices["rowDock"] * num, DataHandler.GetString("GUI_REFUEL_SERVICE_DOCK"), strRegID, LedgerLI.Frequency.Hourly));
			Ledger.AddLI(new LedgerLI(strPayee, CrewSim.coPlayer.strID, GUIStationRefuel.dictPrices["rowDockFacilities"], DataHandler.GetString("GUI_REFUEL_SERVICE_FACILITIES"), strRegID, LedgerLI.Frequency.Hourly));
		}
	}

	public void ToggleVis(bool bShow, bool affectDocked = true)
	{
		if (gameObject == null || gameObject.activeInHierarchy == bShow)
		{
			return;
		}
		foreach (CondOwner value in mapICOs.Values)
		{
			if (value == null || !DataHandler.mapCOs.ContainsKey(value.strID))
			{
				if (value != null)
				{
					Debug.Log("ERROR: Bogus co found: " + value.strID);
				}
				else
				{
					Debug.Log("ERROR: Bogus co found: ");
				}
				Debug.Break();
				continue;
			}
			Pathfinder pathfinder = value.Pathfinder;
			if (pathfinder != null)
			{
				pathfinder.HideFootprints();
			}
			CrewSim.objInstance.ShowBlocksAndLights(value, bShow);
			if (value.HasTickers())
			{
				if (bShow)
				{
					CrewSim.AddTicker(value);
				}
				else
				{
					CrewSim.RemoveTicker(value);
				}
			}
		}
		foreach (Transform tfBG in tfBGs)
		{
			CrewSim.objInstance.ShowBlocksAndLights(tfBG.GetComponent<Item>(), bShow);
		}
		gameObject.SetActive(bShow);
		ShowRoomIDs(CrewSim.bDebugShow && bShow);
		if (!affectDocked)
		{
			return;
		}
		foreach (KeyValuePair<string, Ship> item in aDocked)
		{
			item.Value.ToggleVis(bShow);
		}
	}

	public void ToggleDockedVis(bool show)
	{
		foreach (Ship allDockedShip in GetAllDockedShips())
		{
			allDockedShip?.ToggleVis(show, affectDocked: false);
		}
	}

	public void ToggleCrewVisibility(bool show)
	{
		foreach (CondOwner person in GetPeople(bAllowDocked: false))
		{
			if (!(person.Crew == null))
			{
				person.Crew.ToggleVisibility(show);
			}
		}
	}

	public void RotateCW()
	{
		if (aTiles == null || aTiles.Count == 0)
		{
			return;
		}
		Transform transform = gameObject.transform;
		foreach (KeyValuePair<string, CondOwner> mapICO in mapICOs)
		{
			try
			{
				CondOwner value = mapICO.Value;
				if (value == null)
				{
					Debug.LogWarning("WARNING: Null co " + mapICO.Key + " found on ship " + strRegID + "'s mapICOs.");
					continue;
				}
				if (value.tf == null)
				{
					value.tf = value.transform;
				}
				if (!(value.tf.parent != transform))
				{
					if (value.Item != null)
					{
						value.Item.RotateCW();
					}
					if (value != null && value.transform != null)
					{
						Vector3 position = value.transform.position;
						value.transform.position = new Vector3(position.y, 0f - position.x, position.z);
					}
				}
			}
			catch (Exception ex)
			{
				string text = ((mapICO.Value != null && mapICO.Value.strName != null) ? mapICO.Value.strName : "null co");
				Debug.LogWarning("Caught Exception from " + text + " " + mapICO.Key + " M: " + ex.Message);
			}
		}
		Tile[] array = new Tile[aTiles.Count];
		aTiles.CopyTo(array);
		aTiles = TileUtils.RotateTilesCW(aTiles, nCols);
		int num = nCols;
		nCols = nRows;
		nRows = num;
		nGridRotation = (nGridRotation + 90) % 360;
		vShipPos.Set(vShipPos.y - (float)(nCols - 1), 0f - vShipPos.x);
		foreach (Room aRoom in aRooms)
		{
			if (aRoom == null)
			{
				Debug.LogWarning("WARNING: Null room found in ship " + strRegID + "'s aRooms.");
				continue;
			}
			CondOwner cO = aRoom.CO;
			Tile tile = aRoom.aTiles.FirstOrDefault();
			if (cO != null && cO.transform != null && tile != null && tile.transform != null)
			{
				cO.transform.position = tile.transform.position;
			}
			Dictionary<string, int> dictionary = new Dictionary<string, int>();
			foreach (KeyValuePair<string, int> dictDoor in aRoom.dictDoors)
			{
				int value2 = dictDoor.Value;
				int value3 = aTiles.IndexOf(array[value2]);
				dictionary[dictDoor.Key] = value3;
			}
			aRoom.dictDoors = dictionary;
		}
		foreach (CondOwner value4 in mapICOs.Values)
		{
			if (value4 == null || value4.Item == null || value4.Item.aBlocks == null || value4.tf == null)
			{
				continue;
			}
			foreach (Block aBlock in value4.Item.aBlocks)
			{
				aBlock.UpdateStats();
			}
			if (value4.Item.bHasSpriteSheet)
			{
				Tile[] surroundingTiles = TileUtils.GetSurroundingTiles(GetTileAtWorldCoords1(value4.tf.position.x, value4.tf.position.y, bAllowDocked: false), bCardinalOnly: true);
				value4.Item.SetSpriteSheetIndex(surroundingTiles);
			}
		}
		foreach (JsonZone value5 in mapZones.Values)
		{
			if (value5 == null)
			{
				Debug.LogWarning("WARNING: Null zone found in ship " + strRegID + "'s mapZones.");
				continue;
			}
			for (int i = 0; i < value5.aTiles.Length; i++)
			{
				int num2 = value5.aTiles[i];
				if (array.Length <= num2 || num2 < 0)
				{
					Debug.LogWarning("Trying to copy unavailable index: " + array.Length + "/" + value5.aTiles.Length + "/" + aTiles.Count);
				}
				else
				{
					value5.aTiles[i] = aTiles.IndexOf(array[num2]);
				}
			}
		}
		CrewSim.objInstance.workManager.RefreshTileIDs(strRegID, new List<Tile>(array));
		if (tfBGs != null)
		{
			tfBGs.Rotate(Vector3.back, 90f);
			tfBGs.position = new Vector3(tfBGs.position.y, 0f - tfBGs.position.x, tfBGs.position.z);
		}
		CrewSim.bPoolVisUpdates = true;
		if (FloorPlan != null)
		{
			for (int j = 0; j < FloorPlan.Count; j++)
			{
				FloorPlan[j] = new Vector2(FloorPlan[j].y, 0f - FloorPlan[j].x);
			}
		}
		if (SilhouettePoints != null)
		{
			for (int k = 0; k < SilhouettePoints.Count; k++)
			{
				SilhouettePoints[k] = new Vector2(SilhouettePoints[k].y, 0f - SilhouettePoints[k].x);
			}
		}
	}

	public void MoveShip(Vector2 ptOffset)
	{
		Transform transform = gameObject.transform;
		Vector2 vector = new Vector2(transform.position.x, transform.position.y);
		transform.position = new Vector3(vector.x + ptOffset.x, vector.y + ptOffset.y, transform.position.z);
		foreach (CondOwner value in mapICOs.Values)
		{
			Item item = value.Item;
			if (item == null)
			{
				continue;
			}
			foreach (Block aBlock in item.aBlocks)
			{
				aBlock.UpdateStats();
			}
		}
		ptOffset.x += vShipPos.x;
		ptOffset.y += vShipPos.y;
		vShipPos.Set(ptOffset.x, ptOffset.y);
		foreach (Room aRoom in aRooms)
		{
			aRoom.CO.tf.position = aRoom.aTiles[0].tf.position;
		}
	}

	public IReadOnlyList<Ship> GetAllDockedShips(string exception = null)
	{
		if (CachedAllDockedShips != null && exception == null)
		{
			return CachedAllDockedShips;
		}
		List<Ship> list = new List<Ship>();
		if (aDocked != null)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				Ship value = item.Value;
				if (!(exception == value.strRegID))
				{
					list.Add(value);
					IReadOnlyList<Ship> allDockedShips = value.GetAllDockedShips(strRegID);
					list.AddRange(allDockedShips);
				}
			}
		}
		else if (json != null && json.aDocked != null && json.aDocked.Count > 0)
		{
			foreach (KeyValuePair<string, string> item2 in json.aDocked)
			{
				if (item2.Value != null && !(item2.Value == exception))
				{
					Ship shipByRegID = CrewSim.system.GetShipByRegID(item2.Value);
					list.Add(shipByRegID);
					IReadOnlyList<Ship> allDockedShips2 = shipByRegID.GetAllDockedShips(item2.Value);
					list.AddRange(allDockedShips2);
				}
			}
		}
		if (exception == null)
		{
			CachedAllDockedShips = list;
		}
		return list;
	}

	public Dictionary<string, Ship> GetDockedShipsAndPortIDs()
	{
		Dictionary<string, Ship> dictionary = new Dictionary<string, Ship>();
		if (aDocked != null)
		{
			dictionary = aDocked.CloneShallow();
		}
		else if (json != null && json.aDocked != null && json.aDocked.Count > 0)
		{
			foreach (KeyValuePair<string, string> item in json.aDocked)
			{
				Ship shipByRegID = CrewSim.system.GetShipByRegID(item.Value);
				if (item.Value != null)
				{
					dictionary.Add(item.Key, shipByRegID);
				}
			}
		}
		return dictionary;
	}

	public List<Tile> GetAllDockedTiles()
	{
		List<Tile> list = new List<Tile>();
		list.AddRange(aTiles);
		foreach (KeyValuePair<string, Ship> item in aDocked)
		{
			if (item.Value != null)
			{
				list.AddRange(item.Value.aTiles);
			}
		}
		return list;
	}

	public static List<string> GetOwnedDockedShips(CondOwner coSelf, CondOwner coThem)
	{
		return GetOwnedDockedShips(coSelf, coThem.ship);
	}

	public static List<string> GetOwnedDockedShips(CondOwner coSelf, Ship otherShip, bool includeShipsWithZonesWeOwn = false)
	{
		List<string> list = new List<string>();
		if (coSelf == null)
		{
			return list;
		}
		List<string> shipsForOwner = CrewSim.system.GetShipsForOwner(coSelf.strID);
		Ship ship = otherShip;
		if (ship != null)
		{
			ship = CrewSim.system.GetNearestStation(ship.objSS.vPosx, ship.objSS.vPosy, excludeOutposts: true);
		}
		if (ship == null || shipsForOwner == null || ship.GetRangeTo(otherShip) > 3.342293553032505E-07)
		{
			return list;
		}
		List<Ship> shipsBySubString = CrewSim.system.GetShipsBySubString(ship.strRegID);
		List<Ship> list2 = new List<Ship>();
		foreach (Ship item in shipsBySubString)
		{
			if (item != null && !item.bDestroyed)
			{
				list2.AddRange(item.GetAllDockedShips());
			}
		}
		foreach (Ship item2 in list2)
		{
			if (item2 == null)
			{
				continue;
			}
			bool flag = false;
			foreach (string item3 in shipsForOwner)
			{
				if (!(item2.strRegID != item3))
				{
					list.Add(item3);
					flag = true;
				}
			}
			if (includeShipsWithZonesWeOwn && !flag && item2.GetZones("IsZoneBarter", coSelf, bAllowDocked: false, item2.LoadState == Loaded.Shallow).Count > 0)
			{
				list.Add(item2.strRegID);
			}
		}
		return list;
	}

	public double GetCondAmount(string strStatName, bool bAllowDocked)
	{
		double fAmount = 0.0;
		CondTrigger condTrigger = new CondTrigger();
		condTrigger.aReqs = new string[1] { strStatName };
		VisitCOs(condTrigger, bSubObjects: false, bAllowDocked, bAllowLocked: true, delegate(CondOwner co)
		{
			fAmount += co.GetCondAmount(strStatName);
		});
		return fAmount;
	}

	public string GetReactorGPMValue(string strKey)
	{
		if (Reactor != null)
		{
			return Reactor.GetGPMInfo("Panel A", strKey);
		}
		return "";
	}

	public void SetReactorGPMValue(string strName, string strValue)
	{
		if (Reactor != null)
		{
			Reactor.ApplyGPMChanges(new string[1] { "Panel A," + strName + "," + strValue });
		}
	}

	public void SetThrust(double fAmount)
	{
		bool flag = nLoadState >= Loaded.Edit;
		double num = ((fAmount > 0.0) ? (fAmount / Mass) : 0.0);
		bool flag2 = bTorchDriveThrusting;
		IsUsingTorchDrive = fAmount > 0.0;
		bool flag3 = flag2 != bTorchDriveThrusting || bTorchDriveThrusting;
		bool flag4 = false;
		if (IsDocked())
		{
			foreach (Ship allDockedShip in GetAllDockedShips())
			{
				if (allDockedShip.IsUsingTorchDrive)
				{
					flag4 = true;
					break;
				}
			}
		}
		float fVolumeMod = 0f;
		if (fAmount == 0.0)
		{
			aWPs.Clear();
			if (!flag4)
			{
				objSS.vAccIn.Set(0f, 0f);
			}
		}
		else
		{
			fVolumeMod = Mathf.Min(1f, (float)num / 9.81f / 7f);
			fVolumeMod = 0.25f + 0.75f * fVolumeMod;
			num = num / 149597872.0 / 1000.0;
			float num2 = Mathf.Cos(objSS.fRot);
			float num3 = Mathf.Sin(objSS.fRot);
			float newX = (0f - (float)num) * num3;
			float newY = (float)num * num2;
			objSS.vAccIn.Set(newX, newY);
		}
		if ((flag2 || bTorchDriveThrusting) && !flag4)
		{
			UpdateDockedShips(objSS, Gravity);
		}
		if (flag && flag3)
		{
			AudioManager.am.PlayAudioEmitter("ShipTorchLow", bLoop: true);
			AudioManager.am.TweakAudioEmitter("ShipTorchLow", 1f, fVolumeMod);
		}
	}

	private void WearManeuver(CondTrigger ctDamage, bool bPlayerNotice, float fDmgModifier)
	{
		if (fWearManeuver <= 30f || LoadState < Loaded.Edit || bNeedsGravSet)
		{
			return;
		}
		float num = 0.3f;
		float num2 = ((nActiveStabilizers > 0) ? (num + 1f / Mathf.Pow(2f, nActiveStabilizers)) : 1f);
		fDmgModifier *= num2;
		List<CondOwner> cOs = GetCOs(ctDamage, bSubObjects: false, bAllowDocked: true, bAllowLocked: false);
		int num3 = 75;
		float num4 = 10f;
		int num5 = num3;
		while (num5 > 0 && cOs.Count != 0)
		{
			CondOwner co = cOs[MathUtils.Rand(0, cOs.Count, MathUtils.RandType.Flat)];
			ManeuverDamagePart(co, bPlayerNotice, fDmgModifier * num4);
			num3--;
			if (num3 == 0)
			{
				break;
			}
			num5--;
		}
		fWearManeuver = 0f;
	}

	public float RemoveGasMass(float fMassNeeded)
	{
		if (fMassNeeded <= 0f)
		{
			return 0f;
		}
		if (LoadState <= Loaded.Shallow)
		{
			if (IsAIShip)
			{
				fMassNeeded *= 0.75f;
			}
			float num = Mathf.Min((float)fShallowRCSRemass, fMassNeeded);
			fShallowRCSRemass -= num;
			return num;
		}
		float num2 = 0f;
		List<CondOwner> list = new List<CondOwner>();
		foreach (CondOwner aRCSDistro in aRCSDistros)
		{
			foreach (KeyValuePair<string, Vector2> mapPoint in aRCSDistro.mapPoints)
			{
				if (mapPoint.Key.IndexOf("GasInput") < 0)
				{
					continue;
				}
				list.Clear();
				aRCSDistro.ship.GetCOsAtWorldCoords1(aRCSDistro.GetPos(mapPoint.Key), ctRCSGasInput, bAllowDocked: true, bAllowLocked: false, list);
				foreach (CondOwner item in list)
				{
					GasContainer gasContainer = item.GasContainer;
					if (gasContainer != null)
					{
						num2 += (float)gasContainer.RemoveGasMass(fMassNeeded - num2);
					}
					if (fMassNeeded <= num2)
					{
						break;
					}
				}
				if (fMassNeeded <= num2)
				{
					break;
				}
			}
			if (fMassNeeded <= num2)
			{
				break;
			}
		}
		return num2;
	}

	public void Maneuver(float fX, float fY, float fR, int nNoiseOnly, float fDeltaTime, EngineMode engineMode = EngineMode.RCS)
	{
		if (fDeltaTime <= 0f || objSS == null)
		{
			return;
		}
		bool flag = nLoadState >= Loaded.Edit;
		float num = Math.Abs(fX);
		num += Math.Abs(fY);
		num += Math.Abs(fR);
		bool flag2 = nNoiseOnly > 0 && num <= 1E-05f;
		num += (float)nNoiseOnly;
		float currentRotorEfficiency = CurrentRotorEfficiency;
		if (engineMode == EngineMode.AUTO)
		{
			engineMode = ((!(LiftRotorsThrustStrength > 0f) || !(currentRotorEfficiency > 0f)) ? EngineMode.RCS : EngineMode.MIXED);
		}
		bool flag3 = (fRCSCount == 0f || nRCSDistroCount == 0) && engineMode == EngineMode.RCS;
		if (objSS.bIsBO || num <= 1E-05f || flag3)
		{
			StopManeuver(flag, flag2);
			return;
		}
		if (flag)
		{
			float num2 = 1f;
			int num3 = MathUtils.Rand(0, aRCSThrusters.Count, MathUtils.RandType.Flat);
			Item item = null;
			if (num3 < aRCSThrusters.Count)
			{
				CondOwner condOwner = aRCSThrusters[num3];
				item = condOwner.Item;
				num2 = 1f - (float)condOwner.GetDamageState();
			}
			double num4 = 0.5;
			if (!CrewSim.Paused && item != null && MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) < 0.4 && ((double)num2 >= num4 || (double)item.fFlickerAmount < 1.0))
			{
				double num5 = (double)(1f - num2 * num2) / (1.0 - num4 * num4);
				if (num5 > 1.0)
				{
					num5 = 1.0;
				}
				if (item.fFlickerAmount == 0f)
				{
					if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) < num5)
					{
						num *= (float)num5;
					}
				}
				else if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) >= num5)
				{
					num = 0f;
				}
			}
		}
		float num6 = 1f;
		if (engineMode == EngineMode.RCS || engineMode == EngineMode.MIXED)
		{
			float num7 = 0.728f * fRCSCount * num * fDeltaTime;
			num7 *= (float)fFuelEfficiencyMod;
			if (!flag2)
			{
				num6 = RemoveGasMass(num7);
			}
			if (num6 <= 0f && engineMode == EngineMode.RCS)
			{
				StopManeuver(flag, flag2);
				return;
			}
		}
		if (!flag2)
		{
			float num8 = num6 / num;
			num8 *= 100f;
			float num9 = (float)Mass;
			IReadOnlyList<Ship> allDockedShips = GetAllDockedShips();
			if (allDockedShips != null)
			{
				foreach (Ship item2 in allDockedShips)
				{
					if (item2 != null)
					{
						num9 += (float)item2.Mass;
					}
				}
			}
			if (num9 <= 0f)
			{
				num9 = 0.01f;
			}
			float num10 = 0f;
			float num11 = 0f;
			float num12 = Mathf.Cos(objSS.fRot);
			float num13 = Mathf.Sin(objSS.fRot);
			float num14 = 0f;
			float num15 = 0f;
			if (engineMode == EngineMode.ROTOR || engineMode == EngineMode.MIXED)
			{
				float num16 = LiftRotorsThrustStrength * currentRotorEfficiency;
				num10 = (fX * num12 - fY * num13) * num16 / 149597870f;
				num11 = (fX * num13 + fY * num12) * num16 / 149597870f;
				fR += GetRotorMomentum();
				num14 = num10 / num9;
				num15 = num11 / num9;
			}
			if (engineMode == EngineMode.RCS || engineMode == EngineMode.MIXED)
			{
				num10 = (fX * num12 - fY * num13) * num8 * 5.26077E-09f;
				num11 = (fX * num13 + fY * num12) * num8 * 5.26077E-09f;
				num14 += num10 / num9 / fDeltaTime;
				num15 += num11 / num9 / fDeltaTime;
			}
			objSS.vAccRCS.x = num14;
			objSS.vAccRCS.y = num15;
			float num17 = fR * fDeltaTime;
			if ((double)Mathf.Abs(objSS.fW) > 1E-07 && objSS.fW * (objSS.fW + num17) < 0f)
			{
				objSS.fW = 0f;
			}
			else
			{
				objSS.fW += num17;
				objSS.fA = num17 / fDeltaTime;
			}
			UpdateDockedShips(objSS, Gravity);
		}
		if (flag)
		{
			if (OnManeuver == null)
			{
				OnManeuver = new ManeuverEvent();
			}
			if (engineMode == EngineMode.ROTOR || engineMode == EngineMode.MIXED)
			{
				OnManeuver.Invoke(strRegID, num > 0f);
			}
			if (num6 > 0f && num > 0f && engineMode != EngineMode.ROTOR)
			{
				AudioManager.am.PlayAudioEmitter("ShipRCSFwd", bLoop: true);
			}
			else
			{
				AudioManager.am.StopAudioEmitter("ShipRCSFwd");
			}
			if (num6 > 0f && num > 1f && engineMode != EngineMode.ROTOR)
			{
				AudioManager.am.PlayAudioEmitter("ShipRCSRot", bLoop: true);
			}
			else
			{
				AudioManager.am.StopAudioEmitter("ShipRCSRot");
			}
			if (num6 > 0f && num > 2f && engineMode != EngineMode.ROTOR)
			{
				AudioManager.am.PlayAudioEmitter("ShipRCSSide", bLoop: true);
			}
			else
			{
				AudioManager.am.StopAudioEmitter("ShipRCSSide");
			}
		}
	}

	public Ostranauts.Pathing.Vector2Int ParseColsRows()
	{
		int x = 0;
		int y = 0;
		if (LoadState == Loaded.Shallow && nRows == 0 && json.nRows == 0)
		{
			string input = json.dimensions;
			MatchCollection matchCollection = new Regex("([\\d.]+)m").Matches(input);
			if (matchCollection.Count == 2)
			{
				float num = float.Parse(matchCollection[0].Groups[1].Value);
				float num2 = float.Parse(matchCollection[1].Groups[1].Value);
				x = MathUtils.RoundToInt(num / 0.32f);
				y = MathUtils.RoundToInt(num2 / 0.32f);
			}
		}
		else
		{
			y = ((LoadState > Loaded.Shallow) ? nRows : json.nRows);
			x = ((LoadState > Loaded.Shallow) ? nCols : json.nCols);
		}
		return new Ostranauts.Pathing.Vector2Int(x, y);
	}

	public void UnlockFromOrbit(bool destroyBO = true)
	{
		if (objSS != null && objSS.bOrbitLocked)
		{
			objSS.UpdateTime(StarSystem.fEpoch);
			BodyOrbit bO = CrewSim.system.GetBO(objSS.strBOPORShip);
			if (!objSS.bBOLocked)
			{
				objSS.strBOPORShip = null;
				objSS.boReference = null;
			}
			objSS.bOrbitLocked = false;
			if (destroyBO && bO != null && bO.IsShipOrbit())
			{
				CrewSim.system.RemoveBO(bO);
			}
		}
	}

	public BodyOrbit LockToOrbit()
	{
		if (objSS == null || objSS.IsAccelerating)
		{
			return null;
		}
		BodyOrbit bodyOrbit = CrewSim.system.GetBO(strRegID);
		if (bodyOrbit == null)
		{
			BodyOrbit boClosest = null;
			Vector2 ptGrav = Vector2.zero;
			BodyOrbit bodyOrbit2 = CrewSim.system.GetGreatestGravBO(objSS, StarSystem.fEpoch, ref ptGrav, ref boClosest);
			bodyOrbit2.UpdateTime(StarSystem.fEpoch);
			int num = 15;
			while (num > 0 && bodyOrbit2.IsEscaping(this))
			{
				num--;
				if (bodyOrbit2.boParent != null && bodyOrbit2 != bodyOrbit2.boParent)
				{
					bodyOrbit2 = bodyOrbit2.boParent;
					continue;
				}
				return null;
			}
			if (bodyOrbit2.RadiusAtmo > 0.0 && MathUtils.GetDistance(bodyOrbit2.dXReal, bodyOrbit2.dXReal, objSS.vPosx, objSS.vPosy) < bodyOrbit2.RadiusAtmo)
			{
				return null;
			}
			bodyOrbit = BodyOrbit.CreateBOFromShip(this, bodyOrbit2);
			if (bodyOrbit == null)
			{
				return null;
			}
			CrewSim.system.AddBO(bodyOrbit, bodyOrbit.boParent);
		}
		objSS.LockToOrbit(bodyOrbit);
		return bodyOrbit;
	}

	private float GetRotorMomentum()
	{
		if (aActiveHeavyLiftRotors.Count == 0)
		{
			return 0f;
		}
		float num = 0f;
		foreach (CondOwner aActiveHeavyLiftRotor in aActiveHeavyLiftRotors)
		{
			if (!(aActiveHeavyLiftRotor == null))
			{
				Rotor component = aActiveHeavyLiftRotor.GetComponent<Rotor>();
				if (!(component == null))
				{
					num += component.Momentum;
				}
			}
		}
		return num;
	}

	public void StopManeuver(bool bPlayerNotice, bool bNoiseOnly)
	{
		if (bPlayerNotice)
		{
			AudioManager.am.StopAudioEmitter("ShipRCSFwd");
			AudioManager.am.StopAudioEmitter("ShipRCSRot");
			AudioManager.am.StopAudioEmitter("ShipRCSSide");
			OnManeuver.Invoke(strRegID, arg1: false);
		}
		if (!bNoiseOnly)
		{
			objSS.vAccRCS = Vector2.zero;
			objSS.fA = 0f;
			UpdateDockedShips(objSS, Gravity);
		}
	}

	private void PlayCreakAudio(string strLoot)
	{
		Loot loot = DataHandler.GetLoot(strLoot);
		if (loot != null)
		{
			string lootNameSingle = loot.GetLootNameSingle("SHIP_CREAK");
			AudioManager.am.PlayAudioEmitter(lootNameSingle, bLoop: false, bNoRestart: true);
			AudioManager.am.TweakAudioEmitter(lootNameSingle, 0.85f - MathUtils.Rand(0f, 0.15f, MathUtils.RandType.Flat), MathUtils.Rand(0.5f, 1f, MathUtils.RandType.Flat));
		}
	}

	private void ManeuverDamagePart(CondOwner co, bool bPlayerNotice, float fModifier)
	{
		double num = MathUtils.Rand(0f, 0.00167f, MathUtils.RandType.Flat);
		num *= co.GetCondAmount("StatDamageMax");
		num /= 4000.0;
		num *= (double)fModifier;
		co.AddCondAmount("StatDamage", num);
		if (bPlayerNotice && co.GetDamageState() <= 0.0)
		{
			BeatManager.ResetTensionTimer();
		}
	}

	public void UpdateDockedShips(ShipSitu currentSitu, double gravity)
	{
		if (currentSitu._dockGroup != null)
		{
			currentSitu._dockGroup.SyncShipInput(currentSitu, gravity);
		}
	}

	public double GetRCSRemain()
	{
		if (LoadState <= Loaded.Shallow)
		{
			return fShallowRCSRemass;
		}
		double num = 0.0;
		if (aRCSDistros == null)
		{
			return num;
		}
		List<CondOwner> list = new List<CondOwner>();
		foreach (CondOwner aRCSDistro in aRCSDistros)
		{
			if (aRCSDistro == null)
			{
				continue;
			}
			foreach (KeyValuePair<string, Vector2> mapPoint in aRCSDistro.mapPoints)
			{
				if (mapPoint.Key.IndexOf("GasInput") < 0)
				{
					continue;
				}
				list.Clear();
				aRCSDistro.ship.GetCOsAtWorldCoords1(aRCSDistro.GetPos(mapPoint.Key), ctRCSGasInput, bAllowDocked: true, bAllowLocked: false, list);
				foreach (CondOwner item in list)
				{
					GasContainer gasContainer = item.GasContainer;
					if (gasContainer != null)
					{
						num += gasContainer.Mass;
					}
				}
			}
		}
		return num;
	}

	public double GetRCSMax()
	{
		if (LoadState <= Loaded.Shallow)
		{
			if (fShallowRCSRemassMax == 0.0)
			{
				fShallowRCSRemassMax = fShallowRCSRemass;
			}
			return fShallowRCSRemassMax;
		}
		double num = 0.0;
		List<CondOwner> list = new List<CondOwner>();
		foreach (CondOwner aRCSDistro in aRCSDistros)
		{
			foreach (KeyValuePair<string, Vector2> mapPoint in aRCSDistro.mapPoints)
			{
				if (mapPoint.Key.IndexOf("GasInput") < 0)
				{
					continue;
				}
				list.Clear();
				aRCSDistro.ship.GetCOsAtWorldCoords1(aRCSDistro.GetPos(mapPoint.Key), ctRCSGasInput, bAllowDocked: true, bAllowLocked: false, list);
				foreach (CondOwner item in list)
				{
					double fMols = item.GetCondAmount("StatGasPressureMax") * item.GetCondAmount("StatVolume") / 293.0 / 0.008314000442624092;
					num += GasContainer.GetGasMass("N2", fMols);
				}
			}
		}
		return num;
	}

	public bool HasWeapons()
	{
		return WeaponsSystem.HasWeapons();
	}

	public List<CondOwner> GetRCSCans()
	{
		List<CondOwner> list = new List<CondOwner>();
		if (LoadState <= Loaded.Shallow)
		{
			return list;
		}
		List<CondOwner> list2 = new List<CondOwner>();
		foreach (CondOwner aRCSDistro in aRCSDistros)
		{
			foreach (KeyValuePair<string, Vector2> mapPoint in aRCSDistro.mapPoints)
			{
				if (mapPoint.Key.IndexOf("GasInput") < 0)
				{
					continue;
				}
				list2.Clear();
				aRCSDistro.ship.GetCOsAtWorldCoords1(aRCSDistro.GetPos(mapPoint.Key), ctRCSGasInput, bAllowDocked: true, bAllowLocked: false, list2);
				foreach (CondOwner item in list2)
				{
					list.Add(item);
				}
			}
		}
		return list;
	}

	public void AIRefuel()
	{
		fShallowRCSRemass = GetRCSMax();
	}

	public float RefuelRCS(float amount)
	{
		if (LoadState <= Loaded.Shallow)
		{
			double rCSMax = GetRCSMax();
			if (fShallowMass + (double)amount < rCSMax)
			{
				fShallowMass += amount;
				return 0f;
			}
			fShallowMass = rCSMax;
			return (float)(fShallowMass + (double)amount - rCSMax);
		}
		List<CondOwner> rCSCans = GetRCSCans();
		double gasMass = GasContainer.GetGasMass("N2", 1.0);
		foreach (CondOwner item in rCSCans)
		{
			GasContainer gasContainer = item.GasContainer;
			if (!(gasContainer == null))
			{
				float num = Convert.ToSingle(item.GetCondAmount("StatVolume") * item.GetCondAmount("StatGasPressureMax") / 0.008314000442624092 / item.GetCondAmount("StatGasTemp") * gasMass);
				float num2 = (float)(item.GetCondAmount("StatGasPressure") / item.GetCondAmount("StatGasPressureMax") * (double)num);
				float num3 = Mathf.Min(num - num2, amount);
				gasContainer.AddGasMols("N2", (double)num3 / gasMass);
				amount -= num3;
				if (amount <= 0f)
				{
					amount = 0f;
					break;
				}
			}
		}
		return amount;
	}

	public double GetTotalCOPrice()
	{
		List<CondOwner> cOs = GetCOs(null, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		double num = 0.0;
		foreach (CondOwner item in cOs)
		{
			if (item.HasCond("IsInstalled"))
			{
				num += item.GetCondAmount("StatBasePrice") * 100.0;
			}
		}
		return num;
	}

	public double GetRangeTo(Ship other)
	{
		if (other == null)
		{
			return double.PositiveInfinity;
		}
		return objSS.GetRangeTo(other.objSS);
	}

	public string GetPortName(string portID)
	{
		string result = ((portID == PrimaryDockingPortID) ? "Primary Dock ID:" : "Aux Dock ID: ");
		if (json != null && json.aItems != null)
		{
			JsonItem[] aItems = json.aItems;
			foreach (JsonItem jsonItem in aItems)
			{
				if (jsonItem == null || jsonItem.strID != portID)
				{
					continue;
				}
				if (jsonItem.aGPMSettings == null)
				{
					break;
				}
				JsonGUIPropMap[] aGPMSettings = jsonItem.aGPMSettings;
				foreach (JsonGUIPropMap jsonGUIPropMap in aGPMSettings)
				{
					if (jsonGUIPropMap == null || !(jsonGUIPropMap.strName == "Rename"))
					{
						continue;
					}
					if (jsonGUIPropMap.dictGUIPropMap != null)
					{
						Dictionary<string, string> dictionary = DataHandler.ConvertStringArrayToDict(jsonGUIPropMap.dictGUIPropMap);
						if (dictionary.ContainsKey("strName"))
						{
							result = dictionary["strName"];
						}
					}
					break;
				}
				break;
			}
		}
		return result;
	}

	public bool IsDocked(bool excludeMoored = false)
	{
		if (aDocked != null)
		{
			if (!excludeMoored)
			{
				return aDocked.Count > 0;
			}
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (!item.Key.Contains("MP|"))
				{
					return true;
				}
			}
		}
		else if (json != null && json.aDocked != null)
		{
			if (!excludeMoored)
			{
				return json.aDocked.Count > 0;
			}
			foreach (KeyValuePair<string, string> item2 in json.aDocked)
			{
				if (!item2.Key.Contains("MP|"))
				{
					return true;
				}
			}
		}
		return false;
	}

	public bool IsBOLockedInAnyWay(string exception)
	{
		if (objSS == null)
		{
			return false;
		}
		if (objSS.bIsBO || objSS.bBOLocked)
		{
			return true;
		}
		IReadOnlyList<Ship> allDockedShips = GetAllDockedShips(exception);
		if (allDockedShips == null)
		{
			return false;
		}
		for (int i = 0; i < allDockedShips.Count; i++)
		{
			Ship ship = allDockedShips[i];
			if (ship != null && ship.objSS != null && (ship.objSS.bIsBO || ship.objSS.bBOLocked))
			{
				return true;
			}
		}
		return false;
	}

	public bool IsDockedWithAStation()
	{
		IReadOnlyList<Ship> allDockedShips = GetAllDockedShips();
		if (allDockedShips == null)
		{
			return false;
		}
		foreach (Ship item in allDockedShips)
		{
			if (item == null || item.objSS == null)
			{
				string text = ((item == null) ? "Docked ship is null" : (item.strRegID + " has null objSS"));
				LogAdd("IsDockedWithAStation: " + text);
			}
		}
		return allDockedShips.Any((Ship x) => x != null && (x.IsStation() || x.IsSubStation()));
	}

	public bool CanDockWithExpensive(Ship shipIncoming)
	{
		if (!HasOpenDockingPorts())
		{
			return false;
		}
		List<(string, string)> availableDockingPorts = GetAvailableDockingPorts(shipIncoming);
		if (availableDockingPorts != null)
		{
			return availableDockingPorts.Count > 0;
		}
		return false;
	}

	public bool IsMoored()
	{
		foreach (KeyValuePair<string, Ship> dockedShipsAndPortID in GetDockedShipsAndPortIDs())
		{
			if (dockedShipsAndPortID.Key.Contains("MP|"))
			{
				return true;
			}
		}
		return false;
	}

	public bool IsMooredAsteroid()
	{
		if (!IsMoored())
		{
			return false;
		}
		foreach (Ship mooredShip in GetMooredShips())
		{
			if (mooredShip.Classification == TypeClassification.Asteroid)
			{
				return true;
			}
		}
		return false;
	}

	public List<Ship> GetMooredShips()
	{
		List<Ship> list = new List<Ship>();
		foreach (KeyValuePair<string, Ship> dockedShipsAndPortID in GetDockedShipsAndPortIDs())
		{
			if (dockedShipsAndPortID.Key.Contains("MP|") && dockedShipsAndPortID.Value != null)
			{
				list.Add(dockedShipsAndPortID.Value);
			}
		}
		return list;
	}

	public bool IsDerelict()
	{
		return DMGStatus == Damage.Derelict;
	}

	public bool IsFlyingDark()
	{
		if (bXPDRAntenna && !(strXPDR == "?"))
		{
			return string.IsNullOrEmpty(strXPDR);
		}
		return true;
	}

	public bool HasOKLGSalvageLicense()
	{
		return GetCOs(ctPermitOKLG, bSubObjects: true, bAllowDocked: true, bAllowLocked: true).Count > 0;
	}

	public List<CondOwner> GetOKLGSalvageLicenses()
	{
		return GetCOs(ctPermitOKLG, bSubObjects: true, bAllowDocked: true, bAllowLocked: true);
	}

	public bool TowBracesSecured()
	{
		List<Ship> dockedShips = GetDockedShips();
		if (dockedShips == null || dockedShips.Count == 0)
		{
			return true;
		}
		for (int i = 0; i < dockedShips.Count; i++)
		{
			Ship ship = dockedShips[i];
			if (!TowBraceSecured(ship.strRegID))
			{
				return false;
			}
		}
		return true;
	}

	public bool TowBraceSecured(string targetRegID, bool checkOtherSide = true)
	{
		if (targetRegID == strRegID)
		{
			return false;
		}
		string portIdForDockedShip = GetPortIdForDockedShip(targetRegID);
		if (string.IsNullOrEmpty(portIdForDockedShip))
		{
			return false;
		}
		if (aSecuredTowBraces != null && aSecuredTowBraces.ContainsValue(portIdForDockedShip))
		{
			return true;
		}
		if (checkOtherSide)
		{
			return CrewSim.system.GetShipByRegID(targetRegID)?.TowBraceSecured(strRegID, checkOtherSide: false) ?? true;
		}
		return false;
	}

	public void ToggleTowBracesShallow(bool isOn, string dockingTarget)
	{
		string portIdForDockedShip = GetPortIdForDockedShip(dockingTarget);
		if (string.IsNullOrEmpty(portIdForDockedShip))
		{
			return;
		}
		if (aSecuredTowBraces == null)
		{
			aSecuredTowBraces = new Dictionary<string, string>();
		}
		bool flag = aSecuredTowBraces.ContainsValue(dockingTarget);
		if (!(isOn && flag) && (isOn || flag))
		{
			if (isOn)
			{
				aSecuredTowBraces[portIdForDockedShip] = portIdForDockedShip;
			}
			else
			{
				aSecuredTowBraces.TryRemoveValue(portIdForDockedShip);
			}
		}
	}

	public bool IsActive()
	{
		return !IsDocked();
	}

	public bool IsStation(bool bIgnoreDocks = false)
	{
		if (!bIgnoreDocks && !HasDockingPorts)
		{
			return false;
		}
		if (objSS != null && objSS.bIsBO)
		{
			return true;
		}
		return false;
	}

	public bool IsSubStation()
	{
		return _subStation;
	}

	public bool IsStationHidden(bool bIgnoreDocks = false)
	{
		if ((bIgnoreDocks || !HasDockingPorts) && objSS != null && objSS.bIsBO && Classification != TypeClassification.Waypoint)
		{
			return true;
		}
		return false;
	}

	public bool IsInCombatWith(string regIdThem)
	{
		if (shipCombatTarget != null && shipCombatTarget.strRegID == regIdThem)
		{
			return true;
		}
		AIShip aIShipByRegID = AIShipManager.GetAIShipByRegID(strRegID);
		if (aIShipByRegID != null)
		{
			List<Ship> list = aIShipByRegID.Blackboard.Get<List<Ship>>("Combatants");
			if (list != null)
			{
				return list.Any((Ship x) => x != null && x.strRegID == regIdThem);
			}
		}
		return false;
	}

	public bool IsTargeting(string regIdThem)
	{
		if (string.IsNullOrEmpty(regIdThem))
		{
			return false;
		}
		if (shipCombatTarget != null)
		{
			return shipCombatTarget.strRegID == regIdThem;
		}
		return false;
	}

	public bool IsGroundStation()
	{
		if (Classification != TypeClassification.GroundStation && Classification != TypeClassification.GroundStationUnfinished)
		{
			return Classification == TypeClassification.Skyscraper;
		}
		return true;
	}

	public bool IsPlayerShip()
	{
		return this == CrewSim.GetSelectedCrew().ship;
	}

	public Ship GetDockedShip(string strRegID)
	{
		if (LoadState >= Loaded.Edit)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				Ship value = item.Value;
				if (value != null && value.strRegID == strRegID)
				{
					return value;
				}
			}
		}
		else if (LoadState == Loaded.Shallow && json != null && json.aDocked != null)
		{
			foreach (KeyValuePair<string, string> item2 in json.aDocked)
			{
				if (item2.Value == strRegID)
				{
					return CrewSim.system.GetShipByRegID(strRegID);
				}
			}
		}
		return null;
	}

	public List<Ship> GetDockedShips()
	{
		List<Ship> list = new List<Ship>();
		if (aDocked != null)
		{
			foreach (var (_, ship2) in aDocked)
			{
				if (ship2 != null)
				{
					list.Add(ship2);
				}
			}
		}
		else if (json != null && json.aDocked != null && json.aDocked.Count > 0)
		{
			foreach (KeyValuePair<string, string> item in json.aDocked)
			{
				if (item.Value != null)
				{
					Ship shipByRegID = CrewSim.system.GetShipByRegID(item.Value);
					if (shipByRegID != null)
					{
						list.Add(shipByRegID);
					}
				}
			}
		}
		return list;
	}

	public bool IsDockedWith(string regId)
	{
		Ship shipByRegID = CrewSim.system.GetShipByRegID(regId);
		if (shipByRegID != null)
		{
			return IsDockedWith(shipByRegID);
		}
		return false;
	}

	public bool IsDockedWith(Ship ship)
	{
		if (ship == null)
		{
			return false;
		}
		if (aDocked != null && aDocked.ContainsValue(ship))
		{
			return true;
		}
		if (LoadState == Loaded.Shallow && json != null && json.aDocked != null)
		{
			return json.aDocked.ContainsValue(ship.strRegID);
		}
		return false;
	}

	public bool IsMooredWith(Ship ship)
	{
		if (ship == null)
		{
			return false;
		}
		if (aDocked != null)
		{
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (item.Value == ship && item.Key.Contains("MP|"))
				{
					return true;
				}
			}
		}
		if (LoadState == Loaded.Shallow && json != null && json.aDocked != null)
		{
			foreach (KeyValuePair<string, string> item2 in json.aDocked)
			{
				if (item2.Value == ship.strRegID && item2.Key.Contains("MP|"))
				{
					return true;
				}
			}
		}
		return false;
	}

	public void CyclePrimaryDockingPort()
	{
		string primaryDockingPortID = PrimaryDockingPortID;
		for (int i = 0; i < aDockingPorts.Count; i++)
		{
			string text = aDockingPorts[i];
			if (!(primaryDockingPortID != text) && !text.Contains("MP|"))
			{
				if (i == aDockingPorts.Count - 1)
				{
					strPrimaryDockingPortID = aDockingPorts[0];
				}
				else
				{
					strPrimaryDockingPortID = aDockingPorts[i + 1];
				}
			}
		}
	}

	public void ShowRoomIDs(bool bShow)
	{
		foreach (Room aRoom in aRooms)
		{
			aRoom.ShowID(bShow);
		}
	}

	public JsonItem GetJsonItem(CondOwner co)
	{
		if (co == null || co.tf == null)
		{
			Debug.Log("ERROR: Trying to get save info for null CO: " + co);
			return null;
		}
		List<JsonGUIPropMap> list = new List<JsonGUIPropMap>();
		JsonItem jsonItem = new JsonItem();
		jsonItem.strName = co.strCODef;
		jsonItem.fRotation = co.tf.rotation.eulerAngles.z;
		Item item = co.Item;
		if (item != null)
		{
			jsonItem.fRotation = item.fLastRotation;
		}
		jsonItem.fX = co.tf.position.x;
		jsonItem.fY = co.tf.position.y;
		jsonItem.strID = co.strID;
		double damage = co.GetDamage();
		if (damage > 0.001)
		{
			jsonItem.SetCondAmount("StatDamage", damage);
		}
		if (co.AlwaysLoad)
		{
			jsonItem.bForceLoad = co.AlwaysLoad;
		}
		if (co.coStackHead != null)
		{
			jsonItem.strParentID = co.coStackHead.strID;
		}
		else if (co.objCOParent != null)
		{
			if (co.slotNow != null)
			{
				jsonItem.strSlotParentID = co.objCOParent.strID;
			}
			else
			{
				jsonItem.strParentID = co.objCOParent.strID;
			}
		}
		else
		{
			jsonItem.strParentID = null;
		}
		foreach (string key in co.mapGUIPropMaps.Keys)
		{
			JsonGUIPropMap jsonGUIPropMap = new JsonGUIPropMap();
			jsonGUIPropMap.strName = key;
			jsonGUIPropMap.dictGUIPropMap = DataHandler.ConvertDictToStringArray(co.mapGUIPropMaps[key]);
			list.Add(jsonGUIPropMap);
		}
		jsonItem.aGPMSettings = list.ToArray();
		return jsonItem;
	}

	public JsonShip GetJSON(string strName, bool bSaveGame, List<CondOwner> allCos = null)
	{
		int count = aTiles.Count;
		JsonShip jsonShip = null;
		Debug.Log("Getting JSON for ship: " + strRegID + " - " + model);
		if (nLoadState >= Loaded.Edit)
		{
			MarketConfigs.Clear();
			jsonShip = new JsonShip();
			jsonShip.aItems = new JsonItem[0];
			jsonShip.aCrew = new JsonItem[0];
			if (nRows > 0 && nCols > 0)
			{
				dimensions = ((float)nCols * 0.32f).ToString("#.00") + "m x " + ((float)nRows * 0.32f).ToString("#.00") + "m";
				jsonShip.nCols = nCols;
				jsonShip.nRows = nRows;
				bool activeInHierarchy = gameObject.activeInHierarchy;
				gameObject.SetActive(value: true);
				TileUtils.TrimAllSides(this);
				if (count != aTiles.Count)
				{
					Debug.Log("Ship " + strRegID + " changed tiles from " + count + " to " + aTiles.Count + ", recalcing rooms.");
					CreateRooms();
					if (allCos != null)
					{
						foreach (Room aRoom in aRooms)
						{
							if (aRoom != null && aRoom.CO != null && !allCos.Contains(aRoom.CO))
							{
								allCos.Add(aRoom.CO);
							}
						}
					}
				}
				gameObject.SetActive(activeInHierarchy);
			}
		}
		else
		{
			jsonShip = json.Clone();
			if (jsonShip.aItems == null)
			{
				jsonShip.aItems = new JsonItem[0];
			}
			if (jsonShip.aCrew == null)
			{
				jsonShip.aCrew = new JsonItem[0];
			}
		}
		SaveCOs(bSaveGame, jsonShip, allCos);
		jsonShip.nGridRotation = nGridRotation;
		jsonShip.shipCO = ShipCO.GetJSONSave();
		jsonShip.commData = Comms.GetJson();
		jsonShip.strName = strName;
		jsonShip.strRegID = strRegID;
		jsonShip.nCurrentWaypoint = nCurrentWaypoint;
		jsonShip.fTimeEngaged = fTimeEngaged;
		jsonShip.fWearManeuver = fWearManeuver;
		jsonShip.fWearAccrued = (float)fWearAccrued;
		jsonShip.vShipPos = vShipPos;
		jsonShip.bNoCollisions = bNoCollisions;
		jsonShip.bLocalAuthority = bLocalAuthority;
		jsonShip.bAIShip = bAIShip;
		jsonShip.dLastScanTime = dLastScanTime;
		jsonShip.objSS = objSS.GetJSON();
		jsonShip.DMGStatus = DMGStatus;
		jsonShip.fLastVisit = fLastVisit;
		jsonShip.fFirstVisit = fFirstVisit;
		jsonShip.fAIDockingExpire = fAIDockingExpire;
		jsonShip.fAIPauseTimer = fAIPauseTimer;
		jsonShip.bPrefill = bPrefill;
		jsonShip.bBreakInUsed = bBreakInUsed;
		jsonShip.strTargetRegID = targetRegID;
		jsonShip.strAIDespawnedAt = strAIDespawnedAt;
		jsonShip.bRemove = bRemove;
		if (shipUndock != null)
		{
			jsonShip.strUndockID = shipUndock.strRegID;
		}
		if (shipScanTarget != null)
		{
			jsonShip.strScanTargetID = shipScanTarget.strRegID;
		}
		if (shipCombatTarget != null)
		{
			jsonShip.strCombatTargetID = shipCombatTarget.strRegID;
		}
		if (shipStationKeepingTarget != null)
		{
			jsonShip.strStationKeepingTargetID = shipStationKeepingTarget.strRegID;
		}
		if (shipSituTarget != null)
		{
			jsonShip.objSituScanTarget = shipSituTarget.GetJSON();
		}
		if (json != null && json.aConstructionTemplates != null)
		{
			jsonShip.aConstructionTemplates = (JsonShipConstructionTemplate[])json.aConstructionTemplates.Clone();
		}
		if (MarketConfigs != null)
		{
			jsonShip.aMarketConfigs = MarketConfigs.CloneShallow();
		}
		if (aLog != null)
		{
			jsonShip.aLog = new JsonShipLog[aLog.Count];
			for (int i = 0; i < aLog.Count; i++)
			{
				jsonShip.aLog[i] = aLog[i].Clone();
			}
		}
		jsonShip.strLaw = strLaw;
		jsonShip.strParallax = strParallax;
		jsonShip.make = make;
		jsonShip.model = model;
		jsonShip.year = year;
		jsonShip.designation = designation;
		if (rating != null)
		{
			jsonShip.aRating = rating;
		}
		jsonShip.dimensions = dimensions;
		jsonShip.publicName = publicName;
		jsonShip.origin = origin;
		jsonShip.description = description;
		jsonShip.fShallowMass = Mass;
		jsonShip.fShallowRCSRemass = GetRCSRemain();
		jsonShip.fShallowRCSRemassMax = GetRCSMax();
		jsonShip.fLastQuotedPrice = fLastQuotedPrice;
		jsonShip.nRCSCount = fRCSCount;
		jsonShip.fShallowRotorStrength = fShallowRotorStrength;
		jsonShip.nRCSDistroCount = nRCSDistroCount;
		jsonShip.strPrimaryDockingPortID = strPrimaryDockingPortID;
		jsonShip.aDockingPorts = aDockingPorts.ToArray();
		if (LoadState >= Loaded.Edit)
		{
			jsonShip.nO2PumpCount = aO2AirPumps.Count;
			jsonShip.bXPDRAntenna = bXPDRAntenna;
		}
		jsonShip.bFusionTorch = bFusionReactorRunning;
		jsonShip.strXPDR = strXPDR;
		jsonShip.bShipHidden = bShipHidden;
		jsonShip.bIsUnderConstruction = bIsUnderConstruction;
		jsonShip.strTemplateName = strTemplateName;
		jsonShip.nConstructionProgress = nConstructionProgress;
		jsonShip.nInitConstructionProgress = nInitConstructionProgress;
		jsonShip.fShallowFusionRemain = fShallowFusionRemain;
		jsonShip.fFusionThrustMax = fFusionThrustMax;
		jsonShip.fFusionPelletMax = fFusionPelletMax;
		jsonShip.fEpochNextGrav = fEpochNextGrav;
		jsonShip.fBreakInMultiplier = fBreakInMultiplier;
		jsonShip.ShipType = Classification;
		List<string> list = new List<string>();
		foreach (JsonFaction aFaction in aFactions)
		{
			list.Add(aFaction.strName);
		}
		jsonShip.aFactions = list.ToArray();
		list.Clear();
		if (aRooms.Count > 0)
		{
			List<JsonRoom> list2 = new List<JsonRoom>();
			foreach (Room aRoom2 in aRooms)
			{
				list2.Add(aRoom2.GetJSONSave());
			}
			jsonShip.aRooms = list2.ToArray();
		}
		if (aSecuredTowBraces != null)
		{
			Dictionary<string, string> dictionary = new Dictionary<string, string>();
			foreach (KeyValuePair<string, string> aSecuredTowBrace in aSecuredTowBraces)
			{
				dictionary.Add(aSecuredTowBrace.Key, aSecuredTowBrace.Value);
			}
			jsonShip.aSecuredTowBraces = dictionary;
		}
		if (nLoadState >= Loaded.Edit)
		{
			Dictionary<string, string> dictionary2 = new Dictionary<string, string>();
			foreach (KeyValuePair<string, Ship> item in aDocked)
			{
				if (item.Value != null)
				{
					dictionary2.Add(item.Key, item.Value.strRegID);
				}
			}
			jsonShip.aDocked = dictionary2;
			list.Clear();
			foreach (string item2 in aProxCurrent)
			{
				list.Add(item2);
			}
			jsonShip.aProxCurrent = list.ToArray();
			list.Clear();
			foreach (string aProxIgnore in aProxIgnores)
			{
				list.Add(aProxIgnore);
			}
			jsonShip.aProxIgnores = list.ToArray();
			list.Clear();
			foreach (string item3 in aTrackCurrent)
			{
				list.Add(item3);
			}
			jsonShip.aTrackCurrent = list.ToArray();
			list.Clear();
			foreach (string aTrackIgnore in aTrackIgnores)
			{
				list.Add(aTrackIgnore);
			}
			jsonShip.aTrackIgnores = list.ToArray();
			list.Clear();
			List<JsonShipSitu> list3 = new List<JsonShipSitu>();
			List<float> list4 = new List<float>();
			foreach (WaypointShip aWP in aWPs)
			{
				list3.Add(aWP.objSS.GetJSON());
				list4.Add(aWP.fTime);
			}
			jsonShip.aWPs = list3.ToArray();
			jsonShip.aWPTimes = list4.ToArray();
			list3.Clear();
			list4.Clear();
			jsonShip.aZones = new JsonZone[mapZones.Values.Count];
			int num = 0;
			foreach (JsonZone value in mapZones.Values)
			{
				jsonShip.aZones[num] = value.Clone();
				num++;
			}
			fShallowRotorStrength = -1f;
			fShallowRotorStrength = LiftRotorsThrustStrength;
			jsonShip.fShallowRotorStrength = fShallowRotorStrength;
			List<float[]> list5 = new List<float[]>();
			List<float[]> list6 = new List<float[]>();
			List<string> list7 = new List<string>();
			foreach (KeyValuePair<string, List<Vector2>> dictBG in dictBGs)
			{
				list7.Add(dictBG.Key);
				List<float> list8 = new List<float>();
				List<float> list9 = new List<float>();
				foreach (Vector2 item4 in dictBG.Value)
				{
					list8.Add(item4.x);
					list9.Add(item4.y);
				}
				list5.Add(list8.ToArray());
				list6.Add(list9.ToArray());
			}
			jsonShip.aBGXs = list5.ToArray();
			jsonShip.aBGYs = list6.ToArray();
			jsonShip.aBGNames = list7.ToArray();
			jsonShip.aUniques = json.aUniques;
			jsonShip.aFires = CrewSim.vfxFire.GetFireCOsForShip(this, bRemove: false);
		}
		return jsonShip;
	}

	public void SaveCOs(bool bSaveGame, JsonShip jShip, List<CondOwner> aICOs = null)
	{
		List<CondOwner> list = new List<CondOwner>();
		list = aICOs ?? GetCOs(null, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		if (jShip.aItems == null)
		{
			jShip.aItems = new JsonItem[0];
		}
		if (jShip.aCrew == null)
		{
			jShip.aCrew = new JsonItem[0];
		}
		Dictionary<string, JsonItem> dictionary = new Dictionary<string, JsonItem>();
		JsonItem[] aItems = jShip.aItems;
		foreach (JsonItem jsonItem in aItems)
		{
			dictionary[jsonItem.strID] = jsonItem;
		}
		List<JsonItem> list2 = new List<JsonItem>(jShip.aCrew);
		List<JsonItem> list3 = new List<JsonItem>();
		List<JsonPlaceholder> list4 = new List<JsonPlaceholder>();
		if (jShip.aPlaceholders != null)
		{
			list4.AddRange(jShip.aPlaceholders);
		}
		foreach (CondOwner item in list)
		{
			if (item == null)
			{
				Debug.Log("Skipping null objICO");
				continue;
			}
			bool flag = item.Crew != null;
			bool flag2 = false;
			if (item.HasCond("IsLootSpawner"))
			{
				if (item.mapGUIPropMaps["Panel A"]["strType"].IndexOf("Pspec") >= 0)
				{
					flag2 = true;
				}
			}
			else if (item.HasCond("IsFire"))
			{
				continue;
			}
			if (flag && !bSaveGame)
			{
				continue;
			}
			bool flag3 = false;
			if (dictionary.ContainsKey(item.strID))
			{
				JsonItem jsonItem2 = GetJsonItem(item);
				if (jsonItem2 != null)
				{
					dictionary[item.strID] = jsonItem2;
					flag3 = true;
				}
				else
				{
					Debug.LogError("ERROR: Failed to get JsonItem for " + item.strID + " - " + item.strCODef);
				}
			}
			if (flag2)
			{
				JsonItem jsonItem3 = GetJsonItem(item);
				if (jsonItem3 != null)
				{
					list3.Add(jsonItem3);
				}
				else
				{
					Debug.LogError("ERROR: Failed to get JsonItem for " + item.strID + " - " + item.strCODef);
				}
			}
			else if (item.HasCond("IsPlaceholder"))
			{
				Placeholder component = item.GetComponent<Placeholder>();
				if (component != null)
				{
					JsonItem jsonItem4 = GetJsonItem(item);
					if (jsonItem4 != null)
					{
						JsonPlaceholder jsonPlaceholder = new JsonPlaceholder();
						jsonPlaceholder.strName = item.strID;
						jsonPlaceholder.strInstalledCO = component.strInstalledCO;
						jsonPlaceholder.strActionCO = component.strActionCO;
						jsonPlaceholder.strPersistentCO = component.strPersistentCO;
						jsonPlaceholder.strPersistentCT = component.strPersistentCT;
						jsonPlaceholder.strInstallIA = component.strInstallIA;
						list4.Add(jsonPlaceholder);
						dictionary[item.strID] = jsonItem4;
					}
					else
					{
						Debug.LogError("ERROR: Failed to get JsonItem for " + item.strID + " - " + item.strCODef);
					}
				}
			}
			else
			{
				if (flag3)
				{
					continue;
				}
				if (flag)
				{
					int num = -1;
					for (int j = 0; j < list2.Count; j++)
					{
						if (list2[j].strID == item.strID)
						{
							num = j;
							break;
						}
					}
					if (num < 0)
					{
						JsonItem jsonItem5 = GetJsonItem(item);
						if (jsonItem5 != null)
						{
							list2.Add(jsonItem5);
						}
						else
						{
							Debug.LogError("ERROR: Failed to get JsonItem for " + item.strID + " - " + item.strCODef);
						}
					}
				}
				else
				{
					if (item.HasCond("IsTraderNPC") || item.HasCond("IsMarketActor"))
					{
						AddMarketActorConfigToShip(item);
					}
					JsonItem jsonItem6 = GetJsonItem(item);
					if (jsonItem6 != null)
					{
						dictionary[item.strID] = jsonItem6;
					}
					else
					{
						Debug.LogError("ERROR: Failed to get JsonItem for " + item.strID + " - " + item.strCODef);
					}
				}
			}
			if (item.aLot == null)
			{
				continue;
			}
			foreach (CondOwner lotCO in item.GetLotCOs(bSubItems: true))
			{
				JsonItem jsonItem7 = GetJsonItem(lotCO);
				if (jsonItem7 == null)
				{
					Debug.LogError("ERROR: Failed to get JsonItem for " + lotCO.strID + " - " + lotCO.strCODef);
				}
				else
				{
					dictionary[lotCO.strID] = jsonItem7;
				}
			}
		}
		jShip.aItems = dictionary.Values.ToArray();
		jShip.aCrew = list2.ToArray();
		jShip.aShallowPSpecs = list3.ToArray();
		jShip.aPlaceholders = list4.ToArray();
	}

	public override string ToString()
	{
		return strRegID + "; " + model + "; Load:" + nLoadState.ToString() + "; Docked: " + bDocked;
	}

	public void KnockDownCrew(CondOwner co)
	{
		if (co == null || LoadState < Loaded.Edit || bNeedsGravSet || GUIFFWD.Active)
		{
			return;
		}
		double condAmount = co.GetCondAmount("StatDefense");
		double x = 50.0 - condAmount;
		x = MathUtils.Clamp(x, 0.05, 1.0);
		if (co.HasCond("SkillOpsZeroG"))
		{
			x *= 0.25;
		}
		if (!(MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) <= x))
		{
			return;
		}
		Interaction interaction = DataHandler.GetInteraction("ACTShipKnockDown");
		if (interaction != null)
		{
			CondOwner objUs = (interaction.objThem = co);
			interaction.objUs = objUs;
			if (interaction.Triggered(bStats: false, bIgnoreItems: true))
			{
				co.QueueInteraction(co, interaction, bInsert: true);
			}
		}
	}

	public void GravApplyCrew()
	{
		if (StarSystem.fEpoch < fEpochNextGrav)
		{
			return;
		}
		bool flag = false;
		foreach (PersonSpec aPerson in aPeople)
		{
			CondOwner cO = aPerson.GetCO();
			if (cO == null || !(cO.GetCondAmount("IsHuman") > 0.0) || !cO.bAlive)
			{
				continue;
			}
			CondRule condRule = cO.GetCondRule("StatGrav");
			if (condRule == null)
			{
				continue;
			}
			CondRuleThresh currentThresh = condRule.GetCurrentThresh(cO);
			if (currentThresh == null || Array.IndexOf(condRule.aThresholds, currentThresh) < 3)
			{
				continue;
			}
			double num = 10.0;
			num /= (double)(condRule.aThresholds[3].fMax - condRule.aThresholds[3].fMin);
			if (double.IsNaN(num))
			{
				num = 1.0;
			}
			Wound woundLocation = cO.GetWoundLocation(bBlunt: true, bCut: false, null);
			if (!(woundLocation == null))
			{
				double num2 = num * (fGravity - (double)condRule.aThresholds[3].fMin);
				if (woundLocation.DamageLeft() < num2)
				{
					num2 = woundLocation.DamageLeft();
				}
				bool bAudio = Wound.bAudio;
				Wound.bAudio = LoadState >= Loaded.Edit;
				woundLocation.Damage(num2, 0.0, 0.0, null, "", bUnsocket: true, null, bSkipArmor: true);
				Wound.bAudio = bAudio;
				if (LoadState >= Loaded.Edit)
				{
					flag = true;
				}
			}
		}
		fEpochNextGrav = StarSystem.fEpoch + MathUtils.Rand(0.9, 1.1, MathUtils.RandType.Flat);
		if (flag)
		{
			BeatManager.ResetTensionTimer();
		}
	}

	public double DeltaVRemainingFusion(float fLimiter)
	{
		return (double)GetMaxTorchThrust(fLimiter) * fShallowFusionRemain;
	}

	public bool CheckAccruedWear()
	{
		if (fWearAccrued > 0.0)
		{
			if (nLoadState > Loaded.Shallow)
			{
				DamageAllCOsTrend((float)fWearAccrued, ctWearTime, ShipCO.GetCondAmount("StationMaintLvl"));
				fWearAccrued = 0.0;
				return true;
			}
			return false;
		}
		return false;
	}

	public float GetMaxTorchThrust(float fAmount)
	{
		return (float)((double)(Mathf.Lerp(1f, (float)PelletMax, fAmount) / (float)PelletMax * fAmount) * fFusionThrustMax / Mass * 6.6845869117759804E-12);
	}

	public void AccrueWear(float wear)
	{
		fWearAccrued += wear;
	}

	public void VisualizeOverlays(bool force = false)
	{
		CondTrigger condTrigger = DataHandler.GetCondTrigger("Blank");
		foreach (CondOwner cO in GetCOs(condTrigger, bSubObjects: true, bAllowDocked: false, bAllowLocked: true))
		{
			if (cO.Item != null)
			{
				cO.Item.VisualizeOverlays(force);
			}
			else if (cO.Crew != null)
			{
				cO.Crew.VisualizeDamage(force);
			}
		}
	}

	public bool COIsFactionProperty(CondOwner co)
	{
		if (co == null || co.socUs != null)
		{
			return false;
		}
		return ctFactionCO.Triggered(co);
	}

	public void SetFactions(List<JsonFaction> aJFs, bool bRemoveOld)
	{
		foreach (CondOwner cO in GetCOs(DataHandler.GetCondTrigger("Blank"), bSubObjects: true, bAllowDocked: false, bAllowLocked: true))
		{
			if (COIsFactionProperty(cO))
			{
				cO.SetFactions(aJFs, bRemoveOld);
			}
		}
		if (bRemoveOld)
		{
			aFactions.Clear();
		}
		foreach (JsonFaction aJF in aJFs)
		{
			if (aFactions.IndexOf(aJF) < 0)
			{
				aFactions.Add(aJF);
			}
		}
	}

	public List<JsonFaction> GetShipFactions()
	{
		return aFactions ?? new List<JsonFaction>();
	}

	public bool SharesFactionsWith(List<string> aFactions)
	{
		if (aFactions == null || aFactions.Count == 0)
		{
			return false;
		}
		foreach (string aFaction in aFactions)
		{
			if (HasFaction(aFaction))
			{
				return true;
			}
		}
		return false;
	}

	public bool HasFaction(string strFaction)
	{
		if (string.IsNullOrEmpty(strFaction) || aFactions == null)
		{
			return false;
		}
		foreach (JsonFaction aFaction in aFactions)
		{
			if (aFaction.strName == strFaction)
			{
				return true;
			}
		}
		return false;
	}

	public double GetShipValue()
	{
		double num = 0.0;
		double num2 = 1.0;
		if (nLoadState <= Loaded.Shallow)
		{
			if (json.aRooms != null)
			{
				JsonRoom[] array = json.aRooms;
				foreach (JsonRoom jsonRoom in array)
				{
					num += jsonRoom.roomValue;
				}
			}
			else
			{
				Debug.LogWarning("No rooms on json " + json.designation);
			}
			if (json.nO2PumpCount > 0)
			{
				num2 += 2.0;
			}
		}
		else
		{
			foreach (Room aRoom in aRooms)
			{
				num += aRoom.RoomValue;
			}
			if (aO2AirPumps.Count > 0)
			{
				num2 += 2.0;
			}
		}
		return num * num2;
	}

	public double GetPartsValue()
	{
		double num = 0.0;
		double num2 = 0.0;
		if (LoadState >= Loaded.Edit)
		{
			foreach (CondOwner value in GetMappedCos().Values)
			{
				num2 = value.GetCondAmount("StatBasePrice");
				if (value.HasCond("StatDamageMax"))
				{
					num2 *= value.GetDamageState();
				}
				num += num2;
			}
		}
		else if (json != null && json.aItems != null)
		{
			JsonItem[] aItems = json.aItems;
			foreach (JsonItem jsonItem in aItems)
			{
				if (jsonItem == null)
				{
					continue;
				}
				DataCO dataCO = DataHandler.GetDataCO(jsonItem.strName);
				num2 = dataCO.GetCondAmount("StatBasePrice");
				double condAmount = dataCO.GetCondAmount("StatDamageMax");
				if (condAmount > 0.0)
				{
					double num3 = dataCO.GetCondAmount("StatDamage");
					if (jsonItem.aCondOverrides != null)
					{
						for (int j = 0; j < jsonItem.aCondOverrides.Length; j++)
						{
							if (!(jsonItem.aCondOverrides[j].CondName != "StatDamage"))
							{
								num3 = (jsonItem.aCondOverrides[j].NegativeValue ? (num3 - jsonItem.aCondOverrides[j].Amount) : (num3 + jsonItem.aCondOverrides[j].Amount));
								if (num3 < 0.0)
								{
									num3 = 0.0;
								}
								break;
							}
						}
					}
					num2 *= (condAmount - num3) / condAmount;
				}
				num += num2;
			}
		}
		return num;
	}

	private void SetDerelictValue(float randomPriceMod = -1f)
	{
		if (DMGStatus == Damage.Derelict)
		{
			float num = randomPriceMod;
			if (num < 0f)
			{
				num = DerelictShipEntry.GetRandomPriceModifier(DerelictShipEntry.HashIdIntoNumber(strRegID));
			}
			float num2 = 1.1f - fBreakInMultiplier;
			if (num2 <= 0f)
			{
				num2 = 0.1f;
			}
			fLastQuotedPrice = GetShipValue() * (double)num2 * (double)num;
		}
	}

	public List<RoomSpec> GetRoomSpecs()
	{
		List<RoomSpec> list = new List<RoomSpec>();
		if (nLoadState <= Loaded.Shallow)
		{
			if (json.aRooms != null)
			{
				JsonRoom[] array = json.aRooms;
				for (int i = 0; i < array.Length; i++)
				{
					RoomSpec roomDef = DataHandler.GetRoomDef(array[i].roomSpec);
					if (roomDef != null && !roomDef.IsBlank)
					{
						list.Add(roomDef);
					}
				}
			}
			else
			{
				Debug.LogWarning("No rooms on json " + json.designation);
			}
		}
		else
		{
			foreach (Room aRoom in aRooms)
			{
				RoomSpec roomSpec = aRoom.GetRoomSpec();
				if (!roomSpec.IsBlank)
				{
					list.Add(roomSpec);
				}
			}
		}
		return list;
	}

	public void CreateRooms(Dictionary<int, JsonRoom> mapTileRooms = null)
	{
		Tile[] array = null;
		List<Room> range = aRooms.GetRange(0, aRooms.Count);
		aRooms.Clear();
		_cachedRoomDividerDTOs = null;
		Dictionary<Room, List<Room>> dictionary = new Dictionary<Room, List<Room>>();
		foreach (Tile aTile in aTiles)
		{
			if (aTile.room != null && aTile.room.CO == null)
			{
				aTile.room = null;
			}
			aTile.bPathChecked = false;
			aTile.aAdjRooms.Clear();
		}
		List<Tile> list = new List<Tile>();
		HashSet<Tile> hashSet = new HashSet<Tile>();
		Dictionary<string, int> mapRoomCount = new Dictionary<string, int>();
		int count = aTiles.Count;
		Room room = null;
		CondOwner condOwner = null;
		for (int i = 0; i < count; i++)
		{
			Tile tile = aTiles[i];
			condOwner = tile.coProps;
			if (tile.bPathChecked)
			{
				continue;
			}
			if (condOwner.HasCond("IsPortal"))
			{
				if (!hashSet.Contains(tile))
				{
					hashSet.Add(tile);
				}
				continue;
			}
			if (condOwner.HasCond("IsWall"))
			{
				if (!condOwner.HasCond("IsPortal"))
				{
					tile.room = null;
				}
				continue;
			}
			room = null;
			if (mapTileRooms != null && mapTileRooms.ContainsKey(tile.Index))
			{
				string strRoomID = mapTileRooms[tile.Index].strID;
				CondOwner cOByID = GetCOByID(strRoomID);
				if (cOByID != null)
				{
					room = new Room(cOByID);
					RemoveCO(cOByID);
				}
				else
				{
					room = aRooms.FirstOrDefault((Room x) => x.CO != null && x.CO.strID == strRoomID);
					if (room == null)
					{
						Debug.Log("Generating new room with old ID: " + strRoomID + " for Tile: " + tile.Index);
						room = new Room(DataHandler.GetCondOwner("Compartment", mapTileRooms[tile.Index].strID, null, bLoot: false));
					}
					else
					{
						Debug.Log("Tile " + tile.Index + " requests room that already exists! Assigning existing one " + strRoomID);
					}
				}
				LogRoom(mapRoomCount, room);
				room.CO.AddCondAmount("StatVolume", 0.0 - room.CO.GetCondAmount("StatVolume"));
			}
			if (room == null)
			{
				room = new Room();
				Debug.Log("#Info# Generating completely new room: " + room.CO.strID);
				LogRoom(mapRoomCount, room);
			}
			if (!aRooms.Contains(room))
			{
				aRooms.Add(room);
			}
			room.CO.tf.SetParent(gameObject.transform);
			room.CO.ship = this;
			room.bOuter = false;
			if (!dictionary.ContainsKey(room))
			{
				dictionary[room] = new List<Room>();
			}
			HashSet<Tile> hashSet2 = new HashSet<Tile> { tile };
			list.Add(tile);
			for (int num = 0; num < list.Count; num++)
			{
				tile = list[num];
				if (tile.room != null)
				{
					if (!tile.coProps.HasCond("IsPortal"))
					{
						if (!dictionary[room].Contains(tile.room))
						{
							dictionary[room].Add(tile.room);
						}
					}
					else if (!hashSet.Contains(tile))
					{
						hashSet.Add(tile);
					}
				}
				tile.room = room;
				room.aTiles.Add(tile);
				tile.bPathChecked = true;
				tile.strDebug = tile.Index.ToString();
				condOwner = tile.coProps;
				bool flag = condOwner.HasCond("IsPortal");
				room.CO.tf.position = tile.tf.position;
				if (!room.Void && !condOwner.HasCond("IsFloorSealed"))
				{
					room.Void = true;
				}
				if (!flag)
				{
					array = TileUtils.GetSurroundingTiles(tile, bCardinalOnly: true);
				}
				else
				{
					if (!hashSet.Contains(tile))
					{
						hashSet.Add(tile);
					}
					array = new Tile[0];
				}
				for (int num2 = 1; num2 < array.Length; num2++)
				{
					if (num2 == 2 || num2 == 5 || num2 == 7)
					{
						continue;
					}
					tile = array[num2];
					if (tile != null)
					{
						condOwner = tile.coProps;
						if (tile.bPathChecked)
						{
							continue;
						}
						if (condOwner.HasCond("IsWall") || flag)
						{
							if (!room.Void)
							{
								tile.aAdjRooms.Add(room.CO.strID);
							}
						}
						else if (!hashSet2.Contains(tile))
						{
							list.Add(tile);
							hashSet2.Add(tile);
						}
					}
					else
					{
						room.Void = true;
						room.bOuter = true;
					}
				}
			}
			list.Clear();
		}
		foreach (Tile item in hashSet)
		{
			List<CondOwner> list2 = new List<CondOwner>();
			GetCOsAtWorldCoords1(item.tf.position, ctPortals, bAllowDocked: false, bAllowLocked: false, list2);
			if (list2.Count > 0)
			{
				Room roomAtWorldCoords = GetRoomAtWorldCoords1(list2[0].GetPos("RoomA"), bAllowDocked: false);
				Room roomAtWorldCoords2 = GetRoomAtWorldCoords1(list2[0].GetPos("RoomB"), bAllowDocked: false);
				if (roomAtWorldCoords != null && !roomAtWorldCoords.Void)
				{
					item.room = roomAtWorldCoords;
				}
				else if (roomAtWorldCoords2 != null && !roomAtWorldCoords2.Void)
				{
					item.room = roomAtWorldCoords2;
				}
				else if (roomAtWorldCoords != null)
				{
					item.room = roomAtWorldCoords;
				}
				else if (roomAtWorldCoords2 != null)
				{
					item.room = roomAtWorldCoords2;
				}
				if (item.room != null)
				{
					item.room.aTiles.Add(item);
				}
				if (roomAtWorldCoords != null)
				{
					roomAtWorldCoords.dictDoors[list2[0].strID] = item.Index;
				}
				if (roomAtWorldCoords2 != null)
				{
					roomAtWorldCoords2.dictDoors[list2[0].strID] = item.Index;
				}
			}
		}
		foreach (Room aRoom in aRooms)
		{
			aRoom.ResetBorderCOCache();
			if (!aRoom.Void)
			{
				aRoom.CO.AddCondAmount("StatVolume", (double)(0.25599998f * (float)aRoom.aTiles.Count) - aRoom.CO.GetCondAmount("StatVolume"));
			}
			List<string> list3 = new List<string>();
			foreach (Condition value in aRoom.CO.mapConds.Values)
			{
				if (value.bRoom)
				{
					list3.Add(value.strName);
				}
			}
			foreach (string item2 in list3)
			{
				aRoom.CO.ZeroCondAmount(item2);
			}
		}
		foreach (CondOwner cO3 in GetCOs(DataHandler.GetCondTrigger("TIsInstalled"), bSubObjects: true, bAllowDocked: false, bAllowLocked: true))
		{
			Tile.AddToRoom(GetTileAtWorldCoords1(cO3.tf.position.x, cO3.tf.position.y, bAllowDocked: false), cO3, addEffects: false);
		}
		foreach (Room aRoom2 in aRooms)
		{
			aRoom2.CreateRoomSpecs();
		}
		foreach (CondOwner cO4 in GetCOs(CTRoomStats, bSubObjects: true, bAllowDocked: false, bAllowLocked: true))
		{
			GetRoomAtWorldCoords1(cO4.tf.position, bAllowDocked: true)?.AddToRoom(cO4);
		}
		foreach (KeyValuePair<Room, List<Room>> item3 in dictionary)
		{
			int count2 = item3.Value.Count;
			if (item3.Key.Void || count2 <= 0)
			{
				continue;
			}
			CondOwner cO = item3.Key.CO;
			GasContainer gasContainer = cO.GasContainer;
			double condAmount = cO.GetCondAmount("StatVolume");
			double statGasTemp = GasExchange.GetStatGasTemp(cO, trueValue: true);
			double num3 = 0.0;
			double num4 = 0.0;
			foreach (Room item4 in item3.Value)
			{
				CondOwner cO2 = item4.CO;
				double condAmount2 = cO2.GetCondAmount("StatVolume");
				double statGasTemp2 = GasExchange.GetStatGasTemp(cO2);
				double num5 = Math.Min(condAmount / condAmount2, 1.0);
				GasContainer gasContainer2 = cO2.GasContainer;
				foreach (string key in gasContainer2.mapGasMols1.Keys)
				{
					if (!(key == "StatGasMolTotal"))
					{
						double num6 = gasContainer2.mapGasMols1[key] * num5;
						if (!(num6 <= 0.0))
						{
							num3 += num6;
							float num7 = 1f;
							num4 += num6 * statGasTemp2 * (double)num7;
							MathUtils.DictionaryKeyPlus(ref gasContainer.mapDGasMols, key, num6);
						}
					}
				}
			}
			gasContainer.fDGasTemp = num4 / (num3 + 1.0000000031710769E-30) - statGasTemp;
			cO.GasChanged = true;
			gasContainer.Run();
		}
		foreach (Room item5 in range)
		{
			CrewSim.vfxSmoke.RemoveRoom(item5);
			if (item5.CO == null)
			{
				Debug.LogWarning("Warning: Destroying old room that is already null: " + item5);
			}
			else
			{
				item5.CO.tf.SetParent(null);
				item5.CO.ship = null;
			}
			item5.Destroy();
		}
		CleanupCompartments();
		bCheckRooms = false;
		ShowRoomIDs(CrewSim.bDebugShow);
	}

	private void CleanupCompartments()
	{
		if (aRooms == null || mapICOs == null)
		{
			return;
		}
		List<string> list = null;
		foreach (KeyValuePair<string, CondOwner> kvp in mapICOs)
		{
			if (!(kvp.Value == null) && kvp.Value.HasCond("IsRoom") && !aRooms.Any((Room r) => r.CO.strID == kvp.Key))
			{
				Debug.LogWarning("Removing ghost room: " + kvp.Key);
				if (list == null)
				{
					list = new List<string>();
				}
				list.Add(kvp.Key);
			}
		}
		if (list == null)
		{
			return;
		}
		foreach (string item in list)
		{
			if (mapICOs.TryGetValue(item, out var value))
			{
				if (value != null)
				{
					value.Destroy();
				}
				mapICOs.Remove(item);
			}
		}
	}

	private void CheckRoomPressure()
	{
		if (_cachedRoomDividerDTOs != null)
		{
			foreach (RoomDividerDTO cachedRoomDividerDTO in _cachedRoomDividerDTOs)
			{
				if (cachedRoomDividerDTO != null && !cachedRoomDividerDTO.HasNullValues())
				{
					GasContainer.CheckPressureDifference(cachedRoomDividerDTO.RoomA.CO.GasContainer, cachedRoomDividerDTO.RoomB.CO.GasContainer, cachedRoomDividerDTO.Position);
				}
			}
			return;
		}
		if (aTiles == null)
		{
			return;
		}
		_cachedRoomDividerDTOs = new List<RoomDividerDTO>();
		foreach (Tile aTile in aTiles)
		{
			if (aTile == null || aTile.room != null || aTile.tf == null)
			{
				continue;
			}
			Vector2 vector = aTile.tf.position.ToVector2();
			Room room = null;
			Vector2[] directionVectors = _directionVectors;
			foreach (Vector2 vector2 in directionVectors)
			{
				Vector2 vector3 = vector + vector2;
				Tile tileAtWorldCoords = GetTileAtWorldCoords1(vector3.x, vector3.y, bAllowDocked: false, checkIfShipTile: false);
				if (tileAtWorldCoords == null || tileAtWorldCoords.room == null)
				{
					continue;
				}
				if (room == null)
				{
					room = tileAtWorldCoords.room;
				}
				else if (room != tileAtWorldCoords.room)
				{
					RoomDividerDTO roomDividerDTO = new RoomDividerDTO(vector, room, tileAtWorldCoords.room);
					if (!roomDividerDTO.HasNullValues())
					{
						_cachedRoomDividerDTOs.Add(roomDividerDTO);
						GasContainer.CheckPressureDifference(room.CO.GasContainer, tileAtWorldCoords.room.CO.GasContainer, vector);
						break;
					}
				}
			}
		}
	}

	private void LogRoom(Dictionary<string, int> mapRoomCount, Room objRoom)
	{
		if (!mapRoomCount.ContainsKey(objRoom.CO.strID))
		{
			mapRoomCount[objRoom.CO.strID] = 1;
			return;
		}
		mapRoomCount[objRoom.CO.strID]++;
		Debug.LogError("ERROR: Ship " + strRegID + " has " + mapRoomCount[objRoom.CO.strID] + " rooms with ID " + objRoom.CO.strID);
		Debug.Break();
	}
}
