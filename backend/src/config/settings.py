from __future__ import annotations

import os
from pathlib import Path

import environ


# src/config/settings.py -> backend/src
SRC_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = SRC_DIR.parent
REPO_DIR = BACKEND_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)

# Try backend/.env first, then repo-root .env
for candidate in (BACKEND_DIR / ".env", REPO_DIR / ".env"):
    if candidate.exists():
        env.read_env(str(candidate))
        break


DEBUG = env.bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="unsafe-dev-key-change-me")

ALLOWED_HOSTS = ["*"] if DEBUG else env.list("DJANGO_ALLOWED_HOSTS", default=[])


INSTALLED_APPS = [
    # Minimal Django core
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    # Domain apps (modular monolith)
    "apps.accounts",
    "apps.resumes",
    "apps.analysis",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {
    "default": env.db(),
}

# Pragmatic: enable SSL in production when the URL requests it (e.g. ?sslmode=require).
# django-environ passes query params into OPTIONS automatically for postgres.


LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    # Auth endpoints will come later; keep the base API simple for now.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    # We don't enable django.contrib.auth for now; avoid importing AnonymousUser.
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


