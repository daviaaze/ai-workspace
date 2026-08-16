using System.Collections.Generic;
using System.Linq;
using Ostranauts.Core.Models;
using Ostranauts.Ships.Rooms;
using TMPro;
using UnityEngine;

public class Room
{
	private bool bVoid;

	public bool bOuter;

	public List<Tile> aTiles;

	private Tile[] aTilesRandom;

	private float fTimeLastTileShuffle;

	private float fTimeBetweenShuffles = 5f;

	private CondOwner coRoom;

	private TMP_Text txtID;

	private string strLastID;

	public UniqueList<CondOwner> aCos = new UniqueList<CondOwner>();

	public Dictionary<string, int> dictDoors = new Dictionary<string, int>();

	private static List<RoomSpec> aRmSpecs;

	private RoomSpec _roomSpec;

	public double RoomValue { get; private set; }

	public CondOwner CO
	{
		get
		{
			return coRoom;
		}
		set
		{
			if (!(value == null))
			{
				coRoom.currentRoom = null;
				coRoom.Destroy();
				coRoom = value;
				coRoom.currentRoom = this;
				strLastID = coRoom.strID;
				Void = coRoom.GetCondAmount("StatVolume") == 0.0;
				bOuter = false;
			}
		}
	}

	public bool Void
	{
		get
		{
			return bVoid;
		}
		set
		{
			if (bVoid && !value)
			{
				double condAmount = coRoom.GetCondAmount("StatVolume");
				coRoom.SetCondAmount("StatVolume", condAmount - 1E+99);
			}
			bVoid = value;
			if (bVoid)
			{
				coRoom.strName = DataHandler.GetString("ROOM_NAME_OUTSIDE");
				bool bFreezeConds = coRoom.bFreezeConds;
				coRoom.bFreezeConds = false;
				coRoom.SetCondAmount("StatVolume", 1E+99);
				coRoom.bFreezeConds = bFreezeConds;
			}
			else
			{
				coRoom.strName = DataHandler.GetString("ROOM_NAME_INSIDE");
				bOuter = false;
			}
		}
	}

	public bool IsAirless
	{
		get
		{
			if (!(CO == null))
			{
				return CO.HasCond("DcGasPressure01");
			}
			return true;
		}
	}

	public Room(CondOwner co = null)
	{
		if (co == null)
		{
			coRoom = DataHandler.GetCondOwner("Compartment");
		}
		else
		{
			coRoom = co;
		}
		coRoom.currentRoom = this;
		Void = false;
		bOuter = false;
		aTiles = new List<Tile>();
		if (CrewSim.bDebugShow)
		{
			txtID = Object.Instantiate(Resources.Load<TMP_Text>("prefabTextFloatUI"), coRoom.transform);
			txtID.text = coRoom.strNameFriendly + " " + coRoom.strID.Substring(0, 6);
			txtID.fontSize = 11f;
			txtID.gameObject.name = txtID.text;
		}
		strLastID = coRoom.strID;
	}

	public Tile GetRandomWalkableTile()
	{
		if (Time.realtimeSinceStartup - fTimeLastTileShuffle > fTimeBetweenShuffles || aTilesRandom == null)
		{
			aTilesRandom = aTiles.ToArray();
			MathUtils.ShuffleArray(aTilesRandom);
			fTimeLastTileShuffle = Time.realtimeSinceStartup;
		}
		Tile[] array = aTilesRandom;
		foreach (Tile tile in array)
		{
			if (tile.bPassable)
			{
				return tile;
			}
		}
		return null;
	}

	public RoomSpec GetRoomSpec()
	{
		if (_roomSpec != null)
		{
			return _roomSpec;
		}
		CreateRoomSpecs();
		return _roomSpec ?? (_roomSpec = DataHandler.dictRoomSpec["Blank"]);
	}

	public void SyncAtmoVoid(JsonAtmosphere jsonAtmosphere)
	{
		if (bVoid && !(coRoom == null) && !(coRoom.GasContainer == null))
		{
			coRoom.GasContainer.SyncAtmo(jsonAtmosphere);
		}
	}

	public void CreateRoomSpecs()
	{
		if (aRmSpecs == null)
		{
			aRmSpecs = new List<RoomSpec>(DataHandler.dictRoomSpec.Values).OrderByDescending((RoomSpec rs) => rs.nPriority).ToList();
		}
		foreach (RoomSpec aRmSpec in aRmSpecs)
		{
			if (aRmSpec != null && !aRmSpec.IsBlank && aRmSpec.Matches(this))
			{
				_roomSpec = aRmSpec;
				break;
			}
		}
		if (_roomSpec == null)
		{
			_roomSpec = DataHandler.dictRoomSpec["Blank"];
		}
		CalculateRoomValue();
	}

