"""
Thin re-export so Django discovers models while we keep the actual implementation in
`apps/accounts/infrastructure/models.py` (layered structure).
"""

from apps.accounts.infrastructure.models import *  # noqa: F403


