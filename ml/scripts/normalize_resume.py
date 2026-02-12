"""
Normalize resume text for ML pipeline: unicode, whitespace, optional PII placeholder.
Language is detected or passed; output is suitable for dataset rows.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Optional: add language detection (langdetect) if needed
try:
    import langdetect
except ImportError:
    langdetect = None

LANGUAGES = ("pt", "en", "es")
PII_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PII_PHONE_PATTERN = re.compile(r"\+?[\d\s\-()]{10,}")


def normalize_unicode(text: str) -> str:
    """NFC normalization and strip."""
    if not text:
        return ""
    return unicodedata.normalize("NFC", text.strip())


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines to single space, strip."""
    if not text:
        return ""
    return " ".join(text.split())


def mask_pii(text: str, mask_email: bool = True, mask_phone: bool = True) -> str:
    """Replace PII with placeholders (for training data; do not log raw)."""
    out = text
    if mask_email:
        out = PII_EMAIL_PATTERN.sub("[EMAIL]", out)
    if mask_phone:
        out = PII_PHONE_PATTERN.sub("[PHONE]", out)
    return out


def detect_language(text: str) -> str:
    """Return pt, en, or es. Fallback to pt if detection fails."""
    if not langdetect or not text or len(text) < 20:
        return "pt"
    try:
        lang = langdetect.detect(text)
        if lang in ("pt", "en", "es"):
            return lang
        if lang == "pt-br" or lang.startswith("pt"):
            return "pt"
    except Exception:
        pass
    return "pt"


def normalize_resume_text(
    text: str,
    *,
    mask_pii_flag: bool = True,
    language: str | None = None,
) -> tuple[str, str]:
    """
    Normalize resume text and return (normalized_text, language).
    language: if provided, used as-is (must be pt|en|es); else detected.
    """
    t = normalize_unicode(text)
    t = normalize_whitespace(t)
    if mask_pii_flag:
        t = mask_pii(t)
    lang = language if language in LANGUAGES else detect_language(t)
    return t, lang


def main() -> None:
    """CLI: read from stdin or file, write normalized text and language to stdout."""
    import sys
    import json

    raw = sys.stdin.read() if not sys.argv[1:] else Path(sys.argv[1]).read_text(encoding="utf-8")
    norm, lang = normalize_resume_text(raw)
    out = {"normalized_text": norm, "language": lang}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
