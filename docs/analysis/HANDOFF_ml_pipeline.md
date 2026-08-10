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
| matching | quando há vaga | `matching_embeddings` | migrado para neural nesta sessão |

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
- `ml/data/raw/resumes_v3/prose.jsonl` — **864 currículos** com prosa gerada
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

### Código de produção alterado nesta sessão
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
`apps.analysis.tests`: 95 testes, **3 falhas + 2 erros pré-existentes** (target_fit ml loader,
run_creates_pending, target_fit policy metadata, quality logits 72≠75, synthetic jsonl ausente).
Golden snapshot passa. Qualquer coisa além dessas 5 é regressão nova.

### Git
Branch `fix/seniority-thresholds-text-fusion`, 3 commits feitos. **Tudo desta sessão está
sem commit.**

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

### 5.6 Outros
- `ConnectionResetError` **não** é subclasse de `URLError` — capturar `OSError`
- `urllib` é bloqueado por Cloudflare (erro 1010) sem `User-Agent` customizado
- Job em background com stdout num pipe não drenado **trava** ao encher o buffer; redirecionar
  para arquivo
- Uma exceção dentro de `pool.map` mata a run inteira; isolar cada item

---

## 6. Próxima tarefa: inferência de ocupação e domínio via ESCO

### Problema
`infer_domain_category` (`tasks/target_fit/domain_inference.py:273`) classifica o domínio por
**substring de palavra-chave** sobre 13 categorias fixas (`health`, `education`, `legal`,
`finance`, `engineering`, `marketing`, `sales`, `technology`, `administrative`, `science`, `hr`,
`operations`, `creative`, mais `general`). É heurística pura, tem conjunto fechado, e falha em
qualquer ocupação fora dos dicionários.

### Solução proposta
**Classificação zero-shot por recuperação semântica**, sem treino e sem rótulo:

1. Embedar o texto do currículo com o MiniLM multilíngue já carregado
   (`get_embeddings_model`, `paraphrase-multilingual-MiniLM-L12-v2`)
2. Embedar os labels das 1.701 ocupações ESCO **no idioma do currículo**
3. Cosseno, top-k ocupações mais próximas
4. Derivar o domínio do **código ISCO-08** da ocupação vencedora

Isso é PLN real, usa taxonomia oficial internacional, cobre qualquer ocupação, e não consome
orçamento de rotulagem.

### Detalhe crítico: qual nível do ISCO usar
**Grupos ISCO de 1 dígito são nível de qualificação, não domínio.** O grupo 2 ("Profissionais")
junta médico, advogado e engenheiro. Mapear 1 dígito → domínio produz lixo.

O domínio está no prefixo de **2 dígitos**:

| ISCO | Domínio |
|---|---|
| 21 | engineering / science |
| 22 | health |
| 23 | education |
| 24 | finance / administrative |
| 25 | technology |
| 26 | legal / creative |
| 3x | technicians (usar 3 dígitos para desambiguar) |
| 33 | finance / administrative |
| 34 | legal / creative / hr |
| 5x | sales / operations |
| 7x, 8x | operations |

A tabela acima precisa ser completada consultando a estrutura ISCO-08. O campo `isco` no
`esco_occupations.jsonl` vem no formato `2165.4.1` — o prefixo antes do primeiro ponto é o código
ISCO de 4 dígitos.

### Requisitos de implementação
- **Cascata, não substituição.** Novo passo `domain_embeddings` **antes** da heurística de
  palavra-chave, que permanece como fallback (exigência de arquitetura do TCC)
- **Cache dos embeddings do ESCO.** 1.701 × 384 dimensões é pequeno; calcular uma vez por processo
  (ou pré-computar em disco) e reusar. Nunca reembedar por requisição
- **Retornar o contrato atual** (`domainCategory`, `confidence`, `evidenceTokens`) para não quebrar
  os consumidores em `fit_signals.py:200,242`. Enriquecer com a ocupação ESCO e o código ISCO em
  campos novos
- **Confiança pelo gap**, não pelo cosseno absoluto: diferença entre o top-1 e o top-2. Cosseno
  alto com gap pequeno significa ambiguidade, não certeza
- **Idioma**: usar o label ESCO no idioma do currículo. Os labels pt/es trazem variantes de gênero
  separadas por `/` (`Operador.../Operadora...`) — separar e usar uma
- Sem comentários em código, e se algum for inevitável, em inglês (preferência do repositório)

### Como validar
- Os 864 currículos do corpus têm a **ocupação ESCO verdadeira** nos metadados
  (`occupation.uri`, `occupation.isco`). Isso é um conjunto de avaliação pronto e gratuito:
  medir acurácia top-1 e top-5 de recuperação da ocupação, e acurácia do domínio derivado
- Comparar contra a heurística atual no mesmo conjunto — é o número que vai para o TCC
- Medir por idioma separadamente (pt/en/es), para provar que funciona nos três
- Rodar `apps.analysis.tests`; qualquer falha além das 5 pré-existentes é regressão

---

## 7. Backlog de senioridade (retomar quando o orçamento do 70b resetar)

1. **Rotular os 864 currículos** com `llama-3.3-70b-versatile` (~195/dia → ~4-5 dias).
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
