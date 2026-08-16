using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Ostranauts.Core;
using Ostranauts.Core.Models;
using Ostranauts.Events;
using Ostranauts.InputControl;
using Ostranauts.Objectives;
using Ostranauts.Racing;
using Ostranauts.ShipGUIs.MFD;
using Ostranauts.ShipGUIs.NavStation;
using Ostranauts.ShipGUIs.Utilities;
using Ostranauts.Ships;
using Ostranauts.Ships.AIPilots;
using Ostranauts.Ships.Sensors;
using Ostranauts.Tools.ExtensionMethods;
using Ostranauts.Utils.Models;
using SolarSystem;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;
using Vectrosity;

public class GUIOrbitDraw : GUIData
{
	private static GUIOrbitDraw _instance;

	private static bool _initialized;

	public static NavModMessageEvent NavModMessageEvent = new NavModMessageEvent();

	public double fModTimeDiff = 1.0;

	public static readonly float fLineWidth = 1.5f;

	private const string NAV_DATA_KEY = "DataBINNAV";

	public static UpdateShipSelectionEvent UpdateShipSelection;

	public Texture texLine01;

	public Texture texLine02;

	public Texture texLine03;

	public Texture texLine04;

	public RawImage renderMap;

	private double dCanvasSolarXX;

	private double dCanvasSolarXY;

	private double dOffsetSX;

	private double dOffsetSY;

	public NavPOI follow;

	public static ShipInfo crossHairInfo;

	[NonSerialized]
	public double dFollowOffsetSX;

	[NonSerialized]
	public double dFollowOffsetSY;

	private double oldFollowCX;

	private double oldFollowCY;

	private double dDragStartCX;

	private double dDragStartCY;

	private double dDragStartSX;

	private double dDragStartSY;

	private bool bDragValid;

	private double dLastMiddleX;

	private float fVelocityX;

	private float fVelocityY;

	[NonSerialized]
	public float fVelocityYaw;

	[NonSerialized]
	public double fVRel;

	[NonSerialized]
	public float fBRG;

	[NonSerialized]
	public double dRNG;

	[NonSerialized]
	public float fRemass;

	[NonSerialized]
	public float fRCSMax;

	private Dictionary<string, GameObject> dictImages = new Dictionary<string, GameObject>();

	public float fVelocityZ;

	public double dMagTarget = 1.2E+18;

	public float fZoomTimer;

	private double dScopeRadius = 1.0;

	private BoPredictionGrid _boPredictionGrid;

	private float fTimeMouseDown;

	public FlightPlan livePlan;

	private double dEpoch;

	public double fEpochStationBegin;

	public float fLogScrollRate = 0.1f;

	public float fTimeFuture = 1f;

	public float fTimeFutureTarget = 1f;

	private List<DebugDraw> aDebugDraws = new List<DebugDraw>();

	public Vector3 vCanvasOffset;

	[SerializeField]
	private Button btnDone;

	[SerializeField]
	private Button btnRescue;

	[SerializeField]
	private Button btnScrew01;

	[SerializeField]
	private Button btnScrew02;

	[SerializeField]
	private Button btnScrew03;

	[SerializeField]
	private Button btnScrew04;

	[SerializeField]
	private EditMenu _editMenu;

	private ShipSitu objSSEngage;

	private ShipSitu ssTemp;

	private GameObject goOrbitPanel;

	private CanvasGroup cgStatus;

	private UnityAction<bool> eEngage;

	private TextMeshProUGUI txtSide;

	private Text txtTimeUTC;

	private TMP_Text txtRange;

	private Transform tfPanelIn;

	private Transform tfOrbitLabel;

	private TMP_Dropdown ddTravel;

	private Button btnTravel;

	[SerializeField]
	public Toggle chkStationKeeping;

	private GUILamp ledWLock;

	[SerializeField]
	private Button btnNote;

	private ScrollRect srLog;

	private CanvasGroup cgNag;

	private TMP_Text txtNagTimer;

	private Dictionary<string, GUIBtnPressHold> dictWASD;

	private bool bRCS = true;

	public bool bShowNWZ;

	private float fPreviousSpin;

	private bool bShowMapProjs = true;

	private bool bNoteOpen = true;

	private bool bNoteAnimating;

	private bool initNoAudio;

	private bool bClaimed;

	private double fEpochNagEnd;

	private int nProjSteps = 1;

	private int nProjStepsSelf = 5;

	private const int nSegmentsBody = 64;

	private const int nSamples = 64;

	public float fMinOrbitDiam = 12f;

	public LineType lTypeSensor;

	public Joins jTypeSensor = Joins.None;

	public int nSensorSegments = 64;

	private const double VIS_RANGE_TORCH = 1500000000.0;

	public const double VIS_RANGE_RCS = 20000.0;

	private const double VIS_RANGE_DEAD = 2000.0;

	public static readonly int DERELICTSIZE = 300;

	private Color clrAsteroid2 = new Color(0.32156864f, 0.20784314f, 5f / 51f, 1f);

	private Color clrAsteroid = new Color(0.5294118f, 0.4117647f, 4f / 15f, 0.47058824f);

	public static Color clrText = new Color(0.46484375f, 0.99609375f, 1f, 1f);

	private Color clrShipOrbit = new Color(0.34765625f, 15f / 32f, 0.5294118f, 0.25f);

	public static Color clrBlue01 = new Color(19f / 128f, 0.57421875f, 63f / 64f, 0.9f);

	private Color clrBlue01Half = new Color(19f / 128f, 0.57421875f, 63f / 64f, 0.45f);

	private Color clrBlue02 = new Color(0.07421875f, 0.28515625f, 63f / 128f, 0.9f);

	private Color clrGreen01 = new Color(37f / 128f, 0.99609375f, 89f / 128f, 0.9f);

	private Color clrGreen01Half = new Color(37f / 128f, 0.99609375f, 89f / 128f, 0.45f);

	private Color clrGreen02 = new Color(0.5f, 57f / 64f, 39f / 64f, 0.9f);

	public static Color clrWhite01 = new Color(95f / 128f, 95f / 128f, 95f / 128f, 0.9f);

	public static Color clrWhite02 = new Color(15f / 32f, 15f / 32f, 15f / 32f, 0.9f);

	public static Color clrRed01 = new Color(0.94921875f, 0.24609375f, 23f / 128f, 0.9f);

	private Color clrRed02 = new Color(15f / 64f, 0.05859375f, 0.04296875f, 0.9f);

	public static Color clrDecoy = new Color(0.64453125f, 0.48828125f, 85f / 128f, 0.9f);

	public static Color clrOrange01 = new Color(0.99609375f, 45f / 64f, 0f, 0.9f);

	public static Color clrOrange01Half = new Color(0.99609375f, 45f / 64f, 0f, 0.45f);

	public static Color clrOrange02Half = new Color(0.99609375f, 13f / 32f, 0f, 0.45f);

	public static Color clrHauler = new Color(39f / 64f, 17f / 32f, 0.38671875f, 1f);

	public static Color clrLocalAuthority = new Color(25f / 32f, 0.3125f, 15f / 128f, 0.9f);

	public static Color clrNoSig = new Color(0.49609375f, 0.49609375f, 0.49609375f, 0.2f);

	public Color clrSensor = new Color(39f / 64f, 17f / 32f, 0.38671875f, 1f);

	private List<VectorLine> aUIs;

	private List<ShipDraw> aShipDraws;

	private List<BODraw> aBODraws;

	private List<StellarObjectGroup> aStellarObjectGroups;

	public ShipDraw sdNS;

	private BODraw boMainOccluder;

	private VectorLine lineCross;

	private VectorLine lineStationKeepingTarget;

	private VectorLine lineCourse;

	private VectorLine lineGrav;

	private RectTransform rectDrawPanel;

	[SerializeField]
	private RectTransform rectDisplayPanel;

	private RectTransform rtLines;

	private StringBuilder sb = new StringBuilder();

	public CanvasGroup cgClampWarning;

	public float fClampDisengageWarningTimer;

	private static string strQEKey = "Q+E";

	private List<string> _playerOwnedShips = new List<string>();

	public NavData navPlan;

	private Dictionary<string, string> _shipPropMap;

	private Coroutine _nwzRoutine;

	private Dictionary<string, CondOwner> _navMods = new Dictionary<string, CondOwner>();

	private List<CondOwner> aNavModCleanup;

	private Vector3 noteLowered = new Vector3(252f, -383f);

	private Vector3 noteRaised = new Vector3(-299f, 123.3f);

	private Vector3 eulerLowered = new Vector3(0f, 0f, -6.37f);

	public static UnityEvent OpenedNavStationUI = new UnityEvent();

	public static UnityEventString SelectedShipDraw = new UnityEventString();

	public static UnityAction<double> OnZoom;

	private bool _showAllShips;

	private IInputCommand _commandFlyUp;

	private IInputCommand _commandFlyDown;

	private IInputCommand _commandFlyLeft;

	private IInputCommand _commandFlyRight;

	private IInputCommand _commandShipCCW;

	private IInputCommand _commandShipCW;

	private IInputCommand _commandShipAttitude;

	private IInputCommand _commandShipLockW;

	private IInputCommand _commandZoomOut;

	private IInputCommand _commandZoomIn;

	private IInputCommand _commandClick;

	private IInputCommand _commandRightClick;

	private IInputCommand _commandMiddleClick;

	private IInputCommand _commandPanFaster;

	private IInputCommand _commandScrollWheel;

	private static Color[] colorArray = new Color[14]
	{
		new Color(1f, 0f, 0f),
		Color.yellow,
		Color.blue,
		Color.green,
		Color.magenta,
		new Color(0.5019608f, 0.3529412f, 0f),
		new Color(0.5019608f, 0.5019608f, 0f),
		new Color(0.5882353f, 20f / 51f, 0.5882353f),
		new Color(0f, 0.5019608f, 0.5019608f),
		new Color(0.54509807f, 0f, 0.54509807f),
		new Color(1f, 0.5019608f, 0f),
		new Color(1f, 4f / 51f, 49f / 85f),
		new Color(41f / 51f, 0.52156866f, 21f / 85f),
		new Color(0.4392157f, 0.5019608f, 48f / 85f)
	};

	public double fEpochCycleSafetyBegin;

	private readonly List<Ostranauts.Core.Models.Tuple<double, StellarObjectDraw>> _stellarObjectDrawRef = new List<Ostranauts.Core.Models.Tuple<double, StellarObjectDraw>>();

	public List<Bounds> boundsAddedThisFrame = new List<Bounds>();

	public Dictionary<Bounds, List<ShipDraw>> boundsToRects = new Dictionary<Bounds, List<ShipDraw>>();

	public List<ShipDraw> VisibleShipDraws = new List<ShipDraw>();

	public List<ShipDraw> OverlappingShipDraws = new List<ShipDraw>();

	private bool _delayedLoadingFinished;

	private bool _editModeActive;

	private double _holdthrustTimeStamp;

	private bool _hasNotSeenRefuelingTutorial = true;

	public static GUIOrbitDraw Instance
	{
		get
		{
			return _instance;
		}
		set
		{
			_instance = value;
			_initialized = value != null;
		}
	}

	public static NavPOI CrossHairTarget { get; set; }

	public bool IsPDANav { get; private set; }

	public Dictionary<string, string> ShipPropMap => _shipPropMap ?? dictPropMap;

	private int GetKnobFollowState => GetPropMapData("nFollow", 0);

	private int GetKnobRefState => GetPropMapData("nRef", 0);

	private int GetKnobLabelsState => GetPropMapData("nLabels", 3);

	public int NavModCount => _navMods.Count;

	public bool PlayerThrusting { get; private set; }

	public bool HoldingThrustActive
	{
		get
		{
			if (ledWLock != null)
			{
				return ledWLock.State == 3;
			}
			return false;
		}
	}

	public bool NoteShowing => bNoteOpen;

	public float UpwardsRotation => (float)Math.Atan2(dCanvasSolarXY, dCanvasSolarXX);

	public override CondOwner COSelf
	{
		get
		{
			return coSelfTemp;
		}
		set
		{
			base.COSelf = value;
		}
	}

	public void SolarToCanvas(double sx, double sy, out double cx, out double cy)
	{
		double num = sx + dOffsetSX;
		double num2 = sy + dOffsetSY;
		cx = num * dCanvasSolarXX - num2 * dCanvasSolarXY;
		cy = num * dCanvasSolarXY + num2 * dCanvasSolarXX;
	}

	private void CanvasToSolar(double cx, double cy, out double sx, out double sy)
	{
		double num = cx * dCanvasSolarXX + cy * dCanvasSolarXY;
		double num2 = (0.0 - cx) * dCanvasSolarXY + cy * dCanvasSolarXX;
		double num3 = dCanvasSolarXX * dCanvasSolarXX + dCanvasSolarXY * dCanvasSolarXY;
		sx = num / num3 - dOffsetSX;
		sy = num2 / num3 - dOffsetSY;
	}

	private void GetCanvasXY(NavPOI navPOI, out double cx, out double cy)
	{
		navPOI.GetSXY(out var sx, out var sy);
		SolarToCanvas(sx, sy, out cx, out cy);
	}

	protected override void Awake()
	{
		base.Awake();
		if (NavModMessageEvent == null)
		{
			NavModMessageEvent = new NavModMessageEvent();
		}
		NavModMessageEvent.AddListener(OnNavModMessage);
		if (UpdateShipSelection == null)
		{
			UpdateShipSelection = new UpdateShipSelectionEvent();
		}
		UpdateShipSelection.AddListener(LockTarget);
		if (CrewSim.coPlayer != null)
		{
			_playerOwnedShips = CrewSim.system.GetShipsForOwner(CrewSim.coPlayer.strID);
			_hasNotSeenRefuelingTutorial = !CrewSim.coPlayer.HasCond("TutorialRefuelStart");
		}
		follow = new NavPOI(0.0, 0.0);
		CrossHairTarget = new NavPOI(0.0, 0.0);
		aUIs = new List<VectorLine>();
		aShipDraws = new List<ShipDraw>();
		aBODraws = new List<BODraw>();
		aStellarObjectGroups = new List<StellarObjectGroup>();
		objSSEngage = new ShipSitu();
		if (btnNote != null)
		{
			btnNote.onClick.AddListener(ToggleNote);
			btnNote.transform.Find("bmp").GetComponent<RawImage>().texture = DataHandler.LoadPNG("manuals/DON'T CRASH/000.png", bNorm: false);
			btnNote.transform.Find("bmp").GetComponent<RawImage>().texture.filterMode = FilterMode.Bilinear;
		}
		cgClampWarning = GUIRenderTargets.goThis.transform.Find("CanvasOrbitDraw/goLines/ClampDisengageWarning").GetComponent<CanvasGroup>();
		tfPanelIn = base.transform.Find("pnlInside");
		CanvasManager.HideCanvasGroup(tfPanelIn.GetComponent<CanvasGroup>());
		if (btnRescue != null)
		{
			btnRescue.onClick.AddListener(ToggleInnerPanel);
		}
		if (btnDone != null)
		{
			btnDone.onClick.AddListener(ToggleInnerPanel);
		}
		if (btnScrew01 != null)
		{
			btnScrew01.onClick.AddListener(ToggleEditMode);
		}
		if (btnScrew02 != null)
		{
			btnScrew02.onClick.AddListener(ToggleEditMode);
		}
		if (btnScrew03 != null)
		{
			btnScrew03.onClick.AddListener(ToggleEditMode);
		}
		if (btnScrew04 != null)
		{
			btnScrew04.onClick.AddListener(ToggleEditMode);
		}
		base.transform.Find("btnDockArrow").GetComponent<Button>().onClick.AddListener(delegate
		{
			CrewSim.SwitchUI("strGUIPrefabRight");
		});
		ledWLock = base.transform.Find("NavModControls/Container/prefabPnlWASD/bmpKeyW/LedWLock").GetComponent<GUILamp>();
		if (ledWLock != null)
		{
			ledWLock.State = 0;
		}
		chkStationKeeping.isOn = false;
		chkStationKeeping.onValueChanged.AddListener(ToggleStationKeeping);
		txtTimeUTC = GUIRenderTargets.goLines.transform.Find("pnlTitle/txtTime").GetComponent<Text>();
		tfOrbitLabel = Resources.Load<Transform>("GUIShip/lblOrbit");
		ddTravel = tfPanelIn.Find("DebugFastTravel/Dropdown").GetComponent<TMP_Dropdown>();
		btnTravel = tfPanelIn.Find("DebugFastTravel/TravelButton").GetComponent<Button>();
		btnTravel.onClick.AddListener(OnTravelClick);
		AudioManager.AddBtnAudio(btnTravel.gameObject, "ShipUIBtnNSInstaDockIn", "ShipUIBtnNSInstaDockOut");
		goOrbitPanel = GUIRenderTargets.goLines.transform.Find("pnlOrbits").gameObject;
		txtRange = GUIRenderTargets.goLines.transform.Find("pnlOrbits/txtRange").GetComponent<TMP_Text>();
		rectDrawPanel = goOrbitPanel.GetComponent<RectTransform>();
		GUIRenderTargets.goLines.transform.parent.parent.Find("CameraOrbitDraw").GetComponent<Camera>();
		vCanvasOffset = new Vector3(rectDrawPanel.rect.width * rectDrawPanel.lossyScale.x, rectDrawPanel.rect.height * rectDrawPanel.lossyScale.y, 0f);
		rtLines = GUIRenderTargets.goLines.GetComponent<RectTransform>();
		cgStatus = GUIRenderTargets.goLines.transform.Find("pnlStatus").GetComponent<CanvasGroup>();
		srLog = cgStatus.transform.Find("pnlLog").GetComponent<ScrollRect>();
		cgNag = GUIRenderTargets.goLines.transform.Find("pnlNag").GetComponent<CanvasGroup>();
		cgStatus.transform.Find("txtTitle").GetComponent<TMP_Text>().text = DataHandler.GetString("GUI_ORBIT_NAG_TITLE");
		cgNag.transform.Find("txtDesc").GetComponent<TMP_Text>().text = DataHandler.GetString("GUI_ORBIT_NAG_DESC");
		txtNagTimer = cgNag.transform.Find("txtDots").GetComponent<TMP_Text>();
		InitOrbitArea(goOrbitPanel);
		InitFrame(GUIRenderTargets.goLines.transform.Find("pnlFrame").gameObject);
		SetPropMapData("bRCS", "true");
		SetPropMapData("bTorchSafety", "true");
		SetPropMapData("bTorchSafetyCovered", "true");
		SetPropMapData("bCycleSafetyCovered", "true");
		SetPropMapData("nProjSteps", nProjSteps.ToString());
		SetPropMapData("nFollow", "1");
		SetPropMapData("nLabels", "3");
		SetPropMapData("fTimeRate", fTimeFuture.ToString());
		SetPropMapData("shipPOR", "");
		SetPropMapData("boPOR", "");
		SetPropMapData("objSSEngage.fA", objSSEngage.fA.ToString());
		SetPropMapData("objSSEngage.fW", objSSEngage.fW.ToString());
		SetPropMapData("objSSEngage.fRot", objSSEngage.fRot.ToString());
		SetPropMapData("objSSEngage.vPosx", objSSEngage.vPosx.ToString());
		SetPropMapData("objSSEngage.vPosy", objSSEngage.vPosy.ToString());
		SetPropMapData("objSSEngage.vVel.x", objSSEngage.vVelX.ToString());
		SetPropMapData("objSSEngage.vVel.y", objSSEngage.vVelY.ToString());
		SetPropMapData("objSSEngage.vAccEx.x", objSSEngage.vAccEx.x.ToString());
		SetPropMapData("objSSEngage.vAccEx.y", objSSEngage.vAccEx.y.ToString());
		SetPropMapData("objSSEngage.vAccIn.x", objSSEngage.vAccIn.x.ToString());
		SetPropMapData("objSSEngage.vAccIn.y", objSSEngage.vAccIn.y.ToString());
		SetPropMapData("bShowNWZ", "false");
		dCanvasSolarXX = 0.5;
		dCanvasSolarXY = 0.0;
		dOffsetSX = 0.0;
		dOffsetSY = 0.0;
		dEpoch = 0.0;
		dOffsetSX = (double)(rectDrawPanel.rect.width * 0.5f) / dCanvasSolarXX;
		dOffsetSY = (double)(rectDrawPanel.rect.height * 0.5f) / dCanvasSolarXX;
		ssTemp = new ShipSitu();
		_boPredictionGrid = CrewSim.system.GetBoPredictionGrid();
	}

