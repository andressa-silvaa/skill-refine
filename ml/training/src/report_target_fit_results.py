#!/usr/bin/env python3
"""
Gera ``docs/analysis/tcc_target_fit_results.md`` a partir de JSONLs + métricas (sem PII).

  python ml/training/src/report_target_fit_results.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _metrics(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _career_switch(r: dict) -> bool:
    rd = str(r.get("resume_domain_category") or "").strip().lower()
    td = str(r.get("domain_category") or "").strip().lower()
    if not rd or not td or rd == "general" or td == "general":
        return False
    return rd != td


def _pick_examples(policy_path: Path, reviewed_path: Path, n: int) -> list[tuple[dict, object, object]]:
    """Prefer rows with human review labels when available."""
    out: list[tuple[dict, object, object]] = []
    if reviewed_path.is_file():
        with reviewed_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                lab = r.get("labels") or {}
                if lab.get("label_source") == "review":
                    pol = (r.get("meta") or {}).get("policy_score")
                    fit = lab.get("fit_score")
                    out.append((r, pol, fit))
                if len(out) >= n:
                    return out[:n]
    if len(out) < n and policy_path.is_file():
        with policy_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                lab = r.get("labels") or {}
                pol = (r.get("meta") or {}).get("policy_score")
                fit = lab.get("fit_score")
                out.append((r, pol, fit))
                if len(out) >= n:
                    break
    return out[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/analysis/tcc_target_fit_results.md")
    ap.add_argument("--policy-jsonl", default="ml/data/processed/target_fit_from_db.jsonl")
    ap.add_argument("--reviewed-jsonl", default="ml/data/processed/target_fit_from_db_prefer_review.jsonl")
    ap.add_argument("--metrics-v1", default="ml/models/target_fit_v1/test_metrics.json")
    ap.add_argument("--metrics-v2", default="ml/models/target_fit_v2_reviewed/test_metrics.json")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[3]
    policy_p = root / args.policy_jsonl
    rev_p = root / args.reviewed_jsonl
    m1 = _metrics(root / args.metrics_v1)
    m2 = _metrics(root / args.metrics_v2)

    n_policy = _count_jsonl(policy_p)
    n_rev = _count_jsonl(rev_p)
    reviewed_rows = 0
    if rev_p.is_file():
        with rev_p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if (r.get("labels") or {}).get("label_source") == "review":
                    reviewed_rows += 1

    examples = _pick_examples(policy_p, rev_p, 5)
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Target Fit — resultados (QA / TCC)",
        "",
        "Documento gerado por `ml/training/src/report_target_fit_results.py` (sem PII).",
        "",
        "## Tamanho dos datasets",
        "",
        f"- **Policy export** (`target_fit_from_db.jsonl`): **{n_policy}** linhas.",
        f"- **Prefer-review export** (`target_fit_from_db_prefer_review.jsonl`): **{n_rev}** linhas.",
        f"- **Linhas com rótulo review** no JSONL prefer-review: **{reviewed_rows}**.",
        "",
        "## Métricas de regressão (holdout)",
        "",
        "### Modelo policy (`target_fit_v1`)",
        "",
        f"- MAE: `{m1.get('mae', 'n/a')}`",
        f"- RMSE: `{m1.get('rmse', 'n/a')}`",
        f"- R²: `{m1.get('r2', 'n/a')}`",
        f"- n_test: `{m1.get('n_test', 'n/a')}`",
        "",
        "### Modelo reviewed (`target_fit_v2_reviewed`)",
        "",
        f"- MAE: `{m2.get('mae', 'n/a')}`",
        f"- RMSE: `{m2.get('rmse', 'n/a')}`",
        f"- R²: `{m2.get('r2', 'n/a')}`",
        f"- n_test: `{m2.get('n_test', 'n/a')}`",
        "",
        "## Exemplos anônimos (domínios + scores)",
        "",
    ]

    for i, (r, pol, fit) in enumerate(examples, start=1):
        lab = r.get("labels") or {}
        src = lab.get("label_source")
        cs = _career_switch(r)
        lines.append(f"### Exemplo {i}")
        lines.append("")
        lines.append(f"- **target_position** (truncado): `{str(r.get('target_position') or '')[:80]}`")
        lines.append(f"- **domain_category (alvo)**: `{r.get('domain_category')}`")
        lines.append(f"- **resume_domain_category**: `{r.get('resume_domain_category')}`")
        lines.append(f"- **career_switch (heurística domínio)**: `{'sim' if cs else 'não'}`")
        lines.append(f"- **policy_fit** (meta): `{pol}`")
        lines.append(f"- **label fit_score**: `{fit}` (fonte: `{src}`)")
        lines.append("")

    lines.extend(
        [
            "## Conclusão",
            "",
            "- O score de policy é determinístico e serve como baseline; revisões humanas no CSV ajustam o gold quando exportado com `prefer-review`.",
            "- Casos com **domínio do currículo ≠ domínio do cargo alvo** indicam possível **migração de área**; o modelo e o clamp de senioridade na área-alvo permanecem conservadores.",
            "",
        ]
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
