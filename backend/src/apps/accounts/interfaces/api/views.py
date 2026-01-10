from __future__ import annotations

import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.application.use_cases import (
    AccountsAuthConfig,
    confirm_new_password,
    confirm_email,
    login_with_google,
    login_with_password,
    refresh_session,
    register_user,
    request_email_confirmation,
    request_password_reset,
    verify_password_reset_code,
)
from apps.accounts.domain.errors import (
    AccountsError,
    EmailConfirmationExpired,
    EmailConfirmationInvalid,
    EmailNotRegistered,
    EmailAlreadyInUse,
    EmailSendFailed,
    EmailServiceNotConfigured,
    EmailNotConfirmed,
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
)
from apps.accounts.infrastructure.email_sender import DjangoEmailSender
from apps.accounts.infrastructure.google_verifier import GoogleIdTokenVerifier
from apps.accounts.infrastructure.password_hasher import Argon2PasswordHasher
from apps.accounts.infrastructure.repositories import (
    OrmAuthIdentityRepository,
    OrmEmailConfirmationRepository,
    OrmPasswordRepository,
    OrmPasswordResetRepository,
    OrmSessionRepository,
    OrmUserRepository,
)
from apps.audit.infrastructure.logger import OrmAuditLogger
from shared.auth.drf import request_meta
from shared.auth.jwt import now_utc

from apps.accounts.infrastructure.cloudinary_avatar import avatar_url

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


