from __future__ import annotations

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from apps.accounts.domain.errors import GoogleTokenInvalid
from apps.accounts.domain.ports import GoogleProfile, GoogleTokenVerifier


class GoogleIdTokenVerifier(GoogleTokenVerifier):
    def __init__(self) -> None:
        self._request = google_requests.Request()

    def verify(self, *, id_token: str) -> GoogleProfile:
        try:
            info = google_id_token.verify_oauth2_token(
                id_token,
                self._request,
                audience=settings.GOOGLE_OAUTH_CLIENT_ID,
            )
        except Exception as exc:  # noqa: BLE001
            raise GoogleTokenInvalid() from exc

        # Expected fields: sub, email, email_verified, name
        return GoogleProfile(
            sub=str(info.get("sub") or ""),
            email=str(info.get("email") or ""),
            email_verified=bool(info.get("email_verified")),
            full_name=str(info.get("name")) if info.get("name") else None,
        )


