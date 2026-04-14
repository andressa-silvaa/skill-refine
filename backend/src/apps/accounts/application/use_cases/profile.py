"""Profile/account use cases: delete account."""
from __future__ import annotations

from apps.accounts.domain.errors import ValidationError
from apps.accounts.domain.ports import (
    EmailConfirmationRepository,
    PasswordResetRepository,
    SessionRepository,
    UserRepository,
)
from apps.audit.domain.ports import AuditLogger
from shared.auth.jwt import now_utc


def delete_account(
    *,
    user_id: str,
    users: UserRepository,
    sessions: SessionRepository,
    confirmations: EmailConfirmationRepository,
    password_resets: PasswordResetRepository,
    audit: AuditLogger,
    ip: str | None,
    user_agent: str | None,
) -> None:
    if not user_id:
        raise ValidationError("Missing user")
    now = now_utc()
    confirmations.consume_all_active_for_user(user_id=user_id, when=now)
    password_resets.consume_all_active_for_user(user_id=user_id, when=now)
    users.soft_delete(user_id=user_id, when=now)
    sessions.revoke_all_for_user(user_id=user_id, when=now)
    audit.log(
        action="accounts.deleted",
        actor_user_id=user_id,
        subject_user_id=user_id,
        ip=ip,
        user_agent=user_agent,
        metadata={},
    )
