"""
The PDF export state machine: request, queue, recover, publish.

Rendering lives in ``pdf_render.py`` and storage in ``pdf_storage.py``. Both are re-exported here
because ``pdf_views.py`` and ``tasks.py`` import these names from this module.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.resumes.infrastructure.models import Resume, ResumeExport, ResumeExportStatus, ResumeExportType

from .pdf_render import (
    PDF_RENDER_TIMEOUT_MS,
    _build_print_url,
    render_resume_pdf_from_preview,
)
from .pdf_storage import (
    PDF_EXPORT_FILENAME_PREFIX,
    PDF_EXPORT_ROOT,
    PDF_LAYOUT_VERSION,
    _export_absolute_path,
    _export_exists,
    _export_relative_path,
    _write_export_file,
    build_pdf_filename,
    build_pdf_fingerprint,
    read_export_file,
)

from .pdf_queue import (
    _allow_inprocess_fallback,
    _enqueue_export_task,
    _start_rescue_watchdog,
    _use_celery,
    maybe_recover_export,
)

logger = logging.getLogger(__name__)

PDF_DEFAULT_RETRY_AFTER_SECONDS = 2


def get_ready_export_by_id(user_id: str, resume_id: str, export_id: str) -> ResumeExport | None:
    export = ResumeExport.objects.filter(
        id=export_id,
        user_id=user_id,
        resume_id=resume_id,
        export_type=ResumeExportType.PDF,
    ).first()
    if not export:
        return None
    if export.status != ResumeExportStatus.READY or not _export_exists(export.storage_path):
        return None
    return export


def get_or_request_pdf_export(resume: Resume, user_id: str) -> tuple[str, ResumeExport, str, dict[str, Any]]:
    fingerprint = build_pdf_fingerprint(resume)
    telemetry: dict[str, Any] = {"cache_hit": False}
    to_enqueue = False

    with transaction.atomic():
        export = (
            ResumeExport.objects.select_for_update()
            .filter(
                resume_id=resume.id,
                user_id=user_id,
                export_type=ResumeExportType.PDF,
                fingerprint=fingerprint,
            )
            .first()
        )
        if export and export.status == ResumeExportStatus.READY and _export_exists(export.storage_path):
            telemetry["cache_hit"] = True
            return "ready", export, fingerprint, telemetry

        if not export:
            export = ResumeExport.objects.create(
                resume_id=resume.id,
                user_id=user_id,
                export_type=ResumeExportType.PDF,
                fingerprint=fingerprint,
                status=ResumeExportStatus.PENDING,
                storage_path=_export_relative_path(user_id, str(resume.id), fingerprint),
            )
            to_enqueue = True
        elif export.status in (ResumeExportStatus.FAILED, ResumeExportStatus.READY):
            export.status = ResumeExportStatus.PENDING
            export.error_message = ""
            export.started_at = None
            export.finished_at = None
            export.metrics_json = {}
            if not export.storage_path:
                export.storage_path = _export_relative_path(user_id, str(resume.id), fingerprint)
            export.save(
                update_fields=[
                    "status",
                    "error_message",
                    "started_at",
                    "finished_at",
                    "metrics_json",
                    "storage_path",
                    "updated_at",
                ]
            )
            to_enqueue = True
        elif export.status in (ResumeExportStatus.PENDING, ResumeExportStatus.RUNNING):
            stale_seconds = int(getattr(settings, "PDF_EXPORT_STALE_SECONDS", 90))
            checkpoint = export.started_at or export.updated_at
            if checkpoint and (timezone.now() - checkpoint).total_seconds() >= stale_seconds:
                export.status = ResumeExportStatus.PENDING
                export.started_at = None
                export.finished_at = None
                export.error_message = "Requeued after stale export state."
                export.save(
                    update_fields=[
                        "status",
                        "started_at",
                        "finished_at",
                        "error_message",
                        "updated_at",
                    ]
                )
                to_enqueue = True

    if to_enqueue:
        _enqueue_export_task(str(export.id))
    return "pending", export, fingerprint, telemetry


def build_pdf_status_payload(resume: Resume, export: ResumeExport, cache_hit: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "exportId": str(export.id),
        "fingerprint": export.fingerprint,
        "filename": build_pdf_filename(resume),
        "cacheHit": bool(cache_hit),
    }
    if export.status == ResumeExportStatus.READY and _export_exists(export.storage_path):
        payload["status"] = "ready"
        payload["downloadPath"] = f"/resumes/api/resumes/{resume.id}/pdf?export_id={export.id}"
        payload["metrics"] = export.metrics_json or {}
        return payload
    if export.status == ResumeExportStatus.FAILED:
        payload["status"] = "failed"
        payload["errorMessage"] = export.error_message or "Não foi possível gerar o PDF."
        return payload
    payload["status"] = "pending"
    payload["retryAfterSeconds"] = int(getattr(settings, "PDF_POLL_RETRY_AFTER_SECONDS", PDF_DEFAULT_RETRY_AFTER_SECONDS))
    return payload


def process_pdf_export(export_id: str) -> None:
    export = (
        ResumeExport.objects.select_related("resume")
        .filter(id=export_id, export_type=ResumeExportType.PDF)
        .first()
    )
    if not export:
        logger.warning("PDF export task: export not found", extra={"export_id": export_id})
        return

    if export.status == ResumeExportStatus.READY and _export_exists(export.storage_path):
        return

    started_at = timezone.now()
    ResumeExport.objects.filter(id=export.id).update(
        status=ResumeExportStatus.RUNNING,
        started_at=started_at,
        error_message="",
    )

    stage_metrics: dict[str, Any] = {}
    task_start = time.perf_counter()
    try:
        build_start = time.perf_counter()
        print_url = _build_print_url(str(export.resume_id), str(export.user_id))
        stage_metrics["build_print_url_ms"] = int((time.perf_counter() - build_start) * 1000)

        render_start = time.perf_counter()
        pdf_bytes, render_metrics = _render_resume_pdf_in_isolated_thread(print_url)
        stage_metrics["render_total_ms"] = int((time.perf_counter() - render_start) * 1000)
        stage_metrics.update(render_metrics)

        storage_start = time.perf_counter()
        file_size = _write_export_file(export.storage_path, pdf_bytes)
        stage_metrics["storage_write_ms"] = int((time.perf_counter() - storage_start) * 1000)
        stage_metrics["file_size_bytes"] = file_size
        stage_metrics["queue_wait_ms"] = int((started_at - export.created_at).total_seconds() * 1000)
        stage_metrics["task_total_ms"] = int((time.perf_counter() - task_start) * 1000)

        ResumeExport.objects.filter(id=export.id).update(
            status=ResumeExportStatus.READY,
            file_size_bytes=file_size,
            metrics_json=stage_metrics,
            finished_at=timezone.now(),
            error_message="",
        )
        logger.info(
            "Resume PDF export ready",
            extra={
                "resume_id": str(export.resume_id),
                "user_id": str(export.user_id),
                "export_id": str(export.id),
                "fingerprint": export.fingerprint,
                "metrics": stage_metrics,
            },
        )
        from apps.notifications.services import create_notification

        resume_name = (export.resume.name or export.resume.target_position or "Currículo")[:80]
        create_notification(
            user_id=str(export.user_id),
            type="pdf_ready",
            title_key="notifications.pdfReady",
            params={"name": resume_name},
            action_url=f"/protected/resumes?editResumeId={export.resume_id}",
            entity_ref={"resume_id": str(export.resume_id), "export_id": str(export.id)},
        )
    except Exception as exc:
        error_msg = str(exc)[:2000]
        stage_metrics["task_total_ms"] = int((time.perf_counter() - task_start) * 1000)
        ResumeExport.objects.filter(id=export.id).update(
            status=ResumeExportStatus.FAILED,
            error_message=error_msg,
            finished_at=timezone.now(),
            metrics_json=stage_metrics,
        )
        logger.exception(
            "Resume PDF export failed",
            extra={
                "resume_id": str(export.resume_id),
                "user_id": str(export.user_id),
                "export_id": str(export.id),
                "fingerprint": export.fingerprint,
            },
        )
        try:
            from apps.notifications.services import create_notification

            resume_name = (export.resume.name or export.resume.target_position or "Currículo")[:80]
            create_notification(
                user_id=str(export.user_id),
                type="pdf_failed",
                title_key="notifications.pdfFailed",
                params={"name": resume_name},
                action_url=f"/protected/resumes?editResumeId={export.resume_id}",
                entity_ref={"resume_id": str(export.resume_id), "export_id": str(export.id)},
            )
        except Exception:
            pass
        raise


def _render_resume_pdf_in_isolated_thread(url: str) -> tuple[bytes, dict[str, Any]]:
    result: dict[str, Any] = {}
    error: dict[str, Exception] = {}

    def _run() -> None:
        try:
            pdf_bytes, metrics = render_resume_pdf_from_preview(url)
            result["pdf_bytes"] = pdf_bytes
            result["metrics"] = metrics
        except Exception as exc:
            error["exc"] = exc

    thread = threading.Thread(target=_run, name="resume-pdf-render", daemon=True)
    thread.start()
    thread.join()
    if "exc" in error:
        raise error["exc"]
    return result["pdf_bytes"], result.get("metrics", {})
