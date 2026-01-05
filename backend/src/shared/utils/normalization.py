from __future__ import annotations


def normalize_email(value: str | None) -> str | None:
    """
    Normalize emails to a canonical form:
    - trim
    - lowercase
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


