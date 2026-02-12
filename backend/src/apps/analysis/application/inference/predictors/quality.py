"""
Quality predictor: heuristic-based score 0-100.
"""
from __future__ import annotations

import re
from typing import Any

LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?)|R\$\s*\d+|\$\d+|%\s*(?:de|of)", re.I)
ACTION_VERBS = {
    "pt": ["liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou", "aumentou", "reduziu"],
    "en": ["led", "implemented", "developed", "managed", "coordinated", "created", "increased", "reduced"],
    "es": ["lideró", "implementó", "desarrolló", "gestionó", "coordinó", "creó", "aumentó", "redujo"],
}


def _heuristic_flags(text: str, lang: str) -> dict[str, bool | int]:
    text_lower = (text or "").lower()
    lang_code = (lang or "pt").split("-")[0]
    verbs = ACTION_VERBS.get(lang_code, ACTION_VERBS["pt"])
    has_metrics = bool(METRICS_PATTERN.search(text_lower))
    has_links = bool(LINK_PATTERN.search(text_lower))
    action_count = sum(1 for v in verbs if v in text_lower)
    has_action_verbs = action_count > 0
    bullets = text_lower.count("- ")
    bullet_density = bullets / max(1, len(text_lower.split()))
    return {
        "has_metrics": has_metrics,
        "has_links": has_links,
        "has_action_verbs": has_action_verbs,
        "action_verbs_count": action_count,
        "bullet_density": bullet_density,
    }


def predict_quality(
    resume_text: str,
    language: str,
    sections: Any,
) -> tuple[int, dict[str, bool | int]]:
    """
    Predict quality score 0-100 and feature flags.
    Uses heuristics only (no LLM).
    """
    flags = _heuristic_flags(resume_text, language)
    score = 30
    if flags.get("has_metrics"):
        score += 25
    if flags.get("has_links"):
        score += 20
    if flags.get("has_action_verbs"):
        score += 25
    if flags.get("action_verbs_count", 0) >= 3:
        score += 5
    if (flags.get("bullet_density") or 0) > 0.01:
        score += 5
    return (min(100, score), flags)
