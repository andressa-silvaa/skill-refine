"""
Thin re-export so Django discovers models while we keep the actual implementation in
`apps/audit/infrastructure/models.py` (layered structure).
"""

from apps.audit.infrastructure.models import *  # noqa: F403


