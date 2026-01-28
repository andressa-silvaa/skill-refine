from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("resumes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="resume",
            name="last_step",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
