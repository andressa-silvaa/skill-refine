# Target fit — pipeline ML (TCC)

## Objetivo

Medir **aderência ao cargo-alvo** (`targetPosition`) com score 0–100 **explicável**, sem usar LLM como fonte de verdade. Complementa a **senioridade geral** com **senioridade na área-alvo** (clamp conservador) e o insight de **possível migração de área** quando o domínio do currículo diverge do domínio do cargo alvo.

## Dados (sem PII)

- Export default **somente sinais estruturados**: contagens, alinhamento educacional, flags. **Sem** texto de bullets/resumo no JSONL de treino.
- Identificadores são **pseudo-chaves** (hash com o mesmo salt da exportação de senioridade: `ANALYSIS_INTERNAL_REVIEW_KEY_SALT` / fallback).
- Campos: `analysis_key`, `resume_key`, `user_key`, `lang`, `target_position` (curto), `domain_category` (alvo), `resume_domain_category`, `has_job_description`, `signals`, `labels.fit_score`, `labels.label_source`.
- Schema: `ml/data/schema/target_fit_dataset_schema_v1_0.json`.

## Rótulo (policy)

`labels.fit_score` padrão vem de `compute_target_fit_policy` (regras determinísticas, mesma base do fallback em produção). Modo `--label-source prefer-review` usa `payload_json.targetFitGoldScore` quando `targetFitLabelSource=review` (opcional).

## Modelo

- **sklearn**: `StandardScaler` + `Ridge` sobre vetor fixo de features (sinais + one-hot de domínio alvo e domínio do currículo + mismatch + `has_job_text`).
- Implementação do vetor: `backend/src/apps/analysis/application/inference/target_fit/ml_feature_row.py` (treino e serving devem coincidir).
- Artefatos: `ml/models/target_fit_v1/model.joblib`, `metadata.json`, `test_metrics.json`.

## Métricas

- Regressão no conjunto de teste (split por `resume_key`): **MAE**, **RMSE**, **R²**.
- Relatórios: `ml/training/reports/target_fit_dataset_report.md`, `ml/training/reports/target_fit_eval.md`.

## Limitações

- Export de treino usa `job_text=None` na extração de sinais para consistência; análises **com** texto de vaga em produção passam `has_job_text` ao modelo quando habilitado.
- Sem `targetPosition`, o backend **não** emite bloco de target fit (contrato aditivo).

## Reproduzir

Na raiz do repositório (com Postgres e Django configurados):

```bash
python ml/scripts/run_target_fit_pipeline.py
```

Passos manuais:

```bash
cd backend
python manage.py export_target_fit_dataset --out ../ml/data/processed/target_fit_from_db.jsonl --limit 3000 --since 180d
cd ..
python ml/training/src/validate_target_fit_dataset.py --in ml/data/processed/target_fit_from_db.jsonl --report ml/training/reports/target_fit_dataset_report.md
python ml/training/src/split_target_fit_dataset.py --in ml/data/processed/target_fit_from_db.jsonl --out_dir ml/data/splits/target_fit_v1
python ml/training/src/train_target_fit.py --train_jsonl ml/data/splits/target_fit_v1/train.jsonl --out_dir ml/models/target_fit_v1
python ml/training/src/eval_target_fit.py --model_dir ml/models/target_fit_v1 --test_jsonl ml/data/splits/target_fit_v1/test.jsonl --report ml/training/reports/target_fit_eval.md --metrics_json ml/models/target_fit_v1/test_metrics.json
python ml/training/src/export_target_fit_sklearn_model.py --model_dir ml/models/target_fit_v1 --split_meta ml/data/splits/target_fit_v1/split_meta.json --test_metrics_json ml/models/target_fit_v1/test_metrics.json
```

## Serving (backend)

- `ANALYSIS_TARGET_FIT_ML_ENABLED=true`
- `ANALYSIS_TARGET_FIT_MODEL_DIR=<caminho absoluto para ml/models/target_fit_v1>` (ou use `ANALYSIS_MODEL_ROOT` + `ANALYSIS_TARGET_FIT_ML_SUBDIR=target_fit_v1`)

Falha ao carregar ou prever → **fallback** para `target_fit_policy` sem falhar o job.

Payload inclui `targetFitProvider`, `targetFitModelVersion`, `targetFitDatasetVersion` e `model_metadata_by_task.target_fit` para auditoria.

## QA sem UI (volume + CSV + gold)

1. **Orquestrador** (migrate → seed multi-domínio → batch → pipeline → CSV de candidatos):

   ```powershell
   python ml/scripts/run_target_fit_qa_no_ui.py
   python ml/scripts/run_target_fit_qa_no_ui.py --smoke
   ```

   - Critérios default: ≥800 análises `DONE` para `dev@local.seed.invalid`, ≥500 linhas no JSONL exportado.
   - Se faltar volume: `--auto-scale-on-shortfall` sugere repetir com `--seed-count 2000 --batch-limit 2000` (código de saída 3).

2. **CSV de revisão** (`;`, UTF-8 BOM): `ml/data/processed/target_fit_review_candidates_ptbr.csv` — preencher `review_fit_score` (0–100).

3. **Aplicar reviews no banco** (sem UI):

   ```powershell
   cd backend
   python manage.py apply_target_fit_reviews_from_csv --csv ..\ml\data\processed\target_fit_review_candidates_ptbr.csv
   ```

   Auditoria: ação `analysis.internal.review.target_fit_set` (sem texto de CV).

4. **Re-treino reviewed**:

   ```powershell
   python ml/scripts/run_target_fit_pipeline_reviewed.py
   ```

5. **Relatório TCC** (markdown gerado):

   ```powershell
   python ml/training/src/report_target_fit_results.py
   ```

   Saída: `docs/analysis/tcc_target_fit_results.md`.
