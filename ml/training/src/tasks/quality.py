"""Quality task: ordinal sequence classification (poor/ok/strong)."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ..data import QualityDataset, collate_quality, load_splits, normalize_quality_level
from ..eval.metrics import accuracy, f1_macro, mse_mae, correlation
from ..utils import ensure_padding_token


QUALITY_LEVELS = ("poor", "ok", "strong")
QUALITY_LEVEL_TO_SCORE = {
    "poor": 30,
    "ok": 55,
    "strong": 84,
}


def get_label2id() -> dict[str, int]:
    return {label: idx for idx, label in enumerate(QUALITY_LEVELS)}


def get_id2label() -> dict[int, str]:
    return {idx: label for idx, label in enumerate(QUALITY_LEVELS)}


def build_model_and_tokenizer(base_model: str):
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=len(QUALITY_LEVELS))
    tokenizer, model = ensure_padding_token(tokenizer, model)
    return model, tokenizer


def build_dataloaders(
    splits_dir: Path,
    tokenizer,
    max_length: int,
    batch_size: int,
    languages: list[str] | None = None,
    ablations: list[str] | None = None,
    drop_section_value: str | None = None,
):
    train_records, val_records, test_records = load_splits(
        splits_dir, "quality", languages=languages, ablations=ablations, drop_section_value=drop_section_value
    )
    label2id = get_label2id()
    train_ds = QualityDataset(train_records, tokenizer, max_length, label2id)
    val_ds = QualityDataset(val_records, tokenizer, max_length, label2id) if val_records else None
    test_ds = QualityDataset(test_records, tokenizer, max_length, label2id) if test_records else None
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_quality)
    val_dl = DataLoader(val_ds, batch_size=batch_size, collate_fn=collate_quality) if val_ds else None
    test_dl = DataLoader(test_ds, batch_size=batch_size, collate_fn=collate_quality) if test_ds else None
    return train_dl, val_dl, test_dl, (train_records, val_records, test_records)


def train_step(model, batch, device, class_weights: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    model.train()
    inputs = {
        "input_ids": batch.input_ids.to(device),
        "attention_mask": batch.attention_mask.to(device),
    }
    logits = model(**inputs).logits
    labels = batch.labels.to(device)
    loss = torch.nn.functional.cross_entropy(logits, labels, weight=class_weights)
    return loss, logits


def eval_step(model, batch, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    with torch.no_grad():
        inputs = {
            "input_ids": batch.input_ids.to(device),
            "attention_mask": batch.attention_mask.to(device),
        }
        logits = model(**inputs).logits
    return logits, batch.labels


def compute_metrics(logits: torch.Tensor, labels: torch.Tensor) -> dict[str, float]:
    id2label = get_id2label()
    preds = logits.argmax(dim=-1).cpu().numpy()
    labels_np = labels.cpu().numpy()
    pred_scores = np.array([QUALITY_LEVEL_TO_SCORE[id2label[int(idx)]] for idx in preds], dtype=float)
    true_scores = np.array([QUALITY_LEVEL_TO_SCORE[id2label[int(idx)]] for idx in labels_np], dtype=float)
    mse, mae = mse_mae(true_scores, pred_scores)
    pearson, spearman = correlation(true_scores, pred_scores)
    return {
        "accuracy": accuracy(labels_np, preds),
        "f1_macro": f1_macro(labels_np, preds, list(QUALITY_LEVELS)),
        "mse_score": mse,
        "mae_score": mae,
        "pearson_score": pearson,
        "spearman_score": spearman,
    }
