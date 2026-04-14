# Generated manually for AI seniority / target-fit embedding persistence.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0004_resumeanalysis_seniority_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_text_label",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_text_confidence",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="target_fit_embedding_score",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="target_fit_signals_score",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="target_fit_final_score",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
