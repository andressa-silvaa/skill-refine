from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from playwright.sync_api import Page

from apps.resumes.infrastructure.models import Resume, ResumeExport, ResumeExportStatus, ResumeExportType

from .pdf_browser import create_pdf_page
from .services import create_pdf_token

logger = logging.getLogger(__name__)

PDF_RENDER_TIMEOUT_MS = 60000
PDF_LAYOUT_VERSION = "resume-print-v1"
PDF_DEFAULT_RETRY_AFTER_SECONDS = 2
PDF_EXPORT_FILENAME_PREFIX = "Curriculo"
PDF_EXPORT_ROOT = "resume_exports"
_PDF_PAGE_SEMAPHORE = threading.BoundedSemaphore(
    value=max(1, int(getattr(settings, "PDF_MAX_CONCURRENT_PAGES", 2)))
)
_RESCUE_DELAY_SECONDS = 8


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value).strip("_")
    return cleaned or PDF_EXPORT_FILENAME_PREFIX


def _export_relative_path(user_id: str, resume_id: str, fingerprint: str) -> str:
    return f"{PDF_EXPORT_ROOT}/{user_id}/{resume_id}/{fingerprint}.pdf"


def _export_absolute_path(storage_path: str) -> Path:
    media_root = Path(getattr(settings, "MEDIA_ROOT", ".")).resolve()
    absolute = (media_root / storage_path).resolve()
    if os.path.commonpath([str(media_root), str(absolute)]) != str(media_root):
        raise ValueError("Invalid export path.")
    return absolute


def _export_exists(storage_path: str) -> bool:
    if not storage_path:
        return False
    try:
        return _export_absolute_path(storage_path).exists()
    except Exception:
        return False


