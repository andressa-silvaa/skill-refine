"""
Point 3 of the seniority rebuild: build the human review sample for the LLM labels.

Reviewing 50 random rows would spend attention where it teaches least. The sample is stratified
toward the rows whose verdict actually changes a decision:

  A. llm_label != band_target — the generator and the labeller disagree, so one of them is wrong
     and reading these tells us which. This is where label quality is decided.
  B. parallel groups whose three languages got different labels — direct evidence of language
     bias in the labeller, the metric no other check can produce.
  C. a stratified baseline of agreements across the four labels, so the sample also measures the
     ordinary case and not only the hard tail.

The text shown is exactly what the labeller saw (resume_to_text_sanitized), so a disagreement is
about judgement rather than about different evidence.

Writes:
  ml/data/raw/resumes_v3/review_sample.md      the reading material, one resume per block
  ml/data/raw/resumes_v3/review_verdicts.jsonl one prefilled line per row, `verdict` left empty

Fill `verdict` with intern|junior|mid|senior (or "ok" to accept llm_label), then run
score_label_review.py to get the agreement rate.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/build_label_review_sample.py --count 50
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from apps.analysis.application.inference.text_sanitizer import (  # noqa: E402
    resume_to_text_sanitized,
)

DATA_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3"
LABELS = ("intern", "junior", "mid", "senior")


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"missing {path}")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=50)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    prose = {r["id"]: r for r in _read(DATA_DIR / "prose.jsonl")}
    labels = {r["id"]: r for r in _read(DATA_DIR / "labels.jsonl")}
    pairs = [(i, labels[i]) for i in labels if i in prose]
    if not pairs:
        raise SystemExit("no labelled rows yet")

    disagree = [i for i, l in pairs if l["llm_label"] != l["band_target"]]

    groups: dict[str, list[str]] = defaultdict(list)
    for i, l in pairs:
        if l.get("parallel_group"):
            groups[l["parallel_group"]].append(i)
    inconsistent: list[str] = []
    for ids in groups.values():
        if len(ids) >= 2 and len({labels[i]["llm_label"] for i in ids}) > 1:
            inconsistent.extend(ids)

    agree_by_label: dict[str, list[str]] = defaultdict(list)
    for i, l in pairs:
        if l["llm_label"] == l["band_target"]:
            agree_by_label[l["llm_label"]].append(i)

    n_dis = min(len(disagree), int(args.count * 0.40))
    n_inc = min(len(inconsistent), int(args.count * 0.20))
    picked: list[tuple[str, str]] = []
    picked += [(i, "A: alvo != rotulo") for i in rng.sample(disagree, n_dis)]
    picked += [(i, "B: idiomas divergem") for i in rng.sample(inconsistent, n_inc)]

    remaining = max(0, args.count - len(picked))
    per_label = max(1, remaining // len(LABELS))
    for lab in LABELS:
        pool = [i for i in agree_by_label.get(lab, []) if i not in {p for p, _ in picked}]
        for i in rng.sample(pool, min(per_label, len(pool))):
            picked.append((i, f"C: baseline {lab}"))

    seen: set[str] = set()
    ordered = [(i, why) for i, why in picked if not (i in seen or seen.add(i))][: args.count]
    rng.shuffle(ordered)

    md = [
        "# Revisao manual dos rotulos de senioridade",
        "",
        f"{len(ordered)} curriculos. Para cada um: leia o texto, decida o nivel, e anote em",
        "`review_verdicts.jsonl` (campo `verdict`): `intern`, `junior`, `mid`, `senior`,",
        "ou `ok` se concorda com o rotulo do LLM.",
        "",
        "O rotulo do LLM e o alvo de geracao ficam no FIM de cada bloco, para nao ancorar a leitura.",
        "",
        "---",
        "",
    ]
    verdicts = []
    for n, (rid, why) in enumerate(ordered, 1):
        row = prose[rid]
        lab = labels[rid]
        text = resume_to_text_sanitized(row["resume_data"])
        md += [
            f"## {n}. `{rid}`  ({row['language']})",
            "",
            f"**Ocupacao:** {row['occupation']['label']}  |  **motivo da selecao:** {why}",
            "",
            "```",
            text.strip(),
            "```",
            "",
            f"<details><summary>rotulo do LLM</summary>",
            "",
            f"- LLM: **{lab['llm_label']}**",
            f"- alvo de geracao: {lab['band_target']}",
            "</details>",
            "",
            "---",
            "",
        ]
        verdicts.append(
            {
                "n": n,
                "id": rid,
                "language": row["language"],
                "llm_label": lab["llm_label"],
                "band_target": lab["band_target"],
                "reason": why,
                "verdict": "",
            }
        )

    (DATA_DIR / "review_sample.md").write_text("\n".join(md), encoding="utf-8")
    with (DATA_DIR / "review_verdicts.jsonl").open("w", encoding="utf-8") as fh:
        for v in verdicts:
            fh.write(json.dumps(v, ensure_ascii=False) + "\n")

    from collections import Counter

    print(f"rotulados disponiveis: {len(pairs)}")
    print(f"amostra: {len(ordered)}  ->  {DATA_DIR / 'review_sample.md'}")
    print("composicao:", dict(Counter(w.split(':')[0] for _, w in ordered)))
    print("por idioma:", dict(Counter(prose[i]["language"] for i, _ in ordered)))
    print("por rotulo do LLM:", dict(Counter(labels[i]["llm_label"] for i, _ in ordered)))


if __name__ == "__main__":
    main()
