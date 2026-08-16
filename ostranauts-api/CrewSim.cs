using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Core;
using Ostranauts;
using Ostranauts.ArenaMode;
using Ostranauts.Condowner;
using Ostranauts.Core;
using Ostranauts.Core.Models;
using Ostranauts.Events;
using Ostranauts.InputControl;
using Ostranauts.Inventory;
using Ostranauts.Objectives;
using Ostranauts.Racing;
using Ostranauts.ShipGUIs.Utilities;
using Ostranauts.Ships;
using Ostranauts.Ships.AIPilots;
using Ostranauts.Ships.Comms;
using Ostranauts.Ships.LayoutGenerator;
using Ostranauts.Social.Models;
using Ostranauts.Systems;
using Ostranauts.TargetVisualization;
using Ostranauts.Tools.ExtensionMethods;
using Ostranauts.Trading;
using Ostranauts.UI.CrewBar;
using Ostranauts.UI.Loading;
using Ostranauts.UI.MegaToolTip;
using Ostranauts.UI.Quickbar.Models;
using Ostranauts.UI.ShipEdit;
using Ostranauts.Utils;
using Ostranauts.Utils.Models;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Events;
using UnityEngine.SceneManagement;
using UnityEngine.Serialization;
using UnityEngine.UI;
using Vectrosity;

public class CrewSim : MonoBehaviour
{
	public static OnTileSelectionEvent OnTileSelectionUpdated;

	public static RefreshTooltipEvent RefreshTooltipEvent = new RefreshTooltipEvent();

	public static UnityEvent OnSceneFinishedLoading = new UnityEvent();

	public static UnityEvent OnGameFinishedLoading = new UnityEvent();

	public static UnityEvent OnGameEnd = new UnityEvent();

	public static UnityEvent OnTimeScaleUpdated = new UnityEvent();

	public const float M_PER_TILE = 0.32f;

	public const float PRESSURE_ATMOSPHERIC = 101.3f;

	public const float GAS_CONSTANT = 0.008314f;

	public const float TILE_VOLUME = 0.25599998f;

	public const float KM_PER_AU = 149597870f;

	public const float M_PER_AU = 1.4959786E+11f;

	public const float AU_PER_M = 6.684587E-12f;

	public const float MOS_PER_YEAR = 12f;

	public const float DAYS_PER_YEAR = 360f;

	public const float SEC_PER_YEAR = 31556926f;

	public const float SEC_PER_DAY = 87658.125f;

	public const float GRAV_CONSTANT = 6.67408E-11f;

	public const float DOCKING_RANGE = 3.3422936E-08f;

	public const float SIGNALBEACON_RANGE = 1.0026881E-05f;

	public const float NO_WAKE_ZONE_RANGE = 2.005376E-06f;

	public const float CLOSE_APPROACH_RANGE = 3.3422937E-05f;

	public const double DOCKING_CLAMP_RANGE_COEFF = 1.1;

	public const double DOCKING_PUSHBACK_V = 3.34229345588799E-11;

	public const double ATC_SPEED_LIMIT = 5.013440329548757E-09;

	public const double LIGHT_SPEED = 0.0020039887409959503;

	public const double DEEP_SPACE_SPEED_LIMIT = 0.00020039887409959505;

	public const double MIN_TORCH_SPEED_LIMIT = 1E-08;

	public const double AI_SAFE_ACCEL_LIMIT = 2.9;

	public const double TEMPERATURE_BACKGROUND = 2.725480079650879;

	public const float EARTH_G = 9.81f;

	public const float MICRO_G = 1E-05f;

	public const string HOMEWORLD_LOOT_PREFIX = "HW_";

	public const string DEFAULT_STAR_SYSTEM_LOOT = "TXTDefaultStarSystem";

	private static Loot _lootDefaultStarSystem;

	private Coroutine _bulkSaver;

	public static CrewSim objInstance;

	public static float fTotalGameSec;

	public static float fTotalGameSecUnscaled;

	public static float fTotalGameSecSession;

	private static float fTimeCoeffPause;

	public static bool bRaiseUI;

	public static bool ZoneMenuOpen = false;

	private static bool _bPauseLock;

	public static bool bUILock;

	public static int nRetogglePwr;

	public static JsonShip jsonShip;

	public static GUISaveIndicator objGUISaveIndicator;

	public static Toggle objGUISaveOnClose;

	private static TMP_Text txtDebug1;

	private static TMP_Text txtDebug2;

	private static TMP_Text txtDebug3;

	private static TMP_Text txtBeatLogs;

	private static TMP_Text txtPlotLogs;

	private static TMP_Text txtDialogue;

	private static RectTransform rectRotate;

	private static CanvasGroup cgRotate;

	private static Text txtQueue;

	private static Text txtPriorities;

	private static Text txtAnim;

	private static TMP_Text txtMessageLog;

	private static Tooltippable2 toolMessageLog;

	private static Toggle chkAutoPause;

	private static Toggle chkAIAuto;

	private static ToggleGroup tgMenu;

	private static Button btnCPLeft;

	private static Button btnCPRight;

	private static Button btnCPTop;

	private static Button btnCPBottom;

	private static Button btnCPExit;

	public static List<CondOwner> aSelected;

	public static List<CondOwner> aCrew;

	private Visibility visPlayer;

	public static GameObject goSun;

	public static HashSet<Visibility> aLights;

	public static HashSet<Block> blocks;

	private static GameObject goCrewBar;

	private static GameObject goCrewBarPortraitButton;

	public static GameObject goUI;

	private static GameObject goCanvasGUI;

	public static GameObject goIntUIPanel;

	private static GameObject goDialogue;

	private static GameObject goBtnDebugTemplate;

	private static Transform tfGUIInputsContent;

	private static Transform tfDialogContent;

	private static Transform tfCondContent;

	public static Ship shipPlayerOwned;

	private static List<Ship> aLoadedShips;

	public static StarSystem system;

	public static CondOwner coPlayer;

	public static VFXGasPuffs vfxPuffs;

	public static VFXSparks vfxSparks;

	public static VFXFire vfxFire;

	public static VFXSmoke vfxSmoke;

	private static CondOwner coCamCenter;

	private static bool bWarnedShipEdit;

	public static bool bShipEdit;

	public static bool bShipEditTest;

	public static bool bShipEditHide = false;

	public static bool bShipEditBG = false;

	public static bool bDebugFightMode;

	public static bool bDebugShow = false;

	public static bool bJustClickedInput;

	public static bool bPoolVisUpdates;

	public static bool bPoolShipUpdates;

	public static bool bContinuePaintingJob = true;

	public static Interaction iaItmInstall;

	public static JsonInstallable jiLast;

	private static UniqueList<CondOwner> aTickers;

	private static List<CondOwner> aTickersTemp;

	public static GUIInventory inventoryGUI;

	public static GUIPDA guiPDA;

	public static List<Pathfinder> pathfinders;

	private static bool bTyping;

	public static string strSaveVersion;

	public static List<string> aPatchesApplied;

	public static int[] aSaveVersion;

	public static bool bSaveUsesOldContainerGrids;

	public static bool bSaveHasENCPoliceBoard;

	public static bool bSaveHasCondRuleDupes;

	public static bool bSaveHasMissingPledgeUs;

	public static bool bSaveHasMissingPledgePayloads;

	public static bool bIsQuickstartSession;

	public static MeatState eMeatState = MeatState.Dormant;

	public static bool bUnpauseShield;

	public static double fPauseFlashExtra;

	private static CondTrigger _ctDockSys;

	private static CondTrigger _ctDockingRef;

	private static CondTrigger _ctShipEditSelect;

	private static CondTrigger _ctTrafficRefreshable;

	private bool bcombatAutoPauseAllowed = true;

	private static Ostranauts.Core.Models.Tuple<double, string> tplAutoPause;

	private Vector3 vMouse;

	private Vector3 vPanVelocity = new Vector3(0f, 0f, 0f);

	private GameObject goShipEdit;

	public GameObject goSelPart;

	public GameObject goPaintJob;

	private List<GameObject> aFields;

	private List<CondRule> aMutedCRs;

	public ContextMenuPool contextMenuPool;

	private ScrollRect srMessageLog;

	public CODicts coDicts;

	public WorkManager workManager;

	public static CanvasManager CanvasManager;

	public static int resolutionX;

	public static int resolutionY;

	public bool checkResolution;

	public GameObject tooltipGO;

	public GUITooltip tooltip;

	public CrewSimTut CrewSimTut;

	public bool bHasSeenRosterTutorial;

	public GUILetterbox LetterboxTop;

	public GUILetterbox LetterboxBottom;

	private float fCamSpeed = 7f;

	private float fUIUpdateHeartbeat = 1f;

	private float fUIUpdateLast;

	public float RightMouseButtonDownTimer;

	public float RightMouseButtonDownMax = 0.5f;

	public bool bRaisedMenuThisFrame;

	private int nLastClickIndex;

	private Vector2 vLastClick;

	private Vector3 vLastMouse;

	public Vector3 vDragStart;

	public Vector3 vDragStartScreen;

	[SerializeField]
	private GUICursorRoundel cursorRoundel;

	[SerializeField]
	private GameObject _loadingPrefab;

	[SerializeField]
	private GameObject _confirmationDialoguePrefab;

	public SteamAchievementManager achievementManager;

	public Camera camMain;

	public Camera UICamera;

	public Camera camHighlight;

	public Camera ScreenShotCam;

	public Camera ActiveCam;

	public VHSPostProcessEffect vhs;

	private Vector3 camTravel = new Vector3(0f, 0f, 0f);

	private float camTravelVelocity;

	public bool camFollow;

	public CameraFocusZoom camZoom;

	private float fShakeRaw;

	[NonSerialized]
	public float fShakeUserPref = 1f;

	private Vector3 vShake;

	private List<string> aHidden;

	private VectorLine lineSignal;

	private VectorLine linePower;

	private VectorLine linePowerOff;

	private VectorLine lineSelectRect;

	private CondOwner coConnectLastCrew;

	public CondOwner coConnectMode;

	private CondTrigger ctSelectFilter;

	private GUIData igdConnectMode;

	public static Ostranauts.Core.Models.Tuple<string, CondOwner> tplCurrentUI;

	public static Ostranauts.Core.Models.Tuple<string, CondOwner> tplLastUI;

	private GameObject goStatus;

	private CanvasGroup cgPause;

	public static CanvasGroup cgGameOverShipEdit;

	public static TrailRenderer BulletTrail;

	private static Texture2D[] aCursors;

	private static int nCursor = -1;

	private bool _finishedLoading;

	public static bool bDebug01 = false;

	public static bool bDebug02 = false;

	public static bool bDebug03 = false;

	public static bool bDebug04 = false;

	public static bool bDebug05 = false;

	public static bool bSoakTest = false;

	public static string strDebugOut;

	public static int[] aReqVersion = new int[4] { 1, 0, 0, 0 };

	public static Dictionary<string, int> dictGetCOCounts = new Dictionary<string, int>();

	public static bool chargenOnNewGame;

	public static bool tutorialOnNewGame;

	public static bool PowerVizVisible;

	public float delX;

	public float delY;

	public float delZ;

	[SerializeField]
	private CanvasGroup LoadFailure;

	private readonly string[] _layerMaskDefLosTileHelpers = new string[4] { "Default", "LoS", "Tile Helpers", "Placeholder" };

	private readonly string[] _layerMaskTileHelpers = new string[1] { "Tile Helpers" };

	private readonly string[] _layerMaskDefTileHelpers = new string[2] { "Default", "Tile Helpers" };

	private readonly string[] _layerMaskDefault = new string[1] { "Default" };

	private List<CondOwner> _highlightOnHoverCos = new List<CondOwner>();

	public static List<Animator> COAnimators = new List<Animator>();

	[Header("AI Ship Debugging")]
	public bool EnableAIShipOutput;

	[FormerlySerializedAs("AIRegID")]
	public string[] AIRegIDs;

	private IInputCommand _commandQuickMove;

	private IInputCommand _commandEyedropper;

	private IInputCommand _commandZoneAlternate;

	private IInputCommand _commandEscape;

	private IInputCommand _commandSingleItem;

	private IInputCommand _commandPanSlower;

	private IInputCommand _commandPanFaster;

	private IInputCommand _commandPanCameraUp;

	private IInputCommand _commandPanCameraDown;

	private IInputCommand _commandPanCameraLeft;

	private IInputCommand _commandPanCameraRight;

	private IInputCommand _commandZoomIn;

	private IInputCommand _commandZoomOut;

	private IInputCommand _commandClick;

	private IInputCommand _commandRightClick;

	private IInputCommand _commandMiddleClick;

	private IInputCommand _commandScroll;

	private IInputCommand _commandForceWalk;

	public static OnMouseDownEvent OnLeftClick = new OnMouseDownEvent();

	public static OnMouseDownEvent OnRightClick = new OnMouseDownEvent();

	public static bool bEnableDebugCommands = false;

	private static string sDebugCode = "UNLOCKDEBUG";

	private static int nDebugIndex;

	private static Dictionary<string, CondOwner> dictCOConts;

	private static Loot LootDefaultStarSystem
	{
		get
		{
			if (_lootDefaultStarSystem == null)
			{
				_lootDefaultStarSystem = DataHandler.GetLoot("TXTDefaultStarSystem");
			}
			return _lootDefaultStarSystem;
		}
	}

	public static bool bPauseLock
	{
		get
		{
			return _bPauseLock;
		}
		set
		{
			_bPauseLock = value;
		}
	}

	private static CondTrigger CTDockSys
	{
		get
		{
			if (_ctDockSys == null)
			{
				_ctDockSys = DataHandler.GetCondTrigger("TIsDockSys");
			}
			return _ctDockSys;
		}
	}

	private static CondTrigger CTDockingRef
	{
		get
		{
			if (_ctDockingRef == null)
			{
				_ctDockingRef = DataHandler.GetCondTrigger("TIsDockingRef");
			}
			return _ctDockingRef;
		}
	}

	private static CondTrigger CTShipEditSelect
	{
		get
		{
			if (_ctShipEditSelect == null)
			{
				_ctShipEditSelect = DataHandler.GetCondTrigger("TIsShipEditSelect");
			}
			return _ctShipEditSelect;
		}
	}

	private static CondTrigger CTTrafficRefreshable
	{
		get
		{
			if (_ctTrafficRefreshable == null)
			{
				_ctTrafficRefreshable = DataHandler.GetCondTrigger("TIsTrafficRefreshable");
			}
			return _ctTrafficRefreshable;
		}
	}

	private float fShakeAmp
	{
		get
		{
			return fShakeRaw * fShakeUserPref;
		}
		set
		{
			fShakeRaw = value;
		}
	}

	public bool FinishedLoading => _finishedLoading;

	public static bool Paused
	{
		get
		{
			return fTimeCoeffPause == 0f;
		}
		set
		{
			if (coPlayer != null)
			{
				coPlayer.ZeroCondAmount("TutorialPauseWaiting");
				MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(coPlayer.strID);
			}
			if (bPauseLock)
			{
				OnTimeScaleUpdated.Invoke();
				return;
			}
			fTimeCoeffPause = (value ? 0f : 1f);
			Time.timeScale = MathUtils.Clamp(Time.timeScale, 0.25f, 16f);
			OnTimeScaleUpdated.Invoke();
			foreach (Animator cOAnimator in COAnimators)
			{
				if (!(cOAnimator == null))
				{
					cOAnimator.enabled = !value;
				}
			}
			if (Math.Abs(tplAutoPause.Item1 - StarSystem.fEpoch) <= 0.75)
			{
				tplAutoPause.Item1 = 0.0;
				tplAutoPause.Item2 = null;
			}
		}
	}

	public static bool Typing
	{
		get
		{
			return bTyping;
		}
		set
		{
			bTyping = value;
		}
	}

	public static Ship shipCurrentLoaded
	{
		get
		{
			if (GetSelectedCrew() != null && GetSelectedCrew().ship != null)
			{
				return GetSelectedCrew().ship;
			}
			if (aLoadedShips != null && aLoadedShips.Count > 0)
			{
				return aLoadedShips[0];
			}
			return null;
		}
	}

	public Camera SwitchActiveCamera(bool useMainCam)
	{
		if (useMainCam)
		{
			ActiveCam = camMain;
			ScreenShotCam.gameObject.SetActive(value: false);
		}
		else
		{
			ScreenShotCam.gameObject.SetActive(value: true);
			ActiveCam = ScreenShotCam;
		}
		return ActiveCam;
	}

