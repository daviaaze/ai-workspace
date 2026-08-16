using System;
using System.Collections.Generic;
using System.Linq;
using Ostranauts.Core.Models;
using Ostranauts.Inventory;
using Ostranauts.UI.MegaToolTip;
using UnityEngine;
using UnityEngine.Events;

public class Item : MonoBehaviour
{
	public static readonly UnityEvent ItemAnimationUpdate = new UnityEvent();

	public Renderer rend;

	public JsonItemDef jid;

	public int nWidthInTiles = 1;

	public int nHeightInTiles = 1;

	public bool bPlaceholder;

	public bool bHasSpriteSheet;

	public CondTrigger ctSpriteSheet;

	private Vector3 vScale = new Vector3(1f, 1f, 1f);

	private float fRotLast;

	private int nSheetIndex;

	private string strImgOverride;

	private string strImgNormOverride;

	private string strImgDamagedOverride;

	private string strDmgColorOverride;

	private bool bBlink;

	public List<Visibility> aLights;

	public Dictionary<Transform, Vector2> dictLightSprites;

	private List<Renderer> aLightRenderers;

	public float fFlickerAmount = 1f;

	private MaterialPropertyBlock mpbLights;

	public List<Block> aBlocks;

	public Renderer IsNotification;

	private static Dictionary<int, int> mapSpriteSheetIndices;

	public static Color rgbFit = new Color(0.2f, 0.6f, 1f, 0.2f);

	public static Color rgbUnfit = new Color(1f, 0.2f, 0.2f, 0.2f);

	public static string strFit = "GUIGrid16Horiz";

	public static string strUnfit = "GUIGrid16Diag";

	public List<Loot> aSocketReqs;

	public List<Loot> aSocketForbids;

	public List<Loot> aSocketAdds;

	public static List<Item> aPreRender = new List<Item>();

	private Transform _tf;

	private CondOwner _co;

	private BoxCollider _bc;

	private static readonly List<Visibility> _aLightsDefault = new List<Visibility>();

	private static readonly List<Renderer> _aRendsDefault = new List<Renderer>();

	private static readonly Dictionary<Transform, Vector2> _dictLightSpritesDefault = new Dictionary<Transform, Vector2>();

	private static readonly List<Loot> _aLootsDefault = new List<Loot>();

	private static readonly List<Block> _aBlocksDefault = new List<Block>();

	private MaterialPropertyBlock _mpb;

	private Vector4 _vShaderOffset;

	private float _fOverlayMode;

	private float _fOverlayPriority;

	private float _fOverlayAmount;

	private float _fOverlayBlend;

	private bool _fieldsInitialized;

	private Ship _ship;

	private float _fShaderOverlayLastFrame;

	private Vector4 _vShaderOffsetLastFrame;

	private RenderOverlayMode _overlayModeLastFrame;

	private ItemAnimationDTO _itemAnimation;

	private float _animationTimer;

	private bool _ShowNotification
	{
		get
		{
			if (IsNotification == null)
			{
				return false;
			}
			if (_ship == null)
			{
				CondOwner componentInParent = GetComponentInParent<CondOwner>();
				if (componentInParent != null)
				{
					_ship = componentInParent.ship;
				}
			}
			if (_ship != null && _ship.Comms != null)
			{
				return _ship.Comms.HasUnreadMessage();
			}
			return false;
		}
	}

	public int SpriteSheetIndex => nSheetIndex;

	public float ZScale => vScale.z;

	public string ImgOverride => strImgOverride;

	private static Dictionary<int, int> SpriteSheetIndices
	{
		get
		{
			if (mapSpriteSheetIndices == null)
			{
				mapSpriteSheetIndices = new Dictionary<int, int>
				{
					{ 3, 12 },
					{ 7, 13 },
					{ 5, 14 },
					{ 8, 15 },
					{ 11, 8 },
					{ 15, 9 },
					{ 13, 10 },
					{ 2, 11 },
					{ 10, 4 },
					{ 14, 5 },
					{ 12, 6 },
					{ 4, 7 },
					{ 6, 0 },
					{ 0, 1 },
					{ 9, 2 },
					{ 1, 3 }
				};
			}
			return mapSpriteSheetIndices;
		}
	}

	public float fLastRotation
	{
		get
		{
			return fRotLast;
		}
		set
		{
			while (!bHasSpriteSheet && !(Mathf.Abs(MathUtils.NormalizeAngleDegrees(180f + value - fRotLast) - 180f) <= 45f))
			{
				RotateCW();
			}
		}
	}

