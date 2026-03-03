import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import type { AiInsight } from '../model/useDashboardMock';
import { DashboardSectionCard } from './DashboardSectionCard';
import { InsightItem } from './InsightItem';

type Props = {
  items: AiInsight[];
};

export function DashboardInsights({ items }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const action = (
    <button onClick={() => navigate('/protected/ai-analysis')}>
      {t('dashboard.actions.analyze')}
    </button>
  );

  return (
    <DashboardSectionCard
      title={t('dashboard.sections.aiInsights')}
      action={action}
    >
      {items.map((item) => (
        <InsightItem key={item.id} item={item} />
      ))}
    </DashboardSectionCard>
  );
}
