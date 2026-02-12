"""
Confusion matrix for classification tasks (seniority, sections).
Output: dict label_true -> dict label_pred -> count, and printable table.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def confusion_matrix(y_true: list[Any], y_pred: list[Any], labels: list[Any] | None = None) -> dict[Any, dict[Any, int]]:
    """Return cm[true_label][pred_label] = count."""
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    cm: dict[Any, dict[Any, int]] = {l: defaultdict(int) for l in labels}
    for t, p in zip(y_true, y_pred):
        if t in cm:
            cm[t][p] += 1
        else:
            cm[t] = defaultdict(int)
            cm[t][p] += 1
    return {k: dict(v) for k, v in cm.items()}


def format_cm(cm: dict[Any, dict[Any, int]], labels: list[Any] | None = None) -> str:
    """Format confusion matrix as text table."""
    if not cm:
        return "(empty)"
    if labels is None:
        labels = sorted(set(cm.keys()) | set(k for v in cm.values() for k in v))
    col_width = max(len(str(l)) for l in labels) + 1
    header = "".join(str(l).ljust(col_width) for l in ["(true\\pred)"] + list(labels))
    lines = [header]
    for true_l in labels:
        row = [str(true_l).ljust(col_width)]
        for pred_l in labels:
            row.append(str(cm.get(true_l, {}).get(pred_l, 0)).ljust(col_width))
        lines.append("".join(row))
    return "\n".join(lines)
