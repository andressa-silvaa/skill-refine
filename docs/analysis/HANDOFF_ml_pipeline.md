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
| quality | **78%** | `heuristics` | precisa de corpus rotulado — não iniciado |
| seniority | 12% | `rule_policy` | corpus gerado, rotulagem em andamento |
| target_fit | 10% | `target_fit_embedding_v1` | já é neural (MiniLM multilíngue) |
| matching | quando há vaga | `matching_embeddings` | neural desde a sessão anterior |
| domínio/ocupação | entra em target_fit | `domain_embeddings` | migrado para recuperação ESCO (§6) |

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
`apps.analysis.tests`: 116 testes (21 novos em `test_domain_inference_esco.py`), **3 falhas + 2
erros pré-existentes** (target_fit ml loader, run_creates_pending, target_fit policy metadata,
quality logits 72≠75, synthetic jsonl ausente). Golden snapshot passa. Qualquer coisa além dessas
5 é regressão nova.

### Git
Branch `fix/seniority-thresholds-text-fusion`.

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
| `has_metrics`, `has_action_verbs`, `has_leadership`, termos de estágio | `METRICS_PATTERN`, `ACTION_VERBS`, `LEADERSHIP_WORDS`, `_INTERNSHIP_RE` | classificador **por bullet** (~4.4k bullets no corpus) | desenho do gerador + verificação do professor |
| `insights` (quais forças/melhorias mostrar) | `derive_insights`: if/else sobre as flags | ranking pelas cabeças acima, por ganho esperado | nenhum novo |
| caps de completeness (40/72) | tabela fixa | abstenção calibrada sobre a incerteza do modelo | nenhum novo |

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

### 7.2.3 O teto por minuto é o que trava os jobs, não o diário

O 8b tem **6.000 tokens/min**. A ~1,9k tokens por currículo de prosa, isso são ~3 itens/min: o
default de `--workers 2 --delay 6` tenta ~20/min e o job passa a vida em backoff de 429. Use
`--delay 10` ou mais. E nunca rode um job de background com stdout num pipe de `grep`: o pipe não
drenado esconde justamente as mensagens de 429 (§5.6).

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
defensável na banca é: *o modelo julga, o código mede*. O que muda é que os **caps** derivados da
medição (40/72) deixam de ser constantes e passam a ser abstenção calibrada na incerteza do modelo.

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
