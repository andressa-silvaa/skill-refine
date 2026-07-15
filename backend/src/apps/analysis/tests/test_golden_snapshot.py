"""Golden snapshot safety net for inference refactoring (Fase 0)."""
from __future__ import annotations

import copy
from pathlib import Path

from django.test import SimpleTestCase

from apps.analysis.application.inference.snapshot.compare import (
    compare_snapshots,
    diff_paths,
    format_diff_report,
    load_snapshot,
)
from apps.analysis.application.inference.snapshot.dataset import GOLDEN_CASES, golden_case_ids
from apps.analysis.application.inference.snapshot.runner import (
    assert_golden_case_count,
    default_baseline_path,
    run_golden_snapshots,
)


class GoldenDatasetTest(SimpleTestCase):
    def test_dataset_covers_branch_tags(self) -> None:
        assert_golden_case_count(30)
        ids = golden_case_ids()
        self.assertEqual(len(ids), len(set(ids)), "golden case ids must be unique")
        tags = {t for c in GOLDEN_CASES for t in (c.get("tags") or [])}
        for required in (
            "insufficient_data",
            "thin_profile",
            "intern",
            "junior",
            "mid",
            "senior",
            "job",
            "target",
            "pt",
            "en",
            "es",
        ):
            self.assertIn(required, tags)
        self.assertTrue(any(c.get("job_description_text") for c in GOLDEN_CASES))
        self.assertTrue(any(not c.get("job_description_text") for c in GOLDEN_CASES))
        self.assertTrue(
            any(
                ((c.get("resume_data") or {}).get("data") or {}).get("targetPosition")
                for c in GOLDEN_CASES
            )
        )


class SnapshotCompareUnitTest(SimpleTestCase):
    def test_diff_paths_detects_nested_change(self) -> None:
        left = {"score": 10, "payload_json": {"insights": {"strengths": [{"key": "a"}]}}}
        right = {"score": 11, "payload_json": {"insights": {"strengths": [{"key": "a"}]}}}
        diffs = diff_paths(left, right)
        self.assertTrue(any("score" in d for d in diffs))

    def test_compare_snapshots_fails_on_score_mutation(self) -> None:
        baseline = {
            "cases": [
                {
                    "id": "x",
                    "output": {
                        "score": 50,
                        "task_scores": {"ats": 40},
                        "payload_json": {"seniorityEvidence": [{"type": "rule"}]},
                    },
                }
            ]
        }
        current = copy.deepcopy(baseline)
        current["cases"][0]["output"]["score"] = 51
        diffs = compare_snapshots(baseline, current)
        self.assertTrue(diffs)
        self.assertIn("score", format_diff_report(diffs))


class GoldenSnapshotRegressionTest(SimpleTestCase):
    """End-to-end: current analyze_resume must match frozen baseline field-by-field.

    Uses SimpleTestCase — analyze_resume does not touch the DB.
    """

    def test_baseline_file_exists(self) -> None:
        path = default_baseline_path()
        self.assertTrue(
            path.is_file(),
            f"Missing baseline at {path}. Run: python manage.py compare_inference_snapshots --write-baseline",
        )

    def test_current_matches_frozen_baseline(self) -> None:
        path = default_baseline_path()
        if not path.is_file():
            self.skipTest("baseline.json not frozen yet")
        baseline = load_snapshot(path)
        current = run_golden_snapshots()
        diffs = compare_snapshots(baseline, current)
        self.assertEqual(diffs, [], format_diff_report(diffs))

    def test_sanity_mutated_score_is_detected(self) -> None:
        path = default_baseline_path()
        if not path.is_file():
            self.skipTest("baseline.json not frozen yet")
        baseline = load_snapshot(path)
        current = run_golden_snapshots()
        self.assertTrue(current["cases"], "expected golden cases")
        mutated = copy.deepcopy(current)
        mutated["cases"][0]["output"]["score"] = int(mutated["cases"][0]["output"]["score"]) + 7
        diffs = compare_snapshots(baseline, mutated)
        self.assertTrue(diffs, "comparator must fail when a score is altered")
        self.assertTrue(any("score" in d for d in diffs))
