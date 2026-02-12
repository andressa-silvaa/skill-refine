"""
Payload builders for accounts API responses.
Pure extraction from views; no change to keys, shapes, or behavior.
"""
from __future__ import annotations

from apps.accounts.infrastructure.cloudinary_avatar import avatar_url
from apps.accounts.infrastructure.repositories import OrmUserRepository


def user_payload(
    *,
    users: OrmUserRepository,
    user_id: str,
    fallback: dict,
) -> dict:
    """Build user dict for login/register/me. Uses fallback when user not found by id."""
    u = users.get_by_id(user_id)
    if not u:
        return fallback
    key = getattr(u, "avatar_storage_key", None)
    url = avatar_url(str(key) if key else None)
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "email_verified": bool(getattr(u, "email_verified_at", None)),
        "status": getattr(u, "status", None),
        "created_at": getattr(u, "created_at", None),
        "avatar_storage_key": str(key) if key else None,
        "avatarStorageKey": str(key) if key else None,
        "avatar_url": url,
        "avatarUrl": url,
    }


def login_response_payload(access_token: str, user: dict) -> dict:
    """Login / Google login success payload."""
    return {
        "access_token": access_token,
        "user": user,
    }


def register_response_payload(user: dict, email_confirmation_sent: bool) -> dict:
    """Register success payload."""
    return {
        "user": user,
        "email_confirmation_sent": email_confirmation_sent,
    }


def refresh_response_payload(access_token: str) -> dict:
    """Refresh session success payload."""
    return {"access_token": access_token}


def password_reset_verify_payload(reset_token: str) -> dict:
    """Password reset verify success payload."""
    return {"reset_token": reset_token}


def status_ok_payload() -> dict:
    """Generic success payload (password reset request, confirm, email confirmation, etc.)."""
    return {"status": "ok"}


def me_response_payload(user: object) -> dict:
    """GET /me response payload. user is request.user (ORM model)."""
    key = getattr(user, "avatar_storage_key", None)
    url = avatar_url(str(key) if key else None)
    return {
        "user": {
            "id": str(getattr(user, "id", "")),
            "email": getattr(user, "email", ""),
            "full_name": getattr(user, "full_name", ""),
            "email_verified": bool(getattr(user, "email_verified_at", None)),
            "status": getattr(user, "status", None),
            "created_at": getattr(user, "created_at", None),
            "avatar_storage_key": str(key) if key else None,
            "avatar_url": url,
            "avatarStorageKey": str(key) if key else None,
            "avatarUrl": url,
        }
    }
