"""Golden snapshot runner and comparator for inference refactoring safety net."""

from .compare import compare_snapshots, diff_paths
from .dataset import GOLDEN_CASES, iter_golden_cases
from .runner import run_golden_snapshots, serialize_analysis_result

__all__ = [
    "GOLDEN_CASES",
    "compare_snapshots",
    "diff_paths",
    "iter_golden_cases",
    "run_golden_snapshots",
    "serialize_analysis_result",
]
