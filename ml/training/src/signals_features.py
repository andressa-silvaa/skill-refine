"""
Numeric feature extraction from dataset `signals` dict (schema v1.0).

Must stay aligned with backend `signals_to_feature_dict` for inference.
"""
from __future__ import annotations

import math
from typing import Any

_SKIP_KEYS = frozenset({"reasons", "language", "completeness_level"})

FEATURE_TRANSFORM = "log1p_v1"

# Counts have no upper bound, and StandardScaler plus a linear model extrapolate without one.
# A real resume with a 298-char summary sat 25 sigma above a training range of 30-61 chars, which
# alone contributed +16 to the intern logit and made seniority_signals_v1 emit a single class for
# every real input. log1p turns that 10x outlier into roughly +2, so no single count can dominate.
LOG1P_FEATURES = frozenset(
    {
        "summary_char_count",
        "word_count",
        "total_months_experience",
        "effective_months_experience",
        "months_in_current_role",
        "bullets_count",
        "experiences_count",
        "skills_count",
    }
)


def transform_value(name: str, value: float) -> float:
    if name in LOG1P_FEATURES:
        return math.log1p(max(0.0, float(value)))
    return float(value)


def feature_dict_from_signals(sig: dict[str, Any] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(sig, dict):
        return out
    for k, v in sig.items():
        if k in _SKIP_KEYS:
            continue
        if isinstance(v, bool):
            out[k] = 1.0 if v else 0.0
        elif isinstance(v, (int, float)):
            out[k] = transform_value(k, v)
    return out


def feature_vector(feature_names: list[str], feat: dict[str, float]) -> list[float]:
    return [float(feat.get(n, 0.0)) for n in feature_names]
