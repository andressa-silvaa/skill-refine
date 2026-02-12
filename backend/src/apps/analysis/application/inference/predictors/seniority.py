"""
Seniority predictor: TF-IDF + LogReg or heuristic fallback.
"""
from __future__ import annotations

import re
from typing import Any

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")
SENIORITY_SIGNALS = {
    "pt": {
        "intern": ["estágio", "estagiário", "trainee"],
        "junior": ["júnior", "junior", "iniciante"],
        "mid": ["pleno", "mid", "analista"],
        "senior": ["sênior", "senior", "líder", "lider", "principal", "coordenador", "gerente", "lead"],
    },
    "en": {
        "intern": ["intern", "internship", "trainee"],
        "junior": ["junior", "entry", "associate"],
        "mid": ["mid", "mid-level", "analyst"],
        "senior": ["senior", "lead", "principal", "manager", "director", "head of"],
    },
    "es": {
        "intern": ["prácticas", "practicante", "pasante"],
        "junior": ["junior", "inicial"],
        "mid": ["semi-senior", "analista"],
        "senior": ["senior", "líder", "principal", "coordinador", "gerente", "jefe"],
    },
}
YEARS_PATTERN = re.compile(r"(\d+)\s*(?:anos?|years?|años?)", re.I)


def _heuristic_seniority(text: str, lang: str) -> str:
    text_lower = (text or "").lower()
    lang_code = (lang or "pt").split("-")[0]
    signals = SENIORITY_SIGNALS.get(lang_code, SENIORITY_SIGNALS["pt"])
    if any(s in text_lower for s in signals["senior"]):
        return "senior"
    if any(s in text_lower for s in signals["mid"]):
        return "mid"
    if any(s in text_lower for s in signals["junior"]):
        return "junior"
    if any(s in text_lower for s in signals["intern"]):
        return "intern"
    # Fallback: years of experience
    match = YEARS_PATTERN.search(text_lower)
    if match:
        yrs = int(match.group(1))
        if yrs <= 1:
            return "intern"
        if yrs <= 3:
            return "junior"
        if yrs <= 6:
            return "mid"
        return "senior"
    return "mid"


def predict_seniority(
    resume_text: str,
    language: str,
    model_bundle: tuple[Any, list[str]] | None,
) -> tuple[str, str]:
    """
    Predict seniority class. Returns (class, model_provider).
    model_provider: "tfidf" | "heuristics-only"
    """
    if model_bundle is None:
        pred = _heuristic_seniority(resume_text, language)
        return (pred, "heuristics-only")

    pipeline, labels = model_bundle
    if pipeline is None:
        pred = _heuristic_seniority(resume_text, language)
        return (pred, "heuristics-only")

    try:
        pred = pipeline.predict([resume_text])[0]
        if pred in SENIORITY_LABELS:
            return (pred, "tfidf")
    except Exception:
        pass
    pred = _heuristic_seniority(resume_text, language)
    return (pred, "heuristics-only")
