"""
Leilão Scraper — Multi-source auction scraper for Brazilian government and bank auctions.

Follows the scraping hierarchy from PLANO_FASE3_SCRAPING.md:
1. Crawl4AI (JS rendering, markdown output, $0)
2. HeadlessBrowser (for complex SPAs, $0)
3. PaginatedScraper (for multi-page tables)

Each auction source is a pluggable class that knows:
- Which URLs to scrape
- How to navigate the site
- How to parse lots and prices
- How often to check for updates
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar, Optional, Type
from urllib.parse import urljoin, urlparse


logger = logging.getLogger("aiw.tools.leilao_scraper")

# ─── Database ───────────────────────────────────────────────────────────────

_DB_PATH = Path.home() / ".ai_workspace" / "leiloes.db"


def _get_db() -> sqlite3.Connection:
    """Get or create the leilões database."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leiloes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            edital TEXT,
            lote TEXT,
            titulo TEXT,
            descricao TEXT,
            preco_minimo REAL,
            tipo TEXT,
            situacao TEXT,
            permitido_para TEXT,
            local_retirada TEXT,
            data_propostas_ini TEXT,
            data_propostas_fim TEXT,
            data_pregao TEXT,
            moeda TEXT DEFAULT 'BRL',
            raw_data TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, source_url)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrapes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            status TEXT,
            lots_found INTEGER,
            error TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


# ─── Base Source ────────────────────────────────────────────────────────────

class LeilaoSource:
    """Base class for all auction sources."""

    # Metadata
    name: str = ""
    label: str = ""
    description: str = ""
    base_url: str = ""

    # Scheduling
    check_interval_hours: int = 24

    def __init__(self) -> None:
        self.session = None

    def get_urls_to_scrape(self) -> list[str]:
        """Return list of URLs this source should scrape."""
        raise NotImplementedError

    def parse_lots(self, html: str, url: str) -> list[dict[str, Any]]:
        """Parse auction lots from raw page content."""
        raise NotImplementedError

    def get_edital_urls(self) -> list[str]:
        """Return URLs of active/editais to monitor."""
        return []


# ─── Source: Receita Federal SLE ────────────────────────────────────────────

