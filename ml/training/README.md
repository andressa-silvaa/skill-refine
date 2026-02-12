# Pipeline de treino — Análise de currículo (TCC)

Treino/fine-tuning com **Hugging Face Transformers + PyTorch**: tarefas de senioridade, qualidade, seções e matching. Suporte **mono** (PT-BR, BERTimbau) e **multi** (PT/EN/ES, mBERT ou XLM-R). Métricas, matriz de confusão, ablations, versionamento e export.

---

## Requisitos

- Python 3.10+
- `torch`, `transformers`, `scikit-learn`, `pyyaml`
- Opcional: `scipy` (correlação), `matplotlib` (confusion matrix PNG), `onnx` (export ONNX)

```bash
pip install torch transformers scikit-learn pyyaml scipy matplotlib
```

---

## Uso rápido

### 1. Senioridade (mono PT-BR, BERTimbau)

```bash
cd ml/training
python train.py --task seniority --language_mode mono --languages pt-BR
```

- Lê `../data/splits/train.jsonl`, `val.jsonl`, `test.jsonl`.
- Salva modelo em `../models/<model_version>/`.
- Gera relatório e matriz de confusão em `../reports/<model_version>/`.

### 2. Senioridade (multi PT + EN + ES, XLM-R)

```bash
python train.py --task seniority --language_mode multi --languages pt-BR en-US es-ES --base_model xlm-roberta-base
```

- Filtra splits por `pt-BR`, `en-US`, `es-ES`.
- Métricas globais e (quando disponível) por idioma.

### 3. Qualidade (regressão 0–100)

```bash
python train.py --task quality --language_mode mono --languages pt-BR
```

- Dataset deve ter `labels.quality_score` (0–100).
- Métricas: MSE, MAE, Pearson, Spearman.

### 4. Ablations

```bash
# Uma ablation
python train.py --task seniority --language_mode mono --languages pt-BR --ablation remove_stopwords

# Múltiplas ablations (uma por vez)
python train.py --task seniority --ablation remove_stopwords --ablation drop_metrics_numbers --ablation drop_section --drop_section experience

# Rodar todas e gerar relatório comparativo
python train.py --task seniority --language_mode mono --languages pt-BR --run_ablations_only
```

- **remove_stopwords**: remove stopwords do texto (por idioma).
- **drop_section**: remove uma seção (ex.: experience) antes do treino.
- **drop_metrics_numbers**: remove números e símbolos (%, R$, etc.).

Resultado em `../reports/<model_version>/ablations.md`.

### 5. Config YAML

```bash
python train.py --config configs/train.yaml --task seniority
```

Override por CLI: `--epochs`, `--batch_size`, `--max_length`, `--learning_rate`, `--splits_dir`, `--output_dir`, `--reports_dir`, etc.

---

## Formato do dataset (JSONL)

Cada linha é um JSON. Formato **canônico**:

```json
{
  "id": "...",
  "language": "pt-BR",
  "resume_id": "...",
  "inputs": {
    "resume_text": "...",
    "job_text": "..."
  },
  "labels": {
    "seniority": "junior",
    "quality_score": 85,
    "sections": [...],
    "matching_score": 72
  }
}
```

Também aceito: `resume_text` e `labels` no top level (sem `inputs`). Para **seniority** são obrigatórios: texto do currículo e `labels.seniority` (intern|junior|mid|senior). Para **quality**: `labels.quality_score` (0–100). Para **matching**: `inputs.job_text`, `inputs.resume_text`, `labels.matching_score`.

---

## Estrutura de saída

- **Modelo:** `./models/<model_version>/`  
  - `config.json`, `pytorch_model.bin` (ou safetensors), `tokenizer_config.json`, etc.

- **Relatórios:** `./reports/<model_version>/`  
  - `training_cost.md` (tempo de treino, VRAM, métricas).
  - `confusion_matrix.txt`, `confusion_matrix.png` (tarefa de classificação).
  - `ablations.md` (se `--run_ablations_only`).

- **Versionamento:** em `config.json`  
  - `model_version`, `dataset_version`, `git_commit`.

---

## Export

```bash
python export.py --model_dir ../models/analysis_v1_seniority_mono_xxx
```

Gera `metadata.json` no diretório do modelo (model_name_base, model_version, dataset_version, languages, task, metrics, exported_at).

### ONNX (opcional)

```bash
python export.py --model_dir ../models/... --onnx
```

Exporta para `./models/<model_version>/onnx/`. Comparar tempo de inferência ONNX vs Hugging Face manualmente se necessário.

---

## Tarefas

| Tarefa       | Tipo              | Labels / Saída                    |
|-------------|-------------------|-----------------------------------|
| seniority   | Sequence Classif. | intern, junior, mid, senior       |
| sections    | Sentence/Token    | EXPERIENCE, EDUCATION, SKILLS, …  |
| quality     | Regression        | quality_score 0–100               |
| matching    | Bi-encoder        | matching_score; cosine/MLP        |

- **sections**: detecta formato (tokens+tags NER vs sentença+label).  
- **matching**: bi-encoder (recomendado) ou cross-encoder; dataset precisa de `job_text` + `resume_text` + `matching_score`.

---

## Critérios de aceitação

- `python ml/training/train.py --task seniority --language_mode mono --languages pt-BR` treina e gera relatório.
- `python ml/training/train.py --task seniority --language_mode multi --languages pt-BR en-US es-ES --base_model xlm-roberta-base` treina e gera métricas (por idioma quando aplicável).
- Export salva modelo + tokenizer + metadata.
- Ablations rodam e geram comparação em `ablations.md`.
