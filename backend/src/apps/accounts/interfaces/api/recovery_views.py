from __future__ import annotations

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.domain.errors import (
    AccountsError,
    EmailAlreadyConfirmed,
    EmailConfirmationExpired,
    EmailConfirmationInvalid,
    EmailConfirmationTokenConsumed,
    EmailNotRegistered,
    EmailSendFailed,
    EmailServiceNotConfigured,
    PasswordResetExpired,
    PasswordResetGrantInvalid,
    PasswordResetNotFound,
    PasswordResetNotVerified,
    PasswordResetTooManyAttempts,
    TooManyRequests,
)
from shared.api.responses import error_response as _error
from shared.api.responses import extract_error_message
from shared.api.responses import field_error_response as _field_error
from shared.auth.drf import request_meta

from .payloads import password_reset_verify_payload, status_ok_payload
from .serializers import (
    EmailConfirmationConfirmSerializer,
    EmailConfirmationRequestSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
)
from .services import (
    WrongCurrentPassword,
    email_confirmation_confirm_service,
    email_confirmation_request_service,
    password_change_service,
    password_reset_confirm_service,
    password_reset_request_service,
    password_reset_verify_service,
)

logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

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
            return _error(
                "password_reset_request_failed",
                "Não foi possível processar sua solicitação.",
                status.HTTP_400_BAD_REQUEST,
            )

        return Response(status_ok_payload(), status=status.HTTP_200_OK)


class PasswordResetVerifyView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

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
    throttle_scope = "auth"

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
    throttle_scope = "auth"

    def post(self, request):
        ser = EmailConfirmationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            result = email_confirmation_request_service(ser.validated_data["email"], meta)
        except EmailNotRegistered:
            return _error(
                "email_not_registered",
                "Não existe nenhum usuário cadastrado com este e-mail.",
                status.HTTP_404_NOT_FOUND,
            )
        except TooManyRequests as exc:
            ra = getattr(exc, "retry_after_seconds", None)
            hdr = {"Retry-After": str(ra)} if isinstance(ra, int) and ra > 0 else None
            return _error(
                "too_many_requests",
                "Aguarde um pouco antes de reenviar a confirmação.",
                status.HTTP_429_TOO_MANY_REQUESTS,
                headers=hdr,
            )
        except EmailServiceNotConfigured:
            logger.warning(
                "email_confirmation_request: 503 SMTP not configured (see email_smtp_not_configured in logs)"
            )
            return _error(
                "email_service_unavailable",
                "Não foi possível enviar o e-mail agora. Tente novamente mais tarde.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except EmailSendFailed:
            logger.warning(
                "email_confirmation_request: 503 send failed (see email_smtp_send_failed in logs for SMTP error)"
            )
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
            logger.exception("email_confirmation_request: 503 unexpected error")
            return _error(
                "email_confirmation_request_failed",
                "Serviço temporariamente indisponível. Tente novamente mais tarde.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payload = {**status_ok_payload(), **result}
        return Response(payload, status=status.HTTP_200_OK)


class EmailConfirmationConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        ser = EmailConfirmationConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        meta = request_meta(request)

        try:
            email_confirmation_confirm_service(ser.validated_data["token"], meta)
        except EmailAlreadyConfirmed:
            payload = {**status_ok_payload(), "already_confirmed": True}
            return Response(payload, status=status.HTTP_200_OK)
        except EmailConfirmationExpired:
            return _error("token_expired", "Token expirado. Solicite um novo e-mail.", status.HTTP_400_BAD_REQUEST)
        except EmailConfirmationTokenConsumed:
            return _error(
                "token_consumed",
                "Este link não é mais válido. Solicite um novo e-mail.",
                status.HTTP_400_BAD_REQUEST,
            )
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
