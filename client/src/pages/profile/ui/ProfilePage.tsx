import { AppShell } from '@/widgets/app-shell';
import { useTranslation } from 'react-i18next';

import { ProfileCard } from './components/ProfileCard';
import { AccountStatusCard } from './components/AccountStatusCard';
import { SecurityCard } from './components/SecurityCard';
import { PreferencesCard } from './components/PreferencesCard';

import '@/shared/ui/sr-controls/SrControls.css';
import '@/shared/ui/layout/TwoColumnStack.css';
import './ProfilePage.css';

export function ProfilePage() {
  const { t } = useTranslation();

  return (
    <AppShell>
      <main className="sr-profile" aria-label={t('profile.title')}>
        <header className="sr-profile__header">
          <div className="sr-profile__title">
            <h1 className="sr-profile__h1">{t('profile.title')}</h1>
            <p className="sr-profile__subtitle">{t('profile.subtitle')}</p>
          </div>
        </header>

        <div className="sr-profile__grid" role="presentation">
          <section className="sr-profile__main-col" aria-label={t('profile.title')}>
            <ProfileCard />
            <SecurityCard />
          </section>

          <section className="sr-profile__side-col" aria-label={t('profile.preferences')}>
            <AccountStatusCard />
            <PreferencesCard />
          </section>
        </div>
      </main>
    </AppShell>
  );
}


