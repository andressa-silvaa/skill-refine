"""
Numeric feature extraction from dataset `signals` dict (schema v1.0).

Must stay aligned with backend `signals_to_feature_dict` for inference.
"""
from __future__ import annotations

from typing import Any

_SKIP_KEYS = frozenset({"reasons", "language", "completeness_level"})


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
            out[k] = float(v)
    return out


def feature_vector(feature_names: list[str], feat: dict[str, float]) -> list[float]:
    return [float(feat.get(n, 0.0)) for n in feature_names]
