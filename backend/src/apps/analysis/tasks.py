"""
Analysis tasks: run inference in background.
Celery task; use run_resume_analysis_task.delay(analysis_id).
"""
from __future__ import annotations

from celery import shared_task
from django.db import connection

from apps.analysis.application.worker import run_analysis_worker_safe


@shared_task(bind=True, name="apps.analysis.tasks.run_resume_analysis_task")
def run_resume_analysis_task(self, analysis_id: str) -> None:
    """Celery task: close connection, delegate to worker."""
    connection.close()
    run_analysis_worker_safe(analysis_id)
