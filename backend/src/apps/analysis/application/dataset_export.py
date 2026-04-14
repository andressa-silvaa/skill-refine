"""
Export training / calibration rows from completed analyses (no PII in default mode).

Schema ``1.1`` (JSONL): gold label = persisted ``seniority_final_label`` (review > rule).
See ``ml/data/schema/seniority_dataset_schema_v1_1.json``.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from typing import Any, Iterator

from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.interfaces.api.payloads import resume_detail_payload

from .inference.resume_mapper import resume_to_text
from .inference.safety import truncate_text
from .inference.signals.resume_signals import extract_resume_signals
from .internal_review import pseudo_key

DATASET_SCHEMA_VERSION = "1.1"
DATASET_KIND = "seniority"

_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,6}")


def _user_language_for_export(user_id: str) -> str:
    try:
        from apps.accounts.infrastructure.models import UserPreferences

        prefs = UserPreferences.objects.filter(user_id=user_id).first()
        if prefs and getattr(prefs, "language", None):
            return str(prefs.language)
    except Exception:
        pass
    return "pt-BR"


def sanitize_resume_text(text: str, max_chars: int = 8000) -> str:
    """Redact common PII patterns and cap length (for optional text export)."""
    t = _EMAIL_RE.sub("[redacted-email]", text or "")
    t = _PHONE_RE.sub("[redacted-phone]", t)
    t, _ = truncate_text(t.strip(), max_chars)
    return t


def _signals_dict(rs: Any) -> dict[str, Any]:
    d = asdict(rs)
    d["reasons"] = list(d.get("reasons") or ())
    return d


def _ml_suggestion_from_payload(pj: dict[str, Any]) -> str | None:
    """HF / legacy text-model hint only — not used as training gold."""
    for e in pj.get("seniorityEvidence") or []:
        if not isinstance(e, dict):
            continue
        if e.get("type") == "ml_suggestion" and e.get("label"):
            return str(e["label"])
    return None


def build_seniority_dataset_record(
    analysis: ResumeAnalysis,
    *,
    hash_salt: str,
    include_text: bool = False,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """
    One dataset row: pseudonymised keys, structured signals, labels and targets.
    v1.1 uses persisted gold columns; never ``payload_json.seniorityClass`` as training label.
    """
    resume = analysis.resume
    resume_data = resume_detail_payload(resume)
    language = _user_language_for_export(str(analysis.user_id))
    sections = resume_to_text(resume_data, language=language)
    rs = extract_resume_signals(resume_data, sections, language=language)

    pj = analysis.payload_json or {}
    completeness = pj.get("completeness") if isinstance(pj.get("completeness"), dict) else {}
    conf_db = (analysis.seniority_confidence or "").strip()
    conf = conf_db if conf_db in ("low", "medium", "high") else str(pj.get("seniorityConfidence") or "")
    if conf not in ("low", "medium", "high"):
        conf = str(conf) if conf else ""

    rule_label = (analysis.seniority_rule_label or "").strip() or str(pj.get("seniorityRuleBase") or "")
    final_label = (analysis.seniority_final_label or "").strip()
    if not final_label:
        final_label = rule_label
    if not final_label:
        final_label = str(pj.get("seniorityRuleBase") or "").strip()

    src = (analysis.seniority_label_source or "").strip() or "rule"
    if src not in ("rule", "review"):
        src = "rule"
    policy_v = (analysis.seniority_policy_version or "").strip()
    reviewed = src == "review"

    ver = (schema_version or DATASET_SCHEMA_VERSION).strip() or DATASET_SCHEMA_VERSION

    labels_block: dict[str, Any]
    if ver == "1.0":
        labels_block = {
            "seniority_label": final_label or str(pj.get("seniorityClass") or ""),
            "rule_label": rule_label,
            "ml_label": _ml_suggestion_from_payload(pj),
            "confidence": conf,
        }
    else:
        labels_block = {
            "seniority_label": final_label,
            "rule_label": rule_label,
            "ml_label": _ml_suggestion_from_payload(pj),
            "confidence": conf,
            "source": src,
            "policy_version": policy_v,
            "reviewed": reviewed,
        }

    record: dict[str, Any] = {
        "schema_version": ver,
        "dataset_kind": DATASET_KIND,
        "analysis_key": pseudo_key(raw_id=str(analysis.id), salt=hash_salt),
        "resume_key": pseudo_key(raw_id=str(analysis.resume_id), salt=hash_salt),
        "user_key": pseudo_key(raw_id=str(analysis.user_id), salt=hash_salt),
        "created_at": analysis.created_at.isoformat(),
        "language": language,
        "signals": _signals_dict(rs),
        "labels": labels_block,
        "targets": {
            "overall_score": analysis.score,
            "task_scores": dict(analysis.task_scores or {}),
            "completeness_score": completeness.get("score"),
            "completeness_level": completeness.get("level"),
        },
        "gating_reasons": list(pj.get("gatingReasons") or []) if isinstance(pj.get("gatingReasons"), list) else [],
        "insufficient_data": bool(pj.get("insufficientData")),
        "meta": {
            "seniority_ml_status": str(pj.get("seniorityMlStatus") or ""),
            "provider": analysis.provider or "",
            "model_version": analysis.model_version or "",
            "dataset_version": analysis.dataset_version or "",
            "label_source": src,
            "policy_version": policy_v,
        },
    }
    if include_text:
        record["text_sanitized"] = sanitize_resume_text(sections.full_text)
    return record


def iter_seniority_export_rows(
    *,
    limit: int | None = None,
    since: datetime | None = None,
    mode: str = "signals",
    id_hash_salt: str = "",
    schema_version: str | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Yield one record per completed analysis.

    mode:
      - signals: no CV text.
      - full: includes ``text_sanitized`` (still redacted + capped).
    """
    if mode not in ("signals", "full"):
        raise ValueError("mode must be 'signals' or 'full'")

    include_text = mode == "full"

    qs = (
        ResumeAnalysis.objects.filter(status=AnalysisStatus.DONE)
        .select_related("resume", "user")
        .prefetch_related(
            "resume__resumecontact",
            "resume__resumeexperience_set__resumeexperiencebullet_set",
            "resume__resumeeducation_set",
            "resume__resumeskill_set",
            "resume__resumelanguage_set",
        )
        .order_by("-created_at")
    )
    if since is not None:
        qs = qs.filter(created_at__gte=since)
    if limit is not None:
        qs = qs[:limit]

    salt = id_hash_salt
    for analysis in qs.iterator(chunk_size=200):
        yield build_seniority_dataset_record(
            analysis,
            hash_salt=salt,
            include_text=include_text,
            schema_version=schema_version,
        )


def write_seniority_export_jsonl(
    path: str,
    *,
    limit: int | None = None,
    since: datetime | None = None,
    mode: str = "signals",
    id_hash_salt: str = "",
    schema_version: str | None = None,
) -> int:
    """Write JSONL; returns number of rows written."""
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in iter_seniority_export_rows(
            limit=limit,
            since=since,
            mode=mode,
            id_hash_salt=id_hash_salt,
            schema_version=schema_version,
        ):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def iter_dataset_rows_for_analyses(
    analyses: list[ResumeAnalysis],
    *,
    hash_salt: str,
    include_text: bool = False,
    schema_version: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Export a fixed list of analyses (e.g. filtered low-confidence) to dataset records."""
    for analysis in analyses:
        yield build_seniority_dataset_record(
            analysis,
            hash_salt=hash_salt,
            include_text=include_text,
            schema_version=schema_version,
        )
