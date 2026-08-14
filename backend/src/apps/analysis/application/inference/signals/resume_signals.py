"""
Extract structured ResumeSignals from payload + ResumeSections (feature engineering).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from ..completeness import assess_completeness
from ..tasks.quality.predict import LEADERSHIP_WORDS, LINK_PATTERN
from ..resume_signals import max_years_mentioned_in_work_context
from ..types import ResumeSections
from .date_math import (
    experience_intervals,
    merge_intervals_months,
    months_in_current_role,
    parse_payload_date,
)
from .types import ResumeSignals

_INTERNSHIP_RE = re.compile(
    r"\best[aá]gio\b|\bestagi[aá]ri[oa]?\b|\binternship\b|\bintern\b|\btrainee\b|"
    r"\bpr[aá]cticas\b|\bpracticantes?\b|\bpasantes?\b",
    re.I,
)


def _data(resume_data: dict[str, Any]) -> dict[str, Any]:
    return resume_data.get("data", resume_data)


def _career_text_blob(resume_data: dict[str, Any]) -> str:
    data = _data(resume_data)
    parts: list[str] = []
    parts.append(str(resume_data.get("name") or ""))
    for key in ("targetPosition", "summary"):
        parts.append(str(data.get(key) or ""))
    for exp in data.get("experiences") or []:
        parts.append(str(exp.get("position") or ""))
        parts.append(str(exp.get("company") or ""))
        for b in exp.get("description") or []:
            parts.append(str(b))
    return " ".join(parts).lower()


def _experience_recency_key(exp: dict[str, Any]) -> date | None:
    end = parse_payload_date(str(exp.get("endDate") or "").strip() or None)
    if end:
        return end
    return parse_payload_date(str(exp.get("startDate") or "").strip() or None)


def _most_recent_experiences(experiences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Current role(s) if flagged, else the most recently dated one(s). Falls back to
    every experience when none carries a usable date, since recency can't be judged.
    """
    if not experiences:
        return []
    current = [e for e in experiences if bool(e.get("isCurrent"))]
    if current:
        return current
    dated = [(exp, _experience_recency_key(exp)) for exp in experiences]
    known_dates = [d for _, d in dated if d]
    if not known_dates:
        return experiences
    latest = max(known_dates)
    return [exp for exp, d in dated if d == latest]


def _recent_role_text_blob(resume_data: dict[str, Any]) -> str:
    """
    Scoped to the current/most recent role(s) only — an internship or trainee stint
    years in the past shouldn't veto a candidate's present-day seniority.
    """
    data = _data(resume_data)
    parts: list[str] = []
    for key in ("targetPosition", "summary"):
        parts.append(str(data.get(key) or ""))
    for exp in _most_recent_experiences(list(data.get("experiences") or [])):
        parts.append(str(exp.get("position") or ""))
        parts.append(str(exp.get("company") or ""))
        for b in exp.get("description") or []:
            parts.append(str(b))
    return " ".join(parts).lower()


def _contact_links_present(resume_data: dict[str, Any]) -> bool:
    data = _data(resume_data)
    contact = data.get("contact") or {}
    for key in ("linkedin", "github", "portfolio", "website"):
        v = str(contact.get(key) or "").strip()
        if v:
            return True
    return False


def extract_resume_signals(
    resume_data: dict[str, Any],
    sections: ResumeSections | None,
    language: str = "pt-BR",
    leadership_override: bool | None = None,
) -> ResumeSignals:
    """
    Build signals from structured fields + section strings (no reliance on full_text alone).

    ``leadership_override`` carries the ``bullet_probe`` answer when the head is loaded. The regex
    below stays as the fallback: it scans the whole career blob, so a job title alone sets the flag
    and "supervisar la tensión y la corriente" reads as directing people. Measured against a
    two-annotator consensus it recovers 0.32 of the positives at 0.57 precision, which is below the
    majority class (ml/reports/bullet_probe_v3.md).
    """
    lang = (language or "pt-BR").strip()
    data = _data(resume_data)
    experiences: list[dict[str, Any]] = list(data.get("experiences") or [])
    experiences_count = len(experiences)
    bullets_count = 0
    for exp in experiences:
        for b in exp.get("description") or []:
            if str(b).strip():
                bullets_count += 1

    intervals, date_reasons = experience_intervals(experiences)
    total_months = merge_intervals_months(intervals)
    work_years = max_years_mentioned_in_work_context(resume_data)
    text_months = min(120, work_years * 12) if work_years and experiences_count > 0 else 0
    # Text-derived "N anos" mentions are noisy (may refer to study/hobby time, not
    # tenure) — only trusted as a floor when structured dates yield nothing at all.
    effective_months = total_months if total_months > 0 else text_months
    has_current = any(bool(e.get("isCurrent")) for e in experiences)
    months_current = months_in_current_role(experiences)

    blob = _career_text_blob(resume_data)
    has_internship = bool(_INTERNSHIP_RE.search(_recent_role_text_blob(resume_data)))
    has_leadership = (
        bool(leadership_override)
        if leadership_override is not None
        else bool(LEADERSHIP_WORDS.search(blob))
    )
    section_text = ((sections.full_text if sections else "") or "").lower()
    has_links = _contact_links_present(resume_data) or bool(LINK_PATTERN.search(section_text))

    summary = str(data.get("summary") or "")
    summary_char_count = len(summary.strip())

    skills = data.get("skills") or []
    skills_count = 0
    for s in skills:
        name = s.get("name", s) if isinstance(s, dict) else s
        if str(name or "").strip():
            skills_count += 1

    education_present = False
    for edu in data.get("educations") or []:
        if any(str(edu.get(k) or "").strip() for k in ("institution", "course", "degree")):
            education_present = True
            break

    completeness = assess_completeness(resume_data, sections) if sections else {"score": 0, "level": "insufficient"}
    c_score = int(completeness.get("score") or 0)
    c_level = str(completeness.get("level") or "insufficient")

    reasons: list[str] = list(date_reasons)
    if experiences_count == 0:
        reasons.append("no_experiences")
    if bullets_count == 0 and experiences_count > 0:
        reasons.append("no_experience_bullets")
    if c_level == "insufficient":
        reasons.append("completeness_insufficient")

    insufficient_data = c_level == "insufficient" or (experiences_count == 0 and bullets_count == 0)

    word_count = len((sections.full_text if sections else "").split()) if sections else 0

    return ResumeSignals(
        total_months_experience=total_months,
        effective_months_experience=effective_months,
        experiences_count=experiences_count,
        bullets_count=bullets_count,
        has_current_role=has_current,
        months_in_current_role=months_current,
        has_internship_terms=has_internship,
        has_leadership_terms=has_leadership,
        has_links=has_links,
        summary_char_count=summary_char_count,
        skills_count=skills_count,
        education_present=education_present,
        completeness_score=c_score,
        completeness_level=c_level,
        insufficient_data=insufficient_data,
        reasons=tuple(sorted(set(reasons))),
        word_count=word_count,
        language=lang,
    )
