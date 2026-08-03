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
    "senior_min_bullets": 5
  },
  "phantom_seniors": 0,
  "junior_to_senior": 0,
  "accuracy": 0.8888888888888888,
  "f1_macro": 0.8885912698412699,
  "recall_true_senior_with_evidence": 0.875
}
```

## Top candidates

| p_thr | months | bullets | phantoms | j→sen | F1 macro | rec(sen+ev) |
|-------|--------|---------|----------|-------|----------|-------------|
| 0.65 | 48 | 5 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 48 | 6 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 48 | 8 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 60 | 5 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 60 | 6 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 60 | 8 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 72 | 5 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 72 | 6 | 0 | 0 | 0.8886 | 0.8750 |
| 0.65 | 72 | 8 | 0 | 0 | 0.8886 | 0.8750 |
| 0.70 | 48 | 5 | 0 | 0 | 0.8886 | 0.8750 |
| 0.70 | 48 | 6 | 0 | 0 | 0.8886 | 0.8750 |
| 0.70 | 48 | 8 | 0 | 0 | 0.8886 | 0.8750 |
| 0.70 | 60 | 5 | 0 | 0 | 0.8886 | 0.8750 |
| 0.70 | 60 | 6 | 0 | 0 | 0.8886 | 0.8750 |
| 0.70 | 60 | 8 | 0 | 0 | 0.8886 | 0.8750 |

**Deploy**: set matching `SENIOR_*` / `ANALYSIS_SIGNALS_ML_*` env vars, or embed `inference_thresholds` in `metadata.json` and set `ANALYSIS_SIGNALS_THRESHOLDS_FROM_SETTINGS=false`.
