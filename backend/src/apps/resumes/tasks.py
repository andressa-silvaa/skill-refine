from __future__ import annotations

from celery import shared_task
from django.db import connection

from apps.resumes.interfaces.api.pdf_exports import process_pdf_export


@shared_task(bind=True, name="apps.resumes.tasks.run_resume_pdf_export_task")
def run_resume_pdf_export_task(self, export_id: str) -> None:
    connection.close()
    process_pdf_export(export_id)
