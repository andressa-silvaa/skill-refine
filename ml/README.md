# ML Pipeline — Skill Refine

Pasta oficial de dataset, treino, avaliação e export de modelos para análise de currículo.

## Estrutura

```
ml/
  data/
    raw/           # dados brutos
    processed/      # dados processados
    splits/        # train.jsonl, val.jsonl, test.jsonl
  labeling/
    policies.md
    label_maps.json
  training/
    configs/       # train_seniority.yaml, train_quality.yaml, train_matching.yaml
    src/
      train.py
      export.py
      eval/        # métricas e utilitários
      utils/versioning.py
    reports/       # relatórios por model_version
  models/
    analysis_v1_pt/
      hf/          # modelo HuggingFace exportado
      onnx/        # opcional
      metadata.json
```

## Pipeline senioridade `signals_ml` (one-shot)

Da **raiz do repositório**, com PostgreSQL e migrações aplicadas:

```bash
python ml/scripts/run_seniority_pipeline.py
```

Opções úteis:

- `--since 180d --limit 8000` — janela e tamanho do export
- `--skip-export` — reutiliza `ml/data/processed/seniority_from_db.jsonl`
- `--with-tuning` — roda `tune_thresholds.py` e grava `inference_thresholds` no `metadata.json`
- `--continue-on-validate-warnings` — segue mesmo com issues no `validate_dataset.py`

Saídas esperadas: `ml/training/reports/dataset_report.md`, `ml/training/reports/eval_seniority.md`, `ml/training/reports/seniority_signals_v1_summary.md`, `ml/data/splits/seniority_latest/split_meta.json`, `ml/models/seniority_signals_v1/metadata.json`.

## Pipeline target fit (sklearn, signals-only)

Exporta análises com `targetPosition` preenchido, valida schema, split por `resume_key`, treina `Ridge` + `StandardScaler`, avalia e grava `metadata.json` com `dataset_version` e métricas.

```bash
python ml/scripts/run_target_fit_pipeline.py
```

- `--skip-export` — reutiliza `ml/data/processed/target_fit_from_db.jsonl`
- `--continue-on-validate-warnings` — segue após avisos do validador
- Backend: `python manage.py export_target_fit_dataset --out ../ml/data/processed/target_fit_from_db.jsonl`

Saídas: `ml/training/reports/target_fit_dataset_report.md`, `ml/training/reports/target_fit_eval.md`, `ml/models/target_fit_v1/model.joblib`, `ml/models/target_fit_v1/metadata.json`, `ml/data/splits/target_fit_v1/split_meta.json`.

**Serving:** `ANALYSIS_TARGET_FIT_ML_ENABLED=true` e `ANALYSIS_TARGET_FIT_MODEL_DIR` (absoluto) apontando para `ml/models/target_fit_v1`. Documentação TCC: `docs/analysis/tcc_target_fit_pipeline.md`.

**Verificar antes da UI (Windows PowerShell):**

```powershell
$env:ANALYSIS_TARGET_FIT_ML_ENABLED="true"
$env:ANALYSIS_TARGET_FIT_MODEL_DIR="C:\Skill-Refine-TCC\ml\models\target_fit_v1"
cd backend
python manage.py check_target_fit_ml
```

Se aparecer `Bundle loaded OK`, o payload deve trazer `targetFitProvider=target_fit_ml`. Se cair em policy, confira caminho, `model.joblib`, `metadata.json` e `task: target_fit_signals`.

## IA “real” no backend (text seniority + embeddings)

Coloque exports HuggingFace em `ml/models/` e ative por variáveis de ambiente (ver `backend/src/config/settings_modules/ai.py`).

### Como gerar baseline local `text_seniority_v1`

Objetivo imediato: ter um bundle Hugging Face válido no disco (tokenizer, `config.json`, pesos em `safetensors` ou `bin`, `metadata.json`) para **destravar o caminho neural** de senioridade por texto e o HF core de senioridade quando `ANALYSIS_MODEL_VERSION_BY_TASK` aponta `seniority=text_seniority_v1`. O **próximo passo (TCC)** é fine-tune supervisionado usando labels de revisão (ex.: `seniority_review_label`) pelo pipeline gold que já existe.

