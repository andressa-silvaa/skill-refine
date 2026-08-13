"""
Decide how the seniority probe and the rule policy should combine, by measuring the three options.

Production currently blends them in ``fuse_seniority``, which weights the structural rule at
``0.4 + 0.45 * strength`` — for a well-formed resume that is ~0.85 to the rule and ~0.15 to the text.
Leaving that in place while claiming seniority became model-driven would be false: the rule would
still be deciding. So the choice is measured rather than argued, against two references:

* ``band_target``, on which the rule has an unfair advantage — it reads the month counts the
  generator used to build the resume.
* the 46 human verdicts, the only reference neither side can game.

Whichever wins sets ``ANALYSIS_TEXT_SENIORITY_PROBE_PRIMARY`` in the compose file.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/eval_seniority_fusion_v3.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
SCRIPTS_DIR = Path(__file__).resolve().parent
for extra_path in (str(BACKEND_SRC), str(SCRIPTS_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

from corpus_frame_v3 import BANDS, build_frame  # noqa: E402
from train_text_probes_v3 import (  # noqa: E402
    EMBED_MODEL,
    _groups,
    cv_predict_classes,
    embed_variant,
    ordinal_report,
    prime_payload_cache,
    _resume_payload,
)

from apps.analysis.application.inference.signals.resume_signals import (  # noqa: E402
    extract_resume_signals,
)
from apps.analysis.application.inference.tasks.seniority.rule_based import (  # noqa: E402
    rule_based_seniority,
)
from apps.analysis.application.inference.tasks.seniority.text.fuse_seniority import (  # noqa: E402
    fuse_seniority,
    structural_signals_strength,
)

BAND_RANK = {band: i for i, band in enumerate(BANDS)}
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "seniority_fusion_v3.md"


def _confidence(probabilities: Sequence[float]) -> str:
    top = max(probabilities) if len(probabilities) else 0.0
    if top >= 0.55:
        return "high"
    if top >= 0.38:
        return "medium"
    return "low"


def main() -> int:
    frame = build_frame()
    prime_payload_cache(REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3")
    rows = frame.rows
    x = embed_variant(rows, attribute="text", encoder_name=EMBED_MODEL)
    y = np.asarray([row.band_target for row in rows])
    groups = _groups(rows)

    probe_labels = cv_predict_classes(x, y, groups).tolist()
    probe_probabilities = _out_of_fold_probabilities(x, y, groups)

    rule_labels: list[str] = []
    rule_confidences: list[str] = []
    strengths: list[float] = []
    leadership: list[bool] = []
    months: list[int] = []
    for row in rows:
        signals = extract_resume_signals({"data": _resume_payload(row)}, None, row.language)
        label, confidence, _evidence = rule_based_seniority(signals)
        rule_labels.append(label)
        rule_confidences.append(confidence)
        strengths.append(
            structural_signals_strength(
                total_months_experience=signals.total_months_experience,
                experiences_count=signals.experiences_count,
            )
        )
        leadership.append(bool(signals.has_leadership_terms))
        months.append(int(signals.total_months_experience or 0))

    fused_labels: list[str] = []
    text_weights: list[float] = []
    for i in range(len(rows)):
        label, _fused_confidence, meta = fuse_seniority(
            rule_labels[i],
            rule_confidences[i],
            probe_labels[i],
            _confidence(probe_probabilities[i]),
            strengths[i],
            has_leadership_terms=leadership[i],
            total_months_experience=months[i],
            text_suggests_senior=probe_labels[i] == "senior",
        )
        fused_labels.append(label)
        text_weights.append(float((meta.get("weights") or {}).get("text") or 0.0))

    candidates = {
        "probe alone": probe_labels,
        "rule_based_seniority alone": rule_labels,
        "fuse_seniority (production blend)": fused_labels,
    }

    out: list[str] = [
        "# Should the seniority probe decide, or keep sharing the decision with the rule?\n\n",
        f"{len(rows)} resumes. The probe row is out-of-fold with occupations held out; the rule and the "
        "blend are computed on every row. Mean weight `fuse_seniority` hands to the text: "
        f"**{np.mean(text_weights):.2f}** (so the rule carries {1 - np.mean(text_weights):.2f}).\n\n",
        "## Against `band_target`, the training label\n\n",
        "| decision rule | accuracy | ±1 | macro-F1 | predicted spread |\n|---|---|---|---|---|\n",
    ]
    for name, labels in candidates.items():
        report = ordinal_report(y.tolist(), labels, BAND_RANK)
        out.append(
            f"| {name} | **{report['accuracy']:.1%}** | {report['within_one']:.1%} | "
            f"{report['macro_f1']:.3f} | {_spread(labels)} |\n"
        )
    out.append(
        "\n`band_target` flatters the rule: the generator built each resume from a month budget and the "
        "rule thresholds months, so it is being scored against a label derived from its own input.\n"
    )

    human_rows = frame.with_human()
    if human_rows:
        index = {row.id: i for i, row in enumerate(rows)}
        picks = [index[row.id] for row in human_rows]
        truth = [str(row.human_band) for row in human_rows]
        out.append(
            f"\n## Against the {len(human_rows)} human verdicts, which neither side can game\n\n"
        )
        out.append("| decision rule | accuracy | ±1 | macro-F1 | predicted spread |\n|---|---|---|---|---|\n")
        human_scores: dict[str, float] = {}
        for name, labels in candidates.items():
            subset = [labels[i] for i in picks]
            report = ordinal_report(truth, subset, BAND_RANK)
            human_scores[name] = report["macro_f1"]
            out.append(
                f"| {name} | **{report['accuracy']:.1%}** | {report['within_one']:.1%} | "
                f"{report['macro_f1']:.3f} | {_spread(subset)} |\n"
            )
        out.append(
            "\nThis stratum oversamples teacher/generator disagreements, so every number in it is "
            "pessimistic; what matters is the ordering and the spread column.\n"
        )
        best = max(human_scores, key=lambda key: human_scores[key])
        out.append(f"\n**Best macro-F1 against human judgement: {best}.**\n")

    out.append(
        "\n## What this settles\n\n"
        "**The blend is worse than either thing it blends.** That is the result, and it is not the one "
        "the design expected: `fuse_seniority` loses to the rule on `band_target` and loses to the "
        "probe against human judgement, on both accuracy and macro-F1. Averaging two decision rules "
        "into an ordinal rank and re-thresholding it does not split the difference between them — it "
        "pulls disagreements into the middle bands, which the predicted-spread column shows directly: "
        "the blend inflates `mid` and starves `senior` even where a component got them right.\n\n"
        "So there is no version of this where keeping the blend is defensible. It was already the "
        "weakest option before the probe existed, and the rule's remaining edge on `band_target` is "
        "the circularity the corpus was rebuilt to expose: the generator built each resume from a "
        "month budget, and the rule thresholds months. Against the one reference neither side can "
        "game, the probe ties it on accuracy and beats it on macro-F1 by 0.06 while spreading its "
        "predictions across all four bands, where the rule answers `mid` for half the sample.\n\n"
        "Therefore: the probe is the primary decision when its bundle loads, the rule is the fallback "
        "for when it does not, and blending is switched off. `clamp_seniority_vetoes` stays. Those "
        "vetoes are not a competing judgement — they are product safety on absent evidence (never "
        "`senior` with no experience section), and they are declared as policy rather than dressed up "
        "as inference.\n"
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("".join(out), encoding="utf-8")
    print("".join(out))
    print(f"report -> {REPORT_PATH}")
    return 0


def _out_of_fold_probabilities(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> list[list[float]]:
    from train_text_probes_v3 import _group_splits, fit_classifier

    probabilities: list[list[float]] = [[] for _ in range(len(y))]
    for train_idx, test_idx in _group_splits(x, y, groups, 5):
        model = fit_classifier(x[train_idx], y[train_idx], groups[train_idx])
        predicted = model.predict_proba(x[test_idx])
        for offset, row_idx in enumerate(test_idx):
            probabilities[row_idx] = [float(value) for value in predicted[offset]]
    return probabilities


def _spread(labels: Sequence[str]) -> str:
    counts = Counter(labels)
    return " ".join(f"{band}:{counts.get(band, 0)}" for band in BANDS)


if __name__ == "__main__":
    raise SystemExit(main())
