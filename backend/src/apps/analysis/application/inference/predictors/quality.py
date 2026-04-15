"""
Quality predictor: HF regression/classification or heuristic-based score 0-100.
"""
from __future__ import annotations

from contextlib import nullcontext
import re
from typing import Any

LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?)|R\$\s*\d+|\$\d+|%\s*(?:de|of)", re.I)
ACTION_VERBS = {
    "pt": ["liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou", "aumentou", "reduziu"],
    "en": ["led", "implemented", "developed", "managed", "coordinated", "created", "increased", "reduced"],
    "es": ["lideró", "implementó", "desarrolló", "gestionó", "coordinó", "creó", "aumentó", "redujo"],
}
LEADERSHIP_WORDS = re.compile(
    r"lider|lead|mentoria|mentoring|mentorship|coordena|coordinat|gest[aã]o|manager|roadmap|stakeholder|stakeholders",
    re.I,
)
ARCHITECTURE_WORDS = re.compile(
    r"arquitet|architecture|microsservi|microservice|integra[cç][aã]o|integration|platform|plataforma|governan|observability|observabilidade",
    re.I,
)
TECH_KEYWORDS = re.compile(
    r"\b(python|django|fastapi|react|sql|api|apis|etl|cloud|aws|azure|gcp|cypress|docker|kubernetes|nlp|java|node|typescript|postgres|redis)\b",
    re.I,
)

DEFAULT_QUALITY_LEVEL_TO_SCORE = {
    "poor": 30,
    "ok": 55,
    "strong": 78,
    "good": 72,
    "excellent": 92,
}


def _lang_code(lang: str) -> str:
    return (lang or "pt").split("-")[0]


def _heuristic_flags(text: str, lang: str) -> dict[str, bool | int | float]:
    text_lower = (text or "").lower()
    lang_code = _lang_code(lang)
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


def _heuristic_score(flags: dict[str, bool | int]) -> int:
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


def _extract_hybrid_features(
    text: str,
    language: str,
    seniority_hint: str | None = None,
) -> dict[str, float]:
    text = str(text or "")
    text_lower = text.lower()
    lang_code = _lang_code(language)
    flags = _heuristic_flags(text, language)
    words = re.findall(r"\w+", text_lower, re.UNICODE)
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    unique_ratio = (len(set(words)) / len(words)) if words else 0.0
    metrics_hits = len(METRICS_PATTERN.findall(text_lower))
    tech_hits = len(set(match.group(0).lower() for match in TECH_KEYWORDS.finditer(text_lower)))
    action_count = sum(text_lower.count(verb) for verb in ACTION_VERBS.get(lang_code, ACTION_VERBS["pt"]))
    leadership_hits = len(LEADERSHIP_WORDS.findall(text_lower))
    architecture_hits = len(ARCHITECTURE_WORDS.findall(text_lower))
    github_hits = len(re.findall(r"github\.com", text_lower))
    linkedin_hits = len(re.findall(r"linkedin\.com", text_lower))
    portfolio_hits = len(re.findall(r"portfolio|portf[oó]lio|website|site pessoal|\.me/", text_lower))
    bullets = text_lower.count("- ")
    digit_count = sum(ch.isdigit() for ch in text)
    heuristic_score = _heuristic_score(flags) if isinstance(flags, dict) else 0
    features: dict[str, float] = {
        "word_count": float(len(words)),
        "sentence_count": float(len(sentences)),
        "avg_words_per_sentence": float(len(words) / max(1, len(sentences))),
        "unique_ratio": float(unique_ratio),
        "bullet_count": float(bullets),
        "bullet_density": float(bullets / max(1, len(words))),
        "digit_count": float(digit_count),
        "metrics_hits": float(metrics_hits),
        "has_metrics": float(metrics_hits > 0),
        "action_count": float(action_count),
        "has_action_verbs": float(action_count > 0),
        "leadership_hits": float(leadership_hits),
        "architecture_hits": float(architecture_hits),
        "tech_hits": float(tech_hits),
        "has_links": float(bool(LINK_PATTERN.search(text_lower))),
        "github_hits": float(github_hits),
        "linkedin_hits": float(linkedin_hits),
        "portfolio_hits": float(portfolio_hits),
        "heuristic_score": float(heuristic_score),
        "lang_pt": float(lang_code == "pt"),
        "lang_en": float(lang_code == "en"),
        "lang_es": float(lang_code == "es"),
    }
    for label in ("intern", "junior", "mid", "senior"):
        features[f"seniority_{label}"] = float((seniority_hint or "").strip().lower() == label)
    return features


def _resolve_quality_score_from_label(label: str) -> int | None:
    label_norm = str(label or "").strip().lower()
    if not label_norm:
        return None
    if label_norm.startswith("label_"):
        label_norm = label_norm.split("_", 1)[-1]
    return DEFAULT_QUALITY_LEVEL_TO_SCORE.get(label_norm)