	private void Start()
	{
		_commandFlyUp = InputManager.GetCommand("Thrust Up");
		_commandFlyDown = InputManager.GetCommand("Thrust Down");
		_commandFlyLeft = InputManager.GetCommand("Thrust Left");
		_commandFlyRight = InputManager.GetCommand("Thrust Right");
		_commandShipCCW = InputManager.GetCommand("Turn CCW");
		_commandShipCW = InputManager.GetCommand("Turn CW");
		_commandShipAttitude = InputManager.GetCommand("Attitude");
		_commandShipLockW = InputManager.GetCommand("Locking Thrust");
		_commandZoomIn = InputManager.GetCommand("Zoom Camera In");
		_commandZoomOut = InputManager.GetCommand("Zoom Camera Out");
		_commandClick = InputManager.GetCommand("Click");
		_commandRightClick = InputManager.GetCommand("RightClick");
		_commandMiddleClick = InputManager.GetCommand("MiddleClick");
		_commandPanFaster = InputManager.GetCommand("Pan camera faster");
		_commandScrollWheel = InputManager.GetCommand("ScrollWheel");
		InputManager.OnKeyBindingChanged.AddListener(delegate
		{
			UpdateWASDCluster();
		});
		UpdateWASDCluster();
	}

	private void OnDestroy()
	{
		if (NavModMessageEvent != null)
		{
			NavModMessageEvent.RemoveListener(OnNavModMessage);
		}
		InputManager.OnKeyBindingChanged.RemoveListener(delegate
		{
			UpdateWASDCluster();
		});
		if (Instance == this)
		{
			Instance = null;
		}
	}

	private void OnNavModMessage(NavModMessageType messageType, object arg)
	{
		switch (messageType)
		{
		case NavModMessageType.UpdateUI:
			UpdateUI();
			break;
		case NavModMessageType.WarnClampEngaged:
			CGClampWarning("GUI_ORBIT_WARN_AUTOPILOT_CLAMP");
			break;
		case NavModMessageType.ModeToggle:
			if (arg != null && arg is bool)
			{
				bRCS = (bool)arg;
			}
			break;
		case NavModMessageType.ManeuverThrustSlider:
			break;
		}
	}

	private VectorLine GetLineBodyForShip(Ship objShip, ShipDraw sd, ShipInfo si)
	{
		bool flag = _playerOwnedShips.Contains(objShip.strRegID);
		bool flag2 = si?.Known ?? true;
		if (objShip.IsStation() || objShip.Classification == Ship.TypeClassification.Waypoint || objShip.Classification == Ship.TypeClassification.Asteroid || objShip.Classification == Ship.TypeClassification.SignalBeacon)
		{
			BodyOrbit nearestBO = CrewSim.system.GetNearestBO(objShip.objSS, StarSystem.fEpoch, bIncludePlaceholders: false);
			bool flag3 = false;
			if (nearestBO != null)
			{
				flag3 = nearestBO.GravRadius > objShip.objSS.GetDistance(nearestBO.dXReal, nearestBO.dYReal);
			}
			Color c = (flag ? clrBlue01 : clrWhite01);
			List<Vector2> aVerts;
			switch (objShip.Classification)
			{
			case Ship.TypeClassification.Buoy:
			case Ship.TypeClassification.Outpost:
				aVerts = NavIcon.Outpost(sd.fRadiusM);
				break;
			case Ship.TypeClassification.Infrastructure:
				aVerts = NavIcon.Infrastructure(sd.fRadiusM);
				break;
			case Ship.TypeClassification.GroundStation:
				aVerts = NavIcon.GroundStation(sd.fRadiusM);
				break;
			case Ship.TypeClassification.GroundStationUnfinished:
				aVerts = NavIcon.GroundStationUnfinished(sd.fRadiusM);
				c = clrWhite02;
				break;
			case Ship.TypeClassification.OrbitalStation:
				aVerts = NavIcon.OrbitalStation(sd.fRadiusM);
				break;
			case Ship.TypeClassification.OrbitalStationUnfinished:
				aVerts = NavIcon.OrbitalStationUnfinished(sd.fRadiusM);
				c = clrWhite02;
				break;
			case Ship.TypeClassification.Waypoint:
				c = RacingLeagueManager.ColorWaypoint;
				aVerts = NavIcon.Circle(sd.fRadiusM);
				break;
			case Ship.TypeClassification.Asteroid:
				c = clrAsteroid;
				aVerts = NavIcon.Octagon(sd.fRadiusM);
				break;
			case Ship.TypeClassification.SignalBeacon:
				c = GetFactionColor(sd.ship);
				aVerts = NavIcon.Beacon(sd.fRadiusM);
				break;
			case Ship.TypeClassification.SecurityOutpost:
				aVerts = NavIcon.Triangle(sd.fRadiusM);
				break;
			default:
				aVerts = ((flag3 || objShip.Classification == Ship.TypeClassification.GroundStation) ? NavIcon.GroundStation(sd.fRadiusM) : NavIcon.OrbitalStation(sd.fRadiusM));
				break;
			}
			if (objShip.IsUnderConstruction)
			{
				if (!flag2)
				{
					aVerts = NavIcon.Asterisk();
				}
				return NavIcon.SetupVectorLine(objShip.strRegID, clrWhite02, goOrbitPanel, aVerts);
			}
			return NavIcon.SetupVectorLine(objShip.strRegID, c, goOrbitPanel, aVerts);
		}
		if (objShip.Classification == Ship.TypeClassification.Projectile)
		{
			Color c2 = (objShip.ShipCO.HasCond("IsAmmoDecoyMissile") ? clrDecoy : clrRed01);
			VectorLine vectorLine = NavIcon.SetupVectorLine(objShip.strRegID, c2, goOrbitPanel, NavIcon.Projectile(25f));
			vectorLine.lineType = LineType.Continuous;
			return vectorLine;
		}
		if (!flag2 && objShip.IsDerelict())
		{
			Color c3 = (flag ? clrBlue01 : clrWhite02);
			VectorLine vectorLine2 = NavIcon.SetupVectorLine(objShip.strRegID, c3, goOrbitPanel, NavIcon.Asterisk());
			vectorLine2.lineType = LineType.Discrete;
			return vectorLine2;
		}
		VectorLine vectorLine3;
		if (objShip.DMGStatus == Ship.Damage.Derelict)
		{
			Color c4 = (flag ? clrBlue01 : clrWhite02);
			vectorLine3 = NavIcon.SetupVectorLine(objShip.strRegID, c4, goOrbitPanel, NavIcon.Ship(sd.fRadiusM));
			vectorLine3.lineType = LineType.Discrete;
		}
		else
		{
			Color c5 = ((!flag) ? clrWhite01 : clrBlue01);
			if (objShip.IsFlyingDark())
			{
				c5 = clrWhite02;
			}
			float fRadiusMeters = DERELICTSIZE;
			if (si != null)
			{
				if (si.shipSignature > 70)
				{
					fRadiusMeters = sd.fRadiusM;
				}
				if (si.mark != 0)
				{
					if (si.mark == 1)
					{
						c5 = clrRed01;
					}
					else if (si.mark == 2)
					{
						c5 = clrGreen02;
					}
				}
			}
			List<Vector2> aVerts2 = (objShip.IsUsingTorchDrive ? NavIcon.ShipActiveTorch(fRadiusMeters) : NavIcon.Ship(fRadiusMeters));
			vectorLine3 = NavIcon.SetupVectorLine(objShip.strRegID, c5, goOrbitPanel, aVerts2);
			vectorLine3.lineType = LineType.Discrete;
		}
		sd.silhouetteDrawPoints = NavIcon.GetSilhouette(objShip, sd.fRadiusM);
		return vectorLine3;
	}

	private Color GetFactionColor(Ship ship)
	{
		string shipOwner = CrewSim.system.GetShipOwner(ship.strRegID);
		Color color = clrRed01;
		if (string.IsNullOrEmpty(shipOwner))
		{
			return color;
		}
		JsonFaction faction = CrewSim.system.GetFaction(shipOwner);
		if (faction != null && faction.strFactionColor != null)
		{
			color = DataHandler.GetColor(faction.strFactionColor);
		}
		return color;
	}

	private ShipDraw SetupShipDraw(Ship objShip)
	{
		if (objShip == null)
		{
			Debug.Log("ERROR: No ship provided for SetupShipDraw!");
			Debug.Break();
			return null;
		}
		ShipDraw shipDraw = new ShipDraw(objShip);
		ShipInfo shipInfo = ShipInfo.GetShipInfo(GetNavStationShip(), shipDraw.ship, ShipPropMap);
		shipDraw.lineBodySymbol = GetLineBodyForShip(objShip, shipDraw, shipInfo);
		shipDraw.lineBody = shipDraw.lineBodySymbol;
		if (objShip.IsStation() && !objShip.IsNotAFullStation)
		{
			shipDraw.lineNoWakeRange = CreateBodyLine(objShip.strRegID + "_NWZ", clrOrange02Half, 2.005376E-06f, goOrbitPanel);
		}
		else if (objShip.Classification == Ship.TypeClassification.SignalBeacon)
		{
			shipDraw.lineNoWakeRange = CreateBodyLine(objShip.strRegID + "_NWZ", clrRed01, 1.0026881E-05f, goOrbitPanel);
		}
		shipDraw.DoNotRotate = !shipInfo.Known || shipDraw.ship.IsStation();
		DrawArc(shipDraw, objShip.strRegID);
		Color color;
		if (objShip == GetNavStationShip())
		{
			sdNS = shipDraw;
			for (int i = 0; i < nProjStepsSelf; i++)
			{
				color = shipDraw.lineBody.color;
				color.a = 1f - 1f * (float)i / (float)nProjStepsSelf;
				VectorLine lineBodyForShip = GetLineBodyForShip(objShip, sdNS, null);
				lineBodyForShip.color = color;
				sdNS.AddProjection(lineBodyForShip);
			}
		}
		else
		{
			if (shipDraw.lineBodyNoSignal == null)
			{
				shipDraw.lineBodyNoSignal = NavIcon.SetupVectorLine(objShip.strRegID + "_noSig", clrNoSig, goOrbitPanel, NavIcon.OtherKnown(100f));
				shipDraw.lineBodyNoSignal.lineType = LineType.Discrete;
				VectorLine vectorLine = NavIcon.SetupVectorLine(objShip.strRegID + "_noSigPred", clrNoSig, goOrbitPanel, NavIcon.OtherKnown(100f));
				vectorLine.lineType = LineType.Discrete;
				shipDraw.AddSignalProjection(vectorLine);
			}
			for (int j = 0; j < nProjSteps; j++)
			{
				color = shipDraw.lineBody.color;
				color.a = 1f - 1f * (float)j / (float)nProjSteps;
				VectorLine lineBodyForShip2 = GetLineBodyForShip(objShip, shipDraw, shipInfo);
				lineBodyForShip2.color = color;
				shipDraw.AddProjection(lineBodyForShip2);
			}
		}
		if (shipDraw.ship.ShipCO.HasCond("IsTutorialDerelict"))
		{
			shipInfo.isTutorialDerelict = true;
			shipDraw.sDisplayName = "(TUTORIAL DERELICT)";
			shipDraw.sDisplayRegID = "(TUTORIAL DERELICT)";
		}
		shipDraw.SetShipInfo(shipInfo);
		if (shipDraw.silhouetteDrawPoints != null && shipDraw.silhouetteDrawPoints.Count > 0)
		{
			shipDraw.lineBodySilhouette = new VectorLine(objShip.strRegID + "_sil", shipDraw.silhouetteDrawPoints, shipDraw.lineBody.lineWidth, LineType.Continuous, Joins.Weld);
			shipDraw.lineBodySilhouette.color = shipDraw.lineBody.color;
			shipDraw.lineBodySilhouette.SetCanvas(goOrbitPanel, worldPositionStays: false);
			shipDraw.lineBodySilhouette.active = false;
		}
		shipDraw.SetupLabel(tfOrbitLabel, goOrbitPanel.transform);
		shipDraw.linePath = new VectorLine(objShip.strRegID + "-Path", new List<Vector2>(), fLineWidth, LineType.Continuous, Joins.Weld);
		color = shipDraw.lineBody.color;
		color.a /= 2f;
		shipDraw.linePath.color = color;
		shipDraw.linePath.SetCanvas(goOrbitPanel, worldPositionStays: false);
		return shipDraw;
	}

	public ShipDraw FindShipDraw(Ship objShip)
	{
		return FindShipDraw(objShip.strRegID);
	}

	public ShipDraw FindShipDraw(string regId)
	{
		for (int i = 0; i < aShipDraws.Count; i++)
		{
			ShipDraw shipDraw = aShipDraws[i];
			if (shipDraw != null && shipDraw.ship != null && shipDraw.ship.strRegID == regId)
			{
				return shipDraw;
			}
		}
		return null;
	}

	private ShipDraw RemoveShipDrawFromPool(ref List<ShipDraw> pool, string regId)
	{
		for (int i = 0; i < pool.Count; i++)
		{
			ShipDraw shipDraw = pool[i];
			if (shipDraw == null || shipDraw.ship == null)
			{
				pool.RemoveAt(i);
			}
			else if (shipDraw.ship.strRegID == regId)
			{
				pool.RemoveAt(i);
				return shipDraw;
			}
		}
		return null;
	}

	public StellarObjectDraw FindStellarObjectDraw(string regId)
	{
		if (aStellarObjectGroups == null)
		{
			return null;
		}
		foreach (StellarObjectGroup aStellarObjectGroup in aStellarObjectGroups)
		{
			if (aStellarObjectGroup != null && aStellarObjectGroup.StellarObjectDraws != null)
			{
				StellarObjectDraw stellarObjectDraw = aStellarObjectGroup.FindStellarObjectDraw(regId);
				if (stellarObjectDraw != null)
				{
					return stellarObjectDraw;
				}
			}
		}
		return null;
	}

	private Ship GetNavStationShip()
	{
		return COSelf.ship;
	}

	private ShipSitu GetNavStationShipSitu()
	{
		return GetNavStationShip().objSS;
	}

	public static void TriggerShipRedraw(string regId)
	{
		if (!(Instance == null))
		{
			Instance.InvalidateShipDraw(regId);
		}
	}

	public static void UpdateShipDraw(string regId, ShipInfo si = null)
	{
		if (Instance == null)
		{
			return;
		}
		ShipDraw shipDraw = Instance.FindShipDraw(regId);
		if (shipDraw != null)
		{
			if (si == null)
			{
				si = ShipInfo.GetShipInfo(regId, Instance.ShipPropMap);
			}
			if (si != null)
			{
				shipDraw.shipInfo = si;
			}
		}
	}

	public static void TriggerArcRedraw(string regId)
	{
		if (!(Instance == null))
		{
			ShipDraw shipDraw = Instance.FindShipDraw(regId);
			if (shipDraw != null && shipDraw.ship != null)
			{
				shipDraw.bRedrawArcs = true;
			}
		}
	}

	private void DrawArc(ShipDraw shipDraw, string regId)
	{
		ShipDraw shipDraw2 = shipDraw;
		if (shipDraw2 == null)
		{
			shipDraw2 = FindShipDraw(regId);
		}
		if (shipDraw2 == null || shipDraw2.ship == null)
		{
			return;
		}
		shipDraw2.bRedrawArcs = false;
		List<CondOwner> activatedWeapons = shipDraw2.ship.WeaponsSystem.GetActivatedWeapons(refetch: true);
		bool flag = false;
		if (activatedWeapons != null)
		{
			int num = 0;
			if (shipDraw2.aWeaponArcs == null)
			{
				shipDraw2.aWeaponArcs = new List<WeaponArcDTO>();
			}
			float num2 = (float)shipDraw2.ship.WeaponsSystem.fRangeModGunner;
			foreach (CondOwner item in activatedWeapons)
			{
				if (!item.HasCond("IsPowered"))
				{
					continue;
				}
				float num3 = (float)item.GetCondAmount("IsShipWeaponArcAngleReduction", isThreshold: false);
				float num4 = (float)item.GetCondAmount("IsShipWeaponArcAngle", isThreshold: false) - num3;
				if (num4 < 1f)
				{
					num4 = 1f;
				}
				float num5 = (float)item.GetCondAmount("IsShipWeaponArcRange", isThreshold: false);
				if (item.HasCond("IsShipWeaponMassThrower", isThreshold: false))
				{
					num5 *= num2;
				}
				if (num5 == 0f)
				{
					continue;
				}
				WeaponArcDTO weaponArcDTO = null;
				if (shipDraw2.aWeaponArcs.Count > num)
				{
					weaponArcDTO = shipDraw2.aWeaponArcs[num];
					if (weaponArcDTO == null)
					{
						weaponArcDTO = new WeaponArcDTO();
						shipDraw2.aWeaponArcs[num] = weaponArcDTO;
					}
				}
				else
				{
					weaponArcDTO = new WeaponArcDTO();
					shipDraw2.aWeaponArcs.Add(weaponArcDTO);
				}
				num++;
				VectorLine vectorLine = weaponArcDTO.Arc;
				if (vectorLine == null)
				{
					vectorLine = NavIcon.SetupVectorLine(shipDraw2.ship.strRegID + "_W", (num3 > 0f) ? clrLocalAuthority : clrWhite02, goOrbitPanel, NavIcon.WeaponArc(null, num5, num4));
				}
				else
				{
					vectorLine.name = shipDraw2.ship.strRegID + "_W";
					vectorLine.color = ((num3 > 0f) ? clrLocalAuthority : clrWhite02);
					vectorLine.points2 = NavIcon.WeaponArc(vectorLine.points2, num5, num4);
				}
				vectorLine.lineType = LineType.Continuous;
				weaponArcDTO.Arc = vectorLine;
				weaponArcDTO.Range = num5;
				weaponArcDTO.Rotation = MathF.PI / 180f * item.Item.fLastRotation;
				weaponArcDTO.Fresh = true;
				if (!flag && num3 != 0f && item.HasCond("IsShipWeaponArcBeepLock"))
				{
					flag = true;
				}
			}
			for (int num6 = shipDraw2.aWeaponArcs.Count - 1; num6 > num; num6--)
			{
				VectorLine line = shipDraw2.aWeaponArcs[num6].Arc;
				VectorLine.Destroy(ref line);
				shipDraw2.aWeaponArcs.RemoveAt(num6);
			}
			if (flag)
			{
				AudioManager.am.PlayAudioEmitter("ShipUINSNavArcTick", bLoop: false, bNoRestart: true);
			}
		}
		else if (shipDraw2.aWeaponArcs != null)
		{
			for (int num7 = shipDraw2.aWeaponArcs.Count - 1; num7 >= 0; num7--)
			{
				VectorLine line2 = shipDraw2.aWeaponArcs[num7].Arc;
				VectorLine.Destroy(ref line2);
				shipDraw2.aWeaponArcs.RemoveAt(num7);
			}
		}
	}

	public static void RemoveBODraw(string boName)
	{
		if (!(Instance == null))
		{
			Instance.RemoveOrbital(boName);
		}
	}

	public static void AddDebugDraw(string name, ShipSitu situ, Color color, bool isPrediction = false)
	{
		if (!(Instance == null) && Instance.dictPropMap != null)
		{
			Instance.SetupDebugDraw(name, situ, color, isPrediction);
		}
	}

	public static void AddDebugDraw(string name, Point pos)
	{
		ShipSitu shipSitu = new ShipSitu
		{
			vPosx = pos.X,
			vPosy = pos.Y
		};
		shipSitu.LockToBO();
		AddDebugDraw(name, shipSitu);
	}

	public static void AddDebugDraw(string name, ShipSitu situ, bool isPrediction = false, string reg = null)
	{
		Color color = Color.cyan;
		if (reg != null)
		{
			int num = 0;
			foreach (char c in reg)
			{
				num += c;
			}
			int num2 = num % colorArray.Length;
			color = colorArray[num2];
		}
		AddDebugDraw(name, situ, color, isPrediction);
	}

	private void SetupDebugDraw(string drawName, ShipSitu situ, Color color, bool isPrediction)
	{
		foreach (DebugDraw aDebugDraw in aDebugDraws)
		{
			if (aDebugDraw._displayName == drawName)
			{
				aDebugDraw.MarkForRemoval();
			}
		}
		DebugDraw debugDraw = new DebugDraw(drawName, situ, isPrediction, NavIcon.SetupVectorLine(drawName, color, goOrbitPanel, NavIcon.Diamond(DebugDraw.SIZE)));
		debugDraw.SetupLabel(tfOrbitLabel, goOrbitPanel);
		aDebugDraws.Add(debugDraw);
	}

	public static void ClearDebugDrawsForRegId(string regId)
	{
		if (!(Instance == null) && Instance.dictPropMap != null)
		{
			Instance.ClearDebugDraws(regId);
		}
	}

	public void ClearDebugDraws(string regId = null)
	{
		foreach (DebugDraw aDebugDraw in aDebugDraws)
		{
			if (string.IsNullOrEmpty(regId) || aDebugDraw._displayName.Contains(regId))
			{
				aDebugDraw.MarkForRemoval();
			}
		}
	}

