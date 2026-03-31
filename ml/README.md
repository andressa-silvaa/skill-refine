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
# Gerar metadata.json (obrigatório para backend)
python ml/training/src/export.py --model_version analysis_v1_pt --format hf

# Gerar metadata para artefato hibrido
python ml/training/src/export.py --model_version analysis_quality_hybrid_v1_pt --format hf

# Exportar também para ONNX
python ml/training/src/export.py --model_version analysis_v1_pt --format onnx
```

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
- `task`: seniority | quality | matching | multitask
- `languages_supported`: ["pt-BR", "en-US", "es-ES"]
- `trained_at`: ISO8601
- `metrics`: accuracy, f1_macro, mae_score, etc.
- `input_limits`: max_tokens, max_chars

## Dataset

Splits em `ml/data/splits/`:

- `train.jsonl`, `val.jsonl`, `test.jsonl`
- Formato por tarefa em `ml/labeling/policies.md`
- Para `quality`, o treino usa preferencialmente `labels.quality_level` (`poor|ok|strong`) e preserva `labels.quality_score` para auditoria e mapeamento para 0-100 no backend.
