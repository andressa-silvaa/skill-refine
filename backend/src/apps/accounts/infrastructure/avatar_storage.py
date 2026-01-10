from __future__ import annotations

from apps.accounts.infrastructure.cloudinary_avatar import upload_avatar


def save_user_avatar(*, user_id: str, content, ext: str) -> str:
    _ = ext
    return upload_avatar(user_id=user_id, file_obj=content)