	public Transform TF
	{
		get
		{
			if (_tf == null)
			{
				_tf = base.transform;
			}
			return _tf;
		}
	}

	public CondOwner CO
	{
		get
		{
			if (_co == null)
			{
				_co = GetComponent<CondOwner>();
			}
			return _co;
		}
	}

	public BoxCollider BoxCollider
	{
		get
		{
			if (_bc == null)
			{
				_bc = GetComponent<BoxCollider>();
			}
			return _bc;
		}
	}

	public void Awake()
	{
		_mpb = new MaterialPropertyBlock();
		_fieldsInitialized = true;
	}

	public void VisualizeOverlays(bool force = false)
	{
		CondOwner cO = CO;
		if (rend == null || cO == null)
		{
			return;
		}
		_fOverlayMode = (float)GUIPDA.instance.pdaVisualisers.Gradient;
		_fOverlayPriority = 0f;
		_fOverlayAmount = 0f;
		_fOverlayBlend = GUIPDA.instance.pdaVisualisers.Opacity;
		Room room = null;
		string overlayVariable = GUIPDA.instance.pdaVisualisers.OverlayVariable;
		if (overlayVariable[0] == '_')
		{
			switch (overlayVariable)
			{
			case "_None":
				_fOverlayMode = 0f;
				break;
			case "_Price":
				_fOverlayAmount = (float)cO.GetBasePrice();
				_fOverlayAmount = GUIPDA.instance.pdaVisualisers.InverseLerp(_fOverlayAmount);
				break;
			case "_Damage":
				_fOverlayAmount = cO.GetDamageRate();
				if (cO.HasCond("IsDamaged"))
				{
					_fOverlayPriority = 1f;
					_fOverlayAmount = 1f;
				}
				break;
			case "_Heat":
				_fOverlayAmount = (float)cO.GetCondAmount("StatSolidTemp");
				_fOverlayAmount = Mathf.Max(_fOverlayAmount, (float)cO.GetCondAmount("StatGasTemp"));
				room = null;
				if (cO.ship != null)
				{
					room = cO.ship.GetRoomAtWorldCoords1(cO.transform.position, bAllowDocked: true);
				}
				if (room != null && room.CO != null)
				{
					_fOverlayAmount = Mathf.Max(_fOverlayAmount, (float)room.CO.GetCondAmount("StatGasTemp"));
				}
				_fOverlayAmount = GUIPDA.instance.pdaVisualisers.InverseLerp(_fOverlayAmount);
				break;
			case "_Mass":
				_fOverlayAmount = (float)cO.GetTotalMass();
				_fOverlayAmount = GUIPDA.instance.pdaVisualisers.InverseLerp(_fOverlayAmount);
				break;
			case "_Pressure":
				room = null;
				if (cO.ship != null)
				{
					room = cO.ship.GetRoomAtWorldCoords1(cO.transform.position, bAllowDocked: true);
				}
				if (room != null && room.CO != null)
				{
					_fOverlayAmount = (float)room.CO.GetCondAmount("StatGasPressure");
				}
				if (cO.GetCondAmount("StatGasPressure") > 0.0)
				{
					_fOverlayAmount = (float)cO.GetCondAmount("StatGasPressure");
				}
				_fOverlayAmount = GUIPDA.instance.pdaVisualisers.InverseLerp(_fOverlayAmount);
				break;
			case "_Power":
				if (cO.HasCond("IsPowered"))
				{
					_fOverlayAmount = 1f;
				}
				break;
			default:
				Debug.LogWarning("Overlay variable not recognised! rendering scene like normal!");
				_fOverlayMode = 0f;
				break;
			}
		}
		else
		{
			_fOverlayAmount = GUIPDA.instance.pdaVisualisers.InverseLerp((float)cO.GetCondAmount(overlayVariable));
		}
		if (_fOverlayMode == 0f)
		{
			_fOverlayAmount = cO.GetDamageRate();
		}
		_vShaderOffset = new Vector4(cO.tf.position.x, cO.tf.position.y, ZScale, 0f);
		if (force || !((double)Math.Abs(_fOverlayAmount - _fShaderOverlayLastFrame) < 0.001) || !(_vShaderOffsetLastFrame == _vShaderOffset))
		{
			rend.GetPropertyBlock(_mpb);
			_mpb.SetFloat("_OverlayAmount", _fOverlayAmount);
			_mpb.SetVector("_PositionOffset", _vShaderOffset);
			_mpb.SetFloat("_OverlayPriority", _fOverlayPriority);
			_mpb.SetFloat("_OverlayMode", _fOverlayMode);
			_mpb.SetFloat("_OverlayBlend", _fOverlayBlend);
			rend.SetPropertyBlock(_mpb);
			_fShaderOverlayLastFrame = _fOverlayAmount;
			_vShaderOffsetLastFrame = _vShaderOffset;
		}
	}

