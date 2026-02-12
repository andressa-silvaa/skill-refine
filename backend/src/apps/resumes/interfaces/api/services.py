"""
Resume orchestration and persistence.
Pure extraction from views; no change to business rules or behavior.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from django.core import signing
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeSectionOrder,
    ResumeSkill,
    ResumeStatus,
    ResumeTag,
)

from .payloads import resume_detail_prefetch


def parse_month(value: str | None) -> Any:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    parts = raw.split("-")
    if len(parts) != 2:
        return None
    year_str, month_str = parts
    try:
        year = int(year_str)
        month = int(month_str)
    except ValueError:
        return None
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


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
            start_date=parse_month(exp.get("startDate")),
            end_date=parse_month(exp.get("endDate")),
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
            start_date=parse_month(edu.get("startDate")),
            end_date=parse_month(edu.get("endDate")),
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


def unique_copy_name(user_id: str, base_name: str) -> str | None:
    base = base_name.strip() or "Currículo"
    candidate = f"Cópia de {base}"
    if not Resume.objects.filter(user_id=user_id, name=candidate, deleted_at__isnull=True).exists():
        return candidate
    return None


def section_order(resume: Resume) -> list[str]:
    orders = list(
        ResumeSectionOrder.objects.filter(resume=resume, is_visible=True).order_by("position_index")
    )
    if orders:
        return [order.section_key for order in orders]
    return ["summary", "experience", "education", "skills", "languages", "contact"]


PDF_TOKEN_SALT = "resume-pdf"
PDF_TOKEN_TTL_SECONDS = 120


def create_pdf_token(resume_id: str, user_id: str) -> str:
    return signing.dumps({"resume_id": resume_id, "user_id": user_id}, salt=PDF_TOKEN_SALT)


def parse_pdf_token(token: str | None) -> dict[str, str] | None:
    if not token:
        return None
    try:
        data = signing.loads(token, salt=PDF_TOKEN_SALT, max_age=PDF_TOKEN_TTL_SECONDS)
    except signing.SignatureExpired:
        return None
    except signing.BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    resume_id = str(data.get("resume_id") or "").strip()
    user_id = str(data.get("user_id") or "").strip()
    if not resume_id or not user_id:
        return None
    return {"resume_id": resume_id, "user_id": user_id}


def _list_resumes_queryset(user_id: str):
    """Base queryset for list resumes (same ordering and prefetch as list_resumes)."""
    return (
        Resume.objects.filter(user_id=user_id, deleted_at__isnull=True)
        .order_by("-updated_at")
        .prefetch_related(
            Prefetch(
                "resumetag_set",
                queryset=ResumeTag.objects.order_by("position_index"),
            ),
            Prefetch(
                "resumeskill_set",
                queryset=ResumeSkill.objects.order_by("position_index"),
            ),
        )
    )


def list_resumes(user_id: str):
    """Return queryset of user resumes with list prefetch (tags, skills)."""
    return _list_resumes_queryset(user_id)


def list_resumes_paginated(
    user_id: str, limit: int, offset: int
) -> tuple[list[Resume], int]:
    """
    Return (page of resumes, total count) for the user.
    Same ordering (-updated_at) and prefetch as list_resumes.
    """
    qs = _list_resumes_queryset(user_id)
    total = qs.count()
    page = list(qs[offset : offset + limit])
    return (page, total)


def get_resume_for_edit(user_id: str, resume_id: str) -> Resume | None:
    """Return resume for GET draft/detail or None if not found."""
    return (
        Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True)
        .select_related("resumecontact")
        .prefetch_related(*resume_detail_prefetch())
        .first()
    )


def create_resume_draft(user_id: str, data: dict[str, Any]) -> Resume:
    """Create resume and related records; returns the created Resume."""
    with transaction.atomic():
        status_value = data.get("status") or "draft"
        resume = Resume.objects.create(
            user_id=user_id,
            name=(data.get("name") or "").strip(),
            status=ResumeStatus.COMPLETE if status_value == "complete" else ResumeStatus.DRAFT,
            last_step=(data.get("lastStep") or "").strip() or None,
            target_position=(data.get("targetPosition") or "").strip(),
            summary=(data.get("summary") or "").strip(),
            theme_id=(data.get("themeId") or "").strip() or "classic-one-column",
            theme_palette_id=normalize_optional(data.get("themePaletteId")),
            theme_accent_override=normalize_optional(data.get("themeAccentOverride")),
            theme_secondary_override=normalize_optional(data.get("themeSecondaryOverride")),
            score=data.get("score") if data.get("score") is not None else None,
        )

        contact = data.get("contact")
        if contact is not None:
            ResumeContact.objects.update_or_create(
                resume=resume,
                defaults={
                    "full_name": contact.get("fullName") or "",
                    "email": contact.get("email") or "",
                    "phone": contact.get("phone") or "",
                    "city": contact.get("city") or "",
                    "country": contact.get("country") or "",
                    "linkedin": normalize_optional(contact.get("linkedin")),
                    "portfolio": normalize_optional(contact.get("portfolio")),
                    "github": normalize_optional(contact.get("github")),
                    "website": normalize_optional(contact.get("website")),
                },
            )

        if "experiences" in data:
            replace_experiences(resume, data.get("experiences") or [])
        if "educations" in data:
            replace_educations(resume, data.get("educations") or [])
        if "skills" in data:
            replace_skills(resume, data.get("skills") or [])
        if "languages" in data:
            replace_languages(resume, data.get("languages") or [])

    return resume


def update_resume_draft(user_id: str, resume_id: str, data: dict[str, Any]) -> Resume | None:
    """Update resume and related records; returns the Resume or None if not found."""
    resume = (
        Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True)
        .select_related("resumecontact")
        .first()
    )
    if not resume:
        return None

    status_value = data.get("status")

    with transaction.atomic():
        if "name" in data:
            resume.name = (data.get("name") or "").strip()
        if "targetPosition" in data:
            resume.target_position = (data.get("targetPosition") or "").strip()
        if "summary" in data:
            resume.summary = (data.get("summary") or "").strip()
        if "themeId" in data:
            resume.theme_id = (data.get("themeId") or "").strip() or resume.theme_id
        if "themePaletteId" in data:
            resume.theme_palette_id = normalize_optional(data.get("themePaletteId"))
        if "themeAccentOverride" in data:
            resume.theme_accent_override = normalize_optional(data.get("themeAccentOverride"))
        if "themeSecondaryOverride" in data:
            resume.theme_secondary_override = normalize_optional(data.get("themeSecondaryOverride"))
        if "lastStep" in data:
            resume.last_step = (data.get("lastStep") or "").strip() or None
        if "score" in data:
            resume.score = data.get("score") if data.get("score") is not None else None
        if status_value == "complete":
            resume.status = ResumeStatus.COMPLETE
        elif status_value == "draft":
            resume.status = ResumeStatus.DRAFT

        resume.save()

        if "contact" in data:
            contact = data.get("contact") or {}
            ResumeContact.objects.update_or_create(
                resume=resume,
                defaults={
                    "full_name": contact.get("fullName") or "",
                    "email": contact.get("email") or "",
                    "phone": contact.get("phone") or "",
                    "city": contact.get("city") or "",
                    "country": contact.get("country") or "",
                    "linkedin": normalize_optional(contact.get("linkedin")),
                    "portfolio": normalize_optional(contact.get("portfolio")),
                    "github": normalize_optional(contact.get("github")),
                    "website": normalize_optional(contact.get("website")),
                },
            )

        if "experiences" in data:
            replace_experiences(resume, data.get("experiences") or [])
        if "educations" in data:
            replace_educations(resume, data.get("educations") or [])
        if "skills" in data:
            replace_skills(resume, data.get("skills") or [])
        if "languages" in data:
            replace_languages(resume, data.get("languages") or [])

    return resume


def duplicate_resume(user_id: str, resume_id: str) -> Resume | None:
    """Duplicate resume and all related records; returns the new Resume or None if source not found."""
    resume = (
        Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True)
        .select_related("resumecontact")
        .prefetch_related(
            *resume_detail_prefetch(),
            Prefetch(
                "resumetag_set",
                queryset=ResumeTag.objects.order_by("position_index"),
            ),
            Prefetch(
                "resumesectionorder_set",
                queryset=ResumeSectionOrder.objects.order_by("position_index"),
            ),
        )
        .first()
    )
    if not resume:
        return None

    try:
        contact = resume.resumecontact
    except ResumeContact.DoesNotExist:
        contact = None
    experiences = list(resume.resumeexperience_set.all())
    educations = list(resume.resumeeducation_set.all())
    skills = list(resume.resumeskill_set.all())
    languages = list(resume.resumelanguage_set.all())
    tags = list(resume.resumetag_set.all())
    section_orders = list(resume.resumesectionorder_set.all())

    with transaction.atomic():
        copy_name = unique_copy_name(user_id, resume.name or resume.target_position or "Currículo")
        new_resume = Resume.objects.create(
            user_id=user_id,
            name=copy_name,
            status=ResumeStatus.DRAFT,
            target_position=resume.target_position,
            summary=resume.summary,
            theme_id=resume.theme_id,
            theme_palette_id=resume.theme_palette_id,
            theme_accent_override=resume.theme_accent_override,
            theme_secondary_override=resume.theme_secondary_override,
            last_step=resume.last_step,
            score=resume.score,
        )

        if contact:
            ResumeContact.objects.create(
                resume=new_resume,
                full_name=contact.full_name,
                email=contact.email,
                phone=contact.phone,
                city=contact.city,
                country=contact.country,
                linkedin=contact.linkedin,
                portfolio=contact.portfolio,
                github=contact.github,
                website=contact.website,
            )

        for exp in experiences:
            new_exp = ResumeExperience.objects.create(
                resume=new_resume,
                company=exp.company,
                position=exp.position,
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                position_index=exp.position_index,
            )
            for bullet in exp.resumeexperiencebullet_set.all():
                ResumeExperienceBullet.objects.create(
                    experience=new_exp,
                    content=bullet.content,
                    position_index=bullet.position_index,
                )

        for edu in educations:
            ResumeEducation.objects.create(
                resume=new_resume,
                institution=edu.institution,
                course=edu.course,
                degree=edu.degree,
                start_date=edu.start_date,
                end_date=edu.end_date,
                status=edu.status,
                position_index=edu.position_index,
            )

        for skill in skills:
            ResumeSkill.objects.create(
                resume=new_resume,
                name=skill.name,
                level=skill.level,
                position_index=skill.position_index,
            )

        for lang in languages:
            ResumeLanguage.objects.create(
                resume=new_resume,
                name=lang.name,
                level=lang.level,
                position_index=lang.position_index,
            )

        for tag in tags:
            ResumeTag.objects.create(
                resume=new_resume,
                label=tag.label,
                position_index=tag.position_index,
            )

        for order in section_orders:
            ResumeSectionOrder.objects.create(
                resume=new_resume,
                section_key=order.section_key,
                position_index=order.position_index,
                is_visible=order.is_visible,
            )

    return new_resume


def delete_resume_soft(user_id: str, resume_id: str) -> bool:
    """Soft-delete resume; returns True if found and deleted."""
    resume = Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True).first()
    if not resume:
        return False
    resume.deleted_at = timezone.now()
    resume.save(update_fields=["deleted_at"])
    return True


def get_resume_for_pdf_data(resume_id: str, user_id: str) -> Resume | None:
    """Return resume with detail prefetch for PDF data endpoint (token-validated)."""
    return (
        Resume.objects.filter(
            id=resume_id,
            user_id=user_id,
            deleted_at__isnull=True,
        )
        .select_related("resumecontact")
        .prefetch_related(*resume_detail_prefetch())
        .first()
    )


def get_resume_by_id_and_user(user_id: str, resume_id: str) -> Resume | None:
    """Return resume by id and user (no prefetch). Used for PDF token and PDF download."""
    return Resume.objects.filter(
        id=resume_id, user_id=user_id, deleted_at__isnull=True
    ).first()
