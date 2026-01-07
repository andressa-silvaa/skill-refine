from __future__ import annotations

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_password_reset_grant")]

    operations = [
        migrations.CreateModel(
            name="EmailConfirmationToken",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("email", models.TextField()),
                ("token_hash", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(null=True, blank=True)),
                ("ip", models.GenericIPAddressField(null=True, blank=True)),
                ("user_agent", models.TextField(null=True, blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        to="accounts.user",
                        on_delete=django.db.models.deletion.CASCADE,
                        db_column="user_id",
                    ),
                ),
            ],
            options={"db_table": "email_confirmation_tokens"},
        ),
        migrations.AddIndex(
            model_name="emailconfirmationtoken",
            index=models.Index(fields=["email", "-created_at"], name="idx_ect_email_created"),
        ),
        migrations.AddIndex(
            model_name="emailconfirmationtoken",
            index=models.Index(fields=["expires_at"], name="idx_ect_expires"),
        ),
        migrations.AddIndex(
            model_name="emailconfirmationtoken",
            index=models.Index(fields=["token_hash"], name="idx_ect_token_hash"),
        ),
    ]


