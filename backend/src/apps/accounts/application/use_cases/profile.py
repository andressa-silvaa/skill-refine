"""Profile/account use cases: data export request, delete account."""
from __future__ import annotations

from apps.accounts.domain.errors import ValidationError
from apps.accounts.domain.ports import EmailSender, SessionRepository, UserRepository
from apps.audit.domain.ports import AuditLogger
from shared.auth.jwt import now_utc


def request_data_export(
    *,
    user_id: str,
    to_email: str,
    email_sender: EmailSender,
    audit: AuditLogger,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    if not user_id:
        raise ValidationError("Missing user")
    if not to_email:
        raise ValidationError("Missing email")
    email_sender.send_data_export_requested(to_email=to_email)
    audit.log(
        action="accounts.data_export_requested",
        actor_user_id=user_id,
        subject_user_id=user_id,
        ip=ip,
        user_agent=user_agent,
        metadata={"to_email": to_email},
    )
    return {"status": "requested"}


def delete_account(
    *,
    user_id: str,
    users: UserRepository,
    sessions: SessionRepository,
    audit: AuditLogger,
    ip: str | None,
    user_agent: str | None,
) -> None:
    if not user_id:
        raise ValidationError("Missing user")
    now = now_utc()
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
