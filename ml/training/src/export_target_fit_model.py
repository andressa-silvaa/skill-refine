#!/usr/bin/env python3
"""
Deprecated alias: use ``export_target_fit_sklearn_model.py`` (dataset_version + metrics).
"""
from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    print("Use: python ml/training/src/export_target_fit_sklearn_model.py ...", file=sys.stderr)
    raise SystemExit(2)
