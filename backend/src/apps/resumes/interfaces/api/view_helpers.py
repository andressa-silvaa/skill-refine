from __future__ import annotations

from rest_framework import status

from shared.api.responses import error_response as _error


def require_user_id(request):
    user_id = getattr(request.user, "id", None)
    if not user_id:
        return None, _error("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)
    return user_id, None


def parse_limit_offset(
    *,
    limit_param: str | None,
    offset_param: str | None,
    limit_default: int,
    offset_default: int,
    limit_min: int,
    limit_max: int,
):
    try:
        limit = int(limit_param) if limit_param not in (None, "") else limit_default
    except ValueError:
        limit = None
    try:
        offset = int(offset_param) if offset_param not in (None, "") else offset_default
    except ValueError:
        offset = -1

    if limit is None or limit < limit_min or limit > limit_max:
        return None, _error(
            "validation_error",
            f"Parâmetro limit deve ser um número entre {limit_min} e {limit_max}.",
            status.HTTP_400_BAD_REQUEST,
        )
    if offset < 0:
        return None, _error(
            "validation_error",
            "Parâmetro offset deve ser um número maior ou igual a 0.",
            status.HTTP_400_BAD_REQUEST,
        )

    return (limit, offset), None


def invalidate_dashboard_cache_for_user(user_id: str) -> None:
    from apps.dashboard.interfaces.api.services import invalidate_dashboard_summary_cache

    invalidate_dashboard_summary_cache(str(user_id))