class ReceitaFederalSLE(LeilaoSource):
    """Receita Federal — Sistema de Leilão Eletrônico (SLE).

    URLs pattern:
      Main portal: https://www25.receita.fazenda.gov.br/sle-sociedade/portal
      Edital:      https://www25.receita.fazenda.gov.br/sle-sociedade/portal/edital/{orgao}/{seq}/{ano}
      Lote:        https://www25.receita.fazenda.gov.br/sle-sociedade/portal/edital/{orgao}/{seq}/{ano}/lote/{num}
    """

    name = "receita_federal_sle"
    label = "Receita Federal — SLE"
    description = (
        "Leilões eletrônicos de mercadorias apreendidas/abandonadas "
        "pela Receita Federal do Brasil. Eletrônicos, veículos, roupas, "
        "perfumes, bebidas, etc."
    )
    base_url = "https://www25.receita.fazenda.gov.br/sle-sociedade/portal"
    check_interval_hours = 6

    # Known active editais (orgao/seq/ano)
    KNOWN_EDITAIS: ClassVar[list[str]] = [
        # Brasília - Lotes Apple (iPhone 13, Xiaomi)
        "100100/3/2026",
        "100100/4/2026",
        # Belém - 191 lotes (eletrônicos, minerais)
        "200100/1/2026",
        # Curitiba - 272 lotes (maior edital)
        "900100/8/2026",
        # Rio de Janeiro
        "717600/4/2026",
        # Itaguaí
        "717800/2/2026",
        # Rio de Janeiro
        "717700/2/2026",
        "700100/8/2026",
        "700100/7/2026",
    ]

    def get_urls_to_scrape(self) -> list[str]:
        """Return all edital pages to scrape."""
        urls = [self.base_url]
        for edital in self.KNOWN_EDITAIS:
            urls.append(
                f"https://www25.receita.fazenda.gov.br/sle-sociedade/portal/edital/{edital}"
            )
        return urls

    def get_lote_urls(self, edital: str, total_lotes: int) -> list[str]:
        """Generate individual lot URLs for an edital."""
        base = f"https://www25.receita.fazenda.gov.br/sle-sociedade/portal/edital/{edital}/lote"
        return [f"{base}/{i}" for i in range(1, total_lotes + 1)]

    def parse_edital_list(self, text: str) -> list[dict[str, Any]]:
        """Parse the main portal page to find active editais."""
        editais = []
        # Find edital blocks
        pattern = r"(\d{6}/\d+/\d{4}).*?Propostas até:.*?(\d{2}/\d{2}/\d{4})"
        for match in re.finditer(pattern, text):
            editais.append({
                "edital": match.group(1),
                "data_fim": match.group(2),
            })
        return editais

    def parse_lots(self, text: str, url: str) -> list[dict[str, Any]]:
        """Parse lot listings from an edital page."""
        lots = []
        current_lote = None

        for line in text.split("\n"):
            line = line.strip()

            # Detect lot number
            lote_match = re.match(r"Lote\s+(\d+)", line)
            if lote_match:
                if current_lote:
                    lots.append(current_lote)
                current_lote = {
                    "lote": lote_match.group(1),
                    "source_url": url,
                    "source": self.name,
                }
                continue

            if current_lote:
                # Price
                price_match = re.search(r"Preço mínimo\s*:?\s*R?\$?\s*([\d.]+,\d{2})", line)
                if price_match:
                    current_lote["preco_minimo"] = float(
                        price_match.group(1).replace(".", "").replace(",", ".")
                    )
                    continue

                # Type
                tipo_match = re.match(r"Tipo:\s*(.+)", line)
                if tipo_match:
                    current_lote["tipo"] = tipo_match.group(1).strip()
                    continue

                # Situation
                sit_match = re.match(r"Situação:\s*(.+)", line)
                if sit_match:
                    current_lote["situacao"] = sit_match.group(1).strip()
                    continue

                # Permission
                if "Permite Pessoa Física" in line:
                    current_lote["permitido_para"] = "PF/PJ"
                elif "Permite Pessoa Jurídica" in line and "Permite Pessoa Física" not in line:
                    current_lote["permitido_para"] = "PJ"

        if current_lote:
            lots.append(current_lote)

        return lots

    def parse_lote_detail(self, text: str, url: str) -> dict[str, Any]:
        """Parse detailed lot information from a lot page."""
        detail: dict[str, Any] = {
            "source_url": url,
            "source": self.name,
        }

        # Extract lot number from URL
        lote_match = re.search(r"/lote/(\d+)", url)
        if lote_match:
            detail["lote"] = lote_match.group(1)

        # Extract edital from URL
        edital_match = re.search(r"edital/([\d/]+)/lote", url)
        if edital_match:
            detail["edital"] = edital_match.group(1)

        # Price
        price_match = re.search(r"Preço Mínimo:\s*R?\$?\s*([\d.]+,\d{2})", text)
        if price_match:
            detail["preco_minimo"] = float(
                price_match.group(1).replace(".", "").replace(",", ".")
            )

        # Type
        tipo_match = re.search(r"Tipo:\s*(.+)", text)
        if tipo_match:
            detail["tipo"] = tipo_match.group(1).strip()

        # Status
        sit_match = re.search(r"Situação do Lote:\s*(.+)", text)
        if sit_match:
            detail["situacao"] = sit_match.group(1).strip()

        # Extract merchandise items (quantities and descriptions)
        items = []
        item_pattern = r"(\d+)\s+un\s+(.+?)(?:////|$)"
        for item_match in re.finditer(item_pattern, text):
            items.append({
                "quantidade": int(item_match.group(1)),
                "descricao": item_match.group(2).strip(),
            })

        if items:
            detail["itens"] = items
            detail["total_itens"] = sum(i["quantidade"] for i in items)

        return detail


# ─── Source: CAIXA (Imóveis) ────────────────────────────────────────────────

