from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from rest_framework.response import Response


def set_refresh_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=value,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
        max_age=int(settings.REFRESH_TTL_DAYS * 24 * 60 * 60),
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
    )


def append_query(url: str, params: dict[str, str]) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode(params)}"


def safe_next_url(next_url: str | None) -> str:
    if not next_url:
        return "http://localhost:3000/oauth/callback"
    if next_url.startswith("http://localhost:3000") or next_url.startswith("http://127.0.0.1:3000"):
        return next_url
    return "http://localhost:3000/oauth/callback"
