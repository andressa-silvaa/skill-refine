# Pipeline gold standard — senioridade (TCC)

Este documento descreve o ciclo defendável academicamente: **policy estruturada → revisão humana (baixa confiança) → dataset v1.1 → treino `signals_ml` → serving com fallback rule-based → evidências e A/B**.

## `policy_version`

- **v1.0** — regras em `backend/src/apps/analysis/application/inference/seniority/rule_based.py`, alinhadas a `docs/analysis/seniority_policy.md`.
- Persistido em `ResumeAnalysis.seniority_policy_version` e replicado no export (`labels.policy_version` / `meta.policy_version`).

## Ground truth

1. **Rule label** — sempre recalculável a partir de `extract_resume_signals` + `rule_based_seniority` (meses efetivos, experiências, bullets, estágio).
2. **Review label** (opcional) — humano via `POST /analysis/internal/review/seniority` ou `manage.py review_seniority_label`.
3. **Final label (ouro)** — `seniority_final_label`: se existe review → review; senão → rule. **Não** usar `payload_json.seniorityClass` legado de HF como rótulo de treino.

## Privacidade

- Export default **signals-only** (sem texto de CV). Texto só com `--mode full` e sanitização (`sanitize_resume_text`).
- Endpoints internos expõem apenas pseudo-chaves (`analysisKey`, …), sem PII.

## Dataset e split

- Schema **1.1**: `ml/data/schema/seniority_dataset_schema_v1_1.json`.
- `validate_dataset.py` exige `seniority_label` não vazio para v1.1.
- `split_dataset.py` particiona por `resume_key` (sem vazamento entre treino/teste).

## Métricas

- `python ml/training/src/eval_seniority.py` → relatório principal: `ml/training/reports/eval_seniority.md` (accuracy, F1 macro, matriz de confusão).
- `python ml/training/src/ab_compare_low_confidence.py` → `ml/training/reports/ab_low_confidence_report.md` (efeito de `signals_ml` + gates em linhas de baixa confiança; “senior fantasma”).

## Serving (backend)

- Preferência: **`signals_ml`** quando bundle válido + thresholds (`ANALYSIS_SIGNALS_*`, `SENIOR_*`).
- Se modelo indisponível ou skipped: **rule policy** (`provider: rule_policy`), não ajuste HF sobre o rótulo.
- Sugestão HF fica apenas como evidência `type: ml_suggestion` (não altera label).

## Dataset pequeno vs dataset grande

- Com **poucas dezenas** de análises `DONE`, métricas de teste e matriz de confusão variam muito de execução para execução; o modelo `signals_ml` ainda não é estatisticamente estável para defesa acadêmica.
- Com **centenas ou milhares** de linhas exportadas (currículos sintéticos sem PII + `batch_run_analysis` controlado), o mesmo pipeline (validate → split → train → eval → A/B) produz **métricas mais estáveis** e um histórico comparável entre corridas.
- **Não invente números no texto do TCC**: use sempre os valores gerados em `ml/training/reports/dataset_evolution.md` (append por execução: N linhas, distribuição por classe, % revisado, `dataset_version`, trechos de métricas/confusão e A/B). Rode o agregador `ml/scripts/run_gold_pipeline_with_seed.py` (ou o checklist manual em `ml/README.md`) para atualizar esse ficheiro após cada ciclo de escala.

## Limitações e próximos passos

- Pseudo-key → análise é busca O(n) em DONE (adequado a volumes de TCC; escalar exigiria índice auxiliar).
- Policy v1.0 é deliberadamente conservadora; revisão humana corrige borda.
- Multi-idioma: sinais estruturados + textos de UI i18n; policy numérica é compartilhada.

## Artefatos reprodutíveis

- `dataset_version` e `model_version` carimbados em `metadata.json` do modelo (`export_seniority_sklearn_model.py`).
- `ResumeAnalysis.dataset_version` / `model_version` por execução de análise.

Ver também checklist em `ml/README.md` (secção **Como rodar do zero — gold pipeline**).
