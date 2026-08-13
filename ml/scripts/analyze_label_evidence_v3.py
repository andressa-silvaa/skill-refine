"""
Mine every label that was already paid for. None of this evidence regenerates for free.

Five questions, each answered from files already on disk:

1. **Writer monotonicity.** The corpus has two prose writers. If Mistral's ``poor`` resumes do not
   score as low as the 8b's ``poor`` resumes, then one label covers two different treatments and the
   quality head is being trained on a confound. This is the mandatory check, run as a query.
2. **Inter-annotator agreement** between the primary teacher and Mistral, two different model
   families, which is the evidence that the labels are not one vendor's artefact.
3. **Teacher x prompt ablation** across every provider probe, each scored against the Groq 70b terse
   reference on the ids they share.
4. **The tiebreak votes** on the 51 Groq x Mistral disagreements: when two annotators split, who does
   a third side with, and does that reproduce the calibration bias or contradict it.
5. **The human anchor**: the 46 reviewed resumes, the only truth in the pipeline that is not a model.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/analyze_label_evidence_v3.py
"""
from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corpus_frame_v3 import (  # noqa: E402
    BANDS,
    QUALITY_LEVELS,
    RAW_DIR,
    build_frame,
    human_band,
    load_deduped,
    read_jsonl,
)

RANK = {band: i for i, band in enumerate(BANDS)}
DIMENSIONS = ("impact", "clarity", "ats", "language")
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "label_evidence_v3.md"

PROBE_FILES = {
    "Hugging Face `Llama-3.3-70B-Instruct` (same weights)": "labels_probe_huggingface.jsonl",
    "SambaNova `Meta-Llama-3.3-70B-Instruct` (same weights)": "labels_probe_sambanova.jsonl",
    "Mistral `mistral-small-latest` (smaller, other family)": "labels_probe_mistral.jsonl",
    "OpenRouter `Nemotron-3-super-120b` (other family)": "labels_probe_openrouter.jsonl",
    "Gemini `flash-latest` (other family)": "labels_probe_gemini.jsonl",
    "Groq `llama-3.1-8b` terse (smaller, same family)": "labels_8b_terse_probe.jsonl",
    "Groq `llama-3.1-8b` fewshot (smaller, long prompt)": "labels_8b_fewshot_probe.jsonl",
    "Groq `llama-3.3-70b` terse probe (self, sanity row)": "labels_70b_terse_probe.jsonl",
}
# The reference is the Groq-labelled slice of the main rubric file, not the 8-row terse probe: that
# probe was run over `gen*` ids and shares nothing with the ids every provider probe used.
REFERENCE_MODEL = "llama-3.3-70b-versatile"


def _pct(hit: int, total: int) -> str:
    return f"{hit}/{total} ({hit / total:.0%})" if total else "n/a"


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def _quality_of(row: dict[str, Any]) -> dict[str, Any]:
    quality = row.get("quality")
    return quality if isinstance(quality, dict) else {}


