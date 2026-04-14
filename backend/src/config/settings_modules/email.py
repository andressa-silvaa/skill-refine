"""Email backend configuration (SMTP; Resend supported via RESEND_API_KEY or explicit SMTP)."""
from __future__ import annotations

from .base import env

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

_resend_key = env.str("RESEND_API_KEY", default="").strip()
_email_host = env.str("EMAIL_HOST", default="").strip()

# Resend SMTP: https://resend.com/docs/send-with-smtp
# Easiest: set only RESEND_API_KEY (+ DEFAULT_FROM_EMAIL with a verified domain or onboarding@resend.dev).
if _resend_key and not _email_host:
    EMAIL_HOST = "smtp.resend.com"
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_HOST_USER = "resend"
    EMAIL_HOST_PASSWORD = _resend_key
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
    EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
else:
    EMAIL_HOST = _email_host
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    _smtp_user = env.str("EMAIL_HOST_USER", default="").strip()
    _smtp_password = env.str("EMAIL_HOST_PASSWORD", default="").strip()
    if not _smtp_password and _resend_key and (
        not _email_host or _email_host == "smtp.resend.com"
    ):
        _smtp_password = _resend_key
        if not _smtp_user:
            _smtp_user = "resend"
    EMAIL_HOST_USER = _smtp_user
    EMAIL_HOST_PASSWORD = _smtp_password
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
    EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="no-reply@skillrefine.local")
