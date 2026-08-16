using System;
using System.Collections.Generic;

public class GigManager
{
	public static List<JsonJobSave> aJobs;

	public static float BonusPlantinumTimeDiv = 3f;

	public static float BonusGoldTimeDiv = 2.5f;

	public static float BonusSilverTimeDiv = 1.5f;

	public static void Init(JsonJobSave[] aJobsIn = null)
	{
		aJobs = new List<JsonJobSave>();
		if (aJobsIn != null)
		{
			foreach (JsonJobSave jsonJobSave in aJobsIn)
			{
				aJobs.Add(jsonJobSave.Clone());
			}
		}
	}

	private static void CullJobs()
	{
		foreach (JsonJobSave item in new List<JsonJobSave>(aJobs))
		{
			if (!CheckValid(item))
			{
				aJobs.Remove(item);
			}
		}
	}

	private static bool CheckValid(JsonJobSave jjs)
	{
		if (jjs == null)
		{
			return false;
		}
		if (jjs.strClientID == null || jjs.strThemID == null)
		{
			jjs.bInvalid = true;
			return false;
		}
		if (!jjs.bTaken && jjs.fEpochOfferExpired <= StarSystem.fEpoch)
		{
			jjs.bInvalid = true;
			return false;
		}
		if (jjs.COClient() == null)
		{
			jjs.bInvalid = true;
			return false;
		}
		if (jjs.COThem() == null || jjs.COThem().ship == null)
		{
			jjs.bInvalid = true;
			return false;
		}
		if (jjs.str3rdID != null && (jjs.CO3rd() == null || jjs.CO3rd() == null))
		{
			jjs.bInvalid = true;
			return false;
		}
		return true;
	}

	public static bool TakeJob(JsonJobSave jjs, CondOwner coTaker, CondOwner coKiosk)
	{
		if (jjs == null || coTaker == null)
		{
			return false;
		}
		jjs.bTaken = jjs.CanCOTakeThisJob(coTaker);
		if (jjs.bTaken && jjs.strRegIDPickup != null)
		{
			if (coKiosk.ship.strRegID != jjs.strRegIDPickup || coKiosk == null)
			{
				jjs.strFailReasons = DataHandler.GetString("GUI_JOBS_MAIN_ERROR_WRONG_ORIGIN");
				jjs.bTaken = false;
				return jjs.bTaken;
			}
			if (coKiosk.GetCOsSafe(bAllowLocked: true).Count > 0)
			{
				jjs.strFailReasons = DataHandler.GetString("GUI_JOBS_MAIN_ERROR_INV_FULL");
				jjs.bTaken = false;
				return jjs.bTaken;
			}
		}
		if (jjs.bTaken)
		{
			Interaction interactionSetupClient = jjs.GetInteractionSetupClient();
			Interaction interactionSetupPlayer = jjs.GetInteractionSetupPlayer(coTaker);
			if (interactionSetupClient != null && interactionSetupPlayer != null)
			{
				interactionSetupClient.ApplyEffects();
				interactionSetupPlayer.ApplyEffects();
			}
			jjs.fEpochExpired = StarSystem.fEpoch + jjs.JobTemplate().fDuration * jjs.fTimeMult * 3600.0;
			coTaker.AddCondAmount(Ledger.CURRENCY, 0.0 - jjs.fCostContract - (double)(int)jjs.fItemValue);
			Ledger.RecordTransaction(coTaker, DataHandler.GetString("GUI_JOBS_NAMECO"), 0.0 - jjs.fCostContract - (double)(int)jjs.fItemValue, DataHandler.GetString("GUI_JOBS_LEDGER_COLLATERAL_PREFIX") + interactionSetupClient.strTitle);
			if (jjs.strJobItems != null)
			{
				foreach (CondOwner item in DataHandler.GetLoot(DataHandler.GetJobItems(jjs.strJobItems).strLootPickup).GetCOLoot(coKiosk, bSuppressOverride: false))
				{
					coKiosk.AddCO(item, bEquip: false, bOverflow: true, bIgnoreLocks: true);
				}
			}
		}
		return jjs.bTaken;
	}

	public static void AbandonJob(JsonJobSave jjs, CondOwner coTaker)
	{
		if (jjs != null && !(coTaker == null))
		{
			aJobs.Remove(jjs);
			Interaction interactionAbandonClient = jjs.GetInteractionAbandonClient();
			Interaction interactionAbandonPlayer = jjs.GetInteractionAbandonPlayer(coTaker);
			if (interactionAbandonClient != null && interactionAbandonPlayer != null)
			{
				interactionAbandonClient.ApplyEffects();
				interactionAbandonPlayer.ApplyEffects();
			}
		}
	}