	private void SetupAnimation(JsonItemAnimation jAnim)
	{
		_itemAnimation = new ItemAnimationDTO(jAnim);
		if (jAnim.bRandomStartingFrame)
		{
			nSheetIndex = UnityEngine.Random.Range(0, _itemAnimation.FrameCount / 2) * 2;
		}
		int nIndex = ConvertArrayIndexToTopLeftIndex(nSheetIndex, _itemAnimation.Columns, _itemAnimation.Rows);
		rend.sharedMaterial = DataHandler.GetMaterialSheet(rend, strImgOverride, nIndex, strImgNormOverride, strImgDamagedOverride, strDmgColorOverride, nWidthInTiles, nHeightInTiles);
		float num = 1f * (float)rend.sharedMaterial.GetTexture("_MainTex").width / (float)_itemAnimation.Columns;
		float num2 = 1f * (float)rend.sharedMaterial.GetTexture("_MainTex").height / (float)_itemAnimation.Rows;
		vScale.x = Mathf.Max(MathUtils.RoundToInt(num / 16f), 1);
		vScale.y = Mathf.Max(MathUtils.RoundToInt(num2 / 16f), 1);
		ItemAnimationUpdate.AddListener(OnItemAnimationUpdate);
	}

	public void SetData(string strName, float fX, float fY)
	{
		if (!_fieldsInitialized)
		{
			Awake();
		}
		bool bIsWall = false;
		aLights = _aLightsDefault;
		aLightRenderers = _aRendsDefault;
		dictLightSprites = _dictLightSpritesDefault;
		fFlickerAmount = 1f;
		aSocketAdds = _aLootsDefault;
		aSocketReqs = _aLootsDefault;
		aSocketForbids = _aLootsDefault;
		aPreRender.Remove(this);
		rend = base.gameObject.GetComponent<Renderer>();
		jid = DataHandler.GetItemDef(strName);
		if (jid == null)
		{
			Debug.Log("null jid setting data on: " + strName);
			return;
		}
		bBlink = jid.bBlink;
		strImgOverride = jid.strImg;
		strImgNormOverride = jid.strImgNorm;
		strImgDamagedOverride = jid.strImgDamaged;
		if (strImgDamagedOverride == "" || strImgDamagedOverride == null)
		{
			strImgDamagedOverride = "blank";
		}
		strDmgColorOverride = jid.strDmgColor;
		if (string.IsNullOrEmpty(strDmgColorOverride))
		{
			strDmgColorOverride = "blank";
		}
		vScale.z = jid.fZScale;
		string[] array = jid.aSocketAdds;
		foreach (string text in array)
		{
			if (aSocketAdds == _aLootsDefault)
			{
				aSocketAdds = new List<Loot>();
			}
			if (text == "TILWallAdds")
			{
				bIsWall = true;
			}
			aSocketAdds.Add(DataHandler.GetLoot(text));
		}
		array = jid.aSocketReqs;
		foreach (string strName2 in array)
		{
			if (aSocketReqs == _aLootsDefault)
			{
				aSocketReqs = new List<Loot>();
			}
			aSocketReqs.Add(DataHandler.GetLoot(strName2));
		}
		array = jid.aSocketForbids;
		foreach (string strName3 in array)
		{
			if (aSocketForbids == _aLootsDefault)
			{
				aSocketForbids = new List<Loot>();
			}
			aSocketForbids.Add(DataHandler.GetLoot(strName3));
		}
		bHasSpriteSheet = jid.bHasSpriteSheet;
		if (jid.ctSpriteSheet != null)
		{
			ctSpriteSheet = DataHandler.GetCondTrigger(jid.ctSpriteSheet);
		}
		nWidthInTiles = jid.nCols;
		nHeightInTiles = aSocketAdds.Count / jid.nCols;
		if (jid.objAnimation != null)
		{
			SetupAnimation(jid.objAnimation);
		}
		else if (bHasSpriteSheet)
		{
			rend.sharedMaterial = DataHandler.GetMaterialSheet(rend, strImgOverride, 0, strImgNormOverride, strImgDamagedOverride, strDmgColorOverride);
			vScale.x = (vScale.y = 1f);
		}
		else
		{
			rend.sharedMaterial = DataHandler.GetMaterial(rend, strImgOverride, strImgNormOverride, strImgDamagedOverride, strDmgColorOverride);
			vScale.x = Mathf.Max(MathUtils.RoundToInt(1f * (float)rend.sharedMaterial.GetTexture("_MainTex").width / 16f), 1);
			vScale.y = Mathf.Max(MathUtils.RoundToInt(1f * (float)rend.sharedMaterial.GetTexture("_MainTex").height / 16f), 1);
		}
		rend.sharedMaterial.renderQueue = 2000 + MathUtils.RoundToInt(ZScale * 100f);
		rend.sharedMaterial.SetVector("_Aspect", new Vector4(nWidthInTiles, nHeightInTiles, rend.sharedMaterial.GetTexture("_MainTex").width, rend.sharedMaterial.GetTexture("_MainTex").height));
		if (jid.fDmgComplexity != 0f)
		{
			rend.sharedMaterial.SetFloat("_Complexity", jid.fDmgComplexity);
		}
		if (jid.fDmgIntensity != 0f)
		{
			rend.sharedMaterial.SetFloat("_Intensity", jid.fDmgIntensity);
		}
		if (jid.fDmgCut != -999f)
		{
			rend.sharedMaterial.SetFloat("_Cut", jid.fDmgCut);
		}
		if (jid.fDmgTrim != -999f)
		{
			rend.sharedMaterial.SetFloat("_Trim", jid.fDmgTrim);
		}
		if (!jid.bLerp)
		{
			rend.sharedMaterial.SetFloat("_Lerp", 0f);
		}
		if (!jid.bSinew)
		{
			rend.sharedMaterial.SetFloat("_Sinew", 0f);
		}
		switch (jid.nDmgMode)
		{
		case 1:
			rend.sharedMaterial.SetFloat("_DmgPassThrough", 1f);
			rend.sharedMaterial.SetFloat("_DmgExtend", 0f);
			break;
		case 2:
			rend.sharedMaterial.SetFloat("_DmgPassThrough", 0f);
			rend.sharedMaterial.SetFloat("_DmgExtend", 1f);
			break;
		case 3:
			rend.sharedMaterial.SetFloat("_DmgPassThrough", 1f);
			rend.sharedMaterial.SetFloat("_DmgExtend", 1f);
			break;
		}
		aBlocks = new List<Block>();
		array = jid.aShadowBoxes;
		foreach (string obj in array)
		{
			if (aBlocks == _aBlocksDefault)
			{
				aBlocks = new List<Block>();
			}
			string[] array2 = obj.Split(',');
			if (array2.Length >= 4)
			{
				float result = 0f;
				float result2 = 0f;
				float result3 = 1f;
				float result4 = 1f;
				float.TryParse(array2[0], out result);
				float.TryParse(array2[1], out result2);
				float.TryParse(array2[2], out result3);
				float.TryParse(array2[3], out result4);
				bool result5 = false;
				if (array2.Length > 4)
				{
					bool.TryParse(array2[4], out result5);
				}
				Block block = new GameObject(strName + "block" + aBlocks.Count).AddComponent<Block>();
				block.rx = result3;
				block.ry = result4;
				block.TF.SetParent(TF);
				block.TF.localPosition = new Vector3(result / vScale.x, result2 / vScale.y, 0f);
				block.UpdateStats();
				block.bIsWall = bIsWall;
				block.bIsGlass = result5;
				aBlocks.Add(block);
			}
		}
		if (!bPlaceholder)
		{
			array = jid.aLights;
			foreach (string strName4 in array)
			{
				JsonLight light = DataHandler.GetLight(strName4);
				if (light == null)
				{
					continue;
				}
				Vector2 vector = default(Vector2);
				vector = light.ptPos;
				float x = 1f * vector.x / 16f / vScale.x;
				float y = 1f * vector.y / 16f / vScale.y;
				if (light.strColor != "Blank")
				{
					Visibility visibility = UnityEngine.Object.Instantiate(Visibility.visTemplate, TF);
					visibility.LightColor = DataHandler.GetColor(light.strColor);
					visibility.GO.name = strName4;
					visibility.Parent = TF;
					visibility.tfParent = TF;
					if (light.fRadius > 0f)
					{
						visibility.Radius = light.fRadius;
					}
					visibility.ptOffset = new Vector2(x, y);
					if (aLights == _aLightsDefault)
					{
						aLights = new List<Visibility>();
					}
					aLights.Add(visibility);
				}
				if (light.strImg != null)
				{
					Transform transform = DataHandler.GetMesh("prefabQuadLightSprite").transform;
					transform.SetParent(TF);
					transform.localPosition = new Vector3(x, y, transform.localPosition.z);
					Renderer component = transform.GetComponent<Renderer>();
					component.sharedMaterial = DataHandler.GetMaterial(component, light.strImg);
					Texture texture = component.sharedMaterial.GetTexture("_MainTex");
					if (dictLightSprites == _dictLightSpritesDefault)
					{
						dictLightSprites = new Dictionary<Transform, Vector2>();
					}
					dictLightSprites[transform] = new Vector2((float)texture.width / 16f, (float)texture.height / 16f);
					if (aLightRenderers == _aRendsDefault)
					{
						aLightRenderers = new List<Renderer>();
					}
					aLightRenderers.Add(component);
					if (light.bCanBlink)
					{
						IsNotification = component;
					}
				}
			}
		}
		if (aLights.Count > 0)
		{
			aPreRender.Add(this);
			mpbLights = new MaterialPropertyBlock();
		}
		fLastRotation = TF.rotation.eulerAngles.z;
		ResetTransforms(fX, fY);
		VisualizeOverlays();
	}

