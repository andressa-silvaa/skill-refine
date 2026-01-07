from __future__ import annotations

import logging
from typing import Any

from apps.audit.domain.ports import AuditLogger
from apps.audit.infrastructure.models import AuditLog


class OrmAuditLogger(AuditLogger):
    def log(
        self,
        *,
        action: str,
        actor_user_id: str | None,
        subject_user_id: str | None,
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            AuditLog.objects.create(
                action=action,
                actor_user_id=actor_user_id,
                subject_user_id=subject_user_id,
                ip=ip,
                user_agent=user_agent,
                metadata=metadata or {},
            )
        except Exception:
            logging.getLogger(__name__).exception("Failed to write audit log (ignored)")


