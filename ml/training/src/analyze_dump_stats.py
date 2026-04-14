#!/usr/bin/env python3
"""
Estatísticas do analysis_dump.csv → analysis_dump_stats.md

  python ml/training/src/analyze_dump_stats.py --in ml/training/reports/analysis_dump.csv --out ml/training/reports/analysis_dump_stats.md
"""
from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path


def _f(row: dict, key: str) -> float | None:
    v = (row.get(key) or "").strip()
    if v == "":
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"n": 0, "min": float("nan"), "max": float("nan"), "mean": float("nan"), "std": float("nan")}
    return {
        "n": float(len(vals)),
        "min": float(min(vals)),
        "max": float(max(vals)),
        "mean": float(statistics.mean(vals)),
        "std": float(statistics.pstdev(vals)) if len(vals) > 1 else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    args = ap.parse_args()

    in_p = Path(args.in_path)
    if not in_p.is_file():
        print("missing", in_p)
        return 2

    rows: list[dict[str, str]] = []
    with in_p.open(encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";\t,")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        r = csv.DictReader(f, dialect=dialect)
        for row in r:
            rows.append({k: (v or "") for k, v in row.items()})

    numeric_cols = [
        "overall_score",
        "task_quality",
        "task_seniority",
        "task_target_fit",
        "task_matching",
        "target_fit_embedding_score",
        "target_fit_signals_score",
        "target_fit_final_score",
        "debug_quality_score",
        "debug_seniority_general_score",
        "debug_target_fit_score",
    ]

    col_vals: dict[str, list[float]] = {c: [] for c in numeric_cols}
    for row in rows:
        for c in numeric_cols:
            x = _f(row, c)
            if x is not None:
                col_vals[c].append(x)

    lines: list[str] = [
        "# Analysis dump — estatísticas",
        "",
        f"Linhas (CSV): **{len(rows)}**",
        "",
        "## Por coluna numérica",
        "",
        "| coluna | n | min | max | mean | std |",
        "|--------|---|-----|-----|------|-----|",
    ]

    flags: list[str] = []
    for c in numeric_cols:
        s = _stats(col_vals[c])
        if s["n"] == 0:
            lines.append(f"| {c} | 0 | — | — | — | — |")
            continue
        std = s["std"]
        lines.append(
            f"| {c} | {int(s['n'])} | {s['min']:.2f} | {s['max']:.2f} | {s['mean']:.2f} | {std:.2f} |"
        )
        if c in ("overall_score", "task_quality") and s["n"] >= 3 and std < 2.0:
            flags.append(f"**COLADO?** `{c}` std={std:.2f} < 2 (pouca dispersão).")

    lines.extend(["", "## Flags", ""])
    if flags:
        lines.extend(flags)
    else:
        lines.append("_Nenhum flag de saturação (std < 2) em overall/quality com n≥3._")

    lines.extend(["", "## Providers (contagem por linha DONE)", ""])
    done = [r for r in rows if (r.get("status") or "").strip().lower() == "done"]
    from collections import Counter

    prov = Counter((r.get("target_fit_provider") or "").strip() or "(empty)" for r in done)
    src = Counter((r.get("seniority_label_source") or "").strip() or "(empty)" for r in done)
    lines.append("### target_fit_provider")
    for k, v in prov.most_common():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("### seniority_label_source")
    for k, v in src.most_common():
        lines.append(f"- `{k}`: {v}")

    out_p = Path(args.out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", out_p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
