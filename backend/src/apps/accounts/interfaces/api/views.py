"""
Compatibility facade for accounts API views.

Split by responsibility:
- oauth_views.py
- auth_views.py
- recovery_views.py
"""
from __future__ import annotations

from .auth_views import GoogleLoginView, LoginView, LogoutView, MeView, RefreshView, RegisterView
from .oauth_views import GoogleOAuthCallbackView, GoogleOAuthStartView
from .recovery_views import (
    EmailConfirmationConfirmView,
    EmailConfirmationRequestView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
)

__all__ = [
    "EmailConfirmationConfirmView",
    "EmailConfirmationRequestView",
    "GoogleLoginView",
    "GoogleOAuthCallbackView",
    "GoogleOAuthStartView",
    "LoginView",
    "LogoutView",
    "MeView",
    "PasswordChangeView",
    "PasswordResetConfirmView",
    "PasswordResetRequestView",
    "PasswordResetVerifyView",
    "RefreshView",
    "RegisterView",
]