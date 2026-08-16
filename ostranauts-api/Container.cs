using System.Collections.Generic;
using System.Text;
using Ostranauts.Core.Models;
using Ostranauts.Inventory;
using UnityEngine;

public class Container : MonoBehaviour
{
	public static float fZSubOffset = 0.1f;

	private TrackingCollection<CondOwner> aCOs = new TrackingCollection<CondOwner>();

	private CondOwner co;

	public CondTrigger ctAllowed;

	public bool bAllowStacking = true;

	public GridLayout gridLayout = new GridLayout(6, 6);

	public ICollection<CondOwner> ContainedCOs => aCOs;

	public GUIInventoryWindow InventoryWindow
	{
		get
		{
			foreach (GUIInventoryWindow activeWindow in CrewSim.inventoryGUI.activeWindows)
			{
				if (activeWindow.CO == CO && activeWindow.type == InventoryWindowType.Container)
				{
					return activeWindow;
				}
			}
			return null;
		}
	}

	public CondOwner CO
	{
		get
		{
			if (co == null)
			{
				co = GetComponent<CondOwner>();
				aCOs.Track(delegate(bool any)
				{
					if (co != null)
					{
						co.HasSubCOs = any;
					}
				});
			}
			return co;
		}
	}

	public bool Locked => CO.HasCond("IsLocked");

	public void Destroy()
	{
		for (int num = aCOs.Count - 1; num >= 0; num--)
		{
			aCOs[num].Destroy();
		}
		aCOs.Clear();
		aCOs = null;
		ctAllowed = null;
		gridLayout = null;
		co = null;
	}

	public bool AllowedCO(CondOwner coIn)
	{
		if (coIn == null || coIn == CO)
		{
			return false;
		}
		CondOwner objCOParent = CO.objCOParent;
		while (objCOParent != null)
		{
			if (coIn == objCOParent)
			{
				return false;
			}
			objCOParent = objCOParent.objCOParent;
		}
		if (ctAllowed != null)
		{
			return ctAllowed.Triggered(coIn);
		}
		return true;
	}

	private CondOwner StackOnInsideItem(CondOwner coIncoming)
	{
		if (!bAllowStacking)
		{
			return coIncoming;
		}
		CondOwner condOwner = coIncoming;
		foreach (CondOwner aCO in aCOs)
		{
			condOwner = aCO.StackCO(coIncoming);
			if (condOwner != coIncoming)
			{
				break;
			}
		}
		for (int num = aCOs.Count - 1; num >= 0; num--)
		{
			CondOwner condOwner2 = aCOs[num];
			if (!(condOwner2.coStackHead == null) && Contains(condOwner2.coStackHead) && condOwner2.coStackHead.StackAsList.Contains(condOwner2))
			{
				aCOs.Remove(condOwner2);
				CO.AddMass(0.0 - condOwner2.GetTotalMass());
			}
		}
		return condOwner;
	}

	public static int GetSpace(CondOwner co)
	{
		if (co == null)
		{
			return 0;
		}
		if (co.Item != null)
		{
			return co.Item.nWidthInTiles * co.Item.nHeightInTiles;
		}
		return 1;
	}

	public bool CanFit(CondOwner coFit, bool bAuto, bool bSub, bool bAllowLocked)
	{
		if (!bAllowLocked && co.HasCond("IsLocked"))
		{
			return false;
		}
		int num = 0;
		if (ctAllowed == null || ctAllowed.Triggered(coFit))
		{
			if (CO.HasCond("IsInfiniteContainer"))
			{
				return true;
			}
			num = gridLayout.gridMaxSpace;
		}
		int num2 = 0;
		foreach (CondOwner aCO in aCOs)
		{
			if (aCO.coStackHead != null)
			{
				continue;
			}
			if (aCO.StackCount < aCO.nStackLimit)
			{
				if (aCO.CanStackOnItem(coFit) == 0)
				{
					num2 += GetSpace(aCO);
				}
			}
			else
			{
				num2 += GetSpace(aCO);
			}
			if (!bSub)
			{
				continue;
			}
			if (aCO.compSlots != null)
			{
				foreach (Slot item in aCO.compSlots.GetSlotsHeldFirst(bDeep: false))
				{
					if (item.CanFit(coFit, bAuto, bSub, checkStacks: false, bAllowLocked))
					{
						return true;
					}
				}
			}
			if (aCO.objContainer != null && aCO.objContainer.CanFit(coFit, bAuto, bSub, bAllowLocked))
			{
				return true;
			}
		}
		return num > num2;
	}

