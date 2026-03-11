"""Payload builders for notifications API."""
from __future__ import annotations

from apps.notifications.models import Notification


def notification_payload(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "titleKey": n.title_key,
        "params": n.params or {},
        "isRead": n.is_read,
        "actionUrl": n.action_url or "",
        "entityRef": n.entity_ref or {},
        "createdAt": n.created_at.isoformat() if n.created_at else "",
    }
