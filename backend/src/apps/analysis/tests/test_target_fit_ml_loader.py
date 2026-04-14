"""Target-fit sklearn bundle load + predict (no DB)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
from django.test import SimpleTestCase
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from apps.analysis.application.inference.loaders.loader_target_fit_model import (
    clear_target_fit_ml_cache,
    load_target_fit_ml_bundle,
    predict_target_fit_ml_score,
)
from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.target_fit.fit_signals import TargetFitSignals
from apps.analysis.application.inference.target_fit.ml_feature_row import (
    target_fit_feature_names,
    target_fit_feature_row,
)


class TargetFitMlLoaderTests(SimpleTestCase):
    def tearDown(self) -> None:
        clear_target_fit_ml_cache()
        super().tearDown()

    def test_load_and_predict_roundtrip(self) -> None:
        names = target_fit_feature_names()
        rng = np.random.RandomState(42)
        X = rng.randn(24, len(names))
        y = np.clip(50 + 10 * rng.randn(24), 0, 100)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        model = Ridge(alpha=1.0, random_state=42)
        model.fit(Xs, y)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = {"model": model, "scaler": scaler, "feature_names": names, "task": "target_fit_signals"}
            joblib.dump(bundle, root / "model.joblib")
            (root / "metadata.json").write_text(
                json.dumps(
                    {
                        "task": "target_fit_signals",
                        "model_name": "target_fit_signals",
                        "model_version": "target_fit_test",
                        "dataset_version": "testds",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            loaded = load_target_fit_ml_bundle(root)
            sig = TargetFitSignals(
                required_terms_total=8,
                required_terms_hit=4,
                skills_total=8,
                skills_hit=2,
                experience_keyword_hits=1,
                education_alignment="medium",
                portfolio_evidence=False,
                completeness_score=60,
            )
            vec = target_fit_feature_row(
                sig, resume_domain="finance", target_domain="finance", has_job_text=False
            )
            self.assertEqual(len(vec), len(names))
            score = predict_target_fit_ml_score(
                loaded,
                signals=sig,
                resume_domain="finance",
                target_domain="finance",
                has_job_text=False,
            )
            self.assertTrue(0 <= score <= 100)

    def test_analyze_resume_with_ml_enabled_uses_bundle_when_dir_set(self) -> None:
        """When model dir points at a valid artifact, provider is target_fit_ml."""
        names = target_fit_feature_names()
        rng = np.random.RandomState(7)
        X = rng.randn(16, len(names))
        y = np.clip(45 + 8 * rng.randn(16), 0, 100)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        model = Ridge(alpha=1.0, random_state=0)
        model.fit(Xs, y)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            joblib.dump(
                {"model": model, "scaler": scaler, "feature_names": names, "task": "target_fit_signals"},
                root / "model.joblib",
            )
            (root / "metadata.json").write_text(
                json.dumps(
                    {
                        "task": "target_fit_signals",
                        "model_name": "target_fit_signals",
                        "model_version": "target_fit_v1",
                        "dataset_version": "abc123",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            clear_target_fit_ml_cache()
            with self.settings(
                ANALYSIS_TARGET_FIT_ML_ENABLED=True,
                ANALYSIS_TARGET_FIT_MODEL_DIR=str(root.resolve()),
            ):
                resume_data = {
                    "data": {
                        "targetPosition": "Analista",
                        "summary": "Experiência em relatórios.",
                        "contact": {},
                        "experiences": [
                            {
                                "company": "Co",
                                "position": "Analista",
                                "description": ["Relatórios financeiros e conciliação."],
                            }
                        ],
                        "educations": [{"institution": "UF", "course": "Administração", "degree": "Bacharelado"}],
                        "skills": [{"name": "Excel"}, {"name": "ERP"}],
                        "languages": [],
                    }
                }
                result = analyze_resume(resume_data, None, "pt-BR")
                payload = result["payload_json"]
                self.assertIn("targetFitScore", payload)
                self.assertEqual(payload.get("targetFitProvider"), "target_fit_ml")
                self.assertEqual(payload.get("targetFitModelVersion"), "target_fit_v1")
                meta_tasks = payload.get("model_metadata_by_task") or {}
                self.assertEqual((meta_tasks.get("target_fit") or {}).get("provider"), "target_fit_ml")

