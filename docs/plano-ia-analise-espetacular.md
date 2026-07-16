# Plano — Análise de Currículos com IA de Verdade (heurística apenas como último recurso)

**Data:** 2026-07-16
**Escopo:** as 4 tarefas do pipeline de inferência (`seniority`, `quality`, `matching`, `target_fit`) em `backend/src/apps/analysis/application/inference/`
**Objetivo:** cada tarefa decidida por modelo treinado e validado contra rótulos humanos; heurística usada somente quando o modelo estiver indisponível ou o input for insuficiente.

---

## 0. Estado atual (diagnóstico consolidado)

O que já está pronto e funciona a nosso favor:

| Peça | Estado |
|---|---|
| Código de inferência em cascata (`run_cascade`, 4 tarefas) | ✅ Refatorado (Fases 0–4 concluídas em 2026-07-16) |
| Rede de segurança (golden snapshot, 32 casos + comparador) | ✅ `python manage.py compare_inference_snapshots` |
| Bug de inflação de senioridade (`effective_months_experience` via regex "N anos") | ✅ Corrigido + veto simétrico em `clamp_seniority_vetoes` |
| Loaders prontos para modelos reais (HF, hybrid pkl, bi-encoder, sklearn, embeddings) | ✅ `inference/loader.py`, `loader_signals_model.py`, `tasks/target_fit/loader_ml.py` |
| Infra de revisão humana (endpoint + management commands + campos no banco) | ✅ Pronta, **nunca usada com dados reais** |
| Scripts de treino (`ml/training/src/`, `ml/scripts/`) | ✅ Existem e rodaram no passado |

O que bloqueia "IA espetacular" hoje:

1. **Nenhum modelo utilizável em `ml/models/`** — só existe `text_seniority_v1/model.safetensors` **incompleto** (sem `config.json`, tokenizer ou `metadata.json`; não carrega).
2. **Rótulos de treino circulares** — `label_with_heuristics.py` usa como "ground truth" a keyword inserida pelo próprio gerador sintético ou a saída da heurística atual. O accuracy de 100% em `analysis_seniority_multi_v2_light` é vazamento de sinal trivial, não qualidade.
3. **Zero exemplos revisados por humano** — `for_review.csv` tem 200 linhas exportadas, 0 revisadas; nenhum gold CSV existe no repo nem no histórico git.
4. **Todos os flags de IA desligados por padrão** — `ANALYSIS_SIGNALS_ML_ENABLED`, `ANALYSIS_TEXT_SENIORITY_ENABLED`, `ANALYSIS_EMBEDDINGS_ENABLED`, `ANALYSIS_TARGET_FIT_ML_ENABLED` são todos `False` em `backend/src/config/settings_modules/ai.py`.
5. **Datasets de treino não versionados** — `ml/data/*.jsonl` referenciados pelos configs de treino não existem; os números reportados em `ml/training/reports/` não são reproduzíveis hoje.

**Consequência da ordem:** treinar modelo antes de resolver (2) e (3) apenas replica a heurística com custo maior. Por isso o plano começa por dados.

---

## Princípios do plano

1. **Gold humano é a fonte de verdade** — todo modelo é treinado e/ou avaliado contra rótulos de julgamento humano sobre currículos reais, nunca contra a heurística.
2. **Heurística vira fallback explícito** — permanece na cascata (`run_cascade`) apenas como último degrau, com `provider` registrado, para o caso de modelo indisponível/input insuficiente.
3. **Nada entra em produção sem bater a heurística no gold** — critério de aceite objetivo por tarefa (seção 5).
4. **Ciclo incremental** — revisar → treinar → avaliar → promover → repetir. Nenhuma fase "big bang".

---

## Fase A — Construir o gold dataset humano (bloqueia todo o resto)

### A.1 Seniority (prioridade máxima — é onde o usuário viu o erro)

```powershell
cd backend
# Exporta candidatos priorizados (career switch +200, domínios divergentes +150, scores intermediários +60/80)
python manage.py export_gold_review_candidates --user-email <email> --limit 100 --out ..\ml\data\processed\gold_review_candidates_ptbr.csv
```

Revisão humana do CSV (delimitador `;`, `utf-8-sig`):
- Preencher `review_seniority_label` (`intern|junior|mid|senior`), opcionalmente `review_target_fit_score` (0–100) e `review_note`.
- **Não olhar a coluna `seniority_final_label`** (predição da heurística) antes de decidir — evita ancoragem.
- **Segundo revisor independente em ≥30 casos em comum** para medir concordância inter-anotador (kappa). Essa concordância é o teto realista de qualquer modelo.
- Meta de volume: **≥50 exemplos revisados por classe** (200 no total) antes da primeira avaliação séria; **≥150/classe** (600 total) antes de treinar modelo textual.

