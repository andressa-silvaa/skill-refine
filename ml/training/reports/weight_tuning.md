# Weight tuning (recomendação automática)

Critério: maximizar variância do overall simulado, penalizar violações nos cenários controlados e saturação em [82,88].

## Top combinações (wq, ws, wt, embed_w | variance | penalties | score)

- wq=0.84 ws=0.10 wt=0.06 embed=0.75 | var=138.59 | pen=36.00 | **score=16594.78**
- wq=0.84 ws=0.10 wt=0.06 embed=0.65 | var=136.06 | pen=36.00 | **score=16291.50**
- wq=0.84 ws=0.10 wt=0.06 embed=0.45 | var=134.48 | pen=36.00 | **score=16102.12**
- wq=0.84 ws=0.10 wt=0.06 embed=0.55 | var=134.21 | pen=36.00 | **score=16069.78**
- wq=0.80 ws=0.15 wt=0.05 embed=0.65 | var=129.40 | pen=36.00 | **score=15492.28**
- wq=0.78 ws=0.12 wt=0.10 embed=0.75 | var=129.38 | pen=36.00 | **score=15489.00**
- wq=0.80 ws=0.15 wt=0.05 embed=0.55 | var=128.84 | pen=36.00 | **score=15424.78**
- wq=0.80 ws=0.15 wt=0.05 embed=0.75 | var=128.31 | pen=36.00 | **score=15361.50**
- wq=0.78 ws=0.12 wt=0.10 embed=0.65 | var=127.87 | pen=36.00 | **score=15308.53**
- wq=0.78 ws=0.12 wt=0.10 embed=0.55 | var=127.62 | pen=36.00 | **score=15278.53**
- wq=0.75 ws=0.13 wt=0.12 embed=0.65 | var=127.25 | pen=36.00 | **score=15233.53**
- wq=0.72 ws=0.14 wt=0.14 embed=0.75 | var=127.09 | pen=36.00 | **score=15214.78**

## Melhor candidato

- `ANALYSIS_OVERALL_WEIGHT_QUALITY=0.8400`
- `ANALYSIS_OVERALL_WEIGHT_SENIORITY=0.1000`
- `ANALYSIS_OVERALL_WEIGHT_TARGET_FIT=0.0600`
- `ANALYSIS_TARGET_FIT_EMBED_WEIGHT=0.7500`

_Variância overall simulado: 138.59; penalidades: 36.00_

> **Não aplicar automaticamente.** Copie variáveis para o `.env` apenas após revisão humana.
