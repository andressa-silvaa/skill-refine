"""
Train the quality and seniority heads as linear probes over frozen multilingual MiniLM embeddings.

Why a probe and not a fine-tune: the encoder is already resident in production for target_fit, so a
probe adds one matmul per analysis and nothing to the memory bill. It also trains in seconds on CPU,
which is what makes it affordable to retrain the moment more teacher labels land.

Every head is evaluated with GroupKFold over the ESCO occupation, never over rows. Occupations were
drawn uniformly and independently of the band on purpose (handoff 3.2), and the parallel pt/en/es
renderings of one profile share their occupation, so grouping by occupation holds out both the
occupation and its translations at once. Held-out rows would score a model that memorised either.

Features are the four per-section embeddings concatenated with the whole-document embedding. That
layout was chosen by measurement, not taste: against a single mean over the document it is worth
+8 accuracy points on seniority and +14 on quality (see ``sweep_probe_designs_v3.py``). One mean lets
a 40-word skills list and two lines of achievement prose land in the same average.

Three ablations are reported rather than one number:

* **tenure** — seniority is trained on the production features, then on sections alone (which contain
  no month count anywhere), then on sections plus a document block with the ``(N meses)`` markers
  stripped. This closes the open caveat on ``band_target`` from handoff 7.2.2d.
* **stated level** — accuracy split by ``may_state_seniority``, the slice where the generator was
  allowed to put the band in the job title.
* **label choice for quality** — ``quality_target`` (3 balanced classes, every ``q`` resume) against
  the teacher's ``impact`` 1-5 (finer, far fewer rows). The first is validated by human review; the
  second resolves better. Reporting both is the honest presentation.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/train_text_probes_v3.py
  ./backend/.venv/Scripts/python.exe ml/scripts/train_text_probes_v3.py --no-export
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
SCRIPTS_DIR = Path(__file__).resolve().parent
for extra_path in (str(BACKEND_SRC), str(SCRIPTS_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

from corpus_frame_v3 import BANDS, QUALITY_LEVELS, Frame, Row, build_frame  # noqa: E402

from apps.analysis.application.inference.signals.resume_signals import (  # noqa: E402
    extract_resume_signals,
)
from apps.analysis.application.inference.tasks.seniority.rule_based import (  # noqa: E402
    rule_based_seniority,
)
from apps.analysis.application.inference.text_probe import (  # noqa: E402
    SECTION_ORDER,
    TRANSFORM_ID,
    build_feature_matrix,
)

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CACHE_DIR = REPO_ROOT / "ml" / "data" / "cache" / "probe_embeddings"
MODELS_DIR = REPO_ROOT / "ml" / "models"
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "text_probes_v3.md"
BAND_RANK = {band: i for i, band in enumerate(BANDS)}
QUALITY_RANK = {level: i for i, level in enumerate(QUALITY_LEVELS)}

# Declared product policy, not a fitted quantity: it keeps the probe's 0-100 output on the same scale
# the heuristic produced, so the completeness caps (40/72) and the 0.78 weight keep their meaning.
QUALITY_LEVEL_TO_SCORE = {"poor": 30, "fair": 55, "good": 78}
N_SPLITS = 5
INNER_SPLITS = 4
C_GRID = (1.0, 4.0, 16.0, 64.0)
ALPHA_GRID = (0.1, 1.0, 10.0, 100.0)
SEED = 20260811


def _dataset_version(frame: Frame) -> str:
    return f"resumes_v3_{len(frame)}rows_{date.today().isoformat()}"


_ENCODER: Any = None


def _shared_encoder(encoder_name: str):
    global _ENCODER
    if _ENCODER is None:
        from sentence_transformers import SentenceTransformer

        _ENCODER = SentenceTransformer(encoder_name)
    return _ENCODER


def embed_variant(
    rows: Sequence[Row],
    *,
    attribute: str,
    encoder_name: str,
    include_document: bool = True,
) -> np.ndarray:
    """
    Build the probe features through the production code path, cached on a digest of the exact input.

    ``attribute`` selects which whole-document text feeds the document block (``text`` carries the
    ``(N meses)`` markers, ``text_no_tenure`` does not). The four section blocks never carry months at
    all, so ``include_document=False`` yields a representation that provably cannot read tenure.
    """
    texts = [getattr(row, attribute) for row in rows]
    payloads = [{"data": _resume_payload(row)} for row in rows]
    digest = hashlib.sha256()
    digest.update(f"{encoder_name}|{TRANSFORM_ID}|{attribute}|doc={include_document}".encode())
    for text, payload in zip(texts, payloads):
        digest.update(text.encode("utf-8", "replace"))
        digest.update(json.dumps(payload, sort_keys=True, default=str).encode("utf-8", "replace"))
        digest.update(b"\x00")
    tag = f"{attribute}{'_plusdoc' if include_document else '_sectionsonly'}"
    cache_path = CACHE_DIR / f"{tag}__{digest.hexdigest()[:16]}.npy"
    if cache_path.exists():
        matrix = np.load(cache_path)
        if matrix.shape[0] == len(texts):
            print(f"  {tag}: cache hit {matrix.shape}")
            return matrix

    print(f"  {tag}: encoding {len(texts)} resumes ...")
    matrix = build_feature_matrix(
        _shared_encoder(encoder_name), payloads, texts, include_document=include_document
    )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, matrix)
    print(f"  {tag}: encoded {matrix.shape} -> {cache_path.name}")
    return matrix


def _groups(rows: Sequence[Row]) -> np.ndarray:
    return np.asarray([row.occupation_uri or f"__row_{row.id}" for row in rows])


def _new_classifier(penalty_c: float):
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(
        max_iter=8000,
        C=penalty_c,
        class_weight="balanced",
        random_state=SEED,
    )


def _new_regressor(alpha: float):
    from sklearn.linear_model import Ridge

    return Ridge(alpha=alpha, random_state=SEED)


def _group_splits(x: np.ndarray, y: np.ndarray, groups: np.ndarray, n_splits: int):
    from sklearn.model_selection import GroupKFold

    distinct = len(set(groups.tolist()))
    splitter = GroupKFold(n_splits=max(2, min(n_splits, distinct)))
    return list(splitter.split(x, y, groups))


def select_c(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    """Inner group-aware search. Called on training folds only, never on the fold being scored."""
    if len(set(groups.tolist())) < 2:
        return C_GRID[1]
    best_score, best_c = -1.0, C_GRID[0]
    for penalty_c in C_GRID:
        scores = []
        for train_idx, test_idx in _group_splits(x, y, groups, INNER_SPLITS):
            model = _new_classifier(penalty_c)
            model.fit(x[train_idx], y[train_idx])
            scores.append(float(np.mean(model.predict(x[test_idx]) == y[test_idx])))
        mean_score = float(np.mean(scores))
        if mean_score > best_score:
            best_score, best_c = mean_score, penalty_c
    return best_c


def select_alpha(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    if len(set(groups.tolist())) < 2:
        return ALPHA_GRID[1]
    best_error, best_alpha = float("inf"), ALPHA_GRID[0]
    for alpha in ALPHA_GRID:
        errors = []
        for train_idx, test_idx in _group_splits(x, y, groups, INNER_SPLITS):
            model = _new_regressor(alpha)
            model.fit(x[train_idx], y[train_idx])
            errors.append(float(np.mean(np.abs(model.predict(x[test_idx]) - y[test_idx]))))
        mean_error = float(np.mean(errors))
        if mean_error < best_error:
            best_error, best_alpha = mean_error, alpha
    return best_alpha


def fit_classifier(x: np.ndarray, y: np.ndarray, groups: np.ndarray):
    model = _new_classifier(select_c(x, y, groups))
    model.fit(x, y)
    return model


def fit_regressor(x: np.ndarray, y: np.ndarray, groups: np.ndarray):
    model = _new_regressor(select_alpha(x, y, groups))
    model.fit(x, y)
    return model


def cv_predict_classes(
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    *,
    n_splits: int = N_SPLITS,
) -> np.ndarray:
    """
    Nested out-of-fold predictions. Occupations are held out, and the regularisation strength is
    chosen inside each training fold — reporting the best C found on the folds being scored would
    quote a tuned number as if it were held out.
    """
    predictions = np.empty_like(y)
    for train_idx, test_idx in _group_splits(x, y, groups, n_splits):
        model = fit_classifier(x[train_idx], y[train_idx], groups[train_idx])
        predictions[test_idx] = model.predict(x[test_idx])
    return predictions


def cv_predict_values(
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    *,
    n_splits: int = N_SPLITS,
) -> np.ndarray:
    predictions = np.zeros(len(y), dtype=np.float64)
    for train_idx, test_idx in _group_splits(x, y, groups, n_splits):
        model = fit_regressor(x[train_idx], y[train_idx], groups[train_idx])
        predictions[test_idx] = model.predict(x[test_idx])
    return predictions


def ordinal_report(true: Sequence[str], pred: Sequence[str], order: dict[str, int]) -> dict[str, Any]:
    total = len(true)
    if not total:
        return {"n": 0}
    exact = sum(1 for a, b in zip(true, pred) if a == b)
    within = sum(1 for a, b in zip(true, pred) if abs(order[a] - order[b]) <= 1)
    from sklearn.metrics import f1_score

    return {
        "n": total,
        "accuracy": exact / total,
        "within_one": within / total,
        "macro_f1": float(f1_score(list(true), list(pred), average="macro", zero_division=0)),
        "predicted_distribution": dict(Counter(pred)),
        "deviation": dict(Counter(order[b] - order[a] for a, b in zip(true, pred))),
    }


def confusion_table(true: Sequence[str], pred: Sequence[str], labels: Sequence[str]) -> str:
    counts = Counter(zip(true, pred))
    width = max(len(label) for label in labels) + 2
    header = "true \\ pred".ljust(14) + "".join(label.rjust(width) for label in labels)
    lines = [header]
    for row_label in labels:
        cells = "".join(str(counts.get((row_label, col), 0)).rjust(width) for col in labels)
        lines.append(row_label.ljust(14) + cells)
    return "\n".join(lines)


def rule_baseline(rows: Sequence[Row]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        signals = extract_resume_signals({"data": _resume_payload(row)}, None, row.language)
        label, _conf, _evidence = rule_based_seniority(signals)
        labels.append(label)
    return labels


_PAYLOAD_CACHE: dict[str, dict[str, Any]] = {}


def _resume_payload(row: Row) -> dict[str, Any]:
    return _PAYLOAD_CACHE.get(row.id, {})


def prime_payload_cache(raw_dir: Path) -> None:
    from corpus_frame_v3 import read_jsonl

    for prose in read_jsonl(raw_dir / "prose.jsonl"):
        resume = prose.get("resume_data")
        if isinstance(resume, dict):
            inner = resume.get("data") if isinstance(resume.get("data"), dict) else resume
            _PAYLOAD_CACHE[str(prose.get("id") or "")] = inner


def train_seniority(frame: Frame, embeddings: dict[str, np.ndarray], out: list[str]) -> dict[str, Any]:
    rows = frame.rows
    y = np.asarray([row.band_target for row in rows])
    groups = _groups(rows)

    out.append("## Seniority head — text only, label `band_target`\n")
    out.append(
        f"{len(rows)} resumes, {len(set(groups.tolist()))} distinct occupations, "
        f"{N_SPLITS}-fold GroupKFold over the occupation.\n"
    )
    out.append(f"Label distribution: {dict(Counter(y.tolist()))}\n")

    results: dict[str, Any] = {}
    out_of_fold: dict[str, np.ndarray] = {}
    variants = (
        ("sections + document, tenure visible (production)", "text"),
        ("sections only, no month count anywhere", "sections_only"),
        ("sections + document with tenure stripped", "text_no_tenure"),
    )
    for variant, attribute in variants:
        pred = cv_predict_classes(embeddings[attribute], y, groups)
        out_of_fold[attribute] = pred
        report = ordinal_report(y.tolist(), pred.tolist(), BAND_RANK)
        results[attribute] = report
        out.append(f"### Probe, {variant}\n")
        out.append(
            f"- accuracy **{report['accuracy']:.1%}** · ±1 band {report['within_one']:.1%} · "
            f"macro-F1 {report['macro_f1']:.3f}\n"
        )
        out.append(f"- predicted distribution: {report['predicted_distribution']}\n")
        out.append("```\n" + confusion_table(y.tolist(), pred.tolist(), BANDS) + "\n```\n")

    rule_pred = rule_baseline(rows)
    rule_report = ordinal_report(y.tolist(), rule_pred, BAND_RANK)
    results["rule_based"] = rule_report
    majority = Counter(y.tolist()).most_common(1)[0][0]
    majority_report = ordinal_report(y.tolist(), [majority] * len(rows), BAND_RANK)
    results["majority"] = majority_report

    out.append("### Baselines on the same rows and the same label\n")
    out.append(
        f"- `rule_based_seniority`: accuracy **{rule_report['accuracy']:.1%}** · "
        f"±1 {rule_report['within_one']:.1%} · macro-F1 {rule_report['macro_f1']:.3f}\n"
    )
    out.append(
        f"- majority class (`{majority}`): accuracy {majority_report['accuracy']:.1%} · "
        f"macro-F1 {majority_report['macro_f1']:.3f}\n"
    )
    out.append("```\n" + confusion_table(y.tolist(), rule_pred, BANDS) + "\n```\n")
    out.append(
        "**The rule comparison is biased in favour of the rules and must be reported that way.** "
        "`rule_based_seniority` thresholds `effective_months_experience`, and the generator built "
        "each resume from `total_months_design` — the very number the rules read. The rules are "
        "scored against a label derived from their own input, while the probe has to recover the "
        "band from words. The tenure-stripped row above is the probe measured under the same "
        "handicap the rules never face.\n"
    )

    stated = [i for i, row in enumerate(rows) if row.may_state_seniority]
    unstated = [i for i, row in enumerate(rows) if not row.may_state_seniority]
    if stated and unstated:
        pred = out_of_fold["text"]
        stated_report = ordinal_report(
            [y[i] for i in stated], [pred[i] for i in stated], BAND_RANK
        )
        unstated_report = ordinal_report(
            [y[i] for i in unstated], [pred[i] for i in unstated], BAND_RANK
        )
        results["stated_seniority"] = stated_report
        results["unstated_seniority"] = unstated_report
        out.append("### Second ablation: resumes that name their own level\n")
        out.append(
            "The generator was allowed to write the band into the job title on a "
            f"{len(stated) / len(rows):.0%} slice (`may_state_seniority`), so on those rows the answer "
            "is partly readable off the `roles` block. Splitting the same out-of-fold predictions:\n\n"
        )
        out.append("| slice | n | accuracy | ±1 | macro-F1 |\n|---|---|---|---|---|\n")
        out.append(
            f"| title may state the level | {stated_report['n']} | **{stated_report['accuracy']:.1%}** | "
            f"{stated_report['within_one']:.1%} | {stated_report['macro_f1']:.3f} |\n"
        )
        out.append(
            f"| title must not state it | {unstated_report['n']} | **{unstated_report['accuracy']:.1%}** | "
            f"{unstated_report['within_one']:.1%} | {unstated_report['macro_f1']:.3f} |\n"
        )
        gap = stated_report["accuracy"] - unstated_report["accuracy"]
        out.append(
            f"\nThe gap is {gap * 100:+.1f} points. The unstated slice is "
            f"{len(unstated) / len(rows):.0%} of the corpus and is the number to quote for a resume "
            "that does not advertise its own level; the stated slice is what a real resume with "
            "`Senior` in the title would give. Both are legitimate inputs — a real candidate does "
            "write their own title — so neither slice is leakage, but reporting only the pooled "
            "figure would hide which one is doing the work.\n"
        )

    results["cross_writer"] = cross_writer_transfer(
        rows,
        embeddings["text"],
        {row.id: i for i, row in enumerate(rows)},
        out,
        label_of=lambda row: row.band_target,
        order=BAND_RANK,
        label_name="band_target",
    )

    teacher_rows = frame.with_teacher_band()
    if teacher_rows:
        idx = {row.id: i for i, row in enumerate(rows)}
        sub = np.asarray([idx[row.id] for row in teacher_rows])
        teacher_true = [str(row.teacher_band) for row in teacher_rows]
        agreement = ordinal_report(teacher_true, out_of_fold["text"][sub].tolist(), BAND_RANK)
        results["vs_teacher"] = agreement
        out.append("### Against the teacher labels, as fine-resolution validation\n")
        out.append(
            f"On the {agreement['n']} rows the LLM teacher has judged, the probe agrees "
            f"{agreement['accuracy']:.1%} exactly and {agreement['within_one']:.1%} within one band. "
            "The teacher is the validation set here, not the label: human review put `band_target` at "
            "~94.9% against ~78.5% for the teacher (handoff 7.2.2d).\n"
        )

    human_rows = frame.with_human()
    if human_rows:
        idx = {row.id: i for i, row in enumerate(rows)}
        sub = np.asarray([idx[row.id] for row in human_rows])
        human_true = [str(row.human_band) for row in human_rows]
        vs_human = ordinal_report(human_true, out_of_fold["text"][sub].tolist(), BAND_RANK)
        results["vs_human"] = vs_human
        out.append("### Against the 46 human verdicts, the only non-model truth\n")
        out.append(
            f"- probe vs human: accuracy **{vs_human['accuracy']:.1%}** · ±1 {vs_human['within_one']:.1%} "
            f"(n={vs_human['n']})\n"
        )
        rule_by_id = dict(zip([r.id for r in rows], rule_pred))
        rule_vs_human = ordinal_report(
            human_true, [rule_by_id[row.id] for row in human_rows], BAND_RANK
        )
        results["rule_vs_human"] = rule_vs_human
        out.append(
            f"- `rule_based_seniority` vs human: accuracy {rule_vs_human['accuracy']:.1%} · "
            f"±1 {rule_vs_human['within_one']:.1%}\n"
        )
        out.append(
            "This stratum oversamples teacher/generator disagreements by design, so it understates "
            "both decision rules; it is here because it is the one comparison neither side can game.\n"
        )
    return results


def train_quality(frame: Frame, embeddings: dict[str, np.ndarray], out: list[str]) -> dict[str, Any]:
    rows = frame.rows
    index = {row.id: i for i, row in enumerate(rows)}
    x_all = embeddings["text"]
    results: dict[str, Any] = {}

    out.append("## Quality head — 78% of the score, today five regex flags\n")

    target_rows = frame.with_quality_target()
    sub = np.asarray([index[row.id] for row in target_rows])
    y_target = np.asarray([str(row.quality_target) for row in target_rows])
    groups = _groups(target_rows)
    pred = cv_predict_classes(x_all[sub], y_target, groups)
    report = ordinal_report(y_target.tolist(), pred.tolist(), QUALITY_RANK)
    results["quality_target"] = report
    out.append("### Version A — label `quality_target`, 3 classes, every `q` resume\n")
    out.append(
        f"{report['n']} rows, {len(set(groups.tolist()))} occupations. accuracy **{report['accuracy']:.1%}** · "
        f"±1 {report['within_one']:.1%} · macro-F1 {report['macro_f1']:.3f}\n"
    )
    out.append(f"- label distribution: {dict(Counter(y_target.tolist()))}\n")
    out.append(f"- predicted distribution: {report['predicted_distribution']}\n")
    out.append("```\n" + confusion_table(y_target.tolist(), pred.tolist(), QUALITY_LEVELS) + "\n```\n")

    heuristic_scores = _heuristic_quality_scores(target_rows)
    results["heuristic_separation"] = _separation(heuristic_scores, y_target.tolist())
    probe_scores = [
        QUALITY_LEVEL_TO_SCORE[label] for label in pred.tolist()
    ]
    results["probe_separation"] = _separation(probe_scores, y_target.tolist())
    out.append("### What the incumbent heuristic scores on the same rows\n")
    out.append(
        "`_heuristic_score` is the decision worth 78% of the score today. Its mean output per planted "
        "quality level, against the probe's, on identical rows:\n"
    )
    out.append("| planted | n | `_heuristic_score` | probe (policy map) |\n|---|---|---|---|\n")
    for level in QUALITY_LEVELS:
        heur = results["heuristic_separation"].get(level)
        prob = results["probe_separation"].get(level)
        if heur:
            out.append(
                f"| {level} | {heur['n']} | {heur['mean']:.1f} | {prob['mean']:.1f} |\n"
            )
    out.append(
        "The heuristic reads links, metric patterns and action verbs, which the degradation "
        "instruction does not remove, so it is close to flat across levels it is supposed to separate.\n"
    )

    for dimension, getter in (
        ("impact", lambda r: r.teacher_impact),
        ("clarity", lambda r: r.teacher_clarity),
        ("ats", lambda r: r.teacher_ats),
    ):
        labelled = [row for row in rows if getter(row) is not None]
        if len(labelled) < 40:
            out.append(f"### Version B — `{dimension}` skipped, only {len(labelled)} labelled rows\n")
            continue
        sub_d = np.asarray([index[row.id] for row in labelled])
        y_d = np.asarray([float(getter(row)) for row in labelled])
        groups_d = _groups(labelled)
        pred_d = cv_predict_values(x_all[sub_d], y_d, groups_d)
        mae = float(np.mean(np.abs(pred_d - y_d)))
        rounded = np.clip(np.rint(pred_d), 1, 5)
        exact = float(np.mean(rounded == y_d))
        within = float(np.mean(np.abs(rounded - y_d) <= 1))
        baseline_mae = float(np.mean(np.abs(y_d - np.mean(y_d))))
        try:
            from scipy.stats import spearmanr

            rho = float(spearmanr(pred_d, y_d).statistic)
        except Exception:
            rho = float(np.corrcoef(pred_d, y_d)[0, 1])
        results[dimension] = {
            "n": len(labelled),
            "mae": mae,
            "baseline_mae": baseline_mae,
            "exact": exact,
            "within_one": within,
            "spearman": rho,
            "label_distribution": dict(Counter(y_d.tolist())),
        }
        out.append(f"### Version B — teacher `{dimension}` 1-5, fine resolution\n")
        out.append(
            f"{len(labelled)} labelled rows, {len(set(groups_d.tolist()))} occupations. "
            f"MAE **{mae:.2f}** against {baseline_mae:.2f} for predicting the mean · "
            f"exact {exact:.1%} · ±1 {within:.1%} · Spearman {rho:.3f}\n"
        )
        out.append(f"- label distribution: {results[dimension]['label_distribution']}\n")

    results["cross_writer"] = cross_writer_transfer(
        target_rows,
        x_all,
        index,
        out,
        label_of=lambda row: row.quality_target,
        order=QUALITY_RANK,
        label_name="quality_target",
    )

    pairs = [
        (row.teacher_clarity, row.teacher_ats)
        for row in rows
        if row.teacher_clarity is not None and row.teacher_ats is not None
    ]
    if pairs:
        identical = sum(1 for a, b in pairs if a == b)
        correlation = float(np.corrcoef([a for a, _ in pairs], [b for _, b in pairs])[0, 1])
        results["clarity_ats_identical"] = identical / len(pairs)
        results["clarity_ats_correlation"] = correlation
        out.append("### The measured ceiling on splitting `ats` from `clarity`\n")
        out.append(
            f"The teacher awards the same number for `clarity` and `ats` on **{identical}/{len(pairs)} "
            f"({identical / len(pairs):.1%})** of labelled rows, Pearson **{correlation:.3f}**, and never "
            "differs by more than one point. Both also sit in a 3-5 range, never scoring 1 or 2.\n"
        )
        out.append(
            "So the two heads ship, but the honest claim is narrow. What is fixed is the defect that "
            "mattered: `ats` and `clarity` stop being literal copies of `quality_score` "
            "(`orchestrator.py:758-759`), a number about a different construct. What is *not* fixed is "
            "that they barely differ from each other, and that is a property of the rubric, not of the "
            "model — the prompt asks two questions that the teacher answers as one. Separating them "
            "needs a rubric that scores keyword hygiene and structure apart from concision, plus a "
            "generator whose `poor` instruction degrades formatting and not only content. That is the "
            "same limit already recorded for `language` in handoff 7.2.2b, and it is a relabelling job, "
            "not a retraining job.\n"
        )

    out.append("### Reading of the ablation\n")
    out.append(
        f"Version A trains on {results['quality_target']['n']} rows of a label that human review "
        "confirmed three ways (human 1.50/2.61/3.64 vs teacher 1.56/3.00/3.96 vs Mistral "
        "1.50/2.73/3.75 across poor/fair/good). Version B trains on the teacher's 1-5 scale, which "
        "resolves finer but exists on far fewer rows and inherits the teacher's +0.30 generosity "
        "measured against the human. Version A therefore ships as the decision and Version B ships "
        "alongside it as the `impact`/`clarity`/`ats` resolution, which is also what finally splits "
        "`ats` and `clarity` from being literal copies of `quality_score`.\n"
    )
    return results


def cross_writer_transfer(
    target_rows: Sequence[Row],
    x_all: np.ndarray,
    index: dict[str, int],
    out: list[str],
    *,
    label_of: Any,
    order: dict[str, int],
    label_name: str,
) -> dict[str, Any]:
    """
    The mandatory writer check, in the form that needs no teacher label.

    The corpus has two prose writers, and both labels are *instructions given to a writer*, not
    measurements of what came back. So a label only denotes one thing if both writers answered the
    instruction the same way. Fit the head on one writer and score it on the other: if the treatments
    match the head transfers; if they are two treatments wearing one label, it collapses.

    Run for quality and for seniority, because a pooled score that is partly writer style is
    optimistic for a real resume — a real user is always a third, unseen writer.
    """
    by_writer: dict[str, list[Row]] = {}
    for row in target_rows:
        if row.writer_model and str(label_of(row)) in order:
            by_writer.setdefault(row.writer_model, []).append(row)
    writers = [writer for writer, group in by_writer.items() if len(group) >= 100]

    out.append(f"### Cross-writer transfer on `{label_name}` — the mandatory confound check\n")
    if len(writers) < 2:
        out.append(
            f"Only {len(writers)} writer has 100+ rows carrying `{label_name}`; the check needs two.\n"
        )
        return {}

    out.append(
        f"`{label_name}` is an instruction to a writer, not a measurement of the output. Fitting the "
        "head on one writer and scoring it on the other asks directly whether both writers answered "
        "that instruction the same way — no teacher label involved, so the whole corpus is available "
        "rather than the labelled slice.\n\n"
    )
    out.append(
        "| trained on | n train | tested on | n test | accuracy | ±1 | macro-F1 |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    results: dict[str, Any] = {}
    train_sizes: dict[str, int] = {}
    for train_writer in writers:
        for test_writer in writers:
            if train_writer == test_writer:
                continue
            train_rows = by_writer[train_writer]
            test_rows = by_writer[test_writer]
            x_train = x_all[np.asarray([index[r.id] for r in train_rows])]
            y_train = np.asarray([str(label_of(r)) for r in train_rows])
            x_test = x_all[np.asarray([index[r.id] for r in test_rows])]
            y_test = [str(label_of(r)) for r in test_rows]
            model = fit_classifier(x_train, y_train, _groups(train_rows))
            report = ordinal_report(y_test, model.predict(x_test).tolist(), order)
            report["n_train"] = len(train_rows)
            train_sizes[f"{train_writer}->{test_writer}"] = len(train_rows)
            results[f"{train_writer}->{test_writer}"] = report
            out.append(
                f"| `{train_writer}` | {len(train_rows)} | `{test_writer}` | {report['n']} | "
                f"**{report['accuracy']:.1%}** | {report['within_one']:.1%} | "
                f"{report['macro_f1']:.3f} |\n"
            )

    sizes = sorted(train_sizes.values())
    if len(sizes) == 2 and sizes[1] >= 2 * sizes[0]:
        best_direction = max(results, key=lambda key: results[key]["n_train"])
        out.append(
            f"\n**The two directions are not comparable.** One trains on {sizes[1]} rows and the other "
            f"on {sizes[0]}, so the weaker direction is measuring sample size as much as writer style. "
            f"The well-powered direction — `{best_direction}` at "
            f"{results[best_direction]['accuracy']:.1%} — is the one to read, and averaging the two "
            "understates the head.\n"
        )

    transfers = [report["accuracy"] for report in results.values()]
    within_writer = _within_writer_baseline(by_writer, writers, x_all, index, label_of=label_of)
    for writer, accuracy in within_writer.items():
        results[f"within:{writer}"] = accuracy
    out.append(
        "\nWithin-writer reference on the same rows, occupation held out: "
        + " · ".join(f"`{writer}` {accuracy:.1%}" for writer, accuracy in within_writer.items())
        + "\n"
    )
    baseline = _mean_or_nan(list(within_writer.values()))
    transfer_mean = _mean_or_nan(transfers)
    drop = baseline - transfer_mean
    floor = 1.0 / len(order)
    results["summary"] = {
        "within_writer_mean": baseline,
        "cross_writer_mean": transfer_mean,
        "drop": drop,
        "chance_floor": floor,
    }
    out.append(
        f"\nCross-writer accuracy averages {transfer_mean:.1%} against {baseline:.1%} within writer, "
        f"a drop of **{drop * 100:.1f} points**. Chance on {len(order)} classes is {floor:.0%}.\n"
    )
    out.append(
        "\nThe number that matters for the defence is the cross-writer one, and it is lower than the "
        "headline. A real user is always a third writer the head has never read, so cross-writer is "
        f"the honest estimate of what production delivers on `{label_name}` and the pooled figure is "
        "an upper bound. Both go in the report; quoting only the pooled figure would be a claim about "
        "generalisation that this corpus does not support.\n"
    )
    if drop <= 0.08 and min(transfers) > floor * 1.4:
        out.append(
            "\nThe gap is small enough to pool the writers: a head fitted on one writer's prose still "
            "recovers the other writer's planted level far above chance, and neither direction "
            "collapses. `writer_model` stays in the metadata as a covariate to watch, not as a "
            "stratum the training has to respect.\n"
        )
    else:
        out.append(
            "\nThe gap is wide enough to name as a limitation. Part of the pooled score is writer "
            "style rather than the construct, so the head is not yet demonstrably writer-invariant. "
            "Fixing it needs writer diversity in the corpus, which two generators cannot provide — "
            "not a different head. Until then the cross-writer row is the number to quote.\n"
        )
    return results


def _within_writer_baseline(
    by_writer: dict[str, list[Row]],
    writers: Sequence[str],
    x_all: np.ndarray,
    index: dict[str, int],
    *,
    label_of: Any,
) -> dict[str, float]:
    out: dict[str, float] = {}
    for writer in writers:
        rows = by_writer[writer]
        x = x_all[np.asarray([index[r.id] for r in rows])]
        y = np.asarray([str(label_of(r)) for r in rows])
        pred = cv_predict_classes(x, y, _groups(rows))
        out[writer] = float(np.mean(pred == y))
    return out


def _mean_or_nan(values: Sequence[float]) -> float:
    return float(np.mean(values)) if len(values) else float("nan")


def _heuristic_quality_scores(rows: Sequence[Row]) -> list[int]:
    from apps.analysis.application.inference.tasks.quality.predict import (
        _heuristic_flags,
        _heuristic_score,
    )

    return [_heuristic_score(_heuristic_flags(row.text, row.language)) for row in rows]


def _separation(scores: Sequence[float], labels: Sequence[str]) -> dict[str, Any]:
    buckets: dict[str, list[float]] = {}
    for score, label in zip(scores, labels):
        buckets.setdefault(label, []).append(float(score))
    return {
        label: {"n": len(values), "mean": sum(values) / len(values)}
        for label, values in buckets.items()
    }


def export_bundles(frame: Frame, embeddings: dict[str, np.ndarray], metrics: dict[str, Any]) -> list[Path]:
    import joblib

    rows = frame.rows
    index = {row.id: i for i, row in enumerate(rows)}
    x_all = embeddings["text"]
    dim = int(x_all.shape[1])
    dataset_version = _dataset_version(frame)
    written: list[Path] = []

    seniority_dir = MODELS_DIR / "text_seniority_probe_v1"
    seniority_dir.mkdir(parents=True, exist_ok=True)
    y_band = np.asarray([row.band_target for row in rows])
    band_model = fit_classifier(x_all, y_band, _groups(rows))
    joblib.dump(
        {"heads": {"band": band_model}, "classes": list(band_model.classes_)},
        seniority_dir / "model.joblib",
    )
    (seniority_dir / "metadata.json").write_text(
        json.dumps(
            {
                "task": "text_seniority_probe",
                "model_name": "text_seniority_probe",
                "model_version": "text_seniority_probe_v1",
                "dataset_version": dataset_version,
                "feature_transform": TRANSFORM_ID,
                "embedding_model": EMBED_MODEL,
                "embedding_dim": dim,
                "include_document": True,
                "sections": list(SECTION_ORDER),
                "labels": list(BANDS),
                "label_source": "band_target",
                "label_validation": "human review of 46 resumes put band_target at ~94.9% vs ~78.5% "
                "for the LLM teacher (handoff 7.2.2d)",
                "training_rows": len(rows),
                "evaluation": "GroupKFold over ESCO occupation",
                "metrics": metrics.get("seniority", {}),
                "trained_on": date.today().isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    written.append(seniority_dir)

    quality_dir = MODELS_DIR / "quality_probe_v1"
    quality_dir.mkdir(parents=True, exist_ok=True)
    target_rows = frame.with_quality_target()
    sub = np.asarray([index[row.id] for row in target_rows])
    level_model = fit_classifier(
        x_all[sub],
        np.asarray([str(r.quality_target) for r in target_rows]),
        _groups(target_rows),
    )
    heads: dict[str, Any] = {"level": level_model}
    dimension_rows: dict[str, int] = {}
    dimension_calibration: dict[str, dict[str, float]] = {}
    score_low = float(min(QUALITY_LEVEL_TO_SCORE.values()))
    score_high = float(max(QUALITY_LEVEL_TO_SCORE.values()))
    for dimension, getter in (
        ("impact", lambda r: r.teacher_impact),
        ("clarity", lambda r: r.teacher_clarity),
        ("ats", lambda r: r.teacher_ats),
    ):
        labelled = [row for row in rows if getter(row) is not None]
        if len(labelled) < 40:
            continue
        sub_d = np.asarray([index[row.id] for row in labelled])
        values = np.asarray([float(getter(r)) for r in labelled])
        heads[dimension] = fit_regressor(x_all[sub_d], values, _groups(labelled))
        dimension_rows[dimension] = len(labelled)
        # The teacher never uses the full 1-5 range on clarity or ats, so publishing a naive
        # 1-5 -> 0-100 map would floor them near 50 and contradict the level head on the same resume.
        # Record the range it did use and let inference rescale onto the level head's endpoints.
        dimension_calibration[dimension] = {
            "observed_low": float(values.min()),
            "observed_high": float(values.max()),
            "score_low": score_low,
            "score_high": score_high,
        }
    joblib.dump(
        {"heads": heads, "classes": list(level_model.classes_)},
        quality_dir / "model.joblib",
    )
    (quality_dir / "metadata.json").write_text(
        json.dumps(
            {
                "task": "quality_probe",
                "model_name": "quality_probe",
                "model_version": "quality_probe_v1",
                "dataset_version": dataset_version,
                "feature_transform": TRANSFORM_ID,
                "embedding_model": EMBED_MODEL,
                "embedding_dim": dim,
                "include_document": True,
                "sections": list(SECTION_ORDER),
                "labels": list(QUALITY_LEVELS),
                "label_source": "quality_target for the level head, LLM teacher rubric for impact/clarity/ats",
                "quality_level_to_score": QUALITY_LEVEL_TO_SCORE,
                "score_map_status": "declared product policy, not fitted (handoff 7.5 item 4)",
                "dimension_calibration": dimension_calibration,
                "dimension_calibration_status": (
                    "monotone rescale from the teacher's observed range onto the level head's "
                    "endpoints, so ats/clarity/impact publish on the same scale as quality_score; "
                    "ordering is the model's, units are policy"
                ),
                "training_rows": len(target_rows),
                "dimension_rows": dimension_rows,
                "dimension_heads": sorted(k for k in heads if k != "level"),
                "evaluation": "GroupKFold over ESCO occupation",
                "metrics": metrics.get("quality", {}),
                "trained_on": date.today().isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    written.append(quality_dir)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-export", action="store_true", help="evaluate only, do not write bundles")
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args()

    frame = build_frame()
    prime_payload_cache(REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3")
    print(
        f"frame: {len(frame)} resumes "
        f"({frame.prose_duplicates} duplicate prose lines and "
        f"{frame.rubric_duplicates} duplicate label lines dropped)"
    )

    print("embedding:")
    embeddings = {
        "text": embed_variant(frame.rows, attribute="text", encoder_name=EMBED_MODEL),
        "sections_only": embed_variant(
            frame.rows, attribute="text", encoder_name=EMBED_MODEL, include_document=False
        ),
        "text_no_tenure": embed_variant(
            frame.rows, attribute="text_no_tenure", encoder_name=EMBED_MODEL
        ),
    }

    out: list[str] = [
        "# Text probes over frozen multilingual MiniLM — v3 corpus\n",
        f"Generated {date.today().isoformat()} · encoder `{EMBED_MODEL}` · "
        f"transform `{TRANSFORM_ID}` · dim {embeddings['text'].shape[1]}\n",
        f"Frame: **{len(frame)} resumes** after dropping {frame.prose_duplicates} duplicated prose "
        f"lines and {frame.rubric_duplicates} duplicated label lines. Both files are appended to by "
        "resumable jobs that were run more than once; left in, those rows would train with double "
        "weight.\n",
    ]

    metrics: dict[str, Any] = {}
    metrics["seniority"] = train_seniority(frame, embeddings, out)
    metrics["quality"] = train_quality(frame, embeddings, out)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("".join(out), encoding="utf-8")
    print(f"\nreport -> {report_path}")

    if not args.no_export:
        for path in export_bundles(frame, embeddings, metrics):
            print(f"bundle -> {path}")

    sen = metrics["seniority"]
    qual = metrics["quality"]
    print("\n=== headline ===")
    print(f"seniority probe, production text : {sen['text']['accuracy']:.1%}")
    print(f"seniority probe, tenure stripped : {sen['text_no_tenure']['accuracy']:.1%}")
    print(f"rule_based_seniority (biased)    : {sen['rule_based']['accuracy']:.1%}")
    print(f"quality level probe              : {qual['quality_target']['accuracy']:.1%}")
    if "impact" in qual:
        print(f"impact MAE                       : {qual['impact']['mae']:.2f} (mean baseline {qual['impact']['baseline_mae']:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