	public void RemoveTile(Tile til)
	{
		if (!(til == null))
		{
			aTiles.Remove(til);
			aTilesRandom = null;
		}
	}

	public void Destroy()
	{
		if (aTiles != null)
		{
			aTiles.Clear();
			aTiles = null;
		}
		if (coRoom != null)
		{
			coRoom.Destroy();
			coRoom = null;
		}
	}

	public JsonRoom GetJSONSave()
	{
		JsonRoom jsonRoom = new JsonRoom();
		jsonRoom.bVoid = bVoid;
		jsonRoom.strID = coRoom.strID;
		jsonRoom.roomSpec = ((_roomSpec != null) ? _roomSpec.strName : null);
		if (aCos != null)
		{
			List<int> list = new List<int>();
			for (int i = 0; i < aTiles.Count; i++)
			{
				list.Add(aTiles[i].Index);
			}
			jsonRoom.aTiles = list.ToArray();
		}
		jsonRoom.roomValue = RoomValue;
		return jsonRoom;
	}

	public override string ToString()
	{
		if (coRoom != null)
		{
			return "Room_" + coRoom.ToString();
		}
		return strLastID;
	}

	public void ShowID(bool bShow)
	{
		if (!(txtID == null))
		{
			txtID.gameObject.SetActive(bShow);
			if (bShow)
			{
				txtID.text = CO.strNameFriendly + "; Doors: " + dictDoors.Count + "; " + CO.strID.Substring(0, 6);
			}
		}
	}

	private void UpdateID()
	{
		if (txtID != null && txtID.gameObject.activeInHierarchy)
		{
			txtID.text = CO.strNameFriendly + "; Doors: " + dictDoors.Count + "; " + CO.strID.Substring(0, 6);
			strLastID = CO.strID;
		}
	}

	public void CalculateRoomValue()
	{
		RoomValue = 0.0;
		float num = ((_roomSpec != null) ? _roomSpec.ValueModifier : 1f);
		foreach (CondOwner aCo in aCos)
		{
			if (!(aCo == null) && !aCo.bDestroyed)
			{
				RoomValue += aCo.GetBasePrice() * (double)num;
			}
		}
	}

	public void AddToRoom(CondOwner co, bool addEffects = true)
	{
		if (co == null || CO == null || aCos.Contains(co))
		{
			return;
		}
		if (co.HasCond("IsInstalled", isThreshold: false))
		{
			aCos.Add(co);
			if (addEffects)
			{
				if (co.HasCond("IsModeSwitching", isThreshold: false))
				{
					co.ZeroCondAmount("IsModeSwitching");
				}
				else
				{
					CreateRoomSpecs();
				}
			}
		}
		if (addEffects)
		{
			AddEffectsToRoom(co);
		}
	}

	public void RemoveFromRoom(CondOwner co)
	{
		if (co == null || CO == null)
		{
			return;
		}
		if (aCos.Remove(co) && !co.HasCond("IsModeSwitching", isThreshold: false))
		{
			if (IsRoomSpecValid())
			{
				CalculateRoomValue();
			}
			else
			{
				CreateRoomSpecs();
			}
		}
		RemoveEffectsFromRoom(co);
	}

	private bool IsRoomSpecValid()
	{
		if (_roomSpec != null && !_roomSpec.IsBlank && _roomSpec.Matches(this))
		{
			return true;
		}
		return false;
	}

	private void AddEffectsToRoom(CondOwner co)
	{
		UpdateEffectsOnRoom(co, 1f);
	}

	private void RemoveEffectsFromRoom(CondOwner co)
	{
		UpdateEffectsOnRoom(co, -1f);
	}

	private void UpdateEffectsOnRoom(CondOwner co, float amount)
	{
		if (co == null)
		{
			return;
		}
		if (CO == null)
		{
			Debug.Log("ERROR: Removing effects from room with null CO!");
			Debug.Break();
			return;
		}
		if (CO == co)
		{
			Debug.Log("ERROR: Room removing effects from self!");
			return;
		}
		foreach (Condition value in co.mapConds.Values)
		{
			if (value.bRoom)
			{
				CO.AddCondAmount(value.strName, (double)amount * value.fCount);
			}
		}
		UpdateID();
	}

	public void ResetBorderCOCache()
	{
		if (!(CO == null) && !(CO.GasContainer == null))
		{
			CO.GasContainer.CachedBorderCOs.Clear();
		}
	}
}
