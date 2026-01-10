from __future__ import annotations

import uuid

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from django.conf import settings


def _ensure_configured() -> None:
    url = (getattr(settings, "CLOUDINARY_URL", "") or "").strip()
    if url:
        cloudinary.config(cloudinary_url=url, secure=True)


def upload_avatar(*, user_id: str, file_obj) -> str:
    """
    Uploads an avatar to Cloudinary and returns the public_id.

    public_id format: avatars/<user_id>/<uuid>
    """
    _ensure_configured()
    public_id = f"avatars/{user_id}/{uuid.uuid4()}"
    cloudinary.uploader.upload(
        file_obj,
        public_id=public_id,
        resource_type="image",
        overwrite=True,
        unique_filename=False,
        use_filename=False,
    )
    return public_id


def avatar_url(public_id: str | None) -> str | None:
    if not public_id:
        return None
    _ensure_configured()
    url, _opts = cloudinary.utils.cloudinary_url(
        public_id,
        secure=True,
        resource_type="image",
        transformation=[
            {"width": 256, "height": 256, "crop": "fill", "gravity": "face", "quality": "auto", "fetch_format": "auto"}
        ],
    )
    return url

