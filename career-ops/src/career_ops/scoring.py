"""Scoring de vagas com gates de requisitos obrigatórios."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


INTERMEDIARIOS = {
    "lemon.io", "arc.dev", "toptal", "a.team", "turing", "x-team",
    "gun.io", "terminal.io", "andela", "bairesdev", "globant", "ci&t",
    "freelancermap", "upwork", "epam", "thoughtworks", "combine",
}

RESTRICOES_GEO = (
    "us only", "usa only", "must be based in", "eu residents only",
    "europe only", "onsite", "on-site", "hybrid", "hibrido",
)

MISSING_SKILLS = {
    "PHP": (r"\bphp\b",),
    "Ruby": (r"\bruby\b", r"\bruby on rails\b"),
    "Java": (r"\bjava\b",),
}

PENDING_SKILLS = {
    "Kafka": (r"\bkafka\b",),
    "NestJS": (r"\bnest\.?js\b",),
    "Fastify": (r"\bfastify\b",),
    "Kubernetes": (r"\bkubernetes\b", r"\bk8s\b"),
    "GraphQL": (r"\bgraphql\b",),
    "AWS Step Functions": (r"\bstep functions?\b",),
    "DynamoDB": (r"\bdynamodb\b",),
}

REQUIRED_MARKER = re.compile(
    r"\b(required|mandatory|must|obrigat\w*|proficien\w*|strong experience|"
    r"deep experience|expert\w*|\d+\+?\s*(?:years?|anos?))\b",
)
OPTIONAL_MARKER = re.compile(
    r"\b(nice to have|preferred|desirable|optional|desejavel|plus)\b",
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def _has_alias(text: str, aliases: tuple[str, ...]) -> bool:
    return any(re.search(alias, text) for alias in aliases)


def _is_hard_requirement(title: str, description: str, aliases: tuple[str, ...]) -> bool:
    if _has_alias(title, aliases):
        return True

    required_section = False
    for line in description.splitlines():
        segment = line.strip()
        if re.match(r"^(required|requirements|must have|mandatory|requisitos obrigatorios)", segment):
            required_section = True
        elif re.match(r"^(preferred|nice to have|optional|desired|desejavel)", segment):
            required_section = False

        if not _has_alias(segment, aliases) or OPTIONAL_MARKER.search(segment):
            continue
        if required_section or REQUIRED_MARKER.search(segment):
            return True

    for segment in re.split(r"[.;]", description):
        if _has_alias(segment, aliases) and REQUIRED_MARKER.search(segment):
            if not OPTIONAL_MARKER.search(segment):
                return True
    return False


def _hard_requirement_gaps(
    title: str,
    description: str,
) -> tuple[list[str], list[str], list[str]]:
    missing = [
        skill
        for skill, aliases in MISSING_SKILLS.items()
        if _is_hard_requirement(title, description, aliases)
    ]
    pending = [
        skill
        for skill, aliases in PENDING_SKILLS.items()
        if _is_hard_requirement(title, description, aliases)
    ]

    combined = f"{title} {description}"
    sabre_is_deep = "sabre" in combined and bool(re.search(
        r"\b(expert|specialist|deep|extensive|end[- ]to[- ]end|full lifecycle|"
        r"\d+\+?\s*(?:years?|anos?))\b",
        combined,
    ))
    partial = ["Sabre além de ticketing/pós-booking"] if sabre_is_deep else []
    return missing, pending, partial


def score_vaga(
    empresa: str,
    titulo: str,
    descricao: str | None = None,
    rate: str | None = None,
    fonte: str | None = None,
) -> dict[str, Any]:
    """Retorna score, decisão e lacunas; hard gaps nunca são compensados."""
    description = _normalize(descricao or "")
    title = _normalize(titulo)
    text = f"{title} {description}"
    company = _normalize(empresa)
    source = _normalize(fonte or "")

    if any(name in company or name in source for name in INTERMEDIARIOS):
        return {
            "score": 0,
            "decisao": "descartar",
            "justificativa": "Intermediário/plataforma — contratação direta obrigatória",
            "necessita_humano": False,
            "hard_gaps": [],
        }
    if any(restriction in text for restriction in RESTRICOES_GEO):
        return {
            "score": 0,
            "decisao": "descartar",
            "justificativa": "Restrição geográfica/presencial incompatível",
            "necessita_humano": False,
            "hard_gaps": [],
        }

    missing, pending, partial = _hard_requirement_gaps(title, description)
    hard_gaps = [
        *(f"ausente: {skill}" for skill in missing),
        *(f"pendente: {skill}" for skill in pending),
        *(f"parcial: {skill}" for skill in partial),
    ]
    if missing:
        return {
            "score": 4,
            "decisao": "descartar",
            "justificativa": "Gate obrigatório falhou — " + "; ".join(hard_gaps),
            "necessita_humano": False,
            "hard_gaps": hard_gaps,
        }

    score = 5
    reasons: list[str] = []
    if "node" in text and ("typescript" in text or re.search(r"\bts\b", text)):
        score += 2
        reasons.append("+2 Node.js/TypeScript")
    if any(keyword in text for keyword in ("aws", "serverless", "lambda", "event-driven")):
        score += 1
        reasons.append("+1 AWS/serverless")
    if any(keyword in text for keyword in ("travel", "booking", "gds", "sabre", "hotel", "hospitality")):
        score += 2
        reasons.append("+2 travel tech")
    if "remote" in text:
        score += 1
        reasons.append("+1 remoto")
    if any(keyword in text for keyword in ("contractor", "b2b", "c2c", "freelance")):
        score += 1
        reasons.append("+1 contractor")

    if rate:
        rate_text = rate.lower()
        if any(value in rate_text for value in ("6000", "7000", "8000", "6k", "7k", "8k")):
            score += 1
            reasons.append("+1 rate na faixa")
        elif any(value in rate_text for value in ("3000", "4000", "5000", "3k", "4k", "5k")):
            score -= 2
            reasons.append("-2 rate abaixo do piso")

    score = max(1, min(10, score))
    if pending or partial:
        score = min(score, 6)
        decision = "avaliar"
        reasons.append("gate humano: " + "; ".join(hard_gaps))
    else:
        decision = "aplicar" if score >= 7 else ("avaliar" if score >= 5 else "descartar")

    return {
        "score": score,
        "decisao": decision,
        "justificativa": "; ".join(reasons) or "Sem sinais suficientes",
        "necessita_humano": bool(pending or partial or score in (5, 6)),
        "hard_gaps": hard_gaps,
    }
