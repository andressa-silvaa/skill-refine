import { AppShell } from '@/widgets/app-shell';

import { AppearanceSettingsCard } from './components/AppearanceSettingsCard';
import { AccentColorSettingsCard } from './components/AccentColorSettingsCard';
import { GeneralSettingsCard } from './components/GeneralSettingsCard';
import { PrivacySettingsCard } from './components/PrivacySettingsCard';

import '@/shared/ui/sr-controls/SrControls.css';
import '@/shared/ui/layout/TwoColumnStack.css';
import './SettingsPage.css';

export function SettingsPage() {
  return (
    <AppShell>
      <main className="sr-settings" aria-label="Configurações do usuário">
        <header className="sr-settings__header">
          <div>
            <h1 className="sr-settings__h1">Configurações</h1>
            <p className="sr-settings__subtitle">Gerencie preferências e comportamentos da sua conta.</p>
          </div>
        </header>

        <div className="sr-settings__grid" role="presentation">
          <section className="sr-settings__main-col" aria-label="Geral e privacidade">
            <GeneralSettingsCard />
            <PrivacySettingsCard />
          </section>

          <section className="sr-settings__side-col" aria-label="Aparência">
            <AccentColorSettingsCard />
            <AppearanceSettingsCard />
          </section>
        </div>
      </main>
    </AppShell>
  );
}


