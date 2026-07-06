#!/usr/bin/env python3
"""Leilão Radar CLI — entry point for the MVP.

Usage:
  leilao-radar scrape         Scrape all sources
  leilao-radar analyze        Analyze unprocessed lots
  leilao-radar digest         Generate and send daily digest
  leilao-radar run            Full pipeline: scrape → analyze → digest
  leilao-radar summary        Show database summary
  leilao-radar list [filters] List analyzed opportunities
  leilao-radar paper          Show paper trading opportunities
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from typing import Any

from ai_workspace.leilao_radar.config import Config
from ai_workspace.leilao_radar.storage.database import Database
from ai_workspace.leilao_radar.sources.receita_federal_sle import ReceitaFederalSLE
from ai_workspace.leilao_radar.sources.leilao_net import LeilaoNet
from ai_workspace.leilao_radar.analysis.roi_calculator import ROICalculator
from ai_workspace.leilao_radar.alerts.filters import AlertFilter
from ai_workspace.leilao_radar.alerts.telegram_bot import TelegramBot

logger = logging.getLogger("leilao_radar")


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_scrape(config: Config, db: Database):
    """Scrape all active sources."""
    print("🔍 Scraping sources...")

    # Get source IDs from DB
    sources_db = db.get_active_sources()
    source_map = {s["name"]: s["id"] for s in sources_db}

    results = []

    # Receita Federal SLE
    if "receita_federal_sle" in source_map:
        print("  📡 Receita Federal SLE...", end=" ", flush=True)
        sle = ReceitaFederalSLE(source_id=source_map["receita_federal_sle"])
        result = sle.scrape()

        if result.editais:
            for edital_rec in result.editais:
                edital_id = db.upsert_edital(edital_rec)
                if edital_id:
                    for lot in result.lotes:
                        if lot.get("edital_number") == edital_rec["edital_number"]:
                            lot["edital_id"] = edital_id
                            db.upsert_lote(lot)

        db.log_scrape(
            source_id=source_map["receita_federal_sle"],
            status="success" if result.success else "error",
            lots_found=result.total_lotes,
            lots_new=result.total_lotes,  # Simplified
            error="; ".join(result.errors[:3]) if result.errors else None,
            duration_ms=result.duration_ms,
        )
        db.update_last_scraped(source_map["receita_federal_sle"])
        results.append(("SLE", result.total_lotes, result.errors[:2]))
        print(f"{result.total_lotes} lotes" if result.success else "⚠️ errors")

    # Leilão.net
    if "leilao_net" in source_map:
        print("  🌐 Leilão.net...", end=" ", flush=True)
        net = LeilaoNet(source_id=source_map["leilao_net"])
        result = net.scrape()

        # Create a synthetic edital for Leilão.net lots
        edital_rec = {
            "source_id": source_map["leilao_net"],
            "edital_number": f"agregado_{datetime.now().strftime('%Y%m%d')}",
            "title": "Leilões agregados (Leilão.net)",
            "location": "",
            "end_propostas": None,
            "data_pregao": None,
            "total_lotes": result.total_lotes,
            "permitido_pf": 1,
            "permitido_pj": 1,
            "url": "https://www.leilao.net/",
        }
        edital_id = db.upsert_edital(edital_rec)

        if edital_id:
            for lot in result.lotes:
                lot["edital_id"] = edital_id
                db.upsert_lote(lot)

        db.log_scrape(
            source_id=source_map["leilao_net"],
            status="success" if result.success else "error",
            lots_found=result.total_lotes,
            lots_new=result.total_lotes,
            error="; ".join(result.errors[:3]) if result.errors else None,
            duration_ms=result.duration_ms,
        )
        db.update_last_scraped(source_map["leilao_net"])
        results.append(("Leilão.net", result.total_lotes, result.errors[:2]))
        print(f"{result.total_lotes} lotes" if result.success else "⚠️ errors")

    print(f"\n✅ Scrape concluído — {sum(r[1] for r in results)} lotes ao total")
    for name, count, errors in results:
        status = "⚠️ " if errors else "  "
        print(f"  {status}{name}: {count} lotes")
        for err in errors:
            print(f"      └ {err}")


def cmd_analyze(config: Config, db: Database):
    """Analyze all unprocessed lots."""
    print("📊 Analyzing lots...")

    lotes = db.get_lotes_to_analyze(limit=2000)
    if not lotes:
        print("  Nenhum lote novo para analisar.")
        return

    calculator = ROICalculator(budget_max=config.preco_maximo)
    analyzed = 0

    for lot in lotes:
        analysis = calculator.analyze(lot)
        db.save_analysis(analysis.to_dict())
        analyzed += 1

        if analyzed % 20 == 0:
            print(f"  ... {analyzed}/{len(lotes)} analisados")

    print(f"✅ {analyzed} lotes analisados")

    # Show top results
    top = db.get_lotes_with_analysis({
        "min_roi": 0.30,
        "max_preco": config.preco_maximo,
    })

    if top:
        print(f"\n🥇 Top oportunidades (ROI/mês):")
        for t in top[:10]:
            preco = t.get("preco_minimo", 0) or 0
            roi = t.get("estimated_roi", 0) or 0
            roi_m = t.get("estimated_roi_mensal", 0) or 0
            conf = t.get("confidence", "?")
            titulo = (t.get("titulo") or "Lote")[:60]
            print(
                f"  {conf.upper()[:4]:4s} | "
                f"R$ {preco:>8,.0f} | "
                f"ROI {roi:>5.0%} ({roi_m:>5.0%}/mês) | "
                f"{titulo}"
            )


def cmd_digest(config: Config, db: Database):
    """Generate and send daily digest."""
    print("📬 Generating daily digest...")

    # Get analyzed lots with good ROI
    lotes = db.get_lotes_with_analysis({
        "min_roi": 0.15,
        "max_preco": config.preco_maximo,
        "permitido_pf": True,
    })

    if not lotes:
        print("  Nenhuma oportunidade encontrada.")
        bot = TelegramBot(config)
        bot.send_digest([])
        return

    # Apply filters
    alert_filter = AlertFilter(
        max_price=config.preco_maximo,
        min_roi=config.roi_minimo_percent / 100.0,
    )

    alerts_to_send: list[dict[str, Any]] = []
    for lot in lotes:
        # Check if already alerted today
        if db.already_alerted_today(lot["id"]):
            continue

        decision = alert_filter.evaluate(lot)
        if decision.should_alert:
            alert_rec = {
                "lote_id": lot["id"],
                "alert_type": decision.priority,
                "message": decision.reason,
                "channel": "telegram",
                "delivered": False,
                "priority": decision.priority,
                "preco_minimo": lot.get("preco_minimo"),
                "estimated_roi": lot.get("estimated_roi"),
                "estimated_roi_mensal": lot.get("estimated_roi_mensal"),
                "titulo": lot.get("titulo"),
                "edital_number": lot.get("edital_number"),
                "location": lot.get("location"),
                "confidence": lot.get("confidence"),
            }
            db.save_alerta(alert_rec)
            alerts_to_send.append(alert_rec)

    # Send via Telegram
    bot = TelegramBot(config)
    if bot.available:
        success = bot.send_digest(alerts_to_send)
        if success:
            for alert in alerts_to_send:
                db.mark_alerta_enviado(alert.get("id") or 0)
            print(f"  ✅ Digest enviado ({len(alerts_to_send)} alertas)")
        else:
            print(f"  ⚠️ Falha ao enviar digest ({len(alerts_to_send)} alertas salvos)")
    else:
        print(f"  📝 {len(alerts_to_send)} alertas salvos (Telegram não configurado)")
        if alerts_to_send:
            print("\n  Exemplo de alerta:")
            print(f"    {alert_filter.format_alert_message(lotes[0], alert_filter.evaluate(lotes[0]))}")


def cmd_summary(config: Config, db: Database):
    """Show database summary."""
    s = db.get_summary()
    print(f"""
