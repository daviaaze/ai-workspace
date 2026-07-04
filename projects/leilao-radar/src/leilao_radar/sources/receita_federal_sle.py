"""Parser for Receita Federal — Sistema de Leilão Eletrônico (SLE).

Sources:
  Main portal: https://www25.receita.fazenda.gov.br/sle-sociedade/portal
  Edital page: /sle-sociedade/portal/edital/{orgao}/{seq}/{ano}
  Lote page:   /sle-sociedade/portal/edital/{orgao}/{seq}/{ano}/lote/{num}
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

import httpx
from selectolax.parser import HTMLParser

from leilao_radar.sources.base import BaseSource, SourceResult


class ReceitaFederalSLE(BaseSource):
    """Receita Federal — SLE (Sistema de Leilão Eletrônico)."""

    name = "receita_federal_sle"
    label = "Receita Federal — SLE"
    url = "https://www25.receita.fazenda.gov.br/sle-sociedade/portal"
    tier = "A"
    source_type = "federal"
    check_interval_hours = 6

    # Known active editais (orgao/seq/ano) from last exploration
    KNOWN_EDITAIS: list[str] = [
        "100100/3/2026",   # Brasília - Lotes Apple/iOS
        "100100/4/2026",   # Brasília - Informática
        "200100/1/2026",   # Belém - Eletrônicos, minerais
        "900100/8/2026",   # Curitiba - Celulares, veículos (encerra 27/Jul)
        "717600/4/2026",   # Rio de Janeiro
        "717800/2/2026",   # Itaguaí
        "717700/2/2026",   # Rio de Janeiro
        "700100/8/2026",   # Rio de Janeiro
        "700100/7/2026",   # Rio de Janeiro
    ]

    # Max lotes to try per edital (default range)
    EDITAL_MAX_LOTES: dict[str, int] = {
        "100100/3/2026": 25,
        "100100/4/2026": 200,
        "200100/1/2026": 192,
        "900100/8/2026": 273,
        "717600/4/2026": 41,
        "717800/2/2026": 17,
        "717700/2/2026": 11,
        "700100/8/2026": 100,
        "700100/7/2026": 100,
    }

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)
        self._client = httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
        )

    def scrape(self) -> SourceResult:
        """Scrape all known editais and their lots."""
        result = SourceResult()
        result.source_name = self.name
        start = time.monotonic()

        for edital_key in self.KNOWN_EDITAIS:
            try:
                self._scrape_edital(edital_key, result)
            except Exception as e:
                result.errors.append(f"{edital_key}: {e}")

        # Try to find new editais on the portal
        try:
            self._scrape_portal_home(result)
        except Exception as e:
            result.errors.append(f"portal_home: {e}")

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def _scrape_portal_home(self, result: SourceResult):
        """Scrape main portal to discover new editais."""
        resp = self._client.get(self.url)
        resp.raise_for_status()
        result.http_requests += 1

        html = resp.text
        parser = HTMLParser(html)

        # Look for edital links
        for link in parser.css("a[href*='edital']"):
            href = link.attributes.get("href", "")
            edital_match = re.search(r'edital/([\d]+/[\d]+/[\d]{4})', href)
            if edital_match:
                edital_key = edital_match.group(1)
                if edital_key not in self.KNOWN_EDITAIS:
                    # Found a new edital! Scrape it too
                    try:
                        self._scrape_edital(edital_key, result)
                    except Exception:
                        pass

    def _scrape_edital(self, edital_key: str, result: SourceResult):
        """Scrape a single edital page."""
        url = f"https://www25.receita.fazenda.gov.br/sle-sociedade/portal/edital/{edital_key}"
        resp = self._client.get(url)
        resp.raise_for_status()
        result.http_requests += 1

        html = resp.text
        parser = HTMLParser(html)

        # Extract edital info
        title_el = parser.css_first("h1, h2, .titulo-edital, .edital-title")
        title = title_el.text(strip=True) if title_el else f"Edital {edital_key}"

        # Location
        location = ""
        for loc_pattern in [".local-edital", ".local", "[class*='local']", "[class*='Local']"]:
            loc_el = parser.css_first(loc_pattern)
            if loc_el:
                location = loc_el.text(strip=True)
                break
        if not location:
            # Try to infer from orgao
            orgao = edital_key.split("/")[0]
            location = {
                "100100": "Brasília/DF",
                "200100": "Belém/PA",
                "900100": "Curitiba/PR",
                "717600": "Rio de Janeiro/RJ",
                "717800": "Itaguaí/RJ",
                "717700": "Rio de Janeiro/RJ",
                "700100": "Rio de Janeiro/RJ",
            }.get(orgao, "")

        # Dates
        end_propostas = ""
        data_pregao = ""
        text = parser.body.text() if parser.body else html

        for date_match in re.finditer(r'(\d{2}/\d{2}/\d{4})\s*(?:às|as)?\s*(\d{2}:\d{2})?', text):
            if not end_propostas:
                end_propostas = date_match.group(0)
            elif not data_pregao:
                data_pregao = date_match.group(0)

        # Store edital
        edital_record = {
            "source_id": self.source_id,
            "edital_number": edital_key,
            "title": title,
            "location": location,
            "end_propostas": end_propostas,
            "data_pregao": data_pregao,
            "total_lotes": 0,
            "permitido_pf": 1,
            "permitido_pj": 1,
            "url": url,
        }
        result.editais.append(edital_record)

        # Parse lot listings from the page
        self._parse_lots_from_html(parser, html, edital_key, result)

        # Also try individual lot pages
        max_lotes = self.EDITAL_MAX_LOTES.get(edital_key, 50)
        for lot_num in range(1, max_lotes + 1):
            lote_url = (
                f"https://www25.receita.fazenda.gov.br/sle-sociedade/"
                f"portal/edital/{edital_key}/lote/{lot_num}"
            )
            try:
                lote_resp = self._client.get(lote_url)
                result.http_requests += 1
                if lote_resp.status_code == 200:
                    lot_text = lote_resp.text
                    if "Lote não encontrado" not in lot_text and "Erro" not in lot_text:
                        lot_data = self._parse_lote_page(lot_text, lote_url, lot_num)
                        if lot_data:
                            lot_data["edital_number"] = edital_key
                            lot_data["location"] = location
                            result.lotes.append(lot_data)
                time.sleep(0.3)  # Rate limiting
            except Exception:
                continue

    def _parse_lots_from_html(self, parser: HTMLParser, html: str,
                               edital_key: str, result: SourceResult):
        """Parse lot listings embedded in the edital page."""
        text = parser.body.text() if parser.body else html
        lines = text.split("\n")

        current_lote: dict[str, Any] | None = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            lote_match = re.match(r"Lote\s+(\d+)", line)
            if lote_match:
                if current_lote:
                    result.lotes.append(current_lote)
                current_lote = {
                    "lote_number": lote_match.group(1),
                    "edital_number": edital_key,
                    "titulo": "",
                    "descricao": "",
                    "tipo": "",
                }
                continue

            if current_lote:
                price = self._extract_price(line)
                if price:
                    current_lote["preco_minimo"] = price
                    continue

                tipo_match = re.match(r"Tipo:\s*(.+)", line)
                if tipo_match:
                    current_lote["tipo"] = tipo_match.group(1).strip()
                    current_lote["categoria_normalizada"] = self._normalize_tipo(
                        tipo_match.group(1)
                    )
                    continue

                if "Situação" in line or "Situacao" in line:
                    sit_match = re.search(r"Situa[çc][ãa]o:\s*(.+)", line)
                    if sit_match:
                        current_lote["situacao"] = sit_match.group(1).strip()

                if "Permite Pessoa Física" in line:
                    current_lote["permitido_para"] = "PF/PJ"

        if current_lote:
            result.lotes.append(current_lote)

    def _parse_lote_page(self, html: str, url: str, lot_num: int) -> dict[str, Any]:
        """Parse an individual lot detail page."""
        parser = HTMLParser(html)
        text = parser.body.text() if parser.body else html

        lot: dict[str, Any] = {
            "lote_number": str(lot_num),
            "url": url,
            "titulo": "",
            "descricao": "",
        }

        # Title
        title_el = parser.css_first("h1, h2, .lote-titulo, .titulo-lote")
        if title_el:
            lot["titulo"] = title_el.text(strip=True)

        # Type
        tipo_match = re.search(r"Tipo:\s*(.+)", text)
        if tipo_match:
            lot["tipo"] = tipo_match.group(1).strip()
            lot["categoria_normalizada"] = self._normalize_tipo(tipo_match.group(1))

        # Price
        price = self._extract_price(text)
        if price:
            lot["preco_minimo"] = price

        # Situation
        sit_match = re.search(r"Situa[çc][ãa]o\s*(?:do Lote)?:\s*(.+)", text)
        if sit_match:
            lot["situacao"] = sit_match.group(1).strip()

        # Permission
        if "Permite Pessoa Física" in text:
            lot["permitido_para"] = "PF/PJ"
        elif "Somente Pessoa Jurídica" in text or "Apenas PJ" in text:
            lot["permitido_para"] = "PJ"
        else:
            lot["permitido_para"] = "PF/PJ"  # Assume

        # Items (quantity + description)
        items = []
        item_patterns = [
            r"(\d+)\s*(?:un|unidade|und|x)\s*(.+?)(?:\n|$)",
            r"(\d+)\s*(?:PAR|PC|CX|LT|KG)\s*(.+?)(?:\n|$)",
        ]
        for pattern in item_patterns:
            for match in re.finditer(pattern, text):
                qty = int(match.group(1))
                desc = match.group(2).strip()
                if len(desc) > 3 and qty <= 10000:  # Sanity check
                    items.append({"quantidade": qty, "descricao": desc})

        if items:
            lot["raw_data"] = {"itens": items}
            lot["total_itens"] = sum(i["quantidade"] for i in items)

        return lot