	private int ConvertArrayIndexToTopLeftIndex(int collectionIndex, int columns, int rows)
	{
		int num = collectionIndex % columns;
		int num2 = collectionIndex / columns;
		return (rows - 1 - num2) * columns + num;
	}

	public Material SetUpInventoryMaterial(Texture tex = null)
	{
		Texture texture = tex;
		Material material = UnityEngine.Object.Instantiate(Resources.Load<Material>("Materials/WearInv"));
		material.renderQueue = 3000;
		if (texture == null && strImgOverride != "blank" && strImgOverride != "" && strImgOverride != null)
		{
			texture = DataHandler.LoadPNG(strImgOverride + ".png", bNorm: false);
			material.SetTexture("_MainTex", texture);
		}
		if (strImgNormOverride != "blank" && strImgNormOverride != "" && strImgNormOverride != null)
		{
			material.SetTexture("_BumpMap", DataHandler.LoadPNG(strImgOverride + ".png", bNorm: false));
		}
		if (strImgDamagedOverride != "blank" && strImgDamagedOverride != "" && strImgDamagedOverride != null)
		{
			material.SetTexture("_DmgTex", DataHandler.LoadPNG(strImgDamagedOverride + ".png", bNorm: false));
			material.SetFloat("_DmgPresent", 1f);
		}
		if (jid.fDmgComplexity != 0f)
		{
			material.SetFloat("_Complexity", jid.fDmgComplexity);
		}
		else
		{
			material.SetFloat("_Complexity", 5000f);
		}
		if (jid.fDmgIntensity != 0f)
		{
			material.SetFloat("_Intensity", jid.fDmgIntensity);
		}
		if (jid.fDmgCut != -999f)
		{
			material.SetFloat("_Cut", jid.fDmgCut);
		}
		if (jid.fDmgTrim != -999f)
		{
			material.SetFloat("_Trim", jid.fDmgTrim);
		}
		if (!jid.bLerp)
		{
			material.SetFloat("_Lerp", 0f);
		}
		if (!jid.bSinew)
		{
			material.SetFloat("_Sinew", 0f);
		}
		material.SetVector("_PositionOffset", new Vector4(0f, 0f, 0f, 0f));
		float num = Mathf.Abs(CO.strID.GetHashCode()) % 200;
		if (num == 0f)
		{
			num = 0.1f;
		}
		material.SetFloat("_Seed", num);
		if (GUIMegaToolTip.Selected == CO)
		{
			material.SetFloat("_Highlight", 1f);
		}
		else
		{
			material.SetFloat("_Highlight", 0f);
		}
		material.SetFloat("_Wear", CO.CondPercentage("StatDamage", "StatDamageMax"));
		material.SetVector("_WearCol", GetWearColor(strDmgColorOverride, strImgDamagedOverride));
		if (texture != null)
		{
			material.SetVector("_Aspect", new Vector4(nWidthInTiles, nHeightInTiles, texture.width, texture.height));
		}
		else
		{
			texture = material.GetTexture("_MainTex");
			if (texture != null)
			{
				material.SetVector("_Aspect", new Vector4(nWidthInTiles, nHeightInTiles, texture.width, texture.height));
			}
			else
			{
				material.SetVector("_Aspect", new Vector4(nWidthInTiles, nHeightInTiles, 16f, 16f));
			}
		}
		switch (jid.nDmgMode)
		{
		case 1:
			material.SetFloat("_DmgPassThrough", 1f);
			material.SetFloat("_DmgExtend", 0f);
			break;
		case 2:
			material.SetFloat("_DmgPassThrough", 0f);
			material.SetFloat("_DmgExtend", 1f);
			break;
		case 3:
			material.SetFloat("_DmgPassThrough", 1f);
			material.SetFloat("_DmgExtend", 1f);
			break;
		}
		return material;
	}

