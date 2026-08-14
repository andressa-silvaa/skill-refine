"""
Search for the most accurate head this corpus supports, by measuring instead of guessing.

Two axes, crossed:

* **representation** — how the resume becomes a vector. One mean over the whole document lets a long
  skills list dilute two lines of achievement prose, so the alternatives keep the blocks addressable
  (per-section embeddings) or keep the peaks (mean concatenated with max over the windows).
* **head** — what sits on top: logistic, calibrated linear SVM, a small MLP, or an ordinal model
  that predicts a rank and learns cut points, which matches four ordered bands better than
  one-vs-rest. Gradient boosting is excluded on purpose; ``head_svc`` explains why.

Protocol is identical for every cell: GroupKFold over the ESCO occupation, so no fold shares an
occupation or its pt/en/es translations. The linear head still picks ``C`` inside each training fold.
The winner is then re-run under full nested selection in ``train_text_probes_v3.py``, which is the
number that ships — the ranking here is for choosing, not for quoting.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/sweep_probe_designs_v3.py
  ./backend/.venv/Scripts/python.exe ml/scripts/sweep_probe_designs_v3.py --task quality
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
SCRIPTS_DIR = Path(__file__).resolve().parent
for extra_path in (str(BACKEND_SRC), str(SCRIPTS_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

from corpus_frame_v3 import BANDS, QUALITY_LEVELS, Row, build_frame  # noqa: E402

from apps.analysis.application.inference.text_probe import chunk_text  # noqa: E402

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CACHE_DIR = REPO_ROOT / "ml" / "data" / "cache" / "probe_embeddings"
SECTIONS = ("summary", "roles", "bullets", "credentials")
BAND_RANK = {band: i for i, band in enumerate(BANDS)}
QUALITY_RANK = {level: i for i, level in enumerate(QUALITY_LEVELS)}
C_GRID = (1.0, 4.0, 16.0, 64.0)
SEED = 20260811

_ENCODER: Any = None


def _encoder():
    global _ENCODER
    if _ENCODER is None:
        from sentence_transformers import SentenceTransformer

        _ENCODER = SentenceTransformer(EMBED_MODEL)
    return _ENCODER


def _cached(name: str, texts: Sequence[str], build: Callable[[], np.ndarray]) -> np.ndarray:
    digest = hashlib.sha256(f"{EMBED_MODEL}|{name}".encode())
    for text in texts:
        digest.update(text.encode("utf-8", "replace"))
        digest.update(b"\x00")
    path = CACHE_DIR / f"sweep_{name}__{digest.hexdigest()[:16]}.npy"
    if path.exists():
        matrix = np.load(path)
        if matrix.shape[0] == len(texts):
            return matrix
    matrix = build()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(path, matrix)
    return matrix


def _pooled(texts: Sequence[str], *, with_max: bool) -> np.ndarray:
    """Window every document, encode all windows in one call, then pool per document."""
    flat: list[str] = []
    spans: list[tuple[int, int]] = []
    for text in texts:
        chunks = chunk_text(text) or [""]
        start = len(flat)
        flat.extend(chunks)
        spans.append((start, len(flat)))
    encoded = np.asarray(_encoder().encode(flat, batch_size=64, show_progress_bar=False), dtype=np.float32)
    dim = encoded.shape[1]
    width = dim * (2 if with_max else 1)
    out = np.zeros((len(texts), width), dtype=np.float32)
    for row, (start, end) in enumerate(spans):
        if end <= start:
            continue
        block = encoded[start:end]
        if with_max:
            out[row] = np.concatenate([block.mean(axis=0), block.max(axis=0)])
        else:
            out[row] = block.mean(axis=0)
    return _l2(out)


def _l2(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def build_representations(rows: Sequence[Row]) -> dict[str, np.ndarray]:
    doc = [row.text for row in rows]
    doc_bare = [row.text_no_tenure for row in rows]
    reps: dict[str, np.ndarray] = {}

    reps["doc_mean"] = _cached("doc_mean", doc, lambda: _pooled(doc, with_max=False))
    reps["doc_meanmax"] = _cached("doc_meanmax", doc, lambda: _pooled(doc, with_max=True))
    reps["doc_mean_no_tenure"] = _cached(
        "doc_mean_no_tenure", doc_bare, lambda: _pooled(doc_bare, with_max=False)
    )

    per_section: dict[str, np.ndarray] = {}
    for section in SECTIONS:
        texts = [row.sections.get(section, "") for row in rows]
        per_section[section] = _cached(
            f"sec_{section}", texts, lambda t=texts: _pooled(t, with_max=False)
        )
    reps["sections"] = _l2(np.concatenate([per_section[s] for s in SECTIONS], axis=1))
    reps["sections_plus_doc"] = _l2(
        np.concatenate([reps["sections"], reps["doc_mean"]], axis=1)
    )
    reps["sections_plus_docmax"] = _l2(
        np.concatenate([reps["sections"], reps["doc_meanmax"]], axis=1)
    )
    return reps


def _group_splits(x: np.ndarray, y: np.ndarray, groups: np.ndarray, n_splits: int = 5):
    from sklearn.model_selection import GroupKFold

    distinct = len(set(groups.tolist()))
    return list(GroupKFold(n_splits=max(2, min(n_splits, distinct))).split(x, y, groups))


def _logreg(penalty_c: float):
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(max_iter=8000, C=penalty_c, class_weight="balanced", random_state=SEED)


def head_logreg(x_train, y_train, groups_train, x_test):
    best_score, best_c = -1.0, C_GRID[0]
    if len(set(groups_train.tolist())) >= 2:
        for penalty_c in C_GRID:
            scores = []
            for inner_train, inner_test in _group_splits(x_train, y_train, groups_train, 4):
                model = _logreg(penalty_c)
                model.fit(x_train[inner_train], y_train[inner_train])
                scores.append(float(np.mean(model.predict(x_train[inner_test]) == y_train[inner_test])))
            mean_score = float(np.mean(scores))
            if mean_score > best_score:
                best_score, best_c = mean_score, penalty_c
    model = _logreg(best_c)
    model.fit(x_train, y_train)
    return model.predict(x_test)


def head_mlp(x_train, y_train, groups_train, x_test):
    from sklearn.neural_network import MLPClassifier

    model = MLPClassifier(
        hidden_layer_sizes=(256,),
        alpha=1e-3,
        max_iter=600,
        early_stopping=True,
        n_iter_no_change=15,
        random_state=SEED,
    )
    model.fit(x_train, y_train)
    return model.predict(x_test)


def head_svc(x_train, y_train, groups_train, x_test):
    """
    Calibrated linear SVM. Hinge loss cares only about the margin, which on 1.5k rows and 384-3072
    dense dimensions is often a better fit than logistic loss.

    Gradient boosting is deliberately absent from this sweep: axis-aligned splits on dense semantic
    dimensions are the wrong inductive bias — no single embedding coordinate carries a threshold —
    and a 400-round fit over 3072 columns per fold was measured at hours rather than minutes.
    """
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.svm import LinearSVC

    model = CalibratedClassifierCV(
        LinearSVC(C=1.0, class_weight="balanced", max_iter=8000, random_state=SEED),
        cv=3,
        method="sigmoid",
    )
    model.fit(x_train, y_train)
    return model.predict(x_test)


def make_ordinal_head(order: dict[str, int]):
    """
    Predict the band as a number, then cut it at the thresholds that minimise training error.

    One-vs-rest throws away the fact that ``junior`` sits between ``intern`` and ``mid``: confusing
    intern with senior costs it exactly what confusing intern with junior costs. A rank model is
    penalised by distance, which is the loss the ordinal report actually measures.
    """
    labels = [label for label, _ in sorted(order.items(), key=lambda item: item[1])]

    def head(x_train, y_train, groups_train, x_test):
        from sklearn.linear_model import RidgeCV

        ranks = np.asarray([order[label] for label in y_train], dtype=np.float64)
        model = RidgeCV(alphas=(0.1, 1.0, 10.0, 100.0))
        model.fit(x_train, ranks)
        fitted = model.predict(x_train)
        cuts = _fit_cuts(fitted, ranks, len(labels))
        return np.asarray([labels[_bucket(value, cuts)] for value in model.predict(x_test)])

    return head


def _fit_cuts(values: np.ndarray, ranks: np.ndarray, n_classes: int) -> list[float]:
    """Pick each cut point at the quantile matching the training class frequencies."""
    cuts: list[float] = []
    total = len(ranks)
    cumulative = 0
    for klass in range(n_classes - 1):
        cumulative += int(np.sum(ranks == klass))
        cuts.append(float(np.quantile(values, cumulative / total)) if total else 0.0)
    return cuts


def _bucket(value: float, cuts: Sequence[float]) -> int:
    for index, cut in enumerate(cuts):
        if value < cut:
            return index
    return len(cuts)


def evaluate(x, y, groups, head) -> dict[str, float]:
    from sklearn.metrics import f1_score, precision_score

    predictions = np.empty_like(y)
    for train_idx, test_idx in _group_splits(x, y, groups):
        predictions[test_idx] = head(x[train_idx], y[train_idx], groups[train_idx], x[test_idx])
    return {
        "accuracy": float(np.mean(predictions == y)),
        "macro_f1": float(f1_score(y, predictions, average="macro", zero_division=0)),
        "macro_precision": float(precision_score(y, predictions, average="macro", zero_division=0)),
        "classes_used": len(set(predictions.tolist())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("seniority", "quality", "both"), default="both")
    args = parser.parse_args()

    frame = build_frame()
    print(f"frame: {len(frame)} resumes")
    print("building representations ...")
    started = time.time()
    reps = build_representations(frame.rows)
    for name, matrix in reps.items():
        print(f"  {name:24} {matrix.shape}")
    print(f"  ({time.time() - started:.0f}s)")

    tasks = []
    if args.task in ("seniority", "both"):
        tasks.append(
            (
                "SENIORITY — band_target",
                frame.rows,
                np.asarray([row.band_target for row in frame.rows]),
                BAND_RANK,
            )
        )
    if args.task in ("quality", "both"):
        target_rows = frame.with_quality_target()
        tasks.append(
            (
                "QUALITY — quality_target",
                target_rows,
                np.asarray([str(row.quality_target) for row in target_rows]),
                QUALITY_RANK,
            )
        )

    index = {row.id: i for i, row in enumerate(frame.rows)}
    for title, rows, y, order in tasks:
        picks = np.asarray([index[row.id] for row in rows])
        groups = np.asarray([row.occupation_uri or f"__{row.id}" for row in rows])
        heads = {
            "logreg": head_logreg,
            "ordinal_ridge": make_ordinal_head(order),
            "mlp_256": head_mlp,
            "linear_svc": head_svc,
        }
        print(f"\n{'=' * 92}\n{title}  (n={len(rows)}, {len(set(groups.tolist()))} occupations)\n{'=' * 92}")
        print(f"{'representation':24} {'head':14} {'acc':>7} {'macroF1':>8} {'macroP':>8} {'cls':>4} {'s':>5}")
        results: dict[tuple[str, str], dict[str, float]] = {}
        for rep_name, matrix in reps.items():
            for head_name, head in heads.items():
                started = time.time()
                try:
                    scores = evaluate(matrix[picks], y, groups, head)
                except Exception as exc:
                    print(f"{rep_name:24} {head_name:14} failed: {exc}")
                    continue
                results[(rep_name, head_name)] = scores
                print(
                    f"{rep_name:24} {head_name:14} {scores['accuracy']:7.4f} "
                    f"{scores['macro_f1']:8.3f} {scores['macro_precision']:8.3f} "
                    f"{scores['classes_used']:4d} {time.time() - started:5.0f}"
                )
        best = max(results, key=lambda key: results[key]["macro_f1"])
        print(f"\n  best by macro-F1: {best[0]} + {best[1]}  ->  {results[best]}")
        best_acc = max(results, key=lambda key: results[key]["accuracy"])
        print(f"  best by accuracy : {best_acc[0]} + {best_acc[1]}  ->  {results[best_acc]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
