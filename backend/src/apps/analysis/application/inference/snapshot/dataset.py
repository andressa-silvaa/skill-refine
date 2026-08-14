"""
Golden resume cases covering cascade branch points for analyze_resume().

Cases intentionally exercise insufficient_data, thin/intern profiles, with/without
job_description_text and targetPosition, PT/EN/ES, and each seniority band.

The cases live in ``golden_cases.json`` rather than as a Python literal. They are fixture, not
logic: 700 lines of nested dictionaries in a module hide the handful of lines that actually do
something, and nothing here needs to be executed to be read. The JSON was generated from the
previous literal and verified identical by digest, so the frozen baseline still matches.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

CASES_PATH = Path(__file__).resolve().parent / "golden_cases.json"


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(CASES_PATH.read_text(encoding="utf-8")))


def _cases() -> list[dict[str, Any]]:
    return [copy.deepcopy(case) for case in _load()]


GOLDEN_CASES: list[dict[str, Any]] = _cases()


def iter_golden_cases() -> Iterator[dict[str, Any]]:
    for case in GOLDEN_CASES:
        yield case


def golden_case_ids() -> list[str]:
    return [str(c["id"]) for c in GOLDEN_CASES]
