using System.Collections;
using Ostranauts.Core;
using TMPro;
using UnityEngine;

public class GUILoadingPopUp : MonoSingleton<GUILoadingPopUp>
{
	[SerializeField]
	private TMP_Text txtTitle;

	[SerializeField]
	private TMP_Text txtBody;

	[SerializeField]
	private CanvasGroup cg;

	private void Start()
	{
		LoadManager.OnAsyncSaveStarted.AddListener(delegate
		{
			FadeOutToolTip();
		});
		LoadManager.OnSaveFinished.AddListener(delegate
		{
			FadeOutToolTip();
		});
		LoadManager.OnSavingFailed.AddListener(delegate
		{
			FadeOutToolTip();
		});
	}

	private void OnDestroy()
	{
		LoadManager.OnAsyncSaveStarted.RemoveListener(delegate
		{
			FadeOutToolTip();
		});
		LoadManager.OnSaveFinished.RemoveListener(delegate
		{
			FadeOutToolTip();
		});
		LoadManager.OnSavingFailed.RemoveListener(delegate
		{
			FadeOutToolTip();
		});
	}

	private IEnumerator FadeToolTip(float wait)
	{
		float amt = wait;
		while (amt >= 0f)
		{
			amt -= Time.unscaledDeltaTime;
			cg.alpha = amt / wait;
			yield return null;
		}
		cg.alpha = 0f;
		yield return null;
	}

	public void ShowTooltip(string strTitle, string strBody)
	{
		txtTitle.text = strTitle;
		txtBody.text = strBody;
		cg.alpha = 1f;
	}

	public void FadeOutToolTip(float fadeOutDuration = 1.5f)
	{
		if (cg.alpha != 0f)
		{
			StartCoroutine(FadeToolTip(fadeOutDuration));
		}
	}
}
