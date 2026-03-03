import { useTranslation } from 'react-i18next';

import { AppShell } from '@/widgets/app-shell';
import {
  DashboardHeader,
  DashboardStatsGrid,
  DashboardChartsSection,
  DashboardBottomSection,
  useDashboardMock,
} from '@/widgets/dashboard';

import '@/shared/ui/sr-controls/SrControls.css';
import './DashboardPage.css';

export function DashboardPage() {
  const { t } = useTranslation();
  const data = useDashboardMock();

  return (
    <AppShell>
      <main className="sr-dashboard" aria-label={t('dashboard.mainAria')}>
        <div className="sr-dashboard__container">
          <DashboardHeader userName={data.summary.userName} />

          <section
            className="sr-dashboard__section"
            aria-label={t('dashboard.stats.aria')}
          >
            <DashboardStatsGrid summary={data.summary} />
          </section>

          <section
            className="sr-dashboard__section"
            aria-label={t('dashboard.charts.aria')}
          >
            <DashboardChartsSection
              scoreEvolution={data.scoreEvolution}
              competencies={data.competencies}
            />
          </section>

          <section
            className="sr-dashboard__section"
            aria-label={t('dashboard.bottom.aria')}
          >
            <DashboardBottomSection
              recentResumes={data.recentResumes}
              aiInsights={data.aiInsights}
            />
          </section>
        </div>
      </main>
    </AppShell>
  );
}
