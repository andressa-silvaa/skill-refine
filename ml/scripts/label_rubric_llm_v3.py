"""
Point 2 of the rebuild, widened: one teacher pass produces the labels for EVERY judged area of the
analysis, not just the seniority band.

Why one rubric instead of one pass per task: the cost of a labelling call is dominated by the
prompt, not by the answer. Labelling seniority today and quality next week means paying for the
resume text twice out of a daily budget that fits neither. So the teacher reads the resume once and
returns the whole rubric.

Two stages, on purpose, because Groq bills the two models from SEPARATE daily budgets:

  judgment (70b) - seniority band + the four quality dimensions. Real judgement, expensive model,
                   ~100k tokens/day.
  bullets  (8b)  - per-bullet attributes (quantified / outcome / leadership). Mechanical attribute
                   extraction with a structural output contract, ~500k tokens/day.

Running both spends two independent budgets instead of draining the scarce one twice, and together
they emit the same rubric a single call would have produced.

What this replaces downstream:
  seniority                    -> rule_based_seniority (month thresholds)
  quality.impact/clarity/ats   -> _heuristic_score, and the ats/clarity copies of quality_score
  quality.language             -> nothing today
  bullets.quantified           -> METRICS_PATTERN
  bullets.outcome              -> ACTION_VERBS
  bullets.leadership           -> LEADERSHIP_WORDS

band_target and quality_target are never shown to the model; they are recorded so agreement with
the generator can be measured, exactly as before.

Every call records token usage, so the schedule stops being a guess: the run prints the measured
cost per item and the resulting items/day against the daily budget.

Output (resumable, existing ids skipped):
  ml/data/raw/resumes_v3/labels_rubric.jsonl   (judgment stage)
  ml/data/raw/resumes_v3/labels_bullets.jsonl  (bullets stage)

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/label_rubric_llm_v3.py --stage judgment --limit 8
  ./backend/.venv/Scripts/python.exe ml/scripts/label_rubric_llm_v3.py --stage bullets --limit 8
  ./backend/.venv/Scripts/python.exe ml/scripts/label_rubric_llm_v3.py --stage judgment
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import label_seniority_llm_v3 as base  # noqa: E402

REPO_ROOT = base.REPO_ROOT
OUT_DIR = base.OUT_PATH.parent
LABELS = base.LABELS
USER_AGENT = base.USER_AGENT

MAX_BULLETS = 12
DIMENSIONS = ("impact", "clarity", "ats", "language")

DAILY_TOKEN_BUDGET = {"llama-3.3-70b-versatile": 100_000, "llama-3.1-8b-instant": 500_000}

from llm_providers import GROQ, PROVIDERS, key_for as _key_for  # noqa: E402

QUALITY_RUBRIC = """You also rate how well the resume is WRITTEN, on four independent 1-5 scales.
Writing quality is not seniority: a senior can write badly and an intern can write well.

impact   - 1 duties only, no result anywhere. 3 some bullets show a result. 5 nearly every bullet
           states an outcome with a figure, volume or timeframe.
clarity  - 1 vague filler, unreadable. 3 understandable but wordy or uneven. 5 every line is
           concrete, specific and short.
ats      - 1 no section structure, no role terms a screener would search. 3 usable structure with
           some domain terms. 5 clean sections and the vocabulary of the occupation throughout.
language - 1 broken grammar, wrong register, first-person rambling. 3 acceptable with slips.
           5 correct, consistent and professional.

Rate what is on the page, not the person's potential. Do not reward length."""

JSON_CONTRACT = (
    'Answer with JSON only: {"level": "intern|junior|mid|senior", '
    '"impact": 1-5, "clarity": 1-5, "ats": 1-5, "language": 1-5}. '
    "Use those exact English identifiers whatever language the resume is written in."
)

