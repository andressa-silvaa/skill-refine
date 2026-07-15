"""Field-by-field comparison of golden inference snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def diff_paths(
    expected: Any,
    actual: Any,
    *,
    path: str = "$",
    float_tol: float = 1e-9,
) -> list[str]:
    """
    Recursively diff two JSON-like structures.
    Returns human-readable paths that diverge (empty list = identical).
    """
    diffs: list[str] = []

    if type(expected) is not type(actual) and not (
        _is_number(expected) and _is_number(actual)
    ):
        diffs.append(f"{path}: type {type(expected).__name__} != {type(actual).__name__}")
        return diffs

    if isinstance(expected, dict):
        exp_keys = set(expected)
        act_keys = set(actual)
        for key in sorted(exp_keys - act_keys):
            diffs.append(f"{path}.{key}: missing in actual")
        for key in sorted(act_keys - exp_keys):
            diffs.append(f"{path}.{key}: unexpected in actual")
        for key in sorted(exp_keys & act_keys):
            diffs.extend(diff_paths(expected[key], actual[key], path=f"{path}.{key}", float_tol=float_tol))
        return diffs

    if isinstance(expected, list):
        if len(expected) != len(actual):
            diffs.append(f"{path}: list length {len(expected)} != {len(actual)}")
            # Still compare overlapping prefix for sharper diagnostics.
        for i, (left, right) in enumerate(zip(expected, actual)):
            diffs.extend(diff_paths(left, right, path=f"{path}[{i}]", float_tol=float_tol))
        return diffs

    if _is_number(expected) and _is_number(actual):
        if abs(float(expected) - float(actual)) > float_tol:
            diffs.append(f"{path}: {expected!r} != {actual!r}")
        return diffs

    if expected != actual:
        diffs.append(f"{path}: {expected!r} != {actual!r}")
    return diffs


def compare_snapshots(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    float_tol: float = 1e-9,
) -> list[str]:
    """
    Compare two snapshot documents produced by run_golden_snapshots().
    Diffs cover score, task_scores, seniority_*, payload_json (insights,
    model_metadata_by_task, seniorityEvidence, etc.).
    """
    diffs: list[str] = []
    base_cases = {c["id"]: c for c in baseline.get("cases") or []}
    curr_cases = {c["id"]: c for c in current.get("cases") or []}

    for case_id in sorted(set(base_cases) - set(curr_cases)):
        diffs.append(f"case {case_id!r}: missing in current snapshot")
    for case_id in sorted(set(curr_cases) - set(base_cases)):
        diffs.append(f"case {case_id!r}: unexpected in current snapshot")

    for case_id in sorted(set(base_cases) & set(curr_cases)):
        left = base_cases[case_id].get("output") or {}
        right = curr_cases[case_id].get("output") or {}
        case_diffs = diff_paths(left, right, path=f"cases[{case_id}].output", float_tol=float_tol)
        diffs.extend(case_diffs)
    return diffs


def load_snapshot(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def format_diff_report(diffs: list[str], *, limit: int = 80) -> str:
    if not diffs:
        return "OK: no divergences"
    shown = diffs[:limit]
    lines = [f"{len(diffs)} divergence(s):", *[f"  - {d}" for d in shown]]
    if len(diffs) > limit:
        lines.append(f"  ... and {len(diffs) - limit} more")
    return "\n".join(lines)
