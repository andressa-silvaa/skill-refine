import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0005_soft_delete_email_uniqueness"),
        ("resumes", "0002_resume_last_step"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResumeAnalysis",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "pending"),
                            ("running", "running"),
                            ("done", "done"),
                            ("failed", "failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("score", models.IntegerField(blank=True, null=True)),
                ("task_scores", models.JSONField(blank=True, null=True)),
                ("payload_json", models.JSONField(blank=True, null=True)),
                ("model_name", models.CharField(blank=True, default="", max_length=80)),
                ("model_version", models.CharField(blank=True, default="", max_length=40)),
                ("provider", models.CharField(blank=True, default="local", max_length=16)),
                ("job_description_text", models.TextField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, null=True)),
                (
                    "resume",
                    models.ForeignKey(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resume_analyses",
                        to="resumes.resume",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "resume_analyses",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="resumeanalysis",
            index=models.Index(
                fields=["user", "resume", "-created_at"],
                name="idx_ra_user_resume_created",
            ),
        ),
        migrations.AddIndex(
            model_name="resumeanalysis",
            index=models.Index(
                fields=["resume", "-created_at"],
                name="idx_ra_resume_created",
            ),
        ),
        migrations.AddIndex(
            model_name="resumeanalysis",
            index=models.Index(fields=["status"], name="idx_ra_status"),
        ),
    ]
