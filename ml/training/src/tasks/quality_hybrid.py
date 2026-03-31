"""Hybrid quality model: engineered features + calibrated classifier."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..data import load_splits, normalize_quality_level
from ..eval.metrics import accuracy, correlation, f1_macro, mse_mae

QUALITY_LEVELS = ("poor", "ok", "strong")
QUALITY_LEVEL_TO_SCORE = {
    "poor": 30,
    "ok": 55,
    "strong": 84,
}

LINK_PATTERN = re.compile(r"linkedin\.com|github\.com|portfolio|portf[oó]lio|website|site pessoal|\.me/", re.I)
METRICS_PATTERN = re.compile(r"\d+%|\d+\s*(?:anos?|years?|años?|meses?|months?)|R\$\s*\d+|\$\d+|kpi|sla|okrs?", re.I)
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
ACTION_VERBS = {
    "pt": ["liderou", "implementou", "desenvolveu", "gerenciou", "coordenou", "criou", "aumentou", "reduziu", "automatizou", "otimizou"],
    "en": ["led", "implemented", "developed", "managed", "coordinated", "created", "increased", "reduced", "automated", "optimized"],
    "es": ["lideró", "implementó", "desarrolló", "gestionó", "coordinó", "creó", "aumentó", "redujo", "automatizó", "optimizó"],
}


def get_label2id() -> dict[str, int]:
    return {label: idx for idx, label in enumerate(QUALITY_LEVELS)}


def get_id2label() -> dict[int, str]:
    return {idx: label for idx, label in enumerate(QUALITY_LEVELS)}


def _lang_code(language: str) -> str:
    if str(language).startswith("en"):
        return "en"
    if str(language).startswith("es"):
        return "es"
    return "pt"


def extract_quality_features(
    text: str,
    language: str,
    seniority_hint: str | None = None,
) -> dict[str, float]:
    text = str(text or "")
    text_lower = text.lower()
    lang_code = _lang_code(language)
    verbs = ACTION_VERBS.get(lang_code, ACTION_VERBS["pt"])

    words = re.findall(r"\w+", text_lower, re.UNICODE)
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    unique_ratio = (len(set(words)) / len(words)) if words else 0.0
    metrics_hits = len(METRICS_PATTERN.findall(text_lower))
    tech_hits = len(set(match.group(0).lower() for match in TECH_KEYWORDS.finditer(text_lower)))
    action_count = sum(text_lower.count(verb) for verb in verbs)
    leadership_hits = len(LEADERSHIP_WORDS.findall(text_lower))
    architecture_hits = len(ARCHITECTURE_WORDS.findall(text_lower))
    github_hits = len(re.findall(r"github\.com", text_lower))
    linkedin_hits = len(re.findall(r"linkedin\.com", text_lower))
    portfolio_hits = len(re.findall(r"portfolio|portf[oó]lio|website|site pessoal|\.me/", text_lower))
    bullets = text_lower.count("- ")
    digit_count = sum(ch.isdigit() for ch in text)

    heuristic_score = 30
    if metrics_hits:
        heuristic_score += 20
    if github_hits or linkedin_hits or portfolio_hits:
        heuristic_score += 15
    if action_count:
        heuristic_score += 15
    if leadership_hits:
        heuristic_score += 8
    if architecture_hits:
        heuristic_score += 8
    if tech_hits >= 3:
        heuristic_score += 8
    elif tech_hits >= 2:
        heuristic_score += 4
    if 60 <= len(words) <= 260:
        heuristic_score += 6
    heuristic_score = max(0, min(100, heuristic_score))

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


def load_feature_splits(
    splits_dir,
    languages: list[str] | None = None,
):
    train_records, val_records, test_records = load_splits(splits_dir, "quality", languages=languages)
    return (
        build_feature_matrix(train_records),
        build_feature_matrix(val_records),
        build_feature_matrix(test_records),
        (train_records, val_records, test_records),
    )


def build_feature_matrix(records: list[dict]) -> tuple[list[dict[str, float]], np.ndarray]:
    xs: list[dict[str, float]] = []
    ys: list[int] = []
    label2id = get_label2id()
    for rec in records:
        labels = rec.get("labels") or {}
        level = normalize_quality_level(labels.get("quality_level"), labels.get("quality_score"))
        seniority = labels.get("seniority") or "mid"
        xs.append(
            extract_quality_features(
                text=(rec.get("inputs") or {}).get("resume_text") or "",
                language=rec.get("language") or "pt-BR",
                seniority_hint=seniority,
            )
        )
        ys.append(label2id[level])
    return xs, np.array(ys, dtype=int)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, probabilities: np.ndarray | None = None) -> dict[str, float]:
    id2label = get_id2label()
    score_map = np.array([QUALITY_LEVEL_TO_SCORE[id2label[idx]] for idx in range(len(QUALITY_LEVELS))], dtype=float)
    if probabilities is not None:
        pred_scores = probabilities @ score_map
    else:
        pred_scores = np.array([QUALITY_LEVEL_TO_SCORE[id2label[int(idx)]] for idx in y_pred], dtype=float)
    true_scores = np.array([QUALITY_LEVEL_TO_SCORE[id2label[int(idx)]] for idx in y_true], dtype=float)
    mse, mae = mse_mae(true_scores, pred_scores)
    pearson, spearman = correlation(true_scores, pred_scores)
    return {
        "accuracy": accuracy(y_true, y_pred),
        "f1_macro": f1_macro(y_true, y_pred, list(QUALITY_LEVELS)),
        "mse_score": mse,
        "mae_score": mae,
        "pearson_score": pearson,
        "spearman_score": spearman,
    }
