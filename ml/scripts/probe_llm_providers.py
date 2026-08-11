"""
Test whether an LLM provider is usable as a labelling teacher, in one command.

Adding a provider used to mean guessing an endpoint, guessing a model id, and reading a stack
trace. Everything worth knowing is discoverable: this lists the models the key can actually reach,
sends one real rubric call, and reports cost, latency and the rate-limit headers.

Three failure modes it exists to name, all of them met for real:
  - the published model id is already retired (`llama-3.3-70b` on Cerebras, `gemini-2.0-flash`)
  - the key has no free quota for the model, which arrives as 402 or as a billing message
  - the model is a reasoning model and spends `max_tokens` thinking, so a tight allowance returns
    truncated JSON with finish_reason=length and looks like a parsing bug

CANDIDATES lists services with a free tier. Add the key to backend/.env under the name in the
table and rerun; providers without a key are skipped, not failed.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/probe_llm_providers.py
  ./backend/.venv/Scripts/python.exe ml/scripts/probe_llm_providers.py --only sambanova --models
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

USER_AGENT = "skill-refine-ml/1.0"

# name -> (base url without trailing slash, env var, signup page, preferred model ids to try)
CANDIDATES: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "groq": (
        "https://api.groq.com/openai/v1",
        "AI_CLOUD_API_KEY",
        "https://console.groq.com/keys",
        ("llama-3.3-70b-versatile",),
    ),
    "mistral": (
        "https://api.mistral.ai/v1",
        "MISTRAL_API_KEY",
        "https://console.mistral.ai/api-keys",
        ("mistral-small-latest", "open-mistral-nemo"),
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "GEMINI_API_KEY",
        "https://aistudio.google.com/apikey",
        ("gemini-flash-lite-latest", "gemini-flash-latest"),
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "https://openrouter.ai/keys",
        ("nvidia/nemotron-3-super-120b-a12b:free", "openai/gpt-oss-20b:free"),
    ),
    "sambanova": (
        "https://api.sambanova.ai/v1",
        "SAMBANOVA_API_KEY",
        "https://cloud.sambanova.ai/apis",
        ("Meta-Llama-3.3-70B-Instruct", "Llama-3.3-70B-Instruct"),
    ),
    "nvidia": (
        "https://integrate.api.nvidia.com/v1",
        "NVIDIA_API_KEY",
        "https://build.nvidia.com",
        ("meta/llama-3.3-70b-instruct", "nvidia/llama-3.3-nemotron-super-49b-v1"),
    ),
    "together": (
        "https://api.together.xyz/v1",
        "TOGETHER_API_KEY",
        "https://api.together.ai/settings/api-keys",
        ("meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ),
    "huggingface": (
        "https://router.huggingface.co/v1",
        "HF_TOKEN",
        "https://huggingface.co/settings/tokens",
        ("meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"),
    ),
    "nebius": (
        "https://api.studio.nebius.com/v1",
        "NEBIUS_API_KEY",
        "https://studio.nebius.com",
        ("meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-235B-A22B"),
    ),
    "deepinfra": (
        "https://api.deepinfra.com/v1/openai",
        "DEEPINFRA_API_KEY",
        "https://deepinfra.com/dash/api_keys",
        ("meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"),
    ),
    "dashscope": (
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "DASHSCOPE_API_KEY",
        "https://modelstudio.console.alibabacloud.com",
        ("qwen-plus", "qwen-turbo"),
    ),
}


def _env() -> dict[str, str]:
    out: dict[str, str] = {}
    path = REPO_ROOT / "backend" / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                out[key.strip()] = value.strip()
    return out


def _request(url: str, key: str, payload: dict[str, Any] | None = None) -> tuple[int, Any, dict[str, str]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            headers = {k.lower(): v for k, v in resp.headers.items()}
        return 200, body, headers
    except urllib.error.HTTPError as exc:
        detail: Any
        try:
            detail = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            detail = "<sem corpo legivel>"
        return exc.code, detail, {}
    except Exception as exc:
        return -1, f"{type(exc).__name__}: {exc}", {}


def _first_message(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if isinstance(value, str):
                return value[:180]
            if isinstance(value, dict):
                return str(value.get("message") or value)[:180]
    return str(payload)[:180]


def probe(name: str, key: str, *, list_models: bool) -> None:
    base, _env_name, _signup, preferred = CANDIDATES[name]
    print(f"\n=== {name} ===")

    status, body, _h = _request(f"{base}/models", key)
    available: list[str] = []
    if status == 200 and isinstance(body, dict):
        # Gemini lists ids as "models/<id>" while the chat endpoint wants the bare id.
        available = [str(m.get("id") or "").split("/")[-1] for m in body.get("data") or []]
        print(f"  modelos visiveis: {len(available)}")
        if list_models:
            for model_id in available[:25]:
                print(f"    {model_id}")
    else:
        print(f"  /models indisponivel (HTTP {status}): {_first_message(body)}")

    # Preferred ids go first even when the listing disagrees: several providers serve models they
    # do not list, and several list models the key cannot call.
    ordered = list(preferred) + [m for m in available if m not in preferred][:2]

    messages = [
        {"role": "system", "content": 'Responda apenas JSON: {"level":"intern|junior|mid|senior"}'},
        {
            "role": "user",
            "content": "Analista de dados, 6 anos. Coordenei tres analistas e defini o modelo dimensional.",
        },
    ]
    for model in ordered[:3]:
        payload = {
            "model": model,
            "temperature": 0.0,
            "max_tokens": 900,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        started = time.monotonic()
        status, body, headers = _request(f"{base}/chat/completions", key, payload)
        elapsed = int((time.monotonic() - started) * 1000)
        if status != 200:
            print(f"  {model}: HTTP {status} — {_first_message(body)}")
            continue
        choice = (body.get("choices") or [{}])[0]
        usage = body.get("usage") or {}
        content = str((choice.get("message") or {}).get("content") or "").strip().replace("\n", " ")
        print(f"  {model}: OK {elapsed}ms  tokens={usage.get('total_tokens')}  finish={choice.get('finish_reason')}")
        print(f"    resposta: {content[:90]}")
        limits = {k: v for k, v in headers.items() if "ratelimit" in k or "remaining" in k}
        if limits:
            print(f"    limites: {json.dumps(limits, ensure_ascii=False)}")
        return
    print("  nenhum modelo respondeu")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="probe a single provider by name")
    parser.add_argument("--models", action="store_true", help="list the model ids the key can reach")
    args = parser.parse_args()

    env = _env()
    names = [args.only] if args.only else list(CANDIDATES)
    missing: list[tuple[str, str, str]] = []
    for name in names:
        if name not in CANDIDATES:
            print(f"provedor desconhecido: {name}")
            return 1
        _base, env_name, signup, _models = CANDIDATES[name]
        key = env.get(env_name, "")
        if not key:
            missing.append((name, env_name, signup))
            continue
        probe(name, key, list_models=args.models)

    if missing:
        print("\n=== sem chave configurada (adicione em backend/.env e rode de novo) ===")
        width = max(len(n) for n, _e, _s in missing)
        for name, env_name, signup in missing:
            print(f"  {name:<{width}}  {env_name:<22} {signup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
