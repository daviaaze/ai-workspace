"""CareerOps MVP — montagem do pacote de candidatura."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COVER_TEMPLATE = """Dear {empresa} team,

I'm a Senior Backend Engineer with 6+ years across Node.js/TypeScript and C#/.NET. For the past three years I have worked remotely with an Australian travel-tech team, building supplier integrations, booking workflows and distributed backend services on AWS.

My relevant experience for {titulo} is:
- travel supplier integrations with retry, reconciliation and production observability;
- recent Sabre work limited to e-ticket and post-booking automation;
- backend ownership from design through launch and operation.

I would welcome a conversation about the role's mandatory requirements, technical scope and expected overlap. My start date would be agreed after a professional transition from my current full-time engagement.

Best regards,
Davi Azevedo
Londrina, Brazil (UTC-3)
"""

TRIAGEM_TEMPLATE = """# Respostas de triagem — {empresa} / {titulo}

## Tell me about yourself
I'm a senior backend engineer with 6+ years across Node.js/TypeScript and C#/.NET. For the past three years I have worked remotely with an Australian travel-tech team, focused on integrations, distributed systems and production reliability.

## GDS / Sabre
My recent hands-on Sabre scope is e-ticket delivery, customer email automation and schedule-change safeguards. I have not owned the complete air-shopping, PNR, exchange/refund and cancellation lifecycle.

## Availability
I am currently in a full-time engagement. For the right role I would provide professional notice and agree on a realistic transition date. I would not maintain conflicting full-time commitments.

## Rate
I would first like to understand the scope and total package. For a direct full-time international backend contract, my working target is USD 6,000–8,000 per month or the equivalent in the contract currency.

## Mandatory-skill gap
If a required skill is marked `partial`, `pending` or `absent` in the briefing, replace this section with the exact factual disclosure from RESPOSTAS-TRIAGEM.md. Never hide the gap.
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

    # O CV derivado só pode selecionar e reordenar fatos do mestre.
    cv_orig = Path(cv_mestre_path)
    if cv_orig.exists():
        cv_text = cv_orig.read_text(encoding="utf-8")
        (pasta / "cv-mestre.md").write_text(
            "# CV para adaptação factual\n\n"
            "> Selecione e reordene somente. Não altere empresa, cargo, datas, formação, stack ou escopo.\n\n"
            + cv_text,
            encoding="utf-8",
        )

    # cover letter
    (pasta / "cover-letter.md").write_text(
        COVER_TEMPLATE.format(
            titulo=vaga["titulo"],
            empresa=vaga["empresa"],
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
        f"""# Checklist de aprovação — {vaga['empresa']} / {vaga['titulo']}

- [ ] Descrição completa da vaga salva
- [ ] Requisitos obrigatórios separados dos desejáveis
- [ ] Cada requisito classificado: atende / parcial / pendente / ausente
- [ ] Nenhum requisito hard ausente foi compensado pelo score
- [ ] Empresa, cargos, datas, formação e stacks conferidos com HABILIDADES.md
- [ ] Sabre limitado a ticketing/pós-booking
- [ ] Métricas usam formulação e fonte autorizadas
- [ ] Cada claim central tem história técnica defensável
- [ ] NDA sanitizado
- [ ] Disponibilidade e notice period confirmados com Davi
- [ ] Davi leu e aprovou CV, carta e respostas — data: __________
""",
        encoding="utf-8",
    )

    return pasta
