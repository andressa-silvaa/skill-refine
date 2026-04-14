# Generated manually for gold-standard seniority persistence.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analysis", "0003_resumeanalysis_resume_content_synced_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_rule_label",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_review_label",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_final_label",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_label_source",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_policy_version",
            field=models.CharField(blank=True, default="", max_length=24),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_confidence",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="resumeanalysis",
            name="seniority_evidence",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