	public SignalVisibility VisibleFromNavStation(ShipDraw sd, Ship ship = null)
	{
		Ship ship2 = ((sd != null) ? sd.ship : ship);
		if (ship2 == null || ship2.bDestroyed)
		{
			return SignalVisibility.None;
		}
		if (ship2.ShipCO.HasCond("IsTutorialDerelict"))
		{
			return SignalVisibility.Visible;
		}
		Ship navStationShip = GetNavStationShip();
		double num = navStationShip.objSS.GetRangeTo(ship2.objSS) * 149597872.0;
		float num2 = Mathf.Min(GetNavStationShip().fVisibilityRangeMod, ship2.fVisibilityRangeMod);
		if (ship2.IsStation() && !ship2.IsUnderConstruction)
		{
			ShipInfo shipInfo = ShipInfo.GetShipInfo(navStationShip, ship2, ShipPropMap);
			if (shipInfo != null && shipInfo.Known)
			{
				return SignalVisibility.Visible;
			}
			if (num > 2000.0 * (double)num2)
			{
				return SignalVisibility.None;
			}
		}
		if (ship2 == navStationShip || ship2.IsDockedWith(navStationShip) || ship2.Classification == Ship.TypeClassification.SignalBeacon)
		{
			return SignalVisibility.Visible;
		}
		if (ship2.HideFromSystem)
		{
			return SignalVisibility.None;
		}
		if (_showAllShips)
		{
			return SignalVisibility.Visible;
		}
		if (navStationShip.ElectronicSystems.aElectronicSystems == null || navStationShip.ElectronicSystems.aElectronicSystems.Count == 0)
		{
			navStationShip.ElectronicSystems.UpdateSensorStates();
		}
		if (boMainOccluder != null && StarSystem.IsLOSBlockedByBO(boMainOccluder.bo, COSelf.ship, ship2.objSS))
		{
			return SignalVisibility.None;
		}
		if (!navStationShip.ElectronicSystems.HasAnySensorOn())
		{
			return SignalVisibility.Partial;
		}
		ShipSignature signature = new ShipSignature(ship2, navStationShip);
		double signatureStrength = navStationShip.ElectronicSystems.GetSignatureStrength(signature, num, num2);
		if (sd != null && sd.shipInfo != null)
		{
			bool flag = Math.Abs((double)sd.shipInfo.shipSignature - signatureStrength) > 0.01;
			sd.shipInfo.shipSignature = MathUtils.RoundToInt(signatureStrength * 100.0);
			if (sd.shipInfo.lockingProgress > 0 && signatureStrength < (double)navStationShip.ElectronicSystems.DetectionThreshold)
			{
				sd.shipInfo.lockingProgress = 0;
				flag = true;
			}
			if (flag)
			{
				ShipInfo.SetShipInfo(sd.shipInfo, ShipPropMap);
			}
		}
		if (!(signatureStrength >= (double)navStationShip.ElectronicSystems.DetectionThreshold))
		{
			return SignalVisibility.Partial;
		}
		return SignalVisibility.Visible;
	}

	public SignalVisibility StellarObjectVisible(Ship playerShip, IStellarObject stellarObject, StellarObjectDraw stellarDraw = null)
	{
		if (stellarObject == null)
		{
			return SignalVisibility.None;
		}
		double num = playerShip.objSS.GetRangeTo(stellarObject.objSS) * 149597872.0;
		if (num > 1000.0)
		{
			return SignalVisibility.Partial;
		}
		float fVisibilityRangeMod = playerShip.fVisibilityRangeMod;
		if (playerShip.ElectronicSystems.aElectronicSystems == null || playerShip.ElectronicSystems.aElectronicSystems.Count == 0)
		{
			playerShip.ElectronicSystems.UpdateSensorStates();
		}
		if (boMainOccluder != null && StarSystem.IsLOSBlockedByBO(boMainOccluder.bo, COSelf.ship, stellarObject.objSS))
		{
			return SignalVisibility.None;
		}
		if (!playerShip.ElectronicSystems.HasAnySensorOn())
		{
			return SignalVisibility.None;
		}
		ShipSignature signature = ((stellarDraw != null) ? stellarDraw.GetSignature(playerShip) : new ShipSignature(stellarObject, playerShip));
		double signatureStrength = playerShip.ElectronicSystems.GetSignatureStrength(signature, num, fVisibilityRangeMod);
		float num2 = 0.3f;
		if (!(signatureStrength >= (double)num2))
		{
			return SignalVisibility.Partial;
		}
		return SignalVisibility.Visible;
	}

	public void FlashNWZCircle()
	{
		if (_nwzRoutine != null)
		{
			StopCoroutine(_nwzRoutine);
		}
		_nwzRoutine = StartCoroutine(_FlashNWZCircle());
	}

	private IEnumerator _FlashNWZCircle()
	{
		bool oldValue = GetPropMapData("bShowNWZ", defaultReturnValue: false);
		for (int i = 3; i >= 0; i--)
		{
			bShowNWZ = true;
			yield return new WaitForSecondsRealtime(0.2f);
			bShowNWZ = false;
			yield return new WaitForSecondsRealtime(0.2f);
		}
		bShowNWZ = true;
		yield return new WaitForSecondsRealtime(1.5f);
		SetPropMapData("bShowNWZ", oldValue.ToString());
		bShowNWZ = oldValue;
		_nwzRoutine = null;
	}

	private void LoadSystem()
	{
		List<AsteroidField> list = new List<AsteroidField>();
		foreach (KeyValuePair<string, BodyOrbit> aBO in CrewSim.system.aBOs)
		{
			if (aBO.Value.nDrawFlagsBody != 1 || aBO.Value.nDrawFlagsTrack != 1)
			{
				if (aBO.Value.IsAsteroidField)
				{
					list.Add((AsteroidField)aBO.Value);
				}
				else
				{
					AddOrbital(aBO.Value, goOrbitPanel);
				}
			}
		}
		UpdateShipDraw();
		StartCoroutine(DelayedAsteroidLoading(list));
	}

	private void PanCanvasImmediateS(double sdx, double sdy)
	{
		dOffsetSX += sdx;
		dOffsetSY += sdy;
	}

	private void PanCanvasImmediateC(double cdx, double cdy)
	{
		CanvasToSolar(0.0, 0.0, out var sx, out var sy);
		CanvasToSolar(cdx, cdy, out var sx2, out var sy2);
		PanCanvasImmediateS(sx - sx2, sy - sy2);
	}

	public void ResetCrosshair()
	{
		CrossHairTarget.fOffsetSX = 0.0;
		CrossHairTarget.fOffsetSY = 0.0;
		AudioManager.am.PlayAudioEmitter("ShipUINSMapPan04", bLoop: false, bNoRestart: true);
	}

	public void MoveCrosshair(double cdx, double cdy)
	{
		CanvasToSolar(0.0, 0.0, out var sx, out var sy);
		CanvasToSolar(cdx, cdy, out var sx2, out var sy2);
		CrossHairTarget.fOffsetSX -= sx - sx2;
		CrossHairTarget.fOffsetSY -= sy - sy2;
		AudioManager.am.PlayAudioEmitter("ShipUINSMapPan04", bLoop: false, bNoRestart: true);
	}

	private float GetDeltaTime()
	{
		float num = Math.Min(Time.unscaledDeltaTime, 1f / 15f);
		float num2 = 1f / 60f;
		if (0.9f * num2 < num && num < 1.1f * num2)
		{
			num = num2;
		}
		return num;
	}

	public void ResetTime()
	{
		dEpoch = StarSystem.fEpoch;
		fTimeFuture = 1f;
		fTimeFutureTarget = 1f;
	}

	private void UpdateTime()
	{
		if (fTimeFutureTarget == 0f || fTimeFuture == 0f)
		{
			ResetTime();
		}
		float num = Mathf.Log(fTimeFuture);
		float num2 = Mathf.Log(fTimeFutureTarget);
		float num3 = 0.9f;
		num = num * num3 + num2 * (1f - num3);
		fTimeFuture = Mathf.Exp(num);
		if (fTimeFuture < 1.02f)
		{
			dEpoch = StarSystem.fEpoch;
		}
		else
		{
			dEpoch = StarSystem.fEpoch + (double)fTimeFuture;
		}
		if (follow.bodyOrbit != null)
		{
			double num4 = dEpoch - StarSystem.fEpoch;
			num4 %= follow.bodyOrbit.fPeriod;
			dEpoch = StarSystem.fEpoch + num4;
		}
		txtTimeUTC.text = StarSystem.sUTCEpoch + "\n" + MathUtils.GetUTCFromS(dEpoch - StarSystem.fEpoch);
		if (dEpoch < StarSystem.fEpoch)
		{
			dEpoch = StarSystem.fEpoch;
		}
		sb.Length = 0;
		sb.AppendLine(StarSystem.sUTCEpoch);
		sb.Append(MathUtils.GetUTCFromS(dEpoch - StarSystem.fEpoch));
		txtTimeUTC.text = sb.ToString();
		if (CrossHairTarget.fTargetFuture > 0.0)
		{
			CrossHairTarget.fTargetFuture = dEpoch - StarSystem.fEpoch;
		}
	}

	private void MoveTowards(ref float x, float dir)
	{
		if (x * dir < 0f)
		{
			x *= 0.5f;
		}
		x += dir;
	}

	private float GetDeltaVRemaining(bool bAllowDocked)
	{
		if (!bAllowDocked)
		{
			return (float)GetNavStationShip().DeltaVRemainingRCS;
		}
		double num = GetNavStationShip().Mass;
		foreach (Ship allDockedShip in GetNavStationShip().GetAllDockedShips())
		{
			num += allDockedShip.Mass;
		}
		return (float)(GetNavStationShip().DeltaVRemainingRCS * GetNavStationShip().Mass / num);
	}

	private float GetRCSReactionMass()
	{
		return (float)GetNavStationShip().GetRCSRemain();
	}

	private float GetPowerConnected()
	{
		if (COSelf == null)
		{
			return 0f;
		}
		Powered component = COSelf.GetComponent<Powered>();
		if (component == null)
		{
			return 0f;
		}
		return (float)component.PowerConnected;
	}

	private void KeyboardInput(float delX, float delY)
	{
		if (COSelf.HasCond("IsDamagedSoftware"))
		{
			return;
		}
		if (GetKnobFollowState > 0)
		{
			CanvasToSolar(0.0, 0.0, out var sx, out var sy);
			CanvasToSolar(delX, delY, out var sx2, out var sy2);
			float num = 0.2f;
			double num2 = (sx2 - sx) * (double)num;
			double num3 = (sy2 - sy) * (double)num;
			dFollowOffsetSX += num2;
			dFollowOffsetSY += num3;
			oldFollowCX += delX * num;
			oldFollowCY += delY * num;
		}
		else
		{
			if ((double)delX != 0.0)
			{
				MoveTowards(ref fVelocityX, delX);
			}
			if ((double)delY != 0.0)
			{
				MoveTowards(ref fVelocityY, delY);
			}
		}
	}

	private void Update()
	{
		if (base.COSelf == null || !_initialized)
		{
			return;
		}
		if (cgNag.alpha > 0f)
		{
			if (StarSystem.fEpoch < fEpochNagEnd)
			{
				string text = "";
				for (double num = fEpochNagEnd - StarSystem.fEpoch; num > 0.0; num -= 1.0)
				{
					text += ".";
				}
				txtNagTimer.text = text;
				return;
			}
			CanvasManager.HideCanvasGroup(cgNag);
		}
		if (!bActive)
		{
			StopMapAudio();
		}
		else if (COSelf == null || COSelf.HasCond("IsOff"))
		{
			CrewSim.LowerUI();
		}
		else
		{
			if (_editModeActive)
			{
				return;
			}
			MouseHandler();
			KeyHandler();
			if (chkStationKeeping.isOn && COSelf.ship != null)
			{
				AIShip aIShipByRegID = AIShipManager.GetAIShipByRegID(COSelf.ship.strRegID);
				if (aIShipByRegID == null || aIShipByRegID.ActiveCommandName != "HoldStationAutoPilot")
				{
					chkStationKeeping.isOn = false;
				}
			}
			if (!follow.IsShipOrOrbit())
			{
				SetOldFollow();
			}
			UpdateTime();
			UpdateShipDraw();
			float num2 = 15f * GetDeltaTime();
			float num3 = 7f * GetDeltaTime();
			if (!bRCS)
			{
				if (_commandShipCCW.InputAction.IsPressed() || dictWASD["Q"].bPressed)
				{
					MoveTowards(ref fVelocityYaw, num2);
				}
				if (_commandShipCW.InputAction.IsPressed() || dictWASD["E"].bPressed)
				{
					MoveTowards(ref fVelocityYaw, 0f - num2);
				}
			}
			if (_commandZoomIn.InputAction.IsPressed() || dictWASD["+"].bPressed)
			{
				fVelocityZ += num3;
			}
			if (_commandZoomOut.InputAction.IsPressed() || dictWASD["-"].bPressed)
			{
				fVelocityZ -= num3;
			}
			if (OnZoom != null)
			{
				OnZoom(dScopeRadius);
			}
			float num4 = Mathf.Cos(fVelocityYaw * GetDeltaTime()) * Mathf.Exp(fVelocityZ * GetDeltaTime());
			float num5 = Mathf.Sin(fVelocityYaw * GetDeltaTime()) * Mathf.Exp(fVelocityZ * GetDeltaTime());
			double num6 = dCanvasSolarXX * (double)num4 - dCanvasSolarXY * (double)num5;
			double num7 = dCanvasSolarXX * (double)num5 + dCanvasSolarXY * (double)num4;
			dCanvasSolarXX = num6;
			dCanvasSolarXY = num7;
			float num8 = 1500f * GetDeltaTime();
			if (!bRCS)
			{
				if (_commandFlyLeft.InputAction.IsPressed() || dictWASD["A"].bPressed)
				{
					KeyboardInput(0f - num8, 0f);
				}
				if (_commandFlyRight.InputAction.IsPressed() || dictWASD["D"].bPressed)
				{
					KeyboardInput(num8, 0f);
				}
				if (_commandFlyUp.InputAction.IsPressed() || dictWASD["W"].bPressed)
				{
					KeyboardInput(0f, num8);
				}
				if (_commandFlyDown.InputAction.IsPressed() || dictWASD["S"].bPressed)
				{
					KeyboardInput(0f, 0f - num8);
				}
			}
			fZoomTimer -= GetDeltaTime();
			if (0f < fZoomTimer)
			{
				float num9 = (float)(dCanvasSolarXX * dCanvasSolarXX + dCanvasSolarXY * dCanvasSolarXY) * Mathf.Exp(fVelocityZ * 2f / 8f);
				float num10 = Mathf.Log((float)dMagTarget / num9);
				fVelocityZ += num10 * 15f * GetDeltaTime();
				if (float.IsPositiveInfinity(fVelocityZ))
				{
					fVelocityZ = 100f;
				}
				else if (float.IsNegativeInfinity(fVelocityZ))
				{
					fVelocityZ = -100f;
				}
			}
			if (GetKnobRefState > 0 && GetKnobFollowState > 0)
			{
				double cx = 0.0;
				double cy = 0.0;
				double sx = 0.0;
				double sy = 0.0;
				follow.UpdateTime(dEpoch);
				follow.GetSXY(out var sx2, out var sy2);
				follow.GetParentSXY(dEpoch, out sx, out sy);
				SolarToCanvas(sx, sy, out cx, out cy);
				SolarToCanvas(sx2, sy2, out var cx2, out var cy2);
				double num11 = (double)Mathf.Atan2((float)(cx2 - cx), (float)(cy - cy2)) * -0.4000000059604645;
				num4 = Mathf.Cos((float)num11);
				num5 = Mathf.Sin((float)num11);
				num6 = dCanvasSolarXX * (double)num4 - dCanvasSolarXY * (double)num5;
				num7 = dCanvasSolarXX * (double)num5 + dCanvasSolarXY * (double)num4;
				dCanvasSolarXX = num6;
				dCanvasSolarXY = num7;
				CanvasToSolar(cx2, cy2, out var sx3, out var sy3);
				dOffsetSX -= sx2 - sx3;
				dOffsetSY -= sy2 - sy3;
			}
			follow.UpdateTime(dEpoch);
			follow.GetSXY(out var sx4, out var sy4);
			sx4 += dFollowOffsetSX;
			sy4 += dFollowOffsetSY;
			SolarToCanvas(sx4, sy4, out var cx3, out var cy3);
			PanCanvasImmediateC(cx3 - oldFollowCX, cy3 - oldFollowCY);
			if (GetKnobFollowState > 0)
			{
				follow.GetSXY(out var sx5, out var sy5);
				sx5 += dFollowOffsetSX;
				sy5 += dFollowOffsetSY;
				SolarToCanvas(sx5, sy5, out var cx4, out var cy4);
				float num12 = 0.2f;
				double num13 = rectDrawPanel.rect.width * 0.5f + fVelocityX * num12;
				double num14 = rectDrawPanel.rect.height * 0.5f + fVelocityY * num12;
				if (GetKnobRefState > 0)
				{
					num14 -= (double)(rectDrawPanel.rect.height * 0.25f);
				}
				double num15 = (cx4 - num13) * (double)GetDeltaTime() * 25.0;
				double num16 = (cy4 - num14) * (double)GetDeltaTime() * 25.0;
				fVelocityX += (float)num15;
				fVelocityY += (float)num16;
			}
			PanCanvasImmediateC(fVelocityX * GetDeltaTime(), fVelocityY * GetDeltaTime());
			SetOldFollow();
			CanvasToSolar(0.0, 0.0, out var sx6, out var sy6);
			CanvasToSolar(rectDrawPanel.rect.width * 0.5f, 0.0, out var sx7, out var sy7);
			dScopeRadius = (float)MathUtils.GetMagnitude(sx7 - sx6, sy7 - sy6);
			fVelocityX *= Mathf.Exp(-5f * GetDeltaTime());
			fVelocityY *= Mathf.Exp(-5f * GetDeltaTime());
			fVelocityZ *= Mathf.Exp(-8f * GetDeltaTime());
			fVelocityYaw *= Mathf.Exp(-8f * GetDeltaTime());
			if (cgStatus.alpha != 1f)
			{
				if (Mathf.Abs(fVelocityX) > 10f || Mathf.Abs(fVelocityY) > 10f)
				{
					AudioManager.am.PlayAudioEmitter("ShipUINSMapPan01", bLoop: true);
				}
				else
				{
					AudioManager.am.StopAudioEmitter("ShipUINSMapPan01");
				}
				if (Mathf.Abs(fVelocityZ) > 0.1f || Mathf.Abs(fVelocityYaw) > 0.1f)
				{
					AudioManager.am.PlayAudioEmitter("ShipUINSMapPan03", bLoop: true);
				}
				else
				{
					AudioManager.am.StopAudioEmitter("ShipUINSMapPan03");
				}
			}
			else
			{
				StopMapAudio();
			}
			DrawSystem();
			UpdateUIs();
		}
	}

	private void StopMapAudio()
	{
		AudioManager.am.StopAudioEmitter("ShipUINSMapPan01");
		AudioManager.am.StopAudioEmitter("ShipUINSMapPan02");
		AudioManager.am.StopAudioEmitter("ShipUINSMapPan03");
	}

	public void SetOldFollow()
	{
		follow.UpdateTime(dEpoch);
		follow.GetSXY(out var sx, out var sy);
		sx += dFollowOffsetSX;
		sy += dFollowOffsetSY;
		SolarToCanvas(sx, sy, out oldFollowCX, out oldFollowCY);
	}

	private void UpdateUIs()
	{
		for (int i = 0; i < aUIs.Count; i++)
		{
			if (aUIs[i] != null)
			{
				aUIs[i].Draw();
			}
		}
		if (txtRange != null)
		{
			txtRange.text = "ZOOM RANGE: " + MathUtils.GetDistUnits(dScopeRadius);
		}
		if (CrossHairTarget != null && CrossHairTarget.Ship != null && !CrossHairTarget.Ship.bDestroyed && VisibleFromNavStation(null, CrossHairTarget.Ship) == SignalVisibility.None)
		{
			CrossHairTarget.GetSXY(out var sx, out var sy);
			CrossHairTarget = new NavPOI(sx, sy);
			AudioManager.am.PlayAudioEmitter("ShipUINSMapPan04", bLoop: false);
		}
		BodyOrbit bodyOrbit = null;
		Ship ship = COSelf?.ship;
		if (ship != null && ship.objSS != null)
		{
			bodyOrbit = CrewSim.system.GetBO(ship.objSS.strBOPORShip);
			if (bodyOrbit != null && bodyOrbit.IsPlaceholder())
			{
				bodyOrbit = ((bodyOrbit.boParent == null) ? null : bodyOrbit.boParent);
			}
		}
		if (bodyOrbit == null)
		{
			bodyOrbit = CrewSim.system.GetBO("Sol");
		}
		if (CrossHairTarget != null && CrossHairTarget.Ship != null && !CrossHairTarget.Ship.bDestroyed && (crossHairInfo == null || crossHairInfo._strRegID != CrossHairTarget.name))
		{
			crossHairInfo = ShipInfo.GetShipInfo(GetNavStationShip(), CrossHairTarget.Ship, ShipPropMap);
		}
		if (ship != null && ship.objSS != null && lineGrav != null && lineCourse != null)
		{
			Vector2 gravAccel = CrewSim.system.GetGravAccel(bodyOrbit, GetNavStationShipSitu());
			lineGrav.points2 = new List<Vector2>();
			lineCourse.points2 = new List<Vector2>();
			if (ship.objSS.HasNavData())
			{
				lineCourse.points2 = ship.objSS.NavData.GetPoints(this);
			}
			else if (navPlan != null)
			{
				lineCourse.points2 = navPlan.GetPoints(this);
			}
			VectorLine vectorLine = lineCourse;
			vectorLine.matrix = Matrix4x4.Scale(Vector3.one);
			vectorLine.Draw();
			if (sdNS != null && sdNS.ship != null && sdNS.ship.objSS != null)
			{
				gravAccel = MathUtils.NormalizeVector(gravAccel);
				SolarToCanvas(sdNS.ship.objSS.vPosx + (double)gravAccel.x, sdNS.ship.objSS.vPosy + (double)gravAccel.y, out var cx, out var cy);
				lineGrav.points2.Add(new Vector2((float)cx, (float)cy));
				VectorLine vectorLine2 = lineGrav;
				vectorLine2.matrix = Matrix4x4.Scale(Vector3.one);
				vectorLine2.Draw();
			}
		}
		DrawCrossHair();
		DrawStationKeepingCrossHair();
		if (fClampDisengageWarningTimer > 0f)
		{
			fClampDisengageWarningTimer -= CrewSim.TimeElapsedUnscaled();
			if (fClampDisengageWarningTimer <= 0f)
			{
				cgClampWarning.alpha = 0f;
			}
		}
		NavModMessageEvent.Invoke(NavModMessageType.UpdateUI, null);
	}

