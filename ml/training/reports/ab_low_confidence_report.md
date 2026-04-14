# A/B — low confidence seniority (offline)

- **input**: `C:/Skill-Refine-TCC/ml/data/processed/low_confidence.jsonl`
- **model_dir**: `C:/Skill-Refine-TCC/ml/models/seniority_signals_v1`
- **rows**: 28

## Senior share (rule-only vs signals_ml)

- **`senior` % before (structural rules only)**: 0.00%
- **`senior` % after (signals_ml + gates + vetoes)**: 0.00%

## Senior without structural evidence (phantom risk)

Evidence rule (aligned with current cfg): months ≥ 60, experiences ≥ 2, bullets ≥ 6.

- **rule-only `senior` violating evidence**: 0
- **after signals_ml `senior` still violating evidence**: 0

## Label distribution — rule-only (before)

- `junior`: 28

## Label distribution — after signals_ml

- `junior`: 28

## Dataset label distribution (reference)

- `junior`: 28

## Top gating reasons (from export)


## Sample (20 rows, no PII)

```json
[
  {
    "resume_key": "b60a8dd1d9b1f0b0d46fa75f245197ae",
    "signals": {
      "total_months_experience": 0,
      "experiences_count": 0,
      "bullets_count": 0,
      "completeness_score": 46,
      "word_count": 37,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "b60a8dd1d9b1f0b0d46fa75f245197ae",
    "signals": {
      "total_months_experience": 0,
      "experiences_count": 0,
      "bullets_count": 0,
      "completeness_score": 46,
      "word_count": 37,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "b60a8dd1d9b1f0b0d46fa75f245197ae",
    "signals": {
      "total_months_experience": 0,
      "experiences_count": 0,
      "bullets_count": 0,
      "completeness_score": 46,
      "word_count": 37,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "b60a8dd1d9b1f0b0d46fa75f245197ae",
    "signals": {
      "total_months_experience": 0,
      "experiences_count": 0,
      "bullets_count": 0,
      "completeness_score": 46,
      "word_count": 37,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "b60a8dd1d9b1f0b0d46fa75f245197ae",
    "signals": {
      "total_months_experience": 0,
      "experiences_count": 0,
      "bullets_count": 0,
      "completeness_score": 46,
      "word_count": 37,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "890cb316264e485eaa3413e9886bc806",
    "signals": {
      "total_months_experience": 1,
      "experiences_count": 1,
      "bullets_count": 1,
      "completeness_score": 69,
      "word_count": 51,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "b60a8dd1d9b1f0b0d46fa75f245197ae",
    "signals": {
      "total_months_experience": 0,
      "experiences_count": 0,
      "bullets_count": 0,
      "completeness_score": 46,
      "word_count": 37,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  },
  {
    "resume_key": "0ba7bd432d703b2c7ee8eabc97cf5203",
    "signals": {
      "total_months_experience": 0,
      "experiences_count": 0,
      "bullets_count": 0,
      "completeness_score": 12,
      "word_count": 7,
      "has_internship_terms": false
    },
    "rule_label": "junior",
    "signals_ml_label": "junior",
    "dataset_label": "junior",
    "gatingReasons": []
  }
]
```
