"""
Optional LLM-generated natural-language feedback about an already-decided analysis
result (seniority/quality/target-fit already computed by signals_ml/rule_policy —
this module never decides scores, only explains them in prose).

Uses the same free Groq-compatible cloud provider already configured for the
resume-rewrite feature (AI_CLOUD_BASE_URL/AI_CLOUD_API_KEY/AI_CLOUD_MODEL).
Failure-safe: any error returns None, callers must treat this as purely additive.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _enabled(settings_obj) -> bool:
    return bool(getattr(settings_obj, "ANALYSIS_LLM_FEEDBACK_ENABLED", False))


def _output_language(language: str) -> str:
    lang_key = str(language or "pt-BR").strip().replace("_", "-").lower()
    if lang_key.startswith("en"):
        return "English (US)"
    if lang_key.startswith("es"):
        return "Spanish"
    return "Brazilian Portuguese"


def generate_ai_feedback(
    *,
    resume_text: str,
    seniority_label: str,
    quality_score: int,
    target_fit_score: int | None,
    target_position: str,
    language: str = "pt-BR",
    timeout: int | None = None,
) -> str | None:
    """
    Returns a short natural-language feedback paragraph, or None if disabled/unavailable.
    The seniority_label and scores are GIVEN — the model must never contradict them.
    """
    if not _enabled(settings):
        return None

    base_url = getattr(settings, "AI_CLOUD_BASE_URL", "").rstrip("/")
    api_key = getattr(settings, "AI_CLOUD_API_KEY", "")
    model = getattr(settings, "AI_CLOUD_MODEL", "")
    if not base_url or not api_key or not model:
        return None
    timeout = timeout if timeout is not None else int(getattr(settings, "AI_CLOUD_TIMEOUT_SECONDS", 15))

    output_language = _output_language(language)
    target_line = f"\nCargo-alvo informado pelo candidato: {target_position}" if target_position else ""
    target_fit_line = f"\nAderência ao cargo-alvo (0-100, já calculada): {target_fit_score}" if target_fit_score is not None else ""

    system_prompt = (
        "Você é um consultor de carreira experiente escrevendo feedback curto e direto sobre um currículo. "
        f"Responda em {output_language}, em um único parágrafo de 2 a 4 frases, tom construtivo e específico "
        "(cite algo concreto do currículo sempre que possível). "
        "CRÍTICO: o nível de senioridade e as notas informados abaixo já foram decididos por um modelo "
        "separado a partir de sinais estruturados verificados (datas reais, contagem de experiências/realizações) "
        "— são fatos dados, não sua tarefa. NUNCA proponha, sugira ou implique um nível de senioridade ou nota "
        "diferente do informado. Sua única tarefa é comentar o PORQUÊ desse resultado e o que melhorar, "
        "usando o texto do currículo como evidência."
    )
    user_prompt = (
        f"RESULTADO JÁ DECIDIDO (não questione nem recalcule):\n"
        f"- Nível de senioridade: {seniority_label}\n"
        f"- Nota de qualidade do currículo (0-100): {quality_score}"
        f"{target_fit_line}{target_line}\n\n"
        f"CURRÍCULO:\n---\n{resume_text[:4000]}\n---\n\n"
        "Escreva o feedback agora, em um único parágrafo curto."
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
                "temperature": 0.5,
                "max_tokens": 300,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content = str((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
        return content or None
    except Exception as exc:  # noqa: BLE001 — additive feature, must never break analysis
        logger.warning("llm_feedback: generation failed (%s)", exc)
        return None
