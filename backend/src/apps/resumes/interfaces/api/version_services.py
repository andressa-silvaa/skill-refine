"""
Version history: snapshot creation, change summary, list, get, restore.
"""
from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.resumes.infrastructure.models import Resume, ResumeContact, ResumeVersion
from apps.resumes.interfaces.api.payloads import resume_detail_payload
from apps.resumes.interfaces.api.services import (
    get_resume_for_edit,
    normalize_optional,
    replace_educations,
    replace_experiences,
    replace_languages,
    replace_skills,
)


def _resume_snapshot_data(resume: Resume) -> dict[str, Any]:
    """Build the 'data' dict (API shape) for snapshot. Resume must have detail prefetch."""
    return resume_detail_payload(resume)["data"]


def _build_change_summary(prev: dict[str, Any] | None, new: dict[str, Any]) -> list[str]:
    """Heuristic: list of human-readable change descriptions."""
    if not prev:
        return ["Versão inicial"]
    summary = []
    # Summary
    if (new.get("summary") or "").strip() != (prev.get("summary") or "").strip():
        summary.append("Resumo profissional atualizado")
    # Contact
    c_old = prev.get("contact") or {}
    c_new = new.get("contact") or {}
    if (c_new.get("fullName") or "").strip() != (c_old.get("fullName") or "").strip():
        summary.append("Nome/contato atualizado")
    if (c_new.get("email") or "").strip() != (c_old.get("email") or "").strip():
        summary.append("E-mail atualizado")
    # Target position
    if (new.get("targetPosition") or "").strip() != (prev.get("targetPosition") or "").strip():
        summary.append("Cargo alvo atualizado")
    # Experiences
    exp_old = prev.get("experiences") or []
    exp_new = new.get("experiences") or []
    if len(exp_new) != len(exp_old):
        summary.append("Experiência profissional alterada")
    else:
        for i, ne in enumerate(exp_new):
            oe = exp_old[i] if i < len(exp_old) else {}
            if (ne.get("company") or "") != (oe.get("company") or "") or (ne.get("position") or "") != (oe.get("position") or ""):
                summary.append("Experiência profissional alterada")
                break
    # Educations
    edu_old = prev.get("educations") or []
    edu_new = new.get("educations") or []
    if len(edu_new) != len(edu_old):
        summary.append("Formação acadêmica alterada")
    # Skills
    skill_old = prev.get("skills") or []
    skill_new = new.get("skills") or []
    if len(skill_new) != len(skill_old):
        summary.append("Habilidades alteradas")
    # Languages
    lang_old = prev.get("languages") or []
    lang_new = new.get("languages") or []
    if len(lang_new) != len(lang_old):
        summary.append("Idiomas alterados")
    # Theme
    if (new.get("themeId") or "") != (prev.get("themeId") or ""):
        summary.append("Tema do currículo alterado")
    if not summary:
        summary.append("Alterações gerais")
    return summary


