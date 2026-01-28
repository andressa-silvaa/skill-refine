from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, TypedDict

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.auth.drf import request_meta

from .serializers import RewriteRequestSerializer


logger = logging.getLogger(__name__)


class AIUnavailableError(Exception):
    """Raised when no AI provider can fulfil the request."""


class AIProviderError(Exception):
    """Raised when a specific provider fails."""


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Rate limit exceeded")


class RewriteResult(TypedDict):
    suggested_text: str
    provider: str
    from_cache: bool


def _hash_payload(text: str, context: str, options: dict[str, Any] | None) -> str:
    # Normalizamos para evitar perder cache por espaços ou chaves em ordem diferente
    normalized_text = (text or "").strip()
    normalized_options = options or {}
    payload = {"text": normalized_text, "context": context, "options": normalized_options}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def _rewrite_with_local(text: str, context: str, options: dict[str, Any] | None) -> str:
    mode = getattr(settings, "AI_REWRITE_MODE", "local_first")
    if mode == "cloud_only":
        raise AIProviderError("Local provider disabled by configuration.")

    base_url = getattr(settings, "AI_LOCAL_BASE_URL", "http://localhost:11434").rstrip("/")
    model = getattr(settings, "AI_LOCAL_MODEL", "llama3")
    timeout = int(getattr(settings, "AI_LOCAL_TIMEOUT_SECONDS", 10))

    language = (options or {}).get("language") or "pt-BR"
    tone = (options or {}).get("tone") or "professional"
    max_length = int((options or {}).get("maxLength") or 600)

    prompt = (
        "Você é um assistente especializado em aprimorar resumos de currículo em português do Brasil.\n\n"
        f"Contexto: {context}\n"
        f"Idioma: {language}\n"
        f"Tom desejado: {tone}\n"
        f"Tamanho máximo aproximado: {max_length} caracteres.\n\n"
        "Reescreva o texto abaixo deixando-o mais claro, profissional e conciso, "
        "adequado para a seção de resumo de currículo. Não altere o idioma e não adicione informações fictícias.\n\n"
        "Texto original:\n\"\"\"\n"
        f"{text}\n"
        "\"\"\"\n\n"
        "Texto aprimorado:"
    )

    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise AIProviderError(f"Local provider request failed: {exc}") from exc

    if resp.status_code >= 500:
        raise AIProviderError(f"Local provider returned {resp.status_code}.")

    try:
        data = resp.json()
    except ValueError as exc:
        raise AIProviderError("Local provider returned invalid JSON.") from exc

    suggestion = (
        data.get("response")
        or data.get("generated_text")
        or data.get("output")
        or ""
    )
    suggestion = str(suggestion or "").strip()
    # Alguns modelos retornam o texto entre aspas; removemos aspas externas se existirem.
    if (suggestion.startswith('"') and suggestion.endswith('"')) or (
        suggestion.startswith("'") and suggestion.endswith("'")
    ):
        suggestion = suggestion[1:-1].strip()
    if not suggestion:
        raise AIProviderError("Local provider returned empty response.")
    if len(suggestion) > max_length:
        suggestion = suggestion[: max_length].rstrip()
    return suggestion