	public void NotifyPreRender()
	{
		foreach (Renderer aLightRenderer in aLightRenderers)
		{
			if (aLightRenderer == null)
			{
				continue;
			}
			aLightRenderer.GetPropertyBlock(mpbLights);
			if (IsNotification != null && IsNotification == aLightRenderer)
			{
				if (bBlink || _ShowNotification)
				{
					mpbLights.SetColor("_LightColor", new Color(1f, 1f, 1f, Mathf.PingPong(Time.unscaledTime, 0.5f)));
				}
				else
				{
					mpbLights.SetColor("_LightColor", new Color(0f, 0f, 0f, 0f));
				}
			}
			else
			{
				mpbLights.SetColor("_LightColor", new Color(fFlickerAmount, fFlickerAmount, fFlickerAmount));
			}
			aLightRenderer.SetPropertyBlock(mpbLights);
		}
	}

	private void OnDestroy()
	{
		aPreRender.Remove(this);
		ItemAnimationUpdate.RemoveListener(OnItemAnimationUpdate);
	}

	private void OnItemAnimationUpdate()
	{
		_animationTimer += Time.deltaTime;
		if (_animationTimer >= 1f / (float)_itemAnimation.FrameRate)
		{
			int num = nSheetIndex;
			nSheetIndex = (nSheetIndex + 1) % _itemAnimation.FrameCount;
			if (!_itemAnimation.Loop && nSheetIndex == 0 && num > 0)
			{
				ItemAnimationUpdate.RemoveListener(OnItemAnimationUpdate);
			}
			rend.sharedMaterial = DataHandler.GetMaterialSheet(rend, strImgOverride, ConvertArrayIndexToTopLeftIndex(nSheetIndex, _itemAnimation.Columns, _itemAnimation.Rows), strImgNormOverride, strImgDamagedOverride, strDmgColorOverride, nWidthInTiles, nHeightInTiles);
			_animationTimer = 0f;
		}
	}

