"""Verify the P0 fetch rewire: leilão sources route through the shared
web-access layer (``BaseSource._fetch`` → ``WebFetchTool``) instead of
rolling their own ``httpx.Client``.

No network: ``WebFetchTool._run`` is monkeypatched and source fetch helpers
are stubbed with fixtures. The goal is to confirm the rewire wiring — call
sites, error handling, and parsing — is correct. Live header/behaviour
verification still needs ``leilao-radar scrape`` (see notes on SLE below).
"""

from __future__ import annotations

import json

import pytest

from ai_workspace.tools.web_fetch import WebFetchTool
from ai_workspace.leilao_radar.sources.base import BaseSource
from ai_workspace.leilao_radar.sources.receita_federal_sle import ReceitaFederalSLE

# selectolax is a declared leilão dep not yet in the shared venv (lands with
# the P1 fold). Gate only the leilao_net tests on it; SLE/base tests run now.
try:  # noqa: SIM105
    import selectolax  # type: ignore  # noqa: F401

    HAS_SELECTOLAX = True
except ImportError:
    HAS_SELECTOLAX = False


# ── Fixtures ────────────────────────────────────────────────────────────────

SLE_EDITAL_JSON = {
    "edital": "001/2026",
    "cidade": "Brasília",
    "dataFimPropostas": "2026-07-16",
    "dataAberturaLances": "2026-07-20",
    "permitePF": True,
    "listaLotes": [
        {
            "nrAtribuido": 1,
            "tipo": "Veículo",
            "valorMinimo": 8246,
            "valorAvaliacao": 16492,
            "permitePF": True,
            "situacaoLote": 0,
            "descricao": "Honda Civic 2020",
            "possuiImagens": True,
            "imagens": [{"src": "https://img.example/x.jpg"}],
        }
    ],
}


class _Stub:
    """Records calls to ``WebFetchTool._run`` and returns configured content.

    Used as a class-level monkeypatch: ``setattr(WebFetchTool, "_run", stub)``
    makes ``WebFetchTool()._run(url, ...)`` invoke ``stub(url, ...)``.
    """

    def __init__(self, responses):
        self.calls: list[dict] = []
        self._responses = responses

    def __call__(self, url, extract_text=True, max_length=5_000):
        self.calls.append({"url": url, "extract_text": extract_text})
        return self._responses.get(url, f"HTTP 404 fetching {url}")


class _ConcreteSource(BaseSource):
    """Minimal concrete source to exercise BaseSource fetch helpers."""

    name = "test"
    label = "Test"
    url = "https://test.example"
    tier = "C"
    source_type = "test"

    def scrape(self):  # pragma: no cover - not exercised here
        raise NotImplementedError


@pytest.fixture
def source():
    return _ConcreteSource(source_id=7)


# ── BaseSource shared fetch helpers ─────────────────────────────────────────


def test_fetch_html_success(source, monkeypatch):
    monkeypatch.setattr(WebFetchTool, "_run", _Stub({"https://x/": "<html>hi</html>"}))
    assert source._fetch_html("https://x/") == "<html>hi</html>"


def test_fetch_html_error_prefix_returns_none(source, monkeypatch):
    monkeypatch.setattr(WebFetchTool, "_run", _Stub({}))  # default → "HTTP 404 ..."
    assert source._fetch_html("https://x/") is None


def test_fetch_html_empty_returns_none(source, monkeypatch):
    monkeypatch.setattr(WebFetchTool, "_run", _Stub({"https://x/": ""}))
    assert source._fetch_html("https://x/") is None


def test_fetch_json_success_uses_raw_body(source, monkeypatch):
    """``_fetch_json`` must use ``extract_text=False`` so JSON is not run
    through BeautifulSoup (which would corrupt characters like ``<``/``&``)."""
    stub = _Stub({"https://api/": json.dumps({"a": 1, "b": [2, 3]})})
    monkeypatch.setattr(WebFetchTool, "_run", stub)
    assert source._fetch_json("https://api/") == {"a": 1, "b": [2, 3]}
    assert stub.calls[0]["extract_text"] is False


def test_fetch_json_bad_payload_returns_none(source, monkeypatch):
    monkeypatch.setattr(WebFetchTool, "_run", _Stub({"https://api/": "not json"}))
    assert source._fetch_json("https://api/") is None


def test_fetch_json_error_prefix_returns_none(source, monkeypatch):
    monkeypatch.setattr(WebFetchTool, "_run", _Stub({}))  # → "HTTP 404 ..."
    assert source._fetch_json("https://api/") is None


def test_fetch_exception_returns_none(source, monkeypatch):
    def boom(self, url, **kw):
        raise RuntimeError("network down")

    monkeypatch.setattr(WebFetchTool, "_run", boom)
    assert source._fetch_html("https://x/") is None
    assert source._fetch_json("https://x/") is None


