import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0005_soft_delete_email_uniqueness"),
    ]

    operations = [
        migrations.CreateModel(
            name="Resume",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(blank=True, default="", max_length=160)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "draft"),
                            ("complete", "complete"),
                            ("analyzing", "analyzing"),
                            ("published", "published"),
                            ("archived", "archived"),
                        ],
                        default="draft",
                        max_length=24,
                    ),
                ),
                (
                    "target_position",
                    models.CharField(blank=True, default="", max_length=160),
                ),
                ("summary", models.TextField(blank=True, default="")),
                (
                    "theme_id",
                    models.CharField(default="classic-one-column", max_length=64),
                ),
                (
                    "theme_palette_id",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                (
                    "theme_accent_override",
                    models.CharField(blank=True, max_length=16, null=True),
                ),
                (
                    "theme_secondary_override",
                    models.CharField(blank=True, max_length=16, null=True),
                ),
                ("score", models.IntegerField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        db_column="user_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "resumes",
            },
        ),
        migrations.CreateModel(
            name="ResumeContact",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "resume",
                    models.OneToOneField(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to="resumes.resume",
                    ),
                ),
                ("full_name", models.CharField(blank=True, default="", max_length=160)),
                ("email", models.CharField(blank=True, default="", max_length=254)),
                ("phone", models.CharField(blank=True, default="", max_length=32)),
                ("city", models.CharField(blank=True, default="", max_length=120)),
                ("country", models.CharField(blank=True, default="", max_length=120)),
                ("linkedin", models.CharField(blank=True, max_length=255, null=True)),
                ("portfolio", models.CharField(blank=True, max_length=255, null=True)),
                ("github", models.CharField(blank=True, max_length=255, null=True)),
                ("website", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "db_table": "resume_contacts",
            },
        ),
        migrations.CreateModel(
            name="ResumeEducation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "institution",
                    models.CharField(blank=True, default="", max_length=180),
                ),
                ("course", models.CharField(blank=True, default="", max_length=180)),
                ("degree", models.CharField(blank=True, default="", max_length=120)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("completed", "completed"),
                            ("in_progress", "in_progress"),
                        ],
                        default="completed",
                        max_length=24,
                    ),
                ),
                ("position_index", models.IntegerField(default=0)),
                (
                    "resume",
                    models.ForeignKey(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resumes.resume",
                    ),
                ),
            ],
            options={
                "db_table": "resume_educations",
            },
        ),
        migrations.CreateModel(
            name="ResumeExperience",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.CharField(blank=True, default="", max_length=180)),
                ("position", models.CharField(blank=True, default="", max_length=160)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_current", models.BooleanField(default=False)),
                ("position_index", models.IntegerField(default=0)),
                (
                    "resume",
                    models.ForeignKey(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resumes.resume",
                    ),
                ),
            ],
            options={
                "db_table": "resume_experiences",
            },
        ),
        migrations.CreateModel(
            name="ResumeExperienceBullet",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("content", models.TextField(blank=True, default="")),
                ("position_index", models.IntegerField(default=0)),
                (
                    "experience",
                    models.ForeignKey(
                        db_column="experience_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resumes.resumeexperience",
                    ),
                ),
            ],
            options={
                "db_table": "resume_experience_bullets",
            },
        ),
        migrations.CreateModel(
            name="ResumeLanguage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(blank=True, default="", max_length=80)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("basic", "basic"),
                            ("intermediate", "intermediate"),
                            ("advanced", "advanced"),
                            ("fluent", "fluent"),
                            ("native", "native"),
                        ],
                        default="intermediate",
                        max_length=24,
                    ),
                ),
                ("position_index", models.IntegerField(default=0)),
                (
                    "resume",
                    models.ForeignKey(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resumes.resume",
                    ),
                ),
            ],
            options={
                "db_table": "resume_languages",
            },
        ),
        migrations.CreateModel(
            name="ResumeSectionOrder",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("section_key", models.CharField(max_length=32)),
                ("position_index", models.IntegerField(default=0)),
                ("is_visible", models.BooleanField(default=True)),
                (
                    "resume",
                    models.ForeignKey(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resumes.resume",
                    ),
                ),
            ],
            options={
                "db_table": "resume_section_orders",
            },
        ),
        migrations.CreateModel(
            name="ResumeSkill",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(blank=True, default="", max_length=120)),
                (
                    "level",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("beginner", "beginner"),
                            ("intermediate", "intermediate"),
                            ("advanced", "advanced"),
                            ("expert", "expert"),
                        ],
                        max_length=24,
                        null=True,
                    ),
                ),
                ("position_index", models.IntegerField(default=0)),
                (
                    "resume",
                    models.ForeignKey(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resumes.resume",
                    ),
                ),
            ],
            options={
                "db_table": "resume_skills",
            },
        ),
        migrations.CreateModel(
            name="ResumeTag",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("label", models.CharField(blank=True, default="", max_length=80)),
                ("position_index", models.IntegerField(default=0)),
                (
                    "resume",
                    models.ForeignKey(
                        db_column="resume_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="resumes.resume",
                    ),
                ),
            ],
            options={
                "db_table": "resume_tags",
            },
        ),
        migrations.AddIndex(
            model_name="resume",
            index=models.Index(fields=["user"], name="idx_resumes_user"),
        ),
        migrations.AddIndex(
            model_name="resume",
            index=models.Index(
                fields=["user", "status"], name="idx_resumes_user_status"
            ),
        ),
        migrations.AddIndex(
            model_name="resume",
            index=models.Index(fields=["updated_at"], name="idx_resumes_updated_at"),
        ),
        migrations.AddIndex(
            model_name="resumeeducation",
            index=models.Index(
                fields=["resume", "position_index"], name="idx_resume_edu_order"
            ),
        ),
        migrations.AddIndex(
            model_name="resumeexperience",
            index=models.Index(
                fields=["resume", "position_index"], name="idx_resume_exp_order"
            ),
        ),
        migrations.AddIndex(
            model_name="resumeexperiencebullet",
            index=models.Index(
                fields=["experience", "position_index"], name="idx_resume_exp_bullet"
            ),
        ),
        migrations.AddIndex(
            model_name="resumelanguage",
            index=models.Index(
                fields=["resume", "position_index"], name="idx_resume_lang_order"
            ),
        ),
        migrations.AddIndex(
            model_name="resumesectionorder",
            index=models.Index(
                fields=["resume", "position_index"], name="idx_resume_section_order"
            ),
        ),
        migrations.AddConstraint(
            model_name="resumesectionorder",
            constraint=models.UniqueConstraint(
                fields=("resume", "section_key"), name="uniq_resume_section_key"
            ),
        ),
        migrations.AddIndex(
            model_name="resumeskill",
            index=models.Index(
                fields=["resume", "position_index"], name="idx_resume_skill_order"
            ),
        ),
        migrations.AddIndex(
            model_name="resumetag",
            index=models.Index(
                fields=["resume", "position_index"], name="idx_resume_tag_order"
            ),
        ),
    ]
