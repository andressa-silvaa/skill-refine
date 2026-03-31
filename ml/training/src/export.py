"""
Export entry point. Run from repo root:
  python ml/training/src/export.py --model_version analysis_v1_pt --format hf
  python ml/training/src/export.py --model_version analysis_v1_pt --format onnx
"""
from __future__ import annotations

import sys
from pathlib import Path

_TRAINING_DIR = Path(__file__).resolve().parent.parent
if str(_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(_TRAINING_DIR))

from export import main

if __name__ == "__main__":
    main()
