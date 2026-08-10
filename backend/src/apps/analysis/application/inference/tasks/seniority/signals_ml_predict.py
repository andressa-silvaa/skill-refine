"""
Signals-only sklearn seniority inference (used with loader_signals_model singleton).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from ...signals.types import ResumeSignals
from .signals_ml_policy import apply_signals_ml_gates, raw_argmax_label


FEATURE_TRANSFORM = "log1p_v1"

# Must stay byte-for-byte equivalent to LOG1P_FEATURES in ml/training/src/signals_features.py.
# A silent divergence here is the worst failure mode available: the model would receive a feature
# space it was never fitted on and still answer confidently, which is exactly how
# seniority_signals_v1 came to label every real resume "intern". The bundle records which
# transform it was trained with and the loader refuses a mismatch.
LOG1P_FEATURES = frozenset(
    {
        "summary_char_count",
        "word_count",
        "total_months_experience",
        "effective_months_experience",
        "months_in_current_role",
        "bullets_count",
        "experiences_count",
        "skills_count",
    }
)


def signals_to_feature_dict(signals: ResumeSignals) -> dict[str, float]:
    """Aligned with ``ml/training/src/signals_features.py`` (skip reasons/language/completeness_level)."""
    skip = frozenset({"reasons", "language", "completeness_level"})
    out: dict[str, float] = {}
    for k, v in signals.__dict__.items():
        if k in skip:
            continue
        if isinstance(v, bool):
            out[k] = 1.0 if v else 0.0
        elif isinstance(v, (int, float)):
            out[k] = math.log1p(max(0.0, float(v))) if k in LOG1P_FEATURES else float(v)
    return out


def signals_ml_predict(
    bundle: dict[str, Any],
    signals: ResumeSignals,
    cfg: dict[str, Any],
) -> tuple[str, str, dict[str, float], list[dict[str, Any]], str]:
    """
    Returns (final_label, confidence, prob_by_class, evidence, status).

    status: applied | skipped_insufficient_signals | error
    """
    min_comp = int(cfg.get("MIN_COMPLETENESS_FOR_SIGNALS_ML", 52))
    min_words = int(cfg.get("MIN_WORDS_FOR_SIGNALS_ML", 48))
    evidence: list[dict[str, Any]] = []

    if signals.insufficient_data or signals.experiences_count <= 0:
        evidence.append({"type": "signals_ml", "status": "skipped_insufficient_signals"})
        return "", "low", {}, evidence, "skipped_insufficient_signals"

    if signals.completeness_score < min_comp or signals.word_count < min_words:
        evidence.append(
            {
                "type": "signals_ml",
                "status": "skipped_gating",
                "completeness": signals.completeness_score,
                "word_count": signals.word_count,
            }
        )
        return "", "low", {}, evidence, "skipped_insufficient_signals"

    clf = bundle["pipeline"]
    le = bundle["label_encoder"]
    feature_names: list[str] = bundle["feature_names"]
    feat = signals_to_feature_dict(signals)
    vec = np.asarray([[feat.get(n, 0.0) for n in feature_names]], dtype=np.float64)

    try:
        probs = clf.predict_proba(vec)[0]
    except Exception as exc:
        evidence.append({"type": "signals_ml", "status": "error", "error": str(exc)[:200]})
        return "", "low", {}, evidence, "error"

    classes = list(getattr(le, "classes_", []))
    prob_by_class = {str(classes[i]): float(probs[i]) for i in range(len(classes))}
    raw = raw_argmax_label(prob_by_class)
    final, conf, pol_ev = apply_signals_ml_gates(raw, prob_by_class, signals, cfg)
    evidence.extend(pol_ev)
    return final, conf, prob_by_class, evidence, "applied"
