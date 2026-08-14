"""
Which language the resume is written in, read from the document instead of the user's UI setting.

``worker.py`` passes ``UserPreferences.language`` into the analysis, which is the language of the
*interface*, and falls back to ``pt-BR`` when nothing is saved. The document was never consulted, so
a Brazilian with a Portuguese UI who uploads an English CV had it analysed as Portuguese. There is no
cheaper field to switch to: ``resume_languages`` records the languages the candidate *speaks*.

Measured cost of getting it wrong (ml/reports/language_mismatch_v3.md, 1559 resumes): the ESCO index
is built per language, so retrieval against the wrong one drops occupation top-1 by 29.5 points and
the domain that feeds ``careerSwitch`` and ``target_seniority`` by 14.9. An English resume read as
pt-BR — the default path for a user who never touched settings — loses 17.4 points of domain
accuracy.

**The preference wins ties, and that is deliberate.** The detector overrides a stated user preference,
so it only does so when it is sure. Held-out confidence on the corpus has its 1st percentile at 0.953,
while the cases the detector actually gets wrong — short marketing sentences that read almost
identically in Portuguese and Spanish — land at 0.35 to 0.39. ``MIN_CONFIDENCE`` sits far below the
former and far above the latter, so it discards nothing well-formed and declines exactly the
ambiguous input. Where that gap sits is measured; choosing to sit in the middle of it is declared
policy.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, dict[str, Any] | None] = {}

TASK = "language_detector"
PROVIDER = "language_detector_v1"
FALLBACK_PROVIDER = "user_preference"
MIN_CONFIDENCE = 0.50
MIN_CHARS = 40

# The product answers in these three and nothing else. A resume in a fourth language is scored into
# one of them whatever happens, so the floor above is also what keeps that from being asserted.
SUPPORTED = {"pt": "pt-BR", "en": "en-US", "es": "es-ES"}


def get_language_detector(config: dict[str, Any]) -> dict[str, Any] | None:
    if not bool(config.get("language_detection_enabled", False)):
        return None
    key = str(config.get("language_detector_cache_key") or "language_detector_v1")
    with _lock:
        if key in _cache:
            return _cache[key]
        explicit = str(config.get("language_detector_model_dir") or "").strip()
        if explicit:
            model_dir = Path(explicit)
        else:
            root = Path(config.get("model_root") or config.get("model_dir") or "")
            model_dir = root / str(config.get("language_detector_subdir") or "language_detector_v1")
        try:
            import json

            import joblib

            meta = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
            if str(meta.get("task") or "") != TASK:
                raise ValueError(f"metadata task {meta.get('task')!r} != {TASK!r}")
            bundle = joblib.load(model_dir / "model.joblib")
            if not isinstance(bundle, dict) or "pipeline" not in bundle:
                raise ValueError("invalid language detector bundle")
            bundle["_metadata"] = meta
            _cache[key] = bundle
            logger.info("Loaded language_detector from %s", model_dir)
            return bundle
        except Exception as exc:
            logger.warning("language_detector not loaded: %s", exc)
            _cache[key] = None
            return None


def clear_language_detector_cache() -> None:
    with _lock:
        _cache.clear()


def detect_language(
    bundle: dict[str, Any] | None, text: str, fallback: str
) -> tuple[str, str, float]:
    """
    Return ``(language_tag, provider, confidence)``.

    ``fallback`` is the caller's language — in production the user's preference — and it is returned
    untouched whenever the detector is absent, the text is too short to judge, or the answer is not
    confident enough to override a stated setting.
    """
    if not bundle or len(str(text or "").strip()) < MIN_CHARS:
        return fallback, FALLBACK_PROVIDER, 0.0
    try:
        pipeline = bundle["pipeline"]
        probabilities = pipeline.predict_proba([text])[0]
        classes = list(pipeline.classes_)
        best = max(range(len(classes)), key=lambda i: probabilities[i])
        confidence = float(probabilities[best])
        code = str(classes[best])
    except Exception as exc:
        logger.warning("language detection failed: %s", exc)
        return fallback, FALLBACK_PROVIDER, 0.0

    if confidence < MIN_CONFIDENCE or code not in SUPPORTED:
        return fallback, FALLBACK_PROVIDER, confidence
    return SUPPORTED[code], PROVIDER, confidence