	public CondOwner AddCO(CondOwner objCO)
	{
		if (objCO == null || objCO.bDestroyed)
		{
			Debug.Log("Container.AddCO(), trying to add CO that is null or destroyed. This should probably crash");
			return null;
		}
		if (objCO.coStackHead != null)
		{
			Debug.Log("Container.AddCO(), Trying to add a CO that's not a stackhead. This is probably a logic error in the caller.");
			return null;
		}
		if (aCOs.IndexOf(objCO) >= 0)
		{
			Debug.Log("ERROR: Trying to add a CondOwner that's already been added");
			Debug.Break();
			return null;
		}
		if (AllowedCO(objCO))
		{
			objCO = StackOnInsideItem(objCO);
			if (objCO == null)
			{
				Redraw();
				return null;
			}
			if (CanAddSimple(objCO, out var pairXY))
			{
				AddCOSimple(objCO, pairXY);
				objCO = null;
			}
			Redraw();
			if (objCO == null)
			{
				return objCO;
			}
		}
		CondOwner condOwner = objCO;
		foreach (CondOwner aCO in aCOs)
		{
			condOwner = aCO.AddCO(condOwner, bEquip: false, bOverflow: true, bIgnoreLocks: false);
			if (condOwner == null)
			{
				break;
			}
		}
		return condOwner;
	}

	public void SetIsInContainer(CondOwner co)
	{
		if (CO == this)
		{
			Debug.Log("ERROR: Assigning self as own parent.");
		}
		co.objCOParent = CO;
		if (co.coStackHead == null)
		{
			co.tf.SetParent(CO.tf);
			co.tf.localPosition = new Vector3(0f, 0f, fZSubOffset);
			co.Visible = false;
		}
		if (!CO.HasCond("IsHuman"))
		{
			co.AddCondAmount("IsInContainer", 1.0);
		}
		CondOwner condOwner = CO;
		while (condOwner != null)
		{
			if (condOwner.HasCond("IsHuman") || condOwner.HasCond("IsRobot"))
			{
				co.AddCondAmount("IsCarried", 1.0);
				CondOwnerVisitorAddCond condOwnerVisitorAddCond = new CondOwnerVisitorAddCond();
				condOwnerVisitorAddCond.strCond = "IsCarried";
				condOwnerVisitorAddCond.fAmount = 1.0;
				co.VisitCOs(condOwnerVisitorAddCond, bAllowLocked: true);
				break;
			}
			condOwner = condOwner.objCOParent;
		}
	}

	public void ClearIsInContainer(CondOwner co)
	{
		co.ZeroCondAmount("IsInContainer");
		co.ZeroCondAmount("IsCarried");
		CondOwnerVisitorZeroCond condOwnerVisitorZeroCond = new CondOwnerVisitorZeroCond();
		condOwnerVisitorZeroCond.strCond = "IsCarried";
		co.VisitCOs(condOwnerVisitorZeroCond, bAllowLocked: true);
		co.objCOParent = null;
	}

	public bool CanAddSimple(CondOwner objCO, out PairXY pairXY)
	{
		if (Contains(objCO))
		{
			Debug.Log("Trying to add a CO to a container, but it's already here!");
			pairXY = PairXY.GetInvalid();
			return false;
		}
		if (CO.HasCond("IsInfiniteContainer"))
		{
			pairXY = PairXY.GetInvalid();
			return true;
		}
		PairXY widthHeightForCO = GUIInventoryItem.GetWidthHeightForCO(objCO);
		int x = widthHeightForCO.x;
		int y = widthHeightForCO.y;
		pairXY = gridLayout.FindFirstUnoccupiedTile(x, y, objCO.strID);
		return pairXY.IsValid();
	}

