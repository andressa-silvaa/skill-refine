"""
Accounts API orchestration: call use_cases, apply rules, return data for views.
Pure extraction from views; no change to business rules or HTTP contract.
"""
from __future__ import annotations

from django.conf import settings

from apps.accounts.application.use_cases import (
    AccountsAuthConfig,
    confirm_email,
    confirm_new_password,
    login_with_google,
    login_with_password,
    refresh_session,
    register_user,
    request_email_confirmation,
    request_password_reset,
    verify_password_reset_code,
)
from apps.accounts.application.use_cases import (
    logout as logout_uc,
)
from apps.accounts.domain.errors import (
    EmailSendFailed,
    EmailServiceNotConfigured,
    TooManyRequests,
)
from apps.accounts.infrastructure.email_sender import DjangoEmailSender
from apps.accounts.infrastructure.google_verifier import GoogleIdTokenVerifier
from apps.accounts.infrastructure.password_hasher import Argon2PasswordHasher
from apps.accounts.infrastructure.repositories import (
    OrmAuthIdentityRepository,
    OrmEmailConfirmationRepository,
    OrmPasswordRepository,
    OrmPasswordResetRepository,
    OrmSessionRepository,
    OrmUserRepository,
)
from apps.audit.infrastructure.logger import OrmAuditLogger
from shared.auth.jwt import now_utc


class WrongCurrentPassword(Exception):
    """Raised when current password does not match (password change flow)."""


def get_cfg() -> AccountsAuthConfig:
    return AccountsAuthConfig(
        jwt_secret=settings.JWT_SECRET,
        jwt_issuer=settings.JWT_ISSUER,
        jwt_access_ttl_minutes=settings.JWT_ACCESS_TTL_MINUTES,
        refresh_token_pepper=settings.REFRESH_TOKEN_PEPPER,
        refresh_ttl_days=settings.REFRESH_TTL_DAYS,
        password_reset_code_ttl_minutes=settings.PASSWORD_RESET_CODE_TTL_MINUTES,
        password_reset_grant_ttl_minutes=settings.PASSWORD_RESET_GRANT_TTL_MINUTES,
        password_reset_code_pepper=settings.PASSWORD_RESET_CODE_PEPPER,
        email_confirmation_token_ttl_hours=settings.EMAIL_CONFIRMATION_TOKEN_TTL_HOURS,
        email_confirmation_token_pepper=settings.EMAIL_CONFIRMATION_TOKEN_PEPPER,
        frontend_url=settings.FRONTEND_URL,
        google_oauth_client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
    )


def register_service(validated_data: dict, meta: dict) -> tuple[object, bool]:
    """Register user and optionally send email confirmation. Returns (user_dto, email_confirmation_sent)."""
    users = OrmUserRepository()
    passwords = OrmPasswordRepository()
    identities = OrmAuthIdentityRepository()
    hasher = Argon2PasswordHasher()
    audit = OrmAuditLogger()

    user = register_user(
        cfg=get_cfg(),
        users=users,
        passwords=passwords,
        identities=identities,
        password_hasher=hasher,
        audit=audit,
        email=validated_data["email"],
        full_name=validated_data["full_name"],
        birth_date=validated_data.get("birth_date"),
        password=validated_data["password"],
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )

    email_confirmation_sent = True
    confirmations = OrmEmailConfirmationRepository()
    email_sender = DjangoEmailSender()
    try:
        request_email_confirmation(
            cfg=get_cfg(),
            users=users,
            confirmations=confirmations,
            email_sender=email_sender,
            audit=audit,
            email=validated_data["email"],
            ip=meta["ip"],
            user_agent=meta["user_agent"],
        )
    except (EmailServiceNotConfigured, EmailSendFailed):
        email_confirmation_sent = False
    except TooManyRequests:
        email_confirmation_sent = True
    except Exception:
        email_confirmation_sent = False

    return (user, email_confirmation_sent)