**Baseline sem fine-tune:** a cabeça de classificação é inicializada aleatoriamente sobre `neuralmind/bert-base-portuguese-cased`; previsões podem ser **erradas** até o treino.

Da raiz do repositório (recomendado **WSL/Linux**; use paths `/mnt/c/...`):

```bash
python ml/scripts/export_text_seniority_baseline.py \
  --out ml/models/text_seniority_v1 \
  --base neuralmind/bert-base-portuguese-cased
```

Smoke rápido (carrega o loader do backend e roduz duas predições):

```bash
python ml/scripts/smoke_text_seniority_loader.py --model-dir /mnt/c/Skill-Refine-TCC/ml/models/text_seniority_v1
```

No `.env` do backend (exemplo WSL):

- `ANALYSIS_TEXT_SENIORITY_ENABLED=true`
- `ANALYSIS_TEXT_SENIORITY_MODEL_DIR=/mnt/c/Skill-Refine-TCC/ml/models/text_seniority_v1`
- `ANALYSIS_TEXT_SENIORITY_FUSION_ENABLED=true`
- `ANALYSIS_MODEL_VERSION_BY_TASK` deve incluir `seniority=text_seniority_v1` para o mesmo export servir também o bundle HF de `get_model_bundle(seniority)` (evita fallback “heuristics-only” quando não há pesos em `analysis_v1_pt/hf`).

Opcional: `ANALYSIS_TEXT_SENIORITY_HUB_ID` se não usar pasta local. Em Windows puro, se o carregamento PyTorch falhar, use WSL2/Linux.

### Target fit semântico (sentence-transformers)

1. O padrão baixa/uso local de `paraphrase-multilingual-MiniLM-L12-v2` (multilíngue, CPU).
2. Ative:

```powershell
$env:ANALYSIS_EMBEDDINGS_ENABLED="true"
# opcional:
# $env:ANALYSIS_EMBEDDINGS_MODEL_NAME="paraphrase-multilingual-MiniLM-L12-v2"
# $env:ANALYSIS_TARGET_FIT_EMBED_WEIGHT="0.65"
```

O `targetFitFinalScore` combina embedding + sinais (`target_fit_policy` / `target_fit_ml`). Com embeddings ativos, `targetFitProvider` vira `target_fit_embedding_v1`.

### Fusão lexical (sem modelo neural)

`ANALYSIS_TEXT_SENIORITY_FUSION_ENABLED` (padrão `true`) permite evidência lexical quando não há bundle HF — útil para testes e perfis sem datas estruturadas.

### Smoke (variação de scores)

Com `DJANGO_DEBUG=1`, o payload inclui `debug.scoreBreakdown`. Da raiz do repo:

```powershell
$env:PYTHONPATH="backend\src"
$env:DJANGO_SETTINGS_MODULE="config.settings"
$env:DJANGO_DEBUG="1"
python ml/scripts/run_ai_real_upgrade_smoke.py
```

### Validação TCC — AI real (dump + stats + tuning + gold, sem UI)

Um comando orquestra seed controlado, análises, CSV sem PII, estatísticas, grid de pesos, export de candidatos a gold e documento final.

```powershell
# Rápido (sem revisão humana gold)
python ml/scripts/run_ai_real_validation_no_ui.py --user-email dev@local.seed.invalid --sync --skip-gold

# Completo: exporta gold_review_candidates_ptbr.csv; aplica + eval só se o CSV já tiver colunas preenchidas
python ml/scripts/run_ai_real_validation_no_ui.py --user-email dev@local.seed.invalid --sync
# Depois de preencher review_target_fit_score / review_seniority_label:
cd backend
python manage.py apply_target_fit_reviews_from_csv --csv ..\ml\data\processed\gold_review_candidates_ptbr.csv
cd ..
python ml/training/src/eval_against_gold.py --user-email dev@local.seed.invalid
python ml/training/src/build_tcc_validation_doc.py
```