	public void ResetTransforms(float fX, float fY)
	{
		_ = rend.bounds.size;
		_tf.position = new Vector3(fX, fY, GetZPos());
		_tf.rotation = Quaternion.Euler(0f, 0f, fRotLast);
		_tf.localScale = new Vector3(vScale.x, vScale.y, 1f);
		foreach (Block aBlock in aBlocks)
		{
			aBlock.UpdateStats();
		}
		SetLocalVis();
		foreach (KeyValuePair<Transform, Vector2> dictLightSprite in dictLightSprites)
		{
			dictLightSprite.Key.localScale = new Vector3(dictLightSprite.Value.x / vScale.x, dictLightSprite.Value.y / vScale.y, 1f / _tf.localScale.z);
		}
		BoxCollider component = GetComponent<BoxCollider>();
		component.center = new Vector3(component.center.x, component.center.y, 5f);
		component.size = new Vector3(component.size.x, component.size.y, 10f);
	}

	public float GetZPos()
	{
		if (rend.bounds.size.z > 0.01f)
		{
			return 0f;
		}
		return (0f - vScale.z) * 4f;
	}

	public void SetAlt(string strItemDef)
	{
		if (strItemDef == null)
		{
			SetAlt(null, null);
			return;
		}
		JsonItemDef itemDef = DataHandler.GetItemDef(strItemDef);
		if (itemDef != null)
		{
			SetAlt(itemDef.strImg, itemDef.strImgNorm, itemDef.strImgDamaged, itemDef.strDmgColor);
		}
	}

	public void SetAlt(string strImg, string strImgNorm, string strImgDamaged = "blank", string strDmgColor = "blank", JsonItemAnimation jAnim = null)
	{
		if (strImg == null)
		{
			strImgOverride = jid.strImg;
			strImgNormOverride = jid.strImgNorm;
			strImgDamagedOverride = jid.strImgDamaged;
			strDmgColorOverride = jid.strDmgColor;
		}
		else
		{
			strImgOverride = strImg;
			strImgNormOverride = strImgNorm;
			strImgDamagedOverride = strImgDamaged;
			if (!string.IsNullOrEmpty(strDmgColor) && strDmgColor != "blank")
			{
				strDmgColorOverride = strDmgColor;
			}
			else
			{
				strDmgColorOverride = jid.strDmgColor;
			}
		}
		if (string.IsNullOrEmpty(strImgDamagedOverride))
		{
			strImgDamagedOverride = "blank";
		}
		if (jAnim != null)
		{
			SetupAnimation(jAnim);
		}
		else if (bHasSpriteSheet)
		{
			rend.sharedMaterial = DataHandler.GetMaterialSheet(rend, strImgOverride, SpriteSheetIndices[nSheetIndex], strImgNormOverride, strImgDamagedOverride, strDmgColorOverride);
		}
		else
		{
			rend.sharedMaterial = DataHandler.GetMaterial(rend, strImgOverride, strImgNormOverride, strImgDamagedOverride, strDmgColorOverride);
		}
	}

