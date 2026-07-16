#!/usr/bin/env python3
"""
Offline A/B: structural rule baseline vs signals_ml on low-confidence JSONL rows.

  python ml/training/src/ab_compare_low_confidence.py \\
    --in_jsonl ml/data/processed/low_confidence.jsonl \\
    --model_dir ml/models/seniority_signals_v1 \\
    --out_md ml/training/reports/ab_low_confidence_report.md

Requires ``backend/src`` on PYTHONPATH (script adds it).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _bootstrap_backend_src() -> Path:
    root = Path(__file__).resolve().parents[3]
    src = root / "backend" / "src"
    if not (src / "apps" / "analysis").is_dir():
        print(f"Could not find Django apps under {src}", file=sys.stderr)
        sys.exit(1)
    sys.path.insert(0, str(src))
    return root


def _default_sm_cfg() -> dict[str, Any]:
    """Defaults aligned with ``config/settings_modules/ai.py``."""
    return {
        "SENIOR_PROB_THRESHOLD": 0.70,
        "SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS": 60,
        "SIGNALS_ML_SENIOR_MIN_EXPERIENCES": 2,
        "SIGNALS_ML_SENIOR_MIN_BULLETS": 6,
        "MIN_COMPLETENESS_FOR_SIGNALS_ML": 52,
        "MIN_WORDS_FOR_SIGNALS_ML": 48,
    }


def _cfg_from_thresholds_json(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    raw = doc.get("inference_thresholds") if isinstance(doc.get("inference_thresholds"), dict) else doc
    cfg = _default_sm_cfg()
    key_map = {
        "senior_prob_threshold": "SENIOR_PROB_THRESHOLD",
        "senior_min_total_months": "SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS",
        "senior_min_experiences": "SIGNALS_ML_SENIOR_MIN_EXPERIENCES",
        "senior_min_bullets": "SIGNALS_ML_SENIOR_MIN_BULLETS",
        "min_completeness": "MIN_COMPLETENESS_FOR_SIGNALS_ML",
        "min_words": "MIN_WORDS_FOR_SIGNALS_ML",
    }
    for a, b in key_map.items():
        if a in raw:
            v = raw[a]
            cfg[b] = float(v) if b == "SENIOR_PROB_THRESHOLD" else int(v)
    return cfg


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


def main() -> int:
    _bootstrap_backend_src()
    from apps.analysis.application.inference.loader_signals_model import load_signals_ml_bundle
    from apps.analysis.application.inference.tasks.seniority.rule_based import clamp_seniority_vetoes, rule_based_seniority
    from apps.analysis.application.inference.tasks.seniority.signals_ml_predict import signals_ml_predict

    ap = argparse.ArgumentParser()
    ap.add_argument("--in_jsonl", required=True)
    ap.add_argument("--model_dir", required=True)
    ap.add_argument(
        "--out_md",
        default="ml/training/reports/ab_low_confidence_report.md",
        help="Markdown report path.",
    )
    ap.add_argument("--out", default="", help="Alias for --out_md (.md report).")
    ap.add_argument("--thresholds_json", default="", help="threshold_recommended.json from tune_thresholds.py")
    args = ap.parse_args()

    out_md = (args.out_md or args.out or "").strip()
    if not out_md:
        print("Provide --out_md or --out.", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    with Path(args.in_jsonl).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    bundle = load_signals_ml_bundle(Path(args.model_dir))
    cfg = (
        _cfg_from_thresholds_json(Path(args.thresholds_json))
        if (args.thresholds_json or "").strip()
        else _default_sm_cfg()
    )

    before_dist: Counter[str] = Counter()
    after_dist: Counter[str] = Counter()
    dataset_dist: Counter[str] = Counter()
    reason_dist: Counter[str] = Counter()
    senior_without_evidence_before = 0
    senior_without_evidence_after = 0
    sample_rows: list[dict[str, Any]] = []

    def has_senior_evidence(s: Any) -> bool:
        return (
            s.total_months_experience >= int(cfg["SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS"])
            and s.experiences_count >= int(cfg["SIGNALS_ML_SENIOR_MIN_EXPERIENCES"])
            and s.bullets_count >= int(cfg["SIGNALS_ML_SENIOR_MIN_BULLETS"])
        )

    for row in rows:
        sig = row.get("signals") if isinstance(row.get("signals"), dict) else {}
        lang = str(row.get("language") or "pt-BR")
        rs = _row_to_resume_signals(sig, lang)
        base_label, _, _ = rule_based_seniority(rs)
        before_dist[base_label] += 1

        ml_lab, _ml_conf, _probs, _ev, st = signals_ml_predict(bundle, rs, cfg)
        if st == "applied":
            fl, _ = clamp_seniority_vetoes(ml_lab, rs)
            after_label = fl
        else:
            after_label = base_label
        after_dist[after_label] += 1

        labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
        ds = str(labels.get("seniority_label") or "(empty)")
        dataset_dist[ds] += 1

        for r in row.get("gating_reasons") or []:
            reason_dist[str(r)] += 1

        if base_label == "senior" and not has_senior_evidence(rs):
            senior_without_evidence_before += 1
        if after_label == "senior" and not has_senior_evidence(rs):
            senior_without_evidence_after += 1

        if len(sample_rows) < 20:
            sample_rows.append(
                {
                    "resume_key": str(row.get("resume_key") or ""),
                    "signals": {
                        "total_months_experience": rs.total_months_experience,
                        "experiences_count": rs.experiences_count,
                        "bullets_count": rs.bullets_count,
                        "completeness_score": rs.completeness_score,
                        "word_count": rs.word_count,
                        "has_internship_terms": rs.has_internship_terms,
                    },
                    "rule_label": base_label,
                    "signals_ml_label": after_label,
                    "dataset_label": ds,
                    "gatingReasons": list(row.get("gating_reasons") or [])[:8],
                }
            )

    n = len(rows) or 1
    pct_sen_before = 100.0 * before_dist.get("senior", 0) / n
    pct_sen_after = 100.0 * after_dist.get("senior", 0) / n

    lines = [
        "# A/B — low confidence seniority (offline)",
        "",
        f"- **input**: `{Path(args.in_jsonl).as_posix()}`",
        f"- **model_dir**: `{Path(args.model_dir).as_posix()}`",
        f"- **rows**: {len(rows)}",
        "",
        "## Senior share (rule-only vs signals_ml)",
        "",
        f"- **`senior` % before (structural rules only)**: {pct_sen_before:.2f}%",
        f"- **`senior` % after (signals_ml + gates + vetoes)**: {pct_sen_after:.2f}%",
        "",
        "## Senior without structural evidence (phantom risk)",
        "",
        f"Evidence rule (aligned with current cfg): months ≥ {cfg['SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS']}, "
        f"experiences ≥ {cfg['SIGNALS_ML_SENIOR_MIN_EXPERIENCES']}, bullets ≥ {cfg['SIGNALS_ML_SENIOR_MIN_BULLETS']}.",
        "",
        f"- **rule-only `senior` violating evidence**: {senior_without_evidence_before}",
        f"- **after signals_ml `senior` still violating evidence**: {senior_without_evidence_after}",
        "",
        "## Label distribution — rule-only (before)",
        "",
    ]
    for k, v in sorted(before_dist.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "## Label distribution — after signals_ml", ""])
    for k, v in sorted(after_dist.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "## Dataset label distribution (reference)", ""])
    for k, v in sorted(dataset_dist.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "## Top gating reasons (from export)", ""])
    for k, v in reason_dist.most_common(25):
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "## Sample (20 rows, no PII)", "", "```json"])
    lines.append(json.dumps(sample_rows, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    out = Path(out_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
