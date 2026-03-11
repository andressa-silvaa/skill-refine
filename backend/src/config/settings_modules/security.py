"""CORS and security headers."""
from __future__ import annotations

from .base import DEBUG, env

CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://host.docker.internal:3000",
        "http://host.docker.internal:5173",
    ],
)
try:
    frontend_origin = env.str("FRONTEND_URL", default="").rstrip("/")
    if frontend_origin and frontend_origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(frontend_origin)
except Exception:
    pass
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept", "accept-encoding", "authorization", "content-type",
    "origin", "user-agent", "x-csrftoken", "x-requested-with",
]