def login_service(validated_data: dict, meta: dict) -> tuple[object, str]:
    """Login with password. Returns (AuthResult, refresh_cookie)."""
    users = OrmUserRepository()
    passwords = OrmPasswordRepository()
    identities = OrmAuthIdentityRepository()
    sessions = OrmSessionRepository()
    hasher = Argon2PasswordHasher()
    audit = OrmAuditLogger()

    result, refresh_cookie = login_with_password(
        cfg=get_cfg(),
        users=users,
        passwords=passwords,
        identities=identities,
        sessions=sessions,
        password_hasher=hasher,
        audit=audit,
        email=validated_data["email"],
        password=validated_data["password"],
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    return (result, refresh_cookie)


def google_login_service(validated_data: dict, meta: dict) -> tuple[object, str]:
    """Login with Google id_token from request body. Returns (AuthResult, refresh_cookie)."""
    return google_login_with_id_token_service(validated_data["credential"], meta)


def google_login_with_id_token_service(id_token: str, meta: dict) -> tuple[object, str]:
    """Login with Google id_token (e.g. from OAuth callback code exchange). Returns (AuthResult, refresh_cookie)."""
    users = OrmUserRepository()
    identities = OrmAuthIdentityRepository()
    sessions = OrmSessionRepository()
    audit = OrmAuditLogger()
    google = GoogleIdTokenVerifier()

    result, refresh_cookie = login_with_google(
        cfg=get_cfg(),
        users=users,
        identities=identities,
        sessions=sessions,
        google=google,
        audit=audit,
        id_token=id_token,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    return (result, refresh_cookie)


def refresh_service(refresh_cookie: str, meta: dict) -> tuple[object, str]:
    """Refresh session. Returns (RefreshResult, new_refresh_cookie)."""
    users = OrmUserRepository()
    sessions = OrmSessionRepository()
    identities = OrmAuthIdentityRepository()
    audit = OrmAuditLogger()

    result, new_cookie = refresh_session(
        cfg=get_cfg(),
        users=users,
        sessions=sessions,
        identities=identities,
        audit=audit,
        refresh_cookie_value=refresh_cookie,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )
    return (result, new_cookie)


def logout_service(refresh_cookie: str | None, actor_user_id: str | None, meta: dict) -> None:
    """Revoke session (idempotent)."""
    sessions = OrmSessionRepository()
    audit = OrmAuditLogger()

    logout_uc(
        cfg=get_cfg(),
        sessions=sessions,
        audit=audit,
        refresh_cookie_value=refresh_cookie,
        actor_user_id=actor_user_id,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )


def password_reset_request_service(email: str, meta: dict) -> None:
    """Request password reset (send code email)."""
    users = OrmUserRepository()
    resets = OrmPasswordResetRepository()
    email_sender = DjangoEmailSender()
    audit = OrmAuditLogger()

    request_password_reset(
        cfg=get_cfg(),
        users=users,
        password_resets=resets,
        email_sender=email_sender,
        audit=audit,
        email=email,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )


def password_reset_verify_service(email: str, code: str, meta: dict) -> object:
    """Verify reset code. Returns PasswordResetVerifyResult."""
    resets = OrmPasswordResetRepository()
    audit = OrmAuditLogger()

    return verify_password_reset_code(
        cfg=get_cfg(),
        password_resets=resets,
        audit=audit,
        email=email,
        code=code,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )


def password_reset_confirm_service(
    email: str, reset_token: str, new_password: str, meta: dict
) -> None:
    """Confirm new password after reset."""
    resets = OrmPasswordResetRepository()
    passwords = OrmPasswordRepository()
    hasher = Argon2PasswordHasher()
    audit = OrmAuditLogger()

    confirm_new_password(
        cfg=get_cfg(),
        password_resets=resets,
        passwords=passwords,
        password_hasher=hasher,
        audit=audit,
        email=email,
        reset_token=reset_token,
        new_password=new_password,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )


def email_confirmation_request_service(email: str, meta: dict) -> None:
    """Request email confirmation (resend link)."""
    users = OrmUserRepository()
    confirmations = OrmEmailConfirmationRepository()
    email_sender = DjangoEmailSender()
    audit = OrmAuditLogger()

    request_email_confirmation(
        cfg=get_cfg(),
        users=users,
        confirmations=confirmations,
        email_sender=email_sender,
        audit=audit,
        email=email,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )


def email_confirmation_confirm_service(token: str, meta: dict) -> None:
    """Confirm email with token."""
    users = OrmUserRepository()
    confirmations = OrmEmailConfirmationRepository()
    audit = OrmAuditLogger()

    confirm_email(
        cfg=get_cfg(),
        users=users,
        confirmations=confirmations,
        audit=audit,
        token=token,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
    )


def password_change_service(
    user_id: str, current_password: str, new_password: str, meta: dict
) -> None:
    """Change password for authenticated user. Raises WrongCurrentPassword if current password wrong."""
    passwords = OrmPasswordRepository()
    hasher = Argon2PasswordHasher()
    audit = OrmAuditLogger()

    stored_hash = passwords.get_password_hash(user_id=user_id)
    if not stored_hash or not hasher.verify(stored_hash, current_password):
        audit.log(
            action="accounts.password_change_failed",
            actor_user_id=user_id,
            subject_user_id=user_id,
            ip=meta["ip"],
            user_agent=meta["user_agent"],
            metadata={"reason": "wrong_current_password"},
        )
        raise WrongCurrentPassword()

    now = now_utc()
    password_hash = hasher.hash(new_password)
    passwords.set_password(user_id=user_id, password_hash=password_hash, when=now)
    audit.log(
        action="accounts.password_changed",
        actor_user_id=user_id,
        subject_user_id=user_id,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        metadata={},
    )
