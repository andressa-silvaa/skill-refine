# Generated manually — remove unused visual region field (never exposed in API).

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_soft_delete_email_uniqueness"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userpreferences",
            name="region",
        ),
    ]
