from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.domain.errors import (
    AccountsError,
    EmailAlreadyInUse,
    EmailNotConfirmed,
    GoogleLoginNotConfigured,
    InvalidCredentials,
    RefreshInvalid,
    RefreshRevoked,
    UserDisabled,
)
from apps.accounts.infrastructure.repositories import OrmUserRepository
from shared.api.responses import error_response as _error
from shared.auth.drf import request_meta

from .payloads import login_response_payload, me_response_payload, refresh_response_payload, register_response_payload, user_payload
from .serializers import GoogleLoginSerializer, LoginSerializer, RegisterSerializer
from .services import google_login_service, login_service, logout_service, refresh_service, register_service
from .view_helpers import clear_refresh_cookie, set_refresh_cookie


class RegisterView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

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
    throttle_scope = "auth"

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
        set_refresh_cookie(response, refresh_cookie)
        return response


class GoogleLoginView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

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
        set_refresh_cookie(response, refresh_cookie)
        return response


class RefreshView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        from django.conf import settings

        refresh_cookie = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not refresh_cookie:
            return _error("refresh_missing", "Sessão expirada", status.HTTP_401_UNAUTHORIZED)

        meta = request_meta(request)

        try:
            result, new_cookie = refresh_service(refresh_cookie, meta)
        except (RefreshInvalid, RefreshRevoked):
            response = _error("refresh_invalid", "Sessão expirada", status.HTTP_401_UNAUTHORIZED)
            clear_refresh_cookie(response)
            return response

        response = Response(refresh_response_payload(result.access_token), status=status.HTTP_200_OK)
        set_refresh_cookie(response, new_cookie)
        return response


class LogoutView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.conf import settings

        refresh_cookie = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        meta = request_meta(request)
        actor_user_id = None
        if getattr(request, "user", None) is not None:
            actor_user_id = str(getattr(request.user, "id", None) or "") or None

        logout_service(refresh_cookie, actor_user_id, meta)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(me_response_payload(request.user))
