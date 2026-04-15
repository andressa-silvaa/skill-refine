"""
Evidence-based insights: strengths and improvements from flags + structured signals.
"""
from __future__ import annotations

from typing import Any

from ..resume_signals import education_aligned_with_target, education_tech_gap_suggestion
from ..signals.types import ResumeSignals


def _item(key: str, *, priority: str | None = None, params: dict[str, Any] | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"key": key, "params": params or {}}
    if priority in ("high", "medium", "low"):
        out["priority"] = priority
    if evidence:
        out["evidence"] = evidence
    return out


def derive_insights(
    seniority: str,
    quality_flags: dict[str, Any],
    sections: Any,
    resume_text: str,
    *,
    completeness_level: str | None = None,
    resume_data: dict[str, Any] | None = None,
    signals: ResumeSignals | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Build strengths and improvements; each item may include evidence {section, count, ...}.
    """
    strengths: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []

    rd = resume_data if isinstance(resume_data, dict) else None
    rs = signals

    sparse = completeness_level in ("insufficient", "low")
    has_exp_body = bool(sections and (sections.experience or "").strip())
    summary = (sections.summary if sections else "") or ""
    summary_stripped = summary.strip()
    summary_words = len(summary_stripped.split())

    if rs and rs.experiences_count == 0:
        improvements.append(
            _item(
                "analysis.insights.improvements.add_experiences",
                priority="high",
                evidence={"section": "experience", "count": 0},
            )
        )
    if rs and rs.skills_count == 0:
        improvements.append(
            _item(
                "analysis.insights.improvements.add_skills",
                priority="high",
                evidence={"section": "skills", "count": 0},
            )
        )
    if rs and not rs.education_present:
        improvements.append(
            _item(
                "analysis.insights.improvements.add_education",
                priority="medium",
                evidence={"section": "education", "count": 0},
            )
        )

    if sparse:
        prio = "high" if completeness_level == "insufficient" else "medium"
        improvements.append(
            _item("analysis.insights.improvements.fill_core_sections", priority=prio, evidence={"level": completeness_level or ""})
        )
        if len(summary_stripped) < 20:
            improvements.append(
                _item(
                    "analysis.insights.improvements.executive_summary",
                    priority="high" if completeness_level == "insufficient" else "medium",
                    evidence={"summary_chars": str(len(summary_stripped))},
                )
            )
        elif len(summary_stripped) < 50 and summary_stripped:
            improvements.append(
                _item("analysis.insights.improvements.improve_summary", priority="medium", evidence={"summary_chars": str(len(summary_stripped))})
            )
    else:
        if not quality_flags.get("has_metrics") and has_exp_body:
            improvements.append(
                _item(
                    "analysis.insights.improvements.add_metrics",
                    priority="high",
                    params={"section": "experience"},
                    evidence={"section": "experience", "has_metrics": False},
                )
            )
        elif not quality_flags.get("has_metrics") and not has_exp_body:
            improvements.append(
                _item("analysis.insights.improvements.fill_core_sections", priority="high", evidence={"section": "experience"})
            )
        if not quality_flags.get("has_action_verbs") and (has_exp_body or len((resume_text or "").split()) > 40):
            improvements.append(
                _item(
                    "analysis.insights.improvements.use_action_verbs",
                    priority="medium",
                    evidence={"has_action_verbs": False},
                )
            )
        if not quality_flags.get("has_links"):
            improvements.append(
                _item("analysis.insights.improvements.relevant_links", priority="medium", evidence={"has_links": False})
            )
        if len(summary_stripped) < 50 and has_exp_body:
            improvements.append(
                _item("analysis.insights.improvements.improve_summary", priority="medium", evidence={"summary_chars": str(len(summary_stripped))})
            )

    if rd and education_tech_gap_suggestion(rd):
        improvements.append(
            _item("analysis.insights.improvements.education_target_gap", priority="high", evidence={"tech_gap": True})
        )

    # ATS keywords only when there is enough body to optimize (avoid noise on empty CV)
    if has_exp_body or (rs and rs.bullets_count > 0):
        improvements.append(
            _item("analysis.insights.improvements.ats_keywords", priority="medium", evidence={"section": "experience"})
        )

    if quality_flags.get("has_metrics"):
        strengths.append(_item("analysis.insights.strengths.has_metrics", evidence={"has_metrics": True}))
    if quality_flags.get("has_links"):
        strengths.append(_item("analysis.insights.strengths.has_links", evidence={"has_links": True}))
    if quality_flags.get("has_action_verbs"):
        strengths.append(_item("analysis.insights.strengths.has_action_verbs", evidence={"has_action_verbs": True}))

    if sections and len(summary_stripped) >= 50 and summary_words >= 12:
        if not sparse:
            strengths.append(
                _item("analysis.insights.strengths.clear_structure", evidence={"summary_words": str(summary_words)})
            )
        elif len(summary_stripped) >= 90 and summary_words >= 18:
            strengths.append(
                _item("analysis.insights.strengths.clear_structure", evidence={"summary_words": str(summary_words), "sparse": True})
            )

    edu_present = bool(rs.education_present) if rs else False
    if not rs and rd:
        data_edu = rd.get("data", rd)
        edu_present = any(
            any(str(e.get(k) or "").strip() for k in ("institution", "course", "degree"))
            for e in (data_edu.get("educations") or [])
        )
    if sections and (sections.education or "").strip() and rd and edu_present and education_aligned_with_target(rd):
        strengths.append(_item("analysis.insights.strengths.education_aligned", evidence={"education_present": True}))

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for imp in improvements:
        k = str(imp.get("key") or "")
        if k in seen:
            continue
        seen.add(k)
        deduped.append(imp)
    improvements = deduped

    if not improvements:
        improvements.append(_item("analysis.insights.improvements.other", priority="medium", params={}))

    return {"strengths": strengths, "improvements": improvements}