	public void AddCOList(CondOwner objCO)
	{
		if (!aCOs.Contains(objCO))
		{
			aCOs.Add(objCO);
		}
	}

	public void AddCOSimple(CondOwner objCO, PairXY pairXY)
	{
		if (objCO == null)
		{
			return;
		}
		if (objCO.coStackHead != null)
		{
			Debug.Log("Container.AddCOSimple(), Trying to add a CO that's not a stackhead. This is probably a logic error in the caller.");
			return;
		}
		objCO.ValidateParent();
		aCOs.Insert(objCO);
		SetIsInContainer(objCO);
		if (pairXY.IsValid())
		{
			objCO.pairInventoryXY = pairXY;
			foreach (CondOwner item in objCO.aStack)
			{
				item.pairInventoryXY = pairXY;
			}
			PairXY widthHeightForCO = GUIInventoryItem.GetWidthHeightForCO(objCO);
			int x = widthHeightForCO.x;
			int y = widthHeightForCO.y;
			for (int i = pairXY.y; i < pairXY.y + y; i++)
			{
				for (int j = pairXY.x; j < pairXY.x + x; j++)
				{
					if (j >= 0 && i >= 0 && j < gridLayout.gridMaxX && i < gridLayout.gridMaxY)
					{
						gridLayout.gridID[j, i] = objCO.strID;
					}
				}
			}
		}
		foreach (CondOwner item2 in objCO.aStack)
		{
			SetIsInContainer(item2);
			item2.ship = CO.ship;
		}
		co.AddMass(objCO.GetTotalMass());
		objCO.strSourceCO = null;
		objCO.strSourceInteract = null;
		if (CO.ship != null)
		{
			CO.ship.AddCO(objCO, bTiles: false);
		}
		objCO.ValidateParent();
	}

	public void RemoveCOSimple(CondOwner objCO)
	{
		if (objCO == null)
		{
			return;
		}
		objCO.ValidateParent();
		if (objCO.objCOParent.ship != null)
		{
			objCO.objCOParent.ship.RemoveCO(objCO);
		}
		aCOs.Remove(objCO);
		ClearIsInContainer(objCO);
		objCO.tf.SetParent(null);
		if (objCO.Item != null)
		{
			objCO.Item.ResetTransforms(CO.tf.position.x, CO.tf.position.y);
		}
		foreach (CondOwner item in objCO.aStack)
		{
			ClearIsInContainer(item);
			item.ship = null;
		}
		gridLayout.Remove(objCO.strID);
		CO.AddMass(0.0 - objCO.GetTotalMass());
		objCO.ValidateParent();
	}

	public CondOwner RemoveCO(CondOwner objCO, bool bForce = false)
	{
		if (objCO == null || aCOs.Count == 0)
		{
			return null;
		}
		if (objCO.objCOParent == CO)
		{
			objCO.tf.position = CO.tf.position;
			RemoveCOSimple(objCO);
			foreach (CondOwner item in objCO.aStack)
			{
				aCOs.Remove(item);
				if (item.objCOParent != objCO && item.objCOParent != null)
				{
					Debug.Log("ERROR: Item in " + objCO.strName + " stack has different CO parent: " + item.objCOParent);
					continue;
				}
				ClearIsInContainer(item);
				item.tf.position = CO.tf.position;
			}
			CrewSim.inventoryGUI.RemoveAndDestroy(objCO.strID);
			return objCO;
		}
		foreach (CondOwner aCO in aCOs)
		{
			CondOwner condOwner = aCO.RemoveCO(objCO, bForce);
			if (condOwner != null)
			{
				return condOwner;
			}
		}
		return null;
	}

