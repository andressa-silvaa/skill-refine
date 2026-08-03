# Seniority signals model — evaluation

- **model_dir**: `ml/models/seniority_signals_v1`
- **test_jsonl**: `ml/data/splits/seniority_synthetic_v2/test.jsonl`
- **rows (evaluated)**: 27
- **rows skipped (label not in model classes)**: 0

## Headline metrics

- **accuracy**: 0.8889
- **F1 macro**: 0.8886

## Confusion matrix (rows = true, cols = predicted)

| | intern | junior | mid | senior |
|---|---|---|---|---|
| intern | 4 | 1 | 0 | 0 |
| junior | 0 | 7 | 0 | 0 |
| mid | 0 | 1 | 6 | 0 |
| senior | 0 | 0 | 1 | 7 |

## High-risk confusions

Focus on adjacent seniority steps (policy-sensitive):

- `senior_as_mid`: **1**
- `mid_as_junior`: **1**
- `intern_as_junior`: **1**
- `mid_as_senior`: **0**
- `junior_as_mid`: **0**
- `junior_as_intern`: **0**

## Classification report

```
              precision    recall  f1-score   support

      intern       1.00      0.80      0.89         5
      junior       0.78      1.00      0.88         7
         mid       0.86      0.86      0.86         7
      senior       1.00      0.88      0.93         8

    accuracy                           0.89        27
   macro avg       0.91      0.88      0.89        27
weighted avg       0.91      0.89      0.89        27
```
