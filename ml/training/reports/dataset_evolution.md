# Dataset evolution log (TCC)

Automated snapshots from `report_dataset_evolution.py`.

---

## Snapshot — 2026-04-13 12:46 UTC

- **jsonl**: `ml/data/processed/seniority_from_db.jsonl`
- **rows (N)**: 35
- **dataset_version** (split_meta): `165462efc5e02e5dc7cc463b`
- **reviewed rows**: 0 (0.00% of N)

### Label distribution (gold `seniority_label`)

- `junior`: 34 (97.1%)
- `intern`: 1 (2.9%)

### Model metrics (held-out test)

- **accuracy**: 1.0
- **F1 macro**: 1.0

### Eval excerpt (head)

  > # Seniority signals model — evaluation
  > - **model_dir**: `ml/models/seniority_signals_v1`
  > - **test_jsonl**: `ml/data/splits/seniority_latest/test.jsonl`
  > - **rows (evaluated)**: 1
  > - **rows skipped (label not in model classes)**: 0
  > ## Headline metrics
  > - **accuracy**: 1.0000
  > - **F1 macro**: 1.0000
  > ## Confusion matrix (rows = true, cols = predicted)
  > | | intern | junior |
  > |---|---|---|
  > | intern | 0 | 0 |
  > | junior | 0 | 1 |
  > ## High-risk confusions
  > Focus on adjacent seniority steps (policy-sensitive):
  > - `intern_as_junior`: **0**
  > - `junior_as_intern`: **0**

### A/B low-confidence (excerpt)

  - - **`senior` % before (structural rules only)**: 0.00%
  - - **`senior` % after (signals_ml + gates + vetoes)**: 0.00%

---

## Snapshot — 2026-04-13 12:59 UTC

- **jsonl**: `C:/Skill-Refine-TCC/ml/data/processed/seniority_from_db.jsonl`
- **rows (N)**: 235
- **dataset_version** (split_meta): `eff47b71aa6e337ed4d48c3d`
- **reviewed rows**: 0 (0.00% of N)

### Label distribution (gold `seniority_label`)

- `junior`: 84 (35.7%)
- `mid`: 67 (28.5%)
- `intern`: 51 (21.7%)
- `senior`: 33 (14.0%)

### Model metrics (held-out test)

- **accuracy**: 1.0
- **F1 macro**: 1.0

### Eval excerpt (head)

  > # Seniority signals model — evaluation
  > - **model_dir**: `C:/Skill-Refine-TCC/ml/models/seniority_signals_v1`
  > - **test_jsonl**: `C:/Skill-Refine-TCC/ml/data/splits/seniority_signals_v1/test.jsonl`
  > - **rows (evaluated)**: 31
  > - **rows skipped (label not in model classes)**: 0
  > ## Headline metrics
  > - **accuracy**: 1.0000
  > - **F1 macro**: 1.0000
  > ## Confusion matrix (rows = true, cols = predicted)
  > | | intern | junior | mid | senior |
  > |---|---|---|---|---|
  > | intern | 7 | 0 | 0 | 0 |
  > | junior | 0 | 9 | 0 | 0 |
  > | mid | 0 | 0 | 10 | 0 |
  > | senior | 0 | 0 | 0 | 5 |
  > ## High-risk confusions
  > Focus on adjacent seniority steps (policy-sensitive):

### A/B low-confidence (excerpt)

  - - **`senior` % before (structural rules only)**: 0.00%
  - - **`senior` % after (signals_ml + gates + vetoes)**: 0.00%

---

## Snapshot — 2026-04-13 13:11 UTC

- **jsonl**: `C:/Skill-Refine-TCC/ml/data/processed/seniority_from_db.jsonl`
- **rows (N)**: 1035
- **dataset_version** (split_meta): `d4710d7ed6479a6cd328fb86`
- **reviewed rows**: 0 (0.00% of N)

### Label distribution (gold `seniority_label`)

- `mid`: 328 (31.7%)
- `junior`: 284 (27.4%)
- `intern`: 251 (24.3%)
- `senior`: 172 (16.6%)

### Model metrics (held-out test)

- **accuracy**: 1.0
- **F1 macro**: 1.0

### Eval excerpt (head)

  > # Seniority signals model — evaluation
  > - **model_dir**: `C:/Skill-Refine-TCC/ml/models/seniority_signals_v1`
  > - **test_jsonl**: `C:/Skill-Refine-TCC/ml/data/splits/seniority_signals_v1/test.jsonl`
  > - **rows (evaluated)**: 151
  > - **rows skipped (label not in model classes)**: 0
  > ## Headline metrics
  > - **accuracy**: 1.0000
  > - **F1 macro**: 1.0000
  > ## Confusion matrix (rows = true, cols = predicted)
  > | | intern | junior | mid | senior |
  > |---|---|---|---|---|
  > | intern | 30 | 0 | 0 | 0 |
  > | junior | 0 | 42 | 0 | 0 |
  > | mid | 0 | 0 | 53 | 0 |
  > | senior | 0 | 0 | 0 | 26 |
  > ## High-risk confusions
  > Focus on adjacent seniority steps (policy-sensitive):

### A/B low-confidence (excerpt)

  - - **`senior` % before (structural rules only)**: 0.00%
  - - **`senior` % after (signals_ml + gates + vetoes)**: 0.00%

---