Saídas principais: `ml/training/reports/analysis_dump.csv`, `analysis_dump_stats.md`, `weight_tuning.md`, `recommended_env_overall_weights.env`, `gold_review_candidates_ptbr.csv`, `gold_eval.md`, `docs/analysis/tcc_ai_real_validation.md`.

### QA Target Fit (sem UI, PowerShell)

- **Um comando** (migrate → seed com domínios mistos → batch sync → pipeline + CSV de revisão):

  ```powershell
  python ml/scripts/run_target_fit_qa_no_ui.py
  python ml/scripts/run_target_fit_qa_no_ui.py --smoke
  ```

- **Flags `seed_resumes`:** `--with-target-positions --domain-mix balanced` (gira saúde/finanças/educação/jurídico/marketing/tech + alguns pares “migração”).
- **Revisão humana:** preencher `review_fit_score` no CSV `ml/data/processed/target_fit_review_candidates_ptbr.csv` → `python manage.py apply_target_fit_reviews_from_csv --csv ...`
- **Re-treino reviewed:** `python ml/scripts/run_target_fit_pipeline_reviewed.py` → `ml/models/target_fit_v2_reviewed/`, relatórios `*_reviewed.md`.
- **Resumo TCC:** `python ml/training/src/report_target_fit_results.py` → `docs/analysis/tcc_target_fit_results.md`.

Pipeline adicional: `run_target_fit_pipeline.py` aceita `--in-jsonl`, `--label-source`, `--min-rows`, `--dataset-report`, `--eval-report`.

## Escala controlada do dataset (seed sintético + análises em lote)

Para aumentar volume e diversidade **sem PII** e sem alterar o contrato público de `/analysis/run` (o batch usa o mesmo serviço interno):

```bash
cd backend
python manage.py seed_resumes --user-email dev@local.seed.invalid --count 1000 --seed 42 --profiles balanced
# Com Celery: omitir --sync. Sem worker: usar --sync (executa o worker inline).
python manage.py batch_run_analysis --user-email dev@local.seed.invalid --limit 1000 --concurrency 10 --sleep-ms 50 --only-missing --resume-tag seed_synthetic
cd ..
```

**Orquestração** (seed opcional → batch → export v1.1 → validate/split/train/eval → export modelo → low-confidence → A/B → append em `dataset_evolution.md`), a partir da **raiz do repo**:

```bash
python ml/scripts/run_gold_pipeline_with_seed.py --user-email dev@local.seed.invalid --seed-count 1000 --batch-limit 1000 --concurrency 10 --only-missing --sync
# ou: bash ml/scripts/run_gold_pipeline_with_seed.sh … (delega no .py)
```

Parâmetros úteis: `--skip-seed`, `--skip-batch`, `--export-limit`, `--since 180d`, `--resume-tag seed_synthetic`. Ver também `docs/analysis/tcc_gold_pipeline.md` (secção *Dataset pequeno vs dataset grande*).

### Como rodar — pipeline gold em escala (um comando)

`ml/scripts/run_gold_pipeline_scaled.py` orquestra **migrate → seed → batch (iterativo se faltar volume/classes) → export v1.1 + low-confidence → validate → split → train → eval → metadata → A/B (com bump opcional de thresholds) → dataset_evolution → `gold_run_summary.md`**.

- Splits e modelo por defeito em `ml/data/splits/<out-model-version>/` e `ml/models/<out-model-version>/` (ex.: `seniority_signals_v1`).
- **Windows / sem GPU**: HF/torch podem falhar no worker; o fluxo continua com policy + `signals_ml` (sklearn).
- Se, após `max-iterations`, ainda faltar volume ou classes, o script sai com código **2** antes do treino (salva mesmo assim `gold_run_summary.md`). Use `--continue-on-short-dataset` para treinar apesar disso (útil em smoke tests).