def _predict_hf_quality(model, tokenizer, text: str, max_length: int = 512) -> int | None:
    """Run HF regression or ordinal classification. Returns score 0-100 or None on error."""
    try:
        try:
            import torch
        except Exception:
            torch = None
        inputs = tokenizer(
            text[:12000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        if torch is not None:
            ctx = getattr(torch, "inference_mode", None)
            context = ctx() if callable(ctx) else torch.no_grad()
        else:
            context = nullcontext()
        with context:
            out = model(**inputs)
        logits = out.logits
        if getattr(logits, "ndim", 0) == 2 and getattr(logits, "shape", [0, 0])[-1] > 1:
            n_cls = int(logits.shape[-1])
            id2label = getattr(getattr(model, "config", None), "id2label", {}) or {}
            try:
                probs = torch.softmax(logits, dim=-1).squeeze(0).tolist()
            except Exception:
                probs = []
            if n_cls == 3:
                fallback_scores = [30, 55, 78]
            elif n_cls == 4:
                fallback_scores = [28, 48, 68, 88]
            else:
                fallback_scores = [int(round(20 + 70 * i / max(1, n_cls - 1))) for i in range(n_cls)]
            total = 0.0
            for i in range(min(len(probs), n_cls)):
                label = id2label.get(i) if isinstance(id2label, dict) else None
                if label is None and isinstance(id2label, dict):
                    label = id2label.get(str(i))
                mapped = _resolve_quality_score_from_label(str(label)) if label is not None else None
                if mapped is None and i < len(fallback_scores):
                    mapped = fallback_scores[i]
                if mapped is None:
                    mapped = 55
                total += float(probs[i]) * float(mapped)
            if probs:
                return int(round(min(100, max(0, total))))
            pred_idx = int(logits.argmax(dim=-1).item())
            label = id2label.get(pred_idx) if isinstance(id2label, dict) else None
            mapped_score = _resolve_quality_score_from_label(str(label)) if label is not None else None
            if mapped_score is not None:
                return mapped_score
            if 0 <= pred_idx < len(fallback_scores):
                return fallback_scores[pred_idx]
            return None
        logit = logits.squeeze(-1).item()
        score = int(min(100, max(0, round(logit))))
        return score
    except Exception:
        pass
    return None


def _predict_hybrid_quality(bundle: dict[str, Any], text: str, language: str, seniority_hint: str | None = None) -> int | None:
    try:
        vectorizer = bundle.get("vectorizer")
        estimator = bundle.get("estimator")
        if vectorizer is None or estimator is None:
            return None
        features = _extract_hybrid_features(text, language, seniority_hint=seniority_hint)
        encoded = vectorizer.transform([features])
        score_map = bundle.get("quality_level_to_score") or DEFAULT_QUALITY_LEVEL_TO_SCORE
        if hasattr(estimator, "predict_proba"):
            probs = estimator.predict_proba(encoded)[0]
            classes = list(getattr(estimator, "classes_", list(range(len(probs)))))
            total = 0.0
            for idx, prob in zip(classes, probs):
                label = f"label_{idx}"
                if isinstance(idx, str):
                    label = idx
                mapped = _resolve_quality_score_from_label(label)
                if mapped is None and isinstance(idx, int):
                    mapped = list(score_map.values())[int(idx)] if 0 <= int(idx) < len(score_map) else None
                if mapped is not None:
                    total += float(prob) * float(mapped)
            return int(round(min(100, max(0, total))))
        pred = estimator.predict(encoded)[0]
        mapped = _resolve_quality_score_from_label(str(pred))
        if mapped is not None:
            return mapped
        if isinstance(pred, (int, float)):
            scores = list(score_map.values())
            pred_idx = int(pred)
            if 0 <= pred_idx < len(scores):
                return int(scores[pred_idx])
    except Exception:
        pass
    return None


def predict_quality(
    resume_text: str,
    language: str,
    sections: Any,
    seniority_hint: str | None = None,
    quality_bundle: tuple[Any, dict] | None = None,
    *,
    neural_allowed: bool = True,
) -> tuple[int, dict[str, bool | int]]:
    """
    Predict quality score 0-100 and feature flags.
    Uses HF model when available, else heuristics.
    When neural_allowed is False, skips HF/hybrid (sparse or empty resumes).
    """
    flags = _heuristic_flags(resume_text, language)

    if neural_allowed and quality_bundle:
        model_or_none, extra = quality_bundle
        if model_or_none is not None and isinstance(extra, dict) and extra.get("kind") == "hybrid":
            score = _predict_hybrid_quality(model_or_none, resume_text, language, seniority_hint=seniority_hint)
            if score is not None:
                return (score, flags)
        if model_or_none is not None and isinstance(extra, dict) and extra.get("tokenizer"):
            tokenizer = extra["tokenizer"]
            max_length = 512
            if isinstance(extra.get("metadata"), dict):
                limits = extra["metadata"].get("input_limits") or {}
                max_length = limits.get("max_tokens", 512)
            score = _predict_hf_quality(model_or_none, tokenizer, resume_text, max_length)
            if score is not None:
                return (score, flags)

    return (_heuristic_score(flags), flags)