	public bool CheckFit(Vector3 vCenter, Ship objShip, List<Tile> aGridSprites = null, JsonZone jz = null)
	{
		Tile tile = null;
		bool flag = true;
		if (GUIInventory.instance.Selected != null)
		{
			Vector3 vector = GUIInventory.instance.CODoll.GetPos();
			float num = 3f;
			if (Mathf.Abs((float)Mathf.RoundToInt(vector.x) - vCenter.x) > num || Mathf.Abs((float)Mathf.RoundToInt(vector.y) - vCenter.y) > num)
			{
				flag = false;
			}
			if (flag)
			{
				flag = Visibility.IsCondOwnerLOSVisible(GUIInventory.instance.CODoll, vCenter);
			}
		}
		Vector2 vector2 = new Vector2(vCenter.x - ((float)nWidthInTiles / 2f - 0.5f) * 1f, vCenter.y + ((float)nHeightInTiles / 2f - 0.5f) * 1f);
		vector2.x -= 1f;
		vector2.y += 1f;
		int num2 = 0;
		bool result = true;
		bool flag2 = true;
		Tile tilHit = null;
		rgbFit.a = 0.2f + Mathf.Sin(6f * Time.realtimeSinceStartup) * 0.15f;
		rgbUnfit.a = 0.2f + Mathf.Sin(6f * Time.realtimeSinceStartup) * 0.15f;
		Vector2 vector3 = new Vector2(float.PositiveInfinity, float.PositiveInfinity);
		Vector2 vector4 = new Vector2(float.NegativeInfinity, float.NegativeInfinity);
		CondOwner condOwner = objShip.aDocksys.FirstOrDefault();
		if (condOwner != null)
		{
			Vector2 pos = condOwner.GetPos("DockA");
			Vector2 vector5 = condOwner.GetPos("DockB") - pos;
			float num3 = vector5.magnitude / 2f;
			if (vector5.y > 0.5f)
			{
				vector3.y = pos.y + num3;
			}
			else if (vector5.y < -0.5f)
			{
				vector4.y = pos.y - num3;
			}
			else if (vector5.x > 0.5f)
			{
				vector3.x = pos.x + num3;
			}
			else if (vector5.x < -0.5f)
			{
				vector4.x = pos.x - num3;
			}
		}
		for (int i = 0; i < nHeightInTiles + 2; i++)
		{
			for (int j = 0; j < nWidthInTiles + 2; j++)
			{
				tile = null;
				tilHit = null;
				flag2 = true;
				bool flag3 = i == 0 || i == nHeightInTiles + 1 || j == 0 || j == nWidthInTiles + 1;
				num2 = i * (nWidthInTiles + 2) + j;
				if (aGridSprites != null)
				{
					if (aGridSprites.Count <= num2)
					{
						TileUtils.NewGridSprite();
					}
					tile = aGridSprites[num2];
					tile.transform.position = new Vector3(vector2.x + (float)j, vector2.y - (float)i, tile.transform.position.z);
					tile.gameObject.SetActive(flag3);
					tile.SetColor(rgbFit);
					tile.SetMat(strFit);
				}
				Vector2 vector6 = new Vector2(vector2.x + (float)j, vector2.y - (float)i);
				flag2 = flag && !(vector6.x > vector3.x) && !(vector6.x < vector4.x) && !(vector6.y > vector3.y) && !(vector6.y < vector4.y);
				if (flag2)
				{
					if (num2 >= aSocketReqs.Count)
					{
						break;
					}
					bool flag4 = aSocketReqs[num2].aCOs.Length + aSocketReqs[num2].aLoots.Length == 0;
					bool flag5 = aSocketForbids[num2].aCOs.Length + aSocketForbids[num2].aLoots.Length == 0;
					if (flag4 && flag5)
					{
						continue;
					}
					tilHit = objShip.GetTileAtWorldCoords1(vector6.x, vector6.y, bAllowDocked: true);
					if (tilHit == null)
					{
						flag2 = jz == null && flag4;
					}
					else if (objShip.IsDocked() && TileUtils.WouldConnectShips(tilHit))
					{
						flag2 = false;
					}
					else
					{
						CondOwner coProps = tilHit.coProps;
						if (!new CondTrigger
						{
							aReqs = aSocketReqs[num2].GetLootNames().ToArray(),
							aForbids = aSocketForbids[num2].GetLootNames().ToArray()
						}.Triggered(coProps))
						{
							flag2 = false;
						}
						if (jz != null && !flag3 && Array.FindIndex(jz.aTiles, (int num4) => num4 == tilHit.Index) < 0)
						{
							flag2 = false;
						}
					}
				}
				if (!flag2)
				{
					result = false;
					if (tile == null)
					{
						return result;
					}
					tile.gameObject.SetActive(value: true);
					tile.SetColor(rgbUnfit);
					tile.SetMat(strUnfit);
				}
			}
			if (num2 >= aSocketReqs.Count)
			{
				break;
			}
		}
		return result;
	}

