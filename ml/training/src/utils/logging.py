"""Logging and report paths."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


def save_config(config: dict, output_dir: Path) -> Path:
    path = output_dir / "config.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return path


def training_cost_report(
    output_path: Path,
    train_seconds: float,
    inference_cpu_ms: float | None = None,
    inference_gpu_ms: float | None = None,
    vram_mb: float | None = None,
    ram_mb: float | None = None,
    extra: dict | None = None,
) -> None:
    """Write ml/reports/training_cost.md (or per model_version)."""
    lines = [
        "# Training cost and runtime",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Time",
        "",
        f"- **Training time:** {train_seconds:.1f} s",
        "",
        "## Inference (per example)",
        "",
    ]
    if inference_cpu_ms is not None:
        lines.append(f"- **CPU:** {inference_cpu_ms:.2f} ms")
    if inference_gpu_ms is not None:
        lines.append(f"- **GPU:** {inference_gpu_ms:.2f} ms")
    lines.append("")
    lines.append("## Memory")
    lines.append("")
    if vram_mb is not None:
        lines.append(f"- **VRAM (peak):** {vram_mb:.0f} MB")
    if ram_mb is not None:
        lines.append(f"- **RAM (peak):** {ram_mb:.0f} MB")
    if extra:
        lines.append("")
        lines.append("## Extra")
        lines.append("")
        for k, v in extra.items():
            lines.append(f"- **{k}:** {v}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
