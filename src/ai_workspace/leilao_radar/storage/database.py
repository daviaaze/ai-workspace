"""Database connection and query helpers."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

from ai_workspace.leilao_radar.config import Config
from ai_workspace.leilao_radar.storage.schema import SCHEMA_SQL


class Database:
    """SQLite database manager."""

    def __init__(self, config: Config):
        self.db_path = config.db_path
        self.config = config
        self._init_db()

    def _init_db(self):
        """Initialize database with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection as context manager."""
        c = self._connect()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    # ─── Sources ─────────────────────────────────────────────────────────

    def get_active_sources(self) -> list[dict[str, Any]]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT * FROM sources WHERE is_active = 1 ORDER BY check_interval_hours"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_due_sources(self) -> list[dict[str, Any]]:
        """Get active sources that are due for scraping based on their cadence.

        A source is due if it has never been scraped (``last_scraped_at IS NULL``)
        or if ``last_scraped_at + check_interval_hours <= now``.
        """
        with self.conn() as c:
            rows = c.execute("""
                SELECT * FROM sources
                WHERE is_active = 1
                  AND (last_scraped_at IS NULL
                       OR datetime(last_scraped_at, '+' || check_interval_hours || ' hours')
                          <= datetime('now'))
                ORDER BY check_interval_hours
            """).fetchall()
            return [dict(r) for r in rows]

    def update_last_scraped(self, source_id: int):
        with self.conn() as c:
            c.execute(
                "UPDATE sources SET last_scraped_at = ? WHERE id = ?",
                (datetime.now(), source_id),
            )

    # ─── Editais ─────────────────────────────────────────────────────────

    def upsert_edital(self, edital: dict[str, Any]) -> Optional[int]:
        """Insert or update an edital. Returns edital id."""
        with self.conn() as c:
            cur = c.execute("""
                INSERT INTO editais
                    (source_id, edital_number, title, location, end_propostas,
                     data_pregao, total_lotes, permitido_pf, permitido_pj, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, edital_number) DO UPDATE SET
                    title = excluded.title,
                    location = excluded.location,
                    end_propostas = excluded.end_propostas,
                    data_pregao = excluded.data_pregao,
                    total_lotes = excluded.total_lotes,
                    url = excluded.url
            """, (
                edital.get("source_id"),
                edital.get("edital_number"),
                edital.get("title", ""),
                edital.get("location", ""),
                edital.get("end_propostas"),
                edital.get("data_pregao"),
                edital.get("total_lotes"),
                edital.get("permitido_pf", 1),
                edital.get("permitido_pj", 1),
                edital.get("url", ""),
            ))
            return cur.lastrowid

    # ─── Lotes ───────────────────────────────────────────────────────────

    def upsert_lote(self, lote: dict[str, Any]) -> Optional[int]:
        """Insert or update a lot. Returns lote id."""
        with self.conn() as c:
            cur = c.execute("""
                INSERT INTO lotes
                    (edital_id, lote_number, titulo, descricao, preco_minimo,
                     tipo, situacao, permitido_para, local_retirada, total_itens,
                     confidence_level, confidence_score, raw_data, url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(edital_id, lote_number) DO UPDATE SET
                    titulo = excluded.titulo,
                    descricao = excluded.descricao,
                    preco_minimo = excluded.preco_minimo,
                    situacao = excluded.situacao,
                    raw_data = excluded.raw_data,
                    scraped_at = excluded.scraped_at
            """, (
                lote.get("edital_id"),
                lote.get("lote_number"),
                lote.get("titulo", ""),
                lote.get("descricao", ""),
                lote.get("preco_minimo", 0),
                lote.get("tipo", ""),
                lote.get("situacao", ""),
                lote.get("permitido_para", ""),
                lote.get("local_retirada", ""),
                lote.get("total_itens"),
                lote.get("confidence_level", "desconhecido"),
                lote.get("confidence_score", 0),
                json.dumps(lote.get("raw_data", {}), ensure_ascii=False, default=str),
                lote.get("url", ""),
                datetime.now(),
            ))
            return cur.lastrowid

    def get_lotes_to_analyze(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get lots that haven't been analyzed yet."""
        with self.conn() as c:
            rows = c.execute("""
                SELECT l.*, e.edital_number, e.location, s.name as source_name
                FROM lotes l
                JOIN editais e ON l.edital_id = e.id
                JOIN sources s ON e.source_id = s.id
                LEFT JOIN lote_analysis la ON l.id = la.lote_id
                WHERE la.lote_id IS NULL
                AND l.preco_minimo > 0
                ORDER BY l.preco_minimo ASC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_lotes_with_analysis(self, filters: Optional[dict] = None) -> list[dict[str, Any]]:
        """Get lots with their analysis results."""
        with self.conn() as c:
            query = """
                SELECT l.*, la.*, e.edital_number, e.location, e.end_propostas,
                       s.name as source_name, s.label as source_label
                FROM lotes l
                JOIN editais e ON l.edital_id = e.id
                JOIN sources s ON e.source_id = s.id
                JOIN lote_analysis la ON l.id = la.lote_id
                WHERE l.status = 'ativo'
            """
            params = []

            if filters:
                if filters.get("min_roi"):
                    query += " AND la.estimated_roi >= ?"
                    params.append(filters["min_roi"])
                if filters.get("max_preco"):
                    query += " AND l.preco_minimo <= ?"
                    params.append(filters["max_preco"])
                if filters.get("min_confidence"):
                    query += " AND la.confidence_score >= ?"
                    params.append(filters["min_confidence"])
                if filters.get("permitido_pf"):
                    query += " AND (l.permitido_para LIKE '%PF%' OR l.permitido_para IS NULL)"

            query += " ORDER BY la.estimated_roi_mensal DESC"

            rows = c.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # ─── Analysis ────────────────────────────────────────────────────────

    def save_analysis(self, analysis: dict[str, Any]):
        with self.conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO lote_analysis
                    (lote_id, estimated_market_value, estimated_roi, estimated_roi_mensal,
                     confidence, confidence_score, meses_para_vender,
                     ml_fee_estimate, shopee_fee_estimate, frete_estimate,
                     analyzed_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis["lote_id"],
                analysis.get("estimated_market_value"),
                analysis.get("estimated_roi"),
                analysis.get("estimated_roi_mensal"),
                analysis.get("confidence", "desconhecido"),
                analysis.get("confidence_score", 0),
                analysis.get("meses_para_vender"),
                analysis.get("ml_fee_estimate"),
                analysis.get("shopee_fee_estimate"),
                analysis.get("frete_estimate"),
                datetime.now(),
                analysis.get("notes", ""),
            ))

    # ─── Alerts ──────────────────────────────────────────────────────────

    def already_alerted_today(self, lote_id: int) -> bool:
        """Check if this lot was already alerted today (dedup)."""
        with self.conn() as c:
            row = c.execute("""
                SELECT id FROM alertas
                WHERE lote_id = ? AND DATE(created_at) = DATE('now')
                LIMIT 1
            """, (lote_id,)).fetchone()
            return row is not None

    def save_alerta(self, alerta: dict[str, Any]) -> int:
        with self.conn() as c:
            cur = c.execute("""
                INSERT INTO alertas
                    (lote_id, alert_type, message, created_at, channel, delivered)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alerta["lote_id"],
                alerta["alert_type"],
                alerta["message"],
                datetime.now(),
                alerta.get("channel", "telegram"),
                alerta.get("delivered", False),
            ))
            return cur.lastrowid

    def get_alertas_nao_enviados(self) -> list[dict[str, Any]]:
        with self.conn() as c:
            rows = c.execute("""
                SELECT a.*, l.titulo, l.preco_minimo
                FROM alertas a
                JOIN lotes l ON a.lote_id = l.id
                WHERE a.delivered = 0
                ORDER BY a.created_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def mark_alerta_enviado(self, alerta_id: int):
        with self.conn() as c:
            c.execute(
                "UPDATE alertas SET delivered = 1, sent_at = ? WHERE id = ?",
                (datetime.now(), alerta_id),
            )

    # ─── Logging ─────────────────────────────────────────────────────────

    def log_scrape(self, source_id: int, status: str, lots_found: int,
                   lots_new: int, error: Optional[str] = None, duration_ms: int = 0):
        with self.conn() as c:
            c.execute("""
                INSERT INTO scrape_log
                    (source_id, started_at, finished_at, status, lots_found,
                     lots_new, error, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_id,
                datetime.now(),
                datetime.now(),
                status,
                lots_found,
                lots_new,
                error,
                duration_ms,
            ))

    # ─── Statistics ──────────────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        with self.conn() as c:
            total_lotes = c.execute("SELECT COUNT(*) FROM lotes WHERE status='ativo'").fetchone()[0]
            total_editais = c.execute("SELECT COUNT(*) FROM editais WHERE status='ativo'").fetchone()[0]
            total_analisados = c.execute("SELECT COUNT(*) FROM lote_analysis").fetchone()[0]
            total_alertas = c.execute("SELECT COUNT(*) FROM alertas").fetchone()[0]

            by_source = dict(c.execute(
                "SELECT s.name, COUNT(*) FROM lotes l JOIN editais e ON l.edital_id=e.id "
                "JOIN sources s ON e.source_id=s.id WHERE l.status='ativo' GROUP BY s.name"
            ).fetchall())

            top_roi = c.execute("""
                SELECT l.titulo, l.preco_minimo, la.estimated_roi, la.estimated_roi_mensal,
                       la.confidence
                FROM lote_analysis la
                JOIN lotes l ON la.lote_id = l.id
                WHERE l.status='ativo'
                ORDER BY la.estimated_roi_mensal DESC
                LIMIT 10
            """).fetchall()

            return {
                "total_lotes": total_lotes,
                "total_editais": total_editais,
                "total_analisados": total_analisados,
                "total_alertas": total_alertas,
                "by_source": by_source,
                "top_roi": [dict(r) for r in top_roi],
            }
