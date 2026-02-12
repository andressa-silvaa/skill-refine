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
        return {
            "score": self.score,
            "task_scores": self.task_scores,
            "payload_json": {
                "insights": self.insights,
                "recommendations": self.recommendations,
            },
            "metadata": self.metadata,
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
