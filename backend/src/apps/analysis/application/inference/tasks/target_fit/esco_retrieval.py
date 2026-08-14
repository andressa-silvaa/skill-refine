"""
Zero-shot occupation inference by semantic retrieval over the ESCO taxonomy.

The resume text and the ~1.7k ESCO occupation labels pass through the same multilingual
bi-encoder; the nearest labels are the predicted occupation, and the domain comes from the
ISCO-08 group of the winner. No training, no labels, and the reachable label space is the
official taxonomy instead of a hand-written keyword list, so an occupation nobody enumerated
is still classifiable.

The label matrix and its on-disk cache live in ``esco_index.py``. Everything that module exposes is
re-exported here, because the orchestrator, the warmup, the tests and the ml scripts import those
names from this module.
"""
from __future__ import annotations

import logging
from typing import Any

from .esco_index import (
    CONFIDENCE_HIGH_COSINE,
    CONFIDENCE_HIGH_MARGIN,
    CONFIDENCE_MEDIUM_COSINE,
    CONFIDENCE_MEDIUM_MARGIN,
    DEFAULT_MAX_ALT_LABELS,
    DEFAULT_TOP_K,
    MAX_QUERY_CHARS,
    MIN_COSINE_FLOOR,
    OccupationIndex,
    _encode,
    _first_variant,
    _label_variants,
    clear_esco_cache,
    default_cache_dir,
    default_occupations_path,
    get_occupation_index,
    lang_key,
    load_occupations,
)
from .isco_domains import domain_for_isco

logger = logging.getLogger(__name__)

_INDEX_OPTION_KEYS = frozenset({"occupations_path", "cache_dir", "max_alt_labels", "model_name"})


def warm_occupation_index(model: Any, lang: str, options: dict[str, Any] | None = None) -> bool:
    """Build (or read from disk) the label matrix ahead of the first request."""
    kwargs = {k: v for k, v in (options or {}).items() if k in _INDEX_OPTION_KEYS}
    return get_occupation_index(model, lang, **kwargs) is not None


def retrieve_occupations(
    model: Any,
    text: str,
    lang: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    index: OccupationIndex | None = None,
    **index_kwargs: Any,
) -> list[tuple[dict[str, Any], float]]:
    """Top-k ESCO occupations by cosine, scored by their best-matching label variant."""
    query = str(text or "").strip()[:MAX_QUERY_CHARS]
    if not query:
        return []
    idx = index if index is not None else get_occupation_index(model, lang, **index_kwargs)
    if idx is None:
        return []

    import numpy as np

    vector = _encode(model, [query])[0]
    sims = idx.matrix @ vector
    order = np.argsort(-sims)
    out: list[tuple[dict[str, Any], float]] = []
    taken: set[int] = set()
    for row in order:
        occupation_id = int(idx.row_to_occupation[row])
        if occupation_id in taken:
            continue
        taken.add(occupation_id)
        out.append((idx.occupations[occupation_id], float(sims[row])))
        if len(out) >= top_k:
            break
    return out


def confidence_for(top_cosine: float, domain_margin: float) -> str:
    if domain_margin >= CONFIDENCE_HIGH_MARGIN and top_cosine >= CONFIDENCE_HIGH_COSINE:
        return "high"
    if domain_margin >= CONFIDENCE_MEDIUM_MARGIN or top_cosine >= CONFIDENCE_MEDIUM_COSINE:
        return "medium"
    return "low"


def infer_occupation_domain(
    model: Any,
    text: str,
    lang: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    min_cosine: float = MIN_COSINE_FLOOR,
    index: OccupationIndex | None = None,
    **index_kwargs: Any,
) -> dict[str, Any] | None:
    """
    Domain of the retrieved occupation, or None when retrieval is unavailable or too weak to
    beat the keyword fallback.

    Confidence comes from the margin between the best and the runner-up domain, not from the
    absolute cosine: a high cosine with a thin margin is ambiguity, not certainty. When every
    top-k occupation maps to one domain there is no runner-up, and that unanimity scores as the
    widest possible margin.
    """
    hits = retrieve_occupations(model, text, lang, top_k=top_k, index=index, **index_kwargs)
    if not hits:
        return None
    top_occupation, top_cosine = hits[0]
    if top_cosine < min_cosine:
        return None

    per_domain: dict[str, float] = {}
    for occupation, cosine in hits:
        domain = str(occupation.get("domain") or "general")
        if cosine > per_domain.get(domain, -1.0):
            per_domain[domain] = cosine
    ranked = sorted(per_domain.items(), key=lambda kv: -kv[1])
    best_domain, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    domain_margin = float(best_score - runner_up)
    occupation_gap = float(top_cosine - hits[1][1]) if len(hits) > 1 else float(top_cosine)

    code = lang_key(lang)

    def _label_of(occupation: dict[str, Any]) -> str:
        labels = occupation.get("labels") if isinstance(occupation.get("labels"), dict) else {}
        return _first_variant(labels.get(code) or labels.get("en") or "")

    evidence = [label[:48] for label in (_label_of(o) for o, _c in hits) if label]

    return {
        "domainCategory": best_domain,
        "confidence": confidence_for(top_cosine, domain_margin),
        "evidenceTokens": evidence[:8],
        "occupation": {
            "uri": top_occupation.get("uri") or "",
            "label": _label_of(top_occupation),
            "isco": top_occupation.get("isco") or "",
            "iscoGroup": top_occupation.get("isco_group") or "",
            "cosine": round(float(top_cosine), 4),
        },
        "domainMargin": round(domain_margin, 4),
        "occupationGap": round(occupation_gap, 4),
    }


def build_occupation_query(resume_data: dict[str, Any], *, max_skills: int = 8) -> str:
    """
    Title-first query: occupation labels are job titles, so titles and skills carry the signal
    while paragraphs of achievements dilute it.
    """
    block = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    parts: list[str] = []
    target = str(block.get("targetPosition") or "").strip()
    if target:
        parts.append(target)
    for experience in block.get("experiences") or []:
        if isinstance(experience, dict):
            position = str(experience.get("position") or "").strip()
            if position:
                parts.append(position)
    skills: list[str] = []
    for skill in block.get("skills") or []:
        if isinstance(skill, dict) and skill.get("name"):
            skills.append(str(skill["name"]).strip())
        if len(skills) >= max_skills:
            break
    if skills:
        parts.append(", ".join(skills))
    for education in block.get("educations") or []:
        if isinstance(education, dict):
            course = str(education.get("course") or "").strip()
            if course:
                parts.append(course)
    return "\n".join(parts)[:MAX_QUERY_CHARS]
