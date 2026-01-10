from __future__ import annotations

from datetime import date, datetime

from django.db import models, transaction

from apps.accounts.domain.ports import (
    AuthIdentityRepository,
    EmailConfirmationRepository,
    PasswordRepository,
    PasswordResetRepository,
    SessionRepository,
    UserRepository,
)
from apps.accounts.infrastructure.models import (
    AuthIdentity,
    EmailConfirmationToken,
    PasswordResetRequest,
    Session,
    User,
    UserStatus,
    UserPassword,
)
from shared.utils.normalization import normalize_email


class OrmUserRepository(UserRepository):
    def get_by_email(self, email: str):
        email_n = normalize_email(email) or ""
        if not email_n:
            return None
        try:
            return User.objects.get(email=email_n)
        except User.DoesNotExist:
            return None

    def get_by_id(self, user_id: str):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    def create_user(self, *, email: str, full_name: str, birth_date: date | None):
        return User.objects.create(email=email, full_name=full_name, birth_date=birth_date)

    def mark_email_verified(self, *, user_id: str, when: datetime) -> None:
        User.objects.filter(id=user_id).update(email_verified_at=when)

    def soft_delete(self, *, user_id: str, when: datetime) -> None:
        User.objects.filter(id=user_id).update(deleted_at=when, status=UserStatus.DELETED)


class OrmPasswordRepository(PasswordRepository):
    def set_password(self, *, user_id: str, password_hash: str, when: datetime) -> None:
        UserPassword.objects.update_or_create(
            user_id=user_id,
            defaults={"password_hash": password_hash, "password_updated_at": when, "must_change_password": False},
        )

    def get_password_hash(self, *, user_id: str) -> str | None:
        try:
            return UserPassword.objects.get(user_id=user_id).password_hash
        except UserPassword.DoesNotExist:
            return None


class OrmAuthIdentityRepository(AuthIdentityRepository):
    def ensure_password_identity(self, *, user_id: str, when: datetime) -> None:
        AuthIdentity.objects.get_or_create(
            user_id=user_id,
            provider="password",
            defaults={"provider_user_id": None, "provider_email": None, "last_login_at": when},
        )

    def touch_last_login(self, *, user_id: str, provider: str, when: datetime) -> None:
        AuthIdentity.objects.filter(user_id=user_id, provider=provider).update(last_login_at=when)

    def get_google_identity_by_sub(self, *, sub: str):
        try:
            return AuthIdentity.objects.get(provider="google", provider_user_id=sub)
        except AuthIdentity.DoesNotExist:
            return None

    def upsert_google_identity(self, *, user_id: str, sub: str, email: str, when: datetime) -> None:
        AuthIdentity.objects.update_or_create(
            provider="google",
            provider_user_id=sub,
            defaults={
                "user_id": user_id,
                "provider_email": normalize_email(email),
                "last_login_at": when,
            },
        )


class OrmSessionRepository(SessionRepository):
    def create_session(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None,
    ):
        return Session.objects.create(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            ip=ip,
            user_agent=user_agent,
        )

    def get_session(self, session_id: str):
        try:
            return Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return None

    def revoke_session(self, *, session_id: str, when: datetime, replaced_by_session_id: str | None = None) -> None:
        Session.objects.filter(id=session_id, revoked_at__isnull=True).update(
            revoked_at=when,
            replaced_by_session_id=replaced_by_session_id,
        )

    def revoke_all_for_user(self, *, user_id: str, when: datetime) -> None:
        Session.objects.filter(user_id=user_id, revoked_at__isnull=True).update(
            revoked_at=when,
            replaced_by_session_id=None,
        )


class OrmPasswordResetRepository(PasswordResetRepository):
    def create_request(
        self,
        *,
        user_id: str,
        email: str,
        code_hash: str,
        expires_at: datetime,
    ):
        return PasswordResetRequest.objects.create(
            user_id=user_id,
            email=email,
            code_hash=code_hash,
            expires_at=expires_at,
        )

    def latest_active_for_email(self, *, email: str):
        email_n = normalize_email(email) or ""
        if not email_n:
            return None
        return (
            PasswordResetRequest.objects.filter(email=email_n, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

    def increment_attempts(self, *, request_id: str, when: datetime) -> None:
        with transaction.atomic():
            PasswordResetRequest.objects.filter(id=request_id).update(
                attempts=models.F("attempts") + 1,
                last_attempt_at=when,
            )

    def mark_verified_and_set_grant(
        self,
        *,
        request_id: str,
        when: datetime,
        reset_token_hash: str,
        reset_token_expires_at: datetime,
    ) -> None:
        PasswordResetRequest.objects.filter(id=request_id).update(
            verified_at=when,
            reset_token_hash=reset_token_hash,
            reset_token_expires_at=reset_token_expires_at,
        )

    def consume(self, *, request_id: str, when: datetime) -> None:
        PasswordResetRequest.objects.filter(id=request_id).update(consumed_at=when)


class OrmEmailConfirmationRepository(EmailConfirmationRepository):
    def latest_active_for_email(self, *, email: str):
        email_n = normalize_email(email) or ""
        if not email_n:
            return None
        return (
            EmailConfirmationToken.objects.filter(email=email_n, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

    def count_recent_for_email(self, *, email: str, since: datetime) -> int:
        email_n = normalize_email(email) or ""
        if not email_n:
            return 0
        return EmailConfirmationToken.objects.filter(email=email_n, created_at__gte=since).count()

    def count_recent_for_ip(self, *, ip: str, since: datetime) -> int:
        if not ip:
            return 0
        return EmailConfirmationToken.objects.filter(ip=ip, created_at__gte=since).count()

    def create_token(
        self,
        *,
        user_id: str,
        email: str,
        token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None,
    ):
        return EmailConfirmationToken.objects.create(
            user_id=user_id,
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
            ip=ip,
            user_agent=user_agent,
        )

    def get_active_by_token_hash(self, *, token_hash: str):
        if not token_hash:
            return None
        return (
            EmailConfirmationToken.objects.filter(token_hash=token_hash, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

    def consume(self, *, token_id: str, when: datetime) -> None:
        EmailConfirmationToken.objects.filter(id=token_id).update(consumed_at=when)

    def consume_if_active(self, *, token_id: str, when: datetime) -> bool:
        return (
            EmailConfirmationToken.objects.filter(id=token_id, consumed_at__isnull=True).update(consumed_at=when) == 1
        )

