# Handoff — reconstrução de IA/PLN do skill-refine

Documento de contexto para continuar o trabalho em sessão nova. Contém o objetivo, as decisões
tomadas, o estado real do sistema, as armadilhas descobertas, e a especificação da próxima tarefa
(inferência de ocupação e domínio via ESCO).

---

## 1. Contexto e objetivo

O skill-refine analisa currículos e devolve pontuações. O sistema é a base de uma **defesa de TCC
sobre machine learning e PLN**, então a exigência não é só "funcionar": **nenhuma decisão pode ser
heurística, exceto como fallback**. Heurística existe para o usuário não ficar sem resposta quando
o modelo não pode rodar — nunca como decisor primário.

Fórmula do score final (medida em produção, `debug.scoreBreakdown`):

```
0.78 * quality + 0.12 * seniority + 0.10 * target_fit
```

Estado de cada tarefa:

| Tarefa | Peso | Provider hoje | Situação |
|---|---|---|---|
| quality | **78%** | `quality_probe` | sonda linear sobre MiniLM congelado (§9) |
| seniority | 12% | `text_seniority_probe` | sonda só de texto, decide sozinha (§9) |
| target_fit | 10% | `target_fit_embedding_v1` | já é neural (MiniLM multilíngue) |
| matching | quando há vaga | `matching_embeddings` | neural desde a sessão anterior |
| domínio/ocupação | entra em target_fit | `domain_embeddings` | migrado para recuperação ESCO (§6) |
| flags dos insights | o que aparece na tela | `bullet_probe` | classificador por bullet (§10.1) |
| ordem dos insights | o que se lê primeiro | `insight_gain_v1` | ranking por ganho medido (§10.3) |

`ats` e `clarity` deixaram de ser cópia literal de `quality_score` e ganharam cabeça própria — com
uma ressalva medida em §9.5. Nenhuma tarefa da resposta responde mais por regra: `HEURISTIC_TASKS_TODAY`
em `test_provider_inventory.py` está **vazio**, e o inventário agora cobre `insight_flags` e
`insight_ranking` além dos pilares.

Idiomas suportados: **pt-BR, en-US, es-ES**. Qualquer modelo novo deve ser multilíngue, e a
plataforma tem de cobrir **qualquer ocupação**, não uma lista fechada de domínios.

---

## 2. O diagnóstico que originou tudo

O modelo de senioridade (`seniority_signals_v1`, sklearn LogReg sobre 15 features numéricas)
respondia **`intern` com p≈1.0 para todo currículo real**. Não era imprecisão — era função
constante. Causa raiz, confirmada por decomposição do logit:

- No dataset de treino, `summary_char_count` ia de **30 a 61 caracteres** (resumos-stub escritos à
  mão). Currículo real tem **183 a 360**. Isso colocava a entrada real a **~25 desvios padrão**.
- O coeficiente dessa feature para a classe `intern` era **+0.65**, contribuindo **+16.09** ao
  logit de `intern` contra **−9.16** ao de `senior`.
- Todos os sinais legítimos somados (99 meses de experiência, liderança, completude) valiam ~+5.
  O comprimento do resumo sozinho decidia.

Dois agravantes estruturais:

1. **Rótulos circulares.** Os rótulos vinham de `_holistic_seniority_label(months, n_exp, bullets,
   has_leadership)` — uma fórmula sobre os mesmos números que o classificador recebia. Qualquer
   modelo treinado nisso só reaprende a fórmula. Era heurística lavada, não IA.
2. **Dataset minúsculo e monodomínio.** 180 exemplos sintéticos, 4 domínios de tecnologia
   (dev/data/ops/marketing). Zero financeiro, zero engenharia civil, zero saúde. A acurácia
   reportada de 0.888 era medida em 27 exemplos do mesmo mundo sintético.

---

## 3. Decisões tomadas (e por quê)

### 3.1 Rótulo vem de LLM, não de fórmula
Uma LLM maior lê **apenas o texto final** do currículo e atribui o nível. O modelo pequeno destila
esse julgamento. É isso que quebra a circularidade: o professor pode codificar critério que as
regras não têm. `band_target` (o alvo de geração) é gravado só para medir concordância — **nunca**
é usado como rótulo de treino.

### 3.2 Domínio é variável de ruído, não feature
Enumerar domínios cria conjunto fechado: com 4 buckets o modelo memoriza, e quebra no domínio 5.
A solução é **alta cardinalidade com independência do rótulo**: ocupação sorteada de ~1.700
ocupações do ESCO, uniformemente e independente da banda. Com <2 exemplos por ocupação não há
estatística por domínio para aprender, e o modelo é forçado aos sinais invariantes (escopo,
tenure, autonomia). A ocupação **nunca entra como campo** no modelo; fica só nos metadados, para
permitir a validação em ocupações held-out.

### 3.3 Idioma também é variável de ruído
Sorteado independentemente da banda. Existe um subconjunto **paralelo**: mesmo perfil estrutural e
mesma ocupação renderizados em pt/en/es. Se o rotulador der níveis diferentes para os três, isso é
viés de idioma medido diretamente.

### 3.4 Qualidade é ortogonal a senioridade
Um sênior pode escrever um currículo péssimo e um estagiário um ótimo. `quality_target`
(`poor`/`fair`/`good`) é sorteado independente da banda. Consequência de design: **métrica numérica
pertence à dimensão de qualidade, não à de escopo** — escopo se expressa por verbos e
responsabilidade. Antes de separar isso, exigir métricas em todas as bandas inflacionava
estagiários para pleno.

### 3.5 Estrutura é programática, prosa é LLM
Datas, meses, número de experiências, número de bullets e comprimento do resumo são gerados por
código, porque é onde o controle exato de distribuição importa — foi exatamente isso que quebrou o
v2. A LLM só escreve as palavras.

### 3.6 Ordem dos pilares
**Senioridade primeiro, `quality` depois.** Senioridade destrava o pipeline inteiro e valida a
abordagem ponta a ponta com custo menor. Ressalva honesta para a banca: enquanto `quality` não
tiver modelo, **o número principal que o usuário vê continua vindo de heurística** (78% do peso).

---

## 4. Estado atual

### Corpus
- `ml/data/raw/resumes_v3/prose.jsonl` — **873 currículos** com prosa gerada
- `specs.jsonl`, `specs_b.jsonl`, `specs_cal.jsonl`, `specs_q.jsonl` — as plantas estruturais
- `ml/data/reference/esco_occupations.jsonl` — **1.701 ocupações ESCO** com labels pt/en/es e
  código ISCO-08
- **60 de 100 grupos paralelos** completos nos 3 idiomas
- Rótulos: **zero válidos.** Os 308 produzidos foram apagados (ver 5.2)

### Scripts (`ml/scripts/`)
| Script | Função |
|---|---|
| `fetch_esco_occupations.py` | baixa a taxonomia ESCO (pt/en/es + ISCO) |
| `generate_resume_specs_v3.py` | fase 1a — specs estruturais, sem API |
| `write_resume_prose_v3.py` | fase 1b — prosa via Groq |
| `label_seniority_llm_v3.py` | rotulagem de senioridade via LLM |
| `validate_corpus_v3.py` | validação dos sinais numéricos (exit 1 se reprovar) |
| `inspect_corpus_text_v3.py` | validação do texto (escopo, idioma, ancoragem) |
| `build_label_review_sample.py` | amostra estratificada para revisão humana |
| `eval_domain_inference_esco.py` | avalia recuperação ESCO vs heurística de palavra-chave (§6) |

### Código de produção alterado na sessão da inferência de domínio (§6)
- `tasks/target_fit/esco_retrieval.py` — **novo**: índice de labels ESCO, cache em disco,
  recuperação top-k, confiança por margem, construção da query de ocupação
- `tasks/target_fit/isco_domains.py` — **novo**: mapa ISCO-08 → domínio por prefixo mais longo
- `tasks/target_fit/domain_inference.py` — cascata `domain_embeddings` → `domain_keywords`;
  a heurística virou `_infer_domain_keywords` e continua como fallback
- `orchestrator.py` — passa o modelo de embeddings e a query de ocupação; `_domain_block`
  enriquece a resposta com ESCO **só no caminho neural** (o fallback mantém o shape antigo)
