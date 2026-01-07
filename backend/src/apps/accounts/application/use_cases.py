from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from apps.accounts.domain.errors import (
    EmailConfirmationExpired,
    EmailConfirmationInvalid,
    EmailNotConfirmed,
    EmailNotRegistered,
    EmailAlreadyInUse,
    EmailSendFailed,
    EmailServiceNotConfigured,
    GoogleLoginNotConfigured,
    GoogleTokenInvalid,
    InvalidCredentials,
    PasswordResetExpired,
    PasswordResetGrantInvalid,
    PasswordResetNotFound,
    PasswordResetNotVerified,
    PasswordResetTooManyAttempts,
    RefreshInvalid,
    RefreshRevoked,
    TooManyRequests,
    UserDisabled,
    ValidationError,
)
from apps.accounts.domain.ports import (
    AuthIdentityRepository,
    EmailConfirmationRepository,
    EmailSender,
    GoogleTokenVerifier,
    PasswordHasher,
    PasswordRepository,
    PasswordResetRepository,
    SessionRepository,
    UserDTO,
    UserRepository,
)
from apps.audit.domain.ports import AuditLogger
from shared.auth.jwt import JwtConfig, encode_access_token, now_utc
from shared.utils.normalization import normalize_email


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hash_secret(value: str, pepper: str) -> str:
    # HMAC would also be fine; this is enough for a one-way token hash with a server-side pepper.
    import hashlib

    return hashlib.sha256((pepper + ":" + value).encode("utf-8")).hexdigest()


def _random_digits(length: int) -> str:
    # cryptographically secure digits
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


@dataclass(frozen=True)
class AccountsAuthConfig:
    jwt_secret: str
    jwt_issuer: str
    jwt_access_ttl_minutes: int

    refresh_token_pepper: str
    refresh_ttl_days: int

    password_reset_code_ttl_minutes: int
    password_reset_grant_ttl_minutes: int
    password_reset_code_pepper: str

    email_confirmation_token_ttl_hours: int
    email_confirmation_token_pepper: str
    frontend_url: str

    google_oauth_client_id: str


@dataclass(frozen=True)
class AuthResult:
    access_token: str
    user: UserDTO


@dataclass(frozen=True)
class RefreshResult:
    access_token: str


@dataclass(frozen=True)
class PasswordResetVerifyResult:
    reset_token: str


def register_user(
    *,
    cfg: AccountsAuthConfig,
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
    password_hash = password_hasher.hash(password)
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
    cfg: AccountsAuthConfig,
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
) -> tuple[AuthResult, str]:
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

    stored_hash = passwords.get_password_hash(user_id=str(user.id))
    if not stored_hash or not password_hasher.verify(stored_hash, password):
        audit.log(
            action="accounts.login_failed",
            actor_user_id=str(user.id),
            subject_user_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
            metadata={"reason": "wrong_password"},
        )
        raise InvalidCredentials()

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
        AuthResult(
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


def _normalize_frontend_url(url: str) -> str:
    url = (url or "").strip()
    return url[:-1] if url.endswith("/") else url


def request_email_confirmation(
    *,
    cfg: AccountsAuthConfig,
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

    # Basic throttling: avoid multiple emails in a short window.
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

    # Slightly stronger rate limit (db-based, no cache required).
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
        # If sending failed, make sure the token cannot be used later.
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
    cfg: AccountsAuthConfig,
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

    # Enforce single-use (best-effort): only one request should be able to consume the token.
    if not confirmations.consume_if_active(token_id=str(rec.id), when=now):
        raise EmailConfirmationInvalid()

    # Idempotent: if already verified, nothing else to do.
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

def refresh_session(
    *,
    cfg: AccountsAuthConfig,
    users: UserRepository,
    sessions: SessionRepository,
    identities: AuthIdentityRepository,
    audit: AuditLogger,
    refresh_cookie_value: str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[RefreshResult, str]:
    try:
        session_id, refresh_plain = refresh_cookie_value.split(".", 1)
    except ValueError:
        raise RefreshInvalid()

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
        # Possible token theft; revoke session.
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

    # Rotate: create a new session, revoke current.
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

    return (RefreshResult(access_token=access_token), f"{new_session.id}.{new_refresh_plain}")


def logout(
    *,
    cfg: AccountsAuthConfig,
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


def login_with_google(
    *,
    cfg: AccountsAuthConfig,
    users: UserRepository,
    identities: AuthIdentityRepository,
    sessions: SessionRepository,
    google: GoogleTokenVerifier,
    audit: AuditLogger,
    id_token: str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[AuthResult, str]:
    if not cfg.google_oauth_client_id:
        raise GoogleLoginNotConfigured()

    try:
        profile = google.verify(id_token=id_token)
    except Exception as exc:  # noqa: BLE001
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
        AuthResult(
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


def request_password_reset(
    *,
    cfg: AccountsAuthConfig,
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
        # Simple anti-spam: avoid sending multiple emails in a short window.
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
        # Avoid leaving an "active" reset request that would throttle future attempts and/or enable code verification.
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
    except Exception as exc:  # noqa: BLE001
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
    cfg: AccountsAuthConfig,
    password_resets: PasswordResetRepository,
    audit: AuditLogger,
    email: str,
    code: str,
    ip: str | None,
    user_agent: str | None,
) -> PasswordResetVerifyResult:
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
    return PasswordResetVerifyResult(reset_token=reset_token)


def confirm_new_password(
    *,
    cfg: AccountsAuthConfig,
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