**PowerShell (Windows):** não use `^` (isso é só no **cmd.exe**). Ou coloque tudo numa linha, ou use **backtick** `` ` `` no fim de cada linha para continuar. Exemplo numa linha:

```powershell
python ml/scripts/run_gold_pipeline_scaled.py --user-email dev@local.seed.invalid --target-done 800 --min-dataset-rows 500 --min-classes 3 --seed-count 800 --batch-limit 800 --concurrency 8 --only-missing --sync
```

Exemplo multilinha em PowerShell:

```powershell
python ml/scripts/run_gold_pipeline_scaled.py `
  --user-email dev@local.seed.invalid `
  --target-done 800 --min-dataset-rows 500 --min-classes 3 `
  --seed-count 800 --batch-limit 800 --concurrency 8 `
  --only-missing --sync
```

**Bash / Git Bash** (continuação com `\`):

**Sem Celery (dev Windows):**

```bash
python ml/scripts/run_gold_pipeline_scaled.py \
  --user-email dev@local.seed.invalid \
  --target-done 800 --min-dataset-rows 500 --min-classes 3 \
  --seed-count 800 --batch-limit 800 --concurrency 8 \
  --only-missing --sync
```

**Com Celery:**

```bash
python ml/scripts/run_gold_pipeline_scaled.py \
  --user-email dev@local.seed.invalid \
  --target-done 800 --min-dataset-rows 500 --min-classes 3 \
  --seed-count 800 --batch-limit 800 --concurrency 8 \
  --only-missing
```

**Smoke rápido** (menos análises; pode precisar de `--continue-on-short-dataset` se o export global ainda for pequeno):

```bash
python ml/scripts/run_gold_pipeline_scaled.py \
  --user-email smoke@local.seed.invalid \
  --seed-count 200 --batch-limit 200 --concurrency 4 \
  --target-done 150 --min-dataset-rows 100 --min-classes 2 \
  --max-iterations 1 --sync --continue-on-short-dataset
```

PowerShell (uma linha), mesmo smoke:

```powershell
python ml/scripts/run_gold_pipeline_scaled.py --user-email smoke@local.seed.invalid --seed-count 200 --batch-limit 200 --concurrency 4 --target-done 150 --min-dataset-rows 100 --min-classes 2 --max-iterations 1 --sync --continue-on-short-dataset
```

Relatórios: `ml/training/reports/gold_run_summary.md`, `eval_seniority.md`, `ab_low_confidence_report.md`, `dataset_evolution.md`, `dataset_report.md`.

Diagnóstico extra:

```bash
python ml/training/src/tune_thresholds.py \
  --model_dir ml/models/seniority_signals_v1 \
  --split_dir ml/data/splits/seniority_latest \
  --out_md ml/training/reports/threshold_tuning.md \
  --out_json ml/training/reports/threshold_recommended.json
```

Relatório TCC (preencher após rodar em produção): `docs/analysis/tcc_results_seniority_signals_v1.md`.

**Produção (env):** ver `backend/env.example` e `backend/README.md` — `ANALYSIS_SIGNALS_ML_ENABLED`, `ANALYSIS_SIGNALS_MODEL_DIR` (absoluto), `ANALYSIS_SIGNALS_THRESHOLDS_FROM_SETTINGS`, `SENIOR_*`.

## Comandos reprodutíveis

### Treino

```bash
# Seniority (SequenceClassification)
python ml/training/src/train.py --task seniority --language pt-BR --base_model neuralmind/bert-base-portuguese-cased

# Quality (classificacao ordinal: poor/ok/strong)
python ml/training/src/train.py --task quality --language pt-BR --base_model neuralmind/bert-base-portuguese-cased

# Quality hibrido (features explicitas + calibrador leve)
python ml/training/src/train.py --task quality --quality_mode hybrid --language pt-BR --model_version analysis_quality_hybrid_v1_pt

# Matching (requer dataset com job_text + resume_text)
python ml/training/src/train.py --task matching --language pt-BR --base_model neuralmind/bert-base-portuguese-cased

# Com versionamento explícito
python ml/training/src/train.py --task seniority --language pt-BR --base_model neuralmind/bert-base-portuguese-cased --model_version analysis_v1_pt

