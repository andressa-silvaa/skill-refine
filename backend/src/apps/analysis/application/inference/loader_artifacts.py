"""
Achar e abrir os artefatos no disco: metadata, diretório por idioma/tarefa, HF e TF-IDF.

Separado de ``loader.py`` para que aquele arquivo mostre os três bundles que a inferência pede,
sem o caminho de arquivo e o desempacotamento no meio. Nada aqui decide nada — só resolve caminho
e carrega.
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")


class _MatchingBiEncoderWithProjection:
    """Lazy wrapper around the custom matching bi-encoder artifact."""

    def __init__(self, encoder, hidden_size: int, dropout: float = 0.1, blend_alpha: float = 0.65):
        import torch

        self._torch = torch
        self.encoder = encoder
        self.hidden_size = hidden_size
        self.blend_alpha = float(blend_alpha)
        self.proj = torch.nn.Sequential(
            torch.nn.Linear(hidden_size * 2, hidden_size),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_size, 1),
        )

    def load_state_dict(self, state_dict):
        self.proj.load_state_dict({k.replace("proj.", "", 1): v for k, v in state_dict.items() if k.startswith("proj.")}, strict=True)
        encoder_state = {k.replace("encoder.", "", 1): v for k, v in state_dict.items() if k.startswith("encoder.")}
        self.encoder.load_state_dict(encoder_state, strict=False)

    def eval(self):
        self.encoder.eval()
        self.proj.eval()
        return self

    def __call__(self, job_input_ids, job_attention_mask, resume_input_ids, resume_attention_mask):
        F = self._torch.nn.functional
        job_out = self.encoder(input_ids=job_input_ids, attention_mask=job_attention_mask)
        resume_out = self.encoder(input_ids=resume_input_ids, attention_mask=resume_attention_mask)
        job_pooled = job_out.last_hidden_state[:, 0]
        resume_pooled = resume_out.last_hidden_state[:, 0]
        cos = F.cosine_similarity(job_pooled.unsqueeze(1), resume_pooled.unsqueeze(0), dim=-1).diag()
        concat = self._torch.cat([job_pooled, resume_pooled], dim=-1)
        score = self.proj(concat).squeeze(-1)
        score = self._torch.sigmoid(score)
        return (self.blend_alpha * score) + ((1.0 - self.blend_alpha) * ((cos + 1.0) / 2.0))


def _load_metadata(model_dir: Path) -> dict:
    """Load metadata.json from model dir (parent of hf/)."""
    meta_path = model_dir / "metadata.json"
    if not meta_path.exists():
        meta_path = (model_dir / ".." / "metadata.json").resolve()
    if not meta_path.exists():
        return {}
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


def _metadata_supports_task(metadata: dict, task: str) -> bool:
    """Return True when metadata declares a compatible task for the requested bundle."""
    meta_task = str((metadata or {}).get("task") or "").strip().lower()
    requested = str(task or "").strip().lower()
    if not meta_task:
        return True
    if meta_task in {requested, "multitask"}:
        return True
    if meta_task.startswith(f"{requested}-"):
        return True
    if requested == "seniority" and meta_task == "text_seniority":
        return True
    return False


def _load_hf_seniority(hf_dir: Path) -> tuple[Any, Any, dict]:
    """Load HF model + tokenizer for seniority. Returns (model, tokenizer, metadata)."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        raise RuntimeError("transformers required for HF mode; install: pip install transformers torch")
    tokenizer = AutoTokenizer.from_pretrained(str(hf_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(hf_dir))
    model.eval()
    meta_dir = hf_dir.parent if hf_dir.name == "hf" else hf_dir
    metadata = _load_metadata(meta_dir)
    return model, tokenizer, metadata


def _load_tfidf(path: Path) -> tuple[Any, list[str]]:
    """Load TF-IDF + LogReg pipeline from pickle."""
    with open(path, "rb") as f:
        data = pickle.load(f)
    pipeline = data.get("pipeline")
    labels = data.get("labels", list(SENIORITY_LABELS))
    if pipeline is None:
        raise ValueError("Invalid TF-IDF model: no pipeline")
    return pipeline, labels


def _resolve_model_dir(config: dict, language: str, task: str = "seniority") -> tuple[Path, str, dict]:
    model_root = Path(config.get("model_root", config.get("model_dir", Path())))
    version_by_lang = config.get("model_version_by_lang") or {}
    version_by_task = config.get("model_version_by_task") or {}
    version_by_task_lang = config.get("model_version_by_task_lang") or {}
    model_version = (
        version_by_task_lang.get(f"{task}:{language}")
        or version_by_task_lang.get(f"{task}:{language.strip()}")
        or version_by_task.get(task)
        or version_by_lang.get(language)
        or config.get("model_version", "analysis_v1_pt")
    )
    model_dir = model_root / model_version
    metadata = _load_metadata(model_dir)
    metadata.setdefault("model_version", model_version)
    metadata.setdefault("dataset_version", "unknown")
    metadata.setdefault("languages_supported", [])
    metadata.setdefault("provider", "local")
    return model_dir, model_version, metadata


def _resolve_model_path(config: dict, language: str, task: str = "seniority") -> tuple[Path | None, str, dict]:
    """
    Resolve model path for given language.
    Returns (hf_path_or_none, model_version, metadata).
    """
    model_dir, model_version, metadata = _resolve_model_dir(config, language, task=task)
    model_mode = config.get("model_mode", "hf")

    if model_mode == "heuristics":
        return (None, model_version, {"provider": "heuristics"})

    hf_dir = model_dir / "hf" if (model_dir / "hf").exists() else model_dir

    if not hf_dir.exists():
        return (None, model_version, {})

    config_path = hf_dir / "config.json"
    if not config_path.exists():
        return (None, model_version, {})

    return (hf_dir, model_version, metadata)
