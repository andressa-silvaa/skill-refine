"""Base Django settings: env, apps, db, cache, i18n."""
from __future__ import annotations

from pathlib import Path

import environ

SRC_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = SRC_DIR.parent
REPO_DIR = BACKEND_DIR.parent

env = environ.Env(DJANGO_DEBUG=(bool, False))

for candidate in (BACKEND_DIR / ".env", REPO_DIR / ".env"):
    if candidate.exists():
        env.read_env(str(candidate))
        break

DEBUG = env.bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="unsafe-dev-key-change-me")
API_METRICS_ENABLED = env.bool("API_METRICS_ENABLED", default=DEBUG)

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
    "apps.dashboard",
    "apps.audit",
    "apps.notifications",
    "apps.search",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "shared.api.middleware.ApiMetricsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def _get_db_config():
    url = env.str("DATABASE_URL", default="")
    if not url or url.strip() == "":
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BACKEND_DIR / "db.sqlite3"),
        }
    return env.db()


DATABASES = {"default": _get_db_config()}

REDIS_URL = env.str("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": env.str("DJANGO_CACHE_KEY_PREFIX", default="sr"),
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "skill-refine",
        }
    }

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = str(BACKEND_DIR / "media")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

APP_ENV = env.str("APP_ENV", default="dev")
ALLOW_INPROCESS_JOB_FALLBACK = env.bool("ALLOW_INPROCESS_JOB_FALLBACK", default=DEBUG)

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