# Multi-idioma (pt-BR + en-US + es-ES)
python ml/training/src/train.py --task seniority --language_mode multi --languages pt-BR en-US es-ES --base_model xlm-roberta-base --model_version analysis_v1_multi
```

### Export

```bash
# Dataset oficial (Django): análises DONE → JSONL v1.1 (signals-only por padrão; gold = colunas persistidas)
cd backend
python manage.py migrate
python manage.py backfill_seniority_labels
python manage.py export_seniority_dataset \
  --out ../ml/data/processed/seniority_from_db.jsonl \
  --limit 5000 \
  --schema-version 1.1
cd ..

# Validar schema / distribuições → ml/training/reports/dataset_report.md
python ml/training/src/validate_dataset.py --in ml/data/processed/seniority_from_db.jsonl

# Split determinístico por resume_key (sem vazamento)
python ml/training/src/split_dataset.py \
  --in ml/data/processed/seniority_from_db.jsonl \
  --out_dir ml/data/splits/seniority_latest \
  --seed 42

# Treinar modelo signals (LogReg + scaler; calibração Platt/isotonic se val ≥ --calibration_min_val)
python ml/training/src/train_seniority.py \
  --train_jsonl ml/data/splits/seniority_latest/train.jsonl \
  --val_jsonl ml/data/splits/seniority_latest/val.jsonl \
  --model_version seniority_signals_v1 \
  --out_dir ml/models/seniority_signals_v1

# Avaliar no test (accuracy, F1 macro, matriz; destaca confusões mid↔senior e junior↔mid)
python ml/training/src/eval_seniority.py \
  --model_dir ml/models/seniority_signals_v1 \
  --test_jsonl ml/data/splits/seniority_latest/test.jsonl \
  --out_md ml/training/reports/eval_seniority.md \
  --metrics_json ml/models/seniority_signals_v1/test_metrics.json

# Carimbar dataset_version + métricas de teste no metadata.json
python ml/training/src/export_seniority_sklearn_model.py \
  --model_dir ml/models/seniority_signals_v1 \
  --split_meta ml/data/splits/seniority_latest/split_meta.json \
  --test_metrics_json ml/models/seniority_signals_v1/test_metrics.json

# A/B offline (export de baixa confiança ou JSONL do endpoint interno)
cd backend
python manage.py export_low_confidence_cases --out ../ml/data/processed/low_confidence.jsonl --limit 500
cd ..
python ml/training/src/ab_compare_low_confidence.py \
  --in_jsonl ml/data/processed/low_confidence.jsonl \
  --model_dir ml/models/seniority_signals_v1
```

Produção: defina `ANALYSIS_SIGNALS_ML_ENABLED=true`, `ANALYSIS_MODEL_ROOT` apontando para `ml/models` e (opcional) `ANALYSIS_SIGNALS_ML_SUBDIR=seniority_signals_v1`. O backend carrega `model.joblib` uma vez por processo (`loader_signals_model`).

```bash
# Dataset de calibração / fine-tune a partir de análises já gravadas (JSONL, ver ml/labeling/policies.md)
python ml/scripts/export_seniority_from_db.py --out ml/data/processed/seniority_from_db.jsonl --limit 5000

# Gerar metadata.json (obrigatório para backend)
python ml/training/src/export.py --model_version analysis_v1_pt --format hf

# Gerar metadata para artefato hibrido
python ml/training/src/export.py --model_version analysis_quality_hybrid_v1_pt --format hf

# Exportar também para ONNX
python ml/training/src/export.py --model_version analysis_v1_pt --format onnx
```

### Revisão interna (casos com baixa confiança na senioridade)

Defina no backend:

- `ANALYSIS_INTERNAL_REVIEW_SECRET` (obrigatório; com `DEBUG=False` use segredo com ≥ `ANALYSIS_INTERNAL_SECRET_MIN_LENGTH` caracteres).
- `ANALYSIS_INTERNAL_REVIEW_KEY_SALT` (recomendado) para `analysisKey` / `resumeKey` / `userKey` e chaves do dataset.

Chamadas (sem JWT), com header `X-Analysis-Internal-Token: <segredo>`:

- `GET /analysis/internal/low-confidence?confidence=low&limit=50` — triagem (pseudo-chaves, sem texto de CV).
- `GET /analysis/internal/low-confidence/export` — JSONL schema **1.1** por defeito (signals-only).
- `POST /analysis/internal/review/seniority` — corpo `{ "analysisKey", "reviewLabel", "reviewNote?" }` (rótulo gold).
- `GET /analysis/internal/metrics/seniority?days=7` — agregados para governança.

Comandos equivalentes (CLI): `python manage.py review_seniority_label`, `python manage.py backfill_seniority_labels`.

Pipeline sugerido: validar → split por `resume_key` → `train_seniority.py` → `eval_seniority.py` → carimbar `dataset_version` (`export_seniority_sklearn_model.py`). Ver `ml/labeling/policies.md`.

### Avaliação

```bash
python ml/training/eval.py --model_version analysis_v1_pt
```

### Preparação do dataset de quality

```bash
# Preenche quality_score e quality_level de forma reproduzível
python ml/training/src/bootstrap_quality_labels.py

