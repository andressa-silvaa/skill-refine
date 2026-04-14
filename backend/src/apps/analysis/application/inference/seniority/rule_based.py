"""
Structural seniority policy (primary signal). See docs/analysis/seniority_policy.md.
"""
from __future__ import annotations

from typing import Any

from ..signals.types import ResumeSignals

_ORDER = ("intern", "junior", "mid", "senior")


def _confidence_from_signals(signals: ResumeSignals, base: str) -> str:
    if signals.insufficient_data:
        return "low"
    date_noise = sum(1 for r in signals.reasons if r.startswith("experience_") and "invalid" in r)
    if date_noise >= 2:
        return "low"
    if signals.experiences_count >= 2 and signals.total_months_experience > 0 and not signals.insufficient_data:
        if base in ("mid", "senior"):
            return "high"
        return "medium"
    if signals.experiences_count == 1 and signals.total_months_experience >= 12:
        return "medium"
    return "low"


def rule_based_seniority(signals: ResumeSignals) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Returns (label, confidence, evidence) with confidence in low|medium|high.
    """
    evidence: list[dict[str, Any]] = []

    if signals.experiences_count == 0:
        evidence.append(
            {"type": "veto", "rule": "no_structured_experience", "section": "experience", "count": 0}
        )
        return "junior", "low", evidence

    if signals.has_internship_terms:
        evidence.append({"type": "structural", "rule": "internship_terms_detected"})
        return "intern", "medium", evidence

    m = signals.effective_months_experience
    if m < 12:
        evidence.append({"type": "structural", "rule": "total_months_lt_12", "months": m})
        return "intern", "medium", evidence

    if m <= 24:
        evidence.append({"type": "structural", "rule": "total_months_12_24", "months": m})
        return "junior", _confidence_from_signals(signals, "junior"), evidence

    if m <= 60:
        evidence.append({"type": "structural", "rule": "total_months_25_60", "months": m})
        return "mid", _confidence_from_signals(signals, "mid"), evidence

    if signals.experiences_count >= 2 and signals.bullets_count >= 6:
        evidence.append({"type": "structural", "rule": "senior_track", "months": m})
        return "senior", _confidence_from_signals(signals, "senior"), evidence

    evidence.append({"type": "structural", "rule": "senior_months_insufficient_evidence", "months": m})
    return "mid", "medium", evidence


def clamp_seniority_vetoes(label: str, signals: ResumeSignals) -> tuple[str, list[dict[str, Any]]]:
    """Post-ML vetoes: never senior without evidence."""
    extra: list[dict[str, Any]] = []
    if label == "senior":
        if signals.experiences_count == 0:
            extra.append({"type": "veto", "rule": "never_senior_without_experience"})
            return "junior", extra
        if signals.bullets_count < 6:
            extra.append({"type": "veto", "rule": "never_senior_few_bullets", "count": signals.bullets_count})
            return "mid", extra
    return label, extra