- `config.py` + `settings_modules/ai.py` — `ANALYSIS_ESCO_*` (enabled, path, cache dir, top_k,
  min_cosine, max_alt_labels)
- `warmup.py` — pré-aquece o índice ESCO nos idiomas de `ANALYSIS_PREWARM_LANGUAGES`
- `.gitignore` — `ml/data/` deixou de ignorar `esco_occupations.jsonl` (ver 5.7)

### Código de produção alterado na sessão anterior
- `text_sanitizer.py` — passou a incluir **bullets e duração em meses**; corrigido
  `data.get("education")` → `educations`; `max_chars` 2000 → 4000
- `signals_ml_predict.py` + `ml/training/src/signals_features.py` — transformação **`log1p_v1`**
  nas 8 contagens sem teto, aplicada identicamente nos dois lados
- `loader_signals_model.py` — **trava**: recusa bundle cujo `feature_transform` do metadata
  divirja do que a inferência aplica
- `quality/predict.py` — `LEADERSHIP_WORDS` corrigido (não casava **"Líder"** por causa do acento,
  nem **"gerente"**; adicionados `jefe`, `jefa`, `responsable`, `encargad`, `supervis`)
- `seniority/text/predict.py` — `_normalize_label` completado com 17 entradas (`semi-senior`,
  `prácticas`, `pasante`, `becario`, `entry-level`, `staff`, `principal`, formas acentuadas)
- `matching/predict.py` — novo passo `matching_embeddings` na cascata, reusando o MiniLM já
  carregado para `target_fit`
- `docker-compose.yml` — `ANALYSIS_SIGNALS_ML_ENABLED=false`, fusão de texto desligada,
  thresholds alinhados ao metadata do modelo

### Testes
`apps.analysis.tests`: **181 testes, `OK`**. Golden snapshot passa. Não há mais falha herdada — as
quatro que o documento carregou por várias sessões foram diagnosticadas e corrigidas em §10.5, e três
delas eram defeito real. **Qualquer falha agora é regressão nova**, sem exceção a memorizar.

### Git
Branch `fix/seniority-thresholds-text-fusion`. O trabalho do §9 e do §10 está commitado em cinco
commits temáticos; antes disso o §9 inteiro vivia só no working tree.

---

## 5. Armadilhas descobertas (não repetir)

### 5.1 Groq esconde o limite diário
Os headers `x-ratelimit-*` mostram **só o por-minuto**. O limite diário aparece **apenas no corpo
do erro 429**. Medidos:

| Modelo | req/dia | tokens/min | **tokens/dia** |
|---|---|---|---|
| `llama-3.1-8b-instant` | 14.400 | 6.000 | **500.000** |
| `llama-3.3-70b-versatile` | 1.000 | 12.000 | **100.000** |

O 70b rende **~195 rótulos/dia**. Perdi horas otimizando timeout, workers e backoff perseguindo uma
degradação de throughput cuja causa era o orçamento diário drenando, enquanto os headers mostravam
milhares de tokens livres. **Sempre ler o corpo do 429.**

Consequências de design que decorreram disso: `max_tokens` é cobrado como **reservado**, então
superdimensionar custa orçamento real; e o backoff de 429 não pode ser global e longo, senão um
único 429 congela todos os workers.

### 5.2 O sanitizer não entregava bullets — invalidou 308 rótulos
`resume_to_text_sanitized` montava só resumo, títulos, cursos e skills. **Sem bullets e sem datas.**
A LLM rotulou 308 currículos sem ver o trabalho descrito, que é toda a evidência de senioridade.
Sintoma que isso produziu e que eu interpretei errado por um tempo: concordância de 51,8% com o
alvo e compressão para `mid`. Já corrigido, mas os rótulos foram descartados.

### 5.3 Correlação entra pela porta de trás
Sorteei bullets **por experiência** independente da banda — mas o **total** é
`n_exp × bullets_por_exp`, e `n_exp` correlaciona com a banda. A correlação reapareceu no total
(AUC 0.43). Corrigido sorteando o **orçamento total** de bullets independente da banda.
**Sempre validar a feature agregada, não a de origem.**

### 5.4 Métrica de sobreposição min/max mente com amostra pequena
Usar faixa min/max para medir separação entre bandas dá falso alarme quando as caudas não foram
amostradas. Substituído por **AUC de Mann-Whitney** (0.50 = sem sinal), que é robusto a n pequeno.
`validate_corpus_v3.py` também rotula o veredito como PARCIAL abaixo de 200 linhas.

### 5.5 Restrição de contagem não funciona, restrição estrutural funciona
Pedir "~35 palavras" ao 8b produzia 14, com 50% de falha. Pedir **array com exatamente N itens**
funcionou: 10/10 sem falha. E quando o modelo devolve **mais** do que o pedido, **truncar** é
melhor que rejeitar.

### 5.6 Varredura de palavra-chave no documento inteiro erra o domínio em 4 de 5 currículos
A heurística de domínio media **21,4%** de acerto nos 873 currículos porque escaneia o texto todo:
a seção de formação contém "universidade", "curso", "ensino" em **qualquer** currículo, então
`education` venceu 231 vezes. É o mesmo modo de falha da varredura global em
`has_internship_terms`. Quando a mesma heurística recebe só títulos e skills, cai para 20,8% — mas
aí devolve `general` em 372 casos em vez de errar com confiança. **Restringir o campo de leitura
não conserta um decisor que não entende sinônimos; só troca o tipo de erro.**

### 5.7 `ml/data/` era ignorado pelo git — a taxonomia não existia fora desta máquina
`esco_occupations.jsonl` é **entrada de produto**, lido em tempo de inferência, mas estava sob a
regra `ml/data/` do `.gitignore` junto com os dados derivados. Em qualquer clone o passo ESCO
cairia silenciosamente na heurística. Como `ml/data/` (diretório) impede o git de descer na árvore,
negar um arquivo lá dentro exige trocar a regra por `ml/data/*` e re-incluir os pais:

```
ml/data/*
!ml/data/reference/
ml/data/reference/*
!ml/data/reference/esco_occupations.jsonl
```

O cache de embeddings (`esco_embeddings/*.npz`) continua fora do git — é derivado e depende do
modelo. `*.npz` também já é ignorado globalmente.

### 5.8 Outros
- `ConnectionResetError` **não** é subclasse de `URLError` — capturar `OSError`
- `urllib` é bloqueado por Cloudflare (erro 1010) sem `User-Agent` customizado
- Job em background com stdout num pipe não drenado **trava** ao encher o buffer; redirecionar
  para arquivo
- Uma exceção dentro de `pool.map` mata a run inteira; isolar cada item

---

## 6. Concluído: inferência de ocupação e domínio via ESCO

### O que foi feito
`infer_domain_category` deixou de ser decidida por substring de palavra-chave. Agora é uma
cascata: **`domain_embeddings` → `domain_keywords`**. O passo neural embeda o texto e os labels
das 1.701 ocupações ESCO **no idioma do currículo** com o MiniLM multilíngue que já estava
carregado para `target_fit`, tira o cosseno, e deriva o domínio do **ISCO-08** da ocupação
vencedora. Sem treino, sem rótulo, sem consumir orçamento de LLM.

A heurística continua no lugar como fallback e é ela que responde quando: embeddings estão
desligados, o `sentence-transformers` não importa, a taxonomia não está no disco, ou o cosseno
top-1 fica abaixo de `ANALYSIS_ESCO_MIN_COSINE` (0,20).

### Resultado medido (873 currículos do corpus, `eval_domain_inference_esco.py`)

| Provider | Acurácia de domínio | Ocupação top-1 | top-5 |
|---|---|---|---|
| `domain_keywords` (produção anterior, texto todo) | **21,4%** | — | — |
| `domain_keywords` (mesma evidência: títulos+skills) | 20,8% | — | — |
| `domain_embeddings` (query de títulos+skills) | **85,5%** | **66,1%** | **79,6%** |
| `domain_embeddings` (currículo inteiro como query) | 79,6% | 54,2% | 75,4% |
| `domain_embeddings` (só resumo+bullets, sem títulos) | 64,5% | 30,2% | 51,5% |

