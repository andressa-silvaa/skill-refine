"""Dashboard summary cache."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache

from .summary_service import get_dashboard_summary


def get_dashboard_summary_cached(user_id: str) -> dict[str, Any]:
    ttl_seconds = int(getattr(settings, "DASHBOARD_SUMMARY_CACHE_TTL_SECONDS", 45))
    if ttl_seconds <= 0:
        return get_dashboard_summary(user_id)

    cache_key = f"dashboard:summary:{user_id}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    data = get_dashboard_summary(user_id)
    cache.set(cache_key, data, timeout=ttl_seconds)
    return data


def invalidate_dashboard_summary_cache(user_id: str) -> None:
    cache.delete(f"dashboard:summary:{user_id}")