	public void RotateCW()
	{
		if (bHasSpriteSheet)
		{
			return;
		}
		TF.Rotate(0f, 0f, -90f);
		fRotLast = MathUtils.NormalizeAngleDegrees(fRotLast - 90f);
		aSocketReqs = TileUtils.RotateTilesCW(aSocketReqs, nWidthInTiles + 2);
		aSocketForbids = TileUtils.RotateTilesCW(aSocketForbids, nWidthInTiles + 2);
		aSocketAdds = TileUtils.RotateTilesCW(aSocketAdds, nWidthInTiles);
		MathUtils.Swap(ref nWidthInTiles, ref nHeightInTiles);
		if (aBlocks != null)
		{
			foreach (Block aBlock in aBlocks)
			{
				aBlock.RotateCW();
			}
		}
		SetLocalVis();
		foreach (Transform item in base.transform)
		{
			if (CrewSim.objInstance.workManager.constructionSigns.Contains(item.gameObject))
			{
				item.rotation = Quaternion.identity;
			}
		}
	}

	public void SetLocalVis()
	{
		float x = vScale.x;
		float y = vScale.y;
		if (MathUtils.IsRotationVertical(TF.rotation.eulerAngles.z))
		{
			MathUtils.Swap(ref x, ref y);
		}
		foreach (Visibility aLight in aLights)
		{
			aLight.LocalPosition = new Vector3(aLight.ptOffset.x, aLight.ptOffset.y, 0f);
			aLight.LocalScale = new Vector3(1f / x, 1f / y, 1f / vScale.z);
		}
	}

	public int SetSpriteSheetIndex(Tile[] aTiles)
	{
		if (!bHasSpriteSheet || aTiles == null || ctSpriteSheet == null)
		{
			return 0;
		}
		nSheetIndex = 0;
		if (aTiles[1] != null && ctSpriteSheet.Triggered(aTiles[1].coProps))
		{
			nSheetIndex += 8;
		}
		if (aTiles[3] != null && ctSpriteSheet.Triggered(aTiles[3].coProps))
		{
			nSheetIndex += 4;
		}
		if (aTiles[4] != null && ctSpriteSheet.Triggered(aTiles[4].coProps))
		{
			nSheetIndex += 2;
		}
		if (aTiles[6] != null && ctSpriteSheet.Triggered(aTiles[6].coProps))
		{
			nSheetIndex++;
		}
		rend.sharedMaterial = DataHandler.GetMaterialSheet(rend, strImgOverride, SpriteSheetIndices[nSheetIndex], strImgNormOverride, strImgDamagedOverride);
		return nSheetIndex;
	}

	public override string ToString()
	{
		return TF.name;
	}

	public void SetToMousePosition(Vector2 vMouse)
	{
		TF.position = new Vector3(TileUtils.GridAlign(vMouse.x) + rend.bounds.size.x / 2f - 0.5f, TileUtils.GridAlign(vMouse.y) - rend.bounds.size.y / 2f + 0.5f, TF.position.z);
	}

	public static Color GetWearColor(string strDmgColor, string strImgDamaged)
	{
		if (strDmgColor != "blank" && !string.IsNullOrEmpty(strDmgColor))
		{
			return DataHandler.GetColor(strDmgColor);
		}
		if (strImgDamaged != "blank")
		{
			return new Color(1f, 1f, 1f);
		}
		return DataHandler.GetColor("DamageTintDefault");
	}
}
