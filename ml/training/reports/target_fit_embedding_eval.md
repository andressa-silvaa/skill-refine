# Target fit embedding evaluation (TCC)

Correlate `targetFitEmbeddingScore` (cosine-calibrated) with reviewed gold scores when available.

- Model default: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers).
- Compare MAE/RMSE of blended `targetFitFinalScore` vs human-reviewed fit.
- Enable with `ANALYSIS_EMBEDDINGS_ENABLED=1` (optional `ANALYSIS_EMBEDDINGS_MODEL_NAME`).

See `ml/README.md` for layout and env vars.
