# `target_fit`: os 35% de policy ajudam?

Gerado 2026-08-14 · 1559 currículos · 3118 pares (um positivo e um negativo por currículo) · sem anotação nova.

Produção publica `fit = 0,65 × embedding + 0,35 × policy`. Os 35% são a última regra dentro de um número publicado, e o peso nunca foi medido. Par positivo é o currículo com o `targetPosition` da própria ocupação; negativo é o de outra ocupação sorteada.

## Discriminação por peso do encoder

| `w_e` | composição | AUC (fit vs não-fit) |
|---|---|---|
| 1.00 | só encoder | **0.981** |
| 0.85 | 85/15 | **0.986** |
| 0.65 | 65/35 ← produção | **0.990** |
| 0.50 | 50/50 | **0.992** |
| 0.35 | 35/65 | **0.993** |
| 0.00 | só policy | **0.970** |

Melhor: **`w_e` = 0.35** com AUC 0.993. Produção hoje (0.990) contra só encoder (0.981).

## O caso realista: alvo adjacente (mesmo grupo ISCO)

Aqui o negativo não é uma ocupação sorteada entre 1.701, é um cargo do **mesmo grupo ISCO de 2 dígitos** — um passo de lado, que é o que um usuário real faz. É esta coluna que separa as configurações; a de cima satura.

| `w_e` | composição | AUC sorteado | **AUC adjacente** |
|---|---|---|---|
| 1.00 | só encoder | 0.981 | **0.946** |
| 0.85 | 85/15 | 0.986 | **0.955** |
| 0.65 | 65/35 ← produção | 0.990 | **0.965** |
| 0.50 | 50/50 | 0.992 | **0.970** |
| 0.35 | 35/65 | 0.993 | **0.969** |
| 0.00 | só policy | 0.970 | **0.924** |

Melhor no caso adjacente: **`w_e` = 0.50** (AUC 0.970), contra 0.965 da produção e 0.946 do encoder sozinho.

## Os dois componentes isolados

| componente | AUC | média no fit | média no não-fit |
|---|---|---|---|
| embedding | 0.981 | 71.5 | 10.6 |
| policy | 0.970 | 41.7 | 10.3 |

No caso adjacente, isolados:

| componente | AUC adjacente | média no fit | média no adjacente |
|---|---|---|---|
| embedding | 0.946 | 71.5 | 22.1 |
| policy | 0.924 | 41.7 | 15.3 |

## `target_seniority`: os clamps reagem ao alvo errado?

Rodando `compute_target_seniority` nos dois pares do mesmo currículo, o rótulo é **idêntico em 182/1559 (12%)** dos casos. Média do rótulo (0=intern, 3=senior): fit 1.90 contra não-fit 1.02.

## Como ler

- **Duas dificuldades, e a segunda é a que informa.** Contra ocupação sorteada tudo satura perto de 0,98 e as configurações não se separam. Contra cargo adjacente do mesmo grupo ISCO — o que um usuário real faz — o vão aparece. Nenhuma das duas é currículo real; a comparação **entre** configurações é o que vale, não o valor absoluto.
- **A mistura ganha dos dois componentes isolados, nas duas dificuldades.** Isso é comportamento de ensemble: o encoder e a policy erram em casos diferentes. Refuta a hipótese de que os 35% fossem heurística inerte dentro de um número neural.
- **Não retune 0,65 com isto.** O ótimo medido é 0,50, e a diferença para produção é 0,005 de AUC em pares construídos. Mover uma constante de produção por esse ganho seria ajustar ao proxy — exatamente o erro que ml/reports/education_alignment_v3.md documenta. O valor desta medição é justificar a mistura, não recalibrá-la.
- **Discriminação, não calibração.** Isto responde se a policy ajuda a separar fit de não-fit. Não responde se 72 é o número certo — para isso continua sendo preciso `reviewed_score` humano.
