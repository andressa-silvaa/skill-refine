# Pipeline de dados — Análise de currículo (ML/TCC)

Pipeline de dataset para treino/fine-tuning de modelos de análise de currículo (ex.: BERTimbau). Suporte **multilíngue** (PT-BR, EN-US, ES-ES): prioridade PT-BR, arquitetura pronta para EN/ES. Sem PII em outputs; split por `resume_id` (sem vazamento); rotulagem semi-automática (heurísticas + revisão manual).

---

## Decisão de i18n

**Backend retorna chaves canônicas + params; frontend traduz.**  
Ver `labeling/policies.md` e `labeling/label_maps.json`.

---

## Estrutura

```
ml/
  data/
    raw/              # Dados brutos (não versionados, exceto .gitkeep)
    processed/        # Dataset normalizado + labels
    splits/           # train.jsonl, val.jsonl, test.jsonl (por resume_id)
  datasets/
    SOURCES.md        # Fontes de vagas e currículos (licenças, idioma, links)
  labeling/
    policies.md       # Definição de tarefas e políticas de labels
    label_maps.json
    section_labels.json
    heuristics/       # Verbos e cabeçalhos por idioma
      verbs_pt.json, verbs_en.json, verbs_es.json
      section_headers_pt.json, section_headers_en.json, section_headers_es.json
    review_exports/   # Exports para revisão manual
  schemas/
    analysis_dataset.schema.json   # Linhas por tarefa (seniority, sections, quality, matching)
    dataset_item.schema.json       # Registro unificado (resume_id, resume_text, labels, heuristics)
  scripts/
    collect_jobs.py              # Coleta de vagas (local ou scraping opcional)
    generate_synthetic_resumes.py # Currículos sintéticos (PT-BR primeiro)
    anonymize_resumes.py         # Anonimização PII (currículos reais)
    preprocess.py                # Normalização, seções, tokenização
    label_with_heuristics.py     # Rótulos iniciais por heurísticas (JSON)
    export_for_review.py        # Export CSV/JSONL para revisão manual
    import_reviewed_labels.py   # Reimportar gold (label_source=revisado)
    split_by_resume_id.py       # Split train/val/test sem vazamento (estratificado)
    validate_dataset.py         # Validação schema + labels
    stats_report.py             # Estatísticas + dataset_stats.md
    build_dataset.py            # Orquestração: normalizar → heurísticas → validar → split
    normalize_resume.py         # Normalização texto + PII
    generate_heuristic_labels.py # Heurísticas inline (seniority, quality)
  reports/
    dataset_stats.md            # Gerado por stats_report.py --report-md
  eval/
    metrics.py
    confusion_matrix.py
  README.md
```

---

## Como rodar o pipeline

Recomendado: a partir da raiz do repo, com `PYTHONPATH` incluindo `ml/scripts` ou rodando de dentro de `ml/scripts`.

### 1. Coleta de vagas (opcional)

```bash
cd ml/scripts
# Local: arquivo ou diretório com JSON/CSV
python collect_jobs.py --source ../data/raw/jobs --language pt -o ../data/raw/jobs.jsonl
# Scraping: desativado por padrão (variável SCRAPING_ENABLED)
```

Ver **datasets/SOURCES.md** para fontes públicas e licenças.

### 2. Currículos sintéticos (recomendado para TCC)

```bash
python generate_synthetic_resumes.py -n 100 --language pt -o ../data/raw/synthetic_resumes.jsonl
# Com balanceamento de "currículos ruins" (--bad-ratio 0.2)
```

### 3. Currículos reais anonimizados (opcional)

```bash
# Raw fora do repo (gitignored). Saída anonimizada em data/processed ou raw.
python anonymize_resumes.py path/to/raw_resumes.jsonl -o ../data/raw/anonymized.jsonl
# Opcional: --mask-names, --company-list companies.txt
```

### 4. Pré-processamento

```bash
python preprocess.py ../data/raw/synthetic_resumes.jsonl -o ../data/processed/preprocessed.jsonl
# Opcional: --tokenize (BERTimbau; requer transformers)
```

### 5. Rotulagem heurística

```bash
python label_with_heuristics.py ../data/processed/preprocessed.jsonl -o ../data/processed/labeled.jsonl
```

Usa `labeling/heuristics/verbs_*.json` e `section_headers_*.json`.

### 6. Export para revisão manual

```bash
python export_for_review.py ../data/processed/labeled.jsonl -o ../labeling/review_exports/for_review.csv --format csv
```

Editar colunas `reviewed_seniority`, `reviewed_quality_score`, `reviewed_notes`.

### 7. Reimportar gold

```bash
python import_reviewed_labels.py ../labeling/review_exports/for_review.csv ../data/processed/labeled.jsonl -o ../data/processed/gold.jsonl
```

### 8. Validar dataset

```bash
python validate_dataset.py ../data/processed/labeled.jsonl --stats
# Aceita formato unificado (resume_id, resume_text, labels) ou task_type (seniority, sections, quality, matching)
```