class CaixaImoveis(LeilaoSource):
    """CAIXA Econômica Federal — Venda de Imóveis.

    Imóveis retomados (alienação fiduciária) com descontos de 30-60%.
    """

    name = "caixa_imoveis"
    label = "CAIXA — Venda de Imóveis"
    description = (
        "Imóveis residenciais e comerciais retomados pela CAIXA. "
        "Descontos de 30% a 60% abaixo do valor de mercado. "
        "Financiamento próprio da CAIXA disponível."
    )
    base_url = "https://venda-imoveis.caixa.gov.br"
    check_interval_hours = 24

    SEARCH_URLS: ClassVar[list[str]] = [
        "https://venda-imoveis.caixa.gov.br/listaweb/ListaImoveis.htm?Tipo=1&Regiao=SE",
        "https://venda-imoveis.caixa.gov.br/listaweb/ListaImoveis.htm?Tipo=1&Regiao=SUL",
        "https://venda-imoveis.caixa.gov.br/listaweb/ListaImoveis.htm?Tipo=1&Regiao=CO",
        "https://venda-imoveis.caixa.gov.br/listaweb/ListaImoveis.htm?Tipo=1&Regiao=NE",
        "https://venda-imoveis.caixa.gov.br/listaweb/ListaImoveis.htm?Tipo=1&Regiao=N",
    ]

    def get_urls_to_scrape(self) -> list[str]:
        return self.SEARCH_URLS

    def parse_lots(self, text: str, url: str) -> list[dict[str, Any]]:
        """Parse CAIXA property listings."""
        lots = []
        # Each property is typically in a card/table
        # Pattern: address, price, discount
        prop_patterns = re.finditer(
            r"(?:R\$\s*([\d.]+,\d{2}))",
            text
        )
        # CAIXA site is JS-heavy, likely needs HeadlessBrowser
        # For now, return placeholder — actual parsing requires browser rendering
        return lots


# ─── Source: Banco do Brasil ────────────────────────────────────────────────

class BancoDoBrasilLeiloes(LeilaoSource):
    """Banco do Brasil — Leilões de bens retomados."""

    name = "bb_leiloes"
    label = "Banco do Brasil — Leilões"
    description = (
        "Veículos, imóveis, máquinas agrícolas retomados pelo BB. "
        "Descontos de 20% a 50%."
    )
    base_url = "https://www.bb.com.br/site/leiloes/"
    check_interval_hours = 24

    def get_urls_to_scrape(self) -> list[str]:
        return [
            "https://www.bb.com.br/site/leiloes/",
            "https://www.bb.com.br/site/leiloes/imoveis/",
            "https://www.bb.com.br/site/leiloes/veiculos/",
        ]

    def parse_lots(self, text: str, url: str) -> list[dict[str, Any]]:
        """Parse BB auction listings."""
        return []


# ─── Source: Polícia Federal ────────────────────────────────────────────────

class PoliciaFederalLeiloes(LeilaoSource):
    """Polícia Federal — Leilões de bens apreendidos."""

    name = "pf_leiloes"
    label = "Polícia Federal — Leilões"
    description = (
        "Veículos, equipamentos eletrônicos, bens de luxo, "
        "joias e outros bens apreendidos pela Polícia Federal."
    )
    base_url = "https://www.gov.br/pf/pt-br/assuntos/leiloes"
    check_interval_hours = 12

    def get_urls_to_scrape(self) -> list[str]:
        return [
            "https://www.gov.br/pf/pt-br/assuntos/leiloes",
            "https://www.gov.br/pf/pt-br/assuntos/leiloes/leiloes-de-veiculos",
        ]

    def parse_lots(self, text: str, url: str) -> list[dict[str, Any]]:
        """Parse PF auction listings."""
        lots = []
        return lots


# ─── Source: PRF ────────────────────────────────────────────────────────────

