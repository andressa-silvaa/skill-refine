#!/usr/bin/env python3
"""
Light grid search on seniority gates (CPU only): reduce phantom seniors while monitoring F1 / senior recall.

Uses the same post-processing as production: ``apply_signals_ml_gates`` + ``clamp_seniority_vetoes``.

  python ml/training/src/tune_thresholds.py \\
    --model_dir ml/models/seniority_signals_v1 \\
    --split_dir ml/data/splits/seniority_latest \\
    --out_md ml/training/reports/threshold_tuning.md \\
    --out_json ml/training/reports/threshold_recommended.json

Requires ``backend/src`` on PYTHONPATH (script adds it).
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _bootstrap_backend_src() -> None:
    root = Path(__file__).resolve().parents[3]
    src = root / "backend" / "src"
    if not (src / "apps" / "analysis").is_dir():
        print(f"Could not find Django apps under {src}", file=sys.stderr)
        sys.exit(1)
    sys.path.insert(0, str(src))


def _row_to_resume_signals(sig: dict[str, Any], language: str) -> Any:
    from apps.analysis.application.inference.signals.types import ResumeSignals

    reasons = sig.get("reasons") or []
    rt = tuple(sorted({str(x) for x in reasons})) if isinstance(reasons, list) else tuple()
    return ResumeSignals(
        total_months_experience=int(sig.get("total_months_experience") or 0),
        effective_months_experience=int(sig.get("effective_months_experience") or 0),
        experiences_count=int(sig.get("experiences_count") or 0),
        bullets_count=int(sig.get("bullets_count") or 0),
        has_current_role=bool(sig.get("has_current_role")),
        months_in_current_role=int(sig.get("months_in_current_role") or 0),
        has_internship_terms=bool(sig.get("has_internship_terms")),
        has_leadership_terms=bool(sig.get("has_leadership_terms")),
        has_links=bool(sig.get("has_links")),
        summary_char_count=int(sig.get("summary_char_count") or 0),
        skills_count=int(sig.get("skills_count") or 0),
        education_present=bool(sig.get("education_present")),
        completeness_score=int(sig.get("completeness_score") or 0),
        completeness_level=str(sig.get("completeness_level") or "insufficient"),
        insufficient_data=bool(sig.get("insufficient_data")),
        reasons=rt,
        word_count=int(sig.get("word_count") or 0),
        language=str(language or "pt-BR"),
    )


def _has_senior_evidence(rs: Any, cfg: dict[str, Any]) -> bool:
    return (
        rs.total_months_experience >= int(cfg["SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS"])
        and rs.experiences_count >= int(cfg["SIGNALS_ML_SENIOR_MIN_EXPERIENCES"])
        and rs.bullets_count >= int(cfg["SIGNALS_ML_SENIOR_MIN_BULLETS"])
    )


def main() -> int:
    _bootstrap_backend_src()
    from apps.analysis.application.inference.seniority.rule_based import clamp_seniority_vetoes
    from apps.analysis.application.inference.seniority.signals_ml_policy import apply_signals_ml_gates, raw_argmax_label
    from signals_features import feature_dict_from_signals

    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--split_dir", required=True, help="Uses test.jsonl")
    ap.add_argument("--out_md", required=True)
    ap.add_argument("--out_json", default="", help="Recommended inference_thresholds for metadata.json + deploy.")
    args = ap.parse_args()

    test_path = Path(args.split_dir) / "test.jsonl"
    bundle = joblib.load(Path(args.model_dir) / "model.joblib")
    clf = bundle["pipeline"]
    le = bundle["label_encoder"]
    feature_names: list[str] = bundle["feature_names"]
    classes = list(getattr(le, "classes_", []))
    known = set(classes)

    rows: list[dict[str, Any]] = []
    with test_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            labels = row.get("labels") or {}
            lab = str(labels.get("seniority_label") or "").strip()
            if lab not in ("intern", "junior", "mid", "senior") or lab not in known:
                continue
            rows.append(row)

    if len(rows) < 10:
        print("Need more labeled test rows.", file=sys.stderr)
        return 1

    X_list: list[list[float]] = []
    y_true: list[str] = []
    rs_list: list[Any] = []
    for row in rows:
        sig = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        lang = str(row.get("language") or "pt-BR")
        rs_list.append(_row_to_resume_signals(sig, lang))
        feat = feature_dict_from_signals(sig)
        X_list.append([feat.get(n, 0.0) for n in feature_names])
        labels = row.get("labels") or {}
        y_true.append(str(labels.get("seniority_label") or "").strip())

    X = np.asarray(X_list, dtype=np.float64)
    y_enc = le.transform(np.array(y_true))
    base_min_comp = 52
    base_min_words = 48

    grid_p = [0.65, 0.70, 0.75, 0.80]
    grid_m = [48, 60, 72]
    grid_e = [2]
    grid_b = [5, 6, 8]

    results: list[dict[str, Any]] = []

    for p_thr, m_min, e_min, b_min in product(grid_p, grid_m, grid_e, grid_b):
        cfg = {
            "SENIOR_PROB_THRESHOLD": float(p_thr),
            "SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS": int(m_min),
            "SIGNALS_ML_SENIOR_MIN_EXPERIENCES": int(e_min),
            "SIGNALS_ML_SENIOR_MIN_BULLETS": int(b_min),
            "MIN_COMPLETENESS_FOR_SIGNALS_ML": base_min_comp,
            "MIN_WORDS_FOR_SIGNALS_ML": base_min_words,
        }
        preds: list[str] = []
        phantoms = 0
        for i in range(len(rows)):
            probs = clf.predict_proba(X[i : i + 1])[0]
            prob_by_class = {str(classes[j]): float(probs[j]) for j in range(len(classes))}
            raw = raw_argmax_label(prob_by_class)
            final, _, _ = apply_signals_ml_gates(raw, prob_by_class, rs_list[i], cfg)
            fl, _ = clamp_seniority_vetoes(final, rs_list[i])
            preds.append(fl)
            if fl == "senior" and not _has_senior_evidence(rs_list[i], cfg):
                phantoms += 1

        pred_enc = le.transform(np.array(preds))
        acc = float(accuracy_score(y_enc, pred_enc))
        f1m = float(f1_score(y_enc, pred_enc, average="macro", zero_division=0))
        yi = np.array(y_true)
        pi = np.array(preds)
        mask_sen = yi == "senior"
        rec_sen = float((pi[mask_sen] == "senior").mean()) if mask_sen.any() else 0.0

        true_sen_ev = sum(1 for i, yt in enumerate(y_true) if yt == "senior" and _has_senior_evidence(rs_list[i], cfg))
        pred_sen_ev = sum(
            1
            for i, yt in enumerate(y_true)
            if yt == "senior" and _has_senior_evidence(rs_list[i], cfg) and preds[i] == "senior"
        )
        recall_sen_evidence = (pred_sen_ev / true_sen_ev) if true_sen_ev else 1.0

        junior_to_senior = sum(1 for i in range(len(y_true)) if y_true[i] == "junior" and preds[i] == "senior")

        # Score: minimize phantoms and junior→senior; reward F1 and recall on evidenced true seniors
        score = (
            -phantoms * 3.0
            - junior_to_senior * 5.0
            + f1m * 2.0
            + recall_sen_evidence * 1.5
        )

        results.append(
            {
                "score": score,
                "phantoms": phantoms,
                "junior_to_senior": junior_to_senior,
                "accuracy": acc,
                "f1_macro": f1m,
                "recall_senior_true_label": rec_sen,
                "recall_true_senior_with_evidence": recall_sen_evidence,
                "cfg": cfg,
            }
        )

    results.sort(key=lambda r: (-r["score"], r["phantoms"], -r["f1_macro"]))
    best = results[0]

    md = [
        "# Threshold tuning (signals_ml senior gates)",
        "",
        "Grid: `SENIOR_PROB_THRESHOLD` × `SENIOR_MIN_MONTHS` × experiences (fixed) × bullets.",
        "Objective: **fewer phantom seniors** and **no junior→senior noise**, while keeping F1 and recall on true seniors **with** structural evidence.",
        "",
        "## Recommended (best composite score)",
        "",
        "```json",
        json.dumps(
            {
                "inference_thresholds": {
                    "senior_prob_threshold": best["cfg"]["SENIOR_PROB_THRESHOLD"],
                    "senior_min_total_months": best["cfg"]["SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS"],
                    "senior_min_experiences": best["cfg"]["SIGNALS_ML_SENIOR_MIN_EXPERIENCES"],
                    "senior_min_bullets": best["cfg"]["SIGNALS_ML_SENIOR_MIN_BULLETS"],
                },
                "phantom_seniors": best["phantoms"],
                "junior_to_senior": best["junior_to_senior"],
                "accuracy": best["accuracy"],
                "f1_macro": best["f1_macro"],
                "recall_true_senior_with_evidence": best["recall_true_senior_with_evidence"],
            },
            indent=2,
        ),
        "```",
        "",
        "## Top candidates",
        "",
        "| p_thr | months | bullets | phantoms | j→sen | F1 macro | rec(sen+ev) |",
        "|-------|--------|---------|----------|-------|----------|-------------|",
    ]
    for r in results[:15]:
        c = r["cfg"]
        md.append(
            f"| {c['SENIOR_PROB_THRESHOLD']:.2f} | {c['SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS']} | "
            f"{c['SIGNALS_ML_SENIOR_MIN_BULLETS']} | {r['phantoms']} | {r['junior_to_senior']} | "
            f"{r['f1_macro']:.4f} | {r['recall_true_senior_with_evidence']:.4f} |"
        )
    md.append("")
    md.append("**Deploy**: set matching `SENIOR_*` / `ANALYSIS_SIGNALS_ML_*` env vars, or embed `inference_thresholds` in `metadata.json` and set `ANALYSIS_SIGNALS_THRESHOLDS_FROM_SETTINGS=false`.")
    md.append("")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {out_md}")

    if args.out_json:
        payload = {
            "inference_thresholds": {
                "senior_prob_threshold": best["cfg"]["SENIOR_PROB_THRESHOLD"],
                "senior_min_total_months": best["cfg"]["SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS"],
                "senior_min_experiences": best["cfg"]["SIGNALS_ML_SENIOR_MIN_EXPERIENCES"],
                "senior_min_bullets": best["cfg"]["SIGNALS_ML_SENIOR_MIN_BULLETS"],
            },
            "notes": "Merge into metadata.json or mirror in .env (see threshold_tuning.md).",
        }
        Path(args.out_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
