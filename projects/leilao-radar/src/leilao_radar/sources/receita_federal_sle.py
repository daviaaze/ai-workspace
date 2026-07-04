"""Parser for Receita Federal — Sistema de Leilão Eletrônico (SLE).

Uses the REST API directly (Angular SPA backend):
  GET /sle-sociedade/api/edital/{orgao}/{seq}/{ano}
  GET /sle-sociedade/api/edital  (edital list — WIP)

Returns structured JSON with all lot data including images.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

import httpx

from leilao_radar.sources.base import BaseSource, SourceResult


class ReceitaFederalSLE(BaseSource):
    """Receita Federal — SLE via REST API."""

    name = "receita_federal_sle"
    label = "Receita Federal — SLE"
    url = "https://www25.receita.fazenda.gov.br/sle-sociedade/portal"
    api_base = "https://www25.receita.fazenda.gov.br/sle-sociedade/api"
    tier = "A"
    source_type = "federal"
    check_interval_hours = 6

    # Known active editais from last exploration
    KNOWN_EDITAIS: list[str] = [
        "100100/3/2026",   # Brasília - Apple/iOS (encerra 16/Jul)
        "100100/4/2026",   # Brasília - Informática (encerra 20/Jul)
        "200100/1/2026",   # Belém - Eletrônicos, minerais
        "900100/8/2026",   # Curitiba - Celulares, veículos (encerra 27/Jul)
        "717600/4/2026",   # Rio de Janeiro
        "717800/2/2026",   # Itaguaí
        "717700/2/2026",   # Rio de Janeiro
        "700100/8/2026",   # Rio de Janeiro
        "700100/7/2026",   # Rio de Janeiro
    ]

    ORGAO_LOCATION: dict[str, str] = {
        "100100": "Brasília/DF",
        "200100": "Belém/PA",
        "900100": "Curitiba/PR",
        "717600": "Rio de Janeiro/RJ",
        "717800": "Itaguaí/RJ",
        "717700": "Rio de Janeiro/RJ",
        "700100": "Rio de Janeiro/RJ",
    }

    # Mapping situacaoLote → readable status
    SITUACAO_LOTE: dict[int, str] = {
        0: "Disponível",
        1: "Aberto",
        2: "Em andamento",
        11: "Aberto para lances",
        99: "Encerrado",
    }

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)
        self._client = httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": "LeilaoRadar/0.1 (research project)",
                "Accept": "application/json",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
        )

    def scrape(self) -> SourceResult:
        """Scrape all known editais via REST API."""
        result = SourceResult()
        result.source_name = self.name
        start = time.monotonic()

        for edital_key in self.KNOWN_EDITAIS:
            try:
                self._scrape_edital_api(edital_key, result)
            except Exception as e:
                result.errors.append(f"{edital_key}: {e}")

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def _scrape_edital_api(self, edital_key: str, result: SourceResult):
        """Scrape a single edital via REST API."""
        orgao, seq, ano = edital_key.split("/")
        api_url = f"{self.api_base}/edital/{orgao}/{seq}/{ano}"

        resp = self._client.get(api_url)
        resp.raise_for_status()
        result.http_requests += 1

        data = resp.json()

        # ── Parse edital info ──────────────────────────────────────
        location = self.ORGAO_LOCATION.get(orgao, data.get("cidade", ""))
        title = f"Edital {data.get('edital', edital_key)}"
        data_fim = data.get("dataFimPropostas", "")
        data_pregao = data.get("dataAberturaLances", "")

        edital_record = {
            "source_id": self.source_id,
            "edital_number": edital_key,
            "title": title,
            "location": location,
            "end_propostas": data_fim,
            "data_pregao": data_pregao,
            "total_lotes": len(data.get("listaLotes", [])),
            "permitido_pf": 1 if data.get("permitePF", True) else 0,
            "permitido_pj": 1,
            "url": f"{self.url}/edital/{edital_key}",
        }
        result.editais.append(edital_record)

        # ── Parse lots ─────────────────────────────────────────────
        for lot_data in data.get("listaLotes", []):
            try:
                lot = self._parse_lot_json(lot_data, edital_key, location)
                if lot:
                    result.lotes.append(lot)
            except Exception as e:
                result.errors.append(f"Lote {lot_data.get('nrAtribuido')}: {e}")

    def _parse_lot_json(self, lot_data: dict, edital_key: str,
                        location: str) -> dict[str, Any]:
        """Parse a lot from the API JSON response."""
        lot_num = lot_data.get("nrAtribuido", 0)
        tipo = lot_data.get("tipo", "DIVERSOS")
        valor_minimo = lot_data.get("valorMinimo", 0)
        valor_avaliacao = lot_data.get("valorAvaliacao", 0)
        permite_pf = lot_data.get("permitePF", True)
        sit_lote = lot_data.get("situacaoLote", 0)

        # valorMinimo comes in cents (8246 = R$ 82,46)
        # But some values look like reais already — check scale
        preco = valor_minimo
        if valor_avaliacao > 0 and valor_minimo > 0:
            # If valorMinimo is much smaller than valorAvaliacao,
            # it's likely in cents
            ratio = valor_avaliacao / valor_minimo
            if 50 < ratio < 500:  # Typical range: 2x-10x, so cents
                preco = valor_minimo / 100.0
            # If ratio is ~1-5, valorMinimo is already in reais
            elif 1 < ratio < 5:
                preco = valor_minimo
            else:
                preco = valor_minimo / 100.0  # Default: assume cents
        else:
            preco = valor_minimo / 100.0 if valor_minimo > 1000 else valor_minimo

        # Build title from type + lot number
        titulo = f"{tipo} — Lote {lot_num}"

        # Build rich description
        descricao_parts = [f"Lote {lot_num} — {tipo}"]
        if valor_avaliacao > 0:
            descricao_parts.append(f"Valor de avaliação: R$ {valor_avaliacao:,.2f}")
        descricao_parts.append(f"Lance mínimo: R$ {preco:,.2f}")

        lot = {
            "lote_number": str(lot_num),
            "edital_number": edital_key,
            "location": location,
            "titulo": titulo,
            "descricao": "; ".join(descricao_parts),
            "preco_minimo": preco,
            "tipo": tipo,
            "categoria_normalizada": self._normalize_tipo(tipo),
            "situacao": self.SITUACAO_LOTE.get(sit_lote, f"Código {sit_lote}"),
            "permitido_para": "PF/PJ" if permite_pf else "PJ",
            "total_itens": 1,
            "raw_data": {
                "valor_avaliacao": valor_avaliacao,
                "possui_imagens": lot_data.get("possuiImagens", False),
                "situacao_lote": sit_lote,
                "imagens": [
                    img.get("src", "")
                    for img in lot_data.get("imagens", [])
                ],
            },
        }

        return lot

    def _scrape_portal_home(self, result: SourceResult):
        """Try to discover new editais from portal.

        The portal home is an SPA, so we attempt the API list endpoint.
        """
        try:
            resp = self._client.get(f"{self.api_base}/edital")
            if resp.status_code == 200:
                data = resp.json()
                # Process if the API returns an edital list
                # Currently returns 500, so this is future-proofing
        except Exception:
            pass
