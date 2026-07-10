"""Auth use cases: register, login (password + Google)."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from apps.accounts.application.use_cases import config, types
from apps.accounts.application.use_cases._helpers import _hash_secret
from apps.accounts.domain.errors import (
    EmailAlreadyInUse,
    EmailNotConfirmed,
    GoogleLoginNotConfigured,
    GoogleTokenInvalid,
    InvalidCredentials,
    UserDisabled,
    ValidationError,
)
from apps.accounts.domain.ports import (
    AuthIdentityRepository,
    GoogleTokenVerifier,
    PasswordHasher,
    PasswordRepository,
    SessionRepository,
    UserDTO,
    UserRepository,
)
from apps.audit.domain.ports import AuditLogger
from shared.auth.jwt import JwtConfig, encode_access_token, now_utc
from shared.utils.normalization import normalize_email, normalize_password


def register_user(
    *,
    cfg: config.AccountsAuthConfig,
    users: UserRepository,
    passwords: PasswordRepository,
    identities: AuthIdentityRepository,
    password_hasher: PasswordHasher,
    audit: AuditLogger,
    email: str,
    full_name: str,
    birth_date: datetime | None,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> UserDTO:
    _ = cfg
    email_n = normalize_email(email)
    if not email_n:
        raise ValidationError("Invalid email")

    existing = users.get_by_email(email_n)
    if existing is not None:
        raise EmailAlreadyInUse()

    user = users.create_user(email=email_n, full_name=full_name, birth_date=birth_date)
    password_hash = password_hasher.hash(normalize_password(password))
    now = now_utc()
    passwords.set_password(user_id=str(user.id), password_hash=password_hash, when=now)
    identities.ensure_password_identity(user_id=str(user.id), when=now)

    audit.log(
        action="accounts.register",
        actor_user_id=None,
        subject_user_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
        metadata={"email": email_n},
    )

    return UserDTO(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        email_verified=bool(user.email_verified_at),
    )


def login_with_password(
    *,
    cfg: config.AccountsAuthConfig,
    users: UserRepository,
    passwords: PasswordRepository,
    identities: AuthIdentityRepository,
    sessions: SessionRepository,
    password_hasher: PasswordHasher,
    audit: AuditLogger,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[types.AuthResult, str]:
    email_n = normalize_email(email)
    if not email_n:
        raise InvalidCredentials()

    user = users.get_by_email(email_n)
    if user is None:
        audit.log(
            action="accounts.login_failed",
            actor_user_id=None,
            subject_user_id=None,
            ip=ip,
            user_agent=user_agent,
            metadata={"email": email_n, "reason": "not_found"},
        )
        raise InvalidCredentials()

    if getattr(user, "status", "active") != "active":
        audit.log(
            action="accounts.login_failed",
            actor_user_id=str(user.id),
            subject_user_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"reason": "disabled"},
        )
        raise UserDisabled()

    password_n = normalize_password(password)
    stored_hash = passwords.get_password_hash(user_id=str(user.id))
    if not stored_hash or not password_hasher.verify(stored_hash, password_n):
        audit.log(
            action="accounts.login_failed",
            actor_user_id=str(user.id),
            subject_user_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"reason": "wrong_password"},
        )
        raise InvalidCredentials()

    if password_hasher.needs_rehash(stored_hash):
        try:
            passwords.set_password(
                user_id=str(user.id),
                password_hash=password_hasher.hash(password_n),
                when=now_utc(),
            )
        except Exception:
            pass

    if not getattr(user, "email_verified_at", None):
        audit.log(
            action="accounts.login_failed",
            actor_user_id=str(user.id),
            subject_user_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"reason": "email_not_confirmed"},
        )
        raise EmailNotConfirmed()

    now = now_utc()
    identities.ensure_password_identity(user_id=str(user.id), when=now)
    identities.touch_last_login(user_id=str(user.id), provider="password", when=now)

    refresh_plain = secrets.token_urlsafe(48)
    refresh_hash = _hash_secret(refresh_plain, cfg.refresh_token_pepper)
    expires_at = now + timedelta(days=cfg.refresh_ttl_days)
    session = sessions.create_session(
        user_id=str(user.id),
        refresh_token_hash=refresh_hash,
        expires_at=expires_at,
        ip=ip,
        user_agent=user_agent,
    )

    access_token = encode_access_token(
        cfg=JwtConfig(
            secret=cfg.jwt_secret,
            issuer=cfg.jwt_issuer,
            access_ttl_minutes=cfg.jwt_access_ttl_minutes,
        ),
        user_id=str(user.id),
        session_id=str(session.id),
    )

    audit.log(
        action="accounts.login_succeeded",
        actor_user_id=str(user.id),
        subject_user_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
        metadata={"provider": "password"},
    )

    return (
        types.AuthResult(
            access_token=access_token,
            user=UserDTO(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                email_verified=bool(user.email_verified_at),
            ),
        ),
        f"{session.id}.{refresh_plain}",
    )


def login_with_google(
    *,
    cfg: config.AccountsAuthConfig,
    users: UserRepository,
    identities: AuthIdentityRepository,
    sessions: SessionRepository,
    google: GoogleTokenVerifier,
    audit: AuditLogger,
    id_token: str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[types.AuthResult, str]:
    if not cfg.google_oauth_client_id:
        raise GoogleLoginNotConfigured()

    try:
        profile = google.verify(id_token=id_token)
    except Exception as exc:
        raise GoogleTokenInvalid() from exc

    email_n = normalize_email(profile.email)
    if not email_n or not profile.email_verified:
        raise GoogleTokenInvalid()

    now = now_utc()

    identity = identities.get_google_identity_by_sub(sub=profile.sub)
    if identity is not None:
        user = users.get_by_id(str(identity.user_id))
    else:
        user = users.get_by_email(email_n)

    if user is None:
        user = users.create_user(
            email=email_n,
            full_name=profile.full_name or email_n.split("@", 1)[0],
            birth_date=None,
        )

    if getattr(user, "status", "active") != "active":
        raise UserDisabled()

    users.mark_email_verified(user_id=str(user.id), when=now)
    identities.upsert_google_identity(user_id=str(user.id), sub=profile.sub, email=email_n, when=now)
    identities.touch_last_login(user_id=str(user.id), provider="google", when=now)

    refresh_plain = secrets.token_urlsafe(48)
    refresh_hash = _hash_secret(refresh_plain, cfg.refresh_token_pepper)
    expires_at = now + timedelta(days=cfg.refresh_ttl_days)
    session = sessions.create_session(
        user_id=str(user.id),
        refresh_token_hash=refresh_hash,
        expires_at=expires_at,
        ip=ip,
        user_agent=user_agent,
    )
    access_token = encode_access_token(
        cfg=JwtConfig(
            secret=cfg.jwt_secret,
            issuer=cfg.jwt_issuer,
            access_ttl_minutes=cfg.jwt_access_ttl_minutes,
        ),
        user_id=str(user.id),
        session_id=str(session.id),
    )

    audit.log(
        action="accounts.login_succeeded",
        actor_user_id=str(user.id),
        subject_user_id=str(user.id),
        ip=ip,
        user_agent=user_agent,
        metadata={"provider": "google"},
    )

    return (
        types.AuthResult(
            access_token=access_token,
            user=UserDTO(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                email_verified=True,
            ),
        ),
        f"{session.id}.{refresh_plain}",
    )
