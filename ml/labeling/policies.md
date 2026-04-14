# Rotulagem e dataset (senioridade)

A política canônica de classes e regras está em:

- `docs/analysis/seniority_policy.md`

## Schema do JSONL (v1.0)

Cada linha segue o contrato descrito em `ml/data/schema/seniority_dataset_schema.json`:

- `analysis_key`, `resume_key`, `user_key`: pseudonimização SHA-256 (truncada) com sal configurável (`ANALYSIS_INTERNAL_REVIEW_KEY_SALT` ou `--hash-salt` / fallback do `SECRET_KEY`).
- `signals`: features estruturadas (espelho de `ResumeSignals`).
- `labels`: `seniority_label`, `rule_label`, `ml_label` (quando há evidência de ajuste ML no payload), `confidence`.
- `targets`: `overall_score`, `task_scores`, `completeness_score`, `completeness_level`.
- `text_sanitized`: apenas no modo `full` do export.

## Export a partir do banco

Diretório sugerido: `ml/data/processed/`.

### Export completo (todas as análises DONE)

1. **Somente sinais (recomendado para LGPD)** — sem texto do CV:

   ```bash
   cd backend
   python manage.py export_seniority_dataset --out ../ml/data/processed/seniority_from_db.jsonl --limit 5000
   ```

   Ou, a partir da raiz do repositório:

   ```bash
   python ml/scripts/export_seniority_from_db.py --out ml/data/processed/seniority_from_db.jsonl --limit 5000
   ```

2. **Modo `full`** — adiciona `text_sanitized` (PII comum mascarada + limite de tamanho). Tratar como dado sensível.

   ```bash
   python manage.py export_seniority_dataset --mode full --out ../ml/data/processed/seniority_from_db_full.jsonl --limit 1000
   ```

3. **`--hash-salt`** — pepper dedicado para chaves pseudonimizadas (recomendado em produção).

### Casos de baixa confiança (loop revisão → dataset)

```bash
cd backend
python manage.py export_low_confidence_cases --out ../ml/data/processed/low_confidence.jsonl --confidence low --limit 500
```

Ou via API interna: `GET /analysis/internal/low-confidence/export` (mesmo schema, signals-only).

## Validação e split (reprodutível)

A partir da raiz do repositório:

```bash
python ml/training/src/validate_dataset.py --in ml/data/processed/seniority_from_db.jsonl
python ml/training/src/split_dataset.py --in ml/data/processed/seniority_from_db.jsonl --out_dir ml/data/splits/seniority_latest --seed 42
```

O split é **por `resume_key`** (todas as linhas de um mesmo currículo ficam no mesmo split). `split_meta.json` no diretório de saída contém `dataset_version` (impressão digital estável).

## Treino leve (sinais)

```bash
python ml/training/src/train_seniority.py --train_jsonl ml/data/splits/seniority_latest/train.jsonl --model_version seniority_sklearn_signals_v1 --out_dir ml/models/seniority_sklearn_signals_v1
python ml/training/src/eval_seniority.py --model_dir ml/models/seniority_sklearn_signals_v1 --test_jsonl ml/data/splits/seniority_latest/test.jsonl --out ml/training/reports/seniority_sklearn_eval.txt
python ml/training/src/export_seniority_sklearn_model.py --model_dir ml/models/seniority_sklearn_signals_v1 --split_meta ml/data/splits/seniority_latest/split_meta.json
```

Fine-tune HF completo continua em `ml/training/src/train.py --task seniority`.
