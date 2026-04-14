#!/usr/bin/env python3
"""
Monta docs/analysis/tcc_ai_real_validation.md a partir de relatórios gerados.

  python ml/training/src/build_tcc_validation_doc.py
"""
from __future__ import annotations

import argparse
from pathlib import Path


def _read(p: Path) -> str:
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return f"_Arquivo ausente: `{p.as_posix()}`._\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default="")
    args = ap.parse_args()
    root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[3]

    stats = root / "ml" / "training" / "reports" / "analysis_dump_stats.md"
    tune = root / "ml" / "training" / "reports" / "weight_tuning.md"
    gold = root / "ml" / "training" / "reports" / "gold_eval.md"

    doc = f"""# Validação TCC — AI Real Upgrade (sem UI)

## Cenário e problema

- Senioridade subestimada ou desalinhada ao texto livre.
- Target fit semântico baixo quando o resumo é alinhado ao cargo.
- Score geral ~constante (~84) por mapeamento argmax + níveis de qualidade.

## Solução implementada

- **Senioridade textual**: modelo HF opcional + fusão com sinais; fallback lexical controlado.
- **Target fit**: embeddings multilíngues (sentence-transformers) combinados com sinais/policy/ML.
- **Overall**: blend configurável + breakdown em `debug` apenas com `DEBUG=True`.
- **Diagnóstico**: `debug.scoreBreakdown`, logs estruturados `analysis_score_components`.

## Evidências — estatísticas do dump controlado

{_read(stats)}

## Calibração sugerida (automática)

{_read(tune)}

## Avaliação contra gold humano

{_read(gold)}

## Limitações e próximos passos

- Windows: PyTorch/transformers podem falhar (DLL); preferir WSL2/Linux para carga neural completa.
- Gold set pequeno: MAE/RMSE têm variância alta; expandir revisões e retreinar classificador de senioridade.
- Tuning automático **não substitui** julgamento de produto — validar com stakeholders antes de `.env` prod.

---
_Gerado por `ml/training/src/build_tcc_validation_doc.py` + relatórios em `ml/training/reports/`._
"""
    out = root / "docs" / "analysis" / "tcc_ai_real_validation.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print("Wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
