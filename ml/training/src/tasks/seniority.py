"""Seniority task: Sequence Classification (intern|junior|mid|senior)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ..data import SeniorityDataset, collate_seniority, load_splits
from ..eval.metrics import accuracy, f1_macro, classification_report_per_lang, confusion_matrix_and_report
from ..utils import ensure_padding_token

SENIORITY_LABELS = ("intern", "junior", "mid", "senior")


def get_label2id() -> dict[str, int]:
    return {l: i for i, l in enumerate(SENIORITY_LABELS)}


def get_id2label() -> dict[int, str]:
    return {i: l for i, l in enumerate(SENIORITY_LABELS)}


def build_model_and_tokenizer(base_model: str, num_labels: int = 4):
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=num_labels)
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
    label2id = get_label2id()
    train_records, val_records, test_records = load_splits(
        splits_dir, "seniority", languages=languages, ablations=ablations, drop_section_value=drop_section_value
    )
    train_ds = SeniorityDataset(train_records, tokenizer, max_length, label2id)
    val_ds = SeniorityDataset(val_records, tokenizer, max_length, label2id) if val_records else None
    test_ds = SeniorityDataset(test_records, tokenizer, max_length, label2id) if test_records else None
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_seniority)
    val_dl = DataLoader(val_ds, batch_size=batch_size, collate_fn=collate_seniority) if val_ds else None
    test_dl = DataLoader(test_ds, batch_size=batch_size, collate_fn=collate_seniority) if test_ds else None
    return train_dl, val_dl, test_dl, (train_records, val_records, test_records)


def train_step(model, batch, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.train()
    inputs = {
        "input_ids": batch.input_ids.to(device),
        "attention_mask": batch.attention_mask.to(device),
        "labels": batch.labels.to(device),
    }
    out = model(**inputs)
    return out.loss, out.logits


def eval_step(model, batch, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    with torch.no_grad():
        inputs = {
            "input_ids": batch.input_ids.to(device),
            "attention_mask": batch.attention_mask.to(device),
        }
        out = model(**inputs)
        logits = out.logits
    return logits, batch.labels


def compute_metrics(logits: torch.Tensor, labels: torch.Tensor, id2label: dict[int, str]) -> dict[str, float]:
    preds = logits.argmax(dim=-1).cpu()
    labels_cpu = labels.cpu()
    acc = accuracy(preds.numpy(), labels_cpu.numpy())
    f1 = f1_macro(preds.numpy(), labels_cpu.numpy(), list(id2label.values()))
    return {"accuracy": acc, "f1_macro": f1}


def run_eval(model, dataloader, device, id2label) -> tuple[dict[str, float], list, list, list[str]]:
    all_preds, all_labels, all_langs = [], [], []
    lang_per_batch = None
    model.eval()
    with torch.no_grad():
        for batch in dataloader:
            logits, labels = eval_step(model, batch, device)
            preds = logits.argmax(dim=-1).cpu()
            all_preds.append(preds)
            all_labels.append(labels.cpu())
            if hasattr(batch, "language"):
                all_langs.extend(batch.language)
    preds_cat = torch.cat(all_preds, dim=0).numpy()
    labels_cat = torch.cat(all_labels, dim=0).numpy()
    # Per-language: we need language per sample; if not in batch, pass None and report global only
    report_global = classification_report_per_lang(labels_cat, preds_cat, list(id2label.values()), None)
    cm, cm_report = confusion_matrix_and_report(labels_cat, preds_cat, list(id2label.values()))
    metrics = {
        "accuracy": accuracy(preds_cat, labels_cat),
        "f1_macro": f1_macro(preds_cat, labels_cat, list(id2label.values())),
    }
    return metrics, cm, cm_report, report_global