	public void FlashStationWarn()
	{
		fEpochStationBegin = StarSystem.fEpoch;
		CGClampWarning("GUI_ORBIT_WARN_AUTOPILOT_NWZ");
	}

	public void FlashCycleSafety()
	{
		fEpochCycleSafetyBegin = StarSystem.fEpoch;
		CGClampWarning("GUI_ORBIT_WARN_CYCLE_SAFETY");
	}

	private void DrawCrossHair()
	{
		if (CrossHairTarget.Ship != null)
		{
			ShipDraw shipDraw = FindShipDraw(CrossHairTarget.Ship);
			CrossHairTarget.SensorOffset = shipDraw?.GetPositionOffset() ?? default(Point);
		}
		CrossHairTarget.GetSXY(out var sx, out var sy);
		double num = Math.Atan2(dCanvasSolarXX, dCanvasSolarXY);
		float num2 = (float)(0.004000000189989805 / MathUtils.GetMagnitude(dCanvasSolarXX, dCanvasSolarXY));
		float fScale = 6.684587E-12f + num2;
		DrawVectorLine(lineCross, sx, sy, (float)num, fScale);
	}

	private void DrawStationKeepingCrossHair()
	{
		if ((!chkStationKeeping.isOn && lineStationKeepingTarget != null) || COSelf.ship.shipStationKeepingTarget == null)
		{
			VectorLine.Destroy(ref lineStationKeepingTarget);
			return;
		}
		if (lineStationKeepingTarget == null)
		{
			lineStationKeepingTarget = new VectorLine("Station Keeping", NavIcon.BracketSquared((float)COSelf.ship.shipStationKeepingTarget.objSS.Size * 1.5f), fLineWidth, LineType.Discrete, Joins.Weld);
			lineStationKeepingTarget.color = clrGreen01;
			lineStationKeepingTarget.SetCanvas(goOrbitPanel, worldPositionStays: false);
		}
		ShipDraw shipDraw = FindShipDraw(COSelf.ship.shipStationKeepingTarget);
		if (shipDraw != null)
		{
			new NavPOI(shipDraw, GetNavStationShip(), ShipPropMap).GetSXY(out var sx, out var sy);
			double num = Math.Atan2(dCanvasSolarXX, dCanvasSolarXY);
			num += 1.5707963705062866;
			float num2 = (float)(0.004000000189989805 / MathUtils.GetMagnitude(dCanvasSolarXX, dCanvasSolarXY));
			float fScale = 6.684587E-12f + num2;
			DrawVectorLine(lineStationKeepingTarget, sx, sy, (float)num, fScale);
		}
	}

	private void UpdateShipDraw()
	{
		double num = 100000000.0;
		foreach (BODraw aBODraw in aBODraws)
		{
			if (!(aBODraw.bo.fRadiusKM < 5.0))
			{
				double distance = COSelf.ship.objSS.GetDistance(aBODraw.bo.dXReal, aBODraw.bo.dYReal);
				if (num > distance)
				{
					num = distance;
					boMainOccluder = aBODraw;
				}
			}
		}
		for (int num2 = aShipDraws.Count - 1; num2 >= 0; num2--)
		{
			if (aShipDraws[num2].ship.bChangedStatus || aShipDraws[num2].ship.bDestroyed || VisibleFromNavStation(aShipDraws[num2]) == SignalVisibility.None || (aShipDraws[num2].ship == COSelf.ship && (COSelf.ship.strXPDR == null || COSelf.ship.strXPDR == "?")))
			{
				aShipDraws[num2].ship.bChangedStatus = false;
				ShipDraw shipDraw = aShipDraws[num2];
				aShipDraws.RemoveAt(num2);
				shipDraw.Destroy();
			}
		}
		if (aDebugDraws != null)
		{
			for (int num3 = aDebugDraws.Count - 1; num3 >= 0; num3--)
			{
				if (aDebugDraws[num3] == null || aDebugDraws[num3].Evaluate())
				{
					aDebugDraws.RemoveAt(num3);
				}
			}
		}
		ShipDraw.blink = false;
		ShipDraw.KnobState = GetKnobLabelsState;
		ShipDraw.ActiveLabel = ShipDraw.KnobState;
		if (ShipDraw.KnobState == 3)
		{
			double num4 = StarSystem.fEpoch % 10.0;
			if (num4 < 4.7)
			{
				ShipDraw.blink = false;
				ShipDraw.ActiveLabel = 2;
			}
			else if (num4 < 5.0)
			{
				ShipDraw.blink = true;
				ShipDraw.ActiveLabel = 0;
			}
			else if (num4 < 9.7)
			{
				ShipDraw.blink = false;
				ShipDraw.ActiveLabel = 1;
			}
			else
			{
				ShipDraw.blink = true;
				ShipDraw.ActiveLabel = 0;
			}
		}
		List<ShipDraw> pool = new List<ShipDraw>(aShipDraws);
		foreach (Ship value in CrewSim.system.dictShips.Values)
		{
			if (value.bDestroyed)
			{
				continue;
			}
			SignalVisibility signalVisibility = VisibleFromNavStation(null, value);
			if (value == COSelf.ship || (!value.IsStationHidden() && !value.IsSubStation() && signalVisibility != SignalVisibility.None && (!value.IsUnderConstruction || signalVisibility == SignalVisibility.Visible)))
			{
				ShipDraw shipDraw2 = RemoveShipDrawFromPool(ref pool, value.strRegID);
				if (shipDraw2 != null)
				{
					shipDraw2.SignalVisibility = signalVisibility;
					shipDraw2.ToggleStatusSymbol();
				}
				else
				{
					shipDraw2 = SetupShipDraw(value);
					shipDraw2.SignalVisibility = signalVisibility;
					aShipDraws.Add(shipDraw2);
				}
			}
		}
	}

	private void DrawSystem()
	{
		if (GetNavStationShip() == null || GetNavStationShipSitu() == null)
		{
			return;
		}
		boundsAddedThisFrame.Clear();
		boundsToRects.Clear();
		VisibleShipDraws.Clear();
		OverlappingShipDraws.Clear();
		double num = dEpoch - StarSystem.fEpoch;
		ShowProjections(num > 0.0);
		double cx = rectDrawPanel.rect.width * 0.5f;
		double cy = rectDrawPanel.rect.height * 0.5f;
		CanvasToSolar(cx, cy, out var sx, out var sy);
		Point point = new Point(sx, sy);
		List<BodyOrbit> bosInRadius = _boPredictionGrid.GetBosInRadius(point, dScopeRadius);
		Rect rect = rectDrawPanel.rect;
		foreach (BODraw aBODraw in aBODraws)
		{
			if (dScopeRadius < 50.0 && !bosInRadius.Contains(aBODraw.bo) && !aBODraw.bo.IsShipOrbit())
			{
				aBODraw.bo.UpdateTime(StarSystem.fEpoch, bCorrectTimes: true, bCalcV: false);
				aBODraw.SetState(active: false, showProjections: false);
				continue;
			}
			if (aBODraw.bo.nDrawFlagsTrack != 1)
			{
				aBODraw.bo.UpdateTime(dEpoch, bCorrectTimes: true, bCalcV: false);
				DrawOrbitTrack(aBODraw, num > 0.0, rect);
			}
			if (aBODraw.bo.nDrawFlagsBody != 1)
			{
				aBODraw.bo.UpdateTime(StarSystem.fEpoch, bCorrectTimes: true, bCalcV: false);
				DrawBody(aBODraw, -1, 12f);
			}
			if (!(num <= 0.0) && aBODraw.bo.nDrawFlagsBody != 1)
			{
				aBODraw.bo.UpdateTime(dEpoch, bCorrectTimes: true, bCalcV: false);
				DrawBody(aBODraw, 0, 12f);
			}
		}
		BodyOrbit nearestBO = CrewSim.system.GetNearestBO(GetNavStationShip().objSS, StarSystem.fEpoch, bIncludePlaceholders: false);
		double dVelX = nearestBO.dVelX;
		double dVelY = nearestBO.dVelY;
		float num2 = 0f - (float)Math.Atan2(dCanvasSolarXY, dCanvasSolarXX);
		foreach (ShipDraw aShipDraw in aShipDraws)
		{
			if (aShipDraw.ship.bDestroyed)
			{
				continue;
			}
			bool showSilhouette = (aShipDraw == sdNS || aShipDraw.shipInfo.shipSignature > 80) && dScopeRadius * 149597872.0 < 2.5;
			aShipDraw.ToggleSilhouetteDrawMode(showSilhouette);
			if (aShipDraw.lineBody.active != aShipDraw.IsVisible)
			{
				aShipDraw.lineBody.active = aShipDraw.IsVisible;
			}
			if (aShipDraw.lineBodyNoSignal != null)
			{
				bool flag = aShipDraw.SignalVisibility == SignalVisibility.Partial;
				if (aShipDraw.lineBodyNoSignal.active != flag)
				{
					aShipDraw.lineBodyNoSignal.active = flag;
				}
			}
			if (aShipDraw.linePath.active != aShipDraw.IsVisible)
			{
				aShipDraw.linePath.active = aShipDraw.IsVisible;
			}
			if (!aShipDraw.IsVisible)
			{
				aShipDraw.cgName.alpha = 0f;
				aShipDraw.cgID.alpha = 0f;
			}
			ShipSitu objSS = aShipDraw.ship.objSS;
			if (objSS == null)
			{
				continue;
			}
			BodyOrbit bodyOrbit = null;
			if (objSS.bBOLocked || objSS.bIsBO || objSS.bOrbitLocked)
			{
				bodyOrbit = CrewSim.system.GetBO(objSS.strBOPORShip);
			}
			bodyOrbit?.UpdateTime(StarSystem.fEpoch);
			objSS.TimeAdvance(0.0, bIgnoreAccel: true);
			ShipInfo shipInfo = ShipInfo.GetShipInfo(GetNavStationShip(), aShipDraw.ship, ShipPropMap);
			float num3 = (((aShipDraw.ship.IsDerelict() || aShipDraw.ship.IsUnderConstruction) && !shipInfo.Known) ? ((float)DERELICTSIZE) : aShipDraw.fRadiusM);
			if (shipInfo.shipSignature < 30 && !aShipDraw.ship.IsStation() && aShipDraw.ship.Classification != Ship.TypeClassification.Asteroid)
			{
				num3 = DERELICTSIZE;
			}
			float num4 = (float)((double)(6f / num3) / MathUtils.GetMagnitude(dCanvasSolarXX, dCanvasSolarXY));
			float num5 = 6.684587E-12f + num4;
			float num6 = (aShipDraw.DoNotRotate ? num2 : objSS.fRot);
			double distanceToPlayerAU = ((!aShipDraw.IsVisible && aShipDraw.ship != null) ? GetNavStationShip().GetRangeTo(aShipDraw.ship) : 0.0);
			Point positionOffset = aShipDraw.GetPositionOffset(distanceToPlayerAU);
			if (aShipDraw.IsVisible)
			{
				DrawVectorLine(aShipDraw.lineBody, positionOffset.X, positionOffset.Y, num6, num5);
			}
			else if (aShipDraw.lineBodyNoSignal != null)
			{
				DrawVectorLine(aShipDraw.lineBodyNoSignal, positionOffset.X, positionOffset.Y, num6, num5);
			}
			DrawImage(aShipDraw.goImage, aShipDraw.ship.objSS.vPos, aShipDraw.ship.objSS.GetRadiusAU(), aShipDraw.DoNotRotate);
			if (aShipDraw.IsVisible)
			{
				DrawVectorLine(aShipDraw.lineStatus, positionOffset.X, positionOffset.Y, num2, num5 * 2f);
			}
			if (shipInfo.showSensorViz)
			{
				if (aShipDraw.lineNoWakeRange != null)
				{
					aShipDraw.lineNoWakeRange.active = false;
					VectorLine.Destroy(ref aShipDraw.lineNoWakeRange);
				}
				ShipSignature signatureThem = new ShipSignature(CrewSim.coPlayer.ship, aShipDraw.ship);
				aShipDraw.lineNoWakeRange = CreateSensorTexture(aShipDraw.ship.strRegID + "_NWZ", clrHauler, (float)(aShipDraw.ship.ElectronicSystems.GetSensorRangeKm(signatureThem) / 149597872.0), goOrbitPanel);
			}
			if (aShipDraw.lineNoWakeRange != null)
			{
				if ((bShowNWZ && aShipDraw.ship.IsStation()) || (shipInfo.showSensorViz && aShipDraw.IsVisible) || (CrossHairTarget != null && CrossHairTarget.Ship == aShipDraw.ship && aShipDraw.ship.Classification == Ship.TypeClassification.SignalBeacon && aShipDraw.IsVisible))
				{
					aShipDraw.lineNoWakeRange.active = true;
					DrawCarCircle(aShipDraw.lineNoWakeRange, objSS.vPosx, objSS.vPosy);
				}
				else
				{
					aShipDraw.lineNoWakeRange.active = false;
				}
			}
			if (aShipDraw.aWeaponArcs != null)
			{
				foreach (WeaponArcDTO aWeaponArc in aShipDraw.aWeaponArcs)
				{
					float num7 = (float)(6.0 / aWeaponArc.Range / MathUtils.GetMagnitude(dCanvasSolarXX, dCanvasSolarXY));
					float fScale = 6.684587E-12f + num7;
					DrawVectorLine(aWeaponArc.Arc, objSS.vPosx, objSS.vPosy, num6 + aWeaponArc.Rotation, fScale);
				}
			}
			aShipDraw.linePath.points2 = new List<Vector2>();
			if (aShipDraw.IsVisible && objSS.aPathRecent != null)
			{
				foreach (Ostranauts.Core.Models.Tuple<double, Point> item in objSS.aPathRecent)
				{
					double num8 = StarSystem.fEpoch - item.Item1;
					num8 *= fModTimeDiff;
					SolarToCanvas(item.Item2.X + num8 * dVelX, item.Item2.Y + num8 * dVelY, out var cx2, out var cy2);
					aShipDraw.linePath.points2.Add(new Vector2((float)cx2, (float)cy2));
				}
				aShipDraw.linePath.matrix = Matrix4x4.Scale(Vector3.one);
				aShipDraw.linePath.Draw();
			}
			if (num > 0.0)
			{
				bool flag2 = false;
				if (objSS.HasNavData())
				{
					ShipSitu shipSituAtTime = objSS.NavData.GetShipSituAtTime(dEpoch, bOverflow: true);
					if (shipSituAtTime != null)
					{
						ssTemp.CopyFrom(shipSituAtTime, bKinematicsOnly: false);
						flag2 = true;
					}
				}
				if (!flag2)
				{
					ssTemp.CopyFrom(objSS, bKinematicsOnly: false);
					bodyOrbit?.UpdateTime(dEpoch, bCorrectTimes: true, bCalcV: false);
					ssTemp.TimeAdvance((float)num);
				}
				float fScale2 = ((dScopeRadius * 149597872.0 < 2.5) ? (num5 / 5f) : num5);
				DrawVectorLine(aShipDraw.GetProjection()[0], ssTemp.vPosx, ssTemp.vPosy, ssTemp.fRot, fScale2);
			}
			else if (aShipDraw == sdNS)
			{
				follow.GetVSXY(out var svx, out var svy);
				if (CrossHairTarget.IsShipOrOrbit() && GetKnobFollowState == 1)
				{
					CrossHairTarget.GetVSXY(out svx, out svy);
				}
				ssTemp.CopyFrom(GetNavStationShipSitu(), bKinematicsOnly: false);
				ssTemp.vVelX -= svx;
				ssTemp.vVelY -= svy;
				ssTemp.fW = ssTemp.fA * 0.05f;
				ssTemp.fA = 0f;
				float fScale3 = ((dScopeRadius * 149597872.0 < 2.5) ? (num5 / 5f) : num5);
				for (int i = 0; i < nProjStepsSelf; i++)
				{
					ssTemp.bOrbitLocked = false;
					ssTemp.TimeAdvance(2f * Time.timeScale);
					DrawVectorLine(aShipDraw.GetProjection()[i], ssTemp.vPosx, ssTemp.vPosy, ssTemp.fRot, fScale3);
				}
			}
			SolarToCanvas(positionOffset.X, positionOffset.Y, out var cx3, out var cy3);
			cy3 += (double)((objSS.strBOPORShip == "") ? 20f : (-20f));
			aShipDraw.desiredCanvasPosFromSitu = new Vector3((float)(cx3 - (double)vCanvasOffset.x), (float)(cy3 - (double)vCanvasOffset.y), 0f);
			if (aShipDraw.bRedrawArcs)
			{
				DrawArc(aShipDraw, null);
			}
			TryAddLabelToCanvas(aShipDraw);
		}
		DrawStellarObjects(point);
		OnlyDrawTopLabels();
		if (num > 0.0)
		{
			foreach (BODraw aBODraw2 in aBODraws)
			{
				aBODraw2.bo.UpdateTime(StarSystem.fEpoch, bCorrectTimes: true, bCalcV: false);
			}
		}
		if (aDebugDraws == null)
		{
			return;
		}
		foreach (DebugDraw aDebugDraw in aDebugDraws)
		{
			aDebugDraw.LineBody.active = true;
			aDebugDraw.goLabel.SetActive(value: true);
			aDebugDraw.TargetSitu.TimeAdvance(0.0, bIgnoreAccel: true);
			float fScale4 = 6.684587E-12f + (float)((double)(6f / (float)DebugDraw.SIZE) / MathUtils.GetMagnitude(dCanvasSolarXX, dCanvasSolarXY));
			if (aDebugDraw.IsPrediction)
			{
				aDebugDraw.LineBody.points2 = new List<Vector2>();
				SolarToCanvas(aDebugDraw.TargetSitu.vPosx, aDebugDraw.TargetSitu.vPosy, out var cx4, out var cy4);
				aDebugDraw.LineBody.points2.Add(new Vector2((float)cx4, (float)cy4));
				Point predictedPosition = aDebugDraw.TargetSitu.GetPredictedPosition(30.0);
				SolarToCanvas(predictedPosition.X, predictedPosition.Y, out cx4, out cy4);
				aDebugDraw.LineBody.points2.Add(new Vector2((float)cx4, (float)cy4));
				aDebugDraw.LineBody.matrix = Matrix4x4.Scale(Vector3.one);
				aDebugDraw.LineBody.Draw();
			}
			else
			{
				DrawVectorLine(aDebugDraw.LineBody, aDebugDraw.TargetSitu.vPosx, aDebugDraw.TargetSitu.vPosy, aDebugDraw.TargetSitu.fRot, fScale4);
			}
			SolarToCanvas(aDebugDraw.TargetSitu.vPosx, aDebugDraw.TargetSitu.vPosy, out var cx5, out var cy5);
			cy5 += (double)((aDebugDraw.TargetSitu.strBOPORShip == "") ? 20f : (-20f));
			aDebugDraw.tfLabel.anchoredPosition = new Vector3((float)(cx5 - (double)vCanvasOffset.x), (float)(cy5 - (double)vCanvasOffset.y), 0f);
		}
	}

