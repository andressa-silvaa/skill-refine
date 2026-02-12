"""Task heads (for multi-task extension). Single-task uses AutoModelFor* directly."""
from __future__ import annotations

import torch
import torch.nn as nn
from transformers import AutoModel, AutoConfig


class SequenceClassificationHead(nn.Module):
    """Linear head for sequence classification (e.g. seniority)."""

    def __init__(self, hidden_size: int, num_labels: int, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_size, num_labels)

    def forward(self, pooled: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.dropout(pooled))


class RegressionHead(nn.Module):
    """Linear head for regression (e.g. quality_score 0-100)."""

    def __init__(self, hidden_size: int, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        self.regressor = nn.Linear(hidden_size, 1)

    def forward(self, pooled: torch.Tensor) -> torch.Tensor:
        return self.regressor(self.dropout(pooled)).squeeze(-1)
