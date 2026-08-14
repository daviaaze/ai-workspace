"""CareerOps MVP — tracker (SQLite)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS vagas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa TEXT NOT NULL,
    titulo TEXT NOT NULL,
    url TEXT UNIQUE,
    fonte TEXT,
    data_descoberta TEXT NOT NULL,
    score INTEGER,
    justificativa TEXT,
    status TEXT NOT NULL DEFAULT 'nova',
    rate TEXT,
    contato TEXT,
    data_submissao TEXT,
    data_followup TEXT,
    data_resposta TEXT,
    pacote_path TEXT,
    notas TEXT,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vaga_id INTEGER,
    tipo TEXT NOT NULL,
    detalhe TEXT,
    criado_em TEXT NOT NULL,
    FOREIGN KEY (vaga_id) REFERENCES vagas(id)
);

CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte TEXT NOT NULL,
    query TEXT,
    ultima_verificao TEXT,
    status TEXT DEFAULT 'ativo'
);

CREATE INDEX IF NOT EXISTS idx_vagas_status ON vagas(status);
CREATE INDEX IF NOT EXISTS idx_vagas_score ON vagas(score);
CREATE INDEX IF NOT EXISTS idx_eventos_vaga ON eventos(vaga_id);
"""

STATUS_FLOW = [
    "nova", "scored", "descartada", "avaliar", "preparando",
    "aguardando_aprovacao", "aprovada", "submetida", "sem_retorno",
    "em_conversa", "rejeitada", "oferta", "aceita", "recusada",
]


class Tracker:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def add_vaga(
        self,
        empresa: str,
        titulo: str,
        url: str | None = None,
        fonte: str | None = None,
        score: int | None = None,
        justificativa: str | None = None,
        status: str = "nova",
        rate: str | None = None,
        notas: str | None = None,
    ) -> int:
        now = self._now()
        with self._conn() as c:
            try:
                cur = c.execute(
                    """INSERT INTO vagas
                       (empresa, titulo, url, fonte, data_descoberta, score,
                        justificativa, status, rate, notas, criado_em, atualizado_em)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (empresa, titulo, url, fonte, now, score, justificativa,
                     status, rate, notas, now, now),
                )
                return cur.lastrowid
            except sqlite3.IntegrityError:
                row = c.execute(
                    "SELECT id FROM vagas WHERE url = ?", (url,)
                ).fetchone()
                return row["id"] if row else -1

    def log_event(self, vaga_id: int | None, tipo: str, detalhe: str | None = None) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO eventos (vaga_id, tipo, detalhe, criado_em) VALUES (?, ?, ?, ?)",
                (vaga_id, tipo, detalhe, self._now()),
            )

    def update_status(self, vaga_id: int, status: str, **fields: Any) -> None:
        if status not in STATUS_FLOW:
            raise ValueError(f"Status invalido: {status}. Validos: {STATUS_FLOW}")
        fields["status"] = status
        fields["atualizado_em"] = self._now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [vaga_id]
        with self._conn() as c:
            c.execute(f"UPDATE vagas SET {cols} WHERE id = ?", vals)
        self.log_event(vaga_id, "status_change", f"-> {status}")

    def list_vagas(self, status: str | None = None, min_score: int | None = None) -> list[dict[str, Any]]:
        q = "SELECT * FROM vagas WHERE 1=1"
        params: list[Any] = []
        if status:
            q += " AND status = ?"
            params.append(status)
        if min_score is not None:
            q += " AND score >= ?"
            params.append(min_score)
        q += " ORDER BY data_descoberta DESC"
        with self._conn() as c:
            return [dict(r) for r in c.execute(q, params).fetchall()]

    def get_vaga(self, vaga_id: int) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM vagas WHERE id = ?", (vaga_id,)).fetchone()
        return dict(row) if row else None

    def stats(self) -> dict[str, Any]:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM vagas").fetchone()[0]
            por_status = {
                r["status"]: r["cnt"]
                for r in c.execute(
                    "SELECT status, COUNT(*) cnt FROM vagas GROUP BY status"
                )
            }
            avg_score = c.execute(
                "SELECT AVG(score) FROM vagas WHERE score IS NOT NULL"
            ).fetchone()[0]
        return {"total": total, "por_status": por_status, "avg_score": avg_score}
