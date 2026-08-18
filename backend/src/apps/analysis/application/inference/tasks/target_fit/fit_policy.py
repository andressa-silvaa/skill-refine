"""
Rule-based target-fit score and career-switch flag from fit signals.
"""
from __future__ import annotations

from typing import Any

from .fit_signals import TargetFitSignals

_ORDER = {"intern": 0, "junior": 1, "mid": 2, "senior": 3}

# Audit string when target fit uses rule-based policy (no sklearn bundle).
TARGET_FIT_POLICY_VERSION = "target_fit_policy_v1"


def heuristic_target_fit_score(
    signals: TargetFitSignals,
    *,
    has_job_text: bool,
    resume_domain: str | None = None,
    target_domain: str | None = None,
) -> int:
    """Interpretable 0–100 from structural coverage (CPU-only, no trained model)."""
    total = max(1, signals.required_terms_total)
    cover = signals.required_terms_hit / total
    base = int(round(100 * cover))

    if signals.experience_keyword_hits >= 3:
        base = min(100, base + 12)
    elif signals.experience_keyword_hits >= 1:
        base = min(100, base + 6)

    if signals.portfolio_evidence:
        base = min(100, base + 5)

    if signals.education_alignment == "strong":
        base = min(100, base + 8)
    elif signals.education_alignment == "medium":
        base = min(100, base + 4)

    if signals.skills_hit >= 3:
        base = min(100, base + 6)

    rd = (resume_domain or "").strip().lower()
    td = (target_domain or "").strip().lower()
    if rd and td and rd != "general" and td != "general" and rd != td:
        base = int(round(base * 0.58))
        base = min(base, 52)

    if not has_job_text:
        base = int(round(base * 0.82))
        base = min(base, 72)

    if signals.completeness_score < 40:
        base = min(base, 55)

    return max(0, min(100, base))


def compute_target_fit_policy(
    signals: TargetFitSignals,
    *,
    has_job_text: bool = False,
    resume_domain: str = "general",
    target_domain: str = "general",
) -> int:
    """
    Deterministic 0–100 label for training export and policy fallback.
    Same mapping as ``heuristic_target_fit_score`` (explainable rules).
    """
    return heuristic_target_fit_score(
        signals,
        has_job_text=has_job_text,
        resume_domain=resume_domain,
        target_domain=target_domain,
    )


def compute_career_switch(
    general_label: str,
    fit_score: int,
    resume_domain: str,
    target_domain: str,
) -> dict[str, Any]:
    """Heuristic career switch / migration flag (explainable, rule-based)."""
    g = _ORDER.get(general_label, 1)
    rd = (resume_domain or "general").strip().lower()
    td = (target_domain or "general").strip().lower()

    if g < _ORDER["mid"]:
        return {"detected": False, "reasonKey": ""}

    if fit_score >= 52:
        return {"detected": False, "reasonKey": ""}

    if rd == "general" or td == "general":
        if g >= _ORDER["mid"] and fit_score < 45:
            return {"detected": True, "reasonKey": "analysis.careerSwitch.reasonLowFitMidPlus"}
        return {"detected": False, "reasonKey": ""}

    if rd != td:
        return {"detected": True, "reasonKey": "analysis.careerSwitch.reasonDomainMismatch"}

    return {"detected": False, "reasonKey": ""}
