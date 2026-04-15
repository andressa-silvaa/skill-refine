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
YEARS_PATTERN = re.compile(
    r"(\d+)\s*\+\s*(?:anos?|years?|años?)|(\d+)\s+(?:anos?|years?|años?)",
    re.I,
)


def _intern_signal_heuristic(text_lower: str, lang_code: str) -> bool:
    """Estágio/estagiário/internship com limites de palavra (evita 'intern' ⊂ 'interno')."""
    if lang_code == "es":
        return bool(
            re.search(
                r"\bpr[aá]cticas\b|\bpracticantes?\b|\bpasantes?\b|\btrainee\b|\binternship\b|\bintern\b",
                text_lower,
                re.I,
            )
        )
    if lang_code == "en":
        return bool(re.search(r"\binternship\b|\bintern\b|\btrainee\b", text_lower, re.I))
    return bool(
        re.search(
            r"\best[aá]gio\b|\bestagi[aá]ri[oa]?\b|\btrainee\b|\binternship\b|\bintern\b",
            text_lower,
            re.I,
        )
    )


def _heuristic_seniority(text: str, lang: str, default_without_signals: str = "mid") -> str:
    text_lower = (text or "").lower()
    lang_code = (lang or "pt").split("-")[0]
    signals = SENIORITY_SIGNALS.get(lang_code, SENIORITY_SIGNALS["pt"])
    if any(s in text_lower for s in signals["senior"]):
        return "senior"
    if any(s in text_lower for s in signals["mid"]):
        return "mid"
    if any(s in text_lower for s in signals["junior"]):
        return "junior"
    if _intern_signal_heuristic(text_lower, lang_code):
        return "intern"
    match = YEARS_PATTERN.search(text_lower)
    if match:
        raw = match.group(1) or match.group(2) or "0"
        yrs = int(raw)
        # Mercado 2025–2026: até ~3 anos em função paga costuma ser faixa júnior, não estágio.
        if yrs >= 1:
            if yrs <= 3:
                return "junior"
            if yrs <= 6:
                return "mid"
            return "senior"
    d = (default_without_signals or "mid").strip().lower()
    return d if d in SENIORITY_LABELS else "mid"


def predict_hf_seniority_probs(
    resume_text: str,
    language: str,
    model_bundle: tuple[Any, Any] | None,
    *,
    allow: bool = True,
) -> tuple[str | None, float, str]:
    """
    HF softmax gap (top1 - top2) for ML adjust gating. Skips TF-IDF / heuristics.
    Returns (label_or_none, gap_0_1, provider_tag).
    """
    if not allow or not model_bundle:
        return (None, 0.0, "skipped")
    model_or_pipeline, extra = model_bundle
    if model_or_pipeline is None:
        return (None, 0.0, "no_model")
    if not isinstance(extra, dict) or extra.get("tokenizer") is None:
        return (None, 0.0, "non_hf")
    tokenizer = extra["tokenizer"]
    max_length = 512
    if isinstance(extra.get("metadata"), dict):
        limits = extra["metadata"].get("input_limits") or {}
        max_length = limits.get("max_tokens", 512)
    try:
        import torch

        inputs = tokenizer(
            resume_text[:12000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        ctx = getattr(torch, "inference_mode", None)
        infer_ctx = ctx() if callable(ctx) else torch.no_grad()
        with infer_ctx:
            out = model_or_pipeline(**inputs)
        probs = torch.nn.functional.softmax(out.logits, dim=-1).squeeze(0)
        top2 = torch.topk(probs, k=min(2, probs.numel()))
        if top2.values.numel() < 2:
            gap = 1.0
        else:
            gap = (top2.values[0] - top2.values[1]).item()
        pred_id = int(top2.indices[0])
        if 0 <= pred_id < len(SENIORITY_LABELS):
            return (SENIORITY_LABELS[pred_id], float(gap), "hf")
    except Exception:
        pass
    return (None, 0.0, "hf_error")


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
    *,
    allow_neural: bool = True,
    default_without_signals: str = "mid",
) -> tuple[str, str]:
    """
    Predict seniority class. Returns (class, model_provider).
    model_provider: "hf" | "tfidf" | "heuristics-only"
    When allow_neural is False, skips HF/TF-IDF (avoids unstable logits on sparse text).
    """
    if not allow_neural:
        pred = _heuristic_seniority(resume_text, language, default_without_signals=default_without_signals)
        return (pred, "heuristics-only")

    if model_bundle is None:
        pred = _heuristic_seniority(resume_text, language, default_without_signals=default_without_signals)
        return (pred, "heuristics-only")

    model_or_pipeline, extra = model_bundle
    if model_or_pipeline is None:
        pred = _heuristic_seniority(resume_text, language, default_without_signals=default_without_signals)
        provider = "heuristics-only"
        if isinstance(extra, dict) and extra.get("provider"):
            provider = extra["provider"]
        return (pred, provider)

    if isinstance(extra, dict) and extra.get("tokenizer") is not None:
        tokenizer = extra["tokenizer"]
        max_length = 512
        if isinstance(extra.get("metadata"), dict):
            limits = extra["metadata"].get("input_limits") or {}
            max_length = limits.get("max_tokens", 512)
        pred = _predict_hf(model_or_pipeline, tokenizer, resume_text, max_length)
        if pred:
            return (pred, "hf")
        pred = _heuristic_seniority(resume_text, language, default_without_signals=default_without_signals)
        return (pred, "heuristics-only")

    labels = extra if isinstance(extra, (list, tuple)) else extra.get("labels", list(SENIORITY_LABELS))
    try:
        pred = model_or_pipeline.predict([resume_text])[0]
        if pred in SENIORITY_LABELS:
            return (pred, "tfidf")
    except Exception:
        pass
    pred = _heuristic_seniority(resume_text, language, default_without_signals=default_without_signals)
    return (pred, "heuristics-only")


def reconcile_short_text_hf_seniority(
    resume_text: str,
    language: str,
    hf_class: str,
    *,
    default_without_signals: str,
    max_chars: int = 140,
) -> str | None:
    """
    If HF predicted senior on very short text, return conservative heuristic class; else None.
    """
    if hf_class != "senior" or len((resume_text or "").strip()) >= max_chars:
        return None
    return _heuristic_seniority(resume_text, language, default_without_signals=default_without_signals)
