"""Email confirmation use cases: request, confirm."""
from __future__ import annotations

import secrets
from datetime import timedelta

from apps.accounts.application.use_cases import config
from apps.accounts.application.use_cases._helpers import _hash_secret, _normalize_frontend_url, _utc
from apps.accounts.domain.errors import (
    EmailConfirmationExpired,
    EmailConfirmationInvalid,
    EmailNotRegistered,
    EmailSendFailed,
    EmailServiceNotConfigured,
    TooManyRequests,
    ValidationError,
)
from apps.accounts.domain.ports import (
    EmailConfirmationRepository,
    EmailSender,
    UserRepository,
)
from apps.audit.domain.ports import AuditLogger
from shared.auth.jwt import now_utc
from shared.utils.normalization import normalize_email


def request_email_confirmation(
    *,
    cfg: config.AccountsAuthConfig,
    users: UserRepository,
    confirmations: EmailConfirmationRepository,
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
            action="accounts.email_confirmation_requested",
            actor_user_id=None,
            subject_user_id=None,
            ip=ip,
            user_agent=user_agent,
            metadata={"email": email_n, "result": "email_not_registered"},
        )
        raise EmailNotRegistered()

    if getattr(user, "email_verified_at", None):
        audit.log(
            action="accounts.email_confirmation_requested",
            actor_user_id=str(user.id),
            subject_user_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"email": email_n, "result": "already_verified"},
        )
        return

    now = now_utc()

    last_req = confirmations.latest_active_for_email(email=email_n)
    if last_req is not None:
        last_created = _utc(last_req.created_at)
        if (now - last_created).total_seconds() < 60:
            audit.log(
                action="accounts.email_confirmation_requested",
                actor_user_id=str(user.id),
                subject_user_id=str(user.id),
                ip=ip,
                user_agent=user_agent,
                metadata={"email": email_n, "result": "throttled"},
            )
            raise TooManyRequests()

    since = now - timedelta(hours=1)
    if confirmations.count_recent_for_email(email=email_n, since=since) >= 8:
        raise TooManyRequests()
    if ip and confirmations.count_recent_for_ip(ip=ip, since=since) >= 25:
        raise TooManyRequests()

    token_plain = secrets.token_urlsafe(48)
    token_hash = _hash_secret(token_plain, cfg.email_confirmation_token_pepper)
    expires_at = now + timedelta(hours=cfg.email_confirmation_token_ttl_hours)

    created = confirmations.create_token(
        user_id=str(user.id),
        email=email_n,
        token_hash=token_hash,
        expires_at=expires_at,
        ip=ip,
        user_agent=user_agent,
    )

    frontend = _normalize_frontend_url(cfg.frontend_url)
    confirm_url = f"{frontend}/confirm-email?token={token_plain}"

    try:
        email_sender.send_email_confirmation_link(to_email=email_n, confirm_url=confirm_url)
    except (EmailServiceNotConfigured, EmailSendFailed) as exc:
        confirmations.consume(token_id=str(created.id), when=now)
        raise exc

    audit.log(
        action="accounts.email_confirmation_requested",
        actor_user_id=None,
        subject_user_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
        metadata={"email": email_n, "result": "sent"},
    )


def confirm_email(
    *,
    cfg: config.AccountsAuthConfig,
    users: UserRepository,
    confirmations: EmailConfirmationRepository,
    audit: AuditLogger,
    token: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    token = (token or "").strip()
    if len(token) < 10:
        raise EmailConfirmationInvalid()

    now = now_utc()
    token_hash = _hash_secret(token, cfg.email_confirmation_token_pepper)
    rec = confirmations.get_active_by_token_hash(token_hash=token_hash)
    if rec is None:
        raise EmailConfirmationInvalid()

    if _utc(rec.expires_at) <= now:
        confirmations.consume_if_active(token_id=str(rec.id), when=now)
        raise EmailConfirmationExpired()

    user = users.get_by_id(str(rec.user_id))
    if user is None:
        confirmations.consume_if_active(token_id=str(rec.id), when=now)
        raise EmailConfirmationInvalid()

    if not confirmations.consume_if_active(token_id=str(rec.id), when=now):
        raise EmailConfirmationInvalid()

    if not getattr(user, "email_verified_at", None):
        users.mark_email_verified(user_id=str(user.id), when=now)

    audit.log(
        action="accounts.email_confirmed",
        actor_user_id=str(user.id),
        subject_user_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
        metadata={"email": getattr(user, "email", None)},
    )
