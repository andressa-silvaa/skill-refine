"""Cloud AI provider for resume text rewrite."""
from __future__ import annotations

from typing import Any

import requests
from django.conf import settings


class AIProviderError(Exception):
    """Raised when a specific provider fails."""


def rewrite_with_cloud(text: str, context: str, options: dict[str, Any] | None) -> str:
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
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
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
    except Exception as exc:
        raise AIProviderError("Cloud provider returned unexpected payload.") from exc

    if not content:
        raise AIProviderError("Cloud provider returned empty response.")
    if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")):
        content = content[1:-1].strip()
    if len(content) > max_length:
        content = content[:max_length].rstrip()
    return content