TERSE_SYSTEM = """Rate a resume. Two independent things: career level, and how well it is written.

level: intern = supervised, owns nothing. junior = executes assigned work, decisions reviewed.
mid = owns a workstream end to end and decides how. senior = accountable for outcomes achieved
through other people, or sets technical direction.
Weigh real tenure, decision scope, and whether outcomes depended on others. Titles are unreliable,
trust the described work. Never reward length or bullet count. Judge the current level. Same
standard for every occupation and language.

Writing, 1-5 each, independent of level (a senior can write badly):
impact 1 duties only / 3 some results / 5 nearly every bullet has a figure or outcome
clarity 1 vague filler / 3 wordy but readable / 5 every line concrete and short
ats 1 no structure or role terms / 3 usable / 5 clean sections and occupation vocabulary
language 1 broken grammar / 3 acceptable with slips / 5 correct and professional throughout"""

BULLET_SPEC = """You label each numbered bullet of a resume on three yes/no attributes.

quantified - the bullet states a number, volume, percentage, money value or timeframe
outcome    - the bullet states a RESULT or change, not just an assigned duty
leadership - the bullet shows direction of people, teams, suppliers or cross-area coordination

Judge only what the bullet says. Do not infer from other bullets."""

_usage_lock = threading.Lock()
_usage = {"items": 0, "prompt": 0, "completion": 0}


def render_indexed(resume_data: dict[str, Any]) -> tuple[str, list[str]]:
    """Same view as base.render_for_labelling, with globally numbered bullets."""
    data = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    out: list[str] = []
    bullets: list[str] = []
    summary = str(data.get("summary") or "").strip()
    if summary:
        out.append(f"Resumo/Summary: {summary}")

    for exp in (data.get("experiences") or [])[:12]:
        if not isinstance(exp, dict):
            continue
        title = str(exp.get("position") or "").strip() or "(sem titulo)"
        months = base._months_between(exp.get("startDate"), exp.get("endDate"), exp.get("isCurrent"))
        when = f"{months} meses" if months else "duracao nao informada"
        current = " (atual)" if exp.get("isCurrent") else ""
        out.append(f"\nExperiencia: {title} — {when}{current}")
        for raw in (exp.get("description") or [])[:10]:
            text = str(raw).strip()
            if not text:
                continue
            if len(bullets) >= MAX_BULLETS:
                continue
            out.append(f"[{len(bullets)}] {text}")
            bullets.append(text)

    skills = [str(s.get("name") if isinstance(s, dict) else s).strip() for s in (data.get("skills") or [])]
    skills = [s for s in skills if s][:14]
    if skills:
        out.append("\nCompetencias: " + ", ".join(skills))

    for ed in (data.get("educations") or [])[:3]:
        if isinstance(ed, dict):
            line = " ".join(b for b in (str(ed.get(k) or "").strip() for k in ("degree", "course")) if b)
            if line:
                out.append(f"Formacao: {line}")

    return "\n".join(out)[:4000], bullets


def build_judgment_messages(resume_text: str, *, terse: bool = False) -> list[dict[str, str]]:
    """
    The prompt is 97% of the measured cost (1235 of 1273 tokens per item), and it is paid on every
    resume, so its length is the schedule. terse drops the few-shots and compresses the rubric;
    both variants exist so the saving can be weighed against label agreement.
    """
    if terse:
        return [
            {"role": "system", "content": f"{TERSE_SYSTEM}\n\n{JSON_CONTRACT}"},
            {"role": "user", "content": resume_text},
        ]
    anchors = (base.FEWSHOT[0], base.FEWSHOT[3])
    replies = (
        {"level": "intern", "impact": 1, "clarity": 3, "ats": 2, "language": 3},
        {"level": "senior", "impact": 5, "clarity": 5, "ats": 4, "language": 5},
    )
    msgs = [{"role": "system", "content": f"{base.RUBRIC}\n\n{QUALITY_RUBRIC}\n\n{JSON_CONTRACT}"}]
    for (text, _label), reply in zip(anchors, replies):
        msgs.append({"role": "user", "content": text})
        msgs.append({"role": "assistant", "content": json.dumps(reply)})
    msgs.append({"role": "user", "content": resume_text})
    return msgs


