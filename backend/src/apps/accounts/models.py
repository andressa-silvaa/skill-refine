"""
Compatibility model exports for Django app loading and legacy imports.
"""

from apps.accounts.infrastructure.models import (
    AuthIdentity,
    AuthProvider,
    EmailConfirmationToken,
    PasswordResetRequest,
    Session,
    User,
    UserManager,
    UserPassword,
    UserPreferences,
    UserQuerySet,
    UserStatus,
    UserTheme,
)

__all__ = [
    "AuthIdentity",
    "AuthProvider",
    "EmailConfirmationToken",
    "PasswordResetRequest",
    "Session",
    "User",
    "UserManager",
    "UserPassword",
    "UserPreferences",
    "UserQuerySet",
    "UserStatus",
    "UserTheme",
]


