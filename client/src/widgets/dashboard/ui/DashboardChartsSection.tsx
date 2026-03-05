import { useTranslation } from 'react-i18next';

import type { Competency, ScorePoint } from '../model/types';
import { DashboardSectionCard } from './DashboardSectionCard';
import { DashboardScoreChart } from './DashboardScoreChart';
import { DashboardCompetencies } from './DashboardCompetencies';

import './DashboardChartsSection.css';

type Props = {
  scoreEvolution: ScorePoint[];
  competencies: Competency[];
};

export function DashboardChartsSection({ scoreEvolution, competencies }: Props) {
  const { t } = useTranslation();

  return (
    <div className="sr-dash-charts-section">
      <DashboardSectionCard title={t('dashboard.sections.scoreEvolution')}>
        {scoreEvolution.length === 0 ? (
          <p className="sr-dash-chart-empty">{t('dashboard.sections.noChartData')}</p>
        ) : (
          <DashboardScoreChart data={scoreEvolution} />
        )}
      </DashboardSectionCard>

      <DashboardSectionCard title={t('dashboard.sections.competencies')}>
        {competencies.length === 0 ? (
          <p className="sr-dash-chart-empty">{t('dashboard.sections.noCompetenciesData')}</p>
        ) : (
          <DashboardCompetencies data={competencies} />
        )}
      </DashboardSectionCard>
    </div>
  );
}
