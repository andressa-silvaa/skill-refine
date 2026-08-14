"""
Structured completeness for gating neural models and capping scores.
Cheap, deterministic; uses resume payload + mapped sections (not HF).
"""
from __future__ import annotations

from typing import Any

from .resume_signals import is_thin_student_or_intern_profile
from .types import ResumeSections


def assess_completeness(resume_data: dict[str, Any], sections: ResumeSections) -> dict[str, Any]:
    """
    Returns {"score": 0-100, "level": "insufficient"|"low"|"adequate"}.
    """
    data = resume_data.get("data", resume_data)

    score = 0
    full_text = (sections.full_text or "").strip()
    ft_len = len(full_text)
    if ft_len >= 900:
        score += 28
    elif ft_len >= 400:
        score += 22
    elif ft_len >= 120:
        score += 14
    elif ft_len >= 40:
        score += 8
    elif ft_len > 0:
        score += 3

    summary = (data.get("summary") or "").strip()
    sl = len(summary)
    if sl >= 120:
        score += 22
    elif sl >= 60:
        score += 18
    elif sl >= 35:
        score += 12
    elif sl >= 12:
        score += 6
    elif sl > 0:
        score += 2

    experiences = data.get("experiences") or []
    bullet_count = 0
    has_role_header = False
    for exp in experiences:
        pos = (exp.get("position") or "").strip()
        comp = (exp.get("company") or "").strip()
        if pos or comp:
            has_role_header = True
        for b in exp.get("description") or []:
            if str(b).strip():
                bullet_count += 1
    if bullet_count >= 4:
        score += 32
    elif bullet_count >= 2:
        score += 22
    elif bullet_count >= 1:
        score += 14
    elif has_role_header:
        score += 6

    educations = data.get("educations") or []
    edu_nonempty = 0
    for e in educations:
        if any(str(e.get(k) or "").strip() for k in ("institution", "course", "degree")):
            edu_nonempty += 1
    if edu_nonempty >= 1:
        score += 12

    skills: list[Any] = list(data.get("skills") or [])
    n_skills = 0
    for s in skills:
        name = s.get("name", s) if isinstance(s, dict) else s
        if str(name or "").strip():
            n_skills += 1
    if n_skills >= 6:
        score += 10
    elif n_skills >= 3:
        score += 7
    elif n_skills >= 1:
        score += 4

    score = min(100, score)

    if is_thin_student_or_intern_profile(resume_data):
        score = min(score, 46)

    if score < 28:
        level = "insufficient"
    elif score < 52:
        level = "low"
    else:
        level = "adequate"

    return {"score": score, "level": level}


def quality_score_cap(completeness: dict[str, Any]) -> int:
    """
    Max quality/ATS score allowed for this completeness level.

    This is an **out-of-distribution guard, not an uncertainty proxy**, and the difference is
    measured. The roadmap once proposed replacing these caps with calibrated abstention on the
    model's own uncertainty; the measurement killed that plan and justified keeping them for a
    different reason (ml/reports/completeness_caps_v3.md):

    * The head's confidence does **not** fall on sparse resumes — mean margin 0.683 on ``adequate``
      against 0.669 on ``low``. Completeness does not predict how sure the model is, so it was never
      an uncertainty proxy and can't be replaced by one.
    * It does predict something an uncertainty measure cannot see. Asked directly, the head scores a
      completely empty resume at **78**, with a *confident* margin of 0.368 — an all-zero feature
      vector lands on the linear head's bias term. No abstention keyed on confidence catches that,
      because the model is not uncertain; it is confidently answering a question it was never shown.

    Where each guard actually fires, which is easy to get wrong:

    * ``insufficient`` never reaches the head at all. ``allow_quality_neural`` in the orchestrator
      gates the neural path off at that level, so quality refuses and the analysis fails. **The cap
      of 40 is therefore unreachable in production** and only applies in the golden snapshot, where
      the heuristic is allowed to answer. It is kept for that path, not because it guards anything.
    * ``low`` does reach the head, so 72 is the cap that can really bind — measured at 33% of that
      group.

    Both numbers remain declared product policy rather than derived. The corpus contains no resume
    that reads ``insufficient``, and only 16 labelled ones read ``low`` — too few to fit a value on.
    Declaring them beats implying they were measured.

    The two mechanisms cover different failures and both stay: this cap and the completeness gate for
    degenerate input, ``LOW_CONFIDENCE_MARGIN`` in ``tasks/quality/predict.py`` for in-distribution
    doubt. The shallow-but-``adequate`` resume is the case only the margin catches.
    """
    level = completeness.get("level") or "adequate"
    if level == "insufficient":
        return 40
    if level == "low":
        return 72
    return 100


def matching_score_cap(completeness: dict[str, Any]) -> int:
    if completeness.get("level") == "insufficient":
        return 38
    if completeness.get("level") == "low":
        return 68
    return 100
