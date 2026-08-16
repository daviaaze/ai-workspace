using System;
using System.Collections.Generic;
using System.Linq;
using Ostranauts.Core;
using Ostranauts.Objectives;
using Ostranauts.Utils;
using UnityEngine;

public class Powered : MonoBehaviour
{
	private static readonly double fMinDamage = 0.5;

	public CondOwner co;

	public JsonPowerInfo jsonPI;

	private GUIPowerOverlay guiPower;

	private bool bUsesPower;

	private CondTrigger ctUsePower;

	private CondTrigger ctRecharge;

	private double fPowerLast;

	private double fUpdateLast;

	private double fMinorUpdate;

	private double fPowerConnected;

	private double fDamageAmount;

	private Item itm;

	public CondTrigger ctPowerSource;

	private static Dictionary<Powered, double> mapPwrs = new Dictionary<Powered, double>();

	private static int debugTimesRunThisFrame;

	private static bool bOutput;

	private bool bDebug;

	private bool isOver5Percent;

	private double fMaxStored = -1.0;

	public bool bNoPowerThisLoop;

	private string _overrideCond;

	private double _overrideAmount;

	private static float _flickerChance = 0.2f;

	public PowerUsageRecorder PowerUsageRecorder { get; set; }

	public bool Hide
	{
		get
		{
			if (guiPower != null)
			{
				return guiPower.Hide;
			}
			return false;
		}
		set
		{
			if (guiPower != null)
			{
				guiPower.Hide = value;
			}
		}
	}

	public double PowerConnected => fPowerConnected;

	public double PowerStoredMax
	{
		get
		{
			if (fMaxStored < 0.0)
			{
				fMaxStored = CO.GetCondAmount("StatPowerMax");
			}
			if (CO != null)
			{
				return fMaxStored * CO.GetDamageState();
			}
			return fMaxStored;
		}
	}

	public double PowerStoredPercent
	{
		get
		{
			double condAmount = CO.GetCondAmount("StatPower");
			double num = CO.GetCondAmount("StatPowerMax");
			if (CO != null)
			{
				num *= CO.GetDamageState();
			}
			if (num <= 0.0)
			{
				return 0.0;
			}
			if (condAmount <= 0.0)
			{
				return 0.0;
			}
			if (condAmount > num)
			{
				return 1.0;
			}
			return condAmount / num;
		}
	}

	public double PowerRechargeAmount
	{
		get
		{
			double result = PowerStoredMax;
			if (CO != null)
			{
				result = PowerStoredMax - CO.GetCondAmount("StatPower");
				result *= 0.001;
			}
			return result;
		}
	}

	public CondOwner CO
	{
		get
		{
			if (co == null && guiPower != null)
			{
				co = GetComponent<CondOwner>();
				itm = GetComponent<Item>();
			}
			return co;
		}
	}

	private void Start()
	{
		fUpdateLast = StarSystem.fEpoch + (double)((float)UnityEngine.Random.Range(0, 100) * 0.01f);
		UpdateBaseFlickerAmount();
	}

