#!/usr/bin/env bash
# Wrapper for Unix/macOS; Windows: use `python ml/scripts/run_gold_pipeline_with_seed.py`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec python ml/scripts/run_gold_pipeline_with_seed.py "$@"
