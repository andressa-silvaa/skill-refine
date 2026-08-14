"""
Order the improvement list by measured gain instead of the order the ``if`` statements happen to run.

``derive_insights`` decides *which* suggestions apply from evidence. It did not decide *which comes
first*: that was insertion order, and each branch carried a hand-written ``high``/``medium``/``low``.
Both were guesses, and they sit at the top of what the user reads.

The table this module loads is measured — see ``ml/scripts/calibrate_insight_gain_v3.py`` and
``ml/reports/insight_gain_v3.md``. For every improvement it records

    gain = mean(quality | suggestion absent) - mean(quality | suggestion shown)

over the corpus, scored by ``quality_probe`` through the real production path. **It is correlational,
not causal**: it says resumes without this deficiency score that much higher, not that acting on the
advice earns those points. That is enough to order a list and not enough to promise an outcome, and
nothing here publishes the number to the user.

Two deliberate conservatisms:

* An improvement the calibration could not measure — no contrast group, because it fires for every
  resume — keeps the priority its branch declared and sorts after everything measured. Demoting it
  on absent evidence would be the same guess in the other direction.
* The high/medium/low cut points are the terciles of the measured gains themselves, so no threshold
  is invented here. Where the labels land follows the data; that they exist at all is product policy.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, dict[str, Any] | None] = {}

TASK = "insight_gain"
PROVIDER = "insight_gain_v1"
FALLBACK_PROVIDER = "heuristics"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_gain_table(config: dict[str, Any]) -> dict[str, Any] | None:
    if not bool(config.get("insight_ranking_enabled", False)):
        return None
    key = str(config.get("insight_gain_cache_key") or "insight_gain_v1")
    with _lock:
        if key in _cache:
            return _cache[key]
        explicit = str(config.get("insight_gain_model_dir") or "").strip()
        if explicit:
            model_dir = Path(explicit)
        else:
            root = Path(config.get("model_root") or config.get("model_dir") or "")
            model_dir = root / str(config.get("insight_gain_subdir") or "insight_gain_v1")
        try:
            meta = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
            if str(meta.get("task") or "") != TASK:
                raise ValueError(f"metadata task {meta.get('task')!r} != {TASK!r}")
            gains = meta.get("gains")
            if not isinstance(gains, dict) or not gains:
                raise ValueError("metadata carries no gains")
            _cache[key] = meta
            logger.info("Loaded insight_gain table from %s (%d entries)", model_dir, len(gains))
            return meta
        except Exception as exc:
            logger.warning("insight_gain table not loaded: %s", exc)
            _cache[key] = None
            return None


def clear_gain_cache() -> None:
    with _lock:
        _cache.clear()


def _gain_of(entry: Any) -> float | None:
    if not isinstance(entry, dict):
        return None
    for field in ("within_band_gain", "pooled_gain"):
        value = entry.get(field)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _terciles(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    if len(ordered) < 3:
        return (ordered[0], ordered[-1]) if ordered else (0.0, 0.0)
    low = ordered[len(ordered) // 3]
    high = ordered[(2 * len(ordered)) // 3]
    return low, high


def rank_improvements(
    improvements: list[dict[str, Any]], meta: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], str]:
    """
    Return ``(ordered, provider)``. Without a table the input order and priorities are untouched.
    """
    if not meta or not improvements:
        return improvements, FALLBACK_PROVIDER
    gains = meta.get("gains") or {}
    measured = {
        key: gain
        for key, gain in ((k, _gain_of(v)) for k, v in gains.items())
        if gain is not None
    }
    if not measured:
        return improvements, FALLBACK_PROVIDER

    low_cut, high_cut = _terciles(list(measured.values()))

    def priority_for(gain: float) -> str:
        if gain >= high_cut:
            return "high"
        if gain >= low_cut:
            return "medium"
        return "low"

    ranked: list[tuple[tuple[int, float, int], dict[str, Any]]] = []
    for position, item in enumerate(improvements):
        key = str(item.get("key") or "")
        gain = measured.get(key)
        if gain is None:
            declared = str(item.get("priority") or "low")
            ranked.append(((1, float(-PRIORITY_ORDER.get(declared, 2)), position), item))
            continue
        updated = dict(item)
        updated["priority"] = priority_for(gain)
        evidence = dict(updated.get("evidence") or {})
        evidence["expectedGainRank"] = sum(1 for g in measured.values() if g > gain) + 1
        updated["evidence"] = evidence
        ranked.append(((0, -gain, position), updated))

    ranked.sort(key=lambda pair: pair[0])
    return [item for _sort_key, item in ranked], PROVIDER
