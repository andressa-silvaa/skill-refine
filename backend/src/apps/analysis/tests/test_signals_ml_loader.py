"""
Tests for signals_ml artifact loader and orchestration metadata (no HF).
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import fields
from pathlib import Path

import joblib
import numpy as np
from django.test import TestCase, override_settings
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from apps.analysis.application.inference.tasks.seniority.signals_ml_predict import (
    FEATURE_TRANSFORM,
)
from apps.analysis.application.inference.loader_signals_model import (
    clear_signals_ml_cache,
    get_signals_ml_bundle,
    load_signals_ml_bundle,
    signals_ml_metadata_for_extra,
)
from apps.analysis.application.inference.orchestrator import analyze_resume
from apps.analysis.application.inference.tasks.seniority.signals_ml_predict import signals_ml_predict
from apps.analysis.application.inference.signals.types import ResumeSignals


class SignalsMlLoaderTest(TestCase):
    def tearDown(self) -> None:
        clear_signals_ml_cache()

    def _feature_names(self) -> list[str]:
        skip = frozenset({"reasons", "language", "completeness_level"})
        return sorted(f.name for f in fields(ResumeSignals) if f.name not in skip)

    def _write_min_bundle(self, model_dir: Path) -> None:
        rng = np.random.RandomState(42)
        feature_names = self._feature_names()
        n = 48
        p = len(feature_names)
        X_tr = rng.randn(n, p)
        labs = rng.choice(["junior", "mid", "senior"], size=n)
        le = LabelEncoder()
        y_enc = le.fit_transform(labs)
        pipe = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("lr", LogisticRegression(max_iter=400, random_state=42)),
            ]
        )
        pipe.fit(X_tr, y_enc)
        bundle = {
            "pipeline": pipe,
            "label_encoder": le,
            "feature_names": feature_names,
            "model_version": "seniority_signals_test",
            "mode": "signals_logreg",
            "calibrated": False,
            "calibration_method": "none",
        }
        joblib.dump(bundle, model_dir / "model.joblib")
        meta = {
            "model_name": "seniority_signals",
            "model_version": "seniority_signals_test",
            "dataset_version": "testhash",
            "task": "seniority_signals",
            "features_schema": feature_names,
            "feature_transform": FEATURE_TRANSFORM,
        }
        (model_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    def test_load_signals_ml_bundle_reads_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "seniority_signals_v1"
            d.mkdir(parents=True)
            self._write_min_bundle(d)
            b = load_signals_ml_bundle(d)
            self.assertIn("pipeline", b)
            self.assertEqual(b["_metadata"]["model_version"], "seniority_signals_test")

    def test_get_signals_ml_bundle_cached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "seniority_signals_v1"
            d.mkdir(parents=True)
            self._write_min_bundle(d)
            cfg = {
                "signals_ml_enabled": True,
                "signals_ml_model_subdir": "seniority_signals_v1",
                "model_root": root,
                "signals_ml_cache_key": "t1",
            }
            b1 = get_signals_ml_bundle(cfg)
            b2 = get_signals_ml_bundle(cfg)
            self.assertIsNotNone(b1)
            self.assertIs(b1, b2)

    def test_signals_ml_predict_runs_on_fixture_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "m"
            d.mkdir(parents=True)
            self._write_min_bundle(d)
            bundle = load_signals_ml_bundle(d)
        rs = ResumeSignals(
            total_months_experience=72,
            effective_months_experience=72,
            experiences_count=3,
            bullets_count=8,
            has_current_role=True,
            months_in_current_role=12,
            has_internship_terms=False,
            has_leadership_terms=False,
            has_links=True,
            summary_char_count=120,
            skills_count=5,
            education_present=True,
            completeness_score=80,
            completeness_level="adequate",
            insufficient_data=False,
            reasons=(),
            word_count=120,
            language="pt-BR",
        )
        cfg = {
            "SENIOR_PROB_THRESHOLD": 0.70,
            "SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS": 60,
            "SIGNALS_ML_SENIOR_MIN_EXPERIENCES": 2,
            "SIGNALS_ML_SENIOR_MIN_BULLETS": 6,
            "MIN_COMPLETENESS_FOR_SIGNALS_ML": 52,
            "MIN_WORDS_FOR_SIGNALS_ML": 48,
        }
        lab, conf, probs, ev, st = signals_ml_predict(bundle, rs, cfg)
        self.assertEqual(st, "applied")
        self.assertIn(lab, ("intern", "junior", "mid", "senior"))
        self.assertTrue(probs)
        md = signals_ml_metadata_for_extra(bundle)
        self.assertEqual(md.get("model_name_base"), "seniority_signals")

    @override_settings(
        ANALYSIS_SIGNALS_ML_ENABLED=True,
        ANALYSIS_ALLOW_HEURISTICS_FALLBACK=True,
        ANALYSIS_MODEL_MODE="heuristics",
    )
    def test_analyze_resume_persists_signals_ml_provider_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "seniority_signals_v1"
            d.mkdir(parents=True)
            self._write_min_bundle(d)

            resume_data = {
                "data": {
                    "summary": "Engenheiro de software com experiência em produtos.",
                    "contact": {"linkedin": "https://linkedin.com/in/x"},
                    "experiences": [
                        {
                            "company": "ACME",
                            "position": "Engenheiro de Software",
                            "startDate": "2018-01",
                            "endDate": "2024-06",
                            "isCurrent": False,
                            "description": [
                                "Liderei squad de 4 pessoas.",
                                "Entregas em microserviços.",
                                "Métricas e observabilidade.",
                                "CI/CD e qualidade.",
                                "APIs REST e eventos.",
                                "Mentoria técnica.",
                            ],
                        },
                        {
                            "company": "Beta",
                            "position": "Desenvolvedor",
                            "startDate": "2015-06",
                            "endDate": "2017-12",
                            "description": ["Backend", "PostgreSQL", "Filas"],
                        },
                    ],
                    "educations": [{"institution": "UF", "course": "CC", "degree": "Bacharelado"}],
                    "skills": [{"name": "Python"}, {"name": "Django"}],
                    "languages": [],
                }
            }

            with self.settings(ANALYSIS_MODEL_ROOT=str(root)):
                clear_signals_ml_cache()
                result = analyze_resume(resume_data, None, "pt-BR")
                clear_signals_ml_cache()

            self.assertEqual(result.get("provider"), "signals_ml")
            self.assertTrue(result.get("model_version"))
            meta = (result.get("payload_json") or {}).get("model_metadata_by_task") or {}
            self.assertEqual(meta.get("seniority", {}).get("provider"), "signals_ml")
