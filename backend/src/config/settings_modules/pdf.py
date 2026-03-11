"""Resume PDF export configuration."""
from __future__ import annotations

from .base import env

PDF_MAX_CONCURRENT_PAGES = env.int("PDF_MAX_CONCURRENT_PAGES", default=2)
PDF_POLL_RETRY_AFTER_SECONDS = env.int("PDF_POLL_RETRY_AFTER_SECONDS", default=2)
PDF_EXPORT_STALE_SECONDS = env.int("PDF_EXPORT_STALE_SECONDS", default=90)
PDF_EXPORT_RESCUE_SECONDS = env.int("PDF_EXPORT_RESCUE_SECONDS", default=8)
PDF_EXPORTS_EAGER = env.bool("PDF_EXPORTS_EAGER", default=False)
