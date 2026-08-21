"""Run analyze_resume over golden cases and serialize full outputs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.test.utils import override_settings

from apps.analysis.application.inference.loader import clear_cache
from apps.analysis.application.inference.orchestrator import analyze_resume

from .dataset import GOLDEN_CASES, iter_golden_cases

GOLDEN_SNAPSHOT_SETTINGS: dict[str, Any] = {
    "DEBUG": False,
    "ANALYSIS_EMBEDDINGS_ENABLED": False,
    "ANALYSIS_TARGET_FIT_ML_ENABLED": False,
    "ANALYSIS_QUALITY_PROBE_ENABLED": False,
    "ANALYSIS_TEXT_SENIORITY_PROBE_ENABLED": False,
    "ANALYSIS_REQUIRE_MODEL_ANSWER": False,
    "ANALYSIS_OVERALL_BLEND_ENABLED": True,
    "ANALYSIS_LLM_FEEDBACK_ENABLED": False,
}


def serialize_analysis_result(result: dict[str, Any]) -> dict[str, Any]:
    """Stable JSON-serializable copy of analyze_resume output (full payload)."""
    return json.loads(json.dumps(result, sort_keys=True, default=str))


def run_one_case(case: dict[str, Any]) -> dict[str, Any]:
    result = analyze_resume(
        case["resume_data"],
        job_description_text=case.get("job_description_text"),
        language=case.get("language") or "pt-BR",
    )
    return {
        "id": case["id"],
        "language": case.get("language") or "pt-BR",
        "tags": list(case.get("tags") or []),
        "has_job": bool(case.get("job_description_text")),
        "has_target": bool(
            ((case.get("resume_data") or {}).get("data") or {}).get("targetPosition")
        ),
        "output": serialize_analysis_result(result),
    }


def run_golden_snapshots(
    cases: list[dict[str, Any]] | None = None,
    *,
    apply_deterministic_settings: bool = True,
) -> dict[str, Any]:
    """
    Execute analyze_resume for each golden case and return a snapshot document.
    """
    selected = list(cases) if cases is not None else list(iter_golden_cases())

    def _run() -> dict[str, Any]:
        clear_cache()
        items = [run_one_case(case) for case in selected]
        return {
            "version": 1,
            "case_count": len(items),
            "settings": dict(GOLDEN_SNAPSHOT_SETTINGS) if apply_deterministic_settings else {},
            "cases": items,
        }

    if apply_deterministic_settings:
        with override_settings(**GOLDEN_SNAPSHOT_SETTINGS):
            return _run()
    return _run()


def write_snapshot(path: Path | str, snapshot: dict[str, Any] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = snapshot if snapshot is not None else run_golden_snapshots()
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def default_baseline_path() -> Path:
    """Frozen baseline under tests/golden_snapshots/."""
    # .../application/inference/snapshot/runner.py -> analysis/
    analysis_root = Path(__file__).resolve().parents[3]
    return analysis_root / "tests" / "golden_snapshots" / "baseline.json"


def assert_golden_case_count(min_cases: int = 30) -> None:
    if len(GOLDEN_CASES) < min_cases:
        raise AssertionError(f"Golden dataset has {len(GOLDEN_CASES)} cases; need >= {min_cases}")
