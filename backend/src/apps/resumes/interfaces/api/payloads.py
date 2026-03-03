"""
Payload builders for resume API responses.
Pure extraction from views; no change to keys, shapes, or behavior.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Prefetch

from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeSkill,
    ResumeStatus,
)
from apps.resumes.infrastructure.models import ResumeVersion


def format_month(value: date | None) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m")


def resume_detail_prefetch():
    """Prefetch chain for resume detail (contact, experiences+bullets, educations, skills, languages)."""
    return [
        Prefetch(
            "resumeexperience_set",
            queryset=ResumeExperience.objects.order_by("position_index").prefetch_related(
                Prefetch(
                    "resumeexperiencebullet_set",
                    queryset=ResumeExperienceBullet.objects.order_by("position_index"),
                )
            ),
        ),
        Prefetch(
            "resumeeducation_set",
            queryset=ResumeEducation.objects.order_by("position_index"),
        ),
        Prefetch(
            "resumeskill_set",
            queryset=ResumeSkill.objects.order_by("position_index"),
        ),
        Prefetch(
            "resumelanguage_set",
            queryset=ResumeLanguage.objects.order_by("position_index"),
        ),
    ]


def resume_payload(resume: Resume) -> dict[str, Any]:
    # Use prefetched relations when available (list view); otherwise triggers queries.
    tag_objs = list(resume.resumetag_set.all())
    tags = [t.label for t in tag_objs]
    skill_objs = list(resume.resumeskill_set.all())[:5]
    skills = [s.name for s in skill_objs if (s.name or "").strip()]
    status_value = resume.status
    if status_value not in (ResumeStatus.DRAFT, ResumeStatus.COMPLETE, ResumeStatus.ANALYZING):
        status_value = ResumeStatus.DRAFT
    return {
        "id": str(resume.id),
        "name": resume.name or resume.target_position or "Novo Currículo",
        "updatedAt": resume.updated_at.isoformat(),
        "status": status_value,
        "score": resume.score,
        "tags": tags,
        "skills": skills,
    }


def resume_detail_payload(resume: Resume) -> dict[str, Any]:
    # Use prefetched/related data when available (detail view); avoids N+1.
    try:
        contact = resume.resumecontact
    except ResumeContact.DoesNotExist:
        contact = None

    experiences = list(resume.resumeexperience_set.all())
    educations = list(resume.resumeeducation_set.all())
    skills = list(resume.resumeskill_set.all())
    languages = list(resume.resumelanguage_set.all())

    exp_payload = []
    for exp in experiences:
        bullets = [b.content for b in exp.resumeexperiencebullet_set.all()]
        exp_payload.append(
            {
                "id": str(exp.id),
                "company": exp.company or "",
                "position": exp.position or "",
                "startDate": format_month(exp.start_date),
                "endDate": format_month(exp.end_date),
                "isCurrent": bool(exp.is_current),
                "description": bullets,
            }
        )

    edu_payload = [
        {
            "id": str(edu.id),
            "institution": edu.institution or "",
            "course": edu.course or "",
            "degree": edu.degree or "",
            "startDate": format_month(edu.start_date),
            "endDate": format_month(edu.end_date),
            "status": edu.status,
        }
        for edu in educations
    ]

    skill_payload = [
        {
            "id": str(skill.id),
            "name": skill.name or "",
            "level": skill.level or None,
        }
        for skill in skills
    ]

    lang_payload = [
        {
            "id": str(lang.id),
            "name": lang.name or "",
            "level": lang.level,
        }
        for lang in languages
    ]

    return {
        "id": str(resume.id),
        "name": resume.name or resume.target_position or "Novo Currículo",
        "status": resume.status,
        "updatedAt": resume.updated_at.isoformat(),
        "lastStep": resume.last_step,
        "data": {
            "themeId": resume.theme_id,
            "themePaletteId": resume.theme_palette_id or "",
            "themeAccentOverride": resume.theme_accent_override or "",
            "themeSecondaryOverride": resume.theme_secondary_override or "",
            "targetPosition": resume.target_position or "",
            "summary": resume.summary or "",
            "contact": {
                "fullName": contact.full_name or "" if contact else "",
                "email": contact.email or "" if contact else "",
                "phone": contact.phone or "" if contact else "",
                "city": contact.city or "" if contact else "",
                "country": contact.country or "" if contact else "",
                "linkedin": contact.linkedin or "" if contact else "",
                "portfolio": contact.portfolio or "" if contact else "",
                "github": contact.github or "" if contact else "",
                "website": contact.website or "" if contact else "",
            },
            "experiences": exp_payload,
            "educations": edu_payload,
            "skills": skill_payload,
            "languages": lang_payload,
        },
    }


def version_list_item_payload(version: ResumeVersion) -> dict[str, Any]:
    """Single version for list (all or filtered by resume)."""
    resume = version.resume
    return {
        "id": str(version.id),
        "resumeId": str(version.resume_id),
        "resumeTitle": resume.name or resume.target_position or "Novo Currículo",
        "version": version.version_number,
        "isCurrent": version.is_current,
        "score": version.score,
        "createdAt": version.created_at.isoformat(),
        "changes": version.change_summary_json or [],
    }


def version_detail_payload(version: ResumeVersion) -> dict[str, Any]:
    """Full version detail with snapshot for view/restore."""
    return {
        "id": str(version.id),
        "resumeId": str(version.resume_id),
        "resumeTitle": (version.resume.name or version.resume.target_position or "Novo Currículo"),
        "version": version.version_number,
        "isCurrent": version.is_current,
        "score": version.score,
        "createdAt": version.created_at.isoformat(),
        "changes": version.change_summary_json or [],
        "snapshot": version.snapshot_json,
    }
