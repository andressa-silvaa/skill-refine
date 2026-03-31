"""
Standalone evaluation script for exported models.
Usage:
  python ml/training/eval.py --model_version analysis_v1_pt
  python ml/training/eval.py --model_dir ml/models/analysis_v1_pt
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import torch

# Add ml/training to path
TRAINING_DIR = Path(__file__).resolve().parent
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))


def _resolve_model_dir(args: argparse.Namespace) -> Path:
    if args.model_dir:
        return Path(args.model_dir).resolve()
    if args.model_version:
        models_root = TRAINING_DIR.parent / "models"
        return (models_root / args.model_version).resolve()
    raise ValueError("Either --model_dir or --model_version is required")


def run_eval(model_dir: Path) -> dict:
    """Load model, run on test split, return metrics."""
    hf_dir = model_dir / "hf" if (model_dir / "hf").exists() else model_dir
    hybrid_dir = model_dir / "hybrid"
    matching_dir = model_dir / "matching"
    if not hf_dir.exists() and not hybrid_dir.exists() and not matching_dir.exists():
        raise FileNotFoundError(f"Model not found: {model_dir}")

    metadata_path = model_dir / "metadata.json" if (model_dir / "metadata.json").exists() else hf_dir.parent / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    config = {}
    config_path = hf_dir / "config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    training_config_path = hybrid_dir / "training_config.json"
    if training_config_path.exists():
        with open(training_config_path, encoding="utf-8") as f:
            config = json.load(f)
    matching_config_path = matching_dir / "training_config.json"
    if matching_config_path.exists():
        with open(matching_config_path, encoding="utf-8") as f:
            config = json.load(f)

    task = metadata.get("task") or (
        "quality-hybrid" if training_config_path.exists()
        else ("matching" if matching_config_path.exists() else config.get("task", "seniority"))
    )
    splits_dir = Path(metadata.get("splits_dir") or config.get("splits_dir") or str(TRAINING_DIR.parent / "data" / "splits"))
    if not splits_dir.is_absolute():
        splits_dir = TRAINING_DIR.parent / splits_dir

    if task == "seniority":
        return _eval_seniority(hf_dir, splits_dir, config)
    if task == "quality":
        return _eval_quality(hf_dir, splits_dir, config)
    if task == "quality-hybrid":
        return _eval_quality_hybrid(hybrid_dir, splits_dir, config)
    if task == "matching":
        return _eval_matching(matching_dir, splits_dir, config)
    return {"error": f"Eval not implemented for task: {task}"}


def _eval_seniority(hf_dir: Path, splits_dir: Path, config: dict) -> dict:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from src.data import load_splits
    from src.tasks.seniority import get_id2label, get_label2id, eval_step, compute_metrics
    from src.data import SeniorityDataset, collate_seniority
    from torch.utils.data import DataLoader

    tokenizer = AutoTokenizer.from_pretrained(str(hf_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(hf_dir))
    id2label = get_id2label()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    _, _, test_records = load_splits(
        splits_dir, "seniority",
        languages=config.get("languages"),
    )
    if not test_records:
        return {"error": "No test data", "splits_dir": str(splits_dir)}

    label2id = get_label2id()
    test_ds = SeniorityDataset(test_records, tokenizer, config.get("max_length", 512), label2id)
    test_dl = DataLoader(test_ds, batch_size=config.get("batch_size", 8), collate_fn=collate_seniority)

    all_logits, all_labels = [], []
    model.eval()
    with torch.no_grad():
        for batch in test_dl:
            logits, labels = eval_step(model, batch, device)
            all_logits.append(logits)
            all_labels.append(labels)
    logits_cat = torch.cat(all_logits, dim=0)
    labels_cat = torch.cat(all_labels, dim=0)
    metrics = compute_metrics(logits_cat, labels_cat, id2label)
    return metrics


def _eval_quality(hf_dir: Path, splits_dir: Path, config: dict) -> dict:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from src.data import load_splits
    from src.tasks.quality import eval_step, compute_metrics, get_label2id
    from src.data import QualityDataset, collate_quality
    from torch.utils.data import DataLoader

    tokenizer = AutoTokenizer.from_pretrained(str(hf_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(hf_dir))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    _, _, test_records = load_splits(
        splits_dir, "quality",
        languages=config.get("languages"),
    )
    if not test_records:
        return {"error": "No test data", "splits_dir": str(splits_dir)}

    test_ds = QualityDataset(test_records, tokenizer, config.get("max_length", 512), get_label2id())
    test_dl = DataLoader(test_ds, batch_size=config.get("batch_size", 8), collate_fn=collate_quality)

    all_logits, all_labels = [], []
    model.eval()
    with torch.no_grad():
        for batch in test_dl:
            logits, labels = eval_step(model, batch, device)
            all_logits.append(logits)
            all_labels.append(labels)
    logits_cat = torch.cat(all_logits, dim=0)
    labels_cat = torch.cat(all_labels, dim=0)
    metrics = compute_metrics(logits_cat, labels_cat)
    return metrics


def _eval_quality_hybrid(hybrid_dir: Path, splits_dir: Path, config: dict) -> dict:
    from src.tasks import quality_hybrid as task_mod

    with open(hybrid_dir / "model.pkl", "rb") as f:
        bundle = pickle.load(f)
    vectorizer = bundle["vectorizer"]
    estimator = bundle["estimator"]

    _, _, test_records = task_mod.load_splits(
        splits_dir,
        "quality",
        languages=config.get("languages"),
    )
    if not test_records:
        return {"error": "No test data", "splits_dir": str(splits_dir)}
    x_test, y_test = task_mod.build_feature_matrix(test_records)
    features = vectorizer.transform(x_test)
    probs = estimator.predict_proba(features)
    preds = estimator.predict(features)
    return task_mod.compute_metrics(y_test, preds, probs)


def _eval_matching(matching_dir: Path, splits_dir: Path, config: dict) -> dict:
    from src.tasks import matching as task_mod
    from transformers import AutoModel, AutoTokenizer

    encoder_dir = matching_dir / "encoder"
    bundle_config = json.loads((matching_dir / "matching_config.json").read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(str(encoder_dir))
    encoder = AutoModel.from_pretrained(str(encoder_dir))
    model = task_mod.BiEncoderWithProjection(
        encoder,
        hidden_size=int(bundle_config.get("hidden_size", 768)),
        blend_alpha=float(bundle_config.get("blend_alpha", 0.65)),
    )
    state = torch.load(matching_dir / "model.pt", map_location="cpu")
    model.load_state_dict(state)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    _, _, test_records = task_mod.load_splits(
        splits_dir,
        "matching",
        languages=config.get("languages"),
    )
    if not test_records:
        return {"error": "No test data", "splits_dir": str(splits_dir)}

    from src.data import MatchingBiEncoderDataset, collate_matching_bi
    from torch.utils.data import DataLoader

    test_ds = MatchingBiEncoderDataset(test_records, tokenizer, config.get("max_length", 512))
    test_dl = DataLoader(test_ds, batch_size=config.get("batch_size", 8), collate_fn=collate_matching_bi)

    all_scores, all_labels, all_languages = [], [], []
    model.eval()
    with torch.no_grad():
        for batch in test_dl:
            score, labels = task_mod.eval_step(model, batch, device)
            all_scores.append(score)
            all_labels.append(labels)
            all_languages.extend(getattr(batch, "languages", []))
    scores_cat = torch.cat(all_scores, dim=0)
    labels_cat = torch.cat(all_labels, dim=0)
    metrics = task_mod.compute_metrics(scores_cat, labels_cat)
    metrics.update(task_mod.compute_metrics_per_language(scores_cat, labels_cat, all_languages))
    return metrics


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate exported model on test split")
    p.add_argument("--model_dir", type=Path, help="Path to model dir (e.g. ml/models/analysis_v1_pt)")
    p.add_argument("--model_version", type=str, help="Model version (e.g. analysis_v1_pt)")
    args = p.parse_args()
    try:
        model_dir = _resolve_model_dir(args)
        metrics = run_eval(model_dir)
        print(json.dumps(metrics, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
