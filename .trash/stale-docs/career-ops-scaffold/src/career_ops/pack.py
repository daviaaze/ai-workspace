"""CareerOps MVP — montagem do pacote de candidatura."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COVER_TEMPLATE = """Subject: {titulo} at {empresa}

Hi {nome_recruiter},

I saw you're looking for {titulo} at {empresa}.

I currently run a similar stack in production as a B2B contractor for an Australian travel-tech scale-up:
- Serverless event-driven backend (Node.js, TypeScript, AWS Lambda, EventBridge, DynamoDB)
- Sabre GDS integration for booking flows
- Agent Platform serving 500+ agencies with USD 3M in TTV

I'm a senior backend contractor based in Brazil (UTC-3) with full overlap to EU/UK/US timezones,
available {disponibilidade} at ${rate_lower}–${rate_upper}k/month, invoicing via my own company (DVISION LTDA).

Worth a 20-minute call this week?

Best,
Davi Azevedo
linkedin.com/in/daviaaze | github.com/daviaaze
"""

TRIAGEM_TEMPLATE = """# Respostas de Triagem — {empresa} / {titulo}

(Usar como base; adaptar contexto da vaga. Nunca alterar os fatos.)

## "Tell me about yourself"
I'm a senior backend engineer with 6+ years building travel tech platforms. For the past 3 years I've been a
B2B contractor for Luxury Escapes (Australian travel marketplace), where I work on supplier and GDS integrations
including Sabre — across a serverless, event-driven AWS platform. I built the commission engine behind an agent
platform used by 500+ agencies doing USD 3M in TTV.

## "Experience with GDS / travel industry?"
Hands-on. I integrate travel suppliers and GDS providers into our microservices ecosystem — 9 integrations live
including Sabre, DerbySoft, SynXis, SiteMinder, TravelClick, RateGain and Rentals United. Currently working directly
with Sabre on ticketing and post-booking email automation for our booking engine serving 500+ travel agencies.

## "Rate / salary expectations?"
For a full-time contractor engagement I'm targeting USD 6–8k/month depending on scope.
"""


def montar_pacote(
    vaga: dict[str, Any],
    briefing_text: str,
    cv_mestre_path: str | Path,
    output_base: str | Path,
) -> Path:
    """Monta o pacote de candidatura em candidaturas/<empresa>-<data>/"""
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = f"{vaga['empresa']}-{vaga['titulo']}"[:80].replace(" ", "-").replace("/", "-")
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    pasta = Path(output_base) / f"{slug}-{hoje}"
    pasta.mkdir(parents=True, exist_ok=True)

    # briefing
    (pasta / "briefing.md").write_text(briefing_text, encoding="utf-8")

    # CV adaptado (placeholder — pipeline docx existente em cv-mestre)
    cv_orig = Path(cv_mestre_path)
    if cv_orig.exists():
        (pasta / "cv-mestre.md").write_text(cv_orig.read_text(encoding="utf-8"), encoding="utf-8")
    (pasta / "cv-placeholder.txt").write_text(
        f"[CV ADAPTADO — reordenar bullets do cv-mestre-davi-azevedo.md "
        f"conforme secao 6 para vaga: {vaga['titulo']}]\n",
        encoding="utf-8",
    )

    # cover letter
    (pasta / "cover-letter.md").write_text(
        COVER_TEMPLATE.format(
            titulo=vaga["titulo"],
            empresa=vaga["empresa"],
            nome_recruiter="there",
            disponibilidade="part-time immediately, full-time in 2-4 weeks",
            rate_lower="6",
            rate_upper="8",
        ),
        encoding="utf-8",
    )

    # respostas triagem
    (pasta / "triagem.md").write_text(
        TRIAGEM_TEMPLATE.format(empresa=vaga["empresa"], titulo=vaga["titulo"]),
        encoding="utf-8",
    )

    # checklist de aprovacao
    (pasta / "checklist.md").write_text(
        f"""# Checklist de Aprovacao — {vaga['empresa']}

- [ ] CV adaptado (reordenado por relevancia, sem inventar metricas)
- [ ] Cover letter menciona 1 especifico da vaga
- [ ] Briefing lacunas marcadas (sem suposicao)
- [ ] Sanitizacao NDA se concorrente da Lux
- [ ] Rate compativel com faixa alvo (6-8k)
- [ ] Confirmei que eh contratacao direta (sem intermediarios)
""",
        encoding="utf-8",
    )

    return pasta
