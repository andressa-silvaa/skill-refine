"""
Conservative post-processing for signals-only seniority ML (no Django imports).

``cfg`` keys match defaults in ``config/settings_modules/ai.py`` (see get_signals_ml_thresholds).
"""
from __future__ import annotations

from typing import Any

from ...signals.types import ResumeSignals

_ORDER = ("intern", "junior", "mid", "senior")


def _idx(label: str) -> int:
    try:
        return _ORDER.index(label)
    except ValueError:
        return 1


def confidence_from_gap(top_p: float, second_p: float) -> str:
    gap = float(top_p - second_p)
    if top_p >= 0.55 and gap >= 0.20:
        return "high"
    if top_p >= 0.40 and gap >= 0.12:
        return "medium"
    return "low"


def apply_signals_ml_gates(
    raw_label: str,
    prob_by_class: dict[str, float],
    signals: ResumeSignals,
    cfg: dict[str, Any],
) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Apply senior / intern vetoes on top of argmax label.

    Returns (final_label, confidence, evidence_entries).
    """
    evidence: list[dict[str, Any]] = []
    senior_thr = float(cfg.get("SENIOR_PROB_THRESHOLD", 0.70))
    min_months = int(cfg.get("SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS", 60))
    min_exp = int(cfg.get("SIGNALS_ML_SENIOR_MIN_EXPERIENCES", 2))
    min_bullets = int(cfg.get("SIGNALS_ML_SENIOR_MIN_BULLETS", 6))

    sorted_probs = sorted(prob_by_class.items(), key=lambda x: -x[1])
    top_label, top_p = sorted_probs[0]
    second_p = sorted_probs[1][1] if len(sorted_probs) > 1 else 0.0
    conf = confidence_from_gap(top_p, second_p)

    final = raw_label
    p_senior = float(prob_by_class.get("senior", 0.0))

    if final == "senior":
        reasons: list[str] = []
        if p_senior < senior_thr:
            reasons.append("senior_prob_below_threshold")
        if signals.total_months_experience < min_months:
            reasons.append("senior_total_months_insufficient")
        if signals.experiences_count < min_exp:
            reasons.append("senior_experiences_count_insufficient")
        if signals.bullets_count < min_bullets:
            reasons.append("senior_bullets_insufficient")
        if reasons:
            evidence.append(
                {
                    "type": "signals_ml",
                    "status": "senior_gated",
                    "reasons": reasons,
                    "p_senior": round(p_senior, 4),
                }
            )
            non_senior = [(lab, p) for lab, p in sorted_probs if lab != "senior"]
            final = non_senior[0][0] if non_senior else "mid"

    # Intern / estágio: veto implausible high bands when explicit internship signals exist
    if signals.has_internship_terms:
        if final in ("senior", "mid") and signals.effective_months_experience < 24:
            evidence.append(
                {
                    "type": "signals_ml",
                    "status": "internship_veto",
                    "from": final,
                    "to": "junior" if signals.effective_months_experience >= 12 else "intern",
                }
            )
            final = "junior" if signals.effective_months_experience >= 12 else "intern"
        elif _idx(final) > _idx("junior") and signals.effective_months_experience < 12:
            evidence.append({"type": "signals_ml", "status": "internship_cap", "to": "intern"})
            final = "intern"

    if final != raw_label:
        conf = "low" if conf == "high" else conf

    evidence.append(
        {
            "type": "signals_ml",
            "status": "applied",
            "raw": raw_label,
            "final": final,
            "top_p": round(top_p, 4),
            "gap": round(top_p - second_p, 4),
        }
    )
    return final, conf, evidence


def raw_argmax_label(prob_by_class: dict[str, float]) -> str:
    return max(prob_by_class.items(), key=lambda x: x[1])[0]
