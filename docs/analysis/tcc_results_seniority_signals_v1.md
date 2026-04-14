# Resultados TCC — senioridade `signals_ml` (v1)

Documento **curto** para defesa: robustez da estimativa de senioridade com modelo leve em cima de *signals* estruturados, sem PII, sem mudança de contrato público da API.

> Preencha os campos entre colchetes após rodar `python ml/scripts/run_seniority_pipeline.py` (e opcionalmente `--with-tuning`). Os valores abaixo são *placeholders* até a execução em dados reais.

## 1. Objetivo

- Reduzir classificações **absurdas** (ex.: “sênior” com currículo vazio ou sem evidência estruturada).
- Priorizar **precisão em “senior”** (melhor subestimar do que superestimar).
- Manter **LGPD**: dataset exportado só com chaves hash (`resume_key`, etc.), sem texto identificável nos modos padrão.

## 2. Dataset

| Campo | Valor |
|--------|--------|
| **dataset_version** | `[colar de ml/data/splits/seniority_latest/split_meta.json]` |
| **Export** | `since=[ex.: 90d]`, `limit=[ex.: 5000]` (ver comando no `ml/scripts/run_seniority_pipeline.py`) |
| **Split** | Determinístico por `resume_key`, seed 42 (`split_dataset.py`) |
| **Tamanho / distribuição** | Ver `ml/training/reports/seniority_signals_v1_summary.md` e `dataset_report.md` |

Se o resumo automático sinalizar **desbalanceamento forte**, ajustar antes de thresholds: ampliar `--since` / `--limit` ou revisar política de rótulos.

## 3. Métricas do modelo (held-out test)

Fonte: `ml/training/reports/eval_seniority.md` (ou legado `seniority_signals_v1_eval.md`) + `ml/models/seniority_signals_v1/test_metrics.json`.

| Métrica | Valor |
|---------|--------|
| **Accuracy** | `[ ]` |
| **F1 macro** | `[ ]` |
| **Confusões críticas** (mid↔senior, junior↔mid, intern↔junior) | Ver seção *High-risk confusions* no eval |

## 4. A/B em baixa confiança

Fonte: `ml/training/reports/ab_low_confidence_seniority_signals_v1.md` (gerado após `export_low_confidence_cases` + `ab_compare_low_confidence.py`).

- **% `senior` antes (regras)** vs **depois (`signals_ml`)**: ver relatório.
- **“Senior fantasma”** (senior sem meses/exp/bullets mínimos): contagem antes/depois no relatório.

Comando sugerido (raiz do repo):

```bash
cd backend && python manage.py export_low_confidence_cases --out ../ml/data/processed/low_confidence.jsonl --limit 1000 && cd ..
python ml/training/src/ab_compare_low_confidence.py \
  --in_jsonl ml/data/processed/low_confidence.jsonl \
  --model_dir ml/models/seniority_signals_v1 \
  --out ml/training/reports/ab_low_confidence_seniority_signals_v1.md \
  --thresholds_json ml/training/reports/threshold_recommended.json
```

(O último flag é opcional, se tiver rodado `tune_thresholds.py` / `--with-tuning`.)

## 5. Thresholds finais e justificativa

Fontes: `ml/training/reports/threshold_tuning.md` (grid leve), `backend/src/config/settings_modules/ai.py` (env).

| Parâmetro (env) | Valor escolhido | Justificativa (1 frase) |
|-----------------|-----------------|-------------------------|
| `SENIOR_PROB_THRESHOLD` / `ANALYSIS_SIGNALS_ML_SENIOR_PROB_THRESHOLD` | `[ ]` | `[ ]` |
| `SENIOR_MIN_MONTHS` / `ANALYSIS_SIGNALS_ML_SENIOR_MIN_TOTAL_MONTHS` | `[ ]` | `[ ]` |
| `SENIOR_MIN_EXPERIENCES` | `[ ]` | `[ ]` |
| `SENIOR_MIN_BULLETS` | `[ ]` | `[ ]` |

**Regra de produto**: thresholds calibrados para **cair “senior fantasma”** sem destruir recall de sêniores com evidência (ver tuning + A/B).

## 6. Produção (feature flag)

- `ANALYSIS_SIGNALS_ML_ENABLED=true`
- `ANALYSIS_MODEL_ROOT` = caminho absoluto para `ml/models` **ou** `ANALYSIS_SIGNALS_MODEL_DIR` = caminho absoluto para `.../seniority_signals_v1`
- `ANALYSIS_SIGNALS_THRESHOLDS_FROM_SETTINGS=true` para ler limites do `.env` (recomendado após tuning)

**Persistência** (sem mudar payload público): em `ResumeAnalysis`, campos `provider`, `model_version`, `dataset_version` devem refletir o artefato (`signals_ml` + `metadata.json`). Confirme com uma análise pela UI ou shell Django.

## 7. LGPD

- Export default **signals-only**; chaves pseudoanonimizadas com salt configurável.
- Logs e relatórios sem texto livre de CV nem PII; amostras A/B: apenas `resume_key` hash + sinais numéricos/flags.

## 8. Checklist “pronto para TCC”

- [ ] Pipeline one-shot executado em dados reais.
- [ ] `dataset_report.md`, `split_meta.json`, `seniority_signals_v1_eval.md`, `metadata.json` atualizados.
- [ ] `seniority_signals_v1_summary.md` gerado.
- [ ] A/B low-confidence com queda de “senior fantasma”.
- [ ] Thresholds alinhados ao tuning + env documentado.
- [ ] `signals_ml` ativo por flag; versões persistidas no banco.
- [ ] Endpoints públicos `/analysis/run`, `/analysis/latest`, `/analysis/history` inalterados em contrato.
