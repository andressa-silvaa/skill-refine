import { useTranslation } from 'react-i18next';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useDashboard } from '@/features/dashboard';
import { getApiErrorMessage } from '@/shared/api';
import { notify } from '@/shared/lib/notify';
import { Button, Card } from '@/shared/ui';
import { AppShell } from '@/widgets/app-shell';
import {
  DashboardHeader,
  DashboardStatsGrid,
  DashboardChartsSection,
  DashboardBottomSection,
} from '@/widgets/dashboard';

import '@/shared/ui/sr-controls/SrControls.css';
import './DashboardPage.css';

export function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useDashboard();

  useEffect(() => {
    if (!error) return;
    notify.error(getApiErrorMessage(error, t('dashboard.toast.loadError')));
  }, [error, t]);

  if (loading && !data) {
    return (
      <AppShell>
        <main className="sr-dashboard" aria-label={t('dashboard.mainAria')}>
          <div className="sr-dashboard__container">
            <Card className="sr-dashboard-state">
              <div className="sr-dashboard-state__icon" aria-hidden>
                <i className="fa-solid fa-chart-line" />
              </div>
              <h2 className="sr-dashboard-state__title">{t('dashboard.loadingTitle')}</h2>
              <p className="sr-dashboard-state__subtitle">{t('dashboard.loadingSubtitle')}</p>
            </Card>
          </div>
        </main>
      </AppShell>
    );
  }

  if (error && !data) {
    return (
      <AppShell>
        <main className="sr-dashboard" aria-label={t('dashboard.mainAria')}>
          <div className="sr-dashboard__container">
            <Card className="sr-dashboard-state">
              <div className="sr-dashboard-state__icon is-error" aria-hidden>
                <i className="fa-solid fa-circle-exclamation" />
              </div>
              <h2 className="sr-dashboard-state__title">{t('dashboard.errorTitle')}</h2>
              <p className="sr-dashboard-state__subtitle">{t('dashboard.errorSubtitle')}</p>
              <Button variant="primary" onClick={() => void reload()}>
                {t('dashboard.retry')}
              </Button>
            </Card>
          </div>
        </main>
      </AppShell>
    );
  }

  if (!data) return null;

  const isEmpty = data.summary.totalResumes === 0;

  return (
    <AppShell>
      <main className="sr-dashboard" aria-label={t('dashboard.mainAria')}>
        <div className="sr-dashboard__container">
          <DashboardHeader userName={data.summary.userName} />

          {isEmpty ? (
            <Card className="sr-dashboard-state">
              <div className="sr-dashboard-state__icon" aria-hidden>
                <i className="fa-regular fa-file-lines" />
              </div>
              <h2 className="sr-dashboard-state__title">{t('dashboard.emptyTitle')}</h2>
              <p className="sr-dashboard-state__subtitle">{t('dashboard.emptySubtitle')}</p>
              <Button variant="primary" onClick={() => navigate('/protected/resumes?create=1')}>
                {t('dashboard.emptyCta')}
              </Button>
            </Card>
          ) : (
            <>
              <section className="sr-dashboard__section" aria-label={t('dashboard.stats.aria')}>
                <DashboardStatsGrid summary={data.summary} />
              </section>

              <section className="sr-dashboard__section" aria-label={t('dashboard.charts.aria')}>
                <DashboardChartsSection
                  scoreEvolution={data.scoreEvolution}
                  competencies={data.competencies}
                />
              </section>

              <section className="sr-dashboard__section" aria-label={t('dashboard.bottom.aria')}>
                <DashboardBottomSection
                  recentResumes={data.recentResumes}
                  aiInsights={data.aiInsights}
                />
              </section>
            </>
          )}
        </div>
      </main>
    </AppShell>
  );
}
