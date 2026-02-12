# Políticas de rotulagem e definição de tarefas — Análise de currículo (multilíngue)

Este documento define as tarefas do pipeline de ML para análise de currículo, as políticas de labels, formatos de dataset e critérios de avaliação. Idiomas suportados: **pt** (PT-BR), **en** (EN-US), **es** (ES-ES).

---

## Decisão de i18n (contrato de saída)

**Opção adotada: Opção 1 — Backend retorna chaves canônicas + params, frontend traduz.**

- O backend **nunca** retorna texto pronto em um idioma; retorna `key` (ex.: `analysis.insights.improvements.add_metrics`) e `params` opcionais (ex.: `{ "section": "experience" }`).
- O frontend usa o i18n existente (PT/EN/ES) para renderizar `t(key, params)`.
- **Vantagens**: uma única fonte de verdade para textos, consistência entre idiomas, evolução de copy sem retreinar modelo, sem duplicar dicionários no backend.

**Formato de insight na API:**

```json
{
  "key": "analysis.insights.improvements.add_metrics",
  "priority": "high",
  "params": { "section": "experience" }
}
```

Todos os textos exibidos ao usuário vêm do frontend via chaves; o backend só persiste e devolve `key` + `params`.

---

## Tarefa A — Classificação de senioridade

**Objetivo:** prever o nível de senioridade do candidato a partir do texto do currículo.

### Labels (internos, estáveis)

| Valor interno | Descrição breve | Uso na UI (i18n) |
|---------------|-----------------|------------------|
| `intern`      | Estágio         | analysis.seniority.intern |
| `junior`      | Júnior          | analysis.seniority.junior |
| `mid`         | Pleno           | analysis.seniority.mid |
| `senior`      | Sênior          | analysis.seniority.senior |

Casos ambíguos (ex.: “Pleno/Sênior”): rotular como o **nível mais alto** indicado (ex.: `senior`). Se não houver sinal claro, usar `mid` como default conservador.

### Política objetiva (sinais no texto)

1. **Anos de experiência** (inferidos de datas ou menções explícitas):
   - 0–1 ano, “estágio”, “trainee” → `intern`
   - 1–3 anos, “júnior” → `junior`
   - 3–6 anos, “pleno”, “mid” → `mid`
   - 6+ anos, “sênior”, “lead”, “principal” → `senior`
2. **Liderança**: “liderar”, “coordenação”, “mentoria” → tendência a `mid`/`senior`.
3. **Escopo**: “global”, “multi-equipe” → tendência a `senior`.
4. **Títulos**: cargo contendo “Senior”, “Lead”, “Principal” → `senior`; “Junior”, “Intern” → conforme o termo.

### Formato do dataset (Tarefa A)

Cada exemplo:

- `input_text`: texto do currículo (ou concatenação de seções relevantes: experiência + resumo).
- `label`: uma de `intern` | `junior` | `mid` | `senior`.
- `language`: `pt` | `en` | `es`.
- `source`: `manual` | `heuristic` | `revisado`.
- `confidence`: 0.0–1.0 (opcional).

### Saída do modelo (API)

- `seniority_class`: um dos valores acima.
- `seniority_confidence`: float em [0, 1] (opcional).

---

## Tarefa B — Detecção/segmentação de seções

**Decisão: Opção B1 — Classificação por sentença/linha.**

- Cada **linha ou bloco** de texto recebe um único label de seção.
- Justificativa: mais simples para MVP, suficiente para extrair estrutura (experiência, educação, habilidades, etc.), menor esforço de rotulagem e de avaliação do que NER/BIO.

### Lista de seções suportadas

| Label        | Descrição (PT)        | Uso i18n (se necessário) |
|-------------|------------------------|---------------------------|
| `EXPERIENCE`| Experiência profissional | analysis.sections.experience |
| `EDUCATION` | Formação acadêmica    | analysis.sections.education |
| `SKILLS`    | Habilidades           | analysis.sections.skills |
| `PROJECTS`  | Projetos              | analysis.sections.projects |
| `SUMMARY`   | Resumo / Objetivo     | analysis.sections.summary |
| `CONTACT`   | Contato               | analysis.sections.contact |
| `OTHER`     | Outros                | analysis.sections.other |

### Guidelines de rotulagem

- Uma linha = uma sentença ou um título de seção (ex.: “Experiência profissional” → `EXPERIENCE`).
- Conteúdo sob um título pertence à mesma seção até o próximo título reconhecível.
- Datas, cargos e empresas na área de experiência → `EXPERIENCE`; instituição e curso → `EDUCATION`; lista de tecnologias/competências → `SKILLS`.
- Tudo que não se encaixar → `OTHER`.

### Formato do dataset (Tarefa B)

Por exemplo (por linha):

- `line_text`: string.
- `label`: um de `EXPERIENCE` | `EDUCATION` | `SKILLS` | `PROJECTS` | `SUMMARY` | `CONTACT` | `OTHER`.
- `language`: `pt` | `en` | `es`.
- `resume_id`: identificador do currículo (para split sem vazamento).
- `source`, `confidence`: opcionais.

