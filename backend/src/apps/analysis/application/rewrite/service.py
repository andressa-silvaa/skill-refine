"""Rewrite orchestration: cache, rate limit helpers, service."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, TypedDict

from django.conf import settings
from django.core.cache import cache

from .provider import AIProviderError, rewrite_with_cloud

logger = logging.getLogger(__name__)


class AIUnavailableError(Exception):
    """Raised when no AI provider can fulfil the request."""


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Rate limit exceeded")


class RewriteResult(TypedDict):
    suggested_text: str
    provider: str
    from_cache: bool


def _hash_payload(text: str, context: str, options: dict[str, Any] | None) -> str:
    payload = {"text": (text or "").strip(), "context": context, "options": options or {}}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def rewrite_text_orchestrated(text: str, context: str, options: dict[str, Any] | None) -> RewriteResult:
    cache_ttl_seconds = int(getattr(settings, "AI_REWRITE_CACHE_TTL_SECONDS", 600))
    cache_key = f"ai_rewrite:{_hash_payload(text, context, options)}"

    cached: RewriteResult | None = cache.get(cache_key)
    if cached:
        cached["from_cache"] = True
        logger.info("AI rewrite cache hit", extra={"provider": "cloud", "context": context})
        return cached

    logger.info("AI rewrite provider=cloud", extra={"provider": "cloud", "context": context})
    try:
        suggestion = rewrite_with_cloud(text, context, options)
    except AIProviderError as exc:
        logger.warning(
            "AI rewrite provider failed (provider=cloud): %s",
            exc,
            extra={"provider": "cloud", "context": context, "error": str(exc)},
        )
        raise AIUnavailableError(str(exc)) from exc

    result: RewriteResult = {"suggested_text": suggestion, "provider": "cloud", "from_cache": False}
    cache.set(cache_key, result, timeout=cache_ttl_seconds)
    return result
