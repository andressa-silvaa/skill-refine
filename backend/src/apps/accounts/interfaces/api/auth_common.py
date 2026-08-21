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


class WrongCurrentPassword(Exception):
    """Raised when current password does not match (password change flow)."""


def build_default_password_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


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
