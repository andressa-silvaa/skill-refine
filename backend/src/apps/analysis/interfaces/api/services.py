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
from apps.analysis.application.analysis_resume_validity import is_analysis_valid_for_resume
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.infrastructure.models import Resume
from apps.analysis.application.worker import run_analysis_worker_safe
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
    """In prod (DEBUG=False), default False. In dev, default True."""
    default = getattr(settings, "DEBUG", False)
    return bool(getattr(settings, "ALLOW_INPROCESS_JOB_FALLBACK", default))


def is_analysis_available() -> tuple[bool, str | None]:
    """
    Return (True, None) if analysis can be run, else (False, error_message).
    In prod: Celery must be available or 503.
    """
    if _use_celery():
        return (True, None)
    if _allow_inprocess_fallback():
        return (True, None)
    return (False, "Análise indisponível no momento. Tente novamente em instantes.")


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
    *,
    sync: bool = False,
) -> tuple[ResumeAnalysis | None, str | None]:
    """
    Create a pending ResumeAnalysis and enqueue execution (Celery or thread).
    When ``sync=True``, runs ``run_analysis_worker_safe`` inline (tests / controlled batch).

    Returns (analysis, None) on success, (None, "not_found") if resume invalid,
    (None, "unavailable") if analysis service unavailable (prod, no Celery).
    """
    resume = get_resume_by_id_and_user(user_id, str(resume_id))
    if resume is None:
        return (None, "not_found")

    available, _ = is_analysis_available()
    if not available:
        return (None, "unavailable")

    analysis = ResumeAnalysis.objects.create(
        user_id=user_id,
        resume_id=str(resume_id),
        status=AnalysisStatus.PENDING,
        job_description_text=(job_description_text or "")[:JOB_DESCRIPTION_MAX_LENGTH] or None,
        resume_content_synced_at=resume.updated_at,
    )

    if sync:
        run_analysis_worker_safe(str(analysis.id))
        return (analysis, None)

    if _use_celery():
        try:
            run_resume_analysis_task.delay(str(analysis.id))
        except Exception as exc:
            if _allow_inprocess_fallback():
                logger.warning("Celery unavailable, falling back to thread: %s", exc)
                _start_inprocess_analysis(str(analysis.id))
            else:
                logger.error("Celery unavailable and in-process fallback: %s", exc)
                _mark_analysis_failed(analysis)
    else:
        if _allow_inprocess_fallback():
            _start_inprocess_analysis(str(analysis.id))
        else:
            _mark_analysis_failed(analysis)

    return (analysis, None)


def get_latest_analysis(user_id: str, resume_id: str) -> ResumeAnalysis | None:
    """Return the most recent analysis still valid for current resume content, or None."""
    resume = get_resume_by_id_and_user(user_id, str(resume_id))
    if resume is None:
        return None
    qs = (
        ResumeAnalysis.objects.filter(
            user_id=user_id,
            resume_id=resume_id,
        )
        .order_by("-created_at")[:25]
    )
    for analysis in qs:
        if is_analysis_valid_for_resume(resume, analysis):
            return analysis
    return None


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

    by_resume: dict[str, ResumeAnalysis] = {}
    for rid in owned_ids:
        latest = get_latest_analysis(user_id, str(rid))
        if latest is not None:
            by_resume[str(rid)] = latest
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
