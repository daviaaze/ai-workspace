"""CareerOps MVP — scoring de vagas (regras REGRAS-DE-APLICACAO.md §1)."""
from __future__ import annotations

import re
from typing import Any

# Pesos alinhados com REGRAS-DE-APLICACAO.md §1
FIT_RULES: dict[str, int] = {
    "backend node.js + typescript como stack principal": +2,
    "aws serverless / event-driven explícito": +1,
    "travel tech, booking, gDS, hospitality, marketplace": +2,
    "100% remoto sem restrição geográfica (ou 'latAm welcome')": +1,
    "b2b contractor / freelance / c2c **direto com a empresa**": +1,
    "rate na faixa alvo (usd 6–8k/mês ou equivalente/hora)": +1,
    "part-time 20h (encaixa no plano de 2 contratos)": +1,
    "**recrutadora, staffing agency, consultória ou plataforma intermediária**": -100,  # descarte
    "restrição 'us-only' / 'eu residents only' / fuso sem overlap": -4,
    "exige skill pendente como requisito hard (kafka, nEtsjs, k8s)": -2,
    "presencial/híbrido ou relocation": -100,  # descarte
    "clt/pj brasil": -3,
    "rate < usd 6k/mês ou < usd 50/h": -2,
    "fintech/banking domain obrigatório": -2,
}

PESQUISAS_DESCARTE = [
    re.compile(r"\b(combine|lemon\.io|toptal|arc\.dev|braintrust)\b", re.I),
    re.compile(r"\b(recruiter|staffing agency|consulting)\b", re.I),
    re.compile(r"\b(our client|confidential company)\b", re.I),
    re.compile(r"\b(us-only|us citizens? only|eu residents? only)\b", re.I),
    re.compile(r"\b(on-site|on site|hybrid|relocation)\b", re.I),
]


def score_vaga(empresa: str, titulo: str, descricao: str | None = None,
               rate: str | None = None, fonte: str | None = None) -> dict[str, Any]:
    """Pontua a vaga 1-10 segundo as regras."""
    score = 5
    motivos: list[str] = []
    texto = f"{titulo} {descricao or ''}".lower()

    # Desc automatico por fonte/intermediario
    check_text = f"{empresa} {titulo} {fonte or ''} {descricao or ''}".lower()
    for pat in PESQUISAS_DESCARTE:
        if pat.search(check_text):
            return {
                "score": 0,
                "decisao": "descartar",
                "justificativa": f"Descarte automatico: {pat.pattern[:40]}...",
                "motivos": [f"Intermediario/restricao detectada"],
            }

    if re.search(r"\b(node|nodejs|typescript)\b", texto):
        score += 2; motivos.append("Node/TS (+2)")
    if re.search(r"\b(serverless|lambda|eventbridge|event-driven|step functions)\b", texto):
        score += 1; motivos.append("AWS serverless/event-driven (+1)")
    if re.search(r"\b(travel|booking|gds|sabre|hospitality|marketplace|hotel|ota)\b", texto):
        score += 2; motivos.append("Travel tech / booking / GDS (+2)")
    if re.search(r"\b(remote|100% remoto|worldwide)\b", texto) and \
       not re.search(r"\b(remote\s*-\s*us|remote\s*-\s*eu)\b", texto):
        score += 1; motivos.append("Remoto sem restricao geografica (+1)")
    if re.search(r"\b(b2b|contractor|freelance|c2c)\b", texto):
        score += 1; motivos.append("Contratacao B2B/contractor (+1)")
    if re.search(r"\b(part.time|20h|half-time)\b", texto):
        score += 1; motivos.append("Part-time 20h (+1)")

    if re.search(r"\b(kafka)\b", texto) and "kafka" not in titulo.lower():
        score -= 2; motivos.append("Kafka requisito hard (-2)")
    if re.search(r"\b(nestjs)\b", texto):
        score -= 2; motivos.append("NestJS requisito hard (-2)")
    if re.search(r"\b(fintech|banking|financial services)\b", texto):
        score -= 2; motivos.append("Dominio fintech (-2)")

    if rate:
        nums = re.findall(r"[\d.,]+", rate.replace(",", ""))
        if nums:
            eh_hora = "h" in rate.lower()
            val = float(nums[0])
            if "h" in rate.lower() and val < 50:
                score -= 2; motivos.append(f"Rate <50/h: {rate} (-2)")
            elif val < 6000 and "k" not in rate.lower():
                pass
            elif "k" in rate.lower() and val < 6:
                score -= 2; motivos.append(f"Rate <6k/mes: {rate} (-2)")
            elif not eh_hora and 6 <= val <= 8:
                score += 1; motivos.append(f"Rate na faixa alvo: {rate} (+1)")

    decisao = "descartar" if score < 5 else ("avaliar" if score < 7 else "aplicar")
    return {
        "score": max(0, min(10, score)),
        "decisao": decisao,
        "justificativa": "; ".join(motivos) or "Sem ajustes relevantes",
        "motivos": motivos,
    }