	private void Update()
	{
		if (StarSystem.fEpoch - fUpdateLast >= 1.0)
		{
			Run();
			fUpdateLast = StarSystem.fEpoch;
		}
		if (!CrewSim.Paused && MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) < (double)_flickerChance && itm != null && itm.aLights.Count > 0 && (fDamageAmount >= fMinDamage || (double)itm.fFlickerAmount < 1.0))
		{
			float fFlickerAmount = 1f;
			float num = (float)((1.0 - fDamageAmount * fDamageAmount) / (1.0 - fMinDamage * fMinDamage));
			if (num > 1f)
			{
				num = 1f;
			}
			if (itm.fFlickerAmount == 0f)
			{
				if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) < (double)num)
				{
					fFlickerAmount = num;
				}
			}
			else if (MathUtils.Rand(0.0, 1.0, MathUtils.RandType.Flat) >= (double)num)
			{
				fFlickerAmount = 0f;
			}
			itm.fFlickerAmount = fFlickerAmount;
			foreach (Visibility aLight in itm.aLights)
			{
				aLight.fFlickerAmount = fFlickerAmount;
			}
		}
		if (StarSystem.fEpoch - fMinorUpdate < 0.30000001192092896)
		{
			return;
		}
		fMinorUpdate = StarSystem.fEpoch;
		double condAmount = CO.GetCondAmount("StatPower");
		double powerStoredMax = PowerStoredMax;
		if (powerStoredMax == 0.0 || condAmount / powerStoredMax < 0.05)
		{
			if (!isOver5Percent)
			{
				return;
			}
			CondOwner condOwner = CO.RootParent();
			if (condOwner != null)
			{
				int num2 = 10;
				bool flag = true;
				CondOwner condOwner2 = condOwner;
				while (flag && num2 > 0)
				{
					if (condOwner2.HasCond("IsHuman"))
					{
						condOwner2.LogMessage(CO.strNameFriendly + " is low on power.", "Bad", CO.strID);
						flag = false;
					}
					else if (condOwner2.objCOParent == null)
					{
						flag = false;
					}
					else
					{
						condOwner2 = condOwner2.objCOParent;
						num2--;
					}
				}
			}
			isOver5Percent = false;
		}
		else
		{
			isOver5Percent = true;
			if (condAmount > powerStoredMax)
			{
				ResetCurrentToMaxPower();
			}
		}
	}

	public static void UpdateBaseFlickerAmount()
	{
		int nFlickerAmount = DataHandler.GetUserSettings().nFlickerAmount;
		if (nFlickerAmount < 0)
		{
			_flickerChance = 0f;
		}
		else if (nFlickerAmount == 1)
		{
			_flickerChance = 0.025f;
		}
		else
		{
			_flickerChance = 0.2f;
		}
	}

	private void Run()
	{
		CondOwner cO = CO;
		if (cO == null)
		{
			Debug.LogError("ERROR: Running code on null CO.");
			return;
		}
		if (cO.ship != null)
		{
			if (ctRecharge != null && ctRecharge.Triggered(cO))
			{
				Recharge();
			}
			if (cO.HasCond("IsOverrideOff") || cO.HasCond("IsSignalOff"))
			{
				ShutDown(cO);
			}
			else if (bUsesPower && ctUsePower.Triggered(cO))
			{
				double num = ((_overrideAmount > 0.0 && cO.HasCond(_overrideCond)) ? _overrideAmount : jsonPI.fAmount);
				num *= StarSystem.fEpoch - fUpdateLast;
				UsePower(cO, num);
			}
			UpdatePowerUI();
		}
		if (bDebug)
		{
			debugTimesRunThisFrame++;
			bOutput = true;
		}
	}

	private void LateUpdate()
	{
		if (bOutput)
		{
			Debug.Log("Run Powered.Run() " + debugTimesRunThisFrame + " times this frame");
			bOutput = false;
			debugTimesRunThisFrame = 0;
		}
	}

	public void UserPowerExt(double fAmount)
	{
		UsePower(CO, fAmount);
	}

	private void UsePower(CondOwner coUs, double fAmount)
	{
		fPowerConnected = 0.0;
		double num = fAmount;
		double condAmount = coUs.GetCondAmount("StatPower");
		double num2 = StarSystem.fEpoch - fUpdateLast;
		List<CondOwner> list = new List<CondOwner>();
		if (jsonPI.bAllowExtPower && num > 0.0)
		{
			for (int i = 0; i < jsonPI.aInputPts.Length; i++)
			{
				Vector2 pos = coUs.GetPos(jsonPI.aInputPts[i]);
				Tile tileAtWorldCoords = coUs.ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
				if (tileAtWorldCoords == null)
				{
					continue;
				}
				foreach (Powered aConnectedPowerCO in tileAtWorldCoords.aConnectedPowerCOs)
				{
					if (!(aConnectedPowerCO == null) && !(aConnectedPowerCO.CO == null))
					{
						list.Add(aConnectedPowerCO.CO);
					}
				}
			}
			num = GatherPower(num, list);
			fPowerConnected += QueryPower(list);
		}
		if (num > 0.0 && coUs.HasCond("IsFusionCoreModule") && coUs.ship.Reactor != null && TileUtils.TileRange(coUs.tf.position, coUs.ship.Reactor.tf.position) < 5)
		{
			num = GatherPower(num, new List<CondOwner> { coUs.ship.Reactor });
			fPowerConnected += coUs.ship.Reactor.GetCondAmount("StatPower");
		}
		if (num > 0.0)
		{
			List<CondOwner> cOs = coUs.GetCOs(bAllowLocked: false, ctPowerSource);
			if (cOs != null)
			{
				num = GatherPower(num, cOs);
			}
		}
		if (num > 0.0)
		{
			if (condAmount >= fAmount)
			{
				num = 0.0;
				coUs.AddCondAmount("StatPower", 0.0 - fAmount);
				fPowerConnected += coUs.GetCondAmount("StatPower");
				if (PowerUsageRecorder == null)
				{
					PowerUsageRecorder = new PowerUsageRecorder();
				}
				PowerUsageRecorder.RecordChange((0.0 - fAmount) / num2);
			}
			else
			{
				num -= condAmount;
				coUs.AddCondAmount("StatPower", 0.0 - condAmount);
				fPowerConnected += coUs.GetCondAmount("StatPower");
				if (PowerUsageRecorder == null)
				{
					PowerUsageRecorder = new PowerUsageRecorder();
				}
				PowerUsageRecorder.RecordChange((0.0 - condAmount) / num2);
			}
		}
		if (num <= 0.0 && jsonPI.strIntPowerOn != null)
		{
			if (!coUs.HasCond("IsPowered"))
			{
				coUs.SetCondAmount("IsPowered", 1.0);
				Interaction interaction = DataHandler.GetInteraction(jsonPI.strIntPowerOn, null, getTrackedObject: true);
				if (interaction != null && interaction.CTTestUs.Triggered(coUs) && interaction.CTTestThem.Triggered(coUs))
				{
					coUs.QueueInteraction(coUs, interaction, bInsert: true);
				}
				else
				{
					DataHandler.ReleaseTrackedInteraction(interaction);
				}
			}
			fDamageAmount = coUs.GetDamageRate();
		}
		else if (num > 0.0 && jsonPI.strIntPowerOff != null)
		{
			ShutDown(coUs);
		}
		if (!(num <= 0.0) || list.Count <= 0 || !coUs.HasCond("IsRechargingContainer"))
		{
			return;
		}
		double num3 = fPowerConnected;
		List<CondOwner> cOs2 = coUs.GetCOs(bAllowLocked: true, ctPowerSource);
		if (cOs2 != null)
		{
			foreach (CondOwner item in cOs2)
			{
				if (item == null)
				{
					continue;
				}
				Powered pwr = item.Pwr;
				if (pwr == null)
				{
					continue;
				}
				double num4 = pwr.PowerRechargeAmount;
				if (num2 > 1800.0)
				{
					num4 *= 973.0;
				}
				if (num4 <= 0.0)
				{
					continue;
				}
				if (num3 >= num4)
				{
					pwr.CO.AddCondAmount("StatPower", num4);
					if (pwr.PowerUsageRecorder == null)
					{
						pwr.PowerUsageRecorder = new PowerUsageRecorder();
					}
					pwr.PowerUsageRecorder.RecordChange(num4 / num2);
					num3 -= num4;
				}
				else
				{
					pwr.CO.AddCondAmount("StatPower", num3);
					if (pwr.PowerUsageRecorder == null)
					{
						pwr.PowerUsageRecorder = new PowerUsageRecorder();
					}
					pwr.PowerUsageRecorder.RecordChange(num3 / num2);
					num3 = 0.0;
				}
				if (num3 <= 0.0)
				{
					break;
				}
			}
		}
		if (num3 < fPowerConnected)
		{
			GatherPower(fPowerConnected - num3, list);
			fPowerConnected = num3;
		}
	}

	private void ShutDown(CondOwner coUs)
	{
		if (!coUs.HasCond("IsPowered"))
		{
			return;
		}
		coUs.ZeroCondAmount("IsPowered");
		CondOwner condOwner = coUs.RootParent();
		if (condOwner != null)
		{
			int num = 10;
			bool flag = true;
			CondOwner condOwner2 = condOwner;
			while (flag && num > 0)
			{
				if (condOwner2.objCOParent == null)
				{
					flag = false;
					continue;
				}
				condOwner2 = condOwner2.objCOParent;
				if (condOwner2.HasCond("IsHuman"))
				{
					condOwner2.LogMessage(coUs.strNameFriendly + " powers off.", "Neutral", coUs.strID);
					flag = false;
				}
				else
				{
					num--;
				}
			}
		}
		Interaction interaction = DataHandler.GetInteraction(jsonPI.strIntPowerOff);
		if (interaction != null && interaction.CTTestUs.Triggered(coUs) && interaction.CTTestThem.Triggered(coUs))
		{
			coUs.QueueInteraction(coUs, interaction, bInsert: true);
		}
		if (coUs.HasCond("IsPowerObjective"))
		{
			MonoSingleton<ObjectiveTracker>.Instance.AddObjective(new AlarmObjective(AlarmType.nav_power, coUs, "Unpowered devices", "TIsPowered", stackableObjective: true, coUs.ship.strRegID));
		}
	}

	private void Recharge()
	{
		if (CO == null)
		{
			Debug.LogError("ERROR: Running code on null CO.");
			return;
		}
		Dictionary<Powered, double> dictionary = new Dictionary<Powered, double>();
		double num = -1.0;
		double num2 = 0.0;
		double num3 = StarSystem.fEpoch - fUpdateLast;
		for (int i = 0; i < jsonPI.aInputPts.Length + 1; i++)
		{
			Vector2 zero = Vector2.zero;
			if (i < jsonPI.aInputPts.Length)
			{
				zero = CO.GetPos(jsonPI.aInputPts[i]);
			}
			else
			{
				if (CO.mapPoints == null || !CO.mapPoints.ContainsKey("PowerOutput"))
				{
					break;
				}
				zero = CO.GetPos("PowerOutput");
			}
			Tile tileAtWorldCoords = CO.ship.GetTileAtWorldCoords1(zero.x, zero.y, bAllowDocked: true);
			if (tileAtWorldCoords == null)
			{
				continue;
			}
			foreach (Powered aConnectedPowerCO in tileAtWorldCoords.aConnectedPowerCOs)
			{
				if (aConnectedPowerCO == null || aConnectedPowerCO.CO == null || !aConnectedPowerCO.CO.HasCond("IsPowerStorage"))
				{
					continue;
				}
				double num4 = aConnectedPowerCO.PowerRechargeAmount;
				if (num3 > 1800.0)
				{
					num4 *= 973.0;
				}
				num2 += num4;
				if (num4 > 0.0)
				{
					if (!dictionary.ContainsKey(aConnectedPowerCO))
					{
						dictionary.Add(aConnectedPowerCO, num4);
					}
					if (num < 0.0 || num4 < num)
					{
						num = num4;
					}
				}
			}
		}
		double num5 = CO.GetCondAmount("StatPower");
		if (num2 > 0.0)
		{
			if (num5 >= num2)
			{
				foreach (Powered key in dictionary.Keys)
				{
					key.CO.AddCondAmount("StatPower", dictionary[key]);
					if (key.PowerUsageRecorder == null)
					{
						key.PowerUsageRecorder = new PowerUsageRecorder();
					}
					key.PowerUsageRecorder.RecordChange(dictionary[key] / num3);
					num5 -= dictionary[key];
				}
			}
			else
			{
				double num6 = num;
				num = -1.0;
				List<Powered> list = new List<Powered>();
				while (num5 > 0.0)
				{
					List<Powered> list2 = new List<Powered>(dictionary.Keys);
					foreach (Powered item in list2)
					{
						item.CO.AddCondAmount("StatPower", num6);
						if (item.PowerUsageRecorder == null)
						{
							item.PowerUsageRecorder = new PowerUsageRecorder();
						}
						item.PowerUsageRecorder.RecordChange(num6 / num3);
						dictionary[item] -= num6;
						if (dictionary[item] <= 0.0)
						{
							list.Add(item);
						}
						else if (num < 0.0 || dictionary[item] < num)
						{
							num = dictionary[item];
						}
						num5 -= num6;
					}
					list2.Clear();
					while (list.Count > 0)
					{
						dictionary.Remove(list[0]);
						list.Remove(list[0]);
					}
					if (num < 0.0)
					{
						list2 = null;
						break;
					}
					if (num * (double)dictionary.Keys.Count <= num5)
					{
						num6 = num;
						num = -1.0;
					}
					else
					{
						num = num5 / (double)dictionary.Keys.Count;
					}
					list2 = null;
					if (num5 == 0.0)
					{
						break;
					}
				}
				list.Clear();
				list = null;
			}
			dictionary.Clear();
			dictionary = null;
		}
		fPowerLast = num5;
		CO.SetCondAmount("StatPower", fPowerLast);
	}

	private double GatherPower(double fPowerNeeded, List<CondOwner> aCOs)
	{
		if (aCOs == null)
		{
			Debug.LogError("ERROR: Gathering power from null list.");
			return 0.0;
		}
		double fTime = StarSystem.fEpoch - fUpdateLast;
		mapPwrs.Clear();
		foreach (CondOwner item in aCOs.Distinct())
		{
			Powered pwr = item.Pwr;
			if (pwr == null || pwr.CO == null)
			{
				continue;
			}
			CondOwner condOwner = pwr.co;
			double condAmount = condOwner.GetCondAmount("StatPower");
			if (!(condAmount > 0.0))
			{
				continue;
			}
			if (condOwner.HasCond("IsPowerGen"))
			{
				double num = fPowerNeeded;
				if (fPowerNeeded > condAmount)
				{
					num = condAmount;
				}
				pwr.TransmitPower(num, 0, fTime);
				fPowerNeeded -= num;
				if (fPowerNeeded <= 0.0)
				{
					break;
				}
			}
			else
			{
				mapPwrs.Add(pwr, 0.0 - condAmount);
			}
		}
		if (fPowerNeeded <= 0.0)
		{
			return fPowerNeeded;
		}
		foreach (KeyValuePair<Powered, double> item2 in mapPwrs.OrderBy((KeyValuePair<Powered, double> keyValuePair) => keyValuePair.Value))
		{
			double num2 = 0.0 - item2.Value;
			Powered key = item2.Key;
			double num3 = key.TransmitPower(fPowerNeeded, 0, fTime);
			if (num2 - num3 <= 0.0)
			{
				CondOwner condOwner2 = co.RootParent();
				if (condOwner2 != null)
				{
					condOwner2.LogMessage(key.co.strNameFriendly + " no longer has power!", "Bad", key.co.strID);
				}
			}
			fPowerNeeded -= num3;
			if (fPowerNeeded <= 0.0)
			{
				return fPowerNeeded;
			}
		}
		return fPowerNeeded;
	}

	private double TransmitPower(double fAmount, int nDepth, double fTime)
	{
		if (CO == null)
		{
			Debug.LogError("ERROR: Running code on null CO.");
			return 0.0;
		}
		double num = 0.0;
		double num2 = 0.0;
		if (CO.GetCondAmount("StatPower") >= fAmount)
		{
			num = fAmount;
			CO.AddCondAmount("StatPower", 0.0 - fAmount);
		}
		else
		{
			num += CO.GetCondAmount("StatPower");
			CO.AddCondAmount("StatPower", 0.0 - num);
			bNoPowerThisLoop = true;
			nDepth++;
			for (int i = 0; i < jsonPI.aInputPts.Length; i++)
			{
				Vector2 pos = CO.GetPos(jsonPI.aInputPts[i]);
				Tile tileAtWorldCoords = CO.ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
				if (tileAtWorldCoords == null)
				{
					continue;
				}
				foreach (Powered aConnectedPowerCO in tileAtWorldCoords.aConnectedPowerCOs)
				{
					if (!(aConnectedPowerCO == null) && !(aConnectedPowerCO.CO == null) && !aConnectedPowerCO.bNoPowerThisLoop)
					{
						num2 += aConnectedPowerCO.TransmitPower(jsonPI.fAmount - num - num2, nDepth, fTime);
						if (num + num2 == jsonPI.fAmount)
						{
							break;
						}
					}
				}
			}
			nDepth--;
			if (nDepth <= 0)
			{
				UnmarkTransmits();
			}
		}
		if (PowerUsageRecorder == null)
		{
			PowerUsageRecorder = new PowerUsageRecorder();
		}
		PowerUsageRecorder.RecordChange((0.0 - num) / fTime);
		return num + num2;
	}

	private void UnmarkTransmits()
	{
		bNoPowerThisLoop = false;
		if (CO == null)
		{
			Debug.LogError("ERROR: Running code on null CO.");
			return;
		}
		for (int i = 0; i < jsonPI.aInputPts.Length; i++)
		{
			Vector2 pos = CO.GetPos(jsonPI.aInputPts[i]);
			Tile tileAtWorldCoords = CO.ship.GetTileAtWorldCoords1(pos.x, pos.y, bAllowDocked: true);
			if (tileAtWorldCoords == null)
			{
				continue;
			}
			foreach (Powered aConnectedPowerCO in tileAtWorldCoords.aConnectedPowerCOs)
			{
				if (!(aConnectedPowerCO == null) && !(aConnectedPowerCO.CO == null) && aConnectedPowerCO.bNoPowerThisLoop)
				{
					aConnectedPowerCO.UnmarkTransmits();
				}
			}
		}
	}

	private double QueryPower(List<CondOwner> aCOs)
	{
		if (aCOs == null)
		{
			Debug.LogError("ERROR: Querying power on null list.");
			return 0.0;
		}
		double num = 0.0;
		foreach (CondOwner aCO in aCOs)
		{
			Powered pwr = aCO.Pwr;
			if (pwr != null && pwr.CO != null)
			{
				double condAmount = pwr.CO.GetCondAmount("StatPower");
				if (condAmount > 0.0)
				{
					num += condAmount;
				}
			}
		}
		return num;
	}

	private void UpdatePowerUI()
	{
		if (PowerUsageRecorder != null)
		{
			PowerUsageDTO statsString = PowerUsageRecorder.GetStatsString(CO.GetCondAmount("StatPower"), PowerStoredMax);
			CO.mapInfo["PowerCurrentLoad"] = statsString.PowerCurrentLoad;
			CO.mapInfo["PowerRemainingTime"] = statsString.PowerRemainingTime;
		}
		if (CrewSim.PowerVizVisible && !(guiPower == null))
		{
			float num = 0f;
			double powerStoredMax = PowerStoredMax;
			double condAmount = CO.GetCondAmount("StatPower");
			if (powerStoredMax > 0.0)
			{
				num = Mathf.Min(Convert.ToSingle(condAmount) / (float)powerStoredMax, 1f);
			}
			else if (fPowerLast > 0.0)
			{
				num = Convert.ToSingle(fPowerLast / jsonPI.fAmount);
			}
			guiPower.Set(num, jsonPI);
			if (CO.HasCond("StatPower"))
			{
				CO.mapInfo["Charge"] = ((double)(num * 100f)).ToString("n2") + "%";
			}
		}
	}

	public void SetData(string strJsonPI)
	{
		jsonPI = DataHandler.GetPowerInfo(strJsonPI);
		if (jsonPI == null)
		{
			Debug.Log("Unable to load PowerInfo: " + strJsonPI);
			return;
		}
		if (jsonPI.Overlay())
		{
			guiPower = base.gameObject.AddComponent<GUIPowerOverlay>();
			Transform obj = guiPower.transform;
			Transform transform = CO.transform;
			obj.SetParent(base.transform, worldPositionStays: false);
			obj.localScale = new Vector3(transform.localScale.x, transform.localScale.y, 1f / transform.localScale.z);
			Vector2 vector = default(Vector2);
			if (jsonPI.aInputPts != null && jsonPI.aInputPts.Length != 0)
			{
				vector = CO.GetPos(jsonPI.aInputPts[0]);
			}
			guiPower.AlignInput(vector, new Vector3(1f / transform.localScale.x, 1f / transform.localScale.y, 1f / transform.localScale.z));
		}
		if (jsonPI.fAmount > 0.0)
		{
			if (jsonPI.strUsePowerCT != null)
			{
				bUsesPower = true;
				ctUsePower = DataHandler.GetCondTrigger(jsonPI.strUsePowerCT);
			}
			if (jsonPI.strRechargeCT != null)
			{
				ctRecharge = DataHandler.GetCondTrigger(jsonPI.strRechargeCT);
			}
		}
		if (jsonPI.strOverrideCond != null && jsonPI.fOverrideAmount > 0.0)
		{
			_overrideCond = jsonPI.strOverrideCond;
			_overrideAmount = jsonPI.fOverrideAmount;
		}
		ctPowerSource = (string.IsNullOrEmpty(jsonPI.strPowerSourceCT) ? (ctPowerSource = DataHandler.GetCondTrigger("TIsPowerStorage")) : DataHandler.GetCondTrigger(jsonPI.strPowerSourceCT));
	}

	public void ResetMaxPower()
	{
		fMaxStored = -1.0;
	}

	public void ResetCurrentToMaxPower()
	{
		if (!(CO == null) && CO.HasCond("StatPowerMax"))
		{
			double powerStoredMax = PowerStoredMax;
			double condAmount = CO.GetCondAmount("StatPower");
			if (powerStoredMax < condAmount)
			{
				CO.SetCondAmount("StatPower", powerStoredMax);
			}
		}
	}

	public override string ToString()
	{
		if (CO == null)
		{
			return "Powered: null";
		}
		return CO.ToString();
	}
}
