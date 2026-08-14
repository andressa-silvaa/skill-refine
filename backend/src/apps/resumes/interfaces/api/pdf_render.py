"""
Driving a headless browser to turn the print preview into PDF bytes.

Split out of ``pdf_exports.py`` because it is the only part that touches Playwright, holds the page
semaphore and cares about URLs. The state machine that decides *when* to render stays there.
"""
from __future__ import annotations

import logging
import os
import socket
import subprocess
import threading
import time
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote, urlparse

from django.conf import settings
from playwright.sync_api import Page

from .pdf_browser import create_pdf_page
from .services import create_pdf_token

logger = logging.getLogger(__name__)

PDF_RENDER_TIMEOUT_MS = 60000
_PDF_PAGE_SEMAPHORE = threading.BoundedSemaphore(
    value=max(1, int(getattr(settings, "PDF_MAX_CONCURRENT_PAGES", 2)))
)


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
