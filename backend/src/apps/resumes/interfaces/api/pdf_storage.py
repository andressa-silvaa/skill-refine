"""
Where a rendered PDF lives on disk, and the fingerprint that decides whether it can be reused.

Split out of ``pdf_exports.py`` so the export state machine there reads as a state machine. The
fingerprint is what makes the cache correct: it covers the resume content and the layout version, so
a template change invalidates every stored file without anyone remembering to purge.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path

from django.conf import settings

from apps.resumes.infrastructure.models import Resume

PDF_LAYOUT_VERSION = "resume-print-v1"
PDF_EXPORT_FILENAME_PREFIX = "Curriculo"
PDF_EXPORT_ROOT = "resume_exports"


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value).strip("_")
    return cleaned or PDF_EXPORT_FILENAME_PREFIX


def _export_relative_path(user_id: str, resume_id: str, fingerprint: str) -> str:
    return f"{PDF_EXPORT_ROOT}/{user_id}/{resume_id}/{fingerprint}.pdf"


def _export_absolute_path(storage_path: str) -> Path:
    media_root = Path(getattr(settings, "MEDIA_ROOT", ".")).resolve()
    absolute = (media_root / storage_path).resolve()
    if os.path.commonpath([str(media_root), str(absolute)]) != str(media_root):
        raise ValueError("Invalid export path.")
    return absolute


def _export_exists(storage_path: str) -> bool:
    if not storage_path:
        return False
    try:
        return _export_absolute_path(storage_path).exists()
    except Exception:
        return False


def _write_export_file(storage_path: str, content: bytes) -> int:
    target = _export_absolute_path(storage_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return len(content)


def read_export_file(storage_path: str) -> bytes:
    return _export_absolute_path(storage_path).read_bytes()


def build_pdf_fingerprint(resume: Resume) -> str:
    payload = {
        "resumeId": str(resume.id),
        "updatedAt": resume.updated_at.isoformat(),
        "themeId": resume.theme_id or "",
        "paletteId": resume.theme_palette_id or "",
        "accentOverride": resume.theme_accent_override or "",
        "secondaryOverride": resume.theme_secondary_override or "",
        "layoutVersion": PDF_LAYOUT_VERSION,
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_pdf_filename(resume: Resume) -> str:
    safe_name = _safe_filename(resume.name or resume.target_position or PDF_EXPORT_FILENAME_PREFIX)
    return f"{PDF_EXPORT_FILENAME_PREFIX}_{safe_name}_{date.today().isoformat()}.pdf"
