from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.parsers import JSONParser
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.infrastructure.avatar_storage import save_user_avatar
from apps.accounts.infrastructure.cloudinary_avatar import avatar_url
from apps.accounts.infrastructure.email_sender import DjangoEmailSender
from apps.accounts.infrastructure.models import UserPreferences
from apps.accounts.infrastructure.repositories import OrmSessionRepository, OrmUserRepository
from apps.audit.infrastructure.logger import OrmAuditLogger
from shared.auth.drf import request_meta
from shared.auth.jwt import now_utc

from .serializers import (
    ALLOWED_AVATAR_CONTENT_TYPES,
    AvatarUploadSerializer,
    PreferencesSerializer,
    ProfileUpdateSerializer,
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


def _avatar_url(public_id: str | None) -> str | None:
    return avatar_url(public_id)


class AvatarUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        ser = AvatarUploadSerializer(data=request.data)
        if not ser.is_valid():
            msg = "Arquivo inválido."
            try:
                msg = str(ser.errors.get("avatar", ["Arquivo inválido."])[0])
            except Exception:
                pass
            return _error("invalid_avatar", msg, status.HTTP_400_BAD_REQUEST)

        f = ser.validated_data["avatar"]
        content_type = (getattr(f, "content_type", "") or "").strip().lower()
        ext = ALLOWED_AVATAR_CONTENT_TYPES.get(content_type)
        if not ext:
            return _error("invalid_avatar", "Formato inválido. Envie JPG, PNG ou WEBP.", status.HTTP_400_BAD_REQUEST)

        user = request.user
        user_id = str(getattr(user, "id", ""))
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        try:
            public_id = save_user_avatar(user_id=user_id, content=f, ext=ext)
        except Exception:
            return _error("upload_failed", "Não foi possível enviar a imagem agora.", status.HTTP_503_SERVICE_UNAVAILABLE)

        user.avatar_storage_key = public_id
        user.save(update_fields=["avatar_storage_key", "updated_at"])

        url = _avatar_url(public_id)

        return Response(
            {
                "avatar_storage_key": public_id,
                "avatar_url": url,
                # Backward-friendly aliases (frontend may use camelCase)
                "avatarStorageKey": public_id,
                "avatarUrl": url,
            },
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def patch(self, request):
        ser = ProfileUpdateSerializer(data=request.data, partial=True)
        if not ser.is_valid():
            fields: dict[str, str] = {}
            if "full_name" in ser.errors:
                try:
                    fields["full_name"] = str(ser.errors["full_name"][0])
                except Exception:
                    fields["full_name"] = "Valor inválido."
            return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not getattr(user, "id", None):
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        updated = False
        full_name = ser.validated_data.get("full_name", None)
        if full_name is not None:
            user.full_name = full_name
            updated = True

        if updated:
            user.save(update_fields=["full_name", "updated_at"])

        key = getattr(user, "avatar_storage_key", None)
        url = avatar_url(str(key) if key else None)
        created_at = getattr(user, "created_at", None)

        return Response(
            {
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "email_verified": bool(getattr(user, "email_verified_at", None)),
                    "status": getattr(user, "status", None),
                    "created_at": created_at,
                    "avatar_storage_key": str(key) if key else None,
                    "avatar_url": url,
                    "avatarUrl": url,
                    "avatarStorageKey": str(key) if key else None,
                }
            },
            status=status.HTTP_200_OK,
        )


class PreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request):
        user = request.user
        if not getattr(user, "id", None):
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        prefs, _ = UserPreferences.objects.get_or_create(user_id=user.id)
        return Response(
            {
                "email_notifications_enabled": bool(prefs.email_notifications_enabled),
                "emailNotificationsEnabled": bool(prefs.email_notifications_enabled),
                "language": str(getattr(prefs, "language", "") or ""),
                "theme": str(getattr(prefs, "theme", "") or ""),
                "accent_color": str(getattr(prefs, "accent_color", "") or ""),
                "accentColor": str(getattr(prefs, "accent_color", "") or ""),
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        user = request.user
        if not getattr(user, "id", None):
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        ser = PreferencesSerializer(data=request.data, partial=True)
        if not ser.is_valid():
            fields: dict[str, str] = {}
            for key in ("email_notifications_enabled", "language", "theme", "accent_color"):
                if key in ser.errors:
                    try:
                        fields[key] = str(ser.errors[key][0])
                    except Exception:
                        fields[key] = "Valor inválido."
            return _field_error("validation_error", "Dados inválidos.", fields, status.HTTP_400_BAD_REQUEST)

        prefs, _ = UserPreferences.objects.get_or_create(user_id=user.id)
        updated = False
        if "email_notifications_enabled" in ser.validated_data:
            prefs.email_notifications_enabled = bool(ser.validated_data["email_notifications_enabled"])
            updated = True
        if "language" in ser.validated_data:
            prefs.language = str(ser.validated_data["language"])
            updated = True
        if "theme" in ser.validated_data:
            prefs.theme = str(ser.validated_data["theme"])
            updated = True
        if "accent_color" in ser.validated_data:
            prefs.accent_color = str(ser.validated_data["accent_color"])
            updated = True
        if updated:
            prefs.updated_at = now_utc()
            update_fields = ["updated_at"]
            if "email_notifications_enabled" in ser.validated_data:
                update_fields.append("email_notifications_enabled")
            if "language" in ser.validated_data:
                update_fields.append("language")
            if "theme" in ser.validated_data:
                update_fields.append("theme")
            if "accent_color" in ser.validated_data:
                update_fields.append("accent_color")
            prefs.save(update_fields=update_fields)

        return Response(
            {
                "email_notifications_enabled": bool(prefs.email_notifications_enabled),
                "emailNotificationsEnabled": bool(prefs.email_notifications_enabled),
                "language": str(getattr(prefs, "language", "") or ""),
                "theme": str(getattr(prefs, "theme", "") or ""),
                "accent_color": str(getattr(prefs, "accent_color", "") or ""),
                "accentColor": str(getattr(prefs, "accent_color", "") or ""),
            },
            status=status.HTTP_200_OK,
        )


class PrivacyExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not getattr(user, "id", None):
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        to_email = str(getattr(user, "email", "") or "").strip()
        if not to_email:
            return _error("validation_error", "E-mail do usuário não encontrado.", status.HTTP_400_BAD_REQUEST)

        meta = request_meta(request)
        audit = OrmAuditLogger()
        email_sender = DjangoEmailSender()

        from apps.accounts.application.use_cases import request_data_export as request_data_export_uc
        from apps.accounts.domain.errors import EmailSendFailed, EmailServiceNotConfigured

        try:
            result = request_data_export_uc(
                user_id=str(user.id),
                to_email=to_email,
                email_sender=email_sender,
                audit=audit,
                ip=meta["ip"],
                user_agent=meta["user_agent"],
            )
        except EmailServiceNotConfigured:
            return _error(
                "email_service_not_configured",
                "Serviço de e-mail não configurado.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except EmailSendFailed:
            return _error(
                "email_send_failed",
                "Não foi possível enviar o e-mail agora.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(result, status=status.HTTP_200_OK)


class PrivacyDeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not getattr(user, "id", None):
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        meta = request_meta(request)
        audit = OrmAuditLogger()
        users = OrmUserRepository()
        sessions = OrmSessionRepository()

        from apps.accounts.application.use_cases import delete_account as delete_account_uc

        delete_account_uc(
            user_id=str(user.id),
            users=users,
            sessions=sessions,
            audit=audit,
            ip=meta["ip"],
            user_agent=meta["user_agent"],
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

