from __future__ import annotations

from shared.api.pagination import parse_limit_offset
from shared.api.request_user import require_authenticated_user_id


def require_user_id(request):
    return require_authenticated_user_id(request)


def invalidate_dashboard_cache_for_user(user_id: str) -> None:
    from apps.dashboard.interfaces.api.cache import invalidate_dashboard_summary_cache

    invalidate_dashboard_summary_cache(str(user_id))