	private void DrawStellarObjects(Point centerWorldPos)
	{
		_stellarObjectDrawRef.Clear();
		foreach (StellarObjectGroup aStellarObjectGroup in aStellarObjectGroups)
		{
			if (aStellarObjectGroup.IsVisibleToPlayer(centerWorldPos, dScopeRadius))
			{
				if (aStellarObjectGroup.goImage != null)
				{
					aStellarObjectGroup.goImage.GetComponent<Image>().enabled = false;
				}
				foreach (StellarObjectDraw stellarObjectDraw in aStellarObjectGroup.StellarObjectDraws)
				{
					_stellarObjectDrawRef.Add(new Ostranauts.Core.Models.Tuple<double, StellarObjectDraw>(stellarObjectDraw.DistanceToPlayer, stellarObjectDraw));
				}
			}
			else
			{
				if (aStellarObjectGroup.goImage != null)
				{
					aStellarObjectGroup.goImage.GetComponent<Image>().enabled = true;
				}
				DrawImage(aStellarObjectGroup.goImage, aStellarObjectGroup.AsteroidField.dPosReal, aStellarObjectGroup.AsteroidField.fRadius, aStellarObjectGroup.DoNotRotate);
				aStellarObjectGroup.DisableDraws();
			}
		}
		bool flag = !COSelf.ship.ElectronicSystems.HasAnySensorOn();
		Ship ship = COSelf.ship;
		foreach (Ostranauts.Core.Models.Tuple<double, StellarObjectDraw> item2 in _stellarObjectDrawRef)
		{
			StellarObjectDraw item = item2.Item2;
			SignalVisibility signalVisibility = ((item.StellarObject.objSS.GetDistance(centerWorldPos.X, centerWorldPos.Y) < dScopeRadius * 1.3 && !flag) ? StellarObjectVisible(ship, item.StellarObject, item) : SignalVisibility.None);
			switch (signalVisibility)
			{
			case SignalVisibility.None:
				if (item.lineBody.active)
				{
					item.lineBody.active = false;
				}
				if (item.lineBodyNoSignal.active)
				{
					item.lineBodyNoSignal.active = false;
				}
				continue;
			case SignalVisibility.Visible:
				if (!item.lineBody.active)
				{
					item.lineBody.active = true;
				}
				if (item.lineBodyNoSignal.active)
				{
					item.lineBodyNoSignal.active = false;
				}
				break;
			default:
				if (item.lineBody.active)
				{
					item.lineBody.active = false;
				}
				if (!item.lineBodyNoSignal.active)
				{
					item.lineBodyNoSignal.active = true;
				}
				break;
			}
			float num = 0f;
			ShipSitu objSS = item.StellarObject.objSS;
			float fRot = objSS.fRot;
			BodyOrbit bodyOrbit = null;
			if (objSS.bBOLocked)
			{
				((objSS.boReference == null) ? CrewSim.system.GetBO(objSS.strBOPORShip) : objSS.boReference)?.UpdateTime(StarSystem.fEpoch);
			}
			float num2 = objSS.Size;
			float num3 = (float)((double)(6f / num2) / MathUtils.GetMagnitude(dCanvasSolarXX, dCanvasSolarXY));
			num = 6.684587E-12f + num3;
			if (signalVisibility == SignalVisibility.Visible)
			{
				DrawVectorLine(item.lineBody, objSS.vPosx, objSS.vPosy, fRot, num);
			}
			else
			{
				DrawVectorLine(item.lineBodyNoSignal, objSS.vPosx, objSS.vPosy, fRot, num);
			}
		}
	}

	public void OnlyDrawTopLabels()
	{
		float smoothTime = 0.016f;
		if (ShipDraw.blink)
		{
			smoothTime = 0.008f;
		}
		for (int i = 0; i < VisibleShipDraws.Count; i++)
		{
			ShipDraw shipDraw = VisibleShipDraws[i];
			if (!shipDraw.IsVisible)
			{
				shipDraw.LabelID.cg.alpha = 0f;
				shipDraw.LabelName.cg.alpha = 0f;
				continue;
			}
			Vector3 vector;
			Vector3 vector2;
			if (!(shipDraw.desiredCanvasPosFromSitu.magnitude > 5000f))
			{
				vector = shipDraw.desiredCanvasPosFromSitu;
			}
			else
			{
				vector2 = new Vector3(3000f, 3000f);
				vector = vector2;
			}
			vector2 = vector;
			shipDraw.sharedLabelOffsetCurrent = Vector3.SmoothDamp(shipDraw.sharedLabelOffsetCurrent, shipDraw.sharedLabelOffsetTarget, ref shipDraw.sharedLabelVelocity, 0.12f);
			shipDraw.LabelID.labelRect.localPosition = vector2 + shipDraw.sharedLabelOffsetCurrent;
			shipDraw.LabelName.labelRect.localPosition = vector2 + shipDraw.sharedLabelOffsetCurrent;
			switch (ShipDraw.ActiveLabel)
			{
			case 0:
				shipDraw.LabelID.cg.alpha = Mathf.SmoothDamp(shipDraw.LabelID.cg.alpha, 0f, ref shipDraw.sharedAlphaVelocity, smoothTime);
				shipDraw.LabelName.cg.alpha = Mathf.SmoothDamp(shipDraw.LabelName.cg.alpha, 0f, ref shipDraw.sharedAlphaVelocity, smoothTime);
				break;
			case 1:
				shipDraw.LabelID.cg.alpha = Mathf.SmoothDamp(shipDraw.LabelID.cg.alpha, 1f, ref shipDraw.sharedAlphaVelocity, smoothTime);
				shipDraw.LabelName.cg.alpha = Mathf.SmoothDamp(shipDraw.LabelName.cg.alpha, 0f, ref shipDraw.sharedAlphaVelocity, smoothTime);
				break;
			case 2:
				shipDraw.LabelID.cg.alpha = Mathf.SmoothDamp(shipDraw.LabelID.cg.alpha, 0f, ref shipDraw.sharedAlphaVelocity, smoothTime);
				shipDraw.LabelName.cg.alpha = Mathf.SmoothDamp(shipDraw.LabelName.cg.alpha, 1f, ref shipDraw.sharedAlphaVelocity, smoothTime);
				break;
			}
		}
		for (int j = 0; j < OverlappingShipDraws.Count; j++)
		{
			ShipDraw shipDraw2 = OverlappingShipDraws[j];
			shipDraw2.LabelName.cg.alpha = Mathf.SmoothDamp(shipDraw2.LabelName.cg.alpha, 0f, ref shipDraw2.sharedAlphaVelocity, 0f);
			shipDraw2.LabelID.cg.alpha = Mathf.SmoothDamp(shipDraw2.LabelName.cg.alpha, 0f, ref shipDraw2.sharedAlphaVelocity, 0f);
		}
	}

	public bool FoundIntersection(Bounds toTest, List<Bounds> tested, out Bounds intersected)
	{
		for (int i = 0; i < tested.Count; i++)
		{
			if (toTest.Intersects(tested[i]))
			{
				intersected = tested[i];
				return true;
			}
		}
		intersected = default(Bounds);
		return false;
	}

	public void TryAddLabelToCanvas(ShipDraw shipDraw)
	{
		if (!shipDraw.IsVisible || shipDraw.LabelActive == null || shipDraw.LabelActive.labelRect == null)
		{
			return;
		}
		Bounds bounds = new Bounds(shipDraw.desiredCanvasPosFromSitu, (Vector3)shipDraw.LabelActive.labelRect.sizeDelta);
		Bounds intersected;
		bool flag = FoundIntersection(bounds, boundsAddedThisFrame, out intersected);
		bool flag2 = false;
		Bounds bounds2 = bounds;
		Vector3 zero = Vector3.zero;
		if (flag)
		{
			Vector3 vector = -(intersected.center - bounds.center).normalized;
			zero = vector;
			int num;
			for (num = 1; num < 32; num *= 2)
			{
				Bounds intersected2 = bounds2;
				zero = vector * num;
				bounds2 = new Bounds(bounds.center + zero, bounds.size);
				if (!FoundIntersection(bounds2, boundsAddedThisFrame, out intersected2))
				{
					flag2 = true;
					shipDraw.sharedLabelOffsetTarget = zero;
				}
				num++;
			}
		}
		if (flag2)
		{
			flag = false;
			bounds = bounds2;
		}
		else
		{
			shipDraw.sharedLabelOffsetTarget = Vector3.zero;
		}
		if (flag)
		{
			OverlappingShipDraws.Add(shipDraw);
			return;
		}
		VisibleShipDraws.Add(shipDraw);
		boundsAddedThisFrame.Add(bounds);
	}

	private void ShowProjections(bool bShowMapFuture)
	{
		if (bShowMapFuture == bShowMapProjs)
		{
			return;
		}
		foreach (BODraw aBODraw in aBODraws)
		{
			foreach (VectorLine aProj in aBODraw.aProjs)
			{
				aProj.active = bShowMapFuture && aBODraw.Active;
			}
		}
		foreach (ShipDraw aShipDraw in aShipDraws)
		{
			if (aShipDraw.GetProjection() == null)
			{
				continue;
			}
			int num = 0;
			foreach (VectorLine item in aShipDraw.GetProjection())
			{
				if (aShipDraw == sdNS)
				{
					if (bShowMapFuture)
					{
						item.active = aShipDraw.lineBody.active && num == 0;
					}
					else
					{
						item.active = aShipDraw.lineBody.active;
					}
				}
				else
				{
					item.active = bShowMapFuture && (aShipDraw.lineBody.active || (aShipDraw.lineBodyNoSignal != null && aShipDraw.lineBodyNoSignal.active));
				}
				num++;
			}
		}
		bShowMapProjs = bShowMapFuture;
	}

	public void UpdateShipInfo(ShipInfo si)
	{
		if (si != null)
		{
			ShipInfo.SetShipInfo(si, dictPropMap);
			crossHairInfo = null;
			InvalidateShipDraw(si._strRegID);
			InvalidateStellarObjectDraw(si._strRegID);
		}
	}

	private void InvalidateShipDraw(string regId)
	{
		for (int i = 0; i < aShipDraws.Count; i++)
		{
			ShipDraw shipDraw = aShipDraws[i];
			if (shipDraw == null)
			{
				aShipDraws.RemoveAt(i);
			}
			else if (shipDraw.ship == null || shipDraw.ship.strRegID == regId)
			{
				aShipDraws.RemoveAt(i);
				shipDraw.Destroy();
			}
		}
	}

	private void InvalidateStellarObjectDraw(string regId)
	{
		for (int i = 0; i < aStellarObjectGroups.Count && !aStellarObjectGroups[i].InvalidateStellarObjectDraw(regId); i++)
		{
		}
	}

	public void InvalidateAllShips()
	{
		for (int i = 0; i < aShipDraws.Count; i++)
		{
			ShipDraw shipDraw = aShipDraws[i];
			if (shipDraw == null)
			{
				aShipDraws.RemoveAt(i);
				continue;
			}
			aShipDraws.RemoveAt(i);
			shipDraw.Destroy();
		}
	}

	private void InitOrbitArea(GameObject go)
	{
		txtSide = GUIRenderTargets.goLines.transform.Find("pnlSide/txtSide").GetComponent<TextMeshProUGUI>();
		Rect rect = ((RectTransform)go.transform).rect;
		List<Vector2> list = new List<Vector2>();
		int num = 4;
		float num2 = rect.width / (float)num;
		float num3 = rect.height / (float)num;
		int num4 = 2;
		for (int i = 1; i < num; i++)
		{
			for (int j = 0; (float)j < rect.height; j += 2 * num4)
			{
				list.Add(new Vector2((float)i * num2, j));
				list.Add(new Vector2((float)i * num2, j + num4));
			}
		}
		for (int k = 1; k < num; k++)
		{
			for (int l = 0; (float)l < rect.width; l += 2 * num4)
			{
				list.Add(new Vector2(l, (float)k * num3));
				list.Add(new Vector2(l + num4, (float)k * num3));
			}
		}
		list.Add(new Vector2(1f, 1f));
		list.Add(new Vector2(rect.width - 1f, 1f));
		list.Add(new Vector2(rect.width - 1f, 1f));
		list.Add(new Vector2(rect.width - 1f, rect.height - 1f));
		list.Add(new Vector2(rect.width - 1f, rect.height - 1f));
		list.Add(new Vector2(1f, rect.height - 1f));
		list.Add(new Vector2(1f, rect.height - 1f));
		list.Add(new Vector2(1f, 1f));
		VectorLine vectorLine = new VectorLine("OrbitAxes", list, fLineWidth, LineType.Discrete, Joins.Weld);
		vectorLine.color = clrBlue01;
		vectorLine.SetCanvas(go, worldPositionStays: false);
		aUIs.Add(vectorLine);
		if (lineCross != null)
		{
			VectorLine.Destroy(ref lineCross);
		}
		lineCross = new VectorLine("Target Cross", NavIcon.Cross(125f), fLineWidth, LineType.Discrete, Joins.Weld);
		lineCross.color = clrWhite01;
		lineCross.SetCanvas(go, worldPositionStays: false);
		if (lineCourse != null)
		{
			VectorLine.Destroy(ref lineCourse);
		}
		lineCourse = new VectorLine("Course Vector", new List<Vector2>(new Vector2[2]
		{
			default(Vector2),
			new Vector2(1f, 1f)
		}), fLineWidth, LineType.Continuous, Joins.Weld);
		lineCourse.color = clrOrange01;
		lineCourse.SetCanvas(go, worldPositionStays: false);
		if (lineGrav != null)
		{
			VectorLine.Destroy(ref lineGrav);
		}
		lineGrav = new VectorLine("Grav Vector", new List<Vector2>(new Vector2[2]
		{
			default(Vector2),
			new Vector2(1f, 1f)
		}), fLineWidth, LineType.Discrete, Joins.Weld);
		lineGrav.color = clrRed01;
		lineGrav.SetCanvas(go, worldPositionStays: false);
	}

	private void InitFrame(GameObject go)
	{
		Rect rect = ((RectTransform)go.transform).rect;
		List<Vector2> list = new List<Vector2>();
		list.Add(new Vector2(1f, 1f));
		list.Add(new Vector2(rect.width - 1f, 1f));
		list.Add(new Vector2(rect.width - 1f, 1f));
		list.Add(new Vector2(rect.width - 1f, rect.height - 1f));
		list.Add(new Vector2(rect.width - 1f, rect.height - 1f));
		list.Add(new Vector2(1f, rect.height - 1f));
		list.Add(new Vector2(1f, rect.height - 1f));
		list.Add(new Vector2(1f, 1f));
		VectorLine vectorLine = new VectorLine("Frame", list, fLineWidth, LineType.Discrete, Joins.Weld);
		vectorLine.color = clrBlue01;
		vectorLine.SetCanvas(go, worldPositionStays: false);
		aUIs.Add(vectorLine);
	}

	private Color GetBOColor(BodyOrbit bo)
	{
		if (bo.fMass >= 9.99999944211969E+27)
		{
			return clrOrange01;
		}
		if (bo.fMass >= 9.999999778196308E+22)
		{
			return clrBlue01;
		}
		return clrGreen01;
	}

	private Color GetTrackColor(BodyOrbit bo)
	{
		if (bo.fMass >= 9.99999944211969E+27)
		{
			return clrOrange01Half;
		}
		if (bo.fMass >= 9.999999778196308E+22)
		{
			return clrBlue01Half;
		}
		if (bo.IsPlaceholder())
		{
			return clrShipOrbit;
		}
		return clrGreen01Half;
	}

	private void RemoveOrbital(string boName)
	{
		for (int num = aBODraws.Count - 1; num >= 0; num--)
		{
			BODraw bODraw = aBODraws[num];
			if (!(bODraw.bo.strName != boName))
			{
				bODraw.Destroy();
				aBODraws.RemoveAt(num);
				break;
			}
		}
	}

	private void AddOrbital(BodyOrbit bo, GameObject go)
	{
		foreach (BODraw aBODraw in aBODraws)
		{
			if (aBODraw.bo.strName == bo.strName)
			{
				return;
			}
		}
		BODraw bODraw = new BODraw(bo);
		bODraw.lineBody = CreateBodyTexture(bo.strName + "BodyS", GetBOColor(bo), (float)bo.fRadius, go, texLine01);
		for (int i = 0; i < nProjSteps; i++)
		{
			bODraw.aProjs.Add(CreateBodyTexture(bo.strName + "BodyS_" + i, GetBOColor(bo), (float)bo.fRadius, go, texLine01));
		}
		bODraw.lineGrav = CreateBodyLine(bo.strName + "Grav", clrRed02, (float)(bo.fRadius + bo.GravRadius), go);
		if (bo.fParallaxRadius > 0.0 && bo.fParallaxRadius < 1E+20 && bo.fParallaxRadius < bo.GravRadius)
		{
			bODraw.lineGravInner = CreateBodyLine(bo.strName + "GravInner", clrRed01, (float)bo.fParallaxRadius, go);
		}
		aBODraws.Add(bODraw);
	}

	private IEnumerator DelayedAsteroidLoading(List<AsteroidField> asteroidFields)
	{
		foreach (AsteroidField asteroidField in asteroidFields)
		{
			AddStellarObjects(asteroidField);
			yield return null;
		}
		_delayedLoadingFinished = true;
	}

	private void AddStellarObjects(AsteroidField bo)
	{
		StellarObjectGroup stellarObjectGroup = new StellarObjectGroup(bo);
		if (stellarObjectGroup.goImage == null)
		{
			stellarObjectGroup.goImage = CreateCircleImage("BODrawImage");
		}
		foreach (Asteroid asteroid in bo.Asteroids)
		{
			stellarObjectGroup.AddObject(AddStellarObject(asteroid));
		}
		aStellarObjectGroups.Add(stellarObjectGroup);
	}

	private StellarObjectDraw AddStellarObject(Asteroid bo)
	{
		StellarObjectDraw stellarObjectDraw = new StellarObjectDraw(bo);
		Color c = clrAsteroid;
		stellarObjectDraw.lineBody = NavIcon.SetupVectorLine(bo.strID, c, goOrbitPanel, NavIcon.Octagon(bo.objSS.Size), LineType.Continuous);
		for (int i = 0; i < nProjSteps; i++)
		{
			VectorLine item = NavIcon.SetupVectorLine(bo.strID, new Color(c.r, c.g, c.b, 1f - 1f * (float)i / (float)nProjSteps), goOrbitPanel, NavIcon.Octagon(bo.objSS.Size));
			stellarObjectDraw.aProjs.Add(item);
		}
		if (stellarObjectDraw.lineBodyNoSignal == null)
		{
			stellarObjectDraw.lineBodyNoSignal = NavIcon.SetupVectorLine(bo.strID + "_noSig", clrNoSig, goOrbitPanel, NavIcon.OtherKnown(100f));
			VectorLine vl = NavIcon.SetupVectorLine(bo.strID + " _noSigPred", clrNoSig, goOrbitPanel, NavIcon.OtherKnown(100f));
			stellarObjectDraw.AddSignalProjection(vl);
		}
		return stellarObjectDraw;
	}

	public GameObject CreateCircleImage(string boName)
	{
		if (!dictImages.TryGetValue(boName, out var value))
		{
			value = Resources.Load<GameObject>("GUIShip/GUIOrbitDraw/" + boName);
			dictImages[boName] = value;
		}
		if (value == null)
		{
			return null;
		}
		GameObject obj = UnityEngine.Object.Instantiate(value, goOrbitPanel.transform);
		obj.GetComponent<RectTransform>().rotation = Quaternion.Euler(0f, 0f, UnityEngine.Random.Range(0, 359));
		obj.name = boName;
		return obj;
	}

	private void DrawImage(GameObject goImage, Point vPos, double radiusAU, bool doNotRotate)
	{
		if (!(goImage == null))
		{
			SolarToCanvas(vPos.X, vPos.Y, out var cx, out var cy);
			SolarToCanvas(vPos.X, vPos.Y + 1.0, out var cx2, out var cy2);
			double num = cx2 - cx;
			double num2 = cy2 - cy;
			float num3 = Mathf.Sqrt((float)(num * num + num2 * num2));
			Matrix4x4 matrix4x = Matrix4x4.Scale(Vector3.one);
			matrix4x.SetRow(0, new Vector4(num3, 0f, 0f, (float)cx));
			matrix4x.SetRow(1, new Vector4(0f, num3, 0f, (float)cy));
			float num4 = (float)(2.0 * (radiusAU / dScopeRadius));
			RectTransform component = goImage.GetComponent<RectTransform>();
			component.anchoredPosition = matrix4x.ExtractPosition();
			component.localScale = new Vector3(num4, num4, num4);
			if (!doNotRotate)
			{
				component.rotation = matrix4x.ExtractRotation();
			}
		}
	}

	private VectorLine CreateBodyTexture(string strName, Color c, float fRad, GameObject go, Texture texLine)
	{
		VectorLine vectorLine = new VectorLine(strName, new List<Vector2>(65), texLine, 32f, LineType.Continuous, Joins.Weld);
		vectorLine.textureScale = 1f;
		vectorLine.capLength = 32f;
		vectorLine.color = c;
		vectorLine.SetCanvas(go, worldPositionStays: false);
		vectorLine.MakeSpline(NavIcon.Circle(fRad, 64), loop: true);
		return vectorLine;
	}

	private VectorLine CreateSensorTexture(string strName, Color c, float fRad, GameObject go)
	{
		VectorLine vectorLine = new VectorLine(strName, new List<Vector2>(nSensorSegments + 1), fLineWidth, lTypeSensor, Joins.None);
		vectorLine.textureScale = 1f;
		vectorLine.capLength = 0f;
		vectorLine.color = clrSensor;
		vectorLine.SetCanvas(go, worldPositionStays: false);
		vectorLine.MakeSpline(NavIcon.SensorCircle(fRad, nSensorSegments), loop: true);
		vectorLine.textureScale = 1f;
		return vectorLine;
	}

