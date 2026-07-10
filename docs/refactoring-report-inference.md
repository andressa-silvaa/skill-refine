# Relatório de Refatoração — Pipeline de Inferência de IA (`backend/src/apps/analysis/application/inference`)

**Data:** 2026-07-06
**Autora:** Andressa Silva da Costa
**Escopo:** Cascata de decisão de senioridade, qualidade, matching e target fit (`orchestrator.py` e módulos dependentes)
**Princípio orientador:** nenhuma fase altera um score, label ou evidência de saída para um input já existente. Mudanças de comportamento (remover camadas, trocar pesos, trocar estimator) estão fora deste plano.

---

## 1. Diagnóstico

### 1.1 Estrutura atual

O pipeline é orquestrado por `analyze_resume()` em `orchestrator.py` (~620 linhas), que executa em cascata, para cada uma de quatro tarefas independentes:

| Tarefa | Camadas (da mais simples à mais sofisticada) | Módulos envolvidos |
|---|---|---|
| **Seniority** | regra determinística → sklearn sobre sinais estruturados (`signals_ml`) → BERT (HF) → modelo textual dedicado → fusão ponderada | `seniority/rule_based.py`, `seniority/signals_ml_predict.py`, `seniority/signals_ml_policy.py`, `predictors/seniority.py`, `text_seniority/predict.py`, `text_seniority/fuse_seniority.py` |
| **Quality** | heurística regex → modelo "hybrid" (features + sklearn) → BERT (regressão/classificação ordinal) | `predictors/quality.py` |
| **Matching** | heurística de overlap de palavras → bi-encoder custom → bi-encoder HF genérico | `predictors/matching.py` |
| **Target fit** | sinais/regras → sklearn ML → embeddings (sentence-transformers, blend ponderado) | `target_fit/*.py`, `loaders/loader_target_fit_model.py`, `embeddings/*.py` |

Cada tarefa reimplementa, de forma independente, o mesmo mecanismo conceitual: **tentar o modelo mais sofisticado disponível, capturar falha/indisponibilidade, cair para o próximo nível, registrar proveniência (`provider`/`status`) e evidências**. A forma de registrar isso, porém, difui entre tarefas (tuplas `(label, confidence, probs, evidence, status)` em seniority; `(score, flags)` em quality; `(score, top_matches)` em matching; dicionários ad-hoc em target fit).

### 1.2 Testes existentes

Já existe suíte cobrindo partes do pipeline (`backend/src/apps/analysis/tests/`):
`test_inference.py`, `test_ai_inference_upgrade.py`, `test_seniority_structural.py`, `test_signals_ml_loader.py`, `test_target_fit.py`, `test_target_fit_ml_loader.py`, `test_analysis_api.py`, entre outros. `test_inference.py` já importa e exercita `analyze_resume` diretamente, com fixtures de currículo reutilizáveis — bom ponto de partida para o golden dataset, mas hoje não há um snapshot end-to-end que trave o output completo do orquestrador.

### 1.3 Riscos identificados (sem julgar se devem ser corrigidos agora)

1. **Complexidade acumulada na fusão de seniority** — é a cascata com mais camadas (5) e a única com um passo de "fusão" explícito (`fuse_seniority`), tornando difícil rastrear qual camada produziu o label final sem inspecionar `seniority_evidence`.
2. **Duplicação do padrão cascade/fallback** — a lógica de "tentar modelo → excecão → próximo nível" está reimplementada 4 vezes com formatos de retorno distintos, o que aumenta o custo de manutenção e o risco de inconsistência ao adicionar uma nova tarefa.
3. **Mistura de responsabilidades no orquestrador** — cálculo de score, montagem de metadata (`model_metadata_by_task`), e montagem de bloco de debug (`debug_block`) convivem na mesma função longa.
4. **Ausência de rede de regressão automatizada para o pipeline completo** — os testes atuais validam funções isoladas ou casos pontuais, mas não há um comparador de snapshot que garanta que uma refatoração não mudou nenhum campo de saída para um conjunto amplo e representativo de currículos.
5. **Múltiplas versões de modelo convivendo** (`analysis_quality_v1..v9_pt`, `analysis_seniority_multi_v1/v2_light`) sem uma marcação clara de "versão vigente" — não é um problema de código, mas dificulta saber quais caminhos da cascata são de fato exercitados em produção.

