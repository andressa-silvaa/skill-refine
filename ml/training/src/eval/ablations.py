"""Ablation runner: run training with each ablation flag and collect comparative report."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Any

ABLATION_FLAGS = ["remove_stopwords", "drop_section", "drop_metrics_numbers"]


def run_ablations(
    train_fn: Callable[..., dict[str, Any]],
    config: dict,
    ablations: list[str],
    drop_section_value: str = "experience",
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    """
    train_fn(config, ablations=None, drop_section_value=None) -> metrics dict.
    Run baseline (no ablation), then each ablation; return list of {ablation, metrics}.
    """
    results = []
    # Baseline
    metrics_baseline = train_fn(config, ablations=None, drop_section_value=None)
    results.append({"ablation": "none", "metrics": metrics_baseline})
    for ab in ablations:
        drop = drop_section_value if ab == "drop_section" else None
        metrics = train_fn(config, ablations=[ab], drop_section_value=drop)
        results.append({"ablation": ab, "metrics": metrics})
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    return results


def ablation_report_md(results: list[dict], output_path: Path) -> None:
    """Write markdown comparison of ablations."""
    lines = ["# Ablation study", "", "| Ablation | " + " | ".join(_metric_keys(results)) + " |", "| " + "--- | " * (len(_metric_keys(results)) + 1) + "|"]
    for r in results:
        ab = r.get("ablation", "?")
        m = r.get("metrics", {})
        row = [ab] + [f"{m.get(k, 0):.4f}" for k in _metric_keys(results)]
        lines.append("| " + " | ".join(row) + " |")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _metric_keys(results: list[dict]) -> list[str]:
    keys = set()
    for r in results:
        keys.update((r.get("metrics") or {}).keys())
    return sorted(keys)
