from __future__ import annotations

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_user_avatar_and_preferences")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.TextField(),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=["email"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_users_email_active",
            ),
        ),
    ]
