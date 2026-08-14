"""
Getting an export run: Celery when there is a broker, a thread when there is not, plus the watchdog
that rescues a job whose worker died between claim and finish.

Split out of ``pdf_exports.py`` so that module holds the state machine and this one holds the ways of
starting it. ``_render_resume_pdf_in_isolated_thread`` deliberately stays with the state machine: the
test suite patches ``pdf_exports.render_resume_pdf_from_preview``, and that seam only intercepts if
the caller resolves the name in that module's namespace.
"""
from __future__ import annotations

import logging
import threading
import time

from django.conf import settings
from django.utils import timezone

from apps.resumes.infrastructure.models import ResumeExport, ResumeExportStatus, ResumeExportType

logger = logging.getLogger(__name__)

_RESCUE_DELAY_SECONDS = 8


def _use_celery() -> bool:
    return bool(getattr(settings, "CELERY_BROKER_URL", "")) and getattr(settings, "CELERY_TASKS_ENABLED", True)


def _allow_inprocess_fallback() -> bool:
    return bool(getattr(settings, "ALLOW_INPROCESS_JOB_FALLBACK", False))


def _enqueue_export_task(export_id: str) -> None:
    if getattr(settings, "PDF_EXPORTS_EAGER", False):
        from .pdf_exports import process_pdf_export

        process_pdf_export(str(export_id))
        return
    from apps.resumes.tasks import run_resume_pdf_export_task

    if _use_celery():
        try:
            run_resume_pdf_export_task.delay(str(export_id))
            _start_rescue_watchdog(str(export_id))
            return
        except Exception:
            if not _allow_inprocess_fallback():
                ResumeExport.objects.filter(id=export_id).update(
                    status=ResumeExportStatus.FAILED,
                    error_message="Fila de exportação indisponível. Tente novamente em instantes.",
                    finished_at=timezone.now(),
                )
                return
            logger.warning("Celery unavailable for PDF export, falling back to thread.")
    elif not _allow_inprocess_fallback():
        ResumeExport.objects.filter(id=export_id).update(
            status=ResumeExportStatus.FAILED,
            error_message="Fila de exportação indisponível. Tente novamente em instantes.",
            finished_at=timezone.now(),
        )
        return
    thread = threading.Thread(
        target=run_resume_pdf_export_task,
        args=(str(export_id),),
        name=f"resume-pdf-export-{export_id}",
        daemon=True,
    )
    thread.start()


def _start_rescue_watchdog(export_id: str) -> None:
    delay_seconds = int(getattr(settings, "PDF_EXPORT_RESCUE_SECONDS", _RESCUE_DELAY_SECONDS))
    delay_seconds = max(2, delay_seconds)

    def _watch() -> None:
        try:
            time.sleep(delay_seconds)
            export = ResumeExport.objects.filter(id=export_id, export_type=ResumeExportType.PDF).first()
            if not export:
                return
            if export.status == ResumeExportStatus.PENDING:
                logger.warning(
                    "PDF export watchdog: pending too long, executing local fallback",
                    extra={"export_id": export_id},
                )
                from .pdf_exports import process_pdf_export

                process_pdf_export(export_id)
        except Exception:
            logger.exception("PDF export watchdog failed", extra={"export_id": export_id})

    threading.Thread(target=_watch, name=f"resume-pdf-watchdog-{export_id}", daemon=True).start()


def maybe_recover_export(export: ResumeExport) -> ResumeExport:
    stale_seconds = int(getattr(settings, "PDF_EXPORT_STALE_SECONDS", 90))
    rescue_seconds = int(getattr(settings, "PDF_EXPORT_RESCUE_SECONDS", _RESCUE_DELAY_SECONDS))
    checkpoint = export.started_at or export.created_at
    age_seconds = int((timezone.now() - checkpoint).total_seconds()) if checkpoint else 0

    if export.status == ResumeExportStatus.PENDING and age_seconds >= max(2, rescue_seconds):
        _enqueue_export_task(str(export.id))
        export.refresh_from_db()
        return export

    if export.status == ResumeExportStatus.RUNNING and age_seconds >= max(10, stale_seconds):
        ResumeExport.objects.filter(id=export.id).update(
            status=ResumeExportStatus.PENDING,
            started_at=None,
            finished_at=None,
            error_message="Requeued from stale running export.",
        )
        _enqueue_export_task(str(export.id))
        export.refresh_from_db()
    return export
