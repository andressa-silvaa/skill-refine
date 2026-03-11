# Diagramas UML - Skill Refine

Diagramas de classes baseados nos modelos Django do backend.

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `core-domain.puml` | Domínio principal: User, Resume, ResumeAnalysis, ResumeVersion, ResumeExport, AuditLog, Notification |
| `resume-details.puml` | Detalhes do currículo: Resume, ResumeContact, ResumeExperience, ResumeExperienceBullet, ResumeEducation, ResumeSkill, ResumeLanguage, ResumeTag, ResumeSectionOrder |
| `core-domain.png` / `.svg` | Renderização visual do core domain |
| `resume-details.png` / `.svg` | Renderização visual dos detalhes do currículo |

## Regenerar diagramas

### Com Docker

```bash
# PNG
docker run --rm -v "$(pwd):/data" -w /data plantuml/plantuml -tpng docs/uml/*.puml

# SVG
docker run --rm -v "$(pwd):/data" -w /data plantuml/plantuml -tsvg docs/uml/*.puml
```

### Windows (PowerShell)

```powershell
docker run --rm -v "c:/Skill-Refine-TCC:/data" -w /data plantuml/plantuml -tpng docs/uml/core-domain.puml docs/uml/resume-details.puml
docker run --rm -v "c:/Skill-Refine-TCC:/data" -w /data plantuml/plantuml -tsvg docs/uml/core-domain.puml docs/uml/resume-details.puml
```

### Com PlantUML instalado localmente

```bash
plantuml -tpng docs/uml/*.puml
plantuml -tsvg docs/uml/*.puml
```

## Fonte dos modelos

- **accounts:** `backend/src/apps/accounts/infrastructure/models.py`
- **resumes:** `backend/src/apps/resumes/infrastructure/models.py`
- **analysis:** `backend/src/apps/analysis/models.py`
- **audit:** `backend/src/apps/audit/models.py`
- **notifications:** `backend/src/apps/notifications/models.py`
- **shared:** `backend/src/shared/db/models.py`
