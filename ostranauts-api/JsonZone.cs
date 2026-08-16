using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class JsonZone : IComparable<JsonZone>
{
	public string strName { get; set; }

	public string strRegID { get; set; }

	public bool bTriggerOnOwner { get; set; }

	public int[] aTiles { get; set; }

	public int[] aOldTiles { get; set; }

	public string[] aTileConds { get; set; }

	public string[] categoryConds { get; set; }

	public string strPersonSpec { get; set; }

	public Color zoneColor { get; set; }

	public string strTargetPSpec { get; set; }

	public string[] ranks { get; set; }

	public void Destroy()
	{
		strName = null;
		strRegID = null;
		aTiles = null;
		aTileConds = null;
		strPersonSpec = null;
		strTargetPSpec = null;
		categoryConds = null;
	}

	public JsonZone Clone()
	{
		JsonZone obj = new JsonZone
		{
			strName = strName,
			strRegID = strRegID,
			bTriggerOnOwner = bTriggerOnOwner,
			aTiles = ((aTiles != null) ? ((int[])aTiles.Clone()) : new int[0]),
			aTileConds = ((aTileConds != null) ? ((string[])aTileConds.Clone()) : new string[0]),
			strPersonSpec = strPersonSpec,
			zoneColor = zoneColor
		};
		if (ranks != null)
		{
			if (ranks.Contains("IsPlayerCrew"))
			{
				strTargetPSpec = "ZoneCrew";
			}
			else if (ranks.Contains("IsPlayer"))
			{
				strTargetPSpec = "ZoneCaptain";
			}
			else
			{
				strTargetPSpec = "ZoneCaptainAndCrew";
			}
			ranks = null;
		}
		obj.strTargetPSpec = strTargetPSpec;
		obj.categoryConds = ((categoryConds != null) ? categoryConds : new string[0]);
		return obj;
	}

	public void RemoveTile(int nIndex, Ship objShip)
	{
		if (aTiles == null)
		{
			return;
		}
		List<int> list = new List<int>();
		for (int i = 0; i < aTiles.Length; i++)
		{
			if (aTiles[i] != nIndex)
			{
				list.Add(aTiles[i]);
			}
		}
		if (list.Count == 0)
		{
			objShip.mapZones.Remove(strName);
			return;
		}
		list.Sort();
		aTiles = list.ToArray();
	}

	public int CompareTo(JsonZone other)
	{
		if (other == null || other.categoryConds == null)
		{
			return -1;
		}
		if (categoryConds == null)
		{
			return 1;
		}
		int num = categoryConds.Length;
		int num2 = other.categoryConds.Length;
		if ((num == 1 && num2 != 1) || (num < num2 && num != 0) || (num > 1 && num2 == 0))
		{
			return -1;
		}
		if (num == num2)
		{
			return 0;
		}
		if (num == 0 || num > num2)
		{
			return 1;
		}
		return 0;
	}

	public bool Matches(CondOwner coTest, bool bCheckOwner)
	{
		if (coTest == null)
		{
			return true;
		}
		PersonSpec personSpec = null;
		if (strPersonSpec != null)
		{
			personSpec = StarSystem.GetPerson(DataHandler.GetPersonSpec(strPersonSpec), null, bForceUnrelated: false);
		}
		if (bCheckOwner && bTriggerOnOwner && (personSpec == null || personSpec.GetCO() == coTest))
		{
			return true;
		}
		if (string.IsNullOrEmpty(strTargetPSpec))
		{
			return true;
		}
		JsonPersonSpec personSpec2 = DataHandler.GetPersonSpec(strTargetPSpec);
		if (personSpec2 == null)
		{
			return true;
		}
		if (personSpec == null)
		{
			if (personSpec2.Matches(coTest))
			{
				return true;
			}
		}
		else if (personSpec.IsCOMyMother(personSpec2, coTest))
		{
			return true;
		}
		return false;
	}

	public override string ToString()
	{
		return strName;
	}

	internal void AddTiles(List<int> selectedTileIndices)
	{
		int[] array = aTiles;
		foreach (int item in array)
		{
			if (!selectedTileIndices.Contains(item))
			{
				selectedTileIndices.Add(item);
			}
		}
		aTiles = selectedTileIndices.ToArray();
	}

	internal void RemoveTiles(List<int> selectedTileIndices)
	{
		List<int> list = new List<int>();
		List<int> list2 = new List<int>();
		int[] array = aTiles;
		foreach (int item in array)
		{
			if (selectedTileIndices.Contains(item))
			{
				list2.Add(item);
			}
			else
			{
				list.Add(item);
			}
		}
		aTiles = list.ToArray();
		aOldTiles = list2.ToArray();
	}
}
