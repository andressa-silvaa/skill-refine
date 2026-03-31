from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from apps.resumes.infrastructure.models import (
    Resume,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeSectionOrder,
    ResumeSkill,
)


def parse_resume_date(value: str | None) -> date | None:
    """Aceita YYYY-MM-DD ou legado YYYY-MM (dia 1)."""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    parts = raw.split("-")
    try:
        if len(parts) == 3:
            y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
            return date(y, m, d)
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            if m < 1 or m > 12:
                return None
            return date(y, m, 1)
    except (ValueError, TypeError):
        return None
    return None


# Alias usado por código legado / testes
parse_month = parse_resume_date


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def validate_complete(data: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    target_position = (data.get("targetPosition") or "").strip()
    contact = data.get("contact") or {}
    full_name = (contact.get("fullName") or "").strip()
    email = (contact.get("email") or "").strip()
    if not target_position:
        fields["targetPosition"] = "Informe o cargo alvo."
    if not full_name:
        fields["contact.fullName"] = "Informe o nome completo."
    if not email:
        fields["contact.email"] = "Informe o e-mail."
    return fields


def replace_experiences(resume: Resume, experiences: Iterable[dict[str, Any]]) -> None:
    ResumeExperience.objects.filter(resume=resume).delete()
    for idx, exp in enumerate(experiences):
        exp_obj = ResumeExperience.objects.create(
            resume=resume,
            company=exp.get("company") or "",
            position=exp.get("position") or "",
            start_date=parse_resume_date(exp.get("startDate")),
            end_date=parse_resume_date(exp.get("endDate")),
            is_current=bool(exp.get("isCurrent")),
            position_index=idx,
        )
        bullets = exp.get("description") or []
        for b_idx, content in enumerate(bullets):
            ResumeExperienceBullet.objects.create(
                experience=exp_obj,
                content=str(content or ""),
                position_index=b_idx,
            )


def replace_educations(resume: Resume, educations: Iterable[dict[str, Any]]) -> None:
    ResumeEducation.objects.filter(resume=resume).delete()
    for idx, edu in enumerate(educations):
        ResumeEducation.objects.create(
            resume=resume,
            institution=edu.get("institution") or "",
            course=edu.get("course") or "",
            degree=edu.get("degree") or "",
            start_date=parse_resume_date(edu.get("startDate")),
            end_date=parse_resume_date(edu.get("endDate")),
            status=edu.get("status") or "completed",
            position_index=idx,
        )


def replace_skills(resume: Resume, skills: Iterable[dict[str, Any]]) -> None:
    ResumeSkill.objects.filter(resume=resume).delete()
    for idx, skill in enumerate(skills):
        ResumeSkill.objects.create(
            resume=resume,
            name=skill.get("name") or "",
            level=skill.get("level") or None,
            position_index=idx,
        )


def replace_languages(resume: Resume, languages: Iterable[dict[str, Any]]) -> None:
    ResumeLanguage.objects.filter(resume=resume).delete()
    for idx, lang in enumerate(languages):
        ResumeLanguage.objects.create(
            resume=resume,
            name=lang.get("name") or "",
            level=lang.get("level") or "intermediate",
            position_index=idx,
        )


def unique_copy_name(user_id: str, base_name: str) -> str:
    """Return a unique name for a duplicated resume (e.g. 'Cópia de X' or 'Cópia de X (2)')."""
    base = base_name.strip() or "Currículo"
    candidate = f"Cópia de {base}"
    existing = set(
        Resume.objects.filter(
            user_id=user_id,
            name__startswith=candidate,
            deleted_at__isnull=True,
        ).values_list("name", flat=True)
    )
    if candidate not in existing:
        return candidate
    suffix = 2
    while f"{candidate} ({suffix})" in existing:
        suffix += 1
    return f"{candidate} ({suffix})"


def section_order(resume: Resume) -> list[str]:
    orders = list(
        ResumeSectionOrder.objects.filter(resume=resume, is_visible=True).order_by("position_index")
    )
    if orders:
        return [order.section_key for order in orders]
    return ["summary", "experience", "education", "skills", "languages", "contact"]