Por idioma (configuração escolhida): **en 93,4% · es 85,9% · pt 80,4%** de domínio;
top-1 de ocupação 86,3% / 60,7% / 57,0%.

Confiança calibrada nesses dados: **high 98,2%** (n=494) · **medium 87,5%** (n=184) ·
**low 51,3%** (n=195). Ou seja, `confidence` agora é informação, não enfeite.

**Ressalva honesta para a banca:** o gerador escreve o label ESCO dentro dos títulos dos cargos,
então as linhas com título são um **limite superior**. A linha "só resumo+bullets" (64,5% de
domínio, 30,2% de ocupação) é o piso — o que sobra quando o modelo tem de recuperar a ocupação a
partir do trabalho descrito. O número honesto para currículo real está entre os dois, e mesmo o
piso é 3× a heurística.

### Decisões tomadas com base na medição
- **Query de ocupação é título-primeiro** (`build_occupation_query`: targetPosition + cargos +
  skills + cursos). Bate o currículo inteiro em 6 pontos de domínio e 12 de ocupação: label ESCO é
  título, e parágrafos de realização diluem o sinal. O texto completo continua indo para a
  heurística de fallback, que precisa dele.
- **Só labels preferenciais** (`max_alt_labels=0`). Incluir 4 labels alternativos por ocupação
  *piorou* (84,0% vs 85,5%; top-1 63,1% vs 66,1%): puxa a query para quem tem mais sinônimos
  cadastrados. Ficou configurável porque é mensurável.
- **Confiança pela margem entre domínios**, não pelo cosseno absoluto. Acurácia por margem:
  98% acima de 0,10 · 90% entre 0,05 e 0,10 · 35–62% abaixo de 0,05. O cosseno quase não separa
  (p05 = 0,579), então cosseno alto com margem fina é ambiguidade, exatamente como previsto.
- **ISCO de 2 dígitos como base, 3 e 4 para desambiguar.** `isco_domains.py` faz busca por
  **prefixo mais longo** (4 → 3 → 2). Assim `2166` (designers) vai para `creative` sem tirar
  `21` de `engineering`, e `1211` (finance managers) sai de `administrative` para `finance`.
  Cobertura: **0,6%** das 1.701 ocupações caem em `general`.

### Onde ficou o código
- `tasks/target_fit/esco_retrieval.py` — índice, cache, recuperação, confiança, query
- `tasks/target_fit/isco_domains.py` — mapa ISCO → domínio
- `tasks/target_fit/domain_inference.py` — a cascata
- Contrato: `domainCategory` / `confidence` / `evidenceTokens` intactos (consumidores em
  `fit_signals.py` e `ml_feature_row.py` não sabem que algo mudou). No caminho neural a resposta
  ganha `provider`, `escoOccupation` (uri, label, isco, iscoGroup, cosine), `domainMargin` e
  `occupationGap`. No fallback o shape é **byte a byte o de antes** — foi assim que o golden
  snapshot continuou passando sem regravar baseline.

### Custo em produção
Índice de 1.701 labels × 384 dims por idioma, gravado em
`ml/data/reference/esco_embeddings/<modelo>__<lang>__alt0.npz` (2,4 MB cada). Processo novo lê o
arquivo em vez de reembedar; `warmup.py` faz isso no startup do Celery. Medido: primeira análise
31s (carga do MiniLM inclusa), seguintes **1,4–1,6s**. Nunca reembeda por requisição.

### Limitação conhecida (candidata a próxima melhoria)
**51% das ocupações ESCO caem em `operations`** — as 13 categorias do produto são de colarinho
branco e jogam ofícios, operação de máquina, transporte e serviços todos no mesmo balde. A
recuperação acerta a ocupação e depois perde resolução no mapeamento. Corrigir exige mexer em
`DOMAIN_CATEGORIES`, que muda o comprimento do one-hot em `ml_feature_row.py` e invalida o bundle
`target_fit_v1` — é mudança deliberada, com retreino, não ajuste de passagem.

---

## 7. Roadmap: tirar a heurística de decisão de TODA a análise

Objetivo declarado: **nenhuma área da análise decide por regra quando um modelo pode decidir.**
São ~20 pontos de decisão, mas não são 20 projetos — colapsam em **4 famílias de modelo**.

### 7.1 Inventário completo

**Grupo A — julgamento do texto** (um corpus, um professor, uma passada de rotulagem, várias cabeças)

| Área | Decisor hoje | Vira | Rótulo |
|---|---|---|---|
| `seniority` | `rule_based_seniority`: faixas de meses + vetos | classificador ordinal sobre texto | rubrica do professor |
| `quality` (78% do score) | `_heuristic_score`: 5 flags de regex | regressor multi-dimensão | rubrica |
| `ats` | **cópia literal de `quality_score`** (`orchestrator.py:758`) | cabeça própria: higiene de palavra-chave e estrutura | rubrica |
| `clarity` | **cópia literal de `quality_score`** (`orchestrator.py:759`) | cabeça própria: clareza e concisão | rubrica |
| `has_metrics`, `has_action_verbs`, `has_leadership` | ✅ `bullet_probe` (§10.1) | feito | — |
| termos de estágio (`_INTERNSHIP_RE`) | regex sobre o cargo recente | ainda de pé; escopo já restrito ao cargo atual | — |
| `insights` (quais forças/melhorias mostrar) | ✅ `insight_gain_v1` decide a ordem (§10.3) | as *condições* ainda são `if`; a **seleção** é medida | nenhum novo |
| caps de completeness (40/72) | ✅ ficam, e a razão mudou (§11.4) | guarda de **fora da distribuição**, não proxy de incerteza; abstenção por margem entrou **ao lado**, não no lugar | nenhum novo |

**Grupo B — correspondência semântica** (encoder, quase sem rótulo novo)

| Área | Decisor hoje | Vira | Rótulo |
|---|---|---|---|
| domínio/ocupação | ✅ `domain_embeddings` (§6) | feito | — |
| `target_fit` | 0,65 × cosseno + **0,35 × policy** | 100% encoder + cabeça calibrada | revisão humana (`reviewed_score`) — **nunca** o score da policy, que é circular |
| `matching` | cosseno ✅, mas evidência é interseção de tokens | extração de termo por similaridade no nível do token, mesmo encoder | nenhum |
| `careerSwitch`, clamps de `targetSeniority` | if/else sobre score e domínio | classificador sobre (emb currículo, emb alvo) | revisão humana |
| provider de matching na telemetria | **bug: reporta `heuristics` mesmo quando o cosseno respondeu** | propagar o provider da cascata | — |

**Grupo C — extração e estruturação** (modelos prontos, zero rótulo)

| Área | Decisor hoje | Vira |
|---|---|---|
| PII no `text_sanitizer` | regex | NER multilíngue |
| idioma | **não existe** — vem da request | detector de idioma |
| seções, bullets, datas, meses | leitura de campo e aritmética | **continua programático** (ver 7.4) |

**Grupo D — geração**

| Área | Decisor hoje | Vira |
|---|---|---|
| recomendações | 5 templates fixos em 3 idiomas (`EXAMPLE_TEMPLATES`) | `llm_feedback.py` (já existe, `ANALYSIS_LLM_FEEDBACK_ENABLED=false`) com os templates como fallback |

### 7.2 A economia que faz isso caber: uma passada, uma rubrica

O professor lê o currículo **uma vez** e devolve um JSON com tudo: banda de senioridade, as quatro
dimensões de qualidade, e os atributos por bullet. `label_rubric_llm_v3.py` faz isso em dois
estágios porque os dois modelos têm **orçamentos diários independentes**: julgamento no 70b,
atributos por bullet no 8b.

**Custo medido pela API (`usage`), não estimado** — 8 itens por estágio:

| Estágio | Modelo | tokens/item | itens/dia | 873 currículos |
|---|---|---|---|---|
| judgment (banda + 4 dimensões) | 70b | **1.273** (1.235 prompt + 38 saída) | ~79 | **11,1 dias** |
| bullets (3 atributos por bullet) | 8b | 695 (463 + 232) | ~719 | 1,2 dias |
| judgment no 8b (mesma rubrica) | 8b | ~1.273 | ~392 | ~2,2 dias |

