"""Quality task: Regression 0-100 (or classification if labels are classes)."""
from __future__ import annotations

from pathlib import Path
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ..data import QualityDataset, collate_quality, load_splits
from ..eval.metrics import mse_mae, correlation


def build_model_and_tokenizer(base_model: str, regression: bool = True):
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    # Use sequence classification with 1 output for regression (we use loss MSE in training loop)
    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=1)
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
    train_ds = QualityDataset(train_records, tokenizer, max_length)
    val_ds = QualityDataset(val_records, tokenizer, max_length) if val_records else None
    test_ds = QualityDataset(test_records, tokenizer, max_length) if test_records else None
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_quality)
    val_dl = DataLoader(val_ds, batch_size=batch_size, collate_fn=collate_quality) if val_ds else None
    test_dl = DataLoader(test_ds, batch_size=batch_size, collate_fn=collate_quality) if test_ds else None
    return train_dl, val_dl, test_dl, (train_records, val_records, test_records)


def train_step(model, batch, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.train()
    inputs = {
        "input_ids": batch.input_ids.to(device),
        "attention_mask": batch.attention_mask.to(device),
    }
    logits = model(**inputs).logits.squeeze(-1)
    labels = batch.labels.to(device)
    loss = torch.nn.functional.mse_loss(logits, labels)
    return loss, logits


def eval_step(model, batch, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    with torch.no_grad():
        inputs = {
            "input_ids": batch.input_ids.to(device),
            "attention_mask": batch.attention_mask.to(device),
        }
        logits = model(**inputs).logits.squeeze(-1)
    return logits, batch.labels


def compute_metrics(logits: torch.Tensor, labels: torch.Tensor) -> dict[str, float]:
    preds = logits.cpu().numpy()
    labels_np = labels.cpu().numpy()
    mse, mae = mse_mae(labels_np, preds)
    pearson, spearman = correlation(labels_np, preds)
    return {"mse": mse, "mae": mae, "pearson": pearson, "spearman": spearman}