### Métricas

- F1 por classe (macro e micro).
- Acurácia.
- Matriz de confusão (por idioma e global).

---

## Tarefa C — Pontuação de qualidade por critérios (explicável)

**Objetivo:** score geral (0–100) e critérios objetivos e explicáveis.

**Decisão: Regressão 0–100** para o score geral, com features heurísticas mantidas para explicabilidade (enriquece o TCC e a UI).

### Critérios mínimos (features heurísticas)

1. **Métricas numéricas**: presença de %, R$, números, KPIs (ex.: “aumentou vendas em 20%”) → `has_metrics`.
2. **Verbos de ação**: listas por idioma (pt: liderou, implementou, desenvolveu…; en: led, implemented, developed…; es: lideró, implementó…) → `has_action_verbs`.
3. **Clareza/concisão**: tamanho de sentenças, repetição de palavras (proxy) → heurística + eventual proxy de modelo.
4. **Links relevantes**: LinkedIn, GitHub, portfolio → `has_relevant_links`.

### Formato do dataset (Tarefa C)

- `input_text`: texto do currículo (ou seções).
- `label_score`: inteiro 0–100 (regressão).
- `language`: `pt` | `en` | `es`.
- `feature_flags`: ex. `{ "has_metrics": true, "has_links": true, "has_action_verbs": true }` para auditoria e baseline.

### Saída do modelo (API)

- `score`: 0–100.
- `taskScores`: ex. `{ "ats": 92, "clarity": 78, "seniority": 0 }` (podem vir de submodelos ou heurísticas).
- Insights de qualidade usam **chaves canônicas** (ex.: `analysis.insights.improvements.add_metrics` com `params.section`).

### Métricas

- MSE, MAE, R² por idioma e global.
- Correlação entre score e feature_flags (baseline heurístico).

---

## Tarefa D — Matching vaga ↔ currículo

**Objetivo:** dado `job_text` + `resume_text`, retornar `match_score` (0–100) e `top_skill_matches`.

**Decisão: D1 — Bi-encoder.**

- Embeddings separados para vaga e currículo; score por similaridade de cosseno.
- Top skills/tópicos por overlap (TF-IDF ou embeddings por skill).
- Justificativa: bom custo/benefício, mensurável, evita cross-encoder pesado.

### Formato do dataset (Tarefa D)

- `job_text`: texto da vaga.
- `resume_text`: texto do currículo.
- `language`: `pt` | `en` | `es` (par vaga–currículo no mesmo idioma, ou definir política para misto).
- `label_match`: binário (match / no-match) ou score 0–100.
- `resume_id`: para split **por currículo** (evitar vazamento: mesmo currículo não aparece em train e test).

### Split

- Split por `resume_id`: todos os pares que contêm um dado `resume_id` vão para o mesmo conjunto (train/val/test).

### Saída do modelo (API)

- `match_score`: 0–100.
- `top_skill_matches`: lista de strings (skills/tópicos em comum ou mais relevantes).

---

## Estratégia de dataset e splits

- **language** obrigatório em todo exemplo (`pt` | `en` | `es`).
- **Normalização**: remoção/anonimização de PII (nomes, e-mails, telefones) em scripts; texto normalizado (unicode, espaços).
- **Split**:
  - Por `resume_id` (e, na Tarefa D, por par vaga–currículo sem repetir mesmo currículo em conjuntos diferentes).
  - Proporção sugerida: 70% train, 15% val, 15% test (estratificado por idioma quando possível).
- **Validação**: schema JSON com campos obrigatórios, enums de labels, distribuição por idioma; relatório de estatísticas (counts por label/idioma/split).

---

## Checklist de avaliação

- [ ] Métricas por tarefa (A: F1/acc; B: F1 macro/micro; C: MSE/MAE/R²; D: accuracy/AUC ou MSE no score).
- [ ] Métricas por idioma (pt, en, es) quando aplicável.
- [ ] Matriz de confusão para tarefas de classificação (A, B).
- [ ] Baseline heurístico para comparação (Tarefa C e, se aplicável, D).

---

## Chaves canônicas de insights (exemplos para i18n)

O frontend deve ter chaves para todas as `key` retornadas pelo backend. Exemplos:

**Pontos fortes (strengths):**

- `analysis.insights.strengths.clear_structure`
- `analysis.insights.strengths.education_aligned`
- `analysis.insights.strengths.professional_summary`

**Pontos de melhoria (improvements):**

- `analysis.insights.improvements.add_metrics` (params: `section` opcional)
- `analysis.insights.improvements.ats_keywords`
- `analysis.insights.improvements.executive_summary`
- `analysis.insights.improvements.relevant_links`

Prioridade sempre: `high` | `medium` | `low` (já traduzidas no front: `analysis.priorityHigh`, etc.).
