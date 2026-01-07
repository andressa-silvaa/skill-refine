from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="passwordresetrequest",
            name="verified_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="passwordresetrequest",
            name="reset_token_hash",
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="passwordresetrequest",
            name="reset_token_expires_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]


