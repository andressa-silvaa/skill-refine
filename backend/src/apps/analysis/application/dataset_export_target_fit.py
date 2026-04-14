"""
Export target-fit training rows (signals-only, no resume/job text).

Schema: ``ml/data/schema/target_fit_dataset_schema_v1_0.json``.
Uses the same pseudo-key hashing as seniority export.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterator

from apps.analysis.models import AnalysisStatus, ResumeAnalysis
from apps.resumes.interfaces.api.payloads import resume_detail_payload

from .inference.resume_mapper import resume_to_text
from .inference.target_fit import (
    compute_target_fit_policy,
    extract_target_fit_signals,
    infer_domain_category,
)
from .internal_review import pseudo_key

TARGET_FIT_SCHEMA_VERSION = "1.0"
TARGET_FIT_DATASET_KIND = "target_fit"


def _signals_numeric_only(sig: Any) -> dict[str, Any]:
    d = asdict(sig) if hasattr(sig, "__dataclass_fields__") else dict(sig)
    return {
        "required_terms_total": int(d.get("required_terms_total") or 0),
        "required_terms_hit": int(d.get("required_terms_hit") or 0),
        "skills_total": int(d.get("skills_total") or 0),
        "skills_hit": int(d.get("skills_hit") or 0),
        "experience_keyword_hits": int(d.get("experience_keyword_hits") or 0),
        "education_alignment": str(d.get("education_alignment") or "weak"),
        "portfolio_evidence": bool(d.get("portfolio_evidence")),
        "completeness_score": int(d.get("completeness_score") or 0),
    }


def _user_language_for_export(user_id: str) -> str:
    try:
        from apps.accounts.infrastructure.models import UserPreferences

        prefs = UserPreferences.objects.filter(user_id=user_id).first()
        if prefs and getattr(prefs, "language", None):
            return str(prefs.language)
    except Exception:
        pass
    return "pt-BR"


def _fit_level(score: int) -> str:
    if score < 40:
        return "poor"
    if score < 70:
        return "ok"
    return "strong"


def build_target_fit_dataset_record(
    analysis: ResumeAnalysis,
    *,
    hash_salt: str,
    schema_version: str | None = None,
    label_source: str = "policy",
    lang_filter: str | None = None,
) -> dict[str, Any] | None:
    """
    One JSONL row or None if targetPosition missing.
    Signals extracted with job_text=None (consistent weak target signal).
    Label uses the same policy with has_job_text=False.
    """
    resume_data = resume_detail_payload(analysis.resume)
    data_block = resume_data.get("data") if isinstance(resume_data.get("data"), dict) else {}
    target_pos = str(data_block.get("targetPosition") or "").strip()
    if not target_pos:
        return None

    lang = _user_language_for_export(str(analysis.user_id))
    if lang_filter and lang_filter.strip():
        if lang.strip().lower() != lang_filter.strip().lower():
            return None

    sections = resume_to_text(resume_data, language=lang)
    resume_snippet = (sections.full_text or "")[:12000]

    pj = analysis.payload_json or {}
    completeness = pj.get("completeness") if isinstance(pj.get("completeness"), dict) else {}
    comp_score = int(completeness.get("score") or 0)

    tf_signals = extract_target_fit_signals(
        resume_data,
        target_pos,
        None,
        lang,
        completeness_score=comp_score,
    )

    domain_target = infer_domain_category(target_pos, lang=lang)
    domain_resume = infer_domain_category(resume_snippet, lang=lang)
    td = str(domain_target.get("domainCategory") or "general")
    rd = str(domain_resume.get("domainCategory") or "general")

    has_job = bool((analysis.job_description_text or "").strip())

    fit_score = int(
        compute_target_fit_policy(
            tf_signals,
            has_job_text=False,
            resume_domain=rd,
            target_domain=td,
        )
    )

    src = (label_source or "policy").strip().lower()
    if src not in ("policy", "review", "prefer-review"):
        src = "policy"

    reviewed_score: int | None = None
    if src in ("review", "prefer-review"):
        gold = pj.get("targetFitGoldScore")
        gold_src = str(pj.get("targetFitLabelSource") or "").strip().lower()
        if isinstance(gold, (int, float)) and gold_src == "review":
            reviewed_score = int(max(0, min(100, round(float(gold)))))

    final_score = fit_score
    final_source = "policy"
    if reviewed_score is not None:
        if src == "review":
            final_score = reviewed_score
            final_source = "review"
        elif src == "prefer-review":
            final_score = reviewed_score
            final_source = "review"
    elif src == "review":
        return None

    ver = (schema_version or TARGET_FIT_SCHEMA_VERSION).strip() or TARGET_FIT_SCHEMA_VERSION
    now = datetime.now(timezone.utc).isoformat()

    return {
        "schema_version": ver,
        "dataset_kind": TARGET_FIT_DATASET_KIND,
        "analysis_key": pseudo_key(raw_id=str(analysis.id), salt=hash_salt),
        "resume_key": pseudo_key(raw_id=str(analysis.resume_id), salt=hash_salt),
        "user_key": pseudo_key(raw_id=str(analysis.user_id), salt=hash_salt),
        "lang": lang,
        "target_position": target_pos[:200],
        "domain_category": td,
        "resume_domain_category": rd,
        "has_job_description": has_job,
        "signals": _signals_numeric_only(tf_signals),
        "labels": {
            "fit_score": final_score,
            "fit_level": _fit_level(final_score),
            "label_source": final_source,
        },
        "meta": {
            "generated_at": now,
            "export_kind": "target_fit_signals_v1",
            "policy_score": fit_score,
        },
    }


def iter_target_fit_export_rows(
    *,
    limit: int | None = None,
    since: datetime | None = None,
    id_hash_salt: str = "",
    schema_version: str | None = None,
    label_source: str = "policy",
    lang: str | None = None,
) -> Iterator[dict[str, Any]]:
    qs = (
        ResumeAnalysis.objects.filter(status=AnalysisStatus.DONE)
        .select_related("resume", "user")
        .prefetch_related(
            "resume__resumecontact",
            "resume__resumeexperience_set__resumeexperiencebullet_set",
            "resume__resumeeducation_set",
            "resume__resumeskill_set",
        )
        .order_by("-created_at")
    )
    if since is not None:
        qs = qs.filter(created_at__gte=since)
    if limit is not None:
        qs = qs[:limit]

    salt = id_hash_salt
    lang_override = (lang or "").strip() or None
    for analysis in qs.iterator(chunk_size=200):
        rec = build_target_fit_dataset_record(
            analysis,
            hash_salt=salt,
            schema_version=schema_version,
            label_source=label_source,
            lang_filter=lang_override,
        )
        if rec is not None:
            yield rec


def write_target_fit_export_jsonl(
    path: str,
    *,
    limit: int | None = None,
    since: datetime | None = None,
    id_hash_salt: str = "",
    schema_version: str | None = None,
    label_source: str = "policy",
    lang: str | None = None,
) -> int:
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in iter_target_fit_export_rows(
            limit=limit,
            since=since,
            id_hash_salt=id_hash_salt,
            schema_version=schema_version,
            label_source=label_source,
            lang=lang,
        ):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count
