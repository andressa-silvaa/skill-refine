from __future__ import annotations

from django.db import models

from shared.db.models import SoftDeleteModel, TimestampedModel, UUIDPrimaryKeyModel
from apps.accounts.infrastructure.models import User


class ResumeStatus(models.TextChoices):
    DRAFT = "draft", "draft"
    COMPLETE = "complete", "complete"
    ANALYZING = "analyzing", "analyzing"
    PUBLISHED = "published", "published"
    ARCHIVED = "archived", "archived"


class EducationStatus(models.TextChoices):
    COMPLETED = "completed", "completed"
    IN_PROGRESS = "in_progress", "in_progress"


class SkillLevel(models.TextChoices):
    BEGINNER = "beginner", "beginner"
    INTERMEDIATE = "intermediate", "intermediate"
    ADVANCED = "advanced", "advanced"
    EXPERT = "expert", "expert"


class LanguageLevel(models.TextChoices):
    BASIC = "basic", "basic"
    INTERMEDIATE = "intermediate", "intermediate"
    ADVANCED = "advanced", "advanced"
    FLUENT = "fluent", "fluent"
    NATIVE = "native", "native"


class Resume(UUIDPrimaryKeyModel, TimestampedModel, SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    name = models.CharField(max_length=160, default="", blank=True)
    status = models.CharField(max_length=24, choices=ResumeStatus.choices, default=ResumeStatus.DRAFT)
    last_step = models.CharField(max_length=32, null=True, blank=True)
    target_position = models.CharField(max_length=160, default="", blank=True)
    summary = models.TextField(default="", blank=True)
    theme_id = models.CharField(max_length=64, default="classic-one-column")
    theme_palette_id = models.CharField(max_length=64, null=True, blank=True)
    theme_accent_override = models.CharField(max_length=16, null=True, blank=True)
    theme_secondary_override = models.CharField(max_length=16, null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "resumes"
        indexes = [
            models.Index(fields=["user"], name="idx_resumes_user"),
            models.Index(fields=["user", "status"], name="idx_resumes_user_status"),
            models.Index(fields=["updated_at"], name="idx_resumes_updated_at"),
        ]


class ResumeContact(TimestampedModel):
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, primary_key=True, db_column="resume_id")
    full_name = models.CharField(max_length=160, default="", blank=True)
    email = models.CharField(max_length=254, default="", blank=True)
    phone = models.CharField(max_length=32, default="", blank=True)
    city = models.CharField(max_length=120, default="", blank=True)
    country = models.CharField(max_length=120, default="", blank=True)
    linkedin = models.CharField(max_length=255, null=True, blank=True)
    portfolio = models.CharField(max_length=255, null=True, blank=True)
    github = models.CharField(max_length=255, null=True, blank=True)
    website = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "resume_contacts"


class ResumeExperience(UUIDPrimaryKeyModel, TimestampedModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, db_column="resume_id")
    company = models.CharField(max_length=180, default="", blank=True)
    position = models.CharField(max_length=160, default="", blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    position_index = models.IntegerField(default=0)

    class Meta:
        db_table = "resume_experiences"
        indexes = [
            models.Index(fields=["resume", "position_index"], name="idx_resume_exp_order"),
        ]


class ResumeExperienceBullet(UUIDPrimaryKeyModel):
    experience = models.ForeignKey(ResumeExperience, on_delete=models.CASCADE, db_column="experience_id")
    content = models.TextField(default="", blank=True)
    position_index = models.IntegerField(default=0)

    class Meta:
        db_table = "resume_experience_bullets"
        indexes = [
            models.Index(fields=["experience", "position_index"], name="idx_resume_exp_bullet"),
        ]


class ResumeEducation(UUIDPrimaryKeyModel, TimestampedModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, db_column="resume_id")
    institution = models.CharField(max_length=180, default="", blank=True)
    course = models.CharField(max_length=180, default="", blank=True)
    degree = models.CharField(max_length=120, default="", blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=EducationStatus.choices, default=EducationStatus.COMPLETED)
    position_index = models.IntegerField(default=0)

    class Meta:
        db_table = "resume_educations"
        indexes = [
            models.Index(fields=["resume", "position_index"], name="idx_resume_edu_order"),
        ]


class ResumeSkill(UUIDPrimaryKeyModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, db_column="resume_id")
    name = models.CharField(max_length=120, default="", blank=True)
    level = models.CharField(max_length=24, choices=SkillLevel.choices, null=True, blank=True)
    position_index = models.IntegerField(default=0)

    class Meta:
        db_table = "resume_skills"
        indexes = [
            models.Index(fields=["resume", "position_index"], name="idx_resume_skill_order"),
        ]


class ResumeLanguage(UUIDPrimaryKeyModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, db_column="resume_id")
    name = models.CharField(max_length=80, default="", blank=True)
    level = models.CharField(max_length=24, choices=LanguageLevel.choices, default=LanguageLevel.INTERMEDIATE)
    position_index = models.IntegerField(default=0)

    class Meta:
        db_table = "resume_languages"
        indexes = [
            models.Index(fields=["resume", "position_index"], name="idx_resume_lang_order"),
        ]


class ResumeTag(UUIDPrimaryKeyModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, db_column="resume_id")
    label = models.CharField(max_length=80, default="", blank=True)
    position_index = models.IntegerField(default=0)

    class Meta:
        db_table = "resume_tags"
        indexes = [
            models.Index(fields=["resume", "position_index"], name="idx_resume_tag_order"),
        ]


class ResumeSectionOrder(UUIDPrimaryKeyModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, db_column="resume_id")
    section_key = models.CharField(max_length=32)
    position_index = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "resume_section_orders"
        constraints = [
            models.UniqueConstraint(fields=["resume", "section_key"], name="uniq_resume_section_key"),
        ]
        indexes = [
            models.Index(fields=["resume", "position_index"], name="idx_resume_section_order"),
        ]


class ResumeVersion(UUIDPrimaryKeyModel, TimestampedModel):
    """
    Snapshot of a resume at a point in time. Used for history and restore.
    Each resume has one current version (is_current=True); older versions are kept for audit.
    """
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, db_column="resume_id")
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    version_number = models.PositiveIntegerField()
    is_current = models.BooleanField(default=False)
    snapshot_json = models.JSONField(default=dict)
    change_summary_json = models.JSONField(default=list)
    score = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "resume_versions"
        indexes = [
            models.Index(fields=["resume", "-version_number"], name="idx_resume_versions_resume"),
            models.Index(fields=["user", "-created_at"], name="idx_resume_versions_user"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["resume", "version_number"],
                name="uniq_resume_version_number",
            ),
        ]
