"""Celery configuration."""
from __future__ import annotations

from .base import DEBUG, REDIS_URL, env

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL or "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default=REDIS_URL or "redis://localhost:6379/2")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASKS_ENABLED = env.bool("CELERY_TASKS_ENABLED", default=True)
# Em dev, executa tarefas no mesmo processo (sem broker/worker) para garantir notificações
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=DEBUG)
