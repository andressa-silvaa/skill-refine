"""
Verifica se o Target Fit sklearn será carregado em runtime (env + artefatos).

  python manage.py check_target_fit_ml

Não altera dados. Use antes de subir o app/UI para confirmar target_fit_ml vs policy.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.analysis.application.inference.config import get_config
from apps.analysis.application.inference.loaders.loader_target_fit_model import (
    clear_target_fit_ml_cache,
    get_target_fit_ml_bundle,
)


class Command(BaseCommand):
    help = "Print Target Fit ML config and whether model.joblib loads (no PII)."

    def handle(self, *args, **options):
        clear_target_fit_ml_cache()
        config = get_config(settings)
        enabled = bool(config.get("target_fit_ml_enabled"))
        explicit = str(config.get("target_fit_ml_model_dir") or "").strip()
        sub = str(config.get("target_fit_ml_model_subdir") or "target_fit_v1")
        root = Path(str(config.get("model_root") or config.get("model_dir") or ""))

        self.stdout.write(f"ANALYSIS_TARGET_FIT_ML_ENABLED = {enabled}")
        if explicit:
            resolved = Path(explicit)
            self.stdout.write(f"ANALYSIS_TARGET_FIT_MODEL_DIR = {resolved}")
        else:
            resolved = (root / sub) if sub else root
            self.stdout.write(f"ANALYSIS_TARGET_FIT_MODEL_DIR = (empty) -> fallback {resolved}")

        mj = resolved / "model.joblib"
        meta = resolved / "metadata.json"
        self.stdout.write(f"  model.joblib exists: {mj.is_file()}")
        self.stdout.write(f"  metadata.json exists: {meta.is_file()}")

        if not enabled:
            self.stdout.write(self.style.WARNING("Inference will use target_fit_policy (ML disabled)."))
            return

        bundle = get_target_fit_ml_bundle(config)
        if bundle:
            m = bundle.get("_metadata") or {}
            self.stdout.write(self.style.SUCCESS("Bundle loaded OK: analyses with targetPosition will use target_fit_ml."))
            self.stdout.write(f"  metadata model_version: {m.get('model_version', '')!r}")
            dv = str(m.get("dataset_version", ""))[:32]
            self.stdout.write(f"  metadata dataset_version (prefix): {dv!r}")
            self.stdout.write("  Expected API payload: targetFitProvider=target_fit_ml, targetFitModelVersion=<above>")
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Bundle NOT loaded — analyses will fall back to target_fit_policy. "
                    "Fix path, metadata task=target_fit_signals, and model.joblib."
                )
            )
