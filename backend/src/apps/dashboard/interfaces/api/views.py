from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.request_user import require_authenticated_user_id

from .cache import get_dashboard_summary_cached
from .payloads import dashboard_payload


class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id, auth_error = require_authenticated_user_id(request)
        if auth_error:
            return auth_error

        data = get_dashboard_summary_cached(user_id)
        return Response(dashboard_payload(data), status=status.HTTP_200_OK)

