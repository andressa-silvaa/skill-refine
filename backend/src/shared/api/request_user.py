from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response

from shared.api.responses import error_response


def require_authenticated_user_id(request) -> tuple[str | None, Response | None]:
    user_id = getattr(request.user, "id", None)
    if not user_id:
        return None, error_response("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)
    return str(user_id), None
