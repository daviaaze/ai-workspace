"""Scheduled tasks — leilão pipeline (DB-task dispatch handlers).

These functions are called by ``scheduler.run_scheduled_db_task`` when a
DB task with ``type = "leilao_pipeline"`` is due.  The tasks table entry
is registered via ``aiw leilao setup-schedule`` (see ``cli/_leilao.py``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai_workspace.leilao_radar import Config
from ai_workspace.leilao_radar.storage.database import Database


def leilao_pipeline_task(db_url: str | None = None) -> dict[str, Any]:
    """Run all due leilão sources and store results.

    Reads the SQLite ``sources`` table to find active sources whose
    ``check_interval_hours`` has elapsed since ``last_scraped_at``.
    Each due source is scraped and results upserted into the leilão DB.
    """
    config = Config.from_env()
    db = Database(config)

    due_sources = db.get_due_sources()

    # ── Map source name → source class (lazy imports) ──────────────
    from ai_workspace.leilao_radar.sources import (  # noqa: lazy
        BancoDoBrasilLeiloes,
        CaixaImoveis,
        LeilaoNet,
        LeiloesJudiciais,
        PRFLeiloes,
        PoliciaFederalLeiloes,
        ReceitaFederalSLE,
        SefazLeiloes,
    )

    SOURCE_CLASSES: dict[str, type] = {
        "leilao_net": LeilaoNet,
        "receita_federal_sle": ReceitaFederalSLE,
        "caixa_imoveis": CaixaImoveis,
        "bb_leiloes": BancoDoBrasilLeiloes,
        "pf_leiloes": PoliciaFederalLeiloes,
        "prf_leiloes": PRFLeiloes,
        "leiloes_judiciais": LeiloesJudiciais,
        "sefaz_leiloes": SefazLeiloes,
    }

    results: list[dict[str, Any]] = []
    total_lots = 0
    total_errors = 0

    for src in due_sources:
        name = src["name"]
        cls = SOURCE_CLASSES.get(name)
        if cls is None:
            results.append({"source": name, "status": "skipped", "reason": "no handler"})
            continue

        source = cls(source_id=src["id"])
        t0 = datetime.now()
        try:
            scrape_result = source.scrape()
            elapsed_ms = int((datetime.now() - t0).total_seconds() * 1000)

            # Upsert results
            for edital in scrape_result.editais:
                db.upsert_edital(edital)
            for lote in scrape_result.lotes:
                db.upsert_lote(lote)

            status = "success" if not scrape_result.errors else "partial"
            error_msg = "; ".join(scrape_result.errors) if scrape_result.errors else None
            if error_msg:
                total_errors += len(scrape_result.errors)

            db.log_scrape(
                source_id=src["id"],
                status=status,
                lots_found=len(scrape_result.lotes),
                lots_new=len(scrape_result.editais),
                error=error_msg,
                duration_ms=elapsed_ms,
            )
            db.update_last_scraped(src["id"])

            total_lots += len(scrape_result.lotes)
            results.append({
                "source": name,
                "status": status,
                "lots": len(scrape_result.lotes),
                "editais": len(scrape_result.editais),
                "duration_ms": elapsed_ms,
                "errors": len(scrape_result.errors) if scrape_result.errors else 0,
            })
        except Exception as exc:
            elapsed_ms = int((datetime.now() - t0).total_seconds() * 1000)
            db.log_scrape(
                source_id=src["id"],
                status="error",
                lots_found=0,
                lots_new=0,
                error=str(exc),
                duration_ms=elapsed_ms,
            )
            total_errors += 1
            results.append({"source": name, "status": "error", "error": str(exc)})

    # ── Mirror closed lots to pgvector ──────────────────────────────
    try:
        from ai_workspace.leilao_radar.knowledge_mirror import mirror_closed_lots
        mirror = mirror_closed_lots(limit=100)
        results.append({
            "source": "mirror",
            "status": "done",
            "mirrored": mirror.get("mirrored", 0),
            "total": mirror.get("total", 0),
        })
    except Exception as exc:
        results.append({"source": "mirror", "status": "error", "error": str(exc)})

    return {
        "status": "completed",
        "sources_scraped": len(due_sources),
        "total_lots": total_lots,
        "total_errors": total_errors,
        "details": results,
    }
