"""Smoke: validate_target_fit_dataset.py accepts synthetic JSONL (no DB)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class TargetFitDatasetValidateSmokeTests(SimpleTestCase):
    def test_synthetic_jsonl_validates_clean(self) -> None:
        root = Path(__file__).resolve().parents[5]
        synthetic = root / "ml" / "data" / "synthetic" / "target_fit_smoke.jsonl"
        self.assertTrue(synthetic.is_file(), f"missing {synthetic}")
        report = root / "ml" / "training" / "reports" / "target_fit_smoke_validate.md"
        rc = subprocess.run(
            [
                sys.executable,
                str(root / "ml" / "training" / "src" / "validate_target_fit_dataset.py"),
                "--in",
                str(synthetic),
                "--report",
                str(report),
            ],
            cwd=str(root),
            check=False,
        )
        self.assertEqual(rc.returncode, 0, rc.stdout)
