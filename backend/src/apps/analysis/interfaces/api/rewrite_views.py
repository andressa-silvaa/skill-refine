"""AI rewrite HTTP view."""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.application.rewrite.service import (
    AIUnavailableError,
    RateLimitExceeded,
    rewrite_text_orchestrated,
)
from shared.auth.drf import request_meta

from .serializers import RewriteRequestSerializer

logger = logging.getLogger(__name__)


def _language_from_accept_language(header: str | None) -> str | None:
    if not header or not str(header).strip():
        return None
    first = str(header).split(",")[0].strip().split(";")[0].strip().replace("_", "-")
    return first or None


def _merge_rewrite_options(request, options: dict[str, Any] | None) -> dict[str, Any]:
    """Ensure language is set: body wins, else Accept-Language (browser / client sends both)."""
    merged: dict[str, Any] = dict(options or {})
    lang = merged.get("language")
    if isinstance(lang, str) and lang.strip():
        return merged
    from_header = _language_from_accept_language(request.headers.get("Accept-Language"))
    if from_header:
        merged["language"] = from_header
    return merged


def _rate_limit(request, limit: int = 10, window_seconds: int = 60) -> None:
    meta = request_meta(request)
    ip = meta.get("ip") or "unknown"
    user = getattr(request.user, "id", None)
    actor = str(user or ip or "anonymous")
    key = f"ai_rewrite_rl:{actor}"

    current = cache.get(key, 0)
    if current >= limit:
        raise RateLimitExceeded(window_seconds)
    cache.set(key, int(current) + 1, timeout=window_seconds)


class AiRewriteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "analysis"

    def post(self, request):
        try:
            _rate_limit(request)
        except RateLimitExceeded as exc:
            return Response(
                {"error": "Muitas solicitações de IA. Tente novamente em alguns instantes."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(exc.retry_after_seconds)},
            )

        ser = RewriteRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {
                    "error": {"code": "validation_error", "message": "Dados inválidos."},
                    "fields": ser.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = ser.validated_data
        text: str = data["text"]
        context: str = data["context"]
        options = _merge_rewrite_options(request, data.get("options"))

        try:
            result = rewrite_text_orchestrated(text, context, options)
        except AIUnavailableError as exc:
            logger.error(
                "AI rewrite unavailable after trying all providers",
                extra={"context": context, "options": options or {}, "error": str(exc)},
            )
            body: dict[str, Any] = {"error": "IA indisponível no momento. Tente novamente mais tarde."}
            if getattr(settings, "DEBUG", False):
                body["details"] = str(exc)
            return Response(body, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(
            {
                "suggestedText": result["suggested_text"],
                "provider": result["provider"],
                "fromCache": result.get("from_cache", False),
            },
            status=status.HTTP_200_OK,
        )
