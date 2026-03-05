import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import type { AiInsight } from '../model/types';
import { DashboardSectionCard } from './DashboardSectionCard';
import { InsightItem } from './InsightItem';

type Props = {
  items: AiInsight[];
};

export function DashboardInsights({ items }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const action = (
    <button
      onClick={() => {
        const resumeId = items[0]?.resumeId;
        if (resumeId) {
          navigate(`/protected/ai-analysis?resumeId=${encodeURIComponent(resumeId)}`);
          return;
        }
        navigate('/protected/ai-analysis');
      }}
    >
      {t('dashboard.actions.analyze')}
    </button>
  );

  return (
    <DashboardSectionCard
      title={t('dashboard.sections.aiInsights')}
      action={action}
    >
      {items.length === 0 ? (
        <p className="sr-dash-list-empty">{t('dashboard.sections.noInsights')}</p>
      ) : (
        items.map((item) => (
          <InsightItem
            key={item.id}
            item={item}
            onClick={() => {
              if (item.resumeId) {
                navigate(`/protected/ai-analysis?resumeId=${encodeURIComponent(item.resumeId)}`);
                return;
              }
              navigate('/protected/ai-analysis');
            }}
          />
        ))
      )}
    </DashboardSectionCard>
  );
}
