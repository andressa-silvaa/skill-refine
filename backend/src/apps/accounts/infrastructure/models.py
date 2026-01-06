from __future__ import annotations

from django.db import models

from shared.db.models import CreatedAtModel, SoftDeleteModel, TimestampedModel, UUIDPrimaryKeyModel
from shared.utils.normalization import normalize_email


class UserStatus(models.TextChoices):
    ACTIVE = "active", "active"
    DISABLED = "disabled", "disabled"
    DELETED = "deleted", "deleted"


class AuthProvider(models.TextChoices):
    PASSWORD = "password", "password"
    GOOGLE = "google", "google"


class UserQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=UserStatus.ACTIVE, deleted_at__isnull=True)


class UserManager(models.Manager):
    def active(self):
        return self.get_queryset().active()

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def create(self, **kwargs):
        if "email" in kwargs:
            kwargs["email"] = normalize_email(kwargs.get("email"))
        return super().create(**kwargs)


class User(UUIDPrimaryKeyModel, TimestampedModel, SoftDeleteModel):
    """
    users (identity) — schema source of truth: Django migrations.

    Note: We intentionally do NOT use Django's built-in auth user model yet because
    the required schema stores password hashes in a separate table (`user_passwords`).
    """

    email = models.TextField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    full_name = models.TextField()
    birth_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=UserStatus.choices, default=UserStatus.ACTIVE)

    objects = UserManager()

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email) or ""
        super().save(*args, **kwargs)

    @property
    def is_authenticated(self) -> bool:
        """
        Compatibility with DRF permissions (we don't use django.contrib.auth).
        """

        return True

    @property
    def is_anonymous(self) -> bool:
        return False


class UserPassword(models.Model):
    """
    user_passwords (separate password storage).
    PK = FK to users.id (OneToOne).
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="user_id",
        related_name="password_record",
    )
    password_hash = models.TextField()
    password_updated_at = models.DateTimeField()
    must_change_password = models.BooleanField(default=False)

    class Meta:
        db_table = "user_passwords"


class AuthIdentity(UUIDPrimaryKeyModel, CreatedAtModel):
    """
    auth_identities (password + social).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    provider = models.CharField(max_length=16, choices=AuthProvider.choices)
    provider_user_id = models.TextField(null=True, blank=True)
    provider_email = models.TextField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_identities"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"],
                name="uniq_auth_provider_user",
            ),
            models.UniqueConstraint(
                fields=["user", "provider"],
                name="uniq_auth_user_provider",
            ),
        ]

    def save(self, *args, **kwargs):
        self.provider_email = normalize_email(self.provider_email)
        super().save(*args, **kwargs)


class Session(UUIDPrimaryKeyModel, models.Model):
    """
    sessions (refresh token sessions).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    refresh_token_hash = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    replaced_by_session_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "sessions"
        indexes = [
            models.Index(fields=["user"], name="idx_sessions_user"),
            models.Index(fields=["expires_at"], name="idx_sessions_expires"),
        ]


class PasswordResetRequest(UUIDPrimaryKeyModel, models.Model):
    """
    password_reset_requests (email/code recovery flow).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    email = models.TextField()
    code_hash = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    reset_token_hash = models.TextField(null=True, blank=True)
    reset_token_expires_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "password_reset_requests"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_prr_user_created"),
            models.Index(fields=["expires_at"], name="idx_prr_expires"),
        ]

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email) or ""
        super().save(*args, **kwargs)


