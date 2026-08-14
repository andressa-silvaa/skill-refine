# Detector de idioma do currículo — v3

Gerado 2026-08-14 · 1559 currículos · TF-IDF de n-gramas de caractere (1-3, `char_wb`) + regressão logística · 5-fold GroupKFold pela ocupação.

Substitui `UserPreferences.language`, que é a preferência de **interface** do usuário e nunca olha o documento. Custo medido de errar: recuperação de ocupação cai 29,5 pontos e domínio cai 14,9 (ml/reports/language_mismatch_v3.md).

## Held-out por ocupação: **100.00%**

| idioma real \ predito | pt | en | es | n |
|---|---|---|---|---|
| pt | 738 | 0 | 0 | 738 |
| en | 0 | 407 | 0 | 407 |
| es | 0 | 0 | 414 | 414 |

## Distribuição de confiança no held-out

O piso de confiança abaixo do qual a inferência **não** sobrepõe a preferência do usuário precisa vir daqui, não dos casos escritos à mão — senão é ajustar o limiar aos próprios exemplos.

| percentil | p1 | p5 | p25 | p50 |
|---|---|---|---|---|
| confiança | 0.953 | 0.970 | 0.984 | 0.989 |

Mesmo o percentil 1 do corpus fica em **0.953**, muito acima das falhas do bloco adversarial (0,35 e 0,39). Um piso na casa de 0,50 descarta praticamente nada de texto bem formado e ainda assim recusa os casos curtos e ambíguos — é margem de segurança declarada, não limiar ajustado.

## O teste que decide se o número serve: currículo com idiomas misturados

Prosa gerada é limpa e monolíngue. Currículo real não é: um CV de tecnologia em português lista React, Docker e code review em inglês. Um held-out alto com este bloco falhando significaria que o número não vale para usuário real.

| esperado | predito | confiança | trecho |
|---|---|---|---|
| pt | pt | 0.51 | Desenvolvedor Full Stack com 5 anos de experiencia. Atuei com … |
| pt | pt | 0.45 | Analista de dados. Stack: Python, pandas, SQL, Airflow, dbt, S… |
| es | es | 0.44 | Ingeniero de software con experiencia en microservices, Spring… |
| es | es | 0.45 | Diseñador UX. Herramientas: Figma, Sketch, InVision. Realicé u… |
| en | en | 0.90 | Software engineer with experience in distributed systems, Go, … |
| pt | pt | 0.55 | Gerente de projetos certificada PMP e Scrum Master. Conduzi ce… |
| pt | pt | 0.63 | Analista de marketing digital com foco em campanhas.… |
| en | en | 0.77 | Marketing analyst focused on digital campaigns.… |
| es | pt **FALHOU** | 0.35 | Analista de marketing digital enfocado en campañas.… |
| es | pt **FALHOU** | 0.39 | Analista de marketing digital enfocado en campanas para el mer… |
| pt | pt | 0.67 | Analista de marketing digital com foco em campanhas para o mer… |
| es | es | 0.68 | Disenador grafico con experiencia en identidad visual y produc… |

**10/12** nos casos adversariais.

Falhas acima são o sinal de que treinar só em prosa gerada não cobre currículo real. Antes de embarcar, ou o corpus ganha exemplos misturados ou entra uma biblioteca treinada em texto natural.

## Limites

- Treinado em **prosa gerada por LLM**, não em currículo real. O bloco adversarial acima é escrito à mão e é a única evidência sobre texto fora do gerador.
- Cobre **pt, en, es** e nada mais. Um currículo em francês recebe um dos três, com confiança possivelmente alta — por isso a inferência exige um piso de confiança e cai na preferência do usuário abaixo dele, em vez de afirmar.
