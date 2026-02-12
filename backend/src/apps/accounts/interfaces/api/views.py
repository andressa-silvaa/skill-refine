from __future__ import annotations

import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.domain.errors import (
    AccountsError,
    EmailAlreadyInUse,
    EmailConfirmationExpired,
    EmailConfirmationInvalid,
    EmailNotConfirmed,
    EmailNotRegistered,
    EmailSendFailed,
    EmailServiceNotConfigured,
    GoogleLoginNotConfigured,
    InvalidCredentials,
    PasswordResetExpired,
    PasswordResetGrantInvalid,
    PasswordResetNotFound,
    PasswordResetNotVerified,
    PasswordResetTooManyAttempts,
    RefreshInvalid,
    RefreshRevoked,
    TooManyRequests,
    UserDisabled,
)
from apps.accounts.infrastructure.repositories import OrmUserRepository
from shared.api.responses import (
    error_response as _error,
)
from shared.api.responses import (
    extract_error_message,
)
from shared.api.responses import (
    field_error_response as _field_error,
)
from shared.auth.drf import request_meta

from .payloads import (
    login_response_payload,
    me_response_payload,
    password_reset_verify_payload,
    refresh_response_payload,
    register_response_payload,
    status_ok_payload,
    user_payload,
)
from .serializers import (
    EmailConfirmationConfirmSerializer,
    EmailConfirmationRequestSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    RegisterSerializer,
)
from .services import (
    WrongCurrentPassword,
    email_confirmation_confirm_service,
    email_confirmation_request_service,
    google_login_service,
    google_login_with_id_token_service,
    login_service,
    logout_service,
    password_change_service,
    password_reset_confirm_service,
    password_reset_request_service,
    password_reset_verify_service,
    refresh_service,
    register_service,
)


def _set_refresh_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=value,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
        max_age=int(settings.REFRESH_TTL_DAYS * 24 * 60 * 60),
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
    )


OAUTH_STATE_COOKIE = "sr_google_oauth_state"
OAUTH_NEXT_COOKIE = "sr_google_oauth_next"


def _append_query(url: str, params: dict[str, str]) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode(params)}"


def _safe_next_url(next_url: str | None) -> str:
    if not next_url:
        return "http://localhost:3000/oauth/callback"
    if next_url.startswith("http://localhost:3000") or next_url.startswith("http://127.0.0.1:3000"):
        return next_url
    return "http://localhost:3000/oauth/callback"




class GoogleOAuthStartView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        next_url = _safe_next_url(request.query_params.get("next"))
        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            return redirect(_append_query(next_url, {"oauth_error": "google_not_configured"}))

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
        next_url = _safe_next_url(request.COOKIES.get(OAUTH_NEXT_COOKIE))

        state_cookie = request.COOKIES.get(OAUTH_STATE_COOKIE)
        state = request.query_params.get("state")
        code = request.query_params.get("code")
        if not state_cookie or not state or state != state_cookie or not code:
            return redirect(f"{next_url}?oauth_error=invalid_state")

        callback_url = request.build_absolute_uri("/accounts/auth/google/callback")

        import requests

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
            return redirect(_append_query(next_url, {"oauth_error": "token_exchange_network"}))

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
            return redirect(_append_query(next_url, params))

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
        _set_refresh_cookie(resp, refresh_cookie)
        resp.delete_cookie(OAUTH_STATE_COOKIE, path="/")
        resp.delete_cookie(OAUTH_NEXT_COOKIE, path="/")
        return resp




