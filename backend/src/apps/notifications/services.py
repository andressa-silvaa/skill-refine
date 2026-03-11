"""
Notification creation helper. Call from analysis worker, PDF export, version restore.
"""
from __future__ import annotations

from typing import Any

from apps.notifications.models import Notification, NotificationType


def create_notification(
    user_id: str,
    type: str,
    title_key: str,
    params: dict[str, Any] | None = None,
    action_url: str = "",
    entity_ref: dict[str, Any] | None = None,
) -> Notification:
    """
    Create a notification for the user.
    title_key: i18n key (e.g. notifications.analysisDone)
    params: interpolation params for the key (e.g. {"name": "Currículo X"})
    action_url: frontend path to navigate (e.g. /protected/ai-analysis?open=...)
    entity_ref: optional {resume_id, analysis_id, version_id, export_id}
    """
    if type not in NotificationType.values:
        type = NotificationType.SYSTEM
    return Notification.objects.create(
        user_id=user_id,
        type=type,
        title_key=title_key,
        params=params or {},
        action_url=(action_url or "").strip(),
        entity_ref=entity_ref or {},
    )
