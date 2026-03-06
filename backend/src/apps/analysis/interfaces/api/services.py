"""
Analysis orchestration: run, latest, history.
Validates resume ownership; delegates execution to Celery task.
Falls back to threading when Celery broker unavailable.
"""
from __future__ import annotations

import logging
import threading
from uuid import UUID

from django.conf import settings
from django.db.models import OuterRef, Subquery

from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume
from apps.analysis.tasks import run_resume_analysis_task
from apps.resumes.interfaces.api.services import get_resume_by_id_and_user

logger = logging.getLogger(__name__)

JOB_DESCRIPTION_MAX_LENGTH = 10_000


def _use_celery() -> bool:
    """True if Celery broker is configured and we should use it."""
    return bool(getattr(settings, "CELERY_BROKER_URL", "")) and getattr(
        settings, "CELERY_TASKS_ENABLED", True
    )


def _allow_inprocess_fallback() -> bool:
    return bool(getattr(settings, "ALLOW_INPROCESS_JOB_FALLBACK", False))


def _start_inprocess_analysis(analysis_id: str) -> None:
    threading.Thread(
        target=run_resume_analysis_task,
        args=(analysis_id,),
        name=f"analysis-{analysis_id}",
        daemon=True,
    ).start()


def _mark_analysis_failed(analysis: ResumeAnalysis) -> None:
    analysis.status = AnalysisStatus.FAILED
    analysis.error_message = "Fila de análise indisponível. Tente novamente em instantes."
    analysis.save(update_fields=["status", "error_message", "updated_at"])


def validate_resume_ownership(user_id: str, resume_id: str) -> bool:
    """Return True if resume exists and belongs to user."""
    resume = get_resume_by_id_and_user(user_id, str(resume_id))
    return resume is not None


def run_analysis(
    user_id: str,
    resume_id: UUID | str,
    job_description_text: str | None = None,
) -> ResumeAnalysis | None:
    """
    Create a pending ResumeAnalysis and enqueue execution (Celery or thread).
    Returns the created analysis or None if resume not found/not owned.
    """
    if not validate_resume_ownership(user_id, str(resume_id)):
        return None

    analysis = ResumeAnalysis.objects.create(
        user_id=user_id,
        resume_id=str(resume_id),
        status=AnalysisStatus.PENDING,
        job_description_text=(job_description_text or "")[:JOB_DESCRIPTION_MAX_LENGTH] or None,
    )

    if _use_celery():
        try:
            run_resume_analysis_task.delay(str(analysis.id))
        except Exception as exc:
            if _allow_inprocess_fallback():
                logger.warning("Celery unavailable, falling back to thread: %s", exc)
                _start_inprocess_analysis(str(analysis.id))
            else:
                logger.error("Celery unavailable and in-process fallback disabled: %s", exc)
                _mark_analysis_failed(analysis)
    else:
        if _allow_inprocess_fallback():
            _start_inprocess_analysis(str(analysis.id))
        else:
            _mark_analysis_failed(analysis)

    return analysis


def get_latest_analysis(user_id: str, resume_id: str) -> ResumeAnalysis | None:
    """Return the most recent analysis for this resume owned by user, or None."""
    if not validate_resume_ownership(user_id, resume_id):
        return None
    return (
        ResumeAnalysis.objects.filter(
            user_id=user_id,
            resume_id=resume_id,
        )
        .order_by("-created_at")
        .first()
    )


def get_latest_analyses_map(user_id: str, resume_ids: list[str]) -> dict[str, ResumeAnalysis]:
    """
    Return latest analysis per owned resume id.
    Ignores resume IDs not owned by user.
    """
    cleaned = [str(rid).strip() for rid in resume_ids if str(rid).strip()]
    if not cleaned:
        return {}

    owned_ids = list(
        Resume.objects.filter(
            user_id=user_id,
            id__in=cleaned,
            deleted_at__isnull=True,
        ).values_list("id", flat=True)
    )
    if not owned_ids:
        return {}

    latest_analysis_subquery = (
        ResumeAnalysis.objects.filter(
            user_id=user_id,
            resume_id=OuterRef("resume_id"),
        )
        .order_by("-created_at")
        .values("id")[:1]
    )
    latest = list(
        ResumeAnalysis.objects.filter(
            user_id=user_id,
            resume_id__in=owned_ids,
        )
        .filter(id=Subquery(latest_analysis_subquery))
    )
    by_resume: dict[str, ResumeAnalysis] = {}
    for analysis in latest:
        by_resume[str(analysis.resume_id)] = analysis
    return by_resume


def list_analysis_history(
    user_id: str,
    resume_id: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ResumeAnalysis], int]:
    """Return (page of analyses, total count) for this resume owned by user."""
    if not validate_resume_ownership(user_id, resume_id):
        return ([], 0)
    qs = ResumeAnalysis.objects.filter(
        user_id=user_id,
        resume_id=resume_id,
    ).order_by("-created_at")
    total = qs.count()
    page = list(qs[offset : offset + limit])
    return (page, total)