def _rewrite_with_cloud(text: str, context: str, options: dict[str, Any] | None) -> str:
    mode = getattr(settings, "AI_REWRITE_MODE", "local_first")
    if mode == "local_only":
        raise AIProviderError("Cloud provider disabled by configuration.")

    base_url = getattr(settings, "AI_CLOUD_BASE_URL", "").rstrip("/")
    api_key = getattr(settings, "AI_CLOUD_API_KEY", "")
    model = getattr(settings, "AI_CLOUD_MODEL", "")
    timeout = int(getattr(settings, "AI_CLOUD_TIMEOUT_SECONDS", 15))

    if not base_url or not api_key or not model:
        raise AIProviderError("Cloud provider not configured.")

    language = (options or {}).get("language") or "pt-BR"
    tone = (options or {}).get("tone") or "professional"
    max_length = int((options or {}).get("maxLength") or 600)

    system_prompt = (
        "Você é um assistente especializado em aprimorar resumos de currículo em português do Brasil. "
        "Sempre responda somente com o texto reescrito, sem explicações adicionais."
    )

    user_prompt = (
        f"Contexto: {context}\n"
        f"Idioma: {language}\n"
        f"Tom desejado: {tone}\n"
        f"Tamanho máximo aproximado: {max_length} caracteres.\n\n"
        "Reescreva o texto abaixo deixando-o mais claro, profissional e conciso, "
        "adequado para a seção de resumo de currículo. Não altere o idioma e não adicione informações fictícias.\n\n"
        "Texto original:\n\"\"\"\n"
        f"{text}\n"
        "\"\"\""
    )

    try:
        resp = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_length,
                "temperature": 0.4,
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise AIProviderError(f"Cloud provider request failed: {exc}") from exc

    if resp.status_code >= 500:
        raise AIProviderError(f"Cloud provider returned {resp.status_code}.")

    try:
        data = resp.json()
    except ValueError as exc:
        raise AIProviderError("Cloud provider returned invalid JSON.") from exc

    try:
        choice = (data.get("choices") or [])[0]
        message = choice.get("message") or {}
        content = str(message.get("content") or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise AIProviderError("Cloud provider returned unexpected payload.") from exc

    if not content:
        raise AIProviderError("Cloud provider returned empty response.")
    # Remover aspas externas adicionadas por alguns modelos
    if (content.startswith('"') and content.endswith('"')) or (
        content.startswith("'") and content.endswith("'")
    ):
        content = content[1:-1].strip()
    if len(content) > max_length:
        content = content[: max_length].rstrip()
    return content


def rewrite_text_orchestrated(text: str, context: str, options: dict[str, Any] | None) -> RewriteResult:
    cache_ttl_seconds = int(getattr(settings, "AI_REWRITE_CACHE_TTL_SECONDS", 600))
    cache_key = f"ai_rewrite:{_hash_payload(text, context, options)}"

    cached: RewriteResult | None = cache.get(cache_key)  # type: ignore[assignment]
    if cached:
        # Preserve provider information but mark that it came from cache.
        cached["from_cache"] = True
        logger.info(
            "AI rewrite cache hit",
            extra={"provider": cached.get("provider"), "context": context},
        )
        return cached

    mode = getattr(settings, "AI_REWRITE_MODE", "local_first")
    errors: list[str] = []

    # local-first by default
    providers_order: list[str]
    if mode == "cloud_only":
        providers_order = ["cloud"]
    elif mode == "local_only":
        providers_order = ["local"]
    else:
        providers_order = ["local", "cloud"]

    for provider in providers_order:
        try:
            if provider == "local":
                suggestion = _rewrite_with_local(text, context, options)
            else:
                suggestion = _rewrite_with_cloud(text, context, options)
            result: RewriteResult = {
                "suggested_text": suggestion,
                "provider": provider,
                "from_cache": False,
            }
            cache.set(cache_key, result, timeout=cache_ttl_seconds)
            return result
        except AIProviderError as exc:
            errors.append(f"{provider}: {exc}")
            logger.warning(
                "AI rewrite provider failed",
                extra={
                    "provider": provider,
                    "context": context,
                    "error": str(exc),
                },
            )
            continue

    raise AIUnavailableError("; ".join(errors))


class AiRewriteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
                    "error": {
                        "code": "validation_error",
                        "message": "Dados inválidos.",
                    },
                    "fields": ser.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = ser.validated_data
        text: str = data["text"]
        context: str = data["context"]
        options: dict[str, Any] | None = data.get("options")  # type: ignore[assignment]

        try:
            result = rewrite_text_orchestrated(text, context, options)
        except AIUnavailableError as exc:
            logger.error(
                "AI rewrite unavailable after trying all providers",
                extra={
                    "context": context,
                    "options": options or {},
                    "error": str(exc),
                },
            )
            body: dict[str, Any] = {
                "error": "IA indisponível no momento. Tente novamente mais tarde.",
            }
            # Em modo DEBUG podemos expor detalhes adicionais para facilitar TCC/dev
            if getattr(settings, "DEBUG", False):
                body["details"] = str(exc)
            return Response(
                body,
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "suggestedText": result["suggested_text"],
                "provider": result["provider"],
                "fromCache": result.get("from_cache", False),
            },
            status=status.HTTP_200_OK,
        )