Aplicar de volta ao banco (rota que **não** sobrescreve a predição — mantém a comparação válida):

```powershell
python manage.py apply_target_fit_reviews_from_csv --csv ..\ml\data\processed\gold_review_candidates_ptbr.csv
```

> ⚠️ Não usar `review_seniority_label --analysis-key ...` para fins de dataset: esse comando sobrescreve `seniority_final_label` com o rótulo humano, o que invalida a avaliação (predição == gold trivialmente). Ele serve para corrigir casos individuais de produção, não para montar gold.

### A.2 Quality, Matching e Target Fit

- **Quality:** adicionar coluna `review_quality_score` (0–100) no fluxo de export/review (exige pequena extensão de `export_gold_review_candidates` e `apply_target_fit_reviews_from_csv` — ambos já têm o padrão pronto para replicar). Rubrica de revisão sugerida: completude (0–30), especificidade/métricas nos bullets (0–40), clareza/estrutura (0–30).
- **Target fit:** já suportado (`review_target_fit_score` → `payload_json.targetFitGoldScore`).
- **Matching:** exige pares (currículo, vaga) reais. Coletar via `ml/scripts/collect_jobs.py` + amostra de análises com `job_description_text` preenchido; revisor atribui score 0–100 de aderência. Volume inicial menor é aceitável (matching é a tarefa com menos uso).

### A.3 Governança do dataset

- Versionar os gold CSVs revisados em `ml/data/gold/` **no git** (dados sem PII — o export já usa pseudo-keys e o pipeline de anonimização existe em `ml/scripts/anonymize_resumes.py`).
- Cada rodada de revisão gera `gold_vN.csv` — nunca sobrescrever rodada anterior.
- Registrar em `ml/data/gold/README.md`: quem revisou, quando, critério usado, kappa medido.

**Critério de saída da Fase A:** ≥200 rótulos humanos de seniority (≥50/classe), kappa inter-anotador medido e documentado, gold versionado.

---

## Fase B — Medir a baseline real (heurística corrigida vs. gold)

Antes de treinar qualquer coisa, saber o número que precisa ser batido:

```powershell
$env:PYTHONPATH="backend\src"
$env:DJANGO_SETTINGS_MODULE="config.settings"
python ml/training/src/eval_against_gold.py --user-email <email> --out ml/training/reports/gold_eval_baseline.md
```

Melhorias de tooling necessárias (pequenas, ~1 dia):

1. **Matriz de confusão por classe** no `eval_against_gold.py` (hoje só acurácia agregada) — sem isso não se sabe se o erro está em "intern vs junior" ou "mid vs senior".
2. **Acurácia adjacente** (erro de 1 nível vs. 2+ níveis) — errar "junior→mid" é muito menos grave que "intern→senior".
3. Persistir o relatório por versão (`gold_eval_<data>_<pipeline-version>.md`) para acompanhar evolução.

**Critério de saída da Fase B:** relatório baseline com acurácia por classe da heurística corrigida. Esse número é o mínimo que qualquer modelo precisa superar para ser promovido.

---

## Fase C — Treinar os modelos por tarefa (ordem de prioridade)

### C.1 Seniority — `signals_ml` (sklearn sobre sinais estruturados) — *primeira entrega*

- **Por quê primeiro:** features já extraídas (`ResumeSignals`), treino barato (minutos), pipeline `ml/training/src/` pronto, e a tarefa depende majoritariamente de sinais estruturados (meses reais, nº de experiências, bullets) que agora estão corretos pós-fix.
- **Dados:** gold da Fase A como treino+validação (split por `resume_id`, nunca por linha — `ml/scripts/split_by_resume_id.py` já existe). **Não usar** os sintéticos rotulados por keyword; se precisar de volume, sintéticos entram apenas como pré-treino, com fine-tune e avaliação exclusivamente no gold.
- **Artefato de saída:** `ml/models/seniority_signals_v2/` no formato que `loader_signals_model.py` espera (modelo + `metadata.json` com `inference_thresholds`).
- **Ativação:** `ANALYSIS_SIGNALS_ML_ENABLED=true` + `ANALYSIS_SIGNALS_ML_SUBDIR=seniority_signals_v2`.
- Os vetos (`clamp_seniority_vetoes`, gates de `signals_ml_policy.py`) permanecem — são salvaguardas de sanidade, não heurística de decisão.

### C.2 Seniority — modelo textual (fine-tune de encoder pt-BR) — *segunda entrega*