	public static bool TurnInJob(JsonJobSave jjs, CondOwner coTaker, CondOwner coKiosk)
	{
		if (jjs == null || coTaker == null || coKiosk == null)
		{
			return false;
		}
		if (jjs.fEpochExpired <= StarSystem.fEpoch)
		{
			jjs.strFailReasons = DataHandler.GetString("GUI_JOBS_MAIN_ERROR_EXPIRED");
			return false;
		}
		List<CondOwner> list = new List<CondOwner>();
		if (jjs.strRegIDDropoff != null)
		{
			if (coKiosk.ship.strRegID != jjs.strRegIDDropoff)
			{
				jjs.strFailReasons = DataHandler.GetString("GUI_JOBS_MAIN_ERROR_WRONG_DEST");
				return false;
			}
			if (jjs.strJobItems != null)
			{
				JsonJobItems jobItems = DataHandler.GetJobItems(jjs.strJobItems);
				Loot value = null;
				DataHandler.dictLoot.TryGetValue("TXTJobItemsTemplate", out value);
				value.aCOs = jobItems.aCTsDeliver.Clone() as string[];
				List<CondTrigger> cTLoot = value.GetCTLoot(null);
				new List<CondOwner>();
				List<CondOwner> cOs = coKiosk.GetCOs(bAllowLocked: true);
				if (cOs != null)
				{
					foreach (CondOwner item in cOs)
					{
						foreach (CondTrigger item2 in cTLoot)
						{
							if (item2.Triggered(item))
							{
								item2.fCount -= item.StackCount;
								list.Add(item);
							}
							if (item2.fCount <= 0f)
							{
								cTLoot.Remove(item2);
								break;
							}
						}
					}
				}
				if (cTLoot.Count > 0)
				{
					jjs.strFailReasons = DataHandler.GetString("GUI_JOBS_MAIN_ERROR_INV_MISSING");
					foreach (string itemQuality in GUITooltip.GetItemQualityList(cTLoot))
					{
						jjs.strFailReasons = jjs.strFailReasons + itemQuality + "\n";
					}
					return false;
				}
			}
		}
		Interaction interactionFinishClient = jjs.GetInteractionFinishClient();
		if (interactionFinishClient == null || !interactionFinishClient.Triggered(interactionFinishClient.objUs, interactionFinishClient.objThem, bStats: false, bIgnoreItems: true))
		{
			return false;
		}
		Interaction interactionFinishPlayer = jjs.GetInteractionFinishPlayer(coTaker);
		if (interactionFinishPlayer == null || !interactionFinishPlayer.Triggered(interactionFinishPlayer.objUs, interactionFinishPlayer.objThem, bStats: false, bIgnoreItems: true))
		{
			return false;
		}
		interactionFinishClient.ApplyEffects();
		interactionFinishPlayer.ApplyEffects();
		foreach (CondOwner item3 in list)
		{
			coKiosk.RemoveCO(item3);
			item3.Destroy();
		}
		double num = jjs.fPayout * jjs.fPayoutMult;
		int tier = GetTier(jjs);
		num *= (double)tier;
		num += (double)(int)jjs.fItemValue;
		coTaker.AddCondAmount(Ledger.CURRENCY, num);
		string text = interactionFinishClient.strTitle + " - " + DataHandler.GetString("GUI_JOBS_BONUS_" + tier);
		Ledger.RecordTransaction(coTaker, DataHandler.GetString("GUI_JOBS_NAMECO"), (float)num, text);
		CrewSim.UnlockAchievement("ACH_GIGS");
		aJobs.Remove(jjs);
		coTaker.LogMessage(DataHandler.GetString("GUI_JOBS_LOG_TURNEDIN") + text, "Good", coTaker.strID);
		return true;
	}

	public static int GetTier(JsonJobSave jjs)
	{
		if (jjs == null)
		{
			return 1;
		}
		double num = jjs.fEpochExpired - jjs.JobTemplate().fDuration * jjs.fTimeMult * 3600.0;
		if (StarSystem.fEpoch - num <= jjs.JobTemplate().fDuration * jjs.fTimeMult * 3600.0 / (double)BonusPlantinumTimeDiv)
		{
			return 8;
		}
		if (StarSystem.fEpoch - num <= jjs.JobTemplate().fDuration * jjs.fTimeMult * 3600.0 / (double)BonusGoldTimeDiv)
		{
			return 4;
		}
		if (StarSystem.fEpoch - num <= jjs.JobTemplate().fDuration * jjs.fTimeMult * 3600.0 / (double)BonusSilverTimeDiv)
		{
			return 2;
		}
		return 1;
	}

