"""Matching task: Bi-encoder (cosine similarity) or Cross-encoder. D1) Bi-encoder recommended."""
from __future__ import annotations

from pathlib import Path
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

    def __init__(self, encoder, hidden_size: int, dropout: float = 0.1):
        super().__init__()
        self.encoder = encoder
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
        return score


def train_step(model, batch, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.train()
    job_ids = batch.job_input_ids.to(device)
    job_mask = batch.job_attention_mask.to(device)
    res_ids = batch.resume_input_ids.to(device)
    res_mask = batch.resume_attention_mask.to(device)
    labels = batch.labels.to(device)
    score = model(job_ids, job_mask, res_ids, res_mask)
    loss = F.mse_loss(score, labels)
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
    preds = logits.cpu().numpy()
    labels_np = labels.cpu().numpy()
    mse, mae = mse_mae(labels_np, preds)
    pearson, spearman = correlation(labels_np, preds)
    return {"mse": mse, "mae": mae, "pearson": pearson, "spearman": spearman}
