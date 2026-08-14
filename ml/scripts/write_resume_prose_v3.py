"""
Phase 1b of the v3 synthetic corpus: turn structural specs into natural resume prose via Groq.

Each spec declares occupation, language, scope level and exact counts; the LLM only writes the
words. Structure stays owned by phase 1a so the numeric distribution remains controlled — that
distribution is what broke v2 (summary_char_count 30-61 chars in training vs 183-360 real).

Two deliberate anti-shortcut rules in the prompt:
  - the seniority band is never named to the model; it receives a scope level
    (assist | execute | own | lead) and writes language consistent with it.
  - band keywords (estagiário/júnior/pleno/sênior and equivalents) are forbidden in the prose
    unless the spec's may_state_seniority flag is set (~20%), so a text classifier cannot
    read the answer off a literal keyword yet still sees the real-world phrasing sometimes.

Rate limits (free tier, measured): llama-3.1-8b-instant = 14400 req/day, 6000 tokens/min.
TPM is the binding constraint, so concurrency is low and pacing is driven by response headers.

Output: ml/data/raw/resumes_v3/prose.jsonl  (resumable — existing ids are skipped)

Usage (from repo root):
  python ml/scripts/write_resume_prose_v3.py
  python ml/scripts/write_resume_prose_v3.py --limit 5 --model llama-3.3-70b-versatile
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ML_ROOT = Path(__file__).resolve().parents[1]
SPECS_PATH = ML_ROOT / "data" / "raw" / "resumes_v3" / "specs.jsonl"
OUT_PATH = ML_ROOT / "data" / "raw" / "resumes_v3" / "prose.jsonl"

LANG_NAME = {
    "pt-BR": "Brazilian Portuguese",
    "en-US": "American English",
    "es-ES": "European Spanish",
}

BANNED_TERMS = {
    "pt-BR": ["estagiário", "estagiaria", "júnior", "junior", "pleno", "sênior", "senior", "trainee"],
    "en-US": ["intern", "internship", "junior", "entry-level", "mid-level", "senior", "trainee"],
    "es-ES": ["becario", "prácticas", "junior", "semi-senior", "senior", "pasante"],
}

USER_AGENT = "skill-refine-ml/1.0"

# A ~900 token completion answers in 2-5s. A call still open after this is hung, and retrying is
# far cheaper than waiting: at timeout=90 with 5 retries a single stuck socket blocked a worker
# for minutes and dragged sustained throughput from 5.6/min down to 2.6/min.
REQUEST_TIMEOUT = 20
# A socket that produced nothing in 20s almost never recovers on a fifth attempt, and each extra
# attempt holds a worker. Capping retries here bounds the worst case for one spec at ~2 min
# instead of ~6, which is what kept dragging sustained throughput down over a long run.
REQUEST_ATTEMPTS = 2
RATE_LIMIT_ATTEMPTS = 6
BACKOFF_CAP = 20.0

YEARS_CLAIM = re.compile(
    r"\b(?:mais\s+de\s+|m[aá]s\s+de\s+|over\s+|more\s+than\s+)?\d{1,2}\s*\+?\s*"
    r"(anos|a[nñ]os|years|yrs)\b",
    re.I,
)

SCOPE_BRIEF = {
    "assist": "supervised support work, nothing decided alone",
    "execute": "assigned work delivered with limited autonomy",
    "own": "full responsibility for one workstream and its decisions",
    "lead": "accountable for outcomes reached through other people",
}

# Achievement-with-metric phrasing was originally requested for every band, which made
# low-band resumes read two levels above their target ("Aumentei a participacao em 30%" for a
# 5-month intern). Style is therefore per scope: only own/lead may claim outcomes.
SCOPE_STYLE = {
    "assist": (
        "Use verbs of supervised support (helped, followed, observed, prepared, recorded)."
        " This person must NOT be credited with any improvement, saving or gain: no percentage"
        " gains, no efficiency claims, no decisions of their own. At most one bullet may carry a"
        " number, and only as the volume of work handled."
    ),
    "execute": (
        "Use verbs of completing assigned work (carried out, processed, produced, maintained)."
        " Numbers may describe volume or turnaround, never strategy. No bullet may claim this"
        " person decided direction or led anyone."
    ),
    "own": (
        "Show this person deciding how the work was done and answering for its results, using"
        " verbs of ownership (defined, chose, restructured, took responsibility for)."
    ),
    "lead": (
        "Show direction-setting and results obtained through other people. At least half the"
        " bullets must mention people, teams, suppliers or cross-area coordination, and the reach"
        " should be an area rather than a single task."
    ),
}

# Quality is orthogonal to scope: scope says WHAT the person was responsible for, quality says how
# well the resume communicates it. Keeping them independent is what lets a quality model be trained
# on the same corpus without it learning to read seniority off its own target.
QUALITY_STYLE = {
    "poor": (
        "Write this resume BADLY, the way most real resumes are written: list duties instead of"
        " outcomes, stay generic, use filler verbs (participated in, helped with, was responsible"
        " for activities), name no tools, no volumes and no results. The summary must be empty"
        " platitudes about being dedicated and hardworking."
    ),
    "fair": (
        "Write this resume at an average level: some bullets are specific and one or two carry a"
        " concrete figure, but others stay generic and duty-shaped. The summary is serviceable"
        " but unremarkable."
    ),
    "good": (
        "Write this resume WELL: every bullet is concrete and specific to the occupation, names"
        " real tools, materials or processes, and gives a volume, timeframe or result wherever the"
        " responsibility level permits it. The summary states what the person actually does."
    ),
}

_lock = threading.Lock()
_pace = threading.Semaphore(1)

_gate_lock = threading.Lock()
_next_slot = [0.0]
_delay = [6.0]
_backoff_until = [0.0]
_ENDPOINT = [""]


def _wait_turn() -> None:
    """
    Space calls by a fixed interval instead of modelling the token bucket.

    A token-window pacer was tried first and stalled: every 429 penalty and every retry added
    another reservation, saturating the window so each slot waited a full minute. A flat
    interval plus 429 backoff is predictable and keeps throughput steady.
    """
    while True:
        with _gate_lock:
            now = time.monotonic()
            earliest = max(_next_slot[0], _backoff_until[0])
            if now >= earliest:
                _next_slot[0] = now + _delay[0]
                return
            wait = earliest - now
        time.sleep(min(wait, 20.0))


def _back_off(seconds: float) -> None:
    """
    Pause the shared gate briefly after a 429.

    The pause is global, so honouring a full Retry-After froze every worker at once and was the
    real cause of throughput decaying over a long run. The token window refills continuously, so
    a short pause is enough; if the limit still bites, the next 429 adds another one.
    """
    with _gate_lock:
        capped = max(2.0, min(BACKOFF_CAP, seconds))
        _backoff_until[0] = max(_backoff_until[0], time.monotonic() + capped)


def _estimate_tokens(spec: dict[str, Any]) -> int:
    """
    Size max_tokens to what the reply actually needs, not to a comfortable ceiling.

    Groq charges max_tokens as RESERVED against the per-minute budget, so an over-generous value
    is paid for whether or not it is used. The first formula reserved ~1400 for replies consuming
    ~620, which with the prompt put each call near 2300 tokens and pinned throughput at the
    observed 2.6/min. A bullet is capped at 22 words, i.e. ~30 tokens plus JSON punctuation.
    """
    bullets = sum(int(e["n_bullets"]) for e in spec["experiences"])
    return 230 + 42 * bullets + 45 * int(spec["summary_sentences"]) + 7 * int(spec["n_skills"])


def _api_key() -> str:
    env = ML_ROOT.parent / "backend" / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("AI_CLOUD_API_KEY="):
                v = line.split("=", 1)[1].strip()
                if v:
                    return v
    v = os.environ.get("AI_CLOUD_API_KEY", "").strip()
    if not v:
        raise SystemExit("no AI_CLOUD_API_KEY in backend/.env or environment")
    return v


def build_prompt(spec: dict[str, Any]) -> str:
    lang = spec["language"]
    occ = spec["occupation"]["label"]
    banned = ", ".join(BANNED_TERMS[lang])
    want_sents = int(spec["summary_sentences"])
    summary_ask = (
        f"a professional summary made of exactly {want_sents} separate sentences"
        " (each sentence 12 to 25 words long, returned as separate array items),"
        if want_sents
        else "no summary at all (return an empty summary_sentences array),"
    )
    lines = [
        f"You write realistic resume content in {LANG_NAME[lang]}.",
        f"Occupation: {occ}.",
        "",
        "Write, for each job below, the requested number of achievement bullets, plus",
        summary_ask,
        f"and {spec['n_skills']} short skill names.",
        "",
        "Jobs (most recent first):",
    ]
    for i, e in enumerate(spec["experiences"], 1):
        period = f"{e['months']} months"
        lines.append(
            f"  {i}. {e['position']} at {e['company']} — {period};"
            f" write exactly {e['n_bullets']} bullet(s);"
            f" responsibility level: {SCOPE_BRIEF[e['scope_level']]}."
            f" Style for this job: {SCOPE_STYLE[e['scope_level']]}"
        )
    lines += [
        "",
        "Rules:",
        f"- Everything must be written in {LANG_NAME[lang]}.",
        f"- Writing quality for the WHOLE resume: {QUALITY_STYLE[spec.get('quality_target', 'good')]}",
        "- Each bullet stays short (max 22 words).",
        "- Writing quality is independent of the responsibility levels below: a badly written"
        " resume still describes the same scope, it just describes it vaguely.",
        "- Follow the per-job style above exactly; it is what distinguishes the jobs from one"
        " another and must not be flattened into one uniform tone.",
        "- Bullet wording must reflect the stated responsibility level through verbs and scope,"
        " never by naming a career level.",
        "- Never state a number of years of experience anywhere (no \"5 years\", \"5 anos\","
        " \"5 años\"). The dates already carry tenure and any claim would contradict them.",
        "- Never copy or paraphrase the responsibility-level wording given above into the text."
        " Express it only through which verbs you choose and the scale of what is described.",
        "- Every bullet in the whole resume must be distinct: do not repeat a sentence structure,"
        " a metric, or an achievement across jobs, and do not reuse the same opening verb twice.",
    ]
    if spec.get("wants_leadership_language"):
        lines.append("- At least one bullet must show coordinating or guiding other people.")
    if not spec.get("may_state_seniority"):
        lines.append(f"- Never use these words anywhere: {banned}.")
    lines += [
        "- Do not invent the person's name, contact details, school or employer names.",
        "- Never repeat a job title verbatim in the summary or in a bullet; describe the work"
        " instead. Real resumes do not restate the title they already list.",
        "- The summary must match the responsibility level of job 1 above, in the same register:"
        " a supervised profile does not describe itself as owning results, and a profile"
        " accountable through others does not describe itself as assisting.",
        "",
        'Reply with JSON only: {"summary_sentences": ["...", "..."],'
        ' "experiences": [{"bullets": ["..."]}], "skills": ["..."]}',
        f"summary_sentences must have exactly {spec['summary_sentences']} items.",
        "The experiences array must have exactly"
        f" {len(spec['experiences'])} items, in the same order.",
    ]
    return "\n".join(lines)


def call_groq(
    key: str, model: str, prompt: str, max_tokens: int, endpoint: str = ""
) -> tuple[dict[str, Any] | None, float]:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.8,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint or "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    last_error = ""
    rate_limit_budget = RATE_LIMIT_ATTEMPTS
    hard_budget = REQUEST_ATTEMPTS
    attempt = 0
    while rate_limit_budget > 0 and hard_budget > 0:
        attempt += 1
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                pause = 0.0
                content = payload["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    last_error = "json not an object"
                    hard_budget -= 1
                    continue
                return parsed, pause
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                last_error = "429 rate limited"
                rate_limit_budget -= 1
                wait = _parse_duration(exc.headers.get("retry-after") or "10s")
                _back_off(wait)
                time.sleep(max(2.0, min(BACKOFF_CAP, wait)))
                continue
            last_error = f"HTTP {exc.code}"
            hard_budget -= 1
            time.sleep(2 + attempt * 2)
        except (OSError, json.JSONDecodeError, KeyError, IndexError) as exc:
            last_error = type(exc).__name__
            hard_budget -= 1
            time.sleep(2 + attempt * 2)
    with _lock:
        print(f"  api failed ({last_error})", flush=True)
    return None, 0.0


def _parse_duration(text: str) -> float:
    t = str(text).strip()
    if not t:
        return 0.0
    m = re.match(r"^(?:(\d+(?:\.\d+)?)m)?(\d+(?:\.\d+)?)?s?$", t)
    try:
        if t.endswith("ms"):
            return float(t[:-2]) / 1000.0
        if m:
            mins = float(m.group(1) or 0)
            secs = float(m.group(2) or 0)
            return mins * 60 + secs
        return float(t)
    except ValueError:
        return 5.0


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _summary_text(sentences: Any) -> str:
    parts = []
    for s in sentences or []:
        t = _clean(s)
        if t:
            parts.append(t if t[-1] in ".!?" else f"{t}.")
    return " ".join(parts)


def normalize(spec: dict[str, Any], out: Any) -> Any:
    """Trim over-long replies instead of rejecting them: the target is a cap, not an exact count."""
    if not isinstance(out, dict):
        return out
    want_sents = int(spec["summary_sentences"])
    sents = out.get("summary_sentences")
    if isinstance(sents, list) and len(sents) > want_sents:
        out["summary_sentences"] = sents[:want_sents]
    exps = out.get("experiences")
    if isinstance(exps, list):
        for got, want in zip(exps, spec["experiences"]):
            bl = got.get("bullets") if isinstance(got, dict) else None
            if isinstance(bl, list) and len(bl) > want["n_bullets"]:
                got["bullets"] = bl[: want["n_bullets"]]
    return out


def validate(spec: dict[str, Any], out: Any) -> tuple[bool, str]:
    if not isinstance(out, dict):
        return False, f"reply is {type(out).__name__}, not an object"
    exps = out.get("experiences")
    if not isinstance(exps, list) or len(exps) != len(spec["experiences"]):
        return False, "experiences length mismatch"
    sents = out.get("summary_sentences") or []
    want_sents = int(spec["summary_sentences"])
    if not isinstance(sents, list) or len(sents) != want_sents:
        got = len(sents) if isinstance(sents, list) else "none"
        return False, f"summary_sentences {got} vs {want_sents}"
    if any(len(_clean(s).split()) < 7 for s in sents):
        return False, "summary sentence too short"
    for got, want in zip(exps, spec["experiences"]):
        bl = got.get("bullets")
        if not isinstance(bl, list) or not bl:
            return False, "missing bullets"
    all_bullets = [_clean(b).lower() for e in exps for b in (e.get("bullets") or [])]
    if len(all_bullets) > 2 and len(set(all_bullets)) < len(all_bullets):
        return False, "duplicate bullets across jobs"
    full_text = " ".join([_summary_text(sents)] + all_bullets)
    if YEARS_CLAIM.search(full_text):
        return False, "states years of experience, contradicting the dates"
    return True, ""


def seniority_word_in_prose(spec: dict[str, Any], out: dict[str, Any]) -> str:
    """
    Report — not reject — a band word appearing in the generated prose.

    Rejecting was a retry sink: senior rows carry titles like "Senior X", the model echoes the
    title, and all three attempts died on the same word. It also protected little, since half the
    titles are band-marked by design, so the word is already visible to any reader. Recording it
    instead keeps the row and leaves a flag that training can measure and downweight.
    """
    exps = out.get("experiences") or []
    blob = " ".join(
        [_summary_text(out.get("summary_sentences"))]
        + [_clean(b) for e in exps for b in (e.get("bullets") or [])]
    ).lower()
    titles = " ".join(str(e.get("position") or "") for e in spec["experiences"]).lower()
    for term in BANNED_TERMS[spec["language"]]:
        pattern = rf"\b{re.escape(term)}\b"
        if re.search(pattern, blob) and not re.search(pattern, titles):
            return term
    return ""


def to_resume_data(spec: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    experiences = []
    for e, got in zip(spec["experiences"], out["experiences"]):
        bullets = [_clean(b) for b in (got.get("bullets") or []) if _clean(b)]
        experiences.append(
            {
                "position": e["position"],
                "company": e["company"],
                "startDate": e["startDate"],
                "endDate": e["endDate"],
                "isCurrent": e["isCurrent"],
                "description": bullets[: e["n_bullets"]] or bullets,
            }
        )
    skills = [{"name": _clean(s)} for s in (out.get("skills") or []) if _clean(s)]
    edu = spec["education"]
    educations = (
        [{"institution": edu["institution"], "course": edu["course"], "degree": edu["degree"]}]
        if spec.get("has_education", True)
        else []
    )
    return {
        "data": {
            "summary": _summary_text(out.get("summary_sentences")),
            "targetPosition": spec["experiences"][0]["position"],
            "contact": dict(spec.get("contact") or {}),
            "experiences": experiences,
            "educations": educations,
            "skills": skills,
            "languages": [],
        }
    }


def process_safe(spec: dict[str, Any], key: str, model: str) -> dict[str, Any] | None:
    """One bad row must never abort the run — pool.map propagates any exception."""
    try:
        return process(spec, key, model)
    except Exception as exc:
        with _lock:
            print(f"  crashed on {spec.get('id')}: {type(exc).__name__}: {exc}", flush=True)
        return None


def process(spec: dict[str, Any], key: str, model: str) -> dict[str, Any] | None:
    prompt = build_prompt(spec)
    max_tokens = min(1000, _estimate_tokens(spec))
    for attempt in range(3):
        _wait_turn()
        out, _ = call_groq(key, model, prompt, max_tokens, endpoint=_ENDPOINT[0])
        if out is None:
            continue
        out = normalize(spec, out)
        ok, why = validate(spec, out)
        if ok:
            leaked = seniority_word_in_prose(spec, out)
            return {
                "id": spec["id"],
                "parallel_group": spec.get("parallel_group"),
                "language": spec["language"],
                "band_target": spec["band_target"],
                "occupation": spec["occupation"],
                "may_state_seniority": spec.get("may_state_seniority"),
                "quality_target": spec.get("quality_target"),
                "seniority_word_in_prose": leaked or None,
                "writer_model": model,
                "resume_data": to_resume_data(spec, out),
            }
        with _lock:
            print(f"  retry {spec['id']}: {why}", flush=True)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument(
        "--provider",
        default="groq8b",
        help="entry in ml/scripts/llm_providers.py; the daily cap that gates this job is per provider",
    )
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=6.0, help="seconds between API calls")
    ap.add_argument("--specs", default="specs.jsonl")
    ap.add_argument(
        "--only",
        default="",
        help="regex on spec id; use '^par' to finish the parallel groups the language-invariance"
        " test depends on before spending budget on fresh rows",
    )
    args = ap.parse_args()
    _delay[0] = max(0.5, args.delay)

    specs_path = SPECS_PATH.parent / args.specs
    if not specs_path.exists():
        raise SystemExit(f"missing {specs_path} — run generate_resume_specs_v3.py first")
    specs = [json.loads(l) for l in specs_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    done: set[str] = set()
    if OUT_PATH.exists():
        for line in OUT_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    continue
    todo = [s for s in specs if s["id"] not in done]
    if args.only:
        pattern = re.compile(args.only)
        todo = [s for s in todo if pattern.search(s["id"])]
    if args.limit:
        todo = todo[: args.limit]
    from llm_providers import resolve

    endpoint, model_name, key, _allowance = resolve(args.provider, args.model)
    _ENDPOINT[0] = endpoint
    args.model = model_name
    print(
        f"specs={len(specs)} done={len(done)} todo={len(todo)} "
        f"provider={args.provider} model={args.model}",
        flush=True,
    )
    written = failed = 0
    started = time.time()
    with OUT_PATH.open("a", encoding="utf-8") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for row in pool.map(lambda s: process_safe(s, key, args.model), todo):
                if row is None:
                    failed += 1
                    continue
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                written += 1
                rate = written / max(1e-6, (time.time() - started) / 60)
                print(
                    f"  written={written}/{len(todo)} failed={failed} ({rate:.1f}/min)",
                    flush=True,
                )

    print(f"done: +{written} rows, {failed} failed -> {OUT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