	public CondOwner GetCORef(CondOwner co)
	{
		if (this == null)
		{
			Debug.Log("ERROR: Getting CO from a null");
			Debug.Break();
			return null;
		}
		if (co == null)
		{
			return null;
		}
		foreach (CondOwner aCO in aCOs)
		{
			if (aCO == co)
			{
				return aCO;
			}
			CondOwner cORef = aCO.GetCORef(co);
			if (cORef != null)
			{
				return cORef;
			}
		}
		return null;
	}

	public void VisitCOs(CondOwnerVisitor visitor, bool bAllowLocked)
	{
		if (!bAllowLocked && CO.HasCond("IsLocked"))
		{
			return;
		}
		foreach (CondOwner aCO in aCOs)
		{
			if (!(aCO == null))
			{
				visitor.Visit(aCO);
				aCO.VisitCOs(visitor, bAllowLocked);
			}
		}
	}

	public List<CondOwner> GetCOs(bool bAllowLocked, CondTrigger objCondTrig = null)
	{
		CondOwnerVisitorAddToHashSet condOwnerVisitorAddToHashSet = new CondOwnerVisitorAddToHashSet();
		CondOwnerVisitor visitor = CondOwnerVisitorCondTrigger.WrapVisitor(condOwnerVisitorAddToHashSet, objCondTrig);
		VisitCOs(visitor, bAllowLocked);
		return new List<CondOwner>(condOwnerVisitorAddToHashSet.aHashSet);
	}

	public string GetAltImageMatch(Dictionary<string, string> mapAltImages)
	{
		if (mapAltImages == null || mapAltImages.Keys.Count == 0 || aCOs.Count == 0)
		{
			return null;
		}
		foreach (CondOwner aCO in aCOs)
		{
			foreach (string key in mapAltImages.Keys)
			{
				if (aCO.HasCond(key))
				{
					return mapAltImages[key];
				}
			}
		}
		return null;
	}

	public bool Contains(CondOwner co)
	{
		return aCOs.IndexOf(co) >= 0;
	}

	public void DebugInv(StringBuilder sb)
	{
		sb.AppendLine(CO.strID + " contains:");
		foreach (CondOwner aCO in aCOs)
		{
			sb.AppendLine(CO.strID + "->" + aCO.strID + ".bDestroyed = " + aCO.bDestroyed);
			aCO.DebugInv(sb, CO.strID + "->");
		}
	}

	public double DebugAuditMass(string strPrefix, bool bFix)
	{
		double num = 0.0;
		foreach (CondOwner aCO in aCOs)
		{
			num += aCO.DebugAuditMass(strPrefix + "\t", bFix);
		}
		return num;
	}

	public static void Redraw(Container container)
	{
		if (container != null)
		{
			container.Redraw();
		}
	}

	public void Redraw()
	{
		if (co == null)
		{
			return;
		}
		GUIInventoryWindow inventoryWindow = InventoryWindow;
		if (inventoryWindow != null)
		{
			List<CondOwner> cOs = GetCOs(bAllowLocked: true);
			List<string> list = new List<string>();
			foreach (CondOwner item in cOs)
			{
				if (!(item.coStackHead != null) && !item.HasCond("IsHiddenInv"))
				{
					if (item.objCOParent == CO)
					{
						list.Add(item.strID);
					}
					if (item.objContainer != null)
					{
						item.objContainer.Redraw();
					}
				}
			}
			list.Sort(delegate(string csA, string csB)
			{
				DataHandler.mapCOs.TryGetValue(csA, out var value);
				DataHandler.mapCOs.TryGetValue(csB, out var value2);
				return GetSpace(value2).CompareTo(GetSpace(value));
			});
			inventoryWindow.RedrawWindowContents(list);
		}
		if (co.slotNow != null && Slots.OnSlotContentUpdated != null)
		{
			Slots.OnSlotContentUpdated.Invoke(co, null);
		}
		co.UpdateAppearance();
	}
}
