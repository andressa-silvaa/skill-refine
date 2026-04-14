import type { TFunction } from 'i18next';

/** API may still return legacy Portuguese strings from rows not yet migrated. */
const LEGACY_TO_KEY: Record<string, string> = {
  'Versão inicial': 'initial',
  'Resumo profissional atualizado': 'professional_summary_updated',
  'Nome/contato atualizado': 'name_contact_updated',
  'E-mail atualizado': 'email_updated',
  'Cargo alvo atualizado': 'target_position_updated',
  'Experiência profissional alterada': 'experience_updated',
  'Formação acadêmica alterada': 'education_updated',
  'Habilidades alteradas': 'skills_updated',
  'Idiomas alterados': 'languages_updated',
  'Tema do currículo alterado': 'theme_updated',
  'Alterações gerais': 'general_changes',
  'Versão restaurada': 'version_restored',
  Initial: 'initial',
};

export function translateVersionChangeLabel(t: TFunction, raw: string): string {
  const key = LEGACY_TO_KEY[raw] ?? raw;
  return t(`versionHistory.changeLabels.${key}`, { defaultValue: raw });
}