- **Base:** BERTimbau (`neuralmind/bert-base-portuguese-cased`) ou DeBERTa-v3 multilíngue; o pipeline `ml/scripts/run_seniority_pipeline.py` + `ml/training/` já treina esse formato.
- **Consertar o artefato atual:** `ml/models/text_seniority_v1/` tem só `model.safetensors` — retreinar/exportar completo (`config.json`, `tokenizer.json`, `metadata.json` com `task: text_seniority`), no formato que `tasks/seniority/text/loader_text_seniority_model.py` espera.
- **Dados:** gold textual (o texto sanitizado do currículo + rótulo humano). Com <600 exemplos, usar validação cruzada e regularização forte; expandir gold antes de confiar no número.
- **Ativação:** `ANALYSIS_TEXT_SENIORITY_ENABLED=true` (a fusão `fuse_seniority` já está pronta e é bem desenhada — passa a fundir modelo real em vez do fallback léxico).
- **Ajuste recomendado na fusão:** remover do fallback léxico (`_MID_PATTERNS` em `tasks/seniority/text/predict.py`) o padrão genérico `\b3\s*anos\b` — mesmo como fallback, esse padrão reproduz o bug corrigido no estrutural.

### C.3 Quality — modelo hybrid (features + sklearn) retreinado com gold

- Retreinar `analysis_quality_hybrid` com os `review_quality_score` humanos (o report atual `hybrid_v2` teve 0 acerto na classe "poor" — inaceitável; a classe mais importante para o produto é justamente detectar currículo fraco).
- **Artefato:** `ml/models/analysis_quality_v10_pt/hybrid/model.pkl` + `metadata.json` (`task: quality`) — formato que `loader.get_quality_bundle` espera.
- **Ativação:** `ANALYSIS_MODEL_VERSION_BY_TASK="quality=analysis_quality_v10_pt"`.

### C.4 Target fit — sklearn + embeddings

- Treinar `target_fit_v1` (sklearn sobre `target_fit_feature_row`) com `targetFitGoldScore` humanos; script `ml/training/src/train_target_fit.py` pronto.
- **Artefato:** `ml/models/target_fit_v1/` no formato de `tasks/target_fit/loader_ml.py` (model + scaler + `feature_names`).
- Ligar embeddings semânticos: `ANALYSIS_EMBEDDINGS_ENABLED=true` (usa sentence-transformers MiniLM; `tasks/target_fit/loader_embeddings.py` pronto). O blend ponderado (`ANALYSIS_TARGET_FIT_EMBED_WEIGHT`, default 0.65) já existe — calibrar o peso contra o gold (grid search simples no `eval_against_gold`).
- **Ativação:** `ANALYSIS_TARGET_FIT_ML_ENABLED=true`.

### C.5 Matching — bi-encoder

- Menor prioridade (menos volume de uso, gold mais caro de montar). Enquanto isso, o embedding genérico HF (`get_matching_bundle` já suporta) é melhor que o overlap de palavras atual — pode ser ativado apontando `ANALYSIS_MODEL_VERSION_BY_TASK="matching=<versão-com-encoder>"` com um encoder pt-BR baixado, sem treino próprio, como passo intermediário.

### C.6 (Opcional) Camada LLM para insights e explicações

- **Não** usar LLM como decisor de score/label (classificação fechada com sinais estruturados fortes → modelo supervisionado local vence em precisão, custo, latência e não alucina).
- **Usar** LLM (Claude via API) para o que ele é melhor: gerar `insights`/`recommendations` em linguagem natural rica a partir do resultado estrutural já decidido (hoje `postprocess/insights.py` é template-based). Prompt deve receber os labels/scores decididos pelos modelos + evidências, com instrução explícita de nunca re-inferir senioridade do texto.
- Entra na cascata como provider `llm_insights` com fallback para os templates atuais.

---

## Fase D — Wiring de produção

### D.1 Configuração final (env / `backend/env.example`)

```env
ANALYSIS_MODEL_MODE=hf
ANALYSIS_ALLOW_HEURISTICS_FALLBACK=true          # heurística permanece como último degrau
ANALYSIS_SIGNALS_ML_ENABLED=true
ANALYSIS_SIGNALS_ML_SUBDIR=seniority_signals_v2
ANALYSIS_TEXT_SENIORITY_ENABLED=true
ANALYSIS_TEXT_SENIORITY_FUSION_ENABLED=true
ANALYSIS_EMBEDDINGS_ENABLED=true
ANALYSIS_TARGET_FIT_ML_ENABLED=true
ANALYSIS_TARGET_FIT_ML_SUBDIR=target_fit_v1
ANALYSIS_MODEL_VERSION_BY_TASK=seniority=<versão>;quality=analysis_quality_v10_pt;matching=<versão>
```

### D.2 Deploy de artefatos