def build_bullet_messages(bullets: list[str]) -> list[dict[str, str]]:
    numbered = "\n".join(f"[{i}] {b}" for i, b in enumerate(bullets))
    contract = (
        f'Answer with JSON only: {{"bullets": [...]}} containing EXACTLY {len(bullets)} objects, '
        'one per bullet in order, each {"i": <index>, "quantified": true|false, '
        '"outcome": true|false, "leadership": true|false}.'
    )
    return [
        {"role": "system", "content": f"{BULLET_SPEC}\n\n{contract}"},
        {"role": "user", "content": numbered},
    ]


def call_json(
    endpoint: str,
    key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
) -> dict[str, Any] | None:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
    ).encode("utf-8")
    for attempt in range(5):
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            usage = payload.get("usage") or {}
            with _usage_lock:
                _usage["items"] += 1
                _usage["prompt"] += int(usage.get("prompt_tokens") or 0)
                _usage["completion"] += int(usage.get("completion_tokens") or 0)
            return json.loads(payload["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", errors="ignore")[:300]
                except OSError:
                    pass
                wait = base._parse_duration(exc.headers.get("retry-after") or "20s")
                with base._print_lock:
                    print(f"  429 wait={wait:.0f}s body={detail}", flush=True)
                base._back_off(min(120.0, wait))
                time.sleep(max(2.0, min(120.0, wait)))
                continue
            time.sleep(2 + attempt * 2)
        except (OSError, json.JSONDecodeError, KeyError, IndexError):
            time.sleep(2 + attempt * 2)
    return None


def _dimension(raw: Any) -> int | None:
    try:
        value = int(round(float(raw)))
    except (TypeError, ValueError):
        return None
    return max(1, min(5, value))


def judge_one(
    row: dict[str, Any],
    key: str,
    model: str,
    *,
    endpoint: str = GROQ,
    terse: bool = False,
    max_tokens: int = 140,
) -> dict[str, Any] | None:
    try:
        text, _bullets = render_indexed(row["resume_data"])
    except Exception:
        return None
    if not text.strip():
        return None
    messages = build_judgment_messages(text, terse=terse)
    for _ in range(2):
        base._wait_turn()
        parsed = call_json(endpoint, key, model, messages, max_tokens=max_tokens)
        if not isinstance(parsed, dict):
            continue
        level = str(parsed.get("level") or "").strip().lower()
        if level not in LABELS:
            continue
        dims = {d: _dimension(parsed.get(d)) for d in DIMENSIONS}
        if any(v is None for v in dims.values()):
            continue
        return {
            "id": row["id"],
            "parallel_group": row.get("parallel_group"),
            "language": row["language"],
            "occupation": row.get("occupation"),
            "band_target": row["band_target"],
            "quality_target": row.get("quality_target"),
            "llm_label": level,
            "quality": dims,
            "labeler_model": model,
            "prompt_variant": "terse" if terse else "fewshot",
        }
    with base._print_lock:
        print(f"  no judgment for {row['id']}", flush=True)
    return None


def bullets_one(
    row: dict[str, Any],
    key: str,
    model: str,
    *,
    endpoint: str = GROQ,
) -> dict[str, Any] | None:
    try:
        _text, bullets = render_indexed(row["resume_data"])
    except Exception:
        return None
    if not bullets:
        return None
    messages = build_bullet_messages(bullets)
    budget = 40 + 26 * len(bullets)
    for _ in range(2):
        base._wait_turn()
        parsed = call_json(endpoint, key, model, messages, max_tokens=budget)
        raw = (parsed or {}).get("bullets")
        if not isinstance(raw, list) or not raw:
            continue
        items = []
        for i, entry in enumerate(raw[: len(bullets)]):
            if not isinstance(entry, dict):
                continue
            items.append(
                {
                    "i": i,
                    "quantified": bool(entry.get("quantified")),
                    "outcome": bool(entry.get("outcome")),
                    "leadership": bool(entry.get("leadership")),
                }
            )
        if len(items) != len(bullets):
            continue
        return {
            "id": row["id"],
            "language": row["language"],
            "band_target": row["band_target"],
            "n_bullets": len(bullets),
            "bullets": items,
            "labeler_model": model,
        }
    with base._print_lock:
        print(f"  no bullet labels for {row['id']}", flush=True)
    return None


def cost_report(model: str, provider: str = "") -> None:
    with _usage_lock:
        items, prompt, completion = _usage["items"], _usage["prompt"], _usage["completion"]
    if not items:
        return
    total = prompt + completion
    per_item = total / items
    budget = DAILY_TOKEN_BUDGET.get(model, 0)
    label = f"{provider}/{model}" if provider else model
    print("\n" + "=" * 70)
    print("CUSTO MEDIDO (usage reportado pela API, nao estimativa)")
    print("=" * 70)
    print(f"  {label}: chamadas {items}  prompt {prompt}  saida {completion}  total {total}")
    print(f"  por item: {per_item:.0f} tokens  ({prompt / items:.0f} prompt + {completion / items:.0f} saida)")
    if budget:
        per_day = budget / per_item
        print(f"  orcamento diario {budget} -> ~{per_day:.0f} itens/dia")
        print(f"  873 curriculos -> {873 / max(1e-9, per_day):.1f} dias")
    else:
        print("  teto diario deste provedor: desconhecido, aparece no corpo do 429")


def quality_report(rows: list[dict[str, Any]]) -> None:
    scored = [r for r in rows if isinstance(r.get("quality"), dict)]
    if not scored:
        return
    print("\n" + "=" * 70)
    print("DIMENSOES DE QUALIDADE")
    print("=" * 70)
    for dim in DIMENSIONS:
        values = [r["quality"][dim] for r in scored if r["quality"].get(dim)]
        if values:
            spread = Counter(values)
            mean = sum(values) / len(values)
            print(f"  {dim:<9} media {mean:.2f}  dist {dict(sorted(spread.items()))}")
    planted = [r for r in scored if r.get("quality_target")]
    if planted:
        print("\n  contra o alvo plantado (quality_target):")
        for target in ("poor", "fair", "good"):
            subset = [r for r in planted if r["quality_target"] == target]
            if subset:
                mean = sum(r["quality"]["impact"] for r in subset) / len(subset)
                print(f"    {target:<5} n={len(subset):3d}  impact medio {mean:.2f}")


def _round_robin(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Interleave by (band, language) so truncating with --limit keeps the subset balanced.

    File order is generation order, so a plain head of the corpus can silently skew a whole
    band or language out of the training set.
    """
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (str(row.get("band_target") or ""), str(row.get("language") or ""))
        buckets.setdefault(key, []).append(row)
    ordered: list[dict[str, Any]] = []
    keys = sorted(buckets)
    position = 0
    while len(ordered) < len(rows):
        drained = True
        for key in keys:
            bucket = buckets[key]
            if position < len(bucket):
                ordered.append(bucket[position])
                drained = False
        if drained:
            break
        position += 1
    return ordered


def agreement_report(rows: list[dict[str, Any]], compare_path: Path) -> None:
    """Teacher-vs-teacher agreement on the same ids: the number that justifies a cheaper labeller."""
    if not compare_path.exists():
        print(f"\n(sem comparacao: {compare_path.name} nao existe)")
        return
    other: dict[str, dict[str, Any]] = {}
    for line in compare_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                record = json.loads(line)
                other[record["id"]] = record
            except (json.JSONDecodeError, KeyError):
                continue
    shared = [r for r in rows if r["id"] in other]
    if not shared:
        print("\n(sem ids em comum para comparar)")
        return
    print("\n" + "=" * 70)
    print(f"CONCORDANCIA ENTRE PROFESSORES (n={len(shared)}, contra {compare_path.name})")
    print("=" * 70)
    order = {b: i for i, b in enumerate(LABELS)}
    exact = sum(1 for r in shared if r["llm_label"] == other[r["id"]]["llm_label"])
    within = sum(
        1 for r in shared if abs(order[r["llm_label"]] - order[other[r["id"]]["llm_label"]]) <= 1
    )
    print(f"  banda exata: {exact}/{len(shared)} ({exact / len(shared):.0%})  ±1 nivel: {within / len(shared):.0%}")
    for dim in DIMENSIONS:
        pairs = [
            (r["quality"][dim], other[r["id"]].get("quality", {}).get(dim))
            for r in shared
            if isinstance(r.get("quality"), dict) and other[r["id"]].get("quality")
        ]
        pairs = [(a, b) for a, b in pairs if a and b]
        if pairs:
            mae = sum(abs(a - b) for a, b in pairs) / len(pairs)
            print(f"  {dim:<9} erro medio absoluto {mae:.2f} pontos (escala 1-5)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("judgment", "bullets"), default="judgment")
    ap.add_argument("--provider", choices=tuple(PROVIDERS), default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=5.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--terse", action="store_true", help="short prompt, no few-shots: ~half the tokens")
    ap.add_argument("--compare", default="", help="jsonl of labels from another labeller to agree against")
    ap.add_argument("--only", default="", help="regex on row id, e.g. '^q' for the quality-varied batch")
    ap.add_argument(
        "--overlap-with",
        default="",
        help="label only ids already present in this labels file, so agreement is measured on a "
        "chosen set instead of on whatever the two runs happened to share",
    )
    ap.add_argument(
        "--stratify",
        action="store_true",
        help="round-robin over (band, language) so a --limit subset stays balanced",
    )
    args = ap.parse_args()

    judgment = args.stage == "judgment"
    provider = args.provider or ("groq" if judgment else "groq8b")
    endpoint, default_model, env_name, judgment_tokens = PROVIDERS[provider]
    model = args.model or default_model
    out_path = OUT_DIR / (args.out or ("labels_rubric.jsonl" if judgment else "labels_bullets.jsonl"))
    base._delay[0] = max(0.5, args.delay)

    rows = base.load_rows()
    done: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    record = json.loads(line)
                    done[record["id"]] = record
                except (json.JSONDecodeError, KeyError):
                    continue
    todo = [r for r in rows if r["id"] not in done]
    if args.only:
        pattern = re.compile(args.only)
        todo = [r for r in todo if pattern.search(str(r.get("id") or ""))]
    if args.overlap_with:
        reference: set[str] = set()
        ref_path = OUT_DIR / args.overlap_with
        for line in ref_path.read_text(encoding="utf-8").splitlines() if ref_path.exists() else []:
            if line.strip():
                try:
                    reference.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    continue
        todo = [r for r in todo if r["id"] in reference]
    if args.stratify:
        todo = _round_robin(todo)
    if args.limit:
        todo = todo[: args.limit]
    print(
        f"stage={args.stage} provider={provider} model={model} "
        f"prose={len(rows)} feitos={len(done)} a fazer={len(todo)}"
    )
    if todo:
        print(
            "  bandas: "
            + json.dumps(dict(Counter(r.get("band_target") for r in todo)), ensure_ascii=False)
            + "  idiomas: "
            + json.dumps(dict(Counter(r.get("language") for r in todo)), ensure_ascii=False)
        )

    key = _key_for(env_name)

    def worker(row: dict[str, Any], api_key: str, model_name: str) -> dict[str, Any] | None:
        if judgment:
            return judge_one(
                row,
                api_key,
                model_name,
                endpoint=endpoint,
                terse=args.terse,
                max_tokens=judgment_tokens,
            )
        return bullets_one(row, api_key, model_name, endpoint=endpoint)
    written = 0
    started = time.time()

    def safe(row: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return worker(row, key, model)
        except Exception as exc:
            with base._print_lock:
                print(f"  item {row.get('id')} falhou: {exc}", flush=True)
            return None

    with out_path.open("a", encoding="utf-8") as fh:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for record in pool.map(safe, todo):
                if record is None:
                    continue
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()
                done[record["id"]] = record
                written += 1
                rate = written / max(1e-6, (time.time() - started) / 60)
                print(f"  ok={written}/{len(todo)} ({rate:.1f}/min)", flush=True)

    print(f"\ndone: +{written} -> {out_path}")
    cost_report(model, provider)
    if judgment:
        labelled = [r for r in done.values() if r.get("llm_label")]
        if labelled:
            base.report(labelled)
            if args.compare:
                agreement_report(labelled, OUT_DIR / args.compare)
        quality_report(list(done.values()))


if __name__ == "__main__":
    main()
