# Generated manually for dataset_version field

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="resumeanalysis",
            name="dataset_version",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