	private void Awake()
	{
		if (OnTileSelectionUpdated == null)
		{
			OnTileSelectionUpdated = new OnTileSelectionEvent();
		}
		GameObject gameObject = GameObject.Find("Canvas LoadFail (DeleteOnLoad)");
		if (gameObject != null)
		{
			LoadFailure = gameObject.GetComponent<CanvasGroup>();
		}
		if (LoadFailure != null)
		{
			CanvasManager.ShowCanvasGroup(LoadFailure);
		}
		if (Application.isEditor)
		{
			bEnableDebugCommands = true;
		}
		aCursors = new Texture2D[3];
		aCursors[0] = Resources.Load<Texture2D>("Sprites/GUICursor01");
		aCursors[1] = Resources.Load<Texture2D>("Sprites/GUICursor01Feet");
		aCursors[2] = Resources.Load<Texture2D>("Sprites/GUICursor01Hand");
		SetCursor(0);
		AudioManager.am.FadeOutMusic(2f);
		objInstance = this;
		bShipEditTest = false;
		aLoadedShips = new List<Ship>();
		strDebugOut = "";
		coPlayer = null;
		fTotalGameSec = 0f;
		fTotalGameSecUnscaled = 0f;
		fTotalGameSecSession = 0f;
		nLastClickIndex = 0;
		vLastClick = new Vector2(1000f, 1000f);
		ResetTimeScale();
		fTimeCoeffPause = 1f;
		aHidden = new List<string>();
		aFields = new List<GameObject>();
		aSelected = new List<CondOwner>();
		blocks = new HashSet<Block>();
		goSun = new GameObject("LightsSuns");
		goSun.transform.SetParent(GameObject.Find("PlayState").transform, worldPositionStays: false);
		aLights = new HashSet<Visibility>();
		aTickers = new UniqueList<CondOwner>();
		aTickersTemp = new List<CondOwner>();
		pathfinders = new List<Pathfinder>();
		tplAutoPause = new Ostranauts.Core.Models.Tuple<double, string>();
		coDicts = base.gameObject.AddComponent<CODicts>();
		base.gameObject.AddComponent<CoHighlighter>();
		Debug.Log("Initializing Crewsim Canvasmanager");
		UICamera = GameObject.Find("UI Camera").GetComponent<Camera>();
		vhs = UICamera.GetComponent<VHSPostProcessEffect>();
		if (vhs != null)
		{
			vhs.enabled = false;
		}
		CanvasManager = base.gameObject.AddComponent<CanvasManager>();
		CanvasManager.instance = CanvasManager;
		CanvasManager.Init();
		fShakeUserPref = PlayerPrefs.GetFloat("ScreenShakeMod", 1f);
		Debug.Log("Initializing Crewsim inventory gui");
		inventoryGUI = CanvasManager.goCanvasInventory.GetComponent<GUIInventory>();
		Debug.Log("Initializing Crewsim visibility");
		Visibility.visTemplate = ((GameObject)Resources.Load("LoS")).GetComponent<Visibility>();
		visPlayer = UnityEngine.Object.Instantiate(Visibility.visTemplate, base.transform);
		visPlayer.GO.layer = LayerMask.NameToLayer("LoS");
		visPlayer.Radius = 20f;
		visPlayer.LightColor = Color.black;
		visPlayer.tfParent = base.transform;
		vfxPuffs = base.transform.Find("vfxGasPuffs").GetComponent<VFXGasPuffs>();
		vfxSparks = base.transform.Find("vfxSparksRoot").GetComponent<VFXSparks>();
		vfxFire = base.transform.Find("vfxFireRoot").GetComponent<VFXFire>();
		vfxSmoke = base.transform.Find("vfxSmokePuffs").GetComponent<VFXSmoke>();
		GameObject gameObject2 = Resources.Load("vfxBulletTrail") as GameObject;
		if (gameObject2 != null)
		{
			BulletTrail = gameObject2.GetComponent<TrailRenderer>();
		}
		Debug.Log("Initializing crewsim transforms");
		goCrewBar = CanvasManager.goCanvasCrewBar.transform.Find("GUICrewStatus").gameObject;
		goCrewBarPortraitButton = goCrewBar.transform.Find("btnInvBig").gameObject;
		goCrewBarPortraitButton.GetComponent<Button>().onClick.AddListener(delegate
		{
			if (!bRaiseUI)
			{
				CommandInventory.ToggleInventory(GetSelectedCrew());
			}
			CamCenter(GetSelectedCrew());
		});
		goIntUIPanel = CanvasManager.goCanvasControlPanels.transform.Find("pnlInteractionNav/pnlInteractionUI").gameObject;
		GameObject gameObject3 = GameObject.Find("Main Camera");
		camZoom = gameObject3.GetComponent<CameraFocusZoom>();
		btnCPExit = CanvasManager.goCanvasControlPanels.transform.Find("pnlInteractionNav/btnUIExit").GetComponent<Button>();
		btnCPExit.onClick.AddListener(delegate
		{
			bJustClickedInput = true;
			LowerUI(tplCurrentUI != null && tplCurrentUI.Item1 == "FFWD" && tplLastUI != null && tplLastUI.Item1 != "FFWD");
		});
		AudioManager.AddBtnAudio(btnCPExit.gameObject, "ShipUIBtnPanelSwitchIn", "ShipUIBtnPanelSwitchOut");
		btnCPTop = CanvasManager.goCanvasControlPanels.transform.Find("pnlInteractionNav/btnUIUp").GetComponent<Button>();
		btnCPTop.onClick.AddListener(delegate
		{
			SwitchUI("strGUIPrefabTop");
		});
		AudioManager.AddBtnAudio(btnCPTop.gameObject, "ShipUIBtnPanelSwitchIn", "ShipUIBtnPanelSwitchOut");
		btnCPBottom = CanvasManager.goCanvasControlPanels.transform.Find("pnlInteractionNav/btnUIDn").GetComponent<Button>();
		btnCPBottom.onClick.AddListener(delegate
		{
			SwitchUI("strGUIPrefabBottom");
		});
		AudioManager.AddBtnAudio(btnCPBottom.gameObject, "ShipUIBtnPanelSwitchIn", "ShipUIBtnPanelSwitchOut");
		btnCPLeft = CanvasManager.goCanvasControlPanels.transform.Find("pnlInteractionNav/btnUILeft").GetComponent<Button>();
		btnCPLeft.onClick.AddListener(delegate
		{
			SwitchUI("strGUIPrefabLeft");
		});
		AudioManager.AddBtnAudio(btnCPLeft.gameObject, "ShipUIBtnPanelSwitchIn", "ShipUIBtnPanelSwitchOut");
		btnCPRight = CanvasManager.goCanvasControlPanels.transform.Find("pnlInteractionNav/btnUIRight").GetComponent<Button>();
		btnCPRight.onClick.AddListener(delegate
		{
			SwitchUI("strGUIPrefabRight");
		});
		AudioManager.AddBtnAudio(btnCPRight.gameObject, "ShipUIBtnPanelSwitchIn", "ShipUIBtnPanelSwitchOut");
		Debug.Log("Initializing Crewsim Auto Button");
		chkAIAuto = goCrewBar.transform.Find("pnlControlButtons/AutoTask/chkAutoTask").GetComponent<Toggle>();
		chkAIAuto.onValueChanged.AddListener(ToggleAutotask);
		AudioManager.AddBtnAudio(chkAIAuto.gameObject, "ShipUIBtnReactorCoilFwdIn", "ShipUIBtnReactorCoilFwdOut");
		camMain = gameObject3.GetComponent<Camera>();
		CamZoom(1f);
		vShake = default(Vector3);
		camHighlight = gameObject3.transform.Find("HighlightCam").GetComponent<Camera>();
		ScreenShotCam = GameObject.Find("ScreenshotCam").GetComponent<Camera>();
		ScreenShotCam.gameObject.SetActive(value: false);
		TMP_Text component = CanvasManager.goCanvasGUI.transform.Find("txtVersion").GetComponent<TMP_Text>();
		if (IntPtr.Size == 8)
		{
			component.text = DataHandler.strBuild;
		}
		else
		{
			component.text = DataHandler.strBuild + " (32)";
		}
		Debug.Log("Initializing Crewsim Debug Canvas");
		txtAnim = CanvasManager.goCanvasDebug.transform.Find("pnlAnim/txt").GetComponent<Text>();
		txtQueue = CanvasManager.goCanvasDebug.transform.Find("pnlQueue/txt").GetComponent<Text>();
		txtPriorities = CanvasManager.goCanvasDebug.transform.Find("pnlPriorities/txt").GetComponent<Text>();
		txtDebug1 = CanvasManager.goCanvasDebug.transform.Find("scrDebug1/Viewport/Content").GetComponent<TMP_Text>();
		txtDebug2 = CanvasManager.goCanvasDebug.transform.Find("scrDebug2/Viewport/Content").GetComponent<TMP_Text>();
		txtDebug3 = CanvasManager.goCanvasDebug.transform.Find("scrDebug3/Viewport/Content").GetComponent<TMP_Text>();
		rectRotate = CanvasManager.goCanvasGUI.transform.Find("bmpRotate").GetComponent<RectTransform>();
		cgRotate = rectRotate.GetComponent<CanvasGroup>();
		RectTransform component2 = CanvasManager.goCanvasDebug.transform.Find("pnlBtnList/scrollMask/pnlContent").GetComponent<RectTransform>();
		goBtnDebugTemplate = Resources.Load("CrewSimScene/btnDebugAction") as GameObject;
		Button component3 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component3.onClick.AddListener(delegate
		{
			DebugGiveMoney();
		});
		component3.GetComponentInChildren<TMP_Text>().text = "Give Money";
		Button component4 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component4.onClick.AddListener(delegate
		{
			BeatManager.bLogging = !BeatManager.bLogging;
			txtBeatLogs.text = $"Beat Logs: {BeatManager.bLogging}";
		});
		txtBeatLogs = component4.GetComponentInChildren<TMP_Text>();
		txtBeatLogs.text = $"Beat Logs: {BeatManager.bLogging}";
		Button component5 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component5.onClick.AddListener(delegate
		{
			PlotManager.bDebugLogging = !PlotManager.bDebugLogging;
			txtPlotLogs.text = $"Plot Logs: {PlotManager.bDebugLogging}";
		});
		txtPlotLogs = component5.GetComponentInChildren<TMP_Text>();
		txtPlotLogs.text = $"Plot Logs: {PlotManager.bDebugLogging}";
		Button component6 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component6.onClick.AddListener(delegate
		{
			DebugCheckJsons();
		});
		component6.GetComponentInChildren<TMP_Text>().text = "Json Audit";
		Button component7 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component7.onClick.AddListener(delegate
		{
			BeatManager.DebugPirate();
		});
		component7.GetComponentInChildren<TMP_Text>().text = "Spawn Pirate";
		Button component8 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component8.onClick.AddListener(delegate
		{
			AIShipManager.CheckLocalAuthorityScenario();
		});
		component8.GetComponentInChildren<TMP_Text>().text = "Spawn Police";
		Button component9 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component9.onClick.AddListener(delegate
		{
			BeatManager.DebugClobber();
		});
		component9.GetComponentInChildren<TMP_Text>().text = "Clobber";
		Button component10 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component10.onClick.AddListener(delegate
		{
			StarSystem.SpawnMicroMeteoroid(shipCurrentLoaded, 1f, (double)Time.timeScale > 1.0);
		});
		component10.GetComponentInChildren<TMP_Text>().text = "Mmoid";
		Button component11 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component11.onClick.AddListener(delegate
		{
			Debug.Log("Parts Value: " + shipCurrentLoaded.GetPartsValue());
		});
		component11.GetComponentInChildren<TMP_Text>().text = "Parts Value";
		Button component12 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component12.onClick.AddListener(delegate
		{
			coPlayer.ZeroCondAmount("TutorialNoPlotsCooldown");
			coPlayer.ZeroCondAmount("TutorialZonesNoDorm");
			coPlayer.ZeroCondAmount("IsTensionCooldown");
			BeatManager.GenerateTension();
		});
		component12.GetComponentInChildren<TMP_Text>().text = "Tension";
		Button component13 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component13.onClick.AddListener(delegate
		{
			coPlayer.ZeroCondAmount("TutorialNoPlotsCooldown");
			coPlayer.ZeroCondAmount("TutorialZonesNoDorm");
			coPlayer.ZeroCondAmount("IsReleaseCooldown");
			BeatManager.GenerateRelease();
		});
		component13.GetComponentInChildren<TMP_Text>().text = "Release";
		Button component14 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component14.onClick.AddListener(delegate
		{
			DebugFloorUseAudit();
		});
		component14.GetComponentInChildren<TMP_Text>().text = "Floors Audit";
		Button component15 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component15.onClick.AddListener(delegate
		{
			DebugRefreshPlayerStats(GetSelectedCrew());
		});
		component15.GetComponentInChildren<TMP_Text>().text = "Player Comfort";
		Button component16 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component16.onClick.AddListener(delegate
		{
			DebugReportCauseOfDeath();
		});
		component16.GetComponentInChildren<TMP_Text>().text = "Death Report";
		Button component17 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component17.onClick.AddListener(delegate
		{
			DebugListCOContainers();
		});
		component17.GetComponentInChildren<TMP_Text>().text = "Container Audit";
		Button component18 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component18.onClick.AddListener(delegate
		{
			DebugDCAudit();
		});
		component18.GetComponentInChildren<TMP_Text>().text = "DC Audit";
		Button component19 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component19.onClick.AddListener(delegate
		{
			GetSelectedCrew().DebugFixOldCondRules(bOnlyReport: false);
		});
		component19.GetComponentInChildren<TMP_Text>().text = "DC Fix Selected";
		Button component20 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component20.onClick.AddListener(delegate
		{
			AIShipManager.DebugAuditTransits();
		});
		component20.GetComponentInChildren<TMP_Text>().text = "Audit Transits";
		Button component21 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component21.onClick.AddListener(delegate
		{
			coPlayer.DebugAuditMass("", Input.GetKey(KeyCode.LeftShift));
		});
		component21.GetComponentInChildren<TMP_Text>().text = "Audit Player Mass";
		Button component22 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component22.onClick.AddListener(delegate
		{
			JsonPersonSpec jsonPersonSpec = new JsonPersonSpec
			{
				strCareerNow = "LEOfficer"
			};
			foreach (Ship allLoadedShip in system.GetAllLoadedShips())
			{
				foreach (CondOwner person in allLoadedShip.GetPeople(bAllowDocked: false))
				{
					if (person.pspec != null && jsonPersonSpec.Matches(person))
					{
						Debug.Log(allLoadedShip.strRegID + " has LEO from " + person.pspec.strHomeworldNow + " " + string.Join(',', person.pspec.GetCO().GetAllFactions()));
					}
				}
			}
		});
		component22.GetComponentInChildren<TMP_Text>().text = "Find LEOs";
		Button component23 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component23.onClick.AddListener(delegate
		{
			Debug.Log(GetSelectedCrew().strID + " tickers: " + GetSelectedCrew().GetDebugTickers());
		});
		component23.GetComponentInChildren<TMP_Text>().text = "Log Tickers";
		Button component24 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component24.onClick.AddListener(delegate
		{
			foreach (Ship allLoadedShip2 in system.GetAllLoadedShips())
			{
				foreach (CondOwner person2 in allLoadedShip2.GetPeople(bAllowDocked: false))
				{
					string text = person2.strID + ":";
					double condAmount = person2.GetCondAmount("ThreshStatAchievement");
					text = text + "\tAch: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatAltruism");
					text = text + "\tAlt: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatAutonomy");
					text = text + "\tAut: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatContact");
					text = text + "\tCon: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatEsteem");
					text = text + "\tEst: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatFamily");
					text = text + "\tFam: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatIntimacy");
					text = text + "\tInt: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatMeaning");
					text = text + "\tMea: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatPrivacy");
					text = text + "\tPri: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatSecurity");
					text = text + "\tSec: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					condAmount = person2.GetCondAmount("ThreshStatSelfRespect");
					text = text + "\tSel: " + ((condAmount > 3.0) ? "<color=red>" : "") + condAmount.ToString("N2") + ((condAmount > 3.0) ? "</color>" : "");
					Debug.Log(text);
				}
			}
		});
		component24.GetComponentInChildren<TMP_Text>().text = "Report Thresh";
		Button component25 = UnityEngine.Object.Instantiate(goBtnDebugTemplate, component2).GetComponent<Button>();
		component25.onClick.AddListener(delegate
		{
			MathUtils.GetPushbackVector(shipCurrentLoaded.objSS, system.GetShipByRegID("OKLG").objSS);
		});
		component25.GetComponentInChildren<TMP_Text>().text = "Log Tickers";
		txtDialogue = (Resources.Load("txtDialogue") as GameObject).GetComponent<TMP_Text>();
		txtMessageLog = goCrewBar.transform.Find("pnlMessageScroll/Viewport/txt").GetComponent<TMP_Text>();
		toolMessageLog = goCrewBar.transform.Find("pnlMessageScroll").GetComponent<Tooltippable2>();
		srMessageLog = goCrewBar.transform.Find("pnlMessageScroll").GetComponent<ScrollRect>();
		goShipEdit = CanvasManager.goCanvasShipEdit.transform.Find("ShipEdit").gameObject;
		tgMenu = CanvasManager.goCanvasGUI.GetComponent<ToggleGroup>();
		guiPDA = CanvasManager.goCanvasPDA.transform.Find("GUIPDA2").GetComponent<GUIPDA>();
		guiPDA.Init();
		Debug.Log("Initializing Crewsim Data Canvas");
		chkAutoPause = goCrewBar.transform.Find("pnlControlButtons/AutoPause/chkAutoPause").GetComponent<Toggle>();
		chkAutoPause.onValueChanged.AddListener(delegate(bool isOn)
		{
			bcombatAutoPauseAllowed = isOn;
		});
		Debug.Log("Initializing Crewsim Quit Menu");
		Button component26 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/btnCancel").GetComponent<Button>();
		component26.onClick.AddListener(delegate
		{
			CanvasManager.Invoke("HideCanvasQuit", 0.01f);
		});
		AudioManager.AddBtnAudio(component26.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		Button component27 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlMain/btnQuit").GetComponent<Button>();
		component27.onClick.AddListener(delegate
		{
			PopupQuitToMenu();
		});
		AudioManager.AddBtnAudio(component27.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		Button component28 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlMain/btnShipEdit").GetComponent<Button>();
		component28.onClick.AddListener(delegate
		{
			PopupQuitToShipEdit();
		});
		AudioManager.AddBtnAudio(component28.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		Button component29 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlMain/btnClose").GetComponent<Button>();
		component29.onClick.AddListener(delegate
		{
			PopupQuitToDesktop();
		});
		AudioManager.AddBtnAudio(component29.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		Button component30 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlMain/btnSave").GetComponent<Button>();
		component30.onClick.AddListener(delegate
		{
			MonoSingleton<LoadManager>.Instance.ShowSaveMenu(CanvasManager.goCanvasQuit.transform.Find("GUIQuit"));
		});
		AudioManager.AddBtnAudio(component30.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		objGUISaveIndicator = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlInfo/pnlTop").GetComponent<GUISaveIndicator>();
		objGUISaveOnClose = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlInfo/pnlBottom/Toggle").GetComponent<Toggle>();
		if (objGUISaveOnClose != null)
		{
			if (DataHandler.GetUserSettings() != null)
			{
				objGUISaveOnClose.isOn = DataHandler.GetUserSettings().bSaveOnClose;
			}
			objGUISaveOnClose.onValueChanged.AddListener(delegate(bool isOn)
			{
				if (DataHandler.GetUserSettings() != null)
				{
					DataHandler.GetUserSettings().bSaveOnClose = isOn;
					DataHandler.SaveUserSettings();
				}
			});
		}
		Button component31 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlMain/btnLoad").GetComponent<Button>();
		component31.onClick.AddListener(delegate
		{
			UnityEngine.Object.Instantiate(_loadingPrefab, CanvasManager.goCanvasQuit.transform);
		});
		AudioManager.AddBtnAudio(component31.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		Button component32 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlMain/btnOptions").GetComponent<Button>();
		component32.onClick.AddListener(Options);
		AudioManager.AddBtnAudio(component32.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		Button component33 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlLinks/btnManual").GetComponent<Button>();
		component33.onClick.AddListener(delegate
		{
			Manual();
		});
		AudioManager.AddBtnAudio(component33.gameObject, "ShipUIPaperRustle01", null);
		CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlLinks/btnManual/txt").GetComponent<TMP_Text>().text = DataHandler.GetString("GUI_QUIT_MANUAL");
		Button component34 = CanvasManager.goCanvasGameOver.transform.Find("GUIGameOver/btnQuit").GetComponent<Button>();
		component34.onClick.AddListener(delegate
		{
			QuitToMenu(bSave: false);
		});
		AudioManager.AddBtnAudio(component34.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		Button component35 = CanvasManager.goCanvasGameOver.transform.Find("GUIGameOver/btnShipEdit").GetComponent<Button>();
		component35.onClick.AddListener(delegate
		{
			QuitToShipEdit(bSave: false);
		});
		AudioManager.AddBtnAudio(component35.gameObject, "UIPauseBtnIn", "UIPauseBtnOut");
		cgGameOverShipEdit = CanvasManager.goCanvasGameOver.transform.Find("GUIGameOver/btnShipEdit").GetComponent<CanvasGroup>();
		Button component36 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlLinks/pnlSteam/btn").GetComponent<Button>();
		component36.onClick.AddListener(delegate
		{
			Application.OpenURL("https://steamcommunity.com/app/1022980/discussions/");
		});
		AudioManager.AddBtnAudio(component36.gameObject, "UIGameplayCash", "UIGameplayClick");
		Button component37 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlLinks/pnlDiscord/btn").GetComponent<Button>();
		component37.onClick.AddListener(delegate
		{
			Application.OpenURL("https://discord.gg/UxZg8Ur");
		});
		AudioManager.AddBtnAudio(component37.gameObject, "UIGameplayCash", "UIGameplayClick");
		CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlLinks/btnGuide").GetComponent<Button>().onClick.AddListener(delegate
		{
			Application.OpenURL("https://steamcommunity.com/sharedfiles/filedetails/?id=" + DataHandler.GetString("STEAM_GUIDE_ID"));
		});
		Button component38 = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlBG/pnlLinks/pnlPDFs/btn").GetComponent<Button>();
		component38.onClick.AddListener(delegate
		{
			try
			{
				Application.OpenURL(Application.streamingAssetsPath + "/images/manuals/");
			}
			catch (Exception ex)
			{
				Debug.Log(ex.Message + "\n" + ex.StackTrace.ToString());
			}
		});
		AudioManager.AddBtnAudio(component38.gameObject, "UIGameplayCash", "UIGameplayClick");
		TileUtils.goSelPartTiles = new GameObject("Selected Part Tiles");
		TileUtils.goPartTiles = new GameObject("Ship Part Tiles");
		TileUtils.aSelPartTiles = new List<Tile>();
		Debug.Log("Initializing Crewsim Ledger");
		Ledger.Init(null);
		GUIStationRefuel.SetPrices();
		Debug.Log("Initializing Crewsim Context Menu Pool");
		GameObject original = Resources.Load("prefabContextMenuPool") as GameObject;
		contextMenuPool = UnityEngine.Object.Instantiate(original, CanvasManager.goCanvasContextMenu.transform).GetComponent<ContextMenuPool>();
		contextMenuPool.name = "Context Menu Pool";
		cursorRoundel.fillSecondsMax = RightMouseButtonDownMax;
		cursorRoundel.ResetFill();
		Debug.Log("Initializing Crewsim GigManager");
		workManager = base.gameObject.AddComponent<WorkManager>();
		GigManager.Init();
		resolutionX = Screen.width;
		resolutionY = Screen.height;
		checkResolution = true;
		Debug.Log("Initializing Crewsim Tooltip");
		tooltipGO = Resources.Load("prefabTooltip") as GameObject;
		tooltipGO = UnityEngine.Object.Instantiate(tooltipGO, CanvasManager.instance.goCanvasGUI.transform);
		tooltip = tooltipGO.GetComponent<GUITooltip>();
		tooltip.window = GUITooltip.TooltipWindow.Hide;
		tooltip.tooltipCG.alpha = 0f;
		aMutedCRs = new List<CondRule>();
		cgPause = CanvasManager.canvasStackHolder.transform.Find("Canvas PopUp/bmpPause").GetComponent<CanvasGroup>();
		CanvasManager.HideCanvasGroup(cgPause);
		ActiveCam = camMain;
		if (LoadFailure != null)
		{
			CanvasManager.HideCanvasGroup(LoadFailure);
		}
		Debug.Log("Finished Initializing Crewsim");
		Info.instance.canvas.worldCamera = UICamera;
	}

	private void Start()
	{
		OnSceneFinishedLoading.Invoke();
		OnSceneFinishedLoading.RemoveAllListeners();
		_commandEyedropper = InputManager.GetCommand("Eyedropper");
		_commandQuickMove = InputManager.GetCommand("Quick Move Item");
		_commandZoneAlternate = InputManager.GetCommand("Zone Subtract");
		_commandEscape = InputManager.GetCommand("Cancel");
		_commandSingleItem = InputManager.GetCommand("Grab Singular");
		_commandPanFaster = InputManager.GetCommand("Pan camera faster");
		_commandPanSlower = InputManager.GetCommand("Pan camera slower");
		_commandPanCameraLeft = InputManager.GetCommand("Camera Left");
		_commandPanCameraRight = InputManager.GetCommand("Camera Right");
		_commandPanCameraUp = InputManager.GetCommand("Camera Up");
		_commandPanCameraDown = InputManager.GetCommand("Camera Down");
		_commandZoomIn = InputManager.GetCommand("Zoom Camera In");
		_commandZoomOut = InputManager.GetCommand("Zoom Camera Out");
		_commandClick = InputManager.GetCommand("Click");
		_commandRightClick = InputManager.GetCommand("RightClick");
		_commandMiddleClick = InputManager.GetCommand("MiddleClick");
		_commandScroll = InputManager.GetCommand("ScrollWheel");
		_commandForceWalk = InputManager.GetCommand("Force Walk");
	}

	private void AdvanceSim(float fDelta)
	{
		fTotalGameSec += fDelta * fTimeCoeffPause;
		UpdateICOs();
	}

	private void SetCursor(int nNew)
	{
		if (nCursor != nNew && nNew >= 0 && nNew < aCursors.Length)
		{
			Cursor.SetCursor(aCursors[nNew], new Vector2(0f, 0f), CursorMode.Auto);
			nCursor = nNew;
		}
	}

	private void Update()
	{
		if (!_finishedLoading)
		{
			return;
		}
		bool flag = ((!(fPauseFlashExtra > (double)Time.realtimeSinceStartup)) ? ((int)Time.realtimeSinceStartup % 2 == 0) : ((double)Time.realtimeSinceStartup % 0.4 > 0.2));
		if (tplAutoPause.Item1 > 0.0 && StarSystem.fEpoch <= tplAutoPause.Item1)
		{
			TriggerAutoPause(tplAutoPause.Item2);
			ResetAutoPause();
		}
		if (Paused)
		{
			if (flag && cgPause.alpha != 1f)
			{
				cgPause.alpha = 1f;
			}
			else if (!flag && cgPause.alpha != 0f)
			{
				cgPause.alpha = 0f;
			}
		}
		else if (cgPause.alpha != 0f)
		{
			cgPause.alpha = 0f;
		}
		if (GUIOptionSelect.bRaised || LoadFailure.interactable)
		{
			return;
		}
		fTotalGameSecUnscaled += Time.unscaledDeltaTime;
		fTotalGameSecSession += Time.unscaledDeltaTime;
		BeatManager.Update(Time.unscaledDeltaTime);
		KeyHandler();
		if (nRetogglePwr > 0)
		{
			nRetogglePwr--;
			if (nRetogglePwr == 0)
			{
				TogglePowerUI(shipCurrentLoaded);
			}
		}
		double fEpoch = StarSystem.fEpoch;
		double num = Time.deltaTime * fTimeCoeffPause;
		double num2 = num;
		while (num2 > 0.0)
		{
			double num3 = num2;
			if (aTickers.Count > 0 && aTickers.FirstOrDefault().fNextTickerSecs < num3)
			{
				num3 = aTickers.FirstOrDefault().fNextTickerSecs;
			}
			if (num3 < 0.004)
			{
				num3 = 0.004;
			}
			StarSystem.fEpoch += num3;
			AdvanceSim((float)num3);
			num2 -= num3;
		}
		StarSystem.fEpoch = fEpoch;
		if (system != null)
		{
			system.Update(num);
		}
		if (aSelected.Count == 1 && bDebugShow)
		{
			CondOwner condOwner = aSelected[0];
			txtAnim.text = "Anim State: " + condOwner.GetAnimState();
			txtQueue.text = condOwner.GetDebugQueue();
			txtPriorities.text = condOwner.GetDebugPriorities();
			string debugConds = aSelected[0].GetDebugConds(null);
			if (txtDebug2.text != debugConds)
			{
				txtDebug2.text = debugConds;
			}
			debugConds = "strID: " + aSelected[0].strID;
			debugConds = debugConds + "\nstrCODef: " + aSelected[0].strCODef;
			debugConds += "\nShip: ";
			debugConds += ((aSelected[0].ship != null) ? aSelected[0].ship.strRegID : "null");
			debugConds += "\nobjCOParent: ";
			debugConds += ((aSelected[0].objCOParent != null) ? ((object)aSelected[0].objCOParent) : ((object)"null"));
			if (txtDebug3.text != debugConds)
			{
				txtDebug3.text = debugConds;
			}
		}
		else
		{
			txtDebug2.text = "";
			txtDebug2.text = "Select Object";
		}
		if (lineSignal != null)
		{
			float scaleFactor = CanvasManager.goCanvasGUI.GetComponent<Canvas>().scaleFactor;
			Vector2 value = camMain.WorldToScreenPoint(coConnectMode.transform.position) / scaleFactor;
			Vector2 value2 = InputManager.MousePosition / scaleFactor;
			lineSignal.points2[0] = value;
			lineSignal.points2[1] = new Vector2(value2.x, value.y);
			lineSignal.points2[2] = value2;
			if (GetMouseOverCO(_layerMaskTileHelpers, ctSelectFilter).Count > 0)
			{
				lineSignal.textureScale = 1f;
				lineSignal.textureOffset = Time.time * 12f % 1f;
			}
			else
			{
				lineSignal.textureScale = 128f;
				lineSignal.textureOffset = 0f;
			}
			lineSignal.Draw();
		}
		if (linePower != null && shipCurrentLoaded != null)
		{
			linePower.points2.Clear();
			linePowerOff.points2.Clear();
			DrawPower(shipCurrentLoaded);
			foreach (Ship allDockedShip in shipCurrentLoaded.GetAllDockedShips())
			{
				DrawPower(allDockedShip);
			}
			linePower.textureScale = 1f;
			linePower.textureOffset = (0f - Time.realtimeSinceStartup) * 3f % 1f;
			linePower.Draw();
			linePowerOff.textureScale = 1f;
			linePowerOff.Draw();
		}
		Vector2 mousePosition = InputManager.MousePosition;
		if (lineSelectRect != null)
		{
			float scaleFactor2 = CanvasManager.goCanvasGUI.GetComponent<Canvas>().scaleFactor;
			Vector3 vector = camMain.WorldToScreenPoint(vDragStart);
			lineSelectRect.points2[0] = vector / scaleFactor2;
			lineSelectRect.points2[1] = new Vector2(mousePosition.x / scaleFactor2, vector.y / scaleFactor2);
			lineSelectRect.points2[2] = new Vector2(mousePosition.x / scaleFactor2, mousePosition.y / scaleFactor2);
			lineSelectRect.points2[3] = new Vector2(vector.x / scaleFactor2, mousePosition.y / scaleFactor2);
			lineSelectRect.points2[4] = vector / scaleFactor2;
			lineSelectRect.Draw();
		}
		ClearHighlightedCos();
		MouseHandler();
		contextMenuPool.MoveToCondOwnerPosition();
		bRaisedMenuThisFrame = false;
		vMouse = ActiveCam.ScreenToWorldPoint(new Vector3(mousePosition.x, mousePosition.y, 0f - camMain.transform.position.z));
		bRaiseUI = CanvasManager.State == CanvasManager.GUIState.SHIPGUI || CanvasManager.State == CanvasManager.GUIState.SOCIAL;
		vShake = UnityEngine.Random.insideUnitSphere * fShakeAmp;
		float num4 = 1f;
		if (GetMouseButton(0))
		{
			num4 = 0.25f;
		}
		CanvasManager.CanvasShake(vShake, fShakeAmp * 30f * num4);
		fShakeAmp *= 0.95f;
		if (bDebugShow)
		{
			string debugConds = "Time: " + fTotalGameSec.ToString("N2");
			debugConds = ((fTimeCoeffPause != 0f) ? (debugConds + " x" + Time.timeScale.ToString("N2")) : (debugConds + " x0"));
			debugConds += "\n";
			if (txtDebug1.text != debugConds)
			{
				txtDebug1.text = debugConds;
			}
		}
		CondOwner condOwner2 = coPlayer;
		if (aSelected.Count > 0 && aSelected[0].HasCond("IsHuman"))
		{
			condOwner2 = aSelected[0];
		}
		if (condOwner2 != null)
		{
			MonoSingleton<GUICrewStatus>.Instance.UpdateCrewBar(condOwner2);
			Audio_VacuumController component = condOwner2.GetComponent<Audio_VacuumController>();
			if (component != null)
			{
				component.CheckCurrent();
			}
			CanvasManager.instance.helmet.TunnelOpacity(CanvasManager.instance.helmet.GetTunnelAmount(condOwner2), bInstant: false);
		}
		if (shipCurrentLoaded != null)
		{
			float num5 = shipCurrentLoaded.objSS.vAccDrag.magnitude / 6.684587E-12f;
			if (num5 > 1f)
			{
				float currentRotorEfficiency = shipCurrentLoaded.CurrentRotorEfficiency;
				num5 /= 200f;
				num5 = MathUtils.Clamp(num5, 0f, 1f);
				currentRotorEfficiency = Mathf.Clamp(2f * currentRotorEfficiency + num5, 0.1f, 1f);
				AudioManager.am.PlayWindAudio(num5, currentRotorEfficiency, TimeElapsedScaled());
			}
			else
			{
				AudioManager.am.StopWindAudio();
			}
		}
		if (bPoolVisUpdates)
		{
			UpdateVisLights();
		}
		CondOwner selectedCrew = GetSelectedCrew();
		if (selectedCrew != null)
		{
			visPlayer.Position = selectedCrew.tf.position;
			if (selectedCrew.HasCond("IsVisualImpaired"))
			{
				visPlayer.Radius = 20f;
			}
			else
			{
				visPlayer.Radius = 25f;
			}
			if (selectedCrew.ship != null && selectedCrew.ship.fLastVisit <= 0.0 && !bRaiseUI)
			{
				if (selectedCrew.ship.objSS.bIsBO && !BeatManager.RunEncounter("ENCFirstDock" + selectedCrew.ship.strRegID, bInterrupt: true))
				{
					AudioManager.am.SuggestMusic(DataHandler.GetMusicForStation(coPlayer.ship.strRegID), bForce: true);
				}
				if (selectedCrew.ship != null)
				{
					selectedCrew.ship.fLastVisit = StarSystem.fEpoch;
					if (selectedCrew.ship.fFirstVisit <= 0.0)
					{
						selectedCrew.ship.fFirstVisit = StarSystem.fEpoch;
						if (selectedCrew.ship.nInitConstructionProgress <= 0)
						{
							selectedCrew.ship.nInitConstructionProgress = selectedCrew.ship.nConstructionProgress;
						}
					}
				}
			}
		}
		else if (bShipEdit)
		{
			visPlayer.Position = vMouse;
		}
		if (Screen.width != resolutionX || Screen.height != resolutionY || checkResolution)
		{
			SetResolution(Screen.width, Screen.height);
			resolutionX = Screen.width;
			resolutionY = Screen.height;
			checkResolution = false;
		}
		AudioManager.am.UpdateMusic();
		PlotManager.Update();
		if (!Paused)
		{
			Item.ItemAnimationUpdate.Invoke();
		}
		MonoSingleton<GUIQuickBar>.Instance.BuildButtonList();
	}

	private void ClearHighlightedCos()
	{
		foreach (CondOwner highlightOnHoverCo in _highlightOnHoverCos)
		{
			if (!(highlightOnHoverCo == null))
			{
				highlightOnHoverCo.Highlight = false;
			}
		}
		_highlightOnHoverCos.Clear();
	}

	private void LateUpdate()
	{
		if (!_finishedLoading)
		{
			return;
		}
		if (camFollow)
		{
			CamCenterTravel();
		}
		MoveViewHandler();
		if (aMutedCRs != null)
		{
			foreach (CondRule aMutedCR in aMutedCRs)
			{
				if (aMutedCR != null)
				{
					aMutedCR.bMuteOnce = false;
				}
			}
			aMutedCRs.Clear();
		}
		Destructable.LateUpdateDebug();
	}

	private void DrawPower(Ship ship)
	{
		if (ship == null || ship.aPwrTiles == null || ship.LoadState < Ship.Loaded.Edit)
		{
			return;
		}
		float scaleFactor = CanvasManager.goCanvasGUI.GetComponent<Canvas>().scaleFactor;
		int num = 7600;
		for (int i = 0; i <= ship.aPwrTiles.Count - 2; i += 2)
		{
			if (ship.aPwrTiles[i] == null || ship.aPwrTiles[i + 1] == null)
			{
				ship.aPwrTiles.RemoveRange(i, 2);
				i -= 2;
				continue;
			}
			Vector2 item = camMain.WorldToScreenPoint(ship.aPwrTiles[i].tf.position) / scaleFactor;
			Vector2 item2 = camMain.WorldToScreenPoint(ship.aPwrTiles[i + 1].tf.position) / scaleFactor;
			linePower.points2.Add(item);
			linePower.points2.Add(item2);
			if (linePower.points2.Count > num)
			{
				break;
			}
		}
		num -= linePower.points2.Count;
		for (int j = 0; j <= ship.aPwrTilesOff.Count - 2; j += 2)
		{
			if (linePowerOff.points2.Count > num)
			{
				break;
			}
			if (ship.aPwrTilesOff[j] == null || ship.aPwrTilesOff[j + 1] == null)
			{
				ship.aPwrTilesOff.RemoveRange(j, 2);
				j -= 2;
				continue;
			}
			Vector2 item3 = camMain.WorldToScreenPoint(ship.aPwrTilesOff[j].tf.position) / scaleFactor;
			Vector2 item4 = camMain.WorldToScreenPoint(ship.aPwrTilesOff[j + 1].tf.position) / scaleFactor;
			linePowerOff.points2.Add(item3);
			linePowerOff.points2.Add(item4);
		}
	}

	public void EmptyScene()
	{
		camMain.GetComponent<GameRenderer>().StencilCam.backgroundColor = new Color(0.2f, 0.2f, 0.2f, 1f);
		LowerUI();
		UpdateLog(coPlayer, null);
		goShipEdit.SetActive(bShipEdit);
		SetBracketTarget(null, bUpdateOnly: false);
		SetPartCursor(null);
		if (system != null)
		{
			system.Destroy();
			system = null;
		}
		if (shipCurrentLoaded != null && shipCurrentLoaded.aTiles != null)
		{
			shipCurrentLoaded.Destroy();
		}
		coPlayer = null;
		nLastClickIndex = 0;
		vLastClick.Set(1000f, 1000f);
		ResetTimeScale();
		fTimeCoeffPause = 1f;
		CamZoom(1f);
	}

	public static void StartArenaMode(string selectedShip = null)
	{
		if (shipCurrentLoaded != null)
		{
			shipCurrentLoaded.ValidateCrewSpawners();
			SceneManager.LoadScene("Loading", LoadSceneMode.Additive);
			jsonShip = shipCurrentLoaded.GetJSON(shipCurrentLoaded.strRegID, bSaveGame: false);
			bShipEdit = false;
			bShipEditTest = true;
			bDebugFightMode = true;
			objInstance.NewGame("Ceres Combat", "DebugFightKit");
			objInstance.DebugSetPlayerStartingPosition("CeresAsteroidFieldCentral");
			CanvasManager.CrewSimNormal();
		}
		else if (objInstance == null)
		{
			jsonShip = DataHandler.GetShip(selectedShip);
			OnSceneFinishedLoading.AddListener(delegate
			{
				bShipEdit = false;
				bShipEditTest = true;
				bDebugFightMode = true;
				objInstance.NewGame("Ceres Combat", "DebugFightKit");
				objInstance.DebugSetPlayerStartingPosition("CeresAsteroidFieldCentral");
				CanvasManager.CrewSimNormal();
			});
			SceneManager.LoadScene("Loading");
		}
		else
		{
			Debug.LogWarning("No ship loaded");
		}
	}

	public void TestShip(string starSystem, string spawnNearstation = null, float pushbackDistance = 2f, string strStartingLoot = null)
	{
		if (shipCurrentLoaded != null)
		{
			shipCurrentLoaded.ValidateCrewSpawners();
			SceneManager.LoadScene("Loading", LoadSceneMode.Additive);
			jsonShip = shipCurrentLoaded.GetJSON(shipCurrentLoaded.strRegID, bSaveGame: false);
			bShipEdit = false;
			bShipEditTest = true;
			bDebugFightMode = false;
			NewGame(starSystem, strStartingLoot);
			if (spawnNearstation != null)
			{
				objInstance.DebugSetPlayerStartingPosition(spawnNearstation, pushbackDistance);
			}
			CanvasManager.CrewSimNormal();
		}
		else
		{
			Debug.Log("Error: No ship loaded. Aborting test.");
		}
	}

	public void NewGame(string solarsystem = null, string strStartingLoot = null)
	{
		StartCoroutine(StartNewGame(solarsystem, strStartingLoot));
	}

	private IEnumerator StartNewGame(string starSystem, string strStartingLoot = null)
	{
		_finishedLoading = false;
		LoadManager.ResetLoadedSaveTracking();
		bShipEdit = false;
		LoadingScreen.SetProgressBar(0.1f, "Emptying Scene");
		yield return null;
		EmptyScene();
		LoadingScreen.SetProgressBar(0.2f, "Init Star System");
		yield return null;
		strSaveVersion = DataHandler.strBuild;
		aPatchesApplied = new List<string>();
		bSaveUsesOldContainerGrids = false;
		aSaveVersion = SaveInfo.ParseVersionStr(strSaveVersion);
		bool flag = !bShipEditTest || starSystem != null;
		system = new StarSystem();
		JsonStarSystemSave value = null;
		if (string.IsNullOrEmpty(starSystem))
		{
			List<string> lootNames = LootDefaultStarSystem.GetLootNames();
			if (lootNames.Count > 0)
			{
				starSystem = lootNames[0];
			}
			if (string.IsNullOrEmpty(starSystem))
			{
				starSystem = "NewGame";
			}
		}
		string text = starSystem;
		DataHandler.dictStarSystems.TryGetValue(text, out value);
		if (value != null && flag)
		{
			Debug.Log("Loading '" + text + "' star system.");
			yield return system.Init(value, null);
		}
		else
		{
			if (flag)
			{
				Debug.Log("No data found for '" + text + "' star system. Loading hard-coded star system.");
			}
			yield return system.Init(flag, flag);
		}
		MarketManager.Init();
		LoadingScreen.SetProgressBar(0.4f, "Load Starting Area");
		yield return null;
		Ship ship;
		if (bShipEditTest && jsonShip != null)
		{
			GameObject go = new GameObject("goShip");
			ship = new Ship(go);
			ship.json = jsonShip;
			ship.InitShip(bTemplateOnly: true, Ship.Loaded.Full);
			ship.objSS.vPosx = 1.0;
			ship.objSS.vPosy = 1.0;
			ship.objSS.vVelX = 0.0;
			ship.objSS.vVelY = 0.0;
		}
		else if (jsonShip != null)
		{
			GameObject go2 = new GameObject("goShip");
			ship = new Ship(go2);
			ship.json = jsonShip;
			ship.InitShip(bTemplateOnly: true, Ship.Loaded.Full);
		}
		else
		{
			string strRegID = "";
			List<string> lootNames2 = LootDefaultStarSystem.GetLootNames();
			if (lootNames2.Count > 1)
			{
				strRegID = lootNames2[1];
			}
			ship = system.SpawnShip(strRegID, Ship.Loaded.Full);
			if (ship == null)
			{
				List<Ship> list = system.GetAllLoadedShips().ToList();
				if (list == null || list.Count() == 0)
				{
					Debug.LogError("ERROR: No ships found in system. Cannot start game.");
					yield break;
				}
				ship = list[MathUtils.Rand(0, list.Count(), MathUtils.RandType.Flat)];
			}
			ship.fLastVisit = StarSystem.fEpoch;
		}
		ship.gameObject.transform.SetParent(base.transform, worldPositionStays: false);
		LoadingScreen.SetProgressBar(0.5f, "Spawn Player Character");
		yield return null;
		GetRandomCrew();
		if (jsonShip != null && !ship.IsStation())
		{
			system.RegisterShipOwner(ship.strRegID, coPlayer.strName);
			coPlayer.ClaimShip(ship.strRegID);
			coPlayer.ZeroCondAmount("IsInChargen");
		}
		LoadingScreen.SetProgressBar(0.55f, "Init Plot Manager");
		yield return null;
		BeatManager.Init();
		CrimeManager.Init();
		PlotManager.Init();
		LoadingScreen.SetProgressBar(0.6f, "Update Game Objects");
		yield return null;
		UpdateICOs();
		Ledger.OnLedgerRefresh.Invoke(arg0: false);
		LoadingScreen.SetProgressBar(0.65f, "Toggle Power UI");
		yield return null;
		if (PowerVizVisible)
		{
			TogglePowerUI(ship);
		}
		TileUtils.goPartTiles.SetActive(!TileUtils.goPartTiles.activeInHierarchy);
		LoadingScreen.SetProgressBar(0.8f, "Init AI Ship Manager");
		yield return null;
		AIShipManager.Init();
		LoadingScreen.SetProgressBar(0.9f, "Load Bounties");
		yield return null;
		yield return BountyManager.Init();
		LoadingScreen.SetProgressBar(0.95f, "Set Camera");
		yield return null;
		CamCenter(coPlayer);
		CanvasManager.instance.Black();
		yield return new WaitForSeconds(0.6f);
		bool chargen = starSystem == null || jsonShip == null;
		CrewSimTut = base.gameObject.AddComponent<CrewSimTut>();
		if (!string.IsNullOrEmpty(strStartingLoot))
		{
			foreach (CondOwner item in DataHandler.GetLoot(strStartingLoot).GetCOLoot(coPlayer, bSuppressOverride: false))
			{
				if (!(item == null))
				{
					CondOwner condOwner = coPlayer.AddCO(item, bEquip: true, bOverflow: true, bIgnoreLocks: true);
					if (condOwner != null)
					{
						coPlayer.DropCO(condOwner, bAllowLocked: false);
					}
					if (item.HasCond("IsSocialItem"))
					{
						CanvasManager.instance.goCanvasFloaties.GetComponent<GUISocialItemAnimator>().SpawnSocialItemAnimation(item.strName, item.strPortraitImg);
					}
				}
			}
		}
		SetChargen(chargen);
		SetTutorial();
		if (bDebugFightMode)
		{
			shipPlayerOwned = shipCurrentLoaded;
			ArenaModeManager.InitArenaMode();
		}
		_finishedLoading = true;
		OnGameFinishedLoading.Invoke();
		LoadingScreen.DestroyLoadingInstance();
	}

	private void SetTutorial()
	{
		if (bIsQuickstartSession)
		{
			bool flag = PlayerPrefs.GetFloat("QuickstartTutorial", 1f) == 0f;
			if (PlayerPrefs.GetFloat("QuickstartChargen", 1f) != 0f && flag)
			{
				CrewSimTut.forceTutorialNoChargen = true;
			}
			if (!flag)
			{
				coPlayer.ZeroCondAmount("TutorialZonesNoDorm");
			}
		}
		CrewSimTut.SetNewGameObjectives();
	}

	private void SetChargen(bool isRegularStart = true)
	{
		bool flag = false;
		if (bIsQuickstartSession && PlayerPrefs.GetFloat("QuickstartChargen", 1f) == 0f)
		{
			flag = true;
		}
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsCareerKiosk");
		if (!bShipEditTest && !condTrigger.IsBlank() && shipCurrentLoaded != null && isRegularStart)
		{
			List<CondOwner> cOs = shipCurrentLoaded.GetCOs(condTrigger, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
			if (cOs.Count > 0)
			{
				CondOwner objTarget = cOs[0];
				Interaction interaction = DataHandler.GetInteraction("GUIChargenBodyStarter");
				coPlayer.QueueInteraction(objTarget, interaction, bInsert: true);
				coPlayer.EndTurn();
				bUILock = true;
			}
			else
			{
				CanvasManager.CrewSimNormal();
			}
		}
		else
		{
			CanvasManager.CrewSimNormal();
		}
		if (flag && !isRegularStart)
		{
			CondOwner condOwner = DataHandler.GetCondOwner("ItmSink01Starter");
			shipCurrentLoaded.AddCO(condOwner, bTiles: false);
			condOwner.tf.position = coPlayer.tf.position;
			Interaction interaction2 = DataHandler.GetInteraction("GUIChargenBodyStarter");
			coPlayer.QueueInteraction(condOwner, interaction2, bInsert: true);
			coPlayer.EndTurn();
			bUILock = true;
		}
	}

	public void LoadGame(string fileName, string strShipsFolder, Dictionary<string, byte[]> dictFiles = null)
	{
		StartCoroutine(DoLoadGame(fileName, strShipsFolder, dictFiles));
	}

	public void LoadGame(SaveInfo saveInfo)
	{
		StartCoroutine(DoLoadGame(saveInfo.PathPlayer, saveInfo.PathShipsFolder));
	}

	private IEnumerator DoLoadGame(string fileName, string strShipsFolder, Dictionary<string, byte[]> dictFiles = null)
	{
		Debug.Log("#Info# CrewSim.objInstance.LoadGame(\"" + fileName + "\");");
		_finishedLoading = false;
		jsonShip = null;
		bShipEdit = false;
		bDebugFightMode = false;
		EmptyScene();
		LoadingScreen.SetProgressBar(0.3f, "Load files");
		yield return null;
		JsonGameSave jGS = DataHandler.LoadSaveFile(fileName, dictFiles);
		if (jGS == null)
		{
			yield break;
		}
		fTotalGameSec = jGS.fTotalGameSec;
		fTotalGameSecUnscaled = jGS.fTotalGameSecUnscaled;
		strSaveVersion = jGS.strVersion;
		if (strSaveVersion == null)
		{
			strSaveVersion = "<0.6.4.1";
		}
		aPatchesApplied = ((jGS.aPatchesApplied != null) ? jGS.aPatchesApplied.ToList() : new List<string>());
		string strSaveVersionTemp = strSaveVersion.Replace("\n", string.Empty);
		strSaveVersionTemp = strSaveVersionTemp.Replace("\r", string.Empty);
		strSaveVersionTemp = strSaveVersionTemp.Replace("<", string.Empty);
		strSaveVersionTemp = strSaveVersionTemp.Replace("Early Access Build: ", string.Empty);
		strSaveVersionTemp = strSaveVersionTemp.Replace("Release Build: ", string.Empty);
		aSaveVersion = new int[4] { 0, 6, 4, 1 };
		string[] array = strSaveVersionTemp.Split('.');
		if (array.Length != 0)
		{
			aSaveVersion = new int[array.Length];
		}
		for (int i = 0; i < array.Length; i++)
		{
			int.TryParse(array[i], out aSaveVersion[i]);
		}
		LoadingScreen.SetProgressBar(0.4f, "Load Ships");
		yield return null;
		JsonShip[] aShips;
		if (dictFiles != null)
		{
			List<JsonShip> loadedShips = new List<JsonShip>();
			foreach (string key2 in dictFiles.Keys)
			{
				if (key2.IndexOf("ships/", StringComparison.Ordinal) < 0 || Path.GetExtension(key2) == ".png")
				{
					continue;
				}
				Dictionary<string, JsonShip> dictionary = new Dictionary<string, JsonShip>();
				DataHandler.JsonToData(key2, dictionary, dictFiles);
				foreach (JsonShip value5 in dictionary.Values)
				{
					loadedShips.Add(value5);
				}
				LoadingScreen.SetProgressBar(0.45f, "Finished reading " + key2);
				yield return null;
			}
			aShips = loadedShips.ToArray();
		}
		else if (Directory.Exists(strShipsFolder))
		{
			List<JsonShip> loadedShips = new List<JsonShip>();
			string[] files = Directory.GetFiles(strShipsFolder);
			string[] array2 = files;
			foreach (string text in array2)
			{
				Dictionary<string, JsonShip> dictionary2 = new Dictionary<string, JsonShip>();
				DataHandler.JsonToData(text, dictionary2);
				foreach (JsonShip value6 in dictionary2.Values)
				{
					loadedShips.Add(value6);
				}
				LoadingScreen.SetProgressBar(0.45f, "Finished reading " + text);
				yield return null;
			}
			aShips = loadedShips.ToArray();
		}
		else
		{
			aShips = jGS.aShips;
		}
		LoadingScreen.SetProgressBar(0.5f, "Load star system");
		yield return null;
		DataHandler.dictCOSaves.Clear();
		int num = 0;
		if (jGS.aCOs != null)
		{
			JsonCondOwnerSave[] aCOs = jGS.aCOs;
			foreach (JsonCondOwnerSave jcos in aCOs)
			{
				if (string.IsNullOrEmpty(jcos.strRegIDLast) || !aShips.Any((JsonShip x) => x.strRegID == jcos.strRegIDLast))
				{
					num++;
				}
				else
				{
					DataHandler.dictCOSaves[jcos.strID] = jcos;
				}
			}
		}
		Debug.Log("Skipped loading " + num + " orphaned COs.");
		system = new StarSystem();
		system.bAllowTemplates = false;
		LoadingScreen.SetProgressBar(0.6f, "Init system");
		yield return null;
		yield return system.Init(jGS.objSystem, aShips);
		if (jGS.jComp != null)
		{
			system.AddCompany(jGS.jComp.Clone());
		}
		LoadingScreen.SetProgressBar(0.7f, "Load Market");
		yield return null;
		MarketManager.Init(jGS.objMarketSave);
		LoadingScreen.SetProgressBar(0.8f, "Load ship");
		yield return null;
		Ship ship = system.dictShips[jGS.strShip];
		ship.InitShip(bTemplateOnly: false, Ship.Loaded.Full);
		CondOwnerVisitorCatchUp visitor = new CondOwnerVisitorCatchUp();
		ship.VisitCOs(visitor, bSubObjects: true, bAllowDocked: true, bAllowLocked: true);
		SetCustomInfos(jGS.aCustomInfos);
		if (PowerVizVisible)
		{
			TogglePowerUI(ship);
			nRetogglePwr = 1;
		}
		LoadingScreen.SetProgressBar(0.85f, "Load roster");
		yield return null;
		system.bAllowTemplates = true;
		coPlayer = DataHandler.mapCOs[jGS.strPlayerCO];
		bool bCompRegen = true;
		bool bRosterRegen = true;
		if (coPlayer.Company != null)
		{
			bCompRegen = false;
			bRosterRegen = false;
		}
		else if (jGS.jComp != null && system.GetCompany(jGS.jComp.strName) != null)
		{
			JsonCompany company = system.GetCompany(jGS.jComp.strName);
			bCompRegen = false;
			foreach (string key3 in company.mapRoster.Keys)
			{
				CondOwner value = null;
				if (DataHandler.mapCOs.TryGetValue(key3, out value))
				{
					value.Company = company;
					if (value == coPlayer)
					{
						bRosterRegen = false;
					}
				}
			}
		}
		LoadingScreen.SetProgressBar(0.9f, "Load plot");
		yield return null;
		if (bRosterRegen)
		{
			if (bCompRegen)
			{
				coPlayer.Company = new JsonCompany();
				coPlayer.Company.strName = coPlayer.strName + "'s Company";
				coPlayer.Company.strRegID = ship.strRegID;
			}
			else
			{
				coPlayer.Company = system.GetCompany(jGS.jComp.strName);
			}
			coPlayer.Company.mapRoster[coPlayer.strID] = new JsonCompanyRules();
			coPlayer.Company.mapRoster[coPlayer.strID].bShoreLeave = true;
			coPlayer.Company.mapRoster[coPlayer.strID].bAirlockPermission = false;
			coPlayer.Company.mapRoster[coPlayer.strID].bRestorePermission = true;
			coPlayer.Company.mapRoster[coPlayer.strID].bReplaceBatteries = true;
			coPlayer.Company.mapRoster[coPlayer.strID].bReplaceO2Bottles = true;
			int nUTCHour = StarSystem.nUTCHour;
			coPlayer.Company.mapRoster[coPlayer.strID].StartWorkdayAt(nUTCHour);
			coPlayer.ShiftChange(coPlayer.Company.GetShift(nUTCHour, coPlayer), bSilent: true);
		}
		BeatManager.Init();
		CrimeManager.Init();
		PlotManager.Init(jGS);
		LoadingScreen.SetProgressBar(0.95f, "Load ledger");
		yield return null;
		if (jGS.aLIs != null)
		{
			Ledger.Init(jGS.aLIs);
		}
		LoadingScreen.SetProgressBar(0.95f, "Update COs");
		yield return null;
		UpdateICOs();
		Ledger.OnLedgerRefresh.Invoke(arg0: false);
		LoadingScreen.SetProgressBar(0.95f, "Set Camera");
		yield return null;
		TileUtils.goPartTiles.SetActive(!TileUtils.goPartTiles.activeInHierarchy);
		ClearSavedNavInputs();
		CamCenter(coPlayer);
		AIManual(coPlayer.HasCond("IsAIManual"));
		coPlayer.LogMessage("Welcome back, Captain.", "Neutral", "Game");
		MonoSingleton<ObjectiveTracker>.Instance.LoadObjectives(jGS);
		workManager.LoadTasksFromSave(jGS);
		AIShipManager.Init(jGS.objAIShipManager);
		CollisionManager.strATCClosest = AIShipManager.strATCLast;
		LoadingScreen.SetProgressBar(1f, "Load gigs");
		yield return null;
		GigManager.Init(jGS.aJobs);
		LoadingScreen.SetProgressBar(1f, "Load bounties");
		yield return null;
		yield return BountyManager.Init(jGS.aBounties);
		MonoSingleton<RacingLeagueManager>.Instance.InitFromSave(jGS.objRacingManager);
		LoadingScreen.SetProgressBar(1f, "Patching old save data");
		yield return null;
		bSaveHasCondRuleDupes = VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 26 });
		if (bSaveHasCondRuleDupes)
		{
			Ship[] array3 = system.GetAllLoadedShips().ToArray();
			for (int k = 0; k < array3.Length; k++)
			{
				foreach (CondOwner person in array3[k].GetPeople(bAllowDocked: false))
				{
					person.DebugFixOldCondRules(bOnlyReport: false);
					person.DebugFixOldMovSpeed(bOnlyReport: false);
				}
			}
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 3 }))
		{
			JsonCompany company2 = system.GetCompany("Maintenance");
			if (company2 != null)
			{
				foreach (KeyValuePair<string, JsonCompanyRules> item in company2.mapRoster)
				{
					item.Value.bShoreLeave = true;
					CondOwner condOwner = DataHandler.GetCondOwner(null, item.Key, null, bLoot: false);
					if (!(condOwner != null) || condOwner.HasCond("IsMaintenanceTechNPC"))
					{
						continue;
					}
					condOwner.AddCondAmount("IsMaintenanceTechNPC", 1.0);
					Interaction interaction = DataHandler.GetInteraction("PSPAIMaintenanceTechWorkFireExtinguishAdd");
					if (interaction != null)
					{
						interaction.objUs = condOwner;
						interaction.objThem = condOwner;
						if (interaction.Triggered(bStats: false, bIgnoreItems: true))
						{
							interaction.ApplyChain();
						}
					}
				}
			}
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 5 }) && !coPlayer.HasCond("IsDebug1505Fixed"))
		{
			CondOwner value2 = null;
			if (DataHandler.mapCOs.TryGetValue("Pan Tao", out value2))
			{
				value2.RemoveFromCurrentHome(bForce: true);
				value2.Destroy();
			}
			PersonSpec personSpec = new PersonSpec(DataHandler.GetPersonSpec("ProspectorBCER"), bNew: false);
			Ship shipByRegID = system.GetShipByRegID("BCER");
			value2 = personSpec.MakeCondOwner(PersonSpec.StartShip.OLD, shipByRegID);
			if (DataHandler.mapCOs.TryGetValue("Francisco Ortega", out value2))
			{
				value2.RemoveFromCurrentHome(bForce: true);
				value2.Destroy();
			}
			PersonSpec personSpec2 = new PersonSpec(DataHandler.GetPersonSpec("ProspectorBCRS"), bNew: false);
			shipByRegID = system.GetShipByRegID("BCRS");
			personSpec2.MakeCondOwner(PersonSpec.StartShip.OLD, shipByRegID);
			coPlayer.AddCondAmount("IsDebug1505Fixed", 1.0);
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 6 }) && !coPlayer.HasCond("IsDebug1506Fixed"))
		{
			foreach (LedgerLI shiftLI in Ledger.GetShiftLIs(StarSystem.fEpoch, includeUnpaid: true))
			{
				if (!(shiftLI.strCurrency != Ledger.CURRENCY) && !(shiftLI.strPayee != coPlayer.strID) && !(shiftLI.strPayor == coPlayer.strID))
				{
					shiftLI.fTimePaid = shiftLI.fTime;
				}
			}
			coPlayer.AddCondAmount("IsDebug1506Fixed", 1.0);
		}
		string key;
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 15 }) && !coPlayer.HasCond("IsDebug15-0-15Fixed"))
		{
			List<string> allFactions = coPlayer.GetAllFactions();
			bool flag = false;
			foreach (string item2 in allFactions)
			{
				JsonFaction faction = system.GetFaction(item2);
				if (faction == null)
				{
					coPlayer.RemoveFaction(item2);
				}
				else if (faction.aMembers.Count <= 1)
				{
					if (faction.strName == coPlayer.strName)
					{
						flag = true;
						break;
					}
					coPlayer.RemoveFaction(item2);
				}
			}
			if (!flag)
			{
				JsonFaction faction = new JsonFaction();
				faction.Init();
				key = (faction.strName = (faction.strNameFriendly = coPlayer.strID));
				system.AddFaction(faction);
				coPlayer.AddFaction(faction);
			}
			coPlayer.AddCondAmount("IsDebug15-0-15Fixed", 1.0);
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 25 }))
		{
			foreach (Ship item3 in system.dictShips.Values.ToList())
			{
				if (item3 == null)
				{
					continue;
				}
				bool flag2 = item3.strRegID.Contains("BCER_ROOF|RES");
				bool flag3 = item3.strRegID.Contains("BCRS_RES|RES");
				if (!flag2 && !flag3)
				{
					continue;
				}
				string strRegID = item3.strRegID;
				string shipOwner = system.GetShipOwner(strRegID);
				CondOwner condOwner2 = DataHandler.GetCondOwner(null, shipOwner, null, bLoot: false);
				if (condOwner2 != null)
				{
					condOwner2.UnclaimShip(strRegID);
				}
				system.dictShips.Remove(strRegID);
				string text3 = (item3.strRegID = ((!flag2) ? item3.strRegID.Replace("BCRS_RES|RES", "BCRS|RES") : item3.strRegID.Replace("BCER_ROOF|RES", "BCER|RES")));
				if (item3.json != null)
				{
					item3.json.strRegID = text3;
				}
				system.RegisterShipOwner(text3, shipOwner);
				if (condOwner2 != null)
				{
					condOwner2.ClaimShip(text3);
				}
				system.dictShips.Add(text3, item3);
				foreach (KeyValuePair<string, JsonCondOwnerSave> dictCOSafe in DataHandler.dictCOSaves)
				{
					dictCOSafe.Deconstruct(out key, out var value3);
					JsonCondOwnerSave jsonCondOwnerSave = value3;
					if (jsonCondOwnerSave != null && !(jsonCondOwnerSave.strRegIDLast != strRegID))
					{
						jsonCondOwnerSave.strRegIDLast = text3;
					}
				}
			}
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 27 }))
		{
			foreach (KeyValuePair<string, List<AIShip>> dictAI in AIShipManager.dictAIs)
			{
				foreach (AIShip item4 in dictAI.Value)
				{
					if (item4.Ship.shipScanTarget != null && item4.Ship.shipScanTarget.strRegID.IndexOf("|") >= 0 && system.GetShipOwner(item4.Ship.shipScanTarget.strRegID) == coPlayer.strID)
					{
						item4.Ship.objSS.ResetNavData();
						item4.Ship.ClearShipTarget();
					}
					if (item4.Ship.json != null && !string.IsNullOrEmpty(item4.Ship.json.strScanTargetID) && item4.Ship.json.strScanTargetID.IndexOf("|") >= 0 && system.GetShipOwner(item4.Ship.json.strScanTargetID) == coPlayer.strID)
					{
						item4.Ship.json.strScanTargetID = null;
						item4.Ship.json.objSituScanTarget = null;
						item4.Ship.json.strCombatTargetID = null;
						item4.Ship.json.strTargetRegID = null;
					}
				}
			}
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 27 }))
		{
			foreach (KeyValuePair<string, List<AIShip>> dictAI2 in AIShipManager.dictAIs)
			{
				foreach (AIShip item5 in dictAI2.Value)
				{
					if (item5.Ship.shipScanTarget != null && item5.Ship.shipScanTarget.strRegID.IndexOf("|") >= 0 && system.GetShipOwner(item5.Ship.shipScanTarget.strRegID) == coPlayer.strID)
					{
						item5.Ship.objSS.ResetNavData();
						item5.Ship.ClearShipTarget();
					}
					if (item5.Ship.json != null && !string.IsNullOrEmpty(item5.Ship.json.strScanTargetID) && item5.Ship.json.strScanTargetID.IndexOf("|") >= 0 && system.GetShipOwner(item5.Ship.json.strScanTargetID) == coPlayer.strID)
					{
						item5.Ship.json.strScanTargetID = null;
						item5.Ship.json.objSituScanTarget = null;
						item5.Ship.json.strCombatTargetID = null;
						item5.Ship.json.strTargetRegID = null;
					}
				}
			}
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 33 }) && !coPlayer.HasCond("IsDebug15-0-33Fixed"))
		{
			Ship[] array3 = system.GetAllLoadedShips().ToArray();
			for (int k = 0; k < array3.Length; k++)
			{
				foreach (CondOwner person2 in array3[k].GetPeople(bAllowDocked: false))
				{
					person2.ZeroCondAmount("TraitChronicEmphysema");
					person2.ZeroCondAmount("ChronicEmphysema");
					person2.ZeroCondAmount("Pneumonitis2");
					person2.ZeroCondAmount("Pneumonitis3");
				}
			}
			coPlayer.AddCondAmount("IsDebug15-0-33Fixed", 1.0);
		}
		if (!aPatchesApplied.Contains("0.15.0.34_Mass_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 34 }))
		{
			Ship[] array3 = system.GetAllLoadedShips().ToArray();
			for (int k = 0; k < array3.Length; k++)
			{
				foreach (CondOwner person3 in array3[k].GetPeople(bAllowDocked: false))
				{
					person3.DebugAuditMass("", bFix: true);
				}
			}
			aPatchesApplied.Add("0.15.0.34_Mass_Fix");
		}
		if (VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 0, 38 }))
		{
			foreach (string item6 in new List<string> { "BCER", "OKLG_FLOT" })
			{
				Ship shipByRegID2 = system.GetShipByRegID(item6);
				if (shipByRegID2 != null && !(shipByRegID2.ShipCO == null) && !shipByRegID2.ShipCO.HasCond("IsDebug15-0-38Fixed"))
				{
					DebugRespawnShip.RespawnShip(item6, bNPCs: false);
					system.GetShipByRegID(item6)?.ShipCO.AddCondAmount("IsDebug15-0-38Fixed", 1.0);
				}
			}
		}
		if (!aPatchesApplied.Contains("0.15.1.1_LootSpawn_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 1, 1 }))
		{
			Dictionary<CondOwner, List<CondOwner>> dictionary3 = new Dictionary<CondOwner, List<CondOwner>>();
			foreach (CondOwner value7 in DataHandler.mapCOs.Values)
			{
				if (value7.HasCond("IsLootSpawner") && !(value7.GetGPMInfo("Panel A", "strType") != "Lot Loot") && !(value7.objCOParent == null))
				{
					if (dictionary3.ContainsKey(value7.objCOParent))
					{
						dictionary3[value7.objCOParent].Add(value7);
						continue;
					}
					dictionary3[value7.objCOParent] = new List<CondOwner> { value7 };
				}
			}
			foreach (KeyValuePair<CondOwner, List<CondOwner>> item7 in dictionary3)
			{
				if (item7.Value.Count < 2)
				{
					continue;
				}
				CondOwner condOwner3 = null;
				Crew component = item7.Key.GetComponent<Crew>();
				if (component != null && item7.Key.compSlots != null)
				{
					Slot slot = item7.Key.compSlots.GetSlot("social");
					if (slot != null)
					{
						condOwner3 = slot.GetOutermostCO();
						if (condOwner3 == null)
						{
							foreach (CondOwner item8 in DataHandler.GetLoot("ItmCrewSlots").GetCOLoot(item7.Key, bSuppressOverride: false))
							{
								CondOwner condOwner4 = item7.Key.AddCO(item8, bEquip: true, bOverflow: false, bIgnoreLocks: false);
								if (condOwner4 != null)
								{
									Debug.Log($"{item8} rejected by {item7.Key}. Destroying.");
									condOwner4.Destroy();
								}
								else
								{
									Debug.Log($"{item8} added to {item7.Key}");
								}
							}
							component.SetBodyFaceSkin(Crew.GetBodyType(item7.Key), component.FaceParts, bForce: true);
						}
					}
				}
				int num2 = 0;
				if (condOwner3 != null)
				{
					List<CondOwner> cOs = condOwner3.GetCOs(bAllowLocked: false);
					if (cOs != null)
					{
						num2 = cOs.Count;
					}
				}
				for (int num3 = 1; num3 < item7.Value.Count; num3++)
				{
					CondOwner condOwner5 = item7.Value[num3];
					foreach (CondOwner lotCO in condOwner5.GetLotCOs(bSubItems: false))
					{
						lotCO.RemoveFromCurrentHome(bForce: true);
						if (num2 >= 50 && lotCO.HasCond("IsSocialItem"))
						{
							if (DataHandler.dictCOSaves.ContainsKey(lotCO.strID))
							{
								DataHandler.dictCOSaves.Remove(lotCO.strID);
							}
							Debug.Log($"Excess {item7.Key}.{lotCO} on {item7.Key}. Deleting.");
						}
						else if (item7.Key.AddCO(lotCO, bEquip: true, bOverflow: true, bIgnoreLocks: true) == null)
						{
							num2++;
							Debug.Log($"Transplanting {item7.Key}.{lotCO} from {condOwner5} to {item7.Key}");
						}
						else
						{
							item7.Value[0].AddLotCO(lotCO);
							Debug.Log($"Transplanting {item7.Key}.{lotCO} from {condOwner5} to {item7.Value[0]}");
						}
					}
					condOwner5.RemoveFromCurrentHome(bForce: true);
					if (DataHandler.dictCOSaves.ContainsKey(condOwner5.strID))
					{
						DataHandler.dictCOSaves.Remove(condOwner5.strID);
					}
					condOwner5.Destroy();
				}
			}
			aPatchesApplied.Add("0.15.1.1_LootSpawn_Fix");
		}
		if (!aPatchesApplied.Contains("0.15.1.2_AerostatGrav_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 1, 2 }))
		{
			foreach (string item9 in new List<string>
			{
				"VNCA", "VNCA_SD", "VLA00", "VLA01", "VLA02", "VLA03", "VLA04", "VLA05", "VCBR", "VENC",
				"VENC_SVL", "VENC_GRN"
			})
			{
				Ship shipByRegID3 = system.GetShipByRegID(item9);
				if (shipByRegID3 != null && !(shipByRegID3.ShipCO == null))
				{
					shipByRegID3.ShipCO.AddCondAmount("StationHasGrav", 1.0);
				}
			}
			aPatchesApplied.Add("0.15.1.2_AerostatGrav_Fix");
		}
		if (!aPatchesApplied.Contains("0.99.0.0_SVIRGround_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 99, 0, 1 }))
		{
			Ship shipByRegID4 = system.GetShipByRegID("SVIR");
			BodyOrbit bO = system.GetBO("Titan");
			JsonStarSystemSave value4 = null;
			if (shipByRegID4 != null && shipByRegID4.LoadState <= Ship.Loaded.Shallow && bO != null && DataHandler.dictStarSystems.TryGetValue("NewGame", out value4) && value4.aSpawnStations != null)
			{
				JsonSpawnStation jsonSpawnStation = null;
				JsonSpawnStation[] aSpawnStations = value4.aSpawnStations;
				foreach (JsonSpawnStation jsonSpawnStation2 in aSpawnStations)
				{
					if (jsonSpawnStation2.strName == "SVIR")
					{
						jsonSpawnStation = jsonSpawnStation2;
						break;
					}
				}
				if (jsonSpawnStation != null)
				{
					jsonSpawnStation = jsonSpawnStation.Clone();
					BodyOrbit bO2 = system.GetBO(jsonSpawnStation.strName);
					double fPerihelion = 0.0;
					double fAphelion = 0.0;
					system.CalculatePAFromET(ref fPerihelion, ref fAphelion, jsonSpawnStation.fEccentricity, jsonSpawnStation.fOrbitalPeriodYears, bO);
					jsonSpawnStation.fApoapsisAU = fAphelion;
					jsonSpawnStation.fPeriapsisAU = fPerihelion;
					if (jsonSpawnStation.fOrbitalPeriodYears == 0.0)
					{
						jsonSpawnStation.fOrbitalPeriodYears = system.CalculatePeriodFromPAET(jsonSpawnStation.fPeriapsisAU, jsonSpawnStation.fApoapsisAU, bO.fMass);
					}
					double fRotationPeriod = bO.fRotationPeriod;
					BodyOrbit bodyOrbit = new BodyOrbit(jsonSpawnStation.strName, jsonSpawnStation.fPeriapsisAU, jsonSpawnStation.fApoapsisAU, jsonSpawnStation.fDegreesCW, jsonSpawnStation.fEccentricity, jsonSpawnStation.fOrbitalPeriodYears, jsonSpawnStation.fRadiusKM, jsonSpawnStation.fMassKG, fRotationPeriod, bO);
					bodyOrbit.nDrawFlagsBody = 1;
					if (jsonSpawnStation.bDrawTrack)
					{
						bodyOrbit.nDrawFlagsTrack = 2;
					}
					else
					{
						bodyOrbit.nDrawFlagsTrack = 1;
					}
					system.RemoveBO(bO2);
					system.AddBO(bodyOrbit, bO);
					shipByRegID4.objSS.strBOPORShip = bodyOrbit.strName;
					shipByRegID4.json.objSS.boPORShip = bodyOrbit.strName;
					aPatchesApplied.Add("0.99.0.0_SVIRGround_Fix");
				}
			}
		}
		if (!aPatchesApplied.Contains("0.15.1.11_HygienePledge_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 1, 11 }))
		{
			Ship[] array4 = system.GetAllLoadedShips().ToArray();
			List<string> list = new List<string> { "PSPAIHygieneAdd", "PSPAIUnwearSuitAdd" };
			Ship[] array3 = array4;
			for (int k = 0; k < array3.Length; k++)
			{
				foreach (CondOwner person4 in array3[k].GetPeople(bAllowDocked: false))
				{
					foreach (string item10 in list)
					{
						Interaction interaction2 = DataHandler.GetInteraction(item10);
						if (interaction2 != null)
						{
							interaction2.objUs = person4;
							interaction2.objThem = person4;
							if (interaction2.Triggered(bStats: false, bIgnoreItems: true))
							{
								interaction2.ApplyChain();
							}
						}
					}
				}
			}
			aPatchesApplied.Add("0.15.1.11_HygienePledge_Fix");
		}
		if (!aPatchesApplied.Contains("0.15.1.13_EVABatt_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 1, 13 }))
		{
			Ship[] array5 = system.GetAllLoadedShips().ToArray();
			Debug.Log("Patching EVA batteries for battery replacement pledge.");
			Ship[] array3 = array5;
			foreach (Ship ship2 in array3)
			{
				if (ship2.LoadState >= Ship.Loaded.Edit)
				{
					foreach (CondOwner cO in ship2.GetCOs(DataHandler.GetCondTrigger("TIsFitContainerEVABattery"), bSubObjects: true, bAllowDocked: false, bAllowLocked: true))
					{
						cO.SetCondAmount("IsPocketable", 1.0);
					}
					foreach (CondOwner person5 in ship2.GetPeople(bAllowDocked: false))
					{
						Interaction interaction3 = DataHandler.GetInteraction("PSPAIRechargeAdd");
						if (interaction3 != null)
						{
							interaction3.objUs = person5;
							interaction3.objThem = person5;
							if (interaction3.Triggered(bStats: false, bIgnoreItems: true))
							{
								interaction3.ApplyChain();
							}
						}
					}
					continue;
				}
				foreach (CondOwner person6 in ship2.GetPeople(bAllowDocked: false))
				{
					foreach (CondOwner cO2 in person6.GetCOs(bAllowLocked: true, DataHandler.GetCondTrigger("TIsFitContainerEVABattery")))
					{
						cO2.SetCondAmount("IsPocketable", 1.0);
					}
					Interaction interaction4 = DataHandler.GetInteraction("PSPAIRechargeAdd");
					if (interaction4 != null)
					{
						interaction4.objUs = person6;
						interaction4.objThem = person6;
						if (interaction4.Triggered(bStats: false, bIgnoreItems: true))
						{
							interaction4.ApplyChain();
						}
					}
				}
			}
			aPatchesApplied.Add("0.15.1.13_EVABatt_Fix");
		}
		if (!aPatchesApplied.Contains("0.99.0.0_BCER_ROOF_Zone_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 99, 0, 1 }))
		{
			List<string> obj = new List<string> { "BCER_ROOF" };
			bool flag4 = true;
			foreach (string item11 in obj)
			{
				Ship shipByRegID5 = system.GetShipByRegID(item11);
				if (shipByRegID5 != null && !(shipByRegID5.ShipCO == null) && !shipByRegID5.ShipCO.HasCond("IsDebug99-0-1Fixed"))
				{
					if (shipByRegID5.LoadState >= Ship.Loaded.Edit)
					{
						flag4 = false;
						continue;
					}
					DebugRespawnShip.RespawnShip(item11, bNPCs: false);
					system.GetShipByRegID(item11)?.ShipCO.AddCondAmount("IsDebug99-0-1Fixed", 1.0);
				}
			}
			if (flag4)
			{
				aPatchesApplied.Add("0.99.0.0_BCER_ROOF_Zone_Fix");
			}
		}
		if (!aPatchesApplied.Contains("0.99.0.0_BCER_SARC_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 99, 0, 1 }))
		{
			Debug.Log("Applying 0.99.0.0_BCER_SARC_Fix");
			List<string> obj2 = new List<string> { "BCER_SARC" };
			bool flag5 = true;
			foreach (string item12 in obj2)
			{
				if (system.GetShipByRegID(item12) == null)
				{
					DebugRespawnShip.RespawnShip(item12, bNPCs: false);
					system.GetShipByRegID(item12);
				}
			}
			if (flag5)
			{
				aPatchesApplied.Add("0.99.0.0_BCER_SARC_Fix");
			}
		}
		if (!aPatchesApplied.Contains("0.15.1.18_ShiftThresh_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 1, 18 }))
		{
			Ship[] array6 = system.GetAllLoadedShips().ToArray();
			string[] array7 = new string[3] { "ThreshStatAchievement", "ThreshStatEsteem", "ThreshStatMeaning" };
			Debug.Log("Patching bad shift change thresholds.");
			int num4 = 0;
			Ship[] array3 = array6;
			for (int k = 0; k < array3.Length; k++)
			{
				foreach (CondOwner person7 in array3[k].GetPeople(bAllowDocked: false))
				{
					bool flag6 = false;
					string[] array8 = array7;
					foreach (string strName in array8)
					{
						if (person7.GetCondAmount(strName) > 2.0)
						{
							person7.SetCondAmount(strName, 1.0);
							flag6 = true;
						}
					}
					if (flag6)
					{
						num4++;
					}
				}
			}
			Debug.Log($"Fixed bad shift ThreshStat on {num4} COs.");
			aPatchesApplied.Add("0.15.1.18_ShiftThresh_Fix");
		}
		if (!aPatchesApplied.Contains("0.15.1.20_EVABottle_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 1, 20 }))
		{
			foreach (Ship allLoadedShip in system.GetAllLoadedShips())
			{
				foreach (CondOwner person8 in allLoadedShip.GetPeople(bAllowDocked: false))
				{
					Interaction interaction5 = DataHandler.GetInteraction("PSPAIReplaceO2BottleAdd");
					if (interaction5 != null)
					{
						interaction5.objUs = person8;
						interaction5.objThem = person8;
						if (interaction5.Triggered(bStats: false, bIgnoreItems: true))
						{
							interaction5.ApplyChain();
						}
					}
				}
			}
			aPatchesApplied.Add("0.15.1.20_EVABottle_Fix");
		}
		if (!aPatchesApplied.Contains("0.15.99.5_Strata_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 0, 15, 99, 5 }))
		{
			foreach (Ship allLoadedShip2 in system.GetAllLoadedShips())
			{
				foreach (CondOwner person9 in allLoadedShip2.GetPeople(bAllowDocked: false))
				{
					GUIChargenStack component2 = person9.GetComponent<GUIChargenStack>();
					if (!(component2 == null))
					{
						if (person9.HasCond("IsStrataCitizen") && component2.Strata != 2)
						{
							Debug.Log("Patching " + person9.FriendlyName + " strata from illegal to citizen.");
							component2.DebugSetStrata(2);
						}
						else if (person9.HasCond("IsStrataPermRes") && component2.Strata != 1)
						{
							Debug.Log("Patching " + person9.FriendlyName + " strata from illegal to resident.");
							component2.DebugSetStrata(1);
						}
					}
				}
			}
			aPatchesApplied.Add("0.15.99.5_Strata_Fix");
		}
		if (!aPatchesApplied.Contains("1.0.0.0_BCER_ROOF_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 1, 0, 0, 1 }))
		{
			Debug.Log("Applying 1.0.0.0_BCER_ROOF_Fix");
			List<string> obj3 = new List<string> { "BCER_ROOF" };
			bool flag7 = true;
			foreach (string item13 in obj3)
			{
				Ship shipByRegID6 = system.GetShipByRegID(item13);
				if (shipByRegID6 != null && !(shipByRegID6.ShipCO == null) && !shipByRegID6.ShipCO.HasCond("IsDebug1-0-0-1Fixed"))
				{
					if (shipByRegID6.LoadState >= Ship.Loaded.Edit)
					{
						flag7 = false;
						continue;
					}
					DebugRespawnShip.RespawnShip(item13, bNPCs: false);
					system.GetShipByRegID(item13)?.ShipCO.AddCondAmount("IsDebug1-0-0-1Fixed", 1.0);
				}
			}
			if (flag7)
			{
				aPatchesApplied.Add("1.0.0.0_BCER_ROOF_Fix");
			}
		}
		if (!aPatchesApplied.Contains("1.0.0.3_Rent_Fix") && VersionIsOlderThan(aSaveVersion, new int[4] { 1, 0, 0, 3 }))
		{
			Debug.Log("Applying 1.0.0.3_Rent_Fix");
			foreach (LedgerLI unpaidLI in Ledger.GetUnpaidLIs(coPlayer.strID, DataHandler.GetString("LEDGER_PAYOR_CERES_PLOT_INCOME"), null, bIncludeRepeating: true))
			{
				coPlayer.AddCondAmount(unpaidLI.strCurrency, unpaidLI.fAmount);
				unpaidLI.fTimePaid = StarSystem.fEpoch;
			}
			Ledger.OnLedgerRefresh.Invoke(arg0: true);
			aPatchesApplied.Add("1.0.0.3_Rent_Fix");
		}
		if (VersionIsOlderThan(aSaveVersion, aReqVersion))
		{
			coPlayer.LogMessage("Warning: This Save File uses an old format (v" + strSaveVersionTemp + ") which may cause problems.", "Bad", coPlayer.strID);
			coPlayer.LogMessage("For best results, you should begin a new game, or opt-in to a Steam 'legacy_X' beta branch compatible with v" + strSaveVersionTemp + ".", "Bad", coPlayer.strID);
		}
		CrewSimTut = base.gameObject.AddComponent<CrewSimTut>();
		MonoSingleton<AsyncShipLoader>.Instance.LoadDockedBarterZoneShips(GetSelectedCrew());
		if (OnGameFinishedLoading != null)
		{
			OnGameFinishedLoading.Invoke();
		}
		LoadingScreen.DestroyLoadingInstance();
		Paused = false;
		ForceUpdateAnimators();
		yield return null;
		Paused = true;
		_finishedLoading = true;
	}

	private void ForceUpdateAnimators()
	{
		if (COAnimators == null)
		{
			return;
		}
		foreach (Animator cOAnimator in COAnimators)
		{
			if (!(cOAnimator == null) && !(cOAnimator.gameObject == null) && cOAnimator.gameObject.activeInHierarchy)
			{
				AnimatorCullingMode cullingMode = cOAnimator.cullingMode;
				cOAnimator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
				cOAnimator.Update(0.1f);
				cOAnimator.Update(0.1f);
				cOAnimator.cullingMode = cullingMode;
			}
		}
	}

	private static void ClearSavedNavInputs()
	{
		if (coPlayer.ship != null && coPlayer.ship.LoadState > Ship.Loaded.Shallow && coPlayer.ship.NavPlayerManned)
		{
			coPlayer.ship.Maneuver(0f, 0f, 0f, 0, 1E-10f);
		}
	}

	public void DebugSetPlayerStartingPosition(string spawnNearStation, float pushbackDistance = 2f)
	{
		StartCoroutine(SetPlayerStartingPositionNearStation(spawnNearStation, pushbackDistance));
	}

	public void DebugSetPlayerStartingPosition(string spawnNearStation, Action callback = null)
	{
		StartCoroutine(SetPlayerStartingPositionNearStation(spawnNearStation, 73f, callback));
	}

	public void DebugSetPlayerStartingPosition(Point spawnPos, Action callback = null)
	{
		StartCoroutine(SetPlayerStartingPositionToCoords(spawnPos, callback));
	}

	public void DebugSetPlayerStartingPosition(string boName)
	{
		StartCoroutine(SetPlayerStartingPositionToCoords(default(Point), null, boName));
	}

	private IEnumerator SetPlayerStartingPositionNearStation(string spawnNearStation, float pushbackDistance, Action callback = null)
	{
		yield return new WaitUntil(() => objInstance != null && objInstance.FinishedLoading);
		Ship ship = coPlayer.ship;
		ship.MoveShip(-ship.vShipPos);
		Ship value = null;
		system.dictShips.TryGetValue(spawnNearStation, out value);
		if (value != null)
		{
			value.objSS.UpdateTime(StarSystem.fEpoch);
			ship.objSS.vPosx = value.objSS.vPosx;
			ship.objSS.vPosy = value.objSS.vPosy;
			if (pushbackDistance > 0f)
			{
				Vector2 pushbackVector = MathUtils.GetPushbackVector(ship, value);
				float num = 3.3422936E-08f + pushbackDistance;
				pushbackVector *= num / 149597870f;
				ship.objSS.vPosx = value.objSS.vPosx + (double)pushbackVector.x;
				ship.objSS.vPosy = value.objSS.vPosy + (double)pushbackVector.y;
			}
			else
			{
				DockShip(ship, value.strRegID);
			}
			ship.objSS.vVelX = value.objSS.vVelX;
			ship.objSS.vVelY = value.objSS.vVelY;
		}
		callback?.Invoke();
	}

	private IEnumerator SetPlayerStartingPositionToCoords(Point spawnPos, Action callback, string boName = null)
	{
		yield return new WaitUntil(() => objInstance != null && objInstance.FinishedLoading);
		Ship ship = coPlayer.ship;
		ship.MoveShip(-ship.vShipPos);
		ship.objSS.UpdateTime(StarSystem.fEpoch);
		BodyOrbit bodyOrbit;
		if (!string.IsNullOrEmpty(boName))
		{
			bodyOrbit = system.GetBO(boName);
			if (bodyOrbit == null)
			{
				Debug.LogError("BO not found");
				yield break;
			}
			system.SetSituToRandomSafeCoords(ship.objSS, bodyOrbit.fRadius + 6.68458710606501E-08, bodyOrbit.fRadius + 3.342293553032505E-07, bodyOrbit.dXReal, bodyOrbit.dYReal);
		}
		else
		{
			ship.objSS.vPosx = spawnPos.X;
			ship.objSS.vPosy = spawnPos.Y;
			bodyOrbit = system.GetNearestBO(ship.objSS, StarSystem.fEpoch, bIncludePlaceholders: false);
		}
		ship.objSS.LockToBO(bodyOrbit);
		ship.objSS.bBOLocked = false;
		callback?.Invoke();
	}

	public static bool VersionIsOlderThan(int[] aVersion, int[] aOlderThan)
	{
		if (aVersion == null || aOlderThan == null)
		{
			return true;
		}
		int num = Mathf.Min(aVersion.Length, aOlderThan.Length);
		for (int i = 0; i < num; i++)
		{
			if (aVersion[i] > aOlderThan[i])
			{
				return false;
			}
			if (aVersion[i] < aOlderThan[i])
			{
				return true;
			}
		}
		return false;
	}

	public void StartShipEdit()
	{
		StartCoroutine(LoadShipEdit());
	}

	private IEnumerator LoadShipEdit()
	{
		LoadingScreen.SetProgressBar(0.2f, "Loading scene");
		yield return null;
		bool bLoadSystem = false;
		bShipEdit = true;
		CanvasManager.ShipEdit();
		if (!bWarnedShipEdit)
		{
			CanvasManager.ShowCanvasGroup(CanvasManager.goCanvasShipEdit.transform.Find("ShipEdit/GUIWarning").gameObject);
			bWarnedShipEdit = true;
		}
		EmptyScene();
		LoadingScreen.SetProgressBar(0.4f, "Init system");
		yield return null;
		system = new StarSystem();
		yield return system.Init(bLoadSystem, bLoadSystem);
		LoadingScreen.SetProgressBar(0.5f, "Init ship manager");
		yield return null;
		MarketManager.Init();
		AIShipManager.Init();
		GameObject goShip = new GameObject("goShip");
		goShip.transform.SetParent(base.transform, worldPositionStays: false);
		LoadingScreen.SetProgressBar(0.7f, "Load ship");
		yield return null;
		Ship ship = new Ship(goShip);
		if (jsonShip != null)
		{
			ship.json = jsonShip.Clone();
			if (jsonShip.nConstructionProgress < 100)
			{
				JsonShipConstructionTemplate shipConstructionTemplate = DataHandler.GetShipConstructionTemplate(jsonShip);
				ship.json.aItems = shipConstructionTemplate.aItems;
				ship.json.aShallowPSpecs = shipConstructionTemplate.aShallowPSpecs;
			}
			ship.InitShip(bTemplateOnly: true, Ship.Loaded.Edit);
			ship.gameObject.name = jsonShip.strName;
		}
		else
		{
			ship.json = new JsonShip();
			ship.json.aItems = new JsonItem[0];
			ship.json.aCrew = new JsonItem[0];
			ship.InitShip(bTemplateOnly: true, Ship.Loaded.Edit);
		}
		GUIShipEdit.Instance.LoadShipEdit(jsonShip);
		LoadingScreen.SetProgressBar(1f, "Populate tiles");
		yield return null;
		UpdateICOs();
		if (PowerVizVisible)
		{
			TogglePowerUI(ship);
		}
		TileUtils.goPartTiles.SetActive(!TileUtils.goPartTiles.activeInHierarchy);
		camMain.GetComponent<GameRenderer>().StencilCam.backgroundColor = Color.white;
		_finishedLoading = true;
		OnGameFinishedLoading.Invoke();
		LoadingScreen.DestroyLoadingInstance();
		UnlockAchievement("ACH_EDITOR");
	}

	public static void QueueEncounter(Interaction ia)
	{
		if (!(ia.objUs == null) && !(ia.objThem == null))
		{
			objInstance.StartCoroutine(ShowEncounter(ia));
		}
	}

	private static IEnumerator ShowEncounter(Interaction ia)
	{
		if (!(ia.objUs == null) && !(ia.objThem == null))
		{
			while (bRaiseUI)
			{
				yield return null;
			}
			ia.objUs.QueueInteraction(ia.objThem, ia);
		}
	}

	private static IEnumerator ShowScene(string strScene, float time)
	{
		yield return new WaitForSeconds(time);
		objInstance.EmptyScene();
		if (OnGameEnd != null)
		{
			OnGameEnd.Invoke();
		}
		objInstance = null;
		SceneManager.LoadScene(strScene);
	}

	public void QuitImmediate()
	{
		Application.Quit();
	}

	public static void QueueScene(string strScene, float time)
	{
		objInstance.StartCoroutine(ShowScene(strScene, time));
	}

	private static IEnumerator PauseScene(bool bPause, float time)
	{
		yield return new WaitForSeconds(time);
		Paused = bPause;
	}

	public static void QueuePause(bool bPause, float time)
	{
		objInstance.StartCoroutine(PauseScene(bPause, time));
	}

	public void LoadShipEdit(JsonShip jShip)
	{
		jsonShip = jShip;
		if (jsonShip != null)
		{
			StartShipEdit();
		}
	}

	public void LoadShipEdit(string str)
	{
		jsonShip = DataHandler.GetShip(str);
		if (jsonShip != null)
		{
			StartShipEdit();
			return;
		}
		JsonAsteroidClusterBlueprint asteroidClusterBlueprint = DataHandler.GetAsteroidClusterBlueprint(str);
		if (asteroidClusterBlueprint != null)
		{
			jsonShip = LayoutGenerator.GenerateLayout(asteroidClusterBlueprint);
			StartShipEdit();
		}
	}

	public void StartBulkSave()
	{
		_bulkSaver = StartCoroutine(BulkSave());
	}

	public bool IsBulkSaverRunning()
	{
		return _bulkSaver != null;
	}

	private IEnumerator BulkSave()
	{
		List<JsonShip> list = DataHandler.dictShips.Values.ToList();
		foreach (JsonShip jShip in list)
		{
			yield return new WaitUntil(() => !MonoSingleton<ScreenshotUtil>.Instance.IsRunning);
			jsonShip = jShip;
			yield return LoadShipEdit();
			GUIShipEdit.Instance.SaveShipEdit(jShip.strName);
			Resources.UnloadUnusedAssets();
		}
		jsonShip = null;
		string strRegID = shipCurrentLoaded.strRegID;
		if (strRegID != null)
		{
			system.dictShips.Remove(strRegID);
		}
		StartShipEdit();
		_bulkSaver = null;
	}

	public void ScheduleCODestruction(CondOwner coToDestroy)
	{
		StartCoroutine(DestroyCO(coToDestroy));
	}

	private IEnumerator DestroyCO(CondOwner coToDestroy)
	{
		yield return null;
		if (coToDestroy != null)
		{
			coToDestroy.Destroy();
		}
	}

	public static void StartTyping()
	{
		Typing = true;
		Debug.Log("Started typing");
	}

	public static void EndTyping()
	{
		Typing = false;
		Debug.Log("Stopped typing");
	}

	public void ToggleFinances()
	{
		if (bUILock)
		{
			return;
		}
		if (!bRaiseUI)
		{
			RaiseUI("Finance", coPlayer);
		}
		else if (goUI != null)
		{
			if (goUI.GetComponent<GUIFinance>() != null)
			{
				LowerUI();
			}
			else
			{
				RaiseUI("Finance", coPlayer);
			}
		}
		else
		{
			LowerUI();
		}
	}

	public CondOwner GetRandomCrew(Tile til = null)
	{
		PersonSpec personSpec;
		if (coPlayer == null)
		{
			personSpec = new PersonSpec(DataHandler.GetPersonSpec("PlayerNew"), bNew: true);
			personSpec.nAgeMin = (personSpec.nAgeMax = 18);
		}
		else
		{
			personSpec = new PersonSpec(DataHandler.GetPersonSpec("NPCNew"), bNew: true);
		}
		return AddCrew(personSpec, til);
	}

	public void AddNpcToRoster(CondOwner co)
	{
		if (co == null)
		{
			return;
		}
		Hire hire = new Hire();
		Interaction interaction = DataHandler.GetInteraction("SOCHire2BasicAllow");
		interaction.objThem = co;
		interaction.objUs = coPlayer;
		hire.UpdateUs(interaction);
		interaction.objThem = coPlayer;
		interaction.objUs = co;
		hire.UpdateThem(interaction);
		foreach (CondTrigger item in interaction.LootCTsUs.GetCTLoot(null))
		{
			if (item != null && item.Triggered(co))
			{
				item.ApplyChanceID(bAdd: true, co);
			}
		}
		List<string> lootNames = DataHandler.GetLoot(interaction.strLootRELChangeThemSeesUs).GetLootNames();
		if (lootNames.Count > 0 && co.pspec != null && coPlayer.pspec != null)
		{
			foreach (string item2 in lootNames)
			{
				if (item2.IndexOf("-") == 0)
				{
					coPlayer.socUs.RemovePerson(co.pspec, new List<string> { item2.Substring(1) });
					continue;
				}
				string strNameFriendly = DataHandler.GetCond(item2).strNameFriendly;
				coPlayer.socUs.AddPerson(new Relationship(co.pspec, new List<string> { item2 }, new List<string> { "Became " + strNameFriendly + " during: " + interaction.strTitle }));
				_ = co.strName + " becomes a " + strNameFriendly + " to " + coPlayer.strName + ".";
				interaction.LogSocial(coPlayer.strName, item2, interaction.strTitle);
			}
		}
		lootNames = DataHandler.GetLoot(interaction.strLootRELChangeUsSeesThem).GetLootNames();
		if (lootNames.Count <= 0 || co.pspec == null || coPlayer.pspec == null)
		{
			return;
		}
		foreach (string item3 in lootNames)
		{
			if (item3.IndexOf("-") == 0)
			{
				co.socUs.RemovePerson(coPlayer.pspec, new List<string> { item3.Substring(1) });
				continue;
			}
			string strNameFriendly2 = DataHandler.GetCond(item3).strNameFriendly;
			co.socUs.AddPerson(new Relationship(coPlayer.pspec, new List<string> { item3 }, new List<string> { "Became " + strNameFriendly2 + " during: " + interaction.strTitle }));
			_ = coPlayer.strName + " becomes a " + strNameFriendly2 + " to " + co.strName + ".";
			interaction.LogSocial(coPlayer.strName, item3, interaction.strTitle);
		}
	}

	private CondOwner AddCrew(PersonSpec pspec, Tile til)
	{
		if (pspec == null || shipCurrentLoaded == null)
		{
			return null;
		}
		CondOwner condOwner = pspec.MakeCondOwner(PersonSpec.StartShip.OLD, shipCurrentLoaded);
		if (condOwner == null)
		{
			return null;
		}
		if (coPlayer == null)
		{
			coPlayer = condOwner;
			if (DataHandler.GetUserSettings().strNewPlayer == "true")
			{
				coPlayer.AddCondAmount("IsNewPlayer", 1.0);
			}
			coPlayer.AddCondAmount(GUIFinance.strCondCurr, MathUtils.Rand(95.2, 103.7, MathUtils.RandType.Flat));
			coPlayer.Company = new JsonCompany();
			coPlayer.Company.strName = coPlayer.strName + "'s Company";
			coPlayer.Company.mapRoster[coPlayer.strID] = new JsonCompanyRules();
			coPlayer.Company.strRegID = shipCurrentLoaded.strRegID;
			coPlayer.Company.mapRoster[coPlayer.strID].bShoreLeave = true;
			coPlayer.Company.mapRoster[coPlayer.strID].bAirlockPermission = false;
			coPlayer.Company.mapRoster[coPlayer.strID].bRestorePermission = true;
			coPlayer.Company.mapRoster[coPlayer.strID].bReplaceBatteries = true;
			coPlayer.Company.mapRoster[coPlayer.strID].bReplaceO2Bottles = true;
			coPlayer.Company.mapRoster[coPlayer.strID].bForbidUnwear = false;
			coPlayer.LogMessage("Welcome, Captain.", "Neutral", "Game");
			int nUTCHour = StarSystem.nUTCHour;
			coPlayer.Company.mapRoster[coPlayer.strID].SetAllHours(2);
			coPlayer.ShiftChange(coPlayer.Company.GetShift(nUTCHour, coPlayer), bSilent: true);
			AIManual(coPlayer.HasCond("IsAIManual"));
			MonoSingleton<ObjectiveTracker>.Instance.AddShipSubscription(shipCurrentLoaded.strRegID);
			CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsLootSpawner");
			List<CondOwner> cOs = shipCurrentLoaded.GetCOs(condTrigger, bSubObjects: false, bAllowDocked: false, bAllowLocked: true);
			for (int num = cOs.Count - 1; num >= 0; num--)
			{
				if (!(cOs[num].mapGUIPropMaps["Panel A"]["strType"] == "Loot") && !(cOs[num].mapGUIPropMaps["Panel A"]["strLoot"] != "PlayerNew"))
				{
					til = cOs[num].GetComponent<LootSpawner>().GetSpawnTile(shipCurrentLoaded);
					shipCurrentLoaded.RemoveCO(cOs[num]);
					break;
				}
			}
		}
		if (til == null)
		{
			til = shipCurrentLoaded.GetCrewSpawnTile(condOwner);
		}
		condOwner.ship.RemoveCO(condOwner);
		Vector3 position = default(Vector3);
		if (til != null)
		{
			position.Set(til.transform.position.x, til.transform.position.y, condOwner.transform.position.z);
		}
		condOwner.transform.position = position;
		shipCurrentLoaded.AddCO(condOwner, bTiles: true);
		condOwner.SetCrewZOffset();
		return condOwner;
	}

	public static void AddTicker(CondOwner co)
	{
		aTickers.Add(co);
	}

	public static void RemoveTicker(CondOwner co)
	{
		aTickers.Remove(co);
	}

	private void UpdateICOs()
	{
		CondOwner.nEndTurnsThisFrame = 0;
		aTickersTemp.AddRange(aTickers);
		foreach (CondOwner item in aTickersTemp)
		{
			if (item == null || item.ship == null || item.ship.bDestroyed || !item.ship.gameObject.activeInHierarchy)
			{
				RemoveTicker(item);
			}
			else
			{
				item.UpdateManual();
			}
		}
		aTickersTemp.Clear();
		if (fTotalGameSec - fUIUpdateLast > fUIUpdateHeartbeat)
		{
			fUIUpdateLast = fTotalGameSec;
		}
	}

	public void SetPartCursor(string strName)
	{
		if (strName != null)
		{
			if (goSelPart != null && goSelPart.transform.parent == null)
			{
				UnityEngine.Object.Destroy(goSelPart);
			}
			goSelPart = CreatePartFromName(strName);
		}
		else
		{
			UnityEngine.Object.Destroy(goSelPart);
			goSelPart = null;
			cgRotate.alpha = 0f;
		}
		TileUtils.ResetItemGridSprites();
	}

	private GameObject CreatePartFromName(string strName)
	{
		JsonItem jsonItem = new JsonItem();
		jsonItem.strName = strName;
		jsonItem.fX = vMouse.x;
		jsonItem.fY = vMouse.y;
		jsonItem.fRotation = 0f;
		GameObject gameObject = ((!bShipEditBG) ? shipCurrentLoaded.CreatePart(jsonItem, null, bLoot: true) : DataHandler.GetBackground(strName).gameObject);
		gameObject.layer = LayerMask.NameToLayer("Tile Helpers");
		cgRotate.alpha = 0.7f;
		rectRotate.Find("txt").GetComponent<TMP_Text>().text = InputManager.GetGlyphString("Rotate Item");
		return gameObject;
	}

	public void UnselectNonHumanTargets()
	{
		for (int num = aSelected.Count - 1; num >= 0; num--)
		{
			if (!aSelected[num].HasCond("IsHuman"))
			{
				SelectCO(aSelected[num], bUnselect: true);
			}
		}
	}

	public void SetBracketTarget(string strID, bool bUpdateOnly, bool noAuto = false)
	{
		if (bUpdateOnly && (aSelected.Count != 1 || aSelected[0] == null || aSelected[0].strID != strID))
		{
			return;
		}
		CondOwner[] array = new CondOwner[aSelected.Count];
		aSelected.CopyTo(array);
		CondOwner[] array2 = array;
		foreach (CondOwner condOwner in array2)
		{
			if (!(strID == condOwner.strID) && (!string.IsNullOrEmpty(strID) || !condOwner.HasCond("IsHuman")) && (!ZoneMenuOpen || !condOwner.HasCond("IsHuman")))
			{
				SelectCO(condOwner, bUnselect: true);
			}
		}
		array = null;
		if (GUIShipEdit.Instance != null)
		{
			GUIShipEdit.Instance.UpdateReplaceStrings(DataHandler.GetString("GUI_SHIPEDIT_REPLACE_FLOORS").Replace("XXX", "0"), DataHandler.GetString("GUI_SHIPEDIT_REPLACE_WALLS").Replace("XXX", "0"));
		}
		if (strID == null)
		{
			return;
		}
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsWall1x1InstalledOrMineable");
		CondTrigger condTrigger2 = DataHandler.GetCondTrigger("TIsFloorGrateOrFloorRock");
		CondOwner value = null;
		DataHandler.mapCOs.TryGetValue(strID, out value);
		if (value != null)
		{
			SelectCO(value);
			if (noAuto)
			{
				AIManual(manualMode: true);
			}
			string replaceFloor = (condTrigger.Triggered(value) ? DataHandler.GetString("GUI_SHIPEDIT_REPLACE_WALLS").Replace("XXX", "1") : null);
			string replaceWall = (condTrigger2.Triggered(value) ? DataHandler.GetString("GUI_SHIPEDIT_REPLACE_FLOORS").Replace("XXX", "1") : null);
			if (GUIShipEdit.Instance != null)
			{
				GUIShipEdit.Instance.UpdateReplaceStrings(replaceFloor, replaceWall);
			}
		}
	}

	public static CondOwner GetBracketTarget()
	{
		if (aSelected.Count == 1)
		{
			return aSelected[0];
		}
		return null;
	}

	public static CondOwner GetSelectedCrew()
	{
		if (aSelected != null && aSelected.Count > 0)
		{
			CondOwner condOwner = aSelected[0];
			if ((object)condOwner != null && condOwner.HasCond("IsHuman"))
			{
				return aSelected[0];
			}
		}
		return coPlayer;
	}

	public void UpdateLog(CondOwner co, string strColor)
	{
		if (co == null)
		{
			return;
		}
		CondOwner condOwner = coPlayer;
		if (aSelected.Count > 0)
		{
			condOwner = aSelected[0];
		}
		if (!(condOwner == co))
		{
			return;
		}
		if (condOwner.Crew != null)
		{
			MonoSingleton<GUIRenderTargets>.Instance.SetFace(condOwner);
		}
		string text = txtMessageLog.text;
		string messageLog = condOwner.GetMessageLog();
		if (text != messageLog)
		{
			txtMessageLog.text = messageLog;
			switch (strColor)
			{
			case "Bad":
			case "GoodRemove":
				AudioManager.am.PlayAudioEmitter("UIMessageLogBad", bLoop: false, bNoRestart: true);
				break;
			case "Dialogue":
				AudioManager.am.PlayAudioEmitter("UIMessageLogSocial", bLoop: false, bNoRestart: true);
				break;
			}
			StartCoroutine(ScrollBottom(srMessageLog));
		}
	}

	public void HighlightCOs(List<CondOwner> aHighlights)
	{
		if (aHighlights == null || aHighlights.Count == 0)
		{
			return;
		}
		aHidden.Clear();
		foreach (Ship aLoadedShip in aLoadedShips)
		{
			foreach (CondOwner item in aLoadedShip.GetICOs1(null, bSubObjects: false, bAllowDocked: false, bAllowLocked: false))
			{
				item.DimLights = true;
				aHidden.Add(item.strID);
			}
		}
		foreach (CondOwner aHighlight in aHighlights)
		{
			aHighlight.Highlight = true;
			if (!aHidden.Contains(aHighlight.strID))
			{
				aHidden.Add(aHighlight.strID);
			}
		}
	}

	public void UnhighlightCOs()
	{
		foreach (string item in aHidden)
		{
			CondOwner value = null;
			DataHandler.mapCOs.TryGetValue(item, out value);
			if (value != null)
			{
				value.Highlight = false;
				value.DimLights = false;
			}
		}
	}

	public void ShowInputSelector(CondTrigger ctVisible, GUIData igd)
	{
		Paused = true;
		bPauseLock = true;
		CanvasManager.CrewSimNormal();
		aHidden.Clear();
		foreach (Ship aLoadedShip in aLoadedShips)
		{
			foreach (CondOwner item in aLoadedShip.GetICOs1(null, bSubObjects: false, bAllowDocked: false, bAllowLocked: false))
			{
				if (ctVisible.Triggered(item))
				{
					item.Highlight = true;
				}
				else
				{
					item.DimLights = true;
				}
				aHidden.Add(item.strID);
			}
		}
		GameObject original = Resources.Load<GameObject>("prefabSignalLine");
		lineSignal = UnityEngine.Object.Instantiate(original).GetComponent<VectorObject2D>().vectorLine;
		lineSignal.SetCanvas(CanvasManager.goCanvasGUI, worldPositionStays: false);
		coConnectLastCrew = GetSelectedCrew();
		coConnectMode = igd.COSelf;
		ctSelectFilter = ctVisible;
		igdConnectMode = igd;
		nLastClickIndex = 0;
	}

	public void HideInputSelector()
	{
		UnhighlightCOs();
		VectorLine.Destroy(ref lineSignal);
		CanvasManager.ShipGUI();
		coConnectMode = null;
		ctSelectFilter = null;
		igdConnectMode = null;
		bPauseLock = false;
		Paused = false;
		nLastClickIndex = 0;
	}

	public List<CondOwner> GetMouseOverCOsExternal(Vector3? mousePosition = null)
	{
		CondTrigger condTrigger = ctSelectFilter;
		ctSelectFilter = DataHandler.GetCondTrigger("TCanBeSelectedMTT");
		List<CondOwner> mouseOverCO = GetMouseOverCO(_layerMaskDefLosTileHelpers, ctSelectFilter, mousePosition);
		Room room = null;
		if (shipCurrentLoaded != null)
		{
			room = shipCurrentLoaded.GetRoomAtWorldCoords1(vMouse, bAllowDocked: true);
		}
		if (room == null)
		{
			room = MonoSingleton<AsyncShipLoader>.Instance.GetRoomAtWorldCoords(vMouse);
		}
		if (room != null)
		{
			mouseOverCO.Remove(room.CO);
			mouseOverCO.Add(room.CO);
		}
		ctSelectFilter = condTrigger;
		return mouseOverCO;
	}

	private List<CondOwner> GetMouseOverCO(string[] aLayerMaskNames, CondTrigger ctFilter, Vector3? mousePosition = null)
	{
		int mask = LayerMask.GetMask(aLayerMaskNames);
		Vector2 mousePosition2 = InputManager.MousePosition;
		RaycastHit[] source = Physics.RaycastAll(mousePosition.HasValue ? ActiveCam.ScreenPointToRay(mousePosition.Value) : ActiveCam.ScreenPointToRay(mousePosition2), 100f, mask);
		List<CondOwner> list = new List<CondOwner>();
		CondOwner condOwner = null;
		foreach (RaycastHit item in source.OrderBy((RaycastHit go) => go.distance))
		{
			condOwner = item.transform.GetComponent<CondOwner>();
			if (condOwner != null && (ctFilter == null || ctFilter.Triggered(condOwner, null, logOutcome: false)))
			{
				list.Add(condOwner);
			}
		}
		return list;
	}

	private List<Item> GetMouseOverBG(string[] aLayerMaskNames)
	{
		int mask = LayerMask.GetMask(aLayerMaskNames);
		RaycastHit[] source = Physics.RaycastAll(camMain.ScreenPointToRay(InputManager.MousePosition), 100f, mask);
		List<Item> list = new List<Item>();
		RaycastHit[] array = source.OrderBy((RaycastHit go) => go.distance).ToArray();
		for (int num = 0; num < array.Length; num++)
		{
			RaycastHit raycastHit = array[num];
			if (!(raycastHit.transform.GetComponent<CondOwner>() != null))
			{
				Item component = raycastHit.transform.GetComponent<Item>();
				if (component != null)
				{
					list.Add(component);
				}
			}
		}
		return list;
	}

	private GameObject ClickSelectScenePart(string[] aLayerMaskNames)
	{
		List<CondOwner> mouseOverCO = GetMouseOverCO(aLayerMaskNames, ctSelectFilter);
		Ray ray = camMain.ScreenPointToRay(InputManager.MousePosition);
		CondOwner condOwner = null;
		Vector2 vector = new Vector2(TileUtils.GridAlign(ray.origin.x), TileUtils.GridAlign(ray.origin.y));
		if ((vector - vLastClick).SqrMagnitude() < 0.1f)
		{
			nLastClickIndex++;
			if (nLastClickIndex >= mouseOverCO.Count)
			{
				nLastClickIndex = 0;
			}
			if (nLastClickIndex < mouseOverCO.Count)
			{
				condOwner = mouseOverCO[nLastClickIndex];
			}
		}
		else
		{
			nLastClickIndex = mouseOverCO.Count - 1;
			vLastClick = vector;
			while (nLastClickIndex >= 0)
			{
				condOwner = mouseOverCO[nLastClickIndex];
				if (condOwner.objCOParent != null)
				{
					nLastClickIndex--;
					continue;
				}
				if (condOwner.Crew != null)
				{
					break;
				}
				nLastClickIndex--;
			}
			if (nLastClickIndex < 0)
			{
				nLastClickIndex = 0;
			}
		}
		if (condOwner != null)
		{
			if (CanvasManager.State == CanvasManager.GUIState.SOCIAL)
			{
				return GUISocialCombat2.coUs.gameObject;
			}
			SetBracketTarget(condOwner.strID, bUpdateOnly: false);
			return condOwner.gameObject;
		}
		return null;
	}

	public static void RaiseUI(string strCOGUIKey, CondOwner coSelf)
	{
		if (objInstance.coConnectMode != null || CanvasManager.State == CanvasManager.GUIState.SOCIAL || CanvasManager.State == CanvasManager.GUIState.GAMEOVER)
		{
			return;
		}
		if (GUIInventory.instance.Selected != null)
		{
			GetSelectedCrew().LogMessage(DataHandler.GetString("GUI_INV_NO_CLOSE"), "Bad", GetSelectedCrew().strID);
			AudioManager.am.PlayAudioEmitter("UIMessageLogBad", bLoop: false, bNoRestart: true);
			return;
		}
		CondOwner selectedCrew = GetSelectedCrew();
		if (selectedCrew != coSelf)
		{
			if (coSelf.ship.LoadState < Ship.Loaded.Edit)
			{
				return;
			}
			CondOwner condOwner = coSelf;
			if (!condOwner.IsHumanOrRobot)
			{
				Interaction interactionCurrent = coSelf.GetInteractionCurrent();
				if (interactionCurrent != null)
				{
					condOwner = interactionCurrent.objThem;
				}
			}
			if (condOwner.IsHumanOrRobot && condOwner.Company == coPlayer.Company && condOwner != selectedCrew)
			{
				objInstance.CycleCrew(condOwner);
				if (GetSelectedCrew() != condOwner)
				{
					return;
				}
			}
		}
		guiPDA.State = GUIPDA.UIState.Closed;
		CanvasManager.ShowOrbits(bShow: true);
		objInstance.LowerContextMenu();
		if (strCOGUIKey != "Inventory")
		{
			OnRightClick.Invoke(new List<CondOwner>());
		}
		Dictionary<string, string> dictionary = null;
		if (coSelf.mapGUIPropMaps == null || !coSelf.mapGUIPropMaps.ContainsKey(strCOGUIKey))
		{
			Debug.Log("No such GUI Key found on " + coSelf?.ToString() + "'s GUIPropMaps: " + strCOGUIKey);
			return;
		}
		dictionary = coSelf.mapGUIPropMaps[strCOGUIKey];
		RefreshTooltipEvent.Invoke();
		if (!dictionary.ContainsKey("strGUIPrefab"))
		{
			Debug.Log("No strGUIPrefab Key found on " + coSelf?.ToString() + "'s GUIPropMap named " + strCOGUIKey + ".");
			dictionary = null;
			return;
		}
		tplLastUI = tplCurrentUI;
		tplCurrentUI = new Ostranauts.Core.Models.Tuple<string, CondOwner>(strCOGUIKey, coSelf);
		if (dictionary["strGUIPrefab"] == "SocialCombat")
		{
			if (goUI != null)
			{
				LowerUI();
			}
			Interaction interactionCurrent2 = coSelf.GetInteractionCurrent();
			CondOwner objThem = interactionCurrent2.objThem;
			GUISocialCombat2.strSubUI = interactionCurrent2.strSubUI;
			if (coSelf.socUs != null)
			{
				Relationship relationship = coSelf.socUs.GetRelationship(objThem.strName);
				if (relationship != null && interactionCurrent2.strLootContextUs != null)
				{
					relationship.strContext = interactionCurrent2.strLootContextUs;
				}
			}
			if (objThem.socUs != null)
			{
				Relationship relationship2 = objThem.socUs.GetRelationship(coSelf.strName);
				if (relationship2 != null && interactionCurrent2.strLootContextThem != null)
				{
					relationship2.strContext = interactionCurrent2.strLootContextThem;
				}
			}
			if (interactionCurrent2.strThemType == Interaction.TARGET_OTHER && objThem == GetSelectedCrew())
			{
				CanvasManager.SocialCombat(objThem, coSelf, fDelayedPause: false);
				GUISocialCombat2.fPauseDelay = interactionCurrent2.fDuration * 3600.0 + 0.5;
				GUISocialCombat2.objInstance.ClearActions();
			}
			else
			{
				GUISocialCombat2.fPauseDelay = interactionCurrent2.fDuration * 3600.0 + 0.5;
				CanvasManager.SocialCombat(coSelf, objThem, fDelayedPause: true);
			}
			InputManager.ToggleMovementMode(forceOff: true);
			return;
		}
		if (strCOGUIKey == "Inventory")
		{
			if (!(coSelf != GetSelectedCrew()))
			{
				if (!inventoryGUI.IsOpen)
				{
					CommandInventory.ToggleInventory(coSelf);
				}
				inventoryGUI.SpawnInventoryWindow(coSelf.GetInteractionCurrent().objThem, InventoryWindowType.Container, null);
			}
			return;
		}
		InputManager.ToggleMovementMode(forceOff: true);
		string text = dictionary["strGUIPrefab"];
		if (text == "GUITrade/GUITrade2")
		{
			text = (dictionary["strGUIPrefab"] = "GUITrade/GUITrade");
		}
		GameObject gameObject = Resources.Load<GameObject>("GUIShip/" + text);
		if (gameObject != null)
		{
			objInstance.CloseGUIData();
			goUI = UnityEngine.Object.Instantiate(gameObject);
			goUI.transform.SetParent(goIntUIPanel.transform, worldPositionStays: false);
			coSelf.mapGUIRefs[strCOGUIKey] = goUI.GetComponent<IGUIHarness>();
			string text3 = dictionary["strGUIPrefab"];
			text3 = text3.Substring(text3.IndexOf("/") + 1);
			GUIData gUIData = goUI.GetComponent(text3) as GUIData;
			if (gUIData == null)
			{
				GUIData[] components = goUI.GetComponents<GUIData>();
				if (components != null)
				{
					GUIData[] array = components;
					int num = 0;
					if (num < array.Length)
					{
						gUIData = array[num];
					}
				}
				if (gUIData == null)
				{
					Debug.Log("Component " + text3 + " not found on GUIShip/" + dictionary["strGUIPrefab"] + ".");
				}
			}
			gUIData.Init(coSelf, dictionary, strCOGUIKey);
			goUI.GetComponent<Animator>().SetInteger("AnimState", 5);
			gUIData.bActive = true;
			EventSystem.current.sendNavigationEvents = false;
			UnityEngine.Object.Destroy(goDialogue);
			if ((bool)GUIModal.Instance)
			{
				GUIModal.Instance.Hide();
			}
			if (coPlayer != null && coPlayer.HasCond("IsInChargen"))
			{
				CanvasManager.ShipGUI(new List<GameObject> { CanvasManager.instance.goCanvasPDA });
			}
			else
			{
				CanvasManager.ShipGUI();
			}
			SetUIArrows();
		}
		else
		{
			Debug.Log("Unable to load resource: GUIShip/" + dictionary["strGUIPrefab"]);
			dictionary = null;
		}
	}

	public static void SetToggleWithoutNotify(Toggle chk, bool bValue)
	{
		if (!(chk == null))
		{
			Toggle.ToggleEvent onValueChanged = chk.onValueChanged;
			chk.onValueChanged = new Toggle.ToggleEvent();
			chk.isOn = bValue;
			chk.onValueChanged = onValueChanged;
		}
	}

	public static void LowerUI(bool bRestoreLastUI = false)
	{
		if (bUILock || goUI == null || !objInstance.CloseGUIData())
		{
			return;
		}
		EventSystem.current.sendNavigationEvents = true;
		EventSystem.current.SetSelectedGameObject(null);
		if (bRestoreLastUI && tplLastUI != null)
		{
			RaiseUI(tplLastUI.Item1, tplLastUI.Item2);
			return;
		}
		CanvasManager.ShowOrbits(bShow: false);
		if (bShipEdit)
		{
			CanvasManager.ShipEdit();
		}
		else
		{
			CanvasManager.CrewSimNormal();
		}
		RefreshTooltipEvent.Invoke();
	}

	private bool CloseGUIData()
	{
		if (goUI == null)
		{
			return true;
		}
		if (coConnectMode != null)
		{
			CloseConnectionMode();
		}
		GUIData component = goUI.GetComponent<GUIData>();
		if (component != null)
		{
			if (_commandEscape.InputAction.WasPressedThisFrame() && component.CloseOutermostWindow())
			{
				return false;
			}
			component.SaveAndClose();
		}
		UnityEngine.Object.Destroy(goUI);
		goUI = null;
		return true;
	}

	public static void SetMainMenuOff()
	{
		tgMenu.SetAllTogglesOff();
	}

	public static void SwitchUI(string strDirection)
	{
		if (!(goUI == null))
		{
			goUI = goUI.GetComponent<IGUIHarness>().GoDir(strDirection);
			SetUIArrows();
			GUIData component = goUI.GetComponent<GUIData>();
			if (component != null)
			{
				component.UpdateUI();
			}
			AudioManager.am.PlayAudioEmitter("UIPanelSwitch", bLoop: false);
		}
	}

	public static void SetUIArrows()
	{
		btnCPBottom.gameObject.SetActive(value: false);
		btnCPTop.gameObject.SetActive(value: false);
		btnCPLeft.gameObject.SetActive(value: false);
		btnCPRight.gameObject.SetActive(value: false);
		btnCPExit.gameObject.SetActive(!bUILock);
		string text = DataHandler.GetString("GUI_NAV_SWITCH");
		if (goUI.GetComponent<IGUIHarness>().goUIBottom != null)
		{
			btnCPBottom.gameObject.SetActive(value: true);
			GUIData component = goUI.GetComponent<IGUIHarness>().goUIBottom.GetComponent<GUIData>();
			btnCPBottom.transform.Find("txt").GetComponent<TMP_Text>().text = text + component.strFriendlyName;
		}
		if (goUI.GetComponent<IGUIHarness>().goUITop != null)
		{
			btnCPTop.gameObject.SetActive(value: true);
			GUIData component2 = goUI.GetComponent<IGUIHarness>().goUITop.GetComponent<GUIData>();
			btnCPTop.transform.Find("txt").GetComponent<TMP_Text>().text = text + component2.strFriendlyName;
		}
		if (goUI.GetComponent<IGUIHarness>().goUILeft != null)
		{
			btnCPLeft.gameObject.SetActive(value: true);
			GUIData component3 = goUI.GetComponent<IGUIHarness>().goUILeft.GetComponent<GUIData>();
			btnCPLeft.transform.Find("txt").GetComponent<TMP_Text>().text = text + component3.strFriendlyName;
		}
		if (goUI.GetComponent<IGUIHarness>().goUIRight != null)
		{
			btnCPRight.gameObject.SetActive(value: true);
			GUIData component4 = goUI.GetComponent<IGUIHarness>().goUIRight.GetComponent<GUIData>();
			btnCPRight.transform.Find("txt").GetComponent<TMP_Text>().text = text + component4.strFriendlyName;
		}
	}

	public static void DockAndDespawn(Ship shipAI, Ship shipStation, string issuerRegId = null)
	{
		if (shipAI == null || shipStation == null)
		{
			return;
		}
		List<CondOwner> people = shipAI.GetPeople(bAllowDocked: true);
		for (int num = people.Count - 1; num >= 0; num--)
		{
			CondOwner condOwner = people[num];
			condOwner.CatchUp(bSubItems: true);
			condOwner.UnclaimShip(shipAI.strRegID);
			List<string> aFactionsThem = (from x in shipStation.GetShipFactions()
				select x.strName).ToList();
			float factionScore = condOwner.GetFactionScore(aFactionsThem);
			CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsValidStationDropOff");
			if ((condTrigger != null && !condTrigger.Triggered(condOwner)) || JsonFaction.GetReputation(factionScore) == JsonFaction.Reputation.Dislikes)
			{
				shipAI.LogAdd(condOwner.strID + DataHandler.GetString("NAV_LOG_CREW_DESTROY") + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
				condOwner.Destroy();
			}
			else
			{
				condOwner.LogMove(shipAI.strRegID, shipStation.strRegID, MoveReason.DOCKED, issuerRegId);
				shipAI.LogAdd(condOwner.strID + DataHandler.GetString("NAV_LOG_CREW_TRANSFER") + shipStation.strRegID + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
				MoveCO(condOwner, shipStation, bPlayerShip: false);
				condOwner.ClaimShip(shipStation.strRegID);
				condOwner.ZeroCondAmount("IsShakedownModeActive");
				if (condOwner.Company != null)
				{
					condOwner.Company.SetPermissionAirlock(condOwner.strID, bAllowed: false);
					condOwner.Company.SetPermissionShore(condOwner.strID, bAllowed: false);
					condOwner.Company.SetPermissionRestore(condOwner.strID, bAllowed: false);
					condOwner.Company.SetPermissionBatteries(condOwner.strID, bAllowed: false);
					condOwner.Company.SetPermissionO2Bottles(condOwner.strID, bAllowed: false);
					condOwner.Company.SetPermissionUnwearHelmet(condOwner.strID, bAllowed: true);
					if (condOwner.Company != coPlayer.Company && condOwner.Company.jcrDefaultRules != null)
					{
						condOwner.Company.jcrDefaultRules.SetAllHours(0);
					}
				}
				if (!condOwner.HasQueuedInteraction("WanderSoon"))
				{
					Interaction interaction = DataHandler.GetInteraction("WanderSoon");
					condOwner.QueueInteraction(condOwner, interaction);
				}
			}
		}
		shipAI.LogAdd(DataHandler.GetString("NAV_LOG_DOCKDESPAWN") + shipStation.strRegID + DataHandler.GetString("NAV_LOG_TERMINATOR"), StarSystem.fEpoch, bShowEpoch: true);
		shipAI.ToggleVis(bShow: false);
		shipAI.HideFromSystem = true;
		shipAI.strAIDespawnedAt = shipStation.strRegID;
		AIShipManager.UnregisterShip(shipAI);
	}

	public static void UnMoorShip(Ship shipUs, Ship objShipThem)
	{
		shipUs.UnMoorFrom(objShipThem);
		coPlayer.AddCondAmount("IsUndockGracePeriodMajor", 1.0);
		if (objShipThem.IsAIShip)
		{
			AIShipManager.LEOCheckIllegalUndock(shipUs, objShipThem);
			AIShipManager.ValidateCrew(objShipThem);
		}
		while (objShipThem.nGridRotation != 0)
		{
			TileUtils.TrimTiles(objShipThem);
			objShipThem.RotateCW();
		}
		objInstance.SaveToShallow(objShipThem);
		IReadOnlyList<Ship> allDockedShips = shipUs.GetAllDockedShips();
		for (int num = aLoadedShips.Count - 1; num >= 0; num--)
		{
			Ship loadedShip = aLoadedShips[num];
			if (loadedShip != null && loadedShip != shipUs && !allDockedShips.Any((Ship x) => x != null && x.strRegID == loadedShip.strRegID))
			{
				while (loadedShip.nGridRotation != 0)
				{
					TileUtils.TrimTiles(loadedShip);
					loadedShip.RotateCW();
				}
				objInstance.SaveToShallow(loadedShip);
			}
		}
		MonoSingleton<AsyncShipLoader>.Instance.Unload();
		TileUtils.TrimAllSides(shipUs);
	}

	public static void MoorAddDockingPorts(Ship mooringTarget, out string portIDTarget, Ship incomingShip, out string portIDIncoming)
	{
		List<JsonItem> list = mooringTarget.CreateMooringPorts(incomingShip);
		if (list == null)
		{
			Debug.LogWarning("Could not generare docking ports for " + mooringTarget.strRegID);
			portIDTarget = null;
			portIDIncoming = null;
			return;
		}
		if (mooringTarget.LoadState >= Ship.Loaded.Edit)
		{
			CondOwner component = mooringTarget.CreatePart(list[0], list[0].strID, bLoot: false).GetComponent<CondOwner>();
			mooringTarget.AddCO(component, bTiles: true);
			portIDTarget = component.strID;
		}
		else
		{
			List<JsonItem> list2 = mooringTarget.json.aItems.ToList();
			list2.Add(list[0]);
			mooringTarget.json.aItems = list2.ToArray();
			portIDTarget = list[0].strID;
		}
		if (incomingShip.LoadState >= Ship.Loaded.Edit)
		{
			CondOwner component2 = incomingShip.CreatePart(list[1], list[1].strID, bLoot: false).GetComponent<CondOwner>();
			incomingShip.AddCO(component2, bTiles: true);
			portIDIncoming = component2.strID;
		}
		else
		{
			List<JsonItem> list3 = incomingShip.json.aItems.ToList();
			list3.Add(list[1]);
			incomingShip.json.aItems = list3.ToArray();
			portIDIncoming = list[1].strID;
		}
	}

	public static Ship MoorShip(Ship loaded, Ship incoming, bool moorLoadedToIncoming)
	{
		MoorAddDockingPorts(incoming, out var portIDTarget, loaded, out var portIDIncoming);
		if (string.IsNullOrEmpty(portIDTarget) || string.IsNullOrEmpty(portIDIncoming))
		{
			return null;
		}
		return MoorShip(new DockingPortDTO(loaded, portIDIncoming), new DockingPortDTO(incoming, portIDTarget), moorLoadedToIncoming);
	}

	public static Ship MoorShip(DockingPortDTO loaded, DockingPortDTO incoming, bool moorLoadedToIncoming)
	{
		bool flag = false;
		Ship ship = system.GetShipByRegID(incoming.RegID) ?? system.SpawnShipFromStellarObject(incoming.RegID);
		if (ship != null)
		{
			flag = ship.LoadState >= Ship.Loaded.Edit;
		}
		ship = system.SpawnShip(incoming.RegID, Ship.Loaded.Full);
		if (loaded.PortID == null || incoming.PortID == null)
		{
			if (moorLoadedToIncoming)
			{
				MoorAddDockingPorts(ship, out incoming.PortID, loaded.Ship, out loaded.PortID);
			}
			else
			{
				MoorAddDockingPorts(loaded.Ship, out loaded.PortID, ship, out incoming.PortID);
			}
		}
		if (string.IsNullOrEmpty(incoming.PortID) || string.IsNullOrEmpty(loaded.PortID))
		{
			objInstance.SaveToShallow(ship);
			return null;
		}
		objInstance.SyncFuelDelayed(ship);
		if (!flag)
		{
			CondOwnerVisitorCatchUp visitor = new CondOwnerVisitorCatchUp();
			ship.VisitCOs(visitor, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		}
		DockingSetVisibility(ship);
		if (moorLoadedToIncoming)
		{
			loaded.Ship.MoorTo(ship, incoming.PortID, loaded.PortID);
		}
		else
		{
			ship.MoorTo(loaded.Ship, loaded.PortID, incoming.PortID);
		}
		if (GUIDockSys.instance != null)
		{
			GUIDockSys.instance.ShowTarget();
		}
		loaded.Ship.Comms.Clearance = null;
		ship.Comms.Clearance = null;
		DockingUpdateNavStations(loaded.Ship, ship);
		if (!PositionShipsAtAirlock(loaded, incoming))
		{
			Debug.LogWarning("No matching docking port found " + ship.strRegID + " into " + loaded.RegID + " port us: " + loaded.PortID + " port them: " + incoming.PortID);
			return null;
		}
		PositionDockedShips(ship, loaded.Ship);
		CrimeManager.ClearCrimeFlags(ship.strLaw, loaded.Ship.GetPeople(bAllowDocked: false));
		objInstance.ForceUpdateAnimators();
		return ship;
	}

	private static void PositionDockedShips(Ship shipDocked, Ship exclude)
	{
		foreach (KeyValuePair<string, Ship> dockedShipsAndPortID in shipDocked.GetDockedShipsAndPortIDs())
		{
			if (dockedShipsAndPortID.Value != exclude)
			{
				PositionShipsAtAirlock(shipDocked, dockedShipsAndPortID.Value, dockedShipsAndPortID.Value.GetPortIdForDockedShip(shipDocked.strRegID), dockedShipsAndPortID.Key);
				PositionDockedShips(dockedShipsAndPortID.Value, shipDocked);
			}
		}
	}

	public static Ship DockShip(Ship shipUs, string strRegID, string airLockIdThem = null, string airLockIdUs = null, Clearance clearance = null)
	{
		shipUs.ResetDockedCache();
		shipUs.UnlockFromOrbit();
		bool flag = false;
		Ship shipByRegID = system.GetShipByRegID(strRegID);
		if (shipByRegID != null)
		{
			flag = shipByRegID.LoadState >= Ship.Loaded.Edit;
		}
		shipByRegID = system.SpawnShip(strRegID, Ship.Loaded.Full);
		string text = null;
		if (string.IsNullOrEmpty(airLockIdThem) && clearance == null)
		{
			List<(string, string)> availableDockingPorts = shipByRegID.GetAvailableDockingPorts(shipUs);
			if (availableDockingPorts == null || availableDockingPorts.Count <= 0)
			{
				Debug.LogWarning(shipByRegID.strRegID + " could not find a valid docking port for " + shipUs.strRegID + ", shipus primary: " + shipUs.PrimaryDockingPortID);
				return null;
			}
			text = availableDockingPorts.First().Item1;
			if (airLockIdUs != null)
			{
				Debug.LogWarning(shipUs.strRegID + " airlockID not null, but airlockID them (" + strRegID + ") was");
			}
			airLockIdUs = availableDockingPorts.First().Item2;
		}
		else
		{
			text = airLockIdThem ?? clearance.DockID;
		}
		if (string.IsNullOrEmpty(text))
		{
			string text2 = ((clearance == null) ? "Clearance was null" : clearance.DockID);
			Debug.LogWarning(shipUs.strRegID + " Airlock id null for " + shipByRegID.strRegID + " Clearance: " + text2);
			return null;
		}
		objInstance.SyncFuelDelayed(shipByRegID);
		if (!flag)
		{
			CondOwnerVisitorCatchUp visitor = new CondOwnerVisitorCatchUp();
			shipByRegID.VisitCOs(visitor, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		}
		DockingSetVisibility(shipByRegID);
		CrimeManager.ClearCrimeFlags(shipByRegID.strLaw, shipUs.GetPeople(bAllowDocked: false));
		DockingCheckTutorials(shipByRegID);
		objInstance.ForceUpdateAnimators();
		foreach (CondOwner person in shipByRegID.GetPeople(bAllowDocked: false))
		{
			if (!person.bDestroyed && !person.HasCond("Unconscious") && objInstance.FinishedLoading && JsonFaction.GetReputation(person.GetFactionScore(GetSelectedCrew().GetAllFactions())) == JsonFaction.Reputation.Dislikes)
			{
				JsonPledge pledge = DataHandler.GetPledge("AICombatBoarding");
				if (pledge != null)
				{
					Pledge2 pledge2 = PledgeFactory.Factory(person, pledge, GetSelectedCrew());
					pledge2?.Us.AddPledge(pledge2);
				}
			}
		}
		if (GUIDockSys.instance != null)
		{
			GUIDockSys.instance.ShowTarget();
		}
		shipUs.Comms.Clearance = null;
		shipByRegID.Comms.Clearance = null;
		DockingUpdateNavStations(shipUs, shipByRegID);
		if (shipUs.GetAllDockedShips().Contains(shipByRegID))
		{
			return shipByRegID;
		}
		if (string.IsNullOrEmpty(airLockIdUs))
		{
			airLockIdUs = shipUs.PrimaryDockingPortID;
		}
		if (string.IsNullOrEmpty(airLockIdUs))
		{
			Debug.LogWarning(shipUs.strRegID + " Airlock id null on us for " + shipByRegID.strRegID);
			return null;
		}
		shipUs.Dock(shipByRegID, bSyncOnly: false, text, airLockIdUs);
		bool num = PositionShipsAtAirlock(shipUs, shipByRegID, text, airLockIdUs);
		PositionDockedShips(shipByRegID, shipUs);
		if (!num)
		{
			Debug.LogWarning("Target: " + shipByRegID.strRegID + ", No matching docking port found! PortID them:" + text + " PortID us:" + airLockIdUs);
			return null;
		}
		return shipByRegID;
	}

	private static void DockingSetVisibility(Ship objShipNew)
	{
		objShipNew.gameObject.transform.SetParent(objInstance.transform, worldPositionStays: false);
		objShipNew.ToggleVis(bShow: true);
		if (objShipNew.fLastVisit == 0.0)
		{
			objShipNew.fLastVisit = -1.0;
		}
		if (objShipNew.fFirstVisit == 0.0)
		{
			objShipNew.fFirstVisit = StarSystem.fEpoch;
			objShipNew.nInitConstructionProgress = objShipNew.nConstructionProgress;
		}
	}

	private static void DockingCheckTutorials(Ship objShipNew)
	{
		if (objShipNew.objSS.bIsBO && coPlayer != null && coPlayer.HasCond("TutorialNoStationYet"))
		{
			coPlayer.AddCondAmount("TutorialNoStationYet", 0.0 - coPlayer.GetCondAmount("TutorialNoStationYet"));
		}
		if (coPlayer != null && coPlayer.HasCond("TutorialNoDockedYet"))
		{
			coPlayer.AddCondAmount("TutorialNoDockedYet", 0.0 - coPlayer.GetCondAmount("TutorialNoDockedYet"));
		}
		if (objShipNew.DMGStatus == Ship.Damage.Derelict && !objShipNew.ShipCO.HasCond("IsTutorialDerelictHidden"))
		{
			bool num = BeatManager.RunEncounter("ENCFirstDockDerelict", bInterrupt: true);
			if (num)
			{
				DataHandler.GetUserSettings().strNewPlayer = "false";
				DataHandler.SaveUserSettings();
			}
			if (!num && coPlayer != null && !coPlayer.HasCond("TutorialZonesStart"))
			{
				string glyphString = InputManager.GetGlyphString("Toggle zone UI");
				Objective objective = new Objective(coPlayer, "Open Zones Menu", "TIsTutorialOpenZonesComplete");
				objective.strDisplayDesc = "Press the \"" + glyphString + "\" key to open the zones menu";
				objective.strDisplayDescComplete = "Zone menu opened";
				objective.bTutorial = true;
				MonoSingleton<ObjectiveTracker>.Instance.AddObjective(objective);
				coPlayer.AddCondAmount("TutorialZonesStart", 1.0);
			}
		}
		else if (objShipNew.IsStation())
		{
			BeatManager.ResetReleaseTimer();
		}
	}

	private static void DockingUpdateNavStations(Ship shipUs, Ship objShipNew)
	{
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsNavStationNotOff");
		List<CondOwner> iCOs = shipUs.GetICOs1(condTrigger, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		foreach (Ship item in new List<Ship>(objShipNew.GetAllDockedShips()) { objShipNew })
		{
			if (item == null)
			{
				continue;
			}
			ShipInfo si = new ShipInfo(item, bForceReveal: true);
			foreach (CondOwner item2 in iCOs)
			{
				Dictionary<string, string> value = null;
				item2.mapGUIPropMaps.TryGetValue("Panel A", out value);
				ShipInfo.SetShipInfo(si, value);
			}
			GUIOrbitDraw gUIOrbitDraw = null;
			if (goUI != null)
			{
				gUIOrbitDraw = goUI.GetComponent<GUIOrbitDraw>();
			}
			if (gUIOrbitDraw != null)
			{
				gUIOrbitDraw.UpdateShipInfo(si);
			}
			GUIDockSys gUIDockSys = null;
			if (goUI != null)
			{
				gUIDockSys = goUI.GetComponent<GUIDockSys>();
			}
			if (gUIDockSys != null)
			{
				gUIDockSys.UpdateShipInfo(si);
			}
		}
		List<Ship> obj = new List<Ship>(shipUs.GetAllDockedShips()) { shipUs };
		iCOs = objShipNew.GetICOs1(condTrigger, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		foreach (Ship item3 in obj)
		{
			if (item3 == null)
			{
				continue;
			}
			ShipInfo si2 = new ShipInfo(item3, bForceReveal: true);
			foreach (CondOwner item4 in iCOs)
			{
				Dictionary<string, string> value2 = null;
				item4.mapGUIPropMaps.TryGetValue("Panel A", out value2);
				ShipInfo.SetShipInfo(si2, value2);
			}
		}
	}

	public static bool PositionShipsNearby(Ship shipUs, Ship objShipNew)
	{
		List<CondOwner> iCOs = shipUs.GetICOs1(CTDockSys, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		if (iCOs.Count == 0)
		{
			return false;
		}
		CondOwner condOwner = iCOs[0];
		iCOs = objShipNew.GetICOs1(CTDockingRef, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		if (iCOs.Count == 0)
		{
			return false;
		}
		CondOwner condOwner2 = iCOs[0];
		int num = MathUtils.RoundToInt(57.29578f * objShipNew.objSS.RotationNormalized / 90f) * 90;
		float num2 = condOwner2.transform.rotation.eulerAngles.z;
		if (num2 % 90f != 0f)
		{
			Debug.LogWarning("Dock B reference CO (" + condOwner2.strCODef + ") on ship " + objShipNew.strRegID + " has non-90-degree rotation. Assuming 0.");
			num2 = 0f;
		}
		int num3 = 0;
		num2 = MathUtils.RoundToInt((num2 % 360f + 360f) % 360f);
		if (num2 < (float)num)
		{
			num2 += 360f;
		}
		while ((float)num - num2 != 0f)
		{
			num2 -= 90f;
			num3++;
		}
		while (num3 > 0)
		{
			objShipNew.RotateCW();
			num3--;
		}
		Vector2 pos = condOwner.GetPos("DockA");
		Vector2 zero = Vector2.zero;
		if (condOwner.transform.rotation.eulerAngles.z % 360f == 0f)
		{
			float num4 = objInstance.FindLowestCoord(objShipNew).y - 1f;
			zero = new Vector2(pos.x - (objShipNew.vShipPos.x + (float)MathUtils.RoundToInt((float)objShipNew.nCols / 2f)), pos.y - num4);
		}
		else if (condOwner.transform.rotation.eulerAngles.z % 360f == 90f)
		{
			float num5 = objInstance.FindLowestCoord(objShipNew).x - 1f;
			zero = new Vector2(MathUtils.RoundToInt(pos.x - (num5 + (float)objShipNew.nCols)), pos.y - (objShipNew.vShipPos.y - (float)MathUtils.RoundToInt((float)objShipNew.nRows / 2f)));
		}
		else if (condOwner.transform.rotation.eulerAngles.z % 360f == 180f)
		{
			zero = new Vector2(pos.x - (objShipNew.vShipPos.x + (float)MathUtils.RoundToInt((float)objShipNew.nCols / 2f)), pos.y - 1f - objShipNew.vShipPos.y);
		}
		else
		{
			Vector4 vector = objInstance.FindLowestCoord(objShipNew);
			float x = vector.x;
			zero = new Vector2(MathUtils.RoundToInt(pos.x + 1f - x), pos.y - (vector.y + (float)MathUtils.RoundToInt((float)objShipNew.nRows / 2f)));
		}
		objShipNew.MoveShip(zero);
		return true;
	}

	private Vector4 FindLowestCoord(Ship ship)
	{
		int num = int.MaxValue;
		int num2 = int.MaxValue;
		int num3 = int.MinValue;
		int num4 = int.MinValue;
		foreach (CondOwner cO in ship.GetCOs(null, bSubObjects: false, bAllowDocked: false, bAllowLocked: false))
		{
			if (!(cO == null))
			{
				if (cO.tf.position.x < (float)num2)
				{
					num2 = (int)cO.tf.position.x;
				}
				if (cO.tf.position.y < (float)num)
				{
					num = (int)cO.tf.position.y;
				}
				if (cO.tf.position.x > (float)num3)
				{
					num3 = (int)cO.tf.position.x;
				}
				if (cO.tf.position.y > (float)num4)
				{
					num4 = (int)cO.tf.position.y;
				}
			}
		}
		return new Vector4(num2, num, num3, num4);
	}

	private static bool PositionShipsAtAirlock(DockingPortDTO staticPort, DockingPortDTO incomingPort)
	{
		if (incomingPort.PortID == null)
		{
			return false;
		}
		CondTrigger condTrigger = new CondTrigger();
		condTrigger.aReqs = new string[1] { "IsDockSys" };
		CondTrigger objCondTrig = condTrigger;
		List<CondOwner> iCOs = staticPort.Ship.GetICOs1(objCondTrig, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		if (iCOs.Count == 0)
		{
			return false;
		}
		CondOwner condOwner = null;
		foreach (CondOwner item in iCOs)
		{
			if (item.strID == staticPort.PortID)
			{
				condOwner = item;
				break;
			}
		}
		if (condOwner == null)
		{
			return false;
		}
		iCOs = incomingPort.Ship.GetICOs1(objCondTrig, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		if (iCOs.Count == 0)
		{
			return false;
		}
		CondOwner condOwner2 = null;
		foreach (CondOwner item2 in iCOs)
		{
			if (item2.strID == incomingPort.PortID)
			{
				condOwner2 = item2;
				break;
			}
		}
		if (condOwner2 == null)
		{
			return false;
		}
		float z = condOwner.transform.rotation.eulerAngles.z;
		float z2 = condOwner2.transform.rotation.eulerAngles.z;
		int num = 0;
		z = (z % 360f + 360f) % 360f;
		z2 = (z2 % 360f + 360f) % 360f;
		if (z2 < z)
		{
			z2 += 360f;
		}
		while (z - z2 < 180f)
		{
			z2 -= 90f;
			num++;
		}
		while (num > 0)
		{
			incomingPort.Ship.RotateCW();
			num--;
		}
		Vector2 pos = condOwner.GetPos("DockA");
		Vector2 pos2 = condOwner2.GetPos("DockB");
		incomingPort.Ship.MoveShip(new Vector2(pos.x - pos2.x, pos.y - pos2.y));
		return true;
	}

	private static bool PositionShipsAtAirlock(Ship shipUs, Ship objShipNew, string dockingPortShipNew, string dockingPortUs)
	{
		if (dockingPortShipNew == null)
		{
			return false;
		}
		CondTrigger condTrigger = new CondTrigger();
		condTrigger.aReqs = new string[1] { "IsDockSys" };
		CondTrigger objCondTrig = condTrigger;
		List<CondOwner> iCOs = shipUs.GetICOs1(objCondTrig, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		if (iCOs.Count == 0)
		{
			Debug.LogWarning("No airlocks on ship " + shipUs.strRegID);
			return false;
		}
		CondOwner condOwner = null;
		foreach (CondOwner item in iCOs)
		{
			if (item.strID == dockingPortUs)
			{
				condOwner = item;
				break;
			}
		}
		if (condOwner == null)
		{
			Debug.LogWarning($"Could not find shipUs's docking system CO with ID {dockingPortUs} aCos: {iCOs.Count}");
			return false;
		}
		iCOs = objShipNew.GetICOs1(objCondTrig, bSubObjects: false, bAllowDocked: false, bAllowLocked: false);
		if (iCOs.Count == 0)
		{
			return false;
		}
		CondOwner condOwner2 = null;
		foreach (CondOwner item2 in iCOs)
		{
			if (item2.strID == dockingPortShipNew)
			{
				condOwner2 = item2;
				break;
			}
		}
		if (condOwner2 == null)
		{
			Debug.LogWarning($"Could not find objShipNew's docking system CO with ID {dockingPortShipNew} aCos: {iCOs.Count}");
			return false;
		}
		float z = condOwner.transform.rotation.eulerAngles.z;
		float z2 = condOwner2.transform.rotation.eulerAngles.z;
		int num = 0;
		z = (z % 360f + 360f) % 360f;
		z2 = (z2 % 360f + 360f) % 360f;
		if (z2 < z)
		{
			z2 += 360f;
		}
		while (z - z2 < 180f)
		{
			z2 -= 90f;
			num++;
		}
		while (num > 0)
		{
			objShipNew.RotateCW();
			num--;
		}
		Vector2 pos = condOwner.GetPos("DockA");
		Vector2 pos2 = condOwner2.GetPos("DockB");
		objShipNew.MoveShip(new Vector2(pos.x - pos2.x, pos.y - pos2.y));
		condOwner.SetCondAmount("IsDockSysInUse", 1.0);
		condOwner2.SetCondAmount("IsDockSysInUse", 1.0);
		return true;
	}

	private void SyncFuelDelayed(Ship ship)
	{
		StartCoroutine(_SyncFuel(ship));
	}

	private IEnumerator _SyncFuel(Ship ship)
	{
		yield return new WaitForEndOfFrame();
		yield return new WaitForEndOfFrame();
		yield return new WaitForEndOfFrame();
		if (ship != null && ship.LoadState >= Ship.Loaded.Full)
		{
			ship.SyncFuel();
		}
	}

	public static void UndockShip(Ship shipUs, Ship objShipThem, bool bPushback, bool keepClearance = false)
	{
		shipUs.ResetDockedCache();
		shipUs.Undock(objShipThem);
		if (!keepClearance)
		{
			shipUs.Comms.Clearance = null;
			objShipThem.Comms.Clearance = null;
		}
		if (objShipThem.IsStation())
		{
			coPlayer.AddCondAmount("IsUndockGracePeriodMajor", 1.0);
		}
		else
		{
			coPlayer.AddCondAmount("IsUndockGracePeriodMinor", 1.0);
		}
		AudioManager.am.SuggestMusic("Undocking");
		if (bPushback)
		{
			shipUs.objSS.PushbackFrom(objShipThem);
			shipUs.UpdateDockedShips(shipUs.objSS, shipUs.Gravity);
		}
		if (objShipThem.IsAIShip)
		{
			AIShipManager.LEOCheckIllegalUndock(shipUs, objShipThem);
			AIShipManager.ValidateCrew(objShipThem);
		}
		if (objShipThem.LoadState >= Ship.Loaded.Full)
		{
			while (objShipThem.nGridRotation != 0)
			{
				TileUtils.TrimTiles(objShipThem);
				objShipThem.RotateCW();
			}
		}
		ClearUnusedAirlockFlags(objShipThem);
		objInstance.SaveToShallow(objShipThem);
		foreach (KeyValuePair<string, Ship> dockedShipsAndPortID in shipUs.GetDockedShipsAndPortIDs())
		{
			if (dockedShipsAndPortID.Key.Contains("MP|"))
			{
				shipUs.UnMoorFrom(dockedShipsAndPortID.Value);
			}
		}
		IReadOnlyList<Ship> allDockedShips = shipUs.GetAllDockedShips();
		for (int num = aLoadedShips.Count - 1; num >= 0; num--)
		{
			Ship loadedShip = aLoadedShips[num];
			if (loadedShip != null && loadedShip != shipUs && !allDockedShips.Any((Ship x) => x != null && x.strRegID == loadedShip.strRegID))
			{
				if (loadedShip.LoadState >= Ship.Loaded.Full)
				{
					while (loadedShip.nGridRotation != 0)
					{
						TileUtils.TrimTiles(loadedShip);
						loadedShip.RotateCW();
					}
				}
				objInstance.SaveToShallow(loadedShip);
			}
		}
		MonoSingleton<AsyncShipLoader>.Instance.Unload();
		ClearUnusedAirlockFlags(shipUs);
		if (shipUs.LoadState >= Ship.Loaded.Full)
		{
			TileUtils.TrimAllSides(shipUs);
		}
	}

	private static void ClearUnusedAirlockFlags(Ship shipUs)
	{
		if (shipUs == null || shipUs.aDocksys == null)
		{
			return;
		}
		Dictionary<string, Ship> dockedShipsAndPortIDs = shipUs.GetDockedShipsAndPortIDs();
		foreach (CondOwner aDocksy in shipUs.aDocksys)
		{
			if (!dockedShipsAndPortIDs.ContainsKey(aDocksy.strID))
			{
				aDocksy.ZeroCondAmount("IsDockSysInUse");
			}
		}
	}

	public static void UndockShipInverse(Ship shipUs, Ship pushbackTarget, bool keepClearance = false)
	{
		Dictionary<string, Ship> dockedShipsAndPortIDs = shipUs.GetDockedShipsAndPortIDs();
		foreach (KeyValuePair<string, Ship> item in dockedShipsAndPortIDs)
		{
			Ship value = item.Value;
			shipUs.Undock(value);
			if (!keepClearance)
			{
				value.Comms.Clearance = null;
			}
		}
		if (!keepClearance)
		{
			shipUs.Comms.Clearance = null;
		}
		if (pushbackTarget != null)
		{
			shipUs.objSS.PushbackFrom(pushbackTarget);
		}
		if (shipUs.LoadState >= Ship.Loaded.Full)
		{
			while (shipUs.nGridRotation != 0)
			{
				TileUtils.TrimTiles(shipUs);
				shipUs.RotateCW();
			}
			TileUtils.TrimAllSides(shipUs);
		}
		objInstance.SaveToShallow(shipUs);
		foreach (KeyValuePair<string, Ship> item2 in dockedShipsAndPortIDs)
		{
			if (item2.Key.Contains("MP|"))
			{
				item2.Value.UnMoorFrom(shipUs);
			}
		}
	}

	public void SaveToShallow(Ship ship)
	{
		if (ship == null || ship.bDestroyed)
		{
			return;
		}
		string strRegID = ship.strRegID;
		if (ship.Classification == Ship.TypeClassification.SignalBeacon)
		{
			CondOwner cOFirstOccurrence = ship.GetCOFirstOccurrence(DataHandler.GetCondTrigger("TIsSignalBeaconInstalled"), bSubObjects: false, bAllowDocked: false, bAllowLocked: true);
			if (cOFirstOccurrence == null || cOFirstOccurrence.bDestroyed)
			{
				ship.Destroy(isDespawning: false);
				return;
			}
		}
		JsonShip jSON = ship.GetJSON(strRegID, bSaveGame: true);
		DataHandler.dictShips[jSON.strName] = jSON;
		ship.json = null;
		List<JsonCondOwnerSave> list = new List<JsonCondOwnerSave>();
		List<CondOwner> iCOs = ship.GetICOs1(null, bSubObjects: true, bAllowDocked: false, bAllowLocked: true);
		List<CondOwner> list2 = new List<CondOwner>();
		foreach (CondOwner item in iCOs)
		{
			if (ship.LoadState < Ship.Loaded.Edit && item.jCOS != null)
			{
				list.Add(item.jCOS);
				continue;
			}
			JsonCondOwnerSave jSONSave = item.GetJSONSave();
			if (jSONSave != null)
			{
				list.Add(jSONSave);
			}
			list2.AddRange(item.GetLotCOs(bSubItems: true));
		}
		foreach (CondOwner item2 in list2)
		{
			JsonCondOwnerSave jSONSave2 = item2.GetJSONSave();
			if (jSONSave2 != null)
			{
				list.Add(jSONSave2);
			}
		}
		foreach (JsonCondOwnerSave item3 in list)
		{
			DataHandler.dictCOSaves[item3.strID] = item3;
			if (DataHandler.mapCOs.ContainsKey(item3.strID))
			{
				DataHandler.mapCOs.Remove(item3.strID);
			}
		}
		DestroyAndReload(ship, jSON);
		MonoSingleton<GUIRenderTargets>.Instance.ResetLoadedPortraits();
	}

	private void DestroyAndReload(Ship ship, JsonShip json)
	{
		string strID = coPlayer.strID;
		string strRegID = ship.strRegID;
		JsonAIShipSave jSONAIShipSave = AIShipManager.GetJSONAIShipSave(ship.strRegID);
		double condAmount = ship.ShipCO.GetCondAmount("IsStale");
		string shipOwner = system.GetShipOwner(strRegID);
		ship.Destroy();
		MonoSingleton<TargetVisController>.Instance.ClearTargetVis();
		if (!string.IsNullOrEmpty(shipOwner))
		{
			system.RegisterShipOwner(strRegID, shipOwner);
		}
		Transform parent = GameObject.Find("PlayState").transform;
		GameObject obj = new GameObject("goShip");
		obj.transform.SetParent(parent, worldPositionStays: false);
		ship = new Ship(obj);
		ship.json = json;
		ship.InitShip(bTemplateOnly: false, Ship.Loaded.Shallow);
		system.dictShips[ship.strRegID] = ship;
		if (!DataHandler.mapCOs.TryGetValue(strID, out coPlayer))
		{
			Debug.LogError("ERROR: Unable to reacquire player after removing ship " + strRegID);
		}
		ship.ToggleVis(bShow: false, affectDocked: false);
		if (condAmount != 0.0)
		{
			ship.ShipCO.SetCondAmount("IsStale", condAmount);
		}
		else
		{
			ship.ShipCO.ZeroCondAmount("IsStale");
		}
		if (jSONAIShipSave != null)
		{
			AIShipManager.AddAIToShip(ship, jSONAIShipSave.enumAIType, jSONAIShipSave.strATCLast, jSONAIShipSave, gameLoad: true);
		}
	}

	public void LaunchShip(float fTime, CondOwner coUser, GUIChargenStack cgs)
	{
		StartCoroutine(_LaunchShip(1f, coUser, cgs));
	}

	private IEnumerator _LaunchShip(float fTime, CondOwner coUser, GUIChargenStack cgs)
	{
		while (fTime > 0f)
		{
			fTime -= TimeElapsedUnscaled();
			yield return null;
		}
		Ship ship = coUser.ship;
		Ship ship2 = system.SpawnShip(cgs.strRegIDChosen, Ship.Loaded.Full);
		CareerChosen latestCareer = cgs.GetLatestCareer();
		if (latestCareer.fShipDmgMax > 0f)
		{
			ship2.DamageAllCOs(latestCareer.fShipDmgMax, allowMultiple: true);
		}
		ship2.ToggleVis(bShow: true);
		ship.ToggleVis(bShow: false);
		ship2.MoveShip(-ship2.vShipPos);
		MoveCO(coUser, ship2, bPlayerShip: true);
		coUser.ClaimShip(ship2.strRegID);
		if (latestCareer.fStartATCRange == 0f)
		{
			DockShip(ship2, latestCareer.strStartATC);
		}
		else
		{
			Ship value = null;
			system.dictShips.TryGetValue(latestCareer.strStartATC, out value);
			if (value == null)
			{
				value = ship;
			}
			ship2.objSS.vPosx = value.objSS.vPosx;
			ship2.objSS.vPosy = value.objSS.vPosy;
			Vector2 pushbackVector = MathUtils.GetPushbackVector(ship2, value);
			pushbackVector *= latestCareer.fStartATCRange;
			ship2.objSS.vPosx = value.objSS.vPosx + (double)(pushbackVector.x / 149597870f);
			ship2.objSS.vPosy = value.objSS.vPosy + (double)(pushbackVector.y / 149597870f);
			ship2.objSS.vVelX = value.objSS.vVelX;
			ship2.objSS.vVelY = value.objSS.vVelY;
			ship2.objSS.vAccEx = Vector2.zero;
		}
		MonoSingleton<ObjectiveTracker>.Instance.AddShipSubscription(ship2.strRegID);
		ship.Destroy();
	}

	public void TeleportCO(CondOwner coRider, string strDestRegID, double timeJump = 0.0)
	{
		if (coRider == null || string.IsNullOrEmpty(strDestRegID))
		{
			return;
		}
		Ship shipByRegID = system.GetShipByRegID(strDestRegID);
		if (shipByRegID == null)
		{
			return;
		}
		if (coRider.ship == shipByRegID)
		{
			List<CondOwner> followers = coRider.GetFollowers();
			MoveCO(coRider, shipByRegID, bPlayerShip: false);
			{
				foreach (CondOwner item in followers)
				{
					MoveCO(item, shipByRegID, bPlayerShip: false);
				}
				return;
			}
		}
		if (coRider == GetSelectedCrew())
		{
			MonoSingleton<AsyncShipLoader>.Instance.Unload();
		}
		StartCoroutine(_TeleportCO(coRider, shipByRegID, timeJump));
	}

	private IEnumerator _TeleportCO(CondOwner coUser, Ship objShipNew, double timeJump = 0.0)
	{
		if (coUser == null || objShipNew == null)
		{
			yield break;
		}
		bool bPlayer = coUser == GetSelectedCrew();
		if (bPlayer)
		{
			MonoSingleton<GUILoadingPopUp>.Instance.ShowTooltip(DataHandler.GetString("LOAD_SHIPLOAD"), objShipNew.publicName);
			yield return new WaitForSecondsRealtime(0.1f);
		}
		Ship.Loaded nLoad = Ship.Loaded.Full;
		if (!bPlayer)
		{
			nLoad = Ship.Loaded.Shallow;
		}
		if (timeJump != 0.0)
		{
			system.Update(timeJump);
		}
		objShipNew = system.SpawnShip(objShipNew.strRegID, nLoad);
		if (bPlayer)
		{
			LowerUI();
		}
		Ship ship = coUser.ship;
		List<CondOwner> followers = coUser.GetFollowers();
		MoveCO(coUser, objShipNew, bPlayerShip: false);
		if (objShipNew.LoadState >= Ship.Loaded.Edit)
		{
			CondOwnerVisitorCatchUp visitor = new CondOwnerVisitorCatchUp();
			objShipNew.VisitCOs(visitor, bSubObjects: true, bAllowDocked: true, bAllowLocked: true);
		}
		if (timeJump > 0.0)
		{
			coUser.CatchUp(bSubItems: true);
		}
		foreach (CondOwner item in followers)
		{
			MoveCO(item, objShipNew, bPlayerShip: false);
			if (timeJump > 0.0)
			{
				coUser.CatchUp(bSubItems: true);
			}
		}
		if (objShipNew.LoadState >= Ship.Loaded.Edit)
		{
			foreach (Ship allDockedShip in ship.GetAllDockedShips())
			{
				if (allDockedShip.gameObject.activeInHierarchy)
				{
					objInstance.SaveToShallow(allDockedShip);
				}
			}
			objInstance.SaveToShallow(ship);
			objShipNew.ToggleVis(bShow: true);
		}
		if (bPlayer)
		{
			objInstance.CamCenter(GetSelectedCrew());
			MonoSingleton<GUILoadingPopUp>.Instance.FadeOutToolTip();
			CollisionManager.RefreshCurrentRegion();
		}
	}

	public static void MoveCO(CondOwner objCO, Ship objShipNew, bool bPlayerShip)
	{
		if (objCO == null || objShipNew == null)
		{
			return;
		}
		objCO.RemoveFromCurrentHome();
		Pathfinder pathfinder = objCO.Pathfinder;
		if (pathfinder != null)
		{
			pathfinder.HideFootprints();
		}
		if (objShipNew.aTiles != null && objShipNew.aTiles.Count > 0)
		{
			Tile crewSpawnTile = objShipNew.GetCrewSpawnTile(objCO);
			if (crewSpawnTile != null)
			{
				objCO.transform.position = new Vector3(crewSpawnTile.tf.position.x, crewSpawnTile.tf.position.y, objCO.tf.position.z);
				objCO.currentRoom = crewSpawnTile.room;
			}
		}
		else
		{
			Vector3 crewSpawnPosition = objShipNew.GetCrewSpawnPosition(objCO);
			objCO.transform.position = new Vector3(crewSpawnPosition.x, crewSpawnPosition.y, crewSpawnPosition.z);
			objCO.currentRoom = null;
		}
		objShipNew.AddCO(objCO, bTiles: true);
		if (objCO == coPlayer)
		{
			objInstance.CamCenter(objCO);
		}
		if (bPlayerShip)
		{
			shipPlayerOwned = objShipNew;
			if (coPlayer.Company != null)
			{
				coPlayer.Company.strRegID = shipPlayerOwned.strRegID;
			}
		}
	}

	public void QueueForTransit(JsonTransitConnection jsonTransit, List<CondOwner> cosToMove, Action<JsonTransitConnection, List<CondOwner>> callback)
	{
		List<string> list = new List<string>();
		string originShip = "";
		foreach (CondOwner item in cosToMove)
		{
			if (!(item == null))
			{
				if (item.ship != null)
				{
					originShip = item.ship.strRegID;
				}
				list.Add(item.name);
			}
		}
		StartCoroutine(QueueForTransit(originShip, jsonTransit, list, callback));
	}

	private IEnumerator QueueForTransit(string originShip, JsonTransitConnection jsonTransit, List<string> cosToMove, Action<JsonTransitConnection, List<CondOwner>> moveToTransitCallback)
	{
		double startingTime = StarSystem.fEpoch;
		yield return new WaitUntil(() => StarSystem.fEpoch - startingTime > 8.0);
		Ship shipByRegID = system.GetShipByRegID(jsonTransit.strTargetRegID);
		Ship shipByRegID2 = system.GetShipByRegID(originShip);
		if (shipByRegID == null || shipByRegID.bDestroyed || shipByRegID2 == null || shipByRegID2.bDestroyed)
		{
			yield break;
		}
		List<CondOwner> people = shipByRegID2.GetPeople(bAllowDocked: false);
		List<CondOwner> list = new List<CondOwner>();
		foreach (CondOwner item in people)
		{
			if (!(item == null) && cosToMove.Contains(item.name))
			{
				item.UnclaimShip(item.ship.strRegID);
				item.ClaimShip(shipByRegID.strRegID);
				item.CatchUp(bSubItems: true);
				MoveCO(item, shipByRegID, bPlayerShip: false);
				list.Add(item);
			}
		}
		if (list.Count > 0)
		{
			moveToTransitCallback(jsonTransit, list);
		}
	}

	public void CamZoom(float fAmount)
	{
		if ((double)fAmount < 1.0)
		{
			float num = 0.8f;
			if (bShipEdit)
			{
				num = 0.04f;
			}
			float num2 = Mathf.Max(camMain.orthographicSize - num, 0f);
			camMain.orthographicSize = num2 * fAmount + num;
		}
		else
		{
			float num3 = 150f;
			if (bShipEdit)
			{
				num3 = 150f;
			}
			float num4 = Mathf.Min(camMain.orthographicSize / num3, 1f);
			float num5 = num4 * fAmount / (1f + num4 * (fAmount - 1f));
			camMain.orthographicSize = num5 * num3;
		}
		camMain.GetComponent<GameRenderer>().SetZoom(camMain.orthographicSize);
	}

	public void CamCenter(CondOwner co)
	{
		camFollow = true;
		coCamCenter = co;
	}

	public void CamCenterTravel()
	{
		Vector2 vector = Vector2.zero;
		if (!bShipEdit)
		{
			if (coCamCenter == null)
			{
				return;
			}
			vector = coCamCenter.tf.position;
		}
		if (camMain.transform.position.x == 0f && camMain.transform.position.y == 0f)
		{
			camMain.transform.Translate(vector);
		}
		camTravel.x = vector.x - camMain.transform.position.x;
		camTravel.y = vector.y - camMain.transform.position.y;
	}

	public static void ResetTimeScale()
	{
		Time.timeScale = 1f;
		OnTimeScaleUpdated.Invoke();
	}

	public static void TimeScaleMult(float fMultiplier)
	{
		Time.timeScale = MathUtils.Clamp(Time.timeScale * fMultiplier, 0.25f, 16f);
		OnTimeScaleUpdated.Invoke();
	}

	public static void ToggleSFF()
	{
		if (goUI == null)
		{
			tplCurrentUI = null;
		}
		if (tplCurrentUI != null && tplCurrentUI.Item1 == "FFWD" && goUI != null)
		{
			LowerUI(tplLastUI != null && tplLastUI.Item1 != "FFWD");
		}
		else if (GetSelectedCrew() != null && !GetSelectedCrew().HasCond("IsInChargen"))
		{
			RaiseUI("FFWD", GetSelectedCrew());
		}
	}

	public static float TimeElapsedScaled()
	{
		return Time.deltaTime * fTimeCoeffPause;
	}

	public static float TimeElapsedUnscaled()
	{
		return Mathf.Min(Time.unscaledDeltaTime, 0.1f);
	}

	private void ToggleAutotask(bool autoMode)
	{
		CondOwner selectedCrew = GetSelectedCrew();
		if (!(selectedCrew == null))
		{
			if (autoMode && selectedCrew.HasCond("IsAIManual"))
			{
				AIManual(manualMode: false);
			}
			else if (!autoMode && !selectedCrew.HasCond("IsAIManual"))
			{
				AIManual(manualMode: true);
			}
		}
	}

	public static void AIManual(bool manualMode)
	{
		CondOwner selectedCrew = GetSelectedCrew();
		if (selectedCrew == null)
		{
			return;
		}
		if (manualMode)
		{
			if (!selectedCrew.HasCond("IsAIManual"))
			{
				selectedCrew.AddCondAmount("IsAIManual", 1.0);
				selectedCrew.ZeroCondAmount("IsFollowCommand");
				PlayerMarker.AddMarker(selectedCrew);
			}
		}
		else if (selectedCrew.HasCond("IsAIManual"))
		{
			selectedCrew.ZeroCondAmount("IsAIManual");
			PlayerMarker.AddMarker(selectedCrew);
		}
		chkAIAuto.onValueChanged.RemoveListener(objInstance.ToggleAutotask);
		chkAIAuto.isOn = !manualMode;
		chkAIAuto.onValueChanged.AddListener(objInstance.ToggleAutotask);
	}

	public List<CondOwner> FindCOsAtMousePosition(CondOwner coUs, bool bInteractive)
	{
		return FindCOsAtWorldPosition(ActiveCam.ScreenPointToRay(InputManager.MousePosition).origin, coUs, bInteractive);
	}

	public List<CondOwner> FindCOsAtWorldPosition(Vector3 vPos, CondOwner coUs, bool bInteractive)
	{
		List<CondOwner> list = new List<CondOwner>();
		if (bInteractive)
		{
			if (coUs != null && coUs.bAlive)
			{
				List<CondOwner> list2 = new List<CondOwner>();
				shipCurrentLoaded.GetCOsAtWorldCoords1(vPos, null, bAllowDocked: true, bAllowLocked: true, list2);
				foreach (CondOwner item in list2)
				{
					Debug.Log(item.strName);
					if (item.objCOParent != null)
					{
						continue;
					}
					foreach (string aInteraction in item.aInteractions)
					{
						Interaction interaction = DataHandler.GetInteraction(aInteraction);
						if (interaction != null)
						{
							interaction.objThem = item;
							if (interaction.Triggered(coUs, item, bStats: false, bIgnoreItems: true) && !list.Contains(item))
							{
								list.Add(item);
							}
						}
					}
				}
			}
		}
		else
		{
			if (shipCurrentLoaded != null)
			{
				shipCurrentLoaded.GetCOsAtWorldCoords1(vPos, null, bAllowDocked: true, bAllowLocked: true, list);
			}
			if (list.Count == 0)
			{
				foreach (Ship loadedShip in MonoSingleton<AsyncShipLoader>.Instance.GetLoadedShips())
				{
					loadedShip?.GetCOsAtWorldCoords1(vPos, null, bAllowDocked: true, bAllowLocked: true, list);
				}
			}
		}
		return list;
	}

	public static List<AvailableActionDTO> GetAvailActionsForCO(CondOwner coUs, CondOwner coTarget)
	{
		List<AvailableActionDTO> list = new List<AvailableActionDTO>();
		if (coUs == null || coTarget == null)
		{
			return list;
		}
		if (coUs.socUs != null && coTarget.socUs != null && coUs.socUs != coTarget.socUs)
		{
			coUs.SwitchRELConds(coUs.socUs.GetRelationship(coTarget.strName), bSilent: true);
		}
		Interaction interaction = null;
		Interaction interactionCurrent = coUs.GetInteractionCurrent();
		bool flag = false;
		bool flag2 = false;
		if (interactionCurrent != null && interactionCurrent.strName != "Walk")
		{
			if (interactionCurrent.strName == "GUINavStationAllow")
			{
				flag2 = true;
			}
			interaction = DataHandler.GetInteraction("CancelAction");
			if (interaction != null)
			{
				interaction.objUs = coUs;
				interaction.objThem = coUs;
				interaction.bManual = true;
				CustomActionDTO dto = new CustomActionDTO(interaction);
				TryAddAction(list, dto);
				flag = true;
			}
		}
		Pathfinder pathfinder = coUs.Pathfinder;
		Tile tilDest = null;
		if (pathfinder != null)
		{
			tilDest = pathfinder.tilDest;
		}
		bool flag3 = coTarget.Crew == null && coTarget.HasCond("IsSolid");
		foreach (string aAttackIA in coUs.aAttackIAs)
		{
			interaction = DataHandler.GetInteraction(aAttackIA);
			if (interaction == null)
			{
				continue;
			}
			interaction.objUs = coUs;
			interaction.objThem = coTarget;
			interaction.bManual = true;
			CustomActionDTO customActionDTO = null;
			if (interaction.bPassThrough && coTarget.objContainer != null)
			{
				List<CondOwner> cOs = coTarget.objContainer.GetCOs(bAllowLocked: false, interaction.CTTestThem);
				if (cOs.Count > 0)
				{
					interaction.objThem = cOs[0];
				}
				customActionDTO = new CustomActionDTO(interaction);
			}
			if (flag3 && interaction.attackMode != null && interaction.attackMode.bAllowOnInanimate)
			{
				interaction.CTTestThem = null;
				interaction.PSpecTestThem = null;
			}
			if (interaction.Triggered(interaction.objUs, interaction.objThem))
			{
				if (interaction.aLootItemUseContract != null && interaction.aLootItemUseContract.Count > 0)
				{
					interaction.strTitle += interaction.aLootItemUseContract[0].ShortName;
				}
				if (customActionDTO != null)
				{
					TryAddAction(list, customActionDTO);
					continue;
				}
				AvailableActionDTO availableActionDTO = new AvailableActionDTO(interaction, isReply: false);
				availableActionDTO.IsClickable = !flag;
				TryAddAction(list, availableActionDTO);
			}
		}
		foreach (string lootName in DataHandler.GetLoot("TXTPlayerCombatInteractions").GetLootNames())
		{
			interaction = DataHandler.GetInteraction(lootName);
			if (interaction != null)
			{
				interaction.objUs = coUs;
				interaction.objThem = coTarget;
				interaction.bManual = true;
				if (interaction.Triggered(coUs, coTarget))
				{
					AvailableActionDTO availableActionDTO2 = new AvailableActionDTO(interaction, isReply: false);
					availableActionDTO2.IsClickable = !flag;
					TryAddAction(list, availableActionDTO2);
				}
			}
		}
		foreach (JsonJobSave aJob in GigManager.aJobs)
		{
			if (aJob == null || !aJob.bTaken)
			{
				continue;
			}
			Interaction interactionDo = aJob.GetInteractionDo(coUs, coTarget);
			if (interactionDo != null)
			{
				interactionDo.bManual = true;
				AvailableActionDTO availableActionDTO3 = new AvailableActionDTO(interactionDo, isReply: false);
				availableActionDTO3.IsClickable = !flag;
				availableActionDTO3.IsGig = true;
				if (interactionDo.nMoveType == Interaction.MoveType.DEFAULT)
				{
					interactionDo.nMoveType = Interaction.MoveType.GIG;
				}
				TryAddAction(list, availableActionDTO3);
			}
		}
		bool flag4 = false;
		if (coTarget.socUs != null)
		{
			foreach (ReplyThread aReply in coTarget.aReplies)
			{
				if (!(aReply.strID == coUs.strName) || aReply.bDone)
				{
					continue;
				}
				interaction = DataHandler.GetInteraction(aReply.jis.strName);
				if (interaction == null || !interaction.bSocial)
				{
					continue;
				}
				AvailableActionDTO availableActionDTO4 = InjectRecoveryIa(coUs);
				if (availableActionDTO4 != null)
				{
					TryAddAction(list, availableActionDTO4);
					break;
				}
				interaction = DataHandler.GetInteraction("WaitReply");
				if (interaction != null)
				{
					interaction.objUs = coUs;
					interaction.objThem = coTarget;
					interaction.bManual = true;
					AvailableActionDTO availableActionDTO5 = new AvailableActionDTO(interaction, isReply: false);
					availableActionDTO5.IsClickable = !flag;
					TryAddAction(list, availableActionDTO5);
					flag4 = true;
				}
				break;
			}
		}
		bool flag5 = false;
		if (!flag4)
		{
			foreach (ReplyThread aReply2 in coUs.aReplies)
			{
				if (!(aReply2.strID == coTarget.strName) || aReply2.bDone)
				{
					continue;
				}
				Interaction interaction2 = DataHandler.GetInteraction(aReply2.jis.strName, aReply2.jis, getTrackedObject: true);
				if (interaction2 != null)
				{
					string[] aInverse = interaction2.aInverse;
					for (int i = 0; i < aInverse.Length; i++)
					{
						string[] array = aInverse[i].Split(',');
						Interaction interaction3 = DataHandler.GetInteraction(array[0]);
						if (!(array[0] == "SOCBlank") && interaction3 != null)
						{
							interaction2.AssignReplyRoles(interaction3, array, bNoSwap: false);
							interaction3.bManual = true;
							interaction3.strPlot = interaction2.strPlot;
							if (interaction3.objUs == coUs && interaction3.Triggered(coUs, coTarget, bStats: false, !interaction3.bSocial))
							{
								AvailableActionDTO availableActionDTO6 = new AvailableActionDTO(interaction3, isReply: true);
								availableActionDTO6.IsClickable = !flag;
								TryAddAction(list, availableActionDTO6);
								flag5 = true;
							}
						}
					}
				}
				DataHandler.ReleaseTrackedInteraction(interaction2);
			}
		}
		if (!flag5 && !flag4 && coUs.socUs != null)
		{
			Relationship relationship = coUs.socUs.GetRelationship(coTarget.strName);
			if (relationship != null && relationship.strContext != null && relationship.strContext != "Default")
			{
				foreach (string lootName2 in DataHandler.GetLoot(relationship.strContext).GetLootNames())
				{
					interaction = DataHandler.GetInteraction(lootName2);
					if (interaction != null)
					{
						interaction.objUs = coUs;
						interaction.objThem = coTarget;
						interaction.bManual = true;
						if (interaction.Triggered(interaction.objUs, interaction.objThem, bStats: false, !interaction.bSocial))
						{
							AvailableActionDTO availableActionDTO7 = new AvailableActionDTO(interaction, isReply: true);
							availableActionDTO7.IsClickable = !flag;
							TryAddAction(list, availableActionDTO7);
						}
						flag5 = true;
					}
				}
			}
		}
		if (!flag5 && !flag4)
		{
			if (PlotManager.bDebugLogging)
			{
				Debug.Log("<color=#992299ff>--------Starting QAB Checks--------</color> ");
			}
			foreach (Interaction allPlotQAB in PlotManager.GetAllPlotQABs(coUs, coTarget))
			{
				if (allPlotQAB != null)
				{
					AvailableActionDTO availableActionDTO8 = new AvailableActionDTO(allPlotQAB, isReply: false);
					availableActionDTO8.IsClickable = !flag;
					TryAddAction(list, availableActionDTO8);
				}
			}
			if (PlotManager.bDebugLogging)
			{
				Debug.Log("<color=#992299ff>--------Ending QAB Checks--------</color> ");
			}
			foreach (string aInteraction in coTarget.aInteractions)
			{
				if (aInteraction == null || (aInteraction.IndexOf("Drop") == 0 && !coTarget.HasCond("IsHuman") && !coTarget.HasCond("IsRobot")))
				{
					continue;
				}
				interaction = DataHandler.GetInteraction(aInteraction);
				if (interaction == null)
				{
					continue;
				}
				interaction.objUs = coUs;
				interaction.objThem = coTarget;
				interaction.bManual = true;
				CustomActionDTO customActionDTO2 = null;
				if (interaction.bPassThrough && coTarget.objContainer != null)
				{
					List<CondOwner> cOs2 = coTarget.objContainer.GetCOs(bAllowLocked: false, interaction.CTTestThem);
					if (cOs2.Count > 0)
					{
						interaction.objThem = cOs2[0];
					}
					customActionDTO2 = new CustomActionDTO(interaction);
				}
				if (interaction.Triggered(interaction.objUs, interaction.objThem, bStats: false, !interaction.bSocial))
				{
					if (customActionDTO2 != null)
					{
						TryAddAction(list, customActionDTO2);
						continue;
					}
					AvailableActionDTO availableActionDTO9 = new AvailableActionDTO(interaction, isReply: false);
					availableActionDTO9.IsClickable = !flag || (flag2 && interaction.strName == "GUINavStation");
					TryAddAction(list, availableActionDTO9);
				}
			}
		}
		if (coTarget.socUs != null && !flag4)
		{
			interaction = (GUIQuickBar.ShowSocialCore ? DataHandler.GetInteraction("HideSocialCore") : DataHandler.GetInteraction("ShowSocialCore"));
			if (interaction != null)
			{
				interaction.objUs = coUs;
				interaction.objThem = coTarget;
				interaction.bManual = true;
				AvailableActionDTO availableActionDTO10 = new AvailableActionDTO(interaction, isReply: false);
				availableActionDTO10.IsClickable = !flag;
				if (interaction.Triggered(bStats: false, bIgnoreItems: true))
				{
					TryAddAction(list, availableActionDTO10);
				}
			}
		}
		if ((DataHandler.GetCondTrigger("TIsJettisonableBody").Triggered(coTarget) || DataHandler.GetCondTrigger("TIsJettisonableSignalBeacon").Triggered(coTarget)) && TileUtils.IsExposedToSpace(coTarget) && coTarget != coPlayer)
		{
			Interaction interaction4 = null;
			if (coTarget.HasCond("IsHuman"))
			{
				interaction4 = DataHandler.GetInteraction("JettisonCorpse");
			}
			else if (coTarget.HasCond("IsRobot"))
			{
				interaction4 = DataHandler.GetInteraction("JettisonRobot");
			}
			else if (coTarget.HasCond("IsSignalBeacon"))
			{
				foreach (string allLootName in DataHandler.GetLoot("BeaconFactions").GetAllLootNames())
				{
					interaction4 = DataHandler.GetInteraction("DeployStructure" + allLootName);
					if (interaction4 != null)
					{
						interaction4.objUs = coUs;
						interaction4.objThem = coTarget;
						interaction4.bManual = true;
						AvailableActionDTO availableActionDTO11 = new AvailableActionDTO(interaction4, isReply: false);
						availableActionDTO11.IsClickable = !flag;
						TryAddAction(list, availableActionDTO11);
						interaction4 = null;
					}
				}
			}
			if (interaction4 != null)
			{
				interaction4.objUs = coUs;
				interaction4.objThem = coTarget;
				interaction4.bManual = true;
				AvailableActionDTO availableActionDTO12 = new AvailableActionDTO(interaction4, isReply: false);
				availableActionDTO12.IsClickable = !flag;
				TryAddAction(list, availableActionDTO12);
			}
		}
		if (objInstance.workManager.COIDHasTasks(coTarget.strID))
		{
			bool flag6 = false;
			foreach (AvailableActionDTO item in list)
			{
				if (item.Ia.strName == "ACTCancelTaskThem")
				{
					flag6 = true;
					break;
				}
			}
			if (!flag6)
			{
				interaction = DataHandler.GetInteraction("ACTCancelTaskThem");
				if (interaction != null)
				{
					interaction.objUs = coUs;
					interaction.objThem = coTarget;
					interaction.bManual = true;
					AvailableActionDTO dto2 = new AvailableActionDTO(interaction, isReply: false);
					TryAddAction(list, dto2);
				}
			}
			interaction = GetSelectedCrew().GetInteractionCurrent();
			if (interaction == null || interaction.objThem != coTarget)
			{
				interaction = DataHandler.GetInteraction("ACTResumeTaskThem");
				if (interaction != null)
				{
					interaction.objUs = coUs;
					interaction.objThem = coTarget;
					interaction.bManual = true;
					AvailableActionDTO dto3 = new AvailableActionDTO(interaction, isReply: false);
					TryAddAction(list, dto3);
				}
			}
		}
		TryAddAction(list, InjectRecoveryIa(coUs));
		if (pathfinder != null)
		{
			pathfinder.tilDest = tilDest;
		}
		return list;
	}

	private static AvailableActionDTO InjectRecoveryIa(CondOwner coUs)
	{
		if (!coUs.HasCond("Stunned") && !coUs.HasCond("Recovering"))
		{
			return null;
		}
		Interaction interaction = null;
		interaction = ((!coUs.HasCond("Stunned")) ? DataHandler.GetInteraction("QABRecovering") : DataHandler.GetInteraction("QABStunned"));
		interaction.objUs = coUs;
		interaction.objThem = coUs;
		interaction.bManual = true;
		return new AvailableActionDTO(interaction, isReply: false)
		{
			IsClickable = false
		};
	}

	private static void TryAddAction(List<AvailableActionDTO> interactions, AvailableActionDTO dto)
	{
		if (interactions == null || dto == null || dto.Ia == null)
		{
			return;
		}
		foreach (AvailableActionDTO interaction in interactions)
		{
			Interaction ia = interaction.Ia;
			if (ia.strName == dto.Ia.strName && ia.objThem == dto.Ia.objThem)
			{
				interaction.IsReply = interaction.IsReply || dto.IsReply;
				return;
			}
		}
		interactions.Add(dto);
	}

	public void LowerContextMenu()
	{
		contextMenuPool.Reset();
	}

	public void TogglePowerUI(Ship objShip, Toggle toggle = null)
	{
		if (toggle != null)
		{
			PowerVizVisible = toggle.isOn;
		}
		else
		{
			PowerVizVisible = !PowerVizVisible;
		}
		if (GUIPDA.instance != null)
		{
			GUIPDA.instance.pdaVisualisers.TogglePowerQuietly(PowerVizVisible);
		}
		if (PowerVizVisible)
		{
			GameObject original = Resources.Load<GameObject>("prefabPwrLine");
			linePower = UnityEngine.Object.Instantiate(original).GetComponent<VectorObject2D>().vectorLine;
			linePower.color = Color.yellow;
			linePower.points2.Clear();
			linePower.SetCanvas(CanvasManager.goCanvasWorldGUI, worldPositionStays: false);
			linePower.rectTransform.gameObject.name = linePower.rectTransform.gameObject.name + "Instance";
			linePowerOff = UnityEngine.Object.Instantiate(original).GetComponent<VectorObject2D>().vectorLine;
			linePowerOff.color = Color.gray;
			linePowerOff.points2.Clear();
			linePowerOff.SetCanvas(CanvasManager.goCanvasWorldGUI, worldPositionStays: false);
			linePowerOff.rectTransform.gameObject.name = linePowerOff.rectTransform.gameObject.name + "Instance";
			camMain.cullingMask |= 1 << LayerMask.NameToLayer("Power Overlay");
			camMain.GetComponent<GameRenderer>().StencilCam.cullingMask |= 1 << LayerMask.NameToLayer("Power Overlay");
			if (coPlayer != null)
			{
				coPlayer.ZeroCondAmount("TutorialPowerVizWaiting");
				MonoSingleton<ObjectiveTracker>.Instance.CheckObjective(coPlayer.strID);
			}
		}
		else
		{
			VectorLine.Destroy(ref linePower);
			VectorLine.Destroy(ref linePowerOff);
			camMain.cullingMask &= ~(1 << LayerMask.NameToLayer("Power Overlay"));
			camMain.GetComponent<GameRenderer>().StencilCam.cullingMask &= ~(1 << LayerMask.NameToLayer("Power Overlay"));
		}
		SetToggleWithoutNotify(GUIShipEdit.Instance.chkPwrSE, PowerVizVisible);
	}

	private void Options()
	{
		CanvasGroup component = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/prefabGUIOptions").GetComponent<CanvasGroup>();
		component.GetComponent<GUIPanelFade>().Reset(0.25f, 0f, bFadeIn: true, bFadeOut: false);
		component.interactable = true;
		component.blocksRaycasts = true;
		component.GetComponentInChildren<GUIOptions>().CheckSaveOnExit();
	}

	private void Manual()
	{
		CanvasGroup component = CanvasManager.goCanvasQuit.transform.Find("GUIQuit/pnlManual").GetComponent<CanvasGroup>();
		component.GetComponent<GUIPanelFade>().Reset(0.25f, 0f, bFadeIn: true, bFadeOut: false);
		component.interactable = true;
		component.blocksRaycasts = true;
	}

	public void PopupQuitToMenu()
	{
		GameObject obj = UnityEngine.Object.Instantiate(_confirmationDialoguePrefab, CanvasManager.goCanvasQuit.transform);
		Color clrBg = new Color(0.10980392f, 0.10980392f, 0.10980392f);
		Color clrFg = new Color(1f / 17f, 1f / 17f, 1f / 17f);
		Color clrFont = new Color(40f / 51f, 40f / 51f, 40f / 51f);
		obj.GetComponent<GUIConfirmationDialogue>().Setup(DataHandler.GetString("GUI_CONFIRM_QTM"), delegate
		{
			QuitToMenu(bSave: false);
		}, clrBg, clrFg, clrFont);
	}

	public void QuitToMenu(bool bSave)
	{
		if (!bDebugFightMode && CanvasManager.instance.State != CanvasManager.GUIState.GAMEOVER && objGUISaveOnClose.isOn)
		{
			bSave = true;
		}
		AudioManager.am.ShutDown();
		ResetTimeScale();
		CanvasManager.instance.Black();
		MainMenu.bCueMenuMusic = true;
		bPauseLock = false;
		if (!bShipEdit && bSave)
		{
			MonoSingleton<GUILoadingPopUp>.Instance.ShowTooltip(DataHandler.GetString("LOAD_SAVING"), DataHandler.GetString("LOAD_WAIT"));
			StartCoroutine(QueueSaveAndExit());
		}
		else
		{
			QueueMainMenu();
		}
	}

	public void PopupQuitToShipEdit()
	{
		GameObject obj = UnityEngine.Object.Instantiate(_confirmationDialoguePrefab, CanvasManager.goCanvasQuit.transform);
		Color clrBg = new Color(0.10980392f, 0.10980392f, 0.10980392f);
		Color clrFg = new Color(1f / 17f, 1f / 17f, 1f / 17f);
		Color clrFont = new Color(40f / 51f, 40f / 51f, 40f / 51f);
		obj.GetComponent<GUIConfirmationDialogue>().Setup(DataHandler.GetString("GUI_CONFIRM_QTSE"), delegate
		{
			QuitToShipEdit(bSave: false);
		}, clrBg, clrFg, clrFont);
	}

	public void QuitToShipEdit(bool bSave)
	{
		if (!bDebugFightMode && CanvasManager.instance.State != CanvasManager.GUIState.GAMEOVER && objGUISaveOnClose.isOn)
		{
			bSave = true;
		}
		AudioManager.am.ShutDown();
		ResetTimeScale();
		CanvasManager.instance.Black();
		bPauseLock = false;
		if (!bShipEdit && bSave)
		{
			MonoSingleton<GUILoadingPopUp>.Instance.ShowTooltip(DataHandler.GetString("LOAD_SAVING"), DataHandler.GetString("LOAD_WAIT"));
			StartCoroutine(QueueSaveAndShipEdit());
		}
		else
		{
			QueueShipEdit();
		}
	}

	public void PopupQuitToDesktop()
	{
		GameObject obj = UnityEngine.Object.Instantiate(_confirmationDialoguePrefab, CanvasManager.goCanvasQuit.transform);
		Color clrBg = new Color(0.10980392f, 0.10980392f, 0.10980392f);
		Color clrFg = new Color(1f / 17f, 1f / 17f, 1f / 17f);
		Color clrFont = new Color(40f / 51f, 40f / 51f, 40f / 51f);
		obj.GetComponent<GUIConfirmationDialogue>().Setup(DataHandler.GetString("GUI_CONFIRM_QTD"), delegate
		{
			QuitToDesktop(bSave: false);
		}, clrBg, clrFg, clrFont);
	}

	public void QuitToDesktop(bool bSave)
	{
		if (objGUISaveOnClose.isOn)
		{
			bSave = true;
		}
		AudioManager.am.ShutDown();
		ResetTimeScale();
		CanvasManager.instance.Black();
		MainMenu.bCueMenuMusic = true;
		if (!bShipEdit && bSave)
		{
			MonoSingleton<GUILoadingPopUp>.Instance.ShowTooltip(DataHandler.GetString("LOAD_SAVING"), DataHandler.GetString("LOAD_WAIT"));
			StartCoroutine(QueueSaveAndDesktop());
		}
		else
		{
			QueueDesktop();
		}
	}

	private IEnumerator QueueSaveAndExit()
	{
		yield return null;
		LoadManager.OnSaveFinished.AddListener(QueueMainMenu);
		MonoSingleton<LoadManager>.Instance.AutoSave(useThreading: false);
	}

	private void QueueMainMenu()
	{
		LoadManager.OnSaveFinished.RemoveListener(QueueMainMenu);
		QueueScene("MainMenu2", 1.5f);
		LoadManager.ResetLoadedSaveTracking();
	}

	private void QueueShipEdit()
	{
		LoadManager.OnSaveFinished.RemoveListener(QueueShipEdit);
		OnSceneFinishedLoading.AddListener(delegate
		{
			objInstance.StartShipEdit();
		});
		bShipEditTest = false;
		bShipEdit = false;
		bDebugFightMode = false;
		LoadManager.LoadShipEditor();
	}

	private IEnumerator QueueSaveAndShipEdit()
	{
		yield return null;
		LoadManager.OnSaveFinished.AddListener(QueueShipEdit);
		MonoSingleton<LoadManager>.Instance.AutoSave(useThreading: false);
	}

	private IEnumerator QueueSaveAndDesktop()
	{
		yield return null;
		LoadManager.OnSaveFinished.AddListener(QueueDesktop);
		MonoSingleton<LoadManager>.Instance.AutoSave(useThreading: false);
	}

	private void QueueDesktop()
	{
		LoadManager.OnSaveFinished.RemoveListener(QueueDesktop);
		Application.Quit();
	}

	public Bounds GetViewportBounds(Camera camera, Vector3 v1, Vector3 v2)
	{
		Vector3 min = Vector3.Min(v1, v2);
		Vector3 max = Vector3.Max(v1, v2);
		min.z = -100f;
		max.z = 100f;
		Bounds result = default(Bounds);
		result.SetMinMax(min, max);
		return result;
	}

	private void SelectBounds(Bounds bnd, bool bTiles)
	{
		List<CondOwner> list = new List<CondOwner>();
		if (bTiles)
		{
			foreach (Ship aLoadedShip in aLoadedShips)
			{
				foreach (Tile aTile in aLoadedShip.aTiles)
				{
					list.Add(aTile.coProps);
				}
			}
		}
		else
		{
			list = shipCurrentLoaded.GetICOs1(null, bSubObjects: false, bAllowDocked: true, bAllowLocked: false);
		}
		CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsWall1x1InstalledOrMineable");
		CondTrigger condTrigger2 = DataHandler.GetCondTrigger("TIsFloorGrateOrFloorRock");
		Vector3 vector = default(Vector3);
		int num = 0;
		int num2 = 0;
		foreach (CondOwner item in list)
		{
			if (item == null || item.HasCond("IsRoom"))
			{
				continue;
			}
			vector = item.transform.position;
			if (bnd.Contains(vector))
			{
				SelectCO(item);
				if (condTrigger.Triggered(item))
				{
					num++;
				}
				if (condTrigger2.Triggered(item))
				{
					num2++;
				}
			}
		}
		GUIShipEdit.Instance.UpdateReplaceStrings(DataHandler.GetString("GUI_SHIPEDIT_REPLACE_FLOORS").Replace("XXX", num2.ToString()), DataHandler.GetString("GUI_SHIPEDIT_REPLACE_WALLS").Replace("XXX", num.ToString()));
		if (bTiles)
		{
			OnTileSelectionUpdated.Invoke(aSelected);
		}
	}

	private void PaintBounds(Bounds bnd)
	{
		StartCoroutine(_PaintBounds(bnd));
	}

	private IEnumerator _PaintBounds(Bounds bnd)
	{
		bool oldPauseState = Paused;
		if (bcombatAutoPauseAllowed && !Paused)
		{
			Paused = true;
		}
		Vector3 vPos = bnd.min;
		int count = 0;
		string selPartName = null;
		float angle = 0f;
		if (goSelPart != null)
		{
			CondOwner component = goSelPart.GetComponent<CondOwner>();
			selPartName = ((component != null) ? component.strName : goSelPart.name);
			angle = goSelPart.transform.rotation.eulerAngles.z;
		}
		JsonInstallable ji = jiLast?.Clone();
		Interaction installIa = iaItmInstall;
		for (float x = TileUtils.GridAlign(bnd.min.x); x <= bnd.max.x; x += 1f)
		{
			for (float y = TileUtils.GridAlign(bnd.min.y); y <= bnd.max.y; y += 1f)
			{
				vPos.x = x;
				vPos.y = y;
				if (selPartName != null)
				{
					PaintInstall(vPos, selPartName, angle, ji, ref installIa);
				}
				else
				{
					PaintOrder(vPos, ji);
				}
				count++;
				if (count > 6)
				{
					count = 0;
					yield return null;
				}
			}
		}
		bPoolShipUpdates = true;
		if (Paused != oldPauseState)
		{
			Paused = oldPauseState;
		}
	}

	private void PaintInstall(Vector2 vPos, string strPartName, float fAngle, JsonInstallable jInst, ref Interaction ia)
	{
		GameObject gameObject = CreatePartFromName(strPartName);
		if (gameObject == null)
		{
			return;
		}
		Item component = gameObject.GetComponent<Item>();
		if (component == null)
		{
			UnityEngine.Object.Destroy(gameObject);
			return;
		}
		component.SetToMousePosition(vPos);
		component.fLastRotation = fAngle;
		gameObject.layer = LayerMask.NameToLayer("Default");
		if (bShipEditBG)
		{
			if (shipCurrentLoaded.BGItemFits(component))
			{
				shipCurrentLoaded.BGItemAdd(component);
				Debug.Log("Placing BG at: " + component.transform.position.ToString() + "; local: " + component.transform.localPosition);
			}
		}
		else if (GUIInventory.instance.Selected == null && component.CheckFit(component.rend.bounds.center, shipCurrentLoaded, TileUtils.aSelPartTiles))
		{
			if (ia != null)
			{
				if (InstallFinish(ref ia, gameObject))
				{
					if (jInst == null)
					{
						FinishPaintingJob();
					}
					else
					{
						Interaction interaction = DataHandler.GetInteraction(jInst.strInteractionName);
						if (interaction == null)
						{
							return;
						}
						interaction.objThem = DataHandler.GetCondOwner(jInst.strActionCO);
						interaction.objThem.strPersistentCO = jInst.strPersistentCO;
						ia = InstallStart(interaction, gameObject);
					}
				}
				else
				{
					CondOwner selectedCrew = GetSelectedCrew();
					int hourFromS = MathUtils.GetHourFromS(StarSystem.fEpoch);
					if (selectedCrew != null && selectedCrew.Company.GetShift(hourFromS, selectedCrew).nID != 2)
					{
						selectedCrew.LogMessage(selectedCrew.FriendlyName + DataHandler.GetString("SHIFT_WARN_NONWORK"), "Bad", selectedCrew.strID);
					}
				}
				bContinuePaintingJob = true;
			}
			else
			{
				shipCurrentLoaded.AddCO(gameObject.GetComponent<CondOwner>(), bTiles: true);
			}
		}
		else
		{
			UnityEngine.Object.Destroy(gameObject);
		}
	}

	private void PaintPos(Vector2 vPos)
	{
		Item item = null;
		float num = 0f;
		if (goSelPart != null)
		{
			num = goSelPart.transform.rotation.eulerAngles.z;
			item = goSelPart.GetComponent<Item>();
			if (item == null)
			{
				return;
			}
			item.SetToMousePosition(vPos);
			if (bShipEditBG)
			{
				if (shipCurrentLoaded.BGItemFits(item))
				{
					shipCurrentLoaded.BGItemAdd(item);
					Debug.Log("Placing BG at: " + item.transform.position.ToString() + "; local: " + item.transform.localPosition);
				}
				goSelPart.layer = LayerMask.NameToLayer("Default");
				SetPartCursor(goSelPart.name);
				item = goSelPart.GetComponent<Item>();
				item.fLastRotation = num;
			}
			else
			{
				if (!(GUIInventory.instance.Selected == null) || !item.CheckFit(item.rend.bounds.center, shipCurrentLoaded, TileUtils.aSelPartTiles))
				{
					return;
				}
				nLastClickIndex = 0;
				vLastClick = default(Vector2);
				goSelPart.layer = LayerMask.NameToLayer("Default");
				if (iaItmInstall != null)
				{
					InstallFinish(ref iaItmInstall);
					Paused = false;
					if (bContinuePaintingJob)
					{
						StartPaintingJob(jiLast);
						item = goSelPart.GetComponent<Item>();
						item.fLastRotation = num;
					}
					else
					{
						CondOwner selectedCrew = GetSelectedCrew();
						int hourFromS = MathUtils.GetHourFromS(StarSystem.fEpoch);
						if (selectedCrew != null && selectedCrew.Company.GetShift(hourFromS, selectedCrew).nID != 2)
						{
							selectedCrew.LogMessage(selectedCrew.FriendlyName + DataHandler.GetString("SHIFT_WARN_NONWORK"), "Bad", selectedCrew.strID);
						}
					}
					bContinuePaintingJob = true;
				}
				else if (iaItmInstall == null)
				{
					bPoolShipUpdates = true;
					shipCurrentLoaded.AddCO(goSelPart.GetComponent<CondOwner>(), bTiles: true);
					SetPartCursor(goSelPart.GetComponent<CondOwner>().strName);
					item = goSelPart.GetComponent<Item>();
					item.fLastRotation = num;
				}
			}
		}
		else if (jiLast != null)
		{
			PaintOrder(vPos, jiLast);
		}
	}

	private void PaintOrder(Vector2 vPos, JsonInstallable ji)
	{
		if (ji == null)
		{
			return;
		}
		switch (ji.strName)
		{
		case "Cancel":
		{
			foreach (CondOwner item in FindCOsAtWorldPosition(vPos, null, bInteractive: false))
			{
				Placeholder component = item.GetComponent<Placeholder>();
				if (component != null)
				{
					CondOwner condOwner = DataHandler.GetCondOwner(component.strInstalledCO);
					if (GUIPDA.ctJobFilter != null && !GUIPDA.ctJobFilter.Triggered(condOwner))
					{
						ScheduleCODestruction(condOwner);
						continue;
					}
					ScheduleCODestruction(condOwner);
				}
				else if (component == null && GUIPDA.ctJobFilter != null && !GUIPDA.ctJobFilter.Triggered(item))
				{
					continue;
				}
				workManager.RemoveTask(item.strID);
				if (component != null)
				{
					component.Cancel();
				}
			}
			break;
		}
		case "Uninstall":
		case "Scrap":
		case "Repair":
		case "Dismantle":
		{
			foreach (CondOwner item2 in FindCOsAtWorldPosition(vPos, null, bInteractive: false))
			{
				if (GUIPDA.ctJobFilter != null && !GUIPDA.ctJobFilter.Triggered(item2))
				{
					continue;
				}
				foreach (string jobAction in item2.GetJobActions(ji.strName))
				{
					Interaction interaction2 = DataHandler.GetInteraction(jobAction);
					if (interaction2 != null && interaction2.Triggered(GetSelectedCrew(), item2, bStats: false, bIgnoreItems: true))
					{
						Task2 task4 = new Task2();
						task4.strDuty = "Construct";
						task4.strInteraction = jobAction;
						task4.strTargetCOID = item2.strID;
						task4.strName = ji.strName + "Job" + item2.strID;
						workManager.AddTask(task4);
						break;
					}
				}
			}
			break;
		}
		case "Mine":
		{
			foreach (CondOwner item3 in FindCOsAtWorldPosition(vPos, null, bInteractive: false))
			{
				if (GUIPDA.ctJobFilter != null && !GUIPDA.ctJobFilter.Triggered(item3))
				{
					continue;
				}
				foreach (string item4 in item3.aInteractions.Where((string i) => i.Contains("ACTMine")))
				{
					Interaction interaction = DataHandler.GetInteraction(item4);
					if (interaction != null && interaction.Triggered(GetSelectedCrew(), item3, bStats: false, bIgnoreItems: true))
					{
						Task2 task3 = new Task2();
						task3.strDuty = "Demolish";
						task3.strInteraction = item4;
						task3.strTargetCOID = item3.strID;
						task3.strName = "MineJob" + item3.strID;
						workManager.AddTask(task3);
						break;
					}
				}
			}
			break;
		}
		case "Reload":
		{
			foreach (CondOwner item5 in FindCOsAtWorldPosition(vPos, null, bInteractive: false))
			{
				if (item5.HasCond("IsShipWeapon") && !(item5.objContainer == null))
				{
					Interaction reloadInteraction = workManager.GetReloadInteraction(item5.objContainer.ctAllowed);
					if (reloadInteraction != null)
					{
						Task2 task2 = new Task2();
						task2.strName = reloadInteraction.strName;
						task2.strInteraction = reloadInteraction.strName;
						task2.strTargetCOID = item5.strID;
						task2.strDuty = "Haul";
						task2.bManual = false;
						objInstance.workManager.AddTask(task2);
					}
				}
			}
			break;
		}
		case "Haul":
		{
			foreach (CondOwner item6 in FindCOsAtWorldPosition(vPos, null, bInteractive: false))
			{
				if (WorkManager.CTHaul.Triggered(item6))
				{
					Task2 task = new Task2();
					task.strDuty = "Haul";
					task.strInteraction = "ACTHaulItem";
					task.strTargetCOID = item6.strID;
					task.strName = "HaulJob" + item6.strID;
					workManager.AddTask(task);
				}
			}
			break;
		}
		}
	}

	private void SelectCO(CondOwner co, bool bUnselect = false)
	{
		Debug.Log("Selecting: " + co.strName);
		CondOwner selectedCrew = GetSelectedCrew();
		if (bUnselect)
		{
			aSelected.Remove(co);
			if (co != null)
			{
				co.Selected = false;
			}
			inventoryGUI.UnsetDoll();
		}
		else if (co != null && aSelected.IndexOf(co) < 0)
		{
			aSelected.Add(co);
			co.Selected = true;
			inventoryGUI.UnsetDoll();
		}
		UpdateLog(co, null);
		if (bShipEdit)
		{
			foreach (GameObject aField in aFields)
			{
				UnityEngine.Object.Destroy(aField);
			}
			aFields.Clear();
			GUIShipEdit.Instance.SetPartEdit(co, aFields);
		}
		if (inventoryGUI.IsOpen && co != null && co.IsHumanOrRobot && (selectedCrew != co || inventoryGUI.PaperDollManager.strCOIDLast != co.strID))
		{
			CommandInventory.ToggleInventory(co);
			CommandInventory.ToggleInventory(co);
		}
		if (selectedCrew != co)
		{
			ResetAutoPause();
		}
		if ((co.HasCond("IsPlayerCrew") || co.HasCond("IsPlayer")) && !bUnselect)
		{
			AIManual(co.HasCond("IsAIManual"));
		}
	}

	public void ShowBlocksAndLights(CondOwner objCO, bool bShow)
	{
		if (!(objCO == null))
		{
			ShowBlocksAndLights(objCO.Item, bShow);
		}
	}

	public void ShowBlocksAndLights(Item item, bool bShow)
	{
		if (item == null)
		{
			return;
		}
		bool flag = false;
		foreach (Block aBlock in item.aBlocks)
		{
			if (bShow)
			{
				if (blocks.Add(aBlock))
				{
					aBlock.UpdateStats();
					flag = true;
				}
			}
			else
			{
				flag |= blocks.Remove(aBlock);
			}
		}
		float num = -1f;
		foreach (Visibility aLight in item.aLights)
		{
			if (aLight.Radius > num)
			{
				num = aLight.Radius;
			}
			if (bShow)
			{
				aLights.Add(aLight);
			}
			else
			{
				aLights.Remove(aLight);
			}
		}
		if (flag && !bPoolVisUpdates)
		{
			num = ((num < 0f) ? Visibility.DEFAULTVISIBILITYRANGE : num);
			UpdateVisLights(item.transform.position.ToVector2(), num);
		}
	}

	private void UpdateVisLights(Vector2 positionOther, float range = 0f)
	{
		float num = range * range;
		foreach (Visibility aLight in aLights)
		{
			if (!(aLight.GO == null) && aLight.GO.activeInHierarchy && !(MathUtils.GetDistanceSquared(positionOther, aLight.transform.position.ToVector2()) > num))
			{
				aLight.bRedraw = true;
			}
		}
		if (MathUtils.GetDistanceSquared(positionOther, visPlayer.transform.position.ToVector2()) <= num)
		{
			visPlayer.bRedraw = true;
		}
		bPoolVisUpdates = false;
	}

	private void UpdateVisLights()
	{
		foreach (Visibility aLight in aLights)
		{
			if (!(aLight.GO == null) && aLight.GO.activeInHierarchy)
			{
				aLight.bRedraw = true;
			}
		}
		visPlayer.bRedraw = true;
		bPoolVisUpdates = false;
	}

	public Transform MakeGenericVisibility(JsonLight jl, bool lightSprite = false)
	{
		Transform transform = new GameObject().transform;
		transform.SetParent(shipCurrentLoaded.gameObject.transform);
		transform.name = "Generic Light";
		string cookie = "ItmLitSphere01";
		Visibility visibility = UnityEngine.Object.Instantiate(Visibility.visTemplate);
		visibility.LightColor = DataHandler.GetColor(jl.strColor);
		visibility.GO.name = jl.strName;
		visibility.Parent = transform;
		visibility.tfParent = transform;
		visibility.transform.localScale = new Vector3(2f, 2f, 2f);
		visibility.SetCookie(cookie);
		Vector2 vector = default(Vector2);
		vector = jl.ptPos;
		float x = 1f * vector.x / 16f;
		float y = 1f * vector.y / 16f;
		visibility.ptOffset = new Vector2(x, y);
		if (lightSprite)
		{
			Transform obj = DataHandler.GetMesh("prefabQuadLightSprite").transform;
			obj.SetParent(transform);
			obj.rotation = Quaternion.Euler(-90f, 0f, 0f);
			obj.localPosition = Vector3.zero;
			Renderer component = obj.GetComponent<Renderer>();
			component.sharedMaterial = DataHandler.GetMaterial(component, jl.strImg);
			obj.gameObject.SetActive(value: true);
		}
		aLights.Add(visibility);
		visibility.GO.SetActive(value: true);
		return transform;
	}

	public void AddLight(Visibility vis)
	{
		aLights.Add(vis);
	}

	public void RemoveLight(Visibility vis)
	{
		aLights.Remove(vis);
	}

	private Interaction InstallStart(Interaction iaInstall, GameObject goPart = null)
	{
		if (iaInstall == null)
		{
			return null;
		}
		if (!DataHandler.dictCOs.ContainsKey(iaInstall.strStartInstall) && !DataHandler.dictCOOverlays.ContainsKey(iaInstall.strStartInstall))
		{
			Debug.Log("Error: Cannot install item of type: " + iaInstall.strStartInstall);
			return null;
		}
		MeshRenderer meshRenderer = null;
		if (goPart == null)
		{
			SetPartCursor(iaInstall.strStartInstall);
			meshRenderer = goSelPart.GetComponent<MeshRenderer>();
		}
		else
		{
			meshRenderer = goPart.GetComponent<MeshRenderer>();
		}
		Vector2 mainTextureOffset = meshRenderer.sharedMaterial.mainTextureOffset;
		Vector2 mainTextureScale = meshRenderer.sharedMaterial.mainTextureScale;
		Material material = DataHandler.GetMaterial(meshRenderer, "GUIGrid16");
		Texture mainTexture = meshRenderer.sharedMaterial.mainTexture;
		meshRenderer.material = UnityEngine.Object.Instantiate(material);
		meshRenderer.sharedMaterial.mainTexture = mainTexture;
		meshRenderer.sharedMaterial.mainTextureOffset = mainTextureOffset;
		meshRenderer.sharedMaterial.mainTextureScale = mainTextureScale;
		MaterialPropertyBlock materialPropertyBlock = new MaterialPropertyBlock();
		meshRenderer.GetPropertyBlock(materialPropertyBlock);
		materialPropertyBlock.SetColor("_Color", new Color(1f, 1f, 1f, 0.5f));
		meshRenderer.SetPropertyBlock(materialPropertyBlock);
		TileUtils.goPartTiles.SetActive(value: true);
		if (iaInstall.objThem != null)
		{
			iaInstall.objThem.gameObject.SetActive(value: false);
		}
		if (inventoryGUI.IsOpen)
		{
			CommandInventory.ToggleInventory(GetSelectedCrew());
		}
		if (bcombatAutoPauseAllowed && !Paused)
		{
			Paused = true;
		}
		bUnpauseShield = true;
		return iaInstall;
	}

	private bool InstallFinish(ref Interaction iaItmInsta, GameObject goPart = null)
	{
		if (iaItmInsta == null)
		{
			return false;
		}
		GameObject gameObject = ((goPart != null) ? goPart : goSelPart);
		iaItmInsta.objThem.transform.position = gameObject.transform.position;
		iaItmInsta.objThem.strPersistentCO = iaItmInsta.objThem.strPersistentCO;
		iaItmInsta.objThem.strPersistentCT = iaItmInsta.CTTestThem.strName;
		CondOwner cOPlaceholder = DataHandler.GetCOPlaceholder(gameObject.GetComponent<CondOwner>(), iaItmInsta.objThem, iaItmInsta.strName);
		MeshRenderer component = cOPlaceholder.GetComponent<MeshRenderer>();
		MaterialPropertyBlock materialPropertyBlock = new MaterialPropertyBlock();
		component.GetPropertyBlock(materialPropertyBlock);
		materialPropertyBlock.SetColor("_Color", new Color(1f, 1f, 1f, 0.5f));
		component.SetPropertyBlock(materialPropertyBlock);
		Tile tileAtWorldCoords = shipCurrentLoaded.GetTileAtWorldCoords1(iaItmInsta.objThem.transform.position.x, iaItmInsta.objThem.transform.position.y, bAllowDocked: true);
		if (tileAtWorldCoords == null)
		{
			tileAtWorldCoords = shipCurrentLoaded.GetTileAtWorldCoords1(vMouse.x, vMouse.y, bAllowDocked: true);
		}
		Ship ship = null;
		if (tileAtWorldCoords == null)
		{
			if (shipCurrentLoaded == null)
			{
				cOPlaceholder.Destroy();
				return false;
			}
			ship = shipCurrentLoaded;
		}
		else
		{
			ship = tileAtWorldCoords.coProps.ship;
		}
		ship.AddCO(cOPlaceholder, bTiles: true);
		if (goPart != null)
		{
			UnityEngine.Object.Destroy(goPart);
		}
		else
		{
			SetPartCursor(null);
		}
		TileUtils.goPartTiles.SetActive(value: false);
		bContinuePaintingJob = cOPlaceholder.strPersistentCO == null;
		CondOwner condOwner = null;
		if (!bContinuePaintingJob && GetSelectedCrew() != null)
		{
			iaItmInsta.objUs = GetSelectedCrew();
			condOwner = iaItmInsta.objThem;
			iaItmInsta.objThem = cOPlaceholder;
			iaItmInsta.bManual = true;
			workManager.ClaimTaskDirect(iaItmInsta);
		}
		else
		{
			Task2 task = new Task2();
			task.strDuty = "Construct";
			task.strInteraction = iaItmInsta.strName;
			task.strName = iaItmInsta.strTitle;
			task.strTargetCOID = cOPlaceholder.strID;
			workManager.AddTask(task);
		}
		if (condOwner != null && !condOwner.gameObject.activeInHierarchy)
		{
			condOwner.Destroy();
		}
		iaItmInsta = null;
		if (ship.DMGStatus == Ship.Damage.Derelict && system.GetShipOwner(ship.strRegID) != coPlayer.strID)
		{
			BeatManager.RunEncounter("ENCFirstInstallDerelict", bInterrupt: false);
		}
		return bContinuePaintingJob;
	}

	public void StartAction(string strImgCursor)
	{
		if (goPaintJob == null)
		{
			goPaintJob = Resources.Load("prefabBuildPaintGUI") as GameObject;
			goPaintJob = UnityEngine.Object.Instantiate(goPaintJob, CanvasManager.goCanvasGUI.transform);
		}
		goPaintJob.GetComponent<RawImage>().texture = DataHandler.LoadPNG(strImgCursor, bNorm: false);
	}

	public IEnumerator ScrollBottom(ScrollRect sr)
	{
		LayoutRebuilder.MarkLayoutForRebuild(sr.GetComponent<RectTransform>());
		yield return new WaitForSeconds(0.3f);
		sr.verticalNormalizedPosition = 0f;
	}

	public IEnumerator ScrollTop(ScrollRect sr)
	{
		LayoutRebuilder.ForceRebuildLayoutImmediate(sr.GetComponent<RectTransform>());
		yield return new WaitForEndOfFrame();
		yield return new WaitForEndOfFrame();
		sr.verticalNormalizedPosition = 1f;
	}

	public IEnumerator ScrollPos(ScrollRect sr, float fPos)
	{
		LayoutRebuilder.ForceRebuildLayoutImmediate(sr.GetComponent<RectTransform>());
		yield return new WaitForEndOfFrame();
		yield return new WaitForEndOfFrame();
		sr.verticalNormalizedPosition = fPos;
	}

	public void StartPaintingJob(JsonInstallable ji)
	{
		if (ji == null)
		{
			FinishPaintingJob();
		}
		else if (ji.strName == "Cancel")
		{
			StartAction("GUIActionCancel.png");
		}
		else if (ji.strName == "Uninstall")
		{
			StartAction("GUIActionUninstall.png");
		}
		else if (ji.strName == "Scrap")
		{
			StartAction("GUIActionScrap.png");
		}
		else if (ji.strName == "Repair")
		{
			StartAction("GUIActionRepair.png");
		}
		else if (ji.strName == "Dismantle")
		{
			StartAction("GUIActionDismantle.png");
		}
		else if (ji.strName == "Haul")
		{
			StartAction("GUIActionHaul.png");
		}
		else if (ji.strName == "Reload")
		{
			StartAction("GUIActionReload.png");
		}
		else if (ji.strName == "Mine")
		{
			StartAction("GUIActionMine.png");
		}
		else
		{
			Interaction interaction = DataHandler.GetInteraction(ji.strInteractionName);
			if (interaction == null)
			{
				return;
			}
			interaction.objThem = DataHandler.GetCondOwner(ji.strActionCO);
			interaction.objThem.strPersistentCO = ji.strPersistentCO;
			iaItmInstall = InstallStart(interaction);
		}
		jiLast = ji;
	}

	public void FinishPaintingJob()
	{
		UnityEngine.Object.Destroy(goPaintJob);
		SetPartCursor(null);
		TileUtils.goPartTiles.SetActive(value: false);
		if (iaItmInstall != null)
		{
			if (iaItmInstall.objThem != null)
			{
				iaItmInstall.objThem.Destroy();
			}
			iaItmInstall.Destroy();
			iaItmInstall = null;
		}
	}

	private bool GetMouseButtonDown(int which)
	{
		if (_commandSingleItem.InputAction.IsPressed())
		{
			return false;
		}
		return which switch
		{
			0 => _commandClick.InputAction.WasPressedThisFrame(), 
			1 => _commandRightClick.InputAction.WasPressedThisFrame(), 
			2 => _commandMiddleClick.InputAction.WasPressedThisFrame(), 
			_ => false, 
		};
	}

	public bool GetMouseButtonUp(int which)
	{
		if (_commandSingleItem.InputAction.IsPressed())
		{
			return false;
		}
		return which switch
		{
			0 => _commandClick.InputAction.WasReleasedThisFrame(), 
			1 => _commandRightClick.InputAction.WasReleasedThisFrame(), 
			2 => _commandMiddleClick.InputAction.WasReleasedThisFrame(), 
			_ => false, 
		};
	}

	private bool GetMouseButton(int which)
	{
		if (_commandSingleItem.InputAction.IsPressed())
		{
			return false;
		}
		return which switch
		{
			0 => _commandClick.InputAction.IsPressed(), 
			1 => _commandRightClick.InputAction.IsPressed(), 
			2 => _commandMiddleClick.InputAction.IsPressed(), 
			_ => false, 
		};
	}

	private static bool IsMouseOverGameWindow(Vector2 mousePos)
	{
		if (!(0f <= mousePos.x) || !(0f <= mousePos.y))
		{
			if (mousePos.x < (float)Screen.width)
			{
				return mousePos.y < (float)Screen.height;
			}
			return false;
		}
		return true;
	}

	private bool InGroundRange()
	{
		if (Mathf.Abs(Mathf.RoundToInt(inventoryGUI.CODoll.tfVector2Position.x) - Mathf.RoundToInt(vMouse.x)) <= 2)
		{
			return Mathf.Abs(Mathf.RoundToInt(inventoryGUI.CODoll.tfVector2Position.y) - Mathf.RoundToInt(vMouse.y)) <= 2;
		}
		return false;
	}

	private void MouseHandler()
	{
		List<CondOwner> list = FindCOsAtMousePosition(null, bInteractive: false);
		bool flag = false;
		CondOwner selected = GUIMegaToolTip.Selected;
		if (selected != null && list.Remove(selected))
		{
			list.Insert(0, selected);
		}
		for (int i = 0; i < list.Count; i++)
		{
			if (bRaiseUI)
			{
				break;
			}
			if (CanvasManager.IsCanvasQuitShowing())
			{
				break;
			}
			if (list[i].IsHumanOrRobot)
			{
				tooltip.SetTooltipCrew(list[i], GUITooltip.TooltipWindow.Crew);
				flag = true;
				break;
			}
			if (workManager.COIDHasTasks(list[i].strID))
			{
				tooltip.SetTooltipMulti(list, GUITooltip.TooltipWindow.Task);
				flag = true;
				break;
			}
		}
		if (!flag && tooltip.window != GUITooltip.TooltipWindow.QAB && tooltip.window != GUITooltip.TooltipWindow.MTT)
		{
			tooltip.SetTooltip(null, GUITooltip.TooltipWindow.Hide);
		}
		vLastMouse = InputManager.MousePosition;
		bool flag2 = (bRaiseUI && CanvasManager.State == CanvasManager.GUIState.SHIPGUI) || GUIQuickBar.IsBeingDragged || Info.focused;
		bool flag3 = goSelPart != null || goPaintJob != null;
		if (goSelPart != null)
		{
			bool flag4 = true;
			if (GUIInventory.instance.Selected != null && GUIInventory.instance.bLastMouseInInv)
			{
				flag4 = false;
			}
			if (flag4)
			{
				goSelPart.SetActive(value: true);
				flag3 = true;
				TileUtils.goSelPartTiles.SetActive(value: true);
				cgRotate.alpha = 1f;
			}
			else
			{
				goSelPart.SetActive(value: false);
				flag3 = false;
				TileUtils.goSelPartTiles.SetActive(value: false);
				cgRotate.alpha = 0f;
			}
		}
		if (flag3)
		{
			Canvas component = CanvasManager.goCanvasGUI.GetComponent<Canvas>();
			RectTransformUtility.ScreenPointToLocalPointInRectangle(component.transform as RectTransform, vLastMouse, component.worldCamera, out var localPoint);
			if (goSelPart != null)
			{
				Item component2 = goSelPart.GetComponent<Item>();
				if (component2 != null)
				{
					rectRotate.localPosition = localPoint + new Vector2(0f, component2.nHeightInTiles * 16 * 2);
				}
				else
				{
					rectRotate.localPosition = localPoint + new Vector2(0f, 0f);
				}
				if (bShipEdit)
				{
					Visibility[] componentsInChildren = goSelPart.GetComponentsInChildren<Visibility>();
					if (componentsInChildren != null)
					{
						Visibility[] array = componentsInChildren;
						for (int j = 0; j < array.Length; j++)
						{
							array[j].bRedraw = true;
						}
					}
				}
			}
			if (goPaintJob != null)
			{
				goPaintJob.transform.localPosition = localPoint;
			}
		}
		if (!flag2)
		{
			float y = _commandScroll.InputAction.ReadValue<Vector2>().y;
			if (y != 0f && !EventSystem.current.IsPointerOverGameObject() && IsMouseOverGameWindow(vLastMouse))
			{
				vPanVelocity.z -= 0.2f * y;
			}
			if (GetMouseButtonDown(0))
			{
				vDragStart = vMouse;
				vDragStartScreen = InputManager.MousePosition;
				if (!flag3 && GUIInventory.instance.IsOpen && !EventSystem.current.IsPointerOverGameObject() && !GUIQuickBar.IsBeingDragged && !Info.focused && InGroundRange() && !_commandForceWalk.InputAction.IsPressed())
				{
					foreach (CondOwner item in GetMouseOverCO(_layerMaskDefTileHelpers, GUIInventory.CTGroundItem))
					{
						if (!CoHighlighter.ShouldCondOwnerHighlight(item, bIgnoreGlass: false))
						{
							continue;
						}
						GUIInventoryItem gUIInventoryItem = GUIInventoryItem.SpawnInventoryItem(item.strID);
						if (gUIInventoryItem != null)
						{
							if (_commandQuickMove.InputAction.IsPressed())
							{
								gUIInventoryItem.OnShiftPointerDown();
								break;
							}
							gUIInventoryItem.AttachToCursor();
							item.RemoveFromCurrentHome();
							item.Visible = false;
							GUIInventory.instance.JustClickedItem = true;
							break;
						}
					}
				}
			}
			if (GetMouseButtonDown(2))
			{
				vDragStartScreen = InputManager.MousePosition;
				vDragStart = vMouse;
			}
			else if (GetMouseButtonDown(1))
			{
				if (bShipEdit)
				{
					if (goSelPart != null)
					{
						SetPartCursor(null);
						return;
					}
					if (TileUtils.bShowTiles)
					{
						SetBracketTarget(null, bUpdateOnly: false);
						return;
					}
					if (bShipEditBG)
					{
						List<Item> mouseOverBG = GetMouseOverBG(new string[1] { "Default" });
						if (mouseOverBG != null && mouseOverBG.Count > 0)
						{
							shipCurrentLoaded.BGItemRemove(mouseOverBG[0]);
						}
					}
					else
					{
						nLastClickIndex = 0;
						vLastClick = default(Vector2);
						CondTrigger condTrigger = ctSelectFilter;
						ctSelectFilter = new CondTrigger();
						List<string> list2 = new List<string>();
						if (condTrigger != null)
						{
							list2.AddRange(condTrigger.aForbids);
							Array.Copy(condTrigger.aReqs, ctSelectFilter.aReqs, condTrigger.aReqs.Length);
						}
						list2.Add("IsRoom");
						ctSelectFilter.aForbids = list2.ToArray();
						GameObject gameObject = ClickSelectScenePart(_layerMaskDefault);
						if (gameObject != null)
						{
							shipCurrentLoaded.RemoveCO(gameObject.GetComponent<CondOwner>());
							UnityEngine.Object.Destroy(gameObject);
						}
						ctSelectFilter = condTrigger;
					}
				}
			}
			else if (GetMouseButton(0))
			{
				if (!EventSystem.current.IsPointerOverGameObject() && EventSystem.current.currentSelectedGameObject == null && !GUIQuickBar.IsBeingDragged && !Info.focused && !_commandForceWalk.InputAction.IsPressed())
				{
					if (bShipEdit && _commandEyedropper.InputAction.IsPressed())
					{
						List<CondOwner> mouseOverCO = GetMouseOverCO(_layerMaskDefault, null);
						if (mouseOverCO.Count > 0)
						{
							SetPartCursor(mouseOverCO[0].strCODef);
							GUIShipEdit.Instance.RememberPart(mouseOverCO[0].strCODef);
						}
						else
						{
							SetPartCursor(null);
						}
					}
					else if (flag3 && GUIInventory.instance.Selected == null && GUIShipEdit.Instance.chkFill.isOn)
					{
						FloodFill();
					}
					else if (!inventoryGUI.IsOpen && (iaItmInstall == null || iaItmInstall.objThem.strPersistentCO == null))
					{
						float num = Mathf.Abs(InputManager.MousePosition.x - vDragStartScreen.x);
						if ((Mathf.Abs(InputManager.MousePosition.y - vDragStartScreen.y) > 16f || num > 16f) && lineSelectRect == null)
						{
							lineSelectRect = new VectorLine("SelectionRect", new List<Vector2>(5), 1.5f, LineType.Continuous, Joins.Weld);
							lineSelectRect.color = Color.white;
							lineSelectRect.SetCanvas(CanvasManager.goCanvasGUI, worldPositionStays: false);
						}
					}
				}
			}
			else if (GetMouseButtonUp(0))
			{
				bPoolShipUpdates = false;
				GameObject gameObject2 = null;
				if (_commandForceWalk.InputAction.IsPressed())
				{
					Walk();
					bJustClickedInput = true;
				}
				else if (contextMenuPool.IsRaised)
				{
					LowerContextMenu();
				}
				else if (lineSelectRect != null)
				{
					VectorLine.Destroy(ref lineSelectRect);
					SetBracketTarget(null, bUpdateOnly: false);
					Bounds viewportBounds = GetViewportBounds(camMain, vDragStart, vMouse);
					if (TileUtils.bShowTiles || (bShipEdit && goSelPart == null))
					{
						SelectBounds(viewportBounds, TileUtils.bShowTiles);
					}
					else if (flag3)
					{
						PaintBounds(viewportBounds);
					}
				}
				else if (!EventSystem.current.IsPointerOverGameObject())
				{
					if (TileUtils.bShowTiles)
					{
						List<CondOwner> mouseOverCO2 = GetMouseOverCO(new string[1] { "Tile Helpers" }, ctSelectFilter);
						gameObject2 = null;
						foreach (CondOwner item2 in mouseOverCO2)
						{
							if (gameObject2 != null)
							{
								if (item2.ship == shipCurrentLoaded)
								{
									gameObject2 = item2.gameObject;
								}
							}
							else
							{
								gameObject2 = item2.gameObject;
							}
						}
						CondOwner condOwner = null;
						if (gameObject2 != null)
						{
							condOwner = gameObject2.GetComponent<CondOwner>();
							Tile component3 = gameObject2.GetComponent<Tile>();
							SetBracketTarget(condOwner.strID, bUpdateOnly: false);
							SelectCO(condOwner);
							int value = shipCurrentLoaded.aTiles.IndexOf(component3);
							if (!_commandZoneAlternate.InputAction.IsPressed())
							{
								foreach (JsonZone value2 in shipCurrentLoaded.mapZones.Values)
								{
									if (value2.aTiles.Contains(value))
									{
										int[] aTiles = value2.aTiles;
										foreach (int index in aTiles)
										{
											SelectCO(shipCurrentLoaded.aTiles[index].coProps);
										}
										break;
									}
								}
							}
						}
						else
						{
							SetBracketTarget(null, bUpdateOnly: false);
						}
						OnTileSelectionUpdated.Invoke(aSelected);
					}
					else if (flag3)
					{
						PaintPos(ActiveCam.ScreenPointToRay(Input.mousePosition).origin);
					}
					else if (!bJustClickedInput && GUIInventory.instance.Selected == null && !GUIInventory.instance.JustClickedItem)
					{
						if (coConnectMode != null)
						{
							gameObject2 = ClickSelectScenePart(new string[1] { "Tile Helpers" });
						}
						else if (!bShipEditBG)
						{
							CondTrigger condTrigger2 = ctSelectFilter;
							if (bShipEdit || bDebugShow)
							{
								ctSelectFilter = CTShipEditSelect;
							}
							else
							{
								ctSelectFilter = DataHandler.GetCondTrigger("TCanBeSelected");
							}
							List<CondOwner> list3 = GetMouseOverCO(_layerMaskDefTileHelpers, null).ToList();
							Room room = null;
							if (shipCurrentLoaded != null)
							{
								room = shipCurrentLoaded.GetRoomAtWorldCoords1(vMouse, bAllowDocked: true);
							}
							if (room != null)
							{
								list3.Remove(room.CO);
								list3.Add(room.CO);
							}
							if (!bShipEdit && list3.Count > 0 && list3.IndexOf(GUIMegaToolTip.Selected) >= 0)
							{
								list3.Clear();
								OnRightClick.Invoke(list3);
							}
							gameObject2 = ((!bShipEdit) ? ClickSelectScenePart(_layerMaskDefTileHelpers) : ClickSelectScenePart(_layerMaskDefault));
							if (gameObject2 == null)
							{
								if (bShipEdit)
								{
									SetBracketTarget(null, bUpdateOnly: false);
								}
								else if (list3.Count > 0)
								{
									Walk();
								}
							}
							ctSelectFilter = condTrigger2;
						}
						if (coConnectMode != null)
						{
							CondOwner condOwner2 = null;
							if (gameObject2 != null)
							{
								condOwner2 = gameObject2.GetComponent<CondOwner>();
								if (!ctSelectFilter.Triggered(condOwner2))
								{
									condOwner2 = null;
								}
							}
							if (igdConnectMode == null)
							{
								coConnectMode = null;
							}
							else
							{
								igdConnectMode.SetInput(condOwner2);
							}
							if (coConnectLastCrew != null)
							{
								SetBracketTarget(coConnectLastCrew.strID, bUpdateOnly: false, noAuto: true);
								coConnectLastCrew = null;
								coConnectMode = null;
							}
							else
							{
								SetBracketTarget(null, bUpdateOnly: false);
							}
							HideInputSelector();
							GUIModal.Instance.Hide();
						}
						else if ((gameObject2 != null && !bShipEdit) || (bShipEdit && Input.GetKey(KeyCode.LeftShift)))
						{
							CondOwner component4 = gameObject2.GetComponent<CondOwner>();
							if (component4.strCODef.IndexOf("Closed") >= 0 || component4.strCODef.IndexOf("Open") >= 0)
							{
								_ = component4.ship;
								CondOwner condOwner3 = null;
								string strCODef = component4.strCODef;
								strCODef = ((strCODef.IndexOf("Open") < 0) ? strCODef.Replace("Closed", "Open") : strCODef.Replace("Open", "Closed"));
								condOwner3 = DataHandler.GetCondOwner(strCODef, component4.strID);
								if (condOwner3 != null)
								{
									component4.ModeSwitch(condOwner3, component4.tf.position);
								}
							}
						}
						else if (CanvasManager.State == CanvasManager.GUIState.SOCIAL && GUISocialCombat2.coUs == GetSelectedCrew() && GUISocialCombat2.coUs != GUISocialCombat2.coThem)
						{
							if (GUISocialCombat2.coUs.bAlive)
							{
								Interaction interaction = DataHandler.GetInteraction("SOCSnub");
								interaction.objUs = GUISocialCombat2.coUs;
								interaction.objThem = GUISocialCombat2.coThem;
								interaction.bManual = true;
								GUISocialCombat2.coUs.AIIssueOrder(interaction.objThem, interaction, bPlayerOrdered: true, null);
								Paused = false;
							}
							else
							{
								GUISocialCombat2.objInstance.EndSocialCombat();
							}
						}
					}
				}
				else if (GUIInventory.instance.Selected != null && !GUIInventory.instance.JustClickedItem && !GUIInventory.instance.bLastMouseInInv)
				{
					Walk();
				}
			}
			else if (GetMouseButtonUp(1))
			{
				if ((goSelPart != null && inventoryGUI.Selected == null) || goPaintJob != null || guiPDA.JobsActive)
				{
					guiPDA.HideJobPaintUI();
					return;
				}
				if (!bJustClickedInput)
				{
					if (ZoneMenuOpen)
					{
						return;
					}
					if (objInstance.coConnectMode != null)
					{
						CloseConnectionMode();
					}
					else if ((contextMenuPool.IsRaised && !bRaisedMenuThisFrame) || (double)RightMouseButtonDownTimer > 0.3)
					{
						RightMouseButtonDownTimer = 0f;
						LowerContextMenu();
					}
					else if (EventSystem.current.IsPointerOverGameObject())
					{
						if (CanvasManager.IsOverUIElement(goCrewBar) && CanvasManager.IsOverUIElement(goCrewBarPortraitButton))
						{
							OnRightClick.Invoke(new List<CondOwner> { GetSelectedCrew() });
						}
					}
					else if (!bShipEdit && !bRaiseUI && !inventoryGUI.ClickedInventory(InputManager.MousePosition))
					{
						RightMouseButtonDownTimer = 0f;
						if (bDebugShow)
						{
							ctSelectFilter = null;
						}
						else
						{
							ctSelectFilter = DataHandler.GetCondTrigger("TCanBeSelectedMTT");
						}
						List<CondOwner> mouseOverCO3 = GetMouseOverCO(_layerMaskDefLosTileHelpers, ctSelectFilter);
						Room room2 = null;
						if (shipCurrentLoaded != null)
						{
							room2 = shipCurrentLoaded.GetRoomAtWorldCoords1(vMouse, bAllowDocked: true);
						}
						if (room2 != null)
						{
							mouseOverCO3.Remove(room2.CO);
							mouseOverCO3.Add(room2.CO);
						}
						if (mouseOverCO3 != null && mouseOverCO3.Count > 0)
						{
							OnRightClick.Invoke(mouseOverCO3);
						}
						ctSelectFilter = null;
					}
				}
			}
			else if (GetMouseButton(2))
			{
				float num2 = InputManager.MousePosition.x - vDragStartScreen.x;
				float num3 = InputManager.MousePosition.y - vDragStartScreen.y;
				float num4 = 1f;
				if (camMain != null)
				{
					num4 = camMain.aspect;
				}
				delX += num2 / 15f * num4;
				delY += num3 / 15f;
			}
			else
			{
				if (!flag3 && GUIInventory.instance.IsOpen && !EventSystem.current.IsPointerOverGameObject() && !GUIQuickBar.IsBeingDragged && !Info.focused)
				{
					bool flag5 = InGroundRange();
					bool flag6 = false;
					foreach (CondOwner item3 in GetMouseOverCO(_layerMaskDefTileHelpers, GUIInventory.CTGroundItem))
					{
						if (CoHighlighter.ShouldCondOwnerHighlight(item3, bIgnoreGlass: true))
						{
							item3.Highlight = true;
							_highlightOnHoverCos.Add(item3);
							flag6 = CoHighlighter.ShouldCondOwnerHighlight(item3, bIgnoreGlass: false);
							if (flag6 && flag5)
							{
								GUIInventory.instance.FocusWindow(item3);
							}
						}
					}
					if (_commandForceWalk.InputAction.IsPressed())
					{
						SetCursor(1);
						GUIInventory.instance.UnfocusWindows();
					}
					else if (flag6 && flag5)
					{
						SetCursor(2);
					}
					else
					{
						SetCursor(1);
						GUIInventory.instance.UnfocusWindows();
					}
				}
				else
				{
					SetCursor(0);
				}
				if (GUITooltip2.Visible && toolMessageLog.bMouseOver)
				{
					int num5 = TMP_TextUtilities.FindIntersectingLink(txtMessageLog, vLastMouse, UICamera);
					if (num5 != -1)
					{
						TMP_LinkInfo tMP_LinkInfo = txtMessageLog.textInfo.linkInfo[num5];
						string linkID = tMP_LinkInfo.GetLinkID();
						foreach (JsonLogMessage aMessage in GetSelectedCrew().aMessages)
						{
							if (aMessage != null && !(aMessage.strName != linkID))
							{
								GUITooltip2.SetToolTip(toolMessageLog.strTtTitle, aMessage.strMessage);
								break;
							}
						}
					}
					else
					{
						GUITooltip2.SetToolTip(toolMessageLog.strTtTitle, toolMessageLog.strTtBody);
					}
				}
			}
			if (goSelPart != null)
			{
				Item component5 = goSelPart.GetComponent<Item>();
				if (component5 != null)
				{
					component5.SetToMousePosition(vMouse);
					if (component5.jid.strName != "Cancel")
					{
						component5.CheckFit(component5.rend.bounds.center, shipCurrentLoaded, TileUtils.aSelPartTiles);
					}
				}
				CondOwner component6 = goSelPart.GetComponent<CondOwner>();
				if (component6 == null)
				{
					return;
				}
				Powered component7 = goSelPart.GetComponent<Powered>();
				if (component7 != null && !component6.HasCond("IsPowerInputIgnore") && component7.jsonPI.aInputPts != null && component7.jsonPI.aInputPts.Length != 0)
				{
					for (int k = 0; k < component7.jsonPI.aInputPts.Length; k++)
					{
						Vector3 position = component6.GetPos(component7.jsonPI.aInputPts[k]);
						position.z = -8f;
						TileUtils.GetPowerInputGridSprite(k).transform.position = position;
						TileUtils.GetPowerInputGridSprite(k).SetActive(value: true);
					}
				}
				Vector3 zero = Vector3.zero;
				if (component6.mapPoints != null && component6.mapPoints.ContainsKey("PowerOutput"))
				{
					zero = component6.GetPos("PowerOutput");
					zero.z = -8f;
					TileUtils.GetPowerOutputGridSprite().transform.position = zero;
					TileUtils.GetPowerOutputGridSprite().SetActive(value: true);
				}
				zero = Vector3.zero;
				if (component6.mapPoints.ContainsKey("use"))
				{
					zero = component6.mapPoints["use"];
					if (zero.x != 0f || zero.y != 0f)
					{
						zero = component6.GetPos("use");
						zero.z = -8f;
						TileUtils.GetUseGridSprite().transform.position = zero;
						TileUtils.GetUseGridSprite().SetActive(value: true);
					}
				}
				zero = Vector3.zero;
				if (component6.mapPoints.ContainsKey("ReactorPlug"))
				{
					zero = component6.GetPos("ReactorPlug");
					zero.z = -8f;
					TileUtils.GetReactorGridSprite().transform.position = zero;
					TileUtils.GetReactorGridSprite().SetActive(value: true);
				}
			}
		}
		bJustClickedInput = false;
	}

	public void CloseConnectionMode()
	{
		if (coConnectLastCrew != null)
		{
			SetBracketTarget(coConnectLastCrew.strID, bUpdateOnly: false, noAuto: true);
			coConnectLastCrew = null;
			coConnectMode = null;
		}
		else
		{
			SetBracketTarget(null, bUpdateOnly: false);
		}
		HideInputSelector();
		GUIModal.Instance.Hide();
	}

	public void OnHoldRMB(Action callback)
	{
		if (RightMouseButtonDownTimer < RightMouseButtonDownMax)
		{
			RightMouseButtonDownTimer += Time.deltaTime;
		}
		else if (RightMouseButtonDownTimer >= RightMouseButtonDownMax && RightMouseButtonDownTimer < 5f && !contextMenuPool.IsRaised)
		{
			if (goSelPart != null)
			{
				SetPartCursor(null);
				iaItmInstall = null;
			}
			RightMouseButtonDownTimer = 10f;
			callback?.Invoke();
			cursorRoundel.ResetFill();
		}
	}

	private void Walk()
	{
		CondOwner bracketTarget = GetBracketTarget();
		if (bracketTarget == null)
		{
			bracketTarget = coPlayer;
		}
		if (bracketTarget != null && bracketTarget.bAlive)
		{
			Ray ray = camMain.ScreenPointToRay(InputManager.MousePosition);
			Tile tileAtWorldCoords = shipCurrentLoaded.GetTileAtWorldCoords1(ray.origin.x, ray.origin.y, bAllowDocked: true);
			bracketTarget.AIIssueOrder(null, null, bPlayerOrdered: true, tileAtWorldCoords, ray.origin.x, ray.origin.y);
			AIManual(manualMode: true);
			if (Paused)
			{
				fPauseFlashExtra = Time.realtimeSinceStartup + 3f;
				AudioManager.am.PlayAudioEmitter("UIMessageLogBad", bLoop: false, bNoRestart: true);
			}
		}
	}

	private void MoveViewHandler()
	{
		if (coCamCenter == null)
		{
			coCamCenter = coPlayer;
		}
		float num = 1f;
		if (_commandPanFaster.InputAction.IsPressed())
		{
			num *= 3f;
		}
		if (_commandPanSlower.InputAction.IsPressed())
		{
			num /= 3f;
		}
		if (_commandPanCameraUp.InputAction.IsPressed() && _commandPanCameraUp.CanExecute())
		{
			delY += 1f;
		}
		if (_commandPanCameraDown.InputAction.IsPressed() && _commandPanCameraDown.CanExecute())
		{
			delY -= 1f;
		}
		if (_commandPanCameraLeft.InputAction.IsPressed() && _commandPanCameraLeft.CanExecute())
		{
			delX -= 1f;
		}
		if (_commandPanCameraRight.InputAction.IsPressed() && _commandPanCameraRight.CanExecute())
		{
			delX += 1f;
		}
		if (_commandZoomIn.InputAction.IsPressed() && _commandZoomIn.CanExecute())
		{
			delZ -= 1f;
		}
		else if (_commandZoomOut.InputAction.IsPressed() && _commandZoomOut.CanExecute())
		{
			delZ += 1f;
		}
		float num2 = TimeElapsedUnscaled();
		float num3 = camMain.orthographicSize * num2;
		if (CanvasManager.State == CanvasManager.GUIState.SHIPGUI)
		{
			delX = 0f;
			delY = 0f;
			delZ = 0f;
		}
		delX = Mathf.Clamp(delX, -1f, 1f);
		delY = Mathf.Clamp(delY, -1f, 1f);
		delZ = Mathf.Clamp(delZ, -1f, 1f);
		vPanVelocity.x += delX * num2 * camMain.orthographicSize;
		vPanVelocity.y += delY * num2 * camMain.orthographicSize;
		vPanVelocity.z += delZ * num2;
		if (delX != 0f || delY != 0f)
		{
			camFollow = false;
		}
		float num4 = -3f;
		if (delX == 0f && delY == 0f && delZ == 0f)
		{
			num4 = -15f;
		}
		vPanVelocity.x *= Mathf.Exp(num4 * num2);
		vPanVelocity.y *= Mathf.Exp(num4 * num2);
		vPanVelocity.z *= Mathf.Exp(num4 * num2);
		float num5 = num * fCamSpeed * vPanVelocity.x * num2;
		float num6 = num * fCamSpeed * vPanVelocity.y * num2;
		float magnitude = camTravel.magnitude;
		if (magnitude > 1E-06f)
		{
			if (magnitude > 4f * camTravelVelocity)
			{
				camTravelVelocity = Mathf.Min(camTravelVelocity + num3, 10f);
			}
			else
			{
				camTravelVelocity = Mathf.Max(camTravelVelocity - num3, 0.1f);
			}
			float num7 = Mathf.Min(camTravelVelocity * num3, magnitude) / magnitude;
			float num8 = camTravel.x * num7;
			float num9 = camTravel.y * num7;
			camTravel.x -= num8;
			camTravel.y -= num9;
		}
		else
		{
			camTravelVelocity = 0f;
		}
		Vector3 vector = Vector3.zero;
		if (!bShipEdit && coCamCenter != null)
		{
			vector = coCamCenter.tf.position;
		}
		if (Vector3.Distance(camMain.transform.position, vector) > 0.1f && camFollow)
		{
			Vector3 vector2 = camMain.transform.position + (vector - camMain.transform.position) * 0.05f;
			num5 += vector2.x - camMain.transform.position.x;
			num6 += vector2.y - camMain.transform.position.y;
		}
		num5 += vShake.x * fShakeAmp;
		num6 += vShake.y * fShakeAmp;
		if (num5 != 0f || num6 != 0f)
		{
			camMain.transform.Translate(num5, num6, 0f);
		}
		CamZoom(Mathf.Exp(vPanVelocity.z * 5f * num2));
		delY = 0f;
		delX = 0f;
		delZ = 0f;
	}

	public void CamShake(float fAmount)
	{
		if (fAmount > fShakeAmp)
		{
			fShakeAmp = Mathf.Min(fAmount, 1f);
		}
	}

	private IEnumerator turnPlayer()
	{
		while (true)
		{
			coPlayer.tf.Rotate(new Vector3(0f, 0f, 1f));
			yield return null;
		}
	}

	private bool DebugCodeHandler()
	{
		if (bEnableDebugCommands)
		{
			return true;
		}
		if (!Input.anyKeyDown)
		{
			return false;
		}
		if (!Input.GetKeyDown((KeyCode)Enum.Parse(typeof(KeyCode), sDebugCode[nDebugIndex].ToString())))
		{
			nDebugIndex = 0;
			return false;
		}
		if (++nDebugIndex == sDebugCode.Length)
		{
			UnlockDebug();
		}
		return false;
	}

	public static void ToggleDebug()
	{
		if (bEnableDebugCommands)
		{
			if (objInstance != null)
			{
				objInstance.ExitDebug();
			}
			else
			{
				bEnableDebugCommands = false;
			}
		}
		else if (objInstance != null)
		{
			objInstance.UnlockDebug();
		}
		else
		{
			bEnableDebugCommands = true;
		}
	}

	public void ExitDebug()
	{
		Debug.Log("Debug Command exited");
		coPlayer.LogMessage("**Debug Commands Have Been Disabled**", "Neutral", "Game");
		TMP_Text component = CanvasManager.goCanvasGUI.transform.Find("txtVersion").GetComponent<TMP_Text>();
		if (IntPtr.Size == 8)
		{
			component.text = DataHandler.strBuild;
		}
		else
		{
			component.text = DataHandler.strBuild + " (32)";
		}
		bEnableDebugCommands = false;
		nDebugIndex = 0;
	}

	public void UnlockDebug()
	{
		Debug.Log("Debug Command enabled");
		coPlayer.LogMessage("**Debug Commands Have Been Activated**", "Neutral", "Game");
		TMP_Text component = CanvasManager.goCanvasGUI.transform.Find("txtVersion").GetComponent<TMP_Text>();
		if (IntPtr.Size == 8)
		{
			component.text = "DB" + DataHandler.strBuild;
		}
		else
		{
			component.text = "DB" + DataHandler.strBuild + " (32)";
		}
		bEnableDebugCommands = true;
		nDebugIndex = 0;
	}

	private void FloodFill()
	{
		if (!bShipEdit || !goSelPart)
		{
			return;
		}
		Item component = goSelPart.GetComponent<Item>();
		float fLastRotation = component.fLastRotation;
		CondTrigger condTrigger = new CondTrigger();
		condTrigger.aForbids = new string[2] { "IsWall", "IsFloor" };
		foreach (Tile floodTile in TileUtils.GetFloodTiles(shipCurrentLoaded.GetTileAtWorldCoords1(vMouse.x, vMouse.y, bAllowDocked: false), 100, condTrigger))
		{
			Vector3 position = floodTile.tf.position;
			position.z = component.transform.position.z;
			if (bShipEditBG)
			{
				Item background = DataHandler.GetBackground(goSelPart.name);
				background.transform.position = position;
				background.fLastRotation = fLastRotation;
				shipCurrentLoaded.BGItemAdd(background);
			}
			else
			{
				CondOwner condOwner = DataHandler.GetCondOwner(goSelPart.GetComponent<CondOwner>().strCODef);
				condOwner.transform.position = position;
				condOwner.GetComponent<Item>().fLastRotation = fLastRotation;
				shipCurrentLoaded.AddCO(condOwner, bTiles: true);
			}
		}
	}

	private void KeyHandler()
	{
		bool num = (bRaiseUI && CanvasManager.State == CanvasManager.GUIState.SHIPGUI) || bTyping;
		if (Input.GetKey(KeyCode.LeftAlt) && Input.GetKey(KeyCode.LeftControl) && Input.GetKey(KeyCode.LeftShift) && Input.GetKey(KeyCode.Space))
		{
			Ledger.GetCRO(CanvasManager.goCanvasGUI);
		}
		if (num || CanvasManager.instance.State == CanvasManager.GUIState.GAMEOVER || bRaiseUI)
		{
			return;
		}
		if (bShipEdit && Input.GetKeyDown(KeyCode.Delete))
		{
			CondOwner[] array = new CondOwner[aSelected.Count];
			aSelected.CopyTo(array);
			CondOwner[] array2 = array;
			foreach (CondOwner condOwner in array2)
			{
				if (!(condOwner == null) && !condOwner.HasCond("IsRoom") && !condOwner.HasCond("IsTile"))
				{
					shipCurrentLoaded.RemoveCO(condOwner);
					if (DataHandler.mapCOs.ContainsKey(condOwner.strID))
					{
						DataHandler.mapCOs.Remove(condOwner.strID);
					}
					UnityEngine.Object.Destroy(condOwner.gameObject);
				}
			}
			SetBracketTarget(null, bUpdateOnly: false);
			SetPartCursor(null);
		}
		if (DebugCodeHandler())
		{
			if (Input.GetKeyDown(KeyCode.Alpha1) && Input.GetKey(KeyCode.LeftShift))
			{
				DebugGiveMoney();
			}
			if (Input.GetKeyDown(KeyCode.Alpha2) && Input.GetKey(KeyCode.LeftShift))
			{
				BountyManager.DebugTriggerMove();
			}
			if (Input.GetKeyDown(KeyCode.Alpha3) && Input.GetKey(KeyCode.LeftShift))
			{
				AIShipManager.CheckLocalAuthorityScenario();
			}
			if (Input.GetKeyDown(KeyCode.Alpha4) && Input.GetKey(KeyCode.LeftShift))
			{
				Debug.Log("Parts Value: " + shipCurrentLoaded.GetPartsValue());
			}
			if (Input.GetKeyDown(KeyCode.Alpha5) && Input.GetKey(KeyCode.LeftShift))
			{
				DebugCheckAllPlots();
			}
			if (Input.GetKeyDown(KeyCode.Alpha6) && Input.GetKey(KeyCode.LeftShift))
			{
				vfxFire.AddFireAt(GUIMegaToolTip.Selected);
			}
			if (Input.GetKeyDown(KeyCode.Alpha7) && Input.GetKey(KeyCode.LeftShift))
			{
				DebugStarSysMon();
			}
			if (Input.GetKeyDown(KeyCode.Alpha8) && Input.GetKey(KeyCode.LeftShift))
			{
				coPlayer.SetCondAmount("IsTensionCooldown", 0.0);
				BeatManager.GenerateTension();
			}
			if (Input.GetKeyDown(KeyCode.Alpha9) && Input.GetKey(KeyCode.LeftShift))
			{
				coPlayer.SetCondAmount("IsReleaseCooldown", 0.0);
				BeatManager.GenerateRelease();
			}
			if (Input.GetKey(KeyCode.LeftShift) && Input.GetKeyDown(KeyCode.J))
			{
				DebugCheckJsons();
			}
		}
	}

	public static void MuteCondRule(CondOwner co, string strCond)
	{
		if (!(co == null) && !string.IsNullOrEmpty(strCond))
		{
			CondRule condRule = co.GetCondRule(strCond);
			if (condRule != null)
			{
				condRule.bMuteOnce = true;
				objInstance.aMutedCRs.Add(condRule);
			}
		}
	}

	private void DebugGiveMoney()
	{
		coPlayer.AddCondAmount(GUIFinance.strCondCurr, 5000000.0);
		Ledger.OnLedgerRefresh.Invoke(arg0: true);
	}

	private void DebugExplodeFusion()
	{
		CondOwner condOwner = DataHandler.GetCondOwner("SysExplosionFusion");
		condOwner.tf.position = ActiveCam.ScreenToWorldPoint(new Vector3(InputManager.MousePosition.x, InputManager.MousePosition.y, condOwner.tf.position.z));
		shipCurrentLoaded.AddCO(condOwner, bTiles: false);
	}

	private void DebugCheckAllPlots()
	{
		PlotManager.bDebugCheckAll = true;
		PlotManager.CheckPlots(GetSelectedCrew(), (PlotManager.PlotTensionType)3);
	}

	private void DebugStarSysMon()
	{
		GameObject gameObject = GameObject.Find("GUIStarSystemMonitor");
		if (gameObject != null)
		{
			UnityEngine.Object.Destroy(gameObject);
		}
		else
		{
			UnityEngine.Object.Instantiate(Resources.Load<GameObject>("GUIShip/Tools/GUIStarSystemMonitor"), CanvasManager.goCanvasHelmet.transform).name = "GUIStarSystemMonitor";
		}
	}

	private void DebugCheckJsons()
	{
		Debug.Log("Verifying Json references:");
		DataHandler.ScanDictionaries();
	}

	private void DebugFloorUseAudit()
	{
		List<string> list = new List<string>
		{
			"_StorageAll", "0-12 Floor batch 1", "0-14_HullBatch", "00_Chargen", "3Pilots", "Aerostat Scaffold Dock 02", "Aerostat Scaffold Dock", "Aerostat Scaffold X", "Aerostat Scaffold", "AI Training",
			"AllTiles", "AllTilesUnused", "break zone", "CargoField", "Combat Room Alpha", "CrateRoom", "Doors", "Kiosk Room", "Light Container Testing", "Normals",
			"OKLG", "PAX2020Salvage", "PAX2020Social", "PAX2020Start", "Reactor", "ReactorComponents", "Repairshop", "Small", "Station", "StationChargen",
			"TorchPartsTest", "Waypoint", "_9x9 Air Test", "_Atmo Breathing Test", "_box", "_Chromastronauts", "_lootSpawn", "_meatTest", "_RobotTestFacility", "_test",
			"_Wall Test"
		};
		Dictionary<string, int> dictionary = new Dictionary<string, int>();
		foreach (JsonCondOwner value in DataHandler.dictCOs.Values)
		{
			if ((value.strName.IndexOf("ItmFloor") == 0 || value.strName.IndexOf("ItmWall") == 0) && value.strName.IndexOf("Patch") < 0 && value.strName.IndexOf("Loose") < 0 && value.strName.IndexOf("Dmg") < 0)
			{
				dictionary[value.strName + "\t" + value.strNameFriendly] = 0;
			}
		}
		foreach (JsonCOOverlay value2 in DataHandler.dictCOOverlays.Values)
		{
			if ((value2.strName.IndexOf("ItmFloor") == 0 || value2.strName.IndexOf("ItmWall") == 0) && value2.strName.IndexOf("Patch") < 0 && value2.strName.IndexOf("Loose") < 0 && value2.strName.IndexOf("Dmg") < 0)
			{
				dictionary[value2.strName + "\t" + value2.strNameFriendly] = 0;
			}
		}
		Dictionary<string, Dictionary<string, int>> dictionary2 = new Dictionary<string, Dictionary<string, int>>();
		foreach (JsonShip value3 in DataHandler.dictShips.Values)
		{
			if (list.Contains(value3.strName))
			{
				continue;
			}
			Dictionary<string, int> dictionary3 = new Dictionary<string, int>();
			JsonItem[] aItems = value3.aItems;
			foreach (JsonItem jsonItem in aItems)
			{
				if ((jsonItem.strName.IndexOf("ItmFloor") == 0 || jsonItem.strName.IndexOf("ItmWall") == 0) && jsonItem.strName.IndexOf("Patch") < 0 && jsonItem.strName.IndexOf("Loose") < 0 && jsonItem.strName.IndexOf("Dmg") < 0)
				{
					string text = jsonItem.strName + "\t";
					text = ((!DataHandler.dictCOs.ContainsKey(jsonItem.strName)) ? (text + DataHandler.dictCOOverlays[jsonItem.strName].strNameFriendly) : (text + DataHandler.dictCOs[jsonItem.strName].strNameFriendly));
					if (!dictionary.ContainsKey(text))
					{
						dictionary[text] = 1;
					}
					else
					{
						dictionary[text]++;
					}
					if (!dictionary3.ContainsKey(text))
					{
						dictionary3[text] = 1;
					}
					else
					{
						dictionary3[text]++;
					}
				}
			}
			dictionary2[value3.strName] = dictionary3;
		}
		StringBuilder stringBuilder = new StringBuilder();
		stringBuilder.AppendLine("Total Hull Use Count:");
		foreach (KeyValuePair<string, int> item in dictionary)
		{
			stringBuilder.Append("\t");
			stringBuilder.Append(item.Key);
			stringBuilder.Append("\t");
			stringBuilder.AppendLine(item.Value.ToString());
		}
		foreach (KeyValuePair<string, Dictionary<string, int>> item2 in dictionary2)
		{
			stringBuilder.Append(item2.Key);
			stringBuilder.AppendLine(" Hull Use Count:");
			foreach (KeyValuePair<string, int> item3 in item2.Value)
			{
				stringBuilder.Append("\t");
				stringBuilder.Append(item3.Key);
				stringBuilder.Append("\t");
				stringBuilder.AppendLine(item3.Value.ToString());
			}
		}
		DataHandler.WriteFile("HullPartAudit.txt", stringBuilder.ToString());
		Debug.Log(stringBuilder.ToString());
	}

	private void DebugDCAudit()
	{
		foreach (Ship allLoadedShip in system.GetAllLoadedShips())
		{
			foreach (CondOwner person in allLoadedShip.GetPeople(bAllowDocked: false))
			{
				person.DebugFixOldCondRules(bOnlyReport: true);
			}
		}
	}

	private void DebugReportCauseOfDeath()
	{
		foreach (Ship allLoadedShip in system.GetAllLoadedShips())
		{
			foreach (CondOwner person in allLoadedShip.GetPeople(bAllowDocked: false))
			{
				person.DebugReportCauseOfDeath();
			}
		}
	}

	public void DebugRefreshPlayerStats(CondOwner co)
	{
		if (co == null || co.bDestroyed)
		{
			return;
		}
		co.SetCondAmount("StatHydration", 0.0);
		co.SetCondAmount("StatFood", 0.0);
		co.SetCondAmount("StatSatiety", 8.0);
		co.SetCondAmount("StatDefecate", 0.0);
		co.SetCondAmount("StatSleep", 0.0);
		co.SetCondAmount("StatHygiene", 0.0);
		co.SetCondAmount("StatPain", 0.0);
		co.SetCondAmount("StatFatigue", 0.0);
		co.SetCondAmount("StatOxygen", 0.0);
		co.SetCondAmount("StatCO2Poison", 0.0);
		if (co.HasCond("IsAirtight"))
		{
			co.AddCondAmount("IsGasRequiresCleaning", 1.0);
		}
		double gasMass = GasContainer.GetGasMass("O2", 1.0);
		foreach (CondOwner cO in co.GetCOs(bAllowLocked: true, CTTrafficRefreshable))
		{
			double condAmount = cO.GetCondAmount("StatPowerMax");
			if (condAmount > 0.0)
			{
				cO.SetCondAmount("StatPower", condAmount);
			}
			condAmount = cO.GetCondAmount("IsVesselO2");
			if (condAmount > 0.0)
			{
				condAmount = cO.GetCondAmount("StatGasPressureMax");
				GasContainer gasContainer = cO.GasContainer;
				if (gasContainer != null)
				{
					condAmount = Convert.ToSingle(cO.GetCondAmount("StatVolume") * condAmount / 0.008314000442624092 / cO.GetCondAmount("StatGasTemp") * gasMass);
					double num = (float)(cO.GetCondAmount("StatGasPressure") / cO.GetCondAmount("StatGasPressureMax") * condAmount);
					double num2 = (condAmount - num) * 0.95;
					gasContainer.AddGasMols("O2", num2 / gasMass);
				}
			}
		}
	}

	private void DebugWeaponSlotAudit()
	{
		foreach (JsonInteraction value2 in DataHandler.dictInteractions.Values)
		{
			if (value2.aAModesAddedThem == null || value2.aAModesAddedThem.Length == 0 || value2.strName.IndexOf("SLOT") != 0)
			{
				continue;
			}
			string text = "UN" + value2.strName;
			JsonInteraction value = null;
			if (!DataHandler.dictInteractions.TryGetValue(text, out value))
			{
				Debug.Log("No UNSLOT for " + text);
				continue;
			}
			for (int i = 0; i < value2.aAModesAddedThem.Length; i++)
			{
				if (value.aAModesAddedThem.Length <= i)
				{
					Debug.Log(text + " missing index " + i + "; Should be -" + value2.aAModesAddedThem[i]);
					continue;
				}
				string text2 = value.aAModesAddedThem[i];
				if (string.IsNullOrEmpty(text2) || text2 != "-" + value2.aAModesAddedThem[i])
				{
					Debug.Log(text + " mismatch index " + i + "; Should be -" + value2.aAModesAddedThem[i]);
				}
			}
		}
	}

	private void DebugListCOContainers()
	{
		dictCOConts = new Dictionary<string, CondOwner>();
		foreach (JsonCondOwner value in DataHandler.dictCOs.Values)
		{
			CondOwner condOwner = DataHandler.GetCondOwner(value.strName);
			if (!(condOwner == null))
			{
				dictCOConts[condOwner.strName] = condOwner;
			}
		}
		foreach (JsonCOOverlay value2 in DataHandler.dictCOOverlays.Values)
		{
			CondOwner condOwner2 = DataHandler.GetCondOwner(value2.strName);
			if (!(condOwner2 == null))
			{
				dictCOConts[condOwner2.strName] = condOwner2;
			}
		}
		StringBuilder stringBuilder = new StringBuilder();
		foreach (CondOwner value3 in dictCOConts.Values)
		{
			stringBuilder.Append(value3.strName);
			stringBuilder.Append("\t");
			stringBuilder.Append(value3.FriendlyName);
			stringBuilder.Append("\t");
			if (value3.objContainer != null)
			{
				if (value3.objContainer.ctAllowed != null)
				{
					stringBuilder.Append(value3.objContainer.ctAllowed.strName);
				}
				else
				{
					stringBuilder.Append("null");
				}
			}
			else
			{
				stringBuilder.Append("n/a");
			}
			stringBuilder.Append("\t");
			stringBuilder.AppendLine("ENDCONT");
			if (value3.objContainer != null)
			{
				CondTrigger ctAllowed = null;
				if (value3.objContainer.ctAllowed != null)
				{
					ctAllowed = value3.objContainer.ctAllowed.Clone();
				}
				DebugListCOsThatFitInside(stringBuilder, ctAllowed);
			}
		}
		Debug.Log("Exported container report to COContainers.txt");
		DataHandler.WriteFile("COContainers.txt", stringBuilder.ToString());
	}

	private void DebugListCOsThatFitInside(StringBuilder sb, CondTrigger ctAllowed)
	{
		if (sb == null)
		{
			return;
		}
		foreach (CondOwner value in dictCOConts.Values)
		{
			if (ctAllowed == null || ctAllowed.Triggered(value))
			{
				sb.Append("\t");
				sb.Append(value.strName);
				if (value.objContainer != null)
				{
					sb.Append("*");
				}
				sb.Append("\t");
				sb.Append(value.FriendlyName);
				sb.Append("\t");
				sb.AppendLine("END");
			}
		}
	}

	public static void ScheduleAutoPause(double fDuration, string strReason = null)
	{
		if (tplAutoPause.Item1 == 0.0 || tplAutoPause.Item1 > StarSystem.fEpoch + fDuration)
		{
			tplAutoPause.Item1 = StarSystem.fEpoch + fDuration;
			tplAutoPause.Item2 = strReason;
		}
	}

	public static void TriggerAutoPause(string strReason = null)
	{
		if (objInstance.bcombatAutoPauseAllowed && !(GUISocialCombat2.coUs == GetSelectedCrew()))
		{
			if (strReason != null && GetSelectedCrew() != null)
			{
				GetSelectedCrew().LogMessage(DataHandler.GetString("AUTOPAUSE_PREFIX") + strReason, "Neutral", GetSelectedCrew().strName);
			}
			Paused = true;
			MonoSingleton<GUIQuickBar>.Instance.Refresh();
			AudioManager.am.PlayAudioEmitter("UIGameplayPause", bLoop: false);
		}
	}

	public static void ResetAutoPause()
	{
		tplAutoPause.Item1 = 0.0;
		tplAutoPause.Item2 = null;
	}

	private void GenerateAITrainingJson()
	{
		CondTrigger objCondTrig = new CondTrigger("Humans", new string[1] { "IsHuman" }, null, null, null);
		List<CondOwner> cOs = shipCurrentLoaded.GetCOs(objCondTrig, bSubObjects: false, bAllowDocked: true, bAllowLocked: false);
		Dictionary<string, CondHistory> dictionary = new Dictionary<string, CondHistory>();
		foreach (CondOwner item in cOs)
		{
			foreach (KeyValuePair<string, CondHistory> item2 in item.mapIAHist)
			{
				string key = item2.Key;
				CondHistory value = item2.Value;
				if (!dictionary.ContainsKey(key))
				{
					dictionary[key] = new CondHistory(value.strCondName);
				}
				CondHistory condHistory = dictionary[key];
				foreach (InteractionHistory value2 in value.mapInteractions.Values)
				{
					for (int num = value2.nIterations; num > 0; num--)
					{
						condHistory.AddInteractionScore(value2.strName, value2.fAverage, bNew: true);
					}
				}
			}
		}
		DataHandler.DataToJsonStreaming(new Dictionary<string, JsonAIPersonality> { ["Abner"] = new JsonAIPersonality
		{
			strName = "Abner",
			mapIAHist2 = dictionary
		} }, "ai_training.json", bPersistent: false);
	}

	public void SetResolution(int width, int height)
	{
	}

	public float AspectRatioMod()
	{
		return camMain.aspect / 1.7777778f;
	}

	public static void AddLoadedShip(Ship ship)
	{
		if (ship != null && !aLoadedShips.Contains(ship))
		{
			aLoadedShips.Add(ship);
		}
	}

	public static void RemoveLoadedShip(Ship ship)
	{
		if (ship != null)
		{
			aLoadedShips.Remove(ship);
		}
	}

	public static Ship GetLoadedShipByRegId(string regId)
	{
		if (string.IsNullOrEmpty(regId) || aLoadedShips == null)
		{
			return null;
		}
		return aLoadedShips.FirstOrDefault((Ship ship) => ship.strRegID == regId);
	}

	public static List<Ship> GetAllLoadedShips()
	{
		return aLoadedShips;
	}

	private void DebugAudioAudit()
	{
		Dictionary<string, List<string>> dictionary = new Dictionary<string, List<string>>();
		FileInfo[] files = new DirectoryInfo("Assets/Resources/Audio").GetFiles();
		foreach (FileInfo fileInfo in files)
		{
			if (!(fileInfo.Extension != ".ogg") || !(fileInfo.Extension != ".wav"))
			{
				dictionary[fileInfo.Name.Substring(0, fileInfo.Name.Length - 4)] = new List<string>();
			}
		}
		foreach (KeyValuePair<string, JsonAudioEmitter> dictAudioEmitter in DataHandler.dictAudioEmitters)
		{
			if (dictAudioEmitter.Value.strClipSteady != null && dictionary.ContainsKey(dictAudioEmitter.Value.strClipSteady))
			{
				dictionary[dictAudioEmitter.Value.strClipSteady].Add(dictAudioEmitter.Key + ".strClipSteady");
			}
			if (dictAudioEmitter.Value.strClipTrans != null && dictionary.ContainsKey(dictAudioEmitter.Value.strClipTrans))
			{
				dictionary[dictAudioEmitter.Value.strClipTrans].Add(dictAudioEmitter.Key + ".strClipTrans");
			}
		}
		string text = "";
		foreach (KeyValuePair<string, List<string>> item in dictionary)
		{
			text = text + item.Key + "\t";
			foreach (string item2 in item.Value)
			{
				text = text + item2 + ", ";
			}
			text += "\n";
		}
		Debug.Log(text);
	}

	private void DebugSocialAudit()
	{
		Dictionary<string, int> dictionary = new Dictionary<string, int>();
		Dictionary<string, int> dictionary2 = new Dictionary<string, int>();
		for (int i = 0; i < 100; i++)
		{
			CondOwner condOwner = new PersonSpec
			{
				strLootConds = "CONDNPCRandom"
			}.MakeCondOwner(PersonSpec.StartShip.OLD, shipCurrentLoaded);
			foreach (JsonInteraction value in DataHandler.dictInteractions.Values)
			{
				if (!value.bSocial)
				{
					continue;
				}
				Interaction interaction = DataHandler.GetInteraction(value.strName);
				if (!dictionary2.ContainsKey(interaction.strName))
				{
					dictionary2[interaction.strName] = 0;
				}
				if (interaction.CTTestUs.Triggered(condOwner))
				{
					dictionary2[interaction.strName]++;
					continue;
				}
				string text = interaction.CTTestUs.strFailReasonLast;
				int num = text.IndexOf("/");
				if (num >= 0)
				{
					text = "Chance: " + text.Substring(num);
				}
				if (!dictionary.ContainsKey(text))
				{
					dictionary[text] = 0;
				}
				dictionary[text]++;
			}
			condOwner.Destroy();
		}
		string text2 = "";
		foreach (KeyValuePair<string, int> item in dictionary2)
		{
			text2 = text2 + item.Key + "\t" + item.Value + "\n";
		}
		DataHandler.WriteFile("DebugSocialAudit.csv", text2);
		Debug.Log(text2);
	}

	private void DebugSocialAudit2()
	{
		StringBuilder stringBuilder = new StringBuilder();
		foreach (JsonInteraction value in DataHandler.dictInteractions.Values)
		{
			if (!value.bSocial)
			{
				continue;
			}
			Interaction interaction = DataHandler.GetInteraction(value.strName);
			if (interaction == null)
			{
				continue;
			}
			stringBuilder.Append(interaction.strName + "\t");
			stringBuilder.Append(DebugGetStatLootCSV(interaction.LootCTsUs));
			stringBuilder.Append(DebugGetStatLootCSV(interaction.LootCTsThem));
			if (interaction.CTTestUs != null)
			{
				foreach (string allReqName in interaction.CTTestUs.GetAllReqNames())
				{
					stringBuilder.Append(allReqName + ", ");
				}
				stringBuilder.Append("\t");
				foreach (string allReqName2 in interaction.CTTestUs.GetAllReqNames(bForbids: true))
				{
					stringBuilder.Append(allReqName2 + ", ");
				}
				stringBuilder.Append("\t");
				stringBuilder.Append(interaction.CTTestUs.bAND.ToString());
			}
			else
			{
				stringBuilder.Append("\t");
				stringBuilder.Append("\t");
				stringBuilder.Append("false");
			}
			stringBuilder.AppendLine();
		}
		DataHandler.WriteFile("DebugSocialAudit2.csv", stringBuilder.ToString());
	}

	private string DebugGetStatLootCSV(Loot LootCTsUs)
	{
		StringBuilder stringBuilder = new StringBuilder();
		Dictionary<string, double> dictionary = new Dictionary<string, double>();
		dictionary["StatAchievement"] = 0.0;
		dictionary["StatAltruism"] = 0.0;
		dictionary["StatAutonomy"] = 0.0;
		dictionary["StatContact"] = 0.0;
		dictionary["StatEsteem"] = 0.0;
		dictionary["StatFamily"] = 0.0;
		dictionary["StatIntimacy"] = 0.0;
		dictionary["StatMeaning"] = 0.0;
		dictionary["StatPrivacy"] = 0.0;
		dictionary["StatSecurity"] = 0.0;
		dictionary["StatSelfRespect"] = 0.0;
		if (LootCTsUs != null)
		{
			foreach (CondTrigger item in LootCTsUs.GetCTLoot(null))
			{
				if (!dictionary.ContainsKey(item.strCondName))
				{
					dictionary[item.strCondName] = 0.0;
				}
				dictionary[item.strCondName] += item.fCount;
			}
		}
		stringBuilder.Append(dictionary["StatAchievement"] + "\t");
		stringBuilder.Append(dictionary["StatAltruism"] + "\t");
		stringBuilder.Append(dictionary["StatAutonomy"] + "\t");
		stringBuilder.Append(dictionary["StatContact"] + "\t");
		stringBuilder.Append(dictionary["StatEsteem"] + "\t");
		stringBuilder.Append(dictionary["StatFamily"] + "\t");
		stringBuilder.Append(dictionary["StatIntimacy"] + "\t");
		stringBuilder.Append(dictionary["StatMeaning"] + "\t");
		stringBuilder.Append(dictionary["StatPrivacy"] + "\t");
		stringBuilder.Append(dictionary["StatSecurity"] + "\t");
		stringBuilder.Append(dictionary["StatSelfRespect"] + "\t");
		return stringBuilder.ToString();
	}

	private void OnApplicationQuit()
	{
	}

	public void CycleCrew(CondOwner becomes = null)
	{
		CondOwner selectedCrew = GetSelectedCrew();
		if (selectedCrew.Company == null || selectedCrew.Company != coPlayer.Company || GetSelectedCrew().ship.LoadState < Ship.Loaded.Edit)
		{
			OnRightClick.Invoke(null);
			objInstance.StartCoroutine(CycleCrewPart2(selectedCrew, coPlayer));
			return;
		}
		if (GUIInventory.instance.IsOpen && GUIInventory.instance.Selected != null)
		{
			GetSelectedCrew().LogMessage(DataHandler.GetString("GUI_INV_NO_CYCLE"), "Bad", GetSelectedCrew().strID);
			AudioManager.am.PlayAudioEmitter("UIMessageLogBad", bLoop: false, bNoRestart: true);
			return;
		}
		if (guiPDA != null && guiPDA.pdaVisualisers != null)
		{
			selectedCrew.ApplyGPMChanges(new string[1] { "PDAVizSettings,strSettings," + guiPDA.pdaVisualisers.CreateCustomInfo() });
		}
		Dictionary<string, JsonCompanyRules> mapRoster = selectedCrew.Company.mapRoster;
		if (becomes == null)
		{
			List<CondOwner> list = new List<CondOwner>(mapRoster.Count);
			List<string> list2 = mapRoster.Keys.ToList();
			int num = list2.IndexOf(selectedCrew.strID);
			for (int i = 0; i < list2.Count; i++)
			{
				int index = (num + i) % list2.Count;
				string strName = list2[index];
				CondOwner condOwner = DataHandler.GetCondOwner(null, strName, null, bLoot: true);
				if (!(condOwner == null) && condOwner.ship != null && condOwner.bAlive)
				{
					list.Add(condOwner);
				}
			}
			List<CondOwner> list3 = BuildCandidatesList(selectedCrew, list);
			becomes = ((list3.Count <= 0) ? selectedCrew : list3[0]);
		}
		if (becomes == null)
		{
			becomes = coPlayer;
		}
		objInstance.StartCoroutine(CycleCrewPart2(selectedCrew, becomes));
	}

	private List<CondOwner> BuildCandidatesList(CondOwner currently, List<CondOwner> crewMembers)
	{
		List<CondOwner> list = new List<CondOwner>(crewMembers.Count);
		for (int i = 0; i < crewMembers.Count; i++)
		{
			CondOwner condOwner = crewMembers[i];
			bool flag = condOwner.ship == currently.ship || (currently.ship.LoadState == Ship.Loaded.Full && condOwner.ship.LoadState == Ship.Loaded.Full);
			if (condOwner != currently && flag && !condOwner.HasCond("Unconscious"))
			{
				list.Add(condOwner);
			}
		}
		if (list.Count > 0)
		{
			return list;
		}
		for (int j = 0; j < crewMembers.Count; j++)
		{
			CondOwner condOwner2 = crewMembers[j];
			if (condOwner2 != currently && !condOwner2.HasCond("Unconscious"))
			{
				list.Add(condOwner2);
			}
		}
		return list;
	}

	private IEnumerator CycleCrewPart2(CondOwner currently, CondOwner becomes)
	{
		if (currently != becomes)
		{
			ResetAutoPause();
			MonoSingleton<GUILoadingPopUp>.Instance.ShowTooltip(DataHandler.GetString("LOAD_SHIPLOAD"), becomes.ship.publicName);
		}
		if (becomes.ship.LoadState != Ship.Loaded.Full)
		{
			MonoSingleton<GUILoadingPopUp>.Instance.ShowTooltip("LOADING SHIP", becomes.ship.publicName);
			yield return null;
			MonoSingleton<AsyncShipLoader>.Instance.Unload();
			Ship ship = system.SpawnShip(becomes.ship.strRegID, Ship.Loaded.Full);
			if (ship != null)
			{
				CondOwnerVisitorCatchUp visitor = new CondOwnerVisitorCatchUp();
				ship.VisitCOs(visitor, bSubObjects: true, bAllowDocked: true, bAllowLocked: true);
				LowerUI();
				UnloadOldShips(ship);
				MonoSingleton<AsyncShipLoader>.Instance.LoadDockedBarterZoneShips(coPlayer, becomes.ship);
				ship.ToggleVis(bShow: true);
			}
		}
		else
		{
			if (currently != becomes)
			{
				MonoSingleton<GUILoadingPopUp>.Instance.ShowTooltip("SWITCHING CREW", becomes.ship.publicName);
			}
			CondTrigger condTrigger = DataHandler.GetCondTrigger("TIsNavStationNotOff");
			Interaction interactionCurrent = becomes.GetInteractionCurrent();
			if (interactionCurrent != null && condTrigger.Triggered(interactionCurrent.objThem, null, logOutcome: false))
			{
				if (GUIOrbitDraw.IsOpen())
				{
					GUIOrbitDraw.Instance.CrewSwitch(interactionCurrent.objThem);
				}
				else if (!string.IsNullOrEmpty(interactionCurrent.strRaiseUIThem))
				{
					RaiseUI(interactionCurrent.strRaiseUIThem, interactionCurrent.objThem);
				}
			}
			else if (GUIOrbitDraw.IsOpen())
			{
				LowerUI();
			}
		}
		if (currently != becomes)
		{
			objInstance.SetBracketTarget(becomes.strID, bUpdateOnly: false);
			objInstance.CamCenter(becomes);
			CanvasManager.helmet.TunnelOpacity(CanvasManager.helmet.GetTunnelAmount(becomes), bInstant: true);
			MonoSingleton<GUILoadingPopUp>.Instance.FadeOutToolTip();
			MonoSingleton<GUICrewStatus>.Instance.Refresh();
			OnRightClick.Invoke(null);
			CollisionManager.RefreshCurrentRegion();
			if (guiPDA != null && guiPDA.pdaVisualisers != null)
			{
				guiPDA.pdaVisualisers.ResolveCustomInfo(becomes.GetGPMInfo("PDAVizSettings", "strSettings"));
				guiPDA.pdaVisualisers.AssembleUI();
			}
		}
	}

	private void UnloadOldShips(Ship objShipNew)
	{
		IReadOnlyList<Ship> allDockedShips = objShipNew.GetAllDockedShips();
		foreach (Ship item in system.GetAllLoadedShips().ToList())
		{
			if (item != objShipNew && !allDockedShips.Contains(item) && (item.gameObject.activeInHierarchy || item.LoadState > Ship.Loaded.Shallow))
			{
				SaveToShallow(item);
			}
		}
	}

	public IEnumerator SpawnTrail(TrailRenderer trail, Vector3 vEnd)
	{
		if (!(trail == null))
		{
			float fTime = 0f;
			Vector3 vStart = trail.transform.position;
			while (fTime < 1f)
			{
				trail.transform.position = Vector3.Lerp(vStart, vEnd, fTime);
				fTime += TimeElapsedScaled() / trail.time;
				yield return null;
			}
			trail.transform.position = vEnd;
			UnityEngine.Object.Destroy(trail.gameObject, trail.time);
		}
	}

	internal static string[] CustomInfosString()
	{
		string text = "MeatState=" + eMeatState;
		string text2 = "PDAOverlay=" + guiPDA.pdaVisualisers.CreateCustomInfo();
		string text3 = "PDANotes=" + guiPDA.pdaNotes.CreateCustomInfo();
		string text4 = "PDATimer=" + guiPDA.pdaTimer.CreateCustomInfo();
		string text5 = "PDAPresets=" + guiPDA.pdaVisualisers.PresetsToCustomInfos();
		string text6 = "PDASocialFilters=" + guiPDA.GetFilterSave();
		string text7 = "QAB=" + MonoSingleton<GUIQuickBar>.Instance.CreateCustomInfo();
		return new string[7] { text, text5, text2, text3, text4, text6, text7 };
	}

	internal static void SetCustomInfos(string[] inputs)
	{
		if (inputs == null)
		{
			return;
		}
		for (int i = 0; i < inputs.Length; i++)
		{
			string[] array = inputs[i].Split(new char[1] { '=' });
			if (array.Length <= 1)
			{
				continue;
			}
			switch (array[0])
			{
			case "MeatState":
				ResolveMeatState(array[1]);
				break;
			case "PDAPresets":
				guiPDA.pdaVisualisers.PresetsFromCustomInfos(array[1]);
				break;
			case "PDAOverlay":
				guiPDA.pdaVisualisers.ResolveCustomInfo(array[1]);
				break;
			case "PDANotes":
				guiPDA.pdaNotes.ResolveCustomInfo(array[1]);
				break;
			case "PDANotesAdd":
				guiPDA.pdaNotes.CustomInfoAddition(array[1]);
				break;
			case "PDATimer":
				guiPDA.pdaTimer.ResolveCustomInfo(array[1]);
				break;
			case "PDASocialFilters":
				guiPDA.BuildFilters(array[1]);
				break;
			case "Ceres":
				switch (array[1])
				{
				case "EndP1":
				{
					DataHandler.mapCOs.TryGetValue("Smiley 76", out var value);
					if ((bool)value)
					{
						value.Destroy();
					}
					break;
				}
				case "EndP4Xin":
					Endgame.RunEndgame("xinhua");
					break;
				case "EndP4Titan":
					Endgame.RunEndgame("titan");
					break;
				}
				break;
			case "79AU":
				switch (array[1])
				{
				case "dreamone":
					Endgame.RunEndgame("dreamone");
					break;
				case "dead":
					Endgame.RunEndgame("dead");
					break;
				case "portal":
					Endgame.RunEndgame("portal");
					break;
				}
				break;
			case "RunEncounter":
				BeatManager.RunEncounter(array[1], bInterrupt: true);
				break;
			case "QAB":
				MonoSingleton<GUIQuickBar>.Instance.ResolveCustomInfo(array[1]);
				break;
			default:
				Debug.LogWarning("Custom Infos not recognised! Skipping.");
				break;
			}
		}
	}

	internal static void ResolveMeatState(string meatState)
	{
		switch (meatState)
		{
		case "Inert":
		case "inert":
		case "0":
			eMeatState = MeatState.Inert;
			break;
		case "Dormant":
		case "dormant":
		case "1":
			eMeatState = MeatState.Dormant;
			break;
		case "Spread":
		case "spread":
		case "2":
			eMeatState = MeatState.Spread;
			break;
		case "Decay":
		case "decay":
		case "3":
			eMeatState = MeatState.Decay;
			break;
		case "Eradicate":
		case "eradicate":
		case "4":
			eMeatState = MeatState.Eradicate;
			break;
		case "Hell":
		case "hell":
		case "5":
			eMeatState = MeatState.Hell;
			break;
		default:
			Debug.LogWarning("MeatState not recognised when loading! Leaving Dormant");
			eMeatState = MeatState.Dormant;
			break;
		}
	}

	public static void UnlockAchievement(string strAchievement)
	{
		objInstance.achievementManager.UnlockAchievement(strAchievement);
	}

	public static void LockAchievement(string strAchievement)
	{
		objInstance.achievementManager.LockAchievement(strAchievement);
	}

	public static void LockAllAchievements()
	{
		objInstance.achievementManager.LockAllAchievements();
	}

	public static string GetAchievement(string strAchievement)
	{
		return objInstance.achievementManager.GetAchievement(strAchievement);
	}
}