**Ablação de professor × prompt** (mesmos 8 currículos, `--compare` mede professor contra professor):

| Configuração | tokens/item | itens/dia | Banda exata vs 70b-fewshot | MAE das 4 dimensões |
|---|---|---|---|---|
| 70b + few-shot (referência) | 1.273 | 79 | — | — |
| **70b + prompt curto (`--terse`)** | **825** | **121** | **5/8 (62%) · ±1 = 100%** | 0,12–0,25 |
| 8b + prompt curto | ~650 | ~770 | 2/8 (25%) · ±1 = 88% | 0,12–**1,00** |

Isolando um fator por vez: **encurtar o prompt é seguro, trocar o professor não é.** O prompt curto
no 70b preserva as dimensões (erro médio 0,12–0,25 numa escala de 5) e corta 35% do custo. O 8b com
o *mesmo* prompt cai a **25% de acerto de banda — o nível do chute para 4 classes** — e erra um
ponto inteiro em `impact`. O 8b concorda em `language` (0,12) e razoavelmente em `clarity`/`ats`
(0,75): serve para atributo mecânico (o estágio de bullets acertou 8/8 o contrato), não para julgar
escopo de carreira. Ressalva: n=8, é sonda.

Três coisas que essa medição estabelece:

1. **Os ~195 rótulos/dia registrados em 5.1 estavam otimistas por ~2,5×.** O número real do 70b é
   **79/dia** com a rubrica. Rotular os 873 no 70b é 11 dias, não 5.
2. **A rubrica saiu de graça; o prompt é que custa.** A saída são 38 tokens de 1.273 — as quatro
   dimensões de qualidade custaram ~18 tokens/item. Quem consome o orçamento é o system prompt +
   few-shot, pagos 873 vezes. Encurtá-los é a única otimização grande de graça: cortar os dois
   few-shots (~400 tokens) deve levar o 70b a ~125 itens/dia.
3. **O contrato estrutural do 8b funciona**: 8/8 devolveram exatamente N objetos por bullet,
   confirmando 5.5 (restrição estrutural funciona, restrição de contagem não).

Corolário: rotular duas vezes (uma passada para senioridade, outra para qualidade) custaria o dobro
do orçamento escasso. A rubrica tem de estar definida **antes** de disparar a rotulagem.

### 7.2.1 A dimensão de qualidade nasce constante neste corpus

Nos 8 itens de sonda o professor deu **impact 4,88 · clarity 4,88 · ats 5,00 · language 5,00** —
8 de 8 no topo em duas dimensões. Não é o professor que está quebrado: **868 dos 873 currículos
foram gerados sem `quality_target`**, portanto todos com a instrução `good` (ver §4). Rotular
qualidade neste corpus hoje é comprar uma coluna constante.

**A geração de prosa degradada (`poor`/`fair`) precisa vir antes da rotulagem de qualidade.** É no
8b, não compete com o orçamento do 70b, e o gerador de specs já sorteia `quality_target`
uniformemente (`generate_resume_specs_v3.py:315`) — specs novos saem instantaneamente, sem API.

`specs_q2.jsonl`: **700 specs** gerados com seed 20260810 e prefixo `q`, qualidade
223 poor / 237 fair / 240 good, bandas 173/177/177/173, 529 ocupações distintas, 30 grupos
paralelos.

### 7.2.2 Rotular o corpus NOVO, não o antigo

O corpus antigo serve a **um** pilar: qualidade nele é constante, então rotulá-lo custaria 7,2 dias
para cobrir os 12% da senioridade. Os specs novos têm `band_target` balanceado **e**
`quality_target` uniforme — um único rótulo por currículo alimenta os dois pilares, mais os
atributos por bullet. É por isso que a fila é: prosa nova (8b) → judgment terse (70b) → bullets (8b),
e o corpus antigo fica como validação extra de senioridade se sobrar orçamento.

Com 121 itens/dia no 70b-terse: **360 currículos ≈ 3,0 dias** e cobre senioridade + as 4 dimensões
de qualidade + os bullets.

### 7.2.2b Professores alternativos: quem serve para quê

O gargalho da rotulagem é cota, não capacidade, então testei cinco provedores com camada gratuita.
Todos falam o formato OpenAI, então `PROVIDERS` em `label_rubric_llm_v3.py` mapeia
nome → endpoint, modelo, variável de chave e teto de tokens.

| Provedor | Modelo | Situação |
|---|---|---|
| Groq | `llama-3.3-70b-versatile` | ~11/min, teto 100k tokens/dia → 153 itens/dia |
| **Mistral** | `mistral-small-latest` | **580 tokens/item, ~40/min, 50k tokens/min, sem teto diário aparente** |
| Gemini | `gemini-flash-latest` | funciona, mas a cota gratuita estoura em poucas dezenas |
| OpenRouter | `nvidia/nemotron-3-super-120b-a12b:free` | funciona, ~2/min |
| ~~Cerebras~~ | `gpt-oss-120b` | **HTTP 402 pagamento exigido** — removido do código e do `.env` |
| ~~GitHub Models~~ | — | **HTTP 410**, serviço em desativação |

Os ids de modelo têm de ser lidos do endpoint `/models` de cada serviço: nomes publicados como
`llama-3.3-70b` na Cerebras e `gemini-2.0-flash` já estavam retirados.

**Modelo de raciocínio gasta a cota pensando antes de escrever.** O Gemini queimou ~470 tokens de
pensamento nesta rubrica e com `max_tokens=140` devolvia `{"level": "intern` truncado, com
`finish_reason=length` — parecia falha de JSON e era falta de espaço. Daí o teto ser por provedor.
No Groq ele continua apertado, porque lá `max_tokens` é cobrado como reservado.

**Mistral contra o 70b, n=60 no mesmo conjunto de ids (`--overlap-with`):**

| Medida | Resultado |
|---|---|
| banda exata | 33/60 (55%), **±1 nível 98%** |
| desvio de banda | `{-1: 27, 0: 33}` — **todo erro é um nível para baixo, nenhum para cima** |
| `impact` | erro médio 0,43 ponto (escala 1-5) |
| `clarity` / `ats` | 0,87 / 0,98 |
| `language` | 1,67 |
| monotonia no alvo plantado | poor 1,50 → fair 2,73 → good 3,75 (70b: 1,56 → 3,00 → 3,96) |

A leitura que importa: o desacordo de banda **não é ruído, é viés de calibração**. Ele aplica um
limiar mais severo e erra sempre para o mesmo lado, o que é corrigível e mensurável — diferente do
8b, que errava espalhado no nível do chute.

### 7.2.2c O mesmo modelo em outro provedor mata o gargalho

O teto de 153 rótulos/dia era do **provedor**, não do modelo. SambaNova e Hugging Face servem o
mesmo `Llama-3.3-70B-Instruct` que o Groq, e por serem os mesmos pesos entram sem desvio de
calibração — o que um professor menor nunca conseguiria.

Concordância com o Groq 70b no mesmo conjunto de ids:

| Professor | Modelo | n | Banda exata | ±1 | MAE impact / clarity / ats |
|---|---|---|---|---|---|
| **Hugging Face** | Llama-3.3-70B-Instruct | 41 | **93%** | 100% | **0,15 / 0,10 / 0,12** |
| **SambaNova** | Meta-Llama-3.3-70B-Instruct | 19 | **95%** | 100% | 0,21 / 0,21 / 0,21 |
| Mistral | mistral-small-latest | 130 | 58% | 98% | 0,51 / 0,85 / 1,03 |

Os 5-7% de desacordo entre os iguais são não-determinismo de amostragem, não calibração: os desvios
se espalham para os dois lados (`{-1: 2, 0: 38, 1: 1}`), enquanto os do Mistral apontam todos para
baixo (`{-1: 51, 0: 75}`).

**Consequência de cronograma:** o Hugging Face sustenta ~12-15 itens/min, então os 873 currículos
saem em **~1,2 hora** em vez de 5,7 dias. A rotulagem deixa de ser o gargalho do projeto; o gargalho
volta a ser a geração de prosa (8b, 500k tokens/dia) e o treino.

