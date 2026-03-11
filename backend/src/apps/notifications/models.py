"""
Notification model: user notifications for analysis_done, pdf_ready, version_restored, etc.
Uses title_key + params for i18n; frontend translates.
"""
from __future__ import annotations

from django.db import models

from shared.db.models import TimestampedModel, UUIDPrimaryKeyModel


class NotificationType(models.TextChoices):
    ANALYSIS_DONE = "analysis_done", "analysis_done"
    ANALYSIS_FAILED = "analysis_failed", "analysis_failed"
    PDF_READY = "pdf_ready", "pdf_ready"
    PDF_FAILED = "pdf_failed", "pdf_failed"
    VERSION_RESTORED = "version_restored", "version_restored"
    SYSTEM = "system", "system"


class Notification(UUIDPrimaryKeyModel, TimestampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="notifications",
    )
    type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        db_index=True,
    )
    title_key = models.CharField(max_length=120, default="", blank=True)
    params = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    action_url = models.CharField(max_length=500, default="", blank=True)
    entity_ref = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_notif_user_created"),
            models.Index(fields=["user", "is_read"], name="idx_notif_user_read"),
        ]
        ordering = ["-created_at"]