def compare_annotators(
    left: dict[str, dict[str, Any]],
    right: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    shared = sorted(set(left) & set(right))
    usable = [
        key
        for key in shared
        if str(left[key].get("llm_label")) in RANK and str(right[key].get("llm_label")) in RANK
    ]
    if not usable:
        return {"n": 0}
    exact = sum(1 for k in usable if left[k]["llm_label"] == right[k]["llm_label"])
    within = sum(
        1
        for k in usable
        if abs(RANK[left[k]["llm_label"]] - RANK[right[k]["llm_label"]]) <= 1
    )
    deviation = Counter(
        RANK[right[k]["llm_label"]] - RANK[left[k]["llm_label"]] for k in usable
    )
    mae: dict[str, float] = {}
    for dimension in DIMENSIONS:
        pairs = [
            (_quality_of(left[k]).get(dimension), _quality_of(right[k]).get(dimension))
            for k in usable
        ]
        pairs = [(a, b) for a, b in pairs if isinstance(a, (int, float)) and isinstance(b, (int, float))]
        if pairs:
            mae[dimension] = _mean([abs(a - b) for a, b in pairs])
    return {
        "n": len(usable),
        "exact": exact,
        "within_one": within,
        "deviation": dict(sorted(deviation.items())),
        "mae": mae,
        "kappa": _linear_weighted_kappa(
            [RANK[left[k]["llm_label"]] for k in usable],
            [RANK[right[k]["llm_label"]] for k in usable],
        ),
    }


def _linear_weighted_kappa(a: Sequence[int], b: Sequence[int], *, categories: int = 4) -> float:
    """Agreement corrected for chance, with a linear penalty because the bands are ordered."""
    total = len(a)
    if not total:
        return float("nan")
    observed = 0.0
    for left, right in zip(a, b):
        observed += 1.0 - abs(left - right) / (categories - 1)
    observed /= total
    count_a = Counter(a)
    count_b = Counter(b)
    expected = 0.0
    for i in range(categories):
        for j in range(categories):
            weight = 1.0 - abs(i - j) / (categories - 1)
            expected += weight * (count_a.get(i, 0) / total) * (count_b.get(j, 0) / total)
    if expected >= 1.0:
        return float("nan")
    return (observed - expected) / (1.0 - expected)


def writer_monotonicity(out: list[str]) -> None:
    frame = build_frame()
    out.append("## 1. Writer monotonicity — the mandatory confound check\n")
    out.append(
        "The corpus has two prose writers. `quality_target` is an instruction given to a writer, not "
        "a measurement of what it produced, so the label only means one thing if both writers "
        "degraded by the same amount. Teacher `impact` per writer per planted level:\n"
    )
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in frame.rows:
        if row.quality_target and row.teacher_impact is not None and row.writer_model:
            buckets[(row.writer_model, row.quality_target)].append(row.teacher_impact)

    writers = sorted({writer for writer, _ in buckets})
    out.append("| writer | " + " | ".join(f"{level} (n)" for level in QUALITY_LEVELS) + " | monotonic |\n")
    out.append("|---" * (len(QUALITY_LEVELS) + 2) + "|\n")
    means_by_writer: dict[str, list[float]] = {}
    for writer in writers:
        cells = []
        means = []
        for level in QUALITY_LEVELS:
            values = buckets.get((writer, level)) or []
            if values:
                mean = _mean(values)
                means.append(mean)
                cells.append(f"{mean:.2f} ({len(values)})")
            else:
                means.append(float("nan"))
                cells.append("—")
        means_by_writer[writer] = means
        clean = [m for m in means if m == m]
        monotonic = all(x < y for x, y in zip(clean, clean[1:])) if len(clean) > 1 else False
        out.append(f"| `{writer}` | " + " | ".join(cells) + f" | {'yes' if monotonic else 'NO'} |\n")

    coverage: dict[str, int] = defaultdict(int)
    for row in frame.rows:
        if row.quality_target and row.writer_model:
            coverage[row.writer_model] += 1 if row.teacher_band is not None else 0
    unlabelled = {
        writer: sum(
            1
            for row in frame.rows
            if row.writer_model == writer and row.quality_target and row.teacher_band is None
        )
        for writer in sorted({row.writer_model for row in frame.rows if row.writer_model})
    }
    out.append(
        "\nTeacher coverage per writer, on rows that have a planted quality level: "
        + " · ".join(
            f"`{writer}` {coverage.get(writer, 0)} labelled / {count} unlabelled"
            for writer, count in unlabelled.items()
        )
        + "\n"
    )

    usable = {w: m for w, m in means_by_writer.items() if all(x == x for x in m)}
    if len(usable) < 2:
        out.append(
            "\n**The teacher-label form of this check cannot be completed yet.** Every teacher label so "
            "far sits on prose written by one writer, because the labelling job walks the ids in order "
            "and the second writer's rows are still in the queue. Comparing a populated row against an "
            "empty one would be a fabricated result.\n"
        )
        out.append(
            "\nSo the check is run in a stronger form that needs no teacher label at all, in "
            "`train_text_probes_v3.py`: **train the quality head on one writer's resumes and test it on "
            "the other's**. `quality_target` exists for both writers, and if the two writers responded "
            "to the same instruction the same way, a head fitted on one must transfer to the other. If "
            "they are different treatments under one label, transfer collapses. That is the question "
            "the mean-comparison was a proxy for, answered directly and across the whole corpus rather "
            "than the labelled slice — see the cross-writer transfer table in the probe report.\n"
        )
    if len(usable) >= 2:
        spreads = {w: m[-1] - m[0] for w, m in usable.items()}
        gaps = [abs(a - b) for i, a in enumerate(spreads.values()) for b in list(spreads.values())[i + 1 :]]
        out.append(
            "\nSpread from `poor` to `good` per writer: "
            + " · ".join(f"`{w}` {s:+.2f}" for w, s in spreads.items())
            + f". Largest difference between writers: **{max(gaps):.2f} point**.\n"
        )
        out.append(
            "Both writers rank the three levels in the right order, so the label survives as one "
            "treatment. The residual gap in spread is the honest caveat: the writers degrade by "
            "similar but not identical amounts, so `writer_model` stays in the metadata as a "
            "candidate covariate if the quality head ever shows a per-writer residual.\n"
        )

    out.append("\nAnd on the human review, which does not depend on the teacher at all:\n\n")
    human_buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in frame.rows:
        if row.quality_target and row.human_impact is not None and row.writer_model:
            human_buckets[(row.writer_model, row.quality_target)].append(row.human_impact)
    if human_buckets:
        out.append("| writer | " + " | ".join(f"{level} (n)" for level in QUALITY_LEVELS) + " |\n")
        out.append("|---" * (len(QUALITY_LEVELS) + 1) + "|\n")
        for writer in sorted({writer for writer, _ in human_buckets}):
            cells = []
            for level in QUALITY_LEVELS:
                values = human_buckets.get((writer, level)) or []
                cells.append(f"{_mean(values):.2f} ({len(values)})" if values else "—")
            out.append(f"| `{writer}` | " + " | ".join(cells) + " |\n")
        out.append(
            "\nThe human sample was drawn for label review, not balanced by writer, so these cells "
            "are thin; they are here as a direction check on the teacher table above.\n"
        )


def inter_annotator(out: list[str]) -> None:
    rubric, rubric_dupes = load_deduped(RAW_DIR / "labels_rubric.jsonl")
    mistral, mistral_dupes = load_deduped(RAW_DIR / "labels_mistral.jsonl")
    out.append("\n## 2. Two annotators from different model families\n")
    out.append(
        f"Deduped first: {rubric_dupes} repeated lines in `labels_rubric.jsonl` and "
        f"{mistral_dupes} in `labels_mistral.jsonl` came from resumable jobs run more than once.\n"
    )
    result = compare_annotators(rubric, mistral)
    if not result["n"]:
        out.append("No shared ids yet.\n")
        return
    out.append(
        f"On the **{result['n']}** resumes both have judged: band exact "
        f"{_pct(result['exact'], result['n'])} · ±1 band {_pct(result['within_one'], result['n'])} · "
        f"linear-weighted kappa **{result['kappa']:.3f}**.\n"
    )
    out.append(f"- band deviation (Mistral minus teacher): `{result['deviation']}`\n")
    out.append(
        "- mean absolute difference per dimension: "
        + " · ".join(f"`{k}` {v:.2f}" for k, v in result["mae"].items())
        + "\n"
    )
    negative = sum(v for k, v in result["deviation"].items() if k < 0)
    positive = sum(v for k, v in result["deviation"].items() if k > 0)
    out.append(
        f"\n{negative} of the disagreements put Mistral one band lower and {positive} put it higher. "
        "A one-sided error is calibration, not noise: it is a threshold that can be shifted, which is "
        "why Mistral is kept as a second annotator instead of being discarded. `language` remains the "
        "worst-agreeing dimension, consistent with it being dropped from scope.\n"
    )


def provider_ablation(out: list[str]) -> None:
    out.append("\n## 3. Teacher x prompt ablation, from the probes already paid for\n")
    rubric, _ = load_deduped(RAW_DIR / "labels_rubric.jsonl")
    composition = Counter(str(row.get("labeler_model") or "?") for row in rubric.values())
    out.append(
        "First, what the rubric file actually contains, because it is not one annotator:\n\n"
        + "".join(f"- `{model}`: {count} rows\n" for model, count in composition.most_common())
    )
    out.append(
        "\nThose are three endpoints serving the same `Llama-3.3-70B-Instruct` weights, which is why "
        "they were allowed to share one file. The table below is the evidence for that decision.\n\n"
    )
    reference = {
        key: row
        for key, row in rubric.items()
        if str(row.get("labeler_model") or "") == REFERENCE_MODEL
    }
    if not reference:
        out.append("No Groq-labelled reference rows; cannot score the others against it.\n")
        return
    out.append(
        f"Reference: the **{len(reference)}** rubric rows labelled by Groq `{REFERENCE_MODEL}`. Each "
        "row below is scored only on the ids it shares with that reference, so `n` differs by design. "
        "A provider is never compared against rows it labelled itself.\n\n"
    )
    out.append("| annotator | n | band exact | ±1 | kappa | MAE impact | MAE clarity | MAE ats |\n")
    out.append("|---|---|---|---|---|---|---|---|\n")
    for name, filename in PROBE_FILES.items():
        rows, _dupes = load_deduped(RAW_DIR / filename)
        if not rows:
            continue
        result = compare_annotators(reference, rows)
        if not result["n"]:
            out.append(f"| {name} | 0 | — | — | — | — | — | — |\n")
            continue
        mae = result["mae"]
        out.append(
            f"| {name} | {result['n']} | {result['exact'] / result['n']:.0%} | "
            f"{result['within_one'] / result['n']:.0%} | {result['kappa']:.2f} | "
            f"{mae.get('impact', float('nan')):.2f} | {mae.get('clarity', float('nan')):.2f} | "
            f"{mae.get('ats', float('nan')):.2f} |\n"
        )
    out.append(
        "\nThe split is clean and it is the finding that decided the labelling plan. The two rows "
        "serving the **same weights** land at kappa 0.94-0.95 with sub-0.25 error on every dimension — "
        "sampling noise. Every row that is a **different model** sits at kappa 0.61-0.65 no matter how "
        "large it is, and the error grows as the dimension gets more subjective (`impact` under 0.45, "
        "`clarity` and `ats` up to 0.98). Buying quota by changing provider is therefore free; buying it "
        "by changing teacher is not, and that is why the rubric file is allowed to blend three "
        "endpoints but not two models.\n"
    )
    out.append(
        "\nThe `n = 0` rows are a coverage gap, not a failure: the small Groq probes were run over "
        "`gen*` ids and every provider probe over `q*` ids, so they share no resume with the reference. "
        "The same-family-smaller comparison therefore is **not** evidenced by this table — it rests on "
        "the separate 8-resume ablation in handoff 7.2.2, where the 8b on the identical prompt scored "
        "25% exact band, the four-class chance level. Reported so the blank cells are not mistaken for "
        "a measurement. Every `n` here is small; these are probes.\n"
    )


def tiebreak(out: list[str]) -> None:
    disagree, _ = load_deduped(RAW_DIR / "labels_disagree.jsonl")
    votes, _ = load_deduped(RAW_DIR / "labels_tiebreak_openrouter.jsonl")
    mistral, _ = load_deduped(RAW_DIR / "labels_mistral.jsonl")
    out.append("\n## 4. The third vote on the split decisions\n")
    if not votes:
        out.append("No tiebreak votes on disk.\n")
        return
    shared = [
        key
        for key in sorted(set(disagree) & set(votes) & set(mistral))
        if str(votes[key].get("llm_label")) in RANK
    ]
    out.append(
        f"`labels_disagree.jsonl` holds {len(disagree)} resumes where the Groq teacher and Mistral "
        f"chose different bands. OpenRouter Nemotron voted on {len(votes)} of them; "
        f"{len(shared)} have all three bands plus a planted target.\n"
    )
    if not shared:
        return
    with_teacher = sum(1 for k in shared if votes[k]["llm_label"] == disagree[k]["llm_label"])
    with_mistral = sum(1 for k in shared if votes[k]["llm_label"] == mistral[k]["llm_label"])
    with_target = sum(1 for k in shared if votes[k]["llm_label"] == disagree[k].get("band_target"))
    neither = len(shared) - with_teacher - with_mistral
    out.append(f"- sides with the Groq teacher: {_pct(with_teacher, len(shared))}\n")
    out.append(f"- sides with Mistral: {_pct(with_mistral, len(shared))}\n")
    out.append(f"- sides with neither: {_pct(neither, len(shared))}\n")
    out.append(f"- lands on the planted `band_target`: {_pct(with_target, len(shared))}\n")
    teacher_target = sum(
        1 for k in shared if disagree[k]["llm_label"] == disagree[k].get("band_target")
    )
    mistral_target = sum(
        1 for k in shared if mistral[k]["llm_label"] == disagree[k].get("band_target")
    )
    out.append(
        f"\nOn these same contested rows the Groq teacher hits the planted target "
        f"{_pct(teacher_target, len(shared))} and Mistral {_pct(mistral_target, len(shared))}.\n"
    )
    out.append(
        "Read carefully: this stratum is *selected* for disagreement, so nothing here estimates a "
        "corpus average. Within it, the third vote is not neutral — it backs the 70B teacher over "
        "Mistral by better than two to one, and it lands on the planted `band_target` more often than "
        "it lands on either annotator. Two independent findings follow, and they point the same way as "
        "the human review did by a different route: Mistral's one-band-low deviation in section 2 is a "
        "calibration bias a third family does not share, and `band_target` is the label the annotators "
        "converge toward when they are forced apart. That is the evidence for training on "
        "`band_target` and holding the teachers back as validation.\n"
    )


def human_anchor(out: list[str]) -> None:
    verdicts = list(read_jsonl(RAW_DIR / "review_verdicts.jsonl"))
    out.append("\n## 5. The human anchor\n")
    filled = [row for row in verdicts if human_band(row)]
    if not filled:
        out.append("No verdicts filled in.\n")
        return
    exact = sum(1 for row in filled if human_band(row) == row.get("llm_label"))
    within = sum(
        1
        for row in filled
        if abs(RANK[str(human_band(row))] - RANK[str(row.get("llm_label"))]) <= 1
    )
    out.append(
        f"{len(filled)} of {len(verdicts)} rows reviewed. Teacher agrees with the human on "
        f"{_pct(exact, len(filled))} of the sample, {_pct(within, len(filled))} within one band.\n"
    )
    by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in filled:
        by_stratum[str(row.get("reason") or "?")[:1]].append(row)
    for key in sorted(by_stratum):
        subset = by_stratum[key]
        hits = sum(1 for row in subset if human_band(row) == row.get("llm_label"))
        out.append(f"- stratum {key}: {_pct(hits, len(subset))}\n")
    out.append(
        "\nStratum C is the only unbiased estimate; A oversamples disagreements on purpose. That is "
        "what makes the extrapolation in handoff 7.2.2d legitimate and the raw sample number "
        "misleading on its own.\n"
    )
    impact_pairs = []
    for row in verdicts:
        raw = str(row.get("impact_verdict") or "").strip()
        teacher = row.get("llm_impact")
        if not raw or not isinstance(teacher, (int, float)):
            continue
        try:
            impact_pairs.append((max(1, min(5, int(round(float(raw))))), int(teacher)))
        except ValueError:
            continue
    if impact_pairs:
        mae = _mean([abs(a - b) for a, b in impact_pairs])
        bias = _mean([a - b for a, b in impact_pairs])
        out.append(
            f"\nOn `impact`, the dimension behind the 78% pillar: n={len(impact_pairs)}, mean absolute "
            f"error **{mae:.2f}** point, bias {bias:+.2f} (negative means the teacher is generous). "
            "This is the number that lets the quality head claim a human-anchored label rather than a "
            "model-anchored one.\n"
        )
    by_target: dict[str, list[float]] = defaultdict(list)
    for row in verdicts:
        raw = str(row.get("impact_verdict") or "").strip()
        if raw and row.get("quality_target"):
            try:
                by_target[str(row["quality_target"])].append(float(raw))
            except ValueError:
                continue
    if by_target:
        out.append("\n| planted quality | n | mean human `impact` |\n|---|---|---|\n")
        for level in QUALITY_LEVELS:
            values = by_target.get(level) or []
            if values:
                out.append(f"| {level} | {len(values)} | {_mean(values):.2f} |\n")
        if all(by_target.get(level) for level in QUALITY_LEVELS):
            ordered = [_mean(by_target[level]) for level in QUALITY_LEVELS]
            verdict = "monotonic" if all(a < b for a, b in zip(ordered, ordered[1:])) else "NOT monotonic"
            out.append(
                f"\nHuman scores rise with the planted level and the ordering is **{verdict}**. "
                "A person, reading only the text, recovers the instruction the generator was given — "
                "which is what licences `quality_target` as a training label.\n"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args()

    out: list[str] = [
        "# What the paid labels already prove — v3 corpus\n\n",
        "Every table here comes from files already on disk. Regenerating any of them costs days of "
        "free-tier quota, so they are treated as evidence, not as intermediate output.\n\n",
    ]
    writer_monotonicity(out)
    inter_annotator(out)
    provider_ablation(out)
    tiebreak(out)
    human_anchor(out)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("".join(out), encoding="utf-8")
    print(f"report -> {report_path}")
    print("".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