📊 *Leilão Radar — Summary*

📦 Lotes ativos:    {s['total_lotes']}
📋 Editais ativos:  {s['total_editais']}
🔬 Analisados:      {s['total_analisados']}
🔔 Alertas gerados: {s['total_alertas']}

Por fonte:
""".strip())
    for src, count in s.get("by_source", {}).items():
        print(f"  {src}: {count}")

    if s["top_roi"]:
        print("\n🥇 Top ROI/mês:")
        for t in s["top_roi"]:
            print(
                f"  ROI {t['estimated_roi_mensal']:>5.0%}/mês | "
                f"R$ {t['preco_minimo']:>8,.0f} | "
                f"{t['confidence']:>12s} | "
                f"{(t['titulo'] or '')[:50]}"
            )


def cmd_list(config: Config, db: Database, args: argparse.Namespace):
    """List analyzed opportunities with filters."""
    filters = {}
    if args.min_roi:
        filters["min_roi"] = args.min_roi
    if args.max_preco:
        filters["max_preco"] = args.max_preco
    if args.pf_only:
        filters["permitido_pf"] = True

    lotes = db.get_lotes_with_analysis(filters)

    if not lotes:
        print("Nenhum lote encontrado com esses filtros.")
        return

    print(f"\n📋 {len(lotes)} oportunidades encontradas:\n")
    for lot in lotes[:30]:
        preco = lot.get("preco_minimo", 0) or 0
        roi = lot.get("estimated_roi", 0) or 0
        roi_m = lot.get("estimated_roi_mensal", 0) or 0
        conf = lot.get("confidence", "?")
        titulo = (lot.get("titulo") or "Lote")[:60]

        print(
            f"  [{conf.upper()[:4]:4s}] "
            f"R$ {preco:>8,.0f} | "
            f"ROI {roi:>5.0%} ({roi_m:>5.0%}/mês) | "
            f"{titulo}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Leilão Radar — Automated auction opportunity scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  leilao-radar run              Full pipeline
  leilao-radar scrape --verbose Verbose scrape
  leilao-radar list --min-roi 0.5 --max-preco 5000
  leilao-radar digest           Send today's digest
        """,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # scrape
    subparsers.add_parser("scrape", help="Scrape all sources")

    # analyze
    subparsers.add_parser("analyze", help="Analyze unprocessed lots")

    # digest
    subparsers.add_parser("digest", help="Generate and send daily digest")

    # run
    subparsers.add_parser("run", help="Full pipeline: scrape → analyze → digest")

    # summary
    subparsers.add_parser("summary", help="Database summary")

    # list
    list_parser = subparsers.add_parser("list", help="List opportunities")
    list_parser.add_argument("--min-roi", type=float, default=0.0, help="Minimum ROI")
    list_parser.add_argument("--max-preco", type=float, default=0, help="Maximum price")
    list_parser.add_argument("--pf-only", action="store_true", help="PF only")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.verbose)
    config = Config.from_env()
    db = Database(config)

    if args.command == "scrape":
        cmd_scrape(config, db)
    elif args.command == "analyze":
        cmd_analyze(config, db)
    elif args.command == "digest":
        cmd_digest(config, db)
    elif args.command == "run":
        print("🚀 Leilão Radar — Full Pipeline\n")
        cmd_scrape(config, db)
        print()
        cmd_analyze(config, db)
        print()
        cmd_digest(config, db)
        print("\n✅ Pipeline completo!")
    elif args.command == "summary":
        cmd_summary(config, db)
    elif args.command == "list":
        cmd_list(config, db, args)


if __name__ == "__main__":
    main()
