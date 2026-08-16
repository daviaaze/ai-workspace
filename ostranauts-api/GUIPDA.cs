using System;
using System.Collections.Generic;
using System.Linq;
using Ostranauts.Components;
using Ostranauts.Core;
using Ostranauts.InputControl;
using Ostranauts.Objectives;
using Ostranauts.ShipGUIs;
using Ostranauts.ShipGUIs.Jobs;
using Ostranauts.ShipGUIs.PDA;
using Ostranauts.UI.PDA;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public class GUIPDA : MonoBehaviour
{
	public enum UIState
	{
		Loading,
		Closed,
		Home,
		Objectives,
		JobOrder,
		JobBuild,
		JobBuildScroll,
		Tasks,
		Socials,
		GigNexus,
		Ferry,
		NavLink,
		Viz,
		Notes,
		Timer,
		Standings,
		Bounties
	}

	private enum SortMethod
	{
		AlphabeticalAscending,
		AlphabeticalDescending,
		RelationAscending,
		RelationDescending
	}

	public static GUIPDA instance;

	public static TMP_Text txtPDAUTC;

	public static CondTrigger ctJobFilter;

	private static CondTrigger _ctSocials;

	[SerializeField]
	private GUIPDAFerry uiFerry;

	[SerializeField]
	private GUIBounties _guiBounties;

	public GameObject goJobTypes;

	public GameObject goJobOptions;

	private Toggle chkFilterWalls;

	private Toggle chkFilterFloors;

	private Toggle chkFilterConduits;

	private Toggle chkFilterEquip;

	private Toggle chkFilterCans;

	private Toggle chkFilterLoose;

	private CanvasGroup cgObjectives;

	private CanvasGroup cgTasks;

	private CanvasGroup cgGigNexus;

	private CanvasGroup cgFerry;

	private CanvasGroup cgBounties;

	private CanvasGroup cgJobs;

	private CanvasGroup cgJobOptionsScroll;

	private CanvasGroup cgJobFilters;

	private CanvasGroup cgHome;

	private CanvasGroup cgViz;

	private CanvasGroup cgStandings;

	public PDAVisualisers pdaVisualisers;

	private CanvasGroup cgNotes;

	public PDANotes pdaNotes;

	private CanvasGroup cgTimer;

	public PDATimer pdaTimer;

	private CanvasGroup cgHotbar;

	private ObjectivesApp objectivesApp;

	[SerializeField]
	private ScrollRect srSocials;

	[SerializeField]
	private Transform tfSocialsList;

	[SerializeField]
	private GUIJobItem prefabGUIJobItem;

	[SerializeField]
	public GUIPDAHomepage homepage;

	private CondTrigger _ctPDA;

	private int nNewObjectives;

	private int nIdleCrew;

	private UIState nState;

	private double fLastTaskUpdate;

	[Header("PDA Frame Components")]
	[SerializeField]
	private GameObject bmpFrame;

	[SerializeField]
	private GameObject objBackground;

	[SerializeField]
	private GameObject objForeground;

	[SerializeField]
	private GameObject objHotbar;

	[SerializeField]
	private GameObject objNavigation;

	[SerializeField]
	private GameObject bmpScreen;

	[Header("Socials")]
	[SerializeField]
	private CanvasGroup cgSocials;

	[SerializeField]
	private Transform tfpnlListContent;

	[SerializeField]
	private Button btnSort;

	[SerializeField]
	private MultiSelectDropDown ddFilter;

	[SerializeField]
	private Sprite[] _filterSprites;

	[Header("Objectives")]
	[SerializeField]
	public ObjectivesHost current;

	[SerializeField]
	public ObjectivesHost finished;

	[Header("Localisation Fields")]
	[SerializeField]
	private TextMeshProUGUI topBarTitle;

	[SerializeField]
	private TextMeshProUGUI topBarSubtitle;

	[SerializeField]
	private TextMeshProUGUI tasksTitle;

	[SerializeField]
	private TextMeshProUGUI tasksTask;

	[SerializeField]
	private TextMeshProUGUI tasksTarget;

	[SerializeField]
	private TextMeshProUGUI tasksDuty;

	[SerializeField]
	private TextMeshProUGUI tasksShip;

	[SerializeField]
	private TextMeshProUGUI vizTitle;

	[SerializeField]
	private TextMeshProUGUI presetsTitle;

	[SerializeField]
	private TextMeshProUGUI presetsDefault;

	[SerializeField]
	private TextMeshProUGUI presetsPower;

	[SerializeField]
	private TextMeshProUGUI presetsDamage;

	[SerializeField]
	private TextMeshProUGUI presetsMass;

	[SerializeField]
	private TextMeshProUGUI presetsCost;

	[SerializeField]
	private TextMeshProUGUI presetsHeat;

	[SerializeField]
	private TextMeshProUGUI presetsPressure;

	[SerializeField]
	private TextMeshProUGUI togglesPowerTitle;

	[SerializeField]
	private TextMeshProUGUI togglesPlaceholderTitle;

	[SerializeField]
	private TextMeshProUGUI togglesTasksTitle;

	[SerializeField]
	private TextMeshProUGUI togglesCeilingTitle;

	[SerializeField]
	private TextMeshProUGUI togglesUpdatesTitle;

	[SerializeField]
	private TextMeshProUGUI togglesExteriorsTitle;

	[SerializeField]
	private TextMeshProUGUI togglesContoursTitle;

	[SerializeField]
	private TextMeshProUGUI togglesLogScaleTitle;

	[SerializeField]
	private TextMeshProUGUI togglesLightsTitle;

	[SerializeField]
	private TextMeshProUGUI togglesFOVTitle;

	[SerializeField]
	private TextMeshProUGUI paramatersValue;

	[SerializeField]
	private TextMeshProUGUI paramatersMin;

	[SerializeField]
	private TextMeshProUGUI paramatersMax;

	[SerializeField]
	private TextMeshProUGUI paramatersGradientLabel;

	[SerializeField]
	private TextMeshProUGUI paramatersOpacityLabel;

	[SerializeField]
	private TextMeshProUGUI notesTitle;

	[SerializeField]
	private TextMeshProUGUI timerTitle;

	[SerializeField]
	private TextMeshProUGUI timerReset;

	[SerializeField]
	private TextMeshProUGUI timerPlay;

	[SerializeField]
	private TextMeshProUGUI socialsTitle;

	[SerializeField]
	private TextMeshProUGUI standingsTitle;

	[SerializeField]
	private TextMeshProUGUI gigNexusTitle;

	[SerializeField]
	private TextMeshProUGUI objectivesTitle;

	[SerializeField]
	private TextMeshProUGUI objectivesChkCurrent;

	[SerializeField]
	private TextMeshProUGUI objectivesChkFinished;

	[SerializeField]
	private TextMeshProUGUI objectivesChkSettings;

	[SerializeField]
	private TextMeshProUGUI objectivesChkShowTutorials;

	[SerializeField]
	private TextMeshProUGUI objectivesChkMuteTutorials;

	[SerializeField]
	private TextMeshProUGUI jobsTitle;

	[SerializeField]
	private TextMeshProUGUI jobsFilter;

	[SerializeField]
	private TextMeshProUGUI jobsFilterWall;

	[SerializeField]
	private TextMeshProUGUI jobsFilterFloor;

	[SerializeField]
	private TextMeshProUGUI jobsFilterLoose;

	[SerializeField]
	private TextMeshProUGUI jobsFilterConduits;

	[SerializeField]
	private TextMeshProUGUI jobsFilterCans;

	[SerializeField]
	private TextMeshProUGUI jobsFilterEquip;

	[SerializeField]
	private TextMeshProUGUI ferryTitle;

	[SerializeField]
	private TextMeshProUGUI ferrySubtitle;

	[SerializeField]
	private TextMeshProUGUI ferryATC;

	[SerializeField]
	private TextMeshProUGUI ferryRequestPickup;

	[SerializeField]
	private TextMeshProUGUI ferryArrivalDest;

	[SerializeField]
	private TextMeshProUGUI ferryArrivalPickup;

	[SerializeField]
	private TextMeshProUGUI ferryCancel;

	[SerializeField]
	private TextMeshProUGUI ferryNote;

	[SerializeField]
	private TextMeshProUGUI PDAHomeTitle;

	[Header("Factions")]
	[SerializeField]
	private PDAStandingsBar prefabPDAStandingsBar;

	[SerializeField]
	private TextMeshProUGUI lblFactionName;

	[SerializeField]
	private TextMeshProUGUI lblFactionRep;

	[SerializeField]
	private TextMeshProUGUI lblFactionScore;

	[SerializeField]
	private TextMeshProUGUI lblFactionFunds;

	[SerializeField]
	private TextMeshProUGUI lblFactionAssists;

	[SerializeField]
	private TextMeshProUGUI lblFactionSorties;

	[SerializeField]
	private RawImage imgFactionLogo;

	[SerializeField]
	private GameObject objFunds;

	[SerializeField]
	private GameObject objAssists;

	[SerializeField]
	private GameObject objSorties;

	[SerializeField]
	private string strSelectedFaction = "";

	private SortMethod _currentSortMethod;

	private List<MultiSelectDTO> _socialFilters = new List<MultiSelectDTO>();

	public UIState State
	{
		get
		{
			return nState;
		}
		set
		{
			if (value == nState)
			{
				return;
			}
			CanvasManager.HideCanvasGroup(cgJobs);
			CanvasManager.HideCanvasGroup(cgJobOptionsScroll);
			CanvasManager.HideCanvasGroup(cgObjectives);
			CanvasManager.HideCanvasGroup(cgTasks);
			CanvasManager.HideCanvasGroup(cgSocials);
			ddFilter.Reset();
			CanvasManager.HideCanvasGroup(cgGigNexus);
			CanvasManager.HideCanvasGroup(cgFerry);
			CanvasManager.HideCanvasGroup(cgHome);
			CanvasManager.HideCanvasGroup(cgViz);
			CanvasManager.HideCanvasGroup(cgNotes);
			CanvasManager.HideCanvasGroup(cgTimer);
			CanvasManager.HideCanvasGroup(cgStandings);
			CanvasManager.HideCanvasGroup(cgBounties);
			nState = value;
			_guiBounties.Clear();
			if (nState == UIState.Closed)
			{
				SlidePDA(1);
				return;
			}
			if (CrewSim.inventoryGUI.IsOpen)
			{
				CommandInventory.ToggleInventory(CrewSim.GetSelectedCrew());
			}
			SlidePDA(0);
			switch (nState)
			{
			case UIState.JobOrder:
				CanvasManager.ShowCanvasGroup(cgJobs);
				break;
			case UIState.JobBuild:
				CanvasManager.ShowCanvasGroup(cgJobs);
				break;
			case UIState.JobBuildScroll:
				CanvasManager.ShowCanvasGroup(cgJobs);
				CanvasManager.ShowCanvasGroup(cgJobOptionsScroll);
				break;
			case UIState.Objectives:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgObjectives);
				break;
			case UIState.Tasks:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgTasks);
				ShowTasks();
				break;
			case UIState.Socials:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgSocials);
				ShowSocials();
				break;
			case UIState.GigNexus:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgGigNexus);
				ShowGigNexus();
				ToggleGig(bShow: false);
				break;
			case UIState.Ferry:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgFerry);
				uiFerry.Init();
				break;
			case UIState.Home:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgHome);
				homepage.Activate();
				break;
			case UIState.NavLink:
				ToggleNAVLink();
				State = UIState.Closed;
				break;
			case UIState.Viz:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgViz);
				break;
			case UIState.Notes:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgNotes);
				break;
			case UIState.Timer:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgTimer);
				break;
			case UIState.Standings:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgStandings);
				ShowStandings();
				break;
			case UIState.Bounties:
				HideJobPaintUI();
				CanvasManager.ShowCanvasGroup(cgBounties);
				_guiBounties.Init();
				break;
			}
		}
	}

	public int NewObjectives
	{
		get
		{
			return nNewObjectives;
		}
		set
		{
			nNewObjectives = value;
			UpdateAppNotifs();
		}
	}

	public int IdleCrew
	{
		get
		{
			return nIdleCrew;
		}
		set
		{
			nIdleCrew = value;
			UpdateAppNotifs();
		}
	}

	public bool JobsActive
	{
		get
		{
			if (State != UIState.JobBuild)
			{
				return State == UIState.JobOrder;
			}
			return true;
		}
	}

	public static CondTrigger CTSocials
	{
		get
		{
			if (_ctSocials == null)
			{
				_ctSocials = DataHandler.GetCondTrigger("TRELFamiliar");
			}
			return _ctSocials;
		}
	}

	private CondTrigger CTPDA
	{
		get
		{
			if (_ctPDA == null)
			{
				_ctPDA = DataHandler.GetCondTrigger("TIsComputerPDA");
			}
			return _ctPDA;
		}
	}

	public static UIState GetStateFromString(string strState)
	{
		UIState uIState = UIState.Closed;
		if (strState == null)
		{
			return uIState;
		}
		return strState switch
		{
			"Loading" => UIState.Loading, 
			"Closed" => UIState.Closed, 
			"Home" => UIState.Home, 
			"Objectives" => UIState.Objectives, 
			"JobOrder" => UIState.JobOrder, 
			"JobBuild" => UIState.JobBuild, 
			"JobBuildScroll" => UIState.JobBuildScroll, 
			"Tasks" => UIState.Tasks, 
			"Socials" => UIState.Socials, 
			"GigNexus" => UIState.GigNexus, 
			"Ferry" => UIState.Ferry, 
			"NavLink" => UIState.NavLink, 
			"Viz" => UIState.Viz, 
			"Notes" => UIState.Notes, 
			"Timer" => UIState.Timer, 
			"Standings" => UIState.Standings, 
			"Bounties" => UIState.Bounties, 
			_ => uIState, 
		};
	}

	private void Awake()
	{
	}

	public void Init()
	{
		Localisation();
		txtPDAUTC = base.transform.Find("pnlBackground/pnlBezel/pnlTopBar/txtTime").GetComponent<TMP_Text>();
		goJobTypes = base.transform.Find("pnlJobs/pnlJobTypes").gameObject;
		goJobOptions = base.transform.Find("pnlJobs/scrollJobOptions/Viewport/pnlJobOptions").gameObject;
		base.transform.Find("pnlGigNexus/pnlGig").GetComponent<Button>().onClick.AddListener(delegate
		{
			ToggleGig(bShow: false);
		});
		cgObjectives = base.transform.Find("pnlObjectives").GetComponent<CanvasGroup>();
		objectivesApp = cgObjectives.GetComponent<ObjectivesApp>();
		cgJobOptionsScroll = base.transform.Find("pnlJobs/scrollJobOptions").GetComponent<CanvasGroup>();
		cgJobs = base.transform.Find("pnlJobs").GetComponent<CanvasGroup>();
		cgTasks = base.transform.Find("pnlTasks").GetComponent<CanvasGroup>();
		cgGigNexus = base.transform.Find("pnlGigNexus").GetComponent<CanvasGroup>();
		cgFerry = base.transform.Find("pnlFerry").GetComponent<CanvasGroup>();
		cgBounties = base.transform.Find("pnlBounties").GetComponent<CanvasGroup>();
		cgHome = base.transform.Find("pnlHome").GetComponent<CanvasGroup>();
		cgJobFilters = base.transform.Find("pnlJobs/pnlJobFilters").GetComponent<CanvasGroup>();
		cgViz = base.transform.Find("pnlViz").GetComponent<CanvasGroup>();
		cgStandings = base.transform.Find("pnlStandings").GetComponent<CanvasGroup>();
		pdaVisualisers = cgViz.GetComponent<PDAVisualisers>();
		cgNotes = base.transform.Find("pnlNotes").GetComponent<CanvasGroup>();
		pdaNotes = cgNotes.GetComponent<PDANotes>();
		cgTimer = base.transform.Find("pnlTimer").GetComponent<CanvasGroup>();
		pdaTimer = cgTimer.GetComponent<PDATimer>();
		chkFilterWalls = base.transform.Find("pnlJobs/pnlJobFilters/pnlToggles/chkWalls").GetComponent<Toggle>();
		chkFilterWalls.onValueChanged.AddListener(delegate
		{
			UpdateFilterCT();
		});
		chkFilterFloors = base.transform.Find("pnlJobs/pnlJobFilters/pnlToggles/chkFloors").GetComponent<Toggle>();
		chkFilterFloors.onValueChanged.AddListener(delegate
		{
			UpdateFilterCT();
		});
		chkFilterConduits = base.transform.Find("pnlJobs/pnlJobFilters/pnlToggles/chkConduits").GetComponent<Toggle>();
		chkFilterConduits.onValueChanged.AddListener(delegate
		{
			UpdateFilterCT();
		});
		chkFilterCans = base.transform.Find("pnlJobs/pnlJobFilters/pnlToggles/chkCans").GetComponent<Toggle>();
		chkFilterCans.onValueChanged.AddListener(delegate
		{
			UpdateFilterCT();
		});
		chkFilterEquip = base.transform.Find("pnlJobs/pnlJobFilters/pnlToggles/chkEquip").GetComponent<Toggle>();
		chkFilterEquip.onValueChanged.AddListener(delegate
		{
			UpdateFilterCT();
		});
		chkFilterLoose = base.transform.Find("pnlJobs/pnlJobFilters/pnlToggles/chkLoose").GetComponent<Toggle>();
		chkFilterLoose.onValueChanged.AddListener(delegate
		{
			UpdateFilterCT();
		});
		Toggle toggle = chkFilterWalls;
		Toggle toggle2 = chkFilterFloors;
		Toggle toggle3 = chkFilterConduits;
		Toggle toggle4 = chkFilterCans;
		Toggle toggle5 = chkFilterEquip;
		bool flag = (chkFilterLoose.isOn = true);
		bool flag3 = (toggle5.isOn = flag);
		bool flag5 = (toggle4.isOn = flag3);
		bool flag7 = (toggle3.isOn = flag5);
		bool isOn = (toggle2.isOn = flag7);
		toggle.isOn = isOn;
		AudioManager.AddBtnAudio(chkFilterWalls.gameObject, null, "ShipUIBtnPDAClick02");
		AudioManager.AddBtnAudio(chkFilterFloors.gameObject, null, "ShipUIBtnPDAClick02");
		AudioManager.AddBtnAudio(chkFilterConduits.gameObject, null, "ShipUIBtnPDAClick02");
		AudioManager.AddBtnAudio(chkFilterCans.gameObject, null, "ShipUIBtnPDAClick02");
		AudioManager.AddBtnAudio(chkFilterEquip.gameObject, null, "ShipUIBtnPDAClick02");
		AudioManager.AddBtnAudio(chkFilterLoose.gameObject, null, "ShipUIBtnPDAClick02");
		cgHotbar = base.transform.Find("pnlHotbar").GetComponent<CanvasGroup>();
		cgHotbar.GetComponent<GUIPDAHotBar>().Activate();
		homepage = cgHome.GetComponent<GUIPDAHomepage>();
		homepage.UpdateAppNotifs();
		btnSort.onClick.AddListener(UpdateSocialSortButton);
		AudioManager.AddBtnAudio(btnSort.gameObject, null, "ShipUIBtnPDAClick02");
		BuildFilters();
		State = UIState.Closed;
		TogglePDAFrame(show: false);
		instance = this;
	}

	public void Localisation()
	{
		topBarTitle.SetText(DataHandler.GetString("GUI_PDA_TITLEBAR_CONSOLE"));
		tasksTitle.SetText(DataHandler.GetString("GUI_PDA_TASK_TITLE"));
		tasksTask.SetText(DataHandler.GetString("GUI_PDA_TASK_TASK"));
		tasksDuty.SetText(DataHandler.GetString("GUI_PDA_TASK_DUTY"));
		tasksTarget.SetText(DataHandler.GetString("GUI_PDA_TASK_TARGET"));
		tasksShip.SetText(DataHandler.GetString("GUI_PDA_TASK_SHIP"));
		vizTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_TITLE"));
		presetsTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_TITLE"));
		presetsDefault.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_DEFAULT"));
		presetsPower.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_POWER"));
		presetsDamage.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_DAMAGE"));
		presetsMass.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_MASS"));
		presetsCost.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_COST"));
		presetsHeat.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_HEAT"));
		presetsPressure.SetText(DataHandler.GetString("GUI_PDA_VIZ_PRESETS_PRESSURE"));
		togglesPowerTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_POWER"));
		togglesPlaceholderTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_PLACEHOLDERS"));
		togglesTasksTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_TASKS"));
		togglesCeilingTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_CEILING"));
		togglesUpdatesTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_UPDATES"));
		togglesExteriorsTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_EXTERIORS"));
		togglesContoursTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_CONTOURS"));
		togglesLogScaleTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_LOG_SCALE"));
		togglesLightsTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_LIGHTS"));
		togglesFOVTitle.SetText(DataHandler.GetString("GUI_PDA_VIZ_TOGGLES_FOV"));
		paramatersValue.SetText(DataHandler.GetString("GUI_PDA_VIZ_PARAMS_VALUE"));
		paramatersMin.SetText(DataHandler.GetString("GUI_PDA_VIZ_PARAMS_MIN"));
		paramatersMax.SetText(DataHandler.GetString("GUI_PDA_VIZ_PARAMS_MAX"));
		paramatersGradientLabel.SetText(DataHandler.GetString("GUI_PDA_VIZ_PARAMS_GRADIENT"));
		paramatersOpacityLabel.SetText(DataHandler.GetString("GUI_PDA_VIZ_PARAMS_OPACITY"));
		notesTitle.SetText(DataHandler.GetString("GUI_PDA_NOTES_TITLE"));
		timerTitle.SetText(DataHandler.GetString("GUI_PDA_NOTES_TIMER"));
		timerReset.SetText(DataHandler.GetString("GUI_PDA_NOTES_TIMER_RESET"));
		timerPlay.SetText(DataHandler.GetString("GUI_PDA_NOTES_TIMER_PLAY"));
		socialsTitle.SetText(DataHandler.GetString("GUI_PDA_SOCIALS_TITLE"));
		standingsTitle.SetText(DataHandler.GetString("GUI_PDA_STANDINGS_TITLE"));
		gigNexusTitle.SetText(DataHandler.GetString("GUI_PDA_GIGNEXUS_TITLE"));
		objectivesTitle.SetText(DataHandler.GetString("GUI_PDA_OBJECTIVES_TITLE"));
		objectivesChkCurrent.SetText(DataHandler.GetString("GUI_PDA_OBJECTIVES_CURRENT"));
		objectivesChkFinished.SetText(DataHandler.GetString("GUI_PDA_OBJECTIVES_FINISHED"));
		objectivesChkShowTutorials.SetText(DataHandler.GetString("GUI_PDA_OBJECTIVES_SHOWTUTORIALS"));
		objectivesChkMuteTutorials.SetText(DataHandler.GetString("GUI_PDA_OBJECTIVES_MUTEOBJECTIVES"));
		jobsTitle.SetText(DataHandler.GetString("GUI_PDA_JOBS_TITLE"));
		jobsFilter.SetText(DataHandler.GetString("GUI_PDA_JOBS_FILTER"));
		jobsFilterWall.SetText(DataHandler.GetString("GUI_PDA_JOBS_TOGGLES_WALL"));
		jobsFilterFloor.SetText(DataHandler.GetString("GUI_PDA_JOBS_TOGGLES_FLOOR"));
		jobsFilterLoose.SetText(DataHandler.GetString("GUI_PDA_JOBS_TOGGLES_LOOSE"));
		jobsFilterConduits.SetText(DataHandler.GetString("GUI_PDA_JOBS_TOGGLES_CONDUIT"));
		jobsFilterCans.SetText(DataHandler.GetString("GUI_PDA_JOBS_TOGGLES_CAN"));
		jobsFilterEquip.SetText(DataHandler.GetString("GUI_PDA_JOBS_TOGGLES_EQUIP"));
		ferryTitle.SetText(DataHandler.GetString("GUI_PDA_FERRY_TITLE"));
		ferrySubtitle.SetText(DataHandler.GetString("GUI_PDA_FERRY_SUBTITLE"));
		ferryATC.SetText(DataHandler.GetString("GUI_PDA_FERRY_REQUEST_ATC"));
		ferryRequestPickup.SetText(DataHandler.GetString("GUI_PDA_FERRY_REQUEST_PICKUP"));
		ferryArrivalDest.SetText(DataHandler.GetString("GUI_PDA_FERRY_ARRIVAL_DEST"));
		ferryArrivalPickup.SetText(DataHandler.GetString("GUI_PDA_FERRY_ARRIVAL_PICKUP"));
		ferryCancel.SetText(DataHandler.GetString("GUI_PDA_FERRY_CANCEL"));
		ferryNote.SetText(DataHandler.GetString("GUI_PDA_FERRY_NOTE"));
		PDAHomeTitle.SetText(DataHandler.GetString("GUI_PDA_HOME"));
	}

	public string GetFilterSave()
	{
		string text = "";
		foreach (MultiSelectDTO socialFilter in _socialFilters)
		{
			if (socialFilter.IsOn)
			{
				if (text != "")
				{
					text += ",";
				}
				text += socialFilter.Id;
			}
		}
		return text;
	}

	public void BuildFilters(string savedFilter = null)
	{
		_socialFilters.Clear();
		List<string> allLootNames = DataHandler.GetLoot("RELSocialFilters").GetAllLootNames();
		string[] array = null;
		if (!string.IsNullOrEmpty(savedFilter))
		{
			array = savedFilter.Split(',');
		}
		foreach (string item in allLootNames)
		{
			Condition cond = DataHandler.GetCond(item);
			if (cond != null)
			{
				_socialFilters.Add(new MultiSelectDTO
				{
					Id = item,
					FriendlyName = "Hide " + cond.strNameFriendly,
					IsOn = (array?.Contains(item) ?? false)
				});
			}
		}
		ddFilter.Init(_socialFilters, OnSocialFilterDropDown);
	}

	private void OnSocialFilterDropDown(List<MultiSelectDTO> filters)
	{
		_socialFilters = filters;
		ShowSocials();
	}

	private void UpdateSocialSortButton()
	{
		_currentSortMethod++;
		if (!Enum.IsDefined(typeof(SortMethod), _currentSortMethod))
		{
			_currentSortMethod = SortMethod.AlphabeticalAscending;
		}
		if ((int)_currentSortMethod < _filterSprites.Length)
		{
			btnSort.image.sprite = _filterSprites[(int)_currentSortMethod];
		}
		ShowSocials();
	}

	private void UpdateAppNotifs()
	{
		if (cgHotbar != null)
		{
			cgHotbar.GetComponent<GUIPDAHotBar>().UpdateAppNotifs();
		}
		if (homepage != null)
		{
			homepage.UpdateAppNotifs();
		}
	}

	public void RefreshHotbar()
	{
		if (cgHotbar != null)
		{
			cgHotbar.GetComponent<GUIPDAHotBar>().Refresh();
		}
	}

	public static void OpenApp(string appName)
	{
		if (instance == null || appName == "")
		{
			return;
		}
		string[] array = appName.Split(':');
		_ = array[0];
		string strPage = "";
		if (array.Length > 1)
		{
			strPage = array[1];
		}
		switch (array[0])
		{
		case "home":
			Debug.Log("Opening PDA home screen");
			instance.ToggleHome();
			break;
		case "zones":
			instance.State = UIState.Closed;
			CrewSim.LowerUI();
			MonoSingleton<GUIZones>.Instance.ToggleMenuVisibility();
			break;
		case "goals":
			Debug.Log("Toggling PDA objectives screen");
			instance.ToggleObjectives(strPage);
			break;
		case "gigs":
			Debug.Log("Opening PDA gigs screen");
			instance.ToggleGigNexus();
			break;
		case "bounties":
			Debug.Log("Opening PDA bounties screen");
			instance.ToggleBounties();
			break;
		case "ferry":
			Debug.Log("Opening PDA ferry screen");
			instance.ToggleFerry();
			break;
		case "files":
		{
			Debug.Log("Opening PDA files screen");
			CrewSim.LowerUI();
			List<CondOwner> cOs = CrewSim.GetSelectedCrew().GetCOs(bAllowLocked: false, instance.CTPDA);
			if (cOs != null && cOs.Count > 0)
			{
				cOs[0].AddCondAmount("IsPDAModeFiles", 1.0);
				CrewSim.RaiseUI("Computer", cOs[0]);
			}
			else
			{
				CrewSim.GetSelectedCrew().LogMessage(DataHandler.GetString("GUI_PDA_FILES_ERROR"), "Bad", CrewSim.GetSelectedCrew().strID);
			}
			break;
		}
		case "navmap":
			Debug.Log("Opening PDA nav map screen");
			instance.ToggleNAV();
			break;
		case "navlink":
			Debug.Log("Opening PDA nav link screen");
			instance.ToggleNAVLink();
			break;
		case "socials":
			Debug.Log("Opening PDA socials screen");
			instance.ToggleSocials();
			break;
		case "tasks":
			Debug.Log("Opening PDA tasks screen");
			instance.ToggleTasks();
			break;
		case "roster":
			Debug.Log("Opening PDA roster screen");
			instance.ToggleRosterUI();
			break;
		case "vote":
			Debug.Log("Opening PDA vote screen");
			instance.ToggleVoteUI();
			break;
		case "exit":
			Debug.Log("Closing PDA screen");
			GUITooltip2.SetToolTip("", "", show: false);
			instance.State = UIState.Closed;
			break;
		case "power":
			Debug.Log("Toggling PDA power view");
			CrewSim.objInstance.TogglePowerUI(CrewSim.shipCurrentLoaded);
			break;
		case "duties":
			Debug.Log("Toggling PDA duties screen");
			instance.ToggleDutiesUI();
			break;
		case "build":
			Debug.Log("Toggling PDA build screen");
			instance.ShowJobPaintUI("build");
			break;
		case "orders":
			Debug.Log("Toggling PDA actions screen");
			instance.ShowJobPaintUI("actions");
			break;
		case "inventory":
			Debug.Log("Toggling inventory from PDA");
			instance.State = UIState.Closed;
			CrewSim.LowerUI();
			CommandInventory.ToggleInventory(CrewSim.GetSelectedCrew());
			break;
		case "viz":
			Debug.Log("Toggling viz from PDA");
			instance.ToggleVizUI();
			break;
		case "notes":
			Debug.Log("Toggling notes from PDA");
			instance.ToggleNotesUI();
			break;
		case "timer":
			Debug.Log("Toggling timer from PDA");
			instance.ToggleTimerUI();
			break;
		case "standings":
			Debug.Log("Opening PDA standings screen");
			instance.ToggleStandings();
			break;
		default:
			Debug.LogWarning("Tried to open unrecognised app: " + appName + ", opening home screen!");
			instance.ToggleHome();
			break;
		}
	}

	private void TogglePDAFrame(bool show)
	{
		if (show)
		{
			bmpFrame.SetActive(value: true);
			bmpScreen.SetActive(value: true);
			objForeground.SetActive(value: true);
			objBackground.SetActive(value: true);
			objNavigation.SetActive(value: true);
			objHotbar.SetActive(value: false);
		}
		else
		{
			bmpFrame.SetActive(value: false);
			bmpScreen.SetActive(value: false);
			objForeground.SetActive(value: false);
			objBackground.SetActive(value: false);
			objNavigation.SetActive(value: false);
			objHotbar.SetActive(value: true);
			GUITooltip2.SetToolTip("", "", show: false);
		}
	}

	private void SlidePDA(int nStateNew)
	{
		Animator component = GetComponent<Animator>();
		component.speed = 1f / Time.timeScale;
		int integer = component.GetComponent<Animator>().GetInteger("AnimState");
		TogglePDAFrame(nStateNew != 1);
		if (integer == nStateNew)
		{
			return;
		}
		if (integer == 1)
		{
			component.SetInteger("AnimState", 0);
			AudioManager.am.PlayAudioEmitter("PDAOpen", bLoop: false);
			return;
		}
		component.SetInteger("AnimState", 1);
		AudioManager.am.PlayAudioEmitter("PDAClose", bLoop: false);
		if (cgObjectives.interactable)
		{
			ToggleObjectives();
		}
	}

	private void UpdateFilterCT()
	{
		List<string> list = new List<string>();
		if (chkFilterWalls.isOn)
		{
			list.Add("TIsWall1x1InstalledOrMineable");
		}
		if (chkFilterFloors.isOn)
		{
			list.Add("TIsFloorGrateOrFloorRock");
		}
		if (chkFilterConduits.isOn)
		{
			list.Add("TIsConduit00Installed");
		}
		if (chkFilterCans.isOn)
		{
			list.Add("TIsRCSValidInput");
		}
		if (chkFilterEquip.isOn)
		{
			list.Add("TIsInstalledEquipment");
		}
		if (chkFilterLoose.isOn)
		{
			list.Add("TIsLoose");
		}
		if (list.Count == 0)
		{
			list.Add("TNever");
		}
		ctJobFilter = new CondTrigger("GUIJobFilter", new string[0], new string[0], list.ToArray(), new string[0]);
		ctJobFilter.bAND = false;
	}

	private void ToggleRosterUI()
	{
		if (CrewSim.goUI != null && CrewSim.goUI.GetComponent<GUIRoster>() != null)
		{
			CrewSim.LowerUI();
		}
		else
		{
			CrewSim.RaiseUI("Roster", CrewSim.GetSelectedCrew());
		}
	}

	private void ToggleDutiesUI()
	{
		CrewSim.LowerUI();
		CrewSim.RaiseUI("Duties", CrewSim.coPlayer);
	}

	private void ToggleVoteUI()
	{
		CrewSim.LowerUI();
		CrewSim.RaiseUI("Vote", CrewSim.coPlayer);
	}

	public void ToggleObjectives(string strPage = "current")
	{
		if (cgObjectives.interactable)
		{
			State = UIState.Closed;
			return;
		}
		State = UIState.Objectives;
		ObjectivesApp componentInChildren = base.gameObject.GetComponentInChildren<ObjectivesApp>();
		if (componentInChildren != null)
		{
			switch (strPage)
			{
			case "current":
				componentInChildren.SetPage(ObjectivesAppPage.Current);
				break;
			case "finished":
				componentInChildren.SetPage(ObjectivesAppPage.Finished);
				break;
			case "settings":
				componentInChildren.SetPage(ObjectivesAppPage.Settings);
				break;
			}
		}
	}

	public void ToggleTasks()
	{
		if (cgTasks.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Tasks;
		}
	}

	public void ToggleSocials()
	{
		if (cgSocials.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Socials;
		}
	}

	public void ToggleStandings()
	{
		if (cgStandings.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Standings;
		}
	}

	public void ToggleGigNexus()
	{
		if (cgGigNexus.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.GigNexus;
		}
	}

	public void ToggleBounties()
	{
		if (cgBounties.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Bounties;
		}
	}

	public void ToggleFerry()
	{
		if (cgFerry.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Ferry;
		}
	}

	public void ToggleNAV(string strRegID = null)
	{
		bool flag = GUIOrbitDraw.Instance != null && GUIOrbitDraw.Instance.IsPDANav;
		if ((!string.IsNullOrEmpty(strRegID) || !flag) && !flag)
		{
			CrewSim.LowerUI();
		}
		Ship ship = CrewSim.GetSelectedCrew().ship;
		CondOwner condOwner = null;
		if (MonoSingleton<ObjectiveTracker>.Instance.subscribedShips.Contains(ship.strRegID) && ship.aNavs != null && ship.aNavs.Count > 0)
		{
			condOwner = ship.aNavs[0];
		}
		if (condOwner != null)
		{
			if (!flag)
			{
				CrewSim.RaiseUI("PDANAV", condOwner);
			}
			if (string.IsNullOrEmpty(strRegID))
			{
				return;
			}
			string text = strRegID;
			Ship shipByRegID = CrewSim.system.GetShipByRegID(strRegID);
			if (shipByRegID != null && shipByRegID.IsStationHidden())
			{
				JsonTransit transitConnections = DataHandler.GetTransitConnections(strRegID);
				if (transitConnections != null && transitConnections.aConnections != null)
				{
					JsonTransitConnection[] aConnections = transitConnections.aConnections;
					foreach (JsonTransitConnection jsonTransitConnection in aConnections)
					{
						if (jsonTransitConnection != null && !(jsonTransitConnection.strTargetRegID == strRegID))
						{
							shipByRegID = CrewSim.system.GetShipByRegID(jsonTransitConnection.strTargetRegID);
							if (shipByRegID == null || !shipByRegID.IsStationHidden())
							{
								text = jsonTransitConnection.strTargetRegID;
								break;
							}
						}
					}
				}
			}
			if (GUIOrbitDraw.Instance != null)
			{
				if (GUIOrbitDraw.Instance.IsTargetKnown(text))
				{
					GUIOrbitDraw.Instance.LockTarget(text);
					return;
				}
				CrewSim.GetSelectedCrew().LogMessage(DataHandler.GetString("GUI_PDA_ERROR_SHIP_NOT_FOUND"), "Bad", CrewSim.GetSelectedCrew().strID);
				GUIOrbitDraw.Instance.LockTarget(ship.strRegID);
			}
		}
		else
		{
			CrewSim.GetSelectedCrew().LogMessage(DataHandler.GetString("GUI_PDA_ERROR_NAV_NOT_FOUND"), "Bad", CrewSim.GetSelectedCrew().strID);
			ToggleNAVLink();
		}
	}

	public void ToggleNAVLink()
	{
		CrewSim.LowerUI();
		List<CondOwner> cOs = CrewSim.GetSelectedCrew().GetCOs(bAllowLocked: false, DataHandler.GetCondTrigger("TIsComputerPDANotDamaged"));
		if (cOs != null && cOs.Count > 0)
		{
			cOs[0].AddCondAmount("IsPDAModeNAVLink", 1.0);
			cOs[0].ZeroCondAmount("IsPDAModeFiles");
			CrewSim.RaiseUI("Computer", cOs[0]);
		}
		else
		{
			CrewSim.GetSelectedCrew().LogMessage(DataHandler.GetString("GUI_PDA_NAVLINK_ERROR"), "Bad", CrewSim.GetSelectedCrew().strID);
		}
	}

	public void ToggleClosed()
	{
		GUITooltip2.SetToolTip("", "", show: false);
		State = UIState.Closed;
	}

	public void ToggleHome()
	{
		if (cgHome.interactable)
		{
			GUITooltip2.SetToolTip("", "", show: false);
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Home;
		}
	}

	public void ToggleVizUI()
	{
		if (cgViz.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Viz;
		}
		pdaVisualisers.AssembleUI();
	}

	public void CycleVizMode()
	{
		pdaVisualisers.Cycle();
	}

	public void ToggleNotesUI()
	{
		if (cgNotes.interactable)
		{
			State = UIState.Closed;
			pdaNotes.SaveApp();
		}
		else
		{
			State = UIState.Notes;
		}
		pdaNotes.LoadApp();
	}

	public void SetSelectedFaction(StandingsDTO faction)
	{
		foreach (Transform item in base.transform.Find("pnlStandings/pnlList/Viewport/pnlListContent"))
		{
			PDAStandingsBar component = item.GetComponent<PDAStandingsBar>();
			if (component != null)
			{
				component.Deselect();
			}
		}
		strSelectedFaction = faction.FactionName;
		lblFactionName.text = faction.FactionNameFriendly;
		lblFactionRep.text = faction.Reputation;
		lblFactionRep.color = DataHandler.GetColor("FactionRep" + faction.Reputation);
		string text = (((double)faction.FactionScore > 0.0) ? "+" : "");
		lblFactionScore.text = text + faction.FactionScore.ToString("F1");
		if (faction.ExtrasVisible)
		{
			objFunds.SetActive(value: true);
			objSorties.SetActive(value: true);
			objAssists.SetActive(value: true);
			lblFactionFunds.text = "$" + faction.FactionFunds.ToString("F2");
			lblFactionAssists.text = faction.FactionAssists.ToString("F0");
			lblFactionSorties.text = faction.FactionSorties.ToString("F0");
		}
		else
		{
			objFunds.SetActive(value: false);
			objSorties.SetActive(value: false);
			objAssists.SetActive(value: false);
		}
		imgFactionLogo.texture = DataHandler.LoadPNG("logos/" + faction.FactionName + "Logo.png", bNorm: false);
	}

	public void ShowStandings()
	{
		Transform transform = base.transform.Find("pnlStandings/pnlList/Viewport/pnlListContent");
		foreach (Transform item in transform)
		{
			UnityEngine.Object.Destroy(item.gameObject);
		}
		transform.DetachChildren();
		if (CrewSim.GetSelectedCrew() == null)
		{
			return;
		}
		bool flag = false;
		float num = -9999999f;
		StandingsDTO selectedFaction = null;
		foreach (StandingsDTO standing in GetStandings(CrewSim.coPlayer))
		{
			UnityEngine.Object.Instantiate(prefabPDAStandingsBar, transform).SetFaction(standing);
			if (strSelectedFaction == standing.FactionName)
			{
				flag = true;
				SetSelectedFaction(standing);
			}
			if (standing.FactionScore > num)
			{
				num = standing.FactionScore;
				selectedFaction = standing;
			}
		}
		if (!flag)
		{
			SetSelectedFaction(selectedFaction);
		}
	}

	public void ToggleTimerUI()
	{
		if (cgTimer.interactable)
		{
			State = UIState.Closed;
		}
		else
		{
			State = UIState.Timer;
		}
	}

	public void ToggleGig(bool bShow)
	{
		CanvasGroup component = base.transform.Find("pnlGigNexus/pnlGig").GetComponent<CanvasGroup>();
		if (bShow)
		{
			AudioManager.am.PlayAudioEmitter("ShipUIBtnPDAClick02", bLoop: false);
			CanvasManager.ShowCanvasGroup(component);
		}
		else
		{
			AudioManager.am.PlayAudioEmitter("ShipUIBtnPDAClick01", bLoop: false);
			CanvasManager.HideCanvasGroup(component);
		}
	}

	private void ShowJobPaintUI(string btn)
	{
		State = UIState.JobBuild;
		CrewSim.objInstance.FinishPaintingJob();
		foreach (Transform item in goJobTypes.transform)
		{
			UnityEngine.Object.Destroy(item.gameObject);
		}
		goJobTypes.transform.DetachChildren();
		if (btn == "actions")
		{
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("CANC", "GUIActionCancel", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Cancel"
				});
			});
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("UNIN", "GUIActionUninstall", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Uninstall"
				});
			});
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("SCRA", "GUIActionScrap", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Scrap"
				});
			});
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("REPR", "GUIActionRepair", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Repair"
				});
			});
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("DISM", "GUIActionDismantle", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Dismantle"
				});
			});
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("HAUL", "GUIActionHaul", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Haul"
				});
			});
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("MINE", "GUIActionMine", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Mine"
				});
			});
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData("LOAD", "GUIActionReload", delegate
			{
				CrewSim.objInstance.StartPaintingJob(new JsonInstallable
				{
					strName = "Reload"
				});
			});
			CanvasManager.ShowCanvasGroup(cgJobFilters);
		}
		else
		{
			string[] array = new string[8] { "HULL", "HVAC", "POWR", "SENS", "CTRL", "FURN", "APPS", "MISC" };
			string[] array2 = new string[8] { "GUIBuildHull", "GUIBuildHVAC", "GUIBuildPower", "GUIBuildSensors", "GUIBuildControls", "GUIBuildFurniture", "GUIBuildAppliances", "GUIBuildOther" };
			for (int num = 0; num < array.Length; num++)
			{
				string strType = array[num];
				UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobTypes.transform).SetData(array[num], array2[num], delegate
				{
					ShowJobOptions(strType);
				});
			}
			CanvasManager.HideCanvasGroup(cgJobFilters);
		}
		EventSystem.current.SetSelectedGameObject(null);
	}

	public void HideJobPaintUI()
	{
		bool num = CrewSim.objInstance.goSelPart != null || CrewSim.objInstance.goPaintJob != null;
		CrewSim.objInstance.FinishPaintingJob();
		AudioManager.am.PlayAudioEmitter("ShipUIBtnPDAClick01", bLoop: false);
		if (!num && (State == UIState.JobBuild || State == UIState.JobBuildScroll || State == UIState.JobOrder))
		{
			State = UIState.Closed;
		}
	}

	private void ShowJobOptions(string strType)
	{
		State = UIState.JobBuildScroll;
		foreach (Transform item in goJobOptions.transform)
		{
			UnityEngine.Object.Destroy(item.gameObject);
		}
		foreach (JsonInstallable value in Installables.dictJobBuildOptionsListed[strType].Values)
		{
			UnityEngine.Object.Instantiate(prefabGUIJobItem, goJobOptions.transform).SetData(value);
		}
		EventSystem.current.SetSelectedGameObject(null);
		StartCoroutine(CrewSim.objInstance.ScrollTop(cgJobOptionsScroll.GetComponent<ScrollRect>()));
	}

	private void ShowSocials()
	{
		foreach (Transform item in tfpnlListContent)
		{
			UnityEngine.Object.Destroy(item.gameObject);
		}
		tfpnlListContent.DetachChildren();
		if (CrewSim.GetSelectedCrew() == null)
		{
			return;
		}
		GUISocialsRow component = Resources.Load<GameObject>("GUIShip/GUISocials/prefabSocialsRow").GetComponent<GUISocialsRow>();
		List<Relationship> knownSocialContacts = GetKnownSocialContacts(CrewSim.GetSelectedCrew());
		knownSocialContacts = ((_currentSortMethod == SortMethod.AlphabeticalAscending) ? knownSocialContacts.OrderBy((Relationship x) => x.pspec.strLastName).ToList() : ((_currentSortMethod == SortMethod.AlphabeticalDescending) ? knownSocialContacts.OrderByDescending((Relationship x) => x.pspec.strLastName).ToList() : ((_currentSortMethod != SortMethod.RelationAscending) ? knownSocialContacts.OrderByDescending((Relationship x) => x.fFamiliarity).ToList() : knownSocialContacts.OrderBy((Relationship x) => x.fFamiliarity).ToList())));
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		foreach (Relationship item2 in knownSocialContacts)
		{
			CondOwner cO = item2.pspec.GetCO();
			if (!FilterResult(item2, cO))
			{
				UnityEngine.Object.Instantiate(component, tfpnlListContent).SetContact(selectedCrew.socUs, item2.pspec, cO);
			}
		}
	}

	private bool FilterResult(Relationship rel, CondOwner coContact)
	{
		foreach (MultiSelectDTO socialFilter in _socialFilters)
		{
			if (socialFilter.IsOn)
			{
				if (socialFilter.Id == "IsDead" && coContact == null)
				{
					return true;
				}
				if (rel.aRelationships != null && rel.aRelationships.Contains(socialFilter.Id))
				{
					return true;
				}
			}
		}
		return false;
	}

	public void ScrollSocials(string strName)
	{
		if (State != UIState.Socials || string.IsNullOrEmpty(strName))
		{
			return;
		}
		float num = 0f;
		float num2 = 1f;
		List<Relationship> knownSocialContacts = GetKnownSocialContacts(CrewSim.GetSelectedCrew());
		if (knownSocialContacts.Count > 0)
		{
			num2 = knownSocialContacts.Count;
		}
		using (List<Relationship>.Enumerator enumerator = knownSocialContacts.GetEnumerator())
		{
			while (enumerator.MoveNext() && !(enumerator.Current.pspec.FullName == strName))
			{
				num += 1f;
			}
		}
		float num3 = 1f - num / num2;
		if (num3 <= 1f / num2)
		{
			num3 = 0f;
		}
		ScrollRect component = base.transform.Find("pnlSocials/pnlList").GetComponent<ScrollRect>();
		StartCoroutine(CrewSim.objInstance.ScrollPos(component, num3));
	}

	public static List<Relationship> GetKnownSocialContacts(CondOwner coUs)
	{
		List<Relationship> list = new List<Relationship>();
		if (coUs == null || coUs.socUs == null)
		{
			return list;
		}
		foreach (Relationship allPerson in coUs.socUs.GetAllPeople())
		{
			if (CTSocials.TriggeredREL(allPerson))
			{
				list.Insert(0, allPerson);
			}
			else
			{
				list.Add(allPerson);
			}
		}
		return list;
	}

	private List<StandingsDTO> GetStandings(CondOwner coUs)
	{
		List<JsonFaction> allFactions = CrewSim.system.GetAllFactions();
		List<string> allFactions2 = coUs.GetAllFactions();
		List<StandingsDTO> list = new List<StandingsDTO>();
		List<string> lootNames = DataHandler.GetLoot("TXTFactionAppExtras").GetLootNames();
		List<string> lootNames2 = DataHandler.GetLoot("TXTFactionAppFilters").GetLootNames();
		foreach (JsonFaction item in allFactions)
		{
			float num = 0f;
			bool flag = false;
			foreach (string item2 in allFactions2)
			{
				if (!flag)
				{
					flag = item.HasRelation(item2);
				}
				num += item.GetFactionScore(item2);
			}
			bool extrasVisible = lootNames.Contains(item.strName);
			double condAmount = coUs.GetCondAmount("Stat" + item.strName + "Scrip");
			if (lootNames2.Contains(item.strName))
			{
				double condAmount2 = coUs.GetCondAmount("Stat" + item.strName + "Assists");
				double condAmount3 = coUs.GetCondAmount("Stat" + item.strName + "Sorties");
				JsonFaction.Reputation reputation = JsonFaction.GetReputation(num);
				list.Add(new StandingsDTO
				{
					FactionName = item.strName,
					FactionNameFriendly = item.strNameFriendly,
					Reputation = reputation.ToString(),
					FactionScore = num,
					FactionFunds = condAmount,
					FactionSorties = condAmount3,
					FactionAssists = condAmount2,
					ExtrasVisible = extrasVisible
				});
			}
		}
		return list;
	}

	private void ShowGigNexus()
	{
		Transform transform = base.transform.Find("pnlGigNexus/pnlList/Viewport/pnlListContent");
		foreach (Transform item in transform)
		{
			UnityEngine.Object.Destroy(item.gameObject);
		}
		transform.DetachChildren();
		if (GigManager.aJobs == null)
		{
			Debug.LogError("ERROR: GigManager aJobs is null.");
			return;
		}
		GigManager.GetJobs();
		GUIPDAGigRow component = Resources.Load<GameObject>("GUIShip/prefabGigNexusPDARow").GetComponent<GUIPDAGigRow>();
		bool flag = true;
		foreach (JsonJobSave jjs in GigManager.aJobs)
		{
			if (jjs.bTaken)
			{
				GUIPDAGigRow ggr = UnityEngine.Object.Instantiate(component, transform);
				ggr.SetJob(jjs);
				ggr.onPointerClick.AddListener(delegate
				{
					ShowGig(jjs, ggr);
				});
				flag = false;
			}
		}
		if (flag)
		{
			TMP_Text tMP_Text = UnityEngine.Object.Instantiate(base.transform.Find("pnlGigNexus/pnlGig/Viewport/txt").GetComponent<TMP_Text>(), transform);
			tMP_Text.text = DataHandler.GetString("GUI_JOBSPDA_ROW_EMPTY1");
			UnityEngine.Object.Instantiate(tMP_Text, transform).text = DataHandler.GetString("GUI_JOBSPDA_ROW_EMPTY2");
		}
	}

	private void ShowGig(JsonJobSave jjs, GUIPDAGigRow ggr)
	{
		if (jjs != null)
		{
			ToggleGig(bShow: true);
			base.transform.Find("pnlGigNexus/pnlGig/Viewport/txt").GetComponent<TMP_Text>().text = GUIJobs.GetDisplayGigText(jjs);
			StartCoroutine(CrewSim.objInstance.ScrollTop(base.transform.Find("pnlGigNexus/pnlGig").GetComponent<ScrollRect>()));
			if (ggr != null && ggr.coFocus != null)
			{
				CrewSim.objInstance.CamCenter(ggr.coFocus);
			}
		}
	}

	private void ShowTasks()
	{
		Transform transform = base.transform.Find("pnlTasks/pnlList/Viewport/pnlListContent");
		foreach (Transform item in transform)
		{
			UnityEngine.Object.Destroy(item.gameObject);
		}
		transform.DetachChildren();
		GUITaskRow component = Resources.Load<GameObject>("GUIShip/GUITaskList/pnlTaskRowPDA").GetComponent<GUITaskRow>();
		List<Task2> allTasks = CrewSim.objInstance.workManager.GetAllTasks();
		GUITaskRow gUITaskRow = null;
		foreach (Task2 item2 in allTasks)
		{
			if (gUITaskRow == null)
			{
				gUITaskRow = UnityEngine.Object.Instantiate(component, transform);
			}
			if (gUITaskRow.SetTask(item2))
			{
				gUITaskRow = null;
			}
		}
		if (gUITaskRow != null)
		{
			UnityEngine.Object.Destroy(gUITaskRow.gameObject);
		}
	}

	public void AddTask(Task2 task)
	{
		if (task == null || State != UIState.Tasks)
		{
			return;
		}
		Transform transform = base.transform.Find("pnlTasks/pnlList/Viewport/pnlListContent");
		GUITaskRow gUITaskRow = null;
		foreach (Transform item in transform)
		{
			gUITaskRow = item.GetComponent<GUITaskRow>();
			if (gUITaskRow.Task == task)
			{
				gUITaskRow.SetTask(task);
				return;
			}
		}
		gUITaskRow = UnityEngine.Object.Instantiate(Resources.Load<GameObject>("GUIShip/GUITaskList/pnlTaskRowPDA").GetComponent<GUITaskRow>(), transform);
		gUITaskRow.SetTask(task);
	}

	public void RemoveTask(Task2 task)
	{
		if (task == null || State != UIState.Tasks)
		{
			return;
		}
		foreach (Transform item in base.transform.Find("pnlTasks/pnlList/Viewport/pnlListContent"))
		{
			if (item.GetComponent<GUITaskRow>().Task == task)
			{
				UnityEngine.Object.Destroy(item.gameObject);
				break;
			}
		}
	}
}
