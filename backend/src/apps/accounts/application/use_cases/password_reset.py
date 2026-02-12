"""Password reset use cases: request, verify code, confirm new password."""
from __future__ import annotations

import secrets
from datetime import timedelta

from apps.accounts.application.use_cases import config, types
from apps.accounts.application.use_cases._helpers import _hash_secret, _random_digits, _utc
from apps.accounts.domain.errors import (
    EmailNotRegistered,
    EmailSendFailed,
    EmailServiceNotConfigured,
    PasswordResetExpired,
    PasswordResetGrantInvalid,
    PasswordResetNotFound,
    PasswordResetNotVerified,
    PasswordResetTooManyAttempts,
    ValidationError,
)
from apps.accounts.domain.ports import (
    EmailSender,
    PasswordHasher,
    PasswordRepository,
    PasswordResetRepository,
    UserRepository,
)
from apps.audit.domain.ports import AuditLogger
from shared.auth.jwt import now_utc
from shared.utils.normalization import normalize_email


def request_password_reset(
    *,
    cfg: config.AccountsAuthConfig,
    users: UserRepository,
    password_resets: PasswordResetRepository,
    email_sender: EmailSender,
    audit: AuditLogger,
    email: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    email_n = normalize_email(email)
    if not email_n:
        raise ValidationError("Invalid email")

    user = users.get_by_email(email_n)
    if user is None:
        audit.log(
            action="accounts.password_reset_requested",
            actor_user_id=None,
            subject_user_id=None,
            ip=ip,
            user_agent=user_agent,
            metadata={"email": email_n, "result": "email_not_registered"},
        )
        raise EmailNotRegistered()

    now = now_utc()
    last_req = password_resets.latest_active_for_email(email=email_n)
    if last_req is not None:
        last_created = _utc(last_req.created_at)
        if (now - last_created).total_seconds() < 60:
            audit.log(
                action="accounts.password_reset_requested",
                actor_user_id=None,
                subject_user_id=str(user.id),
                ip=ip,
                user_agent=user_agent,
                metadata={"email": email_n, "result": "throttled"},
            )
            return

    code = _random_digits(5)
    code_hash = _hash_secret(code, cfg.password_reset_code_pepper)
    expires_at = now + timedelta(minutes=cfg.password_reset_code_ttl_minutes)

    created = password_resets.create_request(
        user_id=str(user.id),
        email=email_n,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    try:
        email_sender.send_password_reset_code(to_email=email_n, code=code)
    except (EmailServiceNotConfigured, EmailSendFailed):
        created_id = getattr(created, "id", None)
        if created_id:
            password_resets.consume(request_id=str(created_id), when=now)
        audit.log(
            action="accounts.password_reset_requested",
            actor_user_id=None,
            subject_user_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"email": email_n, "result": "email_failed"},
        )
        raise
    except Exception as exc:
        created_id = getattr(created, "id", None)
        if created_id:
            password_resets.consume(request_id=str(created_id), when=now)
        audit.log(
            action="accounts.password_reset_requested",
            actor_user_id=None,
            subject_user_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"email": email_n, "result": "email_failed"},
        )
        raise EmailSendFailed() from exc

    audit.log(
        action="accounts.password_reset_requested",
        actor_user_id=None,
        subject_user_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
        metadata={"email": email_n, "result": "sent"},
    )


def verify_password_reset_code(
    *,
    cfg: config.AccountsAuthConfig,
    password_resets: PasswordResetRepository,
    audit: AuditLogger,
    email: str,
    code: str,
    ip: str | None,
    user_agent: str | None,
) -> types.PasswordResetVerifyResult:
    email_n = normalize_email(email) or ""
    req = password_resets.latest_active_for_email(email=email_n)
    if req is None:
        raise PasswordResetNotFound()

    now = now_utc()
    if _utc(req.expires_at) <= now or req.consumed_at is not None:
        raise PasswordResetExpired()

    if req.attempts >= 5:
        raise PasswordResetTooManyAttempts()

    import hmac

    expected = req.code_hash
    provided = _hash_secret(code.strip(), cfg.password_reset_code_pepper)
    if not hmac.compare_digest(expected, provided):
        password_resets.increment_attempts(request_id=str(req.id), when=now)
        audit.log(
            action="accounts.password_reset_verify_failed",
            actor_user_id=None,
            subject_user_id=str(req.user_id),
            ip=ip,
            user_agent=user_agent,
            metadata={"request_id": str(req.id)},
        )
        raise PasswordResetNotFound()

    reset_token = secrets.token_urlsafe(48)
    reset_hash = _hash_secret(reset_token, cfg.password_reset_code_pepper)
    reset_expires_at = now + timedelta(minutes=cfg.password_reset_grant_ttl_minutes)
    password_resets.mark_verified_and_set_grant(
        request_id=str(req.id),
        when=now,
        reset_token_hash=reset_hash,
        reset_token_expires_at=reset_expires_at,
    )
    audit.log(
        action="accounts.password_reset_verified",
        actor_user_id=None,
        subject_user_id=str(req.user_id),
        ip=ip,
        user_agent=user_agent,
        metadata={"request_id": str(req.id)},
    )
    return types.PasswordResetVerifyResult(reset_token=reset_token)


def confirm_new_password(
    *,
    cfg: config.AccountsAuthConfig,
    password_resets: PasswordResetRepository,
    passwords: PasswordRepository,
    password_hasher: PasswordHasher,
    audit: AuditLogger,
    email: str,
    reset_token: str,
    new_password: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    email_n = normalize_email(email) or ""
    req = password_resets.latest_active_for_email(email=email_n)
    if req is None:
        raise PasswordResetNotFound()

    now = now_utc()
    if req.consumed_at is not None:
        raise PasswordResetExpired()

    if getattr(req, "verified_at", None) is None:
        raise PasswordResetNotVerified()

    reset_token_expires_at = getattr(req, "reset_token_expires_at", None)
    if not reset_token_expires_at or _utc(reset_token_expires_at) <= now:
        raise PasswordResetGrantInvalid()

    import hmac

    expected = getattr(req, "reset_token_hash", None) or ""
    provided = _hash_secret(reset_token, cfg.password_reset_code_pepper)
    if not hmac.compare_digest(expected, provided):
        raise PasswordResetGrantInvalid()

    password_hash = password_hasher.hash(new_password)
    passwords.set_password(user_id=str(req.user_id), password_hash=password_hash, when=now)
    password_resets.consume(request_id=str(req.id), when=now)
    audit.log(
        action="accounts.password_changed",
        actor_user_id=None,
        subject_user_id=str(req.user_id),
        ip=ip,
        user_agent=user_agent,
        metadata={"request_id": str(req.id)},
    )
