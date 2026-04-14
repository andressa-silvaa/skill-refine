"""
Generalist domain inference from free text (job title, summary, etc.).
No fixed IT taxonomy: broad sectors with multilingual keyword hints.
Output: stable English snake_case category + confidence + matched evidence tokens.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# Stable API-facing categories (never "unknown"; use "general" as fallback).
DOMAIN_CATEGORIES: tuple[str, ...] = (
    "health",
    "education",
    "legal",
    "finance",
    "engineering",
    "marketing",
    "sales",
    "technology",
    "administrative",
    "science",
    "hr",
    "operations",
    "creative",
    "general",
)

# category -> list of lowercase tokens (any language, ASCII-folded)
_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "health": (
        "nurse",
        "nursing",
        "enferm",
        "médic",
        "medico",
        "medicina",
        "clinic",
        "clínica",
        "hospital",
        "patient",
        "paciente",
        "saude",
        "saúde",
        "salud",
        "fisioter",
        "psicolog",
        "farmácia",
        "farmacia",
        "biomedic",
        "odont",
        "veterin",
        "cirurg",
        "therap",
        "terapia",
    ),
    "education": (
        "teacher",
        "professor",
        "profesor",
        "profesora",
        "professora",
        "educação",
        "educacion",
        "education",
        "pedagog",
        "didática",
        "school",
        "escola",
        "univers",
        "academic",
        "curriculum",
        "ensino",
        "aluno",
        "student",
        "tutor",
    ),
    "legal": (
        "lawyer",
        "advogad",
        "abogad",
        "jurid",
        "legal",
        "compliance",
        "contrato",
        "contract",
        "tribunal",
        "court",
        "litig",
        "notár",
        "notario",
    ),
    "finance": (
        "finance",
        "financ",
        "contab",
        "account",
        "auditor",
        "invest",
        "bank",
        "banco",
        "tesour",
        "fp&a",
        "budget",
        "orçamento",
        "tax",
        "fiscal",
        "risk",
        "credit",
    ),
    "engineering": (
        "engineer",
        "engenheir",
        "ingenier",
        "civil",
        "mechanical",
        "mecânico",
        "electrical",
        "elétric",
        "chemical",
        "químico",
        "industrial",
        "projeto",
        "obra",
        "automação",
        "hvac",
    ),
    "marketing": (
        "marketing",
        "brand",
        "marca",
        "growth",
        "seo",
        "sem",
        "content",
        "conteúdo",
        "social media",
        "campanha",
        "campaign",
        "crm",
        "copywrit",
    ),
    "sales": (
        "sales",
        "vendas",
        "ventas",
        "comercial",
        "account executive",
        "business development",
        "bdr",
        "sdr",
        "retail",
        "vendedor",
        "representante",
    ),
    "technology": (
        "software",
        "developer",
        "desenvolvedor",
        "programador",
        "devops",
        "data scientist",
        "cientista de dados",
        "it ",
        "ti ",
        "tech",
        "cloud",
        "aws",
        "azure",
        "kubernetes",
        "frontend",
        "backend",
        "fullstack",
        "machine learning",
        "cyber",
        "sistemas",
    ),
    "administrative": (
        "administrativ",
        "secretári",
        "secretaria",
        "assistente",
        "assistant",
        "office",
        "escritório",
        "recepção",
        "recepcion",
        "backoffice",
        "coordenação administrativa",
    ),
    "science": (
        "research",
        "pesquisa",
        "investigação",
        "laborat",
        "biolog",
        "biólog",
        "químico",
        "chemist",
        "physics",
        "físic",
        "geolog",
        "ambiental",
        "ecolog",
    ),
    "hr": (
        "human resources",
        "recursos humanos",
        "rh ",
        "people ",
        "talent",
        "recrut",
        "recruit",
        "seleção",
        "seleccion",
        "payroll",
        "folha",
        "diversidad",
    ),
    "operations": (
        "operations",
        "operações",
        "operaciones",
        "logística",
        "logistica",
        "supply chain",
        "procurement",
        "compras",
        "warehouse",
        "estoque",
        "inventory",
        "plant manager",
        "produção",
        "lean",
    ),
    "creative": (
        "design",
        "designer",
        "ux",
        "ui ",
        "illustr",
        "fotograf",
        "photograph",
        "video",
        "motion",
        "arte",
        "artíst",
        "creative",
        "creador",
    ),
}


def _fold(text: str) -> str:
    s = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _token_windows(text: str) -> list[str]:
    """Lower phrases and word tokens for substring matching."""
    folded = _fold(text)
    folded = re.sub(r"[^\w\s\-/+&]", " ", folded, flags=re.UNICODE)
    parts = [p for p in re.split(r"\s+", folded.strip()) if len(p) >= 2]
    windows: list[str] = []
    windows.append(folded.strip())
    windows.extend(parts)
    # bigrams
    for i in range(len(parts) - 1):
        windows.append(f"{parts[i]} {parts[i + 1]}")
    return windows


def infer_domain_category(text: str, lang: str | None = None) -> dict[str, Any]:
    """
    Returns:
      domainCategory: str (member of DOMAIN_CATEGORIES)
      confidence: "low" | "medium" | "high"
      evidenceTokens: list[str] (matched snippets, max 8, no PII — generic keywords only)
    """
    _ = lang  # reserved for future locale-specific boosting
    if not (text or "").strip():
        return {"domainCategory": "general", "confidence": "low", "evidenceTokens": []}

    folded_full = _fold(text)
    scores: dict[str, int] = {c: 0 for c in DOMAIN_CATEGORIES if c != "general"}
    hits: dict[str, list[str]] = {c: [] for c in scores}

    for cat, kws in _DOMAIN_KEYWORDS.items():
        for kw in kws:
            if kw.strip() and kw in folded_full:
                scores[cat] = scores.get(cat, 0) + 1
                if len(hits[cat]) < 8 and kw not in hits[cat]:
                    hits[cat].append(kw.strip()[:48])

    best = max(scores, key=lambda c: scores[c]) if scores else "general"
    best_score = scores.get(best, 0)

    if best_score == 0:
        return {"domainCategory": "general", "confidence": "low", "evidenceTokens": []}

    # Second-best to detect ambiguity
    sorted_cats = sorted(scores.items(), key=lambda x: -x[1])
    second = sorted_cats[1][1] if len(sorted_cats) > 1 else 0

    if best_score >= 3 and best_score > second + 1:
        conf = "high"
    elif best_score >= 2 or best_score > second:
        conf = "medium"
    else:
        conf = "low"

    tokens = hits.get(best, [])[:8]
    return {"domainCategory": best, "confidence": conf, "evidenceTokens": tokens}
