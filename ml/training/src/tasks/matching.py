"""Matching task: Bi-encoder (cosine similarity) or Cross-encoder. D1) Bi-encoder recommended."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import AutoModel, AutoTokenizer

from ..data import MatchingBiEncoderDataset, collate_matching_bi, load_splits
from ..eval.metrics import mse_mae, correlation


def build_biencoder_and_tokenizer(base_model: str):
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModel.from_pretrained(base_model)
    return model, tokenizer


def build_dataloaders(
    splits_dir: Path,
    tokenizer,
    max_length: int,
    batch_size: int,
    languages: list[str] | None = None,
):
    train_records, val_records, test_records = load_splits(splits_dir, "matching", languages=languages)
    train_ds = MatchingBiEncoderDataset(train_records, tokenizer, max_length)
    val_ds = MatchingBiEncoderDataset(val_records, tokenizer, max_length) if val_records else None
    test_ds = MatchingBiEncoderDataset(test_records, tokenizer, max_length) if test_records else None
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_matching_bi)
    val_dl = DataLoader(val_ds, batch_size=batch_size, collate_fn=collate_matching_bi) if val_ds else None
    test_dl = DataLoader(test_ds, batch_size=batch_size, collate_fn=collate_matching_bi) if test_ds else None
    return train_dl, val_dl, test_dl, (train_records, val_records, test_records)


class BiEncoderWithProjection(torch.nn.Module):
    """Shared encoder + cosine similarity; optional projection for score regression."""

    def __init__(self, encoder, hidden_size: int, dropout: float = 0.1, blend_alpha: float = 0.65):
        super().__init__()
        self.encoder = encoder
        self.hidden_size = hidden_size
        self.blend_alpha = float(blend_alpha)
        self.proj = torch.nn.Sequential(
            torch.nn.Linear(hidden_size * 2, hidden_size),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_size, 1),
        )

    def forward(
        self,
        job_input_ids,
        job_attention_mask,
        resume_input_ids,
        resume_attention_mask,
    ):
        job_out = self.encoder(input_ids=job_input_ids, attention_mask=job_attention_mask)
        resume_out = self.encoder(input_ids=resume_input_ids, attention_mask=resume_attention_mask)
        job_pooled = job_out.last_hidden_state[:, 0]
        resume_pooled = resume_out.last_hidden_state[:, 0]
        # Option A: cosine sim
        cos = F.cosine_similarity(job_pooled.unsqueeze(1), resume_pooled.unsqueeze(0), dim=-1).diag()
        # Option B: concat + MLP for score
        concat = torch.cat([job_pooled, resume_pooled], dim=-1)
        score = self.proj(concat).squeeze(-1)
        score = torch.sigmoid(score)
        # Blend learned score with cosine to stabilize regression without collapsing to hard buckets.
        return (self.blend_alpha * score) + ((1.0 - self.blend_alpha) * ((cos + 1.0) / 2.0))


def train_step(model, batch, device, huber_beta: float = 0.08) -> tuple[torch.Tensor, torch.Tensor]:
    model.train()
    job_ids = batch.job_input_ids.to(device)
    job_mask = batch.job_attention_mask.to(device)
    res_ids = batch.resume_input_ids.to(device)
    res_mask = batch.resume_attention_mask.to(device)
    labels = batch.labels.to(device)
    score = model(job_ids, job_mask, res_ids, res_mask)
    loss = F.smooth_l1_loss(score, labels, beta=huber_beta)
    return loss, score


def eval_step(model, batch, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    with torch.no_grad():
        score = model(
            batch.job_input_ids.to(device),
            batch.job_attention_mask.to(device),
            batch.resume_input_ids.to(device),
            batch.resume_attention_mask.to(device),
        )
    return score, batch.labels


def compute_metrics(logits: torch.Tensor, labels: torch.Tensor) -> dict[str, float]:
    preds = logits.cpu().numpy().astype(float)
    labels_np = labels.cpu().numpy().astype(float)
    mse, mae = mse_mae(labels_np, preds)
    pearson, spearman = correlation(labels_np, preds)
    mse_score = mse * 10000.0
    mae_score = mae * 100.0
    bucket_accuracy = float(((preds * 100).astype(int) // 20 == (labels_np * 100).astype(int) // 20).mean())
    return {
        "mse": mse,
        "mae": mae,
        "mse_score": mse_score,
        "mae_score": mae_score,
        "pearson": pearson,
        "spearman": spearman,
        "bucket_accuracy": bucket_accuracy,
    }


def compute_metrics_per_language(logits: torch.Tensor, labels: torch.Tensor, languages: list[str]) -> dict[str, float]:
    if not languages or len(languages) != int(labels.shape[0]):
        return {}
    preds = logits.cpu().numpy().astype(float)
    labels_np = labels.cpu().numpy().astype(float)
    lang_arr = np.array(languages)
    metrics: dict[str, float] = {}
    for lang in sorted(set(languages)):
        mask = lang_arr == lang
        if int(mask.sum()) == 0:
            continue
        mse, mae = mse_mae(labels_np[mask], preds[mask])
        pearson, spearman = correlation(labels_np[mask], preds[mask])
        metrics[f"mae_score_{lang}"] = mae * 100.0
        metrics[f"pearson_{lang}"] = pearson
        metrics[f"spearman_{lang}"] = spearman
        metrics[f"bucket_accuracy_{lang}"] = float(
            (((preds[mask] * 100).astype(int) // 20) == ((labels_np[mask] * 100).astype(int) // 20)).mean()
        )
    return metrics


def save_matching_artifact(model: BiEncoderWithProjection, tokenizer, output_dir: Path, config: dict | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    encoder_dir = output_dir / "encoder"
    encoder_dir.mkdir(parents=True, exist_ok=True)
    model.encoder.save_pretrained(encoder_dir)
    tokenizer.save_pretrained(encoder_dir)
    torch.save(model.state_dict(), output_dir / "model.pt")
    bundle_config = {
        "hidden_size": model.hidden_size,
        "dropout": 0.1,
        "blend_alpha": model.blend_alpha,
        "model_type": "matching-biencoder-projection",
    }
    if config:
        bundle_config.update(
            {
                "model_version": config.get("model_version"),
                "dataset_version": config.get("dataset_version"),
                "languages": config.get("languages", []),
                "max_length": config.get("max_length", 512),
                "task": "matching",
                "trained_at": config.get("trained_at"),
            }
        )
    (output_dir / "matching_config.json").write_text(json.dumps(bundle_config, indent=2, ensure_ascii=False), encoding="utf-8")
