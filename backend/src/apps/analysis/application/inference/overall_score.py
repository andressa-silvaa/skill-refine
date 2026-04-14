"""
Overall resume score: primary = quality, optional blend with seniority / target fit for spread (env-tunable).
"""
from __future__ import annotations

from typing import Any


def compute_overall_score(
    quality: float,
    seniority_score_0_100: float,
    target_fit_0_100: float | None,
    *,
    blend_enabled: bool,
    w_quality: float,
    w_seniority: float,
    w_target: float,
) -> tuple[int, dict[str, Any]]:
    """
    Returns (overall int 0-100, formula meta for debug).
    When blend_enabled is False, overall = rounded quality only.
    """
    q = max(0.0, min(100.0, float(quality)))
    s = max(0.0, min(100.0, float(seniority_score_0_100)))
    if not blend_enabled:
        out = int(round(q))
        return out, {
            "mode": "quality_only",
            "weights": {"quality": 1.0, "seniority": 0.0, "target_fit": 0.0},
            "formula": "round(clamp(quality,0,100))",
            "blend_input": {"quality": q, "seniority": s, "target_fit": target_fit_0_100},
        }

    if target_fit_0_100 is None:
        wq, ws = w_quality, w_seniority
        t = wq + ws
        wq, ws = wq / t, ws / t
        mixed = wq * q + ws * s
        formula = f"{wq:.2f}*quality + {ws:.2f}*seniority_score"
        weights = {"quality": wq, "seniority": ws, "target_fit": 0.0}
    else:
        tf = max(0.0, min(100.0, float(target_fit_0_100)))
        tsum = w_quality + w_seniority + w_target
        wq = w_quality / tsum
        ws = w_seniority / tsum
        wt = w_target / tsum
        mixed = wq * q + ws * s + wt * tf
        formula = f"{wq:.2f}*quality + {ws:.2f}*seniority + {wt:.2f}*target_fit"
        weights = {"quality": wq, "seniority": ws, "target_fit": wt}

    out = int(round(max(0.0, min(100.0, mixed))))
    return out, {
        "mode": "blend",
        "weights": weights,
        "formula": formula,
        "blend_input": {"quality": q, "seniority": s, "target_fit": target_fit_0_100},
    }
