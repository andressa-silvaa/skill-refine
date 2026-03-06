from __future__ import annotations

import logging
import time

from django.conf import settings
from django.db import connection

logger = logging.getLogger("api.metrics")


class ApiMetricsMiddleware:
    """
    Minimal API timing/query instrumentation.
    - duration_ms for every request
    - query_count only when DEBUG=True
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        metrics_enabled = bool(getattr(settings, "API_METRICS_ENABLED", False))
        started_at = time.perf_counter()
        before_queries = len(getattr(connection, "queries", [])) if settings.DEBUG else 0

        response = self.get_response(request)

        if metrics_enabled:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            query_count = None
            if settings.DEBUG:
                after_queries = len(getattr(connection, "queries", []))
                query_count = max(0, after_queries - before_queries)

            payload = {
                "path": request.path,
                "method": request.method,
                "status_code": getattr(response, "status_code", None),
                "duration_ms": duration_ms,
            }
            if query_count is not None:
                payload["query_count"] = query_count
            logger.info("api_request", extra=payload)
        return response
