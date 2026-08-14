"""
Train the per-bullet attribute heads as linear probes over frozen multilingual MiniLM embeddings.

This is the head that retires three of the four regex families in the inventory — ``METRICS_PATTERN``,
``ACTION_VERBS`` and ``LEADERSHIP_WORDS`` — and with them the ``insights.py`` branches that read the
same flags. Measured against a two-annotator consensus the regexes recover 0.77 / 0.21 / 0.32 of the
positives they are supposed to find, and ``ACTION_VERBS`` is a list of eight fixed word forms per
language, so it collapses entirely on Spanish first-person preterite
(``ml/reports/bullet_regex_baseline_v3.md``).

Design notes, each one a measurement rather than a preference:

* **No windowing.** Labelled bullets run 15.8 words on average and 44 at the longest, so none reaches
  the 60-word window ``chunk_text`` exists for. ``build_bullet_matrix`` is therefore an exact
  encoding, not an approximation, and the transform is named ``bullet_mean_l2_v1`` so the loader can
  refuse a head trained on anything else.
* **Grouped by occupation, not by bullet.** Bullets nest inside resumes and resumes carry one ESCO
  occupation, so grouping by occupation holds out the resume and its parallel pt/en/es renderings at
  once. Splitting on bullets would put siblings from one resume on both sides and score memorisation.
* **The label has measured noise, and the report says so.** Two labellers of different model families
  agree at kappa 0.77 / 0.54 / 0.70 on the three attributes. ``outcome`` is the noisy one: the second
  annotator calls 82% of bullets an outcome against the first's 65%, the same one-directional
  calibration bias that showed up in the band labels (handoff 7.2.2b). Accuracy on a label that noisy
  has a ceiling below 1.0, so the kappa is printed next to it instead of being left out.
* **Writer transfer is reported, not assumed.** Handoff 9.5 found quality lost 8.3 points across prose
  writers. The corpus has two, so the same test runs here.

Usage (from repo root):
  ./backend/.venv/Scripts/python.exe ml/scripts/train_bullet_probe_v3.py
  ./backend/.venv/Scripts/python.exe ml/scripts/train_bullet_probe_v3.py --no-export
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from dataclasses import dataclass
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

import label_rubric_llm_v3 as L  # noqa: E402
import label_seniority_llm_v3 as base  # noqa: E402

from apps.analysis.application.inference.text_probe import (  # noqa: E402
    BULLET_TRANSFORM_ID,
    build_bullet_matrix,
)
from apps.analysis.application.inference.tasks.quality.predict import (  # noqa: E402
    ACTION_VERBS,
    LEADERSHIP_WORDS,
    METRICS_PATTERN,
)

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
RAW_DIR = REPO_ROOT / "ml" / "data" / "raw" / "resumes_v3"
CACHE_DIR = REPO_ROOT / "ml" / "data" / "cache" / "probe_embeddings"
MODELS_DIR = REPO_ROOT / "ml" / "models"
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "bullet_probe_v3.md"

ATTRS = ("quantified", "outcome", "leadership")
REGEX_NAME = {
    "quantified": "METRICS_PATTERN",
    "outcome": "ACTION_VERBS",
    "leadership": "LEADERSHIP_WORDS",
}
N_SPLITS = 5
INNER_SPLITS = 4
C_GRID = (1.0, 4.0, 16.0, 64.0)
SEED = 20260812


@dataclass(frozen=True)
class Bullet:
    resume_id: str
    index: int
    text: str
    language: str
    band: str
    writer: str
    occupation_uri: str
    labels: dict[str, bool]
    second: dict[str, bool] | None


def _load_jsonl(name: str) -> dict[str, dict[str, Any]]:
    path = RAW_DIR / name
    rows: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows
    duplicates = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("id") in rows:
            duplicates += 1
        rows[row["id"]] = row
    if duplicates:
        print(f"{name}: {duplicates} duplicate lines dropped (last write wins)")
    return rows


def build_bullets(labels_name: str, second_name: str) -> tuple[list[Bullet], dict[str, int]]:
    prose = {row["id"]: row for row in base.load_rows()}
    labels = _load_jsonl(labels_name)
    second = _load_jsonl(second_name)
    out: list[Bullet] = []
    dropped = {"absent": 0, "stale": 0}
    for rid, rec in sorted(labels.items()):
        source = prose.get(rid)
        if source is None:
            dropped["absent"] += 1
            continue
        _text, texts = L.render_indexed(source.get("resume_data") or {})
        marked = rec.get("bullets") or []
        if len(marked) != len(texts):
            dropped["stale"] += 1
            continue
        other = (second.get(rid) or {}).get("bullets") or []
        other_ok = len(other) == len(texts)
        occupation = (source.get("occupation") or {}).get("uri") or f"__resume_{rid}"
        for pos, mark in enumerate(marked):
            out.append(
                Bullet(
                    resume_id=rid,
                    index=pos,
                    text=texts[pos],
                    language=str(rec.get("language") or ""),
                    band=str(rec.get("band_target") or ""),
                    writer=str(source.get("writer_model") or "(none)"),
                    occupation_uri=occupation,
                    labels={a: bool(mark.get(a)) for a in ATTRS},
                    second={a: bool(other[pos].get(a)) for a in ATTRS} if other_ok else None,
                )
            )
    return out, dropped


def regex_flags(text: str, language: str) -> dict[str, bool]:
    low = (text or "").lower()
    verbs = ACTION_VERBS.get((language or "pt").split("-")[0], ACTION_VERBS["pt"])
    return {
        "quantified": bool(METRICS_PATTERN.search(low)),
        "outcome": any(verb in low for verb in verbs),
        "leadership": bool(LEADERSHIP_WORDS.search(low)),
    }


_ENCODER: Any = None


def _encoder():
    global _ENCODER
    if _ENCODER is None:
        from sentence_transformers import SentenceTransformer

        _ENCODER = SentenceTransformer(EMBED_MODEL)
    return _ENCODER


def embed(bullets: Sequence[Bullet]) -> np.ndarray:
    digest = hashlib.sha256()
    digest.update(f"{EMBED_MODEL}|{BULLET_TRANSFORM_ID}".encode())
    for bullet in bullets:
        digest.update(bullet.text.encode("utf-8", "replace"))
        digest.update(b"\x00")
    cache_path = CACHE_DIR / f"bullets__{digest.hexdigest()[:16]}.npy"
    if cache_path.exists():
        matrix = np.load(cache_path)
        if matrix.shape[0] == len(bullets):
            print(f"  embeddings: cache hit {matrix.shape}")
            return matrix
    print(f"  embeddings: encoding {len(bullets)} bullets ...")
    matrix = build_bullet_matrix(_encoder(), [b.text for b in bullets])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, matrix)
    print(f"  embeddings: encoded {matrix.shape} -> {cache_path.name}")
    return matrix


def _new_classifier(penalty_c: float):
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(
        max_iter=8000, C=penalty_c, class_weight="balanced", random_state=SEED
    )


def _group_splits(x: np.ndarray, y: np.ndarray, groups: np.ndarray, n_splits: int):
    from sklearn.model_selection import GroupKFold

    distinct = len(set(groups.tolist()))
    splitter = GroupKFold(n_splits=max(2, min(n_splits, distinct)))
    return list(splitter.split(x, y, groups))


def select_c(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    if len(set(groups.tolist())) < 2 or len(set(y.tolist())) < 2:
        return C_GRID[1]
    best_score, best_c = -1.0, C_GRID[0]
    for penalty_c in C_GRID:
        scores = []
        for train_idx, test_idx in _group_splits(x, y, groups, INNER_SPLITS):
            if len(set(y[train_idx].tolist())) < 2:
                continue
            model = _new_classifier(penalty_c)
            model.fit(x[train_idx], y[train_idx])
            scores.append(float(np.mean(model.predict(x[test_idx]) == y[test_idx])))
        if scores and float(np.mean(scores)) > best_score:
            best_score, best_c = float(np.mean(scores)), penalty_c
    return best_c


def fit_classifier(x: np.ndarray, y: np.ndarray, groups: np.ndarray):
    model = _new_classifier(select_c(x, y, groups))
    model.fit(x, y)
    return model


def cv_predict(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> np.ndarray:
    pred = np.zeros(len(y), dtype=bool)
    for train_idx, test_idx in _group_splits(x, y, groups, N_SPLITS):
        model = _new_classifier(select_c(x[train_idx], y[train_idx], groups[train_idx]))
        model.fit(x[train_idx], y[train_idx])
        pred[test_idx] = model.predict(x[test_idx])
    return pred


def binary_report(truth: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    tp = int(np.sum(pred & truth))
    fp = int(np.sum(pred & ~truth))
    fn = int(np.sum(~pred & truth))
    tn = int(np.sum(~pred & ~truth))
    n = max(1, len(truth))
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision == precision and recall == recall and (precision + recall) > 0
        else float("nan")
    )
    return {
        "accuracy": (tp + tn) / n,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _fmt(value: float) -> str:
    return "n/a" if value != value else f"{value:.2f}"


def kappa(a: Sequence[bool], b: Sequence[bool]) -> float:
    n = len(a)
    if not n:
        return float("nan")
    obs = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = sum(1 for x in a if x) / n
    pb = sum(1 for x in b if x) / n
    exp = pa * pb + (1 - pa) * (1 - pb)
    return (obs - exp) / (1 - exp) if exp < 1 else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="labels_bullets.jsonl")
    ap.add_argument("--second", default="labels_bullets_mistral.jsonl")
    ap.add_argument("--no-export", action="store_true")
    args = ap.parse_args()

    bullets, dropped = build_bullets(args.labels, args.second)
    if not bullets:
        raise SystemExit("no labelled bullets found")
    x = embed(bullets)
    groups = np.asarray([b.occupation_uri for b in bullets])
    resumes = {b.resume_id for b in bullets}

    out: list[str] = []
    out.append("# Per-bullet attribute probe over frozen multilingual MiniLM — v3 corpus")
    out.append("")
    out.append(
        f"Generated {date.today().isoformat()} · encoder `{EMBED_MODEL}` · transform "
        f"`{BULLET_TRANSFORM_ID}` · dim {x.shape[1]}"
    )
    out.append("")
    out.append(
        f"**{len(bullets)} bullets** from {len(resumes)} resumes, {len(set(groups.tolist()))} "
        f"distinct occupations. {N_SPLITS}-fold GroupKFold over the occupation, so a resume and its "
        "parallel renderings never straddle the split."
    )
    if dropped["stale"] or dropped["absent"]:
        out.append("")
        out.append(
            f"Dropped {dropped['stale']} resumes whose label length no longer matches the current "
            f"prose render and {dropped['absent']} absent from the deduped corpus."
        )
    out.append("")
    langs = collections.Counter(b.language for b in bullets)
    writers = collections.Counter(b.writer for b in bullets)
    out.append(f"Language: {dict(langs)}")
    out.append("")
    out.append(f"Prose writer: {dict(writers)}")
    out.append("")

    paired = [b for b in bullets if b.second is not None]
    if paired:
        out.append("## Label noise — the ceiling any head is measured against")
        out.append("")
        out.append(
            f"{len(paired)} bullets carry a second annotator of a different model family. A head "
            "cannot be expected to exceed the agreement of the labellers that produced its target."
        )
        out.append("")
        out.append("| attribute | annotator agreement | kappa |")
        out.append("|---|---|---|")
        for attr in ATTRS:
            first = [b.labels[attr] for b in paired]
            other = [b.second[attr] for b in paired]
            obs = sum(1 for p, q in zip(first, other) if p == q) / len(paired)
            out.append(f"| `{attr}` | {obs:.1%} | {kappa(first, other):.2f} |")
        out.append("")

    truth = {attr: np.asarray([b.labels[attr] for b in bullets]) for attr in ATTRS}
    oof: dict[str, np.ndarray] = {}
    for attr in ATTRS:
        print(f"  cross-validating {attr} ...")
        oof[attr] = cv_predict(x, truth[attr], groups)

    metrics: dict[str, Any] = {}
    out.append("## Heads, out-of-fold")
    out.append("")
    out.append(
        "| attribute | positives | probe acc | probe P | probe R | probe F1 | "
        "regex acc | regex P | regex R | majority acc |"
    )
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for attr in ATTRS:
        y = truth[attr]
        pred = oof[attr]
        probe = binary_report(y, pred)
        rx = np.asarray([regex_flags(b.text, b.language)[attr] for b in bullets])
        regex = binary_report(y, rx)
        majority = max(float(np.mean(y)), float(np.mean(~y)))
        metrics[attr] = {
            "probe": probe,
            "regex": regex,
            "majority_accuracy": majority,
            "positive_rate": float(np.mean(y)),
        }
        out.append(
            f"| `{attr}` | {int(y.sum())} ({np.mean(y):.1%}) | **{probe['accuracy']:.1%}** | "
            f"{_fmt(probe['precision'])} | {_fmt(probe['recall'])} | {_fmt(probe['f1'])} | "
            f"{regex['accuracy']:.1%} | {_fmt(regex['precision'])} | {_fmt(regex['recall'])} | "
            f"{majority:.1%} |"
        )
    out.append("")
    out.append(f"Regex compared: {', '.join(f'`{a}` = `{REGEX_NAME[a]}`' for a in ATTRS)}.")
    out.append("")

    out.append("## By language, out-of-fold accuracy")
    out.append("")
    out.append("| attribute | " + " | ".join(sorted(langs)) + " |")
    out.append("|---|" + "---|" * len(langs))
    for attr in ATTRS:
        y = truth[attr]
        pred = oof[attr]
        rx = np.asarray([regex_flags(b.text, b.language)[attr] for b in bullets])
        cells = []
        for lang in sorted(langs):
            mask = np.asarray([b.language == lang for b in bullets])
            cells.append(
                f"{np.mean(pred[mask] == y[mask]):.1%} (regex {np.mean(rx[mask] == y[mask]):.1%})"
            )
        out.append(f"| `{attr}` | " + " | ".join(cells) + " |")
    out.append("")

    writer_names = [w for w, count in writers.items() if count >= 200]
    if len(writer_names) >= 2:
        out.append("## Cross-writer transfer")
        out.append("")
        out.append(
            "Trained on the bullets of one prose writer and scored on the other's, the test handoff "
            "9.5 used to show quality was partly writer style. Row counts differ, so the two "
            "directions are not symmetric and the weaker one is the data-starved one."
        )
        out.append("")
        out.append("| attribute | direction | train rows | test rows | accuracy | F1 |")
        out.append("|---|---|---|---|---|---|")
        for attr in ATTRS:
            y = truth[attr]
            for train_writer in writer_names:
                for test_writer in writer_names:
                    if train_writer == test_writer:
                        continue
                    tr = np.asarray([b.writer == train_writer for b in bullets])
                    te = np.asarray([b.writer == test_writer for b in bullets])
                    if len(set(y[tr].tolist())) < 2 or not te.any():
                        continue
                    model = fit_classifier(x[tr], y[tr], groups[tr])
                    report = binary_report(y[te], model.predict(x[te]))
                    short_train = train_writer.split("/")[-1][:22]
                    short_test = test_writer.split("/")[-1][:22]
                    out.append(
                        f"| `{attr}` | {short_train} -> {short_test} | {int(tr.sum())} | "
                        f"{int(te.sum())} | {report['accuracy']:.1%} | {_fmt(report['f1'])} |"
                    )
        out.append("")
        metrics["writers"] = dict(writers)

    written: list[str] = []
    if not args.no_export:
        import joblib

        bundle_dir = MODELS_DIR / "bullet_probe_v1"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        heads = {attr: fit_classifier(x, truth[attr], groups) for attr in ATTRS}
        joblib.dump({"heads": heads, "attributes": list(ATTRS)}, bundle_dir / "model.joblib")
        (bundle_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "task": "bullet_probe",
                    "model_name": "bullet_probe",
                    "model_version": "bullet_probe_v1",
                    "dataset_version": f"resumes_v3_{len(bullets)}bullets_{date.today().isoformat()}",
                    "feature_transform": BULLET_TRANSFORM_ID,
                    "embedding_model": EMBED_MODEL,
                    "embedding_dim": int(x.shape[1]),
                    "attributes": list(ATTRS),
                    "label_source": "llama-3.1-8b-instant bullets stage of label_rubric_llm_v3.py",
                    "label_second_annotator": "mistral-small-latest on "
                    f"{len(paired)} bullets, kappa "
                    + ", ".join(
                        f"{a}={kappa([b.labels[a] for b in paired], [b.second[a] for b in paired]):.2f}"
                        for a in ATTRS
                    )
                    if paired
                    else "none",
                    "training_bullets": len(bullets),
                    "training_resumes": len(resumes),
                    "evaluation": "GroupKFold over ESCO occupation",
                    "replaces": [REGEX_NAME[a] for a in ATTRS],
                    "metrics": metrics,
                    "trained_on": date.today().isoformat(),
                },
                indent=2,
                ensure_ascii=False,
                default=float,
            ),
            encoding="utf-8",
        )
        written.append(str(bundle_dir))
        out.append(f"## Bundle\n\nWrote `ml/models/bullet_probe_v1/` (transform `{BULLET_TRANSFORM_ID}`).")
        out.append("")

    text = "\n".join(out)
    print(text)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"\nwrote {REPORT_PATH}")
    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
