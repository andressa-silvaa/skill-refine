"""
The regex layer behind the quality head — fallback only, never the primary decider.

`_heuristic_score` averages 41.4 / 52.4 / 57.8 on resumes planted as poor / fair / good: nearly flat
on the axis it claims to measure, while the pillar it feeds carries 78% of the final score. That is
why it no longer answers unless ``ANALYSIS_REQUIRE_MODEL_ANSWER`` is off, which happens in exactly
one place — the golden snapshot, whose job is to keep this code correct even though it no longer
serves users.

Three of the flags it computes were replaced by ``bullet_probe`` (see ``bullet_flags.py``); the
values below survive as the fallback for when that head is unavailable, plus ``has_links`` and
``bullet_density``, which are measurement rather than judgement.

Kept in its own module so the decision path in ``predict.py`` reads as the cascade it is, without
the regex tables in the way. ``predict.py`` re-exports every public name here, because
``resume_signals.py``, the tests and the ml scripts import them from there.
"""
from __future__ import annotations

import re

LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?)|R\$\s*\d+|\$\d+|%\s*(?:de|of)", re.I)
ACTION_VERBS = {
    "pt": ["liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou", "aumentou", "reduziu"],
    "en": ["led", "implemented", "developed", "managed", "coordinated", "created", "increased", "reduced"],
    "es": ["lideró", "implementó", "desarrolló", "gestionó", "coordinó", "creó", "aumentó", "redujo"],
}
LEADERSHIP_WORDS = re.compile(
    r"l[ií]der|lead|mentoria|mentoring|mentorship|coordena|coordinat|gest[aã]o|gerenci|gerente|"
    r"manager|roadmap|stakeholder|supervis|jefe|jefa|responsable|encargad",
    re.I,
)

DEFAULT_QUALITY_LEVEL_TO_SCORE = {
    "poor": 30,
    "ok": 55,
    "strong": 78,
    "good": 72,
    "excellent": 92,
}


def lang_code(lang: str) -> str:
    return (lang or "pt").split("-")[0]


def heuristic_flags(text: str, lang: str) -> dict[str, bool | int | float]:
    text_lower = (text or "").lower()
    verbs = ACTION_VERBS.get(lang_code(lang), ACTION_VERBS["pt"])
    action_count = sum(1 for v in verbs if v in text_lower)
    bullets = text_lower.count("- ")
    return {
        "has_metrics": bool(METRICS_PATTERN.search(text_lower)),
        "has_links": bool(LINK_PATTERN.search(text_lower)),
        "has_action_verbs": action_count > 0,
        "action_verbs_count": action_count,
        "bullet_density": bullets / max(1, len(text_lower.split())),
    }


def heuristic_score(flags: dict[str, bool | int]) -> int:
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
    return min(100, score)


def resolve_quality_score_from_label(label: str) -> int | None:
    label_norm = str(label or "").strip().lower()
    if not label_norm:
        return None
    if label_norm.startswith("label_"):
        label_norm = label_norm.split("_", 1)[-1]
    return DEFAULT_QUALITY_LEVEL_TO_SCORE.get(label_norm)
