# Completeness caps — are they justified?

Generated 2026-08-14 · 1559 resumes · quality head `quality_probe_v1`, confidence = max class probability.

**This corpus contains no resume that reads `insufficient`, so the cap of 40 is unmeasurable here.** Everything below concerns `low` (cap 72) and the thin-profile rule (cap 58).

## Por nível de completude

| grupo | n | confiança média | acurácia vs `quality_target` | n rotulado | cap | cap morde | score médio |
|---|---|---|---|---|---|---|---|
| adequate | 1505 | 0.683 | 93.0% | 675 | 100 | 0 (0%) | 60.7 |
| low | 54 | 0.669 | 87.5% | 16 | 72 | 18 (33%) | 58.0 |

## Regra de perfil raso

| grupo | n | confiança média | acurácia vs `quality_target` | n rotulado | cap | cap morde | score médio |
|---|---|---|---|---|---|---|---|
| thin | 50 | 0.674 | 85.7% | 14 | 58 | 18 (36%) | 58.8 |
| not thin | 1509 | 0.683 | 93.1% | 677 | 100 | 0 (0%) | 60.7 |

## A pergunta que decide a abstenção: a incerteza separa acerto de erro?

Abstenção calibrada só funciona se alguma medida de incerteza ordenar os acertos acima dos erros. Isso é testável em todos os currículos rotulados de uma vez, sem depender dos 16 de `low`. AUC 0,50 = a medida não sabe nada; 1,00 = separa perfeitamente.

n = 691 rotulados · 642 acertos, 49 erros

| medida de incerteza | AUC (acerto vs erro) | média no acerto | média no erro |
|---|---|---|---|
| confiança (prob. máx.) | **0.872** | 0.759 | 0.548 |
| margem top-1 menos top-2 | **0.880** | 0.575 | 0.191 |
| entropia (invertida) | **0.805** | 0.610 | 0.863 |

## Curva risco-cobertura pela margem

Abstendo dos currículos de menor margem, quanto sobe a acurácia no resto? A coluna `abstém` é a fração da base que deixaria de receber um número afirmado com confiança. É esta tabela, e não um valor escolhido a dedo, que fixa o ponto de operação.

| abstém | corte de margem | n respondido | acurácia no respondido | erros restantes |
|---|---|---|---|---|
| 0% | 0.000 | 691 | **92.9%** | 49 |
| 5% | 0.073 | 656 | **94.7%** | 35 |
| 10% | 0.158 | 622 | **96.5%** | 22 |
| 15% | 0.223 | 587 | **97.4%** | 15 |
| 20% | 0.283 | 553 | **97.8%** | 12 |
| 30% | 0.391 | 484 | **98.8%** | 6 |

## O que o cap destrói quando morde

3 currículos rotulados têm o score cortado por um cap. Nesses, a predição da sonda estava **certa em 2 (67%)**: o corte não está removendo um erro do modelo, está removendo a resposta dele.

