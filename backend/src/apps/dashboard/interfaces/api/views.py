from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.responses import error_response as _error

from .payloads import dashboard_payload
from .services import get_dashboard_summary


class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = getattr(request.user, "id", None)
        if not user_id:
            return _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)

        data = get_dashboard_summary(str(user_id))
        return Response(dashboard_payload(data), status=status.HTTP_200_OK)

