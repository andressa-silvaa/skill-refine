from __future__ import annotations

from django.db import models

from shared.db.models import UUIDPrimaryKeyModel


class AuditLog(UUIDPrimaryKeyModel, models.Model):
    """
    audit_log — append-only audit events.
    """

    actor_user_id = models.UUIDField(null=True, blank=True)
    subject_user_id = models.UUIDField(null=True, blank=True)
    action = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["-created_at"], name="idx_audit_created"),
            models.Index(fields=["actor_user_id", "-created_at"], name="idx_audit_actor_created"),
            models.Index(fields=["subject_user_id", "-created_at"], name="idx_audit_subject_created"),
            models.Index(fields=["action", "-created_at"], name="idx_audit_action_created"),
        ]


