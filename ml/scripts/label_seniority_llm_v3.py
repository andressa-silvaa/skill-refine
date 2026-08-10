"""
Point 2 of the seniority rebuild: assign the TRAINING LABEL with an LLM, not with a formula.

This is what breaks the circularity that made v2 pointless. The v2 labels came from
_holistic_seniority_label(months, n_exp, bullets, has_leadership) — a formula over the same
numbers the classifier then received, so the model could only ever re-learn the formula. Here
the label comes from a larger model reading ONLY the finished resume text, so it can encode
judgement the rules do not have, and the student distils that instead of a threshold table.

The text shown is exactly resume_to_text_sanitized() output — the same view the product feeds
the model at inference — so the labels are grounded in what the student will actually see.

Model: llama-3.3-70b-versatile. Free tier measured at 1000 requests/day and 12000 tokens/min,
so a 1000-row corpus fits one daily window with no room for a second pass. That is why this
labels once per row and relies on the parallel-language groups for a consistency signal
instead of spending three votes per row.

band_target is never shown to the model; it is only recorded so agreement can be measured.

Output: ml/data/raw/resumes_v3/labels.jsonl  (resumable — existing ids are skipped)

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/label_seniority_llm_v3.py --limit 5
  ./backend/.venv/Scripts/python.exe ml/scripts/label_seniority_llm_v3.py
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
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()


ML_ROOT = REPO_ROOT / "ml"
PROSE_PATH = ML_ROOT / "data" / "raw" / "resumes_v3" / "prose.jsonl"
OUT_PATH = ML_ROOT / "data" / "raw" / "resumes_v3" / "labels.jsonl"

LABELS = ("intern", "junior", "mid", "senior")
TODAY = (2026, 8)
USER_AGENT = "skill-refine-ml/1.0"

RUBRIC = """You classify the career seniority of a resume into exactly one of four levels.

intern  - supervised placement or first contact with the field; no ownership of outcomes
junior  - executes assigned work with limited autonomy; decisions are reviewed by others
mid     - owns a workstream end to end and decides how the work is done
senior  - accountable for outcomes achieved through other people, or sets technical direction

How to judge:
- Weigh real tenure, the scope of what the person decided, and whether outcomes depended on
  others. Those are the signals that hold across every occupation.
- Job titles are unreliable and sometimes deliberately inflated or modest. Trust the described
  work over the title.
- Do not reward resume length, bullet count or verbosity. A terse resume can be senior and a
  wordy one can be junior.
- Judge the person's current level, not the highest level they ever touched.
- The same standard applies to every occupation and language. A tradesperson, a nurse and an
  engineer reach "senior" by the same criteria, expressed in their own field's terms."""

FEWSHOT: tuple[tuple[str, str], ...] = (
    (
        "Resumo: Profissional em formacao buscando primeira experiencia pratica na area.\n"
        "Experiencia: Auxiliar de Laboratorio (Estagio) — 5 meses (atual)\n"
        "- Acompanhei a preparacao de amostras sob supervisao da equipe tecnica.\n"
        "- Registrei resultados em planilha conforme orientacao recebida.",
        "intern",
    ),
    (
        "Summary: Maintenance professional with hands-on experience in preventive routines.\n"
        "Experience: Senior Maintenance Technician — 19 months (current)\n"
        "- Carried out scheduled inspections on 40 units following the standard checklist.\n"
        "- Escalated non-standard faults to the shift supervisor for approval.",
        "junior",
    ),
    (
        "Resumen: Responsable de la gestion integral del area de compras de la planta.\n"
        "Experiencia: Comprador — 6 anos (actual)\n"
        "- Defini la estrategia de abastecimiento de 3 familias de producto.\n"
        "- Negocie contratos anuales con proveedores, reduciendo el coste unitario un 12%.",
        "mid",
    ),
    (
        "Resumo: Atuacao consolidada em obras de infraestrutura de grande porte.\n"
        "Experiencia: Engenheiro — 12 anos (atual)\n"
        "- Respondi pela execucao de 6 empreendimentos, coordenando equipes de 20 pessoas.\n"
        "- Defini o metodo construtivo adotado como padrao pela empresa.",
        "senior",
    ),
)

