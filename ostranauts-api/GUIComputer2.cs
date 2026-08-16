using System;
using System.Collections;
using System.Collections.Generic;
using Ostranauts.Core;
using Ostranauts.Objectives;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class GUIComputer2 : GUIData
{
	private enum ScreenState
	{
		Login,
		Home,
		Logo,
		Search,
		Stored
	}

	private CondOwner _coUser;

	private CondOwner _coFileTemp;

	private CondOwner coNAV;

	private ScreenState _state;

	private CondTrigger _ctFile;

	private CondTrigger _ctNav;

	private CondTrigger _ctPDA;

	private CondTrigger _ctComputerOn;

	private CondTrigger _ctDataCard;

	private string strStorageLeft;

	private string strStorageRight;

	private string strStorageRun;

	private GameObject rowTempDevice;

	private List<CanvasGroup> aScreens;

	private CanvasGroup cgLogin;

	private CanvasGroup cgHome;

	private CanvasGroup cgSearch;

	private CanvasGroup cgStored;

	private CanvasGroup cgDetails;

	private CanvasGroup cgBtnHome;

	private CanvasGroup cgBtnQuit;

	private CanvasGroup cgVesselNameChange;

	private TMP_Text txtTime;

	private TMP_InputField txtShipNameInput;

	private CanvasGroup cgShipNameInput;

	[SerializeField]
	private Transform tfListNAVSearch;

	[SerializeField]
	private Transform tfListFileSearchLeft;

	[SerializeField]
	private Transform tfListFileSearchRight;

	[SerializeField]
	private Transform tfListDetailLinks;

	[SerializeField]
	private CanvasGroup cgMoveR;

	[SerializeField]
	private CanvasGroup cgMoveL;

	[SerializeField]
	private CanvasGroup cgDel;

	[SerializeField]
	private CanvasGroup cgRun;

	[SerializeField]
	private CanvasGroup cgStorageSearching;

	[SerializeField]
	private CanvasGroup cgSearchNoneFound;

	[SerializeField]
	private Button btnDetailsExit;

	[SerializeField]
	private Button btnLeftUp;

	[SerializeField]
	private Button btnRightUp;

	[SerializeField]
	private Image bmpBIN;

	[SerializeField]
	private Image bmpSND;

	[SerializeField]
	private Image bmpVID;

	[SerializeField]
	private Image bmpIMG;

	[SerializeField]
	private Image bmpTXT;

	[SerializeField]
	private RawImage bmpDetail;

	[SerializeField]
	private TMP_Text txtStorageLeft;

	[SerializeField]
	private TMP_Text txtStorageRight;

	[SerializeField]
	private TMP_Text txtDetail;

	[SerializeField]
	private TMP_Text txtDetailTitle;

	[SerializeField]
	private GameObject goDetailLinkTemplate;

	[SerializeField]
	private ScrollRect srDetailLinks;

	[SerializeField]
	private ScrollRect srDetailText;

	private bool bRefreshingFiles;

	private bool bBlink = true;

	private bool bSearchingLeft;

	private bool bSearchingRight;

	private float fBlinkPeriod = 0.4f;

	private float fBlink;

	private CondTrigger CTFile
	{
		get
		{
			if (_ctFile == null)
			{
				_ctFile = DataHandler.GetCondTrigger("TIsFitContainerDAT");
			}
			return _ctFile;
		}
	}

	private CondTrigger CTNav
	{
		get
		{
			if (_ctNav == null)
			{
				_ctNav = DataHandler.GetCondTrigger("TIsNavStationNotOff");
			}
			return _ctNav;
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

	private CondTrigger CTComputerOn
	{
		get
		{
			if (_ctComputerOn == null)
			{
				_ctComputerOn = DataHandler.GetCondTrigger("TIsComputerAccessible");
			}
			return _ctComputerOn;
		}
	}

	private CondTrigger CTDataCard
	{
		get
		{
			if (_ctDataCard == null)
			{
				_ctDataCard = DataHandler.GetCondTrigger("TIsDataCard");
			}
			return _ctDataCard;
		}
	}

	private CondOwner COUser
	{
		get
		{
			if (_coUser == null)
			{
				_coUser = CrewSim.GetSelectedCrew();
			}
			return _coUser;
		}
	}

	private CondOwner COFileTemp
	{
		get
		{
			if (_coFileTemp == null)
			{
				_coFileTemp = DataHandler.GetCondOwner("DataFile");
			}
			return _coFileTemp;
		}
	}

	private ScreenState State
	{
		get
		{
			return _state;
		}
		set
		{
			if (_state == value)
			{
				return;
			}
			foreach (CanvasGroup aScreen in aScreens)
			{
				CanvasManager.HideCanvasGroup(aScreen);
			}
			CanvasManager.HideCanvasGroup(cgBtnHome);
			CanvasManager.HideCanvasGroup(cgBtnQuit);
			switch (value)
			{
			case ScreenState.Logo:
				StartCoroutine("LogoAnimation");
				break;
			case ScreenState.Home:
				CanvasManager.ShowCanvasGroup(cgHome);
				CanvasManager.ShowCanvasGroup(cgBtnHome);
				CanvasManager.ShowCanvasGroup(cgBtnQuit);
				break;
			case ScreenState.Login:
				CanvasManager.ShowCanvasGroup(cgLogin);
				base.transform.Find("MiddleGround/Login/LoginBar/txtWelcome").GetComponent<TMP_Text>().text = "Welcome, " + COUser.pspec.strFirstName;
				StartCoroutine("LoginAnimation");
				break;
			case ScreenState.Search:
				COSelf.ZeroCondAmount("IsPDAModeNAVLink");
				CanvasManager.ShowCanvasGroup(cgSearch);
				CanvasManager.ShowCanvasGroup(cgBtnHome);
				CanvasManager.ShowCanvasGroup(cgBtnQuit);
				StartCoroutine(ShowNAVDevices(null));
				break;
			case ScreenState.Stored:
				COSelf.ZeroCondAmount("IsPDAModeFiles");
				CanvasManager.ShowCanvasGroup(cgStored);
				CanvasManager.ShowCanvasGroup(cgBtnHome);
				CanvasManager.ShowCanvasGroup(cgBtnQuit);
				StartCoroutine(ShowStorageDevices(bLeft: true, bRight: true));
				break;
			}
			_state = value;
		}
	}

	protected override void Awake()
	{
		base.Awake();
		txtTime = base.transform.Find("MiddleGround/txtTime").GetComponent<TMP_Text>();
		Button component = base.transform.Find("MiddleGround/btnHome").GetComponent<Button>();
		component.onClick.AddListener(delegate
		{
			CrewSim.LowerUI();
			GUIPDA.OpenApp("home");
		});
		AudioManager.AddBtnAudio(component.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		Button component2 = base.transform.Find("MiddleGround/btnQuit").GetComponent<Button>();
		component2.onClick.AddListener(delegate
		{
			CrewSim.LowerUI();
		});
		AudioManager.AddBtnAudio(component2.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		Button component3 = base.transform.Find("MiddleGround/Home/btnSearch").GetComponent<Button>();
		component3.onClick.AddListener(delegate
		{
			State = ScreenState.Search;
		});
		AudioManager.AddBtnAudio(component3.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		Button component4 = base.transform.Find("MiddleGround/Home/btnStorage").GetComponent<Button>();
		component4.onClick.AddListener(delegate
		{
			State = ScreenState.Stored;
		});
		AudioManager.AddBtnAudio(component4.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		Button component5 = base.transform.Find("MiddleGround/Search/pnlNavStation/btnEdit/editIcon").GetComponent<Button>();
		component5.onClick.AddListener(delegate
		{
			StartNameEdit();
		});
		AudioManager.AddBtnAudio(component5.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		btnDetailsExit.onClick.AddListener(delegate
		{
			CanvasManager.HideCanvasGroup(cgDetails);
		});
		AudioManager.AddBtnAudio(btnDetailsExit.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		btnLeftUp.onClick.AddListener(delegate
		{
			StartCoroutine(ShowStorageDevices(bLeft: true, bRight: false));
		});
		AudioManager.AddBtnAudio(btnLeftUp.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		btnRightUp.onClick.AddListener(delegate
		{
			StartCoroutine(ShowStorageDevices(bLeft: false, bRight: true));
		});
		AudioManager.AddBtnAudio(btnRightUp.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		cgDel.GetComponent<Button>().onClick.AddListener(delegate
		{
			DeleteFilesAll();
		});
		AudioManager.AddBtnAudio(cgDel.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		cgMoveL.GetComponent<Button>().onClick.AddListener(delegate
		{
			MoveFiles(strStorageRight, strStorageLeft);
		});
		AudioManager.AddBtnAudio(cgMoveL.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		cgMoveR.GetComponent<Button>().onClick.AddListener(delegate
		{
			MoveFiles(strStorageLeft, strStorageRight);
		});
		AudioManager.AddBtnAudio(cgMoveR.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		cgRun.GetComponent<Button>().onClick.AddListener(delegate
		{
			RunFile();
		});
		AudioManager.AddBtnAudio(cgRun.gameObject, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
		txtShipNameInput = base.transform.Find("MiddleGround/Search/pnlNavStation/txtInputVesselNameEdit").GetComponent<TMP_InputField>();
		cgShipNameInput = base.transform.Find("MiddleGround/Search/pnlNavStation/txtInputVesselNameEdit").GetComponent<CanvasGroup>();
		txtShipNameInput.onSubmit.AddListener(delegate
		{
			ChangeShipName();
		});
		txtShipNameInput.resetOnDeActivation = true;
		txtShipNameInput.onSelect.AddListener(delegate
		{
			CrewSim.Typing = true;
			SteamManager.OpenOnScreenKeyboard(txtShipNameInput.transform);
		});
		txtShipNameInput.onDeselect.AddListener(delegate
		{
			CrewSim.Typing = false;
			CanvasManager.HideCanvasGroup(cgShipNameInput);
		});
		txtShipNameInput.onValueChanged.AddListener(delegate
		{
			AudioManager.am.PlayAudioEmitter("ShipUIComputerList", bLoop: false);
		});
		CanvasManager.HideCanvasGroup(cgShipNameInput);
		cgBtnHome = component.GetComponent<CanvasGroup>();
		cgBtnQuit = component2.GetComponent<CanvasGroup>();
		cgHome = base.transform.Find("MiddleGround/Home").GetComponent<CanvasGroup>();
		cgLogin = base.transform.Find("MiddleGround/Login").GetComponent<CanvasGroup>();
		cgSearch = base.transform.Find("MiddleGround/Search").GetComponent<CanvasGroup>();
		cgStored = base.transform.Find("MiddleGround/Stored").GetComponent<CanvasGroup>();
		cgDetails = base.transform.Find("MiddleGround/Details").GetComponent<CanvasGroup>();
		aScreens = new List<CanvasGroup> { cgHome, cgLogin, cgSearch, cgStored, cgDetails };
		fBlink = fBlinkPeriod;
		rowTempDevice = Resources.Load("GUIShip/GUIComputer/pnlDeviceRow") as GameObject;
	}

	public override void Init(CondOwner coSelf, Dictionary<string, string> mapGPMData, string strGPMKey)
	{
		base.Init(coSelf, mapGPMData, strGPMKey);
		State = GetCondState();
	}

	private void StartNameEdit()
	{
		CanvasManager.ShowCanvasGroup(cgShipNameInput);
		txtShipNameInput.text = coNAV.ship.publicName;
		txtShipNameInput.ActivateInputField();
	}

	private void ChangeShipName()
	{
		coNAV.ship.publicName = txtShipNameInput.text;
		if (coNAV.ship.json != null)
		{
			coNAV.ship.json.publicName = coNAV.ship.publicName;
		}
		ShowNav(tfListNAVSearch, coNAV);
		txtShipNameInput.DeactivateInputField();
		CanvasManager.HideCanvasGroup(cgShipNameInput);
	}

	private void Update()
	{
		txtTime.text = MathUtils.GetUTCFromS(StarSystem.fEpoch);
		fBlink -= CrewSim.TimeElapsedScaled();
		if (fBlink < 0f)
		{
			bBlink = !bBlink;
			fBlink = fBlinkPeriod;
		}
	}

	public IEnumerator LogoAnimation()
	{
		float duration = 1.4f;
		float timePassed = 0f;
		CanvasGroup component = base.transform.Find("Background/bmpBG").GetComponent<CanvasGroup>();
		CanvasGroup cgBlank = base.transform.Find("Background/bmpBlank").GetComponent<CanvasGroup>();
		cgBlank.alpha = 0f;
		component.alpha = 1f;
		while (duration > 0f)
		{
			duration -= Time.deltaTime;
			yield return null;
		}
		duration = 0.4f;
		while (cgBlank.alpha < 1f)
		{
			timePassed += Time.deltaTime;
			float t = Mathf.Clamp01(timePassed / duration);
			cgBlank.alpha = Mathf.Lerp(cgBlank.alpha, 1f, t);
			yield return null;
		}
		State = ScreenState.Login;
		yield return null;
	}

	public IEnumerator LoginAnimation()
	{
		float duration = 0f;
		float threshold = UnityEngine.Random.Range(0.02f, 0.04f);
		TMP_Text PasswordText = base.transform.Find("MiddleGround/Login/LoginBar/txtPwd").GetComponent<TMP_Text>();
		CanvasGroup cgTick = base.transform.Find("MiddleGround/Login/bmpUnlock").GetComponent<CanvasGroup>();
		CanvasManager.HideCanvasGroup(cgTick);
		while (true)
		{
			if (duration > threshold)
			{
				PasswordText.text += "*";
				duration = 0f;
				threshold = UnityEngine.Random.Range(0.02f, 0.04f);
			}
			duration += Time.deltaTime;
			if (PasswordText.text.Length > 35)
			{
				break;
			}
			yield return null;
		}
		CanvasManager.ShowCanvasGroup(cgTick);
		duration = 0.4f;
		while (duration > 0f)
		{
			duration -= Time.deltaTime;
			yield return null;
		}
		COSelf.AddCondAmount("IsPDALoggedIn", 1.0);
		State = GetCondState();
		yield return null;
	}

	public IEnumerator ShowNAVDevices(CondOwner coAutoSelect)
	{
		AudioManager.am.PlayAudioEmitter("ShipUIComputerProcessing", bLoop: false);
		if (coAutoSelect == null && CTNav.Triggered(COSelf))
		{
			coAutoSelect = COSelf;
		}
		List<CondOwner> aCOs = ((!(coAutoSelect != null)) ? COUser.ship.GetICOs1(CTNav, bSubObjects: true, bAllowDocked: false, bAllowLocked: true) : new List<CondOwner> { coAutoSelect });
		TMP_Text txtSearching = base.transform.Find("MiddleGround/Search/txtSearching").GetComponent<TMP_Text>();
		CanvasGroup component = base.transform.Find("MiddleGround/Search/pnlNavStation").GetComponent<CanvasGroup>();
		foreach (Transform item in tfListNAVSearch)
		{
			UnityEngine.Object.Destroy(item.gameObject);
		}
		CanvasManager.HideCanvasGroup(component);
		CanvasManager.HideCanvasGroup(cgSearchNoneFound);
		float duration = 1.4f;
		float threshold = UnityEngine.Random.Range(0.2f, 0.4f);
		while (duration > 0f)
		{
			txtSearching.alpha = 0f;
			if (bBlink)
			{
				txtSearching.alpha = 1f;
			}
			duration -= Time.deltaTime;
			yield return null;
		}
		duration = 0f;
		bool bNoneFound = true;
		while (true)
		{
			if (State != ScreenState.Search)
			{
				yield break;
			}
			txtSearching.alpha = 0f;
			if (bBlink)
			{
				txtSearching.alpha = 1f;
			}
			if (aCOs.Count > 0 && duration > threshold)
			{
				CondOwner condOwner = aCOs[0];
				aCOs.RemoveAt(0);
				if (condOwner == COSelf && CTPDA.Triggered(condOwner))
				{
					continue;
				}
				CreateDeviceRow(condOwner, tfListNAVSearch, ShowNav);
				AudioManager.am.PlayAudioEmitter("ShipUIComputerList", bLoop: false);
				duration = 0f;
				threshold = UnityEngine.Random.Range(0.02f, 0.04f);
				bNoneFound = false;
			}
			duration += Time.deltaTime;
			if (aCOs.Count == 0)
			{
				break;
			}
			yield return null;
		}
		txtSearching.alpha = 0f;
		if (bNoneFound)
		{
			CanvasManager.ShowCanvasGroup(cgSearchNoneFound);
		}
		if (State == ScreenState.Search)
		{
			if (coAutoSelect != null)
			{
				ShowNav(tfListNAVSearch, coAutoSelect);
			}
			yield return null;
		}
	}

	private IEnumerator ShowStorageDevices(bool bLeft, bool bRight)
	{
		AudioManager.am.PlayAudioEmitter("ShipUIComputerProcessing", bLoop: false);
		if (bLeft)
		{
			strStorageLeft = null;
			bSearchingLeft = true;
			CanvasManager.HideCanvasGroup(txtStorageLeft.GetComponent<CanvasGroup>());
			btnLeftUp.interactable = false;
		}
		if (bRight)
		{
			strStorageRight = null;
			bSearchingRight = true;
			CanvasManager.HideCanvasGroup(txtStorageRight.GetComponent<CanvasGroup>());
			btnRightUp.interactable = false;
		}
		if (bSearchingLeft || bSearchingRight)
		{
			CanvasManager.ShowCanvasGroup(cgStorageSearching);
		}
		CanvasManager.HideCanvasGroup(cgRun);
		CanvasManager.HideCanvasGroup(cgDel);
		CanvasManager.HideCanvasGroup(cgMoveL);
		CanvasManager.HideCanvasGroup(cgMoveR);
		List<CondOwner> aCOs = COUser.ship.GetICOs1(CTComputerOn, bSubObjects: true, bAllowDocked: false, bAllowLocked: false);
		CondOwner.NullSafeAddRange(ref aCOs, COUser.GetCOs(bAllowLocked: false, CTDataCard));
		aCOs.Sort((CondOwner x, CondOwner y) => MathUtils.GetDistanceSquared(x, COSelf).CompareTo(MathUtils.GetDistanceSquared(y, COSelf)));
		TMP_Text txtSearching = base.transform.Find("MiddleGround/Stored/pnlSearching/txtSearching").GetComponent<TMP_Text>();
		foreach (Transform item in tfListFileSearchLeft)
		{
			if (!bLeft)
			{
				break;
			}
			UnityEngine.Object.Destroy(item.gameObject);
		}
		foreach (Transform item2 in tfListFileSearchRight)
		{
			if (!bRight)
			{
				break;
			}
			UnityEngine.Object.Destroy(item2.gameObject);
		}
		float duration = 1.4f;
		float threshold = UnityEngine.Random.Range(0.2f, 0.4f);
		while (duration > 0f)
		{
			txtSearching.alpha = 0f;
			if (bBlink)
			{
				txtSearching.alpha = 1f;
			}
			duration -= Time.deltaTime;
			yield return null;
		}
		duration = 0f;
		while (true)
		{
			if (State != ScreenState.Stored)
			{
				yield break;
			}
			txtSearching.alpha = 0f;
			if (bBlink)
			{
				txtSearching.alpha = 1f;
			}
			if (aCOs.Count > 0 && duration > threshold)
			{
				CondOwner coDevice = aCOs[0];
				aCOs.RemoveAt(0);
				if (bLeft)
				{
					CreateDeviceRow(coDevice, tfListFileSearchLeft, ShowDeviceFiles);
				}
				if (bRight)
				{
					CreateDeviceRow(coDevice, tfListFileSearchRight, ShowDeviceFiles);
				}
				duration = 0f;
				threshold = UnityEngine.Random.Range(0.02f, 0.04f);
				AudioManager.am.PlayAudioEmitter("ShipUIComputerList", bLoop: false);
			}
			duration += Time.deltaTime;
			if (aCOs.Count == 0)
			{
				break;
			}
			yield return null;
		}
		if (bLeft)
		{
			bSearchingLeft = false;
		}
		if (bRight)
		{
			bSearchingRight = false;
		}
		if (!bSearchingLeft && !bSearchingRight)
		{
			CanvasManager.HideCanvasGroup(cgStorageSearching);
		}
		yield return null;
	}

	private void CreateDeviceRow(CondOwner coDevice, Transform tfList, Action<Transform, CondOwner> act = null)
	{
		GameObject obj = UnityEngine.Object.Instantiate(rowTempDevice, tfList);
		string deviceName = GetDeviceName(coDevice);
		DeviceRow component = obj.GetComponent<DeviceRow>();
		component.Init(coDevice, deviceName, act);
		if (coDevice == COSelf)
		{
			component.Tint(Color.white);
		}
	}

	private string GetDeviceName(CondOwner coDevice)
	{
		double num = MathUtils.GetDistance(coDevice, COSelf);
		string text = coDevice.ShortName;
		string text2 = " DIN: " + coDevice.strID.Substring(coDevice.strID.Length - 4).ToUpper();
		if (coDevice.objCOParent != null)
		{
			text = coDevice.RootParent().ShortName + " " + text;
		}
		text = text + " (" + MathUtils.GetDistUnits(num * 6.6845869117759804E-12) + text2 + ")";
		if (coDevice == COSelf)
		{
			text += "*";
		}
		return text;
	}

	private void ShowDeviceFiles(Transform tfList, CondOwner coDevice)
	{
		StartCoroutine(_ShowDeviceFiles(tfList, coDevice));
	}

	private IEnumerator _ShowDeviceFiles(Transform tfList, CondOwner coDevice)
	{
		if (coDevice == null)
		{
			StartCoroutine(ShowStorageDevices(tfList == tfListFileSearchLeft, tfList == tfListFileSearchRight));
			yield break;
		}
		AudioManager.am.PlayAudioEmitter("ShipUIComputerProcessing", bLoop: false);
		GameObject rowTempFile = Resources.Load("GUIShip/GUIComputer/chkDataFileRow") as GameObject;
		if (rowTempFile == null)
		{
			Debug.LogWarning("Error: rowTempFile is null");
			yield break;
		}
		foreach (Transform tf in tfList)
		{
			UnityEngine.Object.Destroy(tf.gameObject);
		}
		yield return null;
		CondOwner coNavData = null;
		bool bNAV = false;
		if (CTNav.Triggered(coDevice))
		{
			bNAV = true;
			coNavData = GUIOrbitDraw.GenerateNavDataCO(coDevice);
			coDevice.AddCO(coNavData, bEquip: false, bOverflow: true, bIgnoreLocks: true);
		}
		List<CondOwner> aCOs = coDevice.GetCOs(bAllowLocked: true, CTFile);
		if (aCOs != null)
		{
			if (aCOs.Count > 0)
			{
				aCOs.RemoveAll((CondOwner co) => co == null);
				aCOs.Sort((CondOwner x, CondOwner y) => string.Compare(x.FriendlyName, y.FriendlyName, StringComparison.Ordinal));
			}
			float threshold = UnityEngine.Random.Range(0.2f, 0.4f);
			float duration = 0f;
			while (true)
			{
				if (State != ScreenState.Stored)
				{
					yield break;
				}
				if (aCOs.Count > 0 && duration > threshold)
				{
					CondOwner condOwner = aCOs[0];
					aCOs.RemoveAt(0);
					if (condOwner.objCOParent == null || condOwner.objCOParent.objCOParent != coDevice)
					{
						continue;
					}
					if (bNAV && condOwner.HasCond("IsDataBINNAV") && condOwner != coNavData)
					{
						coDevice.RemoveCO(condOwner, bForce: true);
						condOwner.Destroy();
						duration = 0f;
						continue;
					}
					GameObject gameObject = UnityEngine.Object.Instantiate(rowTempFile, tfList);
					GUIBtnLitRim component = gameObject.GetComponent<GUIBtnLitRim>();
					component.SetText(condOwner.FriendlyName);
					DatafileRow dfr = gameObject.GetComponent<DatafileRow>();
					dfr.strCOID = condOwner.strID;
					dfr.strName = condOwner.strName;
					dfr.chk.onValueChanged.AddListener(delegate
					{
						ToggleFile(dfr);
					});
					string value = null;
					if (dictPropMap != null && dictPropMap.TryGetValue("Datafile_" + condOwner.strName, out value))
					{
						component.Tint(Color.gray);
						dfr.Tint(Color.gray);
					}
					if (condOwner.HasCond("IsDataIMG"))
					{
						dfr.SetFileIcon(bmpIMG);
					}
					else if (condOwner.HasCond("IsDataSND"))
					{
						dfr.SetFileIcon(bmpSND);
					}
					else if (condOwner.HasCond("IsDataTXT"))
					{
						dfr.SetFileIcon(bmpTXT);
					}
					else if (condOwner.HasCond("IsDataVID"))
					{
						dfr.SetFileIcon(bmpVID);
					}
					else
					{
						dfr.SetFileIcon(bmpBIN);
					}
					duration = 0f;
					threshold = UnityEngine.Random.Range(0.02f, 0.04f);
					AudioManager.am.PlayAudioEmitter("ShipUIComputerList", bLoop: false);
				}
				duration += Time.deltaTime;
				if (aCOs.Count == 0)
				{
					break;
				}
				yield return null;
			}
		}
		if (tfList == tfListFileSearchLeft)
		{
			strStorageLeft = coDevice.strID;
			txtStorageLeft.text = GetDeviceName(coDevice);
			CanvasManager.ShowCanvasGroup(txtStorageLeft.GetComponent<CanvasGroup>());
			btnLeftUp.interactable = true;
		}
		else
		{
			strStorageRight = coDevice.strID;
			txtStorageRight.text = GetDeviceName(coDevice);
			CanvasManager.ShowCanvasGroup(txtStorageRight.GetComponent<CanvasGroup>());
			btnRightUp.interactable = true;
		}
	}

	private void ToggleFile(DatafileRow dfr)
	{
		if (bRefreshingFiles)
		{
			return;
		}
		bRefreshingFiles = true;
		AudioManager.am.PlayAudioEmitter("ShipUIComputerList", bLoop: false);
		Transform transform = tfListFileSearchLeft;
		Transform transform2 = tfListFileSearchRight;
		if (dfr.transform.parent != transform)
		{
			transform = tfListFileSearchRight;
			transform2 = tfListFileSearchLeft;
		}
		CanvasManager.HideCanvasGroup(cgRun);
		CanvasManager.HideCanvasGroup(cgDel);
		CanvasManager.HideCanvasGroup(cgMoveL);
		CanvasManager.HideCanvasGroup(cgMoveR);
		foreach (Transform item in transform2)
		{
			Toggle component = item.GetComponent<Toggle>();
			if (component == null)
			{
				break;
			}
			component.isOn = false;
		}
		strStorageRun = null;
		int num = 0;
		foreach (Transform item2 in transform)
		{
			DatafileRow component2 = item2.GetComponent<DatafileRow>();
			if (component2.chk.isOn)
			{
				strStorageRun = component2.strCOID;
				num++;
			}
		}
		if (num == 1)
		{
			CanvasManager.ShowCanvasGroup(cgRun);
		}
		else
		{
			strStorageRun = null;
		}
		if (num > 0)
		{
			CanvasManager.ShowCanvasGroup(cgDel);
			if (transform == tfListFileSearchLeft)
			{
				CanvasManager.ShowCanvasGroup(cgMoveR);
			}
			else
			{
				CanvasManager.ShowCanvasGroup(cgMoveL);
			}
		}
		bRefreshingFiles = false;
	}

	private void DeleteFilesAll()
	{
		DeleteFiles(tfListFileSearchLeft, strStorageLeft);
		DeleteFiles(tfListFileSearchRight, strStorageRight);
	}

	private void DeleteFiles(Transform tfList, string strStorageCOID)
	{
		CondOwner value = null;
		if (string.IsNullOrEmpty(strStorageCOID) || !DataHandler.mapCOs.TryGetValue(strStorageCOID, out value))
		{
			return;
		}
		bool flag = false;
		foreach (Transform tf in tfList)
		{
			DatafileRow component = tf.GetComponent<DatafileRow>();
			if (component.chk.isOn && !string.IsNullOrEmpty(component.strCOID))
			{
				CondOwner value2 = null;
				if (DataHandler.mapCOs.TryGetValue(component.strCOID, out value2))
				{
					value.RemoveCO(value2);
					flag = true;
				}
			}
		}
		if (flag && strStorageCOID == strStorageLeft)
		{
			ShowDeviceFiles(tfListFileSearchLeft, value);
		}
		if (flag && strStorageCOID == strStorageRight)
		{
			ShowDeviceFiles(tfListFileSearchRight, value);
		}
		if (flag)
		{
			CanvasManager.HideCanvasGroup(cgRun);
			CanvasManager.HideCanvasGroup(cgDel);
			CanvasManager.HideCanvasGroup(cgMoveL);
			CanvasManager.HideCanvasGroup(cgMoveR);
		}
	}

	private void MoveFiles(string strFrom, string strTo)
	{
		if (string.IsNullOrEmpty(strFrom) || string.IsNullOrEmpty(strTo) || strFrom == strTo)
		{
			return;
		}
		CondOwner value = null;
		CondOwner value2 = null;
		if (!DataHandler.mapCOs.TryGetValue(strFrom, out value) || !DataHandler.mapCOs.TryGetValue(strTo, out value2))
		{
			return;
		}
		Transform transform = tfListFileSearchLeft;
		Transform tfList = tfListFileSearchRight;
		if (strFrom == strStorageRight)
		{
			transform = tfListFileSearchRight;
			tfList = tfListFileSearchLeft;
		}
		foreach (Transform item in transform)
		{
			DatafileRow component = item.GetComponent<DatafileRow>();
			if (!component.chk.isOn || string.IsNullOrEmpty(component.strCOID))
			{
				continue;
			}
			CondOwner value3 = null;
			if (DataHandler.mapCOs.TryGetValue(component.strCOID, out value3))
			{
				value.RemoveCO(value3);
				CondOwner condOwner = value2.AddCO(value3, bEquip: false, bOverflow: true, bIgnoreLocks: true);
				if (condOwner != null)
				{
					Debug.LogWarning("Could not add DataFile " + condOwner.strName + " to destination CO " + value2.strName);
				}
				if (value3.HasCond("IsDataBINNAV") && CTNav.Triggered(value2))
				{
					GUIOrbitDraw.ImportNavDataCO(value2, value3);
				}
			}
			value3 = null;
		}
		ShowDeviceFiles(transform, value);
		ShowDeviceFiles(tfList, value2);
	}

	private void RunFile()
	{
		foreach (Transform tfListDetailLink in tfListDetailLinks)
		{
			UnityEngine.Object.Destroy(tfListDetailLink.gameObject);
		}
		if (string.IsNullOrEmpty(strStorageRun))
		{
			return;
		}
		CondOwner value = null;
		if (!DataHandler.mapCOs.TryGetValue(strStorageRun, out value))
		{
			value = COFileTemp;
			value.strID = strStorageRun;
			value.strName = strStorageRun;
		}
		Interaction fileInteraction = GetFileInteraction(value.strName);
		if (fileInteraction == null)
		{
			return;
		}
		if (fileInteraction.strName == "TEMPDataGeneric")
		{
			fileInteraction.strDesc = value.strDesc;
			fileInteraction.strTitle = value.FriendlyName;
		}
		fileInteraction.objUs = COUser;
		fileInteraction.objThem = value;
		fileInteraction.ApplyEffects();
		dictPropMap["Datafile_" + value.strName] = StarSystem.fEpoch.ToString();
		if (strStorageLeft != null)
		{
			TintToggledFiles(tfListFileSearchLeft);
			TintToggledFiles(tfListFileSearchRight);
		}
		CanvasManager.ShowCanvasGroup(cgDetails);
		txtDetailTitle.text = fileInteraction.strTitle;
		txtDetail.text = fileInteraction.strDesc;
		bmpDetail.texture = DataHandler.LoadPNG(fileInteraction.strImage + ".png", bNorm: false);
		string[] aInverse = fileInteraction.aInverse;
		foreach (string obj in aInverse)
		{
			string[] array = obj.Split(',');
			Interaction iaReply = DataHandler.GetInteraction(array[0]);
			if (iaReply == null)
			{
				continue;
			}
			iaReply.objUs = COUser;
			iaReply.objThem = value;
			iaReply.bManual = true;
			iaReply.strPlot = fileInteraction.strPlot;
			if (iaReply.objUs == COUser && iaReply.Triggered(COUser, value))
			{
				GameObject obj2 = UnityEngine.Object.Instantiate(goDetailLinkTemplate, tfListDetailLinks);
				obj2.transform.Find("txt").GetComponent<TMP_Text>().text = iaReply.strTitle;
				obj2.GetComponent<Button>().onClick.AddListener(delegate
				{
					strStorageRun = iaReply.strName;
					RunFile();
				});
				AudioManager.AddBtnAudio(obj2, "ShipUIBtnPDAClick01", "ShipUIBtnPDAClick02");
			}
		}
		StartCoroutine(CrewSim.objInstance.ScrollTop(srDetailLinks));
		StartCoroutine(CrewSim.objInstance.ScrollTop(srDetailText));
	}

	private void TintToggledFiles(Transform tfList)
	{
		foreach (Transform tf in tfList)
		{
			DatafileRow component = tf.GetComponent<DatafileRow>();
			if (!(component == null) && component.chk.isOn)
			{
				component.Tint(Color.gray);
				tf.GetComponent<GUIBtnLitRim>().Tint(Color.gray);
			}
		}
	}

	private Interaction GetFileInteraction(string strFile)
	{
		Interaction interaction = DataHandler.GetInteraction(strFile);
		if (interaction == null)
		{
			interaction = DataHandler.GetInteraction("TEMPDataGeneric");
		}
		return interaction;
	}

	private void ShowNav(Transform tfList, CondOwner co)
	{
		AudioManager.am.PlayAudioEmitter("ShipUIComputerProcessing", bLoop: false);
		coNAV = co;
		CanvasManager.ShowCanvasGroup(base.transform.Find("MiddleGround/Search/pnlNavStation").GetComponent<CanvasGroup>());
		TMP_Text component = base.transform.Find("MiddleGround/Search/pnlNavStation/txtDataValue").GetComponent<TMP_Text>();
		TMP_Text component2 = base.transform.Find("MiddleGround/Search/pnlNavStation/txtStatus").GetComponent<TMP_Text>();
		Button component3 = base.transform.Find("MiddleGround/Search/pnlNavStation/btnLink").GetComponent<Button>();
		Button component4 = base.transform.Find("MiddleGround/Search/pnlNavStation/btnUnlink").GetComponent<Button>();
		CanvasGroup component5 = component3.GetComponent<CanvasGroup>();
		CanvasGroup component6 = component4.GetComponent<CanvasGroup>();
		component.text = co.ship.publicName + "\n";
		component.text = component.text + co.ship.strRegID + "\n";
		component.text = component.text + co.ship.make + "\n";
		component.text = component.text + co.ship.model + "\n";
		component.text = component.text + co.ship.year + "\n";
		CanvasManager.HideCanvasGroup(component5);
		CanvasManager.HideCanvasGroup(component6);
		component3.onClick.RemoveAllListeners();
		component4.onClick.RemoveAllListeners();
		if (MonoSingleton<ObjectiveTracker>.Instance.subscribedShips.IndexOf(co.ship.strRegID) < 0)
		{
			CanvasManager.ShowCanvasGroup(component5);
			component3.onClick.AddListener(delegate
			{
				MonoSingleton<ObjectiveTracker>.Instance.AddShipSubscription(co.ship.strRegID);
				ShowNav(tfList, co);
				AudioManager.am.PlayAudioEmitter("ShipUIComputerLinkOn", bLoop: false);
			});
			component2.text = "STATUS:\n<color=#FF5100>UNLINKED</color>";
		}
		else
		{
			CanvasManager.ShowCanvasGroup(component6);
			component4.onClick.AddListener(delegate
			{
				MonoSingleton<ObjectiveTracker>.Instance.RemoveShipSubscription(co.ship.strRegID);
				ShowNav(tfList, co);
				AudioManager.am.PlayAudioEmitter("ShipUIComputerLinkOff", bLoop: false);
			});
			component2.text = "STATUS:\n<color=#25FF78>LINKED</color>";
		}
	}

	private ScreenState GetCondState()
	{
		if (COSelf.HasCond("IsPDAModeNAVLink"))
		{
			return ScreenState.Search;
		}
		if (COSelf.HasCond("IsPDAModeFiles"))
		{
			return ScreenState.Stored;
		}
		return ScreenState.Home;
	}

	public override void SaveAndClose()
	{
		if (dictPropMap != null)
		{
			base.SaveAndClose();
			if (_coFileTemp != null)
			{
				_coFileTemp.RemoveFromCurrentHome(bForce: true);
				_coFileTemp.Destroy();
			}
		}
	}
}
