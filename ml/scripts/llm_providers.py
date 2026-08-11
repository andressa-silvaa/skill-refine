"""
Shared registry of LLM endpoints for the corpus scripts.

Labelling and prose generation both need "which service, which model, which key, how many tokens",
and the answer stopped being one provider the day the daily cap on one of them became the schedule.

Fields per provider: chat-completions URL, default model, env var holding the key, and the token
allowance for a single reply. The allowance is not cosmetic: a reasoning model spends it thinking
before it writes, so a tight value returns truncated JSON with finish_reason=length and reads like a
parsing bug. On Groq the opposite holds — max_tokens is billed as reserved, so a generous value
burns real budget.

Measured against Groq's llama-3.3-70b on the same resume ids (see the handoff, section 7.2.2c):
Hugging Face and SambaNova serve the same weights and agree on 93-95% of bands; mistral-small agrees
on 58% and shifts every disagreement one level down.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GROQ = "https://api.groq.com/openai/v1/chat/completions"

PROVIDERS: dict[str, tuple[str, str, str, int]] = {
    "groq": (GROQ, "llama-3.3-70b-versatile", "AI_CLOUD_API_KEY", 140),
    "groq8b": (GROQ, "llama-3.1-8b-instant", "AI_CLOUD_API_KEY", 140),
    "huggingface": (
        "https://router.huggingface.co/v1/chat/completions",
        "meta-llama/Llama-3.3-70B-Instruct",
        "HF_TOKEN",
        140,
    ),
    "sambanova": (
        "https://api.sambanova.ai/v1/chat/completions",
        "Meta-Llama-3.3-70B-Instruct",
        "SAMBANOVA_API_KEY",
        140,
    ),
    "mistral": ("https://api.mistral.ai/v1/chat/completions", "mistral-small-latest", "MISTRAL_API_KEY", 200),
    # flash-lite, not flash-latest: this key has no free quota for the bigger model, and the lite
    # ones do not spend the allowance thinking (360 tokens/item against 799).
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "gemini-flash-lite-latest",
        "GEMINI_API_KEY",
        200,
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1/chat/completions",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "OPENROUTER_API_KEY",
        900,
    ),
    "nvidia": (
        "https://integrate.api.nvidia.com/v1/chat/completions",
        "nvidia/llama-3.3-nemotron-super-49b-v1",
        "NVIDIA_API_KEY",
        900,
    ),
}


def key_for(env_name: str) -> str:
    env_file = REPO_ROOT / "backend" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith(f"{env_name}="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise SystemExit(f"no {env_name} in backend/.env or environment")
    return value


def resolve(provider: str, model_override: str = "") -> tuple[str, str, str, int]:
    """Returns (endpoint, model, key, token allowance)."""
    if provider not in PROVIDERS:
        raise SystemExit(f"unknown provider {provider!r}; known: {', '.join(PROVIDERS)}")
    endpoint, default_model, env_name, allowance = PROVIDERS[provider]
    return endpoint, (model_override or default_model), key_for(env_name), allowance
