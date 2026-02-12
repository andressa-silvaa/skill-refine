"""
Accounts use cases — public API.

Import from here to keep compatibility with existing call sites:
  from apps.accounts.application.use_cases import register_user, login_with_password, ...
"""
from __future__ import annotations

from apps.accounts.application.use_cases.auth import (
    login_with_google,
    login_with_password,
    register_user,
)
from apps.accounts.application.use_cases.config import AccountsAuthConfig
from apps.accounts.application.use_cases.email_confirmation import (
    confirm_email,
    request_email_confirmation,
)
from apps.accounts.application.use_cases.password_reset import (
    confirm_new_password,
    request_password_reset,
    verify_password_reset_code,
)
from apps.accounts.application.use_cases.profile import delete_account, request_data_export
from apps.accounts.application.use_cases.session import logout, refresh_session
from apps.accounts.application.use_cases.types import (
    AuthResult,
    PasswordResetVerifyResult,
    RefreshResult,
)

__all__ = [
    "AccountsAuthConfig",
    "AuthResult",
    "PasswordResetVerifyResult",
    "RefreshResult",
    "confirm_email",
    "confirm_new_password",
    "delete_account",
    "login_with_google",
    "login_with_password",
    "logout",
    "refresh_session",
    "register_user",
    "request_data_export",
    "request_email_confirmation",
    "request_password_reset",
    "verify_password_reset_code",
]
