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
from shared.utils.normalization import normalize_password

from .password_services import (
    email_confirmation_confirm_service,
    email_confirmation_request_service,
    password_change_service,
    password_reset_confirm_service,
    password_reset_request_service,
    password_reset_verify_service,
)

from .auth_common import WrongCurrentPassword, build_default_password_hasher, get_cfg








def register_service(validated_data: dict, meta: dict) -> tuple[object, bool]:
    """Register user and optionally send email confirmation. Returns (user_dto, email_confirmation_sent)."""
    users = OrmUserRepository()
    passwords = OrmPasswordRepository()
    identities = OrmAuthIdentityRepository()
    hasher = build_default_password_hasher()
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
        send_result = request_email_confirmation(
            cfg=get_cfg(),
            users=users,
            confirmations=confirmations,
            email_sender=email_sender,
            audit=audit,
            email=validated_data["email"],
            ip=meta["ip"],
            user_agent=meta["user_agent"],
        )
        email_confirmation_sent = bool(send_result.get("email_sent"))
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
    hasher = build_default_password_hasher()
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
