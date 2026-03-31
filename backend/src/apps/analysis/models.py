"""
ResumeAnalysis: one run of AI analysis for a user's resume.
Stores status, scores, insights, and metadata. Used by POST /analysis/run, GET /analysis/latest, GET /analysis/history.
"""
from __future__ import annotations

from django.db import models

from shared.db.models import TimestampedModel, UUIDPrimaryKeyModel


class AnalysisStatus(models.TextChoices):
    PENDING = "pending", "pending"
    RUNNING = "running", "running"
    DONE = "done", "done"
    FAILED = "failed", "failed"


class ResumeAnalysis(UUIDPrimaryKeyModel, TimestampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="+",
    )
    resume = models.ForeignKey(
        "resumes.Resume",
        on_delete=models.CASCADE,
        db_column="resume_id",
        related_name="resume_analyses",
    )
    status = models.CharField(
        max_length=16,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
        db_index=True,
    )
    score = models.IntegerField(null=True, blank=True)  # 0-100
    task_scores = models.JSONField(null=True, blank=True)  # e.g. {"ats": 92, "clarity": 78, "seniority": 0}
    payload_json = models.JSONField(null=True, blank=True)  # structured insights
    model_name = models.CharField(max_length=80, default="", blank=True)
    model_version = models.CharField(max_length=40, default="", blank=True)
    dataset_version = models.CharField(max_length=64, default="", blank=True)
    provider = models.CharField(max_length=16, default="local", blank=True)
    job_description_text = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "resume_analyses"
        indexes = [
            models.Index(fields=["user", "resume", "-created_at"], name="idx_ra_user_resume_created"),
            models.Index(fields=["resume", "-created_at"], name="idx_ra_resume_created"),
            models.Index(fields=["status"], name="idx_ra_status"),
        ]
        ordering = ["-created_at"]
