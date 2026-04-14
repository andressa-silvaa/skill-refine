from __future__ import annotations

from django.db import migrations


# Previously stored Portuguese UI strings; now stable keys for client i18n.
_LEGACY_PT_TO_KEY = {
    "Versão inicial": "initial",
    "Resumo profissional atualizado": "professional_summary_updated",
    "Nome/contato atualizado": "name_contact_updated",
    "E-mail atualizado": "email_updated",
    "Cargo alvo atualizado": "target_position_updated",
    "Experiência profissional alterada": "experience_updated",
    "Formação acadêmica alterada": "education_updated",
    "Habilidades alteradas": "skills_updated",
    "Idiomas alterados": "languages_updated",
    "Tema do currículo alterado": "theme_updated",
    "Alterações gerais": "general_changes",
    "Versão restaurada": "version_restored",
    # Dev / test fixtures
    "Initial": "initial",
}

_TARGET_KEYS = frozenset(_LEGACY_PT_TO_KEY.values())


def forwards(apps, schema_editor):
    ResumeVersion = apps.get_model("resumes", "ResumeVersion")
    for row in ResumeVersion.objects.iterator():
        summary = row.change_summary_json
        if not isinstance(summary, list):
            continue
        new_summary: list[str] = []
        for item in summary:
            if not isinstance(item, str):
                continue
            if item in _TARGET_KEYS:
                new_summary.append(item)
            elif item in _LEGACY_PT_TO_KEY:
                new_summary.append(_LEGACY_PT_TO_KEY[item])
            else:
                new_summary.append(item)
        if new_summary != summary:
            row.change_summary_json = new_summary
            row.save(update_fields=["change_summary_json"])


def backwards(apps, schema_editor):
    # Keys are not reverted to Portuguese (lossy); no-op.
    pass


class Migration(migrations.Migration):
    dependencies = [("resumes", "0004_add_resume_exports")]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
