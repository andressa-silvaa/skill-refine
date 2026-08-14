"""
Os dois ajustes que acontecem depois que os pilares respondem: os caps e a decoração dos insights.

Separados do orquestrador porque são regra de produto declarada, não decisão de modelo, e é útil que
isso fique visível em vez de diluído no meio do pipeline.
"""
from __future__ import annotations

from typing import Any

from ..completeness import matching_score_cap, quality_score_cap
from ..resume_signals import is_thin_student_or_intern_profile

THIN_PROFILE_QUALITY_CAP = 58
THIN_PROFILE_MATCHING_CAP = 60


def apply_completeness_caps(
    *,
    quality_score: int,
    matching_score: int,
    completeness: dict[str, Any],
    resume_data: dict[str, Any],
    job_text: str,
) -> tuple[int, int, int, bool]:
    """
    Returns ``(quality_score, matching_score, quality_cap, thin_profile)``.

    Out-of-distribution guard, not an uncertainty proxy: the head's confidence does not fall on
    sparse resumes, but it does answer a completely empty one with 78 at a *confident* margin
    (ml/reports/completeness_caps_v3.md). The values themselves are declared product policy.
    """
    thin_profile = is_thin_student_or_intern_profile(resume_data)
    quality_cap = quality_score_cap(completeness)
    quality_score = min(quality_score, quality_cap)
    if thin_profile:
        quality_score = min(quality_score, THIN_PROFILE_QUALITY_CAP)
    if job_text:
        matching_score = min(matching_score, matching_score_cap(completeness))
        if thin_profile:
            matching_score = min(matching_score, THIN_PROFILE_MATCHING_CAP)
    return quality_score, matching_score, quality_cap, thin_profile


def decorate_insights(
    insights: dict[str, Any],
    *,
    target_fit_improvement: dict[str, Any] | None,
    career_switch: dict[str, Any],
) -> dict[str, Any]:
    """
    Pin the target-fit improvement and the career-switch context to the top of their lists.

    These two jump the measured ranking on purpose: both are about the *target* the user chose, so
    they answer a question the ranking never sees. Everything below them is ordered by
    `insight_gain_v1`.
    """
    if target_fit_improvement:
        improvements = list(insights.get("improvements") or [])
        improvements.insert(0, target_fit_improvement)
        insights = {**insights, "improvements": improvements}
    if career_switch.get("detected"):
        strengths = list(insights.get("strengths") or [])
        strengths.insert(
            0,
            {
                "key": "analysis.insights.strengths.career_switch_context",
                "params": {"reasonKey": str(career_switch.get("reasonKey") or "")},
            },
        )
        insights = {**insights, "strengths": strengths}
    return insights
