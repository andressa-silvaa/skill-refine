from __future__ import annotations

from typing import Any

from apps.accounts.infrastructure.cloudinary_avatar import avatar_url
from apps.accounts.infrastructure.models import User, UserPreferences
from apps.analysis.interfaces.api.payloads import analysis_payload
from apps.analysis.models import ResumeAnalysis
from apps.audit.infrastructure.models import AuditLog
from apps.resumes.infrastructure.models import Resume, ResumeVersion
from apps.resumes.interfaces.api.payloads import resume_detail_payload, version_detail_payload


def account_payload(user: User) -> dict[str, Any]:
    key = str(getattr(user, "avatar_storage_key", "") or "")
    return {
        "id": str(user.id),
        "email": user.email,
        "fullName": user.full_name,
        "birthDate": user.birth_date.isoformat() if user.birth_date else None,
        "emailVerifiedAt": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "status": user.status,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "updatedAt": user.updated_at.isoformat() if user.updated_at else None,
        "avatarStorageKey": key or None,
        "avatarUrl": avatar_url(key) if key else None,
    }


def preferences_payload(preferences: UserPreferences | None) -> dict[str, Any]:
    if not preferences:
        return {
            "language": "pt-BR",
            "theme": "light",
            "accentColor": "pink",
            "emailNotificationsEnabled": True,
            "region": None,
        }
    return {
        "language": preferences.language,
        "theme": preferences.theme,
        "accentColor": preferences.accent_color,
        "emailNotificationsEnabled": bool(preferences.email_notifications_enabled),
        "region": preferences.region,
        "createdAt": preferences.created_at.isoformat() if preferences.created_at else None,
        "updatedAt": preferences.updated_at.isoformat() if preferences.updated_at else None,
    }


def resume_export_payload(resume: Resume) -> dict[str, Any]:
    detail = resume_detail_payload(resume)
    detail["createdAt"] = resume.created_at.isoformat()
    detail["score"] = resume.score
    return detail


def version_export_payload(version: ResumeVersion) -> dict[str, Any]:
    return version_detail_payload(version)


def analysis_export_payload(analysis: ResumeAnalysis) -> dict[str, Any]:
    return analysis_payload(analysis)


def audit_log_payload(item: AuditLog) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "action": item.action,
        "actorUserId": str(item.actor_user_id) if item.actor_user_id else None,
        "subjectUserId": str(item.subject_user_id) if item.subject_user_id else None,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
        "ip": item.ip,
        "userAgent": item.user_agent,
        "metadata": item.metadata or {},
    }

