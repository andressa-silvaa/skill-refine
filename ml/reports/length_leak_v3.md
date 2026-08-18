# A sonda de senioridade lê comprimento como pista de banda?

Gerado 2026-08-17 · até 80 currículos por banda · `text_seniority_probe_v1`, texto truncado por orçamento de palavras.

## Comprimento por banda no corpus

| banda | n | palavras/currículo (mediana) |
|---|---|---|
| intern | 80 | 166 |
| junior | 80 | 188 |
| mid | 80 | 235 |
| senior | 80 | 230 |

Se essas medianas subissem com a banda, um modelo só-texto pode acertar contando palavras em vez de julgando escopo.

## Acurácia por banda, truncando todos para o mesmo orçamento

| orçamento | intern | junior | mid | senior | média |
|---|---|---|---|---|---|
| sem corte | 85% | 92% | 96% | 98% | **93%** |
| 220 palavras | 81% | 92% | 91% | 95% | **90%** |
| 160 palavras | 80% | 88% | 88% | 95% | **88%** |
| 110 palavras | 85% | 90% | 79% | 89% | **86%** |
| 72 palavras | 84% | 88% | 70% | 92% | **83%** |

A linha `72 palavras` é o comprimento mediano dos currículos escritos à mão que produziram zero senior em produção. Se a coluna `senior` desabar ali, o comprimento era a pista.

## Como ler

- Truncar remove conteúdo junto com comprimento, então parte de qualquer queda é perda de informação legítima. O que denuncia vazamento é a queda ser **desigual entre bandas**: senior e mid perderem muito mais que intern e junior significa que o sinal deles morava no excedente de texto, não no que o texto diz.
- Isto não mede currículo real. Mede se a cabeça sobrevive ao comprimento que currículo real tem.
