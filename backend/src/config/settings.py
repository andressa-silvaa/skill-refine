from __future__ import annotations

import os
from pathlib import Path

import environ


SRC_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = SRC_DIR.parent
REPO_DIR = BACKEND_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)

for candidate in (BACKEND_DIR / ".env", REPO_DIR / ".env"):
    if candidate.exists():
        env.read_env(str(candidate))
        break


DEBUG = env.bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="unsafe-dev-key-change-me")

ALLOWED_HOSTS = ["*"] if DEBUG else env.list("DJANGO_ALLOWED_HOSTS", default=[])

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])


INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.accounts",
    "apps.resumes",
    "apps.analysis",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {
    "default": env.db(),
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"

# Media (user uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = str(BACKEND_DIR / "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

APP_ENV = env.str("APP_ENV", default="dev")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

JWT_SECRET = env.str("JWT_SECRET", default=SECRET_KEY)
JWT_ISSUER = env.str("JWT_ISSUER", default="skill-refine")
JWT_ACCESS_TTL_MINUTES = env.int("JWT_ACCESS_TTL_MINUTES", default=15)

REFRESH_TOKEN_PEPPER = env.str("REFRESH_TOKEN_PEPPER", default=SECRET_KEY)
REFRESH_TTL_DAYS = env.int("REFRESH_TTL_DAYS", default=30)

REFRESH_COOKIE_NAME = env.str("REFRESH_COOKIE_NAME", default="sr_refresh")
REFRESH_COOKIE_SECURE = env.bool("REFRESH_COOKIE_SECURE", default=(not DEBUG))
REFRESH_COOKIE_SAMESITE = env.str("REFRESH_COOKIE_SAMESITE", default="Lax")
REFRESH_COOKIE_PATH = env.str("REFRESH_COOKIE_PATH", default="/")

PASSWORD_RESET_CODE_TTL_MINUTES = env.int("PASSWORD_RESET_CODE_TTL_MINUTES", default=10)
PASSWORD_RESET_GRANT_TTL_MINUTES = env.int("PASSWORD_RESET_GRANT_TTL_MINUTES", default=15)
PASSWORD_RESET_CODE_PEPPER = env.str("PASSWORD_RESET_CODE_PEPPER", default=SECRET_KEY)

EMAIL_CONFIRMATION_TOKEN_TTL_HOURS = env.int("EMAIL_CONFIRMATION_TOKEN_TTL_HOURS", default=24)
EMAIL_CONFIRMATION_TOKEN_PEPPER = env.str("EMAIL_CONFIRMATION_TOKEN_PEPPER", default=SECRET_KEY)
FRONTEND_URL = env.str("FRONTEND_URL", default="http://localhost:3000")

CLOUDINARY_URL = env.str("CLOUDINARY_URL", default="")

GOOGLE_OAUTH_CLIENT_ID = env.str("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env.str("GOOGLE_OAUTH_CLIENT_SECRET", default="")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.str("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="no-reply@skillrefine.local")


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "shared.auth.drf.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
}


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
