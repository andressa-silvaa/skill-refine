"""
Training entry point. Run from repo root or ml/training:
  python ml/training/src/train.py --task seniority --language pt-BR --base_model neuralmind/bert-base-portuguese-cased
  python ml/training/src/train.py --task quality --language pt-BR --base_model neuralmind/bert-base-portuguese-cased
  python ml/training/src/train.py --task matching --language pt-BR --base_model neuralmind/bert-base-portuguese-cased
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure ml/training is on path so "from train import main" works
_TRAINING_DIR = Path(__file__).resolve().parent.parent
if str(_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(_TRAINING_DIR))

from train import main

if __name__ == "__main__":
    main()
