# Política de senioridade (Skill Refine)

Documento de referência para rotulagem, TCC e implementação em `rule_based_seniority`.  
Classes exibidas na UI (sem valor “unknown”): **intern** (Estágio), **junior** (Júnior), **mid** (Pleno), **senior** (Sênior).

## 1. Fonte de verdade primária

1. **Dados estruturados** do payload (`experiences[]` com `startDate`, `endDate`, `isCurrent`, `position`, `description[]`, etc.).
2. **Tempo de experiência** calculado a partir das datas válidas, com mesclagem de intervalos sobrepostos (evita duplicar meses em cargos paralelos).
3. **Termos explícitos** de estágio/trainee (pt/en/es) nos campos de carreira (cargo, resumo, bullets, nome do CV, cargo alvo).

O **modelo signals_ml** (sklearn: features estruturadas + LogReg + scaler, com calibração opcional) é o caminho **principal** quando habilitado e o artefato está presente: prevê a classe a partir de `signals` (sem texto), com **gates conservadores** para `senior` e veto para perfis com termos de estágio (ver `signals_ml_policy.py` e `signals_ml_predict.py`).

O **modelo Hugging Face** permanece como **ajuste fino de até um nível** apenas quando `signals_ml` **não** está ativo ou falha na inferência (erro de carga/execução), com texto suficiente e gap softmax (ver `ml_adjust.py`).

## 2. Cálculo de tempo (`total_months_experience`)

- Para cada experiência: `startDate` e `endDate` no formato `YYYY-MM-DD` ou `YYYY-MM` (dia 1).
- Se `isCurrent` é verdadeiro ou `endDate` ausente: usar **data atual** como fim (mês corrente).
- Intervalos **inválidos** (fim antes do início, parse falho) são **descartados** e registrados em `reasons`.
- **Sobreposição**: intervalos são unidos; a soma é o total de meses **únicos** cobertos por experiências válidas.

## 3. Regras de classe (base estruturada)

Ordem de aplicação (resumo; detalhes no código):

| Prioridade | Condição | Classe base |
|------------|-----------|-------------|
| Veto | `experiences_count == 0` | **junior** (nunca pleno/sênior; evidência: falta de experiência estruturada) |
| Estágio explícito | `has_internship_terms` | **intern** |
| Tempo curto | `total_months_experience < 12` (com ao menos 1 experiência válida) | **intern** |
| Júnior | 12 ≤ meses ≤ 24 | **junior** |
| Pleno | 24 < meses ≤ 60 | **mid** |
| Sênior | meses > 60 **e** `experiences_count ≥ 2` **e** `bullets_count ≥ 6` | **senior** |
| — | meses > 60 mas evidência insuficiente | **mid** (teto) |

### Vetos adicionais (pós-ML)

- `experiences_count == 0` → **nunca** `senior`.
- `bullets_count < 6` → **nunca** `senior`.

## 4. Completude e dados insuficientes

- `completeness_score` (0–100) alinha-se à avaliação existente de completude (texto + seções).
- `insufficient_data == true` quando o nível de completude é **insufficient** ou quando não há experiências **e** não há bullets (currículo essencialmente vazio).
- Completude **baixa** limita o **score de qualidade** (ATS/clareza); não deve inflar senioridade.

## 5. Confiança (low / medium / high)

- **high**: várias experiências com datas válidas, tempo bem coberto, poucos `reasons` críticos.
- **medium**: datas parciais ou poucas experiências.
- **low**: `insufficient_data`, ausência de datas, ou veto “sem experiências”; também quando o ML **não** ajusta por baixa confiança (gap softmax).

A UI deve exibir badge **“Baixa confiança”** quando `confidence == low` (i18n).

## 6. ML

### 6.1 signals_ml (preferencial quando habilitado)

- **Habilitação**: `ANALYSIS_SIGNALS_ML_ENABLED=true` e artefato em `ml/models/<ANALYSIS_SIGNALS_ML_SUBDIR>/` (`model.joblib` + `metadata.json`, `task: seniority_signals`).
- **Carregamento**: singleton por processo (`loader_signals_model.py`); não recarregar a cada requisição.
- **Gating**: não roda com `insufficient_data` ou sem experiências estruturadas; exige `completeness_score` e `word_count` mínimos (alinhados ao gating neural por padrão: `ANALYSIS_SIGNALS_ML_MIN_COMPLETENESS`, `ANALYSIS_SIGNALS_ML_MIN_WORDS`).
- **Conservador para `senior`**: só mantém `senior` se `P(senior) ≥ ANALYSIS_SIGNALS_ML_SENIOR_PROB_THRESHOLD` (padrão 0,70) **e** `total_months_experience ≥ 60` **e** `experiences_count ≥ 2` **e** `bullets_count ≥ 6`; caso contrário recua para a melhor classe não-sênior por probabilidade.
- **Estágio / trainee**: com `has_internship_terms`, veto de faixas altas implausíveis (detalhes em `signals_ml_policy.py`).
- **Persistência interna**: `ResumeAnalysis.provider = signals_ml`, `model_version` e `dataset_version` vindos de `metadata.json` (payload público inalterado).
- **Fallback**: se o bundle não carregar ou `predict_proba` falhar, usa-se o fluxo HF + regras (§6.2). Se o bundle carregar mas o caso for ignorado por gating (`skipped_signals_ml:…`), **não** chama-se o HF para senioridade: mantém-se a **classe base estruturada** (regras), evitando “subir” senioridade só com texto frágil.

