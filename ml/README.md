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
# Dataset oficial (Django): análises DONE → JSONL v1.0 (signals-only por padrão)
cd backend
python manage.py export_seniority_dataset \
  --out ../ml/data/processed/seniority_from_db.jsonl \
  --limit 5000
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
  --out_md ml/training/reports/seniority_signals_v1_eval.md \
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
  --model_dir ml/models/seniority_signals_v1 \
  --out_md ml/training/reports/ab_low_confidence_seniority_signals_v1.md
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
- `GET /analysis/internal/low-confidence/export` — JSONL no schema v1.0 (signals-only).
- `GET /analysis/internal/metrics/seniority?days=7` — agregados para governança.

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
