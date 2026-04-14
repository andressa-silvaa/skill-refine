# A/B — low confidence seniority (offline)

- **input**: `ml/data/processed/low_confidence.jsonl`
- **model_dir**: `ml/models/seniority_signals_v1`
- **rows**: 0

## Senior share (rule-only vs signals_ml)

- **`senior` % before (structural rules only)**: 0.00%
- **`senior` % after (signals_ml + gates + vetoes)**: 0.00%

## Senior without structural evidence (phantom risk)

Evidence rule (aligned with current cfg): months ≥ 48, experiences ≥ 2, bullets ≥ 8.

- **rule-only `senior` violating evidence**: 0
- **after signals_ml `senior` still violating evidence**: 0

## Label distribution — rule-only (before)


## Label distribution — after signals_ml


## Dataset label distribution (reference)


## Top gating reasons (from export)


## Sample (20 rows, no PII)

```json
[]
```
