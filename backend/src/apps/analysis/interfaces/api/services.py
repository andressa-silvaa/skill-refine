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

from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.analysis.tasks import run_resume_analysis_task
from apps.resumes.interfaces.api.services import get_resume_by_id_and_user

logger = logging.getLogger(__name__)

JOB_DESCRIPTION_MAX_LENGTH = 10_000


def _use_celery() -> bool:
    """True if Celery broker is configured and we should use it."""
    return bool(getattr(settings, "CELERY_BROKER_URL", "")) and getattr(
        settings, "CELERY_TASKS_ENABLED", True
    )


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
            logger.warning("Celery unavailable, falling back to thread: %s", exc)
            threading.Thread(
                target=run_resume_analysis_task,
                args=(str(analysis.id),),
                name=f"analysis-{analysis.id}",
                daemon=True,
            ).start()
    else:
        threading.Thread(
            target=run_resume_analysis_task,
            args=(str(analysis.id),),
            name=f"analysis-{analysis.id}",
            daemon=True,
        ).start()

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
