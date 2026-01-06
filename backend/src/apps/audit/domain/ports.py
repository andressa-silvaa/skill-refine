from __future__ import annotations

from typing import Any, Protocol


class AuditLogger(Protocol):
    def log(
        self,
        *,
        action: str,
        actor_user_id: str | None,
        subject_user_id: str | None,
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...


