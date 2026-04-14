# Seniority signals — run summary (auto)

## Dataset

- **rows (processed JSONL)**: 35
- **dataset_version** (split fingerprint): `165462efc5e02e5dc7cc463b`
- **split row counts**: {"train": 28, "val": 6, "test": 1}

### Class distribution (from JSONL labels)

- `junior`: 34 (97.1%)
- `intern`: 1 (2.9%)

### Cross-check (dataset_report.md)

- `junior`: 34
- `intern`: 1

⚠️ **Class imbalance**: top label share ≈ 97.1%. Consider increasing `--since` / `--limit` or reviewing labels/policy before relying on thresholds.

## Test metrics (held-out split)

- **accuracy**: 1.0
- **F1 macro**: 1.0

### Top confusion cells (test)

- `intern_as_junior`: **0**
- `junior_as_intern`: **0**

## Adjacent-class focus

Policy-sensitive pairs: **mid↔senior**, **junior↔mid**, **intern↔junior** (see eval report for full matrix).

- Eval markdown: `C:/Skill-Refine-TCC/ml/training/reports/eval_seniority.md`
