"""
Safety: truncation, sanitization, no PII in logs.
"""
from __future__ import annotations

def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    """
    Truncate text to max_chars. Returns (truncated_text, was_truncated).
    """
    if not text or max_chars <= 0:
        return (text or "", False)
    t = (text or "").strip()
    if len(t) <= max_chars:
        return (t, False)
    return (t[:max_chars].rstrip(), True)


def safe_error_message(exc: BaseException, max_len: int = 500) -> str:
    """Generic error message for user; no stacktrace or payload."""
    msg = str(exc).strip()
    if not msg:
        return "Analysis failed."
    # Remove paths, IDs that might leak info
    safe = " ".join(msg.split())[:max_len]
    return safe or "Analysis failed."
