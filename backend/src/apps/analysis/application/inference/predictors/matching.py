"""
Matching predictor (optional): vaga vs currículo.
Placeholder: returns heuristic-based score when job_text provided.
"""
from __future__ import annotations


def predict_matching(
    resume_text: str,
    job_text: str,
    language: str,
) -> tuple[int, list[str]]:
    """
    Placeholder: simple keyword overlap score 0-100 and top matches.
    No LLM; heuristics only.
    """
    if not job_text or not resume_text:
        return (0, [])
    job_words = set((job_text or "").lower().split())
    resume_words = set((resume_text or "").lower().split())
    overlap = job_words & resume_words
    overlap.discard("")
    n_job = len(job_words) or 1
    n_overlap = len(overlap)
    score = min(100, int(100 * n_overlap / min(n_job, 50)))
    top = list(overlap)[:10]
    return (score, top)
