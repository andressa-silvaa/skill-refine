/**
 * Keys stored in ResumeVersion.change_summary_json (API) and translated on the version-history screen.
 * They must never appear as resume skill chips if mis-synced into skills/tags.
 * Keep in sync with backend version_services._build_change_summary and restore_version.
 */
export const VERSION_CHANGE_SUMMARY_KEYS = new Set([
  'initial',
  'professional_summary_updated',
  'name_contact_updated',
  'email_updated',
  'target_position_updated',
  'experience_updated',
  'education_updated',
  'skills_updated',
  'languages_updated',
  'theme_updated',
  'general_changes',
  'version_restored',
]);