	public static void GetJobs()
	{
		CullJobs();
		List<string> list = new List<string> { CrewSim.coPlayer.strID };
		CondOwner selectedCrew = CrewSim.GetSelectedCrew();
		Ship nearestStationRegional = CrewSim.system.GetNearestStationRegional(selectedCrew.ship.objSS.vPosx, selectedCrew.ship.objSS.vPosy);
		string closestStationId = GetClosestStationId(selectedCrew);
		string text = ((nearestStationRegional != null) ? nearestStationRegional.strRegID : "");
		int num = 0;
		int num2 = 0;
		foreach (JsonJobSave aJob in aJobs)
		{
			if (CheckValid(aJob))
			{
				if (CheckLocal(aJob, selectedCrew, 0.006684586871415377))
				{
					num2++;
				}
				if (aJob.strJobName.Contains("MVPCourierTestDeliverCOShortHop") && aJob.strJobName.Contains(closestStationId))
				{
					num++;
				}
			}
		}
		string text2 = "MVPCourierTestDeliverCOShortHop";
		if (DataHandler.dictJobs.ContainsKey(text2 + closestStationId))
		{
			text2 += closestStationId;
		}
		int num3 = 7;
		while (num <= 0 && num3 > 0)
		{
			num3--;
			JsonJobSave jsonJobSave = MakeJob(text2, list);
			if (jsonJobSave != null)
			{
				aJobs.Add(jsonJobSave);
				list.Add(jsonJobSave.strClientID);
				break;
			}
		}
		if (aJobs.Count > 5 && num2 > 0)
		{
			return;
		}
		num3 = MathUtils.Rand(5, 10, MathUtils.RandType.Flat);
		Loot loot = DataHandler.GetLoot("TXTJobList" + text);
		if (loot.strName == "Blank")
		{
			loot = DataHandler.GetLoot("TXTJobList");
			if (loot.strName == "Blank")
			{
				return;
			}
		}
		while (num3 > 0)
		{
			num3--;
			List<string> lootNames = loot.GetLootNames();
			if (lootNames.Count != 0)
			{
				JsonJobSave jsonJobSave2 = MakeJob(lootNames[0], list);
				if (jsonJobSave2 != null)
				{
					aJobs.Add(jsonJobSave2);
					list.Add(jsonJobSave2.strClientID);
				}
				continue;
			}
			break;
		}
	}

	public static bool CheckLocal(JsonJobSave jjs, CondOwner coUser, double fSearchRadius)
	{
		if (jjs == null)
		{
			return false;
		}
		bool flag = false;
		CondOwner condOwner = jjs.COThem();
		if (condOwner != null && coUser.ship.GetRangeTo(condOwner.ship) < fSearchRadius)
		{
			flag = true;
		}
		if (jjs.CO3rd() != null && coUser.ship.GetRangeTo(jjs.CO3rd().ship) < fSearchRadius)
		{
			flag = true;
		}
		if (!jjs.bTaken && !flag)
		{
			return false;
		}
		if (!jjs.bTaken)
		{
			double num = 1.0;
			double fTimeMult = 1.0;
			Ship ship = coUser.ship;
			if (jjs.strRegIDPickup != null)
			{
				ship = CrewSim.system.GetShipByRegID(jjs.strRegIDPickup);
			}
			Ship ship2 = jjs.COThem()?.ship;
			if (jjs.strRegIDDropoff != null)
			{
				ship2 = CrewSim.system.GetShipByRegID(jjs.strRegIDDropoff);
			}
			if (ship2 != null && ship != null)
			{
				if (ship == ship2)
				{
					num = 1.0;
				}
				else if (JsonTransit.IsTransitConnected(ship.strRegID, ship2.strRegID))
				{
					num = 1.2;
				}
				else
				{
					double rangeTo = ship.GetRangeTo(ship2);
					num = (rangeTo * 149597872.0 / 3600.0 * 2.0 + jjs.fPayout + 1000.0) / jjs.fPayout;
					if (!ship2.objSS.bIsBO)
					{
						num *= 3.0;
					}
					if (rangeTo > 3.342293712194078E-05)
					{
						double? num2 = jjs.JobTemplate()?.fDuration;
						if (num2 == 0.0 || !num2.HasValue)
						{
							num2 = 1.0;
						}
						fTimeMult = (Math.Max(1.0, rangeTo * 70.0) / num2).Value;
					}
				}
			}
			jjs.fTimeMult = fTimeMult;
			jjs.fPayoutMult = num;
		}
		return true;
	}

	private static string GetClosestStationId(CondOwner player)
	{
		if (player == null || player.ship == null)
		{
			return "";
		}
		Ship ship = player.ship;
		if (ship != null && !ship.IsStation())
		{
			Ship nearestStation = CrewSim.system.GetNearestStation(player.ship.objSS.vPosx, player.ship.objSS.vPosy);
			if (nearestStation != null && player.ship.GetRangeTo(nearestStation) < 3.342293553032505E-08 && !nearestStation.HideFromSystem)
			{
				ship = nearestStation;
			}
		}
		return ship.strRegID;
	}

