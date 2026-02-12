"""
Train TF-IDF + Logistic Regression for seniority classification.
Lightweight, no GPU required. Saves model, metrics, and confusion matrix.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

# Optional: sklearn - will fail with clear message if not installed
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.pipeline import Pipeline
except ImportError as e:
    raise ImportError("Install scikit-learn: pip install scikit-learn") from e


SENIORITY_LABELS = ("intern", "junior", "mid", "senior")
LANGUAGES = ("pt", "en", "es", "pt-BR", "en-US", "es-ES")


def _normalize_lang(lang: str) -> str:
    return (lang or "pt").replace("-BR", "").replace("-US", "").replace("-ES", "")


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL; each row has resume_text/input_text and labels.seniority."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def to_canonical(rows: list[dict]) -> tuple[list[str], list[str]]:
    """Extract (texts, labels) in canonical format."""
    texts = []
    labels = []
    for r in rows:
        text = r.get("resume_text") or r.get("input_text") or (r.get("inputs") or {}).get("resume_text") or ""
        labs = r.get("labels") or {}
        lab = labs.get("seniority")
        if not text.strip() or not lab or lab not in SENIORITY_LABELS:
            continue
        texts.append(text.strip())
        labels.append(lab)
    return texts, labels


def train_and_evaluate(
    train_path: Path,
    val_path: Path,
    test_path: Path,
    output_dir: Path,
    *,
    max_features: int = 10000,
    ngram_range: tuple[int, int] = (1, 2),
    C: float = 1.0,
    max_iter: int = 500,
) -> dict:
    """
    Train TF-IDF + LogReg, evaluate on val and test.
    Returns dict with accuracy, f1_macro, confusion_matrix, etc.
    """
    train_rows = load_jsonl(train_path)
    val_rows = load_jsonl(val_path) if val_path.exists() else []
    test_rows = load_jsonl(test_path) if test_path.exists() else []

    X_train, y_train = to_canonical(train_rows)
    X_val, y_val = to_canonical(val_rows)
    X_test, y_test = to_canonical(test_rows)

    if not X_train or not y_train:
        raise ValueError(f"No valid train examples in {train_path}")

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )
    clf = LogisticRegression(
        C=C,
        max_iter=max_iter,
        class_weight="balanced",
        random_state=42,
    )
    pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("clf", clf),
    ])
    pipeline.fit(X_train, y_train)

    # Evaluate on val (or train if no val)
    if X_val:
        y_val_pred = pipeline.predict(X_val)
        val_acc = accuracy_score(y_val, y_val_pred)
        val_f1 = f1_score(y_val, y_val_pred, average="macro", zero_division=0)
    else:
        val_acc = val_f1 = None

    # Evaluate on test (or val if no test)
    if X_test:
        y_test_pred = pipeline.predict(X_test)
        test_acc = accuracy_score(y_test, y_test_pred)
        test_f1 = f1_score(y_test, y_test_pred, average="macro", zero_division=0)
        cm = confusion_matrix(y_test, y_test_pred, labels=list(SENIORITY_LABELS))
        report = classification_report(y_test, y_test_pred, labels=list(SENIORITY_LABELS), zero_division=0)
    elif X_val:
        y_val_pred = pipeline.predict(X_val)
        test_acc = val_acc
        test_f1 = val_f1
        cm = confusion_matrix(y_val, y_val_pred, labels=list(SENIORITY_LABELS))
        report = classification_report(y_val, y_val_pred, labels=list(SENIORITY_LABELS), zero_division=0)
    else:
        y_train_pred = pipeline.predict(X_train)
        test_acc = accuracy_score(y_train, y_train_pred)
        test_f1 = f1_score(y_train, y_train_pred, average="macro", zero_division=0)
        cm = confusion_matrix(y_train, y_train_pred, labels=list(SENIORITY_LABELS))
        report = classification_report(y_train, y_train_pred, labels=list(SENIORITY_LABELS), zero_division=0)

    metrics = {
        "accuracy": float(test_acc),
        "f1_macro": float(test_f1),
        "val_accuracy": float(val_acc) if val_acc is not None else None,
        "val_f1_macro": float(val_f1) if val_f1 is not None else None,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "tfidf_logreg_seniority.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({"pipeline": pipeline, "labels": list(SENIORITY_LABELS)}, f)

    metrics_path = output_dir / "tfidf_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    cm_path = output_dir / "confusion_matrix.txt"
    with open(cm_path, "w", encoding="utf-8") as f:
        f.write("Confusion matrix (rows=true, cols=pred)\n\n")
        f.write("            " + " ".join(f"{l:>8}" for l in SENIORITY_LABELS) + "\n")
        for i, row_label in enumerate(SENIORITY_LABELS):
            f.write(f"{row_label:>8}    " + " ".join(f"{cm[i, j]:>8}" for j in range(len(SENIORITY_LABELS))) + "\n")
        f.write("\n" + report)

    return metrics


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Train TF-IDF + LogReg for seniority")
    p.add_argument("--splits-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "splits")
    p.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent.parent / "models" / "tfidf_seniority")
    p.add_argument("--max-features", type=int, default=10000)
    p.add_argument("--C", type=float, default=1.0)
    args = p.parse_args()

    train_path = args.splits_dir / "train.jsonl"
    val_path = args.splits_dir / "val.jsonl"
    test_path = args.splits_dir / "test.jsonl"

    metrics = train_and_evaluate(
        train_path,
        val_path,
        test_path,
        args.output_dir,
        max_features=args.max_features,
        C=args.C,
    )
    print(f"TF-IDF + LogReg results:")
    print(f"  Accuracy: {metrics['accuracy']:.4f}")
    print(f"  F1 macro: {metrics['f1_macro']:.4f}")
    print(f"  Model saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
