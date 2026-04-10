"""
Date parsing and non-overlapping month counting for resume experiences.
"""
from __future__ import annotations

from datetime import date
from typing import Any


def parse_payload_date(value: str | None) -> date | None:
    """YYYY-MM-DD ou YYYY-MM (dia 1), alinhado ao payload da API."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    parts = raw.split("-")
    try:
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return date(y, m, d)
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            if m < 1 or m > 12:
                return None
            return date(y, m, 1)
    except (ValueError, TypeError):
        return None
    return None


def _months_inclusive(start: date, end: date) -> int:
    if end < start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def experience_intervals(
    experiences: list[dict[str, Any]],
    *,
    today: date | None = None,
) -> tuple[list[tuple[date, date]], list[str]]:
    """
    Build list of (start, end) per experience. Invalid rows add reason codes.
    """
    today = today or date.today()
    intervals: list[tuple[date, date]] = []
    reasons: list[str] = []
    for idx, exp in enumerate(experiences or []):
        start = parse_payload_date(str(exp.get("startDate") or "").strip() or None)
        is_current = bool(exp.get("isCurrent"))
        end_raw = str(exp.get("endDate") or "").strip()
        if is_current:
            end = today
        else:
            end = parse_payload_date(end_raw) if end_raw else None
        if not start:
            reasons.append(f"experience_{idx}_invalid_start")
            continue
        if not end:
            reasons.append(f"experience_{idx}_missing_end")
            continue
        if end < start:
            reasons.append(f"experience_{idx}_end_before_start")
            continue
        intervals.append((start, end))
    return intervals, reasons


def merge_intervals_months(intervals: list[tuple[date, date]]) -> int:
    """Union of intervals, return total inclusive months (approximate by month buckets)."""
    if not intervals:
        return 0
    sorted_iv = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: list[tuple[date, date]] = []
    cur_s, cur_e = sorted_iv[0]
    for s, e in sorted_iv[1:]:
        if s <= cur_e:
            if e > cur_e:
                cur_e = e
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    total = 0
    for s, e in merged:
        total += _months_inclusive(s, e)
    return total


def months_in_current_role(experiences: list[dict[str, Any]], *, today: date | None = None) -> int:
    today = today or date.today()
    best = 0
    for exp in experiences or []:
        if not bool(exp.get("isCurrent")):
            continue
        start = parse_payload_date(str(exp.get("startDate") or "").strip() or None)
        if not start:
            continue
        best = max(best, _months_inclusive(start, today))
    return best