_gate_lock = threading.Lock()
_next_slot = [0.0]
_delay = [5.0]
_backoff_until = [0.0]
_print_lock = threading.Lock()


def _wait_turn() -> None:
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
    with _gate_lock:
        _backoff_until[0] = max(_backoff_until[0], time.monotonic() + max(2.0, seconds))


def _api_key() -> str:
    env = REPO_ROOT / "backend" / ".env"
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


def render_for_labelling(resume_data: dict[str, Any]) -> str:
    """
    Render the resume the way a reader needs it: duration, scope and the described work.

    The product's resume_to_text_sanitized() was used first and it emits only summary, job titles,
    courses and skills — no bullets and no dates. Labels produced from that view were decided
    without the evidence that determines seniority, which is why they collapsed toward "mid".
    """
    data = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    out: list[str] = []
    summary = str(data.get("summary") or "").strip()
    if summary:
        out.append(f"Resumo/Summary: {summary}")

    for exp in (data.get("experiences") or [])[:12]:
        if not isinstance(exp, dict):
            continue
        title = str(exp.get("position") or "").strip() or "(sem titulo)"
        months = _months_between(exp.get("startDate"), exp.get("endDate"), exp.get("isCurrent"))
        when = f"{months} meses" if months else "duracao nao informada"
        current = " (atual)" if exp.get("isCurrent") else ""
        out.append(f"\nExperiencia: {title} — {when}{current}")
        for b in (exp.get("description") or [])[:10]:
            text = str(b).strip()
            if text:
                out.append(f"- {text}")

    skills = [
        str(s.get("name") if isinstance(s, dict) else s).strip()
        for s in (data.get("skills") or [])
    ]
    skills = [s for s in skills if s][:14]
    if skills:
        out.append("\nCompetencias: " + ", ".join(skills))

    for ed in (data.get("educations") or [])[:3]:
        if isinstance(ed, dict):
            bits = [str(ed.get(k) or "").strip() for k in ("degree", "course")]
            line = " ".join(b for b in bits if b)
            if line:
                out.append(f"Formacao: {line}")

    return "\n".join(out)[:4000]


def _months_between(start: Any, end: Any, is_current: Any) -> int:
    def parse(v: Any) -> tuple[int, int] | None:
        parts = str(v or "").strip().split("-")
        if len(parts) >= 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                return None
        return None

    s = parse(start)
    if not s:
        return 0
    e = TODAY if is_current or not end else parse(end)
    if not e:
        return 0
    return max(0, (e[0] - s[0]) * 12 + (e[1] - s[1]) + 1)


def build_messages(resume_text: str) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = [
        {
            "role": "system",
            "content": RUBRIC
            + '\n\nAnswer with JSON only: {"level": "intern|junior|mid|senior"}.'
            " Use those exact English identifiers whatever language the resume is written in.",
        }
    ]
    for text, label in FEWSHOT:
        msgs.append({"role": "user", "content": text})
        msgs.append({"role": "assistant", "content": json.dumps({"level": label})})
    msgs.append({"role": "user", "content": resume_text})
    return msgs


def _parse_duration(text: str) -> float:
    t = str(text).strip()
    if not t:
        return 0.0
    if t.endswith("ms"):
        try:
            return float(t[:-2]) / 1000.0
        except ValueError:
            return 5.0
    m = re.match(r"^(?:(\d+(?:\.\d+)?)m)?(\d+(?:\.\d+)?)?s?$", t)
    if m:
        return float(m.group(1) or 0) * 60 + float(m.group(2) or 0)
    try:
        return float(t)
    except ValueError:
        return 5.0


def call_llm(key: str, model: str, messages: list[dict[str, str]]) -> str | None:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.0,
            "max_tokens": 20,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            level = str((parsed or {}).get("level") or "").strip().lower()
            return level if level in LABELS else None
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = _parse_duration(exc.headers.get("retry-after") or "20s")
                _back_off(min(120.0, wait))
                time.sleep(max(2.0, min(120.0, wait)))
                continue
            time.sleep(2 + attempt * 2)
        except (OSError, json.JSONDecodeError, KeyError, IndexError):
            time.sleep(2 + attempt * 2)
    return None


