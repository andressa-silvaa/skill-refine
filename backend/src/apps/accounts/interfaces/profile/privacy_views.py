"""Privacy: delete account view."""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.infrastructure.repositories import (
    OrmEmailConfirmationRepository,
    OrmPasswordResetRepository,
    OrmSessionRepository,
    OrmUserRepository,
)
from apps.audit.infrastructure.logger import OrmAuditLogger
from shared.api.responses import error_response as _error
from shared.auth.drf import request_meta


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
        confirmations = OrmEmailConfirmationRepository()
        password_resets = OrmPasswordResetRepository()

        from apps.accounts.application.use_cases import delete_account as delete_account_uc

        delete_account_uc(
            user_id=str(user.id),
            users=users,
            sessions=sessions,
            confirmations=confirmations,
            password_resets=password_resets,
            audit=audit,
            ip=meta["ip"],
            user_agent=meta["user_agent"],
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
