"""Parser for Leilão.net — auction aggregator.

Scrapes the main search page to find auctions from multiple sources
(Caixa, BB, Receita Federal, PF, PRF, TJs, etc.).
"""

from __future__ import annotations

import re
import time
from typing import Any

from selectolax.parser import HTMLParser

from ai_workspace.leilao_radar.sources.base import BaseSource, SourceResult


class LeilaoNet(BaseSource):
    """Leilão.net — agregador de leilões."""

    name = "leilao_net"
    label = "Leilão.net (agregador)"
    url = "https://www.leilao.net/"
    tier = "A"
    source_type = "agregador"
    check_interval_hours = 12

    SEARCH_URLS = [
        "https://www.leilao.net/",
        "https://www.leilao.net/leiloes/sp",
        "https://www.leilao.net/leiloes/pr",
        "https://www.leilao.net/leiloes/rj",
        "https://www.leilao.net/leiloes/df",
    ]

    CATEGORY_URLS = [
        "https://www.leilao.net/leiloes/categoria/eletronicos",
        "https://www.leilao.net/leiloes/categoria/informatica",
        "https://www.leilao.net/leiloes/categoria/veiculos",
        "https://www.leilao.net/leiloes/categoria/perfumes",
        "https://www.leilao.net/leiloes/categoria/brinquedos",
    ]

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)

    def scrape(self) -> SourceResult:
        """Scrape Leilão.net for active auctions."""
        result = SourceResult()
        result.source_name = self.name
        start = time.monotonic()

        # Scrape general search pages
        all_urls = self.SEARCH_URLS + self.CATEGORY_URLS
        seen_urls: set[str] = set()

        for url in all_urls:
            html = self._fetch_html(url)
            if html is None:
                result.errors.append(f"{url}: fetch failed")
                continue
            result.http_requests += 1

            lots = self._parse_listing(html, url)
            for lot in lots:
                lot_url = lot.get("url", "")
                if lot_url and lot_url not in seen_urls:
                    seen_urls.add(lot_url)
                    result.lotes.append(lot)

            time.sleep(1.0)  # Rate limit

        # Try individual lot pages for more detail
        for lot in result.lotes[:50]:  # Limit to avoid too many requests
            lot_url = lot.get("url", "")
            if lot_url and "leilao.net" in lot_url:
                html = self._fetch_html(lot_url)
                result.http_requests += 1
                if html:
                    detail = self._parse_lote_detail(html)
                    lot.update(detail)
                time.sleep(0.5)

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def _parse_listing(self, html: str, source_url: str) -> list[dict[str, Any]]:
        """Parse auction listing page."""
        parser = HTMLParser(html)
        lots: list[dict[str, Any]] = []

        # Try multiple card/row selectors (Leilão.net may vary structure)
        cards = (
            parser.css("article.auction-card")
            or parser.css(".leilao-card")
            or parser.css("[class*='leilao']")
            or parser.css("tr[class*='leilao']")
            or parser.css(".card")
        )

        for card in cards:
            try:
                lot = self._parse_card(card, source_url)
                if lot.get("preco_minimo") and lot["preco_minimo"] > 0:
                    lots.append(lot)
            except Exception:
                continue

        # Fallback: parse from raw text if no structured cards found
        if not lots:
            text = parser.body.text() if parser.body else html
            lots = self._parse_from_text(text, source_url)

        return lots

    def _parse_card(self, card, source_url: str) -> dict[str, Any]:
        """Parse a single auction card element."""
        lot: dict[str, Any] = {
            "source_url": source_url,
            "titulo": "",
            "descricao": "",
            "tipo": "",
        }

        # Title / description
        for sel in ["h2", "h3", "h4", ".titulo", ".title", ".nome", "[class*='titulo']"]:
            el = card.css_first(sel)
            if el and el.text(strip=True):
                lot["titulo"] = el.text(strip=True)
                break

        # Extract price from text
        full_text = card.text(strip=True)
        price = self._extract_price(full_text)
        if price:
            lot["preco_minimo"] = price

        # Links
        link = card.css_first("a[href]")
        if link:
            href = link.attributes.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.leilao.net" + href
            lot["url"] = href

        # Type category
        lot["categoria_normalizada"] = self._normalize_tipo(lot.get("titulo", ""))

        return lot

    def _parse_from_text(self, text: str, source_url: str) -> list[dict[str, Any]]:
        """Fallback: parse lots from raw page text."""
        lots: list[dict[str, Any]] = []
        lines = text.split("\n")
        current: dict[str, Any] | None = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for patterns like "Lote 123" or auction titles
            if re.match(r"^(Lote\s+\d+|Leilão|Edital)", line) and len(line) < 200:
                if current:
                    lots.append(current)
                current = {
                    "titulo": line,
                    "source_url": source_url,
                    "tipo": "",
                }
                continue

            if current:
                price = self._extract_price(line)
                if price:
                    current["preco_minimo"] = price

        if current:
            lots.append(current)

        return lots

    def _parse_lote_detail(self, html: str) -> dict[str, Any]:
        """Parse individual lot detail page for more info."""
        parser = HTMLParser(html)
        detail: dict[str, Any] = {}

        text = parser.body.text() if parser.body else html

        # Situation
        sit_match = re.search(r"(Situação|Situacao|Status):\s*(.+)", text)
        if sit_match:
            detail["situacao"] = sit_match.group(2).strip()

        # Location
        loc_match = re.search(r"(Local|Cidade|Retirada):\s*(.+)", text)
        if loc_match:
            detail["local_retirada"] = loc_match.group(2).strip()

        # Permission
        if "Pessoa Física" in text or "PF" in text:
            detail["permitido_para"] = "PF/PJ"
        elif "Pessoa Jurídica" in text or "PJ" in text:
            detail["permitido_para"] = "PJ"

        # Items count
        qty_match = re.search(r"(\d+)\s*(?:item|itens|lote|lotes)", text, re.IGNORECASE)
        if qty_match:
            detail["total_itens"] = int(qty_match.group(1))

        return detail