	private VectorLine CreateBodyLine(string strName, Color c, float fRad, GameObject go)
	{
		VectorLine vectorLine = new VectorLine(strName, new List<Vector2>(65), fLineWidth, LineType.Continuous, Joins.Weld);
		vectorLine.color = c;
		vectorLine.SetCanvas(go, worldPositionStays: false);
		vectorLine.MakeSpline(NavIcon.Circle(fRad, 512), loop: true);
		return vectorLine;
	}

	private double GetBOTErr(BODraw bod, double t, Rect drawPanelRect)
	{
		bool bCorrectTimes = true;
		bod.bo.UpdateTime(t, bCorrectTimes);
		SolarToCanvas(bod.bo.dXReal, bod.bo.dYReal, out var cx, out var cy);
		cx -= (double)(drawPanelRect.width * 0.5f);
		cy -= (double)(drawPanelRect.height * 0.5f);
		return cx * cx + cy * cy;
	}

	private void ImproveTrackEpoch(BODraw bod, Rect drawPanelRect)
	{
		double num = (bod.dTrackEpoch - dEpoch) % bod.bo.fPeriod + dEpoch;
		double num2 = GetBOTErr(bod, num, drawPanelRect);
		double num3 = 86400.0;
		while (Mathf.Abs((float)num3) > 6000f)
		{
			double num4 = num + num3;
			double bOTErr = GetBOTErr(bod, num4, drawPanelRect);
			if (num2 > bOTErr)
			{
				num2 = bOTErr;
				num = num4;
				num3 *= 1.100000023841858;
			}
			else
			{
				num3 *= -0.30000001192092896;
			}
		}
		if (Mathf.Abs((float)(bod.dTrackEpoch - num)) > 6000f)
		{
			bod.dTrackEpoch = num;
			VectorLine.Destroy(ref bod.lineTrackPartial);
			bod.lineTrackPartial = null;
		}
	}

	private VectorLine GetLineTrack(BODraw bod, double centreTime, double originX, double originY, bool arcOnly, VectorLine lineOrbit)
	{
		BodyOrbit bo = bod.bo;
		double num = 0.0;
		double num2 = 0.0;
		bool bCorrectTimes = arcOnly;
		int num3 = 64;
		if (bod.bo.IsShipOrbit())
		{
			num3 = (arcOnly ? 512 : ((bod.bo.fAxis2 > 3.422508598305285E-06) ? 1024 : ((bod.bo.fAxis2 > 1.7112542991526425E-06) ? 512 : ((!(bod.bo.fAxis2 > 8.556271495763212E-07)) ? 128 : 256))));
		}
		else if (bod.bo.IsPlaceholder())
		{
			num3 = (arcOnly ? 128 : 256);
		}
		Vector2[] array = new Vector2[num3 + 1];
		for (int i = 0; i <= num3; i++)
		{
			double num4 = centreTime;
			if (arcOnly)
			{
				int num5 = i - num3 / 2;
				num4 += (double)(num5 * num5 * num5) * bo.fPeriod / Math.Pow(num3, 3.0);
			}
			else
			{
				num4 += (double)i * bo.fPeriod / (double)num3;
				if (bod.bo.boParent != null)
				{
					bod.bo.boParent.UpdateTime(num4, bCorrectTimes: false, bCalcV: false);
					num = bod.bo.boParent.dXReal;
					num2 = bod.bo.boParent.dYReal;
				}
			}
			bo.UpdateTime(num4, bCorrectTimes, bCalcV: false);
			array[i] = new Vector2((float)(bo.dXReal - num - originX), (float)(bo.dYReal - num2 - originY));
		}
		if (lineOrbit == null)
		{
			lineOrbit = new VectorLine(bo.strName + "Orbit", new List<Vector2>(num3), fLineWidth, LineType.Continuous, Joins.Weld);
		}
		lineOrbit.color = GetTrackColor(bo);
		lineOrbit.SetCanvas(goOrbitPanel, worldPositionStays: false);
		lineOrbit.MakeSpline(array, loop: false);
		if (bod.bo.IsShipOrbit() && !arcOnly)
		{
			RepairTrackGlitches(array, lineOrbit);
		}
		return lineOrbit;
	}

	private void RepairTrackGlitches(Vector2[] aPointsNew, VectorLine lineOrbit)
	{
		Vector2 vector = Vector2.zero;
		for (int i = 0; i < aPointsNew.Length && i < lineOrbit.points2.Count; i++)
		{
			if (i != 0 && Vector2.Distance(aPointsNew[i], lineOrbit.points2[i]) > (aPointsNew[i] - vector).magnitude * 3f)
			{
				lineOrbit.points2[i] = aPointsNew[i] - vector;
			}
			else
			{
				vector = aPointsNew[i] - lineOrbit.points2[i];
			}
		}
	}

	private void DrawOrbitTrack(BODraw bod, bool showProjections, Rect drawPanelRect)
	{
		if (bod.bo.nDrawFlagsTrack == 1)
		{
			return;
		}
		float num = Mathf.Sqrt((float)(dCanvasSolarXX * dCanvasSolarXX + dCanvasSolarXY * dCanvasSolarXY));
		double fAxis = bod.bo.fAxis1;
		bool flag = bod.bo != null && bod.bo.IsShipOrbit();
		if ((double)num * fAxis < (double)(fMinOrbitDiam * 0.5f) && !flag)
		{
			bod.SetState(active: false, showProjections: false);
			return;
		}
		bod.SetState(active: true, showProjections);
		bool flag2 = true;
		if (!bod.bo.IsMoon() && (double)num * fAxis > 1000.0)
		{
			flag2 = false;
		}
		double sx = 0.0;
		double sy = 0.0;
		if (flag2)
		{
			if (bod.lineTrackPartial != null)
			{
				bod.lineTrackPartial.active = false;
			}
			if (bod.lineTrackFull == null)
			{
				bod.lineTrackFull = GetLineTrack(bod, 0.0, 0.0, 0.0, arcOnly: false, bod.lineTrackFull);
			}
			bod.lineTrackFull.active = true;
			if (bod.bo.boParent != null)
			{
				sx += bod.bo.boParent.dXReal;
				sy += bod.bo.boParent.dYReal;
			}
		}
		else
		{
			double cx = drawPanelRect.width * 0.5f;
			double cy = drawPanelRect.height * 0.5f;
			CanvasToSolar(cx, cy, out sx, out sy);
			if (bod.lineTrackFull != null)
			{
				bod.lineTrackFull.active = false;
			}
			ImproveTrackEpoch(bod, drawPanelRect);
			bod.lineTrackPartial = GetLineTrack(bod, bod.dTrackEpoch, sx, sy, arcOnly: true, bod.lineTrackPartial);
			bod.lineTrackPartial.active = true;
		}
		SolarToCanvas(sx, sy, out var cx2, out var cy2);
		SolarToCanvas(sx + 1.0, sy, out var cx3, out var cy3);
		SolarToCanvas(sx, sy + 1.0, out var cx4, out var cy4);
		Matrix4x4 matrix = Matrix4x4.Scale(Vector3.one);
		matrix.SetRow(0, new Vector4((float)(cx3 - cx2), (float)(cx4 - cx2), 0f, (float)cx2));
		matrix.SetRow(1, new Vector4((float)(cy3 - cy2), (float)(cy4 - cy2), 0f, (float)cy2));
		if (flag2)
		{
			bod.lineTrackFull.matrix = matrix;
			bod.lineTrackFull.Draw();
		}
		else
		{
			bod.lineTrackPartial.matrix = matrix;
			bod.lineTrackPartial.Draw();
		}
	}

	private void ToggleOrbitalMode(bool show)
	{
		Ship ship = COSelf.ship;
		if ((show && ship.IsDocked()) || ship.IsUsingTorchDrive)
		{
			return;
		}
		BodyOrbit bodyOrbit = CrewSim.system.GetBO(ship.strRegID);
		if (show)
		{
			if (bodyOrbit == null)
			{
				bodyOrbit = ship.LockToOrbit();
			}
			else
			{
				ship.objSS.LockToOrbit(bodyOrbit);
			}
			if (bodyOrbit != null)
			{
				AddOrbital(bodyOrbit, goOrbitPanel);
			}
		}
		else if (bodyOrbit != null)
		{
			if (ship.objSS.strBOPORShip == bodyOrbit.strName)
			{
				ship.UnlockFromOrbit();
			}
			CrewSim.system.RemoveBO(bodyOrbit);
		}
	}

	private void DrawBody(BODraw bod, int nIndex, float fMinDiam)
	{
		if (!bod.Active || bod.lineBody == null)
		{
			return;
		}
		if (nIndex < 0)
		{
			bod.bo.UpdateTime(StarSystem.fEpoch);
		}
		else
		{
			bod.bo.UpdateTime(dEpoch);
		}
		SolarToCanvas(bod.bo.dXReal, bod.bo.dYReal, out var cx, out var cy);
		SolarToCanvas(bod.bo.dXReal, bod.bo.dYReal + 1.0, out var cx2, out var cy2);
		double num = cx2 - cx;
		double num2 = cy2 - cy;
		float num3 = Mathf.Sqrt((float)(num * num + num2 * num2));
		Matrix4x4 matrix = Matrix4x4.Scale(Vector3.one);
		matrix.SetRow(0, new Vector4(num3, 0f, 0f, (float)cx));
		matrix.SetRow(1, new Vector4(0f, num3, 0f, (float)cy));
		if (nIndex < 0)
		{
			if (bod.lineGrav != null)
			{
				bod.lineGrav.matrix = matrix;
				bod.lineGrav.Draw();
			}
			if (bod.lineGravInner != null)
			{
				bod.lineGravInner.matrix = matrix;
				bod.lineGravInner.Draw();
			}
		}
		VectorLine vectorLine = bod.lineBody;
		if (nIndex >= 0)
		{
			vectorLine = bod.aProjs[nIndex];
		}
		float num4 = fMinDiam * 0.5f / vectorLine.points2[0].x;
		if (num3 < num4)
		{
			num3 = num4;
			vectorLine.textureScale = 1f;
			vectorLine.capLength = fLineWidth;
			vectorLine.lineWidth = fLineWidth;
			vectorLine.texture = texLine04;
		}
		else
		{
			vectorLine.textureScale = 1f;
			vectorLine.capLength = 32f;
			vectorLine.lineWidth = 32f;
			vectorLine.texture = texLine01;
		}
		matrix.SetRow(0, new Vector4(num3, 0f, 0f, (float)cx));
		matrix.SetRow(1, new Vector4(0f, num3, 0f, (float)cy));
		vectorLine.matrix = matrix;
		vectorLine.Draw();
	}

	public void DrawVectorLine(VectorLine vectorLine, double sx, double sy, float fRot, float fScale = -1f)
	{
		if (vectorLine != null)
		{
			SolarToCanvas(sx, sy, out var cx, out var cy);
			SolarToCanvas(sx + (double)Mathf.Cos(fRot), sy + (double)Mathf.Sin(fRot), out var cx2, out var cy2);
			float u = (float)(cx2 - cx);
			float v = (float)(cy2 - cy);
			if (fScale <= 0f)
			{
				MathUtils.SetLength(ref u, ref v, 1f);
			}
			else
			{
				u *= fScale;
				v *= fScale;
			}
			Matrix4x4 matrix = Matrix4x4.Scale(Vector3.one);
			matrix.SetRow(0, new Vector4(u, 0f - v, 0f, (float)cx));
			matrix.SetRow(1, new Vector4(v, u, 0f, (float)cy));
			vectorLine.matrix = matrix;
			vectorLine.Draw();
		}
	}

	private void DrawCarCircle(VectorLine vectorLine, double sx, double sy)
	{
		if (vectorLine != null)
		{
			SolarToCanvas(sx, sy, out var cx, out var cy);
			SolarToCanvas(sx, sy + 1.0, out var cx2, out var cy2);
			double num = cx2 - cx;
			double num2 = cy2 - cy;
			float num3 = Mathf.Sqrt((float)(num * num + num2 * num2));
			Matrix4x4 matrix = Matrix4x4.Scale(Vector3.one);
			matrix.SetRow(0, new Vector4(num3, 0f, 0f, (float)cx));
			matrix.SetRow(1, new Vector4(0f, num3, 0f, (float)cy));
			vectorLine.matrix = matrix;
			vectorLine.Draw();
		}
	}

	private void ToggleEditMode()
	{
		AudioManager.am.PlayAudioEmitter("ShipUIScrew", bLoop: false);
		if (_editMenu.gameObject.activeSelf)
		{
			_editMenu.Close();
			_editMenu.gameObject.SetActive(value: false);
			_editModeActive = false;
			NavModMessageEvent.Invoke(NavModMessageType.EditNavStation, false);
			SaveModules();
		}
		else
		{
			_editMenu.gameObject.SetActive(value: true);
			_editMenu.Init(_navMods);
			_editModeActive = true;
			NavModMessageEvent.Invoke(NavModMessageType.EditNavStation, true);
		}
	}

	private void ToggleEditMode(bool inEditMode, Transform tf)
	{
		Transform transform = null;
		foreach (Transform item in tf)
		{
			if (!(item.gameObject.name != "Container"))
			{
				transform = item;
				break;
			}
		}
		if (!(transform == null))
		{
			if (inEditMode)
			{
				transform.gameObject.AddComponent<Ostranauts.ShipGUIs.NavStation.Draggable>();
			}
			else
			{
				UnityEngine.Object.Destroy(transform.gameObject.GetComponent<Ostranauts.ShipGUIs.NavStation.Draggable>());
			}
		}
	}

	private void ToggleInnerPanel()
	{
		if (tfPanelIn.GetComponent<CanvasGroup>().alpha != 1f)
		{
			CanvasManager.ShowCanvasGroup(tfPanelIn.GetComponent<CanvasGroup>());
			AudioManager.am.PlayAudioEmitter("ShipUIScrew", bLoop: false);
		}
		else
		{
			CanvasManager.HideCanvasGroup(tfPanelIn.GetComponent<CanvasGroup>());
			AudioManager.am.PlayAudioEmitter("ShipUIScrew", bLoop: false);
		}
	}

	private void ToggleNote()
	{
		if (btnNote == null)
		{
			bNoteOpen = false;
		}
		else if (!bNoteAnimating)
		{
			if (bNoteOpen)
			{
				AudioManager.am.PlayAudioEmitter("ShipUIPaperRustle02", bLoop: false);
				StartCoroutine(AnimateNote(!bNoteOpen));
			}
			else
			{
				AudioManager.am.PlayAudioEmitter("ShipUIPaperRustle01", bLoop: false);
				StartCoroutine(AnimateNote(!bNoteOpen));
			}
		}
	}

	private void SetNoteInitial(bool open)
	{
		if (open)
		{
			bNoteOpen = true;
			if (!(btnNote == null))
			{
				(btnNote.transform as RectTransform).anchoredPosition = noteRaised;
				btnNote.transform.rotation = Quaternion.identity;
			}
		}
		else
		{
			bNoteOpen = false;
			if (!(btnNote == null))
			{
				(btnNote.transform as RectTransform).anchoredPosition = noteLowered;
				btnNote.transform.rotation = Quaternion.Euler(eulerLowered);
			}
		}
	}

	private IEnumerator AnimateNote(bool open)
	{
		bNoteOpen = open;
		bNoteAnimating = true;
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		if (selectedCrew != null)
		{
			selectedCrew.ZeroCondAmount("TutorialNavNoteWaiting");
			MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(selectedCrew.strID);
		}
		float duration = 0.25f;
		float t = 0f;
		Vector3 origin = noteRaised;
		Vector3 destination = noteLowered;
		Vector3 startRot = Vector3.zero;
		Vector3 destRot = eulerLowered;
		if (open)
		{
			origin = noteLowered;
			destination = noteRaised;
			startRot = eulerLowered;
			destRot = Vector3.zero;
		}
		RectTransform noteRect = btnNote.transform as RectTransform;
		if (!(noteRect == null))
		{
			while (t <= duration)
			{
				float t2 = t / duration;
				noteRect.anchoredPosition = Vector3.Lerp(origin, destination, Mathf.SmoothStep(0f, 1f, t2));
				btnNote.transform.rotation = Quaternion.Euler(Vector3.Lerp(startRot, destRot, Mathf.SmoothStep(0f, 1f, t2)));
				t += Time.unscaledDeltaTime;
				yield return null;
			}
			bNoteAnimating = false;
			noteRect.anchoredPosition = destination;
			btnNote.transform.rotation = Quaternion.Euler(destRot);
		}
	}

	private void ToggleStationKeeping(bool isOn)
	{
		SetPropMapData("chkStationKeeping", isOn.ToString());
		AIShip aIShipByRegID = AIShipManager.GetAIShipByRegID(COSelf.ship.strRegID);
		if (isOn && CrossHairTarget != null && CrossHairTarget.Ship != null)
		{
			if (aIShipByRegID == null || aIShipByRegID.ActiveCommandName != "HoldStationAutoPilot")
			{
				COSelf.ship.shipStationKeepingTarget = CrossHairTarget.Ship;
				ToggleHoldThrust(turnOn: false);
				Debug.Log("Setting station keeping to " + CrossHairTarget.Ship.strRegID);
				AIShipManager.UnregisterShip(COSelf.ship);
				AIShipManager.AddAIToShip(COSelf.ship, AIType.Auto, "INTERREGIONAL", new JsonAIShipSave
				{
					strATCLast = AIShipManager.strATCLast,
					strRegId = COSelf.ship.strRegID,
					strHomeStation = "OKLG",
					enumAIType = AIType.Auto,
					strActiveCommand = "HoldStationAutoPilot",
					strActiveCommandPayload = new string[0]
				});
			}
		}
		else if (isOn && (CrossHairTarget == null || CrossHairTarget.Ship == null || CrossHairTarget.Ship == COSelf.ship))
		{
			chkStationKeeping.isOn = false;
			if (aIShipByRegID != null && aIShipByRegID.ActiveCommandName == "HoldStationAutoPilot")
			{
				AIShipManager.UnregisterShip(COSelf.ship);
				ToggleOrbitalMode(show: true);
			}
			CGClampWarning("GUI_ORBIT_WARN_STATIONKEEP");
		}
		else
		{
			COSelf.ship.shipStationKeepingTarget = null;
			if (aIShipByRegID != null && aIShipByRegID.ActiveCommandName == "HoldStationAutoPilot")
			{
				AIShipManager.UnregisterShip(COSelf.ship);
				ToggleOrbitalMode(show: true);
			}
		}
	}

	private void ToggleHoldThrust(bool turnOn)
	{
		if (StarSystem.fEpoch - _holdthrustTimeStamp < 1.0 || IsPDANav)
		{
			return;
		}
		_holdthrustTimeStamp = StarSystem.fEpoch;
		SetPropMapData("chkHoldThrust", turnOn.ToString());
		AIShip aIShipByRegID = AIShipManager.GetAIShipByRegID(COSelf.ship.strRegID);
		if (turnOn)
		{
			ledWLock.State = 3;
			if (aIShipByRegID == null || aIShipByRegID.ActiveCommandName != "HoldThrustAutoPilot")
			{
				AIShipManager.UnregisterShip(COSelf.ship);
				AIShipManager.AddAIToShip(COSelf.ship, AIType.Auto, "INTERREGIONAL", new JsonAIShipSave
				{
					strATCLast = AIShipManager.strATCLast,
					strRegId = COSelf.ship.strRegID,
					strHomeStation = AIShipManager.strATCLast,
					enumAIType = AIType.Auto,
					strActiveCommand = "HoldThrustAutoPilot",
					strActiveCommandPayload = new string[0]
				});
			}
		}
		else
		{
			if (aIShipByRegID != null && aIShipByRegID.ActiveCommandName == "HoldThrustAutoPilot")
			{
				AIShipManager.UnregisterShip(COSelf.ship);
			}
			ledWLock.State = 0;
		}
	}

	private void SetupTravel()
	{
		ddTravel.ClearOptions();
		if (CrewSim.system == null)
		{
			return;
		}
		List<TMP_Dropdown.OptionData> list = new List<TMP_Dropdown.OptionData>();
		foreach (string key in CrewSim.system.dictShips.Keys)
		{
			if (!(COSelf.ship.strRegID == key))
			{
				Ship shipByRegID = CrewSim.system.GetShipByRegID(key);
				if (shipByRegID.HasDockingPorts || shipByRegID.Classification == Ship.TypeClassification.Asteroid || shipByRegID.Classification == Ship.TypeClassification.SignalBeacon)
				{
					TMP_Dropdown.OptionData item = new TMP_Dropdown.OptionData(key);
					list.Add(item);
				}
			}
		}
		ddTravel.AddOptions(list);
	}

