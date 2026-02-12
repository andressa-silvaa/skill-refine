# Analysis Inference Module

Módulo de inferência local para análise de currículos: senioridade, qualidade, insights e recomendações.

## Estrutura

```
inference/
  config.py         # Config por env (model paths, limits)
  loader.py         # Singleton loader (TF-IDF; HuggingFace quando configurado)
  types.py          # AnalysisResult, ResumeSections
  resume_mapper.py  # resume_to_text por seção (pt/en/es)
  predictors/       # seniority, quality, matching, sections
  postprocess/      # insights, recommendations (heurísticas, sem LLM)
  orchestrator.py   # analyze_resume()
  safety.py         # truncation, sanitization, sem PII em logs
```

## Uso

```python
from apps.analysis.application.inference import analyze_resume

result = analyze_resume(
    resume_data=resume_detail_payload(resume),
    job_description_text="...",  # opcional
    language="pt-BR",  # de user.preferences.language
)
# result: score, task_scores, payload_json, model_name, model_version, provider
```

## Config (env)

- `ANALYSIS_TFIDF_MODEL_PATH` — caminho ao modelo TF-IDF (pickle)
- `ANALYSIS_MODEL_DIR` — diretório base
- `ANALYSIS_MAX_CHARS_RESUME` — limite de caracteres do currículo (12000)
- `ANALYSIS_MAX_CHARS_JOB` — limite da vaga (8000)
- `ANALYSIS_MULTILANG` — usar modelo multi-idioma (mBERT/XLM-R)

## Celery

Quando Celery estiver configurado, troque em `run_analysis`:

```python
from apps.analysis.tasks import run_resume_analysis_task
# run_resume_analysis_task.delay(str(analysis.id))
```

Atualmente usa threading como fallback.
