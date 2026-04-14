"""
Conservative target-area seniority from general seniority + fit signals.
"""
from __future__ import annotations

from typing import Any

from .fit_signals import TargetFitSignals

_ORDER = {"intern": 0, "junior": 1, "mid": 2, "senior": 3}
_REVERSE = ("intern", "junior", "mid", "senior")

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


def _clamp_order(general: str, max_ord: int) -> str:
    g_ord = _ORDER.get(general, 1)
    final_ord = min(g_ord, max_ord)
    return _REVERSE[final_ord]


def compute_target_seniority(
    general_label: str,
    fit_score: int,
    signals: TargetFitSignals,
    lang: str,
) -> dict[str, Any]:
    """
    Returns dict with:
      targetSeniorityLabel: intern|junior|mid|senior
      clampReasonKeys: list[str] i18n keys for UI
    """
    _ = lang
    general_label = (general_label or "junior").strip().lower()
    if general_label not in _ORDER:
        general_label = "junior"

    clamp_keys: list[str] = []

    # Tier caps from fit score
    if fit_score < 40:
        max_ord = _ORDER["junior"]
        clamp_keys.append("analysis.targetFit.clampMaxJuniorScore")
    elif fit_score < 70:
        max_ord = _ORDER["mid"]
        clamp_keys.append("analysis.targetFit.clampMaxMidScore")
    else:
        max_ord = _ORDER["senior"]

    # Evidence vetoes (conservative)
    if signals.experience_keyword_hits == 0 and not signals.portfolio_evidence:
        max_ord = min(max_ord, _ORDER["junior"])
        clamp_keys.append("analysis.targetFit.clampNoExperiencePortfolio")

    if signals.required_terms_total >= 4 and signals.required_terms_hit <= 1:
        max_ord = min(max_ord, _ORDER["junior"])
        clamp_keys.append("analysis.targetFit.clampSparseTargetHits")

    if (
        signals.skills_hit == 0
        and signals.required_terms_total >= 6
        and signals.required_terms_hit <= 2
        and signals.experience_keyword_hits == 0
    ):
        max_ord = min(max_ord, _ORDER["junior"])
        clamp_keys.append("analysis.targetFit.clampSkillsGap")

    # High general seniority with very low structural match → extra conservative
    if _ORDER[general_label] >= _ORDER["mid"] and fit_score < 35:
        max_ord = min(max_ord, _ORDER["junior"])
        clamp_keys.append("analysis.targetFit.clampHighGeneralLowFit")

    label = _clamp_order(general_label, max_ord)

    # de-dup keys preserving order
    seen: set[str] = set()
    uniq_keys = []
    for k in clamp_keys:
        if k not in seen:
            seen.add(k)
            uniq_keys.append(k)

    return {"targetSeniorityLabel": label, "clampReasonKeys": uniq_keys}


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
        # weak domain signal — use fit only for mid+ with low score
        if g >= _ORDER["mid"] and fit_score < 45:
            return {"detected": True, "reasonKey": "analysis.careerSwitch.reasonLowFitMidPlus"}
        return {"detected": False, "reasonKey": ""}

    if rd != td:
        return {"detected": True, "reasonKey": "analysis.careerSwitch.reasonDomainMismatch"}

    return {"detected": False, "reasonKey": ""}