### 6.2 HF (ajuste fino, quando signals_ml não aplica)

- Só executa se `completeness_score ≥ MIN_COMPLETENESS_FOR_ML` e `word_count ≥ MIN_TOKENS_FOR_ML` (constantes no código).
- Só ajusta se o **gap** entre as duas maiores probabilidades (softmax) ≥ limiar.
- Ajuste **máximo de um nível** em relação à classe base (nunca pula dois degraus).
- Se o ML falhar ou estiver indisponível, mantém-se a classe base (**heurística de texto** em `predictors/seniority.py` é apenas *fallback* quando o bundle neural não roda — não substitui a base estruturada).

## 7. Score geral vs senioridade

- O **score principal** (`score` na API) representa **qualidade do currículo** (ATS, clareza, estrutura, etc.), **não** o nível da pessoa.
- `taskScores.seniority` permanece um valor 0–100 mapeado da **classe final** para compatibilidade.
- `scoreMeaning` no payload opcional: `analysis.scoreMeaning.resume_quality` (chave i18n).

## 8. Privacidade

- Não logar texto completo do currículo; logs estruturados com IDs, scores, classes base/final e duração (ver worker).

## 9. Calibração, dataset, revisão interna e versionamento

### 9.1 Dataset (JSONL v1.0)

- Export: `manage.py export_seniority_dataset` ou `ml/scripts/export_seniority_from_db.py` (detalhes em `ml/labeling/policies.md`).
- Cada linha inclui `analysis_key`, `resume_key`, `user_key` (hash com sal; sem UUIDs cruas), `signals`, `labels`, `targets`, `gating_reasons`, `meta`. Texto do CV só em modo `full` como `text_sanitized` (PII comum mascarada).
- **Validação**: `python ml/training/src/validate_dataset.py --in …` gera `ml/training/reports/dataset_report.md`.
- **Split**: `python ml/training/src/split_dataset.py` particiona por **`resume_key`** (evita vazamento entre treino/val/test). `dataset_version` fica em `split_meta.json`.

### 9.2 Revisão interna (LGPD)

- Endpoints (sem JWT):  
  - `GET /analysis/internal/low-confidence` — lista resumida para triagem.  
  - `GET /analysis/internal/low-confidence/export` — mesmo schema JSONL do dataset (signals-only).  
  - `GET /analysis/internal/metrics/seniority?days=7` — agregados (confiança, top `gatingReasons`).
- Autenticação: header `X-Analysis-Internal-Token` = `ANALYSIS_INTERNAL_REVIEW_SECRET`. Segredo vazio → 403. Com **`DEBUG=False`**, o segredo deve ter comprimento ≥ `ANALYSIS_INTERNAL_SECRET_MIN_LENGTH` (padrão 20); caso contrário → 403 (produção “safe-by-default”).
- Respostas **não** expõem `userId`, `resumeId` nem texto do currículo; usam `userKey`, `resumeKey`, `analysisKey` derivados com `ANALYSIS_INTERNAL_REVIEW_KEY_SALT` (ou fallback controlado).
- Throttle DRF: escopo `analysis_internal` (ex.: 120/hora por IP).
- Cada acesso gera log estruturado (`internal_analysis_review_access`) e registro em `audit_log` (`analysis.internal.*`) **sem** PII.

### 9.3 Modelo e rastreabilidade

- Modelos sklearn **signals** em `ml/models/seniority_signals_v1/` (ou versão incrementada) com `metadata.json` contendo `model_name`, `model_version`, `dataset_version` (split), `features_schema`, `metrics_summary` / métricas de teste após `export_seniority_sklearn_model.py`.
- Pipeline HF existente permanece em `ml/training/src/train.py`; ordem em produção: **signals_ml (se habilitado e carregado) → regras quando gated → HF apenas se signals_ml não aplicável ou erro**.
