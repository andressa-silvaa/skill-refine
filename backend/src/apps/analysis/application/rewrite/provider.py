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

    lang_key = str(language).strip().replace("_", "-").lower()
    if lang_key.startswith("en"):
        output_language = "English (US)"
    elif lang_key.startswith("es"):
        output_language = "Spanish"
    else:
        output_language = "Brazilian Portuguese"

    system_prompt = (
        "You are an expert resume coach. The user will ask you to rewrite text for their resume. "
        f"You must reply with ONLY the rewritten text in {output_language}, with no title, no quotes, "
        "and no explanation before or after."
    )
    user_prompt = (
        f"Context: {context}\n"
        f"Output language (BCP-47): {language} — write the entire answer in {output_language}.\n"
        f"Tone: {tone}\n"
        f"Approximate maximum length: {max_length} characters.\n\n"
        "Rewrite the following for a professional resume summary section: make it clearer, concise, and polished. "
        "Keep all factual content; do not invent employers, dates, degrees, or skills.\n\n"
        "Original text:\n\"\"\"\n"
        f"{text}\n"
        "\"\"\"\n\n"
        f"CRITICAL: Respond with ONLY the rewritten summary. The full text must be in {output_language}. "
        "If the original is in a different language, translate it into that output language while rewriting—"
        "do not leave the answer in the source language."
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