	private void OnTravelClick()
	{
		Debug.Log("OnTravelClick");
		GUIDockSys component = igh.goUIRight.GetComponent<GUIDockSys>();
		if (COSelf.ship.IsDocked())
		{
			component.ForceUndock();
		}
		if (CrewSim.system.dictShips.TryGetValue(ddTravel.options[ddTravel.value].text, out var value))
		{
			if (value.GetAvailableDockingPorts(COSelf.ship) == null)
			{
				return;
			}
			COSelf.ship.objSS.CopyFrom(value.objSS, bKinematicsOnly: true);
			COSelf.ship.objSS.PlaceOrbitPosition(value.objSS);
			if (value.HasOpenDockingPorts())
			{
				component.ForceDock(value.strRegID);
			}
			else if (!value.HasDockingPorts)
			{
				CrewSim.MoorShip(new DockingPortDTO(COSelf.ship), new DockingPortDTO(value), moorLoadedToIncoming: true);
			}
		}
		else
		{
			value = CrewSim.system.SpawnShipFromStellarObject(ddTravel.options[ddTravel.value].text);
			if (value != null)
			{
				InvalidateStellarObjectDraw(value.strRegID);
				COSelf.ship.objSS.CopyFrom(value.objSS, bKinematicsOnly: true);
				COSelf.ship.objSS.PlaceOrbitPosition(value.objSS);
				CrewSim.MoorShip(new DockingPortDTO(COSelf.ship), new DockingPortDTO(value), moorLoadedToIncoming: true);
			}
		}
		SetOldFollow();
	}

	private void LoadModules(CondOwner coNav)
	{
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsFitContainerNavMod");
		List<CondOwner> list = null;
		if (CrewSim.bShipEdit || CrewSim.bDebugFightMode)
		{
			list = DataHandler.GetLoot("ItmNavStationModsAll").GetCOLoot(coNav, bSuppressOverride: false);
			aNavModCleanup = new List<CondOwner>(list);
		}
		else
		{
			list = coNav.GetCOsSafe(bAllowLocked: true, condTrigger);
		}
		list = list.OrderBy((CondOwner obj) => obj.strName.Contains("Dmg")).ToList();
		Dictionary<string, string> dictionary = coNav.mapGUIPropMaps["NavModConfig"];
		foreach (CondOwner item in list)
		{
			string text = item.mapGUIPropMaps["NavMod"]["strGUIPrefab"];
			if (item.HasCond("IsDamaged"))
			{
				text = item.mapGUIPropMaps["NavMod"]["strGUIPrefabDmg"];
			}
			if (_navMods.ContainsKey(text))
			{
				continue;
			}
			_navMods[text] = item;
			GameObject gameObject = null;
			if (!string.IsNullOrEmpty(text))
			{
				Transform transform = base.transform.Find(text);
				if (transform != null)
				{
					gameObject = transform.gameObject;
					gameObject.SetActive(value: true);
				}
			}
			if (gameObject == null)
			{
				GameObject gameObject2 = Resources.Load<GameObject>("GUIShip/GUIOrbitDraw/" + text);
				if (gameObject2 == null)
				{
					Debug.LogWarning("Could not load NavMod: " + text);
					continue;
				}
				gameObject = UnityEngine.Object.Instantiate(gameObject2, base.transform);
				gameObject.name = text;
				gameObject.transform.SetAsFirstSibling();
			}
			if (gameObject == null)
			{
				Debug.LogWarning("Failed to load module");
				continue;
			}
			Transform transform2 = gameObject.transform.Find("Container");
			if (transform2 == null)
			{
				Debug.LogWarning("no container child!");
				continue;
			}
			NavModBase component = gameObject.GetComponent<NavModBase>();
			string value = null;
			string text2 = text;
			if (text2.IndexOf("Dmg") == text2.Length - 3)
			{
				text2 = text2.Substring(0, text2.Length - 3);
			}
			if (!dictionary.TryGetValue(text2, out value) || string.IsNullOrEmpty(value))
			{
				value = item.mapGUIPropMaps["NavMod"]["strDefaultPos"];
				component.DisableMod();
			}
			else
			{
				component.EnableMod();
			}
			RectTransform component2 = transform2.GetComponent<RectTransform>();
			string[] array = value.Split('|');
			if (array.Length != 4)
			{
				return;
			}
			Vector2 anchorMin = new Vector2(float.Parse(array[0]), float.Parse(array[1]));
			Vector2 anchorMax = new Vector2(float.Parse(array[2]), float.Parse(array[3]));
			component2.anchorMin = anchorMin;
			component2.anchorMax = anchorMax;
			component2.offsetMin = Vector2.zero;
			component2.offsetMax = Vector2.zero;
			if (!_editMenu.DoesModFit(component))
			{
				component.DisableMod();
			}
		}
		Transform transform3 = base.transform.Find("pnlPegboardBG");
		if (transform3 != null)
		{
			transform3.SetAsFirstSibling();
		}
	}

	private void SaveModules()
	{
		Dictionary<string, string> value = null;
		COSelf.mapGUIPropMaps.TryGetValue("NavModConfig", out value);
		if (value == null)
		{
			value = new Dictionary<string, string>();
		}
		foreach (string item in value.Keys.ToList())
		{
			COSelf.mapGUIPropMaps["NavModConfig"][item] = "";
		}
		foreach (Transform item2 in base.transform)
		{
			if (!item2.gameObject.activeSelf)
			{
				continue;
			}
			NavModBase component = item2.GetComponent<NavModBase>();
			if (!(component == null))
			{
				Ostranauts.Core.Models.Tuple<Point, Point> roundedAnchors = component.GetRoundedAnchors();
				string text = item2.gameObject.name;
				if (text.IndexOf("Dmg") == text.Length - 3)
				{
					text = text.Substring(0, text.Length - 3);
				}
				value[text] = roundedAnchors.Item1.X.ToString("f2") + "|" + roundedAnchors.Item1.Y.ToString("f2") + "|" + roundedAnchors.Item2.X.ToString("f2") + "|" + roundedAnchors.Item2.Y.ToString("f2");
			}
		}
		COSelf.mapGUIPropMaps["NavModConfig"] = value;
	}

	public void CrewSwitch(CondOwner coNav)
	{
		if (coNav == COSelf)
		{
			return;
		}
		NavModBase[] componentsInChildren = GetComponentsInChildren<NavModBase>();
		if (componentsInChildren != null)
		{
			NavModBase[] array = componentsInChildren;
			for (int i = 0; i < array.Length; i++)
			{
				array[i].DisableMod();
			}
		}
		Dictionary<string, string> dict = coNav.mapGUIPropMaps[strCOKey];
		SetData(coNav, dict, strCOKey);
		if (CrewSim.bShipEdit)
		{
			foreach (CondOwner value in _navMods.Values)
			{
				value.Destroy();
			}
		}
		_navMods.Clear();
		LoadModules(coNav);
	}

