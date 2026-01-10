import { AppShell } from '@/widgets/app-shell';

import { ProfileCard } from './components/ProfileCard';
import { AccountStatusCard } from './components/AccountStatusCard';
import { SecurityCard } from './components/SecurityCard';
import { PreferencesCard } from './components/PreferencesCard';

import '@/shared/ui/sr-controls/SrControls.css';
import '@/shared/ui/layout/TwoColumnStack.css';
import './ProfilePage.css';

export function ProfilePage() {
  return (
    <AppShell>
      <main className="sr-profile" aria-label="Perfil do usuário">
        <header className="sr-profile__header">
          <div className="sr-profile__title">
            <h1 className="sr-profile__h1">Perfil</h1>
            <p className="sr-profile__subtitle">Gerencie suas informações pessoais e preferências.</p>
          </div>
        </header>

        <div className="sr-profile__grid" role="presentation">
          <section className="sr-profile__main-col" aria-label="Perfil e segurança">
            <ProfileCard />
            <SecurityCard />
          </section>

          <section className="sr-profile__side-col" aria-label="Preferências">
            <AccountStatusCard />
            <PreferencesCard />
          </section>
        </div>
      </main>
    </AppShell>
  );
}


