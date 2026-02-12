"""
Derive structured insights from model outputs + heuristics.
Canonical keys for i18n.
"""
from __future__ import annotations

from typing import Any


def derive_insights(
    seniority: str,
    quality_flags: dict[str, Any],
    sections: Any,
    resume_text: str,
) -> dict[str, list[dict[str, Any]]]:
    """
    Build strengths and improvements from heuristics + outputs.
    Each item: { "key": "analysis.insights...", "priority"?: "high"|"medium"|"low", "params"?: {} }
    """
    strengths = []
    improvements = []

    # Strengths
    if quality_flags.get("has_metrics"):
        strengths.append({"key": "analysis.insights.strengths.has_metrics", "params": {}})
    if quality_flags.get("has_links"):
        strengths.append({"key": "analysis.insights.strengths.has_links", "params": {}})
    if quality_flags.get("has_action_verbs"):
        strengths.append({"key": "analysis.insights.strengths.has_action_verbs", "params": {}})
    if sections and (sections.summary or "").strip():
        strengths.append({"key": "analysis.insights.strengths.clear_structure", "params": {}})
    if sections and (sections.education or "").strip():
        strengths.append({"key": "analysis.insights.strengths.education_aligned", "params": {}})
    if not strengths:
        strengths.append({"key": "analysis.insights.strengths.other", "params": {}})

    # Improvements
    if not quality_flags.get("has_metrics"):
        improvements.append({
            "key": "analysis.insights.improvements.add_metrics",
            "priority": "high",
            "params": {"section": "experience"},
        })
    if not quality_flags.get("has_action_verbs"):
        improvements.append({
            "key": "analysis.insights.improvements.use_action_verbs",
            "priority": "medium",
            "params": {},
        })
    if not quality_flags.get("has_links"):
        improvements.append({
            "key": "analysis.insights.improvements.relevant_links",
            "priority": "medium",
            "params": {},
        })
    summary = (sections.summary if sections else "") or ""
    if len(summary.strip()) < 50 and (sections.experience if sections else ""):
        improvements.append({
            "key": "analysis.insights.improvements.improve_summary",
            "priority": "medium",
            "params": {},
        })
    improvements.append({
        "key": "analysis.insights.improvements.ats_keywords",
        "priority": "medium",
        "params": {},
    })
    if not improvements:
        improvements.append({"key": "analysis.insights.improvements.other", "priority": "medium", "params": {}})

    return {
        "strengths": strengths,
        "improvements": improvements,
    }
