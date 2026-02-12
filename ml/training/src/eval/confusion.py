"""Confusion matrix: save PNG and table."""
from __future__ import annotations

from pathlib import Path
import numpy as np


def save_confusion_matrix_png(cm: np.ndarray, label_names: list[str], output_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.set_xticks(np.arange(len(label_names)))
    ax.set_yticks(np.arange(len(label_names)))
    ax.set_xticklabels(label_names)
    ax.set_yticklabels(label_names)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    for i in range(len(label_names)):
        for j in range(len(label_names)):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="black" if cm[i, j] < cm.max() / 2 else "white")
    ax.set_title("Confusion matrix")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def confusion_matrix_table(cm: np.ndarray, label_names: list[str]) -> str:
    lines = ["| " + " | ".join([""] + label_names) + " |", "| " + " | ".join(["---"] * (len(label_names) + 1)) + " |"]
    for i, name in enumerate(label_names):
        row = [name] + [str(int(cm[i, j])) for j in range(len(label_names))]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
