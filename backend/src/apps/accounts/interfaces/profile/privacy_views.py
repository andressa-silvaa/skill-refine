"""Privacy export and delete account views."""
from __future__ import annotations

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.infrastructure.email_sender import DjangoEmailSender
from apps.accounts.infrastructure.repositories import OrmSessionRepository, OrmUserRepository
from apps.audit.infrastructure.logger import OrmAuditLogger
from shared.api.responses import error_response as _error
from shared.auth.drf import request_meta

from .services import build_user_data_export, export_filename_for_today


class PrivacyExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        user_id = str(getattr(user, "id", "") or "")
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        export_data = build_user_data_export(user_id)
        if export_data is None:
            return _error("not_found", "Usuário não encontrado.", status.HTTP_404_NOT_FOUND)

        meta = request_meta(request)
        OrmAuditLogger().log(
            action="accounts.data_export_downloaded",
            actor_user_id=user_id,
            subject_user_id=user_id,
            ip=meta.get("ip"),
            user_agent=meta.get("user_agent"),
            metadata={},
        )

        body = json.dumps(export_data, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder)
        response = HttpResponse(body.encode("utf-8"), content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{export_filename_for_today()}"'
        return response

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
