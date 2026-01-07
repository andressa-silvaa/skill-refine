from __future__ import annotations

from django.urls import path

from .views import (
    EmailConfirmationConfirmView,
    EmailConfirmationRequestView,
    GoogleLoginView,
    GoogleOAuthCallbackView,
    GoogleOAuthStartView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    RefreshView,
    RegisterView,
)


urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("google", GoogleLoginView.as_view(), name="google"),
    path("google/start", GoogleOAuthStartView.as_view(), name="google_oauth_start"),
    path("google/callback", GoogleOAuthCallbackView.as_view(), name="google_oauth_callback"),
    path("refresh", RefreshView.as_view(), name="refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("me", MeView.as_view(), name="me"),
    path("password-reset/request", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/verify", PasswordResetVerifyView.as_view(), name="password_reset_verify"),
    path("password-reset/confirm", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path(
        "email-confirmation/request",
        EmailConfirmationRequestView.as_view(),
        name="email_confirmation_request",
    ),
    path(
        "email-confirmation/confirm",
        EmailConfirmationConfirmView.as_view(),
        name="email_confirmation_confirm",
    ),
]


