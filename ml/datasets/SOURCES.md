# Fontes de dados — Pipeline ML (Skill Refine TCC)

Documentação de fontes de vagas e currículos para o pipeline de dataset multilíngue (PT-BR, EN-US, ES-ES). **Nenhum dado sensível (PII)** deve ser versionado; dados brutos ficam em `data/raw/` (gitignored quando contiverem dados reais).

---

## 1. Vagas (jobs)

### 1.1 Datasets públicos (preferível)

| Nome | Licença | Idioma | Tamanho | Link / Data | Observação |
|------|---------|--------|---------|-------------|------------|
| **Kaggle Job Postings (ex.: Real/Fake Job Posting)** | Kaggle Terms | EN | ~18k | [Kaggle](https://www.kaggle.com/datasets) — buscar "job postings" | Baixar manualmente; colocar em `data/raw/jobs/` |
| **O*NET Occupational Data** | Public domain (US) | EN | Grande | [O*NET](https://www.onetcenter.org/database.html) | Descrições de ocupações; útil para vocabulário |
| **Vagas públicas PT-BR (ex.: dados abertos)** | Verificar por dataset | PT | Variável | Portal de Dados Abertos, Kaggle PT | Preferir CSV/JSON com título + descrição |
| **Vagas ES** | Verificar por dataset | ES | Variável | Kaggle / dados abertos ES | Idem |

**Uso no pipeline:** `collect_jobs.py --source <path> --language pt` lê de arquivos locais (CSV/JSON) em `data/raw/jobs/` ou caminho configurado. **Não há download automático** por padrão; o usuário baixa e coloca no diretório.

### 1.2 Scraping (opcional / desativado por padrão)

Se permitido no contexto do TCC e conforme termos de uso dos sites:

- **Interface:** `collect_jobs.py --source scraping --language pt` (ou en/es).
- **Requisitos:** rate limit, backoff, respeito a `robots.txt` e termos.
- **Status:** implementado como opcional; **desativado por default**. Ativar apenas se houver autorização explícita.

---

## 2. Currículos

### 2.1 Currículos sintéticos (recomendado para TCC)

- **Fonte:** gerados por `generate_synthetic_resumes.py`.
- **Idioma:** PT-BR primeiro; EN/ES com mesmos templates e variações.
- **Conteúdo:** cargos (dev, data, produto, design), senioridades (intern/junior/mid/senior), experiências com/sem métricas, skills, links placeholder (`[LINK_LINKEDIN]`, `[LINK_GITHUB]`).
- **Balanceamento:** inclui “currículos ruins” (sem métricas, frases vagas) para classes de qualidade.
- **Sem PII:** nomes/empresas são fictícios; e-mails/telefones já são placeholders no gerador.

### 2.2 Currículos reais anonimizados (opcional)

Se usar currículos reais:

- **Script:** `anonymize_resumes.py` — remove/mascara: nomes, e-mails, telefones, URLs pessoais; empresas muito específicas → "Empresa X".
- **Armazenamento:** versão raw **fora do repositório** (gitignored); apenas versão anonimizada em `data/processed/` ou `data/raw/` (sem PII).
- **Identificador:** cada currículo tem `resume_id` único estável para split sem vazamento.

---

## 3. Rotulagem

- **Heurísticas:** `labeling/heuristics/` — listas de verbos de ação e cabeçalhos de seção por idioma (`verbs_pt.json`, `section_headers_pt.json`, etc.).
- **Semi-automática:** `label_with_heuristics.py` gera rótulos iniciais; `export_for_review.py` exporta para revisão manual; `import_reviewed_labels.py` reimporta como “gold” (v1).

---

## 4. Convenções

- **language:** sempre presente; valores `pt`, `en`, `es` (ou `pt-BR`, `en-US`, `es-ES` conforme schema; normalizar no pipeline).
- **resume_id:** obrigatório em todos os registros que pertencem a um currículo (split por currículo).
- **Sem PII em outputs:** validação e relatórios não devem expor e-mail, telefone, nome real ou link real.

Data da última atualização: 2025-02 (documento vivo; atualizar ao adicionar fontes).
