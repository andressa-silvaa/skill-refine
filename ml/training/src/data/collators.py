"""Collators for DataLoader: seniority, quality (ordinal classification), matching (pairs)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch.utils.data import Dataset

from .load_dataset import normalize_quality_level


@dataclass
class SeniorityBatch:
    input_ids: torch.Tensor
    attention_mask: torch.Tensor
    labels: torch.LongTensor
    languages: list[str]  # per-sample language for per-language metrics (pt-BR, en-US, es-ES)


@dataclass
class QualityBatch:
    input_ids: torch.Tensor
    attention_mask: torch.Tensor
    labels: torch.LongTensor


@dataclass
class MatchingBiEncoderBatch:
    job_input_ids: torch.Tensor
    job_attention_mask: torch.Tensor
    resume_input_ids: torch.Tensor
    resume_attention_mask: torch.Tensor
    labels: torch.FloatTensor
    languages: list[str]


class SeniorityDataset(Dataset):
    def __init__(self, records: list[dict], tokenizer, max_length: int, label2id: dict[str, int]):
        self.records = records
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.label2id = label2id

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, i: int) -> dict[str, Any]:
        rec = self.records[i]
        text = (rec.get("inputs") or {}).get("resume_text") or ""
        lab = (rec.get("labels") or {}).get("seniority", "mid")
        enc = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        lang = (rec.get("language") or "pt-BR").strip()
        if lang in ("pt", "en", "es"):
            lang = {"pt": "pt-BR", "en": "en-US", "es": "es-ES"}.get(lang, "pt-BR")
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.label2id.get(lab, self.label2id["mid"]), dtype=torch.long),
            "language": lang,
        }


class QualityDataset(Dataset):
    def __init__(self, records: list[dict], tokenizer, max_length: int, label2id: dict[str, int]):
        self.records = records
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.label2id = label2id

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, i: int) -> dict[str, Any]:
        rec = self.records[i]
        text = (rec.get("inputs") or {}).get("resume_text") or ""
        labels = rec.get("labels") or {}
        level = normalize_quality_level(labels.get("quality_level"), labels.get("quality_score", 0))
        enc = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.label2id[level], dtype=torch.long),
        }


class MatchingBiEncoderDataset(Dataset):
    def __init__(self, records: list[dict], tokenizer, max_length: int):
        self.records = records
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, i: int) -> dict[str, Any]:
        rec = self.records[i]
        inputs = rec.get("inputs") or {}
        job_text = inputs.get("job_text") or ""
        resume_text = inputs.get("resume_text") or ""
        lab = (rec.get("labels") or {}).get("matching_score", 0)
        if not isinstance(lab, (int, float)):
            lab = float(lab) if lab else 0.0
        job_enc = self.tokenizer(job_text, max_length=self.max_length, padding="max_length", truncation=True, return_tensors="pt")
        resume_enc = self.tokenizer(resume_text, max_length=self.max_length, padding="max_length", truncation=True, return_tensors="pt")
        return {
            "job_input_ids": job_enc["input_ids"].squeeze(0),
            "job_attention_mask": job_enc["attention_mask"].squeeze(0),
            "resume_input_ids": resume_enc["input_ids"].squeeze(0),
            "resume_attention_mask": resume_enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(float(lab) / 100.0, dtype=torch.float32),
            "language": (rec.get("language") or "pt-BR").strip(),
        }


def collate_seniority(batch: list[dict]) -> SeniorityBatch:
    return SeniorityBatch(
        input_ids=torch.stack([b["input_ids"] for b in batch]),
        attention_mask=torch.stack([b["attention_mask"] for b in batch]),
        labels=torch.stack([b["labels"] for b in batch]),
        languages=[b.get("language", "pt-BR") for b in batch],
    )


def collate_quality(batch: list[dict]) -> QualityBatch:
    return QualityBatch(
        input_ids=torch.stack([b["input_ids"] for b in batch]),
        attention_mask=torch.stack([b["attention_mask"] for b in batch]),
        labels=torch.stack([b["labels"] for b in batch]),
    )


def collate_matching_bi(batch: list[dict]) -> MatchingBiEncoderBatch:
    return MatchingBiEncoderBatch(
        job_input_ids=torch.stack([b["job_input_ids"] for b in batch]),
        job_attention_mask=torch.stack([b["job_attention_mask"] for b in batch]),
        resume_input_ids=torch.stack([b["resume_input_ids"] for b in batch]),
        resume_attention_mask=torch.stack([b["resume_attention_mask"] for b in batch]),
        labels=torch.stack([b["labels"] for b in batch]),
        languages=[b.get("language", "pt-BR") for b in batch],
    )