- `ml/models/` está no `.gitignore` — definir mecanismo de distribuição (storage/artefato de release/download no deploy). Documentar em `ml/models/README.md` o layout esperado por tarefa (hf/, hybrid/, matching/, metadata.json).
- `warmup.py` já existe — garantir que o warmup carrega todos os bundles no boot para não pagar cold-start na primeira análise.

### D.3 Observabilidade do fallback

- O `provider` por tarefa já é persistido (`model_metadata_by_task`). Adicionar métrica/alerta: **% de análises decididas por `heuristics-only`/`rule_policy`** por dia. Meta: <5% (apenas inputs insuficientes). Se subir, é sinal de modelo caindo em erro silenciosamente.

---

## Fase E — Validação, promoção e ciclo contínuo

### E.1 Critérios de aceite por tarefa (gate de promoção)

| Tarefa | Métrica no gold humano | Critério para ligar o flag em produção |
|---|---|---|
| Seniority | acurácia exata + adjacente por classe | ≥ baseline heurística corrigida **e** zero casos "intern real → mid/senior" no gold |
| Quality | MAE vs. `review_quality_score` | MAE ≤ baseline **e** recall da classe "poor" ≥ 0.7 |
| Target fit | MAE/RMSE vs. `targetFitGoldScore` | MAE ≤ baseline; zero "absurdos" (career switch + score>70 sem evidência) |
| Matching | correlação com score humano | ≥ baseline overlap de palavras |

### E.2 Processo de promoção de cada modelo

1. Treinar → avaliar no gold (holdout por `resume_id`) → relatório versionado em `ml/training/reports/`.
2. Ligar o flag em ambiente de staging/dev → rodar `compare_inference_snapshots` (**divergência esperada** — mudança de comportamento intencional) → revisar os diffs caso a caso → re-congelar baseline com `--write-baseline`.
3. Ligar em produção → monitorar % de fallback e reclamações → manter flag como kill-switch (desligar volta à heurística instantaneamente, a cascata garante isso).

### E.3 Ciclo contínuo (o que torna "espetacular" sustentável)

- **Mensal:** exportar novos candidatos de review (o `score_row` prioriza os casos onde o modelo mais provavelmente errou), revisar 50–100, acumular no gold.
- **A cada N rodadas:** retreinar com gold ampliado, reavaliar, promover se superar a versão vigente.
- **Sempre:** cada correção manual de produção via `review_seniority_label` vira exemplo de treino futuro automaticamente (o campo `seniority_review_label` fica no banco).

---

## Ordem de execução e esforço estimado

| # | Entrega | Depende de | Esforço |
|---|---|---|---|
| 1 | Validar refatoração + fix atual (rodar testes e `compare_inference_snapshots`, re-congelar baseline) | ambiente Python funcional | 0,5 dia |
| 2 | Fase A.1 — gold de seniority (export + revisão de 100–200 casos) | 1 | 1–3 dias (maior parte é revisão humana) |
| 3 | Fase B — baseline + matriz de confusão no `eval_against_gold.py` | 2 | 1 dia |
| 4 | C.1 — `signals_ml` v2 treinado no gold + ativado | 3 | 1–2 dias |
| 5 | C.2 — modelo textual pt-BR completo + fusão ativada | 3 (gold ≥600 idealmente) | 2–4 dias |
| 6 | A.2 + C.3 — gold de quality + hybrid v10 | 2 | 2–3 dias |
| 7 | C.4 — target fit ML + embeddings calibrados | 2 | 1–2 dias |
| 8 | D — wiring, deploy de artefatos, observabilidade de fallback | 4–7 | 1–2 dias |
| 9 | C.5/C.6 — matching bi-encoder, LLM insights | 8 | opcional / contínuo |

**Caminho crítico:** 1 → 2 → 3 → 4. Com isso (≈1 semana, sendo revisão humana o gargalo), a decisão de senioridade já passa a ser modelo-primeiro validado em gold humano — exatamente o caso que motivou este plano.

---

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Revisão humana não acontecer (gargalo histórico — 0/200 revisadas até hoje) | Reduzir fricção: lote pequeno inicial (50), planilha simples, sessões de 1h; sem gold, **nada** do resto do plano vale a pena — tratar como pré-requisito duro |
| Gold pequeno → modelo textual overfitta | signals_ml primeiro (poucos parâmetros); textual só com ≥600 exemplos; validação cruzada sempre |
| Concordância inter-anotador baixa (<0.6 kappa) | Refinar rubrica de senioridade antes de treinar — se humanos discordam, o problema é de definição, não de modelo |
| Modelo pior que heurística corrigida no gold | O gate da Fase E impede promoção; heurística corrigida permanece — já é melhor que o estado pré-fix |
| Artefatos não versionados se perderem de novo | `ml/data/gold/` no git; artefatos de modelo com mecanismo de distribuição documentado |
