"""
Types for analysis inference: AnalysisResult and internal structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    """Stable result shape for persistence and API."""

    score: int  # 0-100
    task_scores: dict[str, int | float | None]
    insights: dict[str, list[dict[str, Any]]]
    recommendations: list[dict[str, Any]]
    metadata: dict[str, str]
    payload_json: dict[str, Any]

    def to_persist_dict(self) -> dict[str, Any]:
        """Format for ResumeAnalysis persistence (score, task_scores, payload_json)."""
        meta = dict(self.metadata)
        meta.setdefault("datasetVersion", "")
        payload = dict(self.payload_json or {})
        payload["insights"] = self.insights
        payload["recommendations"] = self.recommendations
        return {
            "score": self.score,
            "task_scores": self.task_scores,
            "payload_json": payload,
            "metadata": meta,
        }


@dataclass
class ResumeSections:
    """Resume text split by section."""

    summary: str = ""
    experience: str = ""
    education: str = ""
    skills: str = ""
    languages: str = ""
    contact: str = ""
    projects: str = ""
    full_text: str = ""


def build_persist_payload(
    result: "AnalysisResult",
    *,
    rs: Any,
    base_label: str,
    final_label: str,
    seniority_label_source: str,
    seniority_policy_version: str,
    seniority_confidence: str,
    seniority_evidence: list[Any],
    text_pred: dict[str, Any],
    target_pos: str,
    fit_embedding_score: int | None,
    fit_signals_score: int,
    fit_score: int,
) -> dict[str, Any]:
    """
    Flatten an ``AnalysisResult`` plus the seniority and target-fit columns the worker persists.

    Lives here rather than in the orchestrator because it is the shape of the row, not a step of the
    pipeline: whoever changes ``AnalysisResult`` has to look at this in the same breath.
    """
    from apps.analysis.application.seniority_persist import build_seniority_evidence_json

    d = result.to_persist_dict()
    return {
        "score": d["score"],
        "task_scores": d["task_scores"],
        "payload_json": d["payload_json"],
        "model_name": d["metadata"]["modelName"],
        "model_version": d["metadata"]["modelVersion"],
        "dataset_version": d["metadata"].get("datasetVersion", ""),
        "provider": d["metadata"]["provider"],
        "seniority_rule_label": base_label,
        "seniority_final_label": final_label,
        "seniority_label_source": seniority_label_source,
        "seniority_policy_version": seniority_policy_version,
        "seniority_confidence_persist": seniority_confidence
        if seniority_confidence in ("low", "medium", "high")
        else "low",
        "seniority_evidence_json": build_seniority_evidence_json(rs, seniority_evidence),
        "seniority_text_label": str(text_pred.get("label") or "")[:16],
        "seniority_text_confidence": str(text_pred.get("confidence") or "")[:16],
        "target_fit_embedding_score": (fit_embedding_score if target_pos else None),
        "target_fit_signals_score": (int(fit_signals_score) if target_pos else None),
        "target_fit_final_score": (int(fit_score) if target_pos else None),
    }