def label_one(row: dict[str, Any], key: str, model: str) -> dict[str, Any] | None:
    text = render_for_labelling(row["resume_data"])
    if not text.strip():
        return None
    messages = build_messages(text)
    for _ in range(2):
        _wait_turn()
        level = call_llm(key, model, messages)
        if level:
            return {
                "id": row["id"],
                "parallel_group": row.get("parallel_group"),
                "language": row["language"],
                "occupation": row.get("occupation"),
                "band_target": row["band_target"],
                "llm_label": level,
                "labeler_model": model,
            }
    with _print_lock:
        print(f"  no label for {row['id']}", flush=True)
    return None


def load_rows() -> list[dict[str, Any]]:
    if not PROSE_PATH.exists():
        raise SystemExit(f"missing {PROSE_PATH} — run write_resume_prose_v3.py first")
    rows = []
    for line in PROSE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def report(labels: list[dict[str, Any]]) -> None:
    if not labels:
        return
    print("\n" + "=" * 70)
    print("CONCORDANCIA com o alvo de geracao (band_target)")
    print("=" * 70)
    agree = sum(1 for r in labels if r["llm_label"] == r["band_target"])
    print(f"  exata: {agree}/{len(labels)} ({agree / len(labels):.1%})")
    order = {b: i for i, b in enumerate(LABELS)}
    off = Counter(order[r["llm_label"]] - order[r["band_target"]] for r in labels)
    print("  desvio em niveis:", {k: off[k] for k in sorted(off)})
    print("\n  matriz alvo -> rotulo:")
    print("    " + "".join(f"{b[:6]:>8s}" for b in LABELS))
    for t in LABELS:
        line = f"    {t[:6]:6s}"
        for p in LABELS:
            line += f"{sum(1 for r in labels if r['band_target'] == t and r['llm_label'] == p):>8d}"
        print(line)

    print("\n" + "=" * 70)
    print("CONSISTENCIA CROSS-IDIOMA (grupos paralelos)")
    print("=" * 70)
    groups: dict[str, dict[str, str]] = defaultdict(dict)
    for r in labels:
        if r.get("parallel_group"):
            groups[r["parallel_group"]][r["language"]] = r["llm_label"]
    full = {g: v for g, v in groups.items() if len(v) == 3}
    if not full:
        print("  nenhum grupo completo nos 3 idiomas ainda")
        return
    same = sum(1 for v in full.values() if len(set(v.values())) == 1)
    print(f"  grupos completos: {len(full)} | mesmo rotulo nos 3 idiomas: {same} ({same / len(full):.1%})")
    for g, v in list(full.items())[:5]:
        if len(set(v.values())) > 1:
            print(f"    divergente {g}: {v}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="llama-3.3-70b-versatile")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=5.0)
    ap.add_argument(
        "--out",
        default="labels.jsonl",
        help="write to a separate file to benchmark a cheaper labeller against the current one",
    )
    args = ap.parse_args()
    _delay[0] = max(0.5, args.delay)

    out_path = OUT_PATH.parent / args.out
    rows = load_rows()
    done: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    done[r["id"]] = r
                except (json.JSONDecodeError, KeyError):
                    continue
    todo = [r for r in rows if r["id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"prose={len(rows)} rotulados={len(done)} a rotular={len(todo)} model={args.model}")

    key = _api_key()
    written = 0
    started = time.time()
    with out_path.open("a", encoding="utf-8") as fh:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for out in pool.map(lambda r: label_one(r, key, args.model), todo):
                if out is None:
                    continue
                fh.write(json.dumps(out, ensure_ascii=False) + "\n")
                fh.flush()
                done[out["id"]] = out
                written += 1
                rate = written / max(1e-6, (time.time() - started) / 60)
                print(f"  labeled={written}/{len(todo)} ({rate:.1f}/min)", flush=True)

    print(f"\ndone: +{written} rotulos -> {OUT_PATH}")
    report(list(done.values()))


if __name__ == "__main__":
    main()
