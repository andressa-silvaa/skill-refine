"""
Fine-tune the multilingual MiniLM end to end, and check whether it actually beats the frozen probe.

A frozen encoder can only recombine features that a sentence-similarity objective happened to
preserve. Fine-tuning lets the encoder move its representation toward career scope and writing
quality, which is where the remaining headroom is. It costs a real training run instead of seconds,
and a bigger artefact in production, so it only ships if it wins.

The comparison is the point, so both models see exactly the same data:

* one split, by ESCO occupation, into train / validation / test. Holding out occupations rather than
  rows means no split shares an occupation or its pt/en/es renderings.
* the fine-tune picks its epoch on the validation split. The frozen probe picks its ``C`` on the same
  split. Neither one sees test until it is scored.
* a single split, not k-fold: five fine-tunes on CPU is hours. That is a real weakness of this
  measurement and it is why the frozen probe keeps its k-fold number as the headline in the report —
  this script answers "is fine-tuning worth the artefact", not "what is the exact accuracy".

Export follows the shape ``loader_text_seniority_model`` already loads: ``config.json``, the
tokenizer, and a **real** ``id2label``. The previous text model died because it exported
``LABEL_0..3`` and inference could not tell which class was which (handoff section 8, item 4).

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/finetune_text_heads_v3.py --task seniority
  ./backend/.venv/Scripts/python.exe ml/scripts/finetune_text_heads_v3.py --task quality --epochs 8
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
SCRIPTS_DIR = Path(__file__).resolve().parent
for extra_path in (str(BACKEND_SRC), str(SCRIPTS_DIR)):
    if extra_path not in sys.path:
        sys.path.insert(0, extra_path)

from corpus_frame_v3 import BANDS, QUALITY_LEVELS, Row, build_frame  # noqa: E402

BASE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODELS_DIR = REPO_ROOT / "ml" / "models"
REPORTS_DIR = REPO_ROOT / "ml" / "reports"
MAX_LENGTH = 256
SEED = 20260811

TASKS = {
    "seniority": {
        "labels": list(BANDS),
        "export": "text_seniority_ft_v1",
        "rows": lambda frame: frame.rows,
        "label_of": lambda row: row.band_target,
        "label_source": "band_target",
    },
    "quality": {
        "labels": list(QUALITY_LEVELS),
        "export": "quality_level_ft_v1",
        "rows": lambda frame: frame.with_quality_target(),
        "label_of": lambda row: str(row.quality_target),
        "label_source": "quality_target",
    },
}


def grouped_split(
    rows: Sequence[Row],
    *,
    test_fraction: float = 0.2,
    val_fraction: float = 0.1,
) -> tuple[list[int], list[int], list[int]]:
    """
    Split by occupation, assigning whole occupations to one side.

    Occupations are shuffled with a fixed seed and dealt into test, then validation, then train, until
    each target size is met. Rows of one occupation never straddle the boundary.
    """
    rng = np.random.default_rng(SEED)
    by_group: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        by_group.setdefault(row.occupation_uri or f"__{row.id}", []).append(index)
    keys = list(by_group)
    rng.shuffle(keys)

    total = len(rows)
    want_test = int(total * test_fraction)
    want_val = int(total * val_fraction)
    test: list[int] = []
    val: list[int] = []
    train: list[int] = []
    for key in keys:
        bucket = by_group[key]
        if len(test) < want_test:
            test.extend(bucket)
        elif len(val) < want_val:
            val.extend(bucket)
        else:
            train.extend(bucket)
    return sorted(train), sorted(val), sorted(test)


def _metrics(true: Sequence[str], predicted: Sequence[str], order: dict[str, int]) -> dict[str, Any]:
    from sklearn.metrics import f1_score, precision_score, recall_score

    total = len(true)
    exact = sum(1 for a, b in zip(true, predicted) if a == b)
    within = sum(1 for a, b in zip(true, predicted) if abs(order[a] - order[b]) <= 1)
    return {
        "n": total,
        "accuracy": exact / total if total else 0.0,
        "within_one": within / total if total else 0.0,
        "macro_f1": float(f1_score(list(true), list(predicted), average="macro", zero_division=0)),
        "macro_precision": float(
            precision_score(list(true), list(predicted), average="macro", zero_division=0)
        ),
        "macro_recall": float(
            recall_score(list(true), list(predicted), average="macro", zero_division=0)
        ),
        "classes_used": len(set(predicted)),
    }


def frozen_probe_reference(
    rows: Sequence[Row],
    labels: Sequence[str],
    split: tuple[list[int], list[int], list[int]],
    order: dict[str, int],
) -> dict[str, Any]:
    """Fit the shipped probe design on the same train split and score the same test split."""
    from sklearn.linear_model import LogisticRegression
    from sentence_transformers import SentenceTransformer

    from apps.analysis.application.inference.text_probe import embed_documents

    train_idx, val_idx, test_idx = split
    encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    matrix = embed_documents(encoder, [row.text for row in rows])
    y = np.asarray([_label_for(row, labels) for row in rows])

    best_score, best_c = -1.0, 4.0
    for penalty_c in (1.0, 4.0, 16.0, 64.0):
        model = LogisticRegression(
            max_iter=8000, C=penalty_c, class_weight="balanced", random_state=SEED
        )
        model.fit(matrix[train_idx], y[train_idx])
        score = float(np.mean(model.predict(matrix[val_idx]) == y[val_idx]))
        if score > best_score:
            best_score, best_c = score, penalty_c
    model = LogisticRegression(max_iter=8000, C=best_c, class_weight="balanced", random_state=SEED)
    model.fit(matrix[train_idx], y[train_idx])
    predicted = model.predict(matrix[test_idx]).tolist()
    out = _metrics(y[test_idx].tolist(), predicted, order)
    out["selected_C"] = best_c
    return out


_LABEL_GETTER: Any = None


def _label_for(row: Row, labels: Sequence[str]) -> str:
    return str(_LABEL_GETTER(row))


def finetune(
    rows: Sequence[Row],
    labels: Sequence[str],
    split: tuple[list[int], list[int], list[int]],
    order: dict[str, int],
    *,
    epochs: int,
    batch_size: int,
    learning_rate: float,
) -> tuple[dict[str, Any], Any, Any, list[dict[str, Any]]]:
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.manual_seed(SEED)
    train_idx, val_idx, test_idx = split
    label_to_id = {label: i for i, label in enumerate(labels)}

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(labels),
        id2label={i: label for i, label in enumerate(labels)},
        label2id=label_to_id,
    )

    # 96M of this model's 118M parameters are the 250k-token embedding matrix. With ~1.2k training
    # resumes most of those tokens are seen once or never, so updating them buys overfitting and
    # three copies of optimiser state. Freezing them leaves the 12 transformer layers and the head,
    # which is where task-specific structure has to form anyway.
    frozen = 0
    for parameter in model.base_model.embeddings.word_embeddings.parameters():
        parameter.requires_grad = False
        frozen += parameter.numel()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  frozen word embeddings: {frozen / 1e6:.1f}M · trainable: {trainable / 1e6:.1f}M")

    def encode(indices: Sequence[int]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for i in indices:
            encoded = tokenizer(rows[i].text, truncation=True, max_length=MAX_LENGTH)
            items.append(
                {
                    "input_ids": encoded["input_ids"],
                    "attention_mask": encoded["attention_mask"],
                    "label": label_to_id[_label_for(rows[i], labels)],
                }
            )
        return items

    def collate(batch: list[dict[str, Any]]):
        """Pad to the longest item in the batch, not to 256 — most resumes are far shorter."""
        padded = tokenizer.pad(
            [{k: item[k] for k in ("input_ids", "attention_mask")} for item in batch],
            return_tensors="pt",
        )
        return (
            padded["input_ids"],
            padded["attention_mask"],
            torch.tensor([item["label"] for item in batch], dtype=torch.long),
        )

    train_set, val_set, test_set = encode(train_idx), encode(val_idx), encode(test_idx)
    loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, collate_fn=collate)

    counts = np.bincount(
        [label_to_id[_label_for(rows[i], labels)] for i in train_idx], minlength=len(labels)
    )
    weights = torch.tensor(
        (counts.sum() / np.maximum(counts, 1)) / len(labels), dtype=torch.float32
    )
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = max(1, len(loader) * epochs)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=learning_rate, total_steps=total_steps, pct_start=0.1
    )

    def predict(dataset: list[dict[str, Any]]) -> list[str]:
        model.eval()
        out: list[str] = []
        with torch.inference_mode():
            for input_ids, attention_mask, _target in DataLoader(
                dataset, batch_size=32, collate_fn=collate
            ):
                logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
                out.extend(labels[int(i)] for i in logits.argmax(dim=-1).tolist())
        return out

    history: list[dict[str, Any]] = []
    best_state = None
    best_val = -1.0
    best_epoch = 0
    for epoch in range(1, epochs + 1):
        model.train()
        started = time.time()
        running = 0.0
        for input_ids, attention_mask, target in loader:
            optimizer.zero_grad()
            logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
            loss = loss_fn(logits, target)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            running += float(loss.item())
        val_true = [_label_for(rows[i], labels) for i in val_idx]
        val_metrics = _metrics(val_true, predict(val_set), order)
        history.append(
            {
                "epoch": epoch,
                "loss": running / max(1, len(loader)),
                "val_accuracy": val_metrics["accuracy"],
                "val_macro_f1": val_metrics["macro_f1"],
                "seconds": round(time.time() - started, 1),
            }
        )
        print(
            f"  epoch {epoch}/{epochs}  loss {running / max(1, len(loader)):.4f}  "
            f"val acc {val_metrics['accuracy']:.4f}  val macroF1 {val_metrics['macro_f1']:.3f}  "
            f"({time.time() - started:.0f}s)"
        )
        if val_metrics["macro_f1"] > best_val:
            best_val = val_metrics["macro_f1"]
            best_epoch = epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    test_true = [_label_for(rows[i], labels) for i in test_idx]
    test_metrics = _metrics(test_true, predict(test_set), order)
    test_metrics["selected_epoch"] = best_epoch
    return test_metrics, model, tokenizer, history


def main() -> int:
    global _LABEL_GETTER

    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=sorted(TASKS), required=True)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args()

    spec = TASKS[args.task]
    _LABEL_GETTER = spec["label_of"]
    frame = build_frame()
    rows = list(spec["rows"](frame))
    labels = list(spec["labels"])
    order = {label: i for i, label in enumerate(labels)}
    rows = [row for row in rows if _label_for(row, labels) in order]

    split = grouped_split(rows)
    train_idx, val_idx, test_idx = split
    print(
        f"task {args.task}: {len(rows)} rows -> train {len(train_idx)} / val {len(val_idx)} / "
        f"test {len(test_idx)}, occupations held out"
    )

    print("frozen probe on the same split ...")
    probe = frozen_probe_reference(rows, labels, split, order)
    print(f"  probe test: acc {probe['accuracy']:.4f}  macroF1 {probe['macro_f1']:.3f}  C={probe['selected_C']}")

    print(f"fine-tuning {BASE_MODEL} ...")
    started = time.time()
    finetuned, model, tokenizer, history = finetune(
        rows,
        labels,
        split,
        order,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )
    elapsed = time.time() - started
    print(
        f"  fine-tune test: acc {finetuned['accuracy']:.4f}  macroF1 {finetuned['macro_f1']:.3f}  "
        f"(best epoch {finetuned['selected_epoch']}, {elapsed / 60:.1f} min)"
    )

    wins = finetuned["macro_f1"] > probe["macro_f1"]
    print(f"  verdict: fine-tune {'WINS' if wins else 'does not win'} on macro-F1")

    report = {
        "task": args.task,
        "base_model": BASE_MODEL,
        "label_source": spec["label_source"],
        "max_length": MAX_LENGTH,
        "split": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
        "split_policy": "single split, whole ESCO occupations assigned to one side",
        "frozen_probe_test": probe,
        "finetuned_test": finetuned,
        "finetune_wins_macro_f1": wins,
        "epochs_requested": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "minutes": round(elapsed / 60, 1),
        "history": history,
        "trained_on": date.today().isoformat(),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"finetune_{args.task}_v3.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(f"report -> {REPORTS_DIR / f'finetune_{args.task}_v3.json'}")

    if args.no_export or not wins:
        print("not exporting" + ("" if args.no_export else ": the frozen probe is still the better head"))
        return 0

    export_dir = MODELS_DIR / str(spec["export"])
    export_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(export_dir)
    tokenizer.save_pretrained(export_dir)
    (export_dir / "metadata.json").write_text(
        json.dumps(
            {
                "task": args.task,
                "model_name_base": BASE_MODEL.split("/")[-1],
                "model_version": str(spec["export"]),
                "dataset_version": f"resumes_v3_{len(rows)}rows_{date.today().isoformat()}",
                "provider": "hf_local",
                "labels": labels,
                "label_source": spec["label_source"],
                "input_limits": {"max_tokens": MAX_LENGTH},
                "metrics": {"test": finetuned, "frozen_probe_test": probe},
                "evaluation": "single occupation-held-out split; see report json",
                "trained_on": date.today().isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"bundle -> {export_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
