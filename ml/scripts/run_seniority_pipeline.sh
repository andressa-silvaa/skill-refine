#!/usr/bin/env bash
# One-shot seniority signals ML pipeline (Unix). Repository root = parent of ml/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
exec python ml/scripts/run_seniority_pipeline.py "$@"