class PRFLeiloes(LeilaoSource):
    """Polícia Rodoviária Federal — Leilões de veículos."""

    name = "prf_leiloes"
    label = "PRF — Leilões de Veículos"
    description = (
        "Veículos apreendidos pela PRF (infrações de trânsito). "
        "Preços atrativos, documentação regularizada."
    )
    base_url = "https://www.gov.br/prf/pt-br/leiloes"
    check_interval_hours = 12

    def get_urls_to_scrape(self) -> list[str]:
        return ["https://www.gov.br/prf/pt-br/leiloes"]

    def parse_lots(self, text: str, url: str) -> list[dict[str, Any]]:
        return []


# ─── Source: Leilões Judiciais ──────────────────────────────────────────────

class LeiloesJudiciais(LeilaoSource):
    """Tribunais de Justiça — Leilões judiciais.

    Agrega múltiplos tribunais e plataformas de leilão judicial.
    """

    name = "leiloes_judiciais"
    label = "Leilões Judiciais"
    description = (
        "Imóveis, veículos, empresas em recuperação judicial. "
        "Lances a partir de 50% do valor de avaliação. "
        "Plataformas: Justiça Leilão, Lance Judicial, TJs."
    )
    base_url = "https://www.justica-leilao.com.br"
    check_interval_hours = 12

    PLATFORMS: ClassVar[list[dict[str, str]]] = [
        {"name": "Justiça Leilão", "url": "https://www.justica-leilao.com.br/"},
        {"name": "Lance Judicial", "url": "https://www.lancejudicial.com.br/"},
        {"name": "TJ-SP (SIEJ)", "url": "https://siej.tjsp.jus.br/"},
        {"name": "TJ-RJ", "url": "https://www.tjrj.jus.br/leiloes"},
        {"name": "TJ-MG", "url": "https://www.tjmg.jus.br/leiloes"},
        {"name": "TJ-RS", "url": "https://www.tjrs.jus.br/leiloes"},
    ]

    def get_urls_to_scrape(self) -> list[str]:
        return [p["url"] for p in self.PLATFORMS]

    def parse_lots(self, text: str, url: str) -> list[dict[str, Any]]:
        return []


# ─── Source: SEFAZ (Receita Estadual) ───────────────────────────────────────

class SefazLeiloes(LeilaoSource):
    """Secretarias Estaduais da Fazenda — Leilões de mercadorias apreendidas."""

    name = "sefaz_leiloes"
    label = "SEFAZ — Leilões Estaduais"
    description = (
        "Mercadorias apreendidas por sonegação fiscal (ICMS). "
        "Cada estado tem seu próprio sistema. Eletrônicos, veículos, "
        "mercadorias em geral."
    )
    base_url = "https://www.leilao.fazenda.sp.gov.br"
    check_interval_hours = 24

    ESTADOS: ClassVar[list[dict[str, str]]] = [
        {"uf": "SP", "nome": "São Paulo", "url": "https://www.leilao.fazenda.sp.gov.br/"},
        {"uf": "RJ", "nome": "Rio de Janeiro", "url": "https://www.fazenda.rj.gov.br/leiloes/"},
        {"uf": "MG", "nome": "Minas Gerais", "url": "https://www.fazenda.mg.gov.br/leiloes/"},
        {"uf": "RS", "nome": "Rio Grande do Sul", "url": "https://www.sefaz.rs.gov.br/leiloes/"},
        {"uf": "PR", "nome": "Paraná", "url": "https://www.fazenda.pr.gov.br/leiloes/"},
        {"uf": "BA", "nome": "Bahia", "url": "https://www.sefaz.ba.gov.br/leiloes/"},
    ]

    def get_urls_to_scrape(self) -> list[str]:
        return [e["url"] for e in self.ESTADOS]

    def parse_lots(self, text: str, url: str) -> list[dict[str, Any]]:
        return []


# ─── Source Registry ────────────────────────────────────────────────────────

SOURCES: dict[str, type[LeilaoSource]] = {
    "receita_federal_sle": ReceitaFederalSLE,
    "caixa_imoveis": CaixaImoveis,
    "bb_leiloes": BancoDoBrasilLeiloes,
    "pf_leiloes": PoliciaFederalLeiloes,
    "prf_leiloes": PRFLeiloes,
    "leiloes_judiciais": LeiloesJudiciais,
    "sefaz_leiloes": SefazLeiloes,
}


