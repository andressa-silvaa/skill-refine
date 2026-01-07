from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("actor_user_id", models.UUIDField(null=True, blank=True)),
                ("subject_user_id", models.UUIDField(null=True, blank=True)),
                ("action", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ip", models.GenericIPAddressField(null=True, blank=True)),
                ("user_agent", models.TextField(null=True, blank=True)),
                ("metadata", models.JSONField(default=dict)),
            ],
            options={"db_table": "audit_log"},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["-created_at"], name="idx_audit_created"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["actor_user_id", "-created_at"], name="idx_audit_actor_created"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["subject_user_id", "-created_at"], name="idx_audit_subject_created"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "-created_at"], name="idx_audit_action_created"),
        ),
    ]


