"""
Seniority predictor: HF (SequenceClassification), TF-IDF+LogReg, or heuristic fallback.
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


def _predict_hf(model, tokenizer, text: str, max_length: int = 512) -> str | None:
    """Run HF inference. Returns predicted label or None on error."""
    try:
        import torch
        inputs = tokenizer(
            text[:12000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        ctx = getattr(torch, "inference_mode", None)
        if callable(ctx):
            infer_ctx = ctx()
        else:
            infer_ctx = torch.no_grad()
        with infer_ctx:
            out = model(**inputs)
        pred_id = out.logits.argmax(dim=-1).item()
        if 0 <= pred_id < len(SENIORITY_LABELS):
            return SENIORITY_LABELS[pred_id]
    except Exception:
        pass
    return None


def predict_seniority(
    resume_text: str,
    language: str,
    model_bundle: tuple[Any, Any] | None,
) -> tuple[str, str]:
    """
    Predict seniority class. Returns (class, model_provider).
    model_provider: "hf" | "tfidf" | "heuristics-only"
    """
    if model_bundle is None:
        pred = _heuristic_seniority(resume_text, language)
        return (pred, "heuristics-only")

    model_or_pipeline, extra = model_bundle
    if model_or_pipeline is None:
        pred = _heuristic_seniority(resume_text, language)
        provider = "heuristics-only"
        if isinstance(extra, dict) and extra.get("provider"):
            provider = extra["provider"]
        return (pred, provider)

    # HF model + tokenizer
    if isinstance(extra, dict) and extra.get("tokenizer") is not None:
        tokenizer = extra["tokenizer"]
        max_length = 512
        if isinstance(extra.get("metadata"), dict):
            limits = extra["metadata"].get("input_limits") or {}
            max_length = limits.get("max_tokens", 512)
        pred = _predict_hf(model_or_pipeline, tokenizer, resume_text, max_length)
        if pred:
            return (pred, "hf")
        pred = _heuristic_seniority(resume_text, language)
        return (pred, "heuristics-only")

    # TF-IDF pipeline (sklearn)
    labels = extra if isinstance(extra, (list, tuple)) else extra.get("labels", list(SENIORITY_LABELS))
    try:
        pred = model_or_pipeline.predict([resume_text])[0]
        if pred in SENIORITY_LABELS:
            return (pred, "tfidf")
    except Exception:
        pass
    pred = _heuristic_seniority(resume_text, language)
    return (pred, "heuristics-only")
