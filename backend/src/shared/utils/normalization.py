from __future__ import annotations

import unicodedata

from django.conf import settings


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def reverse_password(value: str) -> str:
    """Reverse the password string before it reaches the XOR cipher."""
    return value[::-1]


def apply_password_cipher(value: str, key: str) -> str:
    """XOR the reversed password bytes with a repeating key, output as hex.

    Custom pre-hash transformation step (academic requirement): reversible on its
    own, which is why Argon2 still runs afterwards as the actual security boundary.
    """
    if not key:
        return value
    key_bytes = key.encode("utf-8")
    value_bytes = reverse_password(value).encode("utf-8")
    transformed = bytes(
        b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(value_bytes)
    )
    return transformed.hex()


def normalize_password(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    return apply_password_cipher(normalized, settings.PASSWORD_HASH_PEPPER)


