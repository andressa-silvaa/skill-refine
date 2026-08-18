"""
Generalist domain inference from free text (job title, summary, etc.).
No fixed IT taxonomy: broad sectors with multilingual keyword hints.
Output: stable English snake_case category + confidence + matched evidence tokens.

Cascade: ESCO semantic retrieval first (open label space, any occupation), keyword matching as
the fallback for when embeddings are unavailable or the nearest occupation is too far away.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from apps.analysis.application.inference.cascade import CascadeResult, run_cascade

from .esco_retrieval import infer_occupation_domain

# Stable API-facing categories (never "unknown"; use "general" as fallback).

from .domain_keywords import DOMAIN_CATEGORIES, _DOMAIN_KEYWORDS


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
    for i in range(len(parts) - 1):
        windows.append(f"{parts[i]} {parts[i + 1]}")
    return windows


def _infer_domain_keywords(text: str) -> dict[str, Any]:
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


_ESCO_OPTION_KEYS = frozenset(
    {"top_k", "min_cosine", "occupations_path", "cache_dir", "max_alt_labels", "model_name"}
)


def infer_domain_category(
    text: str,
    lang: str | None = None,
    *,
    embeddings_model: Any = None,
    occupation_query: str | None = None,
    esco_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns:
      domainCategory: str (member of DOMAIN_CATEGORIES)
      confidence: "low" | "medium" | "high"
      evidenceTokens: list[str] (matched snippets, max 8, no PII — generic keywords only)
      provider: "domain_embeddings" | "domain_keywords"
      occupation / domainMargin / occupationGap: only on the embeddings path
    """

    def _step_embeddings() -> CascadeResult:
        if embeddings_model is None:
            return CascadeResult(value=None, provider="domain_embeddings", status="skipped_disabled")
        query = str(occupation_query or text or "").strip()
        if not query:
            return CascadeResult(value=None, provider="domain_embeddings", status="skipped_empty")
        options = {k: v for k, v in (esco_options or {}).items() if k in _ESCO_OPTION_KEYS}
        found = infer_occupation_domain(embeddings_model, query, lang or "", **options)
        if not found:
            return CascadeResult(value=None, provider="domain_embeddings", status="skipped_low_signal")
        found["provider"] = "domain_embeddings"
        return CascadeResult(value=found, provider="domain_embeddings", status="applied")

    def _step_keywords() -> CascadeResult:
        found = _infer_domain_keywords(text)
        found["provider"] = "domain_keywords"
        return CascadeResult(value=found, provider="domain_keywords", status="applied")

    outcome = run_cascade([_step_embeddings, _step_keywords], default=None)
    if isinstance(outcome.value, dict):
        return outcome.value
    return {**_infer_domain_keywords(text), "provider": "domain_keywords"}
