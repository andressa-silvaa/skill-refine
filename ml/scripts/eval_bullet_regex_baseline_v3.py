"""
Measure the regex families that a per-bullet classifier would replace, against the LLM bullet labels.

Three of the four regex families in the inventory decide a per-bullet fact, so they can be scored
per bullet on the same text the labeller read:

    bullets.quantified  -> METRICS_PATTERN   (quality/predict.py)
    bullets.outcome     -> ACTION_VERBS      (quality/predict.py, 8 fixed word forms per language)
    bullets.leadership  -> LEADERSHIP_WORDS  (quality/predict.py)

The fourth, ``_INTERNSHIP_RE``, reads a whole-document blob rather than a bullet, so it is out of
scope here and stays measured where it lives.

Two references are reported. Against a single annotator the score mixes regex error with labeller
noise. Against the subset where two labellers of different model families agree, the reference is
the part both saw the same way, which is the stricter and more defensible number; the disagreed
bullets are dropped rather than resolved, and the dropped count is printed.

Usage:
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_bullet_regex_baseline_v3.py \
      --labels labels_bullets.jsonl --second labels_bullets_mistral.jsonl --report
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml" / "scripts"))

import label_rubric_llm_v3 as L
import label_seniority_llm_v3 as base

from apps.analysis.application.inference.tasks.quality.predict import (
    ACTION_VERBS,
    LEADERSHIP_WORDS,
    METRICS_PATTERN,
)

RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3"
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "bullet_regex_baseline_v3.md"
ATTRS = ("quantified", "outcome", "leadership")


def load_labels(name: str) -> dict[str, dict[str, Any]]:
    path = RAW_DIR / name
    rows: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows
    duplicates = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("id") in rows:
            duplicates += 1
        rows[row["id"]] = row
    if duplicates:
        print(f"{name}: {duplicates} duplicate lines dropped (last write wins)")
    return rows


def regex_flags(text: str, lang: str) -> dict[str, bool]:
    low = (text or "").lower()
    verbs = ACTION_VERBS.get(lang, ACTION_VERBS["pt"])
    return {
        "quantified": bool(METRICS_PATTERN.search(low)),
        "outcome": any(v in low for v in verbs),
        "leadership": bool(LEADERSHIP_WORDS.search(low)),
    }


def build_rows(labels: dict[str, Any], second: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    prose = {r["id"]: r for r in base.load_rows()}
    rows: list[dict[str, Any]] = []
    stale = 0
    for rid, rec in sorted(labels.items()):
        source = prose.get(rid)
        if source is None:
            stale += 1
            continue
        _text, bullets = L.render_indexed(source.get("resume_data") or {})
        marked = rec.get("bullets") or []
        if len(marked) != len(bullets):
            stale += 1
            continue
        other = (second.get(rid) or {}).get("bullets") or []
        other_ok = len(other) == len(bullets)
        lang = (rec.get("language") or "pt").split("-")[0]
        for pos, mark in enumerate(marked):
            rows.append(
                {
                    "id": rid,
                    "text": bullets[pos],
                    "lang": lang,
                    "band": rec.get("band_target"),
                    "regex": regex_flags(bullets[pos], lang),
                    "label": {k: bool(mark.get(k)) for k in ATTRS},
                    "other": {k: bool(other[pos].get(k)) for k in ATTRS} if other_ok else None,
                }
            )
    return rows, stale


def score(rows: list[dict[str, Any]], pick, title: str, out: list[str]) -> None:
    out.append(f"### Regex vs {title}")
    out.append("")
    out.append("| attribute | regex | n | agreement | precision | recall | misses | false fires |")
    out.append("|---|---|---|---|---|---|---|---|")
    names = {
        "quantified": "`METRICS_PATTERN`",
        "outcome": "`ACTION_VERBS`",
        "leadership": "`LEADERSHIP_WORDS`",
    }
    for attr in ATTRS:
        sub = [r for r in rows if pick(r, attr) is not None]
        n = len(sub)
        if not n:
            continue
        tp = sum(1 for r in sub if r["regex"][attr] and pick(r, attr))
        fp = sum(1 for r in sub if r["regex"][attr] and not pick(r, attr))
        fn = sum(1 for r in sub if not r["regex"][attr] and pick(r, attr))
        tn = n - tp - fp - fn
        acc = (tp + tn) / n
        prec = f"{tp / (tp + fp):.2f}" if tp + fp else "n/a"
        rec = f"{tp / (tp + fn):.2f}" if tp + fn else "n/a"
        out.append(
            f"| `{attr}` | {names[attr]} | {n} | {acc:.1%} | {prec} | {rec} | {fn} | {fp} |"
        )
    out.append("")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="labels_bullets.jsonl")
    ap.add_argument("--second", default="labels_bullets_mistral.jsonl")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    labels = load_labels(args.labels)
    second = load_labels(args.second)
    rows, stale = build_rows(labels, second)
    if not rows:
        raise SystemExit("no bullets to score — is the labelling run finished?")

    out: list[str] = []
    out.append("# Per-bullet regex baseline — v3 corpus")
    out.append("")
    out.append(
        f"Labels `{args.labels}` ({len(labels)} resumes) · second annotator `{args.second}` "
        f"({len(second)} resumes) · **{len(rows)} bullets scored**"
        + (f" · {stale} resumes dropped as stale or absent from deduped prose" if stale else "")
    )
    out.append("")
    langs = collections.Counter(r["lang"] for r in rows)
    bands = collections.Counter(r["band"] for r in rows)
    out.append(f"Language: {dict(langs)} · band: {dict(bands)}")
    out.append("")
    out.append("Positive rate in the labels:")
    out.append("")
    out.append("| attribute | positives | rate |")
    out.append("|---|---|---|")
    for attr in ATTRS:
        pos = sum(1 for r in rows if r["label"][attr])
        out.append(f"| `{attr}` | {pos} | {pos / len(rows):.1%} |")
    out.append("")

    paired = [r for r in rows if r["other"] is not None]
    if paired:
        out.append("### Inter-annotator agreement")
        out.append("")
        out.append(
            f"{len(paired)} bullets labelled twice by different model families. Cohen's kappa "
            "against the chance rate implied by each labeller's own positive rate."
        )
        out.append("")
        out.append("| attribute | agreement | kappa | positive rate A | positive rate B |")
        out.append("|---|---|---|---|---|")
        for attr in ATTRS:
            n = len(paired)
            obs = sum(1 for r in paired if r["label"][attr] == r["other"][attr]) / n
            pa = sum(1 for r in paired if r["label"][attr]) / n
            pb = sum(1 for r in paired if r["other"][attr]) / n
            exp = pa * pb + (1 - pa) * (1 - pb)
            kappa = (obs - exp) / (1 - exp) if exp < 1 else float("nan")
            out.append(f"| `{attr}` | {obs:.1%} | {kappa:.2f} | {pa:.2f} | {pb:.2f} |")
        out.append("")

    score(rows, lambda r, a: r["label"][a], f"single annotator (n={len(rows)})", out)
    if paired:
        agreed = sum(1 for r in paired for a in ATTRS if r["label"][a] == r["other"][a])
        score(
            paired,
            lambda r, a: r["label"][a] if r["label"][a] == r["other"][a] else None,
            f"two-annotator consensus (from {len(paired)} paired bullets, "
            f"{3 * len(paired) - agreed} attribute-level disagreements dropped)",
            out,
        )

    out.append("### Regex recall by language, on label positives")
    out.append("")
    out.append("| language | " + " | ".join(f"`{a}`" for a in ATTRS) + " |")
    out.append("|---|" + "---|" * len(ATTRS))
    for lang in sorted(langs):
        cells = []
        for attr in ATTRS:
            pos = [r for r in rows if r["lang"] == lang and r["label"][attr]]
            if pos:
                hit = sum(1 for r in pos if r["regex"][attr])
                cells.append(f"{hit / len(pos):.2f} (n={len(pos)})")
            else:
                cells.append("n/a")
        out.append(f"| {lang} | " + " | ".join(cells) + " |")
    out.append("")

    for direction, want, label in (
        ("misses", True, "label positive, regex silent"),
        ("false-fires on", False, "label negative, regex fires"),
    ):
        out.append(f"### Examples the regex {direction} — {label}")
        out.append("")
        for attr in ATTRS:
            picked = [
                r
                for r in rows
                if r["label"][attr] is want and r["regex"][attr] is not want
            ][:3]
            for r in picked:
                out.append(f"- `{attr}` ({r['lang']}) — {r['text'][:150]}")
        out.append("")

    text = "\n".join(out)
    print(text)
    if args.report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(text + "\n", encoding="utf-8")
        print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
