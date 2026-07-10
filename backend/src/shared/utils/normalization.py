from __future__ import annotations

import unicodedata


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def normalize_password(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


