# Custo de errar o idioma — recuperação de ocupação ESCO

Gerado 2026-08-14 · 1559 currículos · encoder `paraphrase-multilingual-MiniLM-L12-v2` · índice ESCO de 1.701 ocupações por idioma.

`worker.py` toma o idioma de `UserPreferences.language`, a preferência de interface do usuário, e nunca lê o currículo. A diagonal é o que a §6 mediu; fora dela é o que produção entrega quando a preferência discorda do documento.

## Acerto de ocupação top-1

| idioma real \ assumido | pt | en | es | n |
|---|---|---|---|---|
| pt | **55.8%** | 35.2% | 31.6% | 738 |
| en | 39.3% | **87.2%** | 42.8% | 407 |
| es | 30.0% | 33.6% | **57.5%** | 414 |

## Acerto de domínio — o número que alimenta `careerSwitch` e `target_seniority`

| idioma real \ assumido | pt | en | es | n |
|---|---|---|---|---|
| pt | **79.4%** | 66.5% | 66.3% | 738 |
| en | 76.9% | **94.3%** | 74.9% | 407 |
| es | 67.9% | 68.8% | **83.3%** | 414 |

**Domínio com idioma certo: 84.3%** · **com idioma errado: 69.4%** · queda de **14.9 pontos**.

**Idioma certo: 64.5%** (n=1559) · **idioma errado: 35.0%** (n=3118) · queda de **29.5 pontos**.

Ressalva: o pior caso de produção não é um sorteio uniforme entre idiomas errados. O default é `pt-BR`, então a coluna `pt` é a que um usuário sem preferência salva recebe, qualquer que seja o idioma do currículo dele.
