# Seniority signals model — evaluation

- **model_dir**: `ml/models/seniority_signals_v1`
- **test_jsonl**: `ml/data/splits/seniority_signals_v1/test.jsonl`
- **rows (evaluated)**: 151
- **rows skipped (label not in model classes)**: 0

## Headline metrics

- **accuracy**: 1.0000
- **F1 macro**: 1.0000

## Confusion matrix (rows = true, cols = predicted)

| | intern | junior | mid | senior |
|---|---|---|---|---|
| intern | 30 | 0 | 0 | 0 |
| junior | 0 | 42 | 0 | 0 |
| mid | 0 | 0 | 53 | 0 |
| senior | 0 | 0 | 0 | 26 |

## High-risk confusions

Focus on adjacent seniority steps (policy-sensitive):

- `mid_as_senior`: **0**
- `senior_as_mid`: **0**
- `junior_as_mid`: **0**
- `mid_as_junior`: **0**
- `intern_as_junior`: **0**
- `junior_as_intern`: **0**

## Classification report

```
              precision    recall  f1-score   support

      intern       1.00      1.00      1.00        30
      junior       1.00      1.00      1.00        42
         mid       1.00      1.00      1.00        53
      senior       1.00      1.00      1.00        26

    accuracy                           1.00       151
   macro avg       1.00      1.00      1.00       151
weighted avg       1.00      1.00      1.00       151
```
