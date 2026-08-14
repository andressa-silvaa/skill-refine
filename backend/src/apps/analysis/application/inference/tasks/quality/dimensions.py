"""
Mapping the teacher's 1-5 rubric dimensions onto the published 0-100 scale.

Separate from ``predict.py`` because it is a rescale, not a decision: monotone, so the model's
ordering survives untouched, and declared product policy rather than a fitted quantity.
"""
from __future__ import annotations

from typing import Any

DIMENSION_KEYS = ("ats", "clarity")


def dimension_to_score(value: float, calibration: dict[str, Any] | None) -> int:
    """
    Map a rubric dimension onto the 0-100 scale, using the range the teacher actually used.

    A naive 1-5 -> 0-100 map is wrong here and it shows on screen. The teacher never scores `clarity`
    or `ats` below 3, so that map floors those dimensions near 50 and a resume whose quality reads 42
    would publish an `ats` of 72 — three numbers that contradict each other.

    So the observed label range is recorded at export time and mapped onto the same endpoints the
    level head uses (`quality_level_to_score`), which puts every published number on one scale.
    """
    if not isinstance(calibration, dict):
        clamped = max(1.0, min(5.0, float(value)))
        return int(round((clamped - 1.0) / 4.0 * 100.0))

    low = float(calibration.get("observed_low", 1.0))
    high = float(calibration.get("observed_high", 5.0))
    score_low = float(calibration.get("score_low", 30.0))
    score_high = float(calibration.get("score_high", 78.0))
    if high <= low:
        return int(round(max(0.0, min(100.0, score_high))))
    position = (float(value) - low) / (high - low)
    scaled = score_low + max(0.0, min(1.0, position)) * (score_high - score_low)
    return int(round(max(0.0, min(100.0, scaled))))