def _write_export_file(storage_path: str, content: bytes) -> int:
    target = _export_absolute_path(storage_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return len(content)


def read_export_file(storage_path: str) -> bytes:
    return _export_absolute_path(storage_path).read_bytes()


def build_pdf_fingerprint(resume: Resume) -> str:
    payload = {
        "resumeId": str(resume.id),
        "updatedAt": resume.updated_at.isoformat(),
        "themeId": resume.theme_id or "",
        "paletteId": resume.theme_palette_id or "",
        "accentOverride": resume.theme_accent_override or "",
        "secondaryOverride": resume.theme_secondary_override or "",
        "layoutVersion": PDF_LAYOUT_VERSION,
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_pdf_filename(resume: Resume) -> str:
    safe_name = _safe_filename(resume.name or resume.target_position or PDF_EXPORT_FILENAME_PREFIX)
    return f"{PDF_EXPORT_FILENAME_PREFIX}_{safe_name}_{date.today().isoformat()}.pdf"


def _build_print_url(resume_id: str, user_id: str) -> str:
    token = create_pdf_token(str(resume_id), str(user_id))
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    is_docker = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")

    if is_docker and (
        frontend_url.startswith("http://localhost") or frontend_url.startswith("http://127.0.0.1")
    ):
        try:
            socket.create_connection(("host.docker.internal", 3000), timeout=2).close()
            frontend_url = frontend_url.replace("localhost", "host.docker.internal").replace(
                "127.0.0.1", "host.docker.internal"
            )
        except (socket.error, socket.timeout):
            try:
                gateway_ip = socket.gethostbyname("host.docker.internal")
                frontend_url = frontend_url.replace("localhost", gateway_ip).replace("127.0.0.1", gateway_ip)
            except socket.gaierror:
                try:
                    result = subprocess.run(
                        ["ip", "route", "show", "default"], capture_output=True, text=True, timeout=2
                    )
                    if result.returncode == 0:
                        gateway = result.stdout.split()[2]
                        frontend_url = frontend_url.replace("localhost", gateway).replace("127.0.0.1", gateway)
                except Exception:
                    pass

    backend_url = _resolve_backend_url(frontend_url)
    return frontend_url + f"/resume/print/{resume_id}?token={quote(token)}&apiUrl={quote(backend_url)}"


def _resolve_backend_url(frontend_url: str) -> str:
    configured = (getattr(settings, "BACKEND_URL", "") or "").strip()
    if configured:
        return configured.rstrip("/")

    parsed = urlparse(frontend_url)
    if parsed.scheme and parsed.hostname:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return "http://localhost:8000"


@contextmanager
def _page_slot():
    _PDF_PAGE_SEMAPHORE.acquire()
    try:
        yield
    finally:
        _PDF_PAGE_SEMAPHORE.release()


def render_resume_pdf_from_preview(url: str) -> tuple[bytes, dict[str, Any]]:
    page: Page | None = None
    console_messages: list[str] = []
    metrics: dict[str, Any] = {}
    start_all = time.perf_counter()

    with _page_slot():
        try:
            t0 = time.perf_counter()
            page = create_pdf_page(viewport={"width": 1280, "height": 720})
            metrics["page_create_ms"] = int((time.perf_counter() - t0) * 1000)

            def handle_console(msg):
                console_messages.append(f"{msg.type}: {msg.text}")

            page.on("console", handle_console)

            t0 = time.perf_counter()
            page.goto(url, wait_until="domcontentloaded", timeout=PDF_RENDER_TIMEOUT_MS)
            metrics["navigation_ms"] = int((time.perf_counter() - t0) * 1000)

            page.emulate_media(media="screen")
            t0 = time.perf_counter()
            try:
                page.wait_for_function(
                    "document.fonts && document.fonts.status === 'loaded'",
                    timeout=10_000,
                )
            except Exception:
                pass
            metrics["font_wait_ms"] = int((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            try:
                page.wait_for_function("window.__resumePdfReady === true", timeout=PDF_RENDER_TIMEOUT_MS)
            except Exception as exc:
                frontend_error = page.evaluate("window.__resumePdfError || null")
                page_state = page.evaluate(
                    """() => ({
                        ready: window.__resumePdfReady,
                        error: window.__resumePdfError,
                        metrics: window.__resumePdfMetrics || null,
                        hasData: document.querySelector('.sr-resume-print') !== null,
                        hasError: document.querySelector('.sr-resume-print__error') !== null,
                        hasLoading: document.querySelector('.sr-resume-print__loading') !== null,
                    })"""
                )
                recent_logs = "\n".join(console_messages[-10:])
                if frontend_error:
                    raise RuntimeError(f"Frontend error: {frontend_error}. Console: {recent_logs}") from exc
                raise RuntimeError(f"PDF render timeout. State: {page_state}. Console: {recent_logs}") from exc
            metrics["preview_ready_wait_ms"] = int((time.perf_counter() - t0) * 1000)

            frontend_error = page.evaluate("window.__resumePdfError || null")
            if frontend_error:
                recent_logs = "\n".join(console_messages[-10:])
                raise RuntimeError(f"Frontend error: {frontend_error}. Console: {recent_logs}")

            frontend_metrics = page.evaluate("window.__resumePdfMetrics || null")
            if isinstance(frontend_metrics, dict):
                metrics["frontend_metrics"] = frontend_metrics

            t0 = time.perf_counter()
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            metrics["pdf_render_ms"] = int((time.perf_counter() - t0) * 1000)
            return pdf_bytes, metrics
        finally:
            metrics["playwright_total_ms"] = int((time.perf_counter() - start_all) * 1000)
            if page:
                try:
                    page.close()
                except Exception:
                    pass


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


def _use_celery() -> bool:
    return bool(getattr(settings, "CELERY_BROKER_URL", "")) and getattr(settings, "CELERY_TASKS_ENABLED", True)


def _allow_inprocess_fallback() -> bool:
    return bool(getattr(settings, "ALLOW_INPROCESS_JOB_FALLBACK", False))


def _enqueue_export_task(export_id: str) -> None:
    if getattr(settings, "PDF_EXPORTS_EAGER", False):
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
        raise
