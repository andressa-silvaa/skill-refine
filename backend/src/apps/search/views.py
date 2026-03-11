"""Global search API view."""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.responses import error_response as _error

from .services import global_search


def _user_id(request):
    uid = getattr(request.user, "id", None)
    if not uid:
        return None, _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)
    return str(uid), None


class GlobalSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id, err = _user_id(request)
        if err:
            return err
        q = (request.query_params.get("q") or "").strip()
        types_raw = (request.query_params.get("types") or "").strip()
        types = [t.strip() for t in types_raw.split(",") if t.strip()] if types_raw else None
        try:
            limit = min(max(int(request.query_params.get("limit", 20)), 1), 50)
        except (TypeError, ValueError):
            limit = 20
        items = global_search(user_id, q, types=types, limit=limit)
        return Response({"items": items}, status=status.HTTP_200_OK)
