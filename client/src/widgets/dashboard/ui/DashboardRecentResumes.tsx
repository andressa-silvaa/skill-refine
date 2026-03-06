import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import type { RecentResume } from '../model/types';
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
      {items.length === 0 ? (
        <p className="sr-dash-list-empty">{t('dashboard.sections.noRecentResumes')}</p>
      ) : (
        items.map((item) => (
          <RecentResumeItem
            key={item.id}
            item={item}
            onClick={() =>
              navigate(`/protected/resumes?editResumeId=${encodeURIComponent(item.id)}`)
            }
          />
        ))
      )}
    </DashboardSectionCard>
  );
}
