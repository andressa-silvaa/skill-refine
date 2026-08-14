"""
Recuperacao de senha, confirmacao de email e troca de senha.

Separado de ``services.py`` para manter registro/login/refresh de um lado e os fluxos por token do
outro; sao ciclos de vida diferentes e mudam por motivos diferentes.
"""
from __future__ import annotations

from .auth_common import WrongCurrentPassword, build_default_password_hasher, get_cfg

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
    hasher = build_default_password_hasher()
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


def email_confirmation_request_service(email: str, meta: dict) -> dict[str, bool]:
    """Request email confirmation (resend link). Returns email_sent / already_verified flags."""
    users = OrmUserRepository()
    confirmations = OrmEmailConfirmationRepository()
    email_sender = DjangoEmailSender()
    audit = OrmAuditLogger()

    return request_email_confirmation(
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
    hasher = build_default_password_hasher()
    audit = OrmAuditLogger()

    stored_hash = passwords.get_password_hash(user_id=user_id)
    if not stored_hash or not hasher.verify(stored_hash, normalize_password(current_password)):
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
    password_hash = hasher.hash(normalize_password(new_password))
    passwords.set_password(user_id=user_id, password_hash=password_hash, when=now)
    audit.log(
        action="accounts.password_changed",
        actor_user_id=user_id,
        subject_user_id=user_id,
        ip=meta["ip"],
        user_agent=meta["user_agent"],
        metadata={},
    )