def _cfg() -> AccountsAuthConfig:
    return AccountsAuthConfig(
        jwt_secret=settings.JWT_SECRET,
        jwt_issuer=settings.JWT_ISSUER,
        jwt_access_ttl_minutes=settings.JWT_ACCESS_TTL_MINUTES,
        refresh_token_pepper=settings.REFRESH_TOKEN_PEPPER,
        refresh_ttl_days=settings.REFRESH_TTL_DAYS,
        password_reset_code_ttl_minutes=settings.PASSWORD_RESET_CODE_TTL_MINUTES,
        password_reset_grant_ttl_minutes=settings.PASSWORD_RESET_GRANT_TTL_MINUTES,
        password_reset_code_pepper=settings.PASSWORD_RESET_CODE_PEPPER,
        email_confirmation_token_ttl_hours=settings.EMAIL_CONFIRMATION_TOKEN_TTL_HOURS,
        email_confirmation_token_pepper=settings.EMAIL_CONFIRMATION_TOKEN_PEPPER,
        frontend_url=settings.FRONTEND_URL,
        google_oauth_client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
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


def _canonical_error_code(code: str) -> str:
    return (code or "").strip().upper()


def _error(code: str, message: str, http_status: int) -> Response:
    canonical = _canonical_error_code(code)
    payload = {
        "error": {"code": code, "error_code": canonical, "message": message},
        "error_code": canonical,
        "message": message,
    }
    return Response(payload, status=http_status)


def _field_error(code: str, message: str, fields: dict[str, str], http_status: int) -> Response:
    canonical = _canonical_error_code(code)
    payload = {
        "error": {"code": code, "error_code": canonical, "message": message},
        "error_code": canonical,
        "message": message,
        "fields": fields,
    }
    return Response(payload, status=http_status)


def _user_payload(*, users: OrmUserRepository, user_id: str, fallback: dict) -> dict:
    u = users.get_by_id(user_id)
    if not u:
        return fallback
    key = getattr(u, "avatar_storage_key", None)
    url = avatar_url(str(key) if key else None)
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "email_verified": bool(getattr(u, "email_verified_at", None)),
        "status": getattr(u, "status", None),
        "created_at": getattr(u, "created_at", None),
        "avatar_storage_key": str(key) if key else None,
        "avatarStorageKey": str(key) if key else None,
        "avatar_url": url,
        "avatarUrl": url,
    }


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
        users = OrmUserRepository()
        identities = OrmAuthIdentityRepository()
        sessions = OrmSessionRepository()
        audit = OrmAuditLogger()
        google = GoogleIdTokenVerifier()

        try:
            result, refresh_cookie = login_with_google(
                cfg=_cfg(),
                users=users,
                identities=identities,
                sessions=sessions,
                google=google,
                audit=audit,
                id_token=id_token,
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
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

        users = OrmUserRepository()
        passwords = OrmPasswordRepository()
        identities = OrmAuthIdentityRepository()
        hasher = Argon2PasswordHasher()
        audit = OrmAuditLogger()

        try:
            user = register_user(
                cfg=_cfg(),
                users=users,
                passwords=passwords,
                identities=identities,
                password_hasher=hasher,
                audit=audit,
                email=ser.validated_data["email"],
                full_name=ser.validated_data["full_name"],
                birth_date=ser.validated_data.get("birth_date"),
                password=ser.validated_data["password"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except EmailAlreadyInUse:
            existing = users.get_by_email(ser.validated_data["email"])
            if existing and getattr(existing, "email_verified_at", None) is None:
                return _error(
                    "email_not_confirmed",
                    "Confirme seu e-mail para continuar.",
                    status.HTTP_409_CONFLICT,
                )
            return _error("email_already_in_use", "E-mail já cadastrado", status.HTTP_409_CONFLICT)

        email_confirmation_sent = True
        confirmations = OrmEmailConfirmationRepository()
        email_sender = DjangoEmailSender()
        try:
            request_email_confirmation(
                cfg=_cfg(),
                users=users,
                confirmations=confirmations,
                email_sender=email_sender,
                audit=audit,
                email=ser.validated_data["email"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except (EmailServiceNotConfigured, EmailSendFailed):
            email_confirmation_sent = False
        except TooManyRequests:
            email_confirmation_sent = True
        except Exception:
            email_confirmation_sent = False

        return Response(
            {
                "user": _user_payload(users=users, user_id=str(user.id), fallback=user.__dict__),
                "email_confirmation_sent": email_confirmation_sent,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        users = OrmUserRepository()
        passwords = OrmPasswordRepository()
        identities = OrmAuthIdentityRepository()
        sessions = OrmSessionRepository()
        hasher = Argon2PasswordHasher()
        audit = OrmAuditLogger()

        try:
            result, refresh_cookie = login_with_password(
                cfg=_cfg(),
                users=users,
                passwords=passwords,
                identities=identities,
                sessions=sessions,
                password_hasher=hasher,
                audit=audit,
                email=ser.validated_data["email"],
                password=ser.validated_data["password"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except InvalidCredentials:
            return _error("invalid_credentials", "E-mail ou senha inválidos.", status.HTTP_401_UNAUTHORIZED)
        except EmailNotConfirmed:
            return _error("email_not_confirmed", "Confirme seu e-mail para fazer login.", status.HTTP_403_FORBIDDEN)

        fallback_user = result.user.__dict__
        response = Response(
            {
                "access_token": result.access_token,
                "user": _user_payload(users=users, user_id=str(result.user.id), fallback=fallback_user),
            },
            status=status.HTTP_200_OK,
        )
        _set_refresh_cookie(response, refresh_cookie)
        return response


class GoogleLoginView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = GoogleLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        users = OrmUserRepository()
        identities = OrmAuthIdentityRepository()
        sessions = OrmSessionRepository()
        audit = OrmAuditLogger()
        google = GoogleIdTokenVerifier()

        try:
            result, refresh_cookie = login_with_google(
                cfg=_cfg(),
                users=users,
                identities=identities,
                sessions=sessions,
                google=google,
                audit=audit,
                id_token=ser.validated_data["credential"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except GoogleLoginNotConfigured:
            return _error("google_not_configured", "Google login não configurado", status.HTTP_503_SERVICE_UNAVAILABLE)
        except AccountsError:
            return _error("google_token_invalid", "Token do Google inválido", status.HTTP_401_UNAUTHORIZED)

        fallback_user = result.user.__dict__
        response = Response(
            {
                "access_token": result.access_token,
                "user": _user_payload(users=users, user_id=str(result.user.id), fallback=fallback_user),
            },
            status=status.HTTP_200_OK,
        )
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

        users = OrmUserRepository()
        sessions = OrmSessionRepository()
        identities = OrmAuthIdentityRepository()
        audit = OrmAuditLogger()

        try:
            result, new_cookie = refresh_session(
                cfg=_cfg(),
                users=users,
                sessions=sessions,
                identities=identities,
                audit=audit,
                refresh_cookie_value=refresh_cookie,
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except (RefreshInvalid, RefreshRevoked):
            response = _error("refresh_invalid", "Sessão expirada", status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        response = Response({"access_token": result.access_token}, status=status.HTTP_200_OK)
        _set_refresh_cookie(response, new_cookie)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_cookie = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        meta = request_meta(request)
        audit = OrmAuditLogger()
        sessions = OrmSessionRepository()

        actor_user_id = None
        if getattr(request, "user", None) is not None:
            actor_user_id = str(getattr(request.user, "id", None) or "") or None

        from apps.accounts.application.use_cases import logout as logout_uc

        logout_uc(
            cfg=_cfg(),
            sessions=sessions,
            audit=audit,
            refresh_cookie_value=refresh_cookie,
            actor_user_id=actor_user_id,
            ip=meta["ip"],
            user_agent=meta["user_agent"],
        )

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

        users = OrmUserRepository()
        resets = OrmPasswordResetRepository()
        email_sender = DjangoEmailSender()
        audit = OrmAuditLogger()

        try:
            request_password_reset(
                cfg=_cfg(),
                users=users,
                password_resets=resets,
                email_sender=email_sender,
                audit=audit,
                email=ser.validated_data["email"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
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

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class PasswordResetVerifyView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = PasswordResetVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)
        resets = OrmPasswordResetRepository()
        audit = OrmAuditLogger()

        try:
            result = verify_password_reset_code(
                cfg=_cfg(),
                password_resets=resets,
                audit=audit,
                email=ser.validated_data["email"],
                code=ser.validated_data["code"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except PasswordResetTooManyAttempts:
            return _error("too_many_attempts", "Muitas tentativas. Solicite um novo código.", status.HTTP_429_TOO_MANY_REQUESTS)
        except (PasswordResetNotFound, PasswordResetExpired):
            return _error("invalid_code", "Código inválido ou expirado", status.HTTP_400_BAD_REQUEST)

        return Response({"reset_token": result.reset_token}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        resets = OrmPasswordResetRepository()
        passwords = OrmPasswordRepository()
        hasher = Argon2PasswordHasher()
        audit = OrmAuditLogger()

        try:
            confirm_new_password(
                cfg=_cfg(),
                password_resets=resets,
                passwords=passwords,
                password_hasher=hasher,
                audit=audit,
                email=ser.validated_data["email"],
                reset_token=ser.validated_data["reset_token"],
                new_password=ser.validated_data["new_password"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except PasswordResetNotVerified:
            return _error("not_verified", "Confirme o código antes de redefinir", status.HTTP_403_FORBIDDEN)
        except (PasswordResetGrantInvalid, PasswordResetExpired, PasswordResetNotFound):
            return _error("invalid_reset", "Sessão de reset inválida ou expirada", status.HTTP_400_BAD_REQUEST)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class EmailConfirmationRequestView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = EmailConfirmationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        users = OrmUserRepository()
        confirmations = OrmEmailConfirmationRepository()
        email_sender = DjangoEmailSender()
        audit = OrmAuditLogger()

        try:
            request_email_confirmation(
                cfg=_cfg(),
                users=users,
                confirmations=confirmations,
                email_sender=email_sender,
                audit=audit,
                email=ser.validated_data["email"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
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

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class EmailConfirmationConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = EmailConfirmationConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        users = OrmUserRepository()
        confirmations = OrmEmailConfirmationRepository()
        audit = OrmAuditLogger()

        try:
            confirm_email(
                cfg=_cfg(),
                users=users,
                confirmations=confirmations,
                audit=audit,
                token=ser.validated_data["token"],
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
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

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        key = getattr(user, "avatar_storage_key", None)
        url = avatar_url(str(key) if key else None)
        return Response(
            {
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "email_verified": bool(user.email_verified_at),
                    "status": getattr(user, "status", None),
                    "created_at": getattr(user, "created_at", None),
                    "avatar_storage_key": str(key) if key else None,
                    "avatar_url": url,
                    # Backward-friendly alias
                    "avatarStorageKey": str(key) if key else None,
                    "avatarUrl": url,
                }
            }
        )


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = PasswordChangeSerializer(data=request.data)
        if not ser.is_valid():
            fields: dict[str, str] = {}
            for key in ("current_password", "new_password", "confirm_new_password"):
                if key in ser.errors:
                    try:
                        fields[key] = str(ser.errors[key][0])
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

        user = request.user
        user_id = str(getattr(user, "id", "")) or None
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        passwords = OrmPasswordRepository()
        hasher = Argon2PasswordHasher()
        audit = OrmAuditLogger()
        meta = request_meta(request)

        stored_hash = passwords.get_password_hash(user_id=user_id)
        if not stored_hash or not hasher.verify(stored_hash, current_password):
            audit.log(
                action="accounts.password_change_failed",
                actor_user_id=user_id,
                subject_user_id=user_id,
                ip=meta["ip"],
                user_agent=meta["user_agent"],
                metadata={"reason": "wrong_current_password"},
            )
            return _field_error(
                "invalid_current_password",
                "Senha atual inválida.",
                {"current_password": "Senha atual inválida."},
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            now = now_utc()
            password_hash = hasher.hash(new_password)
            passwords.set_password(user_id=user_id, password_hash=password_hash, when=now)
            audit.log(
                action="accounts.password_changed",
                actor_user_id=user_id,
                subject_user_id=user_id,
                ip=meta["ip"],
                user_agent=meta["user_agent"],
                metadata={},
            )
        except Exception:
            return _error(
                "password_change_failed",
                "Não foi possível atualizar sua senha agora. Tente novamente.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
