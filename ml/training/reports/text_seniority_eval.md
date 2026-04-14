# Text seniority model evaluation (TCC)

Train a sequence-classification head on `seniority_review_label` (gold) with `resume_to_text_sanitized` as input.

- Export HF model to `ml/models/text_seniority_v1/` (tokenizer + `config.json` + weights).
- Metrics: macro-F1, confusion matrix (intern / junior / mid / senior).
- Enable inference with `ANALYSIS_TEXT_SENIORITY_ENABLED=1` and `ANALYSIS_TEXT_SENIORITY_MODEL_DIR=<absolute path>`.

See `ml/README.md` for environment variables.
