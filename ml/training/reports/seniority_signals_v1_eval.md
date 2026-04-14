# Seniority signals model — evaluation

- **model_dir**: `C:/Skill-Refine-TCC/ml/models/seniority_signals_v1`
- **test_jsonl**: `C:/Skill-Refine-TCC/ml/data/splits/seniority_latest/test.jsonl`
- **rows (evaluated)**: 12
- **rows skipped (label not in model classes)**: 0

## Headline metrics

- **accuracy**: 0.9167
- **F1 macro**: 0.8939

## Confusion matrix (rows = true, cols = predicted)

| | intern | junior | mid | senior |
|---|---|---|---|---|
| intern | 2 | 0 | 0 | 0 |
| junior | 0 | 3 | 0 | 0 |
| mid | 0 | 0 | 5 | 0 |
| senior | 0 | 0 | 1 | 1 |

## High-risk confusions

Focus on adjacent seniority steps (policy-sensitive):

- `senior_as_mid`: **1**
- `mid_as_senior`: **0**
- `junior_as_mid`: **0**
- `mid_as_junior`: **0**
- `intern_as_junior`: **0**
- `junior_as_intern`: **0**

## Classification report

```
              precision    recall  f1-score   support

      intern       1.00      1.00      1.00         2
      junior       1.00      1.00      1.00         3
         mid       0.83      1.00      0.91         5
      senior       1.00      0.50      0.67         2

    accuracy                           0.92        12
   macro avg       0.96      0.88      0.89        12
weighted avg       0.93      0.92      0.91        12
```
