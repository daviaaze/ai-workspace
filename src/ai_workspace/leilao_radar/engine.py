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

# SOURCES previously held 7 LeilaoSource subclasses here. All have been
# migrated to BaseSource subclasses in sources/ (caixa_imoveis, bb_leiloes,
# pf_leiloes, prf_leiloes, leiloes_judiciais, sefaz_leiloes) and are now
# scraped via the scheduled pipeline (tasks.py). The engine-based
# ReceitaFederalSLE was also migrated.
SOURCES: dict[str, type[LeilaoSource]] = {}


def get_source(name: str) -> LeilaoSource:
    """Get a source instance by name.

    .. note::

       Most sources have been migrated to ``BaseSource`` subclasses in
       ``sources/`` and are scraped via the scheduled pipeline. This
       lookup is only for legacy engine-based sources.
    """
    cls = SOURCES.get(name)
    if not cls:
        raise ValueError(f"Unknown engine source: {name}. Available: {list(SOURCES.keys())}")
    return cls()


def get_all_sources() -> list[LeilaoSource]:
    """Get instances of all engine-based sources."""
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

