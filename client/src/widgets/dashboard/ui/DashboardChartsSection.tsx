import { useTranslation } from 'react-i18next';

import type { Competency, ScorePoint } from '../model/useDashboardMock';
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
        <DashboardScoreChart data={scoreEvolution} />
      </DashboardSectionCard>

      <DashboardSectionCard title={t('dashboard.sections.competencies')}>
        <DashboardCompetencies data={competencies} />
      </DashboardSectionCard>
    </div>
  );
}
