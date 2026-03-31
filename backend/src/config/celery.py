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
    try:
        from django.conf import settings

        if not getattr(settings, "ANALYSIS_PREWARM_ENABLED", False):
            return

        from apps.analysis.application.inference.warmup import prewarm_analysis_models

        prewarm_analysis_models()
    except Exception:
        # Do not break worker startup if pre-warm fails.
        import logging

        logging.getLogger(__name__).warning(
            "Failed to pre-warm analysis models on Celery startup",
            exc_info=True,
        )
