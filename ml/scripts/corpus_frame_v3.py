"""
Single source of truth for the v3 training frame.

Joins prose, specs, teacher rubric labels and the human review into one row per resume id, and
renders the exact text production reads (``resume_to_text_sanitized``) plus a tenure-free variant.

Two invariants this module enforces, because both were measured problems:

* ``prose.jsonl`` and ``labels_rubric.jsonl`` both have duplicated ids: concurrent resumable jobs
  appended the same work twice. Every file is deduped by id with last-write-wins, and the duplicate
  counts are reported so the dedupe is visible instead of implicit. Left alone, those rows would
  enter training with double weight.
* the sanitized text carries each role's duration in months, so a text model can read tenure
  instead of judging prose. ``strip_tenure`` removes it, which turns the caveat into a measurement.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3"
BACKEND_SRC = REPO_ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from apps.analysis.application.inference.text_sanitizer import (  # noqa: E402
    resume_to_text_sanitized,
)

BANDS = ("intern", "junior", "mid", "senior")
QUALITY_LEVELS = ("poor", "fair", "good")
SPEC_FILES = ("specs.jsonl", "specs_b.jsonl", "specs_cal.jsonl", "specs_q.jsonl", "specs_q2.jsonl")
TENURE_RE = re.compile(r"\s*\(\d+\s*meses\)")


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def load_deduped(path: Path, *, key: str = "id") -> tuple[dict[str, dict[str, Any]], int]:
    """Last write wins. Returns (rows_by_key, duplicate_count)."""
    rows: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for row in read_jsonl(path):
        row_key = str(row.get(key) or "")
        if not row_key:
            continue
        if row_key in rows:
            duplicates += 1
        rows[row_key] = row
    return rows, duplicates


def strip_tenure(text: str) -> str:
    """Drop the ``(N meses)`` markers the sanitizer injects, leaving only prose evidence."""
    return TENURE_RE.sub("", text)


def section_texts(resume_data: dict[str, Any]) -> dict[str, str]:
    """
    Split the resume into the four blocks that carry different evidence.

    Averaging one vector over the whole document lets a long skills list dilute two lines of
    achievement prose. Embedding the blocks separately and concatenating keeps them addressable, and
    it stays inside the doctrine of handoff 7.4 — the code only *locates* fields, every judgement
    about them is still the model's.
    """
    data = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else resume_data
    data = data if isinstance(data, dict) else {}

    roles: list[str] = []
    bullets: list[str] = []
    target = str(data.get("targetPosition") or "").strip()
    if target:
        roles.append(target)
    experiences = data.get("experiences") or []
    if isinstance(experiences, list):
        for exp in experiences[:12]:
            if not isinstance(exp, dict):
                continue
            title = str(exp.get("position") or exp.get("title") or "").strip()
            if title:
                roles.append(f"{title} (atual)" if exp.get("isCurrent") else title)
            for bullet in (exp.get("description") or [])[:10]:
                text = str(bullet).strip()
                if text:
                    bullets.append(text)

    credentials: list[str] = []
    for education in (data.get("educations") or data.get("education") or [])[:6]:
        if isinstance(education, dict):
            course = str(education.get("course") or education.get("degree") or "").strip()
            if course:
                credentials.append(course)
    for skill in (data.get("skills") or [])[:80]:
        name = str(skill.get("name") or "").strip() if isinstance(skill, dict) else str(skill).strip()
        if name:
            credentials.append(name)

    return {
        "summary": _clean(str(data.get("summary") or "")),
        "roles": _clean(" \n".join(roles)),
        "bullets": _clean(" \n".join(bullets)),
        "credentials": _clean(", ".join(credentials)),
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def human_band(verdict: dict[str, Any]) -> str | None:
    """``ok`` means the reviewer backed the label they were shown; mirror score_label_review.py."""
    raw = str(verdict.get("verdict") or "").strip().lower()
    if not raw:
        return None
    if raw == "ok":
        shown = str(verdict.get("llm_label") or "").strip().lower()
        return shown if shown in BANDS else None
    return raw if raw in BANDS else None


@dataclass
class Row:
    id: str
    language: str
    band_target: str
    quality_target: str | None
    writer_model: str
    occupation_uri: str
    occupation_label: str
    isco: str
    parallel_group: str | None
    total_months_design: int | None
    may_state_seniority: bool
    text: str
    text_no_tenure: str
    sections: dict[str, str] = field(default_factory=dict)
    teacher_band: str | None = None
    teacher_quality: dict[str, Any] = field(default_factory=dict)
    teacher_model: str | None = None
    mistral_band: str | None = None
    mistral_quality: dict[str, Any] = field(default_factory=dict)
    human_band: str | None = None
    human_impact: float | None = None

    @property
    def teacher_impact(self) -> int | None:
        value = self.teacher_quality.get("impact")
        return int(value) if isinstance(value, (int, float)) else None

    @property
    def teacher_clarity(self) -> int | None:
        value = self.teacher_quality.get("clarity")
        return int(value) if isinstance(value, (int, float)) else None

    @property
    def teacher_ats(self) -> int | None:
        value = self.teacher_quality.get("ats")
        return int(value) if isinstance(value, (int, float)) else None


@dataclass
class Frame:
    rows: list[Row]
    rubric_duplicates: int
    rubric_unique: int
    mistral_duplicates: int
    missing_quality_target: int
    prose_duplicates: int = 0

    def __len__(self) -> int:
        return len(self.rows)

    def with_quality_target(self) -> list[Row]:
        return [r for r in self.rows if r.quality_target in QUALITY_LEVELS]

    def with_teacher_band(self) -> list[Row]:
        return [r for r in self.rows if r.teacher_band in BANDS]

    def with_teacher_impact(self) -> list[Row]:
        return [r for r in self.rows if r.teacher_impact is not None]

    def with_human(self) -> list[Row]:
        return [r for r in self.rows if r.human_band in BANDS]


def build_frame(raw_dir: Path = RAW_DIR) -> Frame:
    specs: dict[str, dict[str, Any]] = {}
    for name in SPEC_FILES:
        for spec in read_jsonl(raw_dir / name):
            spec_id = str(spec.get("id") or "")
            if spec_id:
                specs[spec_id] = spec

    rubric, rubric_dupes = load_deduped(raw_dir / "labels_rubric.jsonl")
    mistral, mistral_dupes = load_deduped(raw_dir / "labels_mistral.jsonl")
    human, _ = load_deduped(raw_dir / "review_verdicts.jsonl")
    prose_rows, prose_dupes = load_deduped(raw_dir / "prose.jsonl")

    rows: list[Row] = []
    missing_quality = 0
    for row_id, prose in sorted(prose_rows.items()):
        resume_data = prose.get("resume_data")
        if not isinstance(resume_data, dict):
            continue
        text = resume_to_text_sanitized(resume_data)
        if not text:
            continue
        spec = specs.get(row_id) or {}
        occupation = prose.get("occupation") or spec.get("occupation") or {}
        quality_target = spec.get("quality_target")
        label = rubric.get(row_id) or {}
        if quality_target is None:
            quality_target = label.get("quality_target")
        if quality_target is None and row_id.startswith("q"):
            missing_quality += 1
        second = mistral.get(row_id) or {}
        verdict = human.get(row_id) or {}
        try:
            human_impact = float(verdict.get("impact_verdict"))
        except (TypeError, ValueError):
            human_impact = None
        rows.append(
            Row(
                id=row_id,
                language=str(prose.get("language") or ""),
                band_target=str(prose.get("band_target") or spec.get("band_target") or ""),
                quality_target=quality_target if quality_target in QUALITY_LEVELS else None,
                writer_model=str(prose.get("writer_model") or ""),
                occupation_uri=str(occupation.get("uri") or ""),
                occupation_label=str(occupation.get("label") or ""),
                isco=str(occupation.get("isco") or ""),
                parallel_group=prose.get("parallel_group"),
                total_months_design=spec.get("total_months_design"),
                may_state_seniority=bool(
                    prose.get("may_state_seniority", spec.get("may_state_seniority", False))
                ),
                text=text,
                text_no_tenure=strip_tenure(text),
                sections=section_texts(resume_data),
                teacher_band=label.get("llm_label"),
                teacher_quality=label.get("quality") if isinstance(label.get("quality"), dict) else {},
                teacher_model=label.get("labeler_model"),
                mistral_band=second.get("llm_label"),
                mistral_quality=second.get("quality") if isinstance(second.get("quality"), dict) else {},
                human_band=human_band(verdict),
                human_impact=human_impact,
            )
        )
    return Frame(
        rows=rows,
        rubric_duplicates=rubric_dupes,
        rubric_unique=len(rubric),
        mistral_duplicates=mistral_dupes,
        missing_quality_target=missing_quality,
        prose_duplicates=prose_dupes,
    )


def main() -> int:
    import collections

    frame = build_frame()
    print(f"prose rows usable            : {len(frame)}")
    print(f"prose duplicate lines dropped: {frame.prose_duplicates}")
    print(f"labels_rubric unique ids     : {frame.rubric_unique}")
    print(f"labels_rubric duplicate lines: {frame.rubric_duplicates}")
    print(f"labels_mistral duplicates    : {frame.mistral_duplicates}")
    print(f"q* rows with no quality_target: {frame.missing_quality_target}")
    print()
    print(f"rows with quality_target : {len(frame.with_quality_target())}")
    print(f"rows with teacher band   : {len(frame.with_teacher_band())}")
    print(f"rows with teacher impact : {len(frame.with_teacher_impact())}")
    print(f"rows with human verdict  : {len(frame.with_human())}")
    print()
    print("band_target        :", dict(collections.Counter(r.band_target for r in frame.rows)))
    print("quality_target     :", dict(collections.Counter(r.quality_target for r in frame.rows)))
    print("writer_model       :", dict(collections.Counter(r.writer_model for r in frame.rows)))
    print("language           :", dict(collections.Counter(r.language for r in frame.rows)))
    print("distinct occupations:", len({r.occupation_uri for r in frame.rows}))
    print()
    tenure_rows = sum(1 for r in frame.rows if r.text != r.text_no_tenure)
    print(f"rows whose text carries tenure markers: {tenure_rows}")
    sample = next(r for r in frame.rows if r.text != r.text_no_tenure)
    print(f"  with tenure   : {sample.text[:160]}")
    print(f"  without tenure: {sample.text_no_tenure[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
