"""CareerOps MVP — CLI principal (click)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from .config import (
    CANDIDATURAS_DIR, CV_MESTRE_PATH, DEFAULT_CONFIG, KB_PATH,
    TRACKER_DB, load_config,
)
from .scoring import score_vaga
from .tracker import Tracker


def _t(cfg: dict) -> Tracker:
    return Tracker(cfg["_tracker_db"])


@click.group()
@click.option("--config", type=click.Path(), default=None)
@click.pass_context
def cli(ctx, config):
    """CareerOps MVP — pipeline de candidaturas do Davi."""
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = load_config(config)


@cli.command()
@click.pass_context
def scan(ctx):
    """WF-1: descobre vagas (scraping direto + RSS + IMAP)."""
    cfg = ctx.obj["cfg"]
    jobs: list[dict] = []
    click.echo("== Scraping career pages ==")
    for url in cfg["sources"]["career_pages"]:
        found = scrape_url(url)
        click.echo(f"  {url}: {len(found)}")
        jobs.extend(found)
    click.echo("== Feeds RSS ==")
    for url in cfg["sources"]["rss_feeds"]:
        found = parse_rss(url)
        click.echo(f"  {url}: {len(found)}")
        jobs.extend(found)

    added = 0
    t = _t(cfg)
    for j in jobs:
        if j.get("erro"):
            click.echo(f"  ! {j['erro']}", err=True)
            continue
        vid = t.add_vaga(
            empresa=j["empresa"], titulo=j["titulo"], url=j.get("url"),
            fonte=j.get("fonte"), notas=j.get("descricao", "")[:200] or None,
        )
        if vid > 0:
            t.log_event(vid, "discovered", j.get("fonte"))
            added += 1
    click.echo(f"=> {added} novas vagas adicionadas ao tracker.")


@cli.command()
@click.option("--all", "all_vagas", is_flag=True, help="Re-pontua todas as 'nova'")
@click.argument("vaga_id", type=int, required=False)
@click.pass_context
def score(ctx, all_vagas, vaga_id):
    """WF-2: pontua vaga(s)."""
    cfg = ctx.obj["cfg"]
    t = _t(cfg)
    if vaga_id:
        vagas = [t.get_vaga(vaga_id)]
    elif all_vagas:
        vagas = t.list_vagas(status="nova")
    else:
        vagas = t.list_vagas(status="nova")[:10]
    if not vagas or not vagas[0]:
        click.echo("Nenhuma vaga para pontuar.")
        return
    for v in vagas:
        r = score_vaga(v["empresa"], v["titulo"], v.get("notas"), v.get("rate"), v.get("fonte"))
        t.update_status(
            v["id"], "scored", score=r["score"], justificativa=r["justificativa"],
        )
        badge = "[APLICAR]" if r["decisao"] == "aplicar" else (
            "[AVALIAR]" if r["decisao"] == "avaliar" else "[DESCARTAR]"
        )
        click.echo(f"  #{v['id']} {v['empresa']}/{v['titulo'][:45]}  "
                    f"score={r['score']} {badge}")


@cli.command()
@click.argument("vaga_id", type=int)
@click.pass_context
def brief(ctx, vaga_id):
    """WF-3: gera briefing da empresa."""
    from .briefing import gerar_briefing
    cfg = ctx.obj["cfg"]
    t = _t(cfg)
    v = t.get_vaga(vaga_id)
    if not v:
        click.echo(f"Vaga {vaga_id} nao encontrada.", err=True)
        sys.exit(1)
    texto = gerar_briefing(
        empresa=v["empresa"], titulo=v["titulo"],
        score=v.get("score") or 0, decisao="preparando",
        url=v.get("url"),
    )
    bpath = CANDIDATURAS_DIR / f"vaga-{vaga_id}-briefing.md"
    bpath.write_text(texto, encoding="utf-8")
    t.update_status(vaga_id, "preparando", pacote_path=str(bpath))
    click.echo(f"Briefing salvo em {bpath}")


@cli.command()
@click.argument("vaga_id", type=int)
@click.pass_context
def pack(ctx, vaga_id):
    """WF-4: monta pacote de candidatura."""
    from .pack import montar_pacote
    from .briefing import gerar_briefing
    cfg = ctx.obj["cfg"]
    t = _t(cfg)
    v = t.get_vaga(vaga_id)
    if not v:
        click.echo(f"Vaga {vaga_id} nao encontrada.", err=True)
        sys.exit(1)
    briefing = gerar_briefing(
        empresa=v["empresa"], titulo=v["titulo"],
        score=v.get("score") or 0, decisao="preparando",
        url=v.get("url"),
    )
    pasta = montar_pacote(v, briefing, CV_MESTRE_PATH, CANDIDATURAS_DIR)
    t.update_status(vaga_id, "aguardando_aprovacao", pacote_path=str(pasta))
    click.echo(f"Pacote em: {pasta}")
    for f in sorted(pasta.iterdir()):
        click.echo(f"  - {f.name}")


@cli.command()
@click.argument("vaga_id", type=int)
@click.pass_context
def approve(ctx, vaga_id):
    """WF-5a: marca vaga como aprovada (acao humana)."""
    cfg = ctx.obj["cfg"]
    t = _t(cfg)
    t.update_status(vaga_id, "aprovada")
    click.echo(f"Vaga #{vaga_id} APROVADA. Proceder com submissao manual.")


@cli.command()
@click.argument("vaga_id", type=int)
@click.option("--rate", default=None)
@click.pass_context
def applied(ctx, vaga_id, rate):
    """WF-5b: marca vaga como submetida."""
    cfg = ctx.obj["cfg"]
    t = _t(cfg)
    t.update_status(
        vaga_id, "submetida",
        data_submissao=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rate=rate,
    )
    from datetime import timedelta
    fu = (datetime.now(timezone.utc) + timedelta(days=cfg["followup_workdays"]))
    click.echo(f"Submetida. Follow-up em: {fu.strftime('%Y-%m-%d')}")


@cli.command()
@click.pass_context
def inbox(ctx):
    """WF-6: processa caixa de alertas (IMAP)."""
    cfg = ctx.obj["cfg"]
    n = cfg["notifications"]
    host, user, pwd_env = n.get("smtp_host"), n.get("smtp_user"), n.get("smtp_password_env")
    pwd = __import__("os").environ.get(pwd_env or "", "")
    if not (host and user and pwd):
        click.echo("Configure smtp_host/smtp_user e var de ambiente de senha em config.", err=True)
        return
    click.echo("Caixa IMAP ainda nao configurada. Use `scan` para career pages.")


@cli.command()
@click.option("--status", default=None)
@click.option("--min-score", default=None, type=int)
@click.pass_context
def tracker(ctx, status, min_score):
    """Lista vagas no tracker."""
    t = _t(ctx.obj["cfg"])
    rows = t.list_vagas(status=status, min_score=min_score)
    if not rows:
        click.echo("Nenhuma vaga.")
        return
    click.echo(f"{'ID':<5} {'SCORE':<6} {'STATUS':<22} {'EMPRESA':<25} TITULO")
    click.echo("-" * 90)
    for r in rows:
        click.echo(f"{r['id']:<5} {str(r.get('score') or '-'):<6} {r['status']:<22} "
                    f"{r['empresa']:<25} {r['titulo'][:40]}")


@cli.command()
@click.pass_context
def stats(ctx):
    """WF-7: estatisticas do pipeline."""
    t = _t(ctx.obj["cfg"])
    s = t.stats()
    click.echo(f"Total: {s['total']}")
    click.echo(f"Score medio: {s['avg_score']:.1f}" if s["avg_score"] else "Score medio: -")
    click.echo("Por status:")
    for k, v in sorted(s["por_status"].items(), key=lambda x: -x[1]):
        click.echo(f"  {k:<22} {v}")


@cli.command()
@click.pass_context
def review(ctx):
    """Digest semanal consolidado (stats + acoes pendentes)."""
    cfg = ctx.obj["cfg"]
    t = _t(cfg)
    s = t.stats()
    pendentes = t.list_vagas(status="aguardando_aprovacao")
    follow = t.list_vagas(status="submetida")
    click.echo("=== REVIEW SEMANAL ===")
    click.echo(f"Vagas no tracker: {s['total']}")
    if s["avg_score"]:
        click.echo(f"Score medio: {s['avg_score']:.1f}")
    click.echo(f"Aprovacao pendente: {len(pendentes)}")
    for p in pendentes:
        click.echo(f"  #{p['id']} {p['empresa']}/{p['titulo'][:30]}")
    click.echo(f"Submetidas aguardando resposta: {len(follow)}")


@cli.command()
@click.pass_context
def setup(ctx):
    """Inicializa tracker e mostra status."""
    cfg = ctx.obj["cfg"]
    t = _t(cfg)
    click.echo(f"Tracker: {cfg['_tracker_db']}")
    click.echo(f"KB:     {cfg['_kb_path']}")
    click.echo(f"CV:     {cfg['_cv_mestre_path']}")
    click.echo(f"Saidas: {cfg['_output_dir']}")
    s = t.stats()
    click.echo(f"Vagas:  {s['total']}")


def scrape_url(url: str) -> list[dict]:
    from .scanner import scrape_career_page
    return scrape_career_page(url)


def parse_rss(url: str) -> list[dict]:
    from .scanner import parse_rss_feed
    return parse_rss_feed(url)


def main():
    cli()


if __name__ == "__main__":
    main()