# Colapsa quality para 3 classes: poor/ok/strong
python ml/training/src/remap_quality_levels.py

# Adiciona exemplos contrastivos e balanceados para quality (pt-BR)
python ml/training/src/expand_quality_dataset.py

# Gera dataset grande de matching com hard negatives
python ml/training/src/generate_matching_dataset.py
```

## metadata.json

Obrigatório para o backend descobrir e carregar o modelo. Campos:

- `model_name_base`: modelo base (ex: neuralmind/bert-base-portuguese-cased)
- `model_version`: versão (ex: analysis_v1_pt)
- `dataset_version`: hash do split
- `task`: seniority | quality | matching | multitask | **seniority_signals** (sklearn signals-only)
- `features_schema`: lista de features (obrigatório para `seniority_signals`)
- `metrics_summary` / `test_metrics`: accuracy e f1 após `eval_seniority` + `export_seniority_sklearn_model`
- `languages_supported`: ["pt-BR", "en-US", "es-ES"]
- `trained_at`: ISO8601
- `metrics`: accuracy, f1_macro, mae_score, etc.
- `input_limits`: max_tokens, max_chars

## Dataset

Splits em `ml/data/splits/`:

- `train.jsonl`, `val.jsonl`, `test.jsonl`
- Formato por tarefa em `ml/labeling/policies.md`
- Para `quality`, o treino usa preferencialmente `labels.quality_level` (`poor|ok|strong`) e preserva `labels.quality_score` para auditoria e mapeamento para 0-100 no backend.

## Como rodar do zero — gold pipeline (checklist)

1. **Backend** — Postgres + `DATABASE_URL`, `cd backend && python manage.py migrate`.
2. **Rótulos persistidos** — `python manage.py backfill_seniority_labels` (não mexe em linhas já revisadas).
3. **(Opcional) Revisão humana** — `GET /analysis/internal/low-confidence?confidence=low` → `POST /analysis/internal/review/seniority` com `X-Analysis-Internal-Token`, ou `review_seniority_label --analysis-key … --label …`.
4. **Export v1.1** — `export_seniority_dataset --out …/seniority_from_db.jsonl --schema-version 1.1`.
5. **ML** — `python ml/training/src/validate_dataset.py --in …/seniority_from_db.jsonl` → `split_dataset.py` → `train_seniority.py` → `eval_seniority.py` (saída `eval_seniority.md`) → `export_seniority_sklearn_model.py`.
6. **Produção** — `ANALYSIS_SIGNALS_ML_ENABLED=true`, `ANALYSIS_SIGNALS_MODEL_DIR` absoluto; thresholds conforme `env.example`.
7. **A/B** — `export_low_confidence_cases` + `ab_compare_low_confidence.py` → `ab_low_confidence_report.md`.
8. **Escala automática (recomendado)** — `python ml/scripts/run_gold_pipeline_scaled.py …` → `gold_run_summary.md` + `dataset_evolution.md` + relatórios de eval/A/B; ou passo a passo manual com `run_gold_pipeline_with_seed.py`.
9. **Resumo único TCC** — `ml/training/reports/gold_run_summary.md` (após `run_gold_pipeline_scaled.py`).
10. **Documentação TCC** — `docs/analysis/tcc_gold_pipeline.md`.
