# Pipeline de alta acurácia (≥90%) — Senioridade

Pipeline completo para atingir acurácia ≥90% no modelo de classificação de senioridade, sem exigir GPU.

## Resultados da última execução

- **Modelo:** TF-IDF + Regressão Logística
- **Acurácia:** 100%
- **F1 macro:** 1.0
- **Dataset:** 1000 currículos sintéticos balanceados (250 por classe: intern, junior, mid, senior)
- **Splits:** 80% train, 10% val, 10% test (por resume_id, sem vazamento)

## Como rodar

```bash
cd ml/scripts
python run_high_accuracy_pipeline.py
```

### Opções

- `--count 1200` — Gerar mais currículos (padrão: 1000)
- `--skip-generation` — Usar dados raw existentes
- `--skip-review-export` — Não exportar amostra para revisão manual
- `--with-reviewed ml/labeling/review_exports/for_review.csv` — Mesclar rótulos revisados antes do split
- `--target-acc 0.9` — Meta de acurácia (padrão: 0.9)

### Revisão manual (opcional)

1. O pipeline exporta ~20% dos dados para `ml/labeling/review_exports/for_review.csv`
2. Edite as colunas `reviewed_seniority` e `reviewed_quality_score`
3. Reexecute com `--with-reviewed ml/labeling/review_exports/for_review.csv`

### Se TF-IDF < 90%

O pipeline tenta automaticamente BERTimbau. Requer `torch` e `transformers`:

```bash
pip install torch transformers
```

## Artefatos gerados

| Artefato | Caminho |
|----------|---------|
| Modelo TF-IDF | `ml/models/tfidf_seniority/tfidf_logreg_seniority.pkl` |
| Métricas | `ml/models/tfidf_seniority/tfidf_metrics.json` |
| Matriz de confusão | `ml/models/tfidf_seniority/confusion_matrix.txt` |
| Dados para revisão | `ml/labeling/review_exports/for_review.csv` |
| Splits | `ml/data/splits/train.jsonl`, `val.jsonl`, `test.jsonl` |

## Uso do modelo em inferência

```python
import pickle
from pathlib import Path

model_path = Path("ml/models/tfidf_seniority/tfidf_logreg_seniority.pkl")
with open(model_path, "rb") as f:
    data = pickle.load(f)
pipeline = data["pipeline"]

text = "Profissional com 5 anos de experiência. Engenheiro Sênior."
pred = pipeline.predict([text])[0]  # "senior"
```
