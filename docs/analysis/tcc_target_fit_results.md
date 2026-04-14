# Target Fit — resultados (QA / TCC)

Documento gerado por `ml/training/src/report_target_fit_results.py` (sem PII).

## Tamanho dos datasets

- **Policy export** (`target_fit_from_db.jsonl`): **0** linhas.
- **Prefer-review export** (`target_fit_from_db_prefer_review.jsonl`): **0** linhas.
- **Linhas com rótulo review** no JSONL prefer-review: **0**.

## Métricas de regressão (holdout)

### Modelo policy (`target_fit_v1`)

- MAE: `n/a`
- RMSE: `n/a`
- R²: `n/a`
- n_test: `n/a`

### Modelo reviewed (`target_fit_v2_reviewed`)

- MAE: `n/a`
- RMSE: `n/a`
- R²: `n/a`
- n_test: `n/a`

## Exemplos anônimos (domínios + scores)

## Conclusão

- O score de policy é determinístico e serve como baseline; revisões humanas no CSV ajustam o gold quando exportado com `prefer-review`.
- Casos com **domínio do currículo ≠ domínio do cargo alvo** indicam possível **migração de área**; o modelo e o clamp de senioridade na área-alvo permanecem conservadores.
