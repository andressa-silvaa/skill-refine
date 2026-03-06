from __future__ import annotations

import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import permissions
from rest_framework.views import APIView

from apps.accounts.domain.errors import AccountsError
from shared.auth.drf import request_meta

from .services import google_login_with_id_token_service
from .view_helpers import append_query, safe_next_url, set_refresh_cookie

OAUTH_STATE_COOKIE = "sr_google_oauth_state"
OAUTH_NEXT_COOKIE = "sr_google_oauth_next"


class GoogleOAuthStartView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        next_url = safe_next_url(request.query_params.get("next"))
        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            return redirect(append_query(next_url, {"oauth_error": "google_not_configured"}))

        state = secrets.token_urlsafe(24)
        callback_url = request.build_absolute_uri("/accounts/auth/google/callback")

        params = {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "consent select_account",
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        resp = redirect(auth_url)
        resp.set_cookie(
            key=OAUTH_STATE_COOKIE,
            value=state,
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite="Lax",
            max_age=10 * 60,
            path="/",
        )
        resp.set_cookie(
            key=OAUTH_NEXT_COOKIE,
            value=next_url,
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite="Lax",
            max_age=10 * 60,
            path="/",
        )
        return resp


class GoogleOAuthCallbackView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        next_url = safe_next_url(request.COOKIES.get(OAUTH_NEXT_COOKIE))

        state_cookie = request.COOKIES.get(OAUTH_STATE_COOKIE)
        state = request.query_params.get("state")
        code = request.query_params.get("code")
        if not state_cookie or not state or state != state_cookie or not code:
            return redirect(f"{next_url}?oauth_error=invalid_state")

        callback_url = request.build_absolute_uri("/accounts/auth/google/callback")

        try:
            token_res = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "redirect_uri": callback_url,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
        except requests.RequestException:
            return redirect(append_query(next_url, {"oauth_error": "token_exchange_network"}))

        if token_res.status_code != 200:
            google_error = ""
            google_desc = ""
            try:
                body = token_res.json()
                google_error = str(body.get("error") or "")
                google_desc = str(body.get("error_description") or "")
            except Exception:
                pass

            params = {"oauth_error": "token_exchange_failed", "status": str(token_res.status_code)}
            if google_error:
                params["google_error"] = google_error
            if google_desc:
                params["google_error_description"] = google_desc[:180]
            return redirect(append_query(next_url, params))

        token_json = token_res.json()
        id_token = token_json.get("id_token")
        if not id_token:
            return redirect(f"{next_url}?oauth_error=missing_id_token")

        meta = request_meta(request)
        try:
            _, refresh_cookie = google_login_with_id_token_service(id_token, meta)
        except AccountsError:
            return redirect(f"{next_url}?oauth_error=google_token_invalid")

        resp = redirect(next_url)
        set_refresh_cookie(resp, refresh_cookie)
        resp.delete_cookie(OAUTH_STATE_COOKIE, path="/")
        resp.delete_cookie(OAUTH_NEXT_COOKIE, path="/")
        return resp
