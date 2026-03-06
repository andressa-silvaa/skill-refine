"""
Analysis tasks: run inference in background.
Celery task; use celery_app.send_task or run_resume_analysis_task.delay(analysis_id).
"""
from __future__ import annotations

import logging
import time

from celery import shared_task
from django.db import connection
from django.utils import timezone

from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.safety import safe_error_message
from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.dashboard.interfaces.api.services import invalidate_dashboard_summary_cache
from apps.resumes.interfaces.api.payloads import resume_detail_payload

logger = logging.getLogger(__name__)


def _get_user_language(user_id: str) -> str:
    """Get user language from preferences. Fallback pt-BR."""
    try:
        from apps.accounts.infrastructure.models import UserPreferences

        prefs = UserPreferences.objects.filter(user_id=user_id).first()
        if prefs and getattr(prefs, "language", None):
            return str(prefs.language)
    except Exception:
        pass
    return "pt-BR"


@shared_task(bind=True, name="apps.analysis.tasks.run_resume_analysis_task")
def run_resume_analysis_task(self, analysis_id: str) -> None:
    """
    Celery task: load analysis + resume, run inference, persist result.
    Uses its own DB connection.
    """
    connection.close()
    start = time.monotonic()
    analysis = None

    try:
        analysis = (
            ResumeAnalysis.objects.select_related("resume", "user")
            .prefetch_related(
                "resume__resumecontact",
                "resume__resumeexperience_set__resumeexperiencebullet_set",
                "resume__resumeeducation_set",
                "resume__resumeskill_set",
                "resume__resumelanguage_set",
            )
            .get(id=analysis_id)
        )
    except ResumeAnalysis.DoesNotExist:
        logger.warning("Analysis task: record not found", extra={"analysis_id": analysis_id})
        return

    try:
        analysis.status = AnalysisStatus.RUNNING
        analysis.save(update_fields=["status", "updated_at"])
        queue_wait_ms = int((timezone.now() - analysis.created_at).total_seconds() * 1000)

        resume = analysis.resume
        resume_data = resume_detail_payload(resume)
        language = _get_user_language(str(analysis.user_id))
        job_text = (analysis.job_description_text or "").strip() or None

        result = analyze_resume(
            resume_data=resume_data,
            job_description_text=job_text,
            language=language,
        )

        analysis.score = result["score"]
        analysis.task_scores = result["task_scores"]
        analysis.payload_json = result["payload_json"]
        analysis.model_name = result.get("model_name", "")
        analysis.model_version = result.get("model_version", "")
        analysis.provider = result.get("provider", "local")
        analysis.status = AnalysisStatus.DONE
        analysis.save(
            update_fields=[
                "status",
                "score",
                "task_scores",
                "payload_json",
                "model_name",
                "model_version",
                "provider",
                "updated_at",
            ]
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "Analysis task completed",
            extra={
                "analysis_id": str(analysis.id),
                "resume_id": str(analysis.resume_id),
                "user_id": str(analysis.user_id),
                "model_version": analysis.model_version,
                "duration_ms": duration_ms,
                "queue_wait_ms": queue_wait_ms,
            },
        )
        invalidate_dashboard_summary_cache(str(analysis.user_id))
    except Exception as exc:
        logger.exception(
            "Analysis task failed",
            extra={"analysis_id": analysis_id, "error": safe_error_message(exc)},
        )
        try:
            ResumeAnalysis.objects.filter(id=analysis_id).update(
                status=AnalysisStatus.FAILED,
                error_message=safe_error_message(exc, max_len=2000),
            )
        except Exception:
            pass
        try:
            invalidate_dashboard_summary_cache(str(analysis.user_id))
        except Exception:
            pass
        raise
