# Inventário do corte legado — o que cairia se `signals_ml` e `target_fit_ml` não voltarem

> **Status: executado em 2026-08-24.** Este documento passou a ser registro histórico. As duas
> etapas da recomendação foram aplicadas de uma vez, porque a decisão pendente já tinha sido tomada
> nos commits `c538b25` (remove `signals_ml`) e `ba6b5e6` (remove `target_fit_ml`, *no artifact, none
> planned*): `ml/training/` inteiro, `ml/eval/`, `ml/schemas/`, `ml/labeling/` e os 16 scripts do
> cluster v1/v2 não existem mais. O que ficou em `ml/` é o pipeline v3 e os cinco bundles que a
> produção carrega. Os números abaixo são os do levantamento original, preservados como estavam.

Levantamento original, escrito quando nada tinha sido apagado ainda. O objetivo era que a decisão
fosse tomada com o número na mão, porque ela não é técnica: dependia de essas duas famílias voltarem
ou não.

## Por que a pergunta existe

O repositório tem 8.668 linhas de inferência em produção e **11.674 em `ml/scripts`** — os scripts de
medição já são maiores que o sistema. Isso é esperado e é a evidência da defesa. O que não é esperado
é `ml/training`, o pipeline v1/v2, com 5.438 linhas produzindo modelos que **não existem**:

```
analysis_v1_pt               ausente de ml/models/
analysis_quality_v9_pt       ausente
analysis_matching_v3_reg_pt  ausente
seniority_signals_v1         ausente
target_fit_v1                ausente
```

Produção carrega quatro bundles, todos vindos de `ml/scripts/*_v3.py`: `quality_probe_v1`,
`text_seniority_probe_v1`, `bullet_probe_v1`, `insight_gain_v1`, mais `language_detector_v1`.

## O que cairia

### Produção, arquivos inteiros — 524 linhas

| linhas | arquivo |
|---|---|
| 117 | `tasks/target_fit/loader_ml.py` |
| 114 | `loader_signals_model.py` |
| 111 | `tasks/seniority/signals_ml_policy.py` |
| 96 | `tasks/seniority/signals_ml_predict.py` |
| 64 | `management/commands/check_target_fit_ml.py` |
| 22 | `loaders/loader_target_fit_model.py` (shim) |

### Testes, arquivos inteiros — 352 linhas

| linhas | arquivo |
|---|---|
| 202 | `tests/test_signals_ml_loader.py` |
| 150 | `tests/test_target_fit_ml_loader.py` |

### Pipeline v1/v2 — 5.438 linhas

`ml/training/` inteiro: 50 arquivos de código. *(Há também um `.venv` no diretório, fora do git, que
inflava a contagem para ~92k — não é código do projeto.)*

### Scripts alimentadores do v2 — 1.273 linhas

Cluster fechado: só se referenciam entre si, nenhum consumidor no fluxo v3.

| linhas | script |
|---|---|
| 460 | `generate_resumes_v2.py` |
| 297 | `eval_groq_seniority_classifier.py` |
| 147 | `split_by_resume_id.py` |
| 125 | `build_seniority_signals_dataset.py` |
| 114 | `export_text_seniority_baseline.py` |
| 68 | `build_seniority_text_dataset.py` |
| 62 | `relabel_resumes_v2.py` |

### Edições, não remoções — ~90 linhas

`config.py` (33) · `orchestrator.py` (33) · `settings_modules/ai.py` (16) · `docker-compose.yml` (8),
mais uma linha em `test_inference.py` e outra em `test_ai_inference_upgrade.py`.

## Total

**7.587 linhas removidas** e ~90 editadas. Isso é **88% do tamanho da inferência de produção** hoje
(8.668 linhas).

## O que se perde — o argumento honesto do outro lado

Três coisas, e a terceira é a que importa.

1. **`signals_ml` foi superado com número.** Era a abordagem v2 de senioridade sobre 15 features
   numéricas, e foi ela que respondia `intern` com p≈1,0 para todo currículo real (§2). O
   `text_seniority_probe` faz 75,9%. Não há caso para voltar.

2. **O histórico não some do git.** Apagar não perde nada recuperável; a §2 e a §5 do handoff já
   registram o que aquele caminho ensinou.

3. **`target_fit_ml` é andaime de um item que continua no roadmap.** O §7 prevê uma cabeça calibrada
   para `target_fit`, e `ml_feature_row.py` + `ml/training/src/train_target_fit.py` são exatamente a
   estrutura de feature row que ela usaria. **Aqui a decisão não é óbvia** e depende de uma escolha
   de projeto ainda não feita:
   - se a cabeça nova for **sobre o encoder** (como o §7.1 sugere, "100% encoder + cabeça
     calibrada"), o andaime de sinais não serve e pode sair;
   - se for **sobre os sinais** de `TargetFitSignals`, `ml_feature_row.py` fica e `loader_ml.py`
     provavelmente também.

## Contratos que prendem o código de produção ao legado

Estes são os fios que precisam ser cortados junto, e são a razão de não dar para apagar `ml/training`
isoladamente:

- `signals_ml_predict.py:17` — *"Must stay byte-for-byte equivalent to LOG1P_FEATURES in
  ml/training/src/signals_features.py"*
- `ml_feature_row.py:4` — *"Must stay in sync with ml/training/src/train_target_fit.py row builder"*
- `dataset_resume_split.py:4` — *"Used by ml/training/src/split_dataset.py"*

Enquanto `ml/training` existir, esses comentários obrigam quem mexer nas features de produção a
sincronizar um pipeline que não produz nada. Esse é o custo real de manter, e ele é recorrente.

## Efeito colateral a planejar

Remover `target_fit_ml` tira um passo da cascata de `target_fit`, então o `providersByTask` de
alguns casos do golden snapshot muda. A baseline teria de ser regravada **deliberadamente**, com a
verificação de sempre: confirmar que só a integridade mudou e nenhum score se moveu.

## Recomendação

**Cortar em duas etapas, não em uma.**

1. **Agora, sem decisão pendente:** `signals_ml` inteiro (loader, policy, predict, testes) mais os 7
   scripts do v2 e `ml/training/src/signals_features.py` e afins. Superado com número, sem item de
   roadmap dependendo dele. **~1.800 linhas** mais a parte correspondente de `ml/training/src`, risco baixo.

2. **Depois de decidir a forma da cabeça de `target_fit`:** `target_fit_ml`, `ml/training` restante e
   os contratos de sincronia. **~5.790 linhas**, e a decisão precisa vir antes.

O que **não** cai em nenhuma das duas: o código de fallback que continua alcançável — `_heuristic_score`,
`rule_based_seniority`, `domain_keywords`, o léxico. Esses são cobertos pela doutrina declarada
(*fallback deve continuar testado, não continuar servido*) e pelo golden snapshot.
