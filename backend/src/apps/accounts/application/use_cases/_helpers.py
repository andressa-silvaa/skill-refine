"""Private helpers shared across use case modules. Do not import from outside this package."""
from __future__ import annotations

import secrets
from datetime import UTC, datetime


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _hash_secret(value: str, pepper: str) -> str:
    import hashlib

    return hashlib.sha256((pepper + ":" + value).encode("utf-8")).hexdigest()


def _random_digits(length: int) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def _normalize_frontend_url(url: str) -> str:
    url = (url or "").strip()
    return url[:-1] if url.endswith("/") else url
