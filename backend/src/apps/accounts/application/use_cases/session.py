"""Session use cases: refresh, logout."""
from __future__ import annotations

import secrets
from datetime import timedelta

from apps.accounts.application.use_cases import config, types
from apps.accounts.application.use_cases._helpers import _hash_secret, _utc
from apps.accounts.domain.errors import RefreshInvalid, RefreshRevoked
from apps.accounts.domain.ports import (
    AuthIdentityRepository,
    SessionRepository,
    UserRepository,
)
from apps.audit.domain.ports import AuditLogger
from shared.auth.jwt import JwtConfig, encode_access_token, now_utc


def refresh_session(
    *,
    cfg: config.AccountsAuthConfig,
    users: UserRepository,
    sessions: SessionRepository,
    identities: AuthIdentityRepository,
    audit: AuditLogger,
    refresh_cookie_value: str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[types.RefreshResult, str]:
    try:
        session_id, refresh_plain = refresh_cookie_value.split(".", 1)
    except ValueError as exc:
        raise RefreshInvalid() from exc

    session = sessions.get_session(session_id)
    if session is None:
        raise RefreshInvalid()

    now = now_utc()
    if session.revoked_at is not None:
        raise RefreshRevoked()
    if _utc(session.expires_at) <= now:
        raise RefreshRevoked()

    expected = session.refresh_token_hash
    provided = _hash_secret(refresh_plain, cfg.refresh_token_pepper)
    import hmac

    if not hmac.compare_digest(expected, provided):
        sessions.revoke_session(session_id=str(session.id), when=now, replaced_by_session_id=None)
        audit.log(
            action="accounts.refresh_failed",
            actor_user_id=str(session.user_id),
            subject_user_id=str(session.user_id),
            ip=ip,
            user_agent=user_agent,
            metadata={"reason": "hash_mismatch", "session_id": str(session.id)},
        )
        raise RefreshInvalid()

    user = users.get_by_id(str(session.user_id))
    if user is None or getattr(user, "status", "active") != "active":
        raise RefreshRevoked()

    new_refresh_plain = secrets.token_urlsafe(48)
    new_refresh_hash = _hash_secret(new_refresh_plain, cfg.refresh_token_pepper)
    new_expires_at = now + timedelta(days=cfg.refresh_ttl_days)
    new_session = sessions.create_session(
        user_id=str(user.id),
        refresh_token_hash=new_refresh_hash,
        expires_at=new_expires_at,
        ip=ip,
        user_agent=user_agent,
    )
    sessions.revoke_session(session_id=str(session.id), when=now, replaced_by_session_id=str(new_session.id))

    access_token = encode_access_token(
        cfg=JwtConfig(
            secret=cfg.jwt_secret,
            issuer=cfg.jwt_issuer,
            access_ttl_minutes=cfg.jwt_access_ttl_minutes,
        ),
        user_id=str(user.id),
        session_id=str(new_session.id),
    )

    audit.log(
        action="accounts.refresh_succeeded",
        actor_user_id=str(user.id),
        subject_user_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
        metadata={"old_session_id": str(session.id), "new_session_id": str(new_session.id)},
    )

    return (types.RefreshResult(access_token=access_token), f"{new_session.id}.{new_refresh_plain}")


def logout(
    *,
    cfg: config.AccountsAuthConfig,
    sessions: SessionRepository,
    audit: AuditLogger,
    refresh_cookie_value: str | None,
    actor_user_id: str | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    _ = cfg
    if not refresh_cookie_value:
        return
    try:
        session_id, _ = refresh_cookie_value.split(".", 1)
    except ValueError:
        return
    now = now_utc()
    sessions.revoke_session(session_id=session_id, when=now, replaced_by_session_id=None)
    audit.log(
        action="accounts.logout",
        actor_user_id=actor_user_id,
        subject_user_id=actor_user_id,
        ip=ip,
        user_agent=user_agent,
        metadata={"session_id": session_id},
    )
