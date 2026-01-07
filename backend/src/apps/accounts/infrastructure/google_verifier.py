from __future__ import annotations

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import requests

from apps.accounts.domain.errors import GoogleTokenInvalid
from apps.accounts.domain.ports import GoogleProfile, GoogleTokenVerifier


class GoogleIdTokenVerifier(GoogleTokenVerifier):
    def __init__(self) -> None:
        self._request = google_requests.Request()

    def verify(self, *, id_token: str) -> GoogleProfile:
        def _to_profile(info: dict) -> GoogleProfile:
            return GoogleProfile(
                sub=str(info.get("sub") or ""),
                email=str(info.get("email") or ""),
                email_verified=bool(info.get("email_verified")),
                full_name=str(info.get("name")) if info.get("name") else None,
            )

        try:
            info = google_id_token.verify_oauth2_token(
                id_token,
                self._request,
                audience=settings.GOOGLE_OAUTH_CLIENT_ID,
            )
            return _to_profile(info)
        except Exception:
            try:
                resp = requests.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": id_token},
                    timeout=5,
                )
            except requests.RequestException as exc:
                raise GoogleTokenInvalid() from exc

            if resp.status_code != 200:
                raise GoogleTokenInvalid()

            try:
                body = resp.json()
            except Exception as exc:
                raise GoogleTokenInvalid() from exc

            aud = str(body.get("aud") or "")
            iss = str(body.get("iss") or "")
            if aud != settings.GOOGLE_OAUTH_CLIENT_ID:
                raise GoogleTokenInvalid()
            if iss not in ("accounts.google.com", "https://accounts.google.com"):
                raise GoogleTokenInvalid()

            return _to_profile(body)


