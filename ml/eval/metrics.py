"""
Metrics per task and per language: classification (F1, accuracy), regression (MSE, MAE, R²).
Used by eval scripts and baseline comparison.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def accuracy(y_true: list[Any], y_pred: list[Any]) -> float:
    """Accuracy for classification."""
    if not y_true:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)


def f1_per_class(y_true: list[Any], y_pred: list[Any], labels: list[Any] | None = None) -> dict[str, float]:
    """F1 per class. labels: optional list of all classes (default: union of true/pred)."""
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    out: dict[str, float] = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        out[str(label)] = round(f1, 4)
    return out


def f1_macro(y_true: list[Any], y_pred: list[Any], labels: list[Any] | None = None) -> float:
    """Macro F1 (average of per-class F1)."""
    per_class = f1_per_class(y_true, y_pred, labels)
    if not per_class:
        return 0.0
    return sum(per_class.values()) / len(per_class)


def f1_micro(y_true: list[Any], y_pred: list[Any]) -> float:
    """Micro F1 (total TP, FP, FN then F1)."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    n = len(y_true)
    return tp / n if n else 0.0


def mse(y_true: list[float], y_pred: list[float]) -> float:
    """Mean squared error."""
    if not y_true:
        return 0.0
    return sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true)


def mae(y_true: list[float], y_pred: list[float]) -> float:
    """Mean absolute error."""
    if not y_true:
        return 0.0
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)


def r2(y_true: list[float], y_pred: list[float]) -> float:
    """R² (coefficient of determination)."""
    if not y_true or len(y_true) < 2:
        return 0.0
    mean_t = sum(y_true) / len(y_true)
    ss_tot = sum((t - mean_t) ** 2 for t in y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    if ss_tot == 0:
        return 0.0
    return 1.0 - (ss_res / ss_tot)


def metrics_by_language(
    y_true: list[Any],
    y_pred: list[Any],
    languages: list[str],
    task: str = "classification",
) -> dict[str, dict[str, float]]:
    """Compute metrics per language. task: 'classification' or 'regression'."""
    by_lang: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
    for t, p, lang in zip(y_true, y_pred, languages):
        by_lang[lang].append((t, p))
    out: dict[str, dict[str, float]] = {}
    for lang, pairs in by_lang.items():
        if not pairs:
            continue
        tt, pp = zip(*pairs)
        tt, pp = list(tt), list(pp)
        if task == "classification":
            out[lang] = {"accuracy": accuracy(tt, pp), "f1_macro": f1_macro(tt, pp), "f1_micro": f1_micro(tt, pp)}
        else:
            tt_f = [float(x) for x in tt]
            pp_f = [float(x) for x in pp]
            out[lang] = {
                "mse": round(mse(tt_f, pp_f), 4),
                "mae": round(mae(tt_f, pp_f), 4),
                "r2": round(r2(tt_f, pp_f), 4),
            }
    return out
