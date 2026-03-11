from __future__ import annotations

from datetime import date

from django.db.models import Q
from django.utils import timezone

from apps.accounts.infrastructure.models import User, UserPreferences
from apps.analysis.models import ResumeAnalysis
from apps.audit.models import AuditLog
from apps.resumes.infrastructure.models import Resume, ResumeVersion
from apps.resumes.interfaces.api.payloads import resume_detail_prefetch

from .payloads import (
    account_payload,
    analysis_export_payload,
    audit_log_payload,
    preferences_payload,
    resume_export_payload,
    version_export_payload,
)


def export_filename_for_today() -> str:
    return f"skill-refine-data-export-{date.today().isoformat()}.json"


def build_user_data_export(user_id: str) -> dict | None:
    user = User.objects.filter(id=user_id, deleted_at__isnull=True).first()
    if not user:
        return None

    preferences = UserPreferences.objects.filter(user_id=user_id).first()

    resumes = list(
        Resume.objects.filter(user_id=user_id, deleted_at__isnull=True)
        .select_related("resumecontact")
        .prefetch_related(*resume_detail_prefetch())
        .order_by("-updated_at")
    )

    versions = list(
        ResumeVersion.objects.filter(user_id=user_id)
        .select_related("resume")
        .order_by("-created_at")
    )

    analyses = list(
        ResumeAnalysis.objects.filter(user_id=user_id)
        .select_related("resume")
        .order_by("-created_at")
    )

    audit_logs = list(
        AuditLog.objects.filter(Q(actor_user_id=user_id) | Q(subject_user_id=user_id))
        .order_by("-created_at")
    )

    return {
        "meta": {
            "schemaVersion": "1.0",
            "exportedAt": timezone.now().isoformat(),
        },
        "account": account_payload(user),
        "preferences": preferences_payload(preferences),
        "resumes": [resume_export_payload(r) for r in resumes],
        "versionHistory": [version_export_payload(v) for v in versions],
        "analyses": [analysis_export_payload(a) for a in analyses],
        "auditLogs": [audit_log_payload(a) for a in audit_logs],
    }

