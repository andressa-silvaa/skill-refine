"""
ML fine-tuning on top of structural base (max one step, confidence-gated).
"""
from __future__ import annotations

from typing import Any

from ...signals.types import ResumeSignals
from .constants import MIN_COMPLETENESS_FOR_ML, MIN_TOKENS_FOR_ML, ML_SOFTMAX_GAP_MIN, ML_SOFTMAX_GAP_STRONG
from .hf_predict import predict_hf_seniority_probs
from .rule_based import clamp_seniority_vetoes

_ORDER = ("intern", "junior", "mid", "senior")


def _idx(label: str) -> int:
    try:
        return _ORDER.index(label)
    except ValueError:
        return 1


def ml_adjust_seniority(
    resume_text: str,
    language: str,
    base_label: str,
    base_confidence: str,
    base_evidence: list[dict[str, Any]],
    signals: ResumeSignals,
    model_bundle: tuple[Any, Any] | None,
    *,
    allow_ml: bool,
) -> tuple[str, str, list[dict[str, Any]], str]:
    """
    Returns (final_label, confidence, evidence, ml_status).
    ml_status: applied | skipped_gating | skipped_low_gap | skipped_no_model | noop
    """
    evidence = list(base_evidence)
    if not allow_ml:
        evidence.append({"type": "ml", "status": "skipped_gating"})
        fl, ve = clamp_seniority_vetoes(base_label, signals)
        evidence.extend(ve)
        return fl, base_confidence, evidence, "skipped_gating"

    if signals.completeness_score < MIN_COMPLETENESS_FOR_ML or signals.word_count < MIN_TOKENS_FOR_ML:
        evidence.append({"type": "ml", "status": "skipped_gating", "completeness": signals.completeness_score})
        fl, ve = clamp_seniority_vetoes(base_label, signals)
        evidence.extend(ve)
        return fl, base_confidence, evidence, "skipped_gating"

    ml_label, gap, provider = predict_hf_seniority_probs(resume_text, language, model_bundle, allow=True)
    if ml_label is None:
        evidence.append({"type": "ml", "status": "skipped_no_model", "provider": provider})
        fl, ve = clamp_seniority_vetoes(base_label, signals)
        evidence.extend(ve)
        return fl, base_confidence, evidence, "skipped_no_model"

    if gap < ML_SOFTMAX_GAP_MIN:
        evidence.append({"type": "ml", "status": "skipped_low_gap", "gap": round(gap, 4), "provider": provider})
        conf = "low" if base_confidence == "high" else base_confidence
        fl, ve = clamp_seniority_vetoes(base_label, signals)
        evidence.extend(ve)
        return fl, conf, evidence, "skipped_low_gap"

    bi, mi = _idx(base_label), _idx(ml_label)
    if abs(mi - bi) > 1:
        evidence.append(
            {
                "type": "ml",
                "status": "rejected_large_delta",
                "base": base_label,
                "ml": ml_label,
                "gap": round(gap, 4),
                "provider": provider,
            }
        )
        fl, ve = clamp_seniority_vetoes(base_label, signals)
        evidence.extend(ve)
        return fl, base_confidence, evidence, "noop"

    if mi == bi:
        evidence.append({"type": "ml", "status": "agrees", "label": ml_label, "gap": round(gap, 4), "provider": provider})
        conf = "high" if gap >= ML_SOFTMAX_GAP_STRONG and base_confidence == "high" else base_confidence
        fl, ve = clamp_seniority_vetoes(base_label, signals)
        evidence.extend(ve)
        return fl, conf, evidence, "noop"

    final = ml_label
    evidence.append(
        {
            "type": "ml",
            "status": "adjusted",
            "from": base_label,
            "to": final,
            "gap": round(gap, 4),
            "provider": provider,
        }
    )
    adj_conf = "high" if gap >= ML_SOFTMAX_GAP_STRONG else "medium"
    merged_conf = adj_conf if adj_conf == "high" or base_confidence == "low" else "medium"
    fl, ve = clamp_seniority_vetoes(final, signals)
    evidence.extend(ve)
    return fl, merged_conf, evidence, "applied"