	public override void Init(CondOwner coSelf, Dictionary<string, string> dict, string strCOKey)
	{
		initNoAudio = true;
		if (CrewSim.system != null)
		{
			RevealStartingVessels(coSelf);
		}
		base.Init(coSelf, dict, strCOKey);
		if (base.COSelf == null || dictPropMap == null)
		{
			return;
		}
		if (strCOKey != "Panel A")
		{
			_shipPropMap = COSelf.mapGUIPropMaps["Panel A"];
			IsPDANav = strCOKey == "PDANAV";
		}
		if (!IsPDANav)
		{
			LoadModules(COSelf);
		}
		else
		{
			foreach (Transform item in base.transform)
			{
				NavModBase component = item.gameObject.GetComponent<NavModBase>();
				if (!(component == null))
				{
					component.EnableMod();
				}
			}
			bRCS = false;
			bNoteOpen = false;
		}
		LoadSystem();
		SetupTravel();
		if (dictPropMap.TryGetValue("fTimeRate", out var value))
		{
			fTimeFuture = float.Parse(value);
			fTimeFutureTarget = fTimeFuture;
		}
		if (dictPropMap.TryGetValue("strPOIShip", out value))
		{
			foreach (ShipDraw aShipDraw in aShipDraws)
			{
				if (aShipDraw.ship.strRegID == value)
				{
					LockTarget(new NavPOI(aShipDraw, GetNavStationShip(), ShipPropMap));
					break;
				}
			}
		}
		else if (dictPropMap.TryGetValue("strPOIBO", out value))
		{
			LockTarget(new NavPOI(CrewSim.system.GetBO(value)));
		}
		else if (dictPropMap.TryGetValue("strPOIObject", out value))
		{
			LockStellarObjectDelayed(value);
		}
		else if (dictPropMap.TryGetValue("strPOIX", out value))
		{
			double sx = double.Parse(value);
			dictPropMap.TryGetValue("strPOIY", out value);
			double sy = double.Parse(value);
			LockTarget(new NavPOI(sx, sy));
		}
		if (dictPropMap.TryGetValue("chkStationKeeping", out value) && chkStationKeeping != null)
		{
			chkStationKeeping.isOn = bool.Parse(value);
		}
		if (dictPropMap.TryGetValue("chkHoldThrust", out value))
		{
			ToggleHoldThrust(bool.Parse(value));
		}
		if (dictPropMap.TryGetValue("dMagTarget", out value))
		{
			float num = float.Parse(value);
			if (num != 0f)
			{
				dMagTarget = num;
			}
		}
		if (dictPropMap.TryGetValue("fZoomTimer", out value))
		{
			float num2 = float.Parse(value);
			if (fZoomTimer != 0f)
			{
				fZoomTimer = num2;
			}
		}
		SetNoteInitial(btnNote != null);
		if (dictPropMap.TryGetValue("bNote", out value) && bool.Parse(value) != bNoteOpen)
		{
			SetNoteInitial(open: false);
		}
		if (dictPropMap.TryGetValue("bXPDROn", out value) && bool.Parse(value) != bNoteOpen)
		{
			SetNoteInitial(open: false);
		}
		float y = 0.25f;
		if (dictPropMap.TryGetValue("slidThrottle", out value))
		{
			y = float.Parse(value);
		}
		else
		{
			Ship navStationShip = GetNavStationShip();
			if (navStationShip != null)
			{
				double num3 = navStationShip.RCSAccelMaxUndocked;
				if (num3 == 0.0)
				{
					num3 = navStationShip.LiftRotorsThrustStrength / 149597870f;
				}
				if (num3 != 0.0)
				{
					y = Mathf.Clamp((float)(1.9016982118751132E-10 / num3), 0f, 1f);
				}
				y = MathUtils.ExpMapInv(y);
			}
		}
		SetPropMapData("slidThrottle", y.ToString(CultureInfo.InvariantCulture));
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		if (selectedCrew != null)
		{
			if (selectedCrew.HasCond("TutorialNavDockingSwitchNavShow"))
			{
				selectedCrew.ZeroCondAmount("TutorialNavDockingSwitchNavShow");
				MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(selectedCrew.strID);
			}
			selectedCrew.SetCondAmount("IsNavStationUsed", 1.0);
			MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(selectedCrew.strID);
			selectedCrew.ZeroCondAmount("IsNavStationUsed");
			base.gameObject.AddComponent<GUIOrbitDrawTut>().SetNewGameObjectives(this, selectedCrew, sdNS);
		}
		fRCSMax = (float)GetNavStationShip().GetRCSMax();
		fZoomTimer = 2f;
		AudioManager.am.SuggestMusic("Map");
		OpenedNavStationUI.Invoke();
		if (CrewSim.coPlayer != null && !CrewSim.coPlayer.HasCond("IsEnemySpawnBlocked"))
		{
			if (CrewSim.coPlayer.HasCond("IsDuePirateSpawn") && BeatManager.DebugPirate())
			{
				BeatManager.ResetTensionTimer();
			}
			if (CrewSim.coPlayer.HasCond("IsDueFactionSpawn") && BeatManager.DebugFactionShip(CrewSim.coPlayer.GetCondAmount("IsDueFactionSpawn")))
			{
				BeatManager.ResetTensionTimer();
			}
		}
		string text = DataHandler.GetString("GUI_ORBIT_USER_UNKNOWN");
		bool flag = false;
		if (selectedCrew != null)
		{
			string shipOwner = CrewSim.system.GetShipOwner(COSelf.ship.strRegID);
			flag = shipOwner == selectedCrew.strID;
			if (!flag && selectedCrew.socUs != null)
			{
				flag = selectedCrew.socUs.GetRelationship(shipOwner)?.aRelationships.Contains("RELCaptain") ?? false;
			}
			text = selectedCrew.FriendlyName;
			if (COSelf.ship != null)
			{
				COSelf.ship.ElectronicSystems.UpdateDetectionThreshold(selectedCrew);
			}
		}
		if (!flag)
		{
			CanvasManager.ShowCanvasGroup(cgNag);
			fEpochNagEnd = StarSystem.fEpoch + 10.0;
			AudioManager.am.PlayAudioEmitter("ShipUIBtnDCNoClearance", bLoop: false);
		}
		else
		{
			CanvasManager.HideCanvasGroup(cgNag);
		}
		if (COSelf.ship != null)
		{
			COSelf.ship.LogAdd(DataHandler.GetString("NAV_LOG_USER_SESSION") + text + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
		}
		initNoAudio = false;
		Instance = this;
	}

	public override void SaveAndClose()
	{
		UpdateShipSelection.RemoveListener(LockTarget);
		if (_shipPropMap == null && dictPropMap != null && COSelf != null)
		{
			COSelf.mapGUIPropMaps["Panel A"] = dictPropMap;
		}
		_shipPropMap = null;
		if (dictPropMap == null)
		{
			return;
		}
		if (!CrewSim.bShipEdit)
		{
			SetPropMapData("bNote", bNoteOpen.ToString().ToLower());
			SetPropMapData("nProjSteps", nProjSteps.ToString());
			SetPropMapData("fTimeRate", fTimeFuture.ToString());
			SetPropMapData("strPOIShip", null);
			SetPropMapData("strPOIBO", null);
			SetPropMapData("strPOIX", null);
			SetPropMapData("strPOIY", null);
			SetPropMapData("dMagTarget", ((float)(dCanvasSolarXX * dCanvasSolarXX + dCanvasSolarXY * dCanvasSolarXY)).ToString());
			SetPropMapData("fZoomTimer", "2.0");
		}
		else
		{
			foreach (CondOwner value in _navMods.Values)
			{
				value.Destroy();
			}
		}
		if (aNavModCleanup != null)
		{
			foreach (CondOwner item in aNavModCleanup)
			{
				item.RemoveFromCurrentHome();
				item.Destroy();
			}
			aNavModCleanup = null;
		}
		if (CrossHairTarget.Ship != null)
		{
			SetPropMapData("strPOIShip", CrossHairTarget.Ship.strRegID);
		}
		else if (CrossHairTarget.bodyOrbit != null)
		{
			SetPropMapData("strPOIBO", CrossHairTarget.bodyOrbit.strName);
		}
		else if (CrossHairTarget.stellarObj != null)
		{
			SetPropMapData("strPOIObject", CrossHairTarget.stellarObj.strID);
		}
		else
		{
			CrossHairTarget.GetSXY(out var sx, out var sy);
			SetPropMapData("strPOIX", sx.ToString());
			SetPropMapData("strPOIY", sy.ToString());
		}
		VectorLine.Destroy(aUIs);
		VectorLine.Destroy(ref lineCross);
		VectorLine.Destroy(ref lineCourse);
		VectorLine.Destroy(ref lineGrav);
		if (lineStationKeepingTarget != null)
		{
			VectorLine.Destroy(ref lineStationKeepingTarget);
		}
		foreach (BODraw aBODraw in aBODraws)
		{
			aBODraw.Destroy();
		}
		foreach (ShipDraw aShipDraw in aShipDraws)
		{
			aShipDraw.Destroy();
		}
		foreach (StellarObjectGroup aStellarObjectGroup in aStellarObjectGroups)
		{
			aStellarObjectGroup.Destroy();
		}
		foreach (DebugDraw aDebugDraw in aDebugDraws)
		{
			aDebugDraw.Destroy();
		}
		aDebugDraws.Clear();
		if (COSelf != null && COSelf.ship != null && !IsPDANav && !HoldingThrustActive)
		{
			COSelf.ship.Maneuver(0f, 0f, 0f, 0, 1E-10f);
		}
		fClampDisengageWarningTimer = 0f;
		if (cgClampWarning != null)
		{
			cgClampWarning.alpha = 0f;
		}
		StopMapAudio();
		StopAllCoroutines();
		base.SaveAndClose();
		Instance = null;
	}

	private bool HasAncestor(BodyOrbit target, BodyOrbit hit)
	{
		if (hit == null || target == null)
		{
			return false;
		}
		if (target == hit)
		{
			return true;
		}
		return HasAncestor(target.boParent, hit);
	}

	private StellarObjectDraw FindNearestStellarObject(Vector2 canvasPos, float clickRadius, double fTargetEpoch)
	{
		foreach (StellarObjectGroup aStellarObjectGroup in aStellarObjectGroups)
		{
			AsteroidField asteroidField = aStellarObjectGroup.AsteroidField;
			double dTimeCalcLast = asteroidField.dTimeCalcLast;
			asteroidField.UpdateTime(fTargetEpoch);
			SolarToCanvas(asteroidField.dXReal, asteroidField.dYReal, out var cx, out var cy);
			SolarToCanvas(asteroidField.dXReal, asteroidField.dYReal + asteroidField.fRadius, out var cx2, out var cy2);
			double distance = MathUtils.GetDistance(cx, cy, cx2, cy2);
			float num = (float)(MathUtils.GetDistance(canvasPos.x, canvasPos.y, cx, cy) - distance);
			asteroidField.UpdateTime(dTimeCalcLast);
			if (clickRadius > num)
			{
				return aStellarObjectGroup.FindNearestStellarObject(canvasPos, clickRadius, fTargetEpoch);
			}
		}
		return null;
	}

	private BodyOrbit FindNearestBodyOrbit(Vector2 canvasPos, float clickRadius, double fTargetEpoch)
	{
		BodyOrbit bodyOrbit = null;
		float num = clickRadius;
		foreach (BODraw aBODraw in aBODraws)
		{
			if (!HasAncestor(aBODraw.bo, bodyOrbit))
			{
				aBODraw.bo.UpdateTime(fTargetEpoch);
				SolarToCanvas(aBODraw.bo.dXReal, aBODraw.bo.dYReal, out var cx, out var cy);
				SolarToCanvas(aBODraw.bo.dXReal, aBODraw.bo.dYReal + aBODraw.bo.fRadius, out var cx2, out var cy2);
				double distance = MathUtils.GetDistance(cx, cy, cx2, cy2);
				float num2 = (float)(MathUtils.GetDistance(canvasPos.x, canvasPos.y, cx, cy) - distance);
				if (num > num2)
				{
					num = num2;
					bodyOrbit = aBODraw.bo;
				}
			}
		}
		return bodyOrbit;
	}

	private ShipDraw FindNearestShipDraw(Vector2 canvasPos, float radius, double fTargetEpoch)
	{
		ShipDraw result = null;
		float num = radius;
		foreach (ShipDraw aShipDraw in aShipDraws)
		{
			if (aShipDraw == null || aShipDraw.ship == null || aShipDraw.ship.objSS == null)
			{
				Debug.LogWarning("ShipDraws contained a null");
				continue;
			}
			Point predictedPosition = aShipDraw.ship.objSS.GetPredictedPosition((float)(fTargetEpoch - StarSystem.fEpoch));
			predictedPosition += aShipDraw.GetPositionOffset();
			SolarToCanvas(predictedPosition.X, predictedPosition.Y, out var cx, out var cy);
			SolarToCanvas(predictedPosition.X + (double)aShipDraw.fRadiusAU, predictedPosition.Y, out var cx2, out var cy2);
			double distance = MathUtils.GetDistance(cx, cy, cx2, cy2);
			float num2 = (float)(MathUtils.GetDistance(canvasPos.x, canvasPos.y, cx, cy) - distance);
			if (num > num2)
			{
				num = num2;
				result = aShipDraw;
			}
		}
		return result;
	}

	private NavPOI FindNearestNavPOI(Vector2 canvasPos, float radius)
	{
		ShipDraw shipDraw = FindNearestShipDraw(canvasPos, radius, StarSystem.fEpoch);
		if (shipDraw != null)
		{
			return new NavPOI(shipDraw, GetNavStationShip(), ShipPropMap);
		}
		if (dEpoch != StarSystem.fEpoch)
		{
			shipDraw = FindNearestShipDraw(canvasPos, radius, dEpoch);
			if (shipDraw != null)
			{
				return new NavPOI(shipDraw, GetNavStationShip(), ShipPropMap)
				{
					fTargetFuture = dEpoch - StarSystem.fEpoch
				};
			}
		}
		BodyOrbit bodyOrbit = FindNearestBodyOrbit(canvasPos, radius, StarSystem.fEpoch);
		if (bodyOrbit != null)
		{
			return new NavPOI(bodyOrbit);
		}
		if (dEpoch != StarSystem.fEpoch)
		{
			bodyOrbit = FindNearestBodyOrbit(canvasPos, radius, dEpoch);
			if (bodyOrbit != null)
			{
				return new NavPOI(bodyOrbit)
				{
					fTargetFuture = dEpoch - StarSystem.fEpoch
				};
			}
		}
		StellarObjectDraw stellarObjectDraw = FindNearestStellarObject(canvasPos, radius, StarSystem.fEpoch);
		if (stellarObjectDraw != null)
		{
			return new NavPOI(stellarObjectDraw);
		}
		if (dEpoch != StarSystem.fEpoch)
		{
			stellarObjectDraw = FindNearestStellarObject(canvasPos, radius, dEpoch);
			if (stellarObjectDraw != null)
			{
				return new NavPOI(stellarObjectDraw)
				{
					fTargetFuture = dEpoch - StarSystem.fEpoch
				};
			}
		}
		CanvasToSolar(canvasPos.x, canvasPos.y, out var sx, out var sy);
		return new NavPOI(sx, sy);
	}

	private void LockTarget(NavPOI poi)
	{
		if (poi != null)
		{
			CrossHairTarget = poi;
			CrossHairTarget.GetSXY(out dDragStartSX, out dDragStartSY);
			SelectTravelDropDown(CrossHairTarget.name);
			if (!initNoAudio)
			{
				AudioManager.am.PlayAudioEmitter("ShipUINSMapPan04", bLoop: false);
			}
			if (GetKnobFollowState == 2)
			{
				follow = CrossHairTarget;
				SetOldFollow();
			}
		}
	}

	public void LockTarget(string regID)
	{
		ShipDraw shipDraw = FindShipDraw(regID);
		if (shipDraw != null)
		{
			NavPOI navPOI = new NavPOI(shipDraw, GetNavStationShip(), ShipPropMap);
			SetPropMapData("nFollow", 2.ToString());
			crossHairInfo = ShipInfo.GetShipInfo(GetNavStationShip(), navPOI.Ship, ShipPropMap);
			LockTarget(navPOI);
		}
	}

	private void LockStellarObjectDelayed(string regID)
	{
		if (!string.IsNullOrEmpty(regID))
		{
			StartCoroutine(LockTargetWhenReady(regID));
		}
	}

	private IEnumerator LockTargetWhenReady(string regID)
	{
		while (true)
		{
			StellarObjectDraw stellarObjectDraw = FindStellarObjectDraw(regID);
			if (stellarObjectDraw != null)
			{
				LockTarget(new NavPOI(stellarObjectDraw));
				break;
			}
			if (_delayedLoadingFinished)
			{
				break;
			}
			yield return null;
		}
	}

	public bool IsTargetKnown(string strRegID)
	{
		if (string.IsNullOrEmpty(strRegID))
		{
			return false;
		}
		return ShipInfo.GetShipInfo(GetNavStationShip(), CrewSim.system.GetShipByRegID(strRegID), ShipPropMap)?.Known ?? false;
	}

	private void SelectTravelDropDown(string strTargetID)
	{
		if (strTargetID == null)
		{
			return;
		}
		for (int i = 0; i < ddTravel.options.Count; i++)
		{
			if (ddTravel.options[i].text == strTargetID)
			{
				ddTravel.value = i;
				return;
			}
		}
		if (CrewSim.system.dictStellarObjects.ContainsKey(strTargetID))
		{
			TMP_Dropdown.OptionData item = new TMP_Dropdown.OptionData(strTargetID);
			ddTravel.AddOptions(new List<TMP_Dropdown.OptionData> { item });
			ddTravel.value = ddTravel.options.Count - 1;
		}
	}

	private void UpdateWASDCluster()
	{
		if (dictWASD == null)
		{
			dictWASD = new Dictionary<string, GUIBtnPressHold>();
		}
		UpdateWASDBtn("W", "NavModControls/Container/prefabPnlWASD/bmpKeyW");
		UpdateWASDBtn("S", "NavModControls/Container/prefabPnlWASD/bmpKeyS");
		UpdateWASDBtn("A", "NavModControls/Container/prefabPnlWASD/bmpKeyA");
		UpdateWASDBtn("D", "NavModControls/Container/prefabPnlWASD/bmpKeyD");
		UpdateWASDBtn("Q", "NavModControls/Container/prefabPnlWASD/bmpKeyQ");
		UpdateWASDBtn("E", "NavModControls/Container/prefabPnlWASD/bmpKeyE");
		UpdateWASDBtn("+", "NavModControls/Container/prefabPnlWASD/bmpKeyPlus");
		UpdateWASDBtn("-", "NavModControls/Container/prefabPnlWASD/bmpKeyMinus");
		UpdateWASDBtn(strQEKey, "NavModControls/Container/prefabPnlWASD/bmpKeyQE");
	}

	private void UpdateWASDBtn(string strKey, string strBtn)
	{
		if (strKey == null || strBtn == null)
		{
			return;
		}
		Transform transform = base.transform.Find(strBtn);
		if (transform != null)
		{
			GUIBtnPressHold component = transform.GetComponent<GUIBtnPressHold>();
			if (component != null)
			{
				dictWASD[strKey] = component;
			}
			AudioManager.AddBtnAudio(transform.GetComponent<Button>().gameObject, "ShipUIBtnNSDockSysClampIn", "ShipUIBtnNSDockSysClampOut");
		}
	}

	private void ScrollLog(float fAmount)
	{
		float verticalNormalizedPosition = Mathf.Clamp(srLog.verticalNormalizedPosition + fAmount * srLog.verticalScrollbar.size, 0f, 1f);
		srLog.verticalNormalizedPosition = verticalNormalizedPosition;
		AudioManager.am.PlayAudioEmitter("ShipUINSMapPan02", bLoop: false);
	}

	private void MouseHandler()
	{
		if (Info.activeThisFrame)
		{
			return;
		}
		RectTransformUtility.ScreenPointToLocalPointInRectangle(rectDisplayPanel, InputManager.MousePosition, GetComponentInParent<Canvas>().worldCamera, out var localPoint);
		localPoint.x = (localPoint.x - rectDisplayPanel.rect.x) * 512f / rectDisplayPanel.rect.width;
		localPoint.y = (localPoint.y - rectDisplayPanel.rect.y) * 512f / rectDisplayPanel.rect.height;
		Camera component = GUIRenderTargets.goLines.transform.parent.parent.Find("CameraOrbitDraw").GetComponent<Camera>();
		if (component == null)
		{
			return;
		}
		Vector3 vector = component.ScreenToWorldPoint(localPoint);
		RectTransform component2 = rectDrawPanel;
		if (cgStatus.alpha > 0f)
		{
			component2 = cgStatus.GetComponent<RectTransform>();
		}
		Vector3[] array = new Vector3[4];
		component2.GetWorldCorners(array);
		Vector2 canvasPos = default(Vector2);
		canvasPos.x = (vector.x - array[0].x) / (array[2].x - array[0].x) * component2.rect.width;
		canvasPos.y = (vector.y - array[0].y) / (array[2].y - array[0].y) * component2.rect.height;
		bool flag = 0f <= canvasPos.x && canvasPos.x <= component2.rect.width && 0f <= canvasPos.y && canvasPos.y <= component2.rect.height;
		if (GetKnobFollowState == 0)
		{
			double sx;
			double sy;
			if (flag)
			{
				CanvasToSolar(canvasPos.x, canvasPos.y, out sx, out sy);
			}
			else
			{
				CanvasToSolar(rectDrawPanel.rect.width * 0.5f, rectDrawPanel.rect.height * 0.5f, out sx, out sy);
			}
			follow = new NavPOI(sx, sy);
		}
		if (_commandClick.InputAction.WasPressedThisFrame() && !bNoteOpen)
		{
			fTimeMouseDown = Time.realtimeSinceStartup;
			if (!bRCS)
			{
				bDragValid = flag;
				CanvasToSolar(canvasPos.x, canvasPos.y, out dDragStartSX, out dDragStartSY);
				dDragStartCX = canvasPos.x;
				dDragStartCY = canvasPos.y;
			}
			else
			{
				bDragValid = false;
			}
		}
		else if (_commandClick.InputAction.WasReleasedThisFrame() && !bNoteOpen)
		{
			if (flag && Time.realtimeSinceStartup - fTimeMouseDown < 0.25f)
			{
				NavPOI navPOI = FindNearestNavPOI(canvasPos, 8f);
				LockTarget(navPOI);
				CondOwner selectedCrew = CrewSim.GetSelectedCrew();
				if (navPOI.Ship != null && selectedCrew != null)
				{
					SelectedShipDraw.Invoke(navPOI.Ship.strRegID);
				}
			}
		}
		else if (_commandClick.InputAction.IsPressed() && bDragValid)
		{
			if (cgStatus.alpha > 0f)
			{
				if ((double)canvasPos.y - dDragStartCY > 0.0)
				{
					ScrollLog(fLogScrollRate);
				}
				else if ((double)canvasPos.y - dDragStartCY < 0.0)
				{
					ScrollLog(0f - fLogScrollRate);
				}
			}
			else
			{
				SolarToCanvas(dDragStartSX, dDragStartSY, out var cx, out var cy);
				double num = cx - (double)canvasPos.x;
				double num2 = cy - (double)canvasPos.y;
				float num3 = 0.5f;
				float num4 = 3.75f;
				fVelocityX *= 0.5f;
				fVelocityY *= 0.5f;
				fVelocityX += (float)(num * (double)num4);
				fVelocityY += (float)(num2 * (double)num4);
				PanCanvasImmediateC(num * (double)num3, num2 * (double)num3);
			}
		}
		if (_commandRightClick.InputAction.IsPressed())
		{
		}
		if (_commandMiddleClick.InputAction.WasPressedThisFrame())
		{
			if (aUIs != null)
			{
				VectorLine.Destroy(aUIs);
			}
			aUIs = new List<VectorLine>();
			InitOrbitArea(goOrbitPanel);
			InitFrame(GUIRenderTargets.goLines.transform.Find("pnlFrame").gameObject);
		}
		else
		{
			_commandMiddleClick.InputAction.IsPressed();
		}
		float y = _commandScrollWheel.InputAction.ReadValue<Vector2>().y;
		if (flag)
		{
			if (y != 0f)
			{
				fZoomTimer = -1f;
			}
			fVelocityZ -= y * -0.3f;
			if (_commandPanFaster.InputAction.IsPressed())
			{
				fVelocityZ -= y * -1.7f;
			}
		}
		if (y > 0f)
		{
			ScrollLog(fLogScrollRate);
		}
		else if (y < 0f)
		{
			ScrollLog(0f - fLogScrollRate);
		}
	}

	private void KeyHandler()
	{
		if (IsPDANav || CrewSim.Typing)
		{
			return;
		}
		float num = 0f;
		float num2 = 0f;
		float num3 = 0f;
		int nNoiseOnly = 0;
		bool playerThrusting = PlayerThrusting;
		PlayerThrusting = false;
		bool flag = false;
		bool flag2 = false;
		bool flag3 = false;
		if (CrewSim.TimeElapsedScaled() > 0f && bRCS)
		{
			if (_commandFlyUp.InputAction.IsPressed() || dictWASD["W"].bPressed)
			{
				num2 += 1f;
				PlayerThrusting = true;
				flag = true;
			}
			if (_commandFlyDown.InputAction.IsPressed() || dictWASD["S"].bPressed)
			{
				num2 -= 1f;
				PlayerThrusting = true;
				flag = true;
			}
			if (_commandFlyLeft.InputAction.IsPressed() || dictWASD["A"].bPressed)
			{
				num -= 1f;
				PlayerThrusting = true;
			}
			if (_commandFlyRight.InputAction.IsPressed() || dictWASD["D"].bPressed)
			{
				num += 1f;
				PlayerThrusting = true;
			}
			flag2 = _commandShipCCW.InputAction.IsPressed() || dictWASD["Q"].bPressed || dictWASD[strQEKey].bPressed;
			flag3 = _commandShipCW.InputAction.IsPressed() || dictWASD["E"].bPressed || dictWASD[strQEKey].bPressed;
			if (_commandShipAttitude.InputAction.IsPressed() || (flag2 && flag3))
			{
				if (COSelf.ship.objSS.fW > 0f)
				{
					num3 = -1f;
				}
				else if (COSelf.ship.objSS.fW < 0f)
				{
					num3 = 1f;
				}
				PlayerThrusting = true;
				flag2 = true;
				flag3 = true;
			}
			else if (flag2)
			{
				num3 += 1f;
				PlayerThrusting = true;
			}
			else if (flag3)
			{
				num3 -= 1f;
				PlayerThrusting = true;
			}
			if (PlayerThrusting)
			{
				if (!bClaimed)
				{
					bClaimed = true;
					CondOwner selectedCrew = CrewSim.GetSelectedCrew();
					if (selectedCrew != null)
					{
						selectedCrew.ClaimShip(COSelf.ship.strRegID);
						if (COSelf.ship.objSS.bBOLocked && !COSelf.ship.objSS.bIsBO)
						{
							bool flag4 = false;
							foreach (Ship allDockedShip in COSelf.ship.GetAllDockedShips())
							{
								if (allDockedShip != null && !allDockedShip.bDestroyed && allDockedShip.objSS.bIsBO)
								{
									flag4 = true;
									break;
								}
							}
							if (!flag4)
							{
								COSelf.ship.objSS.UnlockFromBO();
							}
						}
					}
				}
				if (num2 == 0f && HoldingThrustActive)
				{
					num2 = 1f;
				}
				if (COSelf.ship.objSS.bBOLocked || COSelf.ship.objSS.bIsBO)
				{
					nNoiseOnly = 1;
					num = (num2 = (num3 = 0f));
				}
				if (COSelf.ship.IsDocked() && !COSelf.ship.TowBracesSecured() && !COSelf.ship.IsMoored())
				{
					CGClampWarning("GUI_ORBIT_WARN_CLAMP");
				}
				NavModMessageEvent.Invoke(NavModMessageType.IsThrusting, this);
				SetPropMapData("chkEngage", false.ToString());
			}
		}
		else if (CrewSim.Paused && bRCS)
		{
			bool flag5 = false;
			if (_commandFlyUp.InputAction.IsPressed() || dictWASD["W"].bPressed)
			{
				flag5 = true;
			}
			if (_commandFlyDown.InputAction.IsPressed() || dictWASD["S"].bPressed)
			{
				flag5 = true;
			}
			if (_commandFlyLeft.InputAction.IsPressed() || dictWASD["A"].bPressed)
			{
				flag5 = true;
			}
			if (_commandFlyRight.InputAction.IsPressed() || dictWASD["D"].bPressed)
			{
				flag5 = true;
			}
			bool flag6 = _commandShipCCW.InputAction.IsPressed() || dictWASD["Q"].bPressed || dictWASD[strQEKey].bPressed;
			bool flag7 = _commandShipCW.InputAction.IsPressed() || dictWASD["E"].bPressed || dictWASD[strQEKey].bPressed;
			if (_commandShipAttitude.InputAction.IsPressed() || flag6 || flag7)
			{
				flag5 = true;
			}
			if (flag5)
			{
				CGClampWarning("GUI_ORBIT_WARN_PAUSED");
			}
		}
		if (_commandShipLockW.InputAction.IsPressed())
		{
			ToggleHoldThrust(ledWLock.State != 3);
		}
		else if (ledWLock.State == 3 && flag)
		{
			ToggleHoldThrust(turnOn: false);
		}
		num3 /= Time.timeScale;
		bool flag8 = false;
		if (COSelf.ship.objSS.fW == 0f)
		{
			flag8 = num3 * fPreviousSpin < 0f;
		}
		bool flag9 = false;
		if (COSelf.ship.IsDocked() && num == 0f && num2 == 0f && num3 == 0f)
		{
			flag9 = COSelf.ship.GetAllDockedShips().Any((Ship dShip) => dShip?.TowBraceSecured(COSelf.ship.strRegID) ?? false);
			if (flag9 && playerThrusting && !PlayerThrusting)
			{
				COSelf.ship.Maneuver(0f, 0f, 0f, 0, 1E-10f);
			}
		}
		bool propMapData = GetPropMapData("chkEngage", defaultReturnValue: false);
		bool flag10 = chkStationKeeping.isOn && !PlayerThrusting;
		if (!PlayerThrusting && playerThrusting)
		{
			flag10 = false;
		}
		bool flag11 = HoldingThrustActive && !PlayerThrusting;
		if ((propMapData || flag9 || flag10 || flag11 || PlayerThrusting) && (!PlayerThrusting || (num3 == 0f && !(flag2 && flag3)) || num != 0f || num2 != 0f))
		{
			ToggleOrbitalMode(show: false);
		}
		if (!propMapData && !flag9 && !flag10 && !flag11)
		{
			string value;
			int engineMode = ((!dictPropMap.TryGetValue("nKnobEngineMode", out value)) ? 1 : int.Parse(value));
			float x = (dictPropMap.TryGetValue("slidThrottle", out value) ? float.Parse(value) : 0.25f);
			x = MathUtils.ExpMap(x);
			COSelf.ship.Maneuver(num * x, num2 * x, flag8 ? 0f : (num3 * x), nNoiseOnly, CrewSim.TimeElapsedScaled(), (Ship.EngineMode)engineMode);
			if (!PlayerThrusting && playerThrusting && !chkStationKeeping.isOn)
			{
				ToggleOrbitalMode(show: true);
			}
		}
		if (fPreviousSpin * num3 >= 0f)
		{
			fPreviousSpin = COSelf.ship.objSS.fW;
		}
		if (PlayerThrusting && _hasNotSeenRefuelingTutorial)
		{
			CheckRefuelingTutorial();
		}
	}

	private void CheckRefuelingTutorial()
	{
		if (!(fRemass <= 0f) && !((double)fRemass > (double)fRCSMax * 0.25))
		{
			CondOwner selectedCrew = CrewSim.GetSelectedCrew();
			if (!(selectedCrew == null))
			{
				MonoSingleton<ObjectiveTracker>.Instance.AddObjective(new Objective(selectedCrew, "Low fuel! Refuel your ship", "TIsTutorialRefuelComplete")
				{
					strDisplayDesc = "Dock with a station and refuel your ship at a refueling kiosk",
					strDisplayDescComplete = "Ship refueled",
					CTFocus = DataHandler.GetCondTrigger("TIsRefuelKiosk"),
					bTutorial = true
				});
				selectedCrew.AddCondAmount("TutorialRefuelStart", 1.0);
				_hasNotSeenRefuelingTutorial = false;
			}
		}
	}

	public void CGClampWarning(string strMessageName, bool bSkipDH = false)
	{
		string text = (bSkipDH ? strMessageName : DataHandler.GetString(strMessageName));
		cgClampWarning.GetComponentInChildren<TMP_Text>().text = text;
		cgClampWarning.alpha = 1f;
		fClampDisengageWarningTimer = 5f;
		AudioManager.am.PlayAudioEmitter("ShipUIBtnNSProxWarn", bLoop: false);
	}

	public static CondOwner GenerateNavDataCO(CondOwner coDevice)
	{
		CondOwner condOwner = DataHandler.GetCondOwner("DataBINNavStationData");
		condOwner.mapGUIPropMaps["DataBINNAV"] = new Dictionary<string, string>();
		if (coDevice == null)
		{
			return condOwner;
		}
		RevealStartingVessels(coDevice);
		if (coDevice.mapGUIPropMaps.TryGetValue("Panel A", out var value))
		{
			foreach (KeyValuePair<string, string> item in value)
			{
				if (item.Key.IndexOf("Contact_") == 0)
				{
					condOwner.mapGUIPropMaps["DataBINNAV"][item.Key] = item.Value;
				}
			}
		}
		return condOwner;
	}

	public static void ImportNavDataCO(CondOwner coDevice, CondOwner coNavData)
	{
		if (coDevice == null || coNavData == null || !coNavData.mapGUIPropMaps.TryGetValue("DataBINNAV", out var value))
		{
			return;
		}
		if (!coDevice.mapGUIPropMaps.TryGetValue("Panel A", out var value2))
		{
			value2 = DataHandler.GetGUIPropMap("NavStation");
			coDevice.mapGUIPropMaps["Panel A"] = value2;
		}
		foreach (KeyValuePair<string, string> item in value)
		{
			if (item.Key.IndexOf("Contact_") == 0)
			{
				coDevice.mapGUIPropMaps["Panel A"][item.Key] = item.Value;
			}
		}
	}

	private static void RevealStartingVessels(CondOwner coDevice)
	{
		if (coDevice == null || !coDevice.HasCond("IsReadyNAVReveals"))
		{
			return;
		}
		coDevice.ZeroCondAmount("IsReadyNAVReveals");
		if (coDevice.ship == null || coDevice.ship.DMGStatus == Ship.Damage.New)
		{
			return;
		}
		if (!coDevice.mapGUIPropMaps.TryGetValue("Panel A", out var value))
		{
			value = DataHandler.GetGUIPropMap("NavStation");
			coDevice.mapGUIPropMaps["Panel A"] = value;
		}
		foreach (Ship allLoadedShip in CrewSim.system.GetAllLoadedShips())
		{
			if (!(MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) > 0.1))
			{
				ShipInfo.SetShipInfo(new ShipInfo(allLoadedShip, bForceReveal: true), value);
			}
		}
	}

	public static bool IsOpen()
	{
		if (Instance != null)
		{
			return !Instance.IsPDANav;
		}
		return false;
	}

	public CondOwner COSelfBase()
	{
		return base.COSelf;
	}
}
