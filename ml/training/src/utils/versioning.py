"""Versioning: dataset hash, git commit, model version."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def dataset_version(splits_dir: Path, train_file: str = "train.jsonl") -> str:
    """Compute hash of train split + date for dataset version."""
    path = splits_dir / train_file
    if not path.exists():
        return "unknown"
    h = hashlib.sha256()
    h.update(path.read_bytes())
    h.update(datetime.now(timezone.utc).strftime("%Y-%m-%d").encode())
    return h.hexdigest()[:12]


def git_commit_hash(repo_root: Path | None = None) -> str:
    try:
        root = repo_root or Path(__file__).resolve().parents[4]
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.strip()[:12]
    except Exception:
        pass
    return "unknown"


def model_version(
    task: str,
    language_mode: str,
    base_model_name: str,
    dataset_ver: str,
) -> str:
    """e.g. analysis_v1_seniority_mono_abc123."""
    base = base_model_name.split("/")[-1].replace("-", "_")[:20]
    return f"analysis_v1_{task}_{language_mode}_{base}_{dataset_ver}"
