"""Metrics: accuracy, F1 macro, regression (MSE, MAE, correlation), per-language breakdown."""
from __future__ import annotations

import numpy as np
from typing import Sequence


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(y_true == y_pred))


def f1_macro(y_true: np.ndarray, y_pred: np.ndarray, labels: Sequence[str] | None = None) -> float:
    from sklearn.metrics import f1_score
    if labels is None:
        labels = list(np.unique(np.concatenate([y_true, y_pred])))
    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def precision_recall_f1(y_true: np.ndarray, y_pred: np.ndarray, labels: Sequence[str]) -> dict:
    from sklearn.metrics import precision_recall_fscore_support
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, labels=range(len(labels)), average="macro", zero_division=0)
    return {"precision": float(p), "recall": float(r), "f1_macro": float(f)}


def mse_mae(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    mse = float(np.mean((y_true - y_pred) ** 2))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    return mse, mae


def correlation(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    if len(y_true) < 2:
        return 0.0, 0.0
    from scipy.stats import pearsonr, spearmanr
    try:
        pearson, _ = pearsonr(y_true, y_pred)
        spearman, _ = spearmanr(y_true, y_pred)
        return float(pearson), float(spearman)
    except Exception:
        return 0.0, 0.0


def classification_report_per_lang(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label_names: list[str],
    languages: np.ndarray | None,
) -> str:
    from sklearn.metrics import classification_report
    report = classification_report(
        y_true, y_pred, labels=range(len(label_names)), target_names=label_names, zero_division=0
    )
    if languages is not None and len(languages) == len(y_true):
        lines = ["## Global", "", report]
        for lang in np.unique(languages):
            mask = languages == lang
            if mask.sum() == 0:
                continue
            sub = classification_report(
                y_true[mask], y_pred[mask], labels=range(len(label_names)), target_names=label_names, zero_division=0
            )
            lines.extend(["", f"## Language: {lang}", "", sub])
        return "\n".join(lines)
    return report


def confusion_matrix_and_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label_names: list[str],
) -> tuple[np.ndarray, str]:
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_true, y_pred, labels=range(len(label_names)))
    lines = ["Confusion matrix (rows=true, cols=pred)", ""]
    header = " " * 12 + " ".join(f"{n[:6]:>6}" for n in label_names)
    lines.append(header)
    for i, name in enumerate(label_names):
        row = f"{name[:10]:10} " + " ".join(f"{cm[i, j]:6}" for j in range(len(label_names)))
        lines.append(row)
    return cm, "\n".join(lines)
