from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0002_add_dataset_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="resumeanalysis",
            name="resume_content_synced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