### 9. Split por resume_id (sem vazamento)

```bash
python split_by_resume_id.py ../data/processed/labeled.jsonl -o ../data/splits --train 0.8 --val 0.1 --test 0.1
# Estratificação por language+seniority (--no-stratify para desativar)
```

Gera `data/splits/train.jsonl`, `val.jsonl`, `test.jsonl`.

### 10. Relatório de estatísticas

```bash
python stats_report.py ../data/processed/labeled.jsonl -o report.json --report-md
# --report-md gera ml/reports/dataset_stats.md (total por idioma, distribuição por classe, exemplos, heuristic vs revisado)
```

### Pipeline completo (sintético → processado → splits)

```bash
# Gerar sintéticos
python generate_synthetic_resumes.py -n 80 --language pt -o ../data/raw/synthetic.jsonl
# Pré-processar + rotular
python preprocess.py ../data/raw/synthetic.jsonl -o ../data/processed/preprocessed.jsonl
python label_with_heuristics.py ../data/processed/preprocessed.jsonl -o ../data/processed/dataset.jsonl
# Validar + split + relatório
python validate_dataset.py ../data/processed/dataset.jsonl --stats
python split_by_resume_id.py ../data/processed/dataset.jsonl -o ../data/splits
python stats_report.py ../data/processed/dataset.jsonl --report-md
```

Ou usar **build_dataset.py** para fluxo integrado (entrada JSONL com task_type ou unificado):

```bash
python build_dataset.py --input ../data/raw/samples.jsonl --output-dir ../data/processed --splits-dir ../data/splits
```

---

## Como adicionar novo idioma

1. **labeling/heuristics/**  
   Criar `verbs_<lang>.json` e `section_headers_<lang>.json` (mesmo formato dos existentes).

2. **Scripts**  
   - `normalize_resume.py` / `label_with_heuristics.py`: já usam `language` e carregam JSON por idioma.  
   - `generate_synthetic_resumes.py`: adicionar `TEMPLATES["<lang>"]`, listas de áreas/skills e `SECTION_HEADERS_<LANG>`.

3. **Schemas e validação**  
   - `schemas/dataset_item.schema.json`: incluir novo valor em `language` (ex.: `"de"`).  
   - `validate_dataset.py`: adicionar idioma em `LANGUAGES`.

4. **label_maps.json**  
   Incluir novo código em `languages` se necessário.

---

## Como revisar rótulos manualmente

1. Exportar:  
   `python export_for_review.py .../labeled.jsonl -o .../review_exports/for_review.csv`

2. Abrir o CSV e preencher:  
   - `reviewed_seniority`: intern | junior | mid | senior  
   - `reviewed_quality_score`: 0–100  
   - `reviewed_notes`: opcional

3. Reimportar:  
   `python import_reviewed_labels.py .../for_review.csv .../labeled.jsonl -o .../gold.jsonl`

4. Usar `gold.jsonl` para splits e treino; `label_source` ficará `revisado` onde houver revisão.

---

## Tarefas (resumo)

| Tarefa | Descrição | Labels / Saída |
|--------|-----------|----------------|
| A — Senioridade | Classificação do nível | intern, junior, mid, senior |
| B — Seções | Classificação por linha/bloco | EXPERIENCE, EDUCATION, SKILLS, ... |
| C — Qualidade | Score 0–100 + critérios explicáveis | label_score, feature_flags |
| D — Matching | Vaga ↔ currículo | match_score, top_skill_matches |

Detalhes em **labeling/policies.md**.

---

## Formato do dataset

- **Unificado (dataset_item):** `id`, `language`, `resume_id`, `resume_text`, `job_text` (opcional), `sections`, `labels`, `heuristics`, `source`, `label_source`, `created_at`, `token_length`.  
  Schema: **schemas/dataset_item.schema.json**.

- **Por tarefa (analysis_dataset):** `task_type`, `language`, `resume_id`, `input_text`/`line_text`/`job_text`/`resume_text`, `label`/`label_score`/`label_match`, etc.  
  Schema: **schemas/analysis_dataset.schema.json**.

---

## Avaliação

- **eval/metrics.py**: accuracy, F1 macro/micro, MSE, MAE, R²; métricas por idioma.  
- **eval/confusion_matrix.py**: matriz de confusão para classificação.  
- Baseline heurístico: comparar saída de `label_with_heuristics.py` / `generate_heuristic_labels.py` com modelo.

---

## Critérios de aceitação

- Pipeline roda end-to-end e gera dataset processado + splits sem vazamento.  
- Validação OK (schema + labels).  
- Relatório de estatísticas (`dataset_stats.md`) com total por idioma, distribuição por classe, exemplos anonimizados, taxa heuristic vs revisado.  
- `language` presente em todos os registros; estrutura permite adicionar EN/ES sem refazer tudo.  
- Nenhum dado sensível (PII) nos outputs.  
- Heurísticas e rotulagem semi-automática implementadas e exportáveis para revisão.
