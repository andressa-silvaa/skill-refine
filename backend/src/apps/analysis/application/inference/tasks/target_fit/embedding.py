"""
Semantic target fit: bi-encoder cosine similarity, calibrated to 0–100.
"""
from __future__ import annotations

import math
import re
from typing import Any

_STOP = frozenset(
    "a o os as de da do das dos em para por com sem um uma un une le la les el los las the and or of to in on at "
    "que com uma pelo pela se na no nas nos".split()
)


def build_cv_embedding_text(sanitized_resume_text: str) -> str:
    return (sanitized_resume_text or "").strip()[:4000]


def build_target_embedding_text(
    target_position: str,
    job_text_sanitized: str,
    domain_category: str,
    language: str,
) -> str:
    """
    Job description if present; else target role + light domain template (no heavy heuristics).
    """
    job = (job_text_sanitized or "").strip()
    if len(job) >= 24:
        return job[:4000]
    tp = (target_position or "").strip()
    dom = (domain_category or "general").strip().lower() or "general"
    dom_hint = {
        "tech": "software engineering technology development",
        "health": "healthcare clinical patient care",
        "education": "education teaching learning",
        "business": "business management strategy operations",
        "general": "professional role responsibilities",
    }.get(dom, dom)
    lang_bit = (language or "pt-BR").split("-")[0].lower()
    return f"{tp}\n{dom_hint}\n{lang_bit}"[:4000]


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zA-ZáàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]{3,}", text.lower())
    return {w for w in words if w not in _STOP}


def compute_semantic_keyword_evidence(cv_text: str, target_text: str, *, limit: int = 8) -> list[str]:
    """Non-PII overlap keywords for explainability."""
    inter = sorted(_tokens(cv_text) & _tokens(target_text))
    return inter[:limit]


def cosine_to_fit_score(cosine: float) -> int:
    """Map cosine [-1,1] to 0..100 with gentle spread (avoids everything ~50)."""
    lo, hi = 0.28, 0.82
    x = (float(cosine) - lo) / (hi - lo + 1e-9)
    x = max(0.0, min(1.0, x))
    x = math.pow(x, 0.92)
    return int(round(100 * x))


def embedding_fit_scores(
    model,
    cv_text: str,
    target_text: str,
) -> tuple[int, float, list[str]]:
    """
    Returns (fit_embedding_0_100, raw_cosine, semantic_keywords).
    """
    if model is None or not cv_text.strip() or not target_text.strip():
        return 0, 0.0, []
    try:
        import numpy as np
    except Exception:
        return 0, 0.0, []
    emb = model.encode(
        [cv_text[:4000], target_text[:4000]],
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    a, b = emb[0], emb[1]
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    cos = float(np.dot(a, b) / denom)
    score = cosine_to_fit_score(cos)
    kw = compute_semantic_keyword_evidence(cv_text, target_text)
    return score, cos, kw