Provedores testados e descartados, com o motivo: **Cerebras** e **DeepInfra** exigem saldo
(HTTP 402), **GitHub Models** responde 410 (serviço em desativação), **Together** devolveu 401 com
a chave fornecida. `probe_llm_providers.py` refaz esse teste em um comando.

**Divisão de trabalho decidida por essas medições:**
- **Hugging Face é o professor primário** — mesmo modelo da referência, bandas e dimensões
- **Groq 70b e SambaNova** como referência e transbordo
- **Mistral sai do volume**: os 253 rótulos dele ficam como segundo anotador para a tabela de
  concordância, que é evidência de que os rótulos não são artefato de um fornecedor só
- **`language` sai do escopo**: saturado no professor forte (4-5) e o pior erro entre professores.
  Fica documentado como dimensão que o gerador atual não consegue produzir — a instrução `poor`
  degrada conteúdo, não gramática

### 7.2.2d A revisão humana inverteu a fonte do rótulo de senioridade

46 currículos revisados à mão (`build_label_review_sample.py` + `score_label_review.py`), amostra
estratificada: 20 discordâncias professor × gerador, 2 divergências de idioma, 24 de linha de base.
É o único ponto do pipeline em que a verdade não vem de um modelo.

| Medida | Resultado |
|---|---|
| estrato C (linha de base, única estimativa não viesada) | **24/24 (100%)** |
| nas 21 linhas contestadas, humano fica com o **alvo plantado** | **17/21 (81%)** |
| nas mesmas, humano fica com o **professor** | 4/21 (19%) |
| concordância geral na amostra | 29/46 (63%), ±1 nível **100%** |

Extrapolando para os 207 rótulos existentes (o professor concorda com o alvo em 73,4%):

| Fonte do rótulo | Acurácia estimada contra julgamento humano |
|---|---|
| **`band_target`** (alvo plantado) | **94,9%** |
| Professor LLM (Llama-3.3-70B) | 78,5% |

**O alvo plantado é um rótulo melhor que o professor.** Os erros do professor se concentram em
`junior` (37%) e `mid` (64%) — `intern` e `senior` saíram 100% — e em **pt-BR (47%, contra en 71% e
es 80%)**, que é o maior idioma do corpus.

Isso refina a doutrina anti-circularidade em vez de contrariá-la. O pecado do v2 era o rótulo vir de
uma **fórmula sobre as mesmas features que o classificador recebia**. Para um modelo que lê contagens
(meses, bullets), `band_target` continua circular. Para um modelo **só de texto**, a revisão humana
mostra que o texto expressa a banda em ~95% dos casos: o rótulo passa a ser validado por humano, base
mais forte do que confiar no julgamento da LLM.

**Ressalva medida, não escondida:** o texto revisado inclui a duração em meses de cada cargo, então
parte da concordância com o alvo pode vir da leitura das datas, não da prosa. Separar isso custa ~15
minutos — reamostrar ~15 currículos com a duração removida e reler.

**A dimensão de qualidade, ao contrário, ficou triplamente confirmada:**

| Fonte | poor | fair | good |
|---|---|---|---|
| **Humano** | **1,50** | **2,61** | **3,64** |
| Professor Llama-3.3-70B | 1,56 | 3,00 | 3,96 |
| Mistral small | 1,50 | 2,73 | 3,75 |

Humano contra professor em `impact`: erro médio **0,35 ponto**, exato 70%, ±1 96%, viés −0,30 (o
professor é levemente generoso). **O rótulo do pilar que vale 78% está ancorado.**

Consequência de cronograma: **a rotulagem sai do caminho crítico.** `band_target` cobre 1.613
currículos e `quality_target` cobre os 745 novos, ambos validados por humano. Os rótulos do professor
passam a ser conjunto de validação de resolução fina (1-5 em quatro dimensões), não rótulo primário.

### 7.2.3 Pacing e o teto diário do 8b

Dois tetos diferentes, e confundi-los custa tempo:

- **Por minuto**: o 8b tem 6.000 tokens/min. A ~1,9k tokens por currículo de prosa são ~3 itens/min,
  então `--workers 1 --delay 20`. O default `--workers 2 --delay 6` tenta ~23k tokens/min e o job
  passa a vida em backoff.
