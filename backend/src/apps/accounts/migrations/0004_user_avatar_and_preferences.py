from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_email_confirmation_tokens")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar_storage_key",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="UserPreferences",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="preferences",
                        serialize=False,
                        to="accounts.user",
                    ),
                ),
                ("language", models.CharField(default="pt-BR", max_length=16)),
                ("theme", models.CharField(choices=[("light", "light"), ("dark", "dark")], default="light", max_length=16)),
                ("accent_color", models.CharField(default="pink", max_length=16)),
                ("email_notifications_enabled", models.BooleanField(default=True)),
                ("region", models.CharField(blank=True, max_length=16, null=True)),
            ],
            options={"db_table": "user_preferences"},
        ),
    ]

