"""
Celery app configuration for Skill Refine.
Broker: Redis (when REDIS_URL or CELERY_BROKER_URL set).
"""
from __future__ import annotations

import os

from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("skill_refine")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_ready.connect
def _prewarm_analysis_models(**kwargs) -> None:
    import logging

    from django.conf import settings

    from apps.analysis.application.inference.warmup import (
        ProbeBundleMissing,
        prewarm_analysis_models,
    )

    logger = logging.getLogger(__name__)
    try:
        if not getattr(settings, "ANALYSIS_PREWARM_ENABLED", False):
            return
        prewarm_analysis_models()
    except ProbeBundleMissing as exc:
        # Deliberately not swallowed. A worker that starts without its probes serves regex under a
        # model's name, which is the silent-degradation failure this project keeps paying for. Killing
        # the worker makes the container restart-loop, which is visible; a warning is not.
        logger.critical("Analysis probes unavailable, shutting the worker down: %s", exc)
        raise SystemExit(1) from exc
    except Exception:
        # Anything else (a slow model download, a transient disk error) must not block startup: the
        # per-request loaders retry, and the probe check above already covers the case that matters.
        logger.warning(
            "Failed to pre-warm analysis models on Celery startup",
            exc_info=True,
        )
