#!/usr/bin/env python3
"""
Grid leve sobre pesos (somente recomendação — não altera settings).

  python ml/training/src/tune_overall_weights.py --in ml/training/reports/analysis_dump.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
from itertools import product
from pathlib import Path


def _f(row: dict, key: str) -> float | None:
    v = (row.get(key) or "").strip()
    if v == "":
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _sim_overall(
    q: float,
    s: float,
    tf: float | None,
    *,
    has_target: bool,
    wq: float,
    ws: float,
    wt: float,
    blend: bool,
) -> float:
    q = max(0.0, min(100.0, q))
    s = max(0.0, min(100.0, s))
    if not blend:
        return float(round(q))
    if not has_target or tf is None:
        t = wq + ws
        if t <= 0:
            return float(round(q))
        return float(round((wq / t) * q + (ws / t) * s))
    tf = max(0.0, min(100.0, tf))
    t = wq + ws + wt
    if t <= 0:
        return float(round(q))
    return float(round((wq / t) * q + (ws / t) * s + (wt / t) * tf))


def _penalty(
    packed: list[tuple[dict, float, float | None, str]],
) -> float:
    p = 0.0
    for row, ov, tfv, lab in packed:
        sk = (row.get("scenario_key") or "").strip()
        if sk == "empty" and ov > 70:
            p += 55.0
        if sk == "migration_no_evidence" and tfv is not None and tfv > 60:
            p += 45.0
        if sk in ("senior_explicit", "summary_en", "senior_sparse_structured"):
            if lab in ("intern", "junior"):
                p += 35.0
            elif lab == "mid":
                p += 12.0
        if sk == "career_switch_marketing_dev" and tfv is not None and tfv > 70:
            p += 30.0
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out-md", default="ml/training/reports/weight_tuning.md")
    ap.add_argument("--out-env", default="ml/training/reports/recommended_env_overall_weights.env")
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
        for row in csv.DictReader(f, dialect=dialect):
            rows.append({k: (v or "") for k, v in row.items()})

    done = [r for r in rows if (r.get("status") or "").strip().lower() == "done"]
    if len(done) < 3:
        print("Too few DONE rows for tuning")
        return 2

    triples = [
        (0.78, 0.12, 0.10),
        (0.72, 0.14, 0.14),
        (0.84, 0.10, 0.06),
        (0.70, 0.15, 0.15),
        (0.80, 0.15, 0.05),
        (0.75, 0.13, 0.12),
    ]
    embed_ws = [0.45, 0.55, 0.65, 0.75]

    best = None
    best_score = -1e18
    report_rows: list[tuple[float, float, float, float, float, float, float]] = []

    for wq, ws, wt in triples:
        for ew in embed_ws:
            packed: list[tuple[dict, float, float | None, str]] = []
            sim_o: list[float] = []
            for r in done:
                q = _f(r, "task_quality")
                s = _f(r, "task_seniority")
                if q is None or s is None:
                    continue
                emb = _f(r, "target_fit_embedding_score")
                sig = _f(r, "target_fit_signals_score")
                tf_obs = _f(r, "target_fit_final_score")
                has_t = tf_obs is not None
                if has_t and emb is not None and sig is not None:
                    tfv = ew * emb + (1.0 - ew) * sig
                else:
                    tfv = tf_obs
                ov = _sim_overall(q, s, tfv, has_target=has_t, wq=wq, ws=ws, wt=wt, blend=True)
                lab = (r.get("seniority_final_label") or "").strip().lower() or "junior"
                packed.append((r, ov, tfv, lab))
                sim_o.append(ov)

            if len(sim_o) < 3:
                continue
            var = statistics.pvariance(sim_o)
            pen = _penalty(packed)
            # Penaliza saturação: muitos overall no intervalo [82,88]
            band = sum(1 for x in sim_o if 82 <= x <= 88)
            sat_pen = (band / max(1, len(sim_o))) * 25.0
            score = var * 120.0 - pen - sat_pen
            report_rows.append((wq, ws, wt, ew, var, pen + sat_pen, score))
            if score > best_score:
                best_score = score
                best = (wq, ws, wt, ew, var, pen + sat_pen)

    md_lines = [
        "# Weight tuning (recomendação automática)",
        "",
        "Critério: maximizar variância do overall simulado, penalizar violações nos cenários controlados e saturação em [82,88].",
        "",
        "## Top combinações (wq, ws, wt, embed_w | variance | penalties | score)",
        "",
    ]
    report_rows.sort(key=lambda t: t[6], reverse=True)
    for tup in report_rows[:12]:
        md_lines.append(
            f"- wq={tup[0]:.2f} ws={tup[1]:.2f} wt={tup[2]:.2f} embed={tup[3]:.2f} | var={tup[4]:.2f} | pen={tup[5]:.2f} | **score={tup[6]:.2f}**"
        )

    md_lines.extend(["", "## Melhor candidato", ""])
    if best:
        md_lines.extend(
            [
                f"- `ANALYSIS_OVERALL_WEIGHT_QUALITY={best[0]:.4f}`",
                f"- `ANALYSIS_OVERALL_WEIGHT_SENIORITY={best[1]:.4f}`",
                f"- `ANALYSIS_OVERALL_WEIGHT_TARGET_FIT={best[2]:.4f}`",
                f"- `ANALYSIS_TARGET_FIT_EMBED_WEIGHT={best[3]:.4f}`",
                "",
                f"_Variância overall simulado: {best[4]:.2f}; penalidades: {best[5]:.2f}_",
            ]
        )
    else:
        md_lines.append("_Nenhum candidato válido._")

    md_lines.extend(
        [
            "",
            "> **Não aplicar automaticamente.** Copie variáveis para o `.env` apenas após revisão humana.",
        ]
    )

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    env_lines = [
        "# Gerado por tune_overall_weights.py — revisar antes de usar",
        f"ANALYSIS_OVERALL_WEIGHT_QUALITY={best[0]:.4f}" if best else "# ANALYSIS_OVERALL_WEIGHT_QUALITY=0.78",
        f"ANALYSIS_OVERALL_WEIGHT_SENIORITY={best[1]:.4f}" if best else "# ANALYSIS_OVERALL_WEIGHT_SENIORITY=0.12",
        f"ANALYSIS_OVERALL_WEIGHT_TARGET_FIT={best[2]:.4f}" if best else "# ANALYSIS_OVERALL_WEIGHT_TARGET_FIT=0.10",
        f"ANALYSIS_TARGET_FIT_EMBED_WEIGHT={best[3]:.4f}" if best else "# ANALYSIS_TARGET_FIT_EMBED_WEIGHT=0.65",
    ]
    out_env = Path(args.out_env)
    out_env.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    print("Wrote", out_md, "and", out_env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
