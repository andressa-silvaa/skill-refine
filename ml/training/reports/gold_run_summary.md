# Gold pipeline — resumo da execução (TCC)

- **Gerado em**: 2026-04-13T13:09:38Z
- **user-email**: `dev@local.seed.invalid`
- **iterações (seed/batch)**: 1
- **seed por iteração**: [800]
- **batch_limit por iteração**: [800]
- **target-done (meta)**: 800
- **Análises DONE (utilizador seed)**: 800

## Dataset exportado (v1.1)

- **linhas (JSONL)**: 1035
- **classes presentes (intern/junior/mid/senior)**: 4

### Distribuição `labels.seniority_label`

- `mid`: 328 (31.7%)
- `junior`: 284 (27.4%)
- `intern`: 251 (24.3%)
- `senior`: 172 (16.6%)

- **dataset_version** (split): `d4710d7ed6479a6cd328fb86`
- **Critérios (≥500 linhas, ≥3 classes)**: OK

## Métricas do modelo (test holdout)

- **accuracy**: 1.0
- **f1_macro**: 1.0

### Matriz de confusão (JSON)

```json
[
  [
    30,
    0,
    0,
    0
  ],
  [
    0,
    42,
    0,
    0
  ],
  [
    0,
    0,
    53,
    0
  ],
  [
    0,
    0,
    0,
    26
  ]
]
```

- **Relatório detalhado**: `C:/Skill-Refine-TCC/ml/training/reports/eval_seniority.md`

## A/B low-confidence (signals_ml vs policy)

- **Relatório**: `C:/Skill-Refine-TCC/ml/training/reports/ab_low_confidence_report.md`
- **A/B (share `senior`) — depois (signals_ml + gates)**: **`senior` % after (signals_ml + gates + vetoes)**: 0.00%
- **phantom `senior` após ML (passo 1)**: 0

### Thresholds / policy

- Nenhum bump automático: phantom após ML zero ou relatório não parseável.

## Evolução do dataset

- **Log append**: `C:/Skill-Refine-TCC/ml/training/reports/dataset_evolution.md`

---

_Reprodutível com_: `python ml/scripts/run_gold_pipeline_scaled.py` (ver `ml/README.md`).
