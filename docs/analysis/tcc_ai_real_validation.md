# Validação TCC — AI Real Upgrade (sem UI)

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

# Analysis dump — estatísticas

Linhas (CSV): **16**

## Por coluna numérica

| coluna | n | min | max | mean | std |
|--------|---|-----|-----|------|-----|
| overall_score | 16 | 36.00 | 71.00 | 55.56 | 11.31 |
| task_quality | 16 | 30.00 | 74.00 | 54.88 | 13.18 |
| task_seniority | 16 | 50.00 | 75.00 | 71.88 | 8.27 |
| task_target_fit | 14 | 11.00 | 82.00 | 39.64 | 23.05 |
| task_matching | 1 | 57.00 | 57.00 | 57.00 | 0.00 |
| target_fit_embedding_score | 14 | 0.00 | 100.00 | 41.57 | 33.50 |
| target_fit_signals_score | 14 | 27.00 | 50.00 | 35.79 | 6.36 |
| target_fit_final_score | 14 | 11.00 | 82.00 | 39.64 | 23.05 |
| debug_quality_score | 16 | 30.00 | 74.00 | 54.88 | 13.18 |
| debug_seniority_general_score | 16 | 50.00 | 75.00 | 71.88 | 8.27 |
| debug_target_fit_score | 14 | 11.00 | 82.00 | 39.64 | 23.05 |

## Flags

_Nenhum flag de saturação (std < 2) em overall/quality com n≥3._

## Providers (contagem por linha DONE)

### target_fit_provider
- `target_fit_embedding_v1`: 14
- `(empty)`: 2

### seniority_label_source
- `fused`: 16


## Calibração sugerida (automática)

# Weight tuning (recomendação automática)

Critério: maximizar variância do overall simulado, penalizar violações nos cenários controlados e saturação em [82,88].

## Top combinações (wq, ws, wt, embed_w | variance | penalties | score)

- wq=0.84 ws=0.10 wt=0.06 embed=0.75 | var=138.59 | pen=36.00 | **score=16594.78**
- wq=0.84 ws=0.10 wt=0.06 embed=0.65 | var=136.06 | pen=36.00 | **score=16291.50**
- wq=0.84 ws=0.10 wt=0.06 embed=0.45 | var=134.48 | pen=36.00 | **score=16102.12**
- wq=0.84 ws=0.10 wt=0.06 embed=0.55 | var=134.21 | pen=36.00 | **score=16069.78**
- wq=0.80 ws=0.15 wt=0.05 embed=0.65 | var=129.40 | pen=36.00 | **score=15492.28**
- wq=0.78 ws=0.12 wt=0.10 embed=0.75 | var=129.38 | pen=36.00 | **score=15489.00**
- wq=0.80 ws=0.15 wt=0.05 embed=0.55 | var=128.84 | pen=36.00 | **score=15424.78**
- wq=0.80 ws=0.15 wt=0.05 embed=0.75 | var=128.31 | pen=36.00 | **score=15361.50**
- wq=0.78 ws=0.12 wt=0.10 embed=0.65 | var=127.87 | pen=36.00 | **score=15308.53**
- wq=0.78 ws=0.12 wt=0.10 embed=0.55 | var=127.62 | pen=36.00 | **score=15278.53**
- wq=0.75 ws=0.13 wt=0.12 embed=0.65 | var=127.25 | pen=36.00 | **score=15233.53**
- wq=0.72 ws=0.14 wt=0.14 embed=0.75 | var=127.09 | pen=36.00 | **score=15214.78**

## Melhor candidato

- `ANALYSIS_OVERALL_WEIGHT_QUALITY=0.8400`
- `ANALYSIS_OVERALL_WEIGHT_SENIORITY=0.1000`
- `ANALYSIS_OVERALL_WEIGHT_TARGET_FIT=0.0600`
- `ANALYSIS_TARGET_FIT_EMBED_WEIGHT=0.7500`

_Variância overall simulado: 138.59; penalidades: 36.00_

> **Não aplicar automaticamente.** Copie variáveis para o `.env` apenas após revisão humana.


## Avaliação contra gold humano

# Avaliação vs gold (revisão humana)

Usuário: `dev@local.seed.invalid`

## Target fit (payload `targetFitGoldScore`)

- N: **44**
- MAE: **12.75**
- RMSE: **19.80**
- Absurdos (career_switch + pred>70 + sem semanticEvidence): **0** / 44

## Senioridade (campo `seniority_review_label`)

- N: **44**; acurácia exata: **41/44**

- Absurdos (insufficientData + senior): **0** (varredura em análises do usuário)



## Limitações e próximos passos

- Windows: PyTorch/transformers podem falhar (DLL); preferir WSL2/Linux para carga neural completa.
- Gold set pequeno: MAE/RMSE têm variância alta; expandir revisões e retreinar classificador de senioridade.
- Tuning automático **não substitui** julgamento de produto — validar com stakeholders antes de `.env` prod.

---
_Gerado por `ml/training/src/build_tcc_validation_doc.py` + relatórios em `ml/training/reports/`._
