"""Helpers for export_seniority_dataset CLI (relative --since)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


_REL_SINCE = re.compile(r"^(\d+)\s*([dDwWmM])$")


def parse_since_argument(raw: str | None) -> datetime | None:
    """
    Parse --since value.

    - ISO date/datetime: ``2025-01-01``, ``2025-01-01T00:00:00Z``
    - Relative: ``90d`` / ``12w`` / ``6m`` (calendar months approximated as 30d for ``m``)
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    m = _REL_SINCE.match(s)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        now = datetime.now(timezone.utc)
        if unit == "d":
            return now - timedelta(days=n)
        if unit == "w":
            return now - timedelta(weeks=n)
        if unit == "m":
            return now - timedelta(days=30 * n)
        return now - timedelta(days=n)

    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"Invalid --since: {raw!r} (use ISO date or e.g. 90d, 12w, 6m)") from None
