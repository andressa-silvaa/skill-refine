import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import type { RecentResume } from '../model/useDashboardMock';
import { DashboardSectionCard } from './DashboardSectionCard';
import { RecentResumeItem } from './RecentResumeItem';

type Props = {
  items: RecentResume[];
};

export function DashboardRecentResumes({ items }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const action = (
    <button onClick={() => navigate('/protected/resumes')}>
      {t('dashboard.actions.viewAll')}
    </button>
  );

  return (
    <DashboardSectionCard
      title={t('dashboard.sections.recentResumes')}
      action={action}
    >
      {items.map((item) => (
        <RecentResumeItem key={item.id} item={item} />
      ))}
    </DashboardSectionCard>
  );
}
