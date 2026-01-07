from __future__ import annotations

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(null=True, blank=True)),
                ("email", models.TextField(unique=True)),
                ("email_verified_at", models.DateTimeField(null=True, blank=True)),
                ("full_name", models.TextField()),
                ("birth_date", models.DateField(null=True, blank=True)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=[("active", "active"), ("disabled", "disabled"), ("deleted", "deleted")],
                        default="active",
                    ),
                ),
            ],
            options={"db_table": "users"},
        ),
        migrations.CreateModel(
            name="AuthIdentity",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("provider", models.CharField(max_length=16, choices=[("password", "password"), ("google", "google")])),
                ("provider_user_id", models.TextField(null=True, blank=True)),
                ("provider_email", models.TextField(null=True, blank=True)),
                ("last_login_at", models.DateTimeField(null=True, blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        to="accounts.user",
                        on_delete=django.db.models.deletion.CASCADE,
                        db_column="user_id",
                    ),
                ),
            ],
            options={"db_table": "auth_identities"},
        ),
        migrations.CreateModel(
            name="PasswordResetRequest",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("email", models.TextField()),
                ("code_hash", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(null=True, blank=True)),
                ("attempts", models.IntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(null=True, blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        to="accounts.user",
                        on_delete=django.db.models.deletion.CASCADE,
                        db_column="user_id",
                    ),
                ),
            ],
            options={"db_table": "password_reset_requests"},
        ),
        migrations.CreateModel(
            name="Session",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("refresh_token_hash", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(null=True, blank=True)),
                ("ip", models.GenericIPAddressField(null=True, blank=True)),
                ("user_agent", models.TextField(null=True, blank=True)),
                ("replaced_by_session_id", models.UUIDField(null=True, blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        to="accounts.user",
                        on_delete=django.db.models.deletion.CASCADE,
                        db_column="user_id",
                    ),
                ),
            ],
            options={"db_table": "sessions"},
        ),
        migrations.CreateModel(
            name="UserPassword",
            fields=[
                (
                    "user",
                    models.OneToOneField(
                        to="accounts.user",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        db_column="user_id",
                        related_name="password_record",
                    ),
                ),
                ("password_hash", models.TextField()),
                ("password_updated_at", models.DateTimeField()),
                ("must_change_password", models.BooleanField(default=False)),
            ],
            options={"db_table": "user_passwords"},
        ),
        migrations.AddIndex(
            model_name="session",
            index=models.Index(fields=["user"], name="idx_sessions_user"),
        ),
        migrations.AddIndex(
            model_name="session",
            index=models.Index(fields=["expires_at"], name="idx_sessions_expires"),
        ),
        migrations.AddIndex(
            model_name="passwordresetrequest",
            index=models.Index(fields=["user", "-created_at"], name="idx_prr_user_created"),
        ),
        migrations.AddIndex(
            model_name="passwordresetrequest",
            index=models.Index(fields=["expires_at"], name="idx_prr_expires"),
        ),
        migrations.AddConstraint(
            model_name="authidentity",
            constraint=models.UniqueConstraint(
                fields=("provider", "provider_user_id"),
                name="uniq_auth_provider_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="authidentity",
            constraint=models.UniqueConstraint(
                fields=("user", "provider"),
                name="uniq_auth_user_provider",
            ),
        ),
    ]