def get_source(name: str) -> LeilaoSource:
    """Get a source instance by name."""
    cls = SOURCES.get(name)
    if not cls:
        raise ValueError(f"Unknown source: {name}. Available: {list(SOURCES.keys())}")
    return cls()


def get_all_sources() -> list[LeilaoSource]:
    """Get instances of all sources."""
    return [cls() for cls in SOURCES.values()]


# ─── Scraper Engine ─────────────────────────────────────────────────────────

class LeilaoScraperEngine:
    """Orchestrates scraping across multiple auction sources."""

    def __init__(self) -> None:
        self.db = _get_db()

    def scrape_source(self, source: LeilaoSource, use_cache: bool = True) -> dict[str, Any]:
        """Scrape a single source and store results."""
        from ai_workspace.tools.scraping_chain import ScrapingChainTool

        scraper = ScrapingChainTool()
        urls = source.get_urls_to_scrape()
        all_lots: list[dict[str, Any]] = []
        errors: list[str] = []

        for url in urls:
            try:
                content = scraper._run(url=url)
                if not content or content.startswith("Error") or content.startswith("All "):
                    errors.append(f"{url}: scraper returned no content")
                    continue

                lots = source.parse_lots(content, url)
                all_lots.extend(lots)

            except Exception as e:
                errors.append(f"{url}: {e}")
                logger.warning("Failed to scrape %s: %s", url, e)

        # For Receita Federal, also scrape individual lot pages
        if isinstance(source, ReceitaFederalSLE):
            for known_edital in source.KNOWN_EDITAIS:
                # Try to get lot detail pages from any found lot numbers
                lot_numbers = set()
                for lot in all_lots:
                    if "lote" in lot:
                        lot_numbers.add(int(lot["lote"]))

                # If no lots parsed yet, try a reasonable range
                if not lot_numbers:
                    # Default ranges per edital
                    ranges = {
                        "100100/3/2026": range(1, 24),
                        "100100/4/2026": range(1, 200),
                        "200100/1/2026": range(1, 192),
                        "900100/8/2026": range(1, 273),
                        "717600/4/2026": range(1, 41),
                        "717800/2/2026": range(1, 17),
                        "717700/2/2026": range(1, 11),
                    }
                    if known_edital in ranges:
                        lot_numbers = ranges[known_edital]

                for lot_num in lot_numbers:
                    lote_url = (
                        f"https://www25.receita.fazenda.gov.br/sle-sociedade/"
                        f"portal/edital/{known_edital}/lote/{lot_num}"
                    )
                    try:
                        content = scraper._run(url=lote_url)
                        if content and not content.startswith("Error"):
                            detail = source.parse_lote_detail(content, lote_url)
                            detail["source_url"] = lote_url
                            all_lots.append(detail)
                    except Exception:
                        pass

        # Store in database
        stored = 0
        for lot in all_lots:
            try:
                self.db.execute("""
                    INSERT OR REPLACE INTO leiloes
                    (source, source_url, edital, lote, titulo, descricao,
                     preco_minimo, tipo, situacao, permitido_para, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source.name,
                    lot.get("source_url", ""),
                    lot.get("edital", ""),
                    str(lot.get("lote", "")),
                    lot.get("titulo", ""),
                    "",  # descricao - could be built from items
                    lot.get("preco_minimo", 0),
                    lot.get("tipo", ""),
                    lot.get("situacao", ""),
                    lot.get("permitido_para", ""),
                    json.dumps(lot, default=str, ensure_ascii=False),
                ))
                stored += 1
            except Exception as e:
                logger.warning("DB insert error: %s", e)

        self.db.commit()

        # Log scrape
        self.db.execute("""
            INSERT INTO scrapes_log (source, status, lots_found, error)
            VALUES (?, ?, ?, ?)
        """, (
            source.name,
            "error" if errors else "success",
            len(all_lots),
            "; ".join(errors[:5]) if errors else None,
        ))
        self.db.commit()

        return {
            "source": source.name,
            "urls_scraped": len(urls),
            "lots_found": len(all_lots),
            "lots_stored": stored,
            "errors": errors,
            "sources_available": list(SOURCES.keys()),
        }

    def scrape_all(self, sources: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """Scrape all specified sources (or all if none specified)."""
        if sources:
            source_instances = [get_source(s) for s in sources]
        else:
            source_instances = get_all_sources()

        results = []
        for src in source_instances:
            logger.info("Scraping source: %s", src.name)
            result = self.scrape_source(src)
            results.append(result)

        return results

    def query(
        self,
        source: Optional[str] = None,
        tipo: Optional[str] = None,
        preco_max: Optional[float] = None,
        preco_min: Optional[float] = None,
        situacao: Optional[str] = None,
        permitido_pf: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query stored auctions with filters."""
        conditions = []
        params: list[Any] = []

        if source:
            conditions.append("source = ?")
            params.append(source)
        if tipo:
            conditions.append("tipo LIKE ?")
            params.append(f"%{tipo}%")
        if preco_max is not None:
            conditions.append("preco_minimo <= ?")
            params.append(preco_max)
        if preco_min is not None:
            conditions.append("preco_minimo >= ?")
            params.append(preco_min)
        if situacao:
            conditions.append("situacao LIKE ?")
            params.append(f"%{situacao}%")
        if permitido_pf:
            conditions.append("permitido_para LIKE '%PF%'")

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = self.db.execute(
            f"SELECT * FROM leiloes WHERE {where} ORDER BY preco_minimo ASC LIMIT ?",
            (*params, limit)
        ).fetchall()

        results = []
        for row in rows:
            lot = dict(row)
            if lot.get("raw_data"):
                try:
                    lot["raw_data"] = json.loads(lot["raw_data"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(lot)

        return results

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics from stored auctions."""
        total = self.db.execute("SELECT COUNT(*) FROM leiloes").fetchone()[0]
        by_source = self.db.execute(
            "SELECT source, COUNT(*) FROM leiloes GROUP BY source"
        ).fetchall()
        by_tipo = self.db.execute(
            "SELECT tipo, COUNT(*) FROM leiloes WHERE tipo != '' GROUP BY tipo ORDER BY COUNT(*) DESC"
        ).fetchall()
        last_scrape = self.db.execute(
            "SELECT source, MAX(scraped_at) FROM scrapes_log GROUP BY source"
        ).fetchall()

        return {
            "total_lots": total,
            "by_source": dict(by_source),
            "by_type": dict(by_tipo[:20]),
            "last_scrape": dict(last_scrape),
            "sources_available": list(SOURCES.keys()),
        }

    def export_json(self, path: Optional[str] = None) -> str:
        """Export all auctions to JSON."""
        rows = self.db.execute("SELECT * FROM leiloes ORDER BY scraped_at DESC").fetchall()
        data = [dict(r) for r in rows]
        output = json.dumps(data, ensure_ascii=False, default=str, indent=2)

        if path:
            Path(path).write_text(output, encoding="utf-8")
            return f"Exported {len(data)} lots to {path}"
        return output

    def find_best_roi(
        self,
        preco_max: float = 50000,
        tipos_interesse: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Find lots with best potential ROI."""
        if tipos_interesse is None:
            tipos_interesse = [
                "CELULAR/ACESSÓRIO", "INFORMÁTICA", "VIDEOGAME",
                "ELETRÔNICO", "RELÓGIO", "INSTRUMENTO MUSICAL",
            ]

        conditions = ["preco_minimo > 0 AND preco_minimo <= ?"]
        params: list[Any] = [preco_max]

        tipo_conditions = " OR ".join("tipo LIKE ?" for _ in tipos_interesse)
        conditions.append(f"({tipo_conditions})")
        params.extend(f"%{t}%" for t in tipos_interesse)

        rows = self.db.execute(
            f"SELECT * FROM leiloes WHERE {' AND '.join(conditions)} ORDER BY preco_minimo ASC",
            params
        ).fetchall()

        return [dict(r) for r in rows]


# ─── CrewAI Tool ────────────────────────────────────────────────────────────

