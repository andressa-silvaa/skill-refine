import { AppShell } from '@/widgets/app-shell';
import { useTranslation } from 'react-i18next';

import { AppearanceSettingsCard, AccentColorSettingsCard, GeneralSettingsCard, PrivacySettingsCard } from '@/widgets/settings';

import '@/shared/ui/sr-controls/SrControls.css';
import '@/shared/ui/layout/TwoColumnStack.css';
import './SettingsPage.css';

export function SettingsPage() {
  const { t } = useTranslation();

  return (
    <AppShell>
      <main className="sr-settings" aria-label={t('settings.title')}>
        <header className="sr-settings__header">
          <div>
            <h1 className="sr-settings__h1">{t('settings.title')}</h1>
            <p className="sr-settings__subtitle">{t('settings.subtitle')}</p>
          </div>
        </header>

        <div className="sr-settings__grid" role="presentation">
          <section className="sr-settings__main-col" aria-label={t('settings.general')}>
            <GeneralSettingsCard />
            <PrivacySettingsCard />
          </section>

          <section className="sr-settings__side-col" aria-label={t('settings.appearanceTitle')}>
            <AccentColorSettingsCard />
            <AppearanceSettingsCard />
          </section>
        </div>
      </main>
    </AppShell>
  );
}