class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            user, email_confirmation_sent = register_service(ser.validated_data, meta)
        except EmailAlreadyInUse:
            users = OrmUserRepository()
            existing = users.get_by_email(ser.validated_data["email"])
            if existing and getattr(existing, "email_verified_at", None) is None:
                return _error(
                    "email_not_confirmed",
                    "Confirme seu e-mail para continuar.",
                    status.HTTP_409_CONFLICT,
                )
            return _error("email_already_in_use", "E-mail já cadastrado", status.HTTP_409_CONFLICT)

        users = OrmUserRepository()
        user_dict = user_payload(users=users, user_id=str(user.id), fallback=user.__dict__)
        payload = register_response_payload(user_dict, email_confirmation_sent)
        return Response(payload, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            result, refresh_cookie = login_service(ser.validated_data, meta)
        except InvalidCredentials:
            return _error("invalid_credentials", "E-mail ou senha inválidos.", status.HTTP_401_UNAUTHORIZED)
        except UserDisabled:
            return _error("invalid_credentials", "E-mail ou senha inválidos.", status.HTTP_401_UNAUTHORIZED)
        except EmailNotConfirmed:
            return _error("email_not_confirmed", "Confirme seu e-mail para fazer login.", status.HTTP_403_FORBIDDEN)

        users = OrmUserRepository()
        user_dict = user_payload(users=users, user_id=str(result.user.id), fallback=result.user.__dict__)
        response = Response(login_response_payload(result.access_token, user_dict), status=status.HTTP_200_OK)
        _set_refresh_cookie(response, refresh_cookie)
        return response


class GoogleLoginView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = GoogleLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            result, refresh_cookie = google_login_service(ser.validated_data, meta)
        except GoogleLoginNotConfigured:
            return _error("google_not_configured", "Google login não configurado", status.HTTP_503_SERVICE_UNAVAILABLE)
        except AccountsError:
            return _error("google_token_invalid", "Token do Google inválido", status.HTTP_401_UNAUTHORIZED)

        users = OrmUserRepository()
        user_dict = user_payload(users=users, user_id=str(result.user.id), fallback=result.user.__dict__)
        response = Response(login_response_payload(result.access_token, user_dict), status=status.HTTP_200_OK)
        _set_refresh_cookie(response, refresh_cookie)
        return response


class RefreshView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_cookie = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not refresh_cookie:
            return _error("refresh_missing", "Sessão expirada", status.HTTP_401_UNAUTHORIZED)

        meta = request_meta(request)

        try:
            result, new_cookie = refresh_service(refresh_cookie, meta)
        except (RefreshInvalid, RefreshRevoked):
            response = _error("refresh_invalid", "Sessão expirada", status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        response = Response(refresh_response_payload(result.access_token), status=status.HTTP_200_OK)
        _set_refresh_cookie(response, new_cookie)
        return response


class LogoutView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_cookie = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        meta = request_meta(request)
        actor_user_id = None
        if getattr(request, "user", None) is not None:
            actor_user_id = str(getattr(request.user, "id", None) or "") or None

        logout_service(refresh_cookie, actor_user_id, meta)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class PasswordResetRequestView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            password_reset_request_service(ser.validated_data["email"], meta)
        except EmailNotRegistered:
            return _error(
                "email_not_registered",
                "Não existe nenhum usuário cadastrado com este e-mail.",
                status.HTTP_404_NOT_FOUND,
            )
        except (EmailServiceNotConfigured, EmailSendFailed):
            return _error(
                "email_service_unavailable",
                "Não foi possível enviar o e-mail agora. Tente novamente mais tarde.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AccountsError:
            return _error("password_reset_request_failed", "Não foi possível processar sua solicitação.", status.HTTP_400_BAD_REQUEST)

        return Response(status_ok_payload(), status=status.HTTP_200_OK)


class PasswordResetVerifyView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = PasswordResetVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            result = password_reset_verify_service(
                ser.validated_data["email"],
                ser.validated_data["code"],
                meta,
            )
        except PasswordResetTooManyAttempts:
            return _error("too_many_attempts", "Muitas tentativas. Solicite um novo código.", status.HTTP_429_TOO_MANY_REQUESTS)
        except (PasswordResetNotFound, PasswordResetExpired):
            return _error("invalid_code", "Código inválido ou expirado", status.HTTP_400_BAD_REQUEST)

        return Response(password_reset_verify_payload(result.reset_token), status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            password_reset_confirm_service(
                ser.validated_data["email"],
                ser.validated_data["reset_token"],
                ser.validated_data["new_password"],
                meta,
            )
        except PasswordResetNotVerified:
            return _error("not_verified", "Confirme o código antes de redefinir", status.HTTP_403_FORBIDDEN)
        except (PasswordResetGrantInvalid, PasswordResetExpired, PasswordResetNotFound):
            return _error("invalid_reset", "Sessão de reset inválida ou expirada", status.HTTP_400_BAD_REQUEST)

        return Response(status_ok_payload(), status=status.HTTP_200_OK)


class EmailConfirmationRequestView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = EmailConfirmationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            email_confirmation_request_service(ser.validated_data["email"], meta)
        except EmailNotRegistered:
            return _error(
                "email_not_registered",
                "Não existe nenhum usuário cadastrado com este e-mail.",
                status.HTTP_404_NOT_FOUND,
            )
        except TooManyRequests:
            return _error(
                "too_many_requests",
                "Aguarde um pouco antes de reenviar a confirmação.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except (EmailServiceNotConfigured, EmailSendFailed):
            return _error(
                "email_service_unavailable",
                "Não foi possível enviar o e-mail agora. Tente novamente mais tarde.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AccountsError:
            return _error(
                "email_confirmation_request_failed",
                "Não foi possível processar sua solicitação.",
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return _error(
                "email_confirmation_request_failed",
                "Serviço temporariamente indisponível. Tente novamente mais tarde.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(status_ok_payload(), status=status.HTTP_200_OK)


class EmailConfirmationConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = EmailConfirmationConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            email_confirmation_confirm_service(ser.validated_data["token"], meta)
        except EmailConfirmationExpired:
            return _error("token_expired", "Token expirado. Solicite um novo e-mail.", status.HTTP_400_BAD_REQUEST)
        except EmailConfirmationInvalid:
            return _error("token_invalid", "Token inválido. Solicite um novo e-mail.", status.HTTP_400_BAD_REQUEST)
        except AccountsError:
            return _error("email_confirmation_failed", "Não foi possível confirmar seu e-mail.", status.HTTP_400_BAD_REQUEST)
        except Exception:
            return _error(
                "email_confirmation_failed",
                "Serviço temporariamente indisponível. Tente novamente mais tarde.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(status_ok_payload(), status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(me_response_payload(request.user))


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = PasswordChangeSerializer(data=request.data)
        if not ser.is_valid():
            fields: dict[str, str] = {}
            for key in ("current_password", "new_password", "confirm_new_password"):
                if key in ser.errors:
                    try:
                        fields[key] = extract_error_message(ser.errors[key])
                    except Exception:
                        fields[key] = "Valor inválido."
            return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        current_password = ser.validated_data["current_password"]
        new_password = ser.validated_data["new_password"]
        confirm_new_password = ser.validated_data["confirm_new_password"]

        if new_password != confirm_new_password:
            return _field_error(
                "validation_error",
                "Dados inválidos.",
                {"confirm_new_password": "As senhas não coincidem"},
                status.HTTP_400_BAD_REQUEST,
            )

        user_id = str(getattr(request.user, "id", "")) or None
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        meta = request_meta(request)

        try:
            password_change_service(user_id, current_password, new_password, meta)
        except WrongCurrentPassword:
            return _field_error(
                "invalid_current_password",
                "Senha atual inválida.",
                {"current_password": "Senha atual inválida."},
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return _error(
                "password_change_failed",
                "Não foi possível atualizar sua senha agora. Tente novamente.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(status_ok_payload(), status=status.HTTP_200_OK)
