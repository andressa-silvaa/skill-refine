# Histórico de Versões — Implementação Real

## 1. Estrutura existente era suficiente?

**Não.** O banco não tinha suporte a versionamento de currículos. Existiam apenas:

- Tabelas de currículo: `resumes`, `resume_contacts`, `resume_experiences`, etc.
- Nenhuma tabela de histórico, snapshots ou auditoria por versão.
- O app `audit` tem logs genéricos (ação, metadados), não snapshots de currículo.

Por isso foi necessária uma modelagem nova dedicada a versões.

---

## 2. Modelagem adotada

Foi criada a tabela **`resume_versions`** com:

| Campo               | Tipo        | Descrição |
|---------------------|------------|-----------|
| `id`                | UUID       | PK        |
| `resume_id`         | FK         | Currículo |
| `user_id`           | FK         | Dono (ownership) |
| `version_number`    | int        | Número sequencial por currículo |
| `is_current`        | bool       | Apenas uma versão atual por currículo |
| `snapshot_json`     | JSON       | Estado completo do currículo (mesmo formato da API `data`) |
| `change_summary_json` | JSON (array) | Resumo das alterações (ex.: "Resumo atualizado", "Experiência alterada") |
| `score`             | int, null  | Score da versão |
| `created_at` / `updated_at` | datetime | Auditoria |

Regras:

- **Unicidade:** `(resume_id, version_number)` único.
- **Índices:** `(resume, -version_number)` e `(user, -created_at)` para listagens.
- O **snapshot** segue o mesmo formato do payload de detalhe do currículo (`themeId`, `contact`, `experiences`, etc.) para permitir visualizar e restaurar.

---

## 3. Como o versionamento passou a funcionar

### Criação de versões

- **Após criar currículo** (`POST /resumes`): é criada a versão 1 (is_current=True), com snapshot do estado inicial e change_summary `["Versão inicial"]`.
- **Após atualizar currículo** (`PATCH /resumes/:id`): o serviço refaz o prefetch do currículo, monta o novo snapshot e compara com o da versão atual (por JSON). Se for **igual**, não cria nova versão. Se for **diferente**:
  - Marca a versão atual como `is_current=False`
  - Cria nova versão com `version_number` incrementado, `is_current=True`, novo snapshot e um **change_summary** heurístico (resumo, contato, cargo, experiências, formação, habilidades, idiomas, tema).

Assim evitamos versões duplicadas quando não há mudança real.

### Resumo de alterações (change_summary)

É gerado por heurística no backend, comparando o snapshot anterior com o novo (ex.: “Resumo profissional atualizado”, “Experiência profissional alterada”, “Formação acadêmica alterada”). Estrutura: lista de strings, reutilizável para exibição e futuras melhorias.

### Endpoints

- **GET /resumes/api/versions** — Lista versões do usuário. Query opcional: `?resume_id=<uuid>` para filtrar por currículo.
- **GET /resumes/api/resumes/:resume_id/versions/:version_id** — Detalhe da versão (inclui snapshot).
- **POST /resumes/api/resumes/:resume_id/versions/:version_id/restore** — Restaura a versão: aplica o snapshot no currículo atual e cria uma **nova** versão (restauração vira a nova “atual”), mantendo o histórico.

### Restaurar

1. Valida ownership (currículo e versão do usuário).
2. Aplica o `snapshot_json` no currículo (resume + contact + experiences, educations, skills, languages).
3. Marca a versão antiga como não atual e cria nova versão com o snapshot restaurado e change_summary `["Versão restaurada"]`.

### Frontend

- A tela “Histórico de Versões” deixou de usar mocks e passou a usar:
  - **GET /resumes/api/versions** (e opcionalmente `?resume_id=`) para a lista.
  - **POST .../restore** para restaurar, com feedback de sucesso/erro e refetch do histórico.
- Filtros por currículo usam a lista de currículos já carregada (`useResumes`) e o filtro por `resume_id` na API de versões.
- Loading, estado vazio e erro estão tratados; i18n e mensagens de sucesso/erro ao restaurar foram adicionadas.

---

## 4. Integração com o fluxo existente

- **Editar e salvar currículo:** continua usando `create_resume_draft` / `update_resume_draft`; ao final das views, chama-se `maybe_create_version_after_save`, que decide se cria ou não uma nova versão.
- **Restaurar versão:** o currículo é atualizado de verdade; a listagem de currículos e o detalhe refletem o estado restaurado; o histórico ganha a nova versão “restaurada”.
- Score e demais dados do currículo vêm do modelo principal; as versões guardam o score no momento do snapshot.

---

## 5. Testes

Foram adicionados testes em `apps.resumes.tests.test_version_history`:

- Criação da primeira versão no primeiro save.
- Criação de nova versão em update com mudanças.
- Listagem de versões (global e por resume_id).
- Obtenção de versão por id (com ownership).
- Restore atualizando currículo e criando nova versão.
- Restore com usuário errado retornando None.

Todos executados com:  
`python manage.py test apps.resumes.tests.test_version_history --noinput`.
