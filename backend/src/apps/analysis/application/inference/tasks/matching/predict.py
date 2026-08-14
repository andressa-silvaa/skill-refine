"""
Matching predictor: bi-encoder embeddings + cosine, or heuristic keyword overlap.
"""
from __future__ import annotations

from contextlib import nullcontext
from typing import Any

from apps.analysis.application.inference.cascade import CascadeResult, run_cascade
from apps.analysis.application.inference.tasks.target_fit.embedding import embedding_fit_scores


def _heuristic_matching(resume_text: str, job_text: str) -> tuple[int, list[str]]:
    """Simple keyword overlap score 0-100 and top matches."""
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


def _predict_hf_matching(model, tokenizer, resume_text: str, job_text: str, max_length: int = 512) -> int | None:
    """Bi-encoder: embed resume and job, cosine similarity. Returns score 0-100 or None."""
    try:
        import torch
        import torch.nn.functional as F
        r_inputs = tokenizer(
            resume_text[:12000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        j_inputs = tokenizer(
            job_text[:8000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        with torch.no_grad():
            r_out = model(**r_inputs)
            j_out = model(**j_inputs)
        r_emb = r_out.last_hidden_state[:, 0, :]
        j_emb = j_out.last_hidden_state[:, 0, :]
        sim = F.cosine_similarity(r_emb, j_emb).item()
        score = int(min(100, max(0, (sim + 1) * 50)))
        return score
    except Exception:
        pass
    return None


def _predict_custom_matching(model, tokenizer, resume_text: str, job_text: str, max_length: int = 512) -> int | None:
    """Custom trained bi-encoder projection model. Returns 0-100 or None."""
    try:
        try:
            import torch
        except Exception:
            torch = None

        r_inputs = tokenizer(
            resume_text[:12000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        j_inputs = tokenizer(
            job_text[:8000],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
        context = torch.no_grad() if torch is not None else nullcontext()
        with context:
            score = model(
                job_input_ids=j_inputs["input_ids"],
                job_attention_mask=j_inputs["attention_mask"],
                resume_input_ids=r_inputs["input_ids"],
                resume_attention_mask=r_inputs["attention_mask"],
            )
        value = float(score.squeeze(-1).item())
        return int(min(100, max(0, round(value * 100))))
    except Exception:
        pass
    return None


def predict_matching_detailed(
    resume_text: str,
    job_text: str,
    language: str,
    matching_bundle: tuple[Any, dict] | None = None,
    embeddings_model: Any = None,
) -> tuple[int, list[str], str]:
    """
    Predict matching score 0-100, top matches, and the provider that actually answered.

    Telemetry used to read the provider off the loaded bundle, so an analysis scored by
    matching_embeddings was still reported as heuristics — the provider table is evidence, so it
    has to name the step that produced the number.
    """
    if not job_text or not resume_text:
        return (0, [], "skipped_no_input")

    heuristic = _heuristic_matching(resume_text, job_text)

    def _bundle_parts() -> tuple[Any, dict[str, Any], Any, int] | None:
        if not matching_bundle:
            return None
        model_or_none, extra = matching_bundle
        if model_or_none is None or not isinstance(extra, dict) or not extra.get("tokenizer"):
            return None
        tokenizer = extra["tokenizer"]
        max_length = 512
        if isinstance(extra.get("metadata"), dict):
            limits = extra["metadata"].get("input_limits") or {}
            max_length = limits.get("max_tokens", 512)
        return model_or_none, extra, tokenizer, max_length

    def _step_custom() -> CascadeResult:
        parts = _bundle_parts()
        if parts is None:
            return CascadeResult(value=None, provider="matching_custom", status="skipped_no_bundle")
        model_or_none, extra, tokenizer, max_length = parts
        if extra.get("kind") != "matching-biencoder":
            return CascadeResult(value=None, provider="matching_custom", status="skipped_wrong_kind")
        score = _predict_custom_matching(model_or_none, tokenizer, resume_text, job_text, max_length)
        if score is None:
            return CascadeResult(value=None, provider="matching_custom", status="error")
        return CascadeResult(
            value=(score, heuristic[1]),
            provider="matching_custom",
            status="applied",
        )

    def _step_hf() -> CascadeResult:
        parts = _bundle_parts()
        if parts is None:
            return CascadeResult(value=None, provider="matching_hf", status="skipped_no_bundle")
        model_or_none, extra, tokenizer, max_length = parts
        if extra.get("kind") == "matching-biencoder":
            return CascadeResult(value=None, provider="matching_hf", status="skipped_custom_kind")
        score = _predict_hf_matching(model_or_none, tokenizer, resume_text, job_text, max_length)
        if score is None:
            return CascadeResult(value=None, provider="matching_hf", status="error")
        return CascadeResult(
            value=(score, heuristic[1]),
            provider="matching_hf",
            status="applied",
        )

    def _step_embeddings() -> CascadeResult:
        """
        Sentence-embedding cosine between resume and job posting.

        The two bundle-based steps above need artifacts that do not ship with the repo, so before
        this existed the effective provider was keyword overlap — which cannot see that "gestão de
        estoque" and "inventory control" are the same requirement. This reuses the multilingual
        bi-encoder already loaded for target_fit, so it needs no extra artifact and no labels.
        """
        if embeddings_model is None:
            return CascadeResult(value=None, provider="matching_embeddings", status="skipped_disabled")
        try:
            score, _cos, _kw = embedding_fit_scores(embeddings_model, resume_text, job_text)
        except Exception:
            return CascadeResult(value=None, provider="matching_embeddings", status="error")
        if not score:
            return CascadeResult(value=None, provider="matching_embeddings", status="error")
        return CascadeResult(
            value=(score, heuristic[1]),
            provider="matching_embeddings",
            status="applied",
        )

    def _step_heuristic() -> CascadeResult:
        return CascadeResult(value=heuristic, provider="heuristics", status="applied")

    result = run_cascade(
        [_step_custom, _step_hf, _step_embeddings, _step_heuristic], default=_step_heuristic()
    )
    score, top = result.value
    return score, top, result.provider


def predict_matching(
    resume_text: str,
    job_text: str,
    language: str,
    matching_bundle: tuple[Any, dict] | None = None,
    embeddings_model: Any = None,
) -> tuple[int, list[str]]:
    """Score and top matches only; see predict_matching_detailed for the provider."""
    score, top, _provider = predict_matching_detailed(
        resume_text,
        job_text,
        language,
        matching_bundle=matching_bundle,
        embeddings_model=embeddings_model,
    )
    return score, top