	private static JsonJobSave MakeJob(string strJobName, List<string> aUsedClients)
	{
		if (string.IsNullOrEmpty(strJobName) || !DataHandler.dictJobs.ContainsKey(strJobName))
		{
			return null;
		}
		if (aUsedClients == null)
		{
			aUsedClients = new List<string>();
		}
		JsonJob job = DataHandler.GetJob(strJobName);
		if (job == null)
		{
			return null;
		}
		Interaction interaction = DataHandler.GetInteraction(job.strIASetupClient);
		if (interaction == null)
		{
			return null;
		}
		if (job.strPSpecClient == null)
		{
			return null;
		}
		PersonSpec person = StarSystem.GetPerson(DataHandler.GetPersonSpec(job.strPSpecClient), null, bForceUnrelated: false, aUsedClients);
		if (person == null)
		{
			return null;
		}
		CondOwner cO = person.GetCO();
		Social soc = null;
		if (cO != null)
		{
			soc = cO.socUs;
		}
		List<string> list = new List<string> { cO.strID };
		if (interaction.PSpecTestThem == null)
		{
			return null;
		}
		PersonSpec person2 = StarSystem.GetPerson(interaction.PSpecTestThem, soc, bForceUnrelated: false, list, interaction.ShipTestThem);
		if (person2 == null)
		{
			return null;
		}
		PersonSpec personSpec = null;
		if (interaction.PSpecTest3rd != null)
		{
			list.Add(person2.FullName);
			personSpec = StarSystem.GetPerson(interaction.PSpecTest3rd, soc, bForceUnrelated: false, list);
			if (personSpec == null)
			{
				return null;
			}
		}
		double num = MathUtils.Rand(job.fContractMin, job.fContractMax, MathUtils.RandType.Flat);
		double num2 = MathUtils.Rand(job.fPayoutMin, job.fPayoutMax, MathUtils.RandType.Flat);
		int num3 = 5;
		while (num3 >= 0 && num >= num2)
		{
			num3--;
			num = MathUtils.Rand(job.fContractMin, job.fContractMax, MathUtils.RandType.Flat);
			num2 = MathUtils.Rand(job.fPayoutMin, job.fPayoutMax, MathUtils.RandType.Flat);
		}
		if (num >= num2)
		{
			return null;
		}
		string randomText = GetRandomText(job.strLootRegIDsOrigin);
		string randomText2 = GetRandomText(job.strLootRegIDsDest);
		if (randomText != null && randomText == randomText2)
		{
			return null;
		}
		JsonJobSave jsonJobSave = new JsonJobSave();
		jsonJobSave.strJobName = job.strName;
		jsonJobSave.fCostContract = num;
		jsonJobSave.fPayout = num2;
		jsonJobSave.fEpochOfferExpired = StarSystem.fEpoch + 3600.0 * MathUtils.Rand(3.0, 6.0, MathUtils.RandType.Flat);
		if (personSpec != null)
		{
			jsonJobSave.str3rdID = personSpec.FullName;
		}
		if (person != null)
		{
			jsonJobSave.strClientID = person.FullName;
		}
		if (person2 != null)
		{
			jsonJobSave.strThemID = person2.FullName;
		}
		jsonJobSave.strTxt1 = GetRandomText(job.strLootTxt1);
		jsonJobSave.strRegIDPickup = randomText;
		jsonJobSave.strRegIDDropoff = randomText2;
		jsonJobSave.strJobItems = GetRandomText(job.strLootJobItems);
		if (jsonJobSave.strJobItems != null)
		{
			List<CondOwner> cOLoot = DataHandler.GetLoot(DataHandler.GetJobItems(jsonJobSave.strJobItems).strLootPickup).GetCOLoot(null, bSuppressOverride: false);
			double num4 = 0.0;
			foreach (CondOwner item in cOLoot)
			{
				num4 += item.GetTotalPrice(null, bIncludeStack: true);
				item.Destroy();
			}
			jsonJobSave.fItemValue = num4 * MathUtils.Rand(0.5, 1.5, MathUtils.RandType.Mid);
		}
		return jsonJobSave;
	}

	private static string GetRandomText(string strLoot)
	{
		Loot loot = DataHandler.GetLoot(strLoot);
		if (loot.strName != "Blank")
		{
			List<string> lootNames = loot.GetLootNames();
			if (lootNames.Count > 0)
			{
				return lootNames[0];
			}
		}
		return null;
	}
}
