"""Sections task: Sentence classification (one label per line/sentence) or NER (BIO). Detects format from dataset."""
from __future__ import annotations

from pathlib import Path
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ..data import load_splits
from ..data.collators import SeniorityDataset, collate_seniority
from ..utils import ensure_padding_token

# Reuse sequence classification: sections as labels (EXPERIENCE, EDUCATION, SKILLS, ...)
SECTION_LABELS = ["EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "SUMMARY", "CONTACT", "OTHER"]


def get_label2id() -> dict[str, int]:
    return {l: i for i, l in enumerate(SECTION_LABELS)}


def get_id2label() -> dict[int, str]:
    return {i: l for i, l in enumerate(SECTION_LABELS)}


def build_model_and_tokenizer(base_model: str, num_labels: int | None = None):
    num_labels = num_labels or len(SECTION_LABELS)
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
):
    # Sections: if dataset has labels.sections as list of {tokens, tags} => NER; else sentence+label => reuse seniority-style
    train_records, val_records, test_records = load_splits(splits_dir, "sections", languages=languages)
    # Stub: sections task often has line_text + section label per line; we'd need SectionDataset(line_text, label)
    # For now reuse SeniorityDataset shape with section label if present (e.g. first section tag as doc-level)
    label2id = get_label2id()
    from ..data.collators import SeniorityDataset
    # Build records with resume_text and label = first section or OTHER
    def _section_record(rec: dict) -> dict:
        sections = (rec.get("labels") or {}).get("sections")
        if isinstance(sections, list) and sections:
            first = sections[0]
            if isinstance(first, dict) and "tags" in first:
                tags = first["tags"]
                lab = tags[0].replace("B-", "").replace("I-", "") if tags else "OTHER"
            else:
                lab = first.get("label", "OTHER") if isinstance(first, dict) else "OTHER"
        else:
            lab = "OTHER"
        return {**rec, "labels": {"seniority": lab if lab in label2id else "OTHER"}}
    train_records = [_section_record(r) for r in train_records]
    val_records = [_section_record(r) for r in val_records]
    test_records = [_section_record(r) for r in test_records]
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
        out = model(
            input_ids=batch.input_ids.to(device),
            attention_mask=batch.attention_mask.to(device),
        )
    return out.logits, batch.labels


def compute_metrics(logits: torch.Tensor, labels: torch.Tensor, id2label: dict[int, str]) -> dict[str, float]:
    from ..eval.metrics import accuracy, f1_macro
    preds = logits.argmax(dim=-1).cpu().numpy()
    labels_np = labels.cpu().numpy()
    return {
        "accuracy": accuracy(preds, labels_np),
        "f1_macro": f1_macro(preds, labels_np, list(id2label.values())),
    }
