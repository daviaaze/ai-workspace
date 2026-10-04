"""CareerOps MVP — briefing de empresa/equipe (REGRAS §4)."""
from __future__ import annotations

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

## 6. Matriz de requisitos
{requisitos_info}

## 7. Ângulo para o Davi
{angulo_info}

## 8. Lacunas e validações
{lacunas_info}

---
> Classificar cada requisito como `atende`, `parcial`, `pendente` ou `ausente`.
> Pontos positivos nunca compensam requisito obrigatório ausente.
> Informação não disponível permanece não disponível.
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
    descricao_presente = bool(descricao and descricao.strip())
    requisitos_info = (
        "| Requisito | Obrigatório? | Evidência | Classificação |\n"
        "|---|---|---|---|\n"
        "| Extrair da descrição completa | confirmar | HABILIDADES.md | pendente |"
        if descricao_presente
        else "**Bloqueado:** descrição completa não foi salva; não preparar pacote."
    )

    return TEMPLATE.format(
        empresa=empresa,
        titulo=titulo,
        score=score,
        decisao=decisao,
        data=now,
        empresa_info=empresa_info or "[PESQUISAR] Modelo de negócio, tamanho, funding, sede.",
        produto_info=produto_info or "[PESQUISAR] Produto principal, público, concorrentes.",
        equipe_info=equipe_info or "[PESQUISAR] Tamanho, liderança e histórico de trabalho remoto.",
        stack_info=stack_info or "[PESQUISAR] Engineering blog, GitHub público e vagas adjacentes.",
        saude_info=saude_info or "[PESQUISAR] Layoffs, funding, reviews e estabilidade da vaga.",
        requisitos_info=requisitos_info,
        angulo_info=(
            "- 6+ anos de backend somando Node.js/TypeScript e C#/.NET\n"
            "- 3 anos com equipe australiana em travel tech\n"
            "- Supplier integrations e booking workflows\n"
            "- Sabre somente em ticketing e pós-booking"
        ),
        lacunas_info=(
            "- [ ] Requisitos obrigatórios separados dos desejáveis\n"
            "- [ ] Skills parciais, pendentes e ausentes declaradas\n"
            "- [ ] Disponibilidade e overlap confirmados\n"
            "- [ ] Métricas e NDA revisados"
        ),
    )