---

## 2. Plano de refatoração (sem regressão lógica)

### Fase 0 — Rede de segurança (pré-requisito)

1. **Golden dataset**: 30–50 currículos cobrindo os pontos de ramificação da cascata — `insufficient_data`, thin profile (estagiário), com/sem `job_description_text`, com/sem `targetPosition`, PT/EN/ES, cada faixa de senioridade. Base: fixtures já existentes em `test_inference.py`/`test_target_fit.py`, complementado por `ml/scripts/generate_synthetic_resumes.py` se necessário.
2. **Snapshot runner**: script que executa `analyze_resume()` para cada item e serializa a saída completa (`score`, `task_scores`, `seniority_*`, `payload_json`) em JSON.
3. **Comparador**: comando que roda o snapshot atual, faz diff campo-a-campo contra o baseline congelado e falha em qualquer divergência — incluindo `seniorityEvidence`, `insights`, `model_metadata_by_task`, não só os scores numéricos.
4. Congelar o baseline **antes** de qualquer alteração de código de produção.

**Critério de saída:** o comparador roda limpo contra o HEAD atual e falha de propósito quando um score é alterado manualmente em um teste de sanidade.

### Fase 1 — Extração estrutural no `orchestrator.py` (sem tocar lógica de decisão)

Extrair blocos sequenciais de `analyze_resume()` em funções privadas por etapa (`_resolve_seniority`, `_resolve_target_fit`, `_resolve_quality_and_matching`, `_build_debug_block`), preservando exatamente variáveis, ordem de chamadas e condições — apenas corte-e-cola nomeado. Validar com testes + comparador de snapshot após cada extração.

### Fase 2 — Consolidar o padrão repetido de cascade/fallback

Introduzir um tipo comum (`CascadeResult(value, provider, status, evidence)`) e uma função `run_cascade(steps)` que tenta cada etapa em ordem e para no primeiro sucesso, **sem alterar a ordem real de nenhuma cascata específica** — apenas canonizando o mecanismo. Migrar uma tarefa por vez, começando pela mais simples (`matching`) antes da mais entrelaçada (`seniority`). Comparar snapshot isoladamente após cada tarefa migrada.

### Fase 3 — Separar decisão de telemetria/debug

Mover a montagem de `debug_block`, `model_metadata_by_task` e `payload_body` para funções puras que recebem resultados já calculados, sem recalcular nada. Só deve ocorrer após Fases 1–2 estabilizarem, para evitar diffs difíceis de revisar sobre uma base ainda em movimento.

### Fase 4 — Reorganização de pastas por tarefa

Agrupar por tarefa (`inference/tasks/seniority/`, `inference/tasks/quality/`, `inference/tasks/target_fit/`) em vez do atual mix de `predictors/`, `seniority/`, `target_fit/`, `text_seniority/` como pastas paralelas. Executar via `git mv` (preserva histórico) em commit isolado, sem lógica alterada no mesmo commit.

### Fora de escopo (mudança de comportamento, não refatoração)

- Reduzir/remover camadas de fallback (ex.: descontinuar `signals_ml`).
- Trocar ou adicionar estimator (ex.: introduzir Naive Bayes).
- Alterar pesos de fusão (`overall_w_quality`, `overall_w_seniority`, `overall_w_target_fit`) ou thresholds de gate (`SENIOR_PROB_THRESHOLD` etc.).

---

## 3. Sequenciamento recomendado

```
Fase 0 (golden dataset + comparador)
   ↓
Fase 1 (extração de funções no orchestrator)
   ↓
Fase 2 (cascade helper — matching → quality → target_fit → seniority)
   ↓
Fase 3 (separar telemetria/debug)
   ↓
Fase 4 (reorganização de pastas)
```

Cada fase só avança após: testes existentes verdes + comparador de golden snapshot sem divergência.
