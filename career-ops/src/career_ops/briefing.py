"""CareerOps MVP — briefing de empresa/equipe (REGRAS §4)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

TEMPLATE = """# Briefing — {empresa} / {titulo}

> Score CareerOps: **{score}/10** | Decisao: {decisao}
> Gerado em: {data}

## 1. Empresa
{empresa_info}

## 2. Produto e clientes
{produto_info}

## 3. Equipe de engenharia
{equipe_info}

## 4. Stack e sinais técnicos
{stack_info}

## 5. Saude e riscos
{saude_info}

## 6. Angulo para o Davi
{angulo_info}

## 7. Lacunas
{lacunas_info}

---
> Lacunas marcadas como "informacao nao disponivel" — nunca preencher com suposicao.
> Fontes: pesquisar Crunchbase, LinkedIn, Glassdoor, levels.fyi, GitHub publico da empresa.
"""


def _web_search(query: str) -> str:
    """Fallback: usa pi-worker-search nao disponivel aqui; retorna placeholder."""
    return f"[PESQUISAR] {query}"


def gerar_briefing(
    empresa: str,
    titulo: str,
    score: int,
    decisao: str,
    url: str | None = None,
    descricao: str | None = None,
    empresa_info: str | None = None,
    produto_info: str | None = None,
    equipe_info: str | None = None,
    stack_info: str | None = None,
    saude_info: str | None = None,
) -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return TEMPLATE.format(
        empresa=empresa,
        titulo=titulo,
        score=score,
        decisao=decisao,
        data=now,
        empresa_info=empresa_info or "[PESQUISAR] Modelo de negocio, tamanho, funding, sede.",
        produto_info=produto_info or "[PESQUISAR] Produto principal, publico, concorrentes.",
        equipe_info=equipe_info or "[PESQUISAR] Tamanho, VP/Head of Eng, brasileiros/latinos no time.",
        stack_info=stack_info or "[PESQUISAR] Engineering blog, GitHub publico, vagas adjacentes.",
        saude_info=saude_info or "[PESQUISAR] Glassdoor/levels.fyi, sinais de layoffs.",
        angulo_info=(
            "- 500+ agencias / USD 3M TTV em travel tech (Agent Platform)\n"
            "- Sabre GDS hands-on (ticketing + pos-booking)\n"
            "- Serverless AWS em producao (Lambda, EventBridge, DynamoDB, SQS/SNS)\n"
            "- 5+ anos remoto internacional (US/UK/AU)"
        ),
        lacunas_info="- [ ] Tamanho exato do time de engenharia\n- [ ] Uso real de AWS Step Functions\n- [ ] Brasileiros/latinos no time",
    )
