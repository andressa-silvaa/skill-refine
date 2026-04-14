# Threshold tuning (signals_ml senior gates)

Grid: `SENIOR_PROB_THRESHOLD` × `SENIOR_MIN_MONTHS` × experiences (fixed) × bullets.
Objective: **fewer phantom seniors** and **no junior→senior noise**, while keeping F1 and recall on true seniors **with** structural evidence.

## Recommended (best composite score)

```json
{
  "inference_thresholds": {
    "senior_prob_threshold": 0.65,
    "senior_min_total_months": 48,
    "senior_min_experiences": 2,
    "senior_min_bullets": 8
  },
  "phantom_seniors": 0,
  "junior_to_senior": 0,
  "accuracy": 0.9166666666666666,
  "f1_macro": 0.8939393939393939,
  "recall_true_senior_with_evidence": 1.0
}
```

## Top candidates

| p_thr | months | bullets | phantoms | j→sen | F1 macro | rec(sen+ev) |
|-------|--------|---------|----------|-------|----------|-------------|
| 0.65 | 48 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.65 | 60 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.65 | 72 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.70 | 48 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.70 | 60 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.70 | 72 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.75 | 48 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.75 | 60 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.75 | 72 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.80 | 48 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.80 | 60 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.80 | 72 | 8 | 0 | 0 | 0.8939 | 1.0000 |
| 0.65 | 48 | 5 | 0 | 0 | 0.8939 | 0.5000 |
| 0.65 | 48 | 6 | 0 | 0 | 0.8939 | 0.5000 |
| 0.65 | 60 | 5 | 0 | 0 | 0.8939 | 0.5000 |

**Deploy**: set matching `SENIOR_*` / `ANALYSIS_SIGNALS_ML_*` env vars, or embed `inference_thresholds` in `metadata.json` and set `ANALYSIS_SIGNALS_THRESHOLDS_FROM_SETTINGS=false`.