- **Por dia (TPD)**: 500.000 no 8b, 100.000 no 70b, e **só aparecem no corpo do 429** — os headers
  `x-ratelimit-*` mostram apenas requisições/dia e tokens/**min**. Corpo real medido:
  `on tokens per day (TPD): Limit 500000, Used 499678 ... service tier on_demand`.

A janela do TPD é **rolante**, não meia-noite: o `retry-after` volta em segundos e a cota
libera conforme o uso de 24h atrás sai da janela. Um job resumível com `--delay` alto continua
pingando; não precisa esperar o "dia seguinte" inteiro.

Diagnóstico em uma chamada, quando um job entrar em 429 sem explicação: peça `max_tokens` alto ao
modelo suspeito e imprima `HTTPError.read()`. E nunca rode job de background com stdout num pipe de
`grep`: o pipe não drenado esconde justamente as mensagens de 429 (§5.6).

### 7.3 O que cada grupo destrava

- **A** cobre `quality` + `ats` + `clarity` + `seniority` + as 4 famílias de regex + a seleção de
  insights. É 90% do score e a maior parte do texto que o usuário lê.
- **B** já está quase todo neural; falta tirar a fatia policy de 35% do `target_fit` e trocar a
  evidência de sobreposição por extração semântica.
- **C** e **D** não precisam de rótulo: são modelos pré-treinados e geração.

### 7.4 O que continua programático — e por quê

Extração de campo, aritmética de datas, contagem de bullets, truncamento e o fallback de i18n
**não são julgamentos, são medição**. Foi justamente o controle exato dessas distribuições que
salvou o corpus v3, e trocá-las por modelo adicionaria erro sem adicionar inteligência. A linha
defensável na banca é: *o modelo julga, o código mede*.

**Correção do que esta seção previa** (medido no §11): os **caps** 40/72 *não* viraram abstenção
calibrada. Completude não prevê a incerteza do modelo — a confiança é a mesma em currículo esparso e
completo. O que ela prevê é entrada **fora da distribuição**, onde o modelo está *confiantemente*
errado (currículo vazio pontua 78 com margem 0,368). Abstenção por margem entrou **ao lado** dos caps,
para dúvida dentro da distribuição, não no lugar deles. Uma frase importante sobreviveu à medição com
sentido novo: *o código mede* também significa que o código detecta quando o modelo não deveria estar
respondendo.

### 7.5 Definição de pronto

1. `ml/models/` deixa de estar vazio: artefato versionado e carregado (hoje qualquer treino cai em
   fallback silencioso, com `ANALYSIS_SIGNALS_ML_ENABLED=false` e `TEXT_SENIORITY_ENABLED=false`)
2. **teste de guarda**: para um currículo bem formado, nenhum provider da resposta pode ser
   `heuristics` / `rule_policy` / `target_fit_policy` / `domain_keywords`
3. telemetria reporta o provider **que respondeu**, não o bundle que existia
4. pesos 0,78/0,12/0,10, `SENIORITY_TO_SCORE` e `cosine_to_fit_score` ajustados em rótulo humano
   de score geral, ou declarados como política de produto

### 7.6 Ordem de execução

1. Definir a rubrica e estender o rotulador **antes** de gastar orçamento (7.2)
2. Disparar a rotulagem (tempo de parede, roda desatendida)
3. Em paralelo, sem API: Grupo C (NER + idioma), o bug de provider do matching, o teste de guarda
4. Cabeças do Grupo A conforme os rótulos chegam
5. Grupo B: cabeça calibrada de `target_fit`, evidência semântica de matching
6. Grupo D: ligar a geração com fallback nos templates

---

## 9. Concluído: as duas cabeças treinadas, e a heurística sai do caminho de decisão

### 9.1 O que ficou de pé

Duas sondas lineares sobre o **MiniLM multilíngue congelado** — o mesmo encoder que já estava
carregado para `target_fit`, então cada análise ganha um matmul e zero memória nova. Treino é
comando de segundos na CPU, o que torna barato retreinar quando mais rótulo chega.

| cabeça | rótulo | acurácia (held-out por **ocupação**) | macro-F1 |
|---|---|---|---|
| `text_seniority_probe` | `band_target` | **75,9%** · ±1 94,5% | 0,749 |
| `quality_probe` (nível) | `quality_target` | **75,1%** · ±1 98,6% | 0,755 |
| `quality_probe` (`impact`) | rubrica do professor 1-5 | MAE **0,62** (baseline 1,30) | ρ 0,859 |
| `quality_probe` (`clarity` / `ats`) | rubrica do professor 1-5 | MAE 0,39 / 0,42 | ρ 0,76 / 0,73 |

Baselines nas mesmas linhas: `rule_based_seniority` 70,4%, classe majoritária 31,2%, chance 33% em
qualidade. **Contra os 46 verdicts humanos — a única referência que não é modelo — a sonda faz 82,6%
contra 67,4% da regra.**

### 9.2 O ganho foi de representação, não de hiperparâmetro

Uma média sobre o currículo inteiro deixa uma lista de 40 skills e duas linhas de conquista caírem no
mesmo vetor, e a lista longa ganha. A transformação passou a embedar **as quatro seções separadamente**
(resumo · cargos · realizações · formação+skills) e concatenar, mais o vetor do documento inteiro.
Medido em `sweep_probe_designs_v3.py`, com protocolo idêntico:

| representação | senioridade | qualidade |
|---|---|---|
| média do documento inteiro | 67,6% | 62,2% |
| **por seção (+ documento)** | **75,9%** | **76,4%** |

Testados e descartados **com número**, não por preferência: MLP de 256 (74,9% / 75,1%), SVM linear
calibrado (74,9% / 74,8%), ordinal ridge (62,9% / 75,1%) e gradient boosting — este último excluído
porque split eixo-alinhado em vetor semântico denso é o *inductive bias* errado (nenhuma coordenada
de embedding carrega um limiar) e custava horas por célula. Regressão logística ganhou nos dois alvos.

`C` é escolhido por **CV aninhado dentro de cada fold de treino**. Reportar o melhor `C` encontrado
nos folds que estão sendo pontuados seria citar número ajustado como se fosse held-out.

### 9.3 As duas ablações que fecham a circularidade

**Tenure.** As quatro seções não contêm contagem de meses em lugar nenhum — só o bloco do documento
tem os marcadores `(N meses)`. Então:

| variante | acurácia |
|---|---|
| seções + documento com meses (produção) | 75,9% |
| seções + documento com meses removidos | 74,7% |
| **só seções — zero contagem de meses** | **74,3%** |

Ler os meses vale 1,6 ponto. A linha de baixo é impossível de acusar de reaprender a fórmula do
gerador, e ainda assim **bate por 4 pontos a regra que só lê meses**. Isso encerra a ressalva aberta
em §7.2.2d de forma muito mais forte do que reamostrar 15 currículos à mão.

**Nível declarado no título.** O gerador pôde escrever a banda no cargo em 22% do corpus
(`may_state_seniority`). Nessas linhas a sonda faz 76,4%; nas outras 78%, faz 75,7%. Diferença de
0,7 ponto — o modelo não está vivendo de ler "Senior" no título.

### 9.4 A fusão de produção era pior que os dois componentes dela

`fuse_seniority` pesava a regra em `0,4 + 0,45 × strength`. Medido contra as duas referências
(`eval_seniority_fusion_v3.py`):

| decisor | vs `band_target` | vs humano (n=46) | macro-F1 vs humano |
|---|---|---|---|
| sonda sozinha | 67,5%¹ | **67,4%** | **0,671** |
| regra sozinha | 70,4% | 67,4% | 0,611 |
| **fusão (produção)** | **64,3%** | **58,7%** | **0,542** |

¹ medido antes da troca de representação; a sonda de produção hoje faz 75,9%.

Média de rank ordinal seguida de re-thresholding **não** divide a diferença entre dois decisores: ela
empurra desacordo para as bandas do meio. A coluna de distribuição mostra direto — a fusão inflava
`mid` e matava `senior` até onde um dos componentes acertava. Não existe versão disso em que manter a
fusão se defende. **A sonda decide, a regra é fallback, o blend está desligado.**
`clamp_seniority_vetoes` fica: veto sobre evidência ausente ("nunca `senior` sem seção de experiência")
é segurança de produto declarada como política, não julgamento competindo com o modelo.

### 9.5 Limites medidos, não escondidos

**`ats` e `clarity` não se separam.** O professor dá o **mesmo número** para as duas em 97,7% das
linhas rotuladas (Pearson 0,978), e nunca difere por mais de um ponto. As duas cabeças existem e
consertam o defeito que importava — `ats` e `clarity` deixam de ser cópia literal de `quality_score`,
que media outra coisa. O que **não** está consertado é que elas quase não diferem entre si, e isso é
propriedade da rubrica, não do modelo: o prompt faz duas perguntas que o professor responde como uma.
Separar exige rubrica que pontue higiene de palavra-chave e estrutura à parte de concisão, e um
gerador cuja instrução `poor` degrade formatação e não só conteúdo. É trabalho de re-rotulagem, não
de retreino — mesmo limite já registrado para `language` em §7.2.2b.

**A generalização para escritor novo é menor que o número principal.** O corpus tem dois escritores de
prosa, e os dois rótulos são *instruções dadas a um escritor*, não medições do que voltou. Treinar
numa e testar na outra:

| alvo | dentro do mesmo escritor | entre escritores | queda | comparação balanceada? |
|---|---|---|---|---|
| `quality_target` | 72,9% | **64,6%** | 8,3 pontos | **sim** (326 vs 317 linhas de treino) |
| `band_target` | 73,3% | 70,3% | 3,0 pontos | **não** (1185 vs 326) |

**Os dois resultados não significam a mesma coisa, e a diferença é tamanho de amostra.**

Em `quality_target` os dois sentidos treinam em ~320 linhas cada e dão 65,6% e 63,5% — comparação
balanceada, queda real. Parte do score agrupado é estilo de escritor e não o construto, então **64,6%
é a estimativa honesta do que produção entrega** e 75,1% é limite superior.

Em `band_target` os sentidos são assimétricos: treinar nas 1.185 linhas do 8b e testar nas 326 do
Mistral dá **78,2% — acima do próprio número agrupado de 75,9%**; o sentido inverso, com 326 linhas de
treino, cai para 62,4%. A média de 70,3% mistura um sentido bem-alimentado com um faminto, então ela
**subestima** a cabeça. A senioridade é robusta a escritor; a qualidade não demonstrou ser.

Em ambos os casos o que conserta é diversidade de escritor no corpus, que dois geradores não dão — não
é outra cabeça nem outro hiperparâmetro. **Um usuário real é sempre um terceiro escritor que a cabeça
nunca leu.**

**O dedupe pegou mais do que o esperado.** Além das linhas repetidas em `labels_rubric.jsonl`,
`prose.jsonl` também tinha ids duplicados (90 linhas) — jobs de prosa resumíveis rodados mais de uma
vez. Sem deduplicar, esses currículos treinariam com peso dobrado. `corpus_frame_v3.py` deduplica
todo arquivo por id com last-write-wins e **reporta a contagem**, para o dedupe ser visível em vez de
implícito.

**A monotonia por escritor via rótulo do professor não deu para fazer:** todo rótulo existente está em
prosa de um único escritor (351 linhas do Mistral seguem sem rótulo). A transferência entre escritores
acima responde a mesma pergunta sem depender de rótulo nenhum, e no corpus inteiro em vez da fatia
rotulada.

### 9.6 Onde ficou o código

- `text_probe.py` — **novo**: `TRANSFORM_ID`, janelamento, `section_texts`, `build_feature_matrix`
  (uma implementação, usada por treino e inferência), e `load_probe_bundle`, que **recusa** bundle cujo
  `feature_transform` ou largura divirja do que a inferência calcula — a mesma trava que
  `loader_signals_model` ganhou depois de um skew silencioso
- `tasks/quality/loader_quality_probe.py`, `tasks/seniority/text/loader_seniority_probe.py` — **novos**
- `tasks/quality/predict.py` — passo `quality_probe` na frente da cascata; `predict_quality_detailed`
  devolve provider e as dimensões, no mesmo idioma de `predict_matching_detailed`
- `tasks/seniority/text/predict.py` — passo de sonda na frente do bundle HF e do léxico
- `orchestrator.py` — sonda primária de senioridade, `ats`/`clarity` das cabeças próprias
- `config.py` + `settings_modules/ai.py` — `ANALYSIS_QUALITY_PROBE_*`, `ANALYSIS_TEXT_SENIORITY_PROBE_*`
- `docker-compose.yml` — as duas flags ligadas
- `ml/scripts/`: `corpus_frame_v3.py`, `train_text_probes_v3.py`, `sweep_probe_designs_v3.py`,
  `eval_seniority_fusion_v3.py`, `analyze_label_evidence_v3.py`, `finetune_text_heads_v3.py`
- `ml/reports/`: `text_probes_v3.md`, `label_evidence_v3.md`, `seniority_fusion_v3.md`

### 9.7 O que ainda impede o fechamento em produção

1. ~~`ml/models/` continua no `.gitignore`~~ — resolvido no §10.5, e reincidiu duas vezes.
2. ~~`ANALYSIS_EMBEDDINGS_ENABLED` só existe em `backend/.env`~~ — explícito no compose.
3. O rotulador do SambaNova está inteiramente em backoff de rate limit (~0,65 rótulo/min). As cabeças
   de resolução fina (`impact`/`clarity`/`ats`) melhoram com cada rótulo novo, então vale retreinar
   quando a fila andar.

---

## 10. Concluído: bullets viram modelo, insights viram ranking, e a suíte fecha

### 10.1 Classificador por bullet — três famílias de regex aposentadas

`METRICS_PATTERN`, `ACTION_VERBS` e `LEADERSHIP_WORDS` decidiam um fato por bullet varrendo o
documento inteiro. Medidos contra o **consenso de dois anotadores** de famílias de modelo diferentes,
sobre 4.682 bullets:

| atributo | regex F1 | sonda F1 | regex recall |
|---|---|---|---|
| `quantified` | 0,81 | **0,92** | 0,77 |
| `outcome` | 0,34 | **0,83** | 0,21 |
| `leadership` | 0,33 | **0,70** | 0,32 |

**`LEADERSHIP_WORDS` pontua 79,0% contra 80,1% da classe majoritária** — responder "não" para tudo
bate a regex que decidia o que aparece na tela. Em espanhol o recall de `ACTION_VERBS` é **0,03 sobre
60 positivos**: são oito formas fixas por idioma e o corpus escreve primeira pessoa do pretérito.

O modo de falha que resume tudo: *"supervisar la tensión y la corriente"* acendia `leadership` — está
supervisionando tensão elétrica, não pessoas. Igual a "gerenciamento de conteúdo".

`bullet_probe_v1`: 5.750 bullets de 764 currículos, 573 ocupações, GroupKFold pela ocupação.
**Sem janelamento, e isso é medição**: bullets têm média 15,8 palavras e máximo 44, nenhum alcança a
janela de 60, então o encoding é exato e não aproximação. Acurácia 92,8% / 83,8% / 85,6%.

**Transferência entre escritores é segura aqui**, diferente da qualidade: perde 1–3 pontos contra os
8,3 do `quality_target`. E o sentido com 1.227 linhas de treino empata com o inverso com 4.523 — a
cabeça está **saturada de dado**, então mais rótulo não ajuda. Isso foi medido, não suposto.

### 10.2 O teto agora é o rótulo, não o modelo

`outcome`: os dois anotadores concordam em 81,7% (**κ 0,54**) e a sonda faz 83,8%. Ela concorda com o
anotador A tanto quanto o anotador B concorda. **Não há o que retreinar** — conserta com rubrica.
O mistral chama 82% dos bullets de "outcome" contra 65% do 8b: é o mesmo viés de calibração
unidirecional do §7.2.2b, não ruído espalhado.

Mesmo limite já registrado para `clarity`/`ats` (§9.5) e `language` (§7.2.2b). São três agora.

### 10.3 Insights por ganho medido

`derive_insights` decidia *quais* sugestões aparecem por evidência, mas não *qual vem primeiro*: era
a ordem em que os `if`s rodam, com `high`/`medium`/`low` escrito à mão. Medido sobre 1.399 currículos
pelo caminho de produção real:

| melhoria | agrupado | dentro da banda |
|---|---|---|
| `add_metrics` | +14,58 | +2,90 |
| `use_action_verbs` | +8,66 | +1,73 |
| `add_education` | +0,29 | +0,33 |
| `relevant_links` | −0,46 | −0,08 |
| `add_skills` | −0,69 | −0,66 |
| **`education_target_gap`** | **−3,24** | **−0,80** |

**`education_target_gap` mede ganho negativo** — é mostrada a currículos que pontuam *mais alto* que
aqueles de quem ela é omitida. Era `priority="high"` e vinha primeiro; passa a última e `low`.

Três conservadorismos: sugestão não medida mantém a prioridade declarada e ordena depois das medidas
(`ats_keywords` dispara para todos, não tem grupo de contraste); os cortes são os **tercis dos
próprios ganhos**, sem limiar inventado; e o número **não vai para a tela**, só a posição.

**Ressalvas que não podem sumir:** é correlacional; o score previsto é o nosso próprio, então parte
do sinal é uma cabeça concordando com a outra sobre as mesmas frases; e o agrupado é confundido por
nível — `add_metrics` cai de +14,58 para +2,90 quando se fixa a banda.

### 10.4 Alinhamento de formação: resultado negativo, medido e revertido

Tentativa de trocar `_TECH_EDU_RE`/`_NON_TECH_EDU_RE` por similaridade no encoder. Construída, ligada,
e **revertida**. A suíte pegou no caso canônico: Biologia + Programador saiu como "alinhada".

| formação | alvo | alinhado? | margem |
|---|---|---|---|
| Enfermagem | Enfermeiro chefe | sim | +0,6130 |
| Ciência da Computação | Programador | sim | +0,3169 |
| **Biologia** | **Programador** | **não** | **+0,1842** |
| Análise e Desenv. de Sistemas | Desenvolvedor Backend | sim | +0,1523 |
| **Ingeniería en Sistemas** | **Desarrollador** | **sim** | **+0,1130** |

Alinhado mínimo 0,1130 **abaixo** de não-alinhado máximo 0,1842. As classes se sobrepõem: nenhum
limiar classifica nem esses dez pares fáceis.

**Por que a calibração proxy enganou:** pares ESCO comparam rótulo de ocupação com rótulo de ocupação,
mesmo registro. A tarefa real compara **área de estudo com cargo**, registros diferentes, e a escala
da margem se move com eles. O proxy mediu o encoder, não a decisão. Sinal ignorado: 68–72% de
acurácia já era medíocre e os limiares por idioma variavam 2,3×.

**Não há par rotulado no disco:** o corpus grava só o nível do diploma (12 strings distintas,
`Graduação`/`Bachelor`/`Máster`) e nunca a área. Isso move o item para perto do custo do `target_fit`.

### 10.5 A suíte fecha inteira — 166 testes, zero falhas

As 4 falhas herdadas eram **três defeitos reais**, não testes desatualizados:

1. **`loader_target_fit_model` era um shim que omitia `load_target_fit_ml_bundle`.** O `ImportError`
   acontecia na coleção, então os **dois** testes do arquivo sumiam em vez de falhar. *Desaparecer é
   pior que falhar.*
2. **`run_resume_analysis_task` abre com `connection.close()`** — correto num worker Celery real, mas
   a task roda inline no teste e fechava a conexão dele.
3. **`ml/data/synthetic/target_fit_smoke.jsonl` não existia** e estava sob `ml/data/*`: passaria aqui
   e falharia em qualquer clone.
4. `test_target_position_exposes_target_fit_policy_metadata` **fixava a heurística como resposta
   esperada** de um pilar que virou neural no §6. Virou dois casos: com encoder o provider é neural,
   sem encoder é a policy — o fallback continua testado sem continuar sendo o esperado.

### 10.6 A armadilha do §5.7 reincidiu duas vezes

`bullet_probe_v1` e `insight_gain_v1` são entrada de produto lida em inferência e estavam ignorados
pelo `.gitignore`. **Terceira ocorrência.** A diferença que importa: o bundle da sonda o `warmup`
pega alto com `SystemExit`; **a tabela de ganho degradava em silêncio**, voltando à ordem chutada com
uma linha de log. Fail-fast só cobre o que alguém lembrou de registrar.

`load_rows()` também passou a deduplicar por id. As 89 linhas repetidas em `prose.jsonl` **não são
cópias**: carregam texto de bullet diferente e `writer_model` diferente, e rótulo de bullet é chaveado
por `(id, índice)` — rotular uma linha e juntar na outra desalinha atributo com frase, em silêncio.

E `_round_robin` balanceia `(banda, idioma)` mas **não escritor**: os 600 primeiros saíram 100% de um
escritor só, não os ~74% previstos, porque os escritores foram anexados em bloco. `--writer` novo, e
a run agora imprime a distribuição de escritores.

### 10.7 O que falta, em ordem de custo

**Sem rótulo novo:** detector de idioma (não existe, vem da request) · evidência semântica de matching
(score já é cosseno, evidência ainda é interseção de token) · ~~caps 40/72 → abstenção calibrada~~
(feito no §11, mas **não** como este item previa) · ligar `llm_feedback` · PII → NER.

**Com anotação nova:** `target_fit` (35% policy em `orchestrator.py` + 22 `if`s de `target_seniority`,
vale ~3,5 pts) · alinhamento de formação (§10.4, precisa de área de estudo no corpus).

**Defeitos registrados e não consertados:**
- **A telemetria de `target_fit` mente por omissão.** O passo de embeddings roda depois da cascata e
  reescreve o provider para `target_fit_embedding_v1`, mas o score é `0,65 × embedding + 0,35 ×
  (ml ou policy)`. A tabela de providers esconde que 35% veio do outro caminho — mesmo espírito do bug
  de matching do §7.1.
- `education_target_gap` mede ganho negativo e continua sendo exibida, só que por último.

---

## 11. Concluído: abstenção por margem — e por que os caps ficaram

O roadmap (§7.1, §7.4) prometia trocar os caps de completude por "abstenção calibrada sobre a
incerteza do modelo". **A medição derrubou esse plano e justificou outro desenho.** Os dois
mecanismos cobrem falhas diferentes e ambos ficam.

### 11.1 O bug que apareceu no caminho: currículo sem resumo derrubava a análise

Achado porque o script de medição bateu nele. Assimetria treino/inferência: `embed_documents`
devolvia largura **0** quando todo texto do lote era vazio. No treino o corpus inteiro é encodado de
uma vez e alguma linha sempre tem conteúdo, então seção vazia virava vetor zero de 384. Na inferência
encoda-se **um** currículo: quem não tem resumo caía nesse ramo, a concatenação saía 1536 em vez de
1920, e a trava de largura recusava a linha.

**Alcance: 160 de 1.559 currículos (10,3%) têm seção vazia, e 134 deles é resumo ausente** — ordinário
em currículo real, não caso de borda.

O sintoma não parecia com a causa. Morria com `ModelAnswerRequired` mandando conferir
`ANALYSIS_QUALITY_PROBE_ENABLED` e o bundle — tudo correto e irrelevante. A trava do §9.6 fez o
trabalho dela: recusou uma linha que o modelo não devia ver. **O defeito era a linha chegar
malformada, não a trava reclamar.**

### 11.2 A premissa do roadmap era falsa

| grupo | n | confiança média | acurácia | cap morde |
|---|---|---|---|---|
| `adequate` | 1505 | 0,683 | 93,0% (n=675) | 0% |
| `low` | 54 | 0,669 | 87,5% (n=16) | 33% |
| `thin` | 50 | 0,674 | 85,7% (n=14) | 36% |

**A confiança não cai em currículo esparso.** Completude nunca foi proxy de incerteza, então não podia
ser substituída por uma. Pior: a acurácia cai enquanto a confiança fica parada — o modelo é confiante
onde erra.

### 11.3 Mas a incerteza prevê erro, e só uma medida mostrou isso

Sobre **691 rotulados** (642 acertos, 49 erros) — não os 16 de `low`:

| medida | AUC (acerto vs erro) |
|---|---|
| probabilidade máxima | 0,872 |
| **margem top-1 − top-2** | **0,880** |
| entropia | 0,805 |

Mesma ordem que o §6 achou para domínio: **margem separa onde valor absoluto não separa.** Ter parado
na primeira medida teria produzido a conclusão errada — "não há sinal de incerteza" — e matado um
mecanismo que funciona.

**Curva risco-cobertura** fixou o corte em vez de eu escolher:

| abstém | corte | acurácia no respondido | erros restantes |
|---|---|---|---|
| 0% | — | 92,9% | 49 |
| **10%** | **0,158** | **96,5%** | **22** |
| 15% | 0,223 | 97,4% | 15 |
| 30% | 0,391 | 98,8% | 6 |

Onde está o joelho é medido; sentar nele é política declarada.

### 11.4 O caso que salvou os caps

Um currículo **completamente vazio recebe 78 com margem 0,368** — ou seja, **confiante**. Vetor de
features todo zero cai no termo de viés da regressão logística.

**Nenhuma abstenção por confiança pega isso**, porque o modelo não está incerto: está respondendo com
segurança uma pergunta que nunca viu. É falha **fora da distribuição**, e completude é a variável certa
para ela.

Então o desenho final:

- **`LOW_CONFIDENCE_MARGIN` (0,158)** → dúvida *dentro* da distribuição. O currículo raso porém
  `adequate` é o caso que **só a margem pega** — o cap não o alcança.
- **Caps e portão de completude** → entrada degenerada, onde o modelo está confiantemente errado.

`analysisIntegrity` ganhou **`lowConfidenceTasks`**, separado de `degradedTasks`: um diz que o modelo
respondeu e a margem dele desconfia, o outro diz que uma regra respondeu. **O score continua
publicado** — a abstenção marca a resposta, não a retira.

### 11.5 O cap de 40 é inalcançável em produção

`allow_quality_neural = level != "insufficient"` corta o caminho neural antes da sonda, então um
currículo `insufficient` **nunca chega no modelo** e a análise recusa. O cap de 40 só se aplica no
golden snapshot, onde a heurística pode responder. Está documentado assim em `completeness.py`.

E a recusa culpava o artefato errado — mandava procurar bundle ausente quando o bundle estava correto.
Agora nomeia a causa real. **Segundo defeito da sessão com o mesmo padrão: o sintoma não parecia com a
causa e a mensagem mandava o operador para o lugar errado.**

### 11.6 O que continua não medido

O corpus tem **zero** currículos `insufficient` e só **16 rotulados** em `low`. Os valores 40 e 72
continuam **política declarada, não derivada**, e agora está escrito assim em vez de implícito. Os 3
currículos rotulados que o cap corta são amostra pequena demais para concluir qualquer coisa.

---

## 8. Backlog de senioridade (retomar quando o orçamento do 70b resetar)

1. **Rotular os 873 currículos** com `llama-3.3-70b-versatile` (~195/dia → ~4-5 dias).
   O renderizador dedicado (`render_for_labelling`) já inclui bullets e duração
2. **Revisão manual de ~50 rótulos** via `build_label_review_sample.py` (amostra estratificada:
   40% discordâncias, 20% grupos com divergência de idioma, 40% baseline)
3. **Completar os 40 grupos paralelos** restantes com
   `write_resume_prose_v3.py --only '^par'` (o filtro por regex já existe)
4. **Treinar o modelo de texto**: encoder multilíngue (XLM-R base ou multilingual MiniLM, não
   BERTimbau), `max_length` 256 (não 64 — não cabe currículo), e exportar bundle **completo**
   com `config.json`, tokenizer e `id2label` real em vez de `LABEL_0..3` — foi por isso que o
   `text_seniority_v1` morreu
5. **Retreinar `signals_ml`** com a transformação `log1p_v1` e gravar `feature_transform` no
   metadata, senão a trava do loader recusa o bundle
6. **Testes de guarda**: classe não-constante em inputs realistas variados; acurácia em
   **ocupações held-out**; concordância no subconjunto paralelo; drift de z-score no load