def _snapshots_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Simple equality to avoid creating duplicate versions."""
    import json
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def maybe_create_version_after_save(user_id: str, resume_id: str) -> None:
    """
    Called after create_resume_draft or update_resume_draft.
    Refetches resume with prefetch, builds snapshot; if different from previous current version, creates new version.
    """
    resume = get_resume_for_edit(user_id, resume_id)
    if not resume:
        return
    snapshot = _resume_snapshot_data(resume)
    prev_snapshot = None
    with transaction.atomic():
        current = ResumeVersion.objects.filter(resume_id=resume_id, is_current=True).first()
        if current:
            prev_snapshot = current.snapshot_json
            if _snapshots_equal(prev_snapshot, snapshot):
                return
            current.is_current = False
            current.save(update_fields=["is_current", "updated_at"])
        next_num = (
            ResumeVersion.objects.filter(resume_id=resume_id).order_by("-version_number").values_list("version_number", flat=True).first()
            or 0
        ) + 1
        change_summary = _build_change_summary(prev_snapshot, snapshot)
        ResumeVersion.objects.create(
            resume=resume,
            user_id=user_id,
            version_number=next_num,
            is_current=True,
            snapshot_json=snapshot,
            change_summary_json=change_summary,
            score=resume.score,
        )


def list_versions(user_id: str, resume_id: str | None = None):
    """
    List versions for user. If resume_id given, filter to that resume.
    Returns queryset of ResumeVersion with resume name for list payload.
    """
    qs = (
        ResumeVersion.objects.filter(user_id=user_id)
        .select_related("resume")
        .order_by("-created_at")
    )
    if resume_id:
        qs = qs.filter(resume_id=resume_id)
    return qs


def list_versions_paginated(
    user_id: str,
    limit: int,
    offset: int,
    resume_id: str | None = None,
) -> tuple[list[ResumeVersion], int]:
    qs = list_versions(user_id, resume_id=resume_id)
    total = qs.count()
    page = list(qs[offset : offset + limit])
    return page, total


def get_version_by_id(user_id: str, resume_id: str, version_id: str) -> ResumeVersion | None:
    """Get a single version; must belong to resume and user."""
    return (
        ResumeVersion.objects.filter(
            id=version_id,
            resume_id=resume_id,
            user_id=user_id,
        )
        .select_related("resume")
        .first()
    )


def restore_version(user_id: str, resume_id: str, version_id: str) -> Resume | None:
    """
    Restore resume to the state in the given version: apply snapshot to resume, then create a new version.
    Returns updated resume or None if not found/unauthorized.
    """
    version = get_version_by_id(user_id, resume_id, version_id)
    if not version:
        return None
    resume = (
        Resume.objects.filter(id=resume_id, user_id=user_id, deleted_at__isnull=True)
        .select_related("resumecontact")
        .first()
    )
    if not resume:
        return None
    snapshot = version.snapshot_json
    with transaction.atomic():
        # Apply snapshot to resume (main model)
        resume.target_position = (snapshot.get("targetPosition") or "").strip()
        resume.summary = (snapshot.get("summary") or "").strip()
        resume.theme_id = (snapshot.get("themeId") or "").strip() or resume.theme_id
        resume.theme_palette_id = normalize_optional(snapshot.get("themePaletteId"))
        resume.theme_accent_override = normalize_optional(snapshot.get("themeAccentOverride"))
        resume.theme_secondary_override = normalize_optional(snapshot.get("themeSecondaryOverride"))
        resume.save(update_fields=[
            "target_position", "summary", "theme_id", "theme_palette_id",
            "theme_accent_override", "theme_secondary_override", "updated_at",
        ])
        # Contact
        contact = snapshot.get("contact") or {}
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
        # Replace nested
        replace_experiences(resume, snapshot.get("experiences") or [])
        replace_educations(resume, snapshot.get("educations") or [])
        replace_skills(resume, snapshot.get("skills") or [])
        replace_languages(resume, snapshot.get("languages") or [])
        # Unset current, create new version from this snapshot
        ResumeVersion.objects.filter(resume_id=resume_id, is_current=True).update(is_current=False)
        next_num = (
            ResumeVersion.objects.filter(resume_id=resume_id).order_by("-version_number").values_list("version_number", flat=True).first()
            or 0
        ) + 1
        ResumeVersion.objects.create(
            resume=resume,
            user_id=user_id,
            version_number=next_num,
            is_current=True,
            snapshot_json=snapshot,
            change_summary_json=["Versão restaurada"],
            score=version.score,
        )
        from apps.notifications.services import create_notification

        resume_name = (resume.name or resume.target_position or "Currículo")[:80]
        create_notification(
            user_id=str(user_id),
            type="version_restored",
            title_key="notifications.versionRestored",
            params={"name": resume_name, "version": str(version.version_number)},
            action_url=f"/protected/version-history",
            entity_ref={"resume_id": str(resume_id), "version_id": str(version.id)},
        )
    return get_resume_for_edit(user_id, resume_id)
