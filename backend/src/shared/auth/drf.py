from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from apps.accounts.infrastructure.models import User
from shared.auth.jwt import JwtError, decode_token


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Bearer access token auth.

    Note: We do NOT rely on django.contrib.auth user model.
    """

    keyword = "Bearer"

    def authenticate(self, request: Request):
        header = request.headers.get("Authorization")
        if not header:
            return None
        try:
            keyword, token = header.split(" ", 1)
        except ValueError:
            return None
        if keyword != self.keyword or not token:
            return None

        try:
            payload = decode_token(secret=settings.JWT_SECRET, issuer=settings.JWT_ISSUER, token=token)
        except JwtError:
            raise AuthenticationFailed("Invalid token")

        if payload.get("typ") != "access":
            raise AuthenticationFailed("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationFailed("Invalid token subject")

        try:
            user = User.objects.active().get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")

        return (user, payload)  # request.user, request.auth


def request_meta(request: Request) -> dict[str, Any]:
    """
    Minimal request metadata for auditing/security.
    """

    return {
        "ip": _client_ip(request),
        "user_agent": request.headers.get("User-Agent"),
    }


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # XFF can be a comma-separated list
        return xff.split(",", 1)[0].strip() or None
    return request.META.get("REMOTE_ADDR")


