using System;
using System.Collections.Generic;
using UnityEngine;

public class Task2
{
	public enum Allowed
	{
		Owned,
		Allowed,
		Forbidden
	}

	public string strName;

	public string strDuty;

	public string strTargetCOID;

	public string strInteraction;

	public string strStatus = "";

	public string strCTTestThem;

	public string[] aOwnerIDs;

	private GameObject goConstructionSign;

	public Color clrTint;

	public float fTintBlend;

	public int nTile;

	public string strTileShip;

	private Interaction iact;

	public double fLastCheck;

	public bool bManual;

	public override string ToString()
	{
		return strName + ": " + strDuty + "; " + strInteraction;
	}

	public GameObject GetConstructionSign()
	{
		return goConstructionSign;
	}

	public void SetConstructionSign(GameObject goSign)
	{
		goConstructionSign = goSign;
	}

	public bool Matches(string strIA, string strTarget)
	{
		if (strIA == null || strTarget == null)
		{
			return false;
		}
		if (strIA == strInteraction)
		{
			return strTarget == strTargetCOID;
		}
		return false;
	}

	public Interaction GetIA()
	{
		return iact;
	}

	public void SetIA(Interaction ia)
	{
		iact = ia;
		if (ia != null && ia.CTTestThem != null)
		{
			strCTTestThem = ia.CTTestThem.strName;
		}
	}

	public string GetIconName()
	{
		string text = null;
		Interaction interaction = DataHandler.GetInteraction(strInteraction);
		if (interaction != null)
		{
			text = interaction.strMapIcon;
		}
		if (text == null || text == "")
		{
			text = "IcoConstructionSign";
		}
		return text;
	}

	public void CopyFrom(Task2 taskFrom)
	{
		if (taskFrom == null)
		{
			return;
		}
		if (taskFrom.aOwnerIDs == null)
		{
			aOwnerIDs = null;
		}
		else
		{
			aOwnerIDs = new string[taskFrom.aOwnerIDs.Length];
			for (int i = 0; i < taskFrom.aOwnerIDs.Length; i++)
			{
				aOwnerIDs[i] = taskFrom.aOwnerIDs[i];
			}
		}
		bManual = taskFrom.bManual;
	}

	public Allowed GetOwnership(string strID)
	{
		if (aOwnerIDs == null || aOwnerIDs.Length == 0)
		{
			return Allowed.Allowed;
		}
		if (strID == null || Array.IndexOf(aOwnerIDs, strID) < 0)
		{
			return Allowed.Forbidden;
		}
		return Allowed.Owned;
	}

	public void AddOwner(string strID)
	{
		if (strID != null)
		{
			List<string> list = null;
			list = ((aOwnerIDs == null) ? new List<string>() : new List<string>(aOwnerIDs));
			if (list.IndexOf(strID) < 0)
			{
				list.Add(strID);
			}
			aOwnerIDs = list.ToArray();
		}
	}

	public void RemoveOwner(string strID)
	{
		if (strID != null && aOwnerIDs != null && Array.IndexOf(aOwnerIDs, strID) >= 0)
		{
			List<string> list = new List<string>(aOwnerIDs);
			list.Remove(strID);
			aOwnerIDs = list.ToArray();
		}
	}

	public void ClearOwners()
	{
		if (aOwnerIDs != null && aOwnerIDs.Length != 0)
		{
			aOwnerIDs = new string[0];
		}
	}

	public void UpdateTint(float blendLoss)
	{
		GameObject constructionSign = GetConstructionSign();
		if (!(constructionSign == null))
		{
			MeshRenderer component = constructionSign.GetComponent<MeshRenderer>();
			if (!(component == null))
			{
				fTintBlend = Mathf.Clamp01(fTintBlend - blendLoss);
				Color value = Color.Lerp(Color.white, clrTint, fTintBlend);
				MaterialPropertyBlock materialPropertyBlock = new MaterialPropertyBlock();
				component.GetPropertyBlock(materialPropertyBlock);
				materialPropertyBlock.SetColor("_Color", value);
				component.SetPropertyBlock(materialPropertyBlock);
			}
		}
	}

	public Interaction AssignHaulZone(CondOwner coHauler, CondOwner coTarget)
	{
		if (coHauler == null || coTarget == null)
		{
			return null;
		}
		if (!WorkManager.CTHaul.Triggered(coTarget))
		{
			return null;
		}
		List<JsonZone> zones = coHauler.ship.GetZones("IsZoneStockpile", coHauler, bAllowDocked: true);
		if (zones == null || zones.Count == 0)
		{
			return null;
		}
		zones.Sort();
		foreach (JsonZone item in zones)
		{
			Ship value = null;
			if (item.strRegID == null || !CrewSim.system.dictShips.TryGetValue(item.strRegID, out value))
			{
				continue;
			}
			if (item.categoryConds != null && item.categoryConds.Length != 0)
			{
				bool flag = false;
				for (int i = 0; i < item.categoryConds.Length; i++)
				{
					if (flag)
					{
						break;
					}
					flag = coTarget.HasCond(item.categoryConds[i]);
				}
				if (!flag)
				{
					continue;
				}
			}
			foreach (CondOwner item2 in value.GetCOsInZone(item, Ship.CtHaulDest, bAllowLocked: false))
			{
				if (item2.CanStackOnItem(coTarget) != 0)
				{
					nTile = -1;
					Tile tileAtWorldCoords = value.GetTileAtWorldCoords1(item2.tf.position.x, item2.tf.position.y, bAllowDocked: true);
					nTile = tileAtWorldCoords.Index;
					strTileShip = tileAtWorldCoords.coProps.ship.strRegID;
					if (nTile >= 0)
					{
						return DataHandler.GetInteraction(strInteraction);
					}
				}
			}
			if (TileUtils.TryFitItem(coTarget.Item, value, item, out var vFits))
			{
				nTile = -1;
				Tile tileAtWorldCoords2 = value.GetTileAtWorldCoords1(vFits.x, vFits.y, bAllowDocked: true);
				nTile = tileAtWorldCoords2.Index;
				strTileShip = tileAtWorldCoords2.coProps.ship.strRegID;
				if (nTile >= 0)
				{
					return DataHandler.GetInteraction(strInteraction);
				}
			}
		}
		coHauler.LogMessage("Could not find a zone with matching category for " + coTarget.strNameFriendly, "Bad", coHauler.strName);
		return null;
	}
}