# ── ReceitaFederalSLE end-to-end (no network) ──────────────────────────────
#
# NOTE: SLE talks to a live government REST API. The rewire routes it through
# WebFetchTool, which sends ``Accept: text/html,application/json,*/*`` (SLE
# previously sent ``Accept: application/json``). The API *should* honour the
# ``application/json`` token, but this cannot be verified offline — run
# ``leilao-radar scrape`` once against SLE to confirm live behaviour.


def test_sle_has_no_httpx_client():
    """The rewire removed the per-source ``httpx.Client``."""
    sle = ReceitaFederalSLE(source_id=42)
    assert not hasattr(sle, "_client"), "SLE must not keep a private httpx client"


def test_sle_scrape_parses_editais_and_lotes():
    sle = ReceitaFederalSLE(source_id=42)
    sle._fetch_json = lambda url: SLE_EDITAL_JSON  # type: ignore[assignment]
    result = sle.scrape()

    n = len(ReceitaFederalSLE.KNOWN_EDITAIS)
    assert len(result.editais) == n
    assert len(result.lotes) == n
    assert result.http_requests == n
    assert result.errors == []

    edital = result.editais[0]
    # First known edital is "100100/3/2026" → orgao 100100 → Brasília/DF
    assert edital["source_id"] == 42
    assert edital["location"] == "Brasília/DF"
    assert edital["edital_number"] == ReceitaFederalSLE.KNOWN_EDITAIS[0]
    assert edital["total_lotes"] == 1
    assert edital["permitido_pf"] == 1

    lot = result.lotes[0]
    # valorMinimo=8246, valorAvaliacao=16492 → ratio 2.0 → "already reais" path
    assert lot["preco_minimo"] == 8246
    assert lot["tipo"] == "Veículo"
    assert lot["categoria_normalizada"] == "VEÍCULO"
    assert lot["situacao"] == "Disponível"
    assert lot["permitido_para"] == "PF/PJ"
    assert lot["raw_data"]["possui_imagens"] is True
    assert lot["raw_data"]["imagens"] == ["https://img.example/x.jpg"]


def test_sle_scrape_handles_fetch_failure():
    sle = ReceitaFederalSLE(source_id=42)
    sle._fetch_json = lambda url: None  # type: ignore[assignment]  # API down
    result = sle.scrape()

    assert result.editais == []
    assert result.lotes == []
    assert result.http_requests == 0
    assert len(result.errors) == len(ReceitaFederalSLE.KNOWN_EDITAIS)
    assert all("API fetch failed" in e for e in result.errors)


def test_sle_scrape_isolates_edital_without_lots():
    """An edital that parses fine but yields no lots must not break the run."""
    sle = ReceitaFederalSLE(source_id=42)
    call = {"n": 0}

    def flaky(url):
        call["n"] += 1
        if call["n"] == 1:
            return {"edital": "empty", "listaLotes": []}
        return SLE_EDITAL_JSON

    sle._fetch_json = flaky  # type: ignore[assignment]
    result = sle.scrape()

    assert len(result.editais) == len(ReceitaFederalSLE.KNOWN_EDITAIS)
    assert len(result.lotes) == len(ReceitaFederalSLE.KNOWN_EDITAIS) - 1


# ── LeilaoNet (requires selectolax — skips if not installed) ───────────────


LEILAO_NET_LISTING_HTML = """
<html><body>
  <div class="card">
    <a href="/leilao/123">Leilão de Veículos</a>
    <span>R$ 5.000,00</span>
  </div>
</body></html>
"""


@pytest.mark.skipif(not HAS_SELECTOLAX, reason="selectolax not in shared venv (lands with P1 fold)")
def test_leilao_net_has_no_httpx_client():
    from ai_workspace.leilao_radar.sources.leilao_net import LeilaoNet

    ln = LeilaoNet(source_id=5)
    assert not hasattr(ln, "_client"), "LeilaoNet must not keep a private httpx client"


@pytest.mark.skipif(not HAS_SELECTOLAX, reason="selectolax not in shared venv (lands with P1 fold)")
def test_leilao_net_scrape_uses_fetch_html():
    from ai_workspace.leilao_radar.sources.leilao_net import LeilaoNet

    ln = LeilaoNet(source_id=5)
    ln._fetch_html = lambda url: LEILAO_NET_LISTING_HTML  # type: ignore[assignment]
    result = ln.scrape()

    n_urls = len(ln.SEARCH_URLS) + len(ln.CATEGORY_URLS)
    assert result.http_requests >= n_urls  # every listing fetched via shared layer
    assert isinstance(result.lotes, list)


@pytest.mark.skipif(not HAS_SELECTOLAX, reason="selectolax not in shared venv (lands with P1 fold)")
def test_leilao_net_scrape_handles_fetch_failure():
    from ai_workspace.leilao_radar.sources.leilao_net import LeilaoNet

    ln = LeilaoNet(source_id=5)
    ln._fetch_html = lambda url: None  # type: ignore[assignment]  # total fetch failure
    result = ln.scrape()

    assert result.lotes == []
    n_urls = len(ln.SEARCH_URLS) + len(ln.CATEGORY_URLS)
    assert len(result.errors) == n_urls
    assert result.http_requests == 0
