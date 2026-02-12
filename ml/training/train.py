"""
Training entry point: Hugging Face Transformers + PyTorch.
Usage:
  python ml/training/train.py --task seniority --language_mode mono --languages pt-BR
  python ml/training/train.py --task seniority --language_mode multi --languages pt-BR en-US es-ES --base_model xlm-roberta-base
  python ml/training/train.py --task quality --language_mode mono
  python ml/training/train.py --ablation remove_stopwords --ablation drop_metrics_numbers
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
import yaml

# Add ml/training to path
TRAINING_DIR = Path(__file__).resolve().parent
SRC_DIR = TRAINING_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

from src.utils import set_seed, dataset_version, git_commit_hash, model_version, save_config, training_cost_report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train analysis model (seniority/quality/sections/matching)")
    p.add_argument("--config", type=Path, default=TRAINING_DIR / "configs" / "train.yaml", help="YAML config")
    p.add_argument("--task", type=str, choices=["seniority", "sections", "quality", "matching"], help="Task")
    p.add_argument("--language_mode", type=str, choices=["mono", "multi"], default="mono")
    p.add_argument("--languages", type=str, nargs="+", help="e.g. pt-BR en-US es-ES")
    p.add_argument("--base_model", type=str, help="Hugging Face model id")
    p.add_argument("--splits_dir", type=Path, help="Path to train/val/test JSONL dir")
    p.add_argument("--output_dir", type=Path, help="Model output dir")
    p.add_argument("--reports_dir", type=Path, help="Reports output dir")
    p.add_argument("--epochs", type=int)
    p.add_argument("--batch_size", type=int)
    p.add_argument("--max_length", type=int)
    p.add_argument("--learning_rate", type=float)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--ablation", type=str, action="append", dest="ablations", help="remove_stopwords | drop_section | drop_metrics_numbers")
    p.add_argument("--drop_section", type=str, default="experience", help="Section to drop when ablation=drop_section")
    p.add_argument("--run_ablations_only", action="store_true", help="Run all ablations and write comparison report")
    args = p.parse_args()
    return args


def load_config(args: argparse.Namespace) -> dict:
    cfg = {}
    if args.config and Path(args.config).exists():
        with open(args.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    # CLI overrides
    if args.task:
        cfg["task"] = args.task
    if args.language_mode:
        cfg["language_mode"] = args.language_mode
    if args.languages:
        cfg["languages"] = args.languages
    if args.base_model:
        cfg["base_model"] = args.base_model
    if args.splits_dir:
        cfg["splits_dir"] = str(args.splits_dir)
    if args.output_dir:
        cfg["output_dir"] = str(args.output_dir)
    if args.reports_dir:
        cfg["reports_dir"] = str(args.reports_dir)
    if args.epochs is not None:
        cfg["epochs"] = args.epochs
    if args.batch_size is not None:
        cfg["batch_size"] = args.batch_size
    if args.max_length is not None:
        cfg["max_length"] = args.max_length
    if args.learning_rate is not None:
        cfg["learning_rate"] = args.learning_rate
    if args.seed is not None:
        cfg["seed"] = args.seed
    if args.ablations:
        cfg["ablations"] = args.ablations
    if args.drop_section:
        cfg["drop_section_value"] = args.drop_section
    # Defaults
    cfg.setdefault("base_model", "neuralmind/bert-base-portuguese-cased")
    cfg.setdefault("languages", ["pt-BR"])
    cfg.setdefault("splits_dir", str(TRAINING_DIR.parent / "data" / "splits"))
    cfg.setdefault("output_dir", str(TRAINING_DIR.parent / "models"))
    cfg.setdefault("reports_dir", str(TRAINING_DIR.parent / "reports"))
    cfg.setdefault("epochs", 3)
    cfg.setdefault("batch_size", 8)
    cfg.setdefault("max_length", 512)
    cfg.setdefault("learning_rate", 2.0e-5)
    cfg.setdefault("ablations", [])
    cfg.setdefault("drop_section_value", "experience")
    return cfg


def _run_sequence_classification(cfg: dict, task_mod) -> dict:
    """Generic sequence classification loop (seniority, sections)."""
    splits_dir = Path(cfg["splits_dir"])
    set_seed(cfg["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, tokenizer = task_mod.build_model_and_tokenizer(cfg["base_model"])
    model = model.to(device)
    train_dl, val_dl, test_dl, _ = task_mod.build_dataloaders(
        splits_dir,
        tokenizer,
        cfg["max_length"],
        cfg["batch_size"],
        languages=cfg.get("languages"),
        ablations=cfg.get("ablations") or None,
        drop_section_value=cfg.get("drop_section_value"),
    )
    if not len(train_dl.dataset):
        raise ValueError("No training data. Check splits_dir and languages filter.")
    id2label = task_mod.get_id2label()
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg.get("weight_decay", 0.01))
    total_steps = len(train_dl) * cfg["epochs"]
    from transformers import get_linear_schedule_with_warmup
    scheduler = get_linear_schedule_with_warmup(opt, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps)
    t0 = time.perf_counter()
    for epoch in range(cfg["epochs"]):
        model.train()
        for step, batch in enumerate(train_dl):
            loss, logits = task_mod.train_step(model, batch, device)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            scheduler.step()
    train_seconds = time.perf_counter() - t0
    # Eval on val or test
    eval_dl = val_dl if val_dl else test_dl
    if eval_dl:
        all_logits, all_labels, all_languages = [], [], []
        model.eval()
        with torch.no_grad():
            for batch in eval_dl:
                logits, labels = task_mod.eval_step(model, batch, device)
                all_logits.append(logits)
                all_labels.append(labels)
                if hasattr(batch, "languages"):
                    all_languages.extend(batch.languages)
        logits_cat = torch.cat(all_logits, dim=0)
        labels_cat = torch.cat(all_labels, dim=0)
        preds = logits_cat.argmax(dim=-1).cpu().numpy()
        labels_np = labels_cat.cpu().numpy()
        metrics = task_mod.compute_metrics(logits_cat, labels_cat, id2label)
        # Per-language metrics (accuracy and f1_macro per pt-BR, en-US, es-ES)
        if all_languages and len(all_languages) == len(preds):
            import numpy as np
            from src.eval.metrics import accuracy as acc_fn, f1_macro as f1_fn
            label_names = list(id2label.values())
            for lang in ("pt-BR", "en-US", "es-ES"):
                mask = np.array(all_languages) == lang
                if mask.sum() > 0:
                    metrics[f"accuracy_{lang}"] = round(acc_fn(preds[mask], labels_np[mask]), 4)
                    metrics[f"f1_macro_{lang}"] = round(f1_fn(preds[mask], labels_np[mask], label_names), 4)
        # Confusion matrix
        from src.eval import confusion_matrix_and_report, save_confusion_matrix_png
        cm, cm_report = confusion_matrix_and_report(labels_np, preds, list(id2label.values()))
        report_dir = Path(cfg["reports_dir"]) / cfg.get("model_version", "run")
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "confusion_matrix.txt").write_text(cm_report, encoding="utf-8")
        save_confusion_matrix_png(cm, list(id2label.values()), report_dir / "confusion_matrix.png")
    else:
        metrics = {}
    metrics["train_seconds"] = train_seconds
    cfg["metrics"] = metrics
    # Save
    out_dir = Path(cfg["output_dir"]) / cfg.get("model_version", "run")
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    if cfg.get("save_config"):
        save_config(cfg, out_dir)
    # Cost report
    report_path = Path(cfg["reports_dir"]) / cfg.get("model_version", "run") / "training_cost.md"
    vram = torch.cuda.max_memory_allocated() / 1024 / 1024 if torch.cuda.is_available() else None
    training_cost_report(report_path, train_seconds, vram_mb=vram, extra=metrics)
    return metrics


def run_seniority(cfg: dict) -> dict:
    from src.tasks import seniority as task_mod
    return _run_sequence_classification(cfg, task_mod)


def run_quality(cfg: dict) -> dict:
    from src.tasks import quality as task_mod
    splits_dir = Path(cfg["splits_dir"])
    set_seed(cfg["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, tokenizer = task_mod.build_model_and_tokenizer(cfg["base_model"])
    model = model.to(device)
    train_dl, val_dl, test_dl, _ = task_mod.build_dataloaders(
        splits_dir, tokenizer, cfg["max_length"], cfg["batch_size"], languages=cfg.get("languages"),
        ablations=cfg.get("ablations") or None, drop_section_value=cfg.get("drop_section_value"),
    )
    if not len(train_dl.dataset):
        raise ValueError("No training data.")
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg.get("weight_decay", 0.01))
    total_steps = len(train_dl) * cfg["epochs"]
    from transformers import get_linear_schedule_with_warmup
    scheduler = get_linear_schedule_with_warmup(opt, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps)
    t0 = time.perf_counter()
    for epoch in range(cfg["epochs"]):
        for batch in train_dl:
            loss, logits = task_mod.train_step(model, batch, device)
            opt.zero_grad()
            loss.backward()
            opt.step()
            scheduler.step()
    train_seconds = time.perf_counter() - t0
    eval_dl = val_dl or test_dl
    if eval_dl:
        all_logits, all_labels = [], []
        model.eval()
        with torch.no_grad():
            for batch in eval_dl:
                logits, labels = task_mod.eval_step(model, batch, device)
                all_logits.append(logits)
                all_labels.append(labels)
        logits_cat = torch.cat(all_logits, dim=0)
        labels_cat = torch.cat(all_labels, dim=0)
        metrics = task_mod.compute_metrics(logits_cat, labels_cat)
    else:
        metrics = {}
    metrics["train_seconds"] = train_seconds
    cfg["metrics"] = metrics
    out_dir = Path(cfg["output_dir"]) / cfg.get("model_version", "quality_run")
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    if cfg.get("save_config"):
        save_config(cfg, out_dir)
    report_path = Path(cfg["reports_dir"]) / cfg.get("model_version", "quality_run") / "training_cost.md"
    vram = torch.cuda.max_memory_allocated() / 1024 / 1024 if torch.cuda.is_available() else None
    training_cost_report(report_path, train_seconds, vram_mb=vram, extra=metrics)
    return metrics


def main() -> None:
    args = parse_args()
    cfg = load_config(args)
    # Resolve paths relative to ml/
    ml_root = TRAINING_DIR.parent
    for key in ("splits_dir", "output_dir", "reports_dir"):
        if key in cfg and cfg[key] and not Path(cfg[key]).is_absolute():
            cfg[key] = str(ml_root / cfg[key].lstrip("./").lstrip("../"))
    splits_dir = Path(cfg["splits_dir"])
    if not splits_dir.exists():
        print(f"ERROR: splits_dir not found: {splits_dir}", file=sys.stderr)
        sys.exit(1)
    # Versioning
    dataset_ver = dataset_version(splits_dir, cfg.get("train_file", "train.jsonl")) if cfg.get("save_dataset_version") else "unknown"
    git_hash = git_commit_hash(ml_root)
    cfg["dataset_version"] = dataset_ver
    cfg["git_commit"] = git_hash
    cfg["model_version"] = model_version(
        cfg["task"],
        cfg["language_mode"],
        cfg["base_model"],
        dataset_ver,
    )
    set_seed(cfg["seed"])
    task = cfg["task"]
    if args.run_ablations_only:
        from src.eval.ablations import run_ablations, ablation_report_md, ABLATION_FLAGS
        def _train(conf, ablations=None, drop_section_value=None):
            conf = dict(conf)
            conf["ablations"] = ablations or []
            conf["drop_section_value"] = drop_section_value
            if task == "seniority":
                return run_seniority(conf)
            if task == "quality":
                return run_quality(conf)
            return {}
        results = run_ablations(_train, cfg, ABLATION_FLAGS, drop_section_value=cfg.get("drop_section_value", "experience"))
        report_path = Path(cfg["reports_dir"]) / cfg["model_version"] / "ablations.md"
        ablation_report_md(results, report_path)
        print(f"Ablation report: {report_path}")
        return
    if task == "seniority":
        metrics = run_seniority(cfg)
    elif task == "quality":
        metrics = run_quality(cfg)
    elif task == "sections":
        from src.tasks import sections as task_mod
        metrics = _run_sequence_classification(cfg, task_mod)
    elif task == "matching":
        print("Matching task: bi-encoder requires job_text + resume_text + matching_score in dataset.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Unknown task: {task}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(metrics, indent=2))
    print(f"Model saved: {Path(cfg['output_dir']) / cfg['model_version']}")


if __name__ == "__main__":
    main()
